# API contracts and frontend integration — Stage 1

Canonical API specification. Track implementation and review status in [STAGES-STEPS.md](../../STAGES-STEPS.md), not a separate completion report.

Status: B1 foundation contract review completed on 2026-09-25 under the owner’s instruction to complete B1.8–B1.10; only health endpoints are implemented. Later-stage schema decisions remain explicitly gated below. Base path for future domain routes: /api/v1. IDs are UUID strings; dates are UTC ISO-8601; monetary amounts are decimal strings plus currency codes.

## Transport and access

Browser → same-origin Next.js BFF → FastAPI. BFF manages identity-provider tokens in server-side session storage and uses protected browser cookies. Mutating BFF requests require origin/CSRF protection appropriate to the selected session implementation. FastAPI independently verifies token issuer/audience/expiry and subject before loading role/ownership in Stage 3. A client student_id or role field is never authority.

No authentication bypass or fake admin exists in the Stage 1 app. Domain endpoints are not mounted until implemented and authorized. Do not expose credentialed cross-origin access by default.

Lists return {items: [], next_cursor: null}; limit defaults to 25 and is bounded to 100. Opaque cursors encode stable ordering. Mutations return saved IDs and versions. Updates include expected_version; stale versions return 409. Import commit and ask require Idempotency-Key. A repeated key with the same principal, operation and body returns its original result; reuse with a different payload returns 409. In-progress responses return 409 with a retryable code rather than duplicating work.

Error envelope: {status: error, request_id, error: {code, message, retryable}}. Use 401 for missing/invalid authentication, 403 for denied role, 404 for absent or inaccessible owned objects, 409 for conflicts, 422 for invalid data, 429 for quota, and 503 for unavailable dependencies. Unsupported accepted requests return status=unsupported with a stable code and explanation; no_results is an ordinary empty catalogue result, not a provider failure.

Stage 1 health errors use this envelope. Future validation responses can add sanitized field locations, never raw submitted values or credentials.

### New-member onboarding contract gate

Before B3.1 implementation, choose self-registration or invitation/provisioning and document BFF routes, required fields, verification/activation, duplicate-account handling and failure/retry states. Specify initial profile creation and recovery from partially completed onboarding. Member onboarding cannot grant admin access; this does not add an admin-management screen.

### Request recovery contract

B5.4 defines pending/completed/failed transitions and recovery ownership after crashes or provider timeouts. Specify when a retry resumes the same logical request, replays a terminal failure or requires a new key; define key/result retention and behavior after expiry. Require atomic claims and stale-pending recovery so concurrent workers cannot finalize duplicate turns. Decide whether distinct simultaneous questions in one session are serialized or rejected, with explicit conflict/retry payloads. Provider execution may be uncertain after timeout: bound repeat calls and preserve one committed logical turn/result without promising exactly-once provider billing. Test these cases alongside same-key/different-payload rules.

## Endpoint inventory

All rows except health are planned, not live routes.

| Module / access | Method and path | Request / result |
| --- | --- | --- |
| Health / public | GET /health/live | Process liveness; 200 |
| Health / public | GET /health/ready | Database SELECT 1 succeeds: 200; missing/unreachable: 503 |
| Identity / member | GET /api/v1/me | Authenticated profile, role and teaching preference |
| Lifecycle / member | DELETE /api/v1/me | Explicit confirmation; deletion receipt, status and retention notice; 202 if asynchronous |
| Curriculum / member | GET /api/v1/curricula | Published curriculum IDs/codes/names/revisions |
| Curriculum / member | GET /api/v1/curricula/{curriculum_id}/levels/{level_id}/tree | Curriculum-bound subject/domain/category/topic/subtopic hierarchy with stable IDs; uncategorized topics attach to domains |
| Curriculum / member | GET /api/v1/curricula/{curriculum_id}/levels | Published levels within the selected curriculum |
| Curriculum / admin | GET, POST /api/v1/admin/curricula | Paginated catalogue or create draft curriculum with code/name/optional description |
| Curriculum / admin | POST /api/v1/admin/curriculum/{kind} | Create child with explicit parent IDs; no client-selected record ID |
| Curriculum / admin | POST /api/v1/admin/curriculum/curriculum/{id}/publish | expected_version; validate eligible nonempty hierarchy |
| Curriculum / admin | PATCH /api/v1/admin/curriculum/{kind}/{id} | name, optional description/outcomes, expected_version; kind allowlist |
| Curriculum / admin | POST /api/v1/admin/curriculum/{kind}/{id}/archive | expected_version; archived record without cascading history deletion |
| Import / admin | POST /api/v1/admin/curriculum/imports | Multipart workbook + required curriculum_id; returns target curriculum ID and import ID and sheet/header metadata; file-size limits configured |
| Import / admin | POST /api/v1/admin/curriculum/imports/{id}/preview | sheet + column mapping; base revision, errors/counts and preview; no catalogue write |
| Import / admin | POST /api/v1/admin/curriculum/imports/{id}/commit | preview_revision + Idempotency-Key; transactional counts/revision; reject invalid/stale preview |
| Import / admin | GET /api/v1/admin/curriculum/imports[/{id}] | Paginated history or detail/row errors; retained-file link only if permitted |
| Learning / member | GET /api/v1/me/learning | Active memberships and path summaries |
| Learning / member | POST /api/v1/me/learning | Selected curriculum/level/subject path; merge/reuse membership |
| Learning / member | PATCH /api/v1/me/learning/{id} | visible boolean + expected_version; hide/restore, not delete history |
| Conversations / member | POST /api/v1/sessions | mode; Study context or Curiosity teaching preference; server-owned revision |
| Conversations / member | GET /api/v1/sessions | Paginated owned sessions/recent activity |
| Conversations / member | GET /api/v1/sessions/{id}/messages | Paginated owned turns |
| Lifecycle / member | DELETE /api/v1/sessions/{id} | Confirmed conversation deletion receipt |
| Teaching / member | POST /api/v1/sessions/{id}/ask | Idempotency-Key plus AnswerRequest below; validated blocks or unsupported/error |
| Teaching / member | POST /api/v1/sessions/{id}/capability-check | Owned, deterministic unsupported check before an open Curiosity answer |
| Resources / member | GET /api/v1/resources | topic/subtopic/type filters; published authorized catalogue items or no_results |
| Resources / member | GET /api/v1/resources/{id}/delivery | Authorized URL, expiry and supported launch mode |
| Resources / admin | GET, POST /api/v1/admin/resources | List filters or new draft fields |
| Resources / admin | GET, PATCH /api/v1/admin/resources/{id} | Detail or edits with expected_version |
| Resources / admin | POST /api/v1/admin/resources/uploads | Validated media upload; returns storage reference, never a filesystem path |
| Resources / admin | POST /api/v1/admin/resources/{id}/publish or /unpublish | expected_version; validates required fields and asset availability |
| Students / admin | GET /api/v1/admin/students | Search name/email/ID, pagination; profile/status summaries |
| Students / admin | GET /api/v1/admin/students/{id} | Basic profile and active/hidden My Learning |
| Activity / admin | GET /api/v1/admin/students/{id}/activity | Measured visits/session counts and last activity; no private messages |
| Recommendations / member | GET /api/v1/sessions/{id}/recommendations?message_id={id} | Proposed Stage 9 contract: owned answered turn; authorized resource cards and subject-filtered random teacher cards |
| Teachers / admin | GET, POST /api/v1/admin/teachers | Filters or teacher draft |
| Teachers / admin | GET, PATCH /api/v1/admin/teachers/{id} | Details/edits; expertise, availability, qualification review status |
| Teachers / admin | POST /api/v1/admin/teachers/{id}/publish or /unpublish | expected_version; validated publication state |
| Kits / admin | GET, POST /api/v1/admin/activity-kits | Filters or draft with multiple topic links |
| Kits / admin | GET, PATCH /api/v1/admin/activity-kits/{id} | Details/edits including cost/currency and topic associations |
| Kits / admin | POST /api/v1/admin/activity-kits/{id}/publish or /unpublish | expected_version; validated publication state |

