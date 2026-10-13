# FLAME bulk import and export

Open the relevant `/admin` tab: **Resource Library**, **Teachers**, **Students**, or **Activity Kits**. Each offers **Import Excel / ZIP**, **Export Excel**, **Download template** and **Sample Excel**. Resources and Kits also offer **Export with media**.

## Prepare the workbook

1. Download the live template. Its `Paths` sheet contains current curriculum path IDs. Static samples intentionally contain no live IDs.
2. Fill `Records`. `record_key` is optional: leave it blank or omit the column and FLAME generates a stable key, shown in preview and exports. Explicit keys remain supported and should stay stable. New templates omit `existing_id`; exports retain it for precise matching of existing items. Repeated keys are consolidated additively; the first nonempty value wins.
3. For Excel mappings, enter your own matching `record_key` in Records and Mappings. Automatically generated keys cannot be referenced by blank mapping keys. Resources may leave Mappings empty and use Map topics after import; Kits still require a mapping. For Resources and Kits, fill `Mappings` with the record key and `topic_id`; optionally add `subtopic_id`. A topic-only link covers its subtopics. For Teachers, enter `subject_id` and optional `topic_id`. Kits require at least one mapping.
4. List cells accept `|` separators or a JSON string array such as `["English", "Tamil"]`. Exports use JSON arrays to preserve list values containing separators. Blank optional cells are allowed. Grade minimum and maximum must both be set or both blank; 0 means KG.
5. Upload, validate and preview. Correct all invalid rows, review matched IDs and preserved fields, then explicitly confirm. Publication is a separate action.

**Sample Kit:** replace `PASTE_TOPIC_ID_FROM_TEMPLATE` in its Mappings sheet before importing. Example profiles, addresses, videos and the blue-square image are test data, not approved teaching content. Replace them before using a real catalogue.

## Folder and ZIP structure

For external URLs, Teachers or Students, an Excel workbook alone is sufficient. For file-based media or kit images, zip the **contents** of the module folder, preserving relative paths:

```text
bulk-import-samples/
  resources/
    resources.xlsx
    assets/
      sample.png
  teachers/
    teachers.xlsx
  students/
    students.xlsx
  activity-kits/
    activity-kits.xlsx
    assets/
      sample.png
```

Inside `resources.zip`:

```text
resources.xlsx
assets/sample.png
assets/your-animation.gif
assets/your-lesson.mp4
```

Inside `activity-kits.zip`:

```text
activity-kits.xlsx
assets/sample.png
assets/your-kit-photo.jpg
```

Set `Records.file` to `assets/your-animation.gif` for a resource. Set `Records.image_files` to `assets/photo-one.png|assets/photo-two.jpg` for a kit. Do not place the workbook inside an extra parent folder in the ZIP. Do not include this README in the ZIP.

Ready-made ZIPs are in `packages/resources.zip` and `packages/activity-kits.zip`. The sample ZIPs include the sample workbook and original sample image. They demonstrate packaging. Kit mappings still need your current path ID.

## Duplicate and merge policy

- Match by `existing_id` first, then the saved `record_key`. Otherwise Resources match canonical URL/type or file-backed title/type, Students match email, and Teachers/Kits match exact trimmed names ignoring case. More than one existing match is invalid; specify an exact exported ID.
- Matching entries are shown in the preview. Existing nonempty scalar values, media references, availability, publication status, student email/status and expertise review status are preserved.
- Empty draft fields may be filled. Languages, kit materials and optional concept/synonym/purpose metadata may receive new values while keeping existing values. Existing grade ranges remain unchanged.
- Published Resource details/media are preserved entirely; valid mappings may be added. Published Teachers/Kits retain their status and still pass their existing validation rules.
- Mappings are added, never removed. Duplicate mappings and repeated Records keys are consolidated. Repeated imports and confirmed-request retries do not create duplicate catalogue entries.
- If a version or mapping changes after preview, nothing is applied. Select **Review latest comparison**, review the updated result and confirm again. Uploaded files are retained for that recovery.
- Cancel leaves the catalogue unchanged and removes only unused media staged by that import. Commit is atomic; invalid rows block the entire workbook.

## Students

Importing creates **pending profiles**, not authentication accounts, passwords, invitations, admin roles or curriculum membership. On the student's next verified sign-in, FLAME checks their confirmed email and provider identity before linking the pending profile and activating it. Existing students retain their identity, email, name and status unless their display name was empty. Administrator emails cannot be imported as students.

## Export and limits

- Excel export contains the whole module catalogue, not just the visible table page or active filters. Deleted resources and administrator profiles are excluded. It contains metadata, existing IDs, stable keys and mappings, but no passwords, tokens, private storage credentials or signed media URLs.
- Excel alone references local asset paths; choose **Export with media** to obtain those files for transfer elsewhere. Existing media in the same FLAME database does not need re-uploading during merge.
- Cross-environment transfer: clear `existing_id` if that ID does not exist at the destination, and replace mapping IDs with destination path IDs. Keep stable keys only when they identify the same real item.
- Imports: 2,000 Records rows, 10,000 Mappings rows; workbook 10 MiB; ZIP 120 MiB compressed, 200 MiB expanded, at most 250 entries. Existing per-file limits and GIF validation still apply. Kits accept up to five images.
- Exports: at most 5,000 records. Split exported rows and their mappings into import batches of at most 2,000 records if needed. ZIP exports support up to 200 files and the same byte limits. External videos are exported as validated URLs, never downloaded provider streams.
- Previews expire after 24 hours. Cancel expired previews and upload a fresh package. The operations cleanup command removes expired preview payloads and unused staged media; schedule it according to deployment retention rules.


## Resource Topic column

Download the current live Resource template. Records has an optional `topic` column immediately after `title`. Enter a readable grouping label, such as `Gravity`; use `Gravity|Force` for multiple labels. These labels are stored separately from curriculum associations and exported again. They do not automatically map resources, create topics, or grant learner visibility. Static older sample workbooks may omit this optional column; add `topic` or use the live template.

After importing, use the Resource Library Topic label filter to find the group, select those resources, and open Map selected topics for actual mapping or unmapping. The table places Topic between Resource and Media type. Topic labels can be edited on drafts, and are retained through metadata-only edits. Additive re-imports add labels to drafts while preserving existing ones; published metadata retains its existing import protection.


### Allowed preparation values

- purposes: explain, demonstrate, practise, human_help. Use | for multiple supported values or leave this optional cell blank. Verbs such as explore, discuss, compare, observe and investigate are not valid purpose categories.
- rights_basis: owned, licensed, permission only when actually verified; leave blank for an unreviewed draft. unknown is not a valid value. Publication still requires rights metadata.
- Interactive: file/external_url may be blank to create an HTML pending draft. Later open Edit and paste/upload HTML5. Preview and publication require actual media; a title/description alone is not executable media.

The confirmation checkbox stays disabled while any row is invalid. The preview identifies blocked confirmation and offers Show first invalid row. Correct the workbook/package, cancel the old preview and validate a new upload; existing keys/IDs and media remain preserved.


### Interactive drafts awaiting HTML

Use type=interactive and leave file/external_url blank when preparing the catalogue before the HTML is ready. FLAME imports the metadata as an unpublished HTML pending draft. Open its Edit action, paste code or upload one HTML file, and Save draft; then preview/publish when complete. Images/videos still require a media source. The exported status column may say draft; status/published/version are informational and cannot publish through import.
