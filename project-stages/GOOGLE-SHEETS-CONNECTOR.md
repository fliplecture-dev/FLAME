# Saved Google Sheets resource connector

Implemented 2026-10-12. This supersedes the initial identifiers-only write-back behaviour. The connection is stored in FLAME rather than relying on browser storage. Each sync remains manual and requires Validate and preview → Confirm. There is no automatic background polling or automatic deletion.

## Workflow

1. Share one spreadsheet with the configured service account as Editor. Keep Image, Video and Interactive tabs using the FLAME template headers.
2. Enter its URL once and choose Validate and preview sync. FLAME saves the administrator-owned connection and restores it when the panel is reopened, including in another browser.
3. On the first sync, new sheet rows are proposed as FLAME drafts and FLAME library resources missing from Sheets are proposed as exports to their media-type tab. Identifiers and row metadata establish a baseline only after successful write-back.
4. Subsequent previews show new incoming rows, unchanged/merged resources, FLAME resources to append, matched sheet fields that will receive FLAME data, and previously linked rows removed from Sheets.
5. Review the comparison and confirm sheet updates. If removed rows exist, separately confirm deletion of the exact listed resource IDs. FLAME uses its existing version-checked deletion workflow: mappings are removed, publication is cleared, media and historical references remain, and admin recovery is not available.
6. The FLAME transaction commits first. Google receives resource metadata and identifiers. Failures show Saved in FLAME — sheet update pending. Retry resumes the saved operation without re-importing, repeating deletions, or duplicating previously appended rows.

## Authority and conflicts

Existing nonempty FLAME resource values remain authoritative under the agreed additive import policy. Incoming new rows and permitted blank-field/list additions use the existing importer. This is not unrestricted two-way overwriting of existing FLAME metadata. Differing matched-row sheet values are displayed and, after explicit confirmation, replaced by reviewed FLAME values.

Curriculum mappings stay inside FLAME; this connector does not export or replace mappings. File bytes, HTML source and private storage paths are not transferred through Sheets. Uploaded assets remain in FLAME; existing resource IDs retain their sources when URL/file cells are blank. Interactive drafts can receive HTML later in the editor. Grade, rights, publication and access rules remain unchanged.

## Deletion safeguards

Automatic column upgrade: confirmed write-back now appends sync_action if it is missing, preserving existing column order/content and adding a dropdown/header note. Existing rows receive sync or deleted as appropriate. Retry accepts exactly that appended header and does not add duplicates after a partial provider failure. Preview only warns about the addition; no column is added until confirmation.

Deletion upgrade (2026-10-12): the optional `sync_action` column now accepts blank/sync, delete, and FLAME-written deleted. Explicit delete requests retain their row and identifiers, require separate confirmation, and receive a deleted receipt after write-back. Resources deleted in Resource Library are also mirrored to retained linked Sheet rows on the next confirmed sync. Deleted rows are excluded from imports and can later be removed without recreating or re-deleting resources. Duplicate tracking is repaired only where saved identity is unambiguous and after confirmation; ambiguous cases remain blocked. See [deletion workflow](RESOURCE-DELETION-WORKFLOW.md).

- Only identities from a previously successful sync can be treated as removed. Missing resources on an initial link are exported, not deleted.
- All three tabs must be present with valid headers. Missing tabs, extra columns, oversized/incomplete reads, invalid rows and ambiguous tracking block confirmation; they never imply deletion.
- Used rows are read fully before enforcing the 2,000-row cap. Moving a row outside the allowed range causes an error, not false removal.
- Clearing IDs on a tracked row retains its established resource identity. A conflicting replacement ID or wrong media-type tab is invalid.
- A row with lost metadata but a retained resource ID/key is flagged as ambiguous, not removed.
- Sheet contents and catalogue state are rechecked at confirmation. Versions, deletion dependencies, connection ownership and preview token are enforced server-side, including through the generic bulk endpoint.
- Cancellation leaves the catalogue unchanged. Before deletion, administrators see resources and dependencies and must confirm their exact IDs.
- FLAME and Google are separate systems. The final read/write window cannot exclude an external collaborator's simultaneous structural edit. Avoid editing/rearranging columns while sync runs. Detected changes require a fresh preview or restoring the pending source. Google append and its tracking metadata use one atomic batch, so response-loss retries can recognize already appended rows.

## Persistence and API

### Sheet cell types

Sync writes grade_min, grade_max and version as numbers, and published as a boolean. This avoids forced-text apostrophe markers and numeric validation errors. Existing matched rows are rewritten with these types on the next confirmed sync, as are new exports. Record keys, UUIDs, URLs and authored content remain literal text; no apostrophe is prepended, and actual apostrophes in content are preserved. Formula execution remains disabled. Numeric/boolean representation changes alone do not count as metadata conflicts.

Migration `20261012_30` adds `flame.google_sheet_connections`: spreadsheet identity, owner, successful row bindings and last-sync time. Applied in development. Existing BulkImport receipts hold snapshots/outgoing actions and durable pending updates. No media, curriculum or recommendation model changes.

`GET /api/v1/admin/bulk/google-sheets/connections` returns the signed-in administrator's saved connections and pending sync. Preview, commit and write-back endpoints retain existing authentication/CSRF protections. Other administrators cannot take over a linked spreadsheet. Existing identifiers-only receipts remain retryable.

Changed files: bulk_transfer/models.py, google_router.py, google_sheets.py, router.py, new sheet_connector.py; resource/router.py shared deletion helper; migration 30; web google-sheets-sync.tsx and BFF route allowlist; backend connector tests and browser regression. Root tracker and guides record this refinement.

## Verification scope

Rollback-only fixtures and mocked Google transport cover initial export, repeated sync, persistent connection retrieval, new rows, FLAME edits reaching Sheets, removed row preview, denied deletion without exact confirmation, confirmed deletion/replay, retained mappings on unchanged resources, failure/retry and missing/oversized tabs. Existing resource mapping/deletion regression passed after sharing the deletion helper. Production build and TypeScript passed. Browser regression checks warnings, conflicts, pending-update recovery, invalid rows, cancellation/mobile and separate deletion confirmation.

No live spreadsheet has been synchronized by these tests. Live Sheets permissions, structural-edit behaviour and provider data require testing with the user's spreadsheet URL. No real resources were deleted by verification.

Final verification: 9 connector/Sheets tests passed; 4 connector plus existing mapping/deletion tests passed; expanded browser regression passed including separate deletion confirmation/cancellation. Production build and TypeScript passed. Migration 30 is applied locally. Credential setup already exists, but a live spreadsheet URL is still needed to verify actual Google read/write access.

