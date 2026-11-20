from alembic import context
from sqlalchemy import create_engine, pool
from app.db_models import Base
from app.config import Settings
config = context.config


def run(connection):
    context.configure(connection=connection, target_metadata=Base.metadata, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    settings = Settings.from_env()
    url = config.get_main_option(
        "sqlalchemy.url") or settings.database_url or f"sqlite:///{(settings.data_dir / 'saas.sqlite3').as_posix()}"
    context.configure(url=url, target_metadata=Base.metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()
elif config.attributes.get("connection") is not None:
    run(config.attributes["connection"])
else:
    settings = Settings.from_env()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    url = config.get_main_option(
        "sqlalchemy.url") or settings.database_url or f"sqlite:///{(settings.data_dir / 'saas.sqlite3').as_posix()}"
    engine = create_engine(url, poolclass=pool.NullPool)
    with engine.connect() as connection:
        run(connection)
    engine.dispose()
