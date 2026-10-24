# CaseBridge - Slice 6

Synthetic data only. Slices 0-4 provide the backend and Slice 5 the overview.
Slice 6 adds the filtered case register/entry form, workspace with actions/history,
and institution profiles. Frontend: 5173; backend: 8000. User verification and a
browser checklist are required before acceptance or commit.

## Verify on Windows PowerShell

Start Docker Desktop with Linux containers. From PowerShell:

~~~powershell
cd C:\SIH26\CaseBridge
.\scripts\verify.ps1
~~~

The script preserves existing .env credentials. If absent, it copies the example
with a generated local password. It loads environment values without adding a
dotenv dependency. DATABASE_URL must use postgresql+psycopg://. Python 3.11+ is
required. The script creates .venv if needed, installs the unchanged requirements,
checks Docker and dependency consistency, starts PostgreSQL, applies the approved
raw-region migration, checks six tables, seeds missing rows, runs all backend regressions, builds the frontend,
and starts temporary backend/frontend servers for HTTP and frontend checks. Stop another server on port
8000 before running it. Failures print a named FAIL and stop immediately.

Expected key output (tool messages and test duration vary):

~~~text
Migration: cases.raw_region nullable TEXT available
PASS: Approved raw-region migration
6 tables: action_log, case_links, cases, coordination_requests, institutions, users
Seed: 6 users, 8 institutions, 30 cases
169 passed in ...s
PASS: Slice 0-6 regression tests
PASS: Frontend production build
PASS: HTTP /health (200; database ok)
PASS: HTTP /cases (30 cases; all eight filters)
PASS: HTTP /overlaps (INST-0001, INST-0003, INST-0006, INST-0008)
PASS: HTTP PGRC-109 unresolved; excluded from overlaps
PASS: HTTP invalid filters rejected (422)
PASS: HTTP acceptance checks
PASS: HTTP case detail and chronological history
PASS: HTTP institution profile and bureau history
PASS: HTTP supervisor creation denied (403; audit persisted)
PASS: HTTP supervisor action denied (403; audit persisted)
PASS: HTTP PGRC-to-RB action denied (403; audit persisted)
PASS: Slice 2 HTTP acceptance checks
PASS: HTTP case reload includes links and coordination requests
PASS: HTTP supervisor link review denied (403; audit persisted)
PASS: HTTP coordination validation and missing resources (422/404)
PASS: Slice 3 HTTP acceptance checks
PASS: HTTP dashboard totals and bureau workload
PASS: HTTP computed alert case lists
PASS: HTTP seven JSON reports and downloadable CSVs
PASS: Original Slice 4 regional acceptance
PASS: Slice 4 HTTP acceptance checks
PASS: Frontend proxy ready (5173 to 8000)
PASS: Frontend overview and case checks (21 tests)
Verification servers stopped; PostgreSQL left running.
~~~

On the existing unmigrated 30-case demo, the migration should also print:

~~~text
Column added: true; source regions backfilled: 30
~~~

On subsequent runs it should print false and 0 instead. A clean empty database
backfills 0 rows before seeding; the new seed imports preserve source regions.
Seed reports 0 new cases on reruns and 30 on first load. These are expectations,
not a claim that this version has passed live verification. Test descriptions are
'author-run on constructed data' when executed by the user.

Both temporary verification servers are stopped afterward, leaving PostgreSQL running. Logs
are backend/verify.stdout.log and backend/verify.stderr.log, ignored by Git.
Live checks intentionally leave four denied audit rows per full run; cases,
links and requests are preserved. A first migration adds one schema audit plus
one update audit for each backfilled source region. Routine reruns add no
migration/backfill audit entries when nothing changes.

## Slice 5 frontend run and manual check

Use the cumulative verifier and then the development launcher:

~~~powershell
cd C:\SIH26\CaseBridge
.\scripts\verify.ps1
if ($?) { .\scripts\dev.ps1 }
~~~