Bracketed optional paths and alternatives in this table describe distinct routes to implement, not literal URL characters. Pagination/filter contracts apply to each catalogue. Publishing never grants students admin endpoint access. No student kit or teacher-contact endpoint is committed while their interaction policy remains undecided.

## Import fields

Agreed headers: Curriculum Code, Level, Subject, Domain, Category, Topic, Subtopic, Learning Outcome, Source URL. Curriculum Code, Level, Subject, Domain, Topic and Subtopic must be populated on each data row. Curriculum Code is the existing curriculum’s stable code, repeated consistently across every imported sheet/row; it is not a UUID or a display name. Category, Learning Outcome and Source URL may be blank. Learning Outcome is optional topic-level guidance: the entire column may be blank or omitted, and no per-subtopic outcome is required. When multiple rows identify the same full Topic path, their nonblank outcomes must agree; the importer stores one value on that Topic and reports conflicts. Use identical headers across level sheets; exclude reference sheets explicitly. No merged cells or blank separator rows inside the import table. The importer rejects mixed codes or a code that does not match the selected curriculum_id; it never creates or switches curricula from workbook text. Current sample workbook validation belongs to B2 and does not block B1. Description and Sort Order may be added as later enrichments; no database IDs or serial numbers are required.

Context includes required curriculum_id and domain_id and nullable category_id. Reject a category from another domain or any mismatched curriculum/level/subject ancestry. The catalogue tree returns subject.domains, domain.categories, domain.topics for uncategorized topics, category.topics and topic.subtopics. A topic appears under exactly one parent branch. Curriculum edit kind accepts curriculum, level, subject, domain, category, topic or subtopic.

Preview result includes import_id, curriculum_id, preview_revision, base_revision, status, counts {created, reused, updated, invalid, duplicates}, and bounded rows {row_number, normalized_path, operation, errors}. Paginate large error reports. Store the parsed preview on the server, never trust a client-supplied clean-row count at commit.

Changes use full parent-path matching; no automatic rename inference. Invalid rows block commit; import omission never deletes. Stable codes may be introduced after workbook review.

## Teaching request and response

POST /api/v1/sessions/{id}/ask, with Idempotency-Key header:

~~~json
{
  "question": "Why does a ball fall?",
  "mode": "study",
  "action": "explain",
  "context": {
    "curriculum_id": "88888888-8888-4888-8888-888888888888",
    "level_id": "11111111-1111-4111-8111-111111111111",
    "subject_id": "22222222-2222-4222-8222-222222222222",
    "domain_id": "66666666-6666-4666-8666-666666666666",
    "category_id": null,
    "topic_id": "33333333-3333-4333-8333-333333333333",
    "subtopic_id": "77777777-7777-4777-8777-777777777777"
  }
}
~~~

Study requires a validated published Topic context with an optional real Subtopic ID; Curiosity requires null context and does not accept a `topic_check_id`. The session stores the authoritative mode/version and teaching preference; reject conflicting client context. No client identity, history or attachments accepted by this initial answer contract. Unsupported student attachments must be clearly handled at the BFF/UI, not silently discarded.

