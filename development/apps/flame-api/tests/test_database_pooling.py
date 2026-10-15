from unittest.mock import patch

from sqlalchemy.pool import NullPool, QueuePool

from app.core.config import Settings
from app.core.database import Database


def config(port=6543, environment="test", host="aws-0-ap-south-1.pooler.supabase.com"):
    settings = Settings(_env_file=None, environment="test",
                        database_url=f"postgresql+psycopg://test:test@{host}:{port}/postgres")
    return settings.model_copy(update={"environment": environment})


def test_external_pool_releases_connections_and_disables_prepared_statements():
    with patch("app.core.database.create_engine") as create:
        Database(config())
    options = create.call_args.kwargs
    assert options["poolclass"] is NullPool
    assert options["connect_args"]["prepare_threshold"] is None
    assert "pool_size" not in options and "max_overflow" not in options


def test_production_session_pooler_does_not_hold_idle_slots():
    db = Database(config(port=5432, environment="production"))
    try:
        assert isinstance(db.engine.pool, NullPool)
    finally:
        db.close()


def test_persistent_development_and_direct_connections_keep_bounded_pool():
    for settings in [config(port=5432), config(port=5432, host="localhost", environment="production")]:
        db = Database(settings)
        try:
            assert isinstance(db.engine.pool, QueuePool)
            assert db.engine.pool.size() == 5
        finally:
            db.close()
