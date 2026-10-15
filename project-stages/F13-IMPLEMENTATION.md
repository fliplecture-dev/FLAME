# F13 implementation report — 2026-10-15

The development implementation runs LLM-generated simulations inside the existing FLAME response box, beside the explanation. No separate simulation page, permanent simulation storage, approval workflow or resource retrieval was added. Thirteen packages are complete in development; F13.11 remains PARTIAL for hosted/serverless affinity and cancellation acceptance. Nothing was deployed.

## Runtime support

| Runtime | Implemented scope |
| --- | --- |
| Matter.js | Generated 2D rigid-body physics in an OffscreenCanvas worker. A trusted world helper supplies fixed stepping, drawing, gravity/friction sliders, dragging, keyboard movement of the first dynamic body and cleanup; generated code uses Matter Bodies/Composite/Body/Events. Custom worker modules may implement their own simulation lifecycle. |
| Three.js | Generated imperative 3D scenes in a worker; the documented renderer helper bounds ordinary rendering and owns disposal. |
| React Three Fiber | Generated JSX scenes in a worker-local React root, with pointer/keyboard camera orbit, pause/resume and reset. |
| Phaser | Trusted Phaser scene adapter using Phaser's bundled Matter integration. Generated worker code supplies bounded circle/rectangle scene commands; the adapter supplies dragging and physics controls. This is a restricted learning-activity API, not arbitrary DOM-based Phaser game code. Existing authored full Phaser catalogue documents remain supported. |
| Rive | The existing original FLAME-authored Weather World artwork, locally embedded with its runtime/WASM. Generated worker controllers can change its authored weather/wind inputs. Existing catalogue Rive documents remain supported. No new `.riv` artwork is generated; the community cat testing draft was not redistributed. |
| HTML5 | Generated Canvas 2D animations and SVG path illustrations through Path2D inside a worker. Arbitrary generated HTML/DOM/SVG documents are outside this worker contract; existing self-contained authored HTML viewers are unchanged. |

The server routes explicit interactive requests using a conservative allowlist: 2D physics → Matter, games/activities → Phaser, 3D science → R3F or explicit Three.js, authored animation → Rive, lightweight animation → HTML5. Normal prose/charts and F12 mathematics retain their existing routes. Routing is lexical and intentionally narrow, not a general multilingual semantic classifier.

## Generation, compilation and containment

The existing provider remains `gpt-6-luna`, with the unchanged 12-second transport timeout and 1,500-token output cap. An eligible fresh answer can make one additional logical simulation-generation request, subject to bounded owner quotas and the existing provider spending policy. Early larger code requests hit provider timeouts; engine-specific prompts and the trusted physics bootstrap reduced the required source. Complex generations can still fail gracefully.

Text uses a new NDJSON ask-stream path. The final answer still goes through the existing schema, quality, ownership, persistence and replay checks. Structured rich JSON waits for final validation; Markdown can show a provisional streaming preview. Simulation generation and compilation occur independently after the saved explanation is available. A compile failure does not remove the text. The existing complete-answer route remains available for older API deployments.

Executable source stays in bounded process/tab memory. A fresh committed answer grants a two-minute, single-use in-process generation opportunity. The owner/message cache has a 15-minute access TTL, 128-entry process bound and at most 20 new opportunities per owner per in-process 24-hour window (also bounded by the configured question limit). Failures are deduplicated too. Expiry, replay or API restart cannot silently start a new paid simulation. Cache cleanup is lazy on access; process/tab teardown releases remaining memory. No source/bundles are written into messages, request receipts, object storage or application logs.

The compiler accepts bounded modules, bundles a fixed local dependency allowlist and executes no generated code in Node. Compilation runs in a native Node worker with a ten-second deadline and two-job process limit. Browser execution uses a script-only, opaque-origin iframe and a disposable worker. The generated module never executes in the iframe's DOM realm or host React tree. The iframe CSP restricts network/resource loading and browser permissions; worker bootstrap removes fetch, nested workers and storage entry points. String evaluation remains blocked. Trusted Phaser/Rive DOM adapters consume bounded commands rather than executable scene code.

