## Current pending-stage delivery and MVP hosting — 2026-10-14

B7 is complete in development after live deadline, signed-in Study/Curiosity reload/follow-up and interrupted-worker recovery verification. Connected B5.3/B5.5/B5.9 and F2.4/F5.4 are complete; generated and restored answers now carry optional server request references. No schema migration was added. The canonical tracker owns counts, detailed evidence and remaining gates: [October 14 delivery](STAGES-STEPS.md#pending-stage-delivery--2026-10-14).

Owner selected two Vercel MVP projects: website root development/apps/web and API root development/apps/flame-api. Explicit FastAPI entry point app.main:app is configured in pyproject.toml. Google Sheets accepts server-only FLAME_GOOGLE_SHEETS_CREDENTIALS_JSON, preferred over the local file path. Admin media/workbook/ZIP uploads and exports now use private-storage transfers when Supabase storage is enabled; only metadata/receipts cross Functions. Owner-bound encrypted tickets, size/SHA verification and stable resource/import/preview IDs support retries. Curriculum workbook bytes and bulk previews already persist in PostgreSQL. Synthetic cloud upload above 4.5 MB, replay, retrieval and private export passed; probe files were removed and DB fixtures rolled back. Expired staging/export cleanup has a dry-run command; actual scheduling and final-upload orphan cleanup remain operations work. Local storage remains active and real catalogue media has not been copied to the private flame-resources bucket. Actual Vercel environments/secrets/runtime role, maximum-size provider/load checks, retention/restoration, supported devices and owner quality/pilot acceptance remain open. Read [Vercel preparation](VERCEL-DEPLOYMENT.md).

Earlier dated snapshots below are historical wherever superseded by this section or the tracker. API 8000 / web 3000 remain canonical locally. GitHub Actions checks were prepared but have not run remotely.

Resumed verification also completed F8.5 production fixture/progress/unsupported-attachment checks and started B10.1–B10.4 integration/pilot verification. Default backend checks, all 72 admin-operation member denials, 36 rollback-only affected tests, 27 frontend units, TypeScript/build and three production-browser suites passed. Current counts and open gates are in the [resumed tracker entry](STAGES-STEPS.md#resumed-private-transfer-and-pilot-verification--2026-10-14).

## Current connector and local startup — 2026-10-12

Current applied migration head is `20261012_30`. B13 now includes a saved administrator-owned Google Sheets connection over Image/Video/Interactive tabs, reviewed resource exports and additive imports, stable automatic identifiers, separately confirmed linked-row deletions and retryable pending write-back. Existing nonempty FLAME values remain authoritative; mappings/assets/HTML remain in FLAME. Native numeric/boolean cell output and unchanged saved-video source retention fixes are implemented. Invalid previews can be refreshed with Validate again. Sync remains manual; latest live read/comparison passed, but no latest live write was performed during verification. See [current tracker summary](STAGES-STEPS.md#latest-resource-and-google-sheets-upgrades--2026-10-12) and [connector guide](GOOGLE-SHEETS-CONNECTOR.md).

Local startup now uses `Start-FLAME.ps1` for a detached session, with explicit stop/status actions and a Windows background reload wrapper. API 8000 / web 3000 supersede earlier port-8001 routing notes below. Actual worker reload, API/database readiness and sign-in HTTP 200 were verified. Existing stage totals/release gates are unchanged.

## Video thumbnail update — 2026-10-09

Browse Media thumbnails are clickable scoped open buttons. YouTube thumbnails load from safe provider metadata; private uploaded Video thumbnail images are managed in Resource Library and mandatory before MP4/WebM publication. Native learner playback uses the thumbnail poster. Migration `20261009_28` applied; no existing resource/media/mapping/publication backfill. See [thumbnail handoff](backend/stage-9-video-thumbnails.md); cloud/device/release gates remain open.

# FLAME — AI agent entry point

## Interactive HTML5 update — 2026-10-09

Live upload follow-up: Gravity Lab — Interactive is saved as an available Grade 1/en HTML5 draft, version 2, with the Grade 1 Gravity topic-wide mapping and eight direct subtopic mappings. Stored preview completes a 10 m fall. It remains unpublished because the owner requested upload/mapping. The non-reloading API on 8000 still had old HTML validation; current reload API is now 127.0.0.1:8001 and the ignored frontend FLAME_API_URL points there. Use that current routing; this supersedes the earlier port-8000 handoff. Existing Image/Video entries were not edited. See latest tracker evidence.

Owner requested Interactive-only HTML/HTML5 support. Admins can upload a bounded, self-contained UTF-8 HTML file as existing private uploaded media; authorized JSON delivery feeds an opaque-origin sandboxed viewer used by Preview/Explore/recommendations. No Image/Video type/player/policy or schema change. Existing external Interactive links retain separate-page delivery. Read [Interactive HTML5 handoff](backend/stage-9-interactive-html5.md) for authoring limits, security boundary, prepared Canva Gravity Lab and verification. The older no-HTML-upload rule below is superseded for this admin Interactive workflow only; arbitrary model response HTML remains excluded. Existing live-content/storage/device/educator release gates remain.

Updated: 2026-10-08. Workspace: E:/FLAME; Windows PowerShell.
Read this file first, then only the relevant canonical specification. Do not duplicate progress tables or schema definitions here.

## Current module update — 2026-10-07

B11 separates recommendation intent/ranking/history/router/model ownership into `app/modules/recommendations/`; Media remains `resources/`, with Teachers and Activity Kits supplying their own candidate DTO interfaces. `app/modules/learning_response/` composes additive envelopes over existing split endpoints; no extra model call or schema migration. Old import paths/JSON remain compatible. Read [B11 handoff](backend/stage-11-modular-migration.md), [development orientation](DEVELOPMENT-HANDOFF.md) and the canonical tracker for current evidence. Earlier implementation snapshots below are historical; they do not supersede these current boundaries or the October MVP selection rules. Existing B5/B7/B8/B9.11/B10 release/quality gates remain open.

## Recommendation quality update — 2026-10-07

B12 adds manually reviewed optional teaching metadata to Media, Teachers and Kits, shared admin fields, twelve offline selection cases and an educator review packet. Ranking uses explicit concepts/alternative terms, grade ranges, regional language codes and purpose boosts while preserving eligibility and saved decisions. Tutor retrieval uses two SELECT queries rather than per-tutor expertise queries. Development migration `20261007_25` is applied. Read [B12 handoff](backend/stage-12-recommendation-quality.md) for measured performance and verification; educator and production-load acceptance remain open.

## Bulk catalogue transfer update — 2026-10-07

B13 adds `app/modules/bulk_transfer/` as an admin import/export coordinator over existing catalogue validation/storage rules. Durable owner-scoped previews, atomic additive merges, receipts, exports, live templates and sample packages are integrated into Media, Teachers, Students and Kits. Migration `20261007_26` is applied. Student imports create pending profiles; only a matching confirmed provider identity can activate one. No auth accounts, invitations, role grants or auto-publications are imported. Read [B13 handoff](backend/stage-13-bulk-transfer.md) and [sample folder instructions](bulk-import-samples/README.md) for merge rules, operational cleanup/limits and verification. Existing release and quality gates remain open.

## Learner Explore development update — 2026-10-08

F10/B14 are complete in development. The learner header CTA and answer/recommendation links open a responsive Media/Teachers/Activity Kits panel with independent published-path browsing, search/filter/pagination, authorized static thumbnails and existing viewers. Member browse/context/open routes reuse catalogue eligibility and recheck path/revision/version on open/scoped delivery; no extra LLM call or recommendation-history writes. Curriculum supplies a single read-only ancestry query; explicit suitability is a pure shared contract helper. Browse state stays separate from Study context. Read [F10/B14 handoff](backend/stage-14-learner-explore.md) for contracts, files, DB/browser/performance evidence and limits. Automatic approval review blocked stopping the running local API; it was left running and must be restarted manually. No migration/deployment/data backfill. Existing B5/B7/B8/B9.11/B10 and physical-device/live-content gates remain open.

## Reference design / media classification update — 2026-10-08

The owner requested the reference-style learner redesign and three active media families: Image, Video, Interactive. Diagrams normalize to Image; GIF/animations and provider videos normalize to Video, with MIME/source metadata retaining playback distinctions. Audio is excluded from active creation/browse/export; existing historical data is retained. Migration `20261008_27` is applied; IDs, mappings, media and publication preserved for the ten provider videos and two images. Read [design/taxonomy handoff](backend/stage-14-reference-design-media-families.md). The old local API process still needs manual restart to interpret the migrated provider records correctly. Existing release/live-content/device gates remain.

## Current local API routing — 2026-10-08

Frontend localhost:3000 now uses FLAME_API_URL=http://127.0.0.1:8001 in its local environment. Current API runs on 8001 with reload. The old API on 8000 was left running because stopping it was previously blocked by policy; it has no Explore routes and must not be used as the frontend's upstream. Existing signed-in Grade 1 Gravity browser listing now shows all ten published videos. No catalogue/auth data changed. For this local session, launch current API with `--port 8001 --reload` if it needs restarting; do not revert routing to the old service. Screenshot evidence: work/gravity-videos-live.png.

## Authority and current work

- [STAGES-STEPS.md](STAGES-STEPS.md) is the single current source for frontend/backend steps, statuses, prerequisites, open decisions and verification history.
- [README.md](README.md) explains document ownership and consolidation.
- Latest explicit owner decisions govern product scope; code establishes implementation and tests prove only tested behavior.
- Owner makes final decisions with a personal technical consultant. Roles in plans are responsibilities, not staffing requirements.
- Read applicable AGENTS.md; frontend changes require relevant installed Next.js documentation under node_modules/next/dist/docs.
- Preserve unrelated dirty/untracked changes. Do not reset, deploy, migrate live data or broaden the task merely because a plan exists.
- Never print/store .env secrets, passwords, service tokens or credentialed DSNs in documents or logs.
- Current implementation snapshot: authenticated member/admin catalogue and session flows plus a protected B7 ask route, OpenAI Responses adapter and stubbed answer rendering. The API now loads the key and project-allowed `gpt-6-luna` (200,000 TPM; 500 RPM); one direct gateway call and one rollback-only owned Study answer/replay passed. The owner reports a USD $5/month project hard spend limit. B9.1 resource policy is owner-approved and B9.2 admin upload/draft flow is implemented in development; publication, delivery, teacher and kit administration remain. See tracker for status updates; do not treat this summary as separate completion evidence.

## Canonical technical references

| Concern | Read / update |
| --- | --- |
| Product scope and exclusions | [MVP scope](../Planning/mvp-scope.md); later approved admin catalogue details below |
| Module ownership, transactions, relational schema and uniqueness | [Module architecture](backend/stage-1/module-architecture.md) |
| API paths, payloads, import fields, frontend mapping and lifecycle | [API contracts](backend/stage-1/api-contracts.md) |
| Nine admin screens, fields, validation and publication | [Admin specification](backend/stage-1/admin-panel-specification.md) |
| Development sequence, decisions, evidence and next step | [Stages and steps](STAGES-STEPS.md) |
| Historical student UI implementation detail | [Frontend delivery notes](../development/apps/web/FRONTEND-STAGES.md) |
| Historical UI checks and repeatable browser setup | [Frontend validation](../development/apps/web/FRONTEND-VALIDATION.md) |
| Future retrieval, not MVP prerequisites | [RAG roadmap](../Planning/RAG/rag_mvp_roadmap.md) |

Critical boundaries: direct LLM, not knowledge RAG; individual members and controlled admin; no achievements/mastery, institution roles, student-file understanding, transcription or commerce. Study answers stay within a validated published curriculum path. Curiosity answers general learning questions across subjects and languages with an under-15 response ceiling; this is not an account-age gate. Open Curiosity has no curriculum/topic IDs. Random teacher cards alongside resources apply only to answered Study turns with a validated subject; no-match never falls back across subjects. Teacher contact/booking and kit recommendations remain excluded. See MVP scope for complete rules.

## Repository and runtime

| Path | Purpose |
| --- | --- |
| development/apps/web/src/lib/api/student-learning.ts | Local curriculum/library providers; explicit unavailable message result; future BFF boundary |
| development/apps/web/src/features/curriculum | Current tree/types, search/Library and immutable merge fixtures |
| development/apps/web/src/features/learning | Workspace, shell, conversations, composer and resource rendering |
| development/apps/web/src/features/progress | Display-only proficiency components |
| development/apps/web/src/app/globals.css and student.css | Theme/layout; source of visual truth |
| development/apps/web/public/brand and learning-assets | Original brand and development media |
| development/apps/flame-api/app/main.py | Factory, lifecycle, safe request middleware and health registration |
| development/apps/flame-api/app/core | Settings, engine/session lifecycle, errors/logging |
| development/apps/flame-api/app/modules/health/router.py | Only implemented HTTP routes |
| development/apps/flame-api/app/modules/teaching/schemas.py | Pydantic answer/context contracts and B7 AnswerService/gateway |
| development/apps/flame-api/tests/test_foundation.py | Foundation/contract tests |

Manifest snapshot: web Next 16.3.5, React/React DOM 19.3.0, TypeScript 7.0.2, lucide-react 1.47.0. API Python >=3.12 (3.13.2 previously tested), FastAPI 0.141.1, Pydantic 2.13.5, pydantic-settings 2.15.0, Uvicorn 0.53.0, SQLAlchemy 2.0.54, psycopg 3.3.6; pytest 9.1.1/httpx 0.28.1. Recheck manifests before dependency changes; no full cross-platform transitive lock recorded.

Local setup/run/test commands belong in the [API README](../development/apps/flame-api/README.md) and [web README](../development/apps/web/README.md). Run from each app directory. API smoke: .venv/Scripts/python.exe scripts/smoke.py. Current local API: 127.0.0.1:8001 with reload; web localhost:3000. The earlier 8000 process is not the frontend upstream; see the October 9 runtime note above.

## Frontend design and integration cautions

Primary visual reference: Ref UI/Sample_2.png. Preserve completed design, not a new dashboard theme.

- FLAME with smaller “by FlipLecture”; original public/brand/flame-logo-horizontal-v1.png.
- Neutral sidebar, Segoe UI/Arial/Helvetica, outline icons, bounded reading column, compact growing composer.
- Tokens: ink #111827; muted #5e697c; line #e6e8ed; paper #fcfcfd; sidebar #f6f6f7; selected #eaf0fc. Spacing 4/8/12/16/20/24/32px.
- Desktop >=1100px; tablet 768–1099px; mobile <=767px. Sidebar/68px rail, tablet overlay and mobile drawer; retain independent content scrolling, focus containment/return, Escape and skip link.
- Only layout preference persists (localStorage flame.sidebar.collapsed). Current learning/history/drafts/attachments/removal archives are in memory.
- Proficiency and curriculum data are illustrative, not authenticated student records. No client-calculated mastery.
- Rich renderer supports more block kinds than backend's initial text/heading/list/table/callout subset. Formula/media generation needs separate validation.
- Development Gravity answer/resource examples are static and labelled, not AI/recommendations.
- Local file/recording controls: 5 files, 10 MB each, 25 MB total, 2-minute voice cap; no upload/transcription. Never silently discard attachments.
- Interactive frames support reviewed packaged demonstrations and admin-uploaded self-contained HTML5 through the October 9 protected publication/JSON-delivery/sandbox contract. No executable model response HTML or arbitrary remote iframe embedding; see the Interactive handoff above.
- Current frontend hierarchy displays Curriculum → Level → Subject → Domain → Topic → Subtopic. Category is stored but hidden from students; its ID remains in Study context. The published-tree adapter preserves all real ancestors and never fabricates child IDs/board metadata.

## Database / implemented contract details

Supabase PostgreSQL selected. On 2026-09-26, approved Alembic revisions through `20260926_08` added encrypted browser session storage, revoked direct client-role access to the `flame` schema and enabled identity-table RLS. Rollback-only database access tests pass; live Supabase Auth and email integration remain unverified. MCP registration is session-dependent and separate from runtime DB access.

API local .env: development/apps/flame-api/.env; template .env.example. Settings use FLAME_ENVIRONMENT, FLAME_LOG_LEVEL, FLAME_DATABASE_URL, FLAME_DATABASE_CONNECT_TIMEOUT (default 3, range 1–30). URL requires postgresql+psycopg, host/database and encoded password; preserve required TLS for hosted connection. Never expose credentials.

Engine pool_pre_ping; pool_size=5; max_overflow=5; pool_timeout=5; expire_on_commit=False. Startup does not create tables/migrate. Production requires DB config and disables /docs and /openapi.json. /health/live returns 200; /health/ready runs SELECT 1 or returns sanitized 503.

Current Pydantic schemas forbid extra fields; trim question length 1–4000; action=explain. Study requires context; Curiosity requires null context. UUID shape validation is not DB ancestry validation. DirectAnswer requires 1–30 blocks and validates table row widths; citations/resources remain empty until compatible extension. Service-owned provenance cannot be set by model text. Exact request fields/examples live in API contracts.

## Curriculum files and historical inspection

Current files:

- [Original workbook](<../Curriculum Documents/Curriculum Level 1 to 5.xlsx>).
- [Candidate revised workbook](<../Curriculum Documents/Curriculum Level 1 to 5 for codex.xlsx>).

Both historical files exist. The “for codex” workbook was structurally inspected on 2026-09-25: six sheets, missing Subject, legacy headers, incomplete parent fields and URLs under Level. Owner confirmed separate KG and Levels 1–5 sheets, all Science. Repeated KG rows in the legacy combined sheet were an open question for that candidate, but the owner has since said not to use either existing workbook and will provide a final one. Findings/hash are historical; the final owner workbook is `Curriculum Documents/Fliplecture Curriculum Grade 1 to 5.xlsx` and has passed B2.1 normalization review. Original workbooks remain unchanged. API contracts include an explicit seven-field frontend target and concrete B1.9 examples; B1 review and handoff are complete; runtime integration remains in later stages.

Historical original inspection: five sheets, KG/Level I combined; early/later Domain semantics differ, no Subject column, “Sub Toipc” spelling, URLs embedded in rows, repeated Lighthouse entries and Level V containing a Level IV label. Current workbook contents may have changed; recheck rather than applying old fixes blindly. Required headers and import rules live in API contracts, relational identity in module architecture.

## Legacy interpretation and maintenance

Planning/flame_docs and broader architecture documents are future-target references, not current MVP mandates. RAG roadmap contains older route examples; current API contracts win. Historical frontend “Stage 8 pending” paragraphs predate its validation report. Backend/ frontend stage numbers are independent.

Do not recreate removed stage/decision reports. Update progress/prerequisites/evidence only in STAGES-STEPS.md; technical definitions in their owning specification; runtime/design pointers here. Keep historical verification labelled with its date and limitations. Any missing product decision required for the current step must be resolved, not guessed.

Current hierarchy decision (2026-09-26): stored Curriculum → Level → Subject → Domain → optional Category → Topic → Subtopic; student navigation hides Category; the 2026-09-28 owner update permits Study at Topic or Subtopic. Teaching Context now requires curriculum_id. Admin creates curricula dynamically; levels, import targets and revisions are curriculum-scoped. API contracts define seven frontend context fields. B4 publication, protected importer/catalogue routes, exact My Learning persistence and curriculum/student admin screens are implemented in development; later F9 resource, teacher and kit screens remain. No fixed Science/KG–5 catalogue is implied.

B1.8–B1.10 closed on 2026-09-25 under the owner’s instruction to complete the remaining foundation steps. B2 internal migrations, parser, preview, commit and history are complete; development Supabase has no permanently imported curriculum data. B3 auth is complete in development: live signup, confirmation, sign-in, password recovery/reset, initial admin access and session revocation were verified after migrations. A restricted runtime database role remains a production deployment gate. B4 publication validation, protected catalogue/import/My Learning routes and authenticated BFF data are complete in development. Migrations through `20260926_14` are applied; rollback-only database tests and a mock-API browser flow passed. B5 now has owned Study/Curiosity sessions, paginated history, internal idempotent request claims, measured activity, and confirmed conversation/account deletion; a disposable development Auth user was removed through FLAME and verified absent, while provider timeout/retry is mock-tested. The owner set a 30-day maximum for backup and operational-log copies on 2026-09-26 and confirmed PITR is not required for MVP; primary FLAME private data is removed immediately on confirmed deletion. B5 remains partial: the server-only Supabase deletion credential is configured in development, while managed backup/log retention and maintenance scheduling still need operational verification; stubbed new-answer transport is mounted under B7; full saved-session continuation remains partial. Mock-API browser history, rollback-only hide/restore and two-worker claim checks passed. Later-stage policy deadlines remain in tracker section 7.






B6 update, 2026-09-26: Completed in development. Conservative KG–5 profiles, published-path Study/Curiosity resolution, bounded prompt assembly and expiring clarification state are implemented. Additive migrations `20260926_13` and `_14` persist owned pending choices and idempotent topic-check events with resolved subject/topic/revision snapshots. The BFF saved-session dialog renders pending choices and paginated topic-check history. The DB-enabled backend suite passed 39 tests, two concurrency-only tests skipped; Alembic drift check passed. B7 must generate and store answer turns and copy the validated IDs for recommendations. Five authored workbook-row cases are draft fixtures for later educator review. See [B6 handoff](backend/stage-6-context.md).




B6.5/B6.6 closure, 2026-09-26: Public topic checks are owned, idempotent and persisted; ready results store the full resolved path. Clarification choice/replay, expiry, topic switches, owner isolation, history pagination and deletion passed rollback-only PostgreSQL checks. Five candidate teaching cases cite exact supplied workbook sheets and rows. Web typecheck, 11 unit tests, build and production-mode mock browser passed. Educator answer review is planned with B8; these cases are not claimed as approved answers.



B7 update, 2026-09-27: Protected `POST /sessions/{id}/ask` connects B5 idempotent claims and B6 validated prompts to a bounded OpenAI Responses adapter, server-owned text blocks/provenance and atomic answer-turn storage with resolved IDs. `20260927_15` stores model/prompt/profile versions, token usage and latency. The BFF composer sends text only, preserves unsupported attachments, and labels AI-generated answers. Rollback-only Study/Curiosity/replay tests, provider-mock retry/malformed tests, Alembic drift check, 11 web unit tests, production build and mock browser answer retry passed. No live provider key/model was configured or called at this delivery; model selection, spend threshold, cancellation and live tests remain B7.1/B7.5/B7.7. The owner selected OpenAI for MVP and has a key, but it is not in the API `.env`; model and monthly USD project hard spend limit remain undecided. See [B7 handoff](backend/stage-7-answer-service.md) for the template and live gates.

B8 update, 2026-09-27: Partial in development. A narrow, owned capability preflight and idempotent unsupported ask outcome handle explicit textbook-evidence, official-grading, file/media-understanding and progress-update requests in Study/Curiosity without model calls. Supported block schemas now bound text, lists, tables, IDs and control characters; an output guard rejects obvious fabricated source/grade/file claims and links. A draft educator case matrix/rubric is in [B8 evaluation](backend/stage-8-evaluation.md). The DB-enabled backend suite passed 55 tests (two concurrency-only skipped); Alembic drift check, 11 web unit tests, build and mock browser unsupported flows passed. At that B8 checkpoint no live model answers or educator acceptance existed; later B7 smoke answers do not constitute educator evaluation. B8.2/B8.6 are NOT STARTED, B8.1/B8.4/B8.5 are PARTIAL, and B8.3 is COMPLETED. See tracker for current evidence.

B7 model decision, 2026-09-27: The owner confirmed that this OpenAI project allows only `gpt-6-luna`, at 200,000 TPM and 500 RPM. This resolves model selection, not the monthly USD hard spend limit or local key setup. B7.1 remains PARTIAL; no live call has run.

B7 live update, 2026-09-27: API settings confirmed key and `gpt-6-luna` without displaying the secret (100 new requests/member/rolling day, 1,500 max output tokens, 12-second timeout). A direct Responses call returned 33 input/31 output tokens. A rollback-only authenticated Study API call returned 200, saved two messages plus model/usage/latency (188 input/13 output tokens), and same-key replay returned the identical answer. The disposable curriculum/session/profile rows were rolled back. The owner reports a USD $5/month project hard spend limit. B7.1 and B7.5 are complete; B7.7 remains partial for live timeout/cancellation and restored-session continuation. B8 live educator evaluation remains open.

B7 Curiosity frontend test, 2026-09-27: The development catalogue has one clearly labelled published test-only curriculum (`flame-curiosity-test`, ID `d4ab2aff-c727-49c1-a72d-f18bf999ee7b`) with the path Science → Gravity → Gravity basics. The live homepage now passes published catalogue data into the student workspace, which suggests a matching Curiosity question. The API process was restarted after key setup. Live rollback-only Curiosity topic-check/answer/replay passed (`gpt-6-luna`, 217 input/68 output tokens); web unit/build and mock browser flow passed. Signed-in real-browser verification remains; archive the test curriculum after use. No workbook rows were permanently imported.

Open Curiosity scope update, 2026-09-27: The owner expanded Curiosity to general learning across science, technology, social studies, mathematics, English and any languages. The B7 ask route now uses `direct-curiosity-open-1` with null curriculum/subject/topic and no `topic_check_id`; Study remains curriculum-bound. The former published test-only curriculum has been archived. Live `gpt-6-luna` answer/replay passed with zero published curricula (164 input/119 output tokens); rollback removed test member/session/turn. Backend suite: 66 passed, 2 skipped; web unit/build/mock browser passed. Historical B6/B7 curriculum-bound Curiosity entries above are superseded. Signed-in browser continuation and B8 educator evaluation remain open.

B7.7 continuation update, 2026-09-28: The saved-session dialog can restore complete paginated Study/Curiosity message pairs into the workspace. Follow-up questions explicitly use the selected owned session ID; Study resolves the exact published seven-ID path before resuming, while the backend still enforces revision and publication. Production-mode mock browser checks passed for reload, restored messages, Curiosity follow-up, Study retry on the same saved ID, and deletion. Web typecheck, 11 unit tests and production build passed. B7.7 remains PARTIAL until live timeout/cancellation and signed-in real-browser continuation are verified; B8 educator case approval and live scoring remain open.

B8 Study evaluation update, 2026-09-28: The FlipLecture founder is the reviewer. A Study-only controlled runner and [review packet](backend/stage-8-study-review-2026-09-28.md) record 17 live `gpt-6-luna` outputs from five workbook-linked cases and two Study override attempts. All passed the existing output guard and word-limit observation; 3,344 input/866 output tokens, 2,242/3,295 ms median/p95 gateway time. Candidate omissions in Grades 2/3/5 await founder judgment; no factual or age-suitability acceptance is claimed. B8.2 is PARTIAL and B8.6 is NOT STARTED. Curiosity remains open to any learning question and its behavior was untouched; its broader quality evaluation was excluded from this implementation pass at owner direction.

B8.4 Study hardening, 2026-09-28: AnswerService now rejects output above the selected Study level word cap; open Curiosity was not changed. Targeted B7/B8 tests (26), rollback-only B7 integration (1), and revalidation of all 17 recorded Study samples passed. Founder scoring remains the next quality gate.

Study verification clarification, 2026-09-28: The 17 B8 baseline answers were direct synthetic prompts and did not use the Study UI or an imported published curriculum. A separate live rollback-only TestClient check used a temporary published KG path from the workbook-linked case, returned a Study answer, stored one user/assistant pair with resolved topic IDs, and replayed identically; no temporary curriculum remained after rollback. This bypassed login with a disposable principal override, so signed-in browser Study with imported curriculum remains unverified.

Final curriculum import and Study verification, 2026-09-28: The founder approved permanent import/publication in development. The accepted `Fliplecture Curriculum Grade 1 to 5.xlsx` hash matched the reviewed B2 profile. The admin-gated service preview found 1,721 new paths, five accepted duplicates and zero issues; commit created 2,272 hierarchy nodes, then publication validation passed. `fliplecture` is published at revision 2 with six Levels and 1,721 Subtopics. Member catalogue listing, Level list, KG tree and exact Subtopic search all returned 200. One live Study API answer on the imported KG path returned 200 with `gpt-6-luna` (199 input/53 output tokens; 3,560 ms model latency); two turns had resolved subject/topic IDs and same-key replay was identical. That check used a disposable principal override, and its session/turn data rolled back. Signed-in real-browser Study remains unverified because the browser tool failed with an environment ACL error. The web BFF preview/commit timeout was increased to 60/240 seconds to allow full workbook imports; typecheck and production build passed. Founder answer scoring remains open. Curiosity continues to accept open questions and its runtime was not changed.

Study prompt responsiveness fix, 2026-09-28: After the full curriculum was published, every draft keystroke re-rendered the large My Learning navigator (up to 1,721 Subtopics, mounted in sidebar/drawer). `StudentWorkspace` now memoizes the navigator against actual tree/selection/view inputs so draft changes do not rebuild it. Typecheck, 11 web unit tests, production build and B4–B8 browser flow passed. Local web port 3000 and API port 8000 remained healthy. Model answer generation after Send is a separate approximately five-second path observed in local API logs; this change targets typing responsiveness.

My Learning search responsiveness, 2026-09-28: The sidebar Find a subtopic field previously filtered and expanded the full imported tree synchronously on every keystroke. The search input now owns its draft text and applies the filter after 180 ms of inactivity; filtered branches are memoized. Matching, no-result and clear behavior passed in the browser flow, alongside typecheck, 11 unit tests and production build. Local web/API health checks returned 200. Search still covers items in My Learning; Library search covers all published items.

Topic-level Study update, 2026-09-28: The founder requested direct questions from a Topic, with Subtopics above the workspace title and again as lower action buttons. Published Topics still require at least one real Subtopic; selecting a Topic now stores a null `subtopic_id` in a separate Study session. Backend session/answer validation still enforces published Topic ancestry and pinned curriculum revision; saved Topic sessions restore by Topic name. Curiosity remains open and unchanged. A rollback-only integration test passed Topic ask/replay and mismatched-context denial. One live `gpt-6-luna` TestClient ask on an actual imported KG Topic returned 200, 194 input/28 output tokens, 2,714 ms stored latency, and identical replay; disposable student/turn rows rolled back. Web typecheck, 11 unit tests, production build and mock browser Topic/Subtopic action flow passed. Signed-in real-browser acceptance remains.

Topic/Subtopic visual revision, 2026-09-28: After reviewing the live Topic screenshot, the founder changed the layout: the Topic title appears before its Subtopics, the duplicate bottom Subtopic section is removed, and a Subtopic workspace highlights its parent Topic with a `View topic` button. Only web layout/tests changed. Web typecheck, 11 unit tests, production build and mock browser flow passed; desktop mock screenshots were visually inspected. The earlier top-and-bottom CTA layout is superseded.

Subtopic navigation refinement, 2026-09-28: The approved Topic screen remains unchanged. Subtopic screens now show a dark filled Topic control beside an outlined list of all sibling Subtopics; the active Subtopic uses a light blue selected state and `aria-current=page`. Students can move directly among siblings or return to the parent Topic. Web typecheck, 11 unit tests, production build and mock browser navigation/visual-state checks passed; desktop screenshot was inspected.

B9 update, 2026-09-28: Owner approved the resource media, rights and private storage policy. Revision 20260928_16 adds resource rights/media metadata and owned upload staging. Admin-only B9.2 routes validate bounded JPEG/PNG/WebP, MP3/M4A and MP4/WebM uploads, exact allowlisted HTTPS links, and real Topic/Subtopic associations; drafts stay unpublished. Local rollback-only integration passed. External hosts default to none, no approved asset has been published, and the private Supabase bucket has not been live-tested. B9.3 publication is next. See [B9 policy](backend/stage-9-resource-policy.md).

B9 implementation update, 2026-09-28: B9.3–B9.10 are complete in development. Revision `20260928_17` adds resource availability/accessibility, kit upload ownership and retry-stable recommendations. Versioned admin resource, teacher and multi-topic kit catalogues have publication gates and filters. Members get exact published resource lookup, five-minute local/Supabase signed delivery, duplicate-safe open/play activity, and subject-matched random teacher/resource cards for answered Study turns; open Curiosity has no teacher match. The web BFF, three admin screens and member cards/viewers are integrated. Rollback-only B7/B9 tests (6), mock browser B4–B9, web typecheck/build and Alembic check passed. The API was restarted and `/health/ready` returned database ok. B9.11 remains partial until a private deployed bucket, approved assets/hosts and signed-in browser/device checks are available; no sample asset was published. See [tracker](STAGES-STEPS.md).


### Local sign-in recovery — 2026-10-09

Frontend local configuration still pointed to port 8001 after the API was restarted on port 8000. No listener existed on 8001; the current API on 8000 has both authentication and latest Explore/Curiosity routes. Corrected only FLAME_API_URL in the ignored frontend environment to http://127.0.0.1:8000. This supersedes the 2026-10-08 port-8001 runtime handoff; use the configured address and running backend consistently. Also corrected the authentication BFF to return the signed_in envelope only on a successful login/verify response, preserving operation-specific upstream errors otherwise. A credential-free empty login request previously returned HTTP 503 with a false signed_in body; after correction it reaches backend validation and returns HTTP 422 with validation_error. No user credentials, identity roles, auth rules, or database data were changed. Actual successful account sign-in remains for the user to retry.
