from uuid import uuid4
import pytest
from pydantic import ValidationError
from app.contracts.learning_metadata import LearningMetadata
from app.modules.recommendations.evaluation import evaluate
from test_curriculum_workspace import isolated_client


def test_representative_evaluation():
    results = evaluate()
    assert len(results) == 12
    assert all(r["passed"] for r in results), results


@pytest.mark.parametrize("value", [{"grade_min": 1}, {"grade_min": 6, "grade_max": 1},
    {"languages": ["English"]}, {"purposes": ["invented"]}, {"concepts": [""]}])
def test_invalid_metadata(value):
    with pytest.raises(ValidationError):
        LearningMetadata.model_validate(value)


def test_metadata_normalization():
    value = LearningMetadata(concepts=[" Gravity ", "gravity"], languages=["EN-IN"], purposes=["explain", "explain"])
    assert value.concepts == ["Gravity"] and value.languages == ["en-in"] and value.purposes == ["explain"]


def test_resource_metadata_versions_and_legacy_compatibility():
    with isolated_client() as client:
        client.app.state.settings.resource_allowed_hosts = "media.example.test"
        body = dict(title="Metadata fixture", type="image", external_url="https://media.example.test/gravity.png")
        result = client.post("/api/v1/admin/resources", json=body)
        assert result.status_code == 201, result.text
        row = result.json()
        assert row["learning_metadata"]["concepts"] == []
        fields = dict(topic_labels=[], concepts=["gravity"], synonyms=["things fall"], grade_min=1, grade_max=3,
            languages=["en"], purposes=["explain"])
        changed = client.patch("/api/v1/admin/resources/" + row["id"], json=dict(expected_version=row["version"], learning_metadata=fields))
        assert changed.status_code == 200, changed.text
        saved = changed.json()
        assert saved["learning_metadata"] == fields and saved["version"] > row["version"]
        assert saved["external_url"] == row["external_url"] and saved["paths"] == []
        stale = client.patch("/api/v1/admin/resources/" + row["id"], json=dict(expected_version=row["version"], learning_metadata={}))
        assert stale.status_code == 409
        invalid = client.patch("/api/v1/admin/resources/" + row["id"], json=dict(expected_version=saved["version"], learning_metadata={"grade_min": 5}))
        assert invalid.status_code == 422
        assert client.get("/api/v1/admin/resources/" + row["id"]).json()["learning_metadata"] == fields


def test_teacher_metadata_and_batched_expertise_queries():
    from sqlalchemy import event
    from app.modules.teachers.candidates import eligible_candidates, public_teacher
    from app.modules.teachers.models import Teacher, TeacherExpertise
    from uuid import UUID
    with isolated_client() as client:
        c = client.post('/api/v1/admin/curricula', json={'code': 'meta-'+uuid4().hex[:8], 'name': 'Metadata fixture'}).json()
        def child(kind, parent):
            result = client.post('/api/v1/admin/curriculum/'+kind, json={'parent_id': parent, 'name': kind})
            assert result.status_code == 201, result.text
            return result.json()['id']
        level = child('level', c['id']); subject = child('subject', level); domain = child('domain', subject); topic = child('topic', domain)
        with client.app.state.database.session() as db, db.begin():
            for i in range(8):
                row = Teacher(name=f'Teacher {i}', published=True, languages=['en'], learning_metadata={'concepts': ['gravity']})
                db.add(row); db.flush()
                db.add(TeacherExpertise(teacher_id=row.id, subject_id=UUID(subject), topic_id=UUID(topic), claim_status='declared'))
        statements = []
        def record(conn, cursor, statement, parameters, context, executemany):
            if statement.lstrip().upper().startswith("SELECT"):
                statements.append(statement)
        with client.app.state.database.session() as db:
            engine = db.get_bind()
            event.listen(engine, 'before_cursor_execute', record)
            try:
                result = eligible_candidates(db, UUID(subject), UUID(topic))
            finally:
                event.remove(engine, 'before_cursor_execute', record)
        optimized_count = len(statements)
        statements.clear()
        with client.app.state.database.session() as db:
            engine = db.get_bind()
            event.listen(engine, 'before_cursor_execute', record)
            try:
                from sqlalchemy import select
                rows = db.scalars(select(Teacher).join(TeacherExpertise).where(TeacherExpertise.subject_id == UUID(subject)).distinct()).all()
                for row in rows:
                    public_teacher(db, row, UUID(subject), UUID(topic))
            finally:
                event.remove(engine, 'before_cursor_execute', record)
        assert len(statements) == 9
        assert optimized_count == 2
        import json
        from pathlib import Path
        output = Path(__file__).resolve().parents[4] / 'work' / 'recommendation-quality' / 'tutor-query-check.json'
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps({'scope': 'Rollback-only eight-tutor fixture; SELECT queries, no transaction control statements.', 'tutors': 8, 'previous_query_pattern': len(statements), 'batched_query_pattern': optimized_count}, indent=2), encoding='utf-8')
        assert len(result) == 8 and all(r.concepts == ['gravity'] for r in result)
        assert optimized_count == 2
        # Exercise both catalogue APIs: metadata-only updates retain their mappings.
        teacher = client.post('/api/v1/admin/teachers', json={'name': 'API teacher', 'learning_metadata': {'concepts': ['gravity']}, 'expertise': [{'subject_id': subject, 'topic_id': topic, 'claim_status': 'declared'}]})
        assert teacher.status_code == 201, teacher.text
        teacher = teacher.json()
        changed = client.patch('/api/v1/admin/teachers/'+teacher['id'], json={'expected_version': teacher['version'], 'learning_metadata': {'purposes': ['human_help']}})
        assert changed.status_code == 200, changed.text
        assert changed.json()['expertise'] == teacher['expertise']
        kit = client.post('/api/v1/admin/activity-kits', json={'name': 'API kit', 'paths': [{'topic_id': topic, 'subtopic_id': None}], 'learning_metadata': {'concepts': ['gravity']}})
        assert kit.status_code == 201, kit.text
        kit = kit.json()
        changed = client.patch('/api/v1/admin/activity-kits/'+kit['id'], json={'expected_version': kit['version'], 'learning_metadata': {'purposes': ['practise']}})
        assert changed.status_code == 200, changed.text
        assert changed.json()['paths'] == kit['paths'] and changed.json()['learning_metadata']['purposes'] == ['practise']
