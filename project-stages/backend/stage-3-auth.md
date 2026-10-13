# B3 identity implementation and activation

Decision (2026-09-26): members self-register using email and password. Email verification is required before password sign-in. Member registration has no role field; the admin_roles table alone grants admin access.

## Flow

Browser requests stay on the same-origin Next.js BFF. Every mutation checks the exact Origin and a random double-submit CSRF value. The browser receives an opaque, HttpOnly, SameSite cookie; Supabase access and refresh tokens are encrypted in flame.browser_sessions with a Fernet key. FastAPI checks the BFF shared key, the hashed session ID, a signed Supabase JWT (issuer, audience, expiry, subject, role), and the server-side profile/admin tables. Expired access tokens refresh under a row lock. Browser sessions have a seven-day absolute lifetime enforced by both the cookie and FastAPI. Logout revokes the local session and calls Supabase logout when the access token is still valid. No client-provided member ID or role is used as authority.

Routes: POST /api/v1/auth/register|login|verify|recover|reset-password|refresh|logout, GET /api/v1/me. The BFF exposes /api/auth/* and /api/me; UI entry points are /sign-up, /sign-in, /recover, /auth/callback, and /admin/sign-in. Verification creates the profile lazily on the first /me, allowing retry after a partial signup/session write. A duplicate signup returns the same pending response as a new signup. Wrong credentials, expired links, and invalid sessions use the standard error envelope.

## Required Supabase configuration

- Enable email/password signup and Confirm Email. Configure the project Site URL to the web origin and allow /auth/callback as a redirect.
- New free-tier Supabase projects using the default email sender cannot edit Auth email templates (June 2026 policy). Configure custom SMTP before editing the two token-hash links below. Paid plans are exempt from the template-edit restriction, but the default sender still limits email delivery to project team addresses; ordinary member signup needs a real sender. See the [Supabase change notice](https://supabase.com/changelog/46599-changes-to-email-template-customisation-on-free-tier) and [SMTP guide](https://supabase.com/docs/guides/auth/auth-smtp).
- Set the Confirm signup email template link to: {{ .SiteURL }}/auth/callback?token_hash={{ .TokenHash }}&type=email
- Set the Reset password template link to: {{ .SiteURL }}/auth/callback?token_hash={{ .TokenHash }}&type=recovery
- Use an asymmetric Supabase JWT signing key when available. For a legacy HS256 project, set FLAME_SUPABASE_JWT_SECRET only on the API server. The BFF never receives this key.
- Copy the project URL and publishable key from Supabase's Connect dialog (or Settings > API Keys) into FLAME_SUPABASE_URL and FLAME_SUPABASE_ANON_KEY in the API .env. Configure the API and web environment examples. Generate a distinct Fernet session key and BFF shared secret. Keep API traffic on a private network; never expose the BFF key to client JavaScript.
- Run migrations 20260926_07 and 20260926_08 with the migration owner. Use a separate, privately connected runtime database role with only necessary FLAME grants before production. The migrations revoke Supabase client roles from the flame schema and enable deny-by-default RLS on identity tables. A schema owner can bypass RLS, so browser access must still pass the BFF and FastAPI guards.
- Register and verify the first admin account, then run the bootstrap_admin.py script with FLAME_BOOTSTRAP_ADMIN_SUBJECT set to the verified auth UUID. It works only while no admin grant exists. There is no public admin selection or admin grant endpoint.

Supabase email templates and token-hash server verification follow [Supabase's email template guide](https://supabase.com/docs/guides/auth/auth-email-templates). JWT key verification follows [Supabase's JWT guide](https://supabase.com/docs/guides/auth/jwts).

## Development completion evidence and deployment gate

On 2026-09-26, live local self-registration delivered email from `no-reply@auth.fliplecture.com`; the token-hash callback confirmed the account, and email/password sign-in reached the web app. The owner selected that verified account as the first admin. The controlled bootstrap created one active admin grant. The owner then completed recovery email, password reset, sign-out and sign-in with the new password. A read-only database check found one active profile, one admin grant and two revoked sessions among three sessions.

The full API suite previously passed 28 tests. The targeted B3 suite passed 9 tests against the migrated development database, including member-versus-admin denial, cross-member ownership denial, expired-session handling, refresh and revocation. Web typecheck passed after the shared retryable sign-out control was added. Five account-screen axe audits and two unauthenticated redirects passed. The BFF checks Origin and CSRF; the read-only B3 readiness audit passed all 12 checks. Migrations `20260926_07` and `20260926_08` are applied with no schema drift; identity RLS is enabled and Supabase client roles have no direct FLAME table access.

B3 is complete for development. Before production deployment, provision a restricted private runtime database role instead of the development schema-owner connection. Admin management screens and protected catalogue/import operations were subsequently mounted in B4; this paragraph records the B3 handoff state.
Read-only readiness command: from development/apps/flame-api, run `python scripts/check_b3_readiness.py`. It reports configuration presence, migration head, identity RLS, direct-role denial, provider email confirmation, signup enablement and JWT key availability without printing secrets.
