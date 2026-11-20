"""Authentication, CSRF, ownership and durable quotas. No external AI calls."""
import hashlib
import os
import secrets
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, update
from sqlalchemy.engine import make_url
from redis.exceptions import ConnectionError as RedisConnectionError

from app.config import Settings
from app.database import Database, migration_config
from app.db_models import AIUsage, DatasetRecord, OwnershipDecision, User, UserSession
from app.errors import ApiError
from app.main import create_app
from app.limits import RateLimiter
from app.auth import token_hash
from app.ai_models import AnalyticalPlan, Explanation
from app.models import AnalyticsQuerySpec
from helpers import sign_in, PASSWORD, ORIGIN


@pytest.fixture
def secure_settings(tmp_path):
    # Optional dedicated PostgreSQL test administrator; never points at an existing user database.
    admin_url=os.getenv("SMARTANALYTICS_TEST_ADMIN_URL")
    redis_options = {"redis_url": os.getenv("SMARTANALYTICS_TEST_REDIS_URL"),
                     "rate_limit_namespace": "sa-qa-" + uuid4().hex}
    if not admin_url:
        yield Settings(data_dir=tmp_path/"data",cookie_secure=False,**redis_options)
        return
    admin=create_engine(admin_url,isolation_level="AUTOCOMMIT")
    name="sa_qa_"+uuid4().hex
    with admin.connect() as connection:
        connection.exec_driver_sql(f'CREATE DATABASE "{name}"')
    url=make_url(admin_url).set(database=name).render_as_string(hide_password=False)
    try:
        yield Settings(data_dir=tmp_path/"data",cookie_secure=False,database_url=url,**redis_options)
    finally:
        with admin.connect() as connection:
            connection.exec_driver_sql(f'DROP DATABASE "{name}" WITH (FORCE)')
        admin.dispose()


@pytest.fixture
def accounts(secure_settings,monkeypatch):
    monkeypatch.setattr("app.ai.dotenv_values",lambda *args,**kwargs:{"OPENAI_API_KEY":"test-placeholder"})
    provider=MagicMock()
    monkeypatch.setattr("app.ai.OpenAI",lambda **kwargs:provider)
    app=create_app(secure_settings)
    a=TestClient(app); b=TestClient(app)
    a_id=sign_in(a,"alice@example.com")
    b_id=sign_in(b,"bob@example.com")
    try:
        yield app,a,b,a_id,b_id,provider
    finally:
        a.close(); b.close(); app.state.database.close()


def test_postgresql_pool_recovers_stale_connection(secure_settings):
    """Exercise SQLAlchemy pre-ping against an actually terminated disposable PG connection."""
    if not secure_settings.database_url:
        pytest.skip("Real PostgreSQL test administrator not supplied")
    from sqlalchemy import text
    from sqlalchemy.pool import NullPool
    database = Database(secure_settings)
    control = create_engine(secure_settings.database_url, poolclass=NullPool)
    try:
        with database.engine.connect() as connection:
            name = connection.execute(text("SELECT current_database()")).scalar_one()
            assert name.startswith("sa_qa_")
            previous_pid = connection.execute(text("SELECT pg_backend_pid()")).scalar_one()
        with control.connect() as connection:
            assert connection.execute(text("SELECT pg_terminate_backend(:pid)"), {"pid": previous_pid}).scalar_one()
        with database.engine.connect() as connection:
            assert connection.execute(text("SELECT 1")).scalar_one() == 1
            assert connection.execute(text("SELECT pg_backend_pid()")).scalar_one() != previous_pid
    finally:
        control.dispose()
        database.close()


def upload(client):
    response=client.post("/api/datasets",files={"file":("synthetic.csv",b"category,amount\nA,10\nB,20\nA,5\n","text/csv")})
    assert response.status_code == 201
    return response.json()["id"]


def test_registration_normalization_hash_and_uniqueness(secure_settings):
    app=create_app(secure_settings)
    client=TestClient(app)
    user_id=sign_in(client,"  Mixed.Case@Example.com  ")
    assert client.get("/api/auth/me").json() == {"id":user_id,"email":"mixed.case@example.com"}
    with app.state.database.session() as db:
        user=db.get(User,user_id)
        assert user.password_hash.startswith("$argon2id$")
        assert PASSWORD not in user.password_hash
    duplicate=client.post("/api/auth/register",json={"email":"MIXED.CASE@example.com","password":PASSWORD})
    assert duplicate.status_code == 409
    assert "password_hash" not in duplicate.text
    app.state.database.close()


