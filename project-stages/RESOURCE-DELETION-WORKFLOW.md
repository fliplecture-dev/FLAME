# Resource deletion: Google Sheets and FLAME

Implemented 2026-10-12. Deletion is reviewed and version checked. The resource is withdrawn and its curriculum mappings removed; its file, metadata snapshot and historical references are retained. There is no storage purge or admin restore operation in this workflow.

## Delete using Google Sheets

1. Run a confirmed sync once. FLAME automatically adds `sync_action` to each Image, Video and Interactive tab if missing, with a dropdown and header note. Preview warns about the planned column addition; cancellation does not add it. The three-tab template also includes it.
2. Keep the row's `record_key` and `existing_id`. Set `sync_action` to `delete`. A title alone cannot identify a resource for deletion.
3. Open FLAME Admin → Resource Library → Sync Google Sheets → Validate and preview sync. If an old preview is open, choose Validate again.
4. Review **Delete requested linked resources**, including mappings/history dependencies. Tick the separate exact-resource deletion confirmation and the general sync confirmation, then Confirm sync.
5. After successful write-back, FLAME writes `sync_action=deleted`, `status=deleted` where that column exists, and `published=FALSE`, while preserving IDs and descriptive metadata. The row remains as a deletion receipt and cannot recreate the resource during a later sync.

| sync_action | Meaning |
| --- | --- |
| Blank or sync | Normal reviewed additive sync. A resource already deleted in FLAME remains deleted. |
| delete | Request deletion of an identified existing resource. Separate confirmation required. |
| deleted | FLAME's completed-deletion marker. Setting this on an active resource is rejected; use delete. |

You may remove a completed deleted row from Sheets after its write-back succeeds. This does not trigger a second deletion. Removing a previously linked active row is still supported as a deletion proposal, but keeping the row and using delete is easier to review and avoids losing its identifiers. Never delete the media tabs or headers to request deletion.

## Delete inside FLAME

1. In Resource Library, use the resource's Delete action, or select rows and choose **Delete selected**.
2. Review affected mappings and historical references, and complete the existing deletion confirmation.
3. Open Sync Google Sheets and obtain a fresh preview. Previously linked rows for these resources appear under **Update deleted rows in Sheets**.
4. Confirm sync. Their retained Sheet rows are marked deleted rather than imported again. A resource deleted before ever being linked will not be exported.

This is a manual connector. Resource Library deletion does not immediately edit Google Sheets.

## Tracking conflicts and retries

When duplicate hidden markers refer to the same identity, or saved bindings plus the surviving row's key/ID identify exactly one valid marker, preview can select the correct marker and warn about redundant markers. Only a confirmed sync removes the redundant tracking entries; it does not delete Sheet rows. Unknown or conflicting identities remain blocked. The implementation uses Google's [developer-metadata deletion request](https://developers.google.com/workspace/sheets/api/reference/rest/v4/spreadsheets/request#DeleteDeveloperMetadataRequest) filtered by metadata ID.

Changes to Sheet content/tracking or FLAME versions after preview require revalidation. Missing tabs, invalid identifiers, wrong media-type tabs and copied/conflicting keys never authorize deletion. Duplicate requests for the same resource are rejected. Existing FLAME ownership/authentication and the exact deletion-ID consent remain enforced.

If the FLAME transaction succeeds but Google write-back fails, use **Retry sheet update**. The saved deletion is retained, and retry writes the same deleted receipt without repeating the deletion or adding a replacement resource. Avoid editing the affected rows during a pending write-back.

## Verification

Eleven existing connector/Sheets tests passed. Two new tests passed: rollback-only explicit-delete/FLAME-delete/confirmation/change/cancel/write-failure/retry/repeat/receipt-removal/rejection lifecycle, and deterministic duplicate-marker selection versus ambiguity rejection. The deletion test verifies mappings are removed while resource/history metadata are retained. Production build/TypeScript and the expanded Sheets browser suite passed, including separate deletion consent, already-deleted row review, pending-write recovery, cancellation and mobile layout. API/database health passed.

A live read of the linked Sheet succeeded and reported zero redundant tracking markers at verification time. Verification did not delete live catalogue data, alter live Sheet values or execute a live marker repair. No schema migration was needed.
