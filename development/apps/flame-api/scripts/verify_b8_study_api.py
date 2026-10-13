"""One rollback-only, live-model Study API check using a temporary published path.

Run from the API directory with --execute. This uses a disposable principal override,
so it checks Study routing, publication, persistence, and replay but not browser login.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.core.config import Settings
from app.main import create_app
from app.modules.conversations.models import AnswerRequest, Message
from app.modules.curriculum.models import Curriculum
from app.modules.identity.dependencies import require_admin, require_member
from app.modules.identity.models import StudentProfile

ROOT = Path(__file__).resolve().parents[4]
OUTPUT = ROOT / "work" / "b8-study-api-check.json"
CASE = json.loads((Path(__file__).resolve().parents[1] / "tests" / "fixtures" /
                   "b6_teaching_cases.json").read_text(encoding="utf-8"))["cases"][0]


def checked(response, status):
    if response.status_code != status:
        raise RuntimeError(f"Study API returned {response.status_code}; expected {status}")
    return response.json()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    if not args.execute:
        print("Dry run: one temporary published Study path and one live model call; add --execute.")
        return
    if OUTPUT.exists():
        parser.error("Existing report preserved; move it before another paid run")
    settings = Settings()
    if not settings.database_url or not settings.llm_openai_api_key or not settings.llm_model:
        parser.error("Database, model, and server-only key must be configured")
    app = create_app(settings)
    member = uuid4()
    app.dependency_overrides[require_member] = lambda: {"id": str(member), "role": "member"}
    app.dependency_overrides[require_admin] = lambda: {"id": str(member), "role": "admin"}
    report = {"date": datetime.now(timezone.utc).isoformat(),
              "scope": "rollback-only TestClient Study route; disposable principal override, not signed-in browser",
              "case_id": CASE["id"], "question": CASE["question"],
              "model": settings.llm_model}
    with TestClient(app) as client:
        with app.state.database.engine.connect() as connection:
            outer = connection.begin()
            original_sessions = app.state.database.sessions
            app.state.database.sessions = sessionmaker(
                bind=connection, expire_on_commit=False, join_transaction_mode="create_savepoint")
            curriculum = None
            try:
                with app.state.database.session() as db, db.begin():
                    db.add(StudentProfile(id=member, auth_subject=str(member)))
                curriculum = checked(client.post("/api/v1/admin/curricula", json={
                    "code": "b8-" + uuid4().hex[:12], "name": "B8 Temporary Study Review"}), 201)["id"]
                def child(kind, parent_id, name, **extra):
                    return checked(client.post("/api/v1/admin/curriculum/" + kind,
                        json={"parent_id": parent_id, "name": name, **extra}), 201)["id"]
                level = child("level", curriculum, CASE["level"])
                subject = child("subject", level, CASE["subject"])
                domain = child("domain", subject, CASE["domain"])
                category = child("category", domain, CASE["category"])
                topic = child("topic", domain, CASE["topic"], category_id=category)
                subtopic = child("subtopic", topic, CASE["subtopic"])
                tree = checked(client.get(f"/api/v1/admin/curricula/{curriculum}/tree"), 200)
                checked(client.post(f"/api/v1/admin/curriculum/curriculum/{curriculum}/publish",
                                    json={"expected_version": tree["version"]}), 200)
                path = {"curriculum_id": curriculum, "level_id": level, "subject_id": subject,
                        "domain_id": domain, "category_id": category, "topic_id": topic,
                        "subtopic_id": subtopic}
                session = checked(client.post("/api/v1/sessions",
                                               json={"mode": "study", "context": path}), 201)
                route = f"/api/v1/sessions/{session['id']}/ask"
                body = {"mode": "study", "context": path, "question": CASE["question"]}
                first = checked(client.post(route, json=body,
                                    headers={"Idempotency-Key": "b8-study-live-check"}), 200)
                replay = checked(client.post(route, json=body,
                                     headers={"Idempotency-Key": "b8-study-live-check"}), 200)
                if first != replay or first["route"] != "direct_llm" or first["curriculum_version"] is None:
                    raise RuntimeError("Study answer/replay or version invariant failed")
                with app.state.database.session() as db:
                    messages = db.query(Message).filter_by(session_id=UUID(session["id"])).all()
                    stored = db.get(AnswerRequest, UUID(first["request_id"]))
                    assistant = next(row for row in messages if row.role == "assistant")
                    if len(messages) != 2 or assistant.resolved_subject_id != UUID(subject) or assistant.resolved_topic_id != UUID(topic):
                        raise RuntimeError("Study persisted turn or resolved path invariant failed")
                    report.update(status="passed", answer=first["blocks"][0]["text"],
                                  response_status=first["status"], prompt_version=stored.prompt_version,
                                  profile_version=stored.profile_version, input_tokens=stored.input_tokens,
                                  output_tokens=stored.output_tokens, latency_ms=stored.latency_ms,
                                  message_rows=len(messages), replay_identical=True,
                                  resolved_study_path=True)
            finally:
                app.state.database.sessions = original_sessions
                outer.rollback()
        with app.state.database.session() as db:
            if curriculum and db.get(Curriculum, UUID(curriculum)) is not None:
                raise RuntimeError("Temporary Study curriculum survived rollback")
    report["temporary_rows_rolled_back"] = True
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in (
        "status", "model", "prompt_version", "profile_version", "input_tokens",
        "output_tokens", "latency_ms", "message_rows", "replay_identical",
        "resolved_study_path", "temporary_rows_rolled_back")}, indent=2))


if __name__ == "__main__":
    main()
