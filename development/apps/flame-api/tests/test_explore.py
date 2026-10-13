"""Explore is an authorized catalogue, not an answer recommendation rewrite."""
from types import SimpleNamespace
from uuid import uuid4
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from app.contracts.catalogue import CatalogueCandidate
from app.core.config import Settings
from app.main import create_app
from app.modules.learning_response import explore


def candidate(index=0, **changes):
    data = dict(id=uuid4(), kind="resource", type="diagram", version=2, title=f"Gravity {index:03}",
                availability_state="available", card={"id": str(uuid4()), "title": "Gravity"})
    return CatalogueCandidate(**(data | changes))


def test_full_dataset_search_paging_and_no_history_access(monkeypatch):
    rows = [candidate(i) for i in range(130)]
    monkeypatch.setattr(explore, "media_candidates", lambda *args: rows)
    path = dict(topic_id=uuid4(), subtopic_id=None, grade="Grade 2", curriculum_revision=17)
    page = explore.browse(None, None, path, "resource", offset=120, limit=24)
    assert page["total"] == 130 and len(page["items"]) == 10
    found = explore.browse(None, None, path, "resource", search="gravity 129")
    assert found["total"] == 1 and found["items"][0]["id"] == str(rows[-1].id)
    focused = explore.browse(None, None, path, "resource", focus_id=rows[-1].id)
    assert focused["offset"] == 120 and str(rows[-1].id) in [item["id"] for item in focused["items"]]
    assert "card" not in found["items"][0]
    assert rows[-1].version == 2  # No writes or recommendation repository involved.


def test_suitability_known_metadata_and_unknown_language():
    assert not explore.suitable(candidate(grade_min=3, grade_max=5), "Grade 2", None)
    assert explore.suitable(candidate(grade_min=0, grade_max=2), "Grade KG", None)
    assert explore.suitable(candidate(languages=["English"]), "Grade 2", "en-GB")
    assert not explore.suitable(candidate(languages=["ta-IN"]), "Grade 2", "en")
    assert explore.suitable(candidate(), "Grade 2", "en")


@pytest.mark.parametrize("kind,owner", [("resource", "media_candidates"), ("kit", "kit_candidates"), ("tutor", "teacher_candidates")])
def test_open_rechecks_owner_eligibility_and_version(monkeypatch, kind, owner):
    row = candidate(kind=kind)
    monkeypatch.setattr(explore, owner, lambda *args: [row])
    path = dict(topic_id=uuid4(), subject_id=uuid4(), subtopic_id=None, grade="Grade 2")
    assert explore.open_item(None, None, path, kind, row.id, 2)["item"]["version"] == 2
    with pytest.raises(HTTPException) as stale:
        explore.open_item(None, None, path, kind, row.id, 1)
    assert stale.value.status_code == 409
    monkeypatch.setattr(explore, owner, lambda *args: [])
    with pytest.raises(HTTPException) as withdrawn:
        explore.open_item(None, None, path, kind, row.id, 2)
    assert withdrawn.value.status_code == 404


def test_revision_is_not_ignored(monkeypatch):
    monkeypatch.setattr(explore, "describe_browse_path", lambda *args: {"curriculum_revision": 17})
    with pytest.raises(HTTPException) as stale:
        explore.context(None, uuid4(), None, 16)
    assert stale.value.status_code == 409


def test_member_routes_require_authentication():
    app = create_app(Settings(_env_file=None, environment="test"))
    with TestClient(app) as client:
        for path in ("/api/v1/explore?topic_id=" + str(uuid4()), "/api/v1/explore/context?session_id=" + str(uuid4()) + "&message_id=" + str(uuid4())):
            assert client.get(path).status_code in (401, 403)


