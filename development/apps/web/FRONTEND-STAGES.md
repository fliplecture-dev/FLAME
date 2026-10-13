# Student frontend redesign

Historical delivery notes for the original eight local UI stages. Current frontend/backend status and remaining integration/admin work are maintained only in [STAGES-STEPS.md](../../../project-stages/STAGES-STEPS.md). Older “Stage 8 pending” entries below are historical; FRONTEND-VALIDATION.md records its subsequent local completion.

Primary visual reference: `../../../Ref UI/Sample_2.png`.
Brand: FLAME, with a smaller “by FlipLecture” endorsement. Use the original logo asset.

## Student hierarchy update — 26 September 2026

The current local My Learning tree and Library follow Curriculum → Level → Subject → Domain → Topic → Subtopic. Students select a Subtopic for Study. Category is absent from student rows, filters and breadcrumbs; its ID remains attached to each Topic and passes through the Study request context for exact ancestry and later LLM routing. Every published Topic must contain a Subtopic. The adapter in `src/features/curriculum/map-published-curriculum.ts` flattens both categorized and uncategorized backend Topic branches into the visible Domain → Topic list without dropping category identity. Search, progress filters, selection keys and Library merges follow the complete path. Local fixtures remain illustrative; live catalogue and membership integration belongs to B3/B4/F3.4.

The earlier Stage 3 and Stage 4 prose below documents the original local implementation; this update supersedes its shorter chapter/concept labels and optional leaf behavior. The 26 September checks are in FRONTEND-VALIDATION.md.
## Delivery checkpoints

1. Design foundation and responsive app layout — completed.
2. Study/Curiosity modes; Pinned, Recent, sidebar profile behavior — completed.
3. Curriculum → subject → topic group → concept hierarchy, progress and filtering — completed.
4. Add from Library; search, filters, partial branch merging and duplicate prevention — completed.
5. Learning workspace; rich responses, breadcrumbs and state handling — completed.
6. Contextual prompt; draft preservation, attachments and microphone interaction — completed.
7. Contextual learning resources and on-demand media — completed.
8. Frontend integration, accessibility, responsive layouts and quality checks — completed locally; see FRONTEND-VALIDATION.md for device/integration limits.

Stage 1 replaces the earlier green/serif design with a neutral sidebar, sans-serif typography, outline icons, a bounded reading column and compact bottom composer. Existing topic selection, search, proficiency display and explicit unavailable-service handling are retained. No fictitious account name is displayed.

All eight frontend stages are implemented, including the subsequent logo, icon rail, My Learning routing, and curriculum/subject removal refinements. Local curriculum and scores remain development data. Backend behavior is outside this frontend redesign.

Stage 8 validation is recorded in FRONTEND-VALIDATION.md. Earlier sections describe each stage's delivery scope.

## Stage 2

Study and Curiosity share the shell, with mode controls available in the sidebar and mobile/collapsed workspace header. Curiosity hides the academic tree and sends a typed request with no topic ID. Study retains its selected topic. Drafts and request displays are retained separately by context in memory.

Pinned and Recent contain actual visited contexts, not fictitious notes. Pin/unpin is available in the workspace and sidebar; recent entries are deduplicated and limited to eight. Curiosity currently uses one exploration workspace; separate conversation history belongs to the conversation implementation stage. The profile panel describes the local session honestly; account integration is not present. Refresh clears this frontend session.

Validated mode/draft isolation, pin/unpin, recent navigation, profile Escape, responsive drawer, and production build.

## Stage 3

My Learning now renders curricula/grades, subjects, chapters and concepts. Higher-level percentages are supplied data; concept proficiency remains 0–10. The small CBSE Grade 5 / Tamil Nadu Grade 6 dataset is illustrative development data, not official board coverage or actual student progress. The same concept ID may appear on different curriculum paths; view/session identity includes every parent ID.

All/In Progress/Mastered/Not Started filters preserve ancestors and do not recalculate aggregate progress. Review-due concepts are included in In Progress. Search and filters combine; clearing restores the full hierarchy. Expand/collapse controls operate on visible branches. Opening a pinned or recent context clears filters and reveals its complete path. Tree state is shared between desktop/mobile and retained across mode changes.

Study requests now carry curriculum, grade, subject, chapter, topic and underlying concept IDs. Curiosity requests carry no academic context. Breadcrumbs and prompt placeholders reflect the selected path. Backend policies, library addition and hierarchy merging are unchanged and remain outside this stage.

Validated production build; filters, empty-state reset, search, expand/collapse, full breadcrumbs, pin path restoration, draft isolation across curricula, and all nine specified viewport widths.

## Stage 4

