"""Serialize imported pending profiles with first verified sign-in for the same email."""
from hashlib import sha256
from sqlalchemy import text


def lock_profile_email(db, email):
    normalized = str(email).strip().lower()
    key = int.from_bytes(sha256(("flame-profile-email:" + normalized).encode()).digest()[:8], "big") % (2**63 - 1)
    db.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": key})
