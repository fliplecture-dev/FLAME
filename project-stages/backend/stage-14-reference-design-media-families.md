# Reference design and three media families — 2026-10-08

Owner update supersedes the earlier seven media-type choices. This is a refinement of F10/B14 and the existing B9/F9 Resource Library, not a new recommendation platform.

## Design

The learner workspace uses a full-width header with the existing FLAME brand, Learn, Curiosity, My Learning, Explore and authenticated profile actions. Existing Pinned/Recent/My Learning navigation remains accessible. The reference's unsupported Home/Practice functions, invented student name, mastery or content are not added.

Blue question bubbles, white rounded explanation cards, a decorative flame marker, blue send/Explore actions, soft blue backgrounds and a two-column Explore card grid follow the reference. Existing curriculum titles, recommendations and viewers remain functional. At narrow widths the existing mode/navigation controls and modal Explore drawer are used. Admin Resource Library shares the palette while retaining its compact forms, mapping dialog and table.

## Classification and source

| Active family | Includes | Source / playback |
| --- | --- | --- |
| Image (`image`) | Images and diagrams | Existing approved image upload/URL delivery and accessible image viewer |
| Video (`video`) | Uploaded video, animation/GIF, YouTube and Vimeo | Upload or YouTube/Vimeo URL source choice; actual MIME/provider metadata determines GIF, native video or provider playback |
| Interactive (`interactive`) | Existing approved interactive content | Existing validated HTTPS source and reviewed launch policy |

Forms, management filters, Explore chips/selectors and exports use these three families. GIF retains `image/gif`, original animated bytes, meaningful description, Play/Pause and reduced-motion behaviour even though its family is Video. External video is a source, not another family. New MP3/M4A resource uploads and audio resource creation are rejected. Conversation attachment/voice capability policies are unchanged.

Old `diagram`, `animation` and `external_video` inputs normalize to Image/Video at API/ORM boundaries for compatibility with existing integrations and workbook samples. New stored records use only the three active values. Existing stored decisions are not rewritten; legacy presentation aliases remain readable.

Migration `20261008_27` is applied and Alembic drift check is clean. It preserves IDs, mappings, storage/source, provider metadata, publication and versions for the reclassified resources. It stores prior classification metadata for rollback. GIF upload metadata becomes Video. Legacy audio, if present in another database, is retained with its IDs/files/mappings but becomes unavailable and unpublished; it is excluded from active library/export and cannot be newly created/published. No files or historical records are deleted.

Actual development data before migration: 10 External video, 2 Image, no Audio. Afterwards: 10 Video, 2 Image; all ten provider metadata objects retained and zero publication-state differences against the migration snapshot. No curriculum or association mutation was performed.

## Main changed files

- Learner: `student-app-shell.tsx`, `explore-workspace.tsx`, `catalogue-recommendations.tsx`, `student.css`.
- Admin: `resource-panel.tsx`, `resource-library-ui.tsx`, `resource-mapping-dialog.tsx`, `external-video-info.tsx`, `admin.css`.
- API: resource validation/models/router/service/candidates/member delivery/external-video policy; recommendation GIF visual detection; bulk import provider handling and export exclusion; safe error wording.
- Database: `migrations/versions/20261008_27_media_families.py`.
- Tests: `test_media_families.py`, updated Resource Library browser expectations for Video plus source selection.

## Verification

Recorded: typecheck/production build and 17 web units passed; 63 affected backend tests passed with database checks enabled, plus three focused family/alias/GIF/audio/provider tests. Alembic check reports no new upgrade operations. Explore and sidebar browser suites passed; the conversation image/GIF/native/external video and kit/tutor regression suite passed using provider SDK fixtures. Resource Library suite verifies Video source selection, GIF saving, mapping, version/retry behaviour, publication and provider metadata.

Desktop/narrow screenshots in `work/explore-desktop.png` and `work/explore-mobile.png` were inspected. Source URL/provider verification and learner access rules remain unchanged. No live provider certification, physical-device/screen-reader certification or deployment is claimed; existing B9.11/F8/B10 gates remain.

## Runtime handoff

The existing local backend process does not reload code automatically. A previous automatic approval review rejected stopping that process (blocked by policy), so it is still running. Restart the backend manually to load the canonical-type/provider handling; otherwise its old code cannot correctly interpret the migrated Video provider records. Restart the frontend if it is running `next start`; `next dev` normally refreshes source changes.

Backend command after stopping the old instance:

```powershell
cd E:\FLAME\development\apps\flame-api
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-access-log
```

