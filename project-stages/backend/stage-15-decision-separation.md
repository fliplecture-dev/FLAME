# B15 functional modules and decision engine separation

Date: 2026-10-16. Status and numbered packages belong to [STAGES-STEPS.md](../STAGES-STEPS.md#b15--functional-modules-and-decision-engine-separation).

## Current package layout — owner-requested follow-up

After policy extraction, the owner explicitly requested a correct, modular folder layout for both kinds of work. B15.11 groups all feature implementations under three canonical layers. The complete [module tree and development rules](../../development/apps/flame-api/app/modules/README.md) describe the current locations; the extraction-stage paths in the historical sections below precede this move.

- `app/modules/functional/` contains eleven existing functional features plus `recommendation_history`. Student identity, memberships, conversations and activity retain separate ownership; no duplicate generic students feature was invented. Health remains a functional operational interface.
- `app/modules/decision_engine/` retains the pure recommendation, teaching and visual components.
- `app/modules/application/` contains teaching, recommendation and learning-response use-case coordination.
- Shared contracts stay in `app/contracts`; infrastructure stays in `app/core`; `app/main.py` remains the composition root.

Actual ownership was corrected while grouping: recommendation tables/repository/reference counts/cleanup moved from recommendation coordination to `functional/recommendation_history`. Its `service.py` exposes the existing transaction-scoped operations. Topic-check records moved to `functional/conversations/topic_checks.py`, and authoritative teaching-context queries moved to `functional/curriculum/teaching_context.py`. Functional modules consequently have no application or engine imports. Policies retain no infrastructure dependencies. Application workflows access history through its public service rather than importing the repository directly. Existing cross-feature ORM/session interfaces remain within the monolith; independent network deployment is not claimed.

App startup and Alembic now call the same explicit, idempotent `functional/model_registry.py`. The initial cold-app snapshot included only 33 tables because it had not imported the existing lifecycle declaration. Verification against the original tracked source at `39c319f264a377ba4c42e5316acdf6cb94d1eda5`, with all pre-existing declarations loaded, confirms **34 identical table/index declarations**, not a new schema. `tests/fixtures/module-layout-baseline.json` records those independently verified original hashes. No database connection or migration was used for this check.

All application, migration, script, test, dynamic-import and monkeypatch paths were migrated to canonical layer paths. Four audited resource-level recommendation adapters were retired to remove upward dependencies. Old flat feature imports are internal paths and are no longer available; any maintenance script outside this repository needs the same prefix migration. Policy helper exports retained inside the relocated application packages still resolve to the one engine implementation. No import hook, duplicate package tree or eager package initializer was added.

The OpenAPI comparison identified two module-qualified Confirm schema identifiers affected by relocation. `app/core/openapi.py` preserves those existing identifiers and references, so the complete published OpenAPI document remains byte-equivalent after canonical JSON serialization: **108 paths**, with unchanged contracts. Cached calls retain the same document. The schema fixture and tests protect against duplicate model registration, upward dependencies, flat imports and future accidental contract changes.

Follow-up verification: **334 backend tests passed, 54 opt-in checks skipped**, plus **44 frontend unit tests passed**. Four added layout tests run in the normal CI suite. All captured B15 policy results still match. This follow-up changes backend package locations and internal import wiring; the earlier browser/build evidence below belongs to the extraction delivery and was not rerun for this folder-only change. Existing external database and packaged-install acceptance remains pending for the previously recorded reasons; this request did not explicitly authorize the denied database target, and it was not retried.

Rollback addition: preserve the current work before restoring reviewed source. Restore each feature directory together with all migrated imports in main, migrations, scripts and tests; restore original recommendation history, topic-check and teaching-context locations together with their owners. Remove the new model-registry/OpenAPI installation calls only when restoring the original bootstrap. The original tracked source archive used for schema comparison is local scratch evidence, not a deployable release. Do not run old and new package copies together or reset unrelated changes. Database downgrade, schema conversion and saved-decision rewrites remain unnecessary.

## Baseline and extraction design

The owner authorized B15 implementation after reviewing the separation plan. B11 already supplied catalogue candidate interfaces and recommendation-owned history. Extend that work in the same application/database; preserve HTTP, storage, database schema and generated-answer behavior.

Fresh full backend baseline: **322 passed, 54 skipped**, two upstream Starlette/AnyIO deprecation warnings. Command: `.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider --basetemp E:/FLAME/work/b15-baseline-temp`. The initial default-temp run had six setup permission errors; the workspace-local temporary directory resolves them. Opt-in database/storage tests remain skipped.

Before extraction, `tests/b15_policy_snapshot.py` captured complete representative decisions in `tests/fixtures/b15-policy-baseline.json`: twelve recommendation evaluation cases, schema-1 image selection/repeat behavior, teaching profiles, topic ambiguity, intent fallback, capability/authority checks, rendering and simulation routing. The fixture intentionally includes the two known negation defects; changing them is separate from extraction.

Fresh synthetic ranking measurement: 1,000 calls over six eligible candidates, median **0.1789 ms**, p95 **0.1897 ms**, zero database/provider calls inside selection. This is an in-process fixture measurement, not production performance. Existing coordinator tests establish one teaching call and no recommendation loader on the answer path; quota/replay/source-generation tests remain unchanged.

Audit of production callers: teaching answer/capability routes use capability checks; answer/prompt/topic-check/clarification use profiles/resolution; answer and simulation generation enforce authority predicates; prompt and simulation routes choose visual engines. Recommendation service uses ranking, legacy image policy and intent fallback; evaluation scripts also consume these helpers. Explore uses word/phrase matching only. Legacy resource selection/image/intent files already re-export B11 implementations. Keep existing test/script imports compatible while wiring active application code to the new owner.

| Destination | Exact responsibility / migration |
| --- | --- |
| `app/contracts/decisions.py` | Shared teaching context/profile/result dataclasses, typed policy input/output dictionaries, candidate protocol and existing Choice/Decision validation. No service imports. |
| `app/contracts/math_templates.json`, `math_templates.py` | One packaged trusted static registry, shared by validation and routing. Frontend parity test compares its existing registry against this file. No second backend registry. |
| `app/modules/decision_engine/recommendation/{selection,image_selection,learning_need}.py` | Existing pure policies; dictionary fields/results unchanged. Selection accepts candidate projections rather than ORM objects. Schema-1 image policy retains a structural candidate contract for compatibility. |
| `app/modules/decision_engine/teaching/{profiles,resolution,capabilities,output_guard}.py` | Pure teaching policy and topic matching; context/profile/result types come from shared contracts. |
| `app/modules/decision_engine/visual/{mathematics,simulation}.py` | Pure rendering decision and engine selection. No generated-source cache, provider adapter, prompt assembly or runtime/compiler code. |
| Existing recommendation/teaching policy paths | Explicit compatibility re-exports. Production coordinators import new policy paths directly. Keep aliases because existing tests/scripts/public Python callers still use them. |
| Existing functional and coordinating modules | Candidate eligibility, current context/access checks, actual output filtering/specification validation, provider calls, quota/claims, transactions, persistence/history and delivery remain authoritative. |

Contracts preserve unknown-level fallback, exact existing language filtering, score ordering by descending score then stable ID, empty-pool results and reason strings. Policy version `b15-parity-1` identifies this source extraction internally; do not add fields to historical/public decision JSON or alter prompt/profile versions. Later behavior changes require evaluation and an explicit version update. Pure functions return ordinary serializable dictionaries or frozen dataclasses; validated Choice/Decision schemas still gate persisted selections.

Functional eligibility is separate from preference: candidate services enforce current publication/mapping/availability and resource playability; ranking applies relevance, grade/language suitability and intent. Selected IDs/versions must still be in the eligible pool. Current delivery and saved-selection replay recheck owner/path/publication/version; the policy result never authorizes an operation. No eligibility duplication is introduced.

## Verification and cutover

The extraction is implemented in source. All 22 extracted function bodies match the pre-refactor source AST after excluding type annotations and normalizing the renamed internal profile import. Shared data classes retain identity through original import paths; Choice/Decision fields and serialized results are unchanged. The registry moved once to `app/contracts/math_templates.json`, is included by setuptools package-data configuration, and is deeply read-only at runtime. Policy constants are immutable; returned decisions remain ordinary independent JSON dictionaries.

Production callers now import the engine directly. Original `recommendations/{selection,image_selection,learning_need,contracts}.py` and `teaching/{profiles,resolution,capabilities,output_guard}.py` export explicit compatibility names. `teaching/math_visuals.py` still owns specification validation, prompt instructions and output filtering; it re-exports routing/registry names. `teaching/simulations.py` still owns generation/cache/quotas and re-exports engine selection. Existing resource adapters remain because tests and evaluation scripts still consume those paths. They contain no second policy implementation. No obsolete adapter with known callers was removed.

Recorded checks:

- Full offline backend suite after extraction: **330 passed, 54 skipped**, two upstream deprecation warnings. Eight new B15 tests cover pre-extraction decision parity, import boundaries, infrastructure-free process imports, functional candidate independence, compatibility identity, deterministic tie-breaking/input preservation, persisted decision validation, ambiguity/unknown grades and immutable rendering state. Existing CI's full pytest command automatically includes them. A later strengthened import-allowlist check initially omitted the standard-library `json` parser; that test rule was corrected and independently reverified.
- Frontend: **44 unit tests passed**, TypeScript passed, production build passed in `.next-b15`. The build's generated tsconfig additions were removed afterward; no product configuration change is required. Build output is ignored. The simulation browser harness now accepts the same `FLAME_TEST_NEXT_DIST_DIR` override as the mathematics harness so all checks can use the fresh build.
- Synthetic production-browser suites passed: `explore-browser.cjs` (Study/Curiosity, all three catalogues, per-item open/access transport, restored history, stale responses, responsive/focus behavior); `math-visuals-browser.cjs` (17 templates, three engines, invariants, controls, history/retry, keyboard/axe and 1440/900/390px); `simulations-browser.cjs` (all six engine paths, isolation, interrupted-source recovery, independent streaming/compilation, zero completed sandbox network requests and host responsiveness after an infinite-loop probe); `resource-library-browser.cjs` (creation, mapping/deletion, external-video validation, preview and native WebM playback). These use isolated synthetic APIs, not live accounts/provider calls or real catalogue writes.
- After-extraction ranking fixture: 1,000 calls/six candidates, median **0.1859 ms**, p95 **0.1959 ms** versus baseline 0.1789/0.1897 ms. The approximately 0.007 ms median difference is an observation from separate local runs, not a production regression guarantee. Policy functions still make zero database/provider calls; coordination/provider/transaction bodies are unchanged.
- `git diff --check` passed. A no-network wheel-build probe could not run because the local Python environment lacks `setuptools`; packaged-wheel installation is unverified. Runtime resource loading, package-data declaration, all template validators and cross-language registry parity are checked from source.

Five selected rollback-only database journeys could not connect inside the sandbox (network permission denied); the other 20 checks in that selected command passed. The escalation was rejected by automatic approval review because the configured external database target was not specifically authorized and tests can perform writes despite transaction rollback. Do not retry that target through another host, credential or indirect execution. Explicit owner approval for this configured development database is required before rerunning B6 resolution, B7 answer/replay, MVP recommendation/schema-1 history, Explore mapping/open and interactive media upload/delivery transactions. Those five database checks are pending, not passing evidence. No migration, production restart, deployment or paid provider call occurred. B15.9 and final B15.10 acceptance remain partial; existing B8/B9.11/B10/F13.11 release gates remain open.

Repeat local checks from the API directory:

```powershell
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider --tb=short --basetemp E:/FLAME/work/b15-verification-temp
```

From the web directory, run `npm run test:unit`, `npm run typecheck`, then build with `$env:FLAME_NEXT_DIST_DIR='.next-b15'; npm run build`. Explore and Resource Library inherit that build setting; mathematics and simulation harnesses additionally accept `$env:FLAME_TEST_NEXT_DIST_DIR='.next-b15'`. Run the four recorded `node tests/<suite>.cjs` commands. Resource Library and simulation suites both use port 3117, so run them sequentially. These browser tools are local prerequisites and are not installed by this refactor.

## Change ownership, cutover and rollback

For a policy-only enhancement, modify the relevant engine component, add evaluation examples, and update `POLICY_VERSION` when behavior changes. Preserve original saved choices; a source policy version is distinct from saved JSON schema and existing teaching prompt/profile versions. Candidate retrieval/delivery changes belong to the functional owner and must retain permission/publication/version tests. Shared contract changes require both suites plus coordinator compatibility checks. Engine code may import only its own components, shared contracts and the narrowly allowed standard library; the static template loader is shared packaged data, not a storage service.

Application factories and fresh isolated Python processes use the new imports successfully. Local browser suites ran the fresh production frontend build with synthetic APIs. Final configured-database cutover acceptance is pending approval; running production services were not restarted. No database conversion is required.

Source baseline: `39c319f264a377ba4c42e5316acdf6cb94d1eda5`. For rollback, preserve subsequent local changes first, then restore only reviewed B15 paths from that revision. Restore caller imports together with their original helper implementations; restore `teaching/context.py` with its original context type and recommendation contracts with their original classes. For the visual phase, restore `teaching/math_templates.json`, its old loader and setuptools package-data entry together with the old frontend registry-test path. New unused engine/contracts files may remain inactive temporarily; do not leave both implementations active. Restore browser-test overrides only if they conflict with a subsequent change. Re-run affected suites before restarting the existing application. Do not reset the entire working tree, downgrade a migration, restore a database backup or rewrite saved decision JSON. This source rollback procedure is documented; no production rollback drill was performed.

## Follow-up behavior changes

- Negated tutor intent: “Explain gravity; I do not want a tutor” currently yields `human_help`. A future policy change should yield `explain` and never offer a tutor solely due to the negated phrase; explicit positive tutor requests must still work.
- Plural animation opt-out: “Explain gravity with no animations” currently selects Matter. A future policy change should return no simulation for singular/plural opt-outs while retaining positive simulation requests.

These cases are preserved in the parity fixture; B15 extraction does not claim to repair them.

## Subsequent visual-policy delivery — 2026-10-16

[B16](stage-16-visual-routing.md) intentionally supersedes the extracted visual behavior with keyword routing, composed mathematics and catalogue-first inline simulations. The historical B15 fixture remains; its parity test explicitly accounts for the reviewed Three.js default and plural animation opt-out fix. The plural defect above is resolved by B16; negated tutor intent remains open. B15 database and packaged-install acceptance remain pending.
