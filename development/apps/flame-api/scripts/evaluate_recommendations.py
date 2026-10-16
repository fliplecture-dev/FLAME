"""Run from flame-api: python scripts/evaluate_recommendations.py --output <directory>."""
import argparse
import json
import statistics
import sys
from pathlib import Path
from time import perf_counter
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.modules.application.recommendations.evaluation import candidates, evaluate
from app.modules.application.recommendations.selection import learning_need, select_recommendations


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--samples", type=int, default=20)
    args = parser.parse_args()
    if args.samples < 5:
        parser.error("Use at least five samples.")
    args.output.mkdir(parents=True, exist_ok=True)
    results = evaluate()
    baseline = evaluate(omit_metadata=True)
    timings = []
    need = learning_need("Explain gravity", "")
    for count in (100, 1000, 5000):
        pool = [dict(candidates()[i % 6], id=f"candidate-{i}") for i in range(count)]
        select_recommendations(pool, need, "Explain gravity", "Gravity pulls objects down.", grade="Grade 1")
        samples = []
        for _ in range(args.samples):
            start = perf_counter()
            select_recommendations(pool, need, "Explain gravity", "Gravity pulls objects down.", grade="Grade 1")
            samples.append((perf_counter() - start) * 1000)
        timings.append(dict(candidate_count=count, samples=len(samples),
            p50_ms=round(statistics.median(samples), 3), p95_ms=round(sorted(samples)[int(.95 * (len(samples) - 1))], 3)))
    report = dict(scope="Synthetic offline ranking, not HTTP/database/LLM load testing or educator approval.",
        metadata_omitted_baseline=dict(passed=sum(r["passed"] for r in baseline), total=len(baseline), results=baseline),
        with_metadata=dict(passed=sum(r["passed"] for r in results), total=len(results), results=results),
        ranking_performance=timings)
    (args.output / "recommendation-evaluation.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    lines = ["# Recommendation educator review", "", "Synthetic cases. Educator review is pending; automated results do not establish teaching quality.", ""]
    for r in results:
        lines.extend([f"## {r['case']}", f"Question: {r['question']}", f"Answer: {r['answer']}",
            f"Expected: {r['expected']} · Selected: {r['actual']} · Mode: {r['mode']}",
            f"Reason: {r['reason']}", "Educator decision: pending", "Educator notes:", ""])
    (args.output / "educator-review.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"passed": sum(r["passed"] for r in results), "total": len(results), "ranking_performance": timings}))
    return 0 if all(r["passed"] for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
