"""Remove expired previews and only their unused staging media; schedule operationally."""
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sqlalchemy import select
from app.main import create_app  # register all models
from app.core.config import Settings
from app.core.database import Database
from app.modules.functional.bulk_transfer.models import BulkImport
from app.modules.functional.bulk_transfer.router import cleanup


def main():
    config=Settings(); database=Database(config)
    try:
        with database.session() as db, db.begin():
            rows=db.scalars(select(BulkImport).where(BulkImport.created_at < datetime.now(timezone.utc)-timedelta(hours=24)).with_for_update()).all()
            removed = 0
            for row in rows:
                # Pending Sheets receipts must survive until identifier write-back succeeds.
                if row.status == 'completed' and (row.result or {}).get('writeback') == 'pending': continue
                cleanup(db,config,row.payload.get('uploads',{}).values(),row.owner_subject)
                db.delete(row)
                removed += 1
            print(f'Removed {removed} expired bulk preview/receipt records; catalogue entries and pending sheet write-backs retained.')
    finally: database.close()


if __name__=='__main__': main()
