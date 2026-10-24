# CaseBridge frontend - Slice 5

React + React DOM, Vite and recharts. Plain CSS, native fetch and built-in Node
tests; no UI library, router, compiler plugin or extra testing package is declared.
Only the Overview is implemented in this slice. See the root README for the
cumulative setup, backend rules and migration.

## Verify and open the app (PowerShell from repo root)

~~~powershell
cd C:\SIH26\CaseBridge
.\scripts\verify.ps1
if ($?) { .\scripts\dev.ps1 }
~~~

Verification installs frontend dependencies, generates package-lock.json on first
installation (uses npm ci on later runs), builds, starts the backend on 8000 and
Vite on 5173, and runs eight real proxy/API integration tests. It stops both
verification servers afterward. Dev starts them again for the browser checklist;
keep that PowerShell window open and press Ctrl+C to stop both owned processes.
Open http://127.0.0.1:5173 yourself. Include package-lock.json in the verified commit.

Manual alternatives, after verification, in two terminals:

~~~powershell
. .\scripts\load_env.ps1
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
~~~

~~~powershell
cd C:\SIH26\CaseBridge\frontend
npm.cmd run dev
~~~

Individual npm commands from frontend/:

~~~powershell
npm.cmd run build
npm.cmd test
~~~

The tests require the real backend and Vite dev server to be running, plus a prior
build. They do not mock API responses and do not use a browser. A successful build
and proxy tests do not prove rendering, layout or click behavior; check these
manually below. No package installation, build, server start or browser execution
was performed by the assistant.

## Browser checklist

1. Open http://127.0.0.1:5173. Demo login lists all six database users. The reference
   date is 24 October 2026. No placeholder case counts should appear while loading.
2. Select Anita Rao. Officer workspace shows PGRC bureau, 17 bureau cases,
   14 bureau open, 7 assigned open. PGRC alert flags: 5 overdue, 3 due within seven
   days, 3 pending over 30 days. The main register cards are explicitly global.
3. Select Rahul Mehta. Officer workspace changes to RB: 11 bureau cases, 9 bureau
   open, 5 assigned open. RB flags: 1 overdue, 3 due soon, 2 pending over 30 days.
4. Select Dr. R. K. Sharma. It changes to Supervisor workspace / Cross-bureau
   supervision with Read-only role, 25 open cases, 8 institutions and 3 bureaus.
   All-bureau flags show 4 overlaps, 7 overdue, 7 due soon, 6 pending over 30 days,
   2 escalated and 0 unacknowledged. Regional coverage is shown for this role.
5. Global cards remain total 30, pending 10, under process 12, disposed 5, overdue
   7, due within seven days 7, escalated 2, transferred 1. The chart shows OTHER 2,
   PGRC 17 and RB 11. It is labeled All bureaus and includes disposed cases.
6. Switch quickly between users and use Refresh overview. After loading, the
   selected name and role panel must agree; an old user's panel must not linger.
7. In browser developer tools Network, requests to /api/demo/me, /api/cases,
   /api/dashboard/summary and /api/alerts must include X-User-Id matching the
   selected user. Only initial /api/demo/users discovery is without a selection.
8. Tab through the user selector and Refresh button; the focus ring should be
   visible. Resize to mobile width: cards should stack without horizontal scroll,
   and chart values and select labels should remain readable.

## API and UI behavior

The initial read-only /demo/users catalog comes from PostgreSQL; no seed user IDs
or names are embedded in the app. Once selected, the shared client sends
X-User-Id on every data request. /demo/me validates that ID and supplies the actual
role used to build the panel. Unknown/missing IDs return 403 without a write audit
because these are reads. Existing write permissions and denial audits are unchanged.

The global register/chart intentionally remain all-bureau views for either role.
Officer panels and alerts are bureau-scoped; assigned-open counts additionally
match the selected officer ID. Supervisor panels/flags cover all bureaus. All
case values come from existing PostgreSQL-backed endpoints. No mock production
responses, fixed user IDs or displayed count fixtures are used.

Overview requests run in parallel, are aborted on user switch/unmount, and guard
against stale responses. Loading, empty catalog and request-error states have no
fabricated totals and provide retry controls. CSS respects reduced motion; the
chart has a screen-reader table. A Vite /api proxy forwards to 8000 without adding
CORS/auth libraries. There is no production deployment in this slice. Vite's
built-in JSX support is used; React Fast Refresh is not configured without an
additional plugin. No environment/database credentials are bundled into the UI.
