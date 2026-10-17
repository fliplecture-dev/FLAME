Current access-policy update: see [user access and profiles](USER-ACCESS-PROFILES.md) for guest Curiosity, calendar-day limits, optional phone, `/profile` and migration 32 activation. Owner-approved development Supabase activation now includes migrations 31/32 (head 20261017_32, clean drift), with nine rollback-only PostgreSQL/grant checks passing and local 8000/3000 readiness verified. Earlier sign-in-only and source-only migration evidence below is historical.

# Fliplecture discovery and FLAME entry — development handoff

Delivery date: 2026-10-17. Tracker ownership: F14, F15, B17 and B18 in [STAGES-STEPS.md](STAGES-STEPS.md). This is source/local verification, not production activation or a fresh inventory audit.

## Product behavior delivered

- `/` is a public Fliplecture landing page. Its centred composer asks FLAME anything; Books, Kits, Teachers and Classes open independent search. Typing does not reveal the learning sidebar.
- `/search?kind=books&q=...` uses the reference-style top search bar, catalogue navigation, category chips, expandable filters, selected-filter removal, results, paging and item details. Query/category/filter/page state supports links, reload and Back/Forward. Opening details preserves the result list and returns keyboard focus to the card.
- `/flame` retains the authenticated learning workspace, Study/Curiosity, curriculum, history, viewers, language and theme. A submitted home/item question enters Curiosity once; Study still needs confirmed published context. The product identity is Fliplecture; FLAME names the learning engine.
- Current owner access contract: guests can ask 10 Curiosity questions per India calendar day; signed-in students share 25 questions across Curiosity/Study. Study and student profiles require sign-in. Public catalogue reads remain available without a student cookie and still require the server-only BFF key. [Guest/profile implementation and activation](USER-ACCESS-PROFILES.md) supersedes the original sign-in-before-AI contract.
- A pending question is kept in this tab's session storage for at most 30 minutes, never in a URL. Sign-in and same-tab recovery/verification can return to `/flame`. Storage failure leaves the home question in place. The root conversation provider retains in-memory drafts, files and requests across client navigation; full reload/sign-out still clears them.
- “Ask FLAME about this” carries kind/ID/version and a readable question. The server rechecks the current published listing before provider I/O and before finalization. Listing text is untrusted data in a bounded prompt; missing/stale listings do not become fabricated answers. Existing request hashes are preserved when the new optional field is absent.
- Completed answers show catalogue shortcuts only when the student explicitly requests that category. Ordinary explanations have no catalogue footer; a Books request exposes only Books, and negated requests are suppressed. These are search entry points using the question, not newly ranked Books/Classes recommendations. Existing teacher/kit/media recommendation and interactive-rendering policies remain in place.

## Catalogue ownership and data

The source audit found no Books or Classes functional module. New `functional/discovery` owns a shared, kind-discriminated `flame.catalogue_entries` table for Books and Classes. Teachers and Kits remain in their original functional modules/tables; independent search reads their published records rather than copying inventory or weakening topic-scoped Explore routes.

Owner reports that Teachers/Kits currently have no database records; no external inventory query or live seeding was performed. Empty catalogue success, filtered zero matches and search/service failure have different UI states. Sample books in browser evidence belong exclusively to the synthetic local test server.

Books/Classes fields: title, description, category, subject, grade/age label, language, format, author/instructor, location, supplied schedule, availability, optional paired price/currency, publication/version and creation time. Publication requires description/category. New records are drafts; edits withdraw previously published records until explicit republication. Version-checked row locks reject stale edits/publication. There is no delete, checkout, enrolment or booking execution.

Teachers/Kits reuse administrator-reviewed topic labels for categories, current published curriculum subject mappings, explicit grade ranges and recorded languages. Language filters match any recorded language; cards/details display all recorded languages. Unknown values are not inferred. Books/Classes support their supplied metadata facets. Facets are stable across filters, bounded to 100 values per field; results are capped at 48 per page with a bounded offset and 200-character literal query. `%`/`_` are escaped, not treated as search wildcards. Search uses SQL filtering/paging, with no model calls, teaching-topic prerequisite or learning-progress writes. Initial empty inventory exits after one count query.

