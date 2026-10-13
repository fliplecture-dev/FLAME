"""Retry confirmed Supabase Auth deletions left pending by a timeout or outage."""
import argparse
from sqlalchemy import select
from app.core.config import Settings
from app.core.database import Database
from app.modules.data_lifecycle.models import DeletionRequest
from app.modules.data_lifecycle.service import complete_provider_deletion

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()
    if args.limit < 1 or args.limit > 100:
        parser.error("--limit must be between 1 and 100")
    settings = Settings()
    if not settings.supabase_url or not (settings.supabase_secret_key or settings.supabase_service_role_key):
        parser.error("Supabase deletion credential is required")
    database = Database(settings)
    try:
        with database.session() as db:
            ids = db.scalars(select(DeletionRequest.id).where(
                DeletionRequest.status == "pending_provider").order_by(
                DeletionRequest.requested_at, DeletionRequest.id).limit(args.limit)).all()
        completed = sum(complete_provider_deletion(database, settings, request_id) for request_id in ids)
        print(f"Pending receipts checked: {len(ids)}; completed: {completed}; still pending: {len(ids) - completed}")
    finally:
        database.close()

if __name__ == "__main__":
    main()
