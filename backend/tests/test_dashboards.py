"""Dashboard Studio CRUD, validation, quotas and tenant isolation."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from helpers import ORIGIN, sign_in
from test_security import secure_settings


def upload(client: TestClient, name: str = "orders.csv") -> str:
    response = client.post(
        "/api/datasets",
        files={"file": (name, b"category,amount,date\nA,10,2026-01-01\nB,20,2026-02-01\n", "text/csv")},
    )
    assert response.status_code == 201, response.json()
    return response.json()["id"]


def create_dashboard(client: TestClient, name: str = "Sales overview") -> dict:
    response = client.post("/api/dashboards", json={"name": name, "description": "Synthetic analytics"})
    assert response.status_code == 201, response.json()
    return response.json()


def table_widget(dataset_id: str, revision: int, **overrides) -> dict:
    body = {
        "expected_revision": revision,
        "dataset_id": dataset_id,
        "title": "Orders table",
        "query": {
            "columns": ["category", "amount"],
            "filters": [], "sorts": [], "group_by": [], "aggregations": [],
            "offset": 0, "limit": 25,
        },
        "visualization": {"type": "table"},
        "width_columns": 6,
        "height_rows": 4,
    }
    body.update(overrides)
    return body


def chart_widget(dataset_id: str, revision: int) -> dict:
    return {
        "expected_revision": revision,
        "dataset_id": dataset_id,
        "title": "Amount by category",
        "query": {
            "columns": [], "filters": [], "sorts": [], "group_by": ["category"],
            "aggregations": [{"function": "sum", "column": "amount", "alias": "sum_amount"}],
            "offset": 0, "limit": 25,
        },
        "visualization": {"type": "bar", "series": ["sum_amount"]},
    }


def test_dashboard_and_widget_crud_with_optimistic_revision(client: TestClient):
    dataset_id = upload(client)
    dashboard = create_dashboard(client)
    dashboard_id = dashboard["id"]
    assert dashboard["revision"] == 1 and dashboard["widgets"] == []

    added = client.post(f"/api/dashboards/{dashboard_id}/widgets", json=chart_widget(dataset_id, 1))
    assert added.status_code == 201, added.json()
    detail = added.json()
    assert detail["revision"] == 2 and detail["widget_count"] == 1
    widget = detail["widgets"][0]
    assert widget["dataset_status"] == "ready"
    assert widget["query"]["aggregations"][0]["alias"] == "sum_amount"

    fetched = client.get(f"/api/dashboards/{dashboard_id}/widgets/{widget['id']}")
    assert fetched.status_code == 200 and fetched.json()["id"] == widget["id"]

    updated_widget = client.patch(
        f"/api/dashboards/{dashboard_id}/widgets/{widget['id']}",
        json={"expected_revision": 2, "title": "Updated chart", "width_columns": 12},
    )
    assert updated_widget.status_code == 200, updated_widget.json()
    assert updated_widget.json()["revision"] == 3
    assert updated_widget.json()["widgets"][0]["title"] == "Updated chart"

    stale = client.patch(f"/api/dashboards/{dashboard_id}", json={"expected_revision": 2, "name": "Stale"})
    assert stale.status_code == 409
    assert stale.json()["error"]["code"] == "dashboard_conflict"

    renamed = client.patch(
        f"/api/dashboards/{dashboard_id}",
        json={"expected_revision": 3, "name": "Executive overview", "description": None},
    )
    assert renamed.status_code == 200
    assert renamed.json()["revision"] == 4
    assert renamed.json()["description"] is None

    removed = client.delete(
        f"/api/dashboards/{dashboard_id}/widgets/{widget['id']}?expected_revision=4"
    )
    assert removed.status_code == 200
    assert removed.json()["revision"] == 5 and removed.json()["widgets"] == []

    deleted = client.delete(f"/api/dashboards/{dashboard_id}?expected_revision=5")
    assert deleted.status_code == 204
    assert client.get(f"/api/dashboards/{dashboard_id}").status_code == 404


def test_dataset_deletion_preserves_widget_history(client: TestClient):
    dataset_id = upload(client)
    dashboard = create_dashboard(client)
    detail = client.post(
        f"/api/dashboards/{dashboard['id']}/widgets",
        json=table_widget(dataset_id, 1),
    ).json()
    widget_id = detail["widgets"][0]["id"]

    assert client.delete(f"/api/datasets/{dataset_id}").status_code == 204
    widget = client.get(f"/api/dashboards/{dashboard['id']}/widgets/{widget_id}")
    assert widget.status_code == 200
    assert widget.json()["dataset_id"] is None
    assert widget.json()["dataset_id_snapshot"] == dataset_id
    assert widget.json()["dataset_name_snapshot"] == "orders"
    assert widget.json()["dataset_status"] == "dataset_deleted"


def test_contracts_reject_owner_code_and_incompatible_visualizations(client: TestClient):
    dataset_id = upload(client)
    dashboard = create_dashboard(client)
    dashboard_id = dashboard["id"]
    assert client.post("/api/dashboards", json={"name": "Injected", "owner_id": "someone"}).status_code == 422
    assert client.post("/api/dashboards", json={"name": "   "}).status_code == 422

    sql = table_widget(dataset_id, 1)
    sql["query"]["sql"] = "DROP TABLE users"
    assert client.post(f"/api/dashboards/{dashboard_id}/widgets", json=sql).status_code == 422

    javascript = table_widget(dataset_id, 1)
    javascript["visualization"]["expression"] = "window.alert(1)"
    assert client.post(f"/api/dashboards/{dashboard_id}/widgets", json=javascript).status_code == 422

    incompatible = table_widget(dataset_id, 1, visualization={"type": "pie", "series": ["amount"]})
    assert client.post(f"/api/dashboards/{dashboard_id}/widgets", json=incompatible).status_code == 422

    unknown = table_widget(dataset_id, 1)
    unknown["query"]["columns"] = ["not_a_column"]
    response = client.post(f"/api/dashboards/{dashboard_id}/widgets", json=unknown)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_column"


def test_dashboard_and_widget_quotas(client: TestClient):
    dataset_id = upload(client)
    first = create_dashboard(client, "Widget quota")
    revision = 1
    for index in range(12):
        response = client.post(
            f"/api/dashboards/{first['id']}/widgets",
            json=table_widget(dataset_id, revision, title=f"Widget {index + 1}"),
        )
        assert response.status_code == 201, response.json()
        revision = response.json()["revision"]
    exceeded = client.post(
        f"/api/dashboards/{first['id']}/widgets",
        json=table_widget(dataset_id, revision, title="Widget 13"),
    )
    assert exceeded.status_code == 409
    assert exceeded.json()["error"]["code"] == "widget_limit_reached"

    for index in range(49):
        assert client.post("/api/dashboards", json={"name": f"Dashboard {index + 2}"}).status_code == 201
    exceeded = client.post("/api/dashboards", json={"name": "Dashboard 51"})
    assert exceeded.status_code == 409
    assert exceeded.json()["error"]["code"] == "dashboard_limit_reached"


def test_dashboard_routes_are_owner_scoped_and_cors_allows_patch(tmp_path: Path):
    app = create_app(Settings(data_dir=tmp_path / "data", cookie_secure=False))
    alice = TestClient(app)
    bob = TestClient(app)
    sign_in(alice, "dashboard-alice@example.com")
    sign_in(bob, "dashboard-bob@example.com")
    try:
        alice_dataset = upload(alice, "alice.csv")
        alice_dashboard = create_dashboard(alice)
        dashboard_id = alice_dashboard["id"]
        assert bob.get("/api/dashboards").json()["items"] == []
        assert bob.get(f"/api/dashboards/{dashboard_id}").status_code == 404
        assert bob.patch(f"/api/dashboards/{dashboard_id}", json={"expected_revision": 1, "name": "Taken"}).status_code == 404
        assert bob.delete(f"/api/dashboards/{dashboard_id}?expected_revision=1").status_code == 404
        assert bob.post(
            f"/api/dashboards/{dashboard_id}/widgets",
            json=table_widget(alice_dataset, 1),
        ).status_code == 404

        preflight = alice.options(
            "/api/dashboards",
            headers={"Origin": ORIGIN, "Access-Control-Request-Method": "PATCH"},
        )
        assert preflight.status_code == 200
        assert "PATCH" in preflight.headers["access-control-allow-methods"]

        blocked = alice.post(
            "/api/dashboards",
            json={"name": "Blocked"},
            headers={"Origin": "https://attacker.example", "X-CSRF-Token": "invalid"},
        )
        assert blocked.status_code == 403
    finally:
        alice.close()
        bob.close()
        app.state.database.close()


def test_revision_check_is_atomic_for_concurrent_updates(secure_settings):
    app = create_app(secure_settings)
    first = TestClient(app)
    second = TestClient(app)
    sign_in(first, "revision@example.com")
    sign_in(second, "revision@example.com", register=False)
    dashboard = create_dashboard(first)
    try:
        def rename(client: TestClient, name: str):
            return client.patch(
                f"/api/dashboards/{dashboard['id']}",
                json={"expected_revision": 1, "name": name},
            ).status_code

        with ThreadPoolExecutor(max_workers=2) as pool:
            statuses = sorted(pool.map(lambda item: rename(*item), [(first, "First"), (second, "Second")]))
        assert statuses == [200, 409]
        assert first.get(f"/api/dashboards/{dashboard['id']}").json()["revision"] == 2
    finally:
        first.close()
        second.close()
        app.state.database.close()