def test_curiosity_matches_topic_or_precise_subtopic_without_guessing(monkeypatch):
    topic, other = uuid4(), uuid4()
    def row(tid, label, leaf, **changes):
        return dict(curriculum_id=uuid4(), curriculum="Fixture", curriculum_revision=3,
            level_id=uuid4(), level="Grade 1", subject_id=uuid4(), subject="Science", domain_id=uuid4(),
            domain="Motion", topic_id=tid, topic=label, subtopic_id=uuid4(), subtopic=leaf) | changes
    first = row(topic, "Gravity", "Falling objects")
    second = first | {"subtopic_id": uuid4(), "subtopic": "Gravity at a distance"}
    light = row(other, "Light", "Shadows")
    monkeypatch.setattr(explore, "browse_search_paths", lambda db: [first, second, light])
    result = explore.curiosity_context(None, "Explain gravity")
    assert result["context"]["topic_id"] == topic and result["context"]["subtopic_id"] is None
    assert not result["candidates"]
    assert explore.curiosity_context(None, "Explain falling objects")["context"]["subtopic_id"] == first["subtopic_id"]
    assert explore.curiosity_context(None, "Explain light")["context"]["topic_id"] == other
    assert explore.curiosity_context(None, "Tell me about dinosaurs") == {"context": None, "candidates": []}
    assert explore.curiosity_context(None, "") == {"context": None, "candidates": []}
    another = row(uuid4(), "Gravity", "Falling", level="Grade 2", curriculum="Other curriculum")
    monkeypatch.setattr(explore, "browse_search_paths", lambda db: [first, second, another])
    ambiguous = explore.curiosity_context(None, "Explain gravity")
    assert ambiguous["context"] is None and len(ambiguous["candidates"]) == 2
    assert explore.curiosity_context(None, "Explain grade 1 gravity")["context"]["topic_id"] == topic
    assert explore.curiosity_context(None, "Explain Other curriculum gravity")["context"]["topic_id"] == another["topic_id"]

    shadows=row(uuid4(),'Shadows','How shadows form')
    plant=row(uuid4(),'Needs of Plants','Light')
    monkeypatch.setattr(explore,'browse_search_paths',lambda db:[first,second,light,shadows,plant])
    combined=explore.curiosity_context(None,'light and shadows')['candidates']
    assert {p['topic_id'] for p in combined}=={other,shadows['topic_id']}
    assert all(p['subtopic_id'] is None for p in combined)
    combined=explore.curiosity_context(None,'falling objects and light')['candidates']
    assert {(p['topic_id'],p['subtopic_id']) for p in combined}=={(topic,first['subtopic_id']),(other,None)}


@pytest.mark.parametrize("kind,owner", [("resource", "media_candidates"), ("tutor", "teacher_candidates"), ("kit", "kit_candidates")])
def test_curiosity_combines_filters_deduplicates_and_keeps_open_scope(monkeypatch, kind, owner):
    paths = [dict(topic_id=uuid4(), subject_id=uuid4(), subtopic_id=None, curriculum_revision=17, grade="Grade 1"),
             dict(topic_id=uuid4(), subject_id=uuid4(), subtopic_id=uuid4(), curriculum_revision=18, grade="Grade 5")]
    shared = candidate(kind=kind, type="image", title="Gravity shared")
    older = candidate(kind=kind, type="video", title="Gravity older", grade_min=5, grade_max=5)
    hidden = candidate(kind=kind, title="Too old", grade_min=9, grade_max=10)
    monkeypatch.setattr(explore, "curiosity_context", lambda *args: {"context":None,"candidates":paths})
    monkeypatch.setattr(explore, "context", lambda db, topic, *args: next(p for p in paths if p["topic_id"] == topic))
    monkeypatch.setattr(explore, owner, lambda *args: [shared, older, hidden])
    found = explore.browse_curiosity(None, None, "gravity", kind, limit=1)
    assert found["total"] == 2 and len(found["items"]) == 1
    page = explore.browse_curiosity(None, None, "gravity", kind, offset=1, limit=1)
    assert page["items"][0]["id"] == str(shared.id)
    assert page["items"][0]["browse_path"] == paths[0]
    assert found["items"][0]["browse_path"] == paths[1]
    filtered = explore.browse_curiosity(None, None, "gravity", kind, search="shared", media_type="image")
    assert filtered["total"] == 1
    focused = explore.browse_curiosity(None, None, "gravity", kind, limit=1, focus_id=shared.id)
    assert focused["offset"] == 1


