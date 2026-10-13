# Video thumbnails and Browse Media opening — 9 October 2026

Implemented under existing F9/F10/B9/B14 work; release acceptance remains open.

Explore thumbnail areas are accessible buttons, including icon fallbacks. Pointer click or Enter/Space uses the same scoped open-item flow as Open media; browsing/loading a thumbnail does not create an open/activity event. Existing Open media buttons remain. Curiosity thumbnails retain their per-item matched path.

YouTube uses verified provider thumbnail metadata; older metadata without an image gets a thumbnail derived from its validated video ID. Provider URLs are restricted to existing YouTube/Vimeo image hosts. Frontend images use no-referrer. Provider image failures show the existing fallback icon. Uploaded video thumbnails are private PNG/JPEG/WebP uploads; no public storage key is returned.

Resource Library Video editors support thumbnail upload, local/saved preview, replacement and removal. Saved thumbnail uploads reuse existing administrator ownership and retained ResourceUpload records. Replacing/removing a thumbnail is a versioned resource edit and requires an unpublished resource. MP4/WebM publication requires an uploaded static thumbnail; incomplete drafts can still be saved. GIF keeps its existing animation policy. Provider video thumbnails load automatically and can be overridden with an uploaded image. Existing published records are not automatically edited or withdrawn.

Migration `20261009_28` adds nullable `resources.thumbnail_storage_key`, following `20261008_27`; applied to the development database, drift check clean. No original file, association or publication change. Read-only inspection found zero existing uploaded MP4/WebM records requiring remediation.

## Contract and delivery

- Admin create/edit accepts optional `thumbnail_upload_id`; PATCH null removes it. Only Video can attach static images. Upload ownership, image MIME and reused-upload conflicts are checked transactionally.
- Admin responses include `has_thumbnail` and `thumbnail_upload_id`. Member/Explore cards include `has_thumbnail` and a safe provider `thumbnail_url`; private custom thumbnails resolve through authorized delivery.
- Member `resources/{id}/delivery?thumbnail=true` retains published availability, mapped path/revision, version and grade/language checks. Private images use five-minute signing. Local content selects the thumbnail only with `thumbnail=true` and a signature bound to its actual key; changing the flag does not reuse the video signature. Local withdrawal blocks existing content links; cloud revocation follows the existing five-minute URL policy.
- Admin `preview?thumbnail=true` and protected local `preview-content?thumbnail=true` provide saved draft previews. Native learner video delivery includes `poster_url`, used by the player before playback.
- Additive bulk imports retain existing thumbnails and do not import thumbnail files; attach new imported-video thumbnails through Resource Library before publishing. Existing import schemas/export package formats remain unchanged.

## Source ownership

Backend: resource models/router/service/member router/storage, new `resources/thumbnails.py`, safe provider metadata fallback, Explore item DTO and domain error messages. Bulk transfer excludes the new admin-only upload field from its existing normalized payload. Frontend: Explore thumbnail/workspace, scoped thumbnail-button styles, Resource Library thumbnail fields and native-video poster support. Tests: `test_video_thumbnails.py`, extended Explore and Interactive browser suites.

## Verification

40 focused backend checks passed with development database integration enabled: thumbnail ownership/publication/signed content/withdrawal, Interactive, media-family and provider regressions. Final thumbnail checks also passed after adding removal/republication coverage. Another 15 bulk-import/B9 resource checks passed (55 unique focused backend checks across these runs). Production build/TypeScript passed. Explore browser suite passed thumbnail loading, pointer/keyboard opening and existing Study/Curiosity/scoped-path/mobile flows. Interactive browser suite passed saved uploaded-video thumbnail management alongside existing Image/Video/Interactive/fullscreen checks. Current API on 8001 exposes the thumbnail query and readiness returned database OK.

Repeat from flame-api with `FLAME_RUN_DB_TESTS=1`: `.venv/Scripts/python.exe -m pytest tests/test_video_thumbnails.py tests/test_interactive_media.py tests/test_media_families.py tests/test_external_video.py -q`. From web: `npm run build`, then sequentially `node tests/explore-browser.cjs` and `node tests/interactive-browser.cjs`. Migration drift: `.venv/Scripts/python.exe -m alembic check`.

Live private-cloud thumbnail upload/signing, actual mobile/device accessibility and release acceptance remain B9.11/B10. Provider images can be unavailable; their fallback remains clickable. No paid model request or deployment. Reversal of content is the existing unpublish/edit workflow; do not downgrade the thumbnail column after saving real thumbnail data without a reviewed retention plan.
