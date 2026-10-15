# FLAME project stages — canonical documentation

Consolidated: 2026-09-25.

Start with [PROJECT_CONTEXT.md](PROJECT_CONTEXT.md) for technical orientation. Use [STAGES-STEPS.md](STAGES-STEPS.md) as the combined frontend/backend development plan and the only active progress tracker.

For the reviewed folder structure, actual technology stack, current implementation, setup and remaining acceptance work, read [DEVELOPMENT-HANDOFF.md](DEVELOPMENT-HANDOFF.md) (documentation reconciled: 2026-10-09; dated environment evidence retained). It is a technical handoff, not another progress tracker.

For the current curriculum hierarchy, mapping coverage, catalogue lifecycle, recommendation flow and Excel relationships, read [CURRICULUM-CATALOGUE-RELATIONSHIPS.md](CURRICULUM-CATALOGUE-RELATIONSHIPS.md).

For learner Explore, member browsing APIs, verification and runtime restart instructions, read [F10/B14 handoff](backend/stage-14-learner-explore.md).

For the Interactive-only HTML5 build, source files, upload/delivery/viewer flow, live Gravity Lab draft and mappings, current port-8001 runtime, repeatable checks and remaining acceptance, read [B9 Interactive HTML5 handoff](backend/stage-9-interactive-html5.md). Its October 9 runtime note supersedes earlier local routing snapshots.

For clickable Browse Media thumbnails, provider images, private uploaded-video thumbnail management and publication requirements, read [Video thumbnail handoff](backend/stage-9-video-thumbnails.md).

## Document ownership

| File | Owns |
| --- | --- |
| PROJECT_CONTEXT.md | Agent entry point, code/design/runtime locations and integration cautions |
| DEVELOPMENT-HANDOFF.md | Dated orientation: actual stack, folder/module map, setup, evidence, gaps and handoff priorities |
| STAGES-STEPS.md | Numbered steps, current totals/statuses, stage prerequisites, decisions, evidence and execution sequence |
| backend/stage-1/module-architecture.md | Module boundaries, transactions and relational schema rules |
| backend/stage-1/api-contracts.md | API contracts, Excel input, mapping, response and lifecycle rules |
| backend/stage-1/admin-panel-specification.md | Nine admin screen fields/actions/validation |

The three specifications remain separate because they contain unique implementation detail. Brief summaries/link references are intentional; do not copy their tables into the context or tracker.

Product scope remains in [Planning/mvp-scope.md](../Planning/mvp-scope.md); future RAG remains in its [roadmap](../Planning/RAG/rag_mvp_roadmap.md). Existing frontend delivery/validation notes are historical evidence, not parallel current progress trackers.

## Consolidation record

| Retired file (relative to this folder) | Preserved destination |
| --- | --- |
| backend/backend-development-stages.md | STAGES-STEPS: B1–B10, dependency gates and deferred roadmap; API resource provenance in api-contracts |
| MVP pre requisites/stage-wise-prerequisites.md | STAGES-STEPS: stage entry prerequisites, decision deadlines and readiness record |
| backend/stage-1/input-review.md | PROJECT_CONTEXT: code/workbook observations; STAGES-STEPS: current decisions |
| backend/stage-1/completion.md | STAGES-STEPS: verification evidence and old-to-new Stage 1 step mapping |
| backend/stage-1/README.md | This index and direct links to the retained specifications |

Original ten-file folder snapshot: [recovery archive](../work/project-stages-before-consolidation-2026-09-25.zip). Retired files can be recovered from it; it is historical, not an active source of requirements.

Progress IDs/counts/statuses were preserved. Consolidation is documentation work, not new feature completion. Paths were repaired after the owner's folder moves; candidate revised workbook discovery does not imply validation.

## Update rule

Change each fact in its owning document, link from other documents, and record actual checks in the tracker. Do not maintain a second stage list, prerequisite checklist or completion report. Read applicable AGENTS.md before implementation; never include credentials.
