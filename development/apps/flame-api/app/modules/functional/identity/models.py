"""Individual identity mappings and controlled admin grants (B2.4)."""
from datetime import datetime
from uuid import UUID, uuid4
from sqlalchemy import DateTime, String, LargeBinary, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class StudentProfile(Base):
    __tablename__ = "student_profiles"
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    auth_subject: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(255))
    email: Mapped[str | None] = mapped_column(String(320))
    phone_number: Mapped[str | None] = mapped_column(String(32))
    contact_number: Mapped[str | None] = mapped_column(String(32))
    address: Mapped[str | None] = mapped_column(String(1000))
    city: Mapped[str | None] = mapped_column(String(100))
    state: Mapped[str | None] = mapped_column(String(100))
    country: Mapped[str | None] = mapped_column(String(100))
    pincode: Mapped[str | None] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(24), nullable=False, server_default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class AdminRole(Base):
    __tablename__ = "admin_roles"
    auth_subject: Mapped[str] = mapped_column(String(255), primary_key=True)
    granted_by_subject: Mapped[str | None] = mapped_column(String(255))
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

class BrowserSession(Base):
    __tablename__ = "browser_sessions"
    id_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    auth_subject: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    access_token: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    refresh_token: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class GuestAccess(Base):
    """Opaque browser capability; never a Supabase user or member credential."""
    __tablename__ = "guest_access"
    id_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    student_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("flame.student_profiles.id", ondelete="RESTRICT"), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
