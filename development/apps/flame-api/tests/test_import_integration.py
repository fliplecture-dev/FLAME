"""Rollback-only database integration tests for the internal B2 import service."""

from datetime import datetime, timedelta, timezone
import os
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.core.config import Settings
from app.core.database import Database
from app.modules.activity_kits.models import ActivityKit, KitTopic
from app.modules.curriculum.import_models import CurriculumImport, CurriculumImportSource
from app.modules.curriculum.import_service import CurriculumImportService, ImportFailure
from app.modules.curriculum.models import Category, Curriculum, Domain, Level, Subject, Subtopic, Topic
from app.modules.identity.models import AdminRole

pytestmark = pytest.mark.db_integration


def _row(category=None, subtopic="Push basics", source=None):
    return ["fliplecture", "Grade 1", "Science", "Motion", category, "Push", subtopic, None, source]


def _seed_preview(session_factory, curriculum_id, owner, rows, *, base_revision=0, invalid=0):
    preview_id = uuid4()
    with session_factory() as session, session.begin():
        batch = CurriculumImport(
            curriculum_id=curriculum_id, owner_subject=owner, filename="synthetic.xlsx",
            file_hash="0" * 64, file_bytes=None, status="previewed",
            sheet_levels={"Grade 1": "Grade 1"}, preview_revision=preview_id,
            base_revision=base_revision, issue_count=invalid,
            preview_rows=[{"sheet": "Grade 1", "row": i + 2, "values": values,
                           "operation": "created"} for i, values in enumerate(rows)],
            preview_result={"counts": {"created": len(rows), "reused": 0,
                                       "updated": 0, "invalid": invalid, "duplicates": 0},
                            "errors": ([{"sheet": "Grade 1", "row_number": 2,
                                         "column": "Topic", "code": "required"}] if invalid else [])},
            payload_expires_at=datetime.now(timezone.utc) + timedelta(days=30),
        )
        session.add(batch)
        session.flush()
        batch_id = batch.id
    return batch_id, preview_id


def test_internal_import_commit_isolated_idempotent_and_atomic():
    if os.environ.get("FLAME_RUN_DB_TESTS") != "1":
        pytest.skip("Set FLAME_RUN_DB_TESTS=1 to run rollback-only Supabase tests")
    database = Database(Settings())
    assert database.engine is not None
    try:
        with database.engine.connect() as connection:
            outer = connection.begin()
            try:
                factory = sessionmaker(bind=connection, expire_on_commit=False, join_transaction_mode="create_savepoint")
                owner = "b2-test-" + str(uuid4())
                other = "b2-other-" + str(uuid4())
                curriculum_id, other_id = uuid4(), uuid4()
                with factory() as session, session.begin():
                    session.add_all([
                        AdminRole(auth_subject=owner),
                        Curriculum(id=curriculum_id, code="fliplecture", normalized_code="fliplecture", name="Test target"),
                        Curriculum(id=other_id, code=other, normalized_code=other, name="Isolated target"),
                    ])
                service = CurriculumImportService(factory)
                rows = [_row(), _row(category="Motion", subtopic="Everyday push", source="Reference text"),
                        _row(category="Motion", subtopic="Everyday push", source="Other reference text")]
                batch_id, preview_id = _seed_preview(factory, curriculum_id, owner, rows)
                with pytest.raises(ImportFailure, match="admin_required"):
                    service.detail(owner="not-an-admin", import_id=batch_id)
                result = service.commit(owner=owner, import_id=batch_id,
                                        preview_revision=preview_id, idempotency_key="one")
                assert result["changes"]["created_nodes"] == 8
                assert result["changes"]["sources_added"] == 2
                assert result["revision"] == 1
                assert service.commit(owner=owner, import_id=batch_id,
                                      preview_revision=preview_id, idempotency_key="one") == result
                with pytest.raises(ImportFailure, match="idempotency_conflict"):
                    service.commit(owner=owner, import_id=batch_id,
                                   preview_revision=uuid4(), idempotency_key="one")
                with factory() as session:
                    levels = session.scalars(select(Level).where(Level.curriculum_id == curriculum_id)).all()
                    assert len(levels) == 1
                    assert session.scalar(select(func.count()).select_from(Level).where(Level.curriculum_id == other_id)) == 0
                    subject = session.scalar(select(Subject).where(Subject.level_id == levels[0].id))
                    domain = session.scalar(select(Domain).where(Domain.subject_id == subject.id))
                    topics = session.scalars(select(Topic).where(Topic.domain_id == domain.id)).all()
                    assert len(topics) == 2
                    assert {topic.category_id is None for topic in topics} == {True, False}
                    assert session.scalar(select(func.count()).select_from(Subtopic).where(Subtopic.topic_id.in_([t.id for t in topics]))) == 2
                    assert session.scalar(select(func.count()).select_from(Category).where(Category.domain_id == domain.id)) == 1
                    assert session.scalar(select(func.count()).select_from(CurriculumImportSource).where(CurriculumImportSource.curriculum_id == curriculum_id)) == 2
                    category = session.scalar(select(Category).where(Category.domain_id == domain.id))
                    assert [topic.display_order for topic in topics] == [0, 0]
                with factory() as session, session.begin():
                    kit = ActivityKit(name="Two-topic test kit")
                    session.add(kit)
                    session.flush()
                    session.add_all([KitTopic(kit_id=kit.id, topic_id=topic.id) for topic in topics])
                with factory() as session:
                    assert session.scalar(select(func.count()).select_from(KitTopic).where(KitTopic.kit_id == kit.id)) == 2
                with pytest.raises(IntegrityError):
                    with factory() as session, session.begin():
                        second_domain = Domain(subject_id=subject.id, name="Other domain",
                                               normalized_name="other domain", display_order=1)
                        session.add(second_domain)
                        session.flush()
                        session.add(Topic(domain_id=second_domain.id, category_id=category.id,
                                          name="Wrong ancestor", normalized_name="wrong ancestor",
                                          display_order=0))
                        session.flush()
                missing_subtopic, missing_preview = _seed_preview(
                    factory, curriculum_id, owner, [_row(subtopic=None)], base_revision=1)
                with pytest.raises(ImportFailure, match="subtopic_required"):
                    service.commit(owner=owner, import_id=missing_subtopic,
                                   preview_revision=missing_preview, idempotency_key="missing-subtopic")
                stale_batch, stale_preview = _seed_preview(factory, curriculum_id, owner, rows, base_revision=0)
                with pytest.raises(ImportFailure, match="stale_preview"):
                    service.commit(owner=owner, import_id=stale_batch,
                                   preview_revision=stale_preview, idempotency_key="stale")
                invalid_batch, invalid_preview = _seed_preview(factory, curriculum_id, owner, rows, base_revision=1, invalid=1)
                with pytest.raises(ImportFailure, match="invalid_rows"):
                    service.commit(owner=owner, import_id=invalid_batch,
                                   preview_revision=invalid_preview, idempotency_key="invalid")
                assert service.detail(owner=owner, import_id=batch_id)["status"] == "committed"
                assert service.issue_page(owner=owner, import_id=invalid_batch)["total"] == 1
                first_page = service.history(owner=owner, curriculum_id=curriculum_id, limit=1)
                assert len(first_page["items"]) == 1 and first_page["next_cursor"]
                second_page = service.history(owner=owner, curriculum_id=curriculum_id,
                                              limit=1, cursor=first_page["next_cursor"])
                assert second_page["items"][0]["import_id"] != first_page["items"][0]["import_id"]
            finally:
                outer.rollback()
    finally:
        database.close()