@pytest.mark.parametrize("password",["short","abcdefghijklmnop","NoNumbersHere!!","NoSymbolHere123", "A"*129])
def test_password_policy(secure_settings,password):
    app=create_app(secure_settings); client=TestClient(app)
    client.headers.update({"Origin":ORIGIN,"X-CSRF-Token":client.get("/api/auth/session").json()["csrf_token"]})
    assert client.post("/api/auth/register",json={"email":"new@example.com","password":password}).status_code == 422
    app.state.database.close()


def test_login_generic_errors_and_success(accounts):
    app,a,b,a_id,b_id,_=accounts
    for email in ["alice@example.com","absent@example.com"]:
        response=a.post("/api/auth/login",json={"email":email,"password":"Wrong-Password123!"})
        assert response.status_code == 401
        assert response.json()["error"]["message"] == "Email or password is incorrect."
    response=a.post("/api/auth/login",json={"email":"ALICE@example.com","password":PASSWORD})
    assert response.status_code == 200
    assert response.json()["user"]["id"] == a_id


def test_logout_revokes_replay_and_keeps_other_users(accounts):
    app,a,b,a_id,b_id,_=accounts
    name=app.state.auth.cookie_name
    old_cookie=a.cookies.get(name)
    assert a.post("/api/auth/logout").status_code == 204
    assert a.get("/api/auth/me").status_code == 401
    replay=TestClient(app); replay.cookies.set(name,old_cookie)
    assert replay.get("/api/auth/me").status_code == 401
    assert b.get("/api/auth/me").json()["id"] == b_id


@pytest.mark.parametrize("expired_field",["expires_at","last_seen_at"])
def test_session_expiration(accounts,expired_field):
    app,a,b,a_id,b_id,_=accounts
    with app.state.database.session.begin() as db:
        db.execute(update(UserSession).where(UserSession.user_id == a_id).values(**{expired_field:0}))
    assert a.get("/api/auth/me").status_code == 401
    assert b.get("/api/auth/me").status_code == 200


def test_session_cookie_flags_rotation_and_hashed_storage(secure_settings):
    app=create_app(replace(secure_settings,cookie_secure=True))
    client=TestClient(app,base_url="https://testserver")
    boot=client.get("/api/auth/session")
    name=app.state.auth.cookie_name
    initial=client.cookies.get(name)
    client.headers.update({"Origin":ORIGIN,"X-CSRF-Token":boot.json()["csrf_token"]})
    response=client.post("/api/auth/register",json={"email":"secure@example.com","password":PASSWORD})
    assert response.status_code == 201
    cookie=response.headers["set-cookie"].lower()
    assert all(value in cookie for value in ["httponly","secure","samesite=lax","path=/"])
    assert "domain=" not in cookie
    token=client.cookies.get(name)
    assert token != initial
    with app.state.database.session() as db:
        assert db.get(UserSession,token_hash(initial)) is None
        stored=db.get(UserSession,token_hash(token))
        assert stored is not None and len(stored.token_hash)==64
        assert token not in stored.token_hash
    app.state.database.close()


@pytest.mark.parametrize("headers",[{"X-CSRF-Token":""},{"Origin":"https://attacker.example"},{"Origin":""},{"Sec-Fetch-Site":"cross-site"}])
def test_csrf_blocks_state_changes(accounts,headers):
    app,a,*_=accounts
    response=a.post("/api/datasets",files={"file":("test.csv",b"id\n1\n")},headers=headers)
    assert response.status_code == 403
    assert a.get("/api/datasets").json()["total"] == 0


def test_login_itself_requires_csrf(secure_settings):
    app=create_app(secure_settings); client=TestClient(app)
    client.get("/api/auth/session")
    response=client.post("/api/auth/login",json={"email":"absent@example.com","password":PASSWORD},headers={"Origin":ORIGIN})
    assert response.status_code == 403
    app.state.database.close()


@pytest.mark.parametrize("method,path",[("GET","/api/datasets"),("GET","/api/datasets/00000000-0000-0000-0000-000000000000"),("POST","/api/datasets/00000000-0000-0000-0000-000000000000/query"),("POST","/api/datasets/00000000-0000-0000-0000-000000000000/ai/ask"),("GET","/api/dashboards"),("GET","/api/dashboards/00000000-0000-0000-0000-000000000000"),("GET","/api/auth/usage")])
def test_unauthenticated_api_access(secure_settings,method,path):
    app=create_app(secure_settings); client=TestClient(app)
    payload={"question":"count rows"} if path.endswith("/ask") else {}
    response=client.request(method,path,json=payload) if method == "POST" else client.get(path)
    assert response.status_code == 401
    app.state.database.close()