Host messages require the active frame source and session nonce. Work liveness uses unpredictable challenge-response messages; unsolicited ready/heartbeat messages cannot refresh an established deadline. A stuck worker is terminated independently of its event loop. Close/reset/navigation remove the worker/frame, loops and listeners; generated and trusted adapters also supply cooperative disposal. Reduced-motion preference starts playback paused. Runtime failures preserve the explanation and provide reset/close controls.

These are tested browser boundaries, not a claim of perfect safety. Geometry/body limits protect the documented helper paths; arbitrary generated worker code is not a hard memory/GPU quota. Browser/GPU process failures and hostile allocation/shader workloads require further containment review before public rollout.

## Installed direct packages

| Package | Exact version |
| --- | --- |
| matter-js | 0.20.0 |
| three | 0.180.0 |
| @react-three/fiber | 9.8.2 |
| phaser | 3.90.0 |
| @rive-app/canvas-lite | 2.37.6 |
| esbuild | 0.25.11 |

Versions are locked in the web package manifest/lockfile; engine bundles load only when requested. Phaser activities do not load an additional standalone Matter engine.

## Verification

| Check | Result |
| --- | --- |
| Production build and TypeScript | Passed using isolated `.next-f13` output. |
| Frontend unit suite | 41 passed, including pending-source polling, deadlines/transport abort, retrieval-only recovery, forbidden imports, invalid syntax and unsupported engines. |
| Backend default suite | Latest repair verification: 281 passed, 53 opt-in skips; two existing upstream deprecation warnings. |
| Expanded rollback-only development DB check | Passed: answer/history/replay, simulation ownership and deduplication, expired/restarted opportunity behavior, no source in message/request JSON, streamed final answer and exact-key replay. Synthetic rows rolled back. |
| F11 production browser regression | Passed Markdown/GFM/KaTeX/code/charts, saved history, retry, Study/Curiosity, accessibility and 1440/900/390px layout. |
| F12 production browser regression | Passed all sixteen mathematics activities, controls, dragging/touch, history, retry, accessibility and responsive layout. |
| Generated runtime smoke suite | Matter, Three, R3F, Phaser, authored Rive, Canvas and SVG paths rendered inside actual response frames; pause/resume/reset/expand/close and worker teardown checked. |
| Runtime isolation | DOM/storage, fetch/nested workers and string evaluation blocked. Dynamic network-import attempts did not reach a local sentinel. Thrown errors, synchronous loops and fake-heartbeat loops terminated while the surrounding conversation remained usable. |
| Independent streaming | A real response-layout stream remained visible while compilation was deliberately held and then failed. |

The four required demonstrations used actual configured-provider source, held only in a temporary memory server and executed in the real response component against a synthetic signed-in API. These were not live student/database answers. The test source was reused in memory across browser retries to avoid additional model calls.

| Required demonstration | Observed result |
| --- | --- |
| Falling ball / Matter.js | Gravity control changed downward movement; zero-gravity control, pause/resume and reset exercised. |
| Two colliding balls / Matter.js | Actual collisionStart events recorded; pointer dragging changed a body's position. |
| Sliding block / Matter.js | Under matching initial conditions, higher paired-surface friction reduced travel. |
| Rotatable solar system / R3F | Sun/four-planet illustrative scene rendered; pointer input changed camera azimuth. Sizes, spacing and motion are illustrative. |

Local screenshots are under `work/f13/`. Tests include scoped axe checks, 390px layout and reduced-motion startup. Physical Android/iOS, broad assistive-technology review and educator acceptance remain release work. Static validation and screenshots alone were not used as the isolation verdict.

## Modified files

