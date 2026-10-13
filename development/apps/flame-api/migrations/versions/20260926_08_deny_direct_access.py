"""Deny direct client-role access to FLAME-owned data.

The API uses a private database connection. Supabase anon/authenticated and
service_role have no schema or table grants; RLS is an additional deny layer.
"""
from alembic import op

revision = "20260926_08"
down_revision = "20260926_07"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("REVOKE ALL ON SCHEMA flame FROM PUBLIC")
    op.execute("REVOKE ALL ON ALL TABLES IN SCHEMA flame FROM PUBLIC")
    op.execute("REVOKE ALL ON ALL SEQUENCES IN SCHEMA flame FROM PUBLIC")
    op.execute("""
    DO $$
    DECLARE role_name text;
    BEGIN
      FOREACH role_name IN ARRAY ARRAY['anon', 'authenticated', 'service_role'] LOOP
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = role_name) THEN
          EXECUTE format('REVOKE ALL ON SCHEMA flame FROM %I', role_name);
          EXECUTE format('REVOKE ALL ON ALL TABLES IN SCHEMA flame FROM %I', role_name);
          EXECUTE format('REVOKE ALL ON ALL SEQUENCES IN SCHEMA flame FROM %I', role_name);
          EXECUTE format('ALTER DEFAULT PRIVILEGES IN SCHEMA flame REVOKE ALL ON TABLES FROM %I', role_name);
          EXECUTE format('ALTER DEFAULT PRIVILEGES IN SCHEMA flame REVOKE ALL ON SEQUENCES FROM %I', role_name);
        END IF;
      END LOOP;
    END $$;
    """)
    op.execute("ALTER TABLE flame.student_profiles ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE flame.admin_roles ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE flame.browser_sessions ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER DEFAULT PRIVILEGES IN SCHEMA flame REVOKE ALL ON TABLES FROM PUBLIC")
    op.execute("ALTER DEFAULT PRIVILEGES IN SCHEMA flame REVOKE ALL ON SEQUENCES FROM PUBLIC")


def downgrade():
    # Never restore direct grants or disable RLS during a downgrade.
    pass
