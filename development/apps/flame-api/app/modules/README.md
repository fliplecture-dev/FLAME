# FLAME backend module structure

Each directory owns a different kind of work. Keep package initializers free of service imports so a policy or feature can be imported and tested on its own.

```text
modules/
├── functional/                 Records, eligibility, delivery and lifecycle
│   ├── activity_kits/
│   ├── bulk_transfer/
│   ├── conversations/          Sessions, requests, messages and topic-check records
│   ├── curriculum/             Catalogue, imports and authoritative teaching context
│   ├── data_lifecycle/
│   ├── health/
│   ├── identity/               Student identity, profiles, roles and access
│   ├── learning/               Memberships and visibility
│   ├── recommendation_history/ Stored choices, references and cleanup
│   ├── resources/
│   ├── student_activity/
│   ├── teachers/
│   └── model_registry.py       App and Alembic use the same model declarations
├── decision_engine/            Pure policy over typed data
│   ├── recommendation/         Intent, ranking, images and display/repetition
│   ├── teaching/               Profiles, capabilities and topic matching
│   └── visual/                 Keyword intent, response/math/engine routing and media relevance
└── application/                Use cases connecting functional services and policy
    ├── learning_response/      Composition and Explore workflows
    ├── recommendations/        Candidate retrieval, selection and acknowledgements
    └── teaching/               Prompts, answer/provider and simulation orchestration
```

Shared DTOs and trusted static specifications live in `app/contracts/`. Configuration, database infrastructure, safe errors and logging remain in `app/core/`. `app/main.py` is the composition root: it registers models, configures infrastructure and mounts the unchanged HTTP routes.

## Dependency rules

- **Functional owners** may use core infrastructure, shared contracts and other functional public interfaces. They never import application workflows or decision policies. They enforce permissions, publication, mapping, availability and current delivery eligibility themselves.
- **Decision policies** may use shared contracts, their own policy components and the allowed standard library. They receive eligible data and return decisions. They never access a database, HTTP transport, provider, private storage or functional/application modules.
- **Application workflows** coordinate functional interfaces and policies. They own request sequencing, provider invocation, prompt construction and composition. Recommendation storage is accessed through `functional.recommendation_history.service`; its repository stays private to that owner.
- All persisted ORM declarations belong to the functional layer. Add a new model module to `functional/model_registry.py` so app startup and Alembic agree. Importing the registry or a package must not connect to the database.
- Actual output validation, authorization and sandbox enforcement stay at their execution boundaries. A policy decision is never an access grant.

Existing functional features retain their established internal file layout: HTTP in `router.py`, business operations in `service.py`, queries in `repository.py` when needed, and declarations in `models.py`. Large features may have focused files for imports, candidates or lifecycle operations. Do not create empty files or force every feature into identical CRUD scaffolding. Topic-check records are in `conversations/topic_checks.py`; authoritative teaching context queries are in `curriculum/teaching_context.py`.

## Independent development

For media/student/teacher/kit changes, work in the relevant functional owner and run its validation/access/lifecycle tests. Student functionality already spans `identity`, `learning`, `conversations` and `student_activity`; a duplicate generic student owner would blur that ownership. For a ranking or teaching-rule change, work in the engine and run policy evaluation and contract tests without database/provider setup. For a use-case change, work in application coordination and verify retry, quota, failure and persistence behavior.

Use absolute canonical imports such as `app.modules.functional.resources.candidates` and `app.modules.decision_engine.recommendation.selection`. All in-repository scripts, tests and Alembic wiring use the new locations. The old flat `app.modules.resources`, `app.modules.teaching` and other feature paths are retired internal Python paths; external maintenance scripts using them need the same import migration. Policy helper exports retained inside application packages still resolve to the one engine implementation. The retired resource-level recommendation adapters no longer create upward dependencies.

`tests/test_module_layout.py` enforces ownership/direction, canonical imports, model registration and the pre-move OpenAPI/PostgreSQL schema baseline. `tests/test_b15_decision_engine.py` enforces engine isolation and extraction parity, with explicitly recorded subsequent visual-policy changes. `tests/test_visual_routing.py` verifies the B16 response and catalogue-first policies, functional delivery and coordinator boundaries. All run in the normal API CI suite. Before intentionally changing an HTTP/schema contract, review the change and update its compatibility fixture explicitly.

The active visual entry point is `decision_engine/visual/routing.py:decide_response_visual`; `keywords.py` owns positive/negative language, `mathematics.py` trusted template matching, `graphs.py` required graph intent and bounded fallback specifications, `simulation.py` engine selection and `media.py` catalogue relevance. Application teaching workflows persist/use the shared plan and coordinate catalogue lookup before bounded generation. `functional/resources/simulations.py` owns current eligible document delivery and never ranks or calls providers. See the [B16 handoff](../../../../../project-stages/backend/stage-16-visual-routing.md) for behavior, source pinning and verification.

This remains one application and database. The boundaries support independent code changes and tests; separate deployment or independent database scaling would require additional service contracts and operational work. Existing cross-feature ORM/session use is retained rather than claiming network-service isolation.