~~~json
{
  "response_id": "44444444-4444-4444-8444-444444444444",
  "message_id": "66666666-6666-4666-8666-666666666666",
  "request_id": "55555555-5555-4555-8555-555555555555",
  "status": "ok",
  "curriculum_version": "revision-1",
  "blocks": [{"id": "b1", "kind": "text", "text": "Earth's gravity pulls the ball downward."}],
  "route": "direct_llm",
  "knowledge_source": "model_generated",
  "grounded": false,
  "confidence": null,
  "citations": [],
  "resources": []
}
~~~

The Pydantic models in teaching/schemas.py implement this initial direct-answer contract. Generated answer resource attachments remain empty. B9 retrieves catalogue recommendations separately using the persisted assistant `message_id`; replay returns the same ID. Future extensions require compatible schema updates and tests. Model output supplies only teaching blocks; the service assigns provenance/IDs.

### F11 rich response blocks — 2026-10-15

The answer's existing root fields, B11 `learning_response.schema_version=1`, split recommendation requests, ownership and idempotency rules remain in use. The block discriminator now also accepts `markdown` and `chart`. Historic `text` remains literal text; heading/list/table/callout blocks remain readable. The current frontend normalizes both live and restored blocks through the same validation/fallback adapter. Unknown or malformed blocks produce a local readable notice instead of hiding the whole answer. Older frontend builds which whitelist only the original five kinds cannot consume new answers: roll out the compatible frontend before enabling the new backend prompt; no automatic old-client downgrade is implemented.

Example persisted/returned blocks (IDs below are illustrative; actual generated block IDs are server-assigned):

```json
[
  {"id":"explanation","kind":"markdown","text":"**Distance** at constant speed: $$d=vt$$."},
  {
    "id":"chart","kind":"chart","chartType":"line",
    "title":"Distance at two metres per second","description":"An illustrative example.",
    "xKey":"seconds","xLabel":"Seconds","yLabel":"Metres","illustrative":true,
    "series":[{"key":"metres","label":"Distance"}],
    "data":[{"seconds":1,"metres":2},{"seconds":2,"metres":4}]
  }
]
```

- Markdown: 1–6000 characters, GFM tables/read-only checklists, fenced code with optional language, `$$...$$` inline mathematics and `$$` on separate lines for display mathematics. Single-dollar text is literal currency. Raw HTML/MDX is not executed; Markdown images do not load external media. Existing server authority/URL restrictions still apply to generated text, even though the renderer can safely display authorized HTTPS/root-relative links in supplied content.
- Chart: `chartType` is bar/line/pie. Required fields: id, kind, chartType, title (1–200 chars), description (1–500), xKey, series and data. xLabel/yLabel are optional strings up to 100 characters, default empty. illustrative defaults true; generation instructions require true for invented examples and permit false only for learner-supplied data. This flag is a presentation label, not verified source provenance.
- Data keys: distinct ASCII identifiers matching `[A-Za-z][A-Za-z0-9_]{0,39}`; constructor/prototype/__proto__ are forbidden. One to four unique series, each with key and label (1–100 chars), distinct from xKey. One to fifty rows, each with exactly xKey plus all series keys. Category is a nonempty string up to 100 chars or a finite number. Series values are numbers, never numeric strings/booleans, finite and within ±1e12. Pie requires one series, nonnegative values and a positive total. Extra block/series properties are rejected; model callbacks/JSX/component props are never accepted. Chart configuration is application-owned and chart data has an accessible table alternative.
- Model-only envelope: ordinary answers are Markdown prose; chart answers use `{"format":"flame-rich-1","blocks":[...]}` with markdown/chart blocks and no IDs. Optional Study `<flame-intent>` metadata follows the complete envelope and is split before parsing. Malformed/truncated/duplicate-key JSON fails as invalid_provider_output. The service assigns IDs, applies the existing 6000-character answer limit, block-count bounds, readable-content word/control/authority guards and complete atomic persistence. Formatting adds no provider request or token-limit increase.
- Prompt versions: `direct-school-2-rich1` (plus existing `-intent1` suffix in Study) and `direct-curiosity-open-2-rich1`. Saved-history projection includes Markdown and chart labels/data, retaining the existing eight-turn, per-turn and aggregate history budgets. JSON message storage requires no migration or historical backfill. Legacy typed MathML formulas remain a frontend development-content feature.

KaTeX runs with trust=false and bounded expansion/size; local CSS/fonts are bundled. Shiki highlights controlled languages into React tokens without executing source; unknown languages/load failures retain plain code. Recharts is loaded on demand and chart animations are disabled. Complete answers remain the transport unit; this extension does not introduce streaming or arbitrary model-generated interactives.

### F12 interactive mathematics and rendering decisions — 2026-10-15

`math_visual` extends the existing block union and model-only flame-rich-1 envelope. Root answer provenance, recommendation composition and atomic message/request lifecycle remain unchanged. Deploy the compatible frontend before enabling the new backend prompt: older frontend builds cannot render this kind. There is no automatic old-client downgrade or historical data rewrite.

```json
{
  "id":"server-assigned-block-id","kind":"math_visual","version":1,
  "template":"fraction_bar","title":"Three quarters",
  "description":"Change the shaded parts to explore fractions.",
  "parameters":{"numerator":3,"denominator":4}
}
```

The model omits id; the service assigns it. Required fields are kind, integer version=1, template, title (1–200 chars), description (1–500) and parameters. Root extra fields are forbidden. Parameters must exactly match the trusted template's keys; numeric cells are finite actual numbers, bounded by the registry and limited to three decimal places. Integer controls require integral values, and boolean/numeric-string substitutes are rejected. Enumerated strings accept only registered options. Fractions represent a single whole: 0 ≤ numerator ≤ denominator ≤ 12; number-line bounds contain the chosen position. Initial constructions reject coincident endpoints and degenerate triangles. Transient local degeneracy is displayed with a readable mathematical explanation rather than persisted as a new example.

