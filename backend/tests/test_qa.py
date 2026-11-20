"""Stabilization regressions and a real HTTP journey on isolated synthetic data."""
from io import BytesIO
from pathlib import Path
import socket
import sqlite3
import threading
import time
from types import SimpleNamespace
from unittest.mock import MagicMock

import httpx
import pandas as pd
import pytest
import uvicorn

from app.ai import AIService
from app.ai_models import AnalyticalPlan, Explanation
from app.config import Settings
from app.main import create_app
from app.models import AnalyticsQuerySpec
from app.profiling import _unique_column_names
from app.storage import DatasetRepository
from helpers import sign_in
from test_security import secure_settings
from dataclasses import replace


def test_normalized_headers_preserve_all_columns(client):
    response = client.post("/api/datasets",files={"file":("headers.csv",b"x, x,x_2,X\n1,2,3,4\n","text/csv")})
    assert response.status_code == 201
    metadata=response.json()
    names=[c["name"] for c in metadata["columns"]]
    assert len({name.casefold() for name in names}) == 4
    result=client.post(f"/api/datasets/{metadata['id']}/query",json={"columns":names})
    assert result.status_code == 200
    assert list(result.json()["rows"][0].values()) == [1,2,3,4]
    assert _unique_column_names(["x","x","x_2","X"]) == ["x","x_3","x_2","X_4"]


@pytest.mark.parametrize("alias",["category","CATEGORY"])
def test_group_alias_collision_rejected(client,alias):
    dataset=client.post("/api/datasets",files={"file":("a.csv",b"category,amount\nA,2\n","text/csv")}).json()["id"]
    response=client.post(f"/api/datasets/{dataset}/query",json={"group_by":["category"],"aggregations":[{"function":"sum","column":"amount","alias":alias}]})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_alias"


@pytest.mark.parametrize("value",[{"sql":"DROP TABLE x"},[1,[2]],"x"*4001])
def test_invalid_filter_values_rejected(client,value):
    dataset=client.post("/api/datasets",files={"file":("a.csv",b"name\nA\n","text/csv")}).json()["id"]
    response=client.post(f"/api/datasets/{dataset}/query",json={"filters":[{"column":"name","operator":"eq","value":value}]})
    assert response.status_code == 422


def test_sqlite_connections_close_and_rollback(tmp_path):
    repository=DatasetRepository(tmp_path)
    with repository._connect() as connection:
        connection.execute("CREATE TABLE test(value INTEGER)")
    with pytest.raises(sqlite3.ProgrammingError):
        connection.execute("SELECT 1")
    with pytest.raises(RuntimeError):
        with repository._connect() as connection:
            connection.execute("INSERT INTO test VALUES (1)")
            raise RuntimeError("rollback")
    with repository._connect() as connection:
        assert connection.execute("SELECT COUNT(*) FROM test").fetchone()[0] == 0
    repository.database_path.unlink()  # Test-only isolated database, proves no Windows handle leak.


def test_multiple_dimensions_do_not_generate_misleading_chart(client):
    dataset=client.post("/api/datasets",files={"file":("a.csv",b"category,region,amount\nA,N,2\nA,S,3\n","text/csv")}).json()["id"]
    response=client.post(f"/api/datasets/{dataset}/query",json={"group_by":["category","region"],"aggregations":[{"function":"sum","column":"amount","alias":"total"}]})
    assert response.status_code == 200
    assert response.json()["chart"] is None
    assert len(response.json()["rows"]) == 2