@pytest.mark.db_integration
def test_explore_database_mapping_and_open_rechecks():
    import os
    from tempfile import TemporaryDirectory
    from sqlalchemy.orm import sessionmaker
    from app.modules.identity.dependencies import require_admin, require_member
    from app.modules.identity.models import StudentProfile
    from app.modules.resources.models import Resource, ResourceTopic
    from app.modules.teachers.models import Teacher, TeacherExpertise
    from app.modules.conversations.models import ConversationSession, Message
    from time import perf_counter
    from sqlalchemy import event
    from app.modules.activity_kits.models import ActivityKit, KitTopic
    from pathlib import Path
    if os.environ.get("FLAME_RUN_DB_TESTS") != "1":
        pytest.skip("Set FLAME_RUN_DB_TESTS=1 for rollback-only checks")
    base = Settings()
    with TemporaryDirectory() as storage:
        app = create_app(Settings(_env_file=None, environment="test", database_url=base.database_url,
            resource_local_dir=storage, resource_allowed_hosts="media.example.test"))
        member, other = uuid4(), uuid4()
        principal = {"id": str(member), "role": "admin"}
        app.dependency_overrides[require_member] = lambda: principal
        app.dependency_overrides[require_admin] = lambda: principal
        with TestClient(app) as client, app.state.database.engine.connect() as connection:
            transaction = connection.begin()
            original = app.state.database.sessions
            app.state.database.sessions = sessionmaker(bind=connection, expire_on_commit=False, join_transaction_mode="create_savepoint")
            try:
                with app.state.database.session() as db, db.begin():
                    db.add_all([StudentProfile(id=value, auth_subject=str(value), display_name="Explore fixture",
                        email=str(value)+"@example.test") for value in (member, other)])
                response = client.post("/api/v1/admin/curricula", json={"code":"explore-"+uuid4().hex[:8], "name":"Explore fixture"})
                assert response.status_code == 201, response.text
                cid = response.json()["id"]
                def child(kind, parent, name):
                    response = client.post("/api/v1/admin/curriculum/"+kind, json={"parent_id":parent,"name":name})
                    assert response.status_code == 201, response.text
                    return response.json()["id"]
                level = child("level", cid, "Grade 2")
                subject = child("subject", level, "Science")
                domain = child("domain", subject, "Motion")
                topic = child("topic", domain, "Gravity")
                leaf = child("subtopic", topic, "Falling")
                sibling = child("subtopic", topic, "Push and pull")
                other_topic = child("topic", domain, "Light")
                child("subtopic", other_topic, "Shadows")
                tree = client.get(f"/api/v1/admin/curricula/{cid}/tree").json()
                published = client.post(f"/api/v1/admin/curriculum/curriculum/{cid}/publish", json={
                    "expected_version":tree["version"],"expected_draft_revision":tree["draft_revision"]})
                assert published.status_code == 200, published.text
                revision = published.json()["revision"]
                with app.state.database.session() as db, db.begin():
                    rows = [Resource(type="diagram", title=f"Gravity {index:03}", external_url="https://media.example.test/gravity.png",
                        alt_text="A ball falling toward Earth", learning_metadata={"topic_labels":["Gravity"]}, published=True, version=2, availability="available") for index in range(130)]
                    direct = Resource(type="diagram", title="Direct falling", external_url="https://media.example.test/direct.png", published=True, version=2)
                    draft = Resource(type="diagram",title="Private draft",external_url="https://media.example.test/draft.png")
                    unavailable = Resource(type="diagram",title="Unavailable",external_url="https://media.example.test/unavailable.png",published=True,availability="unavailable")
                    unmapped = Resource(type="diagram",title="Unmapped",external_url="https://media.example.test/unmapped.png",published=True)
                    wrong_grade = Resource(type="diagram",title="Grade five",external_url="https://media.example.test/grade.png",published=True,learning_metadata={"grade_min":5,"grade_max":6})
                    db.add_all([*rows,direct,draft,unavailable,unmapped,wrong_grade]);db.flush()
                    db.add_all([ResourceTopic(resource_id=row.id,topic_id=topic) for row in [*rows,draft,unavailable,wrong_grade]])
                    db.add(ResourceTopic(resource_id=direct.id,topic_id=topic,subtopic_id=leaf))
                    teacher = Teacher(name="Science tutor",published=True,version=2)
                    away = Teacher(name="Unavailable tutor",published=True,availability="on leave")
                    db.add_all([teacher,away]);db.flush()
                    key="resource-uploads/"+uuid4().hex+".png"
                    (Path(storage)/"resource-uploads").mkdir()
                    from PIL import Image
                    Image.new("RGB",(2,2),"blue").save(Path(storage)/key)
                    kit = ActivityKit(name="Gravity kit",description="Practise falling objects",materials=["Ball"],
                        instructions="Observe with an adult",supervision="Adult required",image_keys=[key],
                        availability="Available",published=True,version=2)
                    db.add(kit);db.flush()
                    db.add(KitTopic(kit_id=kit.id,topic_id=topic,subtopic_id=leaf))
                    kid = kit.id
                    db.add_all([TeacherExpertise(teacher_id=row.id,subject_id=subject) for row in (teacher,away)])
                    conversation = ConversationSession(student_id=member,mode="study",curriculum_id=cid,revision=revision,
                        context_snapshot={"subtopic_id":leaf})
                    db.add(conversation);db.flush()
                    answer = Message(session_id=conversation.id,turn_number=1,role="assistant",blocks=[{"kind":"text","text":"Gravity pulls."}],
                        resolved_curriculum_id=cid,resolved_subject_id=subject,resolved_topic_id=topic,resolved_revision=revision)
                    db.add(answer);db.flush()
                    rid, direct_id, tid, sid, mid = rows[0].id,direct.id,teacher.id,conversation.id,answer.id
                params = {"topic_id":topic,"curriculum_revision":revision}
                timings=[]
                counts=[]
                query_counter=[0]
                def count_query(conn,cursor,statement,parameters,execution_context,executemany):
                    if statement.lstrip().upper().startswith("SELECT"):
                        query_counter[0]+=1
                event.listen(connection,"before_cursor_execute",count_query)
                for _ in range(5):
                    query_counter[0]=0
                    started=perf_counter();response=client.get("/api/v1/explore",params=params);timings.append(round((perf_counter()-started)*1000,2))
                    counts.append(query_counter[0])
                    assert response.status_code == 200,response.text
                    assert response.json()["total"] == 130
                assert counts == [2] * 5
                event.remove(connection,"before_cursor_execute",count_query)
                page = client.get("/api/v1/explore",params=params|{"offset":120}).json()
                assert len(page["items"]) == 10
                assert client.get("/api/v1/explore",params=params|{"search":"Gravity 129"}).json()["total"] == 1
                assert client.get("/api/v1/explore",params=params|{"subtopic_id":leaf}).json()["total"] == 131
                assert client.get("/api/v1/explore",params=params|{"subtopic_id":sibling}).json()["total"] == 130
                assert client.get(f"/api/v1/explore/resource/{direct_id}",params=params|{"version":2}).status_code == 404
                assert client.get(f"/api/v1/explore/resource/{direct_id}",params=params|{"subtopic_id":leaf,"version":2}).status_code == 200
                assert client.get(f"/api/v1/explore/resource/{rid}",params=params|{"version":1}).status_code == 409
                assert client.get(f"/api/v1/resources/{rid}/delivery",params=params|{"version":2}).status_code == 200
                assert client.get(f"/api/v1/resources/{rid}/delivery",params={"topic_id":other_topic,"version":2}).status_code == 404
                assert client.get("/api/v1/explore",params=params|{"curriculum_revision":revision+1}).status_code == 409
                teachers = client.get("/api/v1/explore",params=params|{"kind":"tutor"}).json()
                assert teachers["total"] == 1 and teachers["items"][0]["availability_state"] == "unknown"
                assert client.get(f"/api/v1/explore/tutor/{tid}",params=params|{"version":2}).status_code == 200
                assert client.get("/api/v1/explore",params=params|{"kind":"kit"}).json()["total"] == 0
                kits = client.get("/api/v1/explore",params=params|{"kind":"kit","subtopic_id":leaf}).json()
                assert kits["total"] == 1 and kits["items"][0]["coverage"] == "subtopic"
                assert client.get(f"/api/v1/explore/kit/{kid}",params=params|{"subtopic_id":leaf,"version":2}).status_code == 200
                assert client.get(f"/api/v1/explore/kit/{kid}",params=params|{"subtopic_id":sibling,"version":2}).status_code == 404
                saved = client.get("/api/v1/explore/context",params={"session_id":sid,"message_id":mid})
                assert saved.status_code == 200 and saved.json()["context"]["subtopic_id"] == leaf
                with app.state.database.session() as db, db.begin():
                    curiosity = ConversationSession(student_id=member, mode="curiosity", context_snapshot={})
                    db.add(curiosity); db.flush()
                    questions = ["Explain Explore fixture Grade 2 Gravity", "Explain Explore fixture Grade 2 Light", "Dinosaurs on Mars"]
                    curiosity_answers = []
                    for turn, question in enumerate(questions, 1):
                        db.add(Message(session_id=curiosity.id, turn_number=turn, role="user", blocks=[{"kind":"text", "text":question}]))
                        answer = Message(session_id=curiosity.id, turn_number=turn, role="assistant", blocks=[{"kind":"text", "text":"Answer"}])
                        db.add(answer); db.flush(); curiosity_answers.append(str(answer.id))
                    curiosity_id = str(curiosity.id)
                for message_id, expected in zip(curiosity_answers, (topic, other_topic, None)):
                    result = client.get("/api/v1/explore/context", params={"session_id":curiosity_id,"message_id":message_id})
                    assert result.status_code == 200, result.text
                    assert (result.json()["context"]["topic_id"] if result.json()["context"] else None) == expected
                combined = client.get("/api/v1/explore/curiosity", params={"session_id":curiosity_id,
                    "message_id":curiosity_answers[0], "search":"Gravity 129"})
                assert combined.status_code == 200 and combined.json()["total"] == 1, combined.text
                assert combined.json()["items"][0]["browse_path"]["topic_id"] == topic
                assert client.get("/api/v1/explore/curiosity",params={"session_id":sid,"message_id":mid}).status_code == 404
                principal["id"] = str(other)
                assert client.get("/api/v1/explore/context",params={"session_id":sid,"message_id":mid}).status_code == 404
                assert client.get("/api/v1/explore/context",params={"session_id":curiosity_id,"message_id":curiosity_answers[0]}).status_code == 404
                assert client.get("/api/v1/explore/curiosity",params={"session_id":curiosity_id,"message_id":curiosity_answers[0]}).status_code == 404
                principal["id"] = str(member)
                with app.state.database.session() as db, db.begin():
                    db.get(Resource,rid).published=False
                assert client.get(f"/api/v1/explore/resource/{rid}",params=params|{"version":2}).status_code == 404
                print("Explore rollback fixture: 130 topic media, HTTP milliseconds:",timings,"SELECT counts:",counts)
                import json
                (Path(__file__).resolve().parents[4]/"work"/"b14-explore-performance.json").write_text(json.dumps({
                    "fixture":"130 published topic-linked external images; rollback-only local TestClient", "http_ms":timings,
                    "select_counts":counts, "median_ms":sorted(timings)[2],"max_ms":max(timings)},indent=2))
            finally:
                app.state.database.sessions = original
                transaction.rollback()


@pytest.mark.parametrize("kind", ["resource","tutor","kit"])
def test_admin_topic_labels_do_not_break_or_influence_catalogue_candidates(kind):
    from app.contracts.learning_metadata import candidate_metadata, metadata_data
    saved={"topic_labels":["Gravity"],"concepts":["force"]}
    assert metadata_data(saved)["topic_labels"]==["Gravity"]
    row=candidate(kind=kind, **candidate_metadata(saved))
    assert row.concepts==["force"]
    assert "topic_labels" not in row.selection_data()
