# B11 modular migration: technical handoff

Date: 7 October 2026. Progress and acceptance statuses belong to [STAGES-STEPS.md](../STAGES-STEPS.md). One FastAPI application, one PostgreSQL database; no deployment, provider call or data migration is part of this refactor.

## Baseline audit

Reviewed the entire tracker: B5 lifecycle operations, B7 live failure/continuation checks, B8 educator evaluation, B9.11 live storage/assets and B10 release remain open. Existing source mixed recommendation HTTP orchestration, catalogue ORM access, image/intent selection and recommendation persistence under `resources/`. Teaching imported resource-owned intent helpers; kits exposed publication checks through their admin router. Media deletion queried recommendation ORM directly. Conversation deletion did not remove recommendation rows before deleting messages, so existing RESTRICT foreign keys blocked deletion once recommendations existed.

Before migration: the original 42 targeted recommendation/answer tests passed; adding the mapping/deletion test exposed an obsolete GIF-inline assertion (42 passed, one failed). The old fixture now checks the current optional animation card. Frontend baseline: 14 unit tests and build passed. The learner browser baseline exposed a short generated video fixture race; fixtures now capture attached canvases with explicit VP8 and controlled looping. A wider B4 mock omitted the second level from its whole-curriculum tree; the fixture now reflects the complete catalogue. These are test corrections, not changes to media selection, video looping or curriculum behavior in the product.

## Final ownership and dependency direction

| Owner | Public interface / implementation |
| --- | --- |
| Shared data contract | `app/contracts/catalogue.py`: typed CatalogueCandidate and availability classification, no ORM/router dependencies. |
| Curriculum | `curriculum/public_paths.py`: validated ancestry/revision and readable grade/topic/objective. Old resources.path_info remains an alias. |
| Conversations | `conversations/recommendation_context.py`: owned answer/context, bounded preceding questions, ordered earlier answer IDs and optional inferred intent. Returns a snapshot, not ORM entities. |
| Media | `resources/candidates.py`: publication/mapping/source/storage eligibility and safe media cards. Existing upload/map/publish/delivery/player APIs remain authoritative. |
| Teachers | `teachers/candidates.py`: published expertise/languages, unavailable exclusion and accurate unknown/listed availability. No scheduling/contact. |
| Activity Kits | `activity_kits/service.py` owns publication requirements; `candidates.py` supplies available eligible guides/materials/supervision. No execution/checkout or invented prerequisite checks. |
| Recommendations | `recommendations/{learning_need,selection,image_selection,contracts,service,repository,models,router}.py`: intent fallback, ranking, schema-1/schema-2 decisions, acknowledgements and persisted repetition history. |
| Learning response | `learning_response/{contracts,composer,service}.py`: additive response envelopes and isolated failure states; reuses teaching's ask service without running recommendations on the answer path. |
| Teaching | Existing profiles/context/provider/quota/claim/replay and complete answer persistence. Optional intent stays in the same model call, now imported from recommendations. |

Recommendation coordination imports public catalogue/context services and its own repository; it does not import foreign ORM models or admin routers. Candidate IDs/versions are checked against the returned eligible DTOs before storing a new choice. The catalogue services own safety/eligibility; selection owns relevance; the composer owns assembly. Router registration occurs once at the original URLs.

## Persistence and compatibility

`RecommendationSet` now belongs to `recommendations/models.py`, mapping exactly the existing `flame.recommendation_sets` table. `resources/models.py` retains the same class alias; no duplicate table registration, schema change or JSON backfill. Schema-1 image decisions and schema-2 general decisions stay readable and are not silently reranked. New selected IDs/versions retain their meaning. Resource deletion dependency counts go through the recommendation repository. Confirmed conversation/account deletion removes owned recommendation rows before their message/session foreign keys.

Legacy resource selection/intent/image/router import paths remain transitional adapters. Existing application wiring uses the new owners. Keep these adapters through B10 integration and remove them only after auditing callers; no removal deadline is invented. Internal legacy catalogue helper consumers should migrate to the typed public candidate services.

## Composer contract

Existing endpoints and root fields remain valid. The extra `learning_response` object is additive:

```json
{
  "schema_version": 1,
  "message_id": "<owned-answer-UUID>",
  "request_id": "<answer-request-UUID-or-null>",
  "answer": {"status": "completed", "blocks": []},
  "recommendations": {"status": "pending", "data": null, "code": null}
}
```

