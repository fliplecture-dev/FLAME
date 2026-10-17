# FLAME API

Current user-access refinement (2026-10-17): guest Curiosity is capped at 10 questions and signed-in students at 25, reset at midnight Asia/Kolkata. Optional phone and owned student contact/address profiles use migration 20261017_32 after 31; both are applied to the owner-confirmed development Supabase target, with clean schema drift and nine rollback-only PostgreSQL/grant checks passing. See the [access/profile contract and verification](../../../project-stages/USER-ACCESS-PROFILES.md). Future member/per-user tiers are not implemented.

FastAPI backend with B2 import services, B3 identity and protected B4 curriculum, My Learning, import and student-directory routes. See the [canonical documentation index](../../../project-stages/README.md) and [development tracker](../../../project-stages/STAGES-STEPS.md).

## Local setup (PowerShell)

For daily development, use `npm run dev` from `development/apps/web` (or `Start-FLAME.ps1` at the project root). It starts this API automatically on 8000 before the website starts and waits for database readiness. Use the manual Uvicorn command below only when intentionally managing the backend separately. Do not start a second API on 8001 to recover local sign-in.

`Start-FLAME.ps1` runs independently in the background so closing the update terminal does not close FLAME. Use `Start-FLAME.ps1 stop` and `Start-FLAME.ps1 status` for control; logs are under `work/dev-session.*.log`. `npm run dev` remains foreground and stops when its terminal closes.

Run from development/apps/flame-api:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e '.[test]'
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-access-log
```

An existing .venv can be reused. Configuration comes from FLAME_ environment variables or a local .env based on .env.example. No real secrets are committed. Use --no-access-log so Uvicorn does not duplicate structured application logs with raw request URLs.

GET /health/live returns 200 if the process is running. GET /health/ready checks PostgreSQL with SELECT 1; it returns 503 when no database is configured or connection fails. Local startup does not require PostgreSQL. Production configuration requires a PostgreSQL URL, but this skeleton is not a production-ready learning backend.

FLAME_DATABASE_URL accepts postgresql+psycopg://user:password@host:5432/database. Keep credentials in local environment/secret storage. No tables are automatically created and no migrations run at startup. B2.2–B2.5 introduced FLAME-owned Alembic migrations in the dedicated `flame` schema.

/docs and /openapi.json are available in development, disabled in production. Request logs contain generated IDs, method, matched route template, status and duration; not question bodies, raw query strings or database exceptions.

## Local media folders

This workspace uses `E:/FLAME/flame-resources` through the ignored backend `.env` setting `FLAME_RESOURCE_LOCAL_DIR`. The example config uses the relative equivalent `../../../flame-resources` when run from this API directory.

- `images/`: uploaded images, diagrams, GIFs and thumbnails.
- `media/`: uploaded video files and retained historical audio files.
- `interactive/`: uploaded or pasted HTML5 documents.

Files retain generated names. The database's logical `resource-uploads/<id>.<extension>` keys do not change; the local storage adapter resolves them into these folders. Existing flat `resource-uploads/` files under a configured root remain readable. Cloud storage keys are unchanged. Local preview, member delivery and bulk media export all use the same resolver. Files are private and served through authorized FLAME endpoints; copying an arbitrary file into a folder does not create a resource record. The root folder is excluded from Git. Existing old-root uploads were copied and hash-verified, then the three original files were removed at the owner's explicit request to complete the move.

## Database migrations

Use a configured `FLAME_DATABASE_URL` and run from this API directory. The migration role must be able to create and own the `flame` schema. Alembic reads the URL from the existing secret-backed settings; `alembic.ini` contains no credentials. The first online command creates the dedicated schema if needed. Migrations do not touch Supabase provider auth schemas.

```powershell
.\.venv\Scripts\python.exe -m alembic current
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m alembic check
```

The development database was migrated through `20260926_11` on 2026-09-26. The import service checks `admin_roles` and is mounted through protected B4 routes; catalogue and My Learning operations are also mounted. B3 identity routes, session storage and direct-access denial are applied in development. Live signup, email confirmation, sign-in, recovery/reset, admin bootstrap and session revocation were validated on 2026-09-26. A restricted runtime database role is required before production deployment. Do not run a downgrade against retained member data.

## Internal curriculum import

`app/modules/curriculum/workbook_parser.py` reads selected `.xlsx` sheets as text and validates the B2 import profile. `import_service.py` provides admin-checked upload, frozen preview, idempotent transactional commit, import history, paginated rows/errors, and a 30-day uploaded-file retention hook. A committed import retains history and source text after its raw workbook bytes are purged. B4 exposes this service through admin-only HTTP routes after B3 identity checks.

Migration 20260930_18 adds one private hierarchy snapshot per curriculum. Path-row saves and confirmed complete-replacement imports update that snapshot; published normalized rows remain member-visible until the explicit publish transaction applies the draft and writes one immutable revision. Admin .xlsx export supports draft, published and historical revision sources, with Metadata and hidden Stable IDs sheets for validated round trips.

The owner workbook parses as 1,726 rows, including five accepted duplicate paths. A full-workbook preview and commit were tested inside a rolled-back transaction; no curriculum content was permanently imported. The import migration was also applied from an empty temporary database and passed `alembic check`; that database was removed. The full commit took about two minutes against development Supabase, so an authenticated HTTP integration should run it as a background operation or allow for that duration.

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m pip check
```