The last command prints Frontend: http://127.0.0.1:5173 and Backend:
http://127.0.0.1:8000. Keep that window open, open the frontend URL yourself,
and press Ctrl+C to stop both owned development servers after checking the UI.
The development launcher does not install packages, run migrations or start Docker;
run verification first. Separate manual terminal commands and the full click-through
checklist are in frontend/README.md.

The verifier also checks Node/npm, installs the authorized frontend dependencies,
builds, starts a temporary Vite server and runs the cumulative frontend tests. It uses
npm install on first setup and npm ci when package-lock.json exists; commit the
generated frontend/package-lock.json after checks pass. Root .gitignore already
excludes node_modules, dist, .env and log files. No additional Python dependency
or schema change was introduced for Slice 5. Declared npm packages are React,
React DOM (React's browser renderer), Vite and recharts only; Vite handles JSX
without an extra React plugin. Tests use Node's built-in runner.

Expected new PASS lines include Node and npm available, Frontend dependencies
installed, Frontend production build, Frontend port 5173 available, Temporary
frontend started, Frontend proxy ready (5173 to 8000), and Frontend API and role
checks (8 tests). These run alongside all Slice 0-4 checks. Tests and a build do
not prove browser rendering or click behavior; complete the manual checklist too.

A read-only GET /demo/users supplies actual PostgreSQL IDs/names/roles/bureaus;
initial discovery cannot send a selected user ID. After selection every data
request uses X-User-Id via the shared client. GET /demo/me validates that identity
without writing an audit row. Invalid identity reads return 403; all earlier
write authorization and denied-write audit behavior remain unchanged.

Officer workspace shows its bureau totals, assigned-open workload and
bureau-scoped alert flags. Supervisor workspace shows all-bureau oversight,
read-only role, institution/bureau counts and regional coverage. Main status
cards and the chart explicitly remain global for either role. No fixture users,
seed IDs or case counts are embedded in production UI code. Data requests run
in parallel and cancel on selection change; stale users' snapshots are guarded.
Loading/errors/empty users have retry feedback. Slice 6 adds case forms/workspaces below. Link-review UI and the Reports tab remain
reserved for their later slices.

Quick checklist: Anita Rao -> PGRC 17 cases, 7 assigned open; Rahul Mehta -> RB 11,
5 assigned open; Dr. R. K. Sharma -> supervisor/read-only, 25 open, 8 institutions,
3 bureaus. Global total stays 30; chart PGRC 17, RB 11, OTHER 2. Switch quickly,
refresh, inspect X-User-Id in Network, and check keyboard/mobile layout. Full
expected global/alert/region counts are in frontend/README.md. The role panels
implement the officer/supervisor distinction in the kickoff rules; no separate
role-table document was present in the supplied local folder.

## Slice 6 case views and persistence

Run the same cumulative command block above after stopping a previous dev session
with Ctrl+C. Expect 169 backend tests and 21 frontend tests, plus every earlier
HTTP check and the production build. The five new backend cases invoke the actual
frontend payload builders with Node, then exercise FastAPI/PostgreSQL commits in
rollback-isolated tests. Node/npm availability is therefore checked before pytest.
No backend behavior, schema, seed file, expected outcome or npm dependency changed.
Only the npm test command now includes the new case tests alongside overview tests.

Native hash URLs are #overview, #cases, #cases/{id}, #institutions/{id}. They allow
reload and Back/Forward without a router package. User IDs remain database-backed,
reads cancel on page/user changes, and pages key their state to both. Saving
single-flights a mutation and disables header user/navigation controls. Success
uses the committed server response and its history; no fake action is appended.
Unmounted pages cannot redirect on a late save completion, and writes are never
automatically retried after a network error.

Case register has all eight filter criteria, Apply/Clear, matching count, case
and institution links, and a New case form for officers. It submits only that
user's bureau and eligible officer choices; unknown IDs remain unresolved. Raw
reported region is retained. Blank received date delegates to DEMO_TODAY. Backend
403/409/422 responses are shown, and write authorization is still checked there.

Case workspace shows fields, owner, next action, dates and chronological history.
The form supports notes/status changes, escalation and transfers with target
bureau/officer. File reference is text only. Blank next step/deadline clears it;
unchanged prefilled values remain. Supervisor and foreign-bureau views have no
write form. Institution profile shows the exact Permanent ID, address, region,
involved bureaus, all cases and expandable chronological case histories. Unresolved
cases have no guessed institution link. Link review/coordination UI remains Slice 7.

Use the full checklist in frontend/README.md. Key checks: Riverbend 7; INST-0001 5;
West 12; opening PGRC-101, adding a note/file name, reloading the same case, and
finding it again in INST-0001's expanded history. Test New case by submitting
existing PGRC-101 and checking 409, then Cancel. Successful creation is exercised
in rollback tests; adding an extra persistent case would change the reference 30.
For the same reason, manual status/transfer tests should use a throwaway database;
use a note with existing status/deadline unchanged for this reference walkthrough.

The assistant could compile the frontend with the dependencies installed by the
user in Slice 5; the build passed. It did not install packages, start Docker,
open a browser or run database/proxy integration tests. Browser rendering and
interaction remain user checks. Commit message after verified output and browser
check: slice 6: add case register workspace and institution profiles.

## Approved raw-region schema exception

The original cases table could not retain PGRC-109's CSV region because its
institution identity is unresolved. The user approved adding nullable TEXT
cases.raw_region through backend/migrate_raw_region.py. This extends the runtime
schema but leaves schema.sql, seed_cases.csv, seed_users.csv and
expected_outcomes.md unchanged. There are still exactly six tables; no migration
service or new library was added.

The migration runs in a PostgreSQL transaction and takes an advisory transaction
lock to serialize repeated invocations. It adds the column if missing, validates
an existing column's type/nullability, then fills only null raw_region values
from the bundled CSV using exact case_code equality. It never guesses an
institution from a name, changes institution_id/identity_resolved, overwrites an
existing source region, resets case work, or changes links/coordination. Each
filled case gets an update audit. Any failure rolls back the transaction.

New seed imports and POST /cases preserve raw_region. Case creation accepts an
optional nonblank raw_region string; omission leaves it null. Effective region
uses the registered institution region first and falls back to the reported
raw_region. The same rule is used by API fields, case filters, dashboard and
reports. Missing both produces an Unknown bucket. Source region does not establish
institution identity. PGRC-109 remains identity_resolved false, institution_id
null, and appears in no overlap despite counting under Central.

The previously observed Central 4/Unknown 1 limitation is addressed in code by
this approved extension, not by weakening the original target. The final HTTP
check still requires Central 5, East 6, North 2, South 5 and West 12. It also
checks that Central filtering returns five cases including unresolved PGRC-109.
The old schema-only functional assertion was updated to this approved behavior;
no prior Slice 0-3 assertion or original expected-outcome file was weakened.

## Individual backend commands

After Docker setup and dependency installation:

~~~powershell
. .\scripts\load_env.ps1
.\.venv\Scripts\python.exe -m backend.migrate_raw_region
.\.venv\Scripts\python.exe -m backend.seed
.\.venv\Scripts\python.exe -m backend.check_db
.\.venv\Scripts\python.exe -m pytest backend\tests -q
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
~~~

Always migrate before seeding/starting this version, including on a clean
database initialized from the unchanged schema.sql. Stop the foreground server
with Ctrl+C. In another PowerShell terminal:

~~~powershell
curl.exe -i http://127.0.0.1:8000/health
curl.exe "http://127.0.0.1:8000/cases?institution_name=Riverbend"
curl.exe "http://127.0.0.1:8000/cases?region=Central"
curl.exe http://127.0.0.1:8000/dashboard/summary
curl.exe http://127.0.0.1:8000/alerts
curl.exe -OJ http://127.0.0.1:8000/reports/bureau-wise.csv
~~~

## Case register and writes

GET /cases returns a JSON array sorted by case_code. Filters combine with AND:

| Parameter | Matching |
| --- | --- |
| institution_name | Literal case-insensitive substring, including unresolved raw names |
| aicte_id | Exact registered AICTE Permanent ID |
| case_code | Exact case code |
| bureau | RB, PGRC or OTHER |
| region | Exact effective region: institution, then reported region |
| category | Exact category |
| status | Exact schema status |
| received_from, received_to | Inclusive received_on date range, YYYY-MM-DD |

Invalid dates/bureaus/statuses and reversed date ranges return 422; no matches
return an empty array. GET /cases/{id} adds chronological history, links and
coordination_requests. History orders by timestamp then log ID. Missing resources
return 404. GET /institutions/{id} returns permanent ID, address, region, bureaus
involved and all cases with histories. Denied actors do not add involved bureaus.

POST /cases requires case_code, institution_name and bureau. Optional fields:
aicte_id, raw_region, officer_id, category, description, received_on, status,
remarks, next_action, expected_disposal_on. received_on defaults to DEMO_TODAY;
status to pending; owner to acting user. Known exact institution IDs resolve;
unknown/missing IDs retain raw values. New institutions are never created by this
endpoint. Nonblank identity names/codes/remarks are required; extra fields are
rejected. Creation returns 201 plus details and audit. Duplicate codes return 409.

POST /cases/{id}/actions requires remarks, with optional file-name-only doc_ref,
next_action, expected_disposal_on and status. event_type defaults to update.
Escalation uses event_type escalate and sets status escalated. Transfer uses
transfer with a different to_bureau and an officer_id in that bureau; it changes
bureau, owner and status transferred. The source bureau then loses write access.
Explicit null clears a next step/deadline; omitted fields preserve it. Closing one
case via an update to disposed never changes another case or its links/requests.
last_action_on uses DEMO_TODAY; audit timestamps use PostgreSQL now().

Reads are available without a header. Every write requires an existing demo
X-User-Id. Supervisors are read-only; officers may write only in their bureau
(access is not limited to the assigned officer). Denials return 403 and commit
an audit row; successful writes commit their mutation and audit together.
Validation/conflict errors make no case changes. X-User-Id is a demo switch, not
production authentication. No authentication library was added.

## Seeding and identity

The explicit demo bootstrap loads six users first and establishes eight
institutions from nonempty exact IDs in the supplied synthetic CSV. The reusable
case importer resolves only existing exact IDs, matches officers by exact name
and bureau, and rejects missing/ambiguous officers. New users/institutions/cases
have create audits. Reruns preserve existing cases, statuses and histories.
Bootstrap is a local administrative operation, not a runtime writable API.

## Links and coordination

GET /overlaps recomputes institutions with non-disposed cases in at least two
distinct bureaus. It includes the banner, permanent ID and case codes, bureaus,
statuses and officers. It ignores descriptions, categories and link-review state.

POST /links accepts case_a, case_b, type (cross_bureau_overlap or related_incident),
review_state (confirmed/rejected), and reason. Rejection needs a nonblank reason.
Pairs are ordered by numeric ID and reversing a pair updates the same unique
link. Both cases must have resolved identity at the same institution; cross-bureau
links need different bureaus. Only officers from either involved bureau may
review. Both histories receive link_review audits. No automatic merge or closure.

POST /coordination/check accepts link_id, action_type, doc_category and period.
Optional category/period nulls match null; strings are trimmed, not fuzzily
matched. It returns warning, existing_request and choices. Matching covers
pending statuses requested/acknowledged/in_progress across currently confirmed
links at the same institution. Requester and target bureau are not matching keys.
Different category/period/action does not warn. The check creates no request.

POST /coordination adds to_bureau and optional follow_up_on. The target must be
the other linked bureau. Save rechecks under an institution row lock. A duplicate
without a choice returns 409 with warning and creates nothing. decision coordinate
returns 200 with the existing request and audits the choice; a stale choice
returns 409. decision proceed_separately requires nonblank proceed_reason and
creates a new row (201) without changing the original. No match creates normally.
An optional initial follow_up_on enables the unacknowledged reminder alert.

POST /coordination/{id}/ack requires owner_id and follow_up_on. Only target-bureau
officers may acknowledge, and the owner must be an officer there. It transitions
requested to acknowledged and records coord_ack on both histories. Acknowledged
items still warn. POST /coordination/{id}/complete accepts {} or remarks; only
the target bureau may complete a pending item. Completed/declined items do not
warn and cannot be completed again. Completion uses audit event update because
the original schema has no coord_complete event. Rejecting a link does not
silently close requests; target officers can still explicitly complete them.

## Dashboard, alerts and reports

GET /dashboard/summary returns as_of, total, five statuses, open workload, overdue,
due_within_7_days, unresolved_cases, and bureau_wise/region_wise/institution_wise
status tables. Unresolved cases remain separate rows in institution reports.
Data is queried through SQLAlchemy and aggregated in Python for the prototype;
endpoints never read CSVs or return hard-coded totals.

At DEMO_TODAY=2026-10-24: total 30; pending 10; under_process 12; escalated 2;
transferred 1; disposed 5; open 25; overdue 7; due within 7 days 7. Bureaus:
PGRC 17, RB 11, OTHER 2. Regions: Central 5, East 6, North 2, South 5, West 12.

GET /alerts recomputes these lists on each read:

| Key | Rule |
| --- | --- |
| overlap | Open cases in at least two bureaus at one resolved institution |
| pending_too_long | Pending, received strictly more than 30 days ago |
| due_within_7_days | Non-disposed, due today through today+7 inclusive |
| overdue | Non-disposed, deadline strictly before today |
| escalated | status escalated |
| unacknowledged | Requested, no acknowledgment timestamp, follow-up strictly before today |

No deadline means no due/overdue alert. Alert comparisons and ageing use
get_demo_today on each read. DEMO_TODAY defaults to 2026-10-24; invalid ISO dates
fail clearly. Follow-up dates are explicit inputs. No business rule uses wall time.

GET /reports/{type} returns type, as_of, ordered columns and rows.
GET /reports/{type}.csv returns a downloadable table with Content-Disposition.

| Type | Contents |
| --- | --- |
| institution-wise | Institution status/workload, unresolved cases individually |
| bureau-wise | Bureau status/workload |
| region-wise | Effective region status/workload |
| status-wise | Five statuses and counts |
| ageing-buckets | Open-case received ages: 0-7, 8-30, 31-60, 61-90, 91+ days |
| disposal-rate | Overall and bureau disposed/total percentages |
| overlapping-cases | One open-case row per overlapping institution |

Ageing totals at reference date: 0, 6, 6, 4, 9 (25 open cases). Future received
dates clamp to age zero. Overall disposal rate: 16.67%. Overlap report: 15 case
rows across four institutions. Unknown report types return 404. Empty databases
return zero totals, empty alerts and no division errors. CSVs escape formula
prefixes in untrusted text without changing stored or JSON values.

## Tests, lifecycle and workflow

There are 169 backend tests/cases and 21 Node integration tests through the real
Vite proxy. Five new rollback-isolated backend cases verify production frontend
form payloads against PostgreSQL; the 13 new Node cases cover register/workspace
behavior alongside the eight earlier overview checks. The approved region behavior
is checked against the original target; the migration is tested for repeatability,
audit correctness, exact-code mapping and preservation. All data mutations in
tests roll back. Tests never skip, use SQLite, or commit test records permanently.
ASGI tests use Python's standard library instead of an extra HTTP client package.
Multi-process concurrency/load tests and automated browser rendering are not claimed;
frontend click-through verification is performed by the user.

Compose exposes only PostgreSQL at 127.0.0.1:5432. It mounts unchanged schema.sql
for first initialization of an empty named volume. Restarting preserves data.
Changing .env does not change an existing database's credentials. Only the
approved raw-region migration extends that initial schema; no create_all or
additional service is used.

~~~powershell
docker compose stop
docker compose start
~~~

One slice at a time. The assistant must not run Docker, install packages or open
a browser. Update scripts/verify.ps1 cumulatively, provide RUN THIS, expected
output, unrun checks and a commit message, then await user output. Do not claim
a slice is done. Fix failures from actual user output and wait for explicit
permission to proceed to the next slice. Commit/push only after verification is
green. Preserve all four original input files. The nullable raw_region migration
is the explicit user-approved exception to matching the original runtime schema.
