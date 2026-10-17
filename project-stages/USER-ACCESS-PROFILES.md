# Fliplecture user access and student profiles

Owner decision and source delivery: 2026-10-17. This contract supersedes the earlier requirement to sign in before every FLAME question. [STAGES-STEPS.md](STAGES-STEPS.md) remains the only progress tracker.

## Access rules

| Visitor | Home and Books/Kits/Teachers/Classes search | Curiosity | Study | Student profile |
| --- | --- | --- | --- | --- |
| Guest | Public | 10 new questions per calendar day, per anonymous browser identity | Selecting Study requests sign-in; guest API rejects Study/context payloads | Sign-in required |
| Signed-in student | Public | Shares a 25-question daily allowance with Study | Requires sign-in and a valid published curriculum path | Read/update only their own details |
| Administrator | Public | Existing administrator quota exemption retained | Existing administrator/member authorization retained | Own profile; no new administrative grants |

Both allowances reset at **00:00 Asia/Kolkata (India time)**. The owner explicitly chose calendar days, replacing the rolling 24-hour policy. There is no membership-tier, subscription, per-user override or future member-policy engine in this delivery. The existing server request ceiling may reduce the fixed guest/member caps; the documented default is now 25. Simulation generation retains its existing separate bounded allowance.

Questions are counted from persistent answer-request claims across all owned sessions in that calendar day. The profile row lock serializes quota checks before a new claim. Exact-key retries/replays do not consume another question or call the model again; pending, unsupported and failed new claims retain the existing counting semantics. A new logical retry after a terminal provider failure can consume another claim. The remaining-question counter refreshes after requests, on window focus and at the server-reported midnight reset. Rejection preserves the draft and explains the reset. The guest allowance/sidebar sign-in links retain an unsent text question for exactly one member request after authentication; browser Back into the guest workspace does not consume that sign-in-only handoff. Selecting Study remains an explicit Study sign-in route.

## Guest journey and boundary

The first home or catalogue item question opens `/flame` directly in Curiosity, retaining answer language and the item reference. The guest workspace exposes the existing composer, responses and catalogue links. Study controls request `/sign-in?next=/flame?mode=study`; a successful sign-in enters Study with its usual curriculum selection gate. Attachments remain honestly unsupported for both guests and members.

The BFF obtains a random server-issued capability and stores it only in a seven-day **HttpOnly, SameSite=Lax** cookie (Secure in production). Only its SHA-256 hash is persisted in `guest_access`, linked to a `student_profiles` row with status `guest`. Guest identities are not Supabase accounts. Guest endpoints validate the capability, expiry, profile status, Curiosity mode and conversation ownership. Guest data is excluded from student administration/export. No guest token authorizes member, profile, curriculum or administrator APIs. Signed-in BFF requests cannot use the guest route to avoid their member allowance. Mutations retain exact-origin and double-submit CSRF checks.

The guest allowance belongs to the anonymous browser identity; it is not proof of a unique person across browsers or cleared cookies. Cookie expiry does not delete conversation rows or supply a retention scheduler. Existing data-retention/operational acceptance remains open. Guest responses/drafts stay in this tab's conversation provider while navigating; they are not automatically imported into a signed-in account or reconstructed after a full reload.

## Optional phone and private profile

Sign-up and sign-in include **Phone number (optional)**. Email/password and email verification remain the authentication method; a phone is contact data, not a verified login identifier or SMS/OTP method. Blank sign-in phone input leaves an existing phone unchanged. Registration saves the optional phone in provider metadata; lazy profile creation copies it, while a supplied sign-in phone updates only the verified account's profile. Password whitespace is preserved.

`/profile`, linked from the workspace profile menu, supports display name plus optional phone number, contact number, address, city, state, country and pincode/postal code. The email is read-only. Blank optional fields clear saved values. Phone numbers accept 7–15 digits with common separators and an optional country code; postal codes are not restricted to Indian digits. Length bounds are enforced server-side. Save failures retain typed input.

The member-owned `GET/PATCH /me/profile` routes derive identity from the authenticated principal. Payloads cannot choose an owner or change email, status, role or auth subject. These contact/address fields are not added to AI prompts or public catalogue projections.

## Source map

| Responsibility | Source |
| --- | --- |
| Guest identity/capability | `development/apps/flame-api/app/modules/functional/identity/guests.py` and `models.py` |
| Owned contact fields/validation | `functional/identity/profile.py`, `profile_data.py` and `router.py` |
| Guest Curiosity coordination | `application/teaching/guest_router.py` |
| Limits/calendar boundary | `application/teaching/usage.py` and `answer_service.py` |
| Guest BFF and cookie | `development/apps/web/src/app/api/auth/guest/route.ts`, `api/guest/[...path]/route.ts` |
| Guest workspace/allowance | `src/features/learning/guest-workspace.tsx`, `question-allowance.tsx` |
| Profile page/form/proxy | `src/app/profile/page.tsx`, `features/auth/student-profile-form.tsx`, `app/api/me/profile/route.ts` |

API additions: `POST /api/v1/guest/identity`, `GET /guest/me`, `GET /guest/usage`, `POST /guest/sessions` and the owned `capability-check`, `ask`, `ask-stream`, `simulation` subroutes; `GET /me/usage`; `GET/PATCH /me/profile`. All are behind the server-only BFF key. Existing member routes and provider credentials remain private.

## Database activation and checks