No API keys or authentication settings need changing.

## Five annotation refinements — 2026-10-08

Learn/Curiosity/My Learning now align beside the profile at the right of the top header. Explore moves to the far right of the curriculum breadcrumb row, with horizontal breadcrumb scrolling preserving its visibility on compact screens. Inside Explore, search precedes the media category chips; a keyboard-accessible filter icon beside the chips toggles the learning-path controls with aria-expanded/controls. One labelled refresh icon beside the dropdowns refreshes paths and results, preserves selections, prevents duplicate refresh requests and clears recovered errors. Compact accessible error text remains; the separate error-action block is removed. Reduced-motion preferences disable the refresh animation.

Changes are limited to student-app-shell.tsx, explore-workspace.tsx, student.css and the Explore browser assertions. No API, database, media taxonomy or recommendation changes. Header/tool order/alignment and recovery are checked at the annotated 1090/1588 widths and the existing 390px drawer layout; typecheck/production build and sidebar regression checks pass. Screenshots: work/annotations-header-1090.png and work/explore-desktop.png.

## Header and Explore simplification — 2026-10-08

Latest owner annotations remove the top-header Learn/Curiosity/My Learning buttons and the duplicate Explore media-type/language/refresh row. The brand and account controls remain in the header; Explore stays opposite the breadcrumb. Study/Curiosity and My Learning remain in sidebar/compact/mobile navigation. Media category chips are the only media-type selector in Explore; path filtering and search remain. Language filtering is no longer sent by this UI; metadata and other API consumers remain unchanged. Removed refresh-icon instructions; errors now explain that closing/reopening Explore retries with latest paths. Reopening invalidates cached lists, and a previous error triggers the existing published-path reload without a new toolbar control.

Typecheck, production build, Explore browser and sidebar suites passed. Browser assertions verify removed controls, preserved search/chips/path filters, stale-path recovery on reopening, viewers, desktop/1090px/mobile layouts, pin/recent/My Learning and keyboard behaviour. No backend/database change. Earlier five-annotation header/dropdown placement notes are superseded by this owner instruction.

### Explore text/action removal — 2026-10-08

Latest owner annotations remove the Explore path text (including the empty-path placeholder), the entire Return to current topic / Clear filters action row, and the Select a curriculum, grade and topic prompt. Search, category chips, path filter icon/controls, eligibility and current-context initialization remain. No new placeholder replaces the removed prompt. Typecheck, production build and existing Explore browser flow passed; mobile path selection now uses the existing filter controls. No backend/database changes or tracker count/status changes.

## Runtime recovery superseding the earlier restart blocker — 2026-10-08

The old API on 8000 still had no Explore route. To avoid stopping the protected process, the updated API was started on 127.0.0.1:8001 with reload and the frontend local FLAME_API_URL was changed to match. Next dev loaded the environment update. The user's existing signed-in browser visibly returned ten Grade 1 Gravity videos; no re-upload, remapping or republication. Screenshot: work/gravity-videos-live.png. Launch current API with the same normal command but `--port 8001 --reload` if restarting. The earlier manual-restart requirement is resolved for current frontend routing; the old idle process remains on 8000. Source-code and catalogue data were not altered in this recovery.


### Reference navigation shell refinement — 2026-10-09

Learner UI only: centered Study/Curiosity segmented switch with a keyboard-accessible mode dropdown, full-height collapsible left sidebar/compact rail, mobile navigation drawer, and account/admin/sign-out controls at the bottom. Existing profile popover opens upward; its local-workspace fallback now links to the existing sign-in route. FLAME branding is in navigation; Explore remains opposite the context breadcrumb. Neutral page/sidebar surfaces and centered empty workspace match the supplied desktop/mobile references; the mobile composer remains at the bottom. Existing selection handlers, conversations, pins/recent, hierarchy, learning progress, recommendation/Explore and authentication APIs remain unchanged. Desktop navigation changes at 1100px, mobile drawer at 768px, and Explore retains its existing 1280px breakpoint. No backend or database changes. Production build, TypeScript, Explore and sidebar browser suites passed; live desktop expanded/compact, mobile drawer/account placement and dropdown keyboard checks completed. Evidence: work/reference-shell-desktop.png, work/reference-shell-desktop-compact.png, work/reference-shell-mobile.png, work/reference-shell-mobile-navigation.png. Files: student-app-shell.tsx, mode-switcher.tsx, student-profile.tsx, student.css. No tracker count/status changes.


### Annotated FLAME menu and Explore edge action — 2026-10-09

