r"""Controlled, synthetic B8 model-quality baseline. No private member data or credentials are written.

Run from the API directory:
  .\.venv\Scripts\python.exe -m scripts.evaluate_b8 --execute
The default command only prints the planned case count.
"""
import argparse
from datetime import datetime, timezone
import json
from math import ceil
from pathlib import Path
from statistics import median
from time import perf_counter
from uuid import uuid4

from app.core.config import Settings
from app.modules.application.teaching.answer_service import _answer
from app.modules.functional.curriculum.teaching_context import TeachingContext
from app.modules.application.teaching.gateway import GatewayError, OpenAIResponsesGateway
from app.modules.application.teaching.profiles import profile
from app.modules.application.teaching.prompt import assemble

ROOT = Path(__file__).resolve().parents[4]
FIXTURES = Path(__file__).resolve().parents[1] / "tests" / "fixtures"
DEFAULT_OUTPUT = ROOT / "work" / "b8-live-baseline.json"


def candidates():
    study = json.loads((FIXTURES / "b6_teaching_cases.json").read_text(encoding="utf-8"))["cases"]
    extra = json.loads((FIXTURES / "b8_evaluation_cases.json").read_text(encoding="utf-8"))["cases"]
    indexed = {case["id"]: case for case in study}
    result = []
    for case in study:
        result.append({**case, "group": "study_factual", "mode": "study", "runs": 3})
    for case in extra:
        source = indexed.get(case.get("study_case_id"))
        result.append({**case, "source": source})
    return result


def prompt_for(case):
    source = case.get("source") or case
    names = {"curriculum": "FlipLecture B8 review", "level": source["level"],
             "subject": source["subject"], "domain": source["domain"],
             "category": source.get("category"), "topic": source["topic"],
             "subtopic": source["subtopic"]}
    context = TeachingContext(ids={}, names=names, revision=1,
                              curriculum_description=None, learning_outcome=None)
    return context, assemble(case["question"], context,
                             profile(source["level"], source["level"]), [])


def summary(rows):
    times = sorted(row["latency_ms"] for row in rows if row["status"] == "ok")
    return {
        "attempted": len(rows),
        "ok": len(times),
        "failed": len(rows) - len(times),
        "input_tokens": sum(row.get("input_tokens", 0) for row in rows),
        "output_tokens": sum(row.get("output_tokens", 0) for row in rows),
        "gateway_median_ms": median(times) if times else None,
        "gateway_p95_ms": times[ceil(0.95 * len(times)) - 1] if times else None,
        "timing_scope": "gateway-to-validated-answer; excludes browser and BFF",
    }


def write_report(path, report):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true", help="Make live paid model calls")
    parser.add_argument("--limit", type=int, default=0, help="Maximum calls; 0 means all")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    if args.limit < 0:
        parser.error("--limit must be non-negative")
    plan = [(case, attempt + 1) for case in candidates() for attempt in range(case["runs"])]
    if args.limit:
        plan = plan[:args.limit]
    if not args.execute:
        print(f"Dry run: {len(plan)} synthetic model calls planned. Add --execute to run.")
        return
    if args.output.exists():
        parser.error("Output already exists; choose a new --output path to preserve earlier review evidence")
    settings = Settings()
    if not settings.llm_openai_api_key or not settings.llm_model:
        parser.error("The API model and key must be configured before live evaluation")
    gateway = OpenAIResponsesGateway(settings.llm_openai_api_key.get_secret_value(),
                                     settings.llm_model,
                                     timeout_seconds=settings.llm_timeout_seconds,
                                     max_output_tokens=settings.llm_max_output_tokens)
    report = {"status": "provisional_owner_review_pending",
              "created_at": datetime.now(timezone.utc).isoformat(),
              "model": settings.llm_model,
              "response_storage": False,
              "scope": "direct B6 prompt plus B7 gateway/output guard, synthetic cases; not browser/API latency",
              "cases": [], "summary": {}}
    for case, attempt in plan:
        context, prompt = prompt_for(case)
        row = {"case_id": case["id"], "group": case["group"], "mode": case["mode"],
               "attempt": attempt, "question": case["question"],
               "expected_facts": case.get("expected_facts", []),
               "teaching_constraints": case.get("teaching_constraints", []),
               "review_notes": case.get("review_notes"),
               "source_sheet": case.get("source_sheet") or (case.get("source") or {}).get("source_sheet"),
               "source_row": case.get("source_row") or (case.get("source") or {}).get("source_row"),
               "prompt_version": prompt.version, "profile_version": prompt.profile_version,
               "review": {"critical_facts": None, "topic_adherence": None,
                          "under_15_suitable": None, "language_quality": None, "notes": None}}
        started = perf_counter()
        try:
            generated = gateway.generate(prompt.messages)
            source = case.get("source") or case
            word_limit = profile(source["level"], source["level"]).max_words
            answer = _answer(uuid4(), context, generated, max_words=word_limit)
            row.update(status="ok", answer=answer["blocks"][0]["text"],
                       provenance={"route": answer["route"], "knowledge_source": answer["knowledge_source"],
                                   "grounded": answer["grounded"], "confidence": answer["confidence"],
                                   "citations": answer["citations"], "curriculum_version": answer["curriculum_version"]},
                       model=generated.model, input_tokens=generated.input_tokens,
                       output_tokens=generated.output_tokens,
                       word_count=len(generated.text.split()),
                       word_limit=profile((case.get("source") or case).get("level"),
                                          (case.get("source") or case).get("level")).max_words)
            row["over_word_limit"] = row["word_count"] > row["word_limit"]
        except GatewayError as exc:
            row.update(status="error", error_code=exc.code)
        row["latency_ms"] = round((perf_counter() - started) * 1000)
        report["cases"].append(row)
        report["summary"] = summary(report["cases"])
        write_report(args.output, report)
        print(f"{len(report['cases'])}/{len(plan)} {case['id']} #{attempt}: {row['status']}", flush=True)
    print(json.dumps(report["summary"], indent=2))


if __name__ == "__main__":
    main()
