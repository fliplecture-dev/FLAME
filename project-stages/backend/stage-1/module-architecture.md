# Modular backend and initial data model

Canonical technical specification; progress and prerequisites are maintained in [STAGES-STEPS.md](../../STAGES-STEPS.md). Schema definitions here are plans unless explicitly identified as implemented.

## Runtime

One FastAPI application under development/apps/flame-api, one PostgreSQL database, one deployment initially. Next.js BFF calls the API using server-held authentication. The browser never receives database credentials or provider secrets.

Each feature owns router.py (HTTP), schemas.py (validation), service.py (business operations), repository.py (queries) and models.py (tables) when needed. Do not create empty CRUD implementations merely to fill folders. Current implementation contains health plus teaching contract schemas; other modules are introduced in their delivery stages.

## Ownership

| Module | Owned data / responsibility | Public surface |
| --- | --- | --- |
| identity | Auth identity mapping, profiles, admin assignment | /me; BFF auth/session operations |
| curriculum | Curricula, levels, subjects, domains, optional categories, topics, subtopics, revisions, imports | Catalogue and admin import/edit |
| learning | My Learning memberships/visibility | Member learning items |
| conversations | Sessions, turns, pins if enabled, idempotent requests | Sessions/messages |
| teaching | Profiles, prompt versions, answer orchestration | Ask endpoint mounted under sessions |
| ai_gateway | Provider adapters, usage and timeouts | Internal only |
| resources | Media metadata, publication and authorized delivery | Member resources and admin CRUD |
| teachers | Profiles, expertise, language, publication and listed availability eligibility | Admin catalogue and public candidate/profile interface |
| activity_kits | Kits, money/currency, publication, topic links and eligible activity guides | Admin catalogue and public candidate/guide interface |
| recommendations | Intent, relevance ranking, decisions, acknowledgements and shown ID/version history | Existing session recommendation endpoints; owning repository/table mapping |
| learning_response | Nonblocking composition of teaching output and optional recommendation states | Additive envelopes on existing ask/recommendation endpoints |
| student_activity | Minimal events and admin aggregates | Admin student activity |
| data_lifecycle | Coordinates deletion across owners | Member deletion operations |
| health | Liveness/readiness | Public operational endpoints |

No separate general admin business module: protected admin routers invoke the same owning services. Admin Student Management composes identity, learning and activity service results, without reading private conversation text.

## Boundaries and transactions

Routers validate transport inputs and call services. Repositories do not generate prompts or call providers. Modules may call another module's public service/interface, not its repository. Avoid cyclic imports; Teaching coordinates Conversations, Curriculum and AI Gateway. Shared core contains configuration, engine/session lifecycle, errors and logging only.

Use a request-scoped transaction for related local writes; services accept a unit of work/session rather than independently committing nested calls. Foreign keys may cross modules within the monolith. Account deletion is coordinated by lifecycle but each module deletes its owned data. External provider calls must not hold a database transaction open.

Use an outbox/durable worker only when an implemented workflow requires reliable asynchronous processing. Resource activity is recorded after authorized operations with duplicate suppression. No message broker is needed for the foundation.

## Initial relational model (Stage 2 migrations, not implemented yet)