@pytest.mark.parametrize("method,suffix",[("GET",""),("GET","/preview"),("GET","/profile"),("POST","/query"),("POST","/ai/ask"),("GET","/export"),("POST","/export"),("DELETE","")])
def test_cross_user_access_is_not_found_and_does_not_contact_ai(accounts,method,suffix):
    app,a,b,a_id,b_id,provider=accounts
    dataset=upload(a)
    assert a.get("/api/datasets").json()["total"] == 1
    assert b.get("/api/datasets").json()["total"] == 0
    payload={"question":"count rows"} if suffix == "/ai/ask" else {}
    response=b.request(method,f"/api/datasets/{dataset}{suffix}",json=payload) if method == "POST" else b.request(method,f"/api/datasets/{dataset}{suffix}")
    assert response.status_code == 404
    provider.responses.parse.assert_not_called()
    assert a.get(f"/api/datasets/{dataset}/preview").json()["total_rows"] == 3
    assert a.get(f"/api/datasets/{dataset}/export").status_code == 200
    with app.state.database.session() as db:
        assert db.get(DatasetRecord,dataset).owner_id == a_id


def test_ownership_cannot_be_supplied_in_question(accounts):
    app,a,b,a_id,b_id,provider=accounts
    dataset=upload(a)
    response=b.post(f"/api/datasets/{dataset}/ai/ask",json={"question":"count rows","user_id":a_id})
    assert response.status_code == 422
    provider.responses.parse.assert_not_called()


def test_login_rate_limit_persists_between_instances(secure_settings):
    settings=replace(secure_settings,login_limit=2)
    first=create_app(settings); second=create_app(settings)
    a=TestClient(first); b=TestClient(second)
    for client in (a,b):
        client.headers.update({"Origin":ORIGIN,"X-CSRF-Token":client.get("/api/auth/session").json()["csrf_token"]})
    for client,expected in [(a,401),(b,401),(a,429)]:
        assert client.post("/api/auth/login",json={"email":"unknown@example.com","password":PASSWORD}).status_code == expected
    first.state.database.close(); second.state.database.close()


def test_ai_usage_is_user_specific_and_records_tokens(accounts):
    app,a,b,a_id,b_id,provider=accounts
    dataset=upload(a)
    plan=AnalyticalPlan(status="answer",message="",query=AnalyticsQuerySpec(group_by=["category"],aggregations=[{"function":"sum","column":"amount","alias":"total"}],limit=50).model_dump())
    provider.responses.parse.side_effect=[SimpleNamespace(output_parsed=plan,usage=SimpleNamespace(input_tokens=100,output_tokens=50)),SimpleNamespace(output_parsed=Explanation(explanation="Computed values are in the table."),usage=SimpleNamespace(input_tokens=80,output_tokens=30))]
    response=a.post(f"/api/datasets/{dataset}/ai/ask",json={"question":"Sum amount by category"})
    assert response.status_code == 200
    usage=a.get("/api/auth/usage").json()
    assert usage["provider_attempts"] == 2
    assert usage["input_tokens"] == 180 and usage["output_tokens"] == 80
    assert b.get("/api/auth/usage").json()["provider_attempts"] == 0


def test_ai_per_user_limits_are_independent(accounts,monkeypatch):
    app,a,b,a_id,b_id,provider=accounts
    # Consume the first user's entire minute allowance through the shared limiter.
    limiter=app.state.auth.limiter
    for _ in range(10):
        limiter.hit("ai_minute",a_id,10,60,"ai_rate_limited")
    a_dataset=upload(a); b_dataset=upload(b)
    assert a.post(f"/api/datasets/{a_dataset}/ai/ask",json={"question":"count"}).status_code == 429
    provider.responses.parse.return_value=SimpleNamespace(output_parsed=AnalyticalPlan(status="unsupported",message="Unsupported request.",query=None),usage=None)
    assert b.post(f"/api/datasets/{b_dataset}/ai/ask",json={"question":"forecast"}).status_code == 200