Canonical definitions live in `app/modules/teaching/math_templates.json`, included as package data. The frontend `src/features/learning/math-templates.json` is a checked matching copy, enforced by parity tests. Version 1 contains seventeen templates:

| Engine (application-owned) | Allowed templates |
| --- | --- |
| React Konva | counting_groups, fraction_bar, fraction_circle, shape_explorer, number_line, ruler_measurement |
| JSXGraph | point_geometry, segment_geometry, triangle_angles, circle_geometry, parallel_lines, perpendicular_lines, perpendicular_bisector |
| Mafs | coordinate_points, linear_function, quadratic_function, trigonometric_function |

`trigonometric_function` uses only the trusted `sin`/`cos` enum and bounded numeric `a`, `k`, `h`, `d`, `x` parameters from the registry: `y=a*sin(k*(x-h))+d` or the cosine equivalent, with angles in radians. No expression string is accepted or evaluated. Selection recognizes sine/cosine before generic linear equations. Equations in explanatory Markdown remain KaTeX notation, separate from this interactive Mafs graph.

The registry owns engine selection and parameter bounds. No model-supplied engine, library props, event handlers, JavaScript/JSX/HTML, JessieCode, general expression strings or remote assets are accepted. Linear/quadratic families use trusted numerical functions with bounded domains and sampling. Measurements are mathematical units, not physically calibrated screen centimetres. Recharts continues to handle data comparisons; KaTeX handles formula typography; approved catalogue interactives retain their separate sandbox and authorization rules.

**Selection policy:** `teaching/math_visuals.py` derives a server-owned decision from the current question, known teaching level and, only for narrow follow-up wording, a previously saved math activity. Priority: explicit text-only request → data comparison/chart → specific mathematical goal (construction, function/coordinates, fraction, number line, measurement, counting or shape) → semantic auto selection in the existing model call. Construction/relationship questions select geometry; identifying basic shapes selects primary math. Known KG–5 levels restrict the template allowlist using registry minLevel; unknown/open Curiosity remains under-15 and can use semantic selection, including non-English questions, without assuming a grade. Explicit unsupported-depth requests use an age-suitable text explanation. Lexical hints are conservative and are not a full multilingual classifier.

The same prompt includes only allowed template defaults/bounds. High-confidence math routing narrows to one preferred template. After parsing and validation, the backend filters visuals incompatible with the decision or teaching level and caps accepted math_visual blocks at one per answer. Text-only suppresses charts and math activities; data-chart routing suppresses math activities; explicit math routing suppresses data charts. Compatible explanatory Markdown remains. If filtering leaves no content, a short readable Markdown fallback is returned. The service does not fabricate missing activity parameters or make another model call; a suitable prose answer may have no activity.

Successful ask results add optional server-owned `rendering_decision` metadata: mode (auto/text/chart/math), preferred_template (nullable), reason, and selected_templates/selected_engines derived from the final validated blocks. Empty selection arrays indicate that no math activity was retained. It is retained in the idempotent request result, not displayed as implementation detail or treated as source provenance. The saved message stores its canonical blocks/initial parameters. Replay returns the same answer/IDs/decision without another model request. Prompt versions are `direct-school-3-math1` (with existing Study -intent1 suffix) and `direct-curiosity-open-3-math1`; quota, 6000-character answer bound, token cap and recommendation-intent separation remain.

**Local interaction/history:** numeric/select controls provide keyboard equivalents, descriptions expose current values, Reset restores the saved initial parameters and expand/restore adjusts the drawing area in place. Libraries load lazily on the client; board/resize subscriptions clean up on unmount. A failed engine load preserves controls and readable state. Changes to controls/dragging are local and are not sent to the model, graded, used as mastery, or persisted. Reload and bounded follow-up history use the original saved specification, explicitly described as the saved initial activity. Persisting adjusted state or sending it in follow-up context requires a separate validated contract. Existing JSON message storage needs no migration or backfill. History assembly trims older pairs to the remaining UTF-8/message allowance after template instructions and the current question, while preserving the existing total prompt budget.

## Current Study boundary, open Curiosity and recommendations

Study questions require a validated published seven-ID path and pinned revision. Curiosity questions require null context and can cover general learning across subjects and languages; the ask route does not invoke B6 topic-check or attach a curriculum version or resolved subject/topic IDs. Under-15 response guidance and the explicit unsupported-capability check still apply. The B6 topic-check/clarification endpoints and records remain owned historical interfaces, but the current frontend does not use them to ask Curiosity questions.

The B9 member recommendation endpoint derives a subject only from a validated owned answered Study turn. Open Curiosity has no subject mapping, so it must not infer a teacher expertise match from the question text or reuse an earlier Study subject. Return no subject-matched teacher card for open Curiosity. The endpoint returns `status: ok` or `no_results` with `resources` and `teachers` arrays; a saved selection is stable on retry and withdrawn entries are filtered again.

## Frontend adapter mapping