Migration **20261017_32** adds seven nullable contact/address columns and the guest-capability table with PostgreSQL RLS/revokes. It follows the earlier catalogue migration **20261017_31**. The owner confirmed development Supabase project `fsisfydsxngyjqjqejkc`, and both migrations were applied on 2026-10-17. Current head is **20261017_32**; `alembic check` reports no new upgrade operations. Runtime guest identity/profile and ORM profile reads require this schema on any other target. Downgrade refuses to discard guest/contact data silently.

For another explicitly authorized target, the activation command from `development/apps/flame-api` is:

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade 20261017_32
```

Review both additive migrations if the current head is 20261012_30. This creates no live catalogue listings, Supabase users or membership tiers. Rollback-only PostgreSQL quota/ownership/profile checks and guest RLS/grant checks passed after activation. Concurrent load, a restricted production runtime role, live signup/recovery with the optional phone and production website activation retain their separate acceptance gates.

Hermetic checks:

```powershell
# API directory: offline SQL/HTTP; no provider/account/database writes outside SQLite
.\.venv\Scripts\python.exe -m pytest -q -m "not db_integration" -p no:cacheprovider --basetemp=../../../work/access-final-all
# Web directory: synthetic API, real production Next/BFF
$env:FLAME_NEXT_DIST_DIR='.next-discovery'
npm run build
node tests/user-access-browser.cjs
node tests/discovery-browser.cjs
node tests/sidebar-conversations-browser.cjs
```

API evidence: **406 passed and 26 skipped** (the current collection excludes 37 opt-in database checks); includes guest/member quota limits, duplicate/streamed replay behaviour, calendar boundary, guest expiry/ownership/Study denial, optional auth phone and private clearable profile updates. SQLite validates SQL/HTTP behaviour, not PostgreSQL locking/RLS. New migration SQL renders offline. Web build/TypeScript and **48 unit tests** passed. The user-access and updated discovery browser suites passed against synthetic APIs, including optional phone, Study sign-in, guest cap/draft retention, profile save/reload/clear/failure recovery and light/dark responsive accessibility. The existing sidebar regression passed after its synthetic fixture was updated for the new usage endpoint. Final draft-continuation verification passed: the blocked guest question is restored through sign-in, sent once under the member allowance, and the counter shows 24 of 25 remaining. Back into the guest workspace preserves sign-in-only intent without sending it as another guest question.

Final source verification: production build, TypeScript, all 48 web units, 406 offline API checks, and user-access/discovery/sidebar production-browser suites passed. Profile mobile light/dark and guest-limit desktop screenshots in `work/access/` were visually reviewed. Migration 31/32 review SQL: `work/access/migrations-31-32-review.sql`, generated without a database connection. Hosted development schema activation was subsequently approved and completed; see the activation receipt below.


## Approved development activation — 2026-10-17

The owner selected the option to apply migrations to configured development Supabase project `fsisfydsxngyjqjqejkc`. Alembic upgraded **20261012_30 → 20261017_31 → 20261017_32** successfully. `alembic check` reports no schema drift.

Nine explicitly targeted PostgreSQL checks passed (eight shared SQL/HTTP cases plus one migration/RLS check). Tests use nested savepoints inside outer transactions that roll back all synthetic profiles, capabilities, sessions, messages and usage rows; there were no Supabase Auth or paid model calls. Guest token storage has RLS enabled and neither `anon` nor `authenticated` has SELECT permission; direct SELECT on `student_profiles` is also denied to both roles. This verifies the current database grants, not a future restricted production runtime-role deployment.

`tests/test_guest_profile_postgres.py` is marked `db_integration`, opts in only with `FLAME_ACCESS_DB_VERIFY=1`, and requires `FLAME_ACCESS_DB_HOST` to match the explicitly authorized development hostname. It refuses a production settings target. The default offline run never connects to this database through these tests.

The existing hidden background launcher is running API **8000** and web **3000**. Local readiness returned 200 for API/database, `/`, `/flame`, all four `/search?kind=...` pages and the public Books BFF. Unsigned `/profile` redirects to sign-in (307), while its private API returns 401. The first homepage request timed out during cold Next.js development compilation; warm checks all passed. No paid AI request, permanent test account/inventory, production web deployment or DNS change was made. Existing physical-device, hosted-provider and main-domain release gates remain open.


## Account menu refresh — 2026-10-17

The workspace profile popover now has an avatar/name/email header and consistent full-width icon rows for Student profile and Sign out, with Delete account separated by a divider and destructive color. Rounded surfaces, hover/focus feedback, busy states and theme-aware contrast replace native button styling. Deletion still requires confirmation; opening it focuses Cancel, cancelling returns focus to Delete account, and Escape closes the popover without closing the mobile navigation drawer.

Production build and TypeScript passed. The synthetic user-access browser suite passed, including account-menu accessibility/viewport checks at 1440, 900, 390 and 320px in both themes, confirmation cancellation, and Escape focus restoration. Light desktop and dark mobile screenshots in `work/access/account-menu-*.png` were visually reviewed. No account was deleted during verification.


Question allowance placement: guest and member counters, the midnight India reset time, and the guest upgrade/sign-in link are now in the profile popover below the account header. The learning workspace no longer shows an allowance strip. The existing usage refresh events and guest draft preservation on sign-in remain connected across desktop, compact rail and mobile drawer.

Placement verification passed: TypeScript, production build, and the synthetic user-access browser suite. The browser verifies that counters are absent from the workspace and hidden when the profile menu is closed, update after guest/member questions, and preserve the guest draft through the menu sign-in link. Responsive light/dark accessibility checks passed; the updated dark mobile menu screenshot was reviewed.