Current Books/Classes administration is in `/admin`, with separate tabs, manual draft/edit, reload/paging, explicit publish/withdraw, and a save-before-publish guard. Existing teacher/kit administration is reused. Dedicated Books/Classes spreadsheet imports, authorized cover/thumbnail delivery, numeric price filtering, and normalized class schedules/timezones/current availability are follow-up work. Schedule and availability are supplied labels, not a live scheduling feed.

## API/BFF contracts

| Route | Access and purpose |
| --- | --- |
| `GET /api/v1/catalogue` | BFF-only public published search; kind, q, category, subject, level, language, format, author, location, sort, offset, limit |
| `GET /api/v1/catalogue/{kind}/{id}` | BFF-only public published detail, with optional exact version |
| `GET/POST /api/v1/admin/catalogue/{books\|classes}` | Admin-only draft listing/creation |
| `PATCH /api/v1/admin/catalogue/{kind}/{id}` | Admin-only complete editable payload plus expected_version; saves as draft |
| `POST /api/v1/admin/catalogue/{kind}/{id}/publication` | Admin-only expected_version + published flag |
| `POST /api/v1/sessions/{id}/ask[-stream]` | Existing owned/member route; additive optional catalogue_item `{kind,id,version}` |

Browser catalogue requests use `/api/catalogue/[[...path]]`, with allowlisted paths, no-store responses, server-only BFF key and CSRF validation for admin mutations. Books/Classes state is not sent through admin endpoints for public searches. Item absence returns 404; stale edit returns 409; invalid input returns 422. An unconfigured BFF returns a catalogue-specific unavailable message.

The pre-B17 compatibility golden fixture is retained: tests strip only the five intentionally added catalogue paths, four new schema definitions, the optional AnswerRequest property and the new table before checking the original 108 paths/34-table hashes. Current source declarations have 113 paths and 35 tables.

## Database activation

Migration source: `development/apps/flame-api/migrations/versions/20261017_31_discovery_catalogues.py`, parent `20261012_30`. It creates only the new table/index/checks, enables RLS and revokes direct public/anon/authenticated access. It does not seed or alter existing inventory. Downgrade refuses to drop populated inventory.

The migration has **not been applied** to the configured external database. Alembic's repository environment intentionally disables CLI offline migrations; direct Alembic Operations/PostgreSQL SQL rendering is covered by an isolated test. SQLite tests exercise the mapped Books/Classes queries and HTTP lifecycle without certifying PostgreSQL locking, JSONB filtering, RLS, runtime-role grants or a real migration round trip.

Before connecting the live Books/Classes screens: review/apply the additive migration against the agreed development target, verify schema drift/runtime grants and rollback-only PostgreSQL catalogue/search/publication tests, then add owner-approved records through administration. Do not treat missing schema as empty inventory or seed examples into the live database. Existing Teachers/Kits reads use their original tables.

## Main-domain release preparation

`FLIPLECTURE_CANONICAL_ORIGIN` is optional and unset by default. When explicitly enabled with `https://fliplecture.com` or `https://www.fliplecture.com`, Next redirects the legacy FLAME host's `/` to main-domain `/flame`, and other legacy paths to their same-path main-domain destination. Search queries are retained by Next. Host conditions prevent loops on the selected main domain; invalid canonical origins fail configuration.

Before release, inventory the existing main website's marketing routes/content and hosting project. Choose apex/www canonical handling; prepare DNS/TLS, hosting bindings, `FLAME_WEB_ORIGIN`, BFF/API settings and Supabase verification/recovery allowlists. Host-only cookies and browser storage do not transfer from the old subdomain: plan reauthentication, not session-cookie copying. Keep a backup/current deployment pointer and route/redirect checks before changing traffic. Existing marketing content has not been imported into the new About page.

Rollback preparation: leave the current production projects/DNS in place while validating source/staging; remove the optional canonical-origin setting to disable these redirects; restore the prior deployment if cutover fails. Do not downgrade a populated new catalogue as part of a UI rollback. Actual staging-domain checks, production migration, DNS/auth settings and traffic cutover require their own recorded release action (B18.6 remains NOT STARTED).

## Verification

