# B13 — Additive catalogue import and export

Development delivery: 2026-10-07. Owner request: import/export Resources, Teachers, Students and Activity Kits, merge duplicates without overwriting existing data, and provide Excel samples and package folder instructions.

## Implemented flow

Each of the four admin tabs offers Import Excel / ZIP, Export Excel, Download template and Sample Excel. Resources and Kits also offer Export with media and Sample ZIP. Import uses upload → validation/preview → explicit confirmation → confirmed result/list refresh. Native dialogs support keyboard cancellation and narrow layouts; preview tables paginate thirty rows and scroll horizontally.

The shared `bulk_transfer` module coordinates the operation. It reuses catalogue schemas, resource file inspection/private storage, hierarchy validators, teacher expertise checks and kit publication requirements. Existing catalogue routes remain available. It does not add another recommendation or LLM call.

## Merge contract

- Match exact `existing_id`, then registered `record_key`, otherwise canonical resource URL/type or file-backed title/type, normalized student email, or trimmed/case-insensitive teacher/kit name. Multiple existing matches are rejected; use an exported ID. Matched IDs appear in preview for administrator review.
- Repeated keys and duplicate items inside one workbook consolidate; the first nonempty value is retained. Mappings deduplicate. Conflicting repeated keys that identify different existing items are invalid.
- Existing nonempty scalar values, media references, availability, publication states, student email/status and reviewed expertise are preserved. Empty draft details may be filled. Language/material/concept/purpose lists receive additions while retaining existing entries; grade ranges are filled only when unspecified.
- Published Resource media/details stay unchanged. Mapping additions are permitted and versioned. Published Teachers/Kits retain status and must satisfy their current validation rules after a merge.
- Mapping additions use valid current IDs, never create curriculum nodes, and never remove saved links. Existing links retained by an unchanged re-import are not treated as new paths.
- New Media, Teachers and Kits are drafts. New Students are pending profiles, not auth accounts or memberships. No passwords, invitations or roles are imported. A pending profile is claimed only after matching a confirmed email and independently verified provider identity. Email advisory locks serialize that claim with bulk profile imports. Inactive/removed profiles cannot be reactivated by import; administrator emails are excluded.

## Transactions and failure recovery

Migration `20261007_26` adds durable `bulk_imports` and `bulk_identities`; applied in development. Previews belong to one administrator. A current preview token, whole-item snapshot/versions, valid paths and explicit confirmation are checked again before application. External-video inspection is repeated at commit; only its volatile `verified_at` timestamp is excluded from comparison, while source identity, returned metadata, versions and saved values remain checked. A stale preview saves nothing and offers Review latest comparison; normalized workbook data and staged uploads are retained. Application is atomic. A locked completed job returns its saved receipt on retry, preventing duplicate creation.

Invalid rows block the entire workbook. No silent row skipping, destructive replacement, automatic publication or unsafe retry is performed. Cancellation deletes only staged, unused media; linked or directly shared/historical media is retained. Cancel does not remove catalogue entries. Previews expire after 24 hours. Run `scripts/cleanup_bulk_imports.py` operationally to purge expired payloads/receipts and unused staging files; deployment scheduling remains an operations task. For Vercel, October 14 private transfers now stage browser bytes directly in Supabase and return metadata-only preview receipts; stable IDs allow uncertain confirmation to replay the same preview. Private exports bypass Function payload limits. `scripts/purge_transfer_artifacts.py` dry-runs cleanup of expired transport staging/exports, separately from bulk preview retention. See [hosting guide](../VERCEL-DEPLOYMENT.md).

## Export and sample files

Excel exports the entire module catalogue, rather than a table page/filter. It includes stable keys, existing IDs, metadata and mappings, with informational publication/version/status fields. These fields cannot change publication or access on import. Student exports exclude administrator profiles. Tokens, passwords, auth subjects, signed delivery URLs and storage credentials are not exported.

Resources and Kits can export a ZIP containing the workbook and original stored media bytes. External provider videos remain URLs; FLAME does not download/extract their streams. Downloads use the authenticated BFF with private/no-store headers. Source/playback policy stays with the existing resource APIs.

See [sample folder guide](../bulk-import-samples/README.md). Four `.xlsx` samples and two media packages exist in `project-stages/bulk-import-samples`, with public copies for download from `/admin`. Workbooks were authored, inspected and rendered with the Spreadsheets skill/artifact tool. Runtime-generated templates/exports use the application's existing Python Excel stack. Static samples contain example data; download the live template for current path IDs. The Kit placeholder mapping must be replaced before import.

## Limits

