"""Two independent cookie jars exercising a real local HTTP server."""
import httpx
from test_qa import live_server
from test_security import secure_settings
from helpers import sign_in


def test_two_users_over_real_http_cannot_cross_dataset_boundaries(live_server):
    alice,settings=live_server
    response=alice.post("/api/datasets",files={"file":("http-isolation.csv",b"category,amount\nA,10\nB,20\nA,5\n")})
    assert response.status_code == 201
    dataset=response.json()["id"]
    with httpx.Client(base_url=alice.base_url,timeout=15) as bob:
        sign_in(bob,"http-bob@example.com")
        assert bob.get("/api/datasets").json()["items"] == []
        assert bob.get(f"/api/datasets/{dataset}/preview").status_code == 404
        assert bob.post(f"/api/datasets/{dataset}/query",json={}).status_code == 404
        assert bob.post(f"/api/datasets/{dataset}/ai/ask",json={"question":"count"}).status_code == 404
        assert bob.get(f"/api/datasets/{dataset}/export").status_code == 404
        assert bob.delete(f"/api/datasets/{dataset}").status_code == 404
        own=alice.post(f"/api/datasets/{dataset}/ai/ask",json={"question":"Sum amount by category"})
        assert own.status_code == 200
        assert own.json()["results"]["rows"] == [{"category":"A","total":15.0},{"category":"B","total":20.0}]
        exported=alice.post(f"/api/datasets/{dataset}/export",json={"columns":["amount"]})
        assert exported.status_code == 200
        assert '"10"' in exported.text
        assert alice.get("/api/datasets").headers["access-control-allow-credentials"] == "true"
        assert alice.post("/api/auth/logout").status_code == 204
        assert alice.get(f"/api/datasets/{dataset}/preview").status_code == 401
        assert bob.get("/api/auth/me").status_code == 200
