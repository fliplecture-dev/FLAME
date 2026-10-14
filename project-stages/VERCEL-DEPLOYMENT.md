# FLAME MVP on Vercel

Owner-selected target, 2026-10-14: two Vercel projects from this repository. Runtime acceptance is tracked only in [STAGES-STEPS.md](STAGES-STEPS.md), especially B5/B9.11/B10/F8. No deployment is recorded by this guide.

Deployment performed on 2026-10-14 at the owner's request: `flame-web` and `flame-api` are connected to `fliplecture-dev/FLAME` with the roots below. Website: https://flame.fliplecture.com. API: https://flame-api.vercel.app. Both initial production builds from `93b2e8f33a424cd4229b4d8dd40e0e581a44b601` reached READY in Mumbai (`bom1`). Exact runtime evidence and remaining acceptance are recorded in STAGES-STEPS.md. Work locally, run affected checks, then commit/push reviewed changes to main. Git integration triggers applicable builds; verify deployment results and hosted journeys after each release. Full production pilot acceptance remains open.

| Project | Root Directory | Framework / entry point |
| --- | --- | --- |
| Website | `development/apps/web` | Next.js; `npm ci`, `npm run build`; automatic output directory |
| Python API | `development/apps/flame-api` | FastAPI; `pyproject.toml` explicitly selects `app.main:app` |

