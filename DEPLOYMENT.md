# Public SIH prototype

Production URL: https://casebridge-rho.vercel.app/ . Deployed on 30 October 2026
with a dedicated free Neon database in Singapore. Public `/api/health` confirms
the API and database are available without a Vercel login. The initial database
contains 30 synthetic cases, eight institutions and six demo users.

The GitHub repository is connected to this Vercel project. Pushes to `main`
automatically deploy to production, with deployment status reported to GitHub.

Verification: 214 local backend tests and 44 local frontend checks passed. The
43 applicable frontend/API checks also passed against the public URL; the
development-only Vite document check was excluded from the cloud run. Report
JSON and CSV parity, exact-ID overlap results and role restrictions were checked.
The browser also saved a reviewed link, created request #1 (Fee records,
2025-26), and acknowledged it with Vikram Singh as owner and 27 October 2026 as
the follow-up date. Refresh and an independent API read confirmed persistence;
the original case status stayed unchanged. This request remains available as a
synthetic judging example at `/#overlaps/1/2`.

CaseBridge is a student prototype with synthetic records. The officer selector
is a demonstration of roles, not account authentication. Never upload real
complaints, personal documents or production credentials to this deployment.

## Hosting

The linked Vercel project is `casebridge` in the `aaron-0610` account. Vercel
Services (Beta) builds the React frontend and FastAPI backend together. Requests
under `/api` go to Python; all other requests go to the frontend. PostgreSQL
must be a separate, dedicated demo database. The free Neon plan is sufficient
for this prototype; no paid resource is required.

1. Accept the Neon marketplace terms in your Vercel account. The CLI cannot
   complete installation until the account owner does this.
2. Install the free database:
   `npx vercel integration add neon --billing-plan free_v3 --name casebridge-demo --meta region=sin1 --meta auth=false --no-claim --no-env-pull`
3. Pull the production environment to an ignored local file with
   `npx vercel env pull .vercel/.env.production.local --environment production`.
   Never print or commit its values. Keep the provider's `DATABASE_URL`, including
   its SSL query parameters; standard PostgreSQL URLs use psycopg automatically.
   Do not change the local development
   `.env` or copy the local database.
4. With that dedicated cloud URL loaded into the current process, run
   `python -m backend.bootstrap_demo`. It creates an empty database's schema,
   applies the region migration and inserts bundled synthetic records. Reruns
   preserve existing work. Partial or unfamiliar schemas fail transactionally.
5. Set `DEMO_TODAY=2026-10-24` in Vercel to keep the seeded judging scenario
   consistent. Run `npx vercel deploy --prod --yes`.
6. Verify `/api/health`, the case register, overlap comparison, role selection,
   request acknowledgment and Reports/CSV on the public URL. Refresh the page
   to confirm saved changes persist. Use synthetic test records only.

`.vercelignore` excludes local credentials, virtual environments, generated
slides, screenshots and test files from uploads. No database creation or seed
reset runs automatically during application startup.

## Branding

The header uses the original AICTE emblem; its official source is recorded in
`frontend/public/ASSET_SOURCES.md`. The header and footer explicitly identify
this as a student SIH prototype, not an official AICTE service.
