from __future__ import annotations

from io import BytesIO

import pandas as pd
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from helpers import sign_in


def upload_csv(client: TestClient, content: bytes, name: str = "sales.csv"):
    return client.post("/api/datasets", files={"file": (name, content, "text/csv")})


def test_health(client: TestClient):
    assert client.get("/api/health").json() == {"status": "ok", "service": "smartanalytics-api"}


def test_valid_csv_upload_and_missing_values(client: TestClient):
    response = upload_csv(client, b"name,revenue,region\nA,10,North\nB,,\n")
    assert response.status_code == 201
    dataset = response.json()
    assert dataset["row_count"] == 2
    assert dataset["column_count"] == 3
    assert dataset["missing_cell_count"] == 2
    assert dataset["source"] == "upload"
    profile = client.get(f"/api/datasets/{dataset['id']}/profile").json()
    assert profile["quality"]["missing_cell_count"] == 2
    assert profile["numeric"][0]["column"] == "revenue"


def test_valid_xlsx_upload(client: TestClient):
    buffer = BytesIO()
    pd.DataFrame({"city": ["Rabat", "Casablanca"], "orders": [3, 5]}).to_excel(buffer, index=False)
    response = client.post(
        "/api/datasets", files={"file": ("cities.xlsx", buffer.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
    )
    assert response.status_code == 201
    assert response.json()["file_type"] == "xlsx"
    assert response.json()["row_count"] == 2


def test_invalid_extension(client: TestClient):
    response = client.post("/api/datasets", files={"file": ("notes.txt", b"hello", "text/plain")})
    assert response.status_code == 415
    assert response.json()["error"]["code"] == "unsupported_file_type"


def test_corrupted_files_are_rejected_and_not_persisted(client: TestClient):
    csv_response = upload_csv(client, b'column\n"unterminated', "broken.csv")
    xlsx_response = client.post("/api/datasets", files={"file": ("broken.xlsx", b"not a zip workbook", "application/octet-stream")})
    assert csv_response.status_code == 422
    assert xlsx_response.status_code == 422
    assert client.get("/api/datasets").json()["total"] == 0


def test_header_only_empty_dataset_is_valid(client: TestClient):
    response = upload_csv(client, b"name,value\n", "empty.csv")
    assert response.status_code == 201
    dataset = response.json()
    assert dataset["row_count"] == 0
    profile = client.get(f"/api/datasets/{dataset['id']}/profile").json()
    assert profile["quality"]["completeness_percentage"] is None


def test_preview_pagination_and_validation(client: TestClient):
    dataset = upload_csv(client, b"id,name\n1,A\n2,B\n3,C\n").json()
    response = client.get(f"/api/datasets/{dataset['id']}/preview?offset=1&limit=1")
    assert response.status_code == 200
    assert response.json()["rows"] == [{"id": 2, "name": "B"}]
    assert response.json()["total_rows"] == 3
    invalid = client.get(f"/api/datasets/{dataset['id']}/preview?limit=101")
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "validation_error"


def test_upload_size_limit(data_dir):
    client = TestClient(create_app(Settings(cookie_secure=False,data_dir=data_dir, max_upload_bytes=8)))
    sign_in(client)
    response = upload_csv(client, b"id,value\n1,42\n")
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "upload_too_large"


def test_delete_dataset(client: TestClient):
    dataset = upload_csv(client, b"id\n1\n").json()
    assert client.delete(f"/api/datasets/{dataset['id']}").status_code == 204
    assert client.get(f"/api/datasets/{dataset['id']}").status_code == 404
    assert client.get("/api/datasets").json()["total"] == 0


def test_metadata_persists_after_app_restart(data_dir):
    settings = Settings(cookie_secure=False,data_dir=data_dir, max_upload_bytes=1024 * 1024)
    first = TestClient(create_app(settings))
    sign_in(first)
    dataset = upload_csv(first, b"id,value\n1,42\n").json()
    first.close()
    second = TestClient(create_app(settings))
    sign_in(second,register=False)
    assert second.get(f"/api/datasets/{dataset['id']}").status_code == 200
    assert second.get(f"/api/datasets/{dataset['id']}/preview").json()["rows"][0]["value"] == 42


def test_filename_is_sanitized_and_uuid_is_used_for_storage(client: TestClient, data_dir):
    response = upload_csv(client, b"id\n1\n", "../unsafe<>name.csv")
    dataset = response.json()
    assert response.status_code == 201
    assert dataset["original_filename"] == "unsafe_name.csv"
    stored = list((data_dir / "files").iterdir())
    assert len(stored) == 1
    assert stored[0].name == f"{dataset['id']}.csv"

