"""Read-only B3 deployment readiness audit. Prints no credentials or member data."""
from cryptography.fernet import Fernet
import httpx
from sqlalchemy import text

from app.core.config import Settings
from app.core.database import Database


def main() -> int:
    settings = Settings()
    checks: list[tuple[str, bool, str]] = []
    checks.append(("Supabase project URL", bool(settings.supabase_url), "FLAME_SUPABASE_URL"))
    checks.append(("Supabase publishable key", bool(settings.supabase_anon_key), "FLAME_SUPABASE_ANON_KEY"))
    checks.append(("Web origin", bool(settings.web_origin), "FLAME_WEB_ORIGIN"))
    checks.append(("BFF shared key", bool(settings.bff_shared_key and len(settings.bff_shared_key.get_secret_value()) >= 32), "FLAME_BFF_SHARED_KEY (at least 32 characters)"))
    cipher_valid = False
    if settings.session_encryption_key:
        try:
            Fernet(settings.session_encryption_key.get_secret_value().encode())
            cipher_valid = True
        except ValueError:
            pass
    checks.append(("Session encryption key", cipher_valid, "FLAME_SESSION_ENCRYPTION_KEY (Fernet key)"))
    checks.append(("Database URL", bool(settings.database_url), "FLAME_DATABASE_URL"))
    if settings.database_url:
        db = Database(settings)
        try:
            with db.engine.connect() as connection:
                head = connection.scalar(text("SELECT version_num FROM flame.alembic_version"))
                checks.append(("B3 database migrations", head == "20260926_08", "alembic upgrade head"))
                rows = connection.execute(text("""
                    SELECT c.relname, c.relrowsecurity
                    FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
                    WHERE n.nspname = 'flame'
                      AND c.relname IN ('student_profiles', 'admin_roles', 'browser_sessions')
                """)).all()
                checks.append(("Identity RLS", len(rows) == 3 and all(row.relrowsecurity for row in rows), "enable RLS on all three identity tables"))
                direct = connection.scalar(text("""
                    SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
                    WHERE n.nspname='flame' AND c.relkind='r'
                      AND (has_table_privilege('anon', c.oid, 'SELECT')
                        OR has_table_privilege('authenticated', c.oid, 'SELECT')
                        OR has_table_privilege('service_role', c.oid, 'SELECT'))
                """))
                checks.append(("Direct client table access denied", direct == 0, "revoke FLAME table access from Supabase client roles"))
        except Exception:
            checks.append(("Database audit", False, "database reachable and B3 migrations applied"))
        finally:
            db.close()
    if settings.supabase_url and settings.supabase_anon_key:
        try:
            response = httpx.get(settings.supabase_url + "/auth/v1/settings",
                                 headers={"apikey": settings.supabase_anon_key.get_secret_value()}, timeout=10)
            response.raise_for_status()
            provider = response.json()
            checks.append(("Email confirmation enabled", provider.get("mailer_autoconfirm") is False, "disable mailer_autoconfirm in Supabase Auth"))
            checks.append(("Signup enabled", provider.get("disable_signup") is False, "enable email signup in Supabase Auth"))
            jwks = httpx.get(settings.supabase_url + "/auth/v1/.well-known/jwks.json", timeout=10)
            jwks.raise_for_status()
            asymmetric = bool(jwks.json().get("keys"))
            checks.append(("JWT verification key", asymmetric or bool(settings.supabase_jwt_secret), "configure an asymmetric signing key or FLAME_SUPABASE_JWT_SECRET for legacy HS256"))
        except (httpx.HTTPError, ValueError):
            checks.append(("Provider settings audit", False, "Supabase Auth settings endpoint reachable"))
    for label, passed, remedy in checks:
        print(f'{"PASS" if passed else "PENDING"} {label}' + (f" - {remedy}" if not passed else ""))
    return 0 if all(passed for _, passed, _ in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
