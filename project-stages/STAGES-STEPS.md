# FLAME — Development stages and steps

Updated: 2026-10-14. Canonical progress tracker, not a claim of end-to-end completion.
Companion technical handoff: [PROJECT_CONTEXT.md](PROJECT_CONTEXT.md).

Resumed delivery (2026-10-14): Vercel-compatible private uploads/exports and replay receipts are implemented; real large-file storage, database regressions and production-browser checks passed. F8.5 completed; B10.1–B10.4 started. See [resumed verification](#resumed-private-transfer-and-pilot-verification--2026-10-14) for current evidence and remaining acceptance gates.

Latest delivery (2026-10-14): B7 recovery/continuation and connected B5/F5 steps completed in development; Vercel preparation, hosted Sheets credential support and live private-bucket probe delivered. See [pending-stage evidence](#pending-stage-delivery--2026-10-14). Previous delivery (2026-10-13): published Light/Gravity Phaser upgrades and object controls, embedded Rive sandbox support, testing drafts for the Rive cat and States of Matter, and the file-only Weather World prototype. See [current Interactive status](#current-interactive-status--2026-10-14). The saved three-tab Google Sheets connector and its remaining live-write acceptance are summarized in [resource and Sheets upgrades](#latest-resource-and-google-sheets-upgrades--2026-10-12) and the [connector workflow](GOOGLE-SHEETS-CONNECTOR.md). Local routing is API 8000 / web 3000; migration `20261012_30` is the latest recorded applied head. Earlier dated port-8001 notes are historical. Current step totals: 162, with 137 completed, 20 partial and 5 not started. See the [October 14 pending-stage delivery](#pending-stage-delivery--2026-10-14); older counts below retain their checkpoint dates.

Documentation audit — 2026-10-09: verified 55 frontend and 107 backend step rows against the totals (130 completed, 20 partial, 12 not started). Reconciled the main [development handoff](DEVELOPMENT-HANDOFF.md) with B12/B13/F10/B14, current migration-source head, three media families, Explore/layout follow-ups and Interactive build/live draft evidence. Corrected stale port-8000 restart instructions and old teacher/metadata policy summaries. No status promotion, application test rerun, fresh database audit, publication or deployment in this documentation review; recorded verification retains its original scope/date. Remaining development and acceptance work stays assigned to the existing B5/B7/B8/B9.11/B10 and frontend gate rows.

## 1. How to use this tracker

Implement by stable step ID, e.g. “Proceed B2.3”. Inspect the linked source/contracts and applicable AGENTS.md before code changes. A step is a reviewable work package, not a promise it fits one prompt.

- **COMPLETED:** implementation or explicitly named planning deliverable exists, with recorded evidence. Local UI completion is not live-service completion.
- **PARTIAL:** useful work exists, but the stated acceptance condition is unmet.
- **NOT STARTED:** no implementation evidence for the step. An existing design does not count as implementation.
- **IN PROGRESS:** use only while an assigned step is actively being implemented; none asserted at this baseline.
- **BLOCKED:** use when a specific missing input prevents the next action; record dependency/owner. Future dependency does not automatically mean blocked.
- **DEFERRED / OUT OF MVP:** intentional exclusion; never count as completed MVP work.
- Tests listed as recorded were not rerun while creating this document. Reverify affected behavior before closing new steps.
- Stage completion requires all mandatory steps plus integration/verification evidence. Optional work is explicitly identified and may be deferred with a reason.
- Preserve step IDs. If a work package needs splitting, add child IDs (e.g. B2.8a) and mark the parent as a roll-up, avoiding double-counting.
- Update status, evidence/date, unresolved issue and next step after each delivery. Update PROJECT_CONTEXT.md for material architecture/progress changes.
- No blanket deployment, destructive database changes, secret exposure or expansion beyond the owner's current request is authorized here.

### Sources and interpretation

1. This document consolidates the former backend roadmap, stage prerequisites, input review and Stage 1 completion report. See the [consolidation record](README.md).
2. [Frontend stages](../development/apps/web/FRONTEND-STAGES.md): original eight local UI stages.
3. [Frontend validation](../development/apps/web/FRONTEND-VALIDATION.md): subsequent local Stage 8 completion evidence; supersedes older “Stage 8 pending” paragraphs.
4. Verification evidence and open decisions are maintained in sections 7–8 below, not a separate completion report.
5. [Schema/module plan](backend/stage-1/module-architecture.md), [API contracts](backend/stage-1/api-contracts.md), [Admin specification](backend/stage-1/admin-panel-specification.md).
6. [MVP scope](../Planning/mvp-scope.md): apply latest owner decisions and the approved admin specification where older scope text differs.

The original frontend stages 1–8 are completed for local review. This tracker extends their acceptance to live MVP integration, so several now show PARTIAL without negating completed UI work. F9 is a newly documented admin implementation track, not a claim that the original frontend plan had nine stages. Backend numbers remain unchanged.

Backend Stages 1–4 and B6 are complete in development. B5 is partial; the latest recorded applied migration is `20261012_30` (saved Google Sheets connections), following media families, video thumbnails and Interactive draft support. B6 context/prompt and owned topic-check/clarification/history services are complete. B7 is complete in development as of October 14, including protected ask transport, live deadline and signed-in continuation checks; the API now has a configured key and `gpt-6-luna`; one direct gateway call plus rollback-only live Study and Curiosity answer/replay checks passed. B8 has deterministic unsupported outcomes, bounded block validation and a Study-only live model baseline for founder review; accepted answer quality remains open. B4 mounts protected published catalogue/search, admin curriculum/import/student routes and exact My Learning membership paths through Subtopic. B4 browser flows and real database checks passed; the final workbook is now published in development; the temporary Curiosity test curriculum has been archived, and no deployment has occurred. Owned session/history, measured activity, local deletion and live-verified Study/Curiosity answer routes now exist. B9 resource, teacher and activity-kit catalogues and their admin/member screens are implemented in development; live private-storage and approved-asset acceptance remain. Educator quality evaluation and broader signed-in pilot/device acceptance remain open; Study/Curiosity continuation passed October 14.

## 2. Totals and stage overview

Counts are reviewable work packages, not estimates of hours or percentage effort. Frontend and backend steps often coordinate on one feature but represent different deliverables; do not interpret the total as independent tasks.

2026-10-08 reconciliation: all ten F10/B14 steps are complete in development with API/DB/browser evidence. Earlier acceptance statuses are unchanged. At that checkpoint the Explore/Interactive API used port 8001; the 2026-10-12 startup refinement supersedes this with canonical port 8000. The 2026-10-09 audit confirmed all 162 numbered rows match the totals; Interactive implementation and the live draft/mappings use existing steps. Release/live-content/device gates remain open.

| Track | Stages tracked | Steps | Completed | Partial | Blocked | Not started |
| --- | --- | --- | --- | --- | --- | --- |
| Frontend | 8 original + 1 admin + 1 Explore track | 55 | 46 | 7 | 0 | 2 |
| Backend | 14 | 107 | 91 | 13 | 0 | 3 |
| Total | 24 | 162 | 137 | 20 | 0 | 5 |

### Frontend overview

| Stage | Focus | Steps | Status toward integrated MVP |
| --- | --- | --- | --- |
| F1 | Design foundation and responsive layout | 4 | COMPLETED |
| F2 | Study/Curiosity navigation and profile | 4 | COMPLETED (development) |
| F3 | Curriculum navigation and context | 5 | PARTIAL |
| F4 | Library and My Learning | 5 | PARTIAL |
| F5 | Conversations and structured responses | 5 | PARTIAL |
| F6 | Composer and unsupported input handling | 6 | PARTIAL |
| F7 | Resource cards and viewers | 5 | PARTIAL |
| F8 | Frontend integration and release validation | 5 | PARTIAL |
| F9 | Admin frontend — newly tracked delivery stage | 11 | PARTIAL |
| F10 | Learner Explore panel and recommendation entry points | 5 | COMPLETED (development; physical-device/release gates remain) |

### Backend overview

| Stage | Focus | Steps | Status |
| --- | --- | --- | --- |
| B1 | Foundation and API contracts | 10 | COMPLETED |
| B2 | Database and Excel curriculum import | 10 | COMPLETED (internal services; protected routes in B3/B4) |
| B3 | Individual authentication and admin access | 7 | COMPLETED (development authentication, recovery, admin access and session checks verified) |
| B4 | Curriculum administration, My Learning and student directory | 8 | COMPLETED (development; live curriculum publication/release validation remains later) |
| B5 | Conversations, student activity and data lifecycle | 9 | PARTIAL (owned storage/activity/deletion; retention operations remain) |
| B6 | Curriculum context and prompt construction | 6 | COMPLETED (development topic gate, prompt, clarification and draft fixtures; generated answers belong to B7) |
| B7 | Direct LLM gateway and answer service | 7 | COMPLETED (development; hosted termination/release checks remain B10) |
| B8 | Response quality and capability handling | 6 | PARTIAL (capability handling and schema checks; educator/live evaluation pending) |
| B9 | Resource library, teachers and activity kits | 11 | PARTIAL (B9.1–B9.10 complete in development; B9.11 live storage/content gate) |
| B10 | Integration, evaluation and pilot readiness | 8 | PARTIAL (Vercel preparation; integrated pilot/release gates remain) |
| B11 | Modular recommendation migration and response composition | 11 | COMPLETED (development; release gates remain) |
| B12 | Recommendation metadata, evaluation, ranking and performance | 4 | COMPLETED (bounded development cycle; educator/release gates remain) |
| B13 | Additive catalogue import/export, samples and saved Google Sheets connector | 5 | COMPLETED (development; live sync acceptance, production load/retention scheduling remain) |
| B14 | Member catalogue browsing and independent item access | 5 | COMPLETED (development; canonical API 8000 / web 3000; release gates remain) |

## 3. Frontend steps

Completed UI evidence primarily comes from the 2026-09-20 frontend validation report and existing components/tests. NOT STARTED integration rows are acceptance targets, not evidence.

### F1 — Design foundation and responsive layout

Status: **COMPLETED**. Steps: **4**.

| Step | Status | Work item | Completion evidence / acceptance condition |
| --- | --- | --- | --- |
| F1.1 | COMPLETED | Implement neutral theme, typography, spacing and original FLAME/by FlipLecture branding. | Existing CSS/brand assets; recorded frontend build and visual review. |
| F1.2 | COMPLETED | Implement desktop sidebar, compact rail, tablet overlay and mobile drawer. | Existing shell; desktop >=1100px, tablet 768–1099px, mobile <=767px. |
| F1.3 | COMPLETED | Keep reading area independent of composer and support dynamic viewport heights. | Recorded responsive/composer checks. |
| F1.4 | COMPLETED | Provide keyboard focus handling, Escape, skip link and sidebar preference persistence. | Recorded keyboard and blocked-storage checks. Only layout preference persists. |

### F2 — Study/Curiosity navigation and profile

Status: **PARTIAL**. Steps: **4**.

| Step | Status | Work item | Completion evidence / acceptance condition |
| --- | --- | --- | --- |
| F2.1 | COMPLETED | Implement Study/Curiosity switching and isolated local drafts/selections. | Existing mode/workspace components; recorded isolation tests. |
| F2.2 | COMPLETED | Implement local pinned/recent context navigation and honest local profile display. | Recorded navigation checks; no authenticated account implied. |
| F2.3 | COMPLETED | Integrate the chosen new-member onboarding path, authenticated member/profile and sign-in/sign-out/recovery states. | Live signup, confirmation, recovery/reset and new-password sign-in verified; profile shows server role, retryable sign-out and account error states implemented. |
| F2.4 | COMPLETED | Connect resumable sessions/recent history; decide whether server-side pins are MVP polish. | 2026-10-14: signed-in Study and Curiosity history survive reload and resume with follow-ups in the same conversation. Server-side pins/recent paths are implemented and B5 pin/hide/restore tests passed; drafts remain local. |

### F3 — Curriculum navigation and context

Status: **PARTIAL**. Steps: **5**.

| Step | Status | Work item | Completion evidence / acceptance condition |
| --- | --- | --- | --- |
| F3.1 | COMPLETED | Implement existing curriculum/subject/chapter/concept tree, search, filters and breadcrumbs. | Original local frontend scope verified; illustrative scores are fixtures. |
| F3.2 | COMPLETED | Preserve full existing path identity across navigation, modes and narrow layouts. | Recorded path and draft-isolation checks. |
| F3.3 | COMPLETED | Extend types/tree/breadcrumbs to Curriculum → Level → Subject → Domain → Topic → Subtopic. | 2026-09-26: local My Learning, Library, stable path keys and published-tree adapter use selectable Subtopics; Category is retained only as hidden context. Unit, build and UI checks passed. Live BFF data still depends on B3/B4. |
| F3.4 | COMPLETED | Replace local catalogue with authorized BFF data; map stable UUIDs and revision. | B4 server loader and browser BFF flow use published UUID trees/revision; no assumed board or grade metadata. |
| F3.5 | COMPLETED | Remove fixture mastery/progress from production flows and handle unavailable values honestly. | Live navigation hides unsupported progress filters/guide and renders unavailable proficiency without a score. |

### F4 — Library and My Learning

Status: **PARTIAL**. Steps: **5**.

| Step | Status | Work item | Completion evidence / acceptance condition |
| --- | --- | --- | --- |
| F4.1 | COMPLETED | Implement local Library tabs/search/filters, loading/empty/error states and accessible dialog. | Recorded desktop/mobile Library checks. |
| F4.2 | COMPLETED | Implement immutable partial-path merge, deduplication and retained-data preservation. | Existing merge tests; local fixtures only. |
| F4.3 | COMPLETED | Implement curriculum/subject removal confirmation and local restoration. | No individual chapter/concept removal; existing local tests. |
| F4.4 | COMPLETED | Connect addition/hide/restore and catalogue loading to BFF/API. | Exact paths and subject masks survive reload; signed-session DB test, concurrent duplicate check and browser restoration passed. |
| F4.5 | PARTIAL | Test server conflicts, failed saves, partial additions and restored session links. | B4 stale/conflict and load retry covered; restored conversation/session links depend on B5. |

### F5 — Conversations and structured responses

Status: **PARTIAL**. Steps: **5**.

| Step | Status | Work item | Completion evidence / acceptance condition |
| --- | --- | --- | --- |
| F5.1 | COMPLETED | Implement rich renderer, local turns, contextual drafts and reading-position restoration. | Recorded rich blocks/MathML/scroll tests; development preview labelled. |
| F5.2 | COMPLETED | Implement pending/unavailable/error/retry states without duplicate local questions. | Existing service reports unavailable, not fabricated AI. |
| F5.3 | PARTIAL | Integrate session creation, paginated history, resume and confirmed conversation deletion. | B5 UI creates Study/Curiosity sessions, shows paginated owned history and confirms deletion; mock-browser saved-session continuation now restores messages and reuses the owned session; signed-in live continuation remains open. |
| F5.4 | COMPLETED | Adapt validated complete answers, provenance, request IDs and retry semantics. | 2026-10-14: generated provenance labels, internal server request references and restored references are integrated. Owner requested removal of Answer reference details from student responses; successful-answer UUIDs are no longer rendered. Owner-scoped history loads references in one bounded page query; terminal failures replay and new attempts use new keys. Existing TypeScript, frontend unit/build and rollback-only B7 evidence remains. |
| F5.5 | PARTIAL | Verify answer rendering and recovery against live/stubbed API failures. | B7 mock browser answer/error/retry and published Curiosity suggestion passed; live Curiosity API call passed with rollback-only member data. Mock-browser restored Study/Curiosity follow-up now passes; signed-in real-browser and B8 quality/failure coverage remain. |

### F6 — Composer and unsupported input handling

Status: **PARTIAL**. Steps: **6**.

| Step | Status | Work item | Completion evidence / acceptance condition |
| --- | --- | --- | --- |
| F6.1 | COMPLETED | Implement growing composer, desktop/touch keyboard and IME handling. | Recorded input/viewport checks. |
| F6.2 | COMPLETED | Implement local file selection/previews and limits. | 5 files, 10 MB each, 25 MB total; no server processing. |
| F6.3 | COMPLETED | Implement local microphone recording/playback and cleanup. | 2-minute cap; synthetic-microphone checks, no transcription. |
| F6.4 | COMPLETED | Keep per-context drafts and original attachment snapshots for retries. | Existing local behavior verified. |
| F6.5 | COMPLETED | Connect text requests and retain explicit unavailable/disabled states for attachments/voice processing. | B7 text requests flow through the BFF; attachments/voice remain explicitly unavailable and retained. |
| F6.6 | NOT STARTED | Verify real-device keyboard/microphone behavior for any controls retained in MVP. | Part of F8 device coverage; unsupported processing remains excluded. |

### F7 — Resource cards and viewers

Status: **PARTIAL** (all implementation steps complete in development; live approved-asset/device acceptance remains in B9.11/F8). Steps: **5**.

| Step | Status | Work item | Completion evidence / acceptance condition |
| --- | --- | --- | --- |
| F7.1 | COMPLETED | Implement local resource cards, expansion and on-demand accessible viewers. | Recorded images/audio/video/captions and detail views. |
| F7.2 | COMPLETED | Implement reviewed simulation allowlist, sandboxing and playback cleanup. | October 9 owner override adds admin-uploaded self-contained HTML5 to the isolated catalogue viewer; October 13 adds embedded Rive WASM support. Sandbox remains allow-scripts only; parent access, JavaScript eval and network probes were blocked. Self-contained Phaser/Rive browser checks recorded; [current Interactive status](#current-interactive-status--2026-10-14). Live cloud/device/educator gates remain. |
| F7.3 | COMPLETED | Connect explicit approved-resource lookup and authorized delivery URLs. | B9 exact published-topic lookup and five-minute authorized delivery are wired through the BFF; explicit media requests make no LLM call. |
| F7.4 | COMPLETED | Handle no-results, withdrawal, unavailable/expired URLs and renewal/retry. | Member viewer shows empty/error states, requests a fresh delivery URL on retry and uses reviewed launch modes; withdrawal/expiry pass rollback-only API tests. |
| F7.5 | COMPLETED | Present intent-based eligible media, activity guides and explicitly requested tutor profiles alongside Study answers. | Owner MVP update 2026-10-03: structured one-primary/one-alternative decisions, specific reasons, optional viewers, previous-resource references, display acknowledgement and failure isolation. Published expertise and accurate availability; no automatic contact, booking or commerce. |

### F8 — Frontend integration and release validation

Status: **PARTIAL**. Steps: **5**.

| Step | Status | Work item | Completion evidence / acceptance condition |
| --- | --- | --- | --- |
| F8.1 | COMPLETED | Run local frontend unit, build/type and integrated Edge review. | Recorded 2026-09-20: 8 unit tests; build/type checks passed. |
| F8.2 | COMPLETED | Validate local responsive, keyboard and accessibility states. | Recorded 320–1920px coverage and 14 axe states; not accessibility certification. |
| F8.3 | PARTIAL | Rerun unit/type/build/browser checks against integrated member and admin flows. | October 14: 27 web units, TypeScript, production build, replacement-import/sidebar/resource-bulk production-browser suites passed. Resource tests updated two stale page-selection button selectors to the current checkbox. Signed-in full-flow, legacy B4 harness modernization and remaining F2–F9 regressions await B10. |
| F8.4 | NOT STARTED | Check supported real mobile devices, screen readers and browser compatibility. | Physical keyboards/microphones, VoiceOver/NVDA, Safari/Firefox previously unverified; record release support matrix. |
| F8.5 | COMPLETED | Verify production build excludes fixture answers/progress and enforces unsupported-feature policy. | 2026-10-14 production browser: anonymous root redirects to sign-in; signed-in workspace has no development answer preview, shows unavailable progress without fixture percentages, and retains an unsupported attachment locally without sending an ask. Production route always requires live catalogue/account data; backend capability checks and frontend units pass. |

### F9 — Admin frontend — newly tracked delivery stage

Status: **PARTIAL**. Steps: **11**.

| Step | Status | Work item | Completion evidence / acceptance condition |
| --- | --- | --- | --- |
| F9.1 | PARTIAL | Build protected admin layout/navigation and shared form/list/error/conflict components. | Admin sign-in link and admin-only learning-workspace CTA reach protected `/admin`. The responsive workspace now has labelled section navigation, account context, loading/empty/error feedback and clearer form grouping; shared components across all catalogues and full keyboard/mobile regression remain F9.11. |
| F9.2 | COMPLETED | Build Admin Sign-in/recovery/sign-out and non-admin denial. | Admin sign-in and shared recovery/sign-out work; admin access page checks server role, unauthenticated redirect and member-denial integration tests pass. Management screens follow F9.3–F9.11. |
| F9.3 | COMPLETED | Build Curriculum Catalogue creation, full hierarchy, metadata edit/rename/publication/archive. | Full-width Catalogue list/workspace with compact navigation, sticky actions and metrics. The six-column spreadsheet editor supports search/status/cascade filters, inline and bulk edits, insert/duplicate/delete, keyboard save/cancel, frozen identity/status/action columns, shared-node rename, stale-edit review and explicit publication. Saved hierarchy changes remain private in a revision-checked draft; members stay on the published revision. Excel export supports draft, published and historical revision snapshots. Permanent deletion uses dependency review and typed confirmation; Archive remains recoverable. |
| F9.4 | COMPLETED | Build Excel Import upload/map/preview/error/confirmation workflow. | Excel Import is a complete-replacement flow inside the selected curriculum: upload or round-trip exported workbook, validate metadata/sheets, preview additions/removals/reuse/issues, edit/delete rows, revalidate, and type REPLACE code. Commit creates a private replacement draft and never changes the member catalogue until explicit Publish changes. |
| F9.5 | COMPLETED | Build Import History list/detail/counts/row errors. | Import History is a tab of the same curriculum workspace with status, counts, mapping and row issues. No unauthorized retained-file download. |
| F9.6 | COMPLETED | Build Resource Library filters/preview/publication. | Protected screen 5 has server-backed search/type/status filters, pagination, preview and versioned publication. |
| F9.7 | COMPLETED | Build Add/Edit Resource upload/link/path mapping/accessibility fields. | Screen 6 maps exact paths and rights/accessibility metadata; Interactive uses the unified HTML upload/Code/Preview editor and saved sandbox preview. Later records supersede the original nine-mapping Gravity draft: published Light/Gravity upgrades and saved unpublished Rive testing drafts are recorded in [current Interactive status](#current-interactive-status--2026-10-14). Image/Video form/source rules unchanged; [handoff](backend/stage-9-interactive-html5.md). |
| F9.8 | PARTIAL | Build Student Management profile/enrollment/measured activity. | B4 searchable, paginated directory/profile and readable memberships plus B5 measured visit/session/question/resource-open summary; signed-in live browser validation remains. |
| F9.9 | COMPLETED | Build Teacher Management list/add/edit/expertise/review/publication. | Protected screen 8 has search/subject/status filters, pagination, declared/reviewed expertise and versioned publication; no login/booking. |
| F9.10 | COMPLETED | Build Activity Kit Management multi-topic links, cost/currency and publication. | Protected screen 9 has search/topic/status filters, pagination, uploads, multi-topic reuse and versioned publication; catalogue only. |
| F9.11 | PARTIAL | Verify admin views: keyboard/mobile, empty/loading/error, stale edits and denied access. | Production-mode mock browser covers typed full replacement → private draft → inline edits → history → explicit publish, B9 navigation/CTA, 390px overflow and import-screen axe audit. Rollback-only B4 database checks cover draft conflicts, published isolation before publish, replacement/export/publication, archive/restore, deletion and association blocking. Signed-in live browser/device and broader keyboard/screen-reader regression remain B10/F8. |

### F10 — Learner Explore panel and recommendation entry points

Status: **COMPLETED in development**. Steps: **5**. Owner explicitly authorized implementation after the plan/tracker update. [Delivery and runtime handoff](backend/stage-14-learner-explore.md). Target is the learner workspace `/`, not `/admin`. Reuse the existing shell, curriculum context, recommendation cards and viewers; do not recreate the reference's Home/Practice navigation.

| Step | Status | Work item | Acceptance condition / dependency |
| --- | --- | --- | --- |
| F10.1 | COMPLETED | Add compact top-right Explore CTA and responsive right-side panel. | Media, Teachers and Activity Kits tabs; header-aware positioning; desktop conversation reflow and narrow-screen drawer without composer overlap. Keyboard, focus return, Escape and expanded state supported; preserve conversation position. Contract audit B14.1 precedes integration.  2026-10-08: CTA, desktop reflow and narrow modal/focus/Escape verified at 1536px/390px. [Handoff](backend/stage-14-learner-explore.md). |
| F10.2 | COMPLETED | Implement independent Explore context, searchable filters and paginated results. | Default to current Study path; browsing does not change Study/LLM context. Accessible curriculum/level/subject/domain/topic/subtopic selection; optional Category filtering respects existing hidden-Category navigation. Parent changes reset invalid descendants. Curiosity asks for an accessible path rather than guessing. Separate panel filters from My Learning/editor state; loading/empty/retry states and full-dataset counts via B14.2.  2026-10-08: Independent path selection, Topic/Subtopic search, cascade reset, paging/search and Curiosity verified. [Handoff](backend/stage-14-learner-explore.md). |
| F10.3 | COMPLETED | Present compact catalogue items and reuse accessible viewers. | Compact video icon/title, appropriate image thumbnails, accurate availability and meaningful captions. Reuse image, GIF reduced-motion/Play/Pause, video fullscreen/close, teacher profile and kit guide. No autoplay, automatic launch/contact or provider-policy changes; B14.3 rechecks access before opening. Preserve filters/results/viewer-return position.  2026-10-08: Lazy authorized static thumbnails, compact video icons and existing media/kit/tutor viewers verified; GIF/native/external player suite passed. [Handoff](backend/stage-14-learner-explore.md). |
| F10.4 | COMPLETED | Link answer recommendations to the same Explore panel. | CTA browses current context; answer action opens its saved context, correct tab and optional highlighted item. Existing inline/card actions remain; no rewritten earlier decisions or duplicate automatic recommendations. Explore remains available with no recommendation; listing cards does not acknowledge recommendation display. No additional LLM call; answer generation remains independent.  2026-10-08: Saved-answer/recommendation entry points and focus-page support implemented; no browsing acknowledgements or history rewrites. [Handoff](backend/stage-14-learner-explore.md). |
| F10.5 | COMPLETED | Verify responsive, context, accessibility and conversation regressions; record handoff. | Desktop/narrow layouts, keyboard/focus, old-answer/current-context distinction, independent browsing, viewer return, rapid filter changes and search/paging beyond the first page pass. Existing Study, Curiosity, pins/recent and My Learning preserved. Record actual browser results and limitations; coordinate B14.5, retain F8/B10 physical-device/release gates.  2026-10-08: Explore/media/sidebar browser suites, typecheck/build and 17 web units passed; physical/live gates unchanged. [Handoff](backend/stage-14-learner-explore.md). |

**F10/B14 handoff — execution order:** B14.1 contract/context audit → B14.2 browsing services and F10.1 panel shell → B14.3 open-time access and F10.2–F10.3 results/viewers → B14.4 request/cache/activity handling and F10.4 answer entry points → B14.5/F10.5 integrated verification and handoff. All ten steps completed in development on 2026-10-08. API/rollback-only DB and production-browser checks passed. Manual API restart pending after automatic approval review blocked stopping its process. No schema migration, paid provider call or deployment; existing live-content/device/release gates remain. [Handoff](backend/stage-14-learner-explore.md).

## 4. Backend steps

Stages follow the source roadmap. Each stage includes tests and frontend integration where relevant; final-stage testing is not a reason to postpone access/security checks.

### B1 — Foundation and API contracts

Status: **COMPLETED**. Steps: **10**.

| Step | Status | Work item | Completion evidence / acceptance condition |
| --- | --- | --- | --- |
| B1.1 | COMPLETED | Inspect repository, member UI/service boundary and original curriculum workbook. | Input review records inspection; source workbook still needs normalization. |
| B1.2 | COMPLETED | Record direct-LLM MVP boundaries and excluded capabilities. | Scope and Stage 1 plans; individual accounts, no RAG/mastery/feedback. |
| B1.3 | COMPLETED | Define modular-monolith ownership, transactions and initial schema. | module-architecture.md; design only, not tables. |
| B1.4 | COMPLETED | Specify nine admin screens and assign implementation stages. | admin-panel-specification.md; UI not implemented. |
| B1.5 | COMPLETED | Implement FastAPI configuration, lifecycle, DB adapter, safe logs/errors and health routes. | app/main.py/core/health; only health mounted. |
| B1.6 | COMPLETED | Implement initial typed teaching contracts and foundation tests. | schemas.py; 16 tests passed 2026-09-25, covering mandatory curriculum_id and all optional Category/Subtopic combinations; 2 upstream deprecation warnings. |
| B1.7 | COMPLETED | Configure development Supabase connection and verify connectivity. | Prior SELECT 1 success recorded; recheck before migrations, no secrets in tracker. |
| B1.8 | COMPLETED | Finalize curriculum mapping and frontend adaptation contract. | 2026-09-25: mandatory dynamic Curriculum root; seven context fields, scoped ancestry/revisions (Subtopic made required on 2026-09-26) and frontend adapter acceptance cases reviewed. Sample content/normalization is B2 work. |
| B1.9 | COMPLETED | Review member/admin API examples, resource action, errors, retries, versions and capability handling. | 2026-09-25: final contract review completed; request/answer examples validated, preview and catalogue revisions distinguished, idempotency/access/capability boundaries reviewed. Detailed later-stage schemas retain their explicit gates. |
| B1.10 | COMPLETED | Record unresolved policies and accept Stage 1 handoff. | 2026-09-25: owner instructed completion of remaining foundation steps; review/handoff delivered. Project owner accountable, developer responsible for implementation; section 7 needed-by steps retained as decision deadlines. |

### B2 — Database and Excel curriculum import

Status: **COMPLETED**. Steps: **10**.

| Step | Status | Work item | Completion evidence / acceptance condition |
| --- | --- | --- | --- |
| B2.1 | COMPLETED | Inspect corrected workbook and agree normalization, limits, sheet mapping and row semantics. | 2026-09-25: final workbook accepted with 1,726 populated rows and five tolerated duplicate full paths; sheet mapping, plain-text hyperlink handling, normalization and parser limits recorded in `backend/stage-1/b2-import-profile.md`. |
| B2.2 | COMPLETED | Set up Alembic, development DB permissions and FLAME schema ownership. | 2026-09-25: live development connection/CREATE permission checked; `flame` schema created and owned by migration role; Alembic configured to this schema. Provider auth schemas untouched; RLS not claimed. |
| B2.3 | COMPLETED | Migrate curricula, owned levels/hierarchy and per-curriculum revisions with UUIDs, FKs and scoped uniqueness. | 2026-09-25: `4ade4490344f` applied; `20260925_05` adds nullable topic outcome. Two-curriculum isolation, null/categorized topic uniqueness and wrong-domain category rejection checked with rolled-back synthetic rows. |
| B2.4 | COMPLETED | Migrate member/admin, learning, conversation/request and lifecycle/activity foundations. | 2026-09-25: `cacbe880bb5f` applied; membership ancestry/uniqueness and request ownership/idempotency checked with rolled-back synthetic rows. No mastery tables. |
| B2.5 | COMPLETED | Migrate resources/associations, teachers/expertise and kits/multi-topic associations. | 2026-09-25: `902e0b18bb4f` and `20260925_04` applied; media references only, fixed-precision cost/currency checks, unique kit/resource/topic links and teacher subject ancestry checked with rolled-back synthetic rows. |
| B2.6 | COMPLETED | Implement safe workbook parser and server-side row/header/path validation. | 2026-09-25: bounded XLSX parser validates selected sheets, headers, required text, curriculum code/level, full-path duplicates and topic-outcome conflicts; ignores hyperlink metadata. Final workbook parses as 1,726 rows, five tolerated duplicates, zero issues. Final backend tests: 21 passed. |
| B2.7 | COMPLETED | Implement read-only catalogue preview with normalized full paths and bounded row errors. | 2026-09-25: internal admin-gated upload/preview stores file hash, selected sheet mapping, base revision and frozen rows; compares scoped existing paths, returns bounded preview rows and paginated errors. Full final workbook preview: 1,721 distinct paths, five duplicates, zero invalid. |
| B2.8 | COMPLETED | Implement transactional, idempotent commit and stale-preview protection. | 2026-09-25: internal commit locks owner/import/curriculum, replays matching keys, rejects changed keys and stale/invalid previews, writes one scoped revision transactionally, and reuses matching paths. Full 1,726-row commit and repeat preview (1,721 reused paths) verified then rolled back. |
| B2.9 | COMPLETED | Implement import-history storage/query and provenance/display-order preservation. | 2026-09-25: migration `20260925_06` applied; owner-scoped history/detail, row/error pages, plain-text source references, first-seen sibling display order and 30-day raw-file purge hook implemented. |
| B2.10 | COMPLETED | Add deterministic seeds, migration and importer integration tests. | 2026-09-25: deterministic rollback-only Supabase tests cover repeat import, idempotency, invalid/stale rollback, null/categorized paths, wrong ancestry, cross-curriculum isolation, two-topic kit, source text and retention. All migrations passed on a clean temporary database and `alembic check`; no public importer route mounted before B3 auth. |

### B3 — Individual authentication and admin access

Status: **COMPLETED**. Steps: **7**. Self-registration with email verification was selected on 2026-09-26. BFF/API identity flows, session model, guards, migrations and tests are implemented; live signup, confirmation, sign-in, first admin bootstrap, recovery, password reset and session revocation were verified in development. See [B3 activation notes](backend/stage-3-auth.md).

| Step | Status | Work item | Completion evidence / acceptance condition |
| --- | --- | --- | --- |
| B3.1 | COMPLETED | Choose self-registration or invitation/provisioning; confirm Supabase Auth flows, account fields, verification/activation, callbacks and controlled admin bootstrap. | Depends B1/B2; no public admin selection, institution or teacher login. |
| B3.2 | COMPLETED | Implement BFF-owned protected sessions, secure cookies and CSRF/origin defenses. | Opaque HttpOnly cookie, encrypted DB tokens, row-locked refresh, exact Origin plus CSRF checks; migration applied and rollback-only session test passed. |
| B3.3 | COMPLETED | Implement the chosen onboarding path, member sign-in/recovery/sign-out/refresh and profile mapping, including partial-onboarding recovery. | Live verified signup, login, recovery email/reset and new-password sign-in passed; profile creation, refresh/expiry and sign-out covered by rollback-only integration. |
| B3.4 | COMPLETED | Verify token issuer/audience/expiry/subject independently in FastAPI. | HS256/JWKS signature and issuer/audience/expiry/UUID subject/role validation tested, including invalid tokens. |
| B3.5 | COMPLETED | Implement ownership/role dependencies and least-privilege DB grants/RLS strategy. | Member/admin/owner guards and rollback-only access tests pass; Supabase client roles have no FLAME grants and identity RLS is enabled. A restricted runtime database role remains a production deployment gate. |
| B3.6 | COMPLETED | Protect all implemented catalogue/import/admin/member operations. | All mounted identity/member routes require BFF key and session as appropriate; catalogue/import/admin CRUD remain unmounted, with reusable member/admin/owner guards. |
| B3.7 | COMPLETED | Test onboarding success/failure/duplicates, member/admin/cross-member, expired/revoked sessions, CSRF and recovery. | 9 targeted B3 tests pass, including real database role/owner/session checks; web typecheck and five account-screen axe audits/two redirects pass; live recovery and two revoked sessions confirmed. |

### B4 — Curriculum administration, My Learning and student directory

Status: **COMPLETED in development**. Steps: **8**.

| Step | Status | Work item | Completion evidence / acceptance condition |
| --- | --- | --- | --- |
| B4.1 | COMPLETED | Implement published curriculum listing/tree/search with complete stable paths. | Depends B2/B3; uncategorized topics appear once; published Topics require Subtopics. |
| B4.2 | COMPLETED | Implement curriculum/child creation, curriculum publication and versioned rename/edit/archive operations. | Finalize ancestor-archive eligibility and continued-session/revision policy first; IDs/references/history preserved; conflicts and duplicate sibling names rejected. See module architecture and API lifecycle contract. |
| B4.3 | COMPLETED | Expose protected import preview/commit/history APIs and connect admin screens. | F9.3–F9.5; idempotency, stale preview and invalid rows surfaced. |
| B4.4 | COMPLETED | Implement My Learning addition and partial-path merge/deduplication. | Student-owned memberships; no institutional enrollment semantics. |
| B4.5 | COMPLETED | Implement hide/restore retaining history and identity. | Only curriculum/subject removal; confirmation and unchanged unrelated branches. |
| B4.6 | COMPLETED | Implement paginated admin student directory/profile/enrollment search. | Name/email/ID, status/date, active/hidden learning; no private chat or implicit deletion rights. |
| B4.7 | COMPLETED | Integrate expanded frontend tree/Library/My Learning/student screens through BFF. | F3/F4/F9.8; production fixtures replaced for these flows. |
| B4.8 | COMPLETED | Test refresh/sign-in persistence, paths, concurrent additions, archive and isolation. | Empty/error/search/restoration cases; no fabricated academic progress. |

### B5 — Conversations, student activity and data lifecycle

Status: **PARTIAL**. Steps: **9**.

| Step | Status | Work item | Completion evidence / acceptance condition |
| --- | --- | --- | --- |
| B5.1 | COMPLETED | Agree retention/deletion durations, draft policy and minimal activity definitions. | Depends B3/B4; pins optional; define backup expiry and privacy without inventing periods. |
| B5.2 | COMPLETED | Implement Study/Curiosity sessions with authoritative mode/path/version snapshots. | Reject mismatched IDs; owned context remains stable after curriculum rename. |
| B5.3 | COMPLETED | Implement messages/history pagination/recent/resume and bounded-history interface. | 2026-10-14: rollback-only B5 history pagination, owner/mode/path isolation, hidden-learning retention and bounded-history checks passed. Signed-in Study/Curiosity reload, message restoration and follow-up passed; interrupted-worker recovery includes prior owned turns. |
| B5.4 | COMPLETED | Implement idempotent request/turn state and concurrent retry recovery. | Finalize API request-recovery rules first: failed retries, stale pending claims, key retention/expiry and distinct concurrent questions. Test crash/timeout recovery; same payload reuses result, different payload conflicts; no duplicate turns. |
| B5.5 | COMPLETED | Implement minimal deduplicated activity recording and aggregates. | 2026-10-14: rollback-only B5 visit deduplication/question/session aggregates and B9 resource-open deduplication/access checks passed. Admin summaries expose counts rather than private chat or mastery; broad pilot/browser acceptance remains B10/F9.8. |
| B5.6 | COMPLETED | Implement confirmed member conversation deletion. | Owned primary session, messages, answer requests and activity are removed together; residual backup expiry is a B5.7 deployment check. |
| B5.7 | PARTIAL | Implement confirmed account deletion/revocation across module-owned private data. | Preserve shared catalogues/assets; document log/backups handling. |
| B5.8 | PARTIAL | Connect resumable/history/delete UI and admin measured activity. | F2/F5/F9.8; drafts honestly local if not selected for persistence. |
| B5.9 | COMPLETED | Test isolation, retries, concurrent writes, hide/restore and deletion lifecycle. | 2026-10-14: B5 lifecycle/isolation/hide/restore/replay checks, two-worker claim test, B7 terminal failure/interrupted lease recovery and signed-in Study/Curiosity continuation passed. Synthetic UUID concurrency fixtures cleaned; managed retention/scheduling remains B5.7. |

B5 development evidence (2026-09-26): migration `20260926_12` added request leases/fencing and passed Alembic check. Rollback-only PostgreSQL tests cover Study path validation, stable snapshots after rename, revision conflicts, owner isolation, session pagination, bounded owner-only history, hide/restore history, activity deduplication, request replay after revision, expired-claim fencing, terminal failure replay, conversation deletion, local account removal, and mocked Supabase Auth deletion with pending-receipt retry. A separate two-worker claim test passed and cleaned up its UUID fixtures. The BFF/browser flow against a mock API passed saved-session creation, reload, paginated message history, in-dialog load failure/retry and confirmed deletion; admin shows aggregate activity without text. API tests, web typecheck, unit tests and build passed. At that date, the public ask route remained B7 work. The 2026-09-27 B7 update below supersedes that transport status; full restored-session continuation remains open. The owner selected a 30-day maximum for backup and operational-log copies, with immediate primary learning-data deletion; a tested maintenance command purges completed receipt/tombstone identifiers after 30 days. The server-only Supabase deletion credential is configured in development; current secret and legacy service-role key headers are covered by backend tests. One disposable Auth user was created and deleted through the FLAME account route, with a 200 deleted result, scrubbed/inactive local profile, and subsequent Supabase admin lookup returning 404. Managed backup/log configuration, scheduled maintenance, and live signed-session browser history remain outstanding. See the B5 contract in api-contracts.md.
### B6 — Curriculum context and prompt construction

Status: **COMPLETED**. Steps: **6**.

| Step | Status | Work item | Completion evidence / acceptance condition |
| --- | --- | --- | --- |
| B6.1 | COMPLETED | Confirm Study level semantics and Curiosity response policy. | Study uses validated curriculum paths; open Curiosity has an under-15 response ceiling, no account-age gate and no subject/topic resolution. |
| B6.2 | COMPLETED | Implement authoritative curriculum lookup/path validation and optional metadata loading. | Descriptions/outcomes may be absent; no invented metadata or evidence. |
| B6.3 | COMPLETED | Define versioned KG–5 teaching profiles and under-15 Curiosity response rules. | Vocabulary/language/length/examples/mathematics; lower learner level when available; no expert explanations or teaching-settings UI. |
| B6.4 | COMPLETED | Build deterministic prompt assembly with bounded history/token budgets. | Server policy separate from untrusted question/history; integrate B5 interface. |
| B6.5 | COMPLETED | Enforce published curriculum boundaries in Study and allow general questions in Curiosity. | Study revalidates full path/revision. Open Curiosity needs no topic check or resolved subject and keeps under-15 prompt rules. Historical topic-check/clarification records remain owned and readable. |
| B6.6 | COMPLETED | Add representative educator-informed prompt fixtures and adversarial tests. | No provider needed for prompt unit tests; no source-grounding claims. |

B6 development evidence (2026-09-26): migrations `20260926_13` and `_14` add owned pending clarification and durable, idempotent topic-check events. Study revalidates its pinned published seven-ID path; Curiosity resolves exact imported Topic/Subtopic phrases against current published paths, returns an under-15-safe out-of-scope response or candidate clarification, and never guesses unknown Level labels. The saved-session BFF shows pending choices and paginated topic-check history after reload. A ready event persists its validated full path, revision and resolved subject/topic IDs for B7 recommendations. New questions cancel prior pending choices; choices and checks replay safely; expiry, owner checks, topic switches and session deletion have rollback-only PostgreSQL coverage. Five authored draft cases identify exact workbook sheets/rows and expected facts/constraints; they are candidate cases for later educator review, not approved answers. Prompt policy separates untrusted data and bounds history/question size. The DB-enabled backend suite passed 39 tests (two concurrency-only skipped, two upstream deprecation warnings); Alembic drift check, web typecheck, 11 unit tests, build and mock-API browser flow passed. The 2026-09-27 open Curiosity update below supersedes the curriculum-bound Curiosity gate and BFF flow described in this historical evidence; B8 evaluates actual answer quality. See [B6 handoff](backend/stage-6-context.md).

### B7 — Direct LLM gateway and answer service

Status: **COMPLETED in development**. Steps: **7**. Verified 2026-10-14; hosted runtime acceptance remains B10.

| Step | Status | Work item | Completion evidence / acceptance condition |
| --- | --- | --- | --- |
| B7.1 | COMPLETED | Select provider/model and configure secret credentials, quota and budget. | API `.env` loads the server-only key and `gpt-6-luna`; owner confirms USD $5/month project hard spend limit, with project model limit 200,000 TPM/500 RPM. Local 100 daily member requests and 1,500 output tokens configured; live calls passed. |
| B7.2 | COMPLETED | Implement internal provider adapter with explicit timeouts/retry/cancellation limits. | No SDK calls from controllers; no database transaction held during network generation. |
| B7.3 | COMPLETED | Implement AnswerService orchestration across ownership/context/history/prompt/gateway. | Use B3/B5/B6; enforce session context and supported explain action. |
| B7.4 | COMPLETED | Validate complete structured blocks and assign server-owned provenance/IDs. | direct_llm/model_generated/grounded=false/confidence=null/citations=[]; no model authority. |
| B7.5 | COMPLETED | Persist request results, versions, usage, latency and safe failure state. | Live Study turn saved version/model, 188 input and 13 output tokens, latency and one user/assistant pair; same-key replay made no second call. Owner confirms project hard limit; hard-limit 429 is handled without retry. |
| B7.6 | COMPLETED | Expose authenticated ask endpoint and integrate BFF/composer/rendering. | F5/F6; initial supported text-block subset; resource objects remain gated until B9. |
| B7.7 | COMPLETED | Test stubs and controlled live calls, throttling/outages/malformed output/cancellation/retries. | 2026-10-14: real HTTP timeout/disconnect/503 transport checks and malformed provider-shape guards passed; live configured-provider probe observed two ReadTimeouts and bounded provider_unavailable. Rollback-only terminal replay/lease recovery plus signed-in Study/Curiosity reload/follow-up and pending-response reload recovery passed. Client disconnect recovery does not promise provider cancellation; hosted function termination remains B10. |

B7 handoff and local key template: [answer service](backend/stage-7-answer-service.md). Development transport/recovery/continuation verification completed October 14; hosted function termination/load remains B10. The owner-reported USD $5/month hard spend limit is retained.

### B8 — Response quality and capability handling

Status: **PARTIAL**. Steps: **6**.

| Step | Status | Work item | Completion evidence / acceptance condition |
| --- | --- | --- | --- |
| B8.1 | PARTIAL | Agree educator-reviewed evaluation cases and measurable acceptance thresholds. | Draft matrix/rubric in `backend/stage-8-evaluation.md`; owner and educator approval pending. |
| B8.2 | PARTIAL | Evaluate Study profiles/catalogue adherence and open Curiosity quality across subjects and languages. | 17 Study-only live model samples and two override attempts recorded for founder review. The final workbook is now published in development, and one rollback-only live API answer on an imported KG path passed with resolved IDs and identical replay. Signed-in Study browser verification and founder factual/age scoring remain. Curiosity is open and unchanged; its quality evaluation is outside this implementation pass per owner direction. |
| B8.3 | COMPLETED | Implement consistent unsupported outcomes and UI explanations. | Owned capability preflight and idempotent ask outcome; Study/Curiosity browser flow explains textbook evidence, official grading, file/media and progress limits without model calls. |
| B8.4 | PARTIAL | Harden schema/length/content validation and policy-override resistance. | Block size/count/ID, control-character, obvious fabricated-authority and level-specific Study word-cap checks pass; two live Study overrides passed the guard, while founder factual/age scoring remains. |
| B8.5 | PARTIAL | Test quotas/outages/bad outputs and answer/resource status/retry contracts. | Stubbed daily quota, temporary 429/timeout, hard spend-limit 429, malformed-output replay and no-duplicate-turn checks pass; live outages and B9 resource outcomes remain. |
| B8.6 | NOT STARTED | Record evaluation results, fixes and owner/reviewer acceptance. | No guaranteed-correct claims; unmet required thresholds remain open. |

B8 implementation and next instruction: keep B8 **PARTIAL** while B8.3 is complete, B8.1/B8.4/B8.5 are partial, and B8.2 has a provisional Study-only live baseline without founder scoring; B8.6 has no acceptance evidence. Use the [evaluation rubric](backend/stage-8-evaluation.md) and [Study review packet](backend/stage-8-study-review-2026-09-28.md) for founder approval of expected facts and thresholds, score the recorded live outputs, fix failures, then record reviewer acceptance. The B7 [handoff](backend/stage-7-answer-service.md) records the configured model, key template and live smoke evidence. B9 resource outcomes stay pending until actual catalogue assets exist. B9.1–B9.10 are implemented in development. B9.11 has rollback-only database and mock-browser coverage; live private Supabase Storage, approved catalogue assets, signed-in browser and device acceptance remain.

### B9 — Resource library, teachers and activity kits

Status: **PARTIAL**. Steps: **11**.

| Step | Status | Work item | Completion evidence / acceptance condition |
| --- | --- | --- | --- |
| B9.1 | COMPLETED | Agree formats/size/link/interactive policy, distribution rights and durable storage. | [B9.1 resource policy](backend/stage-9-resource-policy.md) approved by owner 2026-09-28; empty external-host allowlist until specific hosts are approved. |
| B9.2 | COMPLETED | Implement validated uploads/links and resource metadata/path associations. | Admin upload/draft validation and owned associations; Interactive accepts bounded self-contained HTML/HTM and unpublished pending-media drafts. Local storage resolves named activity folders while preserving opaque keys and legacy compatibility. October 12–13 records include approved Light/Shadow publication, published Phaser upgrades and saved Rive drafts; [current Interactive status](#current-interactive-status--2026-10-14). Latest recorded applied migration is `20261012_30`; deployed private bucket remains B9.11. |
| B9.3 | COMPLETED | Implement versioned draft/edit/publish/unpublish and admin catalogue filters. | Optimistic versions, search/type/status filters and rights, availability, published-path, asset and accessibility publication gates. |
| B9.4 | COMPLETED | Implement exact authorized topic/type/level/version resource lookup. | Member-only published Topic/Subtopic/type lookup checks current curriculum revision and returns ordinary `no_results`; no LLM call. |
| B9.5 | COMPLETED | Implement delivery URLs, expiry/refresh and withdrawn/missing-asset handling. | Existing Image/Video five-minute signed delivery unchanged. Interactive HTML uses authorized bounded JSON document delivery and scoped path/revision/version rechecks; raw executable HTML URLs are blocked. Local lifecycle and mocked private-cloud boundaries passed; live Supabase remains B9.11. |
| B9.6 | COMPLETED | Integrate Resource Library/editor and member cards/viewers. | BFF-backed editor/viewers and activity; shared sandboxed Interactive Preview/Explore/recommendation viewer includes Restart, fullscreen and cleanup. October 12 records approved Light/Shadow publication and scoped open/HTML delivery; October 13 records Phaser/Rive sandbox and saved draft previews. Weather World remains file-only. See [current Interactive status](#current-interactive-status--2026-10-14); full signed-in learner/cloud/device acceptance remains. |
| B9.7 | COMPLETED | Implement teacher catalogue CRUD/publication/search and reviewed/declared expertise. | Versioned admin CRUD, subject filter, exact subject/topic expertise validation, declared/reviewed status and publication; no mastery score. |
| B9.8 | COMPLETED | Implement intent-based media, activity-kit and explicitly requested tutor recommendations for validated Study answers. | Owner MVP update 2026-10-03: question/concept relevance, one primary plus at most one distinct useful alternative, saved ID/version display history, stable decisions and open-time rechecks. Tutors use published subject/topic expertise and accurate unknown/listed availability; no contact/booking. Open Curiosity remains unmapped. |
| B9.9 | COMPLETED | Implement multi-topic activity-kit CRUD/publication/filtering. | One versioned kit reuses multiple Topic associations; upload, materials, supervision, cost/currency and publication constraints pass rollback-only checks. |
| B9.10 | COMPLETED | Integrate Teacher and Activity Kit Management screens. | BFF-backed protected screens, filters and pagination; mock-browser navigation passed. |
| B9.11 | PARTIAL | Test publication/access/expiry/upload safety, intent-based tutor/media selection and multi-topic kit integrity. | Existing rollback/mock and approved local Light/Shadow, Phaser/Rive checks remain. October 14: private bucket synthetic access checks and direct 4,923,512-byte upload/validation/replay/private export passed; owner/size/hash/media rejection and resource regressions passed. Real catalogue cloud migration/hosted delivery, full signed-in learner expiry/withdrawal, physical-device/accessibility/educator and legacy regression acceptance remain. Cat/Matter are testing drafts; Weather World has no resource row. [Current Interactive status](#current-interactive-status--2026-10-14) and [handoff](backend/stage-9-interactive-html5.md). |

**MVP recommendation update (2026-10-03).** New Study answers reuse the existing LLM answer call for optional validated intent metadata, with a deterministic fallback. Catalogue associations retrieve candidates; concept/intent/grade/language checks select at most one primary and one distinct useful alternative. New media/kit/tutor decisions and shown ID/version history persist in the existing recommendation JSON. Earlier saved decisions are preserved. Media retains the existing viewers and standard provider policy; kit/tutor views recheck eligibility without launching activities or contacting anyone. 42 targeted backend tests, production build and desktop/narrow browser regressions passed. No schema migration. This October 3 snapshot predates B12: optional structured grade/language metadata now exists for resources/kits; student prerequisite tracking and live tutor schedules remain absent; materials/supervision and accurately labelled catalogue availability are used. See [implementation and verification](../work/mvp-learning-recommendations.md). B9.11 live-storage/approved-content acceptance remains open.

**B9 handoff — next execution order.** B9.1–B9.10 are complete in development. The approved [resource policy](backend/stage-9-resource-policy.md) governs the remaining live checks; local storage and mock-browser evidence do not close B9.11.

**Interactive follow-up handoff (reconciled 2026-10-14).** [How it was built and how to reproduce it](backend/stage-9-interactive-html5.md): existing upload/storage/metadata/mappings → authorized HTML JSON delivery → sandboxed viewer. Its October 9 Gravity draft/version and port-8001 snapshot are historical: October 12–13 publication, Phaser/Rive and prototype records are summarized in [current Interactive status](#current-interactive-status--2026-10-14). Use canonical API 8000 / web 3000 through the root launcher. Next: full signed-in learner verification of approved published activities → live private-cloud HTML checks → physical-device/accessibility/educator and regression acceptance. Cat/Matter remain unpublished; Weather World remains unregistered. B9.11 stays PARTIAL and totals remain unchanged.

The 2026-09-30 Curriculum Catalogue workspace enhancement is tracked under B4/F9. It improves the shared admin shell used to reach B9 screens, but it does not change the B9.11 storage and licensed-asset acceptance gates below.

1. **Operations:** provision a private Supabase Storage bucket and configure the API for `FLAME_RESOURCE_STORAGE_BACKEND=supabase` and `FLAME_RESOURCE_STORAGE_BUCKET` using server-only Supabase credentials. Verify private upload, object presence and five-minute signing in the development environment. Keep `FLAME_RESOURCE_ALLOWED_HOSTS` empty unless the owner approves specific external media hosts.
2. **Project owner/admin:** provide representative assets with recorded distribution rights, attribution and accessibility metadata. Upload drafts, associate exact published Topic/Subtopic paths, then publish through the protected Resource Library. Use an approved external link only after its host is allowlisted. No sample asset is presumed licensed.
3. **Developer/reviewer:** in signed-in member and admin browsers, verify exact lookup, no-results, cards/viewers, URL renewal after expiry, missing assets, withdrawal, duplicate-safe open/play activity, explicitly requested subject/topic-matched tutor profiles with unknown/listed availability, Curiosity with no teacher match, and suitable practice kits across mapped topics. Check keyboard/mobile states and non-admin denial. Preserve current published-curriculum revision checks and confirm no storage key or filesystem path reaches members.
4. **Acceptance:** rerun rollback-only B9 tests, web typecheck/build and browser flows with live storage, then record concrete results in this tracker. The previous targeted B7/B9 integration run passed 6 tests, mock B4–B9 browser and web build passed, and Alembic reported no drift. The full backend suite was interrupted while stalled in a B6 integration test on the populated development catalogue; it is not counted as a passing gate. Mark B9.11 complete only after the live checks above; carry broader signed-in journeys and operational release gates into B10/F8/F9.11.

### B10 — Integration, evaluation and pilot readiness

Status: **PARTIAL**. Steps: **8**. Vercel preparation started 2026-10-14; pilot acceptance remains open.

| Step | Status | Work item | Completion evidence / acceptance condition |
| --- | --- | --- | --- |
| B10.1 | PARTIAL | Complete contract integration and remove production fixture dependencies. | 2026-10-14: production fixture exclusion verified; resource/curriculum/bulk private-transfer contracts integrated with retry receipts. Full signed-in member/admin contract journeys and remaining F8/F9/B11 acceptance remain. |
| B10.2 | PARTIAL | Run migrations, unit/integration/browser and full member journeys. | 2026-10-14: default backend/frontend/build checks, 36 rollback-only transfer/resource/curriculum/bulk checks, and production import/sidebar regressions passed. No migration added or applied. Full hosted sign-in→learning→media/deletion journeys and legacy B4 browser harness modernization remain. |
| B10.3 | PARTIAL | Verify all nine admin screens and per-endpoint non-admin denial. | 2026-10-14: all 72 registered admin operations reject ordinary members before body validation/storage; isolated production import/history/publication/conflict and resource tests recorded below. Full nine-screen signed-in hosted acceptance, Teachers/Kits/Students and physical-device checks remain. |
| B10.4 | PARTIAL | Close quality/privacy/accessibility/supported-device acceptance gaps. | 2026-10-14: production fixture/progress exclusion and unsupported attachment retention verified; no private transfer bytes go through the BFF. B8 educator scoring, full privacy/retention and supported-device/screen-reader acceptance remain. |
| B10.5 | PARTIAL | Configure approved hosting environments and secrets, monitoring and rate limits. | 2026-10-14: two unchanged Vercel roots, app.main:app entry point, hosted Sheets JSON credentials and operating guide prepared. Private bucket and direct media/workbook/ZIP uploads/exports implemented; live 4,923,512-byte upload/replay/private export passed. Actual Vercel environments/secrets, restricted runtime role, monitoring, scheduling and full-size provider/hosted checks remain. |
| B10.6 | NOT STARTED | Verify backups/restoration, retention/deletion and resource withdrawal. | Record recovery evidence and backup expiry; preserve shared data. |
| B10.7 | PARTIAL | Document release/rollback procedures, operational support and outstanding risks. | 2026-10-14: Vercel release/paired rollback and operations guidance prepared in VERCEL-DEPLOYMENT.md; GitHub Actions local checks added. Hosted rollback rehearsal, recovery/support ownership and accepted release risks remain. |
| B10.8 | NOT STARTED | Obtain owner pilot acceptance and separate authorization for deployment. | Evidence-backed release decision; MVP completion does not imply RAG/mastery completion. |

### B11 — Modular recommendation migration and response composition

Status: **COMPLETED in development**. Steps: **11**. Verified 2026-10-07; no deployment or data migration. [Technical handoff and rollback](backend/stage-11-modular-migration.md).

**Goal:** separate recommendation coordination from media ownership, retain independent Media/Teachers/Kits catalogue boundaries, and add a small learning-response composer. Keep one FastAPI application and one PostgreSQL database. Preserve current behavior, APIs, saved conversations and publication/access/concurrency rules throughout migration.

**Entry gate:** existing B5/B7/B9 interfaces and the current MVP recommendation implementation are available. Capture a fresh affected-test baseline before moving code. B9.11 live storage acceptance and B8 quality review remain independent open gates; they are not prerequisites for a behavior-preserving module extraction. Final integration must include B11 before B10 acceptance.

| Step | Status | Work item | Completion evidence / acceptance condition |
| --- | --- | --- | --- |
| B11.1 | COMPLETED | Audit current module dependencies and capture the migration baseline. | 2026-10-07: Full tracker/dependency audit and baseline source snapshot; 42 baseline passes plus one obsolete GIF fixture assertion recorded. [Handoff](backend/stage-11-modular-migration.md). |
| B11.2 | COMPLETED | Define explicit module interfaces and shared candidate/decision/composition contracts. | 2026-10-07: Typed candidate/decision/composition contracts validated with message/ID/version guards. [Handoff](backend/stage-11-modular-migration.md). |
| B11.3 | COMPLETED | Extract recommendation orchestration into app/modules/recommendations/. | 2026-10-07: New recommendations owner registered once; original route and selection imports remain compatibility adapters. [Handoff](backend/stage-11-modular-migration.md). |
| B11.4 | COMPLETED | Expose Media candidate and open-time eligibility services from the existing resources module. | 2026-10-07: Media-owned candidate service retains publication/mapping/source/storage checks and existing players. [Handoff](backend/stage-11-modular-migration.md). |
| B11.5 | COMPLETED | Expose Teacher candidate and profile eligibility services. | 2026-10-07: Teacher-owned expertise/language/availability service; known-unavailable profiles excluded, unknown labels retained. [Handoff](backend/stage-11-modular-migration.md). |
| B11.6 | COMPLETED | Expose Kit candidate and guide eligibility services. | 2026-10-07: Kit-owned publication and candidate/guide services; requirements disclosed, no activity launch or commerce. [Handoff](backend/stage-11-modular-migration.md). |
| B11.7 | COMPLETED | Isolate recommendation persistence and repetition-history access. | 2026-10-07: Existing table/JSON moved to owning repository with one class alias; legacy reads and cleanup/FK ordering verified; Alembic clean. [Handoff](backend/stage-11-modular-migration.md). |
| B11.8 | COMPLETED | Introduce a small learning-response composer after module interfaces and history are verified. | 2026-10-07: Composer uses the existing teaching call and separate selection request; pending/none/unavailable and replay/quota isolation verified. [Handoff](backend/stage-11-modular-migration.md). |
| B11.9 | COMPLETED | Integrate composition with existing endpoints and frontend adapters. | 2026-10-07: Original URLs/root fields preserved; frontend handles legacy/new envelopes, mismatched IDs, pending and failures. [Handoff](backend/stage-11-modular-migration.md). |
| B11.10 | COMPLETED | Verify behavior parity, failure isolation and authorization across the migrated modules. | 2026-10-07: 53 backend tests, 17 frontend units/build and three browser suites passed; obsolete B4 Saved Conversations harness remains B10 work. [Handoff](backend/stage-11-modular-migration.md). |
| B11.11 | COMPLETED | Complete the module handoff and rollback/cutover review. | 2026-10-07: Technical ownership/contracts/compatibility/rollback documented; API restarted; no schema migration or deployment. [Handoff](backend/stage-11-modular-migration.md). |

### B12 — Recommendation metadata and measured improvement cycle

Owner-authorized 2026-10-07 after B11. This bounded stage adds optional catalogue metadata, automated evaluation, targeted ranking changes and local measurements. Educator approval and production load acceptance remain separate B8/B10 gates. [Implementation and handoff](backend/stage-12-recommendation-quality.md).

| Step | Status | Work | Evidence / remaining boundary |
| --- | --- | --- | --- |
| B12.1 | COMPLETED | Add validated optional recommendation metadata to Media, Teachers and Kits and their editors. | Migration `20261007_25` applied; existing data preserved; version/validation/serialization tests and browser persistence checks pass. |
| B12.2 | COMPLETED | Provide repeatable representative evaluation and educator review packet. | Twelve synthetic cases pass; metadata-omitted ablation passes ten. Educator review is pending under B8. |
| B12.3 | COMPLETED | Use concepts, synonyms, explicit grade/language suitability and purpose boosts in ranking. | Force/gravity, repetition, exclusions and existing response/access/history integration tests pass; prior saved decisions preserved. |
| B12.4 | COMPLETED | Measure ranking and query behavior, fix confirmed retrieval overhead, and record handoff. | Eight-tutor fixture: nine SELECTs reduced to two; 100/1,000/5,000-candidate ranking measurements recorded. Twenty backend tests, 17 web units, build and Resource Library browser suite pass; HTTP/LLM load acceptance remains B10. |

### B13 — Additive import/export for Media, Teachers, Students and Kits

Owner-authorized 2026-10-07. Preserve existing nonempty data, merge missing draft details/list values and valid mapping additions, never replace media or publish automatically. [Handoff](backend/stage-13-bulk-transfer.md) · [Samples and folder guide](bulk-import-samples/README.md).

| Step | Status | Work | Evidence / boundary |
| --- | --- | --- | --- |
| B13.1 | COMPLETED | Define workbook/package contracts and additive duplicate matching. | Automatic keys for new rows; exported IDs/keys preserve identity; topic labels remain separate from curriculum mappings. Sheets uses row-tracking metadata and stable bindings; conflicting identity/type or ambiguous tracking blocks confirmation. Existing nonempty FLAME values remain authoritative. |
| B13.2 | COMPLETED | Implement four catalogue imports with validation, staging and atomic confirmation. | Durable previews/receipts, latest snapshot/version checks, retry replay, cancellation and pending-student linking. Resource Sheets connector persists owner-scoped connections, reviews exports/new rows/removals and requires separate exact-resource deletion consent. Applied migration `20261012_30`; manual sync, no unattended deletion. |
| B13.3 | COMPLETED | Implement Excel/media export and downloadable live templates/sample packages. | Four catalogue exports/sample packages and path references retained. Sheets Image/Video/Interactive template has gridlines, header instructions/examples and applicable validation through row 2001. Grades/version write as numbers and publication as boolean; IDs stay text. HTML/assets/private paths are retained in FLAME. |
| B13.4 | COMPLETED | Integrate preview/confirmation/recovery and downloads into all four admin tabs. | Existing four-module transfer UI plus saved Sheets selection, column warnings/errors, incoming/outgoing/deletion review and pending-write retry. Invalid rows visibly disable confirmation; Validate again replaces stale previews. Existing same-type/same-URL video sources are retained during provider outages; changed/new sources still validated. |
| B13.5 | COMPLETED | Verify data preservation, security/retention boundaries and publish development handoff. | Earlier bulk/auth/build/browser evidence retained. Latest typed-output connector/Sheets suite: 10 tests passed; subsequent provider-outage regression: 1 passed; TypeScript passed. Live linked Sheet read and actual pending payload re-comparison verified, with no live writes/deletions during checks. End-to-end confirmed sync acceptance, max-size production load and cleanup scheduling remain. [Connector handoff](GOOGLE-SHEETS-CONNECTOR.md). |



**Target ownership (within the existing application):**

```text
app/modules/
  teaching/          LLM explanations, answer validation and quota/replay
  resources/         Media catalogue, storage, mapping and playback
  teachers/          Tutor catalogue, expertise and listed availability
  activity_kits/     Kit catalogue, requirements and guide availability
  recommendations/  Intent, candidate ranking, decisions and shown history
  learning_response/ Small composer and composed-result contract
```

Catalogue services provide eligibility-filtered candidates through explicit interfaces; recommendations chooses candidates; the composer assembles the explanation and decision. Recommendation persistence belongs to recommendations; media/teacher/kit records remain with their existing modules. Shared primitive contracts must not introduce circular dependencies. Folder presence alone is not completion evidence.

**B11 handoff — execution order:** audit/contracts (B11.1–B11.2) → extraction (B11.3) → catalogue interfaces (B11.4–B11.6) → history compatibility (B11.7) → composer (B11.8) → endpoint/frontend adapters (B11.9) → regression evidence (B11.10) → handoff/rollback (B11.11). All B11 steps completed in development on 2026-10-07. Existing B5/B7/B8/B9.11/B10 acceptance remains open; the obsolete full B4 browser harness needs modernization.

### B14 — Member catalogue browsing and independent item access

Status: **COMPLETED in development**. Steps: **5**. Companion frontend track: F10. [Contracts and verification](backend/stage-14-learner-explore.md). Reuse B9 catalogue ownership, B11 module interfaces/composition and B12 metadata. Manual browsing lists eligible mapped content; recommendation ranking still chooses a bounded set for the specific question. Do not use selected-recommendation-only opening as authorization for arbitrary catalogue items.

| Step | Status | Work item | Acceptance condition / dependency |
| --- | --- | --- | --- |
| B14.1 | COMPLETED | Audit member listing/open routes and define browse/context contracts. | Document reusable resource APIs and missing teacher/kit browse capabilities; define IDs, versions, publication revision, search/filter/pagination totals, mapping coverage and honest grade/language/availability fields. Define authorized path selection and saved-answer context handling. No private storage keys exposed; assess schema needs before proposing any migration.  2026-10-08: Member browse/context/open contracts and access/module boundaries documented; no migration needed. [Handoff](backend/stage-14-learner-explore.md). |
| B14.2 | COMPLETED | Implement member browsing through catalogue-owned query services and BFF adapters. | Authenticated server-side full-dataset filtering/paging for Media, Teachers and Kits, using current published IDs/revisions. Topic-wide resources/kits cover descendants; direct Subtopic links do not cover siblings. Teacher expertise respects exact Subject/Topic ownership. Enforce publication, availability, access, suitability, kit requirements and source eligibility; unmapped/deleted/draft items excluded. Never depend on admin endpoints or intent-ranking to list the catalogue.  2026-10-08: Owner eligibility reused; exact paths, suitability, 130-item paging/search and catalogue exclusions verified. [Handoff](backend/stage-14-learner-explore.md). |
| B14.3 | COMPLETED | Provide independent browse item-opening validation and reuse delivery/profile/guide services. | Recheck member access, selected path/revision, mapping, version, publication/availability and playback eligibility at open time. Stale/withdrawn content returns an actionable error without interrupting the answer. Authorized image/GIF/video, teacher and kit opening works without a saved recommendation; preserve current storage expiry and provider rules.  2026-10-08: Independent open and scoped delivery recheck path/revision/version; foreign-answer and stale/withdrawn rejection pass. [Handoff](backend/stage-14-learner-explore.md). |
| B14.4 | COMPLETED | Bound browsing overhead and preserve activity/history semantics. | Lazy requests, bounded paging/cache keyed by member access scope/path/revision/filter, appropriate invalidation and no cross-member or long-lived signed-URL reuse. Frontend cancels/discards obsolete responses. Record genuine open/play separately from listing; reuse existing activity/CSRF serialization. Manual listing never rewrites earlier decisions or suppresses automatic recommendations.  2026-10-08: Single read-only ancestry, abort/generation guards, bounded component cache and existing activity implemented; two SELECTs for Topic-only media. Large-topic/remote-storage load remains B10. [Handoff](backend/stage-14-learner-explore.md). |
| B14.5 | COMPLETED | Verify access, mapping, stale-state recovery and measured performance; publish handoff. | Isolated tests cover all three catalogues, inherited/direct mapping, expertise/unknown availability, unpublished/unmapped/inaccessible/unavailable exclusion, path changes, stale versions, paging and manual open authorization. Measure representative query counts and HTTP latency; no extra LLM request or answer dependency. Coordinate F10.5 browser verification; document commands, results and remaining live-content/device/release limits.  2026-10-08: 26 affected backend tests passed with DB enabled; focused DB rerun eight passed; latest DTO unit check seven passed/one opt-in DB skip. Local fixture median 127.74ms/max 317.66ms; browser/build evidence recorded. [Handoff](backend/stage-14-learner-explore.md). |

**Scope boundaries:** no new recommendation platform, vector infrastructure, microservices, booking/payment, mastery, automatic topic switching or provider overhaul. Existing B5/B7/B8/B9.11/B10 gates remain open. Live approved assets and device acceptance cannot be closed with synthetic tests. No new schema is assumed until B14.1 establishes a need.

## 5. Execution order and dependency gates

| Delivery batch | Work to execute together | Gate / review result |
| --- | --- | --- |
| A — Finish foundation review | B1.8–B1.10; confirm F3 mapping and F9 forms | Dynamic Curriculum-root model and provisional contracts reviewed; sample cleanup deferred to B2; deferred policies have deadlines. |
| B — Persist catalogue safely | B2.1–B2.10 | Repeatable migrations and tested importer services. Importer remains internal until protected. |
| C — Protect identity and administration | B3; F2.3; F9.1–F9.2 | Member/admin auth and denial tests pass. |
| D — Curriculum and enrollment | B4; F3; F4; F9.3–F9.5; enrollment part of F9.8 | Real hierarchy/import/My Learning survive reload and restoration. |
| E — History/activity/lifecycle | B5; F2.4; F5.3; remaining F9.8 | Owned history, retry safety and deletion/activity behavior demonstrated. |
| F — Teaching context | B6; prepare B8 evaluation set | Versioned level-aware prompts and missing-context policy tested. |
| G — Answers and quality | B7/B8; F5.4–F5.5; F6.5 | Validated direct answers, safe failures and agreed quality acceptance. |
| H — Resource/teacher/kit catalogues | B9; F7; F9.6–F9.7/F9.9–F9.11 | Development implementation complete; execute the B9 handoff above for live storage, approved assets and signed-in acceptance before closing B9.11. |
| H1 — Modular recommendation migration | B11.1–B11.11; existing B5/B7/B9 interfaces | Behavior-preserving extraction, catalogue eligibility interfaces, saved-history compatibility and a nonblocking composer accepted before final B10 integration. No microservices or new database required. |
| H2 — Recommendation quality and bulk transfer | B12; B13 | Complete in development on 2026-10-07; educator, production-load/retention and release gates remain separate. |
| H3 — Learner Explore workspace | B14.1–B14.5; F10.1–F10.5 | Development completed 2026-10-08 with API/DB/browser evidence; October 12 managed startup supersedes the earlier pending restart. B10 full signed-in/live-content/device acceptance remains. |
| I — Pilot readiness | B10; F8; F6.6 | Evidence-backed integration, including B11 migration parity, operations and owner acceptance. Deployment requires separate authorization. |

Scaffolding/tests can proceed with fixtures where safe; final acceptance cannot be claimed from mocks alone. Admin frontend may be built against reviewed contracts in parallel; it is not a prerequisite for starting the backend.

### Immediate next action

**B11–B14 and F10 are complete in development.** Start local services with `Start-FLAME.ps1` using canonical API 8000 / web 3000; October 12 managed startup supersedes earlier port-8001 and pending-restart notes. Review the signed-in learner `/` UI using the [F10/B14 handoff](backend/stage-14-learner-explore.md), [Interactive handoff](backend/stage-9-interactive-html5.md) and [current Interactive status](#current-interactive-status--2026-10-14). Continue B8 educator, B5 operations and B9.11 hosted-content gates, then B10 integration including legacy B4 harness modernization and Explore real-device/live acceptance. B13 still needs a fresh reviewed, explicitly confirmed linked-Sheet sync with typed-cell/repeat-sync verification. Development completion does not close these gates.

B1–B4, B6 and B7 are complete in development; B5 and B8 are partial. B7 API/BFF answer transport works in live Study and open Curiosity flows; B8 unsupported-capability handling works in stubbed flows. The OpenAI key and `gpt-6-luna` are configured; the owner confirms a USD $5/month project hard spend limit and live Study/Curiosity answers passed. The temporary Curiosity test curriculum is archived; open Curiosity answered with zero published curricula. Next review B8 educator cases and evaluate actual outputs; B7.7 development verification is complete, while hosted function termination remains B10. B5 still needs managed retention/scheduling; live Study/Curiosity restored-session checks passed October 14. The final workbook is published in development; no deployment was performed, and a restricted runtime database role remains a production gate. In the B9 track, follow the handoff directly below the B9 table: configure and verify private storage, publish approved content, then run signed-in browser/device acceptance before closing B9.11.

### Workbook inspection and B1 closure checklist — 2026-09-25

Read-only ZIP/XML inspection of all six sheets. SHA-256: `98f9225be65483171cbe4cb6077d3959fa0c0663b795f51c6d36c2384e7f7494`. No merged cells found. Counts include headers and annotations, not valid import records.

| Sheet | Nonempty rows | Intended level |
| --- | --- | --- |
| KG Level | 9 | KG |
| Stem-Foundation KG & Level I | 72 | Level 1, per owner's six-separate-level clarification |
| Stem-Foundation Level II | 42 | Level 2 |
| Stem-Foundation Level III | 366 | Level 3 |
| Stem-Foundation Level IV | 995 | Level 4 |
| Stem-Foundation Level V | 286 | Level 5 |

All sheets lack Subject and use legacy `Sub Toipc` headers. Parent values are absent on continuation rows; separator rows are present. Later sheets contain URLs in B2 under Level; the combined-named sheet also has an auxiliary I:L classification table. Science is confirmed for all six levels. The combined sheet explicitly labels rows 2–10 KG and starts Level 1 at row 12; Level V also contains an outdated Level IV label at B30. These are historical findings for a candidate the owner has said not to use. No repeated-row or auxiliary-table decision is required for that candidate. Structural inspection does not establish educator validation or B2 importer acceptance.

- B2.1: inspect the final workbook when supplied, then settle its sheet mapping, normalization and row semantics. The old six-sheet findings above are historical, not import instructions or a B1 prerequisite.
- B1.8: the reviewed seven-field target remains; the 2026-09-26 owner rule now requires Subtopic and hides Category from student navigation. Implementation belongs to F3.
- B1.9: concrete member/admin/error/resource examples and mapping reviewed at closure. Domain schemas/routes are implemented in their owning stages.
- B1.10: project owner is accountable for decisions and handoff; developer owns technical delivery. Section 7 needed-by steps are deadlines; no calendar dates invented. Foundation review and handoff completed under the owner’s explicit instruction; no finalized workbook required. Later retention/provider/media decisions remain gated by their recorded implementation steps.

### Stage-entry prerequisites (merged checklist)

Prerequisites are inputs to begin a stage, not completed deliverables. No later-stage readiness is inferred merely because its plan exists. Product owner is accountable; developer, curriculum reviewer and operations owner describe responsibilities, not required new staff.

| Stage | Required entry inputs / decisions | Current readiness |
| --- | --- | --- |
| B1 | Repository/runtime access; frontend request/block/resource examples; direct-LLM scope and decision owner | Foundation and B1.8–B1.10 review/handoff complete |
| B2 | Reviewed IDs/ownership/contracts; live development PostgreSQL; FLAME-only migration ownership; representative normalized workbook; genuine history/fixture distinction | Development DB and schema migrations verified 2026-09-25; final workbook/normalization pending owner |
| B3 | B2 identity/ownership structures; Supabase Auth configuration; callbacks/recovery email/test accounts; server session/token rules; separate member/admin and revoked/expired identities | Development migrations and rollback-only access tests pass; live signup, confirmation, sign-in, recovery/reset and first admin access verified. A separate restricted runtime database role is required before production. |
| B4 | Validated catalogue and authorized access; browse/add/hide/restore contracts; new/partial/duplicate/restored membership fixtures; no invented progress | Depends B2/B3 |
| B5 | Authorized session storage; path/version/mode identity; hide-retention behavior; retry/pagination/history budgets; deletion/draft policy; UI resume fixtures | Depends B3/B4 and policy decisions; LLM credentials not required |
| B6 | Curriculum lookup and bounded-history interfaces; representative teaching-level metadata; language/depth/boundary rules; prompt budget/version fixtures | Depends B5 interfaces and level decisions; descriptions/outcomes optional |
| B7 | B3/B5/B6 interfaces; provider/model/secret quota access; limits, complete-block contract, telemetry and failure fixtures | Responses transport, ask route and stub tests exist; key and `gpt-6-luna` configured; owner confirms USD $5/month hard spend limit; rollback-only live Study/Curiosity answers passed. B7.7 development verification completed October 14; hosted termination/load acceptance remains B10 |
| B8 | Reviewable answers/model-prompt traceability; educator cases/expected facts; measurable quality/latency/cost thresholds; unsupported/error tests | B8.3 complete; B8.1/B8.2/B8.4/B8.5 partial; B8.6 not started. Study-only live outputs await founder scoring; Curiosity quality and browser latency are unscored |
| B9 | DB/auth/activity interfaces; representative approved assets and distribution rights; path/type/version metadata; player contracts; storage/URL/expiry policy | B9.1–B9.10 implemented; approved local Light/Shadow publication/scoped delivery and Phaser/Rive checks recorded. Deployed private bucket, full signed-in learner/device/educator and remaining catalogue acceptance stay open under B9.11 |
| B11 | Existing B5/B7/B9 contracts and saved decisions; affected-test baseline; candidate/composed-response contracts; reviewed ownership/dependency direction | Development migration verified 2026-10-07; same table and URLs, targeted parity/failure/browser checks passed. Existing quality/storage/release gates remain open. |
| F10/B14 | Reference-based Explore plan; existing B9 viewers/catalogues, B11 interfaces and B12 metadata; member browse/open contract audit | Development complete 2026-10-08; contracts, eligibility/version, DB and browser checks recorded. October 12 managed startup supersedes pending restart; storage/device/release gates remain. |
| B10 | Completion evidence for required earlier steps including B11; integrated flows; hosting/secret/durable-storage choices; recovery/support/acceptance ownership | Not ready; this checklist does not authorize deployment |

Each stage hands off the tested result defined by its steps. For readiness updates record: stage/accountable owner, evidence, exact missing input and responsible owner, needed-by step/date, ready/partial/not-ready assessment, and eventual completion evidence separately. Do not wait for all later-stage inputs before working on an available current step.

## 6. Mandatory constraints across every stage

- Stored hierarchy: Curriculum → Level → Subject → Domain → optional Category → Topic → Subtopic. Student view hides Category; Study may use a published Topic or one of its real Subtopics. Backend generates IDs; curriculum_id is mandatory import metadata, and the workbook repeats its matching Curriculum Code plus other required parents on every row; preserve same-domain category validation and stable full-path identity.
- Excel headers: Curriculum Code, Level, Subject, Domain, Category, Topic, Subtopic, Learning Outcome, Source URL. Required on every data row: Curriculum Code, Level, Subject, Domain, Topic, Subtopic. Learning Outcome is optional topic-level guidance and may be blank throughout or omitted; no unique per-subtopic outcome is required. One workbook import targets one existing curriculum; reject mixed/mismatched codes and conflicting nonblank outcomes for one Topic. Topic-only leaves are no longer accepted under the 2026-09-26 owner rule.
- Direct LLM only; model_generated, grounded=false, confidence=null, citations=[]. Importing Excel or playing media is not RAG.
- Individual accounts, controlled admin access; no institutions or teacher login.
- No achievements/mastery/official grading, feedback, automatic struggle detection, purchases/booking, student-file understanding or transcription.
- Nine admin screens only. Operational limits/logging are necessary backend features, not additional admin dashboards.
- Teacher/kit administration and context-aware recommendations are required. The owner's 2026-10-03 MVP instruction supersedes random teacher cadence and the previous kit-recommendation exclusion: explicit human-help requests may offer eligible tutors, practice requests may offer published suitable activity guides. Contact/enquiry/booking, automatic struggle detection, progress-based personalization and book recommendations remain excluded.
- Curiosity responses must suit under-15 learners and may cover general learning topics and languages without curriculum/topic resolution. This is not an account-age gate. Study remains bound to a validated published path.
- No private messages in admin student activity; no client-supplied identity authority.
- Separate binary media from metadata; published authorized resources only; no arbitrary interactive execution.
- Keep credentials server-side; do not put real .env values or DSNs in this tracker.
- Preserve user changes and real history; no production fixtures represented as learning progress.
- Follow module ownership and API contracts; do not skip server checks because the frontend validates a form.

## 7. Open inputs and decision deadlines

Owner: project owner (with consultant advice); implementation responsibilities do not imply additional staff.

| Input / decision | Current evidence | Needed for |
| --- | --- | --- |
| Normalized workbook and path classification | Final accepted workbook imported and published in development on 2026-09-28; 1,721 distinct Subtopics and five accepted duplicates. | Complete for development; future workbook revisions need their own preview |
| Name normalization and import limits | Whitespace rule documented; final case/Unicode/limits unresolved | B2 parser/constraints |
| Frontend seven-level mapping/API payload review | B4 BFF integration now carries all seven IDs/nulls through live catalogue, Library and My Learning; Study answer transport is implemented under B7; live provider verification remains | F5/B5/B6 |
| Production database runtime role | Development B3 roles and RLS tested; the API still uses a schema-owner connection in development | Before production deployment / B10 |
| Curriculum archive and revision behavior | B4 policy resolved and documented: archived ancestors block new selection, owned history remains, and B5 must reject continued Study questions if the selected path is unavailable or revision changed | Implement response in B5/B6 |
| Request recovery and concurrency | B5 claim/finalize recovery is integrated with the B7 ask route; stubbed replay and retry passed, with live deadline and interrupted-worker recovery verified October 14; hosted termination remains B10 | Verify B5.9/B7.7 |
| Open Curiosity continuation | Signed-in Study/Curiosity restored-session continuation passed October 14; hosted full-flow/quality acceptance remains | B10/F5.5 |
| Activity, drafts, retention/deletion and backup periods | Activity definitions and local-only drafts documented; owner set a 30-day maximum for residual backup/log copies on 2026-09-26, with immediate primary-data deletion; PITR is not required for MVP | Verify actual managed backup/log retention and any external copies; PITR may be evaluated later |
| KG–5 meaning and open Curiosity | Conservative explicit-label KG–5 Study mapping implemented. Open Curiosity has no curriculum gate and uses an under-15 prompt; educator quality review remains | B8.1/B8.2 |
| Provider/model/credentials/quota/spend limits | Owner selected OpenAI and configured the API key/model. `gpt-6-luna` is the only project-allowed model (200,000 TPM; 500 RPM). API key/model configured; owner confirms USD $5/month hard spend limit. Daily member requests and response tokens are capped, and live Study/open Curiosity answer/replay passed. See B7 handoff | B7 operations and B8 cost review |
| Educator cases and quality thresholds | Founder is the reviewer; 17 Study samples and one real imported-path API answer await factual and age-suitability scoring. | B8.1/B8.6 |
| Media formats/storage/links/distribution/expiry | B9 policy plus later keyless YouTube/Vimeo and HTML5 overrides apply. Generic external links require approved hosts; uploaded Interactive uses bounded JSON, not signed URLs. Private Supabase upload/delivery and Image/Video expiry still need live verification | B9.11 live storage/delivery and B10 production gate |
| Teacher recommendation presentation | Owner October 3 decision supersedes random cadence: explicit human-help intent selects eligible mapped tutors by expertise/availability, at most one primary plus one useful alternative; contact/booking excluded | B9.8/F7.5 |
| Hosting/support/recovery/pilot acceptance | Not verified | B10 |

## 8. Evidence and update record

Existing baseline:

| Evidence | Result | Scope limit |
| --- | --- | --- |
| Frontend validation, 2026-09-20 | 8 unit tests; build/type; Edge UI/responsive/14 axe states recorded passing | Local fixtures; physical devices and real backend integration not certified |
| Backend Stage 1, 2026-09-24 | 11 tests passed; 2 upstream deprecation warnings; pip check/smoke evidence recorded | Health/contracts only; mocked readiness tests not real DB proof |
| Supabase connection follow-up | SELECT 1 success recorded | No domain tables, RLS, auth or migrations proven |
| This tracker, 2026-09-25 | Plans/evidence reconciled; step IDs/statuses added | Documentation work only; no implementation or tests executed |
| Consolidation, 2026-09-25 | Prerequisites/decision/evidence records merged; moved paths repaired | 132 step IDs/statuses retained; no new feature completion |
| Owner scope clarification, 2026-09-25 | Excel-school-topic-only Curiosity, under-15 responses, random subject-matched teacher cards approved | Historical decision superseded by 2026-09-27 open Curiosity instruction; subject-matched cards now require validated Study context |

### Preserved Stage 1 verification detail

Recorded 2026-09-24, not rerun during consolidation:

- Python 3.13.2, FastAPI 0.141.1, Pydantic 2.13.5, SQLAlchemy 2.0.54, psycopg 3.3.6, pytest 9.1.1; existing virtual environment reused.
- 11 backend tests passed: lifespan, live/ready behavior, sanitized DB failure, 404/405/422/500 errors, request IDs, invalid configuration, production docs exclusion, client-authority rejection, provenance and Domain/optional Category shape.
- Two upstream deprecations: Starlette httpx TestClient and AnyIO portal alias; do not hide them instead of reviewing compatible dependencies.
- pip check reported no broken requirements. Smoke Uvicorn returned /health/live=200 and unconfigured /health/ready=503; test server stopped.
- Later local-secret Supabase SELECT 1 succeeded independently of mocked readiness tests. No domain migrations, live LLM, deployment or frontend mutation was implied.
- Direct dependencies pinned; full cross-platform transitive lock not provided. Reproduction commands live in the API README and frontend validation report.

Old Stage 1 substep mapping: 1.1 → B1.1/B1.8; 1.2 → B1.4; 1.3 → B1.3; 1.4 → B1.6/B1.9; 1.5 → B1.5; 1.6 → B1.6/B1.7/B1.10. This preserves historical references without a second status table.

For every subsequent delivery append a concise record:

| Date | Step IDs | Status change | Files / migration revision | Checks and actual result | Open issue / next step |
| --- | --- | --- | --- | --- | --- |
| 2026-09-25 | B1.9/B3/B4/B5/B6/B9/F2/F7 | No status change | MVP scope, API contracts, module architecture and this tracker | Documentation review updates; step IDs/statuses retained; no runtime tests | Finalize onboarding, archive/revision, recovery and clarification policies before their implementation gates; B1.8 remains next |

| 2026-09-25 | B1.8–B1.10 | Remain PARTIAL | API contracts, tracker, PROJECT_CONTEXT.md | All six workbook sheets structurally inspected; frontend types/service boundary reviewed; documentation changes only | Repeated KG rows, normalization and owner contract/handoff acceptance pending; no Supabase mutations |

| 2026-09-25 | B1.8/B1.9/B2/F3/F9 | B1 review remains PARTIAL | Teaching Context, tests, scope and canonical specifications | 14 foundation tests passed; 2 existing upstream deprecation warnings; 8 JSON examples parsed; Study example validated against updated schema | Sample normalization moved to B2; domain migrations/admin integration still pending |

| 2026-09-25 | B1.8/B1.9/B1.10 | PARTIAL → COMPLETED | API contracts, tracker, project context, foundation tests | 16 tests passed; 2 existing upstream warnings; 8 JSON examples parsed; request/answer models verified; 132 unique step IDs and totals reconciled | B2 next; all section 7 later-stage gates retained; no DB mutations |

| 2026-09-25 | B2.1–B2.5 | B2.1 BLOCKED; B2.2–B2.5 COMPLETED | Alembic config, four FLAME schema revisions, domain models, API README | Live DB/schema ownership verified; 23 FLAME tables; rolled-back synthetic ancestry/uniqueness/idempotency/money checks passed; Alembic check clean; 16 API tests and pip check passed | Final workbook needed for B2.1 and import acceptance; B2.6 parser can use synthetic canonical rows; no public importer or deployment |

| 2026-09-25 | B2.1/B2.6 | No status change | API contracts, admin specification, module architecture, tracker | Owner requested curriculum in sheet; Curriculum Code added as required per-row target assertion; documentation only | Final workbook still needed to validate mapping and normalization; importer must reject mixed/mismatched codes |

| 2026-09-25 | B2.1/B2.3/B2.6 | No status change | `20260925_05`, topic model and canonical import specifications | Migration applied; nullable column and zero Topic rows verified; Alembic check clean; 16 API tests passed with 2 existing warnings. Column may be entirely blank/omitted; per-topic consistency specified | Final workbook and importer still pending; no LLM prompt integration claimed |

| 2026-09-26 | B2.6/B2.8/F3.3/B4.1 | F3.3 COMPLETED; B2 remains complete | Parser/commit validation, Study schema, local tree/Library/adapter, contracts and tracker; no migration | 19 backend tests passed (2 upstream warnings); Alembic check clean; 11 web unit tests, typecheck and build passed; browser suite passed 14 axe states and 15 viewport cases | B3 auth, B4 publication validation/protected routes, F3.4 live BFF data; no permanent import or deployment |

| 2026-09-26 | B3.1–B3.7/F2.3/F9.2 | B3 COMPLETED; F2.3/F9.2 COMPLETED | `20260926_07`/`20260926_08`, BFF/API identity, account screens, B3 notes and tests | Owner verified signup email, confirmation, sign-in, recovery/reset and admin access; one active profile/admin grant and two revoked sessions observed. Nine targeted B3 tests, web typecheck, five axe audits/two redirects and 12 readiness checks passed. | B4 next; restricted runtime DB role required before production; admin management screens remain F9.3–F9.11 |

| 2026-09-26 | B6.1–B6.6 | B6.1–B6.4 COMPLETED; B6.5–B6.6 PARTIAL | Teaching context/profiles/prompt/resolution/clarification services, `20260926_13`, B6 handoff; no frontend edits | 38 DB-enabled backend tests passed, 2 concurrency-only skipped; Alembic upgrade/check passed; rollback-only fixtures | B7 public answer and clarification exchange, per-turn subject persistence, BFF/history and educator fixtures remain |

| 2026-09-26 | B6.5/B6.6 | COMPLETED in development | Teaching router, idempotent persisted topic checks and paginated history (`20260926_14`), BFF saved-session panel, five exact-workbook-row draft cases and adversarial tests | 39 DB-enabled backend tests passed, 2 concurrency-only skipped; web typecheck, 11 unit tests, build and production-mode mock browser passed | B7 generated answer turns/history and B8 educator quality review remain |

| 2026-09-27 | B7.1–B7.7/F5.4/F5.5/F6.5 | B7 PARTIAL; B7.2–B7.4/B7.6 and F6.5 COMPLETED; B7.1/B7.5/B7.7 and F5.4/F5.5 PARTIAL | OpenAI Responses gateway, AnswerService/ask route, `20260927_15`, BFF/composer and answer tests | 44 DB-enabled backend tests passed, 2 concurrency-only skipped; targeted B6/B7 tests and Alembic drift check passed; 11 web unit tests, build and mock production browser answer retry passed. No live provider call. | OpenAI provider selected after this delivery; choose model, configure server key and spend policy, then run controlled live/cancellation checks and finish F5 resume/provenance coverage. |

| 2026-09-27 | B7.1 | Remains PARTIAL | Tracker, project context; `.env.example` already has a commented key placeholder | Owner selected OpenAI for MVP and reports key ready, but it is not in API `.env`; no live call made | Select model and monthly USD hard spend limit; configure key in the API `.env` and run controlled live verification. |

| 2026-09-27 | B8.1/B8.3–B8.5 | B8 PARTIAL; B8.3 COMPLETED, B8.1/B8.4/B8.5 PARTIAL | Capability gate/preflight, bounded answer schemas/output guard, browser mapping, `backend/stage-8-evaluation.md`, B8 tests; no migration | 55 DB-enabled backend tests passed, 2 concurrency-only skipped; Alembic drift clean; 11 web unit tests, production build and mock browser Study/Curiosity unsupported checks passed. No live or educator evaluation. | Owner/educator review of cases and thresholds; select/configure B7 model/key for B8.2/B8.6 live evaluation; B9 resource cases later. |


| 2026-09-27 | B7.1/B7.2/B7.5/B7.7/B8.4/B8.5 | B7 and B8 remain PARTIAL; no step-status promotion | B7 handoff with local key template and model/spend explanation; Responses multipart/refusal and hard-limit handling; tracker/README/context alignment | 64 DB-enabled backend tests and 11 web unit tests passed, 2 concurrency-only backend tests skipped; Alembic drift check and web production build clean. No key/model configured and no live provider call. | Owner configures key and `gpt-6-luna` in API `.env`, chooses monthly USD hard spend limit; controlled B7 live check and B8 educator review/evaluation remain. |

| 2026-09-27 | B7.1 | Remains PARTIAL | Tracker, B7 handoff and API `.env.example` updated for the owner's allowed-model decision | Project allows only `gpt-6-luna`, with 200,000 TPM and 500 RPM; API key and model are still not configured locally; no live call | Select monthly USD project hard spend limit, add key/model to API `.env`, then run controlled live check. |

| 2026-09-27 | B7.1/B7.5 | Remain PARTIAL | API defaults, `.env.example`, local API `.env` numeric settings and B7 handoff updated | Effective settings are 100 new logical requests per member per rolling day and 1,500 maximum output tokens per answer; 64 backend tests passed, 2 concurrency-only skipped. Key/model remain unconfigured; no live call. | Set key plus `gpt-6-luna`, choose monthly USD hard spend limit and run controlled live check. |

| 2026-09-27 | B7.1/B7.5/B7.7 | B7.1/B7.5 COMPLETED; B7.7 PARTIAL; B7 remains PARTIAL | Configured API key/model and owner-confirmed USD $5/month project hard spend limit; direct gateway and rollback-only authenticated Study answer/replay | Direct call: 33 input/31 output tokens. Study API call: 200, `gpt-6-luna`, 188 input/13 output tokens, latency recorded, two messages stored, replay identical, all test data rolled back. Key not displayed. | Live timeout/cancellation and restored-session continuation remain B7.7; B8 educator output evaluation remains. |

| 2026-09-27 | B7.7/F5.5 | Remain PARTIAL | Published clearly labelled development Curiosity test curriculum; homepage passes live catalogue and suggests its Subtopic; API restarted to load key | Live Curiosity topic-check `ready` and answer 200 (`gpt-6-luna`, 217 input/68 output tokens), same-key replay; test member/session/answer rolled back. Web 11 unit tests, build and production-mode mock browser flow passed. Test curriculum remains published for manual use. | Signed-in real-browser journey, live timeout/cancellation and restored-session continuation; archive test curriculum after use. |

| 2026-09-27 | B6/B7/B8/F5 | B6 COMPLETED; B7 PARTIAL; B8 PARTIAL; B8.2/B8.6 NOT STARTED | Open Curiosity answer/prompt and frontend; archived temporary test curriculum; updated scope, contracts and handoffs | Live `gpt-6-luna` Curiosity answer with zero published curricula: 200, 164 input/119 output tokens, null curriculum/subject/topic, same-key replay; rollback removed test member/session/turn. Backend 66 passed, 2 skipped; web 11 unit tests, build and mock browser passed. | B7.7 live timeout/cancellation and signed-in restored-session; B8 educator-approved cases, scoring and acceptance. |

| 2026-09-28 | B7.7/F2.4/F5.3/F5.5 | Remain PARTIAL; mock-browser continuation added | Saved-session resume action, exact published Study path lookup, paginated message restoration, explicit owned session ID in answer transport, browser flow; no migration | Web typecheck, 11 unit tests, production build and production-mode mock browser Study/Curiosity resume/follow-up passed. Study retry used the same saved session ID; Curiosity follow-up used its saved ID. No signed-in live-browser or live provider timeout/cancellation check. | Complete B7.7 live timeout/cancellation and signed-in real-browser continuation; B8 educator approval and live scoring remain. |

| 2026-09-28 | B8.1/B8.2/B8.4 | B8.2 NOT STARTED → PARTIAL; B8 stage remains PARTIAL | Study-only case fixture and controlled live runner, 17-response JSON baseline, founder review packet and evaluation rubric; no migration or Curiosity behavior change | Existing B8 tests: 15 passed. Live `gpt-6-luna`: 17/17 validated Study answers, 3,344 input/866 output tokens, 2,242 ms median and 3,295 ms p95 gateway time; no word-limit violation. Candidate omissions in Grade 2/3/5 flagged without claiming factual acceptance. | Founder approves/corrects expected facts and thresholds, scores samples and affected reruns; published-path/browser latency and B7.7 live failure checks remain. Curiosity remains open and unchanged, with its quality row unscored at owner direction. |

| 2026-09-28 | B8.4 | Remains PARTIAL; Study length guard added | AnswerService applies the B6 profile word cap to Study generated output; Curiosity path unchanged; B8 unit check | 26 targeted B7/B8 tests passed; one rollback-only B7 database integration passed; all 17 recorded Study answers passed the new guard without new provider calls. | Founder scores facts, topic and level; any failed group reruns before B8 acceptance. |

| 2026-09-28 | B4/F3 | Subtopic sibling navigation refined; statuses unchanged | Approved Topic screen retained. On Subtopic screens, a solid blue book-marked Topic button sits beside outlined sibling Subtopic buttons; the current Subtopic has a selected blue tint. All buttons switch Study context directly. | Web typecheck, 11 unit tests, build and mock browser sibling-switch/visual-state checks passed; desktop screenshot inspected. | Signed-in browser visual acceptance remains. |
| 2026-09-28 | B4/F3 | Topic/Subtopic workspace visual revision; statuses unchanged | Topic heading now precedes its Subtopic list; the lower duplicate list was removed. A Subtopic view highlights the parent Topic with a `View topic` button that returns to Topic Study. No API or Curiosity change. | Web typecheck, 11 unit tests, production build and mock browser flow passed; Topic and Subtopic screenshots were inspected at desktop size. | Signed-in browser visual acceptance remains. |
| 2026-09-28 | B4/B6/B7 | Direct Topic Study selection enabled; stage statuses unchanged | Topic row opens Study; Subtopics appear above the heading and as lower actions. Study session/answer contracts accept a null Subtopic ID while validating the published Topic ancestry and pinned revision; existing Subtopic sessions remain distinct. Saved Topic sessions resume by Topic name. Curiosity runtime unchanged. | Rollback-only B7 integration passed Topic ask/replay and mismatched Subtopic rejection. Real imported KG Topic TestClient ask returned 200 (`gpt-6-luna`, 194 input/28 output tokens, 2,714 ms stored latency), two turns and identical replay; disposable rows rolled back. Web typecheck, 11 unit tests and build passed; browser Topic/CTA/resume flow checked. | Founder quality scoring and signed-in real-browser acceptance remain. |
| 2026-09-28 | B4/B8.2 | Final curriculum published in development; B8.2 remains PARTIAL | Founder-approved final workbook SHA-256 `962c8f...868da` imported as `fliplecture` (ID `744f0dc7-e40f-473a-8a49-c67b7eea27a4`), revision 2; 1,721 distinct Subtopics, five accepted duplicate rows, zero preview issues; 6 levels, 6 subjects, 30 domains, 92 categories, 417 topics | Member catalogue listing, six levels, KG tree and exact Subtopic search returned 200. A rollback-only Study session/ask on the imported KG path returned 200 (`gpt-6-luna`, 199 input/53 output tokens, 3,560 ms model latency), stored two turns with resolved topic IDs, and replayed identically. Web BFF import preview/commit timeout raised to 60/240 seconds; typecheck and build passed. No Curiosity runtime change. | Founder factual/age review and signed-in Study browser flow remain; TestClient used a disposable principal override for the Study call. |
| 2026-09-28 | B8.2/B7.7 | Remain PARTIAL; live Study API path verified | `scripts/verify_b8_study_api.py`, temporary published KG path, `work/b8-study-api-check.json`; no permanent import/migration | Protected Study ask returned 200 with `gpt-6-luna`, 202 input/59 output tokens, 2,976 ms stored latency, one user/assistant pair and resolved Study IDs; same-key replay identical. Outer transaction rolled back; independent query found zero temporary curricula. Principal was overridden for the rollback test. | Signed-in real-browser Study journey with a published imported path and founder quality scoring remain; no claim that the 17 direct-prompt samples exercised the Study screen. |

| 2026-09-28 | B9.1 | NOT STARTED → PARTIAL; B9 stage PARTIAL | B9.1 resource policy proposal and tracker; no migration or runtime change | Existing resource schema, API contracts, admin specification, MVP scope and local viewer reviewed; no runtime tests needed for documentation | Owner confirms formats/limits, external hosts, durable storage/expiry and distribution-rights evidence; then implement B9.2 |

| 2026-09-28 | B9.1/B9.2 | B9.1/B9.2 COMPLETED in development; B9 stage PARTIAL | Approved resource policy, admin upload/draft routes, private storage adapter, Pillow image checks, revision 20260928_16, B9 tests and configuration | Migration applied and Alembic check clean; rollback-only B9 test 4 passed; backend suite 59 passed/12 skipped before final two safety checks; pip check clean. No live Supabase Storage upload or publication | B9.3 versioned edit/publish/unpublish and admin filters; configure private bucket and approved hosts before live use; B9.5 URL expiry later |

| 2026-09-28 | B9.3–B9.11/F7/F9 | B9.3–B9.10 complete in development; B9.11/F9.11 partial | Revision `20260928_17`, versioned resource/teacher/kit APIs, BFF, admin screens, member cards/viewer and five-minute delivery | Six rollback-only B7/B9 integration tests, B4–B9 mock browser, web typecheck/build and Alembic check passed; API ready on port 8000. Full backend suite was interrupted after stalling in B6 integration; targeted B9 checks passed. | Configure and live-test private Supabase Storage with approved assets/hosts; finish signed-in browser/device and B9.11/F9.11 acceptance. |
| 2026-09-28 | F9.1/F9.3–F9.5/F9.8/F9.11 | F9.3–F9.5 remain COMPLETED; F9.1/F9.8/F9.11 remain PARTIAL | Admin curriculum/import/student workspace, responsive styles, B4 mock browser flow, web README; no migration | Typecheck, production build, 11 web unit tests and mock browser flow passed. Browser covered create → workbook upload → sheet mapping → preview → commit → history, admin navigation and 390px overflow; import screen axe audit passed. Desktop/mobile screenshots inspected. API and web returned HTTP 200. | Signed-in live admin, real workbook operation, stale-edit/denied-access and physical-device/screen-reader acceptance remain F9.11/B10. |
| 2026-09-29 | F9.3–F9.5/F9.11/B4 | F9.3–F9.5 remain COMPLETED; F9.11 PARTIAL | Integrated Catalogue list/workspace, guarded DELETE routes, updated B4 mock browser and rollback-only API test; no migration | 11 web unit tests, web typecheck/build, full B4–B9 mock browser journey, 390px overflow and import axe check passed. Rollback-only B4 integration test passed deletion and existing import/publication behavior. | Signed-in live admin, real workbook operation, keyboard/screen-reader/device and B9.11 storage acceptance remain. |
| 2026-09-29 | F9.3–F9.5/F9.11/B4 | F9.3–F9.5 enhanced; F9.11 remains PARTIAL; B9.11 unchanged | Six-column hierarchy grid, transactional path batch API, workbook correction/re-preview table, permanent deletion dependency review/typed modal, Archive/Restore actions; no migration | Rollback-only B4 DB integration passed invalid workbook correction, multi-row edits, stale revision, deletion and association block. Web typecheck/build, 11 unit tests, production-mode B4–B9 mock browser and import axe audit passed. API restarted; live/ready healthy with new OpenAPI routes. | Signed-in live admin session at :3000, real workbook/device/keyboard and screen-reader checks remain; existing published curricula still apply saved edits immediately. B9.11 private storage gate unchanged. |

| 2026-09-30 | F9.3–F9.5/F9.11/B4 | F9.3–F9.5 enhanced; F9.11 remains PARTIAL; B9.11 unchanged | Revision 20260930_18, private curriculum snapshots, atomic explicit publish, complete-replacement import with typed confirmation, round-trip Excel export/metadata, conflict recovery, full-width workspace metrics and compact overflow actions | Migration applied and drift clean; 61 non-DB backend tests passed; rollback-only B4 test 2 passed/1 concurrency-only skipped; web typecheck, 11 unit tests, production build and B4–B9 browser/axe/390px flow passed. API /health/live, /health/ready and web /admin returned 200. | Sign out/in once to refresh the already-granted admin role for packmymail@gmail.com; run a signed-in real workbook/browser and physical keyboard/screen-reader/device pass. B9.11 private storage/assets remain the next B9 execution order. |

Use repository test commands in PROJECT_CONTEXT.md and app READMEs. Completed tests must match changed behavior; for example, Pydantic UUID checks do not prove DB ancestry, UI hiding does not prove authorization, and SELECT 1 does not prove migrations.

### B11 verification — 2026-10-07

Recommendation coordination and its table mapping now have their own module; typed catalogue services and a small nonblocking composer preserve split URLs/root fields, stored decisions and ID/version history. 53 targeted backend tests (two existing upstream warnings), 17 frontend units, production build, learner recommendation/media, Resource Library and sidebar browser suites passed. Alembic detected no new upgrade operations. The local API restarted and health/CSRF checks returned 200. The broader B4 browser harness still expects the removed Saved Conversations section and is not counted as passing; its modernization remains under B10. [Technical handoff and rollback](backend/stage-11-modular-migration.md); source-only baseline snapshot and machine-readable results: work/b11-baseline-source.zip and work/b11-verification.json. No paid LLM call, schema/backfill, data publication or deployment. B5/B7/B8/B9.11/B10 acceptance stays open.

## 9. Deferred roadmap — excluded from the 162-step MVP count

- Saved unsent drafts, streaming and a single blocking answer/recommendation HTTP response remain optional. Pins already persist; B11 adds composed envelopes over separate requests without delaying explanations. Separate fetching/display remains the current MVP delivery pattern.
- Future knowledge ingestion → traditional filtered RAG → deterministic routed RAG → measured hybrid/reranking improvements → media/personalized retrieval → optional bounded agentic retrieval.
- Later assessment/mastery, institution access, student-file processing/transcription, tutor contact/booking and commerce require new scope. Current MVP tutor selection requires explicit human help and uses expertise/availability rather than random cadence.
- See [RAG roadmap](../Planning/RAG/rag_mvp_roadmap.md). Do not add vector infrastructure or speculative microservices as MVP prerequisites.

## 2026-09-26 hierarchy visibility decision

The 2026-09-26 owner decision required Subtopics for Study selection; the 2026-09-28 direct Topic Study decision supersedes that selection requirement. My Learning shows Curriculum → Level → Subject → Domain → Topic → Subtopic; Category is never displayed to students. Published Topics still require real Subtopics, while a Study question may bind to the Topic or a Subtopic. The category_id remains in the imported hierarchy and Study context for exact ancestry and LLM answer routing. The final Fliplecture workbook has a Subtopic on every populated row. The existing Supabase `flame` schema already supports this separation, so this decision changes validation, API contracts, and the frontend adapter without changing table structure. Public catalogue/My Learning routes remain gated by B3/B4 authentication and membership work.

### B4 development completion evidence — 2026-09-26

Migrations `20260926_09`–`20260926_11` add descendant soft archive, exact My Learning paths and revision details. Protected B4 API routes implement published listing/search/tree, curriculum creation/edit/publication/archive, importer upload/preview/commit/history/issues, owned membership add/hide/restore and paginated student search/profile. Archive and continued-session policy is recorded in the module architecture and API contracts; B5 must apply its unavailable-context rule when session endpoints arrive.

The full backend suite passed 30 tests with development PostgreSQL integration enabled; the opt-in two-worker concurrent-addition check passed and removed its UUID fixtures. Alembic reached head with no schema drift. Web unit tests (11), typecheck and production build passed. A production-mode browser test using a disposable mock API covered BFF catalogue loading, exact Subtopic addition, refresh, subject hide/restore, Library search, error/retry and admin draft creation. Signed-in session persistence, revoked-session denial, cross-member isolation, stale import preview, idempotent commit, archive filtering and revision history were verified against development PostgreSQL with rollback-only fixtures. Browser checks used mock API data; no real workbook was permanently published and no deployment was performed.








### B12 verification — 2026-10-07

The owner-requested metadata → evaluation → targeted ranking → performance cycle is implemented in development. Read [B12 handoff](backend/stage-12-recommendation-quality.md) for changed files, measurements, repeatable commands and limitations. Optional metadata is manually entered; educator review and release/load gates remain open. API restarted after additive migration; no deployment or real-catalogue backfill.


### B13 verification — 2026-10-07

Four catalogue bulk imports and exports are complete in development. Existing nonempty data/media/publication states are preserved; confirmed imports add missing draft details, list entries and valid mappings. Samples and folder paths are documented in [bulk-import-samples/README.md](bulk-import-samples/README.md). See [B13 handoff](backend/stage-13-bulk-transfer.md) for test commands/evidence and operational limits. No deployment or real-data bulk import was performed.

### F10/B14 planning update — 2026-10-08

Owner requested the learner Explore development plan to be entered in this tracker. Added five frontend and five backend implementation steps with acceptance conditions, dependencies and execution order. All ten are NOT STARTED; planning is not implementation evidence. Totals now cover 162 steps: 120 COMPLETED, 20 PARTIAL, 22 NOT STARTED, zero BLOCKED. Companion entry point updated; no application code, runtime tests, schema changes or deployment. Next Explore work package: B14.1.

### F10/B14 development verification — 2026-10-08

All ten Explore steps completed in development under the owner's proceed instruction. Reused catalogue eligibility, viewers and activity; added browse/context/open routes, scoped delivery, top-right CTA, responsive panel, filters/search/pagination, static thumbnails and answer/recommendation links. 26 affected backend tests passed with DB enabled; focused DB rerun eight passed; subsequent DTO unit check seven passed with the DB opt-in test skipped because its flag was absent. Typecheck, 17 web units, production build and Explore/media/sidebar browser suites passed. Fixture changes rolled back; no schema migration, paid LLM call, deployment or real-catalogue mutation. Automatic approval review blocked stopping the running API (blocked by policy); manual restart remains. [Files, contracts, checks and limits](backend/stage-14-learner-explore.md). Current totals: 162 steps, 130 COMPLETED, 20 PARTIAL, 12 NOT STARTED, zero BLOCKED; earlier release gates unchanged.

### Reference design and three media families — 2026-10-08

Owner-requested refinement of F10/B14 and B9/F9: reference-style learner header, bubbles/cards, compact existing CTAs, profile and two-column Explore grid; consistent admin palette. Active media choices are Image, Video, Interactive across forms, resource management, API/database, Explore and bulk export. Diagram aliases normalize to Image; animation/GIF/provider aliases normalize to Video. Source/MIME retain provider and animated playback; no new Audio uploads/creation. Migration `20261008_27` applied, Alembic clean; development catalogue now 10 Video and 2 Image, all provider metadata/publication retained. IDs/mappings/files/versions preserved; legacy audio retained inactive if present elsewhere. 63 affected DB-enabled backend tests and three focused family tests, typecheck/build and 17 web units passed; Explore/sidebar/media/browser evidence in [handoff](backend/stage-14-reference-design-media-families.md). Existing completion totals unchanged. Manual local API restart remains required after the earlier policy-blocked stop; production, approved live assets and physical-device/screen-reader gates remain open.

### Five learner/Explore annotation refinements — 2026-10-08

F10.1/F10.2 layout refinements: right-aligned header navigation; Explore at the opposite end of the breadcrumb row; search above media chips; learning-path filter icon beside the chips; unified refresh icon beside dropdowns instead of separate error-action buttons. Accessible compact errors, refresh duplicate guard, selection preservation, keyboard/expanded state and reduced-motion support retained. Typecheck/production build and sidebar checks passed; annotated-width and Explore recovery/browser evidence recorded in the [design handoff](backend/stage-14-reference-design-media-families.md). No backend/schema/media-type changes or status/count changes.

### Latest header / Explore simplification — 2026-10-08

F10 owner refinement: remove Learn/Curiosity/My Learning from top header and remove the duplicate media-type/language/refresh row from Explore. Category chips, search, path filter icon, breadcrumb Explore action, account and existing sidebar navigation remain. Error recovery uses close/reopen and reloads latest paths after an error. Typecheck, production build, Explore and sidebar browser suites passed; no backend/schema or status/count change. [Current design handoff](backend/stage-14-reference-design-media-families.md).

### Explore text/action removal — 2026-10-08

Latest owner annotations remove the Explore path text (including the empty-path placeholder), the entire Return to current topic / Clear filters action row, and the Select a curriculum, grade and topic prompt. Search, category chips, path filter icon/controls, eligibility and current-context initialization remain. No new placeholder replaces the removed prompt. Typecheck, production build and existing Explore browser flow passed; mobile path selection now uses the existing filter controls. No backend/database changes or tracker count/status changes.

### Live Grade 1 Gravity Explore recovery — 2026-10-08

Confirmed the old API on port 8000 lacked every Explore route and returned HTTP 404. Database/current catalogue service still had ten published mapped videos for FlipLecture / Grade 1 / Science / Gravity (Forces & Motion) / Gravity. Started current Uvicorn on 127.0.0.1:8001 with reload, leaving the policy-protected old process untouched; changed only FLAME_API_URL in the frontend local environment to that address. Signed-in existing browser now displays 10 matching resources with Video selected; proof: work/gravity-videos-live.png. No media, mappings, publication, roles or credentials changed. This verifies live listing, not live provider playback/rights/educator acceptance; earlier release gates remain.

### Explore follows learning navigation — 2026-10-08

An open Explore now follows changes to the active curriculum/topic/subtopic/revision in Media, Teachers and Activity Kits without reopening. Keeps the selected catalogue and media category, resets the previous search/page/scroll, clears old results/errors/viewers, and invalidates pending answer/path/item requests. Independent Explore filtering remains until actual learning navigation changes; saved-answer entry retains its requested path. The shared learning-path filter now sits beside search in all three catalogues. Production build and the expanded Explore browser suite passed, including all three catalogues, topic changes, subtopic changes, independent browsing, saved-answer entry and existing asynchronous-response protection. Live Light subtopic navigation verified; proof: work/explore-follows-learning-path.png. No backend/database changes or tracker status/count changes.

### Curiosity follows the latest question — 2026-10-08

F10/B14 refinement: the owned Explore context endpoint matches saved Curiosity questions against published topic/subtopic names using one curriculum read query. A unique match browses automatically; multiple grades/curricula offer labelled choices; an unmatched new question clears previous results. Open Media/Teachers/Kits follows each confirmed latest Curiosity answer, retains its tab/category, resets old searches/pages/viewers, and discards stale context responses. Restored Curiosity and deliberate saved-answer entry work without changing Study progress or recommendation history. Publication/access/version checks remain. Nine backend checks passed with rollback-only database coverage; production build and expanded browser coverage passed. Name matching is conservative, not general semantic search; no new LLM request or schema migration. See stage-14-learner-explore.md for behaviour and evidence. Tracker counts/statuses unchanged.


### Curiosity combined results across matching paths — 2026-10-08

Owner refinement supersedes the earlier ambiguous-path choice behaviour: Curiosity now directly displays combined eligible media, teachers and kits across all matching published topics/subtopics. No matching-path list or confirmation is rendered. The authenticated /api/v1/explore/curiosity endpoint reads the owned saved question, re-resolves current published paths, applies existing owner eligibility/suitability, deduplicates by kind/ID before global filtering/sorting/pagination, and returns each item's authorized browse_path for scoped open/thumbnail/delivery. Study remains scoped as before; later questions still clear and refresh results with stale-response protection. No schema, mappings, publication or LLM changes. Twelve backend checks with rollback database coverage and production build/TypeScript passed; browser regression coverage verifies multi-path results across all catalogues, combined search, scoped item opening, and existing Study/Curiosity behaviour. Counts/statuses unchanged.


### Local sign-in recovery — 2026-10-09

Frontend local configuration still pointed to port 8001 after the API was restarted on port 8000. No listener existed on 8001; the current API on 8000 has both authentication and latest Explore/Curiosity routes. Corrected only FLAME_API_URL in the ignored frontend environment to http://127.0.0.1:8000. This supersedes the 2026-10-08 port-8001 runtime handoff; use the configured address and running backend consistently. Also corrected the authentication BFF to return the signed_in envelope only on a successful login/verify response, preserving operation-specific upstream errors otherwise. A credential-free empty login request previously returned HTTP 503 with a false signed_in body; after correction it reaches backend validation and returns HTTP 422 with validation_error. No user credentials, identity roles, auth rules, or database data were changed. Actual successful account sign-in remains for the user to retry.


### Reference navigation shell refinement — 2026-10-09

Learner UI only: centered Study/Curiosity segmented switch with a keyboard-accessible mode dropdown, full-height collapsible left sidebar/compact rail, mobile navigation drawer, and account/admin/sign-out controls at the bottom. Existing profile popover opens upward; its local-workspace fallback now links to the existing sign-in route. FLAME branding is in navigation; Explore remains opposite the context breadcrumb. Neutral page/sidebar surfaces and centered empty workspace match the supplied desktop/mobile references; the mobile composer remains at the bottom. Existing selection handlers, conversations, pins/recent, hierarchy, learning progress, recommendation/Explore and authentication APIs remain unchanged. Desktop navigation changes at 1100px, mobile drawer at 768px, and Explore retains its existing 1280px breakpoint. No backend or database changes. Production build, TypeScript, Explore and sidebar browser suites passed; live desktop expanded/compact, mobile drawer/account placement and dropdown keyboard checks completed. Evidence: work/reference-shell-desktop.png, work/reference-shell-desktop-compact.png, work/reference-shell-mobile.png, work/reference-shell-mobile-navigation.png. Files: student-app-shell.tsx, mode-switcher.tsx, student-profile.tsx, student.css. No tracker count/status changes.


### Annotated FLAME menu and Explore edge action — 2026-10-09

Owner corrections supersede the earlier centered-mode dropdown: the top Study/Curiosity tabs now have no menu/arrow. Sidebar, compact rail and mobile drawer branding use plain FLAME with a mode dropdown, reusing the same Study/Curiosity handlers. Removed logo/tagline from these navigation headers. Explore is a fixed middle-right edge action, outside the breadcrumb header; at desktop pane widths its open action sits on the pane boundary. Existing close control and Escape slide the panel back toward the right before closing the native dialog after 220ms. Pending requests are invalidated immediately, close timers cancel on intentional reopening and unmount, focus returns after closing, and reduced-motion users skip animation/delay. The mobile modal and desktop browsing/reflow contracts remain.

Verification: production build/TypeScript, Explore and sidebar regression suites passed. Expanded Explore checks cover no dropdown in the centered switch, keyboard switching through the FLAME menu, edge-action geometry, close-animation state and reduced-motion completion, plus prior Study/Curiosity/combined-path, pin/recent/My Learning and responsive behaviour. Live signed-in UI checked at the annotated desktop width; screenshot work/flame-menu-edge-explore.png. No backend/database changes or tracker count/status changes.


### Explore breadcrumb alignment and single toggle — 2026-10-09

Latest owner refinement replaces the middle-right edge handle: closed Explore is inline at the opposite end of the curriculum/grade/topic breadcrumb row. A single Explore toggle is rendered: in the context header while closed, or in the drawer header while open, keeping it operable in the mobile native modal. Removed the separate X close action. The button has no independent movement; drawer header, toggle and contents share the panel's slide transform without a delayed opacity fade. Existing 220ms close completion, immediate request invalidation, Escape, reduced-motion handling, and browsing state remain. Focus restoration now occurs after native dialog closing and after the header toggle has remounted. Live Grade 1 Gravity listing/toggle verified; screenshots work/explore-breadcrumb-toggle.png and work/explore-single-toggle-open.png. No backend/database changes or tracker status/count changes.

Verification for the single-toggle refinement: final production build/TypeScript and expanded Explore browser suite passed, including restored breadcrumb alignment, one toggle, focus return after closing, animation/reduced-motion completion and existing Study/Curiosity browsing.


### Explore attached chevron and panel top alignment — 2026-10-09

Explore now uses an accessible icon-only left chevron in the hierarchy row while closed. The same toggle becomes a right chevron attached to the panel's upper-left edge while open and moves with the panel's single slide transform. Panel top is measured from the hierarchy-row button and recalculated on header/window resize; it never rises above that button. Desktop pane offset/height and mobile modal inset/height use this measured anchor; narrow layouts reserve 40px so the attached chevron remains visible and clickable. Study/Curiosity/media/teacher/kit APIs and browsing behaviour are unchanged. Production build/TypeScript and expanded Explore browser regression suite passed, including direction icons, panel/chevron top alignment, toggle/focus, animation/reduced motion and existing responsive browsing. Live Grade 1 Gravity verified with panelTop=chevronTop=70px. Screenshot: work/explore-chevron-panel.png. Tracker counts/statuses unchanged.


### Preserve Explore results across close/reopen — 2026-10-09

Removed unconditional cache clearing and refresh-attempt increments on every drawer opening. A component/member-scoped last successful page now survives close/reopen when its exact path/revision, catalogue, search, pagination and recovery generation are unchanged; it bypasses the short cross-query cache expiry without clearing the DOM or showing a loading flash. Results, filters, pagination and remembered scroll remain. Context/filter/revision changes and catalogue updates still invalidate or select new results; reopening after an error refreshes paths/data. Resource/teacher/kit opening and media delivery continue to recheck current eligibility/version, so a retained listing cannot grant access to withdrawn/stale items. Study and Curiosity use the same presentation persistence; no backend/schema changes.

Production build/TypeScript and expanded Explore browser suite passed. New assertions verify no additional listing requests or loading indicator on reopening after advancing time past the old cache lifetime, retained page/scroll, same-question Curiosity reopening, and a stale curriculum failing on item open then recovering through latest paths. Existing topic changes, combined browsing, viewers, close animation, focus, reduced motion and mobile flow still pass. Tracker counts/statuses unchanged.


### Desktop resizable learning panes — 2026-10-09

Added pointer-captured vertical edge dividers for desktop navigation and Explore. Sidebar width ranges from 220–520px; Explore ranges from 300–760px, constrained by available space to preserve a 400px study area. Arrow keys adjust widths (Shift for larger steps), Home/End use limits, and double-click resets. Widths persist locally across reloads. CSS clamps preferences after viewport changes; tablet/mobile layouts remain unchanged. Navigation resize is enabled with the existing desktop sidebar at 1100px+, and Explore resizing is enabled only in its three-pane desktop layout at 1280px+. Dividers do not take layout width and do not trigger catalogue fetches or alter learning context. A ResizeObserver keeps accessible width values synchronized; pointer completion/cancellation removes drag styling.

Production build/TypeScript and expanded Explore browser regression suite passed. Checks exercise real mouse drags on both edges, study minimum width, no extra listing requests, saved widths in a newly loaded browser page, keyboard resizing, double-click reset, drag cleanup, and hidden mobile separators alongside existing Study/Curiosity/viewer flows. Live desktop values verified: navigation 328px, study 712px, Explore 548px. Screenshot: work/desktop-resizable-panes.png. Source: desktop-pane-resizer.tsx, student-app-shell.tsx, explore-workspace.tsx, student.css and explore-browser.cjs. No backend/database changes or tracker status/count changes.

### Interactive-only HTML5 upgrade — 2026-10-09

Owner authorized application-owned HTML/HTML5 for Interactive alone. Added 2 MiB UTF-8 HTML/HTM uploads, existing private storage/ownership/versioning, isolated JSON document delivery, sandboxed admin/Explore/recommendation viewers, Restart and accurate interactive-request selection/reasons. No Image/Video classification/format/player/provider changes, schema migration, real catalogue mutation/publication, deployment or additional LLM call. Existing approved external Interactive links retain separate-page behaviour. Prepared the supplied Canva lab with packaged CSS, removed platform/remote dependencies, repaired missing pause/resume IDs and added scene layout observation for correct iframe/mobile initialization. [Contracts, authoring workflow and files](backend/stage-9-interactive-html5.md).

Verification: final production build/TypeScript, 17 frontend units, initial 10 focused backend/B9/media-family checks and final three Interactive checks with rollback-only database lifecycle passed. One additional mocked private-cloud read check passed (bounded size, fixed bucket URL, no redirects). The final Interactive browser suite passed original Image preview and native Video play/pause plus HTML5 upload/local and saved preview, scoped Explore viewer, complete Gravity fall, parent/localStorage isolation, Restart, unmount cleanup, mobile scene geometry and Escape. Desktop/mobile screenshots inspected: work/interactive-desktop.png and work/interactive-mobile.png. Broader backend run: 54 passed, two old GIF tests fail because they expect animation rather than the existing video family. The larger resource-library/conversation-image browser suites reached generated native-video fixture failures/timeouts and are not recorded as passing; Image/Video product code was not modified to address them. Final direct native-video smoke passed. Existing B9.11/B10 live cloud/content/device/educator gates and tracker counts remain unchanged.


### Live Gravity HTML resource upload and mapping — 2026-10-09

Owner requested upload of the prepared Gravity HTML and mapping to Grade 1 Gravity and all subtopics. Through the signed-in admin UI, created Gravity Lab — Interactive as HTML5 uploaded media with Grade 1/en and demonstrate/practise metadata, rights/source and keyboard notes. Saved nine associations under FlipLecture / Grade 1 / Science / Gravity (Forces & Motion) / Gravity: one topic-wide link plus all eight current direct subtopics (Everyday Effects of Gravity; Gravity Acts at a Distance; Gravity is a Force; Gravity Pulls Objects to Earth; New entry; Test; test 1; What is Gravity?). Current resource version 2, available, unpublished draft. Existing Image/Video records and mappings were not edited. Saved mapping list verified; stored sandbox preview completed a 10 m fall. Screenshot work/gravity-resource-mappings.jpg.

The existing API on 8000 had no reload flag and rejected HTML using its old loaded validation. Started current API on 127.0.0.1:8001 with --reload and changed only FLAME_API_URL in the ignored frontend local environment to that address. Readiness and authenticated upload/draft/mapping/preview succeeded; old 8000 process left running. This supersedes the earlier port-8000 runtime instruction for the current local session. No migration, publication, deployment or paid model request; live cloud/device/educator gates and tracker counts unchanged.




### Interactive fullscreen landscape toggle — 2026-10-09

Enhanced the shared Interactive viewer only: top-right Full screen/Restore compact icon; parent-owned native fullscreen; landscape orientation request where supported; rotated wide viewport fallback for portrait/unsupported browsers. Toggling retains the same iframe and experiment state. Restore/browser exit unlocks owned orientation; Escape restores before closing; unmount exits fullscreen and restores scrolling. Sandbox permissions are unchanged. Image/Video, backend, schema and real catalogue records are unchanged. See [viewer build and limitations](backend/stage-9-interactive-html5.md).

Typecheck and final production build passed. Expanded browser suite passed native fullscreen/restore, mocked orientation lock/unlock, browser-driven exit, retained simulation state, portrait fallback bounds/wide HTML viewport, rejected native/orientation API fallback, Escape, fullscreen unmount/scroll cleanup and existing Image/Video/upload/Explore/sandbox/restart flows. Desktop/mobile screenshots inspected. Actual phone rotation/browser/accessibility acceptance remains B9.11/B10; step statuses and totals unchanged. No publication, deployment or paid model request.


### Interactive fullscreen manual orientation override — 2026-10-09

Owner superseded automatic phone rotation: removed all orientation lock/unlock calls and rotated CSS. Fullscreen now presents an upright wide HTML canvas (at least the viewport longer dimension), scrollable horizontally in portrait, with visible top-right restore controls. Manual phone rotation naturally fits the canvas to landscape. Native fullscreen/fallback, state preservation, Escape and cleanup remain. Current Interactive/development handoffs updated; earlier rotation evidence above is historical.

Final production build/TypeScript and expanded Interactive browser suite passed, including no orientation API calls, upright portrait/wide canvas/scrolling, visible restore control and manual landscape viewport resize alongside existing native/fallback fullscreen and Image/Video/sandbox flows. Updated portrait screenshot inspected. No backend/schema/media records/publication changes; counts/statuses and physical-device release gates unchanged.


### Browse Media thumbnail opening and video thumbnail management — 2026-10-09

Existing F9/F10/B9/B14 enhanced: thumbnail buttons open media through the same scoped pointer/keyboard workflow as Open media. YouTube/provider thumbnails now appear; old YouTube metadata safely derives an image from its validated video ID. Resource Library manages private static video thumbnail uploads/replacements/removal; native MP4/WebM publication requires one, drafts remain saveable, GIF policy unchanged. Native learner playback uses the saved poster. Migration `20261009_28` applied; drift clean; zero existing uploaded MP4/WebM resources found in a read-only check. No media/mapping/publication backfill. [Build, contracts, checks and limits](backend/stage-9-video-thumbnails.md).

40 focused backend checks passed, with final thumbnail removal/republication checks passing separately; 15 additional bulk-import/B9 resource checks passed. Production build/TypeScript, expanded Explore and Interactive browser suites passed. Current API on 8001 exposes thumbnail delivery and readiness is healthy. Bulk import compatibility excludes the new admin thumbnail field; new imported videos require Resource Library thumbnail setup before publication. B9.11/B10 cloud/device/release gates and all step counts/statuses remain unchanged.


### Resource Library bulk selection and actions — 2026-10-09

Added a leading row checkbox and mixed-state page checkbox to the saved resource table, Select this page, Deselect this page and Clear selection. Selection is keyed by resource ID and persists across library searches, hierarchy filters and pagination. Bulk Map topics, Publish, Unpublish and Delete open a review dialog. The dialog fetches current resource versions; mapping adds selected valid topic/subtopic paths while preserving existing links and publication status. Mapping selections persist across path searches/pages. Each mutation uses existing authorization, validation, concurrency and deletion APIs. Already-matching publication/mapping states are skipped; duplicate submissions are guarded. Successful resources are deselected and the library refreshed; failures remain selected with individual errors/request references and require explicit latest-version review before retry. Operations are per resource, not an atomic transaction over the entire selection.

Delete requires explicit confirmation after reviewing resource titles, mappings and dependencies. Existing backend deletion rules retain shared media and historical records; deletion cannot be undone in the admin UI. No real catalogue records were modified for testing. Source: resource-panel.tsx, new resource-bulk-dialog.tsx, admin.css and new tests/resource-bulk-browser.cjs.

Verification: final production build/TypeScript passed. Isolated bulk browser suite passed 32-record page/search selection, deselection/clear, additive mapping/cancel, published mapping without status changes, path search/page selection, duplicate-click prevention, partial publication failure with review/retry, already-published skip, unpublish preserving associations, delete cancellation/confirmation/dependency information/stale-version retry and narrow-screen layout. Screenshot inspected: work/resource-bulk-library.png. The broader existing resource-library suite timed out at its generated native WebM Play video fixture before bulk verification; it is not recorded as passing. Backend APIs/schema and existing tracker status totals are unchanged.


### Bulk mapping dialog refinement — 2026-10-09

Owner requested a wider mapping dialog, existing-mapping checkboxes, select/deselect all, and faster topic loading. Dialog width now caps at 1120px with responsive hierarchy wrapping and compact resource review. Paths mapped to all reviewed resources are checked; paths mapped to some are mixed, with saved per-resource counts. Explicit checking adds to all; explicit unchecking removes from all. Untouched mappings are preserved. Select/deselect all targets every matching path across pagination, with visible count and scope. Pending map/unmap summaries preserve edits across filters, searches and explicit latest-version recovery. Published status and existing authorization/concurrency checks remain unchanged. This supersedes the previous additive-only bulk mapping behaviour; unmapping is now explicitly supported.

Confirmed client loading cause: sequentially reviewing every resource delayed starting the hierarchy request. Hierarchy now starts immediately and independently; resource version reviews use at most four concurrent reads per review run. Late results from closed/replaced reviews are discarded, and Apply stays blocked until current version review and hierarchy retrieval succeed. Mutation requests remain sequential. Indexed path labels avoid repeated full-list lookup for large selection summaries.

Verification: production build/TypeScript and expanded isolated resource-bulk browser suite passed. Added checks for prechecked shared mappings, mixed partial mappings, published mapping/unmapping, filtered select/deselect across all pages (112 paths), preserved untouched links, bounded review concurrency and hierarchy retrieval before review completion, plus 1120px desktop and 390px dialog fit. Existing bulk partial failures/version retry/cancel/double-click/delete tests passed. Screenshot inspected: work/resource-bulk-mapping-wide.png. No live catalogue mutation, backend/schema change or tracker total/status promotion.


### Bulk mapping status and review filters — 2026-10-09

Added filters beside the bulk path checkbox: Saved mapping status (All, Mapped to any resource, Mapped to all resources, Partially mapped, Unmapped in all resources), Path type (Topic-wide/Subtopic/All), and Pending changes (All/All pending/Will map/Will unmap). Saved status counts direct associations across the currently reviewed resources, separately from pending checkbox edits; inherited subtopic coverage remains explained and is not mislabeled as a direct link. All filters combine with search/hierarchy and apply before pagination. Select/deselect all is scoped to every matching path across pages. Clear path filters resets browsing only and preserves map/unmap edits. Shows matching count and actionable empty state; no additional API requests are made for filter changes.

Production build/TypeScript and expanded isolated bulk browser suite passed. Filter regression verifies any/all/partial/unmapped counts for two resources, topic/subtopic combinations, pending-unmap review, zero-match messaging, stable saved-state results during edits, preservation on filter clearing, and existing concurrency/retry/mapping/deletion flows. Desktop mapping screenshot inspected; 390px dialog fit passed. Sources: resource-bulk-dialog.tsx, admin.css, tests/resource-bulk-browser.cjs. No live resource mutations, backend/schema changes or tracker count/status changes.


### Interactive HTML source editor — 2026-10-09

Added Paste / edit HTML5 code as an Interactive-only media source choice in Add/Edit. A labelled monospace textarea accepts a complete single document, shows UTF-8 byte size against 2 MiB, and provides explicit isolated Preview HTML. Existing uploaded Interactive records load their saved JSON preview document for source editing; loading failures have Retry. Typing creates a text/html interactive.html File and uses existing authenticated upload, storage, creation-reference, version-checked draft save and publication APIs. Metadata-only edits keep existing media. Edits preserve source and uploaded references after failures/latest-version review; source changes invalidate the prior upload reference. Published source stays read-only until explicitly unpublished. Blank/oversized paste is blocked before upload; server document validation remains authoritative. No ZIP/multi-file support, schema/API change or extra publication behaviour.

Changed source: new html-source-editor.tsx, resource-panel.tsx, admin.css and new tests/html-editor-browser.cjs. Production build/TypeScript passed. Focused browser tests passed pasted creation/explicit sandbox preview, one creation under double-click, saved source loading, metadata-only retention, replacement and stale-version recovery preserving code, upload reuse, invalid HTML/oversize handling, publication protection and 390px layout. Existing interactive-browser suite also passed HTML file upload, stored admin preview, scoped Explore delivery, original Image/Video checks, simulation/fullscreen/restart/isolation/mobile/Escape. Narrow screenshot inspected: work/html-source-editor.png. Testing used isolated mock resources; no live catalogue writes or tracker status/count changes.


### Unified Interactive upload, source and preview — 2026-10-09

Owner combined the separate Interactive upload/paste sources. Interactive now has no media-source dropdown or approved HTTPS URL creation field. One editor presents adjacent Code (edit / paste) and Preview tabs plus Upload HTML5 file. A bounded UTF-8 file read populates Code without a server upload; Preview renders current code only on explicit tab selection. The instructor can edit uploaded code and save through the existing file APIs. Original uploaded filename is retained during editing. Invalid extension/type, oversized, blank, unreadable or invalid UTF-8 files retain previous code. Reading blocks Save; unmount invalidates late file reads. Keyboard tab navigation and responsive layout are included. Existing saved external Interactive records/API support remain compatible; no new external link can be entered in this form. Image/Video source options are unchanged.

Production build/TypeScript, expanded html-editor-browser and updated interactive-browser suites passed. Added coverage for absence of Interactive source/URL inputs, upload populating Code without an upload request, invalid file/UTF-8 preservation, Preview/Code keyboard switching and existing draft/retry/version/publication controls. Original HTML upload, saved admin and member/Explore previews, simulation, isolation, fullscreen, Image/Video and narrow layout regressions passed. The first full-suite attempt used a raw CRLF textarea equality check and timed out; corrected the test for native textarea LF normalization and the rerun passed without product changes. Screenshot inspected: work/html-source-editor.png. No backend/schema or live resource mutation; tracker totals/statuses unchanged.


### Automatic bulk import record keys and simplified templates — 2026-10-09

Records.record_key is now optional, including omission of the column. The decoder/preview generates a kind-scoped deterministic SHA-256 alias for identifiable rows using existing ID, resource type/source URL or title, student email, or teacher/kit name. Explicit keys are preserved; generated keys remain in the normalized preview payload, identities, confirmation receipt and exports. Identical identifying input produces the same key, independent of worksheet row number. Natural-match ambiguity/deletion/version/access checks and additive-only merge policy remain authoritative. Blank mappings are not guessed: Excel mapping rows still require a matching Records key; resources may import unmapped and use the UI mapping dialog. Kits retain their mandatory mapping rule.

New live preparation templates omit existing_id and informational publication/version/status columns; record_key remains as an optional column for pre-upload mapping. Existing exported/legacy workbooks with IDs are still accepted, and exports preserve existing_id for precise, ambiguity-safe re-import. No catalogue IDs, identity rows or saved user keys were deleted. UI, generated Guide and both package README copies explain the distinction.

Source: bulk_transfer/workbooks.py, service.py, router.py; frontend bulk-transfer.tsx; tests/test_bulk_transfer.py and package guides. Verification: 17 backend bulk tests passed using rollback-only database fixtures, covering four-kind omitted/blank/explicit keys, simplified template versus export IDs, actionable keyless mapping errors, automatic-key resource preview/review/commit/re-import/export, and previous merge/conflict/security/retention rules. Production frontend build/TypeScript and four-module bulk-transfer browser suite passed. No schema migration or real catalogue import/publication; tracker counts/statuses unchanged.


### Resource Topic preparation labels, table column and filter — 2026-10-09

Added optional Records.topic immediately after title in live resource templates/exports. A value such as Gravity, or Gravity|Force (JSON arrays also supported), is stored as learning_metadata.topic_labels in the existing JSONB metadata. Labels group imports and never resolve/create curriculum nodes or associations. No database schema migration is required. Labels are validated (20 labels, 255 characters each), preserved in exports and metadata-only edits, and use the existing additive draft/publication-preservation policy on re-import.

Resource Library adds Topic between Resource and Media type, displaying labels or Not specified; actual mapping columns remain separate. Topic label search filters saved resources server-side before count/pagination using case-insensitive literal matching. It combines with existing library filters and does not affect saved mappings. Selected resources can then use existing bulk mapping/unmapping. Draft editor exposes Topic labels alongside Title. Shared metadata form retains labels on edits; recommendation selection does not use grouping labels as concept evidence. Generated workbook Guide and both package README copies updated; older static samples remain compatible and can add the optional topic header or use the live template.

Sources: learning_metadata.py, bulk_transfer/workbooks.py/service.py/router.py, resources/router.py, learning-metadata-editor.tsx, resource-panel.tsx, admin.css, backend bulk tests and resource-bulk browser tests. Final production build/TypeScript passed; six focused backend checks passed, including rollback-only import/filter/export and no implicit mapping. Expanded bulk browser suite passed Topic column order, full-library label counts across pagination, case-insensitive grouping, metadata-only label retention, plus existing mapping/unmapping/retry/publication/delete and narrow layouts. Screenshot inspected: work/resource-topic-column.png. No real catalogue writes/publication or tracker count/status changes.


### Learning timeout diagnosis and accurate BFF feedback — 2026-10-09

Owner reported “The API took too long. Refresh the curriculum status before retrying” during a learning question. Confirmed this string was the generic BFF timeout handler for every endpoint, including sessions, capability checks and /ask; it does not establish a curriculum revision conflict or provider-key failure. Current frontend points to 127.0.0.1:8001. Both 8001 and 8000 readiness checks returned HTTP 200/database ok. Active 8001 logs show development reloads waiting for connections, then successful startup; latest session/capability operations returned 200/201 in roughly 7–7.5 seconds. Other recent /ask logs returned 200 in 4–6 seconds. The exact timed-out frontend request was not captured/reproduced: browser inspection failed to initialize, and user resend was requested. Reload-related delay is a possible explanation, not a confirmed sole root cause. No provider request/key/model change, backend restart or real conversation mutation was performed.

BFF now returns stage-specific timeout guidance for /ask (preserve question, use same-question Retry), capability-check (answer not yet requested), and sessions (refresh conversations; completion unconfirmed). Curriculum guidance is confined to curriculum mutations. Timeout/unavailable responses include a safe request reference and server-side diagnostic route/method/deadline/code; route IDs are masked and query strings, bodies, credentials, cookies and session tokens are never logged. Learning errors expose the safe reference. Existing deadlines, retries, quotas, idempotency and concurrency checks remain unchanged.

Sources: auth-bff.ts, student-learning.ts and new tests/upstream-timeout.test.cjs. Two focused timeout tests and production build/TypeScript passed. A successful signed-in retry of the owner’s exact question remains unverified; if the timeout recurs, use the returned reference to identify its stage. Tracker status/count totals unchanged.


### Media browser topic fetch and candidate metadata correction — 2026-10-09

Owner requested verification of topic-specific media fetch. Read-only execution of the real Explore catalogue initially failed with CatalogueCandidate extra_forbidden for topic_labels, including default empty labels on old resources. Root cause: the new admin grouping field was forwarded with all learning_metadata into a strict teaching-candidate contract. This also affected kit/tutor candidates. Added candidate_metadata to exclude admin-only topic_labels while retaining validated teaching metadata; all three owner adapters now use it. Admin labels/filter/import/export remain intact; strict candidate validation, publication/access/suitability and mapping checks are unchanged.

Live read-only verification using current development database/settings returned FlipLecture / Grade 1 / Science / Gravity (Forces & Motion) / Gravity, published revision 22: 12 eligible media (10 videos, 1 image, 1 Interactive), all 12 mapped/published and no drafts. Each of eight current subtopics returned all 10 mapped videos. These are real catalogue-service results, not a signed-in user-browser request; browser inspection was unavailable. Active API 8001 readiness returned 200 after code reload. No real resource/mapping/publication change was made.

Regression: 24 Explore/recommendation-metadata backend tests passed, including rollback-only routed catalogue checks with admin labels on 130 fixture resources, strict three-kind candidate projection, mapping/suitability/version/access/metadata behaviours. Updated the metadata test to include the new optional empty topic_labels field. Explore browser suite passed Study/Curiosity topic changes, combined candidates, scoped open/delivery, stale response suppression and desktop/mobile/focus. Sources: learning_metadata.py; resources/teachers/activity_kits candidates.py; test_explore.py and test_recommendation_metadata.py. Tracker totals/statuses unchanged.


### Mixed media workbook lifecycle and invalid-preview crash — 2026-10-11

Owner reported exporting existing media, adding 20 rows without keys/IDs and re-importing, with Runtime TypeError reading length in BulkTransfer. Confirmed root cause of the UI crash: invalid preview entries do not acquire preserved_fields in the planner, and response() omitted that field, while the renderer assumed the array existed. Backend response now consistently supplies errors/preserved_fields/fields_to_fill and mapping counts; frontend normalizes older saved previews and blocks invalid-row confirmation. Malformed responses produce an actionable status message without claiming that nothing was saved. The underlying workbook validation error is now visible; no user workbook was attached, so its exact row-level cause is not asserted. Missing new file assets and orphan partial mapping rows receive clearer package/partial-workbook instructions.

Added [media management lifecycle guide](MEDIA-MANAGEMENT-LIFECYCLE.md). Preserving old record keys/IDs while leaving both blank on new entries is supported. Partial workbooks do not delete omitted resources/links. New file additions need their assets in a ZIP; existing media references need not be bundled again. Interactive-only packages use the same single-document validation. Existing import remains additive: nonempty detail/media replacement uses the Edit UI, not an overwrite import mode.

Rollback-only lifecycle regression passed actual initial image export, mixed retained row plus 20 automatically keyed HTML additions, renderable 20-row missing-asset preview, confirmed ZIP, confirmation replay, unchanged full re-import, partial Interactive-only unchanged merge, retained omitted resources and additive metadata preservation. Extended four-module browser suite passed invalid old-contract row rendering, disabled confirmation, reload/resume and cancel without crash, alongside existing transfer controls/recovery. Final production build/TypeScript passed. API configured at 8001 returned readiness 200 in 2.61 seconds. Learning space unavailable is a distinct catalogue/session-load failure; exact current authenticated failure was not reproduced. No live resource import or schema/status-count change.

Sources: bulk_transfer/router.py and service.py; bulk-transfer.tsx; test_bulk_transfer.py; bulk-transfer-browser.cjs and lifecycle guide.


### Confirm-import blocking diagnosis and authoring feedback — 2026-10-11

Read-only inspection of the newest pending resource job, Test Curriculum.xlsx, confirmed 32 rows: 12 unchanged and 20 invalid (Excel 14–33). Confirmation is correctly disabled by validation, not by automatic keys. All new rows use unsupported purposes (introduce/discuss/explore/compare/read/investigate/observe/model) and rights_basis=unknown. Read-only copies of the normalized payload, without changing the saved job, additionally identified missing media sources on Interactive rows 15, 23, 25, 28, 32. Fifteen new records are Video URLs; five Interactive entries have neither file nor external URL. No import/metadata/mapping/rights change was applied.

Bulk review now displays an accessible confirmation-blocked count/banner, purpose guidance, and Show first invalid row, linked to the disabled checkbox. Old Pydantic purpose errors are rendered as readable authoring guidance. Resource prevalidation reports invalid purposes, rights basis and missing media source together, rather than revealing one problem per re-upload. No category/rights assumption, silent coercion, skipped row or validation bypass. Blank unreviewed rights may save a draft but existing publication checks still require verified rights. Template Guide and both README copies list allowed values/source requirements.

Verification: five focused backend key/authoring tests, production build/TypeScript and expanded four-module bulk browser regression passed. Browser checks confirm readable invalid rows, disabled confirmation, jump-to-row, resume/cancel, and valid import confirmation/recovery. Existing import remains pending and requires corrected workbook/media plus explicit confirmation. Sources: bulk-transfer.tsx, bulk_transfer/service.py/workbooks.py, authoring/browser tests and guides. Tracker totals/statuses unchanged.


### Metadata-first Interactive draft import — 2026-10-11

Owner authorized Interactive workbook rows without media, to paste HTML later, and clarified owned metadata is test data. New Interactive records may now omit file/external_url and save as unpublished pending-media drafts; Image/Video still require a source. Migration 20261011_29 (from 20261009_28) changes the source constraint only for unpublished Interactive rows with both sources absent. Applied in development. Downgrade refuses to remove that capability while pending drafts exist instead of deleting/mutating records.

Resource create/import schemas accept pending Interactive drafts; same-key re-import retains the source-free record without assigning fake media. Admin response marks source=pending and media_ready=false. Preview returns an explicit interactive_pending message; the resource editor opens blank editable Code without a missing-content error. Library format displays HTML pending. Publication is blocked server-side with interactive_media_required and an actionable message; adding valid HTML via existing upload/PATCH makes the existing resource media-ready and previewable. Type changes to other source-required families are checked before writing. Publication, ownership, rights, size/document validation and member visibility rules are preserved. Column Z status=draft is accepted informational data; bulk creation still cannot publish.

Verification: production build/TypeScript, two authoring/pending lifecycle backend tests and expanded HTML editor browser suite passed. The final pending backend regression also confirms missing Image/Video media remains rejected, metadata-only Interactive import/re-import, pending preview and publication block, later validated HTML attachment, real isolated preview and explicit successful publication. Rollback-only fixtures; no real catalogue import/commit/publication. Browser verifies HTML pending row, empty editor, disabled publication and later paste/save. Guides/template Guide/lifecycle document updated. Existing failed preview must be cancelled and the corrected workbook re-uploaded; saved workbook contents were not automatically rewritten. The owner’s test owned values were unchanged.

Sources: migration 29, resources/models.py/router.py/service.py, bulk_transfer/service.py/workbooks.py, core/errors.py; resource-panel.tsx/resource-library-ui.tsx; authoring/browser tests and guides. Stage totals/statuses unchanged.

### Google Sheets sync refinement — 2026-10-11

B13 bulk-transfer refinement implemented: three resource tabs, manual preview/confirm, schema warning list, stable automatic record keys and identifier write-back, preservation of FLAME mapping/publication/data, pending-write recovery. Isolated backend/browser verification and production build passed; live Google verification awaits configured service-account credentials and Editor sharing. No new stage-count or schema change. Details: [Google Sheets resource sync](GOOGLE-SHEETS-RESOURCE-SYNC.md).


### Reliable local server startup — 2026-10-12

Fixed confirmed web/API port mismatch: web local config targeted 8001 while restarted backend listened on 8000. npm run dev now manages backend readiness and frontend startup on canonical API 8000 / web 3000; validates configuration/BFF key agreement, prevents silent port fallback, cleans owned process trees, and limits Uvicorn reload watching to app sources. Added root Start-FLAME.ps1 and dev:check diagnostic; dev:web remains explicit frontend-only escape hatch and production startup unchanged. Unit readiness/failure tests passed. Two actual cold starts verified API/database readiness, frontend sign-in HTTP 200, and zero orphan listeners after stopping the managed process tree. No database/schema/publication changes; totals unchanged.


### Saved Google Sheets connector refinement — 2026-10-12

Implemented persistent administrator-owned spreadsheet connections with reviewed FLAME-to-Sheets metadata exports, new incoming rows, repeat identity matching and removed-row detection. Owner selected existing deletion workflow: removed linked rows require separate exact-resource confirmation; shared/media/history retention and version checks reused. Migration 20261012_30 applied. No automatic background sync or unattended deletion. Existing nonempty FLAME fields remain authoritative; matched sheet conflicts are reviewed before overwrite. See [connector workflow](GOOGLE-SHEETS-CONNECTOR.md). Counts unchanged.

### Independent local server session — 2026-10-12

Repeated shutdown investigation found neither listener nor the previous launcher alive; logs showed normal backend shutdown and no application traceback. The exact external termination source was not recorded. Child recovery alone cannot survive loss of its launcher. Root Start-FLAME.ps1 now uses a detached background Node session with independent log handles, duplicate-start protection, token-scoped explicit stop requests and status command. Foreground npm run dev remains available. No boot service/task is installed. Verified launcher survives the launching command's exit, repeat start avoids duplicates, explicit stop removes owned listeners, restart succeeds, and backend source reload keeps the same launcher and frontend PID with API health and sign-in HTTP 200. Three startup tests passed. Session control files ignored; no schema/functionality or stage-count change.

### Google Sheets validation-compatible output — 2026-10-12

Replaced forced-text grade/version/publication values with native numbers/booleans for both appended and existing synced rows. Literal IDs and authored content stay text without added prefixes; genuine content apostrophes are preserved. Boolean comparisons normalize TRUE/FALSE to avoid repeat-sync conflicts. Ten isolated connector/Sheets tests passed, including initial export, typed existing-row write-back, repeated sync, retries and confirmed deletion. API/database readiness passed after source reload. Live spreadsheet values were not changed by verification; the next confirmed sync rewrites matched cells with corrected types. Counts unchanged.

Follow-up: owner confirmed grade_min, grade_max and version still showed text markers. Read-only inspection of the saved linked spreadsheet found zero literal apostrophe prefixes, but 32 text version cells and 21 text cells in each grade column. Running worker predated the output fix: detached Windows Uvicorn reload was waiting on its console CTRL_C_EVENT path, so the earlier health-only reload check did not prove new code was loaded. Added Windows-background-only owned-worker replacement wrapper and restarted the local session. Actual source-change verification now confirms old worker PID exits and a new worker starts while the launcher/frontend stay available; API/database check and sign-in HTTP 200 pass. Existing Sheet cells remain untouched until a fresh confirmed sync rewrites their native types. No database/schema/count changes.

Sync confirmation follow-up: saved preview had one invalid Video row (sheet row 15), blocked by provider verification of an unchanged existing YouTube URL. Additive imports now retain the saved source when ID/key resolves to the same media type and identical external URL; new or changed URLs still receive provider/allowlist verification. Added Validate again to cancel the stale preview and obtain a fresh server comparison without confirmation; invalid-count reason is explicit. Rollback-only regression verifies same-source sync succeeds during a provider outage while a changed source fails. Read-only re-comparison of the actual pending payload returned 32 unchanged and zero invalid. TypeScript passed. No live resource or Sheet values were modified; user confirmation still required.

## Latest resource and Google Sheets upgrades — 2026-10-12

This summary consolidates the latest B13 refinements. Development implementation is complete for the listed features; it does not close earlier MVP/release gates.

Deletion lifecycle upgrade: `sync_action` supports explicit delete requests with stable IDs, separate exact-resource consent and deleted-row receipts. Retained linked rows for resources deleted in FLAME are mirrored on the next confirmed sync and never re-imported. Existing missing-row deletion review remains supported. Safe redundant tracking-marker selection/confirmed cleanup added; unknown/conflicting identities remain blocked. Updated template validation, sync review and [operator workflow](RESOURCE-DELETION-WORKFLOW.md). Eleven existing connector/Sheets tests, two new lifecycle/tracking tests, production build/TypeScript and expanded browser confirmation/retry/retired-row/cancellation/mobile checks passed. Live Sheet read succeeded; zero redundant markers at check time. No live deletions, Sheet writes or marker repair executed during verification; no migration or count change.

Deletion-column follow-up: existing connected Sheets no longer require manually adding sync_action. Confirmed sync appends it to all three resource tabs if absent, sets dropdown/header guidance, and writes sync/deleted values while preserving existing columns. Preview lists planned additions; retries recognize the appended header. A focused partial-provider-write regression passed and confirms header addition is idempotent; TypeScript passed. No live Sheet headers were edited during verification.

Automatic-column final verification: seven connector/deletion tests passed with original templates missing sync_action, plus the focused partial-header/write-failure retry test passed separately. API/database health passed. Existing row updates, appended exports, retained deleted rows and repeated sync all use the same added column; no duplicate columns on retries.

### Resource Library refresh display — 2026-10-12

Owner reported briefly seeing deleted media before the fresh list arrived. API already excludes deleted_at records and BFF requests use no-store; Resource Library kept rendering previous rows during asynchronous refresh. Added an opt-in catalogue display mode for resources that hides prior rows/counts during initial load, refresh and query changes, associates loaded data with its query, and uses the current query for refresh callbacks. Error and stale responses cannot restore old rows; other catalogue display defaults remain. Table selection is disabled while loading and the count shows Loading resources. Production build/TypeScript and focused isolated browser checks passed delayed deletion refresh, cold reload, filter changes, late old responses and failed refresh without cached rows. No database, resource/publication or Sheet changes; tracker counts unchanged.

Local storage follow-up: configured `E:/FLAME/flame-resources` with images/media/interactive directories. Generated database/cloud keys remain unchanged; a shared local resolver routes suffixes into those folders, with legacy flat-file fallback. Admin/member delivery, HTML preview and bulk export use the resolver. Three original uploads copied and SHA-256 verified; old files retained and all three resource asset references present at the new root. New root ignored by Git. Two local-layout tests and four Interactive tests (including rollback-only upload/preview/publication/scoped-delivery/withdrawal) passed. No catalogue/publication/schema changes; manually placing a file does not register it as a resource.

| Feature | Current behavior | Delivery / acceptance status |
| --- | --- | --- |
| Saved data connection | One spreadsheet with Image, Video and Interactive tabs; saved per administrator in FLAME and restored across browsers. | Implemented; migration 30 applied. Live linked spreadsheet read succeeded. |
| Incoming data | New rows become drafts; generated record keys and existing IDs establish repeat identity. Supported additive merges preserve existing nonempty FLAME values. | Implemented; isolated initial/repeat/partial/retry lifecycle evidence recorded. |
| FLAME to Sheets | Missing library resources export to their type tab. Reviewed FLAME metadata replaces differing matched Sheet values after confirmation. | Implemented; mocked provider/rollback-only verification passed. Latest live write acceptance remains unverified. |
| Removed Sheet rows | Only previously successfully linked missing rows qualify; deletion preview and separate exact-resource consent are required. Existing deletion workflow removes mappings/publication and retains media/history. | Implemented and isolated-test verified; no unattended deletion. |
| Conflict handling | Column/row warnings, invalid-row blocking, snapshot/version rechecks, ambiguous identity rejection, cancel/revalidate and durable pending write-back retry. | Implemented. Latest saved-preview comparison: 32 unchanged, zero invalid after source-retention fix. User must obtain a fresh preview and confirm. |
| Cell formatting | grade_min, grade_max and version are numbers; published is boolean. Existing matched rows receive corrected types on confirmed sync. Genuine content apostrophes are preserved. | Implemented; 10 connector/Sheets tests passed. Read-only live audit found old text-typed cells; correction was not written during verification. |
| Template guidance | Gridlines on all media tabs, applicable dropdown/numeric/text validation through row 2001, header notes and examples. Server validation remains authoritative after Google conversion/paste. | Implemented; prior template evidence retained. |
| Interactive authoring | Drafts may sync without HTML; paste/upload and sandbox preview remain in the resource editor. HTML/file bytes do not travel through Sheets. | Implemented under existing Interactive workflow. |
| Curriculum mapping and recommendations | Mappings remain in FLAME. Topic/subtopic links determine eligible media; title/description, concepts/synonyms, grades, languages, purposes and supporting metadata rank suitable candidates. Sheet topic labels organize resources and do not create mappings. | Existing behavior preserved; no recommendation algorithm change in this sync upgrade. |
| Local server continuity | Start-FLAME.ps1 starts a detached session with stop/status controls. Windows reload now replaces the owned API worker without console Ctrl+C; API 8000 and web 3000 remain canonical. | Verified actual worker replacement, retained launcher/frontend, API/database health and sign-in HTTP 200. |

### Remaining acceptance and limits

- Run a fresh preview and explicitly confirm the user's linked Sheet sync, then verify native numeric cells, repeat-sync stability and any reviewed additions/updates. Current verification performed live reads and comparison only.
- Sync is manual: Validate and preview → Confirm. Automatic polling, real-time synchronization and unrestricted bidirectional overwrites are not implemented.
- Sheets resource transfer does not manage Teachers, Students, Kits or curriculum mappings; existing Excel/ZIP transfers remain available for those modules.
- Verify hosted credential/Editor access, provider quota/retry behavior, concurrent collaborator edits, maximum-size performance and existing release/device/private-storage gates before deployment.
- No new numbered steps or status promotions were introduced. Totals remain 130 completed, 20 partial and 12 not started out of 162.


### Local resource move completed — 2026-10-12

Owner explicitly requested moving the existing files after the initial verified copy. Rechecked SHA-256 equality and configured destination for all three old-root files before removing their originals. Two PNGs now reside in flame-resources/images and one HTML document in flame-resources/interactive. Old .private-resources contains no files; empty directories retained. Database keys remain unchanged; API/database readiness passed. No resource records or publication status changed.

### Light and Shadow instructional HTML5 collection — 2026-10-12

Created 15 self-contained instructional activities in flame-resources/interactive from a read-only curriculum inventory: Grade 1 Light/Shadows/light-and-sound-signals/lighthouse and Grade 4 light energy, straight paths/materials, reflection and refraction topics. Covers 61 subtopic lesson entries and 30 matching FlipLecture/TN Stateboard topic paths. Each lesson includes an explanation, experiment instruction, adjustable SVG model, observation, check with corrective feedback and keyboard-accessible controls. No external dependencies, network requests or student-progress writes. Source generator and [coverage/import guide](LIGHT-SHADOW-INTERACTIVES.md) plus JSON path manifest retained. HTML validator/media inspection passed all 15; sandbox browser checks passed all 61 lessons, control/reset/quiz behavior and keyboard/mobile overflow. Desktop/mobile screenshots reviewed. Models are simplified and labelled; no educator acceptance or catalogue publication claimed. Files only: no live resource creation, mappings or publication performed. Stage counts unchanged.

### Light/Shadow Curiosity results and approved publication — 2026-10-12

Owner reported no results for light and shadows. Live investigation found no registered Discovery Lab resources and a resolver bug: the globally preferred Light leaf under Needs of Plants discarded explicitly requested Light/Shadows topics. Explore now resolves precision per parent and prioritizes explicit topic names over unrelated identically named leaves, preserving combined-topic and precise-subtopic queries and scoped deduplication. Fourteen Explore tests passed; one DB integration case skipped in that run. Registered all 15 generated activities as mapped drafts using validated owner-scoped upload/create workflows. Owner then explicitly approved publication with owned/FLAME/members rights details. Versioned edit/publication handlers published all 15, with 30 topic-wide mappings, grade/language/purpose/concept metadata and accessibility notes. Live light and shadows browse returns the Light and Shadows Interactive labs; scoped open and sandbox HTML delivery passed for both. Activity manifest records resource IDs/publication/versions. Earlier files-only delivery note is superseded by this approved registration/publication. No unrelated media edited, no educator-quality acceptance or stage-count change.

## Current Interactive status — 2026-10-14

Documentation reconciliation of deliveries recorded through October 13; receipts and local project READMEs were read on October 14. This review does not assert fresh database state or rerun the recorded application/browser checks. These refinements belong to B9.2/B9.5/B9.6/B9.11, F7.2/F9.7 and F10/B14; no numbered steps or status promotions are added.

| Activity / capability | Latest recorded state | Remaining acceptance / next action |
| --- | --- | --- |
| Light/Shadow collection | Fifteen activities explicitly approved and published October 12 with 30 topic-wide mappings; scoped browse/open/HTML delivery passed. | Full signed-in learner, private-cloud, device/accessibility and educator acceptance under B9.11/F8/B10. |
| What is Light? / Gravity Lab | Published Phaser upgrades October 13; receipts preserve 12 and 146 mappings respectively. Later object controls and Gravity auto-reset retain publication/mappings. | Verify current versions through the protected catalogue before subsequent edits; close remaining B9.11 gates. Receipt versions are delivery snapshots. |
| Embedded Rive support | Embedded runtime/WASM works within self-contained HTML; allow-scripts sandbox and 2 MiB limit retained. Recorded security probes block parent access, JavaScript eval and network. | Check Canvas Lite support per artwork. Raw .riv/ZIP import, multi-file delivery and larger runtimes remain future work. |
| Rive cat / States of Matter | Registered unpublished testing drafts; saved admin previews verified. Matter is original illustrative artwork; cat community-artwork rights require review. | Review rights/content, add approved curriculum mappings and obtain explicit publication authorization before learner release. |
| Weather World | Five-weather file-only prototype; no resource row, mappings, publication or Sheet writes. Source and recorded checks: [activity README](../flame-resources/interactive/weather-world/README.md). | Preview the bundled index.html through the Interactive editor; registration/mapping/publication require a subsequent owner request. |

### Interactive activity folders — 2026-10-13

- Moved the five existing active HTML activities into named folders under `E:/FLAME/flame-resources/interactive`: `what-is-light`, `how-shadows-form`, `shadow-position`, `light-travels-in-a-straight-line`, and `gravity-lab-interactive`.
- Opaque HTML filenames, database storage keys, resource IDs and curriculum mappings remain unchanged. Local storage resolves named activity folders, rejects duplicate keys and paths escaping the interactive directory, and retains flat/legacy compatibility. New local HTML uploads receive a separate folder named by their storage identifier.
- Verified all five moved documents through ResourceStorage with SHA256 equality; three local storage tests passed. Migration receipt: `work/interactive-folder-migration.json`.
- This change organizes storage only. The sandbox still requires self-contained HTML; separate JavaScript/assets and Phaser ZIP package delivery are not yet implemented.

### What is Light? Phaser activity — 2026-10-13

- Converted `flame-resources/interactive/what-is-light` into an editable Phaser 3.90.0 project (`index.html`, `js/game.js`, local `js/phaser.min.js`, MIT license, `build.py`, README).
- Five experiments replace the text-heavy lesson layout: aim light with a draggable torch, test light sources, tilt a mirror, compare materials, and follow reflected light into an eye. HTML keyboard controls accompany Canvas interaction; artwork is procedural and the activity uses no network/assets downloads at runtime.
- Bundled the project into its existing opaque HTML entry file (1,208,540 bytes), retaining the resource ID and all 12 mappings. Published resource updated from version 5 to 6 with new description/accessibility metadata and Phaser attribution. Previous HTML preserved in `work/what-is-light-before-phaser.html`.
- Passed FLAME HTML validation and actual sandbox browser checks for Phaser boot, five experiments, drag, keyboard, reset, mobile overflow, zero external requests and page errors. Desktop/mobile screenshots in `work/what-is-light-phaser-*.png`; receipt in `work/what-is-light-phaser-upgrade.json`.
- Separate package/asset delivery is still not enabled. This activity works through the current self-contained HTML player.

### Gravity Lab Phaser upgrade — 2026-10-13

- Rebuilt `flame-resources/interactive/gravity-lab-interactive` as a Phaser 3.90.0 project with editable HTML, local JavaScript/library, MIT license, README and build script. Existing opaque HTML entry remains a self-contained FLAME-compatible bundle (1,210,150 bytes).
- Four hands-on experiments: draggable drop height, mass comparison with prediction, upward throws, and Earth versus Moon/Mars. Live measurements, pause/resume, reset, slow motion and expandable explanations supplement the animated scene. Keyboard controls accompany pointer interaction.
- Constant near-surface gravity and no air resistance/bounce are explicit. Checked landing times and throw peak/return time against kinematics, and rounded world gravity against NASA's planetary fact sheet.
- Published resource advanced from version 12 to 13 with all 146 mappings and its resource ID preserved. Updated byte sizes, description, accessibility note and library/science attribution. Previous HTML retained in `work/gravity-before-phaser.html`; receipt in `work/gravity-phaser-upgrade.json`.
- Browser checks passed in the actual FLAME sandbox: all four experiments, dragging, mass-independent fall, world comparisons, pause/resume, slow motion, reset, keyboard/mobile overflow, zero page errors/external requests. Screenshots: `work/gravity-phaser-desktop.png`, `work/gravity-phaser-mobile.png`.

### Gravity auto-reset — 2026-10-13
- Gravity Lab automatically resets two seconds after landing, preserving settings and result text. Comparison modes wait for both balls. Pending resets are cancelled on mode changes/manual reset; no automatic replay.
- Sandbox checks passed for all four experiments, result hold, setting preservation and timer cancellation. Published activity revised with mappings unchanged; previous bundle retained in work/gravity-before-autoreset.html.

### Light Lab object actions — 2026-10-13
- Moved action controls onto scene objects using accessible HTML buttons aligned with the Phaser artwork. Torch tap/drag, source cards, mirror rotation and material cycling now work inside the interactive box. Keyboard arrow/activation controls and responsive hit areas preserved.
- Updated editable index.html/game.js and registered standalone bundle through a versioned resource edit, preserving publication and all 12 mappings. Sandbox browser checks passed for all five experiments, dragging without accidental toggles, keyboard controls, mobile overflow and in-scene hit areas. Prior HTML retained in work/light-before-object-actions.html.

### Gravity object interaction handles — 2026-10-13
- Gravity actions now attach to scene objects: ball tap/drag, mass/power badges, world surface toggle. Pause/reset/slow motion moved inside the lab header. Keyboard controls, prediction, live measurements and two-second auto-reset retained.
- Updated editable project and registered bundle via versioned resource edit, preserving published status and all 146 mappings. Sandbox checks passed for all four experiments, pointer/keyboard actions, pause/resume, auto-reset and mobile. Previous HTML retained in work/gravity-before-object-actions.html.

### Embedded Rive sandbox support — 2026-10-13

- Enabled WebAssembly compilation with `wasm-unsafe-eval` in both API and InteractiveExperience CSP. JavaScript eval, external network, nested frames, workers and parent DOM/session access remain blocked. Existing HTML/Phaser sandbox mode remains `allow-scripts` only; the 2 MiB HTML limit and media data model are unchanged.
- Converted the supplied cat-follow-pointer Rive ZIP into a self-contained Canvas Lite 2.37.6 demo with embedded WASM/artwork, pointer/touch gaze binding, keyboard arrows/Home, centre and pause/resume. Runtime MIT licence embedded in the bundle. Stored project: `flame-resources/interactive/rive-cat-demo`; existing ZIP untouched.
- Registered draft resource `b5e14408-02e0-5081-9a08-8ea2aa5e7b7f`, “Rive Demo - Cat follows pointer (sandbox test)”, version 2. Saved admin preview verified. No curriculum mappings/publication: supplied community artwork rights require review before learner publication.
- Checks passed: 3 non-DB interactive tests, 3 local storage tests, TypeScript, and browser sandbox boot/render/gaze binding/pointer/keyboard/pause/centre/resize/mobile. Security probes confirmed parent access, JavaScript eval and network blocked; Phaser still boots. Receipt: `work/rive-cat-registered.json`; screenshots: `work/rive-cat-desktop.png`, `work/rive-cat-mobile.png`.
- This supports embedded Rive HTML wrappers. Raw .riv/ZIP import, larger WebGL runtimes and general activity package delivery remain future work. Canvas Lite feature support must be checked per artwork.

### States of Matter Rive proof of concept — 2026-10-13

- Added `flame-resources/interactive/states-of-matter` with three state buttons, short explanations and direct mouse/touch interaction. Solid particles are individually draggable within 12 scene units and smoothly return while vibrating; liquid particles move/rearrange under dragging; gas particles scatter under pointer motion/drag and bounce at container walls. Hover highlighting and keyboard arrows/Space included. No heating/cooling, phase transitions or quizzes.
- Authored an original Rive container, interaction halo and three animation states in RML. Official Rive CLI 1.5.1 downloaded to work/tools/rive-cli, SHA256-verified (no global installation/account), compiled a script-free .riv. Verify/inspect passed with zero problems; headless screenshot inspected.
- Activity-local JavaScript controller synchronizes selected state and pointer effects into Rive view-model properties and runs particle motion/collisions. Existing FLAME sandbox/fullscreen/restart player unchanged; runtime/WASM/artwork embedded under the existing 2 MiB limit, with no external downloads.
- Registered a Resource Library testing draft titled “States of Matter - Particle Play Lab (Rive prototype)”; no automatic learner publication or curriculum mapping. Saved admin preview verified. Receipt: work/matter-registered.json.
- Sandbox browser checks passed exact solid selection/clamping/spring-back/vibration; liquid displacement/rearrangement; gas hover push/scatter/confinement/bounces; Rive state and colour synchronization; keyboard/mobile overflow; all three touch states and pointer cancellation; zero page errors/network. Screenshots: work/matter-gas-desktop.png and work/matter-solid-mobile.png. This remains an illustrative particle model, not calibrated molecular dynamics.

### Weather World prototype — 2026-10-13

- Created `flame-resources/interactive/weather-world/index.html`, “Weather World — Explore Different Weather Types”, using the States of Matter architecture: script-free original Rive landscape/state machine plus modular JavaScript pointer/particle controller. Reused Rive CLI 1.5.1 and Canvas Lite 2.37.6. No backend/database/resource-row changes, mappings, publication or Sheet writes.
- One rounded storybook environment contains gradient sky, Sun/clouds, meadow, animated tree and grass, house, path/puddles and snow cover. Five looping Rive states blend weather colours/light, cloud appearance, tree motion, Sun and snow visibility. JavaScript controls direct cloud positioning through the same Rive view model, plus sun glow, raindrop response, splashes/ripples, gust direction/leaves and snow swirl/puffs.
- Added Sunny/Cloudy/Rainy/Windy/Snowy buttons, selected-weather explanation and observation prompt, direct pointer/touch/keyboard actions and weather-preserving reset. Fixed touch state switching after a canvas drag by handling pointer-up and suppressing the duplicate compatibility click. No quizzes, season or phase simulation.
- CLI verify/inspect passed with zero scene problems; headless artwork inspected. Existing FLAME HTML validation/CSP accepted the 1,388,681-byte self-contained bundle. Final browser checks passed five Rive state/sky transitions, all direct weather gestures, keyboard/reset/mobile layout and all five native touch gestures, with zero network/page errors.
- Preview without saving: Admin → Resource Library → Add resource → Interactive → upload weather-world/index.html in the HTML editor → Preview. Source/rebuild/verification guide: flame-resources/interactive/weather-world/README.md. Browser check: work/qa/check-weather-sandbox.cjs; screenshots: work/weather-*-desktop.png and work/weather-snowy-mobile.png. Tracker counts/status gates unchanged.

### Tracker reconciliation — 2026-10-14

Read the root README and this tracker; checked the October 13 Light/Gravity publication receipts, cat/Matter draft receipts, prototype READMEs and current API/viewer CSP source. Reconciled latest summary, affected F7/F9/B9 evidence, B14 routing and execution/readiness guidance with the existing October 12–13 records. Corrected the Weather World browser-check path. Earlier dated evidence remains historical. Recounted all 162 unique numbered rows: frontend 43 completed / 9 partial / 3 not started; backend 87 completed / 11 partial / 9 not started; total 130 completed / 20 partial / 12 not started, zero blocked. Documentation only: no application tests rerun, fresh database audit, sync confirmation, resource publication or deployment. Next actions remain the acceptance gates above.

### Pending-stage delivery — 2026-10-14

Started with B7.7 under the owner's instruction to finish pending work. B7 is now complete in development: signed-in Chrome Study and Curiosity answers, reload/recent restoration and follow-ups passed; Curiosity pending-response reload restored one saved follow-up. Live provider deadline probe recorded two ReadTimeouts in about 1.1 seconds without changing production deadlines. Real loopback HTTP timeout/disconnect/503 tests and five malformed-provider-shape checks passed. Fixed shape validation so malformed envelopes return invalid_provider_output. Rollback-only B7 answer/replay/history-reference and interrupted-worker recovery checks passed (three tests); two-worker B5 claim test passed and cleaned its own UUID fixtures.

Completed B5.3/B5.5/B5.9 and F2.4/F5.4 against the recorded evidence. Added optional Answer reference details for successful answers and owner-scoped references in paginated history; live restored display verified. B5/B9 catalogue suite: two passed/one opt-in concurrency skip; concurrency was then run separately and passed. B9 resources: four passed. Reconciled the stale GIF test with Video family, optional-card recommendations and local storage resolution; its rollback-only lifecycle rerun passed. No product classification/selection change was made for that test.

Latest full default backend suite: 163 passed, 47 opt-in skips, two upstream deprecation warnings; pip check clean. TypeScript, 23 frontend units and isolated production Next.js build passed. GitHub Actions checks were added but have not yet run on GitHub. Screenshots: work/b7-study-continuation.png, work/b7-curiosity-continuation.png, work/b7-restored-reference.png. Receipts: work/b7-live-timeout.json and work/b9-private-storage-check.json. Synthetic live learning conversations remain in the signed-in account as verification evidence; unrelated history was preserved.

Owner confirmed Vercel for both MVP projects, with Root Directory development/apps/web and development/apps/flame-api. Added explicit tool.vercel entrypoint and [Vercel preparation/operating guide](VERCEL-DEPLOYMENT.md), plus server-only Sheets JSON credential support (five focused checks passed). Provisioned private flame-resources bucket in the configured development Supabase project. Synthetic PNG signed delivery and authenticated HTML read passed; anonymous access was blocked and both probe objects were removed. Local backend/storage settings, real files, resource IDs/mappings/publication and applied migration head were unchanged. Private-bucket expiry, real catalogue cloud migration/hosted delivery and device/educator acceptance still belong to B9.11.

B10.5/B10.7 started and remain PARTIAL. B8 scoring is assigned to the owner, who agreed to review the existing 17-output packet; no case/threshold/score acceptance inferred. Still required: Vercel-compatible large upload/export and durable import-preview handling, actual hosted secrets/restricted DB role, managed retention/scheduling/restoration, full admin/member regressions, supported physical devices/screen readers, owner quality/pilot acceptance and separate deployment decision. Six PARTIAL steps became COMPLETED; two NOT STARTED steps became PARTIAL. Totals: 136 completed, 16 partial, 10 not started; all 162 IDs preserved.

### Resumed private-transfer and pilot verification — 2026-10-14

Completed the owner's choice to preserve large upload limits with direct private-storage uploads. Added administrator-only authorization/confirmation/export routes and browser adapters for resource uploads, curriculum workbooks, all four bulk previews, templates/packages and curriculum exports. Only metadata and encrypted owner-bound tickets cross Functions; browser bytes use private signed URLs. Size/SHA/media/package validation, stable server-generated IDs and completion replay preserve existing ownership/publication rules. No migration or local storage-setting change. Durable curriculum bytes and bulk preview state already exist in PostgreSQL. API/BFF duration ceilings are 300 seconds; transfer transport waits up to 240 seconds.

Real synthetic private-storage verification: 4,923,512-byte PNG uploaded directly, confirmed, replayed, retrieved with matching SHA and followed by a private XLSX template download. Fixed Supabase missing-object HEAD handling to recognize 400/404, matching its official storage client. All generated staging/final/export keys were checked absent after cleanup; test database rows rolled back. The live direct suite passed 11 checks. Subsequent rollback-only direct/resource/curriculum/bulk regression: 36 passed, one live-storage opt-in skipped (already verified separately). Default backend suite: 170 passed, 53 opt-in skips; the subsequently added admin-guard test passed and covers all 72 registered admin operations. Two upstream deprecation warnings remain.

Frontend: 27 unit checks, TypeScript and isolated production build passed. Production-browser replacement import, sidebar and resource-bulk suites passed. Sidebar checks additionally verify sign-in redirect, no development answer preview, unavailable progress without fixture percentages, and unsupported attachments retained locally without an ask. Resource-bulk tests now use the current page-selection checkbox instead of two obsolete buttons. F8.5 is complete in development; B10.1–B10.4 started and remain partial. No GitHub Actions run, Vercel deployment, permanent catalogue import/publication or real-asset cloud migration occurred.

Added dry-run/execute cleanup for generated staging/export objects older than 24 hours; fresh/recently updated objects and catalogue assets are retained. Cleanup unit check passed. Actual maintenance scheduling, unreferenced final-upload recovery, full-size Supabase/Vercel plan/load limits, hosted secrets/runtime role, backup/log retention/restoration, legacy B4 harness modernization, full signed-in admin/member journeys, supported physical devices/screen readers and owner quality/pilot acceptance remain open. The owner is the reviewer for the existing 17-output Study packet; scores and accepted thresholds have not been supplied.

Current totals: 137 completed, 20 partial, five not started; all 162 unique step IDs preserved. See [Vercel guide](VERCEL-DEPLOYMENT.md) for implementation and remaining release requirements.

### Main update and deployment handoff — 2026-10-14

Owner requested the verified local changes be updated on main, confirmed no Vercel projects exist yet, and moved hosting setup/server testing to a separate thread. Final local checks passed: 171 default backend tests, 53 opt-in skips and two upstream warnings; 27 frontend units, TypeScript and isolated production build. Successful-answer reference details were removed from student rendering at the owner's request; internal correlation metadata remains. No hosted URL exists to verify and no deployment was performed. Use VERCEL-DEPLOYMENT.md for the two exact roots, environment settings, private-storage/provider limits and remaining release gates. Tracker statuses/counts remain 137 completed, 20 partial and five not started.

Publication verified: application changes pushed to origin/main as `5c0f25886a135ce073364f1065d7d282c1d977a8`; remote main matched and the working tree was clean. [GitHub Application checks](https://github.com/fliplecture-dev/FLAME/actions/runs/38524414198) passed both jobs: clean Ubuntu dependency installation, backend tests/pip check, frontend TypeScript/units/production build. This is CI evidence, not hosted Vercel acceptance; release gate statuses are unchanged.
