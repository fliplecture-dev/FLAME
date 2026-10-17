"""BFF-only public discovery and separately authorized administration."""
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID
from fastapi import APIRouter, Depends, Query, Request, Response
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import select
from app.core.domain_errors import fail
from app.modules.functional.identity.router import require_bff
from app.modules.functional.identity.dependencies import require_admin
from app.modules.functional.discovery.models import CatalogueEntry
from app.modules.functional.discovery import service

router = APIRouter(prefix="/api/v1", tags=["fliplecture-discovery"])
Kind = Literal["books", "kits", "teachers", "classes"]
NewKind = Literal["books", "classes"]
Admin = Annotated[dict, Depends(require_admin)]


class EntryDraft(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=4000)
    category: str | None = Field(default=None, max_length=80)
    subject: str | None = Field(default=None, max_length=120)
    level: str | None = Field(default=None, max_length=80)
    language: str | None = Field(default=None, max_length=80)
    format: str | None = Field(default=None, max_length=80)
    author: str | None = Field(default=None, max_length=255)
    location: str | None = Field(default=None, max_length=255)
    schedule: str | None = Field(default=None, max_length=255, description="Include date, time and timezone; omit when unknown.")
    availability: str | None = Field(default=None, max_length=255)
    price: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    currency: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")

    @model_validator(mode="after")
    def price_pair(self):
        if (self.price is None) != (self.currency is None):
            raise ValueError("Enter both price and currency or leave both blank.")
        return self


class EntryEdit(EntryDraft):
    expected_version: int = Field(ge=1)


class Publication(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: int = Field(ge=1)
    published: bool


@router.get("/catalogue", dependencies=[Depends(require_bff)])
def catalogue(request: Request, response: Response, kind: Kind = "books", q: str = Query(default="", max_length=200),
              category: str | None = Query(default=None, max_length=255), subject: str | None = Query(default=None, max_length=255),
              level: str | None = Query(default=None, max_length=255), language: str | None = Query(default=None, max_length=80),
              format: str | None = Query(default=None, max_length=80), author: str | None = Query(default=None, max_length=255),
              location: str | None = Query(default=None, max_length=255), offset: int = Query(default=0, ge=0, le=10000),
              limit: int = Query(default=24, ge=1, le=48), sort: Literal["title", "newest"] = "title"):
    response.headers["Cache-Control"] = "no-store"
    filters = dict(category=category, subject=subject, level=level, language=language, format=format, author=author, location=location)
    with request.app.state.database.session() as session:
        return service.search(session, kind, q, filters, offset, limit, sort)


@router.get("/catalogue/{kind}/{item_id}", dependencies=[Depends(require_bff)])
def listing(request: Request, response: Response, kind: Kind, item_id: UUID, version: int | None = Query(default=None, ge=1)):
    response.headers["Cache-Control"] = "no-store"
    with request.app.state.database.session() as session:
        return service.detail(session, kind, item_id, version)


@router.get("/admin/catalogue/{kind}")
def admin_list(request: Request, principal: Admin, kind: NewKind, offset: int = Query(default=0, ge=0), limit: int = Query(default=24, ge=1, le=48)):
    with request.app.state.database.session() as session:
        rows = session.scalars(select(CatalogueEntry).where(CatalogueEntry.kind == kind).order_by(CatalogueEntry.created_at.desc(), CatalogueEntry.id).offset(offset).limit(limit)).all()
        return {"items": [entry_data(row) for row in rows], "offset": offset, "limit": limit}


def entry_data(row):
    return {name: getattr(row, name) for name in ["id", "kind", "version", "published", *EntryDraft.model_fields]}


@router.post("/admin/catalogue/{kind}", status_code=201)
def create(request: Request, principal: Admin, kind: NewKind, body: EntryDraft):
    with request.app.state.database.session() as session, session.begin():
        row = CatalogueEntry(kind=kind, **body.model_dump(), published=False, version=1)
        session.add(row); session.flush()
        return entry_data(row)


def locked(session, kind, item_id, expected_version):
    row = session.scalar(select(CatalogueEntry).where(CatalogueEntry.id == item_id, CatalogueEntry.kind == kind).with_for_update())
    if row is None:
        fail(404, "catalogue_item_unavailable")
    if row.version != expected_version:
        fail(409, "catalogue_version_changed")
    return row


@router.patch("/admin/catalogue/{kind}/{item_id}")
def edit(request: Request, principal: Admin, kind: NewKind, item_id: UUID, body: EntryEdit):
    with request.app.state.database.session() as session, session.begin():
        row = locked(session, kind, item_id, body.expected_version)
        # Editing a public record withdraws it until the revised content is explicitly published.
        for name, value in body.model_dump(exclude={"expected_version"}).items():
            setattr(row, name, value)
        row.version += 1; row.published = False
        session.flush()
        return entry_data(row)


@router.post("/admin/catalogue/{kind}/{item_id}/publication")
def publish(request: Request, principal: Admin, kind: NewKind, item_id: UUID, body: Publication):
    with request.app.state.database.session() as session, session.begin():
        row = locked(session, kind, item_id, body.expected_version)
        if body.published and not (row.description and row.category):
            fail(422, "catalogue_description_category_required")
        row.published = body.published; row.version += 1
        session.flush()
        return entry_data(row)