def test_corrupt_workbook_xml_returns_structured_error(client):
    from zipfile import ZipFile
    buffer=BytesIO()
    with ZipFile(buffer,"w") as archive:
        archive.writestr("[Content_Types].xml","<invalid")
    response=client.post("/api/datasets",files={"file":("bad.xlsx",buffer.getvalue(),"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_dataset_file"


@pytest.fixture
def live_server(tmp_path, monkeypatch, secure_settings):
    monkeypatch.setattr("app.ai.dotenv_values",lambda *args,**kwargs:{})
    def generate(self,instructions,payload,model):
        if model is Explanation:
            return Explanation(explanation="A totals 15 and B totals 20, based on computed results.")
        question=payload["question"]
        if question in {"ambiguous","unsupported","injection"}:
            return AnalyticalPlan(status="clarification" if question == "ambiguous" else "unsupported",message="Specify an analytical measure." if question == "ambiguous" else "This operation is unsupported.",query=None)
        return AnalyticalPlan(status="answer",message="",query=AnalyticsQuerySpec(group_by=["category"],aggregations=[{"function":"sum","column":"amount","alias":"total"}],sorts=[{"column":"category"}],limit=50).model_dump())
    monkeypatch.setattr(AIService,"_generate",generate)
    original=AIService.__init__
    def init(self,datasets):
        original(self,datasets)
        self.client=MagicMock()
    monkeypatch.setattr(AIService,"__init__",init)
    settings=replace(secure_settings, data_dir=tmp_path/"isolated-http")
    listener=socket.socket()
    listener.bind(("127.0.0.1",0))
    address=f"http://127.0.0.1:{listener.getsockname()[1]}"
    server=uvicorn.Server(uvicorn.Config(create_app(settings),log_level="critical"))
    thread=threading.Thread(target=server.run,kwargs={"sockets":[listener]},daemon=True)
    thread.start()
    deadline=time.monotonic()+10
    while not server.started:
        if not thread.is_alive() or time.monotonic()>deadline:
            raise RuntimeError("Isolated HTTP server did not start")
        time.sleep(.01)
    try:
        with httpx.Client(base_url=address,timeout=15) as client:
            sign_in(client)
            yield client,settings
    finally:
        server.should_exit=True
        thread.join(timeout=10)
        listener.close()
        assert not thread.is_alive()


def test_full_http_csv_xlsx_ai_cors_persistence_and_delete(live_server):
    client,settings=live_server
    assert client.get("/api/health").status_code == 200
    allowed=client.options("/api/datasets",headers={"Origin":"http://127.0.0.1:5173","Access-Control-Request-Method":"POST","Access-Control-Request-Headers":"content-type"})
    assert allowed.headers["access-control-allow-origin"] == "http://127.0.0.1:5173"
    denied=client.options("/api/datasets",headers={"Origin":"https://untrusted.example","Access-Control-Request-Method":"POST"})
    assert "access-control-allow-origin" not in denied.headers
    frame=pd.DataFrame({"date":["2026-01-01","2026-01-02","2026-02-01"],"category":["A","B","A"],"amount":[10,20,5]})
    expected=frame.groupby("category")["amount"].sum().to_dict()
    excel=BytesIO(); frame.to_excel(excel,index=False)
    for filename,content in [("journey.csv",frame.to_csv(index=False).encode()),("journey.xlsx",excel.getvalue())]:
        upload=client.post("/api/datasets",files={"file":(filename,content)})
        assert upload.status_code == 201
        dataset=upload.json(); dataset_id=dataset["id"]
        assert dataset["row_count"] == 3
        assert dataset["columns"][0]["type"] == "datetime"
        assert client.get(f"/api/datasets/{dataset_id}/preview").json()["rows"][0]["amount"] == 10
        assert client.get(f"/api/datasets/{dataset_id}/profile").json()["quality"]["completeness_percentage"] == 100
        # A new repository reads persisted metadata, without sharing an application object.
        from app.database import Database
        from app.repository import DatasetRepository as SQLRepository
        database=Database(settings)
        assert SQLRepository(settings.data_dir,database).get(dataset_id,client.get("/api/auth/me").json()["id"]).row_count == 3
        database.close()
        filtered=client.post(f"/api/datasets/{dataset_id}/query",json={"columns":["amount"],"filters":[{"column":"amount","operator":"gte","value":10}],"sorts":[{"column":"amount","direction":"desc"}]})
        assert filtered.json()["rows"] == [{"amount":20},{"amount":10}]
        response=client.post(f"/api/datasets/{dataset_id}/ai/ask",json={"question":"sum amount by category"})
        assert response.status_code == 200
        body=response.json()
        assert {r["category"]:r["total"] for r in body["results"]["rows"]} == expected
        assert body["chart"]["rows"] == body["results"]["rows"]
        for question,status in [("ambiguous","clarification"),("unsupported","unsupported"),("injection","unsupported")]:
            assert client.post(f"/api/datasets/{dataset_id}/ai/ask",json={"question":question}).json()["status"] == status
        assert client.post(f"/api/datasets/{dataset_id}/query",json={"sql":"DROP TABLE datasets"}).status_code == 422
        assert client.delete(f"/api/datasets/{dataset_id}").status_code == 204
        assert client.get(f"/api/datasets/{dataset_id}").status_code == 404
        assert client.post(f"/api/datasets/{dataset_id}/query",json={}).status_code == 404
    assert client.get("/api/datasets").json()["total"] == 0


def test_date_minimum_is_not_a_numeric_chart(client):
    dataset=client.post("/api/datasets",files={"file":("dates.csv",b"category,date\nA,2026-01-01\nA,2026-02-01\n","text/csv")}).json()["id"]
    response=client.post(f"/api/datasets/{dataset}/query",json={"group_by":["category"],"aggregations":[{"function":"min","column":"date","alias":"first_date"}]})
    assert response.status_code == 200
    assert response.json()["chart"] is None
    assert response.json()["rows"][0]["first_date"].startswith("2026-01-01")


def test_workbook_archive_member_limit(client):
    from zipfile import ZipFile
    buffer=BytesIO()
    with ZipFile(buffer,"w") as archive:
        for index in range(2001):
            archive.writestr(f"item{index}.xml","")
    response=client.post("/api/datasets",files={"file":("oversized.xlsx",buffer.getvalue())})
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "workbook_too_large"


def test_workbook_xml_entities_are_rejected(client):
    from zipfile import ZipFile
    buffer=BytesIO()
    with ZipFile(buffer,"w") as archive:
        archive.writestr("[Content_Types].xml",'<?xml version="1.0"?><!DOCTYPE x [<!ENTITY attack "untrusted">]><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">&attack;</Types>')
    response=client.post("/api/datasets",files={"file":("entities.xlsx",buffer.getvalue())})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_dataset_file"