| Existing frontend | Backend contract / adapter responsibility |
| --- | --- |
| getCurriculum/getLearningLibrary local providers | Replace through authenticated BFF calls; do not connect browser to DB |
| Curriculum/Subject/Chapter/Topic | Render Curriculum → Level → Subject → Domain → Topic → Subtopic; Category is a hidden context ancestor, never a student-visible row or breadcrumb |
| curriculumId and levelId | Distinct backend curriculum_id and level_id; gradeId alias removed; no invented board metadata |
| topicGroupId | Retire legacy alias; integrated topicId means backend topic_id |
| Domain/Category (not present) | Add domainId and nullable categoryId to frontend context; flatten Category visually while preserving its ID and validated ancestry for teaching |
| legacy topicId and conceptId | Replace with explicit topicId and required subtopicId; select real Subtopics only |
| message | question |
| history from browser | Ignore as authority; backend loads owned persisted messages |
| available + blocks | Map backend ok to available |
| unavailable + reason | Map unsupported/error to unavailable while retaining request ID/retry semantics |
| frontend progress/proficiency | null; do not derive from visits or questions |
| Curiosity context=null | No client-selected Study path or topic-check; answer general learning questions under under-15 teaching rules, with null curriculum/topic IDs |
| Interactive HTML5 | Existing packaged gravity-lab demo plus protected admin-uploaded self-contained HTML5; JSON delivery and isolated catalogue viewer described in the October 9 Interactive handoff |

The completed frontend is preserved in Stage 1. It still uses local providers until authenticated BFF integration occurs. This mapping is a proposal, not a claim of completed frontend integration.

## Planned media-only response extension

B9 defines a separate validated resource result instead of forcing it into DirectAnswer. Use status ok/no_results, route=resource_lookup, knowledge_source=resource_catalog, empty answer blocks/citations, grounded=false and null confidence/model usage; return authorized catalogue resource metadata. Resource approval does not ground generated answers. Explicit resource lookup uses the resource endpoints, not inference from a resource ID in an explain request. The exact published Topic/Subtopic lookup is implemented; delivery is a separate authorization and five-minute URL request.

## Lifecycle and publication

Hide My Learning retains messages. Delete session/account invokes an explicit member-confirmed workflow and agreed retention; shared curriculum/assets survive account deletion. Revoked publication removes catalogue visibility; signed URLs may remain usable until their agreed short expiry, unless delivery is reauthorized per request. The approved window is five minutes; local delivery rechecks publication even for an issued URL. B4 archive/revision policy is recorded below for browse and future B5/B6 resume, ask and recommendation outcomes: archived-ancestor eligibility, machine-readable unavailable-context responses and the revision governing each operation. Historical context never bypasses current resource/teacher authorization.

## Acceptance examples for future stages

- Same workbook committed twice with the same key yields one import result.
- Same key with a different request body yields conflict.
- Member calls admin kits endpoint: forbidden.
- Kit linked to two topics appears once per filtered listing with one stable kit ID.
- Published teacher's declared expertise is not represented as verified.
- Science questions never recommend unrelated-subject teachers; empty eligible pool yields no teacher card.
- Curiosity topic changes remain open questions; no answer turn inherits a subject ID from another turn.
- Recommendation retries preserve selection while withdrawn/private records remain inaccessible.
- Curiosity explanations and unsupported-capability responses remain under-15 appropriate.
- Resource opened repeatedly through a retried request does not create duplicate activity.
- A request to explain a video is unsupported; resource playback is a normal database lookup.
- No domain route is represented as implemented in Stage 1 OpenAPI.

## B1 review details — 2026-09-25

These are the reviewed B1 contract baseline, not implemented domain routes. The owner authorized completion of the remaining foundation review and handoff; later-stage decision gates remain in force.

### Workbook mapping

Historical candidate only: the six previously inspected sheets were mapped to KG and Levels 1–5, with Science confirmed for that candidate. The owner subsequently instructed us not to use either existing workbook and will supply a final workbook. Its sheet selection, row semantics and normalization must be inspected under B2.1; no decision about repeated KG rows or an auxiliary table in the abandoned candidate is required. Preserve source sheet/row provenance for whichever final sheets are selected, and never deduplicate across levels based only on names.

### Exact frontend target

Integrated Study context uses curriculumId, levelId, subjectId, domainId, categoryId (nullable and hidden), topicId and required subtopicId, mapped one-to-one to snake_case API context. This target supersedes ambiguous legacy aliases in the mapping table above. Remove gradeId/topicGroupId/conceptId aliases from the integrated boundary; do not assign two meanings to topicId or invent board metadata.

Backend tree shape: curriculum.levels → level.subjects → subject.domains; domain.categories and domain.topics (uncategorized); category.topics; topic.subtopics. Student navigation flattens both topic branches beneath Domain and never renders Category text. Each published Topic has at least one real Subtopic; Study may select the Topic or one of its Subtopics. Category ID stays in context for ancestry validation and precise answer routing. Empty draft child arrays are valid but not publishable as a Topic leaf. Search, merge, drafts and restored selection compare all seven IDs/nulls, never labels alone. Catalogue revision is server-owned and separate from path identity. Proficiency remains null; unsupported status filters must be removed or represent unavailable status rather than manufacture learning progress.

F3 adapter acceptance cases: categorized/uncategorized topics with real subtopics; repeated names under distinct hidden categories; no Category label in student UI; full-path restoration; mismatched ancestry rejection. The local frontend adapter and unit tests now cover hidden Category identity and required Subtopics (2026-09-26). Authenticated BFF catalogue integration remains F3.4/B4.

### Concrete request/result examples

The UUIDs below are illustrative. Entity version is an integer edit counter; catalogue revision is a separate opaque value.

Member addition: POST /api/v1/me/learning

~~~json
{"curriculum_id":"88888888-8888-4888-8888-888888888888","level_id":"11111111-1111-4111-8111-111111111111","subject_id":"22222222-2222-4222-8222-222222222222"}
~~~

Validate curriculum/level/subject ancestry and reuse an existing owned membership. Result:

~~~json
{"id":"77777777-7777-4777-8777-777777777777","version":1,"visible":true,"curriculum_id":"88888888-8888-4888-8888-888888888888","level_id":"11111111-1111-4111-8111-111111111111","subject_id":"22222222-2222-4222-8222-222222222222"}
~~~

Admin rename: PATCH /api/v1/admin/curriculum/topic/{id}

~~~json
{"name":"Gravity","expected_version":1}
~~~

Result preserves the UUID, advancing entity version and catalogue revision:

~~~json
{"id":"33333333-3333-4333-8333-333333333333","name":"Gravity","version":2,"revision":"revision-2"}
~~~

Stale edit: HTTP 409. Reload and reconcile; never blindly repeat a stale mutation.

~~~json
{"status":"error","request_id":"55555555-5555-4555-8555-555555555555","error":{"code":"version_conflict","message":"This item changed. Reload before saving.","retryable":false}}
~~~

Idempotency codes: idempotency_key_conflict for different payload (409, retryable=false); request_in_progress for a pending identical operation (409, retryable=true). Retry with original key/body and bounded backoff. A retryable flag does not authorize new keys to bypass pending work. Terminal-failure replay and expired-lease recovery are implemented in the internal B5 claim service; keys remain for the session lifetime. The protected ask transport is mounted; same-key completed results replay and terminal failures require a new key for another attempt.

Explicit resource action: GET /api/v1/resources?topic_id={uuid}&type=image. No ask/LLM call. Empty result:

~~~json
{"status":"no_results","request_id":"55555555-5555-4555-8555-555555555555","items":[],"next_cursor":null}
~~~

Resource lists use items per pagination conventions; recommendations use resources and teachers. Provider failure must not become no_results. Final resource metadata/expiry schemas belong to B9.

Unsupported attachments/transcription remain rejected at BFF/UI with an explanation and retained draft; do not silently send reduced text-only requests. The B8 `POST /sessions/{id}/capability-check` route checks an owned session and returns `continue` or a named unsupported capability without calling a model. The ask route persists and replays `status=unsupported`, `request_id`, a stable code and a safe explanation for explicit textbook-evidence, official-grading, student-file/media-understanding or progress-update requests. Curiosity checks capability before a direct open answer; supported questions need no topic-check ID. Unsupported outcomes contain no generated blocks or citations. Extra unsupported request fields still receive HTTP 422. Current successful DirectAnswer schema/provenance remains unchanged.

### Dynamic curriculum contracts — mandatory root

All full paths begin with curriculum_id. GET /api/v1/curricula returns {items, next_cursor}; each item includes id, code, name, revision. Creation at POST /api/v1/admin/curricula accepts {code, name, description?}, returning {id, code, name, state: draft, version: 1, revision}. Code is a stable unique catalogue identifier; do not derive it from Level or silently create a curriculum from workbook text. Admin selects or creates the target before upload. Empty curricula are manageable by admins but not selectable for member teaching until published with eligible content.

Generic child creation kind is level/subject/domain/category/topic/subtopic (curriculum uses the dedicated create route). Parent inputs: level requires curriculum_id; subject requires level_id; domain requires subject_id; category requires domain_id; topic requires domain_id and nullable category_id; subtopic requires topic_id. All require name; server assigns UUIDs and verifies ancestry/access. Curriculum rename/description edits and archive use the existing generic kind routes with kind=curriculum; code and parent moves are not editable through rename. Publication/creation is protected by the same admin checks as imports.

Excel columns are Curriculum Code, Level, Subject, Domain, Category, Topic, Subtopic, Learning Outcome (optional), Source URL. curriculum_id remains mandatory upload metadata; the repeated Curriculum Code is a human-readable assertion of that selected target, validated against its stable normalized code. One import targets one existing curriculum. Preview/result contains curriculum_id and base_revision; commit loads the stored target and never trusts a replacement target from the client. Catalogue revisions and invalidation are per curriculum. To import equivalent paths into a different curriculum, use its own code in the workbook; a repeated file within the same curriculum reuses matching full paths.

The selected curriculum is a required Study ancestor, not identity authority. Verify the level belongs to it. Persist full paths/revisions in learning and sessions. Curiosity keeps request context=null and has no curriculum or topic resolution. Unknown/inaccessible curricula follow 404 semantics; authorized mismatched ancestry is 422. B2/B4 tests must prove isolation beyond these typed UUID contracts.

B1 acceptance uses synthetic paths across two independent curricula with repeated names; sample workbook cleanup, repeated KG rows and import limits belong to B2. Adding future curricula must require data entry/import only, not code/schema changes.

### B1 final review resolutions

- `preview_revision` is an opaque server-generated identifier for one immutable parsed preview, distinct from `base_revision` (the target curriculum revision used for comparison). It binds import ID, owner, curriculum ID, file hash, selected sheets/mapping and normalized rows. Re-preview produces a new identifier and invalidates the previous preview. Commit submits only this identifier plus Idempotency-Key; the server loads the stored preview, rejects invalid/stale/foreign previews and atomically compares base_revision before writing. Same-key completed commits replay their saved result before stale-preview evaluation.
- All routes containing `{kind}` enforce exact allowlists; literal import routes cannot be interpreted as a node kind. New child creation returns the saved id, parent references, version and resulting curriculum revision. Curriculum creation emits its initial revision even when empty. A node edit advances its curriculum revision; unrelated curricula are unaffected.
- Each curriculum tree response carries curriculum_id, level_id and revision. Existing node arrays preserve all ancestors. Entity version is used for edits, revision for catalogue consistency, and preview_revision for a frozen import preview; these tokens are never interchangeable.
- B1 reviews the seven-field frontend mapping and member/admin boundary without implementing F3/F9. The 2026-09-26 product rule supersedes its optional-Subtopic case: Category remains optional/hidden, and the 2026-09-28 owner update allows Study at Topic or Subtopic; same-named paths under different curricula remain distinct. No alias may substitute level_id for curriculum_id.
- Later detailed onboarding, crash recovery, clarification and resource schemas are finalized before B3, B5, B6 and B9 respectively, as assigned in the tracker. B1 closure does not represent these services as implemented or erase their gates.