Final recorded results: production build and TypeScript passed; **48 frontend units** and **398 offline backend tests** passed (26 skipped, 28 database-integration checks deselected). Discovery/admin, sidebar, rich-response/language/theme, mathematics (17 templates/three engines) and simulation (eight inline runtime/isolation fixtures plus recovery/streaming) browser suites passed. The final discovery rerun also verified saved Tamil preference through catalogue selection/sign-in and the unsaved-edit publication guard. No configured provider or external database was used.

Commands from `development/apps/web`:

```powershell
$env:FLAME_NEXT_DIST_DIR='.next-discovery'
npm run build
npm run test:unit
node tests/discovery-browser.cjs
node tests/sidebar-conversations-browser.cjs
$env:FLAME_TEST_NEXT_DIST_DIR='.next-discovery'
node tests/rich-response-browser.cjs
```

Backend offline checks from `development/apps/flame-api`:

```powershell
.\.venv\Scripts\python.exe -m pytest -q -m 'not db_integration' -p no:cacheprovider --basetemp=../../../work/discovery-pytest-review
```

Recorded evidence is summarized in the tracker delivery entry. The new browser harness uses real production Next/BFF pages and an isolated synthetic API, with no provider/account/database writes. It covers query carry-over, filtering/zero results, paging/Back, details/focus, sign-in continuation, exactly one item-aware Curiosity request, empty catalogues, failure/retry, stale-response suppression, Books draft/publication/withdrawal, Classes admin entry, light/dark accessibility and 1440/768/390/320px layouts. Screenshots: `work/discovery/home-desktop.png`, `home-mobile.png`, `books-desktop.png`, `books-mobile.png`, `books-dark-mobile.png`.

Existing browser harnesses now enter `/flame` rather than the public root. Conversation restoration retains in-flight turns, deletion clears alternate in-memory keys, library additions are serialized, and drawer overflow menus portal into their modal surface. Existing sidebar and rich-response/language/theme checks accompany this delivery. Physical keyboards/screen readers, real-device on-screen keyboards, configured signup/recovery, full live-data integration and prior B8/B9.11/B10/F13.11/B15 acceptance gates remain open.

## Owner interaction refinements — 2026-10-17

Canonical workspace URL is now `/flame`; `/learn` remains a compatibility redirect. Home, item questions, sign-in/recovery continuation, account/admin links, legacy-host release configuration and current browser harnesses use `/flame`.

The unsolicited four-category response footer is removed. A small deterministic request matcher only displays categories explicitly requested by the question, respecting common negation and excluding ordinary explanations/definitions. This makes no additional model request and does not change the existing server-owned recommendation policies.

Workspace mode, selected topic, resumed conversation and navigation-tree view are retained in the application provider by Next's documented browser-history segment identifier. Shared viewport positions restore the reading location on browser Back/Forward; responses and drafts are reused without resending the question. Stored positions clamp to available content if asynchronous cards reflow. Snapshots stay in this tab's application memory and disappear on full reload/sign-out.

Composer attachment/image/audio buttons use explicit zero-padding flex centring; browser assertions compare SVG and button centres at desktop/tablet/mobile widths. About identifies FLAME as Fliplecture's agentic model engine, developed by Fliplecture, and describes age/prior-skill/educational-needs adaptation as its design intent using shared learning context, rather than claiming an unimplemented skill-assessment service.

Regression checks cover ordinary answers without shortcuts, Books-only requests, a catalogue round trip restoring Curiosity/response/draft/scroll without another ask, icon centring, About wording, the compatibility redirect, existing Study navigation, and the rich-response/language/theme flow. No backend/schema/data/domain change accompanies these refinements. Tracker package counts are unchanged.

Refinement verification: production build/TypeScript and all 48 web unit tests passed; updated discovery, sidebar and rich-response/language/theme production-browser suites passed against synthetic APIs. No backend test rerun was required for this frontend-only refinement; the earlier 398-test backend result retains its delivery scope.

## Fliplecture logo refresh — 2026-10-17

Current owner-approved specification. This replaces the earlier heavy/medium system-font and Rozha One variants, including the near-black, soft-white and pale-mint wordmark colours.

