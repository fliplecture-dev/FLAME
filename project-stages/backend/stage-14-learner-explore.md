# F10 / B14 — Learner Explore workspace

Answer-footer update — 2026-10-15: `GET /api/v1/explore/summary?session_id=<UUID>&message_id=<UUID>` requires the same member and saved-answer ownership checks as answer context. It returns no-store `{videos,images,interactives}` integer counts over all eligible media in that answer's Explore context, without pagination or recommendation selection. Study validates the saved path/revision; Curiosity combines explicit published path matches and deduplicates resource IDs after suitability filtering. GIF visuals count as images. The frontend replaces “Explore this topic” with positive counts only; loading/error/zero results stay hidden. Click opens the existing answer-context media panel, where current eligibility and delivery checks still apply. The header Explore control and teacher/kit recommendation entry points are unchanged. F12/F13 generated visuals do not inflate catalogue counts. No extra provider calls, persistence, acknowledgements or schema migration were introduced.

Development delivery: 2026-10-08. Progress statuses belong to [STAGES-STEPS.md](../STAGES-STEPS.md).

## Existing behaviour and implemented boundary

Resources, Teachers and Activity Kits already own published candidate eligibility and public detail data. Recommendations ranks those candidates for a saved Study answer, persists its choices and suppresses repeated displays. Its opening route authorizes a saved selected recommendation, not an arbitrary item in a catalogue.

Explore adds independent member browsing using the existing owner services. It does not call the LLM, rank a new recommendation, write recommendation history, change mappings or change the conversation's Study context. Manual Teachers browsing is an explicit student action and does not change the human-help requirement for automatic tutor recommendations.

The learner header has a compact Explore CTA. Media, Teachers and Activity Kits share one panel, path filters, search, language/type filters, counts, pagination and existing viewers. The panel reflows alongside the conversation at 1280px and above; below that it uses a native modal drawer with focus trapping, Escape and focus return. This breakpoint reserves space for the existing navigation, reading area and a 350–420px Explore pane rather than copying the reference's fixed dimensions.

Static image thumbnails load only near the visible panel region through authorized delivery; GIFs and videos use icons and only play when opened. Thumbnail previews do not acknowledge a recommendation or record a media-open event. The compact video icon/title design remains. Viewer open/play uses the existing serialized activity/CSRF queue.

## Member API contract

All routes require the existing active member identity. The B9 BFF explicitly allowlists these routes; no admin catalogue endpoint is used by the panel.

| Method / route | Parameters | Result / checks |
| --- | --- | --- |
| GET `/api/v1/explore` | `topic_id`, optional `subtopic_id`, `curriculum_revision`; `kind=resource/tutor/kit`; `search`, `media_type`, `language`, `offset`, `limit` (1–50, default 24), optional `focus_id` | Published eligible items across the complete selected topic scope, matching total and page. Stable title/ID sorting. Focus ID chooses the page containing a recommended item if it remains eligible. |
| GET `/api/v1/explore/context` | `session_id`, `message_id` | Owned saved Study answer's published path/revision, or Curiosity's current matching paths. Multiple matches trigger combined browsing internally; no path-choice list is rendered. Stale Study revisions and foreign sessions are rejected. |
| GET `/api/v1/explore/curiosity` | Owned Curiosity `session_id`, `message_id`; catalogue kind, search/media/language filters, offset/limit/focus | Re-resolves current published matches, retrieves eligible items from each owner, applies suitability, deduplicates by kind/ID, sorts and paginates the combined dataset. Each item includes `browse_path` for independently checked opening and delivery. |
| GET `/api/v1/explore/{kind}/{candidate_id}` | Selected path/revision, required `version`, optional `language` | Rechecks owner eligibility, suitability and current version before returning public media/profile/guide data. No saved recommendation is required. |
| GET `/api/v1/resources/{id}/delivery` | Existing parameters remain compatible; Explore supplies selected path/revision, version and optional language | Resources revalidates scoped eligibility/version independently before issuing existing playback or short-lived delivery data. |

List DTO: ID, version, kind/type, title, description, availability state, languages, explicit grade range, mapping coverage and static-image MIME/accessibility information. No private storage keys or credentials are returned. Unknown grade/language metadata does not become a fabricated suitability claim. Known grade mismatches are excluded; language filters apply when metadata exists.

