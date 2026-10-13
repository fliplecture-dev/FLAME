# Resource Library bulk media lifecycle

Updated: 2026-10-11.

## Choose the operation

| Scenario | Records keys / IDs | What to upload | Effect |
|---|---|---|---|
| New external videos | Leave new record_key and existing_id blank | resources.xlsx, supported URLs in external_url | Generate keys, validate sources, save drafts |
| New images/videos/HTML5 | Leave new keys and IDs blank | ZIP containing resources.xlsx and referenced assets/ files | Generate keys, validate/store media, save drafts |
| Export plus 20 new rows | Preserve existing keys/IDs; blank both on new rows | XLSX for URL-only additions; ZIP for new files | Existing records preserved, new rows added |
| Unchanged full re-import | Keep exported keys and IDs | Exported workbook; existing media need not be bundled again | Existing rows unchanged |
| Partial import | Only chosen Records, with their matching Mappings rows | Workbook or ZIP for newly added files | Omitted resources and mappings remain saved |
| Interactive metadata first | type=interactive; leave source blank | resources.xlsx | Save HTML pending drafts; paste/upload HTML in Edit later |
| Interactive-only batch | type=interactive, file=assets/name.html | ZIP with those HTML files and resources.xlsx | Same validation/save workflow as other uploaded media |
| Edit existing nonempty details or replace media | Use existing resource Edit action | Resource editor, including Code/Preview for HTML5 | Version-checked edit; unpublish first when required |
| Add mappings | Existing keys if prepared in Excel, or Resource Library selection | Mappings sheet or Map selected topics | Adds valid associations |
| Remove mappings / delete / publish | Use explicit Resource Library actions | Reviewed and confirmed UI action | Import does not perform these actions |

## Mixed export and additions

1. Export Excel. Keep the Records, Mappings, Paths and Guide sheet names/headers.
2. Preserve record_key and existing_id on old rows. Do not reuse these identifiers on new rows.
3. Add new rows with blank keys and IDs, a title, type and a supported media source. Topic is an optional grouping label; it creates no association.
4. If the new rows refer to files, prepare a ZIP. Only newly added files are required; exported existing file references resolve through the retained resource ID/key.
5. Existing Mappings rows can remain when their Records rows remain. For new automatically keyed records, leave mappings empty and map them in FLAME after import. Supply your own readable keys only when preparing their Mappings in advance.
6. Validate and preview. Invalid rows block the whole import; read the displayed Excel row errors before confirming.
7. Confirm once, review the receipt, then filter by Topic label and use the bulk mapping dialog. Publish separately.

```text
resources.zip
  resources.xlsx
  assets/
    force.png
    gravity.mp4
    gravity-lab.html
```

Use assets/gravity-lab.html in Records.file, not a Windows absolute path. Each Interactive is one complete UTF-8 HTML/HTM document up to 2 MiB, with inline CSS/JavaScript and embedded assets. Preserve the original file; no ZIP of a multi-file interactive application is supported.

## Editing versus additive import

The current importer deliberately preserves existing nonempty values and media. Editing a description in an exported workbook does not overwrite its saved nonempty description. Empty draft fields can be filled; draft metadata lists and mappings can receive additions. Published media/details retain their values. Use the Edit resource screen for actual replacement, unpublish if required, save as draft and publish explicitly. Overwrite mode is not implemented.

## Partial workbook rules

Remove unwanted Records rows and their Mappings rows together. A mapping key absent from the partial Records sheet is rejected rather than guessed or silently discarded. Leaving a resource or mapping out of the workbook never deletes it. Removing a link requires the mapping dialog; deletion requires confirmation.

## Failure recovery

- Invalid rows: the preview should remain visible with row-level errors and disabled confirmation. Cancel, correct the workbook/package and upload again.
- Missing new assets: use a ZIP with resources.xlsx at the root and matching assets/ paths. Existing retained media do not need re-upload.
- Stale comparison: Review latest comparison, inspect changes, confirm again. Keep the existing uploaded job; do not create a duplicate job merely to retry.
- Lost completion response: inspect the import receipt/status. Confirm retries are idempotent.
- A saved review may resume after refresh; old preview rows missing optional arrays are normalized safely.
- Learning space unavailable is a separate catalogue/session-loading error; it does not establish a workbook key error. Retry after API readiness recovers; persistent cases need request diagnostics.

## Verification

Rollback-only regression passed: initial resource import/export, mixed old row plus 20 automatically keyed HTML additions, missing-file preview errors with complete response arrays, confirmed mixed ZIP, unchanged full re-import, partial Interactive-only import, retained omitted records, confirmation replay, and additive metadata preservation. Browser regression passed legacy invalid preview rendering, blocked confirm, reload/resume and cancellation plus the four catalogue import/export flows. No real catalogue entries were added by these tests.
