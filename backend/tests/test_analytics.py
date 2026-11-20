from __future__ import annotations

from fastapi.testclient import TestClient


SALES = b"date,category,amount,region\n2026-01-01,A,10,North\n2026-01-15,A,20,South\n2026-02-01,B,5,North\n2026-02-02,B,,North\n"


def create_sales(client: TestClient) -> str:
    response = client.post("/api/datasets", files={"file": ("sales.csv", SALES, "text/csv")})
    assert response.status_code == 201
    return response.json()["id"]


def query(client: TestClient, dataset_id: str, body: dict):
    return client.post(f"/api/datasets/{dataset_id}/query", json=body)


def test_filter_sort_selection_and_pagination(client: TestClient):
    dataset_id = create_sales(client)
    response = query(client, dataset_id, {
        "columns": ["category", "amount"],
        "filters": [{"column": "amount", "operator": "gte", "value": 10}],
        "sorts": [{"column": "amount", "direction": "desc"}],
        "offset": 0, "limit": 1,
    })
    assert response.status_code == 200
    result = response.json()
    assert result["total_rows"] == 2
    assert result["rows"] == [{"category": "A", "amount": 20.0}]


def test_grouping_and_aggregation_accuracy(client: TestClient):
    dataset_id = create_sales(client)
    response = query(client, dataset_id, {
        "group_by": ["category"],
        "aggregations": [
            {"function": "count", "alias": "orders"},
            {"function": "sum", "column": "amount", "alias": "total_amount"},
            {"function": "avg", "column": "amount", "alias": "average_amount"},
            {"function": "min", "column": "amount", "alias": "minimum"},
            {"function": "max", "column": "amount", "alias": "maximum"},
        ],
        "sorts": [{"column": "category", "direction": "asc"}],
    })
    assert response.status_code == 200
    rows = response.json()["rows"]
    assert rows[0] == {"category": "A", "orders": 2, "total_amount": 30.0, "average_amount": 15.0, "minimum": 10.0, "maximum": 20.0}
    assert rows[1]["orders"] == 2
    assert rows[1]["total_amount"] == 5.0
    assert response.json()["chart"]["dimension"] == "category"


def test_date_grouping(client: TestClient):
    dataset_id = create_sales(client)
    response = query(client, dataset_id, {
        "date_group": {"column": "date", "granularity": "month", "alias": "month"},
        "aggregations": [{"function": "sum", "column": "amount", "alias": "revenue"}],
        "sorts": [{"column": "month", "direction": "asc"}],
    })
    assert response.status_code == 200
    assert [row["revenue"] for row in response.json()["rows"]] == [30.0, 5.0]


def test_missing_values_and_null_filter(client: TestClient):
    dataset_id = create_sales(client)
    response = query(client, dataset_id, {
        "columns": ["category", "amount"],
        "filters": [{"column": "amount", "operator": "is_null"}],
    })
    assert response.status_code == 200
    assert response.json()["rows"] == [{"category": "B", "amount": None}]


def test_empty_dataset_returns_empty_result(client: TestClient):
    upload = client.post("/api/datasets", files={"file": ("empty.csv", b"name,value\n", "text/csv")})
    response = query(client, upload.json()["id"], {"columns": ["name"], "limit": 25})
    assert response.status_code == 200
    assert response.json()["rows"] == []
    assert response.json()["total_rows"] == 0


def test_invalid_columns_operators_and_sql_payloads_are_rejected(client: TestClient):
    dataset_id = create_sales(client)
    invalid_column = query(client, dataset_id, {"columns": ["amount\"; DROP TABLE datasets; --"]})
    invalid_operator = query(client, dataset_id, {"filters": [{"column": "category", "operator": "gt", "value": "A"}]})
    unrestricted_sql = query(client, dataset_id, {"sql": "DROP TABLE datasets", "columns": ["category"]})
    assert invalid_column.status_code == 422
    assert invalid_column.json()["error"]["code"] == "invalid_column"
    assert invalid_operator.status_code == 422
    assert invalid_operator.json()["error"]["code"] == "invalid_operator"
    assert unrestricted_sql.status_code == 422
    assert client.get(f"/api/datasets/{dataset_id}").status_code == 200


def test_query_limits_and_complexity_validation(client: TestClient):
    dataset_id = create_sales(client)
    assert query(client, dataset_id, {"limit": 201}).status_code == 422
    too_many_filters = {"filters": [{"column": "category", "operator": "eq", "value": "A"}] * 11}
    assert query(client, dataset_id, too_many_filters).status_code == 422
    invalid_in = query(client, dataset_id, {"filters": [{"column": "category", "operator": "in", "value": []}]})
    assert invalid_in.status_code == 422