The My Learning + control opens Add from Library. Curriculum, Subject and Topic tabs have active-tab search and grade/board filters, plus subject and chapter filters when applicable. Topic results distinguish full chapters from individual concepts. The catalog is a small separate local fixture, loaded through the service boundary, with loading/error/retry and empty states.

Additions merge immutably by IDs within each parent path. Existing progress and student fields win; only missing nodes are added. A concept creates just its ancestors, and later subject/curriculum additions fill missing descendants. Added indicators require the entire selected path to exist. Successful additions clear navigation filters and expand their branches. Nothing is posted to an invented endpoint; additions last for this tab session and reset on refresh.

Desktop uses a centered dialog; mobile uses a full-screen sheet above the navigation drawer. Escape, close, focus return, keyboard tabs and focus containment are supported.

Validation: production build and TypeScript; browser concept/subject/curriculum additions, duplicate indicators, search/filter/reset, desktop/mobile and Escape restoration. Pure merge tests run with `node --test tests/merge-learning-path.test.cjs` on Node 22.13+; cover input immutability, partial branches, stable-ID deduplication, progress preservation and repeat additions.

## Stage 5

The learning workspace now stores a sequence of question/response turns for every full Study path and for Curiosity. Changing topic or mode restores that context’s conversation, draft, and reading position. Requests include completed prior turns as structured history through the frontend service boundary. State remains in memory until refresh because persistence and backend conversation APIs are not connected.

The response renderer supports trusted typed blocks for headings, paragraphs, ordered/unordered lists, accessible tables, native MathML formulas, callouts, reviewed images/diagrams, captioned video, and HTTPS or local resource links. It renders plain strings through React and rejects unsupported resource schemes; it does not render raw generated HTML. Gravity includes a clearly labelled development-only static response so the rich layout can be reviewed without pretending the AI is connected. The preview is excluded from production builds.

Each question is kept as a conversation turn. Pending, unavailable-service, and unexpected-error states appear in the response position. Retry replaces the failed state on the same turn and retains its original request/context, avoiding duplicate questions. The composer keeps text for unavailable/error results and clears it only after an actual available response.

The content viewport scrolls independently while the prompt remains accessible. It follows new content only when the reader is already near the end, keeps the reading position when new content arrives above the fold, restores a separate position per learning context, and offers Jump to latest when needed. Mobile breadcrumbs shorten to subject and concept while desktop shows the full curriculum path.

Validation: production build and TypeScript passed. Browser checks covered rich blocks and MathML, per-context conversation and draft isolation, unavailable retry without duplicated turns, scroll restoration, reading-position preservation, Jump to latest, mobile breadcrumb reduction, prompt visibility, and horizontal overflow.

## Stage 6

The bottom composer grows automatically with multiline text, up to a capped height. Desktop Enter sends, Shift+Enter inserts a newline, and touch devices keep Enter for newlines. IME composition does not submit. File, image, microphone and send controls remain visible, and blank requests require either text or an attachment.

File/image pickers support PNG/JPEG/WebP/GIF, PDF, TXT/Markdown, CSV, XLS/XLSX, DOCX, and supported audio formats. Files are validated locally: up to 5 per draft, 10 MB each and 25 MB combined. Empty files, unsupported types, duplicate files and oversize selections show a message; valid files in a mixed selection are retained. These are frontend selection limits, not a substitute for server validation. Images have local previews; other files show names/sizes; audio has local playback. Remove controls are available before sending. Object URLs are created only by preview components and revoked when those previews unmount.

The microphone uses MediaRecorder after explicit user interaction. Stop attaches a voice note, Cancel discards it, and a two-minute limit stops recording. Switching context stops and saves an active recording to its original context. Delayed permission requests that are cancelled or unmounted release any subsequently granted stream. Stop, cancel, errors and unmount stop microphone tracks. Permission denial, missing/busy devices and unsupported recording environments have readable messages. No speech transcription is performed.

Text, files and recordings are stored per Study path or Curiosity session in memory. Attachment-only requests are supported. Each submitted turn retains its original attachment snapshot, so removing a draft attachment cannot change the original question or its retry. Successful responses would remove only the submitted draft files and preserve newer files/text; unavailable/error responses keep the draft. The current service always reports unavailable and performs no upload or file processing. A future BFF adapter must serialize/upload the File payloads rather than blindly JSON-encoding browser File objects. Refresh clears this local session.

The app uses dynamic height, visual viewport resizing, safe-area padding, and a content-resizing viewport hint. The composer caps attachment and text scrolling independently to keep controls visible at narrow/short sizes.