- API: `app/main.py`; `app/modules/learning_response/service.py`; `app/modules/teaching/{answer_router.py,answer_service.py,gateway.py,prompt.py,simulations.py,simulation_router.py}`; `scripts/check_simulations.py`; `tests/{test_simulations.py,test_b7_integration.py}`.
- Web configuration: `package.json`, `package-lock.json`, `next.config.mjs`, and repository `.gitignore` for isolated build output.
- Web transport: `src/app/api/auth/csrf/route.ts` (reuse valid tokens for concurrent requests), `src/app/api/b4/[...path]/route.ts`, `src/app/api/simulations/compile/route.ts`, `src/lib/api/{auth-bff.ts,student-learning.ts}`.
- Response UI: `src/app/{layout.tsx,simulation.css}`; `src/features/learning/{conversation-types.ts,use-learning-conversations.ts,flame-conversation.tsx,response-simulation.tsx,simulation-player.tsx}`.
- Runtime/compiler: `src/lib/simulations/{spec.ts,request.ts,document.ts,compiler.cjs,compiler.d.cts}`; `src/simulation-runtime/{compile.cjs,frame.js,worker.js,assets/weather.riv,assets/RIVE-LICENSE.txt,assets/README.md}`.
- Web tests: `tests/{simulation-fixtures.cjs,simulation-request.test.cjs,simulations-browser.cjs,simulations.test.cjs}` and build-directory overrides in the existing rich-response/math browser suites.
- Handoff: this report, `STAGES-STEPS.md`, `PROJECT_CONTEXT.md`, API contracts and the web README. Existing uncommitted F11/F12 work was preserved.

## Remaining limits and release gate

### Interactive preparation progress — 2026-10-15

The response shows a numeric 0–100% progress bar only while preparing an actual interactive simulation. Initial eligibility checking is silent: ordinary text/F12 answers never flash a simulation progress bar. Source progress starts only after the server returns `pending`; cached-ready source can proceed directly to compilation. Shared tab-memory jobs notify mounted viewers when preparation is confirmed. A shared `simulation-progress.tsx` component covers source generation (0–69%), compilation including lazy player loading (70–89%), sandbox startup (90–99%) and the authenticated ready signal (100%). Intermediate values are explicitly labelled “Estimated progress”: the provider/compiler do not expose a true percentage. Unfinished work never reaches 100%; terminal source/runtime failures and closed players remove progress, and recovery/reset creates a fresh stage indicator. Ready shows 100% for one second and then hides the indicator. Timers/listeners are disposed on stage changes/unmount. The bar exposes progressbar bounds/value/text, keeps percentage updates out of live status announcements and respects reduced motion.

Changed files: `src/features/learning/{simulation-progress.tsx,response-simulation.tsx,simulation-player.tsx}`, `src/app/simulation.css`, and `tests/simulations-browser.cjs`. No packages, provider calls, token settings or storage were added for progress.

Verified: production build/TypeScript and 41 frontend unit tests passed. The production browser regression (Matter fixture plus shared recovery/streaming/failure/isolation cases) passed generation progress, actual-ready 100%, held compilation below 90%, failure removal, scoped accessibility, mobile/reduced-motion and teardown checks. The signed-in app also showed compilation at 70% and both existing Matter/Three players at 100% on readiness. Generation screenshot: `work/f13/preparation-progress.png` (synthetic test source, no extra provider call).

Eligibility-only correction reverified production build/TypeScript and 41 frontend units. Browser coverage deliberately delays a non-simulation eligibility response and asserts no progress both before and after `ineligible`, then checks that actual simulation preparation still shows progress and the completed indicator disappears.

### Explicit engine request routing repair — 2026-10-15

Inspection of the user's response pane showed “using matter.js create a force explainer” and “using three.js show me the world” answered with text-only execution refusals. `select_engine` checked for interaction keywords before checking explicit engine names, so both requests were ineligible. That also omitted the sandbox capability instruction from the explanation prompt and skipped arming source generation. Explicit allowlisted engine names combined with visual creation verbs (create/show/render/build/draw/display/make/demonstrate) now opt in without requiring the learner to say “interactive” or “simulation”. Library information questions, explicit text-only/no-simulation requests and default F12 mathematics keep their existing routing. The same selector still governs prompt assembly, generation arming and source retrieval.

Live verification then exposed provider source requests timing out under the teaching answer's 12-second transport budget (two attempts took about 25 seconds). Simulation generation now runs in a daemon background job, capped at four running jobs per API process, with immediate `pending` responses and retrieval-only polling. It uses the same configured provider/model and 1500-token cap, with one 60-second transport attempt; ordinary teaching responses retain their existing 12-second/two-attempt settings. Sanitized allowlisted failure codes are cached/logged without source or provider payloads. There is no automatic paid retry after a failed source job.

