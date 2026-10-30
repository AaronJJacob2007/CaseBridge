# CaseBridge development history

> Archived implementation notes from the original README. These retain the
> development sequence and earlier verification expectations. For the current
> product overview, setup instructions and verified test counts, see the
> [project README](../README.md). Relative paths below describe the repository
> root as they did in the original notes.

Synthetic data only. Slices 0-4 provide the backend and Slice 5 the overview.
Slice 6 adds the filtered case register/entry form, workspace with actions/history,
and institution profiles. Slice 7 adds overlap comparison, manual link reviews,
repeated-request warnings, acknowledgment and completion. Slice 8 adds seven report tables, CSV downloads and an explicit local demo reset. Frontend: 5173; backend: 8000. User verification and a
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
206 passed in ...s
PASS: Slice 0-8 regression tests
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
PASS: Frontend overview, case, coordination and report checks (44 tests)
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
Live checks intentionally leave five denied audit rows per full run; cases,
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
Loading/errors/empty users have retry feedback. Slice 6 adds case forms/workspaces below. Link review and coordination are described below; the Reports tab is available in Slice 8.

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
the target bureau may complete a previously acknowledged pending item. Completed/declined items do not
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

There are 206 backend tests/cases and 44 Node tests, including checks through the real
Vite proxy. Five new rollback-isolated backend cases verify production frontend
form payloads against PostgreSQL; the 13 new Node cases cover register/workspace
behavior alongside the eight earlier overview checks. The approved region behavior
is checked against the original target; the migration is tested for repeatability,
audit correctness, exact-code mapping and preservation. Successful test writes roll back. Live denied-write checks preserve denied audit rows. Tests never skip, use SQLite, or commit test records permanently.
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

## Slice 7 verification scope

No new endpoint, migration or dependency is needed. Frontend production helpers
build review/coordination/acknowledgment payloads. Every request submission calls
the real check endpoint first, including warning choices, and retains a 409
warning payload if a competing save happens after checking. Edited matching
fields invalidate the displayed warning. A changed/finished request requires a
fresh check rather than silently creating another request.

Six added backend tests exercise those production JS helpers and the submission
orchestration against actual ASGI/PostgreSQL responses inside rollback
transactions, including all eight reference steps, Coordinate reuse, a separate
reason, rejection, supervisor denied audit and a competing save. Eight added Node
tests cover overlap payloads, real reload/role context, input guards, routes and
a real supervisor 403. Existing acceptance assertions remain unchanged.

The API test fixture temporarily clears coordination requests/links within its
outer rollback transaction, then restores the user's persisted coordination
state at teardown. This keeps the existing seed-state assertions isolated from
manual walkthrough records; it does not delete live requests. Verify while dev
is stopped so the transactional tests do not compete with browser writes.

## Slice 7 browser walkthrough

Use Demo login Rahul Mehta. Open Overlap & coordination.
1. Expect the exact banner "Potential Overlapping Cases - Coordination Required"
   and INST-0001, INST-0003, INST-0006, INST-0008, with real cases, bureaus,
   statuses and officers. Unresolved PGRC-109 must not appear.
2. At INST-0001 choose PGRC-101 and RB-201, Compare cases, then Confirm link.
   Both case histories record the review; neither case status changes.
3. As Rahul, enter action type Document request, document category Fee records,
   period 2025-26, target PGRC. Check only: no matching pending request.
   Check and save request: a requested item appears. Leave initial follow-up
   blank for this walkthrough so it does not change the original alert counts.
4. Switch to Anita Rao (same comparison remains). Enter the same action,
   category and period; target is now RB. Check only: warning shows the saved
   request, requester, target, owner and status. Coordinate reuses it without
   creating another. Proceed separately with a blank reason shows an error.
   A successful separate-request save with reason is covered by rollback tests.
5. Change period to 2024-25 and Check only: no warning; nothing saved.
   Restore 2025-26, change category to Salary records and Check only: no warning.
6. Anita acknowledges Rahul's request: owner Anita Rao, follow-up 2026-10-30.
   Expect acknowledged, owner/date persisted. Repeat Fee records / 2025-26:
   warning still appears. Reload and reselect Anita (Demo login resets on reload).
   Confirmed review, request, acknowledgment and histories remain.
7. Anita enters completion remarks and Mark completed. Check Fee records /
   2025-26 again: no matching pending request, unless you deliberately created
   another pending request. Neither case status changes.
8. As Rahul at INST-0003 compare PGRC-104 / RB-203, reject with Unrelated incidents.
   Reload: rejected review/reason remains, and INST-0003 still appears in overlaps.