Validation: production build/TypeScript; attachment validation tests (`node --test tests/prompt-attachments.test.cjs`); browser text growth, files/images, draft isolation, attachment-only send, retry snapshots, recording/stop/cancel, context-switch cleanup, permission denial, late permission cancellation, and narrow/short viewport checks. Audio tests used a synthetic browser microphone. Actual phone keyboards and physical microphone hardware remain device checks for the final validation stage.


## Stage 7

Responses can now carry typed resource recommendations through the learning service, conversation state, and response renderer. Supported types include images, diagrams, audio, video, animations, approved simulations, activities, experiments, books, kits, tutors and classes. Three compact cards appear initially; Explore more reveals the remaining resources. Empty lists render no recommendation section.

Resources open on demand in a native modal dialog, with a full-screen mobile layout, accessible names, keyboard focus wrapping, Escape/close and focus return. Images include alternative text and captions. Audio/video use native controls without autoplay; supplied transcripts and caption tracks are supported. Loading failures offer retry. Closing removes the media and simulation, stops playback and keeps the conversation/draft intact.

Interactive embeds resolve only from the application-owned catalog and run in a sandboxed iframe with scripts but without same-origin access. The included gravity lab compares a two-metre fall on Earth and the Moon using a simplified no-air-resistance model. Detail resources render plain text and optional validated HTTPS/local links in a new tab. No purchases, booking, or progress updates are performed.

The development-only Gravity preview includes an original SVG diagram, local synthetic narration, a silent canvas-generated WebM animation with captions, the gravity lab, and clearly labelled activity/detail examples. These recommendations are static fixtures, not AI output or real tutor/book/class listings. Production response resources require the future service integration. Packaged sample assets remain public static files. No new runtime dependency was added.

Validation: production build and TypeScript; resource URL/catalog tests; browser checks for cards/expansion, images, audio/video metadata and playback, transcripts/captions, Earth/Moon simulation results, every detail category, failed-resource retry, focus return/wrapping, playback cleanup, retained draft, and 768/390/320px viewers. Desktop and mobile screenshots were reviewed. Full application/device/accessibility integration review remains Stage 8.

## Curriculum and subject removal (before Stage 8)

My Learning offers removal on curriculum and subject rows. The Library offers the same actions in its Curriculum and Subject tabs, including partially added branches. Every removal opens the shared confirmation dialog with Cancel initially focused. Cancel and Escape leave state unchanged; Remove executes the action. Chapters and concepts have no individual removal action. Subject removal affects only its curriculum path. Removed branches clear matching selections and pinned/recent shortcuts; other learning remains unchanged. An empty curriculum remains visible after removing its last subject.

Removed curriculum and subject snapshots are retained in memory. Add from Library restores applicable saved snapshots before merging catalog additions, preserving progress and topics. Restoring one subject in an active curriculum does not restore unrelated removed subjects. Consumed snapshots are cleared to avoid later additions resurrecting stale branches. Conversation drafts/history stay keyed by their original context and return when that topic is selected again. This is tab-session behavior only; refresh clears local changes. The dialog states this limitation. Permanent retention requires backend persistence.

Validated confirmation, Cancel, Escape, focus wrapping, subject/curriculum removal and restoration through both interfaces, preserved progress/drafts, and protected topic rows. Dialogs were checked at desktop, tablet, 390px and 320px mobile sizes, including above the Library and mobile drawer. TypeScript and production build passed. Stage 8 remains pending.
## Compact navigation and logo update (before Stage 8)

My Learning rail behavior: opens and focuses the existing curriculum tree (expanded sidebar on desktop, navigation overlay on tablet), switching to Study when necessary. It preserves selected topics, tree expansion and drafts. Add from Library is opened through the + in My Learning. Verified on desktop and 1024px/768px tablet layouts.

The supplied Logo_Horizontal v1.png is used across the sidebar, tablet/mobile drawer and mobile header, with a quieter by FlipLecture endorsement. The source image is copied unchanged; the compact rail displays only its flame mark using CSS clipping.

Desktop (1100px+) can collapse the sidebar into a 68px icon rail. Tablet (768–1099px) uses the rail with an expandable modal navigation overlay. Mobile retains its existing drawer. The rail provides expand, Study, Curiosity, Library and profile controls, with accessible names, hover/focus labels and active mode styling. The sidebar preference is saved in localStorage; navigation continues working when browser storage is blocked. Topic selection, tree expansion and drafts are preserved across collapse/expand. Only the layout preference persists across refresh; learning state remains in memory.

Validated desktop/tablet/mobile controls, mode/draft isolation, Library/profile access, preference restoration, blocked-storage fallback, keyboard close, logo loading and horizontal overflow. Production build and TypeScript passed. Stage 8 and the optional Undo/partial-addition refinements remain pending.
