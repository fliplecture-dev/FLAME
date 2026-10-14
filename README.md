# FLAME

FLAME is a learning application with a Next.js frontend and a Python FastAPI backend. Both applications live in this repository and are deployed as separate services.

## Repository structure

- `development/apps/web`: Next.js, React and TypeScript website, browser-facing API routes, and frontend tests.
- `development/apps/flame-api`: FastAPI services, PostgreSQL models, Alembic migrations, and backend tests.
- `project-stages`: development documentation and sample import fixtures.
- `Start-FLAME.ps1`: Windows local development launcher.

## Local setup

Install a Node.js version supported by the pinned Next.js version and Python 3.12 or later.

From `development/apps/flame-api`:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e '.[test]'
Copy-Item .env.example .env
```

From `development/apps/web`:

```powershell
npm ci
Copy-Item .env.example .env.local
```

Configure the local environment files for your own Supabase project and database. Set matching `FLAME_BFF_SHARED_KEY` values in both applications. Never commit credentials. Apply the reviewed Alembic migrations to your own development database before starting the app; migrations do not run automatically.

From the repository root:

```powershell
.\Start-FLAME.ps1
```

Alternatively, run `npm run dev` from the web directory. The launcher checks the Python API and database on port 8000 before starting the website on port 3000.

## Checks

From the web directory:

```powershell
npm run typecheck
npm run test:unit
npm run build
```

From the API directory:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Database integration tests are opt-in; consult the API README before enabling them. Some browser tests require locally configured accounts, services or private test assets. The owner's curriculum workbook and local uploads are not distributed in this public repository.

## Deployment

For a Next.js deployment, set the project root to `development/apps/web`. Deploy the API from `development/apps/flame-api` with entry point `app.main:app`, and configure the website's `FLAME_API_URL` to its deployed address.

The MVP hosting target is two Vercel projects with those exact Root Directory values. See [Vercel deployment preparation](project-stages/VERCEL-DEPLOYMENT.md) for environment settings, runtime requirements and remaining upload/storage acceptance.

Production requires PostgreSQL, Supabase authentication, a private Supabase Storage bucket, matching shared keys, a session encryption key, and the correct website origin. Configure the OpenAI key and model together to enable learning answers. All credentials belong in the hosting platform's environment settings.

The local launcher is for development. Production `npm start` does not start Python. GitHub Actions checks both applications; Docker and automatic deployment are not configured. With Supabase storage enabled, media/workbook/ZIP uploads and generated exports transfer directly through private storage; only authorization metadata and confirmation receipts cross Vercel Functions. Local storage retains multipart uploads. See the deployment guide for provider size limits and hosted acceptance.

See the application READMEs and `project-stages/README.md` for more detail.