def test_real_kg_workbook_reimport_reuses_paths():
    if os.environ.get("FLAME_RUN_DB_TESTS") != "1":
        pytest.skip("Set FLAME_RUN_DB_TESTS=1 to run rollback-only Supabase tests")
    path = Path(__file__).resolve().parents[4] / "Curriculum Documents" / "Fliplecture Curriculum Grade 1 to 5.xlsx"
    if not path.exists():
        pytest.skip("Owner workbook is not distributed with the backend package")
    database = Database(Settings())
    assert database.engine is not None
    try:
        with database.engine.connect() as connection:
            outer = connection.begin()
            try:
                factory = sessionmaker(bind=connection, expire_on_commit=False,
                                       join_transaction_mode="create_savepoint")
                owner = "b2-kg-" + str(uuid4())
                curriculum_id = uuid4()
                with factory() as session, session.begin():
                    session.add_all([
                        AdminRole(auth_subject=owner),
                        Curriculum(id=curriculum_id, code="fliplecture",
                                   normalized_code="fliplecture", name="KG reimport test"),
                    ])
                service = CurriculumImportService(factory)
                payload = path.read_bytes()
                first = service.upload(owner=owner, curriculum_id=curriculum_id,
                                       filename=path.name, payload=payload)
                first_id = UUID(first["import_id"])
                first_preview = service.preview(owner=owner, import_id=first_id,
                                                sheet_levels={"Grade KG": "Grade KG"})
                assert first_preview["counts"]["created"] == 8
                first_result = service.commit(owner=owner, import_id=first_id,
                    preview_revision=UUID(first_preview["preview_revision"]), idempotency_key="kg-first")
                second = service.upload(owner=owner, curriculum_id=curriculum_id,
                                        filename=path.name, payload=payload)
                second_id = UUID(second["import_id"])
                second_preview = service.preview(owner=owner, import_id=second_id,
                                                 sheet_levels={"Grade KG": "Grade KG"})
                assert second_preview["counts"]["reused"] == 8
                assert second_preview["counts"]["created"] == 0
                second_result = service.commit(owner=owner, import_id=second_id,
                    preview_revision=UUID(second_preview["preview_revision"]), idempotency_key="kg-second")
                assert second_result["changes"]["created_nodes"] == 0
                assert second_result["revision"] == first_result["revision"]
                assert service.row_page(owner=owner, import_id=second_id, limit=3)["next_offset"] == 3
                assert service.issue_page(owner=owner, import_id=second_id)["items"] == []
                assert service.purge_expired_payloads(now=datetime.now(timezone.utc) + timedelta(days=31)) == 2
                assert service.detail(owner=owner, import_id=second_id)["status"] == "committed"
            finally:
                outer.rollback()
    finally:
        database.close()
