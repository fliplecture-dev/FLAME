"""Create and delete one disposable B5 Auth identity in the development project."""
import argparse
from uuid import UUID, uuid4
import httpx
from fastapi.testclient import TestClient
from app.core.config import Settings
from app.core.database import Database
from app.modules.functional.data_lifecycle.service import delete_provider_user
from app.main import create_app
from app.modules.functional.identity.dependencies import require_member
from app.modules.functional.identity.models import StudentProfile


def admin_headers(settings: Settings) -> dict[str, str]:
    if settings.supabase_secret_key:
        return {"apikey": settings.supabase_secret_key.get_secret_value()}
    legacy = settings.supabase_service_role_key.get_secret_value()
    return {"apikey": legacy, "Authorization": "Bearer " + legacy}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true", help="create and delete one disposable development user")
    args = parser.parse_args()
    if not args.execute:
        parser.error("Pass --execute to run the live disposable-account check")
    settings = Settings()
    if settings.environment != "development" or not settings.supabase_url or not settings.database_url:
        parser.error("A configured development Supabase project and database are required")
    if not (settings.supabase_secret_key or settings.supabase_service_role_key):
        parser.error("A server-only Supabase admin key is required")
    email = "flame-b5-" + uuid4().hex + "@example.invalid"
    try:
        response = httpx.post(settings.supabase_url + "/auth/v1/admin/users",
                              headers=admin_headers(settings), json={"email": email}, timeout=10)
    except httpx.HTTPError as error:
        parser.error("Supabase user creation failed: " + type(error).__name__)
    if response.status_code not in (200, 201):
        parser.error(f"Supabase user creation failed with HTTP {response.status_code}")
    user = response.json()
    user_id = UUID(user.get("id") or user.get("user", {}).get("id"))
    print("Disposable Supabase user created:", user_id)
    try:
        application = create_app(settings)
        application.dependency_overrides[require_member] = lambda: {"id": str(user_id), "role": "member"}
        with TestClient(application) as client:
            with application.state.database.session() as db, db.begin():
                db.add(StudentProfile(id=user_id, auth_subject=str(user_id), email=email))
            result = client.request("DELETE", "/api/v1/me", json={"confirm": True})
            if result.status_code not in (200, 202):
                raise RuntimeError(f"FLAME deletion returned HTTP {result.status_code}; disposable user ID: {user_id}")
            payload = result.json()
            print("FLAME deletion status:", payload["status"])
            print("Deletion receipt:", payload["deletion_request_id"])
            with application.state.database.session() as db:
                profile = db.get(StudentProfile, user_id)
                assert profile and profile.status in ("deleted", "deleting") and profile.email is None
            if result.status_code == 202:
                raise RuntimeError("Supabase deletion is pending; run scripts/retry_deletions.py after fixing provider access")
        verification = httpx.get(settings.supabase_url + "/auth/v1/admin/users/" + str(user_id),
                                 headers=admin_headers(settings), timeout=10)
        if verification.status_code != 404:
            raise RuntimeError(f"Supabase user lookup returned HTTP {verification.status_code}, expected 404")
        print("Verified: local profile inactive and Supabase Auth identity absent")
    except Exception:
        database = Database(settings)
        try:
            with database.session() as db, db.begin():
                profile = db.get(StudentProfile, user_id)
                cleanup = profile is None or profile.status == "active"
                if profile is not None and profile.status == "active":
                    db.delete(profile)
            if cleanup:
                delete_provider_user(settings, str(user_id))
        finally:
            database.close()
        raise


if __name__ == "__main__":
    main()
