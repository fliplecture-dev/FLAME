"""Purge completed FLAME deletion receipts and auth-subject tombstones after the configured window."""
import argparse
from app.core.config import Settings
from app.core.database import Database
from app.modules.functional.data_lifecycle.service import purge_completed_tombstones


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=100)
    args = parser.parse_args()
    if not 1 <= args.limit <= 1000:
        parser.error("--limit must be between 1 and 1000")
    settings = Settings()
    database = Database(settings)
    try:
        removed = purge_completed_tombstones(
            database, limit=args.limit, retention_days=settings.deletion_receipt_retention_days
        )
        print(f"Completed deletion tombstones purged: {removed}")
    finally:
        database.close()


if __name__ == "__main__":
    main()
