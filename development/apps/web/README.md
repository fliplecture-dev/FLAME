# Fliplecture frontend

The product wordmark uses locally bundled **Tilt Warp**, regular **400**. Its text matches the symbol background (**#00513F**) in light mode and the braces (**#60FF00**) in dark mode; the white admin header keeps #00513F. The brace SVG has rounded corners (18/128). See the [current brand specification, source files and verification](../../../project-stages/FLIPLECTURE-DISCOVERY-IMPLEMENTATION.md#fliplecture-logo-refresh--2026-10-17).

## Fliplecture discovery entry (F14/F15/B17/B18)

The public `/` route is now the Fliplecture homepage. Books, Kits, Teachers and Classes open `/search`; submitting a question enters FLAME Curiosity at `/flame` without requiring sign-in. Guests receive 10 questions per India calendar day; signed-in students share 25 across Curiosity and Study, resetting at midnight Asia/Kolkata. Study requests sign-in. Optional phone is available on sign-up/sign-in; `/profile` edits private contact/address details. [Access contract and approved development activation](../../../project-stages/USER-ACCESS-PROFILES.md). Existing learner browser scripts now target `/flame`; `/learn` redirects there for compatibility. Browser Back restores the active workspace and response, and catalogue response links appear only for explicitly requested categories. New Books/Classes administration is available under `/admin`; new records are private drafts until explicitly published. Independent catalogue search uses the server-only-key BFF at `/api/catalogue` and makes no model calls.

Owner-approved development Supabase activation applied `20261017_31` and `20261017_32`; schema drift is clean. Other targets need the reviewed migrations before coordinating API/web activation. No example/live inventory is seeded. Covers, expanded price/availability filters, structured class schedules and automatic Books/Classes recommendation ranking remain tracked follow-ups. [Implementation, activation, verification and domain-cutover handoff](../../../project-stages/FLIPLECTURE-DISCOVERY-IMPLEMENTATION.md).

For isolated browser verification, set `$env:FLAME_NEXT_DIST_DIR='.next-discovery'`, run `npm run build`, then `node tests/discovery-browser.cjs`. The harness owns its synthetic local API and web server on port 3128 and requires the existing Playwright/Edge/axe tools (override with FLAME_UI_TOOLS). It does not use real accounts, provider calls or database records.

The guest/profile browser suite is `node tests/user-access-browser.cjs` (port 3134, synthetic API, existing Playwright/Edge/axe tools). Member-policy tiers are deferred.

Current development progress and remaining integration/admin steps: [canonical tracker](../../../project-stages/STAGES-STEPS.md). FRONTEND-STAGES.md and FRONTEND-VALIDATION.md preserve local UI delivery evidence.

The student learning interface lives in the existing Next.js / React / TypeScript app. Run `npm ci` to restore dependencies, `npm run dev` for http://localhost:3000, and `npm run build` to validate the production build.

### Rich response rendering (F11)

Study, Curiosity and restored conversations share `LearningContent`. Explicit Markdown blocks use react-markdown/GFM/math/KaTeX; fenced programming code uses lazy Shiki tokens. Typed bar/line/pie blocks use lazy Recharts with a data-table alternative. Single `$` is literal currency; `$$...$$` is inline math and double-dollar lines delimit display math. Existing text blocks remain literal. Catalogue images/videos/interactives continue through their authorized viewers.

Run `npm run test:unit` and `npm run typecheck`. For the isolated production browser check in PowerShell:

```powershell
$env:FLAME_NEXT_DIST_DIR='.next-f11'
npm run build
node tests/rich-response-browser.cjs
```

The browser script uses the existing `.kilo/ui-check/node_modules` Playwright/axe tooling (override with FLAME_UI_TOOLS), an isolated mock API and port 3115. It does not access real accounts/provider/database rows; screenshots go under `work/f11/`. Schema/generation/history integration and the coordinated frontend-first rollout requirement are described in [API contracts](../../../project-stages/backend/stage-1/api-contracts.md#f11-rich-response-blocks--2026-10-15). Keep the KaTeX override aligned with the direct version so parsing/rendering and local fonts use the patched installation.

### Interactive mathematics (F12)

F12 mathematics adds lazy React Konva/JSXGraph/Mafs activity templates through the same live/restored block adapter. Template definitions in `src/features/learning/math-templates.json` must match the backend registry (parity-tested). Change a template's wire shape only through an explicit versioned contract. Local control/drag state is not saved or sent to the model. Mafs uses a pinned React 19 observer override plus a small default-export adapter in `src/lib/mafs-resize-observer.ts`, configured for the app's Turbopack build; recheck this bridge when changing Mafs, the observer or the bundler.

After the isolated `.next-f11` build above, run `node tests/math-visuals-browser.cjs` for F12's synthetic production-browser checks on port 3116. It covers all sixteen templates, controls, geometry/function behavior, loading fallback, history/retry and responsive accessibility. Screenshots go to `work/f12/`. The backend's opt-in `scripts/check_rich_answer.py --execute --math-template fraction_bar` (or triangle_angles/linear_function) performs one synthetic paid formatting/selection check with no student/database writes. Full field/decision rules are in [F12 API contracts](../../../project-stages/backend/stage-1/api-contracts.md#f12-interactive-mathematics-and-rendering-decisions--2026-10-15).

### Reliable local startup

`npm run dev` starts/checks FastAPI at `http://127.0.0.1:8000`, waits for database readiness, then starts Next.js at `http://localhost:3000`. It pins local API routing and local media delivery to 8000, checks the frontend/backend BFF shared key, watches only backend app sources, and stops its owned process trees together. There is no automatic fallback to 8001 or 3001. If a separate FLAME API already runs on 8000 it is checked and reused; restart that external API after changing its `.env`. Unrelated services occupying a port are not terminated.

From the project root, `./Start-FLAME.ps1` starts an independent background session that survives closing the launching terminal. Use `./Start-FLAME.ps1 status` to inspect its launcher and `./Start-FLAME.ps1 stop` to stop its owned servers. Logs are in `work/dev-session.stdout.log` and `work/dev-session.stderr.log`. Repeated starts reuse the session. Run it again after restarting your computer; no operating system service or boot task is installed. `npm run dev` remains a foreground alternative and stops on Ctrl+C/terminal closure. Backend `.venv` and both local env files must already be configured. `npm run dev:check` diagnoses matching configuration/API/database readiness; `npm run dev:web` is the explicit frontend-only option for externally managed APIs. Production `npm start` still uses the configured `FLAME_API_URL` and does not launch FastAPI.

## Student UI

On Windows, the background launcher uses `scripts/dev-api.py` for backend reloads. It replaces its owned worker directly rather than relying on a console Ctrl+C event, which is unavailable in a detached session. Source reloads briefly interrupt backend requests while the frontend remains running. This wrapper uses the installed Uvicorn supervisor; verify it when upgrading Uvicorn.

The `/flame` route contains the full-screen curriculum and learning workspace; the public `/` route opens the Fliplecture homepage. Students can expand Curriculum → Level → Subject → Domain → Topic and select a Subtopic for Study, see 0–10 proficiency when available, and enter a learning request. Category is hidden from student navigation but its ID remains in the Study context. Tablet/mobile navigation uses a native modal drawer with keyboard focus containment and Escape support. Learning content scrolls independently of the prompt input.

- `src/features/curriculum/`: curriculum hierarchy types, published-tree adapter, navigation, and replaceable local data.
- `src/features/progress/`: reusable proficiency labels and indicators.
- `src/features/learning/`: student workspace, prompt input, and typed content renderer. Activity/assessment components can be composed inside LearningContent later.
- `src/lib/api/student-learning.ts`: curriculum and message integration boundary.
- `src/app/student.css`: responsive student interface styles.

## Current data and integration boundary

`local-curriculum.ts` contains editable development content, using a small Curriculum → Level → Subject → Domain → Topic → Subtopic hierarchy from the redesign brief. The real curriculum has not been published. The current redesign uses varied illustrative progress values; they are not authenticated student records. The component tree accepts any subject hierarchy without Science-specific logic. Subject and chapter scores are supplied values, never calculated or awarded by the UI. Null represents unavailable proficiency.

Message submission currently returns an explicit unavailable result and retains the entered text. No AI replies, assessment results, or progress changes are fabricated. Conversation drafts and local request previews remain in memory for the current page; configured My Learning selections persist through the B4 API. Authentication and B4 catalogue/My Learning persistence are connected when the BFF is configured. Conversation persistence and actual teaching content remain later-stage work.

Configured environments load published curriculum and My Learning through the authenticated BFF; the local fixture remains only for unconfigured development. Keep FastAPI authoritative for student scope, learning state, chapter/subject aggregates, curriculum gates, and assessment results. The frontend's 0–10 display must not independently translate backend mastery into permission to progress.

The content renderer supports text, images/diagrams, captioned video, and resource links. It renders text without raw HTML injection. Stage 7 interactive resources resolve from an application-owned catalog and run in sandboxed frames; arbitrary response HTML is not embedded.

## Validation

Stage 8 is complete for local frontend review. See [FRONTEND-VALIDATION.md](FRONTEND-VALIDATION.md) for executed checks, repeatable commands and remaining physical-device/backend integration limits. Run npm run test:unit for pure logic checks and npm run test:ui for the integrated browser suite after setting up its temporary tools and starting the dev server.

`npm run build` compiles the app and checks TypeScript. Browser verification should cover topic selection, chapter/subject collapse, search and no-results state, direct and topic-bound requests, whitespace-only input, retained text on unavailable service, keyboard navigation, drawer Escape/close, and narrow-screen overflow. Backend availability and real mobile keyboard behavior require integration/device checks when those services and devices are available.

The staged frontend now includes Add from Library with curriculum/subject/chapter/concept addition and progress-preserving hierarchy merging. See `FRONTEND-STAGES.md` for the current scope and review checkpoints. Run `node --test tests/merge-learning-path.test.cjs` for the merge tests (Node 22.13+).


Stage 5 adds typed rich learning blocks and separate in-memory conversations for every Study context and Curiosity. The service currently returns an explicit unavailable result, so no AI answer is fabricated. In development, selecting CBSE → Grade 5 → Science → Force and Energy → Forces and Gravitation → Gravity displays a labelled static formatting preview. Conversation persistence and real response content require the future BFF/API integration.


Stage 6 completes the growing prompt with local file/image selection, preview/removal, and microphone recording/playback. Draft attachments and submitted snapshots stay in memory per learning context; no upload or transcription service is connected. Limits: 5 files, 10 MB each, 25 MB total, 2 minutes per voice note. Run `node --test tests/prompt-attachments.test.cjs` for selection validation. Browser recording tests use a synthetic microphone; real mobile keyboards and microphone hardware need device testing.


Stage 7 adds compact response recommendations and on-demand image/diagram, audio/video, simulation and resource-detail viewers. Select the Gravity Subtopic in development to review the local samples, then use Explore more for the additional categories. Samples are not AI recommendations or commercial listings. Resource metadata flows through the service boundary; real recommendations await backend integration. Run node --test tests/learning-resources.test.cjs for URL/catalog checks. See FRONTEND-STAGES.md for validation and remaining Stage 8 scope.

## B3 account screens

Member signup, sign-in, recovery, verification and admin sign-in are available at /sign-up, /sign-in, /recover, /auth/callback and /admin/sign-in. The same-origin BFF keeps an opaque HttpOnly session cookie and checks Origin plus CSRF on mutations. Configure .env.local using .env.example and the API settings in [B3 activation notes](../../../project-stages/backend/stage-3-auth.md). When no BFF secret is set in development, / continues to show the local learning fixture; configured environments require a valid member session.

## B4 live curriculum and administration

With `FLAME_BFF_SHARED_KEY` configured, the student route loads published trees and owned My Learning paths from FastAPI. Library additions persist exact paths through Subtopic; curriculum and subject hide/restore survive refresh and sign-in. Live paths show unavailable proficiency without invented scores or progress filters. The protected `/admin` Curriculum Catalogue opens on a searchable curriculum list with Archive, Restore and guarded Delete permanently actions. The selected workspace has a six-column hierarchy table (Level through Subtopic) with inline cells, keyboard save/cancel, cascading suggestions, filters, row insertion/duplication/deletion, bulk controls and a shared-node rename choice. Complete paths save to a private, revision-checked draft; incomplete branches can be filled in the table. Members continue to use the published revision until an admin explicitly publishes all saved draft changes. Excel Import is a complete-replacement workflow with metadata checks, editable review rows, additions/removals/reuse counts and typed REPLACE code confirmation. Commit creates a private replacement draft. Export Excel downloads the current draft, published catalogue or a historical revision using the round-trip workbook schema. The Students section has searchable, paginated profiles with readable learning paths and B5 measured activity. Resource Library, Teachers and Activity Kits are also available in development; live storage/asset acceptance remains B9.11.

`node tests/b4-browser.cjs` runs a disposable mock-API browser flow for BFF loading, search, add/hide/restore, error retry, admin draft creation, integrated workbook upload/map/preview/commit, cascading hierarchy navigation, inline edit, import history, explicit publish and B9 admin navigation and a 390px overflow check. It audits the import screen with axe and does not write curriculum data to the development database.

B5 adds a live saved-conversations panel for authenticated students: create a Study or Curiosity session, browse paginated owned history and confirm deletion. The profile offers confirmed account deletion, including Supabase Auth removal when the server credential is configured, and shows a pending notice if provider removal needs retry; the admin student view shows measured visit/session/question/resource-open counts. Visits are deduplicated per workspace opening. Drafts and pins remain local to the tab, and the question composer now sends text through the protected B7 ask route, while attachments and voice remain explicitly unavailable. Saved transcripts can be inspected after reload, including a hidden or renamed Study path snapshot; full in-workspace continuation remains open. The API server has the configured key and `gpt-6-luna`; live Study and open Curiosity answer/replay checks passed. Curiosity accepts general learning questions in any subject or language without a published curriculum or topic-check, while Study retains its selected path.



## B9 catalogues (development)

The protected `/admin` page has Resource Library, Teachers and Activity Kits screens with server-backed search, filters and pagination. Admins can reach it from the Admin sign in link on `/sign-in` or the Admin dashboard link in their learning workspace; normal admin sign-in redirects there. Answered Study turns fetch eligible resource and subject-matched teacher cards through `/api/b9`; a resource viewer refreshes delivery URLs and records open/play activity. Curiosity does not infer a teacher subject. `node tests/b4-browser.cjs` covers cards and admin navigation with a mock API. Live asset, signed-in browser and device acceptance remain B9.11.

Development recovery refinement: API health-check failures during reload no longer shut down the frontend. Unexpected owned backend/frontend process exits retry automatically, at most three times per minute. Persistent errors remain visible and retries pause instead of spinning. Ctrl+C still stops the whole owned tree. Closing the terminal or shutting down Windows stops local development; automatic recovery needs the launcher to stay running.



## F13 generated simulations

Eligible interactive questions now render a temporary simulation directly in the response box: Matter.js 2D physics, Three.js/R3F 3D science, restricted Phaser Matter activities, the existing FLAME-authored Rive Weather World asset, and HTML5 Canvas/SVG paths. Source compiles against fixed local dependencies and executes only in a terminable worker inside an opaque-origin iframe. Text streaming and its saved final explanation are independent of compilation. Rive runtime cannot generate new artwork; normal code fences remain display-only.

Try “Interactive falling ball with adjustable gravity using Matter.js” or “Rotatable 3D solar system using React Three Fiber.” One additional bounded configured-provider generation can occur for a fresh eligible answer. Source stays in memory, outside conversation storage. Process-local opportunities/cache safely expire after API restart or on a different worker; hosted affinity and cancellation acceptance remain F13.11 work.

For isolated verification in PowerShell, set `$env:FLAME_NEXT_DIST_DIR='.next-f13'` and run `npm run build`, then `node tests/simulations-browser.cjs`. The harness uses the same local Playwright/Edge tools as the existing UI suites and a synthetic signed-in API. `node tests/simulations-browser.cjs --live` explicitly runs the four synthetic configured-LLM demonstrations and holds their source only in a temporary memory server. Existing F11/F12 browser suites can target this build with `$env:FLAME_TEST_NEXT_DIST_DIR='.next-f13'`. See the [F13 report](../../../project-stages/F13-IMPLEMENTATION.md) for modified files, versions, evidence and remaining release limits.
