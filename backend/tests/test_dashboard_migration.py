"""Non-destructive 0001 -> 0002 migration checks on isolated databases only."""
from __future__ import annotations

import json
import os
from pathlib import Path
from uuid import uuid4

from alembic import command
import pytest
from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.engine import make_url

from app.database import migration_config


USER_ID = "10000000-0000-0000-0000-000000000001"
DATASET_ID = "20000000-0000-0000-0000-000000000002"
DASHBOARD_ID = "30000000-0000-0000-0000-000000000003"
WIDGET_ID = "40000000-0000-0000-0000-000000000004"


def metadata_json() -> str:
    return json.dumps({
        "id": DATASET_ID,
        "name": "Synthetic orders",
        "original_filename": "synthetic-orders.csv",
        "file_type": "csv",
        "file_size_bytes": 42,
        "row_count": 2,
        "column_count": 2,
        "missing_cell_count": 0,
        "created_at": "2026-11-13T20:00:00Z",
        "columns": [
            {"name": "category", "type": "text", "pandas_dtype": "object", "missing_count": 0, "missing_percentage": 0},
            {"name": "amount", "type": "number", "pandas_dtype": "float64", "missing_count": 0, "missing_percentage": 0},
        ],
        "source": "upload",
    })


def engine_for(url: str):
    engine = create_engine(url)
    if url.startswith("sqlite:"):
        @event.listens_for(engine, "connect")
        def enable_foreign_keys(connection, _):
            connection.execute("PRAGMA foreign_keys=ON")
    return engine


def exercise_migration(url: str):
    config = migration_config(url)
    command.upgrade(config, "0001_multi_user")
    engine = engine_for(url)
    try:
        with engine.begin() as connection:
            connection.execute(text(
                "INSERT INTO users (id,email,password_hash,created_at,active) "
                "VALUES (:id,:email,:password_hash,:created_at,:active)"
            ), {"id": USER_ID, "email": "migration@example.com", "password_hash": "synthetic-hash", "created_at": 1, "active": True})
            connection.execute(text(
                "INSERT INTO dataset_metadata (id,owner_id,metadata_json,stored_extension,created_at) "
                "VALUES (:id,:owner_id,:metadata_json,:extension,:created_at)"
            ), {"id": DATASET_ID, "owner_id": USER_ID, "metadata_json": metadata_json(), "extension": "csv", "created_at": "2026-11-13T20:00:00+00:00"})
        with engine.connect() as connection:
            before = {
                "users": connection.execute(text("SELECT COUNT(*) FROM users")).scalar_one(),
                "datasets": connection.execute(text("SELECT COUNT(*) FROM dataset_metadata")).scalar_one(),
                "email": connection.execute(text("SELECT email FROM users WHERE id=:id"), {"id": USER_ID}).scalar_one(),
                "metadata": connection.execute(text("SELECT metadata_json FROM dataset_metadata WHERE id=:id"), {"id": DATASET_ID}).scalar_one(),
            }

        command.upgrade(config, "0002_dashboard_studio")
        schema = inspect(engine)
        assert {"dashboards", "dashboard_widgets"}.issubset(schema.get_table_names())
        assert {index["name"] for index in schema.get_indexes("dashboards")} >= {
            "ix_dashboards_owner_id", "ix_dashboards_owner_updated"
        }
        assert {index["name"] for index in schema.get_indexes("dashboard_widgets")} >= {
            "ix_dashboard_widgets_dashboard_id", "ix_dashboard_widgets_dataset_id",
            "ix_dashboard_widgets_dashboard_position",
        }
        foreign_keys = {fk["referred_table"]: (fk.get("options") or {}).get("ondelete") for fk in schema.get_foreign_keys("dashboard_widgets")}
        assert str(foreign_keys["dashboards"]).upper() == "CASCADE"
        assert str(foreign_keys["dataset_metadata"]).upper() == "SET NULL"
        assert {constraint["name"] for constraint in schema.get_check_constraints("dashboard_widgets")} >= {
            "ck_dashboard_widgets_query_version_positive", "ck_dashboard_widgets_position",
            "ck_dashboard_widgets_width", "ck_dashboard_widgets_height",
        }

        with engine.connect() as connection:
            after = {
                "users": connection.execute(text("SELECT COUNT(*) FROM users")).scalar_one(),
                "datasets": connection.execute(text("SELECT COUNT(*) FROM dataset_metadata")).scalar_one(),
                "email": connection.execute(text("SELECT email FROM users WHERE id=:id"), {"id": USER_ID}).scalar_one(),
                "metadata": connection.execute(text("SELECT metadata_json FROM dataset_metadata WHERE id=:id"), {"id": DATASET_ID}).scalar_one(),
            }
        assert after == before

        with engine.begin() as connection:
            connection.execute(text(
                "INSERT INTO dashboards (id,owner_id,name,description,revision,created_at,updated_at) "
                "VALUES (:id,:owner,'Migration dashboard',NULL,1,1,1)"
            ), {"id": DASHBOARD_ID, "owner": USER_ID})
            connection.execute(text(
                "INSERT INTO dashboard_widgets "
                "(id,dashboard_id,dataset_id,dataset_id_snapshot,dataset_name_snapshot,title,query_version,query_spec_json,visualization_json,position,width_columns,height_rows,created_at,updated_at) "
                "VALUES (:id,:dashboard,:dataset,:dataset,'Synthetic orders','Orders',1,:query,:visualization,0,6,4,1,1)"
            ), {
                "id": WIDGET_ID, "dashboard": DASHBOARD_ID, "dataset": DATASET_ID,
                "query": json.dumps({"columns": ["category"], "filters": [], "sorts": [], "group_by": [], "aggregations": [], "offset": 0, "limit": 25}),
                "visualization": json.dumps({"type": "table", "series": [], "value_column": None, "show_legend": True, "show_data_table": True}),
            })
            connection.execute(text("DELETE FROM dataset_metadata WHERE id=:id"), {"id": DATASET_ID})
            widget = connection.execute(text(
                "SELECT dataset_id,dataset_id_snapshot,dataset_name_snapshot FROM dashboard_widgets WHERE id=:id"
            ), {"id": WIDGET_ID}).mappings().one()
            assert widget["dataset_id"] is None
            assert widget["dataset_id_snapshot"] == DATASET_ID
            assert widget["dataset_name_snapshot"] == "Synthetic orders"
            connection.execute(text("DELETE FROM dashboards WHERE id=:id"), {"id": DASHBOARD_ID})
            assert connection.execute(text("SELECT COUNT(*) FROM dashboard_widgets")).scalar_one() == 0
    finally:
        engine.dispose()