### B4 implemented catalogue and membership boundary — 2026-09-26

The published-path search route is GET /api/v1/curricula/search?q=... and returns the seven stable IDs, visible names, and catalogue revision for each matching Subtopic. The student tree keeps Category hidden from display while retaining category_id in Topic paths. My Learning POST accepts optional domain_id, category_id, topic_id and subtopic_id in addition to curriculum_id, level_id and subject_id, and validates exact ancestry server-side. A selected Topic or Subtopic remains an exact saved path through refresh/sign-in. Hide/restore remains restricted to curriculum and subject scope. B4 admin revision history is GET /api/v1/admin/curricula/{id}/revisions. Archived catalogue branches are unavailable for new selection; owned historical membership rows are retained.


## B5 request recovery and lifecycle implementation contract — 2026-09-26

B5 stores a Study session's seven authoritative path IDs, display-name snapshot and server curriculum revision at creation. Curiosity has no Study context. Transcript reads remain owned and available after My Learning hide or curriculum rename/archive. A new Study question revalidates the current published path and exact revision; mismatch returns 409 unavailable_context. B5 exposes owned session listing, detail, paginated messages, bounded complete-pair history for later prompt construction, measured activity and confirmed deletion.

The internal request claim service reserves one pending question per session by locking the session row. Same key and canonical body replays completed or terminal-failed results; different body conflicts. A distinct simultaneous key conflicts with session_request_in_progress. A pending same-key retry receives request_in_progress during its 90-second lease. After lease expiry, the original key can claim once more; a new fencing token prevents an old worker from committing. After two claims without a result, the request becomes terminal retry_exhausted. A provider timeout may have incurred an external call; this contract guarantees one committed turn, not exactly-once provider billing. Keys and results remain until the owned session is deleted; no time-based key expiry is currently applied. B7 calls this service around provider work and validates a complete text answer before atomic finalization. The public ask route is mounted, with live provider configuration pending.

Activity types are visit, session_started, question and resource_open. Each event has a member-scoped deduplication key. Session creation and a completed question write their events server-side; the live web workspace writes one visit event per opening. Future authorized resource delivery records resource_open through the server-side activity model; the current member activity route accepts visits only. Admin sees counts and last activity time, not question or response text. These counts are measured usage, not mastery or completion.

Confirmed conversation deletion immediately removes messages, answer requests, session events and the session from the primary FLAME database. Confirmed account deletion removes FLAME-owned private rows and My Learning paths, strips local display name/email and removes FLAME browser session tokens, then hard-deletes the owned Supabase Auth identity through a server-only Supabase secret key or legacy service-role key. The local profile becomes inactive before the provider call. A provider timeout leaves a pending_provider receipt and an inaccessible local tombstone; scripts/retry_deletions.py retries the exact provider ID, treating a provider 404 as success. A completed receipt marks the tombstone deleted; a maintenance command purges completed receipts and auth-subject tombstones after 30 days. Pending provider deletions are never purged by that command. Shared curricula and assets remain. A disposable development Supabase Auth user was removed through the FLAME route on 2026-09-26, then an admin lookup returned 404. Provider timeout and retry are mock-tested. The owner selected a 30-day maximum for backup and operational-log copies on 2026-09-26. Primary FLAME private data is removed immediately after confirmation; the 30-day period applies to residual copies, not a waiting period before deletion. The period may be changed later by updating this policy and the backup/log systems together. PITR is not required for MVP. Managed Supabase backup and log retention must still be checked against the active plan and any exported copies before release; this application cannot force those systems to expire a copy. Local drafts and pins are browser memory only. Session history and stubbed new answers are available through the BFF; live provider calls await configuration.











B9 development contract (2026-09-28): `GET /api/v1/resources` requires an exact published `topic_id`, optional `subtopic_id`, `type` and `curriculum_revision`; it returns paginated `items` with `status: ok|no_results` and resource provenance, with no storage key. `GET /api/v1/resources/{id}/delivery` returns `{status,url,expires_at,launch_mode}` after current publication/asset checks. `POST /api/v1/resources/{id}/activity` accepts `event_type: open|play`, a member-scoped deduplication key and optional owned session ID. `GET /api/v1/sessions/{id}/recommendations?message_id=...` returns retry-stable, currently eligible `resources` and `teachers`; only Study answers with resolved subject/topic qualify. Admin catalogues use `expected_version` on changes and publication. Deployed private Supabase Storage remains a B9.11 live gate.

## B11 additive learning-response envelope (2026-10-07)

The existing ask/recommendation/open/acknowledgement URLs and root response fields remain compatible. The optional `learning_response` object has schema_version=1, message_id, request_id, nullable answer and recommendations. Answer status is completed/unsupported/unavailable and carries validated blocks. Recommendation status is completed/none/pending/unavailable, with nullable data and safe code. A Study ask returns pending without running selection; Curiosity returns none. A recommendation GET returns its legacy payload at root and in recommendations.data, with answer=null. Selection failures roll back and return unavailable, preserving the saved explanation; ownership/context/version HTTP errors are not converted into successful results. Consumers validate message IDs and continue accepting legacy payloads. No recursive envelopes, extra provider request or automatic media launch. See [B11 contract and handoff](../stage-11-modular-migration.md).


