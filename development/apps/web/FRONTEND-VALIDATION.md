# Frontend validation — Stage 8

Completed locally on 20 September 2026 using Microsoft Edge (Chromium) on Windows.

## Student hierarchy regression — 26 September 2026

The local six-level curriculum hierarchy, hidden Category context, required Subtopic selection, full-path Library merging and published-tree adapter passed 11 unit tests, TypeScript checking and a production build. The browser suite passed its 14 axe accessibility audits and 15 viewport cases, including 320px width, against the development server. These checks cover local behavior and adapter shape; authenticated catalogue and student membership requests remain for B3/B4/F3.4. No curriculum data was permanently imported into Supabase by this UI change.
## Result

Stages 1–8 of the frontend implementation are complete for local review. This validates the frontend with local fixtures and unavailable-service responses; it does not validate or implement backend APIs, authentication, a database, uploads, transcription or live AI.

## Fixes made during Stage 8

- Darkened muted text, proficiency labels, composer captions and placeholder text to address contrast failures while preserving the existing theme.
- Prevented resizing into tablet layout from automatically opening navigation over a resource viewer or conversation.
- Updated regression checks to use the current tablet rail and remembered sidebar preference.
- Added repeatable unit and UI test commands.

## Executed checks

| Area | Evidence |
| --- | --- |
| Data logic | Eight unit tests passed: immutable path merging, partial branches, deduplication, progress preservation, attachment limits/types and resource URL/catalog handling. |
| Conversations | Rich content and MathML, independent mode/context drafts, retry without duplicate turns, original attachment snapshots and per-context reading positions passed. |
| Composer | Growing text, attachments and previews, invalid files, synthetic microphone recording, stop/cancel, context switching, denied/late permission cleanup and unsupported recording passed. Touch emulation verified Enter adds a newline and the send button submits. |
| Curriculum and Library | Additions, searches/filters, whole-curriculum and subject confirmation/cancellation, re-add progress/draft restoration, empty curricula and isolated subject restoration passed. |
| Resources | Diagram, narration, animation, transcripts/caption tracks, simulation results, detail categories, loading failure/retry, focus return and media cleanup passed. |
| Navigation | Logo loading, rail actions, My Learning routing, preference restoration, blocked-storage fallback, mobile drawer and keyboard close passed. |
| Responsive | 1920, 1440, 1280, 1100, 1024, 900, 768, 600, 430, 390, 360 and 320px widths at 900px height; also 390×430, 768×430 and 320×568. Composer bounds and horizontal overflow passed. |
| Accessibility | Fourteen axe scans using WCAG 2 A/AA, 2.1 AA and 2.2 AA rule tags reported zero violations in tested states. Keyboard checks covered skip link, focus containment/return, nested Library/removal dialogs and Escape. Framework development tooling was excluded from app scans. |
| Production | Build/type checking passed. Production preview returned HTTP 200, excluded the development response fixture, retained unavailable requests, passed an additional accessibility scan, and supported tablet rail/nested Library without runtime errors. |

Desktop and narrow mobile screenshots were visually inspected. Local reports/screenshots are in E:/FLAME/.kilo/ui-check/stage8 (ignored test artifacts).

Automated accessibility scans are not a full accessibility certification.

## Repeat the checks

From development/apps/web:

~~~powershell
npm run test:unit
npm run typecheck
npm run build
~~~

The UI suite requires an already running development server (npm run dev), installed Microsoft Edge, and temporary audit packages outside the application dependencies:

~~~powershell
npm install --prefix ../../../.kilo/ui-check --no-save playwright @axe-core/playwright
npm run test:ui
~~~

Optional environment variables: FLAME_UI_URL changes the server URL; FLAME_UI_TOOLS points to the audit tools' node_modules directory.

tests/frontend-browser.cjs checks the integrated flows, fourteen accessibility states and fifteen viewport cases. Additional local regression scripts for recording, resources, subject removal and the rail live in the ignored .kilo/ui-check folder.

## Device and integration limits

- Real iOS/Android keyboards, physical microphones and mobile browser permission dialogs were not tested on hardware. Mobile layout/touch checks used browser emulation; microphone checks used synthetic input.
- VoiceOver/NVDA listening and Safari/Firefox compatibility were not verified. These remain checks before public release.
- Learning data, progress, drafts, history and removal archives are in memory until refresh. Only the sidebar layout preference persists locally.
- Library error/retry UI exists, but a failing real catalog service cannot be validated until that service is connected.
- Live AI, authentication, backend persistence, uploads and transcription need a separate integration phase.