`curriculum.public_paths.describe_browse_path` validates published, active Topic ancestry, optional Category ownership/archive state and the exact Subtopic in a single read-only query. It does not acquire the curriculum-edit lock used by mutation paths. Existing resource, teacher and kit eligibility remains with their owners; common suitability is a pure shared contract helper.

Topic-wide media/kits cover the topic and its subtopics. Direct Subtopic associations do not cover sibling subtopics or a Topic-only view. Teacher expertise is scoped to the current Subject UUID, with optional Topic expertise. Unknown tutor availability remains explicitly labelled; known-unavailable tutors are excluded. Kits retain their publication/material/guide/storage checks. Unmapped, withdrawn, draft, deleted and unsuitable media is excluded through the same owner services.

## Context and state

- CTA initializes from the current Study context; reopening in that context preserves independent panel browsing state.
- Browsing another path does not select a new Study conversation. Actual Study navigation updates an open panel automatically.
- Curiosity follows its latest saved question. One match uses scoped browsing; multiple matching curricula/grades display their combined eligible media/teachers/kits directly, without a path choice. Unmatched questions clear old results.
- Searchable path lookup includes topics and subtopics. Cascading selectors reset invalid children. Category stays hidden in the learner interface under the existing product decision; exact Topic IDs retain its ancestry.
- Every completed saved answer has Explore this topic; selected recommendations have a related catalogue link. Answer links resolve the owned saved answer context, choose the correct tab and can locate/highlight an item beyond page one.
- Existing automatic inline images, optional cards and earlier references remain unchanged. Browsing never rewrites previous answer decisions or marks catalogue items as displayed recommendations.
- Panel search, filters and position survive viewer return and closing/reopening within the current context. They are not promised to persist across a full page reload.
- Fetches are lazy; search is debounced 250ms. AbortController and request generations discard outdated results. Opening has an immediate duplicate-submit guard. Obsolete answer-context responses are also discarded.
- A component/member-scoped cache holds at most 20 list responses for 15 seconds, with no signed media URLs. Refresh results invalidates it. Open/delivery always rechecks the server. Refresh paths updates published trees/revision while retaining selected IDs and search values; unavailable IDs require a new path selection.
- Errors do not remove the explanation. No videos autoplay, kits launch or tutors receive contact. Existing external-video provider policy is unchanged.

## Changed application files

Backend:

- `app/modules/learning_response/explore.py`, `explore_router.py`: browse/context/open orchestration over catalogue owners.
- `app/modules/curriculum/public_paths.py`: efficient read-only published ancestry.
- `app/contracts/catalogue.py`: shared suitability helper.
- `app/modules/resources/member_router.py`: scoped delivery revalidation.
- `app/modules/activity_kits/candidates.py`: precise Subtopic coverage in public candidates.
- `app/main.py`, `app/core/errors.py`: routes and actionable safe errors.
- `tests/test_explore.py`: unit/security and rollback-only integration coverage.

Frontend:

- `src/features/learning/explore-context.tsx`, `explore-workspace.tsx`, `explore-thumbnail.tsx`: context, panel, requests, state and static thumbnails.
- `student-app-shell.tsx`, `student-workspace.tsx`, `flame-conversation.tsx`: CTA/layout and answer entry points.
- `catalogue-recommendations.tsx`: related links and reused viewers with optional scoped delivery; existing recommendation behaviour preserved.
- `src/app/api/b9/[...path]/route.ts`, `src/app/student.css`: member forwarding and responsive styles.
- `tests/explore-browser.cjs`: isolated mock-backend production-browser journey.

## Verification and repeatable commands

API working directory: `development/apps/flame-api`.

```powershell
$env:FLAME_RUN_DB_TESTS='1'
.venv/Scripts/python.exe -m pytest tests/test_explore.py tests/test_b11_modularity.py tests/test_mvp_recommendations.py tests/test_recommendation_metadata.py tests/test_b9_catalogues.py -q
```

Web working directory: `development/apps/web`.

```powershell
npm run typecheck
npm run test:unit
npm run build
node tests/explore-browser.cjs
node tests/conversation-images-browser.cjs
node tests/sidebar-conversations-browser.cjs
```