9. Switch to Dr. R. K. Sharma: side-by-side data and requests are readable;
   review/request/acknowledgment/completion forms are absent. Actual attempted
   supervisor writes are tested through the real API: 403 and persisted denied
   audit. UI error notices preserve HTTP status and server message.

Only links, requests and audit history change. Keep case statuses/deadlines and
the 30-case catalog unchanged. Check-only calls never save requests. If a request
already exists from an earlier attempt, expect the matching warning and use
Coordinate, or complete that request as its target before repeating a fresh run.
Stop dev with Ctrl+C before running verification again.


## Slice 8: clean setup, reports and explicit reset

Prerequisites on a clean Windows machine: Git, Python 3.11+ on PATH, Node.js
22.12+ (Node 24 supported), npm and Docker Desktop running Linux containers.
Clone this repository into C:\SIH26\CaseBridge, then open PowerShell:

~~~powershell
cd C:\SIH26\CaseBridge
.\scripts\verify.ps1
if ($?) { .\scripts\dev.ps1 }
~~~

Verification creates the local .env with a generated password if missing, installs
the declared Python/npm dependencies, starts the one PostgreSQL service, migrates,
seeds missing rows, runs all checks and stops its temporary servers. If setting
up manually, copy .env.example to .env and replace its placeholder password before
first database initialization. Keep DATABASE_URL and POSTGRES_PASSWORD consistent;
do not change credentials on an existing volume. No extra library is needed.
Dev prints http://127.0.0.1:5173; open it yourself and keep the terminal running.
Ctrl+C stops the two development servers. PostgreSQL persists until stopped.

Reports is a lazy-loaded #reports page available to either role. Choose any of
institution-wise, bureau-wise, region-wise, status-wise, ageing buckets, disposal
rate or overlapping cases. Tables follow the server's ordered columns and show
its as_of date. Reports cover all bureaus. Missing IDs are labelled Not supplied,
unresolved identity is No, zero remains zero and an open-ended age bucket says
No upper limit. No report guesses an institution identity. Refresh requests new
saved data. Downloads fetch the actual server CSV using X-User-Id and download
as casebridge-<type>.csv; failures retain their HTTP detail and offer another
attempt. Changing report/user cancels abandoned reads and downloads. Empty reports
show a message and can download their headers. Screen readers receive labelled
selection, table captions, column/row headings and feedback; tables scroll on
small screens. Resource errors also display their HTTP status.

### Reset only when you want to discard saved demo work

The following command permanently replaces the local synthetic demo records,
including notes, repaired statuses, audits, link reviews and coordination requests.
Stop development with Ctrl+C first, keep Docker Desktop running, then run:

~~~powershell
.\scripts\reset_demo.ps1
if ($?) { .\scripts\verify.ps1 }
if ($?) { .\scripts\dev.ps1 }
~~~

The PowerShell wrapper loads .env and refuses while ports 8000/5173 are in use.
The Python entry point also restricts the target to localhost/127.0.0.1/::1 and
the database named by POSTGRES_DB. It drops only the six named tables, executes
the unchanged schema.sql, applies the approved raw_region migration, then seeds
from the unchanged CSVs. Unexpected public tables or external dependencies cause
refusal/failure; no CASCADE, volume deletion, table outside the six or new service
is used. A transaction/advisory lock protects recreation; failures restore the
pre-reset tables and records. All previous demo work is intentionally removed
only on successful commit. Routine verification never invokes the persistent
reset. Reset tests use outer rollback transactions to restore the user's records.

Expected reset output:

~~~text
PASS: Demo reset committed (six tables, approved raw_region migration, seed loaded).
Cases: 30; pending: 10; under_process: 12; escalated: 2; transferred: 1; disposed: 5; open: 25
Previous demo actions, links and coordination requests have been removed.
~~~

Slice 8 cumulative expectations: 206 backend tests; 44 frontend tests; production
build and all earlier HTTP checks. The three reset tests check reference recovery,
repeatability, actual record preservation after outer rollback, seed-failure
rollback and refusal of unexpected tables. Eleven new Node checks compare all
seven actual report JSON/CSV tables, supervisor visibility, download errors,
cancellation and display/route helpers. These are not browser click tests.

Browser walkthrough:
1. Open Reports as Anita. Institution-wise shows 9 rows (8 institutions plus
   unresolved PGRC-109); its missing ID stays Not supplied and identity No.
2. Check bureau totals PGRC 17, RB 11, OTHER 2; region totals Central 5, East 6,
   North 2, South 5, West 12; status totals 10/12/2/1/5 in server order.
