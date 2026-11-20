from pathlib import Path
from threading import Lock

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.orm import sessionmaker

MIGRATION_HEAD = "0002_dashboard_studio"
_MIGRATION_LOCK = Lock()


def migration_config(url: str | None = None) -> Config:
    root = Path(__file__).resolve().parents[1]
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "migrations"))
    if url:
        config.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
    return config


class Database:
    def __init__(self, settings):
        settings.data_dir.mkdir(parents=True, exist_ok=True)
        self.url = settings.database_url or f"sqlite:///{(settings.data_dir / 'saas.sqlite3').as_posix()}"
        if settings.environment == "production" and not self.url.startswith("postgresql+psycopg://"):
            raise RuntimeError("Production requires a PostgreSQL database URL.")
        sqlite = self.url.startswith("sqlite:")
        self.engine = create_engine(self.url, pool_pre_ping=True,
                                    connect_args={"check_same_thread": False, "timeout": 15} if sqlite else {"connect_timeout": 5})
        if sqlite:
            @event.listens_for(self.engine, "connect")
            def foreign_keys(connection, _):
                connection.execute("PRAGMA foreign_keys=ON")
        if settings.auto_migrate and settings.environment != "production":
            with _MIGRATION_LOCK:
                with self.engine.begin() as connection:
                    config = migration_config()
                    config.attributes["connection"] = connection
                    command.upgrade(config, "head")
        with self.engine.connect() as connection:
            if "alembic_version" not in inspect(connection).get_table_names() or connection.execute(text("SELECT version_num FROM alembic_version")).scalar() != MIGRATION_HEAD:
                raise RuntimeError("Database migrations are required. Run alembic upgrade head.")
        self.session = sessionmaker(self.engine, expire_on_commit=False)

    def close(self):
        self.engine.dispose()
