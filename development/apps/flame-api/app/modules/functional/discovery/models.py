"""Books and Classes; existing Teachers and Kits retain their owners."""
from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4
from sqlalchemy import Boolean, CheckConstraint, DateTime, Index, Integer, Numeric, String, func, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class CatalogueEntry(Base):
    __tablename__ = "catalogue_entries"
    __table_args__ = (
        CheckConstraint("kind IN ('books', 'classes')", name="catalogue_kind"),
        CheckConstraint("price IS NULL OR price >= 0", name="catalogue_price_nonnegative"),
        CheckConstraint("(price IS NULL) = (currency IS NULL)", name="catalogue_price_currency"),
        CheckConstraint("currency IS NULL OR currency ~ '^[A-Z]{3}$'", name="catalogue_currency"),
        Index("ix_catalogue_entries_kind_published_title", "kind", "published", "title"),
    )
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(4000))
    category: Mapped[str | None] = mapped_column(String(80))
    subject: Mapped[str | None] = mapped_column(String(120))
    level: Mapped[str | None] = mapped_column(String(80))
    language: Mapped[str | None] = mapped_column(String(80))
    format: Mapped[str | None] = mapped_column(String(80))
    author: Mapped[str | None] = mapped_column(String(255))
    location: Mapped[str | None] = mapped_column(String(255))
    schedule: Mapped[str | None] = mapped_column(String(255))
    availability: Mapped[str | None] = mapped_column(String(255))
    price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    currency: Mapped[str | None] = mapped_column(String(3))
    published: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
