"""Alembic environment for FLAME-owned objects only."""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import text

from app.core.config import Settings
from app.core.database import Base, Database
from app.modules.functional.model_registry import register_models

register_models()

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

SCHEMA = "flame"
target_metadata = Base.metadata


def include_name(name, type_, parent_names):
    if type_ == "schema":
        return name == SCHEMA
    if type_ == "table":
        return parent_names.get("schema_name") == SCHEMA
    return True


def run_migrations_offline() -> None:
    raise RuntimeError("Offline migrations are disabled; use a configured database")


def run_migrations_online() -> None:
    settings = Settings()
    if settings.database_url is None:
        raise RuntimeError("FLAME_DATABASE_URL is required for migrations")

    database = Database(settings)
    assert database.engine is not None
    try:
        with database.engine.begin() as connection:
            # The version table is in flame. Create its namespace first on a
            # clean database; never use or mutate provider-owned auth schemas.
            connection.execute(text("CREATE SCHEMA IF NOT EXISTS flame"))
            owns_schema = connection.execute(text("""
                SELECT pg_get_userbyid(nspowner) = current_user
                FROM pg_namespace WHERE nspname = 'flame'
            """)).scalar_one()
            if not owns_schema:
                raise RuntimeError("Migration role must own the flame schema")
            context.configure(
                connection=connection,
                target_metadata=target_metadata,
                version_table_schema=SCHEMA,
                include_schemas=True,
                include_name=include_name,
                transactional_ddl=True,
            )
            with context.begin_transaction():
                context.run_migrations()
    finally:
        database.close()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