3. Ageing bucket totals are 0, 6, 6, 4, 9. Overall disposal rate is 16.67%.
   Overlapping cases has 15 rows at four institutions.
4. Download each report and open the CSV. Verify filename, column order and
   totals. Switch report/user quickly and check #reports survives refresh.
5. Switch to Dr. Sharma: all seven reports/downloads remain readable. Test
   keyboard selection and narrow-window horizontal table scrolling.
6. Optionally stop the backend in a manual two-terminal session and Refresh:
   expect an error with Try again; restore the backend and retry. Do not stop
   unrelated processes. Normal empty case searches retain their existing message.
7. After the explicit reset, Overview returns to the Slice 4 counts; PGRC-111
   is pending, links/requests are empty and only initial/migration audit history
   remains. Verification adds its usual denied audit rows. Reload the app after
   reset because old case/user IDs and hash links may no longer identify records.

The assistant ran the local build and test collection only; PostgreSQL/reset,
proxy tests, actual downloads and browser layout require the user's run.
Commit only after those checks are green:
slice 8: add report exports and transactional demo reset


Live alert acceptance also verifies persisted unacknowledged request IDs, order,
fields, follow-up date and overdue-day count against PostgreSQL. It does not
assume that browser-created requests are absent, delete them or complete them.
The original seed-only assertion (no unacknowledged requests) and all case-count
expectations remain intact. A rollback regression checks a saved overdue request,
missing/duplicate/wrong-age alerts and removal after acknowledgment.


If an earlier Slice 8 verification left slice8_unexpected_table, stop dev, load
.env with scripts/load_env.ps1, then explicitly run:

~~~powershell
. .\scripts\load_env.ps1
.\.venv\Scripts\python.exe -m backend.cleanup_slice8_test_table
if ($?) { .\scripts\verify.ps1 }
~~~

The cleanup removes only that exact empty single-column test table on the local
demo database and records an administrative audit. Unexpected structure, rows
or dependent objects block removal. It does not reset saved work. The corrected
refusal test explicitly rolls back its outer transaction and checks that the
test table is gone afterward. The verifier also rechecks six tables after pytest.


## Post-Slice 8: institutional UI polish

The follow-up UI uses formal navy/white styling, restrained status accents,
consistent controls and readable tables. Overview brings the selected bureau's
cross-bureau institution overlaps, past-due acknowledgments and overdue cases
ahead of global metrics. Three institution/case links show real records; the
full metrics, chart and supervisor region totals remain available below.
The acknowledgment count includes only requested items with a past follow-up
(as in the existing API), not every pending request. Overlap counts include
reviewed institutions and are not labelled unreviewed work.

The overlap list uses a compact four-column case table and a comparison chooser.
Comparison displays a shared exact institution identity, bureau/status cards,
case dates, next actions and expandable histories. Confirm/Reject and recorded
request controls use the existing endpoints/permissions. The duplicate warning
shows the existing request ID, status, matching fields, owner and follow-up,
then Coordinate/Proceed separately with a reason. A static four-step guide
explains the workflow; it does not imply automatic progression or completion.
There is no new dependency, backend endpoint or database mutation in this polish.

Stop dev with Ctrl+C and run the same cumulative commands:

~~~powershell
.\scripts\verify.ps1
if ($?) { .\scripts\dev.ps1 }
~~~

Expect the existing 206 backend tests, 44 frontend checks and a production build.
Browser checks: compare Overview as Anita/Rahul/supervisor; check scope labels,
counts and institution/case links; open PGRC-101/RB-201 and check the shared ID,
bureau cards, review and histories; exercise a repeated-request warning and
acknowledgment; check supervisor forms remain hidden. Use a narrow window and
keyboard navigation. Status/deadline reference totals should stay unchanged.
No reset is needed for these checks. Browser layout and live regression results
still require user verification. Commit after verification:
ui: polish institutional overview and coordination screens


The request form now offers the standard Document request action from a selector,
preventing the Document Request capitalization mismatch seen in browser testing.
Other action (specify) retains custom action types with explicit exact-matching
help. Changing the selection clears a stale warning. Document category and period
remain exact-match inputs; backend matching and saved records are unchanged.
Browser check: as Anita select Document request, enter Fee records / 2025-26,
target RB and Check only against Rahul's still-pending request. Expect the
matching request warning. Selecting Other action reveals a required custom field;
switching back restores the canonical Document request value.


## Review fixes: issue 1 - repeated actions across bureau directions