Recorded: 26 affected backend tests passed with database checks enabled; final focused Explore reruns cover the latest contract/suitability/focus changes. Typecheck, 17 web units and production build passed. Explore browser checks cover lazy loading, independent context, search beyond the first page, race suppression, static thumbnails, viewer return, all three catalogues, unknown availability, stale-path refresh, Curiosity browsing, desktop reflow, narrow modal/focus/Escape and no recommendation acknowledgements. Existing conversation media and sidebar suites passed. Provider SDKs in the media suite are fixtures, not a live YouTube/Vimeo availability certification.

The 130-resource rollback-only fixture returns 24 items per page and exactly two SELECTs for Topic-only media browsing. Five local TestClient samples: median 127.74ms; maximum 317.66ms (includes first-request overhead). See `work/b14-explore-performance.json`; these are small local fixture measurements, not production load guarantees. Subtopic precision adds a mapping query; kit publication/storage validation retains the existing cost.

## Remaining limits and runtime handoff

- Server browsing evaluates the selected topic's eligible candidates for exact totals before pagination; it does not load all curricula's catalogue records. Very large single-topic catalogues and remote storage HEAD checks need production measurement/optimization under B10. Current fixture assets use local storage/approved test URLs.
- Physical devices, screen readers, live approved assets/private Supabase Storage and educator/release acceptance remain the existing F8/B8/B9.11/B10 gates.
- No schema migration, paid LLM request, real-catalogue data mutation or deployment was performed. Database fixture changes rolled back.
- Automatic approval review blocked stopping the current local API process, with reason reported as blocked by policy. The process was left running; restart it manually to load the new routes. In the backend terminal, stop the old process with Ctrl+C, then use the existing command below. The frontend must use the new build or its normal development refresh.

```powershell
cd E:\FLAME\development\apps\flame-api
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-access-log
```

After restart, open the learner workspace `/` and use Explore. The feature is not an admin navigation panel.

## Owner refinement: follow learning navigation — 2026-10-08

The earlier manual restart note is superseded by the live recovery recorded in STAGES-STEPS.md: the frontend currently uses the updated API at 127.0.0.1:8001.

Explore previously synchronized the Study path only on opening. It now synchronizes an already-open panel when the active learning path or revision changes, across Media, Teachers and Activity Kits. Independent filter changes do not alter Study and remain until actual Study navigation. Saved-answer entry sets its navigation baseline before fetching, preventing the synchronization effect from cancelling a deliberately opened answer. Navigation clears old results, searches, pagination, scroll and viewer state, invalidates pending requests, and preserves the selected catalogue and media category. The path-filter button shares the search row for all three catalogues.

Verification: production build/TypeScript and expanded Explore browser suite passed. Regression coverage includes all three tabs following topic/subtopic navigation without the Explore trigger, distinct-topic result changes, independent filtering, saved-answer links, stale asynchronous response suppression and existing desktop/mobile interactions. Live signed-in Light subtopic changes matched the Explore selection without reopening. Screenshot: work/explore-follows-learning-path.png. No backend API, catalogue data, mapping, publication or tracker count changes.

## Owner refinement: Curiosity question exploration — 2026-10-08

Previously open Curiosity answers deliberately had no Study context and Explore returned null. The existing owned-answer context endpoint now matches the saved Curiosity question to current published topic/subtopic names, reusing teaching's phrase normalization. Curriculum returns the eligible names and IDs with one joined read query; no teaching N+1 path loading, extra provider request, schema change, or conversation context mutation is needed. Explicit curriculum/grade names narrow the scope before resolving specific subtopics. Topic-only matches collapse children into one topic-wide path.

One matching path automatically feeds the existing Media/Teachers/Kits browser. Multiple matches return labelled paths for a student choice, rather than guessing grade or curriculum. Unmatched questions clear previous cards. Matching is conservative phrase matching against published names, not general semantic classification: a question with no matching topic/subtopic name can still receive its LLM explanation without library results. Existing owner publication, availability, suitability, mapping and playback checks remain authoritative when listing/opening.

The shared frontend follows the latest Curiosity turn and re-evaluates after its confirmed answer. A pending/new question clears previous results, search/page/scroll and open viewers; request generations and abort guards discard obsolete matching responses. The selected catalogue/media category stays unchanged. Saved Curiosity histories and answer-specific Explore links work; opening an earlier answer remains intentional until a newer question arrives. Ambiguous-path choices do not change academic Study selection or progress. Initial empty Curiosity retains manual path selection.

