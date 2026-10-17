"""Explicit-target, rollback-only PostgreSQL acceptance for user access/profile.

No Supabase Auth or AI provider calls; imported tests use their synthetic gateway.
"""
import os
from contextlib import contextmanager
from types import SimpleNamespace
import pytest
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session
from app.core.config import Settings
from app.core.database import Database
from test_guest_profile_access import (
    api,
    test_calendar_reset_is_midnight_india_time_and_fixed_limits,
    test_guest_10_questions_same_key_replay_and_calendar_day_count,
    test_guest_capability_is_private_expiring_and_cannot_use_study_or_member_routes,
    test_signed_in_limit_25_and_duplicate_does_not_use_an_extra_question,
    test_profile_update_is_owned_optional_clearable_and_rejects_privilege_changes,
    test_optional_auth_phone_is_validated_and_registration_preserves_it,
    test_optional_login_phone_is_saved_only_to_the_authenticated_profile,
    test_migration_source_renders_profile_columns_guest_fk_and_rls,
)

pytestmark = pytest.mark.db_integration


@pytest.fixture
def database():
    settings = Settings()
    expected = os.environ.get("FLAME_ACCESS_DB_HOST")
    if os.environ.get("FLAME_ACCESS_DB_VERIFY") != "1" or not expected or not settings.database_url:
        pytest.skip("Set FLAME_ACCESS_DB_VERIFY=1 and explicitly confirm FLAME_ACCESS_DB_HOST")
    if settings.environment == "production" or make_url(settings.database_url.get_secret_value()).host != expected:
        pytest.fail("Configured database is not the explicitly confirmed development target")
    owner = Database(settings)
    with owner.engine.connect() as connection:
        outer = connection.begin()
        @contextmanager
        def session():
            with Session(bind=connection, expire_on_commit=False, join_transaction_mode="create_savepoint") as db:
                yield db
        try:
            yield SimpleNamespace(session=session, close=lambda: None)
        finally:
            outer.rollback()
    owner.close()


def test_guest_storage_postgresql_schema_head_and_rls(database):
    with database.session() as db:
        assert db.bind.dialect.name == "postgresql"
        assert db.scalar(text("SELECT version_num FROM flame.alembic_version")) == "20261017_32"
        assert db.scalar(text("SELECT relrowsecurity FROM pg_class JOIN pg_namespace n ON n.oid=relnamespace WHERE n.nspname='flame' AND relname='guest_access'")) is True
        for role in ("anon", "authenticated"):
            assert db.scalar(text("SELECT has_table_privilege(:role, 'flame.guest_access', 'SELECT')"),{"role":role}) is False