Owner corrections supersede the earlier centered-mode dropdown: the top Study/Curiosity tabs now have no menu/arrow. Sidebar, compact rail and mobile drawer branding use plain FLAME with a mode dropdown, reusing the same Study/Curiosity handlers. Removed logo/tagline from these navigation headers. Explore is a fixed middle-right edge action, outside the breadcrumb header; at desktop pane widths its open action sits on the pane boundary. Existing close control and Escape slide the panel back toward the right before closing the native dialog after 220ms. Pending requests are invalidated immediately, close timers cancel on intentional reopening and unmount, focus returns after closing, and reduced-motion users skip animation/delay. The mobile modal and desktop browsing/reflow contracts remain.

Verification: production build/TypeScript, Explore and sidebar regression suites passed. Expanded Explore checks cover no dropdown in the centered switch, keyboard switching through the FLAME menu, edge-action geometry, close-animation state and reduced-motion completion, plus prior Study/Curiosity/combined-path, pin/recent/My Learning and responsive behaviour. Live signed-in UI checked at the annotated desktop width; screenshot work/flame-menu-edge-explore.png. No backend/database changes or tracker count/status changes.


### Explore breadcrumb alignment and single toggle — 2026-10-09

Latest owner refinement replaces the middle-right edge handle: closed Explore is inline at the opposite end of the curriculum/grade/topic breadcrumb row. A single Explore toggle is rendered: in the context header while closed, or in the drawer header while open, keeping it operable in the mobile native modal. Removed the separate X close action. The button has no independent movement; drawer header, toggle and contents share the panel's slide transform without a delayed opacity fade. Existing 220ms close completion, immediate request invalidation, Escape, reduced-motion handling, and browsing state remain. Focus restoration now occurs after native dialog closing and after the header toggle has remounted. Live Grade 1 Gravity listing/toggle verified; screenshots work/explore-breadcrumb-toggle.png and work/explore-single-toggle-open.png. No backend/database changes or tracker status/count changes.

Verification for the single-toggle refinement: final production build/TypeScript and expanded Explore browser suite passed, including restored breadcrumb alignment, one toggle, focus return after closing, animation/reduced-motion completion and existing Study/Curiosity browsing.


### Explore attached chevron and panel top alignment — 2026-10-09

Explore now uses an accessible icon-only left chevron in the hierarchy row while closed. The same toggle becomes a right chevron attached to the panel's upper-left edge while open and moves with the panel's single slide transform. Panel top is measured from the hierarchy-row button and recalculated on header/window resize; it never rises above that button. Desktop pane offset/height and mobile modal inset/height use this measured anchor; narrow layouts reserve 40px so the attached chevron remains visible and clickable. Study/Curiosity/media/teacher/kit APIs and browsing behaviour are unchanged. Production build/TypeScript and expanded Explore browser regression suite passed, including direction icons, panel/chevron top alignment, toggle/focus, animation/reduced motion and existing responsive browsing. Live Grade 1 Gravity verified with panelTop=chevronTop=70px. Screenshot: work/explore-chevron-panel.png. Tracker counts/statuses unchanged.


### Desktop resizable learning panes — 2026-10-09

Added pointer-captured vertical edge dividers for desktop navigation and Explore. Sidebar width ranges from 220–520px; Explore ranges from 300–760px, constrained by available space to preserve a 400px study area. Arrow keys adjust widths (Shift for larger steps), Home/End use limits, and double-click resets. Widths persist locally across reloads. CSS clamps preferences after viewport changes; tablet/mobile layouts remain unchanged. Navigation resize is enabled with the existing desktop sidebar at 1100px+, and Explore resizing is enabled only in its three-pane desktop layout at 1280px+. Dividers do not take layout width and do not trigger catalogue fetches or alter learning context. A ResizeObserver keeps accessible width values synchronized; pointer completion/cancellation removes drag styling.

Production build/TypeScript and expanded Explore browser regression suite passed. Checks exercise real mouse drags on both edges, study minimum width, no extra listing requests, saved widths in a newly loaded browser page, keyboard resizing, double-click reset, drag cleanup, and hidden mobile separators alongside existing Study/Curiosity/viewer flows. Live desktop values verified: navigation 328px, study 712px, Explore 548px. Screenshot: work/desktop-resizable-panes.png. Source: desktop-pane-resizer.tsx, student-app-shell.tsx, explore-workspace.tsx, student.css and explore-browser.cjs. No backend/database changes or tracker status/count changes.


### Resource Library bulk selection and actions — 2026-10-09