Verification: nine backend checks passed, including rollback-only real database published-topic queries, consecutive saved Curiosity questions, unmatched results, foreign-answer rejection, and existing eligibility checks. Production build/TypeScript and Explore browser coverage verify Study following, restored Curiosity, Gravity/Light question changes, Media/Teachers/Kits refresh, no-match clearing, ambiguous selection, independent filtering, saved-answer entry, stale async responses and existing desktop/mobile interactions. Browser provider/answer results are isolated fixtures; no paid LLM request or production data mutation occurred. Live existing Curiosity history also returned an honest no-match state for an unmatched sky question. Evidence: work/explore-curiosity-gravity.png and work/explore-curiosity.png.


### Curiosity combined results across matching paths — 2026-10-08

Owner refinement supersedes the earlier ambiguous-path choice behaviour: Curiosity now directly displays combined eligible media, teachers and kits across all matching published topics/subtopics. No matching-path list or confirmation is rendered. The authenticated /api/v1/explore/curiosity endpoint reads the owned saved question, re-resolves current published paths, applies existing owner eligibility/suitability, deduplicates by kind/ID before global filtering/sorting/pagination, and returns each item's authorized browse_path for scoped open/thumbnail/delivery. Study remains scoped as before; later questions still clear and refresh results with stale-response protection. No schema, mappings, publication or LLM changes. Twelve backend checks with rollback database coverage and production build/TypeScript passed; browser regression coverage verifies multi-path results across all catalogues, combined search, scoped item opening, and existing Study/Curiosity behaviour. Counts/statuses unchanged.


### Preserve Explore results across close/reopen — 2026-10-09

Removed unconditional cache clearing and refresh-attempt increments on every drawer opening. A component/member-scoped last successful page now survives close/reopen when its exact path/revision, catalogue, search, pagination and recovery generation are unchanged; it bypasses the short cross-query cache expiry without clearing the DOM or showing a loading flash. Results, filters, pagination and remembered scroll remain. Context/filter/revision changes and catalogue updates still invalidate or select new results; reopening after an error refreshes paths/data. Resource/teacher/kit opening and media delivery continue to recheck current eligibility/version, so a retained listing cannot grant access to withdrawn/stale items. Study and Curiosity use the same presentation persistence; no backend/schema changes.

Production build/TypeScript and expanded Explore browser suite passed. New assertions verify no additional listing requests or loading indicator on reopening after advancing time past the old cache lifetime, retained page/scroll, same-question Curiosity reopening, and a stale curriculum failing on item open then recovering through latest paths. Existing topic changes, combined browsing, viewers, close animation, focus, reduced motion and mobile flow still pass. Tracker counts/statuses unchanged.


### Media browser topic fetch and candidate metadata correction — 2026-10-09

Owner requested verification of topic-specific media fetch. Read-only execution of the real Explore catalogue initially failed with CatalogueCandidate extra_forbidden for topic_labels, including default empty labels on old resources. Root cause: the new admin grouping field was forwarded with all learning_metadata into a strict teaching-candidate contract. This also affected kit/tutor candidates. Added candidate_metadata to exclude admin-only topic_labels while retaining validated teaching metadata; all three owner adapters now use it. Admin labels/filter/import/export remain intact; strict candidate validation, publication/access/suitability and mapping checks are unchanged.

Live read-only verification using current development database/settings returned FlipLecture / Grade 1 / Science / Gravity (Forces & Motion) / Gravity, published revision 22: 12 eligible media (10 videos, 1 image, 1 Interactive), all 12 mapped/published and no drafts. Each of eight current subtopics returned all 10 mapped videos. These are real catalogue-service results, not a signed-in user-browser request; browser inspection was unavailable. Active API 8001 readiness returned 200 after code reload. No real resource/mapping/publication change was made.

Regression: 24 Explore/recommendation-metadata backend tests passed, including rollback-only routed catalogue checks with admin labels on 130 fixture resources, strict three-kind candidate projection, mapping/suitability/version/access/metadata behaviours. Updated the metadata test to include the new optional empty topic_labels field. Explore browser suite passed Study/Curiosity topic changes, combined candidates, scoped open/delivery, stale response suppression and desktop/mobile/focus. Sources: learning_metadata.py; resources/teachers/activity_kits candidates.py; test_explore.py and test_recommendation_metadata.py. Tracker totals/statuses unchanged.