Default tests cover foundation contracts and workbook parsing. Set `FLAME_RUN_DB_TESTS=1` to add rollback-only integration tests against the configured development PostgreSQL database. These cover import reuse, idempotency, stale/invalid preview rejection, path isolation, source text, wrong ancestry, multi-topic kits, and retention. No test curriculum records are left behind.

## Structure

- app/main.py: application factory, lifespan, request middleware, router registration.
- app/core: settings, database engine/session lifecycle, logging, errors.
- app/modules/functional: feature records, eligibility, delivery and lifecycle services.
- app/modules/decision_engine: pure recommendation, teaching and visual policy.
- app/modules/application: teaching, recommendation and learning-response coordination.
- app/contracts: shared typed data and the trusted mathematics registry.
- tests: policy, functional, integration and architecture/compatibility checks.

See the [module structure and dependency rules](app/modules/README.md) before adding a feature. Add new ORM declarations to `functional/model_registry.py`, used by both app startup and Alembic. Internal components such as the provider gateway do not need public endpoints. Package grouping does not change endpoint URLs or database tables.

Implementation references: [FastAPI lifespan](https://fastapi.tiangolo.com/advanced/events/), [FastAPI tests](https://fastapi.tiangolo.com/tutorial/testing/), [SQLAlchemy PostgreSQL adapter](https://docs.sqlalchemy.org/en/20/dialects/postgresql.html).

The current import contract requires a Subtopic on every curriculum row. Category remains optional stored ancestry for Study/LLM context and is hidden in student navigation. The existing development Supabase flame tables support this rule without a migration; B4 publication validation rejects Topics with no Subtopics. No workbook data has been permanently imported.

## B3 identity (local implementation)

The API now exposes BFF-key-guarded identity routes and GET /api/v1/me. See [B3 activation notes](../../../project-stages/backend/stage-3-auth.md) for Supabase verification templates, environment settings, admin bootstrap and B3 development completion evidence. Migrations 20260926_07 and 20260926_08 were applied to the development database after explicit owner approval and passed `alembic check`. Protected importer routes are mounted in B4.

## B4 curriculum and My Learning

The admin Curriculum Catalogue now supports revision-checked transactional path-row batches over the normalized hierarchy, a stored-workbook review/correction endpoint that reuses the existing parser, recoverable Archive/Restore, and permanent deletion after dependency review plus typed confirmation. Permanent deletion blocks resources, kits, learning memberships, teacher expertise and conversation history; import/revision history and hierarchy are removed in one transaction when deletion is allowed. The API logs a deletion event with the actor and curriculum ID.

B4 routes require a BFF key and a valid member/admin session. Published catalogue listing, stable-path search and trees exclude archived branches. Admin routes create and version curriculum nodes, validate publication, retain edit/archive revision details, expose workbook upload/preview/commit/history and provide paginated student search/profile data. My Learning stores exact Curriculum, Subject, Topic or Subtopic selections with server-validated ancestry. Hide/restore retains IDs and history. The development database has migrations through `20260926_11`; no curriculum was permanently imported.

Run `$env:FLAME_RUN_DB_TESTS='1'; .\.venv\Scripts\python.exe -m pytest -q` for rollback-only integration tests. The separate `FLAME_RUN_DB_CONCURRENCY_TESTS=1` check uses its own UUID fixtures and removes them after the two-worker test. A restricted runtime database role is still required before production deployment.

## B5 sessions and lifecycle (partial)

The B5 router exposes member-owned Study/Curiosity session creation, recent listing, paginated messages, deduplicated visit recording and an internal resource-open activity foundation, confirmed conversation deletion, confirmed FLAME-local account-data removal, and admin measured activity counts. Study sessions pin a validated seven-ID path, readable names and curriculum revision. The internal request service provides atomic claim/replay, a 90-second lease, two-attempt stale recovery and fencing-token finalization; B7 now connects it to a validated answer gateway and protected ask route. The development database is migrated through `20260927_15`.

Account deletion removes FLAME browser session tokens and private rows, scrubs local name/email, then hard-deletes the owned Supabase Auth identity using the server-only `FLAME_SUPABASE_SECRET_KEY` (or legacy `FLAME_SUPABASE_SERVICE_ROLE_KEY`). The local profile is inactive before the provider call. If Supabase fails, the route returns 202 pending_provider and scripts/retry_deletions.py retries the receipt. scripts/purge_deletion_receipts.py purges completed receipts and auth-subject tombstones after the configured window (30 days by default); schedule it in operations. A disposable development Supabase Auth user was created and removed through FLAME on 2026-09-26; the route returned deleted and an admin lookup returned 404. Provider timeout/retry remains mock-tested. In a development project, `python -m scripts.verify_live_deletion --execute` repeats the disposable-account check; it creates and deletes one Auth user and leaves the minimal completed receipt for the normal purge job. The owner chose a 30-day maximum for backup and operational-log copies; primary private rows are removed immediately. Verify Supabase plan retention and any exported backups/log drains before release. The local receipt window can be changed with `FLAME_DELETION_RECEIPT_RETENTION_DAYS`; change the backup/log policy and infrastructure configuration together.







## B6 teaching context (completed in development)

Teaching services validate the current published school path and pinned Study revision, load optional curriculum metadata, select an explicit KG–5 Study profile and assemble versioned bounded prompts from owned complete-pair B5 history. Open Curiosity uses a general under-15 prompt across subjects and languages without curriculum lookup. Migrations `20260926_13` and `_14` persist owned pending clarification and idempotent topic-check events with resolved path snapshots. Historical authenticated topic-check, clarification and paginated topic-check history routes remain mounted; the current Curiosity answer flow and saved-session dialog do not use this gate. Five draft teaching cases are tied to exact rows in the supplied workbook; educator review remains for B8. B7 saves Study turns with validated resolved IDs and open Curiosity turns with null curriculum/subject/topic through the protected ask endpoint. Live `gpt-6-luna` Study and Curiosity answer/replay checks passed. See [B6 handoff](../../../project-stages/backend/stage-6-context.md).
## B7 direct answer gateway (completed in development)

`POST /api/v1/sessions/{id}/ask` requires an authenticated member, an `Idempotency-Key`, text question, mode and exact Study context. Curiosity requires null context and no `topic_check_id`; it accepts general learning questions. The gateway uses the OpenAI Responses API with `store=false`, no tools, a bounded output cap and at most one transport/rate retry. It requires both `FLAME_LLM_OPENAI_API_KEY` and `FLAME_LLM_MODEL` server-side; both are now configured in development. `FLAME_LLM_DAILY_REQUEST_LIMIT` (25 per signed-in student per India calendar day; 10 for guest Curiosity), `FLAME_LLM_TIMEOUT_SECONDS` (12) and `FLAME_LLM_MAX_OUTPUT_TOKENS` (1,500 per answer) are documented in `.env.example` and can be overridden in the local API `.env`. Do not put the key in the BFF or browser. The member daily request cap is a development safeguard; `gpt-6-luna` is the only project-allowed model; the owner reports a USD $5/month project hard spend limit. See [B7 handoff](../../../project-stages/backend/stage-7-answer-service.md) for the local key template, model choice, spending controls and live verification steps.

The `20260927_15` revision stores prompt/profile/model version, usage and latency without storing another prompt copy. The provider runs outside database transactions. Complete responses are persisted once and replay under the same key; terminal failures replay their safe code and a new logical attempt needs a new key. Study/Curiosity stub and browser retry checks passed. A direct live gateway call and rollback-only owned Study and open Curiosity API answer/replay passed; the owner reports a USD $5/month hard spend limit. Live deadline, interrupted-worker recovery and signed-in Study/Curiosity continuation passed on 2026-10-14. Hosted termination/load and educator quality acceptance remain B10/B8. Successful and saved answers expose optional owner-scoped request references.

## B8 capability handling (partial)

`POST /api/v1/sessions/{id}/capability-check` is an authenticated, owned, deterministic preflight for Curiosity before its open answer. Explicit requests for textbook-page evidence, official grading, student-file/image or video/audio understanding, transcription and progress updates return `status=unsupported` with a stable code and explanation. The ask route stores that outcome under its idempotency key without a model call. Ordinary Curiosity questions continue directly to the open answer prompt; Study retains published-path validation. Complete answer blocks are bounded and reject duplicate IDs or control characters. These are narrow checks, not a factual-quality guarantee. The draft review cases and rubric are in `project-stages/backend/stage-8-evaluation.md`. A Study-only live baseline and founder scoring packet are in `project-stages/backend/stage-8-study-review-2026-09-28.md`; factual and age-suitability acceptance remains open. Run `.\.venv\Scripts\python.exe -m scripts.evaluate_b8` to list the synthetic case count, or add `--execute` for controlled paid calls. The runner writes synthetic answers and usage to `work/b8-live-baseline.json` from the workspace root and never writes credentials. Curiosity remains open and unchanged.

## B9.2 resource drafts (development)

Admin-only POST /api/v1/admin/resources/uploads accepts one multipart file and returns an owned upload ID, MIME type, size and media type. POST /api/v1/admin/resources creates an unpublished draft with either that upload ID or an approved HTTPS external URL, resource metadata/rights fields, and optional Topic/Subtopic associations. The admin UI creates media-only drafts; associations are managed separately. An upload ID can be consumed once by the admin who uploaded it. These routes do not publish or serve resources.

The approved policy is in project-stages/backend/stage-9-resource-policy.md. Local development uses FLAME_RESOURCE_LOCAL_DIR, which must stay outside public web assets. Production requires FLAME_RESOURCE_STORAGE_BACKEND=supabase and FLAME_RESOURCE_STORAGE_BUCKET naming a private bucket, plus a server-only Supabase secret key. FLAME_RESOURCE_ALLOWED_HOSTS is a comma-separated exact hostname list and defaults to empty, disabling external links. The deployed private bucket and large-upload behavior require live verification before publication. Run the rollback-only B9 test with FLAME_RUN_DB_TESTS=1 and pytest tests/test_b9_resources.py.

## B9 catalogues (development)

Migrations `20260928_16` and `_17` add private upload staging, resource publication metadata and retry-stable recommendations. Admin routes manage versioned resources, teachers and multi-topic kits; member routes provide exact published resource lookup, five-minute delivery URLs, duplicate-safe open/play events and answered Study recommendations. Curiosity has no subject-derived teacher cards. Set `FLAME_RESOURCE_STORAGE_BACKEND=supabase` plus a private bucket and credentials for deployment; local storage is development only. External host allowlist defaults to empty. No example asset has been published. Run `FLAME_RUN_DB_TESTS=1` with `pytest tests/test_b9_resources.py tests/test_b9_catalogues.py` for rollback-only checks. See [policy](../../../project-stages/backend/stage-9-resource-policy.md).


## Resource mapping and retained deletion (2026-10-03)
Media publication validates availability, rights, accessibility and storage independently of placement. Unmapped resources may be published; member lookup/delivery still require at least one valid mapping in a published curriculum.

Association-only `PATCH /api/v1/admin/resources/{id}` accepts `expected_version` and `paths`, including an empty list. It validates current IDs, replaces associations atomically, increments the server version and preserves publication. Published mapping changes take effect on new member lookups immediately. Metadata editing retains the existing separate unpublish/edit/publish UI flow.

Admin `GET /api/v1/admin/resources/{id}/delete-preview` reviews current mappings and dependencies. `POST /api/v1/admin/resources/{id}/delete` requires `expected_version` and matching `confirm_resource_id`. It retains a deletion record, publication is removed, associations are deleted atomically, and the resource is excluded from catalogue/preview/member delivery/recommendation access. Upload ownership, media bytes, shared kit assets, activity records and conversation history remain intact. There is no admin restore or automated storage-purge operation. Private cloud URLs already issued retain the existing expiry window.

Migration `20261003_23` adds retained deletion metadata. Regression coverage: `FLAME_RUN_DB_TESTS=1 pytest tests/test_resource_mapping_deletion.py` (rollback-only).

## External video catalogue and standard playback (2026-10-03)

Migration `20261003_24` stores external-video metadata. `type=external_video` accepts validated HTTPS YouTube/Vimeo URLs through explicit adapters, never uploads or arbitrary iframe HTML. Other providers are unsupported. `POST /api/v1/admin/resources/external-video/inspect` returns normalized provider/video identity, title/description/thumbnail and verification state from bounded, fixed HTTPS oEmbed requests without redirects. Provider HTML is discarded.

The owner's later instruction removes the API-key publication checkpoint and relaxes strict navigation-free playback. No YouTube Data API key or Vimeo API token is required or consulted. Publication rechecks public metadata, rights, accessibility and availability; oEmbed metadata is not a guarantee of embedding or all provider privacy settings. Provider errors are handled inside the player.

Admin preview and authorized published/mapped learner delivery return standard allowlisted embed URLs. FLAME offers Play/Pause, fullscreen/exit and close. Provider links and branding may navigate externally, as accepted by the owner. FLAME adds no external-site fallback. Learner authorization, valid published curriculum mappings, publication status and version checks remain enforced. Legacy provider links misclassified as uploaded video/interactive do not bypass validation. Existing mapping/unmapping while published and retained deletion remain available.

Tests: `FLAME_RUN_DB_TESTS=1 pytest tests/test_external_video.py`. HTTP provider and SDK calls use fixtures in regression tests. Live availability and actual provider player behavior still depend on each video/provider. See [current policy](../../../project-stages/backend/stage-9-resource-policy.md).

## MVP learning recommendations (2026-10-03)

New Study answer prompts append a bounded intent/concept/language tag in the existing answer call. It is removed before rendering and stored only as validated metadata in the existing answer-request result. No extra model request, quota bypass or candidate-ID authority is introduced. Missing/malformed or unrelated intent falls back to conservative rules.

`GET /api/v1/sessions/{id}/recommendations?message_id=...` retains owned-session and current published path/revision checks. New decisions persist within `RecommendationSet.image_decision.recommendation_decision`, alongside the compatible image decision. One primary and at most one different useful-format alternative are validated against published/available mapped resources, complete published kits and published expertise-matched tutors. IDs, versions and acknowledged displays survive reopening. Earlier saved decisions are not reselected.

`POST /api/v1/sessions/{id}/recommendations/displayed` acknowledges rendered optional cards with message ID, candidate ID and version. Inline images retain `images/displayed`. `GET /api/v1/sessions/{id}/recommendations/{candidate_id}?message_id=...` rechecks the original selection, ownership, path, publication and version before opening a resource, activity guide or tutor profile. Existing resource delivery rechecks media eligibility. Kit guides do not execute activities or provide checkout; tutor profiles do not contact/book anyone. Unknown tutor availability is labelled unknown and listed schedules are not live-verified.

No migration is required. Tests and remaining metadata gaps are documented in `work/mvp-learning-recommendations.md` at the workspace root.

## B11 modular migration (2026-10-07)

Recommendation coordination, selection/history contracts, repository and the existing table mapping now belong to `app/modules/recommendations/`. Media/Teachers/Kits own typed candidate services. Legacy resource-module imports remain transitional aliases. `learning_response/` adds a schema-versioned envelope to existing ask/recommendation responses without removing root fields or running selection before the answer completes. New Study asks return pending selection; a separate GET returns completed/none/unavailable. Authorization failures retain their HTTP status; selection failure does not erase the answer. No extra model request or database migration. Conversation/account deletion clears recommendation-owned rows before their foreign keys. See [B11 technical handoff](../../../project-stages/backend/stage-11-modular-migration.md).

## Functional modules and decision engine (2026-10-16)

`app/modules/decision_engine/{recommendation,teaching,visual}` owns pure policy functions; `app/contracts/decisions.py` supplies their typed inputs/results. The shared trusted template registry is packaged under `app/contracts/math_templates.json`. `modules/functional` retains records, permissions, publication, candidate eligibility and delivery. `modules/application` coordinates providers, quotas, transactions and response composition; saved recommendation choices belong to `functional/recommendation_history`. Canonical Python imports now include the layer; old flat feature paths are retired internal imports, and all repository callers are migrated. Existing policy helper names within the application packages still re-export the engine implementation. Public HTTP/OpenAPI contracts, persisted decisions and all 34 table declarations are unchanged. The full pytest suite includes infrastructure-free policy and layer-boundary checks. Configured-database verification/final cutover acceptance is still pending; see [B15 handoff](../../../project-stages/backend/stage-15-decision-separation.md).

## Manual Google Sheets resource sync

Set FLAME_GOOGLE_SHEETS_CREDENTIALS_FILE to a server-only Google service-account JSON file, enable Sheets API, and share the intended spreadsheet as Editor with that account. Resource Library → Sync Google Sheets provides the three-tab template, preview/confirm and identifier retry. Mapping remains in FLAME. Setup, limits and tests: ../../../project-stages/GOOGLE-SHEETS-RESOURCE-SYNC.md. No schema migration is needed.

## Vercel MVP preparation — 2026-10-14

Admin private transfers use GET `/api/v1/admin/transfers/configuration` and POST `authorize`, `complete`, `export`. Authorization accepts purpose, target, filename, MIME type, declared size and SHA-256. File bytes go directly to signed private storage; only the encrypted owner-bound ticket crosses the BFF for confirmation. Existing resource, curriculum and bulk validators remain authoritative; stable server-generated IDs support receipt replay. Curriculum bytes and bulk previews remain durable in PostgreSQL. Exports return five-minute private URLs. API/BFF duration ceilings are 300 seconds; hosted size/plan limits and full-size load acceptance remain open.

Use `python -m scripts.purge_transfer_artifacts` to inspect expired staging/export candidate counts; `--execute` removes only generated objects older than 24 hours. Schedule it separately from bulk-preview and deletion maintenance. It excludes catalogue assets and does not reclaim orphan final uploads. Opt-in cloud verification uses `FLAME_RUN_DB_TESTS=1` and `FLAME_RUN_STORAGE_TESTS=1` with `tests/test_direct_uploads.py`; it rolls back fixtures and removes its own files.

Use this exact project Root Directory: development/apps/flame-api. pyproject.toml selects app.main:app through tool.vercel. Production requires durable Supabase storage and the existing identity/database settings; local launcher commands are not deployment start commands. For the saved Sheets connector on Vercel, set server-only FLAME_GOOGLE_SHEETS_CREDENTIALS_JSON to the service-account JSON; the local credential file path remains supported. See ../../../project-stages/VERCEL-DEPLOYMENT.md for setup and outstanding hosted acceptance. The private flame-resources development bucket has been provisioned and synthetic upload/read/signing verified; local resource files and backend storage selection remain unchanged.