## Video thumbnail extension — 2026-10-09

Admin resource create/PATCH accepts `thumbnail_upload_id`; null on PATCH removes a thumbnail. Video-only, owner-scoped validated PNG/JPEG/WebP images reuse ResourceUpload ownership. MP4/WebM publication requires a thumbnail; drafts may remain incomplete. Admin cards expose `has_thumbnail`/`thumbnail_upload_id`; member/Explore cards expose `has_thumbnail` and safe provider `thumbnail_url`. Scoped member delivery accepts `thumbnail=true` and retains eligibility/version/revision checks; private thumbnails use five-minute signing. Native-video delivery includes `poster_url`. Protected admin preview/preview-content accept `thumbnail=true`. See [thumbnail handoff](../stage-9-video-thumbnails.md) for signing, withdrawal, provider fallback and bulk-import limitations.


## F13 transient simulations and independent text stream — 2026-10-15

The stored answer block union is unchanged. Generated simulations are transient, message-bound response adjuncts rendered beside LearningContent inside `.flame-message`; executable source is never accepted as ordinary Markdown/F12 data or persisted in history/request receipts.

- `POST /api/v1/sessions/{session_id}/ask-stream`: existing AnswerRequest body, member/session ownership, Origin/CSRF through the BFF and Idempotency-Key. Returns no-store `application/x-ndjson` events: `{type:"delta",text:"..."}`, optional heartbeat, then `{type:"answer",answer:<existing final answer envelope>}` or `{type:"failure",code:"..."}`. Final validation/persistence/replay remain authoritative. Existing `/ask` JSON remains available. Structured rich JSON is buffered for final rendering; Markdown previews are provisional.
- `POST /api/v1/sessions/{session_id}/simulation`: strict body `{message_id:<assistant UUID>,start:false|true}`. The server owns engine selection from the saved user question and verifies both session/message ownership. Returns status `ineligible`, `expired`, `limited`, `pending`, `error`, or `ready`. Ready includes `{version:1,engine:"matter|three|r3f|phaser|rive|html5",title,description,source}`; title<=160, description<=500 and source<=16000 characters. No resource IDs, external assets or arbitrary dependencies can be requested. All responses are no-store.
- A newly committed eligible answer arms one in-process generation opportunity for two minutes; replay does not arm another. `start:true` can consume it once. Completed/failed generation is deduplicated by owner/message for a 15-minute access TTL. `start:false` only retrieves an existing cache entry. Expiry or worker restart yields expired rather than another paid call. Limits are 128 process entries and at most min(20, configured question limit) starts per owner in an in-process 24-hour window.
- The response client polls `pending` with `start:false` at one-second intervals between completed requests. Only the initial fresh-answer request can use `start:true`. A 90-second overall deadline aborts hanging transport and exits loading; “Check simulation” resumes retrieval with `start:false` after timeout/network failure. It never starts another generation. Terminal statuses stop polling; ready source is reduced to the strict compiler fields. Shared tab-memory promises cover the entire polling lifecycle, not an individual `pending` response.
- Source starts execute in background threads, at most four active jobs per process, returning `pending` immediately while work continues. The configured OpenAI source job uses one 60-second transport attempt with the existing model and output-token cap, plus `reasoning.effort=low` for GPT-5/GPT-6/o3/o4 model families (omitted for other names); text requests retain their configured timing/retry policy. No HTTP poll starts another provider call. Failures expose/cache only allowlisted codes (`provider_unavailable`, `provider_rate_limited`, `provider_budget_exceeded`, `provider_output_limit`, `invalid_provider_output`, `invalid_simulation_output`) or the generic `simulation_generation_failed`. No source/provider error text is logged. Process restart/host termination still discards these transient jobs.
- Same-origin `POST /api/simulations/compile`: member session plus Origin/CSRF required. Strict versioned source spec; bounded request, two concurrent jobs, ten-second terminable Node compilation worker, restricted engine import registry and maximum bundle size. Returns a transient trusted-frame/worker bundle or a sanitized error code; it does not execute generated code on the server. Model code runs only in the isolated browser worker. Parent messages validate active contentWindow plus nonce; no trust is assigned to an opaque `null` origin alone.

The canonical [F13 report](../../F13-IMPLEMENTATION.md) defines supported helper APIs, actual test evidence and browser/GPU limitations. F13.11 is PARTIAL for hosted/serverless process affinity, cancellation and compiler packaging acceptance. No durable queue, schema migration, permanent simulation storage, approval workflow or new retrieval pipeline is introduced.

## Answer output-language preference — 2026-10-15

Study and Curiosity answer requests accept optional `response_language`: `en`, `ta`, `hi`, `ml`, `kn`, `te`, `mr`, `bn`, `gu`, `ur`, `or`, `pa`, `as`, `kok`, `mni`, `sa`. Unsupported values fail schema validation. The new composer defaults to `en`; omitted/null values preserve legacy prompt behavior and legacy idempotency hashes for older clients.

The selected language is a trusted prompt preference for learner-facing prose, headings and generated simulation labels, independent of input language or conflicting language requests in the question. Mathematical notation, programming syntax and structured keys remain intact. The original question and history are not rewritten. Language participates in the request hash; changing it requires a new request key, while retries keep the original snapshot. The browser stores the preference locally; transient simulation generation retains it only in bounded owner-scoped memory. This does not translate application controls or add an account preference/database migration. LLM adherence remains probabilistic.