Longer timing alone subsequently produced `invalid_provider_output`. Source jobs now explicitly request low reasoning effort for supported GPT-5/GPT-6/o3/o4 model families; other model names omit that optional setting. A truncated provider response reports `provider_output_limit`, rather than concealing it as malformed output. This does not increase the token cap or change normal text-request settings. Official [reasoning documentation](https://developers.openai.com/api/docs/guides/reasoning) confirms that reasoning shares the output-token budget; it supports the configuration choice, not a claim that every earlier invalid response was proven to have the same cause. The OpenAI Docs skill was used for this request setting.

Final verification: **281 backend tests passed, 53 skipped; 41 frontend unit tests passed; rollback-only B7 database integration passed**. Both exact prompts were submitted in the actual signed-in localhost app using the configured provider. The Matter response displayed a running canvas, live numeric readouts, gravity/friction and pause/reset controls; Pause changed to Resume. The Three response displayed a procedural blue/green globe inside the existing response box. Screenshot: `work/f13/live-three-response.jpg`. This live pass establishes rendering and Matter pause interaction; embedded-browser pointer automation rejected fractional iframe coordinates, so live globe drag interaction was not verified in this pass. Earlier fixture/live-demo interaction evidence remains separate. Model-generated descriptions can still promise unsupported custom controls; the runtime currently exposes the documented fixed controls only. No source was saved to disk.

Regression coverage includes both exact prompts, all six explicit engines, exclusions, F12 defaults, prompt assembly after an old execution refusal, background dedup/concurrency and single-attempt transport. An initial full-suite run hit permissions on the old pytest temporary directory; rerunning with a fresh isolated directory passed. The local launcher also now binds web port 3000 to IPv4 loopback explicitly, retaining the localhost origin; Windows had selected IPv6-only localhost, preventing embedded-browser reconnection. No broader network binding or dependency change was added.

### Loading-state repair — 2026-10-15

The reported “Preparing interactive simulation…” state exposed a client lifecycle gap: the response component cached one request, so a `pending` response never advanced to source retrieval. `request.ts` now polls the existing job, sharing the whole polling promise across mounts. Only the first fresh-answer request can start generation; all follow-up polls and the explicit “Check simulation” recovery action use `start:false`. A 90-second deadline aborts transport and leaves a recoverable message rather than indefinite loading. Expired, limited, ineligible and failed results stop polling. Source is still compiled and executed through the existing isolated player; no dependencies or persistence were added.

The frontend unit count is now 41. Production build and TypeScript passed again. The complete browser regression passed: two pending replies before ready for all six engines (plus isolation/SVG probes), interruption/retrieval-only recovery, one fresh start followed by retrieval-only polling, independent text streaming under compiler failure, controls, responsive/accessibility checks, worker cleanup and runtime failure/network containment. The browser regression uses delayed synthetic source responses and the actual compiler/runtime, rather than making additional provider calls; earlier configured-provider demonstration evidence above remains separate.

F13.11 remains PARTIAL: source/opportunity state is process-local. Multiple API workers/serverless instances need affinity or a reviewed shared ephemeral design; otherwise the next request safely returns expired rather than regenerating. Hosted stream cancellation and native compiler packaging must be verified in the chosen environment. An already-started provider request can finish within its existing timeout after the viewer closes. No durable queue or new external service was introduced to conceal these limits.

The new worker path requires browser Worker/OffscreenCanvas support and WebGL for 3D; verified here with desktop Edge/Chromium. Physics uses illustrative canvas units. Compiler limits and helper budgets do not hard-cap arbitrary browser/GPU memory. The npm audit still reports the previously recorded Next.js critical advisory plus high sharp/source-map-js advisories; no unrelated framework upgrade was performed. Public deployment, physical devices, educator validation and broader security review remain open under the existing release gates.

References used for implementation: [Matter Engine](https://brm.io/matter-js/docs/classes/Engine.html), [Phaser Matter](https://docs.phaser.io/phaser/concepts/physics/matter), [R3F Canvas/root](https://r3f.docs.pmnd.rs/api/canvas), [OpenAI Responses streaming](https://developers.openai.com/api/docs/guides/streaming-responses). The OpenAI Docs skill was used for the streaming contract.
