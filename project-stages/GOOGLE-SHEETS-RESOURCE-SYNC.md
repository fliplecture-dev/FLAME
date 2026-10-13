# Google Sheets resource sync

Implemented 2026-10-11. Manual additive sync is available in **Resource Library → Sync Google Sheets**. Live Google verification requires server configuration and a shared spreadsheet. No existing resource or curriculum schema migration is required.

## Setup

1. Enable Google Sheets API in your Google Cloud project.
2. Create a service account and obtain its JSON credentials. Store the JSON outside the repository and web/public folders, readable only by the backend service. Do not paste it into the application, chat, or spreadsheet.
3. Set `FLAME_GOOGLE_SHEETS_CREDENTIALS_FILE` in the API environment to the absolute credential-file path. Restart the API. Install backend dependencies from pyproject.toml (google-auth with requests transport is added).
4. Download **three-tab template** from the sync dialog, open it in Google Sheets, and keep tabs **Image**, **Video**, **Interactive**. The optional Guide tab is ignored.
5. The dialog displays the configured service-account email. Share only the intended spreadsheet with that account as **Editor**. There is no domain-wide delegation or Drive discovery.
6. Enter the spreadsheet URL or ID, validate, review, and explicitly confirm.

Google's service-account authorization and row metadata APIs are documented at [service account OAuth](https://developers.google.com/identity/protocols/oauth2/service-account) and [developer metadata](https://developers.google.com/workspace/sheets/api/guides/metadata).

## Column contract

Use exact resource-template names. `record_key`, `existing_id`, and `title` columns must exist; identifier cells can be blank. The tab determines `image`, `video`, or `interactive`; optional `type` cells must agree. Unknown/duplicate columns and missing required columns block the preview, with tab/column-specific messages. Missing optional columns produce warnings. Formulas are rejected; paste plain values. Up to 2,000 total resource rows, 60 columns, and 12 MiB Google responses are supported.

Other columns include `topic` (organizational label), `external_url`, description/accessibility/rights fields, concepts/synonyms, grade ranges, teaching_languages and purposes. Existing informational publication/version/status columns do not publish or overwrite status. This sync has no Mappings tab: existing associations are retained and managed exclusively in FLAME's individual/bulk mapping controls.

New Image and Video rows require a validated supported URL. This integration does not download local file paths, Google Drive assets, arbitrary media URLs, or embedded HTML from Sheets. Use Excel/ZIP or the resource editor for uploaded media. Existing media can be retained by record key/ID with source cells blank. New Interactive rows can omit media and remain HTML-pending drafts; paste/upload HTML in FLAME later.

## Save and identity flow

- Preview reads only the named three tabs. It reserves random developer metadata on rows to track them independently of titles and row numbers; preview cancellation leaves this harmless tracking metadata in Sheets.
- Blank keys use a stable `gs-` alias derived from the row marker. Existing IDs/keys use the existing bulk matching rules; ambiguous matches are invalid.
- Preview reports new/merge/unchanged/invalid rows and conflicting fields that will remain unchanged. New records are drafts. Existing nonempty values, media, availability, publication and mappings remain under the existing additive rules. Lists on drafts can be extended; published media/details remain unchanged.
- Confirmation re-reads the sheet and checks source contents, headers, marker identity, owner, catalogue snapshot and versions. Invalid rows block the whole sync; cancel and correct/re-preview rather than silently skipping them. Removing a sheet row does not delete a FLAME resource.
- Catalogue changes commit in FLAME first. Identifiers are then written using developer-metadata row filters with RAW values; non-identifier cells are represented as null and skipped.
- Google failure leaves **Saved in FLAME — sheet update pending**. The receipt is durable and the retry action writes identifiers without re-importing resources. Completed retries are idempotent. Pending receipts are excluded from bulk cleanup. Closing/reopening the dialog restores pending work in this browser.
- Write-back retries reject changed content/columns/identifiers or deleted/moved-to-another-tab source rows. Restore the original source or resolve it in a fresh sync. FLAME data is retained.

## Boundaries and limitations

This is Sheets-to-FLAME import with identifier write-back, not full two-way editing, automatic scheduling, deletion reconciliation, or Google OAuth account linking. Updates made inside FLAME do not rewrite sheet descriptions/titles. Different nonempty values are flagged and preserved, not overwritten.

Do not edit/rearrange sheet columns during an active sync. Source rechecks detect changes before operations, and row metadata avoids stale row-number writes, but Google and PostgreSQL cannot participate in one atomic transaction or lock out a collaborator editing in the final read/write interval. A fresh sync is required after detected source changes. A partial API write response or response loss can be retried idempotently. Credential revocation/quota/network issues leave FLAME data intact.

## Implementation files

- `development/apps/flame-api/app/modules/bulk_transfer/google_sheets.py`: bounded Google transport, row tracking, schema issues, conflict detection, source recheck and identifier writes.
- `development/apps/flame-api/app/modules/bulk_transfer/google_router.py`: admin setup/template/preview/confirm/write-back endpoints.
- `bulk_transfer/router.py`: existing owner/version/atomic catalogue workflow extended to Sheets receipts.
- `core/config.py`, `main.py`, `pyproject.toml`, `.env.example`: configuration, routing, dependency.
- `scripts/cleanup_bulk_imports.py`: preserves pending identifier receipts.
- `development/apps/web/src/features/curriculum/google-sheets-sync.tsx`, `resource-panel.tsx`, `src/app/api/b9/[...path]/route.ts`: admin UI and existing session/CSRF BFF.
- `tests/test_google_sheets_sync.py`, `development/apps/web/tests/google-sheets-browser.cjs`: isolated verification.

## Verification

Production build and TypeScript passed. Browser suite passed setup-required state, configured email, column warnings, conflict display, disabled confirmation, success, pending write-back, reopening/retry without another commit, invalid rows, cancellation, no browser runtime errors, and mobile fit. Backend rollback tests verify three families, pending Interactive drafts, repeat sync, stable aliases, identifier write-back failure/retry, source edits, reordered rows, conflicts, preserved publication/mappings, deleted-sheet-row retention, invalid confirmation, cancellation and template/configuration. Google transport contract tests cover row metadata search.

All Google responses in automated lifecycle tests were isolated fixtures. Live credentials/permissions/quota/write-back have not been verified; no user spreadsheet was changed and no real resource was imported by these tests.

Final verification: 26 bulk/Sheets regression tests passed, then all 6 Sheets tests passed after the final transport/identifier confirmation refinements. Production build and final TypeScript check passed; isolated browser suite passed. Live localhost admin dialog verified the service-account setup-required message and disabled sync until configured. Screenshot: work/google-sheets-live-setup.jpg. No live Google credentials were present.


## Superseding update — 2026-10-12

The saved connector now persists links in FLAME, exports resource metadata (not just identifiers), and detects removed linked sheet rows with separately confirmed resource deletion. Earlier statements about identifiers-only write-back and no deletion apply to legacy imports. Full current policy, safeguards and verification: [Saved connector](GOOGLE-SHEETS-CONNECTOR.md).