Added a leading row checkbox and mixed-state page checkbox to the saved resource table, Select this page, Deselect this page and Clear selection. Selection is keyed by resource ID and persists across library searches, hierarchy filters and pagination. Bulk Map topics, Publish, Unpublish and Delete open a review dialog. The dialog fetches current resource versions; mapping adds selected valid topic/subtopic paths while preserving existing links and publication status. Mapping selections persist across path searches/pages. Each mutation uses existing authorization, validation, concurrency and deletion APIs. Already-matching publication/mapping states are skipped; duplicate submissions are guarded. Successful resources are deselected and the library refreshed; failures remain selected with individual errors/request references and require explicit latest-version review before retry. Operations are per resource, not an atomic transaction over the entire selection.

Delete requires explicit confirmation after reviewing resource titles, mappings and dependencies. Existing backend deletion rules retain shared media and historical records; deletion cannot be undone in the admin UI. No real catalogue records were modified for testing. Source: resource-panel.tsx, new resource-bulk-dialog.tsx, admin.css and new tests/resource-bulk-browser.cjs.

Verification: final production build/TypeScript passed. Isolated bulk browser suite passed 32-record page/search selection, deselection/clear, additive mapping/cancel, published mapping without status changes, path search/page selection, duplicate-click prevention, partial publication failure with review/retry, already-published skip, unpublish preserving associations, delete cancellation/confirmation/dependency information/stale-version retry and narrow-screen layout. Screenshot inspected: work/resource-bulk-library.png. The broader existing resource-library suite timed out at its generated native WebM Play video fixture before bulk verification; it is not recorded as passing. Backend APIs/schema and existing tracker status totals are unchanged.


### Bulk mapping dialog refinement — 2026-10-09

Owner requested a wider mapping dialog, existing-mapping checkboxes, select/deselect all, and faster topic loading. Dialog width now caps at 1120px with responsive hierarchy wrapping and compact resource review. Paths mapped to all reviewed resources are checked; paths mapped to some are mixed, with saved per-resource counts. Explicit checking adds to all; explicit unchecking removes from all. Untouched mappings are preserved. Select/deselect all targets every matching path across pagination, with visible count and scope. Pending map/unmap summaries preserve edits across filters, searches and explicit latest-version recovery. Published status and existing authorization/concurrency checks remain unchanged. This supersedes the previous additive-only bulk mapping behaviour; unmapping is now explicitly supported.

Confirmed client loading cause: sequentially reviewing every resource delayed starting the hierarchy request. Hierarchy now starts immediately and independently; resource version reviews use at most four concurrent reads per review run. Late results from closed/replaced reviews are discarded, and Apply stays blocked until current version review and hierarchy retrieval succeed. Mutation requests remain sequential. Indexed path labels avoid repeated full-list lookup for large selection summaries.

Verification: production build/TypeScript and expanded isolated resource-bulk browser suite passed. Added checks for prechecked shared mappings, mixed partial mappings, published mapping/unmapping, filtered select/deselect across all pages (112 paths), preserved untouched links, bounded review concurrency and hierarchy retrieval before review completion, plus 1120px desktop and 390px dialog fit. Existing bulk partial failures/version retry/cancel/double-click/delete tests passed. Screenshot inspected: work/resource-bulk-mapping-wide.png. No live catalogue mutation, backend/schema change or tracker total/status promotion.


### Bulk mapping status and review filters — 2026-10-09

Added filters beside the bulk path checkbox: Saved mapping status (All, Mapped to any resource, Mapped to all resources, Partially mapped, Unmapped in all resources), Path type (Topic-wide/Subtopic/All), and Pending changes (All/All pending/Will map/Will unmap). Saved status counts direct associations across the currently reviewed resources, separately from pending checkbox edits; inherited subtopic coverage remains explained and is not mislabeled as a direct link. All filters combine with search/hierarchy and apply before pagination. Select/deselect all is scoped to every matching path across pages. Clear path filters resets browsing only and preserves map/unmap edits. Shows matching count and actionable empty state; no additional API requests are made for filter changes.

Production build/TypeScript and expanded isolated bulk browser suite passed. Filter regression verifies any/all/partial/unmapped counts for two resources, topic/subtopic combinations, pending-unmap review, zero-match messaging, stable saved-state results during edits, preservation on filter clearing, and existing concurrency/retry/mapping/deletion flows. Desktop mapping screenshot inspected; 390px dialog fit passed. Sources: resource-bulk-dialog.tsx, admin.css, tests/resource-bulk-browser.cjs. No live resource mutations, backend/schema changes or tracker count/status changes.