The check endpoint now accepts optional to_bureau as draft context but excludes
it from the matching keys. The form includes its selected target in prechecks.
Matching continues to use institution, currently confirmed candidate link,
action_type, doc_category, period and requested/acknowledged/in_progress status.
Requester and target bureau are not matching keys. Existing institution-wide
matching across confirmed pairs at the same institution is retained. Saving still
validates that the target is the other linked bureau and rechecks for duplicates.
No seed, schema, original expected outcome or saved record changes are required.

Three rollback PostgreSQL regressions create Rahul's Document request / Fee records
/ 2025-26 to PGRC, then check Anita's identical draft to RB. They cover all three
pending statuses, the complete existing-request warning, no precheck writes and
409 on a duplicate save. Cumulative verification expects 206 backend tests and 44
frontend checks. Issue 1 verification passed; subsequent review fixes are tracked below.
DESIGN.md was not present in the repository when issue 1 was inspected.


## Review fixes: issue 2 - acknowledgment before completion

Completion now requires acknowledged/in_progress status and a non-null
acknowledged_at timestamp, after the existing officer/target-bureau checks.
Requested or unacknowledged records return 409: Acknowledge the request before
marking it completed. Completed/declined items still return 409 on repeated
completion. A rejected link does not close requests: previously acknowledged
items can still be completed, while an unacknowledged item must have its link
confirmed again before acknowledgment. No existing records are auto-acknowledged.

The completion form is hidden until these conditions hold. Its UI helper also
checks target bureau and officer role; server authorization remains authoritative.
Six rollback PostgreSQL cases test rejection before acknowledgment (including
rejected links and status-only bypasses), success after acknowledgment/in-progress,
no case-status changes and repeat-completion rejection. Two older tests now
acknowledge first to follow the explicitly revised rule. A Node check verifies
completion visibility across states, roles and bureaus. Expect 206 backend tests
and 44 frontend checks. Seed files and expected_outcomes.md are unchanged.

Browser check: open a requested item as its target-bureau officer. Acknowledge
and assign responsibility is visible; Mark completed is absent. Choose an owner
and follow-up, acknowledge, then confirm completion remarks/Mark completed appear.
Reload before completion to verify the acknowledged state persists. Complete it,
then verify the controls disappear and the request reads completed. Supervisors
and source-bureau officers have no completion control at either stage.
Review issues 3-6 are addressed in the UI pass: overdue items sort by days overdue,
open overdue cases show a red badge, and shared styling uses centralized tokens.
Case histories remain scoped to their own case; no history query was changed.
Reports and browser-downloaded CSVs omit internal institution IDs. Browser layout
and cumulative regression checks still require verification.


## Monthly / quarterly receipt-cohort performance

Reports now includes Monthly / quarterly performance. Choose a calendar month
or quarter and year, then Apply period. Defaults use DEMO_TODAY (October 2026),
not the system clock. The JSON and CSV endpoints are:

- GET /reports/performance?kind=monthly&year=2026&period=10
- GET /reports/performance.csv?kind=quarterly&year=2026&period=3

Each table has All, PGRC, RB and OTHER rows, including zero counts. Cases received
means received_on is within the selected period, inclusive, through DEMO_TODAY.
Disposed counts those same cases whose current saved status is disposed;
outstanding counts all other current statuses. Received = disposed + outstanding.
Bureaus use current assignments, and unresolved cases are included. Dates show
calendar boundaries, receipts-through and status-as-of. Current periods are
labelled partial; future periods and invalid selections return 422.

These are current outcomes of a receipt cohort, not disposals made during the
period or historical period-end backlog. There is no reliable dedicated disposal
date or complete historical status snapshot in the original schema, so neither
is inferred from last_action_on or remarks. Reopening a case changes its current
cohort outcome. CSV retains the same dates/counts and the browser filename includes
the selected year/period. No schema, seed or expected_outcomes.md changes.

Eighteen new backend cases cover calendar boundaries, leap years, quarter ranges,
empty periods, current status/reopening, invalid/future periods, JSON/CSV parity,
and supervisor access. Four of these run without PostgreSQL. Three standalone
Node checks cover period URLs, date/zero presentation and CSV preservation.
Cumulative expectations: 206 backend cases and 44 Node checks.

Run scripts/verify.ps1, then scripts/dev.ps1. In Reports select Monthly / quarterly
performance, apply October 2026 and Q3 2026, download each CSV and compare all rows.
Check February 2024 gives zero counts with its leap-day boundary and November 2026
shows a clear future-period error. Browser layout and PostgreSQL integration tests
must be verified locally; this agent session cannot access local PostgreSQL.
