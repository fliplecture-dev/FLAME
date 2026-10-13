# Admin-panel specification — MVP

Canonical screen specification. Current F9/B-stage implementation status is maintained in [STAGES-STEPS.md](../../STAGES-STEPS.md).

All nine screens require owner/admin access except the sign-in form. Backend authorization applies independently of UI visibility. No institution roles, feedback, achievement, usage-dashboard or teaching-settings screens are included.

## Shared behavior

Paginated lists, clear loading/empty/error states, stable IDs, validated forms and preserved drafts on failed saves. Mutation responses contain the saved record/version; stale edits return conflict. Confirmation is required for import commit, archive and unpublish. Never reveal private conversation contents through Student Management.

| Screen | Fields and display | Actions | Validation and failure behavior |
| --- | --- | --- | --- |
| 1. Admin Sign-in | Selected identity-provider sign-in fields; recovery state | Sign in/out, recover account | Auth failure is generic; authenticated non-admin denied; no self-assignment of admin role |
| 2. Curriculum Catalogue | Curriculum → Level → Subject → Domain → Category (optional) → Topic → Subtopic; IDs, revision, state and optional provenance | Create curriculum/child nodes, browse, rename, edit metadata, publish curriculum, archive | Reject duplicate sibling names, invalid category/domain relationships and stale versions; preserve history/links |
| 3. Excel Import | Required target curriculum, workbook, sheet, column mappings, path preview, invalid/duplicate rows, created/reused/updated counts | Upload, validate/preview, confirm valid batch | Invalid rows block commit; full-path matching; same commit idempotent; changed catalogue requires renewed preview |
| 4. Import History | Import ID, target curriculum, date, status, revision, counts and row errors | List, inspect result | Empty history is normal; original-file download only if retained and authorized; failed jobs are visible |
| 5. Resource Library | Title, type, curriculum associations, publication, availability | Search/filter, preview, edit, publish/unpublish | No unpublished items in member results; unavailable files/links shown clearly |
| 6. Add/Edit Resource | Title, description, type, file OR URL, level/topic associations, optional caption/transcript | Upload/link, preview, save draft, publish | Type/size limits configured; require accessible description for images; validate parent paths; constrain interactive launches |
| 7. Student Management | Student ID, name/email, registration, status, active/hidden My Learning, measured activity | Search/filter/paginate, view profile/enrollment/activity | Admin only; no achievements or inferred completion; no private messages or implicit suspend/delete controls |
| 8. Teacher Management | Name, bio, qualifications, experience, languages, expertise/levels, verification, availability, publication | List/filter, add/edit, publish/unpublish | Required name and valid mappings; distinguish self-declared and reviewed claims; no invented mastery score |
| 9. Activity Kit Management | Name, images, description/materials, multiple topics/subtopics, suitable levels, cost/currency, availability, supplier link, instructions/supervision, publication | List/filter, add/edit, publish/unpublish | Nonnegative fixed-precision cost; currency required with cost; unique valid topic links; one kit record reused across topics |

## Resource-specific fields

Image/diagram: file or supported URL, alt text and optional caption.
Audio/video: file or supported URL, optional captions/transcript where available.
Interactive experience: reviewed application experience or supported HTTPS URL; embedded/separate-page behavior defined by delivery policy, not arbitrary HTML returned by the model.
Accepted MIME types, upload limits and external providers are unresolved until Stage 9. Do not assume existing gravity-lab support allows arbitrary uploads.

## Scope details

- Excel preview is read-only with respect to curriculum; commit performs the catalogue write. Original file storage is separate from PostgreSQL rows.
- Import preview binds one selected curriculum and includes Domain and optional Category. Curriculum Code and required hierarchy values repeat on each row; reject mixed codes or a code mismatched to the selected curriculum_id. Learning Outcome is optional once per full Topic path, may be blank throughout, and conflicting nonblank values for one Topic are row errors. All selected sheets use the agreed headers. Category and Source URL can be blank; never create a synthetic category to fill a gap. Resource, teacher and kit selectors preserve full ancestor paths when displaying similarly named topics.
- Teacher profile administration supplies the eligible pool for MVP random teacher cards alongside resource recommendations. Server-resolved query subject must match explicit teacher subject expertise before random selection; Science queries show only Science teachers. Published/eligible records only; no matching teacher means no card. Display only approved public fields and distinguish declared/reviewed claims. No struggle detection, contact/enquiry, booking or payments. Card count/display frequency remain implementation choices.
- Kit cost is descriptive catalogue data, not a checkout total. Stock accounting, purchases and recommendations remain excluded.
- Topic visits and session counts describe activity, not completion, achievement or mastery.
- Member account/conversation deletion is a member lifecycle workflow, not an implicit admin permission.

## Integration sequencing

Agree forms and examples in Stage 1. Implement importer/schema in Stage 2, protected access in Stage 3, curriculum/student directory integration in Stage 4, activity/lifecycle in Stage 5, and resource/teacher/kit operations in Stage 9. The admin frontend can be developed against these contracts in parallel.

Curriculum is mandatory and dynamic. Use the existing Catalogue screen to create an empty draft curriculum (unique code, display name, optional description), then add levels/descendants manually or by import. No tenth admin screen is needed. Member selection exposes eligible published paths. Show curriculum in all path selectors, breadcrumbs and import history; similarly named paths in different curricula stay distinct. KG–5 Science is sample content, not a hardcoded restriction.