| Element | Current specification |
| --- | --- |
| Product wordmark | Lowercase **fliplecture**, set in **Tilt Warp** from Google Fonts |
| Font style | Native regular **400**, normal style, default XROT/YROT rotation; letter spacing **-0.015em**, line height **1.15** |
| Light-mode wordmark | Forest green **#00513F**, matching the symbol background |
| Dark-mode wordmark | Lime **#60FF00**, matching the symbol's `{}` braces |
| Admin header | Remains a light surface in both theme preferences, so its wordmark stays **#00513F** |
| Symbol | Code-drawn SVG: **#00513F** background, **#60FF00** braces, **128 × 128** viewBox and **18** corner radius |
| Loading | Local `next/font/local` asset, `--font-brand` variable and `display: swap`; no browser request to Google Fonts |
| Scope | Home, catalogue search, FLAME workspace/navigation drawer, account forms, About and administration; compact sidebar and browser tab use the symbol |

The font applies to the product wordmark. Other interface text retains the existing Segoe UI/Arial/Helvetica stack. Historical raster brand assets are unused; the unused Rozha One font files were removed.

Source owners:

- [Shared logo component](../development/apps/web/src/components/ui/fliplecture-logo.tsx).
- [Brand colours, typography and responsive sizes](../development/apps/web/src/app/brand.css).
- [Font loader and browser-tab metadata](../development/apps/web/src/app/layout.tsx).
- [Bundled Tilt Warp font](../development/apps/web/src/app/fonts/TiltWarp-Regular.ttf) and [OFL license](../development/apps/web/src/app/fonts/OFL-TiltWarp.txt), obtained from the [official Google Fonts repository](https://github.com/google/fonts/tree/main/ofl/tiltwarp).
- [Rounded brace SVG](../development/apps/web/public/brand/fliplecture-symbol.svg).

Verification boundaries: the shared-logo delivery passed production build/TypeScript, all 48 web units and the discovery/sidebar production-browser suites using synthetic APIs. After selecting Tilt Warp, production build/TypeScript and focused browser checks confirmed the actual bundled font loads at weight 400, same-origin font requests, responsive fit and light/dark axe accessibility at 1440/390/320px. The final palette-only adjustment was checked by injecting current source `brand.css` over that production build: exact computed colours and light/dark axe accessibility passed on desktop/mobile. At the time of the documentation reconciliation, a new production build and the full suites had not been rerun for that palette-only adjustment; later search-surface verification is recorded below.

Current home previews: `work/discovery/home-desktop.png`, `home-mobile.png`, `home-dark-desktop.png` and `home-dark-mobile.png`. These show Tilt Warp and the final green/lime palette. The initial workspace/search screenshots predated the final font/palette; the discovery suite refreshes them when rerun.

F14.2/F14.7 statuses and package counts are unchanged. No backend, database, inventory or deployment change accompanies the brand refresh.

## Dark search surface correction — 2026-10-17

A global dark-mode input background overrode the homepage textarea and catalogue search field, producing a rectangular grey strip inside each rounded container. The existing transparent workspace-composer exception in `src/app/theme.css` now also covers the homepage composer and catalogue search input. Other form controls retain their existing surfaces. The discovery browser harness checks empty/filled and focused/blurred fields at 320/1440px for a unified transparent inner surface and no horizontal overflow.

Verification: production build and TypeScript passed. The expanded discovery production-browser suite passed, including both dark search controls in empty/filled, focused/blurred states at 320/1440px, existing light/dark axe audits and catalogue/sign-in/admin/history flows. Current home, search and workspace screenshots were refreshed; dark desktop-home and mobile-search screenshots were visually reviewed. No backend changes or tests were required.

## Catalogue search focus correction — 2026-10-17

The global focus outline highlighted the inner rectangular text input while typing. Catalogue search now draws its focus indicator around the rounded outer form using `:focus-within`; only the inner input outline is suppressed. Search/clear buttons retain their own visible keyboard focus. This shared form serves Books, Kits, Teachers and Classes. The discovery browser harness covers all four categories in both themes at 320/1440px, typing, the rounded outer indicator, keyboard focus on the clear action, blur and overflow.
Focus verification: production build, TypeScript and the expanded discovery production-browser suite passed. All four catalogue inputs retain rounded form focus in both themes at 320/1440px, with working typing, keyboard action focus and no overflow. Light desktop/dark mobile focused-search screenshots were visually reviewed (`work/discovery/search-focused-light-1440.png`, `search-focused-dark-320.png`).