This is an illustrative envelope; placeholders are not executable IDs. The actual answer retains its validated blocks, provenance, request/message IDs and existing status at the response root.

- `POST /api/v1/sessions/{id}/ask`: teaching executes once under existing quota/idempotency rules. A completed Study answer returns recommendations=pending; Curiosity/unsupported outcomes return none. No recommendation loader or extra model call runs here.
- `GET /api/v1/sessions/{id}/recommendations?message_id=...`: existing resource/teacher/kit/image/general-decision fields remain at root. The envelope has answer=null and recommendation status completed or none; data contains the legacy recommendation payload without a recursive envelope.
- Unexpected selection/storage failure returns recommendation status unavailable with a safe code; exceptions do not rewrite the completed answer or commit half a selection. TimeoutError uses recommendation_timeout. Ownership/context/version HTTP failures retain their existing status codes.
- Opening and display acknowledgement URLs remain unchanged and continue rechecking ownership, paths, publication and versions. No new public endpoint or worker/queue was added.

The frontend adapter accepts both legacy and composed responses, rejects mismatched message IDs, distinguishes none/pending/unavailable, and keeps errors alongside the explanation. Its existing stale-response guards, viewers, compact cards and position preservation remain. Pending selection is a separate request, so a slow catalogue lookup does not hold the current explanation response. Existing BFF request deadlines still bound upstream requests; no new timeout executor was introduced.

## Regression coverage and remaining gates

Final verification: 53 targeted backend tests passed (two existing Starlette/AnyIO deprecation warnings); 17 frontend unit tests and production build passed. Learner recommendation/GIF/native/external video, Resource Library creation/mapping/publication/deletion and sidebar history/pin/reload/narrow-screen browser scripts passed. Alembic check reported no new upgrade operations. These are targeted gates, not a passing claim for the entire backend/browser suite.

The wider `tests/b4-browser.cjs` harness still expects the removed Saved Conversations sidebar and stops at Start Curiosity session. Its earlier whole-curriculum mock was corrected to include both levels; the obsolete sidebar journey remains a B10 test-harness modernization item. Current Curiosity/history interfaces are separately covered by API and sidebar tests; no removed UI was restored just to satisfy that historical script. Existing F8/F9/B10 signed-in/full-flow acceptance remains open. Added tests verify one table/router owner, legacy import aliases, public-service dependencies, same-call teaching composition, replay/quotas, sanitized selection failure, none versus unavailable, schema-1 read without mutation, new envelope rendering, mismatched message IDs, and owned recommendation cleanup during conversation deletion. Existing representative journeys cover force/gravity, kits/tutors, repeat/reference history, publication/versions/access, admin mappings/deletion and GIF/external/native players.

No paid OpenAI call or real student mutation was needed; model/provider/browser tests use fixtures and DB integration rolls back. Physical-device/screen-reader/live-bucket/licensing and educator acceptance remain with B8/B9.11/B10. Source/module completion must not close these gates.

## Cutover and rollback

Local cutover: verify tests/build/schema parity, then restart the existing API so main.py registers the new router and composer. Existing URLs/table data need no conversion; browser refresh picks up the additive client adapter.

A source-only pre-migration snapshot is at `work/b11-baseline-source.zip`; it excludes credentials and runtime data. It contains the previous main/router/model/selection/teaching/conversation/migration wiring and three affected frontend files. The kit publication extraction preserves its callable import, so reverting the previous registered wiring does not require changing kit data or dropping tables.

Rollback procedure: stop the API, preserve subsequent edits and current source separately, restore only the snapshot's reviewed paths inside E:/FLAME, rebuild the frontend, verify old endpoints and restart. Do not reset the whole dirty working tree, restore a database backup, downgrade migrations or delete media. Newly added inactive modules can remain during rollback; old registered paths/owned models must be restored together to avoid duplicate model registration. If later work starts importing the new owner directly, audit those callers before restoring old wiring.

Rollback compatibility is covered by alias/table identity and legacy-response/decision tests. A production rollback drill was not performed; no production deployment occurred. The snapshot is not a reproducible Git release: commit the reviewed complete checkout and provision secrets/media/backups separately before release.