def test_database_limiter_is_atomic_and_redis_fails_closed(secure_settings):
    database=Database(secure_settings); limiter=RateLimiter(database)
    def attempt(_):
        try:
            limiter.hit("atomic","same-user",3,60)
            return True
        except ApiError as error:
            assert error.status_code == 429
            return False
    with ThreadPoolExecutor(max_workers=8) as pool:
        assert sum(pool.map(attempt,range(12))) == 3
    limiter.redis=MagicMock()
    limiter.redis.eval.side_effect=RedisConnectionError("not exposed")
    with pytest.raises(ApiError) as error:
        limiter.hit("redis","subject",3,60)
    assert error.value.status_code == 503
    database.close()


def test_populated_migration_downgrade_is_refused(accounts):
    from alembic import command
    app,*_=accounts
    config=migration_config()
    with app.state.database.engine.connect() as connection:
        config.attributes["connection"]=connection
        with pytest.raises(RuntimeError,match="Refusing a destructive downgrade"):
            command.downgrade(config,"base")


def test_empty_migration_roundtrip_and_model_parity(secure_settings):
    from alembic import command
    from alembic.autogenerate import compare_metadata
    from alembic.migration import MigrationContext
    from app.db_models import Base
    database=Database(secure_settings)
    with database.engine.begin() as connection:
        assert compare_metadata(MigrationContext.configure(connection),Base.metadata) == []
        config=migration_config(); config.attributes["connection"]=connection
        command.downgrade(config,"base")
        command.upgrade(config,"head")
    database.close()


def test_production_rejects_insecure_configuration(tmp_path):
    with pytest.raises(ValueError):
        Settings(data_dir=tmp_path,environment="production",cookie_secure=False)
    with pytest.raises(ValueError):
        Settings(data_dir=tmp_path,environment="production",cookie_secure=True,redis_url=None)


def test_malicious_upload_remains_isolated(accounts):
    app,a,b,a_id,b_id,_=accounts
    response=a.post("/api/datasets",files={"file":("../../private.exe",b"not data")})
    assert response.status_code == 415
    assert b.get("/api/datasets").json()["total"] == 0


def test_private_responses_are_not_cacheable(accounts):
    app,a,*_=accounts
    response=a.get("/api/datasets")
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-content-type-options"] == "nosniff"


def test_legacy_import_requires_explicit_owners_and_preserves_source(accounts,secure_settings,tmp_path):
    from datetime import datetime,UTC
    from app.storage import DatasetRepository as LegacyRepository
    from app.models import DatasetMetadata,ColumnMetadata
    from app.legacy_migration import import_legacy,digest
    app,a,b,a_id,b_id,_=accounts
    legacy=LegacyRepository(tmp_path/"legacy")
    dataset_id=str(uuid4())
    metadata=DatasetMetadata(id=dataset_id,name="legacy",original_filename="legacy.csv",file_type="csv",file_size_bytes=5,row_count=1,column_count=1,missing_cell_count=0,created_at=datetime.now(UTC),columns=[ColumnMetadata(name="id",type="integer",pandas_dtype="int64",missing_count=0,missing_percentage=0)])
    legacy.file_path(dataset_id,"csv").write_bytes(b"id\n1\n")
    legacy.save(metadata,"csv")
    before=digest(legacy.database_path),digest(legacy.file_path(dataset_id,"csv"))
    database=app.state.database
    dry=import_legacy(database,secure_settings.data_dir,legacy.database_path)
    assert dry["applied"] is False
    assert a.get("/api/datasets").json()["total"] == 0
    import_legacy(database,secure_settings.data_dir,legacy.database_path,apply=True)
    assert a.get("/api/datasets").json()["total"] == b.get("/api/datasets").json()["total"] == 0
    with pytest.raises(ValueError):
        import_legacy(database,secure_settings.data_dir,legacy.database_path,{dataset_id:"alice@example.com"},apply=True)
    import_legacy(database,secure_settings.data_dir,legacy.database_path,{dataset_id:"alice@example.com"},"explicit-test-administrator",apply=True)
    assert a.get(f"/api/datasets/{dataset_id}/preview").status_code == 200
    assert b.get(f"/api/datasets/{dataset_id}/preview").status_code == 404
    import_legacy(database,secure_settings.data_dir,legacy.database_path,{dataset_id:"alice@example.com"},"explicit-test-administrator",apply=True)
    with database.session() as db:
        assert len(db.scalars(select(OwnershipDecision)).all()) == 1
    assert before == (digest(legacy.database_path),digest(legacy.file_path(dataset_id,"csv")))