- 2,000 import record rows / 10,000 mapping rows; 10 MiB workbook; 120 MiB compressed ZIP / 200 MiB expanded / 250 entries. Paths must be relative under assets; unsafe, duplicate, encrypted or symlink ZIP entries and formula cells are rejected. Actual file content and existing per-file limits are checked, including GIF animation validation.
- 5,000 export records; package export up to 200 media files and the same byte limits. Split large exports into import batches. JSON list exports preserve literal separators. Existing media can be merged without re-uploading it.
- Work is synchronous and bounded. Maximum-size production/storage/provider throughput was not load-tested; begin with small batches and measure before increasing deployment limits. Large uploads may take longer, and timeouts require checking the persisted job before retrying confirmation. The October 14 direct-transfer adapter retains the ticket for the selected File and retries the same preview ID after an uncertain confirmation; a page reload discards that in-memory ticket. Unused staging is handled by cancellation/expiry cleanup.

## Verification evidence

- Affected backend suite: 18 tests passed across bulk transfer, identity, catalogues, mapping/deletion and MVP recommendations. Subsequent bulk/auth rerun: 14 passed; final duplicate-key and cancellation/verified-identity checks passed after their targeted refinements. Three additional merge-limit cases, the sample-decoding case and a fresh external-video inspection timestamp regression passed; oversized additive lists are blocked without changing existing values.
- Coverage includes all four add/merge/export flows, preserved scalar/media fields, multiple mapping additions, repeated keys/natural duplicates, committed receipt replay, stale preview recovery, invalid-row atomicity, published-resource mapping without unpublishing, safe ZIP/formula handling, cancellation cleanup, owner isolation and verified pending-profile activation.
- Four generated sample workbooks decode with the actual importer. Generated workbook XML without dimension metadata is supported. Sample sheets and guides were visually reviewed; ZIP bytes contain the original sample image.
- 17 web unit tests and production build/typecheck passed. `bulk-transfer-browser.cjs` passed four-tab controls, binary BFF downloads, preview confirmation, duplicate-click protection, stale comparison recovery, success refresh, cancellation/Escape and 390px layout.
- Existing Resource Library browser suite passed on rerun. Its first run timed out at the dynamically generated WebM playback fixture; product playback code was unchanged. Existing media/mapping/deletion/GIF/external-video flows passed on rerun. This fixture sensitivity is not a production performance result.
- Alembic check: no new upgrade operations. No real users, invitations, curriculum publications, permanent fixture catalogue entries, paid provider/model calls or deployment were performed.

## Repeatable verification / operations

From `development/apps/flame-api`:

```powershell
$env:FLAME_RUN_DB_TESTS='1'
.\.venv\Scripts\python.exe -m pytest tests/test_bulk_transfer.py tests/test_identity.py tests/test_b9_catalogues.py tests/test_resource_mapping_deletion.py tests/test_mvp_recommendations.py -q --tb=short
.\.venv\Scripts\python.exe -m alembic check
```

From `development/apps/web`: `npm run test:unit`, `npm run build`, `node tests/bulk-transfer-browser.cjs`, `node tests/resource-library-browser.cjs`.

Operations: `python scripts/cleanup_bulk_imports.py` from the backend environment removes expired records/staging only. Schedule it externally; it was not run against existing development data during this delivery.

API restarted after migration and implementation; health returns 200 and the seven bulk route patterns are registered.

## Changed files

- Backend: `app/modules/bulk_transfer/{models,workbooks,service,router,errors}.py`, module registration in `app/main.py` and `migrations/env.py`, migration `20261007_26_bulk_transfer.py`, safe bulk error handler, pending-profile identity linking/helper and admin student listing/detail changes, cleanup script, `tests/test_bulk_transfer.py`.
- Web: `bulk-transfer.tsx`, Resource/Teacher/Kit/Student admin panel integration, `admin.css`, B9 BFF upload/download allowlist and bulk timeout handling, `bulk-transfer-browser.cjs`, public sample files.
- Documents/assets: sample workbooks, original sample PNGs, ZIP packages, folder README, tracker and project context. Builder/visual evidence remains under `work/bulk-sample-builder`; browser evidence under `work/bulk-transfer-narrow.png`.

## Remaining boundaries

Student invitation/provisioning, CSV import, destructive updates/replacement, batch auto-publication and curriculum import are not part of this additive transfer. Larger asynchronous jobs, cross-environment ID remapping and production load/retention scheduling need further work. Existing B5 operations, B8 educator review, B9.11 private-storage/content acceptance and B10 release gates remain open. Static sample media and example profiles are not educator-approved content.


### Automatic bulk import record keys and simplified templates — 2026-10-09

Records.record_key is now optional, including omission of the column. The decoder/preview generates a kind-scoped deterministic SHA-256 alias for identifiable rows using existing ID, resource type/source URL or title, student email, or teacher/kit name. Explicit keys are preserved; generated keys remain in the normalized preview payload, identities, confirmation receipt and exports. Identical identifying input produces the same key, independent of worksheet row number. Natural-match ambiguity/deletion/version/access checks and additive-only merge policy remain authoritative. Blank mappings are not guessed: Excel mapping rows still require a matching Records key; resources may import unmapped and use the UI mapping dialog. Kits retain their mandatory mapping rule.