| Entity | Key fields / constraints |
| --- | --- |
| student_profiles | UUID id; unique auth_subject; display_name; registration/status; minimized profile fields |
| admin_roles | auth_subject; controlled grant; no public role assignment |
| curricula | UUID id; globally unique normalized code; display name; description; draft/published/archived state; edit version; active revision |
| levels | UUID id; required curriculum_id FK; normalized code/name unique within curriculum; display name; edit version |
| subjects | UUID id; level_id FK; unique normalized name within parent |
| domains | UUID id; subject_id FK; unique normalized name within subject |
| categories | UUID id; domain_id FK; unique normalized name within domain; unique (id, domain_id) for composite references |
| topics | UUID id; required domain_id FK; nullable category_id; composite (category_id, domain_id) FK to categories; normalized-name uniqueness within domain/category; nullable learning_outcome |
| subtopics | UUID id; topic_id FK; unique normalized name within parent |
| curriculum_revisions | revision id, required curriculum_id FK, timestamp, approved catalogue change; revision belongs to exactly one curriculum |
| curriculum_imports | required curriculum_id FK, owner, file reference/hash, column map, base revision, status, counts/errors |
| learning_memberships | student + selected curriculum/level/subject path unique; visible/hidden; retained on removal |
| sessions | student, mode, selected path (nullable in Curiosity), revision, teaching context snapshot |
| messages | session, turn, role, validated blocks, created_at; Study resolved topic/subject/version; null curriculum mapping for open Curiosity and stable recommendation selection reference/snapshot as needed |
| answer_requests | student/session/idempotency key unique; payload hash; pending/completed/failed result |
| resources | id, type, title, description, storage key OR reviewed URL, publication, version |
| resource_topics | resource + topic/subtopic association with uniqueness and valid parent path |
| teachers | id, name, bio, qualifications, experience, languages, review state, availability, publication |
| teacher_expertise | teacher + subject/topic/level associations; declared/reviewed status |
| activity_kits | id, name, description, materials, cost NUMERIC, currency, availability, supplier URL, instructions, publication |
| kit_topics | kit_id + topic_id unique; optional subtopic association validated against topic |
| activity_events | student, session/path, event type, timestamp, deduplication key |
| deletion_requests | subject, request status, timestamps; coordinate policy-aware deletion |

Topic IDs remain stable through rename. Catalogue revision and session snapshots preserve historical context; a rename cannot rewrite the meaning of already stored prompt context. Missing import rows never delete data. Archive uses restricted references rather than cascading removal. B4 archived-ancestor eligibility, retained memberships and no-reactivation policy are specified in the B4 section below. Retained history remains readable subject to ownership/deletion policy. The B4 policy below blocks new questions in affected sessions and specifies revision handling for continued teaching and recommendations. Preserve original historical snapshots; current publication/access checks still govern delivered resources and teachers. Record the decision in the tracker and translate it into API/UI outcomes before implementation.

### Optional categories and import identity

Every topic has a domain. If category_id is null it belongs directly to that domain. Otherwise the composite foreign key ensures the selected category belongs to the same domain. Use separate unique indexes for categorized topics (domain_id, category_id, normalized_name WHERE category_id IS NOT NULL) and uncategorized topics (domain_id, normalized_name WHERE category_id IS NULL), so SQL NULL semantics do not allow duplicate imports.

Curriculum ancestry is resolved through domains.subject_id, subjects.level_id and levels.curriculum_id. Do not duplicate subject_id on topics. The server validates the entire submitted context against these relationships. Names reused under different categories or domains are distinct paths, not duplicates.

Keep optional Source URL as provenance associated with the imported topic/subtopic, separate from name fields. Preserve sheet/row and source-reference associations when duplicate paths have different URLs; do not silently replace a prior reference. Reference URLs alone do not ground generated answers. Record sibling display order from optional Sort Order or first encounter in workbook sheet/row order. Renames preserve IDs; moving a node to another parent requires an explicit edit and validation, not inference from Excel names.

Excel names cannot identify renames reliably. Admin rename preserves identity; future external import codes can support automated rename matching. Normalize surrounding whitespace and agree case/Unicode policy after inspecting real data.

No document, chunk, embedding, institution, achievement or mastery tables in MVP. Existing frontend proficiency/progress fields are null unless backed by genuine approved data; activity is never converted into mastery.

## Curriculum scope and recommendation ownership

Curriculum validates each Study teaching request against a published school path. Open Curiosity accepts general learning questions without a selected path or per-turn curriculum mapping and applies an under-15 response ceiling. Explicit unsupported capabilities are checked before generation.

Teachers service filters eligible published subject-expert associations, then randomly selects within that pool. Resources service independently supplies approved topic-related resources. Teaching/member recommendation composition uses those public services, never model-invented profiles or another module's private repository. No-match returns no teacher card; no cross-subject fallback. Preserve selected IDs for retry stability while rechecking current publication/access at delivery. Exact storage and card/display settings are implementation details, not completed schema.

## Growth path

