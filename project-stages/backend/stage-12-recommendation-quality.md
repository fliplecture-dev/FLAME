# B12 — Recommendation metadata, evaluation and performance

Implemented in development on 2026-10-07. This is the bounded improvement cycle requested after B11. Educator acceptance remains B8 work; this handoff does not close release gates.

## What changed

1. **Metadata:** Resources, Teachers and Activity Kits own optional `learning_metadata`: concepts, alternative terms, grade range (0 = KG), language codes and teaching purposes. Admin editors reuse one component. The server validates ranges, term limits and language codes. These fields are entered manually; no extra LLM call or automatic suitability/rights claims. Existing rows retain their content and receive an empty metadata object.
2. **Evaluation:** An offline command produces twelve representative selection cases, expected/actual decisions and an educator review packet. Automated checks and educator decisions are separate. Cases cover force/gravity, synonyms, demonstration, practice, human help, unrelated content, repetition, explicit repeat, grade/language mismatch and unavailable candidates. Existing integration tests cover publication/access, failure isolation and reopening history.
3. **Targeted ranking fixes:** Rank specific concepts/alternative terms alongside existing descriptions. Structured grade ranges take precedence over inferred title grades. Language matching accepts regional codes such as `en-in`. Teaching purposes and explicit concepts add small ranking boosts; they do not override eligibility or the required concept match. Topic mapping continues to supply candidates rather than force display. Existing decisions attached to previous answers are preserved.
4. **Performance:** Request logs expose retrieval, ranking and total recommendation timings and counts without storing the question/answer. Tutor expertise is fetched in one batch after catalogue retrieval. A rollback-only eight-tutor fixture measures nine SELECTs for the previous query pattern and two for the batched pattern. Ranking reuses answer terms within a request; the two benchmark runs do not establish a consistent speed gain.

## Contracts and operational behavior

- All three create/edit APIs accept `learning_metadata`; omitted PATCH fields preserve metadata, `{}` clears optional metadata, and `null` is rejected. Existing authorization, version checks and atomic transactions apply.
- Mapping, media references, file replacement, publication and availability rules are unchanged. Resource metadata editing still requires unpublishing, because the catalogue stores one resource version. Save does not publish.
- Applying migration `20261007_25` adds three JSONB columns/checks with empty defaults. It is applied to the configured development database; `alembic check` reports no drift.
- API restarted on localhost:8000. No deployment, paid provider calls, permanent fixture publication or edits to existing catalogue metadata were performed.
- Rollback: restore previous application code while retaining additive columns. Do not drop metadata columns after administrators start using them; dropping them loses their entered metadata.

## Repeatable checks

From `development/apps/flame-api`:

```powershell
.\.venv\Scripts\python.exe scripts/evaluate_recommendations.py --output ../../../work/recommendation-quality
$env:FLAME_RUN_DB_TESTS='1'
.\.venv\Scripts\python.exe -m pytest tests/test_recommendation_metadata.py tests/test_mvp_recommendations.py tests/test_b11_modularity.py tests/test_b9_catalogues.py tests/test_conversation_images.py tests/test_resource_mapping_deletion.py -q --tb=short
.\.venv\Scripts\python.exe -m alembic check
```

From `development/apps/web`: `npm run test:unit`, `npm run build`, `node tests/resource-library-browser.cjs`.

## Recorded verification

- 20 affected backend tests pass, including metadata validation/persistence, preserved media/mappings, stale-version rejection, typed candidate use and batched query counts. Fixtures roll back.
- 17 frontend unit tests and production build/typecheck pass.
- Resource Library browser suite passes: entered metadata saves/reopens; existing creation, retries, mapping/deletion, GIF, external video and uploaded playback flows remain working. Desktop metadata screenshot reviewed; compact purpose checkboxes corrected after visual review. The metadata editor also fits the 390px viewport; desktop and narrow screenshots reviewed. Narrow mapping/player flows remain verified by the same suite.
- Twelve offline cases pass. Omitting structured metadata on the same ranker/fixtures passes ten: this is a metadata ablation, not a historical production quality baseline.
- Twenty synthetic ranking samples per size: p50/p95 in milliseconds = 2.539/2.757 (100 candidates), 26.822/29.565 (1,000), 131.837/134.682 (5,000). These are local ranking measurements, not HTTP/database/LLM load results or a response-time guarantee.
- Artifacts: `work/recommendation-quality/recommendation-evaluation.json`, `ranking-before-token-reuse.json`, `tutor-query-check.json`, `educator-review.md`; desktop capture `work/recommendation-metadata-editor.png`.

## Changed source groups

- `app/contracts/{learning_metadata,catalogue}.py`.
- `app/modules/{resources,teachers,activity_kits}/models.py`, their routers and candidate adapters; resource serialization in `resources/service.py`.
- `app/modules/recommendations/{selection,service,evaluation}.py`.
- `migrations/versions/20261007_25_learning_metadata.py`.
- `scripts/evaluate_recommendations.py`, `tests/test_recommendation_metadata.py`.
- Web `learning-metadata-editor.tsx`, `resource-panel.tsx`, `b9-admin.tsx`, `admin.css` and Resource Library browser test.

## Remaining work

- Administrators must supply/review accurate metadata on real catalogue entries; this task does not infer or backfill it.
- Educator review packet is pending. Use reviewed failures to add cases and adjust ranking narrowly; do not equate twelve synthetic checks with accepted teaching quality.
- Production HTTP concurrency, storage/network latency and paid-model response-time evaluation remain release work. Kit path/storage checks can still incur per-kit work; this task only fixes the confirmed tutor N+1 pattern.
- Full conversational/age/progress personalization, embeddings, tutor booking and a separate recommendation platform remain deferred.