New live preparation templates omit existing_id and informational publication/version/status columns; record_key remains as an optional column for pre-upload mapping. Existing exported/legacy workbooks with IDs are still accepted, and exports preserve existing_id for precise, ambiguity-safe re-import. No catalogue IDs, identity rows or saved user keys were deleted. UI, generated Guide and both package README copies explain the distinction.

Source: bulk_transfer/workbooks.py, service.py, router.py; frontend bulk-transfer.tsx; tests/test_bulk_transfer.py and package guides. Verification: 17 backend bulk tests passed using rollback-only database fixtures, covering four-kind omitted/blank/explicit keys, simplified template versus export IDs, actionable keyless mapping errors, automatic-key resource preview/review/commit/re-import/export, and previous merge/conflict/security/retention rules. Production frontend build/TypeScript and four-module bulk-transfer browser suite passed. No schema migration or real catalogue import/publication; tracker counts/statuses unchanged.


### Resource Topic preparation labels, table column and filter — 2026-10-09

Added optional Records.topic immediately after title in live resource templates/exports. A value such as Gravity, or Gravity|Force (JSON arrays also supported), is stored as learning_metadata.topic_labels in the existing JSONB metadata. Labels group imports and never resolve/create curriculum nodes or associations. No database schema migration is required. Labels are validated (20 labels, 255 characters each), preserved in exports and metadata-only edits, and use the existing additive draft/publication-preservation policy on re-import.

Resource Library adds Topic between Resource and Media type, displaying labels or Not specified; actual mapping columns remain separate. Topic label search filters saved resources server-side before count/pagination using case-insensitive literal matching. It combines with existing library filters and does not affect saved mappings. Selected resources can then use existing bulk mapping/unmapping. Draft editor exposes Topic labels alongside Title. Shared metadata form retains labels on edits; recommendation selection does not use grouping labels as concept evidence. Generated workbook Guide and both package README copies updated; older static samples remain compatible and can add the optional topic header or use the live template.

Sources: learning_metadata.py, bulk_transfer/workbooks.py/service.py/router.py, resources/router.py, learning-metadata-editor.tsx, resource-panel.tsx, admin.css, backend bulk tests and resource-bulk browser tests. Final production build/TypeScript passed; six focused backend checks passed, including rollback-only import/filter/export and no implicit mapping. Expanded bulk browser suite passed Topic column order, full-library label counts across pagination, case-insensitive grouping, metadata-only label retention, plus existing mapping/unmapping/retry/publication/delete and narrow layouts. Screenshot inspected: work/resource-topic-column.png. No real catalogue writes/publication or tracker count/status changes.


### Mixed media workbook lifecycle and invalid-preview crash — 2026-10-11

Owner reported exporting existing media, adding 20 rows without keys/IDs and re-importing, with Runtime TypeError reading length in BulkTransfer. Confirmed root cause of the UI crash: invalid preview entries do not acquire preserved_fields in the planner, and response() omitted that field, while the renderer assumed the array existed. Backend response now consistently supplies errors/preserved_fields/fields_to_fill and mapping counts; frontend normalizes older saved previews and blocks invalid-row confirmation. Malformed responses produce an actionable status message without claiming that nothing was saved. The underlying workbook validation error is now visible; no user workbook was attached, so its exact row-level cause is not asserted. Missing new file assets and orphan partial mapping rows receive clearer package/partial-workbook instructions.

Added [media management lifecycle guide](../MEDIA-MANAGEMENT-LIFECYCLE.md). Preserving old record keys/IDs while leaving both blank on new entries is supported. Partial workbooks do not delete omitted resources/links. New file additions need their assets in a ZIP; existing media references need not be bundled again. Interactive-only packages use the same single-document validation. Existing import remains additive: nonempty detail/media replacement uses the Edit UI, not an overwrite import mode.

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

### Google Sheets manual resource sync — 2026-10-11

Implemented the agreed Image / Video / Interactive tabs workflow through existing additive bulk import. Mapping remains in FLAME. Includes three-tab template, service-account setup status, tab/column errors and optional warnings, conflicting-value review, explicit confirmation, stable developer-metadata row identity, automatic keys/IDs written back after durable catalogue commit, pending write-back retry/replay and reopen recovery. Existing authentication, CSRF, validation, version checks, publication and mappings preserved. No schema migration. Pending receipts excluded from expiry cleanup.

Status: implementation and isolated verification complete; live Google setup/verification pending because credentials and spreadsheet access are not supplied. See GOOGLE-SHEETS-RESOURCE-SYNC.md for setup, changed files, limits and verification. Stage totals unchanged.