Introduce knowledge retrieval behind an internal evidence interface later. Extract services only when scaling, isolation or release needs justify network boundaries. Keep versions, stable IDs and permission filters in contracts now. Automated testing and indexes follow actual access patterns, not speculative microservice complexity.

## Mandatory dynamic curriculum root — owner decision 2026-09-25

Stored hierarchy: Curriculum → Level → Subject → Domain → optional Category → Topic → Subtopic. Student navigation hides Category and renders Curriculum → Level → Subject → Domain → Topic → Subtopic. Every published Topic has at least one Subtopic; Category ID remains available to the teaching service. Curriculum is a programme/catalogue, not an institution or a fixed board enumeration. New curricula and levels are database records; never hardcode the sample KG–5 Science workbook as system scope. A curriculum can be created empty and populated later. Same level/topic names under different curricula remain independent records.

Every Study context and saved path includes curriculum_id. Study sessions and answer turns bind their full path to a revision of that curriculum. Open Curiosity has no curriculum revision. Import preview/commit is bound to exactly one authorized curriculum and its base revision; a repeated workbook Curriculum Code must match that selected target on every row. An import cannot change its target or write another curriculum. Revisions and stale-preview checks are scoped to that curriculum so independent catalogues can be edited separately.

Validate submitted path ancestry through all FKs before accepting operations. Where curriculum_id is also stored on sessions/imports/revisions, use composite references or transactional checks to prevent mismatches; UUID shape validation alone is insufficient. Resource/teacher/kit topic mappings inherit curriculum through the same chain. Same-named Science subjects in different curricula are distinct expertise mappings; do not silently authorize cross-curriculum matches. Open Curiosity does not search a published curriculum or select a programme from question text.

Admin creates curricula and child nodes via the existing Curriculum Catalogue screen or adds descendants by import. Publication requires an eligible nonempty path; archiving a curriculum removes its descendants from new selection while preserving owned historical snapshots. Current root/ancestor eligibility is checked for writes and delivery; detailed resume/continued-question policy remains gated before B4.2. Cross-curriculum reparenting is excluded from MVP edits; create/import a new path, preserving existing historical IDs.

No migrations are applied in B1. B2 implements and tests curriculum-scoped uniqueness, FKs, revisions, import isolation and repeat-import identity with at least two curricula sharing level/subject/topic labels. A production workbook is not required to finalize this design.

### B4 archive and revision policy — 2026-09-26

Archiving a curriculum or descendant hides that branch from new published catalogue selection and search. A parent archive makes every descendant ineligible without changing descendant IDs or rewriting membership rows. Archived nodes cannot be edited or used as parents for new nodes, and reactivation is outside the MVP. Import commits that encounter an archived matching path fail explicitly. Admin revision history records the affected ID and the before/after values for edits; historical IDs remain stable.

My Learning hide/restore changes only visibility. A subject hide masks its selected descendants; a curriculum hide preserves all owned membership rows and hides the curriculum selection. Restoring reuses those rows and their IDs. An archived path remains stored as history but is unavailable for new selection or restoration while archived.

When B5 sessions are implemented, existing transcripts remain readable after an archive or rename. A new question in an existing Study session must revalidate every current ancestor and require the current curriculum revision to equal the session's pinned revision. If an ancestor is archived or the revision differs, return a machine-readable unavailable_context result and prompt the student to start a new selection/session. This rule avoids silently changing the meaning of a historical Study context. Recommendations and resource delivery always use current publication and authorization, even for a historical transcript. Open Curiosity has no catalogue resolution on new turns.


## B11 implemented boundaries (2026-10-07)

[Modular migration handoff](../stage-11-modular-migration.md) records actual code/interfaces and compatibility. Typed catalogue contracts live in `app/contracts`, not shared business logic in core. Media, Teachers and Kits expose eligible candidate DTOs; Recommendations imports these interfaces and an owned conversation snapshot service rather than catalogue ORM/admin routers. The composer preserves split HTTP requests: answers return immediately with pending selection, while a later recommendation response is completed, none or unavailable. Existing authorization, publication and version guards remain. One app/database; no extra model call, worker or migration. Recommendation table ownership moved without changing its physical schema/JSON.
