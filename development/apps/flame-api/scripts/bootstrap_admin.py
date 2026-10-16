"""One-time controlled admin bootstrap; never exposed through HTTP."""
from os import environ
from uuid import UUID
from sqlalchemy import select
from app.core.config import Settings
from app.core.database import Database
from app.modules.functional.identity.models import AdminRole, StudentProfile


def main():
    subject = str(UUID(environ["FLAME_BOOTSTRAP_ADMIN_SUBJECT"]))
    db = Database(Settings())
    try:
        with db.session() as session, session.begin():
            if session.scalar(select(AdminRole.auth_subject).limit(1)):
                raise RuntimeError("An admin already exists; bootstrap is closed")
            profile = session.scalar(select(StudentProfile).where(StudentProfile.auth_subject == subject))
            if profile is None or profile.status != "active":
                raise RuntimeError("Verified active member profile is required before bootstrap")
            session.add(AdminRole(auth_subject=subject, granted_by_subject=None))
        print("Initial admin grant created")
    finally:
        db.close()


if __name__ == "__main__":
    main()