def test_sqlite_migration_0001_to_0002_preserves_existing_rows(tmp_path: Path):
    exercise_migration(f"sqlite:///{(tmp_path / 'migration.sqlite3').as_posix()}")


def test_postgresql_migration_0001_to_0002_preserves_existing_rows():
    admin_url = os.getenv("SMARTANALYTICS_TEST_ADMIN_URL")
    if not admin_url:
        pytest.skip("Isolated PostgreSQL administrator not supplied")
    admin = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    name = "sa_dashboard_migration_" + uuid4().hex
    with admin.connect() as connection:
        connection.exec_driver_sql(f'CREATE DATABASE "{name}"')
    url = make_url(admin_url).set(database=name).render_as_string(hide_password=False)
    try:
        exercise_migration(url)
    finally:
        with admin.connect() as connection:
            connection.exec_driver_sql(f'DROP DATABASE "{name}" WITH (FORCE)')
        admin.dispose()


def test_dashboard_downgrade_refuses_saved_data(tmp_path: Path):
    url = f"sqlite:///{(tmp_path / 'downgrade.sqlite3').as_posix()}"
    config = migration_config(url)
    command.upgrade(config, "0002_dashboard_studio")
    engine = engine_for(url)
    try:
        with engine.begin() as connection:
            connection.execute(text(
                "INSERT INTO users (id,email,password_hash,created_at,active) "
                "VALUES (:id,'downgrade@example.com','synthetic',1,1)"
            ), {"id": USER_ID})
            connection.execute(text(
                "INSERT INTO dashboards (id,owner_id,name,description,revision,created_at,updated_at) "
                "VALUES (:id,:owner,'Keep me',NULL,1,1,1)"
            ), {"id": DASHBOARD_ID, "owner": USER_ID})
        with pytest.raises(RuntimeError, match="Refusing a destructive Dashboard Studio downgrade"):
            command.downgrade(config, "0001_multi_user")
        with engine.connect() as connection:
            assert connection.execute(text("SELECT name FROM dashboards WHERE id=:id"), {"id": DASHBOARD_ID}).scalar_one() == "Keep me"
    finally:
        engine.dispose()