Keep these directories unchanged. Vercel supports the existing `app/main.py` entry point and the explicit `tool.vercel.entrypoint` setting. Do not configure `Start-FLAME.ps1`, `npm run dev`, Uvicorn reload, or a second Python process inside the website deployment. See [Vercel FastAPI documentation](https://vercel.com/docs/frameworks/backend/fastapi).

## Environment settings

Use Vercel's project environment settings, scoped separately to Preview and Production. Never commit the local `.env` files or copy production secrets into a public preview. Use a fixed website origin for acceptance; arbitrary preview hostnames are not automatically authorized.

| Website variable | Value / source |
| --- | --- |
| `FLAME_API_URL` | HTTPS origin of the API project, without a trailing slash |
| `FLAME_WEB_ORIGIN` | Exact HTTPS origin of the website project |
| `FLAME_BFF_SHARED_KEY` | Same private random value as the API project; server-only |

| API variable | Value / source |
| --- | --- |
| `FLAME_ENVIRONMENT` | `production` |
| `FLAME_DATABASE_URL` | Restricted runtime PostgreSQL role, SQLAlchemy `postgresql+psycopg://` URL; verify connectivity from Vercel |
| `FLAME_SUPABASE_URL` | Supabase HTTPS project URL, without a trailing slash |
| `FLAME_SUPABASE_ANON_KEY` | Project publishable/anon key used by the existing identity adapter |
| `FLAME_SUPABASE_JWT_SECRET` | Only if the project's existing token verification uses legacy HS256 |
| `FLAME_SUPABASE_SECRET_KEY` | Server-only secret for confirmed account deletion; legacy service-role key is an alternative |
| `FLAME_SESSION_ENCRYPTION_KEY` | Stable Fernet encryption key for server session tokens; preserve across redeployments |
| `FLAME_WEB_ORIGIN` | Same exact website origin as the website project |
| `FLAME_BFF_SHARED_KEY` | Same server-only shared key as the website project |
| `FLAME_RESOURCE_STORAGE_BACKEND` | `supabase` |
| `FLAME_RESOURCE_STORAGE_BUCKET` | Existing verified private bucket |
| `FLAME_LLM_OPENAI_API_KEY` / `FLAME_LLM_MODEL` | Configure together; retain the owner's permitted model and spend controls |
| `FLAME_LLM_TIMEOUT_SECONDS` | `12` |
| `FLAME_LLM_MAX_OUTPUT_TOKENS` | `1500` |
| `FLAME_LLM_DAILY_REQUEST_LIMIT` | `100` |
| `FLAME_DELETION_RECEIPT_RETENTION_DAYS` | `30`; this controls local receipts, not provider backup/log expiry |

Configure Supabase Auth's website/callback/recovery URLs for the chosen website domain. Do not use the development schema-owner database connection as the production runtime role. Migrations run separately with the reviewed migration role; neither startup nor a deployment build runs them automatically.

## Private transfers and persistence

Vercel's [Function limits](https://vercel.com/docs/functions/limitations) cap request and response bodies at 4.5 MB. Both projects now use private transfers for large files: the signed-in administrator authorizes a file through the BFF, the browser PUTs bytes directly into private Supabase staging, and the API validates size, SHA-256 and existing media/workbook/package rules before returning a small receipt. Two-hour encrypted tickets bind the administrator, target and server-generated identity. Retrying confirmation reuses the same upload/import/preview record. No service key reaches the browser and no upload publishes an item.

Curriculum workbooks, media uploads and all four bulk previews use this path when Supabase storage is configured. Bulk templates/packages and curriculum exports return five-minute private download URLs; bytes bypass both Functions. Local development retains multipart routes when local storage is selected. A real synthetic PNG above 4.5 MB completed upload, validation, receipt replay, authenticated retrieval and private template delivery; test files were removed and database fixtures rolled back. Full-size 100 MiB video/120 MiB ZIP acceptance remains a hosted load check, including the Supabase project/bucket file-size cap and available memory/time. Configure the private bucket to permit at least 120 MiB and verify that the project's storage plan supports that limit; no paid-plan change is recorded.

The existing 2 MiB Interactive HTML limit is separate from the platform payload limit; verify serialized JSON sizes as well as file sizes. Vercel runtime disk is not durable storage. The API's production validator already requires Supabase media storage; live upload, signing, expiry, withdrawal and missing-object checks remain B9.11 acceptance work.

For Google Sheets, set `FLAME_GOOGLE_SHEETS_CREDENTIALS_JSON` to the complete service-account JSON in the API project's server-only environment settings. This secret value takes precedence over `FLAME_GOOGLE_SHEETS_CREDENTIALS_FILE`, which remains supported locally. Share the target spreadsheet with that service account as Editor. Never use a `NEXT_PUBLIC_` variable, public asset or committed credential file. Hosted token acquisition and confirmed sync acceptance still need verification. Curriculum workbook bytes/preview state and bulk preview payloads already persist in PostgreSQL; bundled media uses private storage. Temporary files are used only during validation. Provider deletion retries retain their existing database workflow.

The API entry point and transfer BFF specify a 300-second maximum; confirmation/export transport waits up to 240 seconds. Verify duration support in the chosen Vercel plan, measured import runtime, cold-start database connections, bounded pool usage and concurrent ask leases. A browser disconnect can lose its response while a synchronous ask continues; saved history and idempotent replay recover the persisted answer. A function termination relies on the existing expiring claim/fencing mechanism and must be checked on the hosted runtime.

## Release and recovery procedure

Both app roots include `vercel.json` with `regions: ["bom1"]` so Git-triggered deployments keep server functions near the Mumbai database. The initial deployment's region override did not persist for later builds; pinning the region in source fixes that. Explore requests allow 30 seconds for cold starts. Repeated checks of the same private asset are reused only within one request's database session; later requests still check object availability.

Prepare both projects and their secrets, apply reviewed migrations separately, then check API `/health/live` and `/health/ready`. Run the signed-in member/admin journeys against the chosen preview environment, including answers/reload/continuation, denied access, imports, resource delivery and withdrawal. Record exact evidence in the tracker. Publish the MVP only after the owner release decision and remaining acceptance inputs are recorded.

For rollback, restore the previously accepted website and API deployments together. Preserve shared keys, session encryption key, database and private bucket. Do not downgrade or purge retained data as part of a code rollback. Use compatible migration/application versions; rehearse database restoration separately under B10.6.

Receipt/tombstone purging and confirmed provider deletion retries require a scheduled, authenticated operations mechanism; serverless application startup is not a scheduler. Existing commands are `python -m scripts.retry_deletions` and `python -m scripts.purge_deletion_receipts` in the API project. They mutate previously confirmed deletion workflows, so do not run them as a build step. Record actual managed backup/log retention and tested scheduling under B5.7/B10.6.

Private transfer cleanup is `python -m scripts.purge_transfer_artifacts` (dry run), then `--execute` after reviewing its candidate count. It removes only generated staging/export objects older than 24 hours, with a default maximum of 100 per run; fresh/recently updated files and catalogue assets are excluded. Schedule it daily alongside reviewed maintenance jobs. Unreferenced final resource uploads need separate database-aware cleanup that preserves pending bulk previews; this command deliberately excludes that namespace. Actual scheduling and orphan recovery remain operations acceptance gates.