def test_unauthenticated_upload_is_rejected_before_multipart_parsing(secure_settings):
    app=create_app(secure_settings); client=TestClient(app)
    response=client.post("/api/datasets",content=b"malformed multipart",headers={"Content-Type":"multipart/form-data; boundary=invalid"})
    assert response.status_code == 401
    app.state.database.close()


def test_chunked_request_body_limit_is_structured(accounts):
    app,a,*_=accounts
    response=a.post("/api/auth/login",content=iter([b" "*65536,b"x"]),headers={"Content-Type":"application/json"})
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "request_too_large"


def test_cancelled_ai_request_does_not_call_provider(accounts):
    from threading import Event
    from app.ai import AIService
    from app.service import DatasetService
    app,a,b,a_id,b_id,provider=accounts
    dataset=upload(a)
    service=DatasetService(app.state.auth.settings,app.state.database)
    service.limiter=app.state.auth.limiter
    assistant=AIService(service)
    cancelled=Event(); cancelled.set()
    with pytest.raises(ApiError) as error:
        assistant.ask(dataset,"Count rows",a_id,cancelled)
    assert error.value.status_code == 499
    provider.responses.parse.assert_not_called()


@pytest.mark.parametrize("origin",["*","https://*.example.com","https://example.com/path"])
def test_unsafe_cors_configuration_is_rejected(tmp_path,origin):
    with pytest.raises(ValueError):
        Settings(data_dir=tmp_path,cors_origins=(origin,))


def test_frontend_owner_form_field_cannot_change_ownership(accounts):
    app,a,b,a_id,b_id,_=accounts
    response=a.post("/api/datasets",data={"owner_id":b_id},files={"file":("owned.csv",b"id\n1\n")})
    assert response.status_code == 201
    dataset=response.json()["id"]
    with app.state.database.session() as db:
        assert db.get(DatasetRecord,dataset).owner_id == a_id
    assert b.get(f"/api/datasets/{dataset}").status_code == 404


def test_storage_collision_does_not_remove_an_existing_dataset(accounts,monkeypatch):
    from uuid import UUID
    app,a,b,a_id,b_id,_=accounts
    dataset=upload(a)
    monkeypatch.setattr("app.service.uuid4",lambda:UUID(dataset))
    response=b.post("/api/datasets",files={"file":("collision.csv",b"id\n99\n")})
    assert response.status_code == 409
    assert a.get(f"/api/datasets/{dataset}/preview").json()["total_rows"] == 3


def test_readiness_checks_redis_and_fails_closed(accounts):
    app,a,*_=accounts
    assert a.get("/api/ready").status_code == 200
    app.state.auth.limiter.redis=MagicMock()
    app.state.auth.limiter.redis.ping.side_effect=RedisConnectionError("private connection details")
    response=a.get("/api/ready")
    assert response.status_code == 503
    assert "private connection details" not in response.text


def test_non_ascii_csrf_is_rejected_without_server_error(accounts):
    app,a,*_=accounts
    response=a.post("/api/datasets",files={"file":("test.csv",b"id\n1\n")},headers=[(b"X-CSRF-Token",b"\xff")])
    assert response.status_code == 403
    assert a.get("/api/datasets").json()["total"] == 0


def test_password_hashing_concurrency_is_bounded(accounts):
    from app.auth import HASH_SLOTS
    app,a,b,a_id,b_id,_=accounts
    for _ in range(4):
        assert HASH_SLOTS.acquire(blocking=False)
    try:
        response=a.post("/api/auth/register",json={"email":"busy@example.com","password":PASSWORD})
        assert response.status_code == 429
        assert response.json()["error"]["code"] == "authentication_busy"
        response=a.post("/api/auth/login",json={"email":"alice@example.com","password":PASSWORD})
        assert response.status_code == 429
        assert a.get("/api/auth/me").json()["id"] == a_id
    finally:
        for _ in range(4):
            HASH_SLOTS.release()


def test_session_and_revocation_are_shared_between_instances(accounts,secure_settings):
    app,a,b,a_id,b_id,_=accounts
    second=create_app(secure_settings)
    mirror=TestClient(second)
    mirror.cookies.update(a.cookies)
    mirror.headers.update(a.headers)
    try:
        assert mirror.get("/api/auth/me").json()["id"] == a_id
        assert mirror.post("/api/auth/logout").status_code == 204
        assert a.get("/api/auth/me").status_code == 401
        assert b.get("/api/auth/me").json()["id"] == b_id
    finally:
        mirror.close()
        second.state.database.close()
