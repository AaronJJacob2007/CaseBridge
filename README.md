# CaseBridge - Slice 2

Synthetic data only. Slice 2 adds case creation, case details and action history,
case actions, institution profiles, and demo role/bureau permission enforcement.
Slices 0-1 health, table checks, seeding, case filters and overlaps remain.
The frontend is reserved for Slice 5.

## Run verification (Windows PowerShell)

Start Docker Desktop with Linux containers. From PowerShell:

~~~powershell
cd C:\SIH26\CaseBridge
.\scripts\verify.ps1
~~~

The script preserves an existing .env. If absent, it creates one from
.env.example with a generated local password. It loads only the environment
keys documented in that example, without adding a dotenv dependency.

The script checks Docker/Compose, creates .venv if needed, installs the unchanged
backend/requirements.txt, checks dependency consistency, starts only PostgreSQL,
checks six tables, seeds demo data, runs all 67 tests, and starts a temporary backend
on 127.0.0.1:8000 for real HTTP checks. It stops at the first failure and prints a
short FAIL line. It never resets the database. Stop any existing server on 8000
before verification. The temporary backend is stopped afterward; PostgreSQL
remains running. Backend startup logs are backend/verify.stdout.log and
backend/verify.stderr.log (ignored by Git).

Expected PASS lines (other tool output and durations vary):

~~~text
PASS: Environment loaded
PASS: Docker Compose available
PASS: Docker engine reachable
PASS: Compose configuration
PASS: Python environment
PASS: Dependencies installed
PASS: Dependency consistency
PASS: PostgreSQL healthy
PASS: Six database tables
PASS: Demo seed loaded
PASS: Slice 0-2 regression tests
PASS: Backend port 8000 available
PASS: Temporary backend started
PASS: Backend ready
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
Verification backend stopped; PostgreSQL left running.
~~~

Also expect these data/test results:

~~~text
6 tables: action_log, case_links, cases, coordination_requests, institutions, users
Seed: 6 users, 8 institutions, 30 cases
67 passed in ...s
~~~

Seeding reports 30 newly inserted cases on a fresh database, or 0 on a rerun.
There are 2 Slice 0 tests, 28 Slice 1 cases, and 37 Slice 2 cases, including
parameterized tests. These are author-run on constructed data when executed by the user.
No live verification is claimed until the user supplies output.

## Individual commands and development server

After the environment/dependencies/database are set up, individual commands are:

~~~powershell
. .\scripts\load_env.ps1
.\.venv\Scripts\python.exe -m backend.seed
.\.venv\Scripts\python.exe -m backend.check_db
.\.venv\Scripts\python.exe -m pytest backend\tests -q
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
~~~

The last command stays in the foreground; stop it with Ctrl+C. In a second
PowerShell terminal:

~~~powershell
curl.exe -i http://127.0.0.1:8000/health
curl.exe "http://127.0.0.1:8000/cases?institution_name=Riverbend"
curl.exe "http://127.0.0.1:8000/cases?case_code=PGRC-109"
curl.exe http://127.0.0.1:8000/overlaps
~~~

These should show HTTP 200 /health with database ok, 7 Riverbend cases, one
unresolved PGRC-109 record, and the four expected institution alerts respectively.
The frontend is reserved for Slice 5, with port 5173. There is no frontend server
to start in Slice 1. No packages were added to requirements for this slice.

## Case API contract

GET /cases returns a JSON array sorted by case_code. Filters combine with AND:

| Query parameter | Matching |
| --- | --- |
| institution_name | Literal case-insensitive substring; includes unresolved raw names |
| aicte_id | Exact registered AICTE Permanent ID |
| case_code | Exact case code |
| bureau | Exact RB, PGRC or OTHER |
| region | Exact institution region |
| category | Exact category |
| status | Exact schema status |
| received_from, received_to | Inclusive received_on date range, YYYY-MM-DD |

Invalid bureau/status/date values and reversed date ranges return HTTP 422.
An unmatched filter returns an empty array. Unresolved records have null
institution_id and aicte_id, identity_resolved false, and retain raw identity.

GET /overlaps recomputes from PostgreSQL on each request: resolved institutions
with non-disposed cases in at least two distinct bureaus. Each alert includes the
required banner, permanent ID, institution name, and open cases with codes,
bureaus, statuses and officer names. Categories/descriptions are irrelevant.
No suggested links are persisted or automatically confirmed.

## Slice 2 write and history API

GET /cases/{case_id} returns all case fields plus history, sorted by audit time
then log ID. Each history entry includes event_type, remarks, doc_ref, actor,
bureau and timestamp. GET /institutions/{institution_id} returns its permanent
ID, name, address, region, campus, bureaus_involved, and all its cases (including
disposed cases) with their individual histories. Previous bureaus recorded in
successful action history are included; denied attempts do not make a bureau
involved. Missing resources return 404. Reads remain available without a demo
header; writes require X-User-Id to match an existing database user.

POST /cases accepts:

~~~json
{
  "case_code": "PGRC-DEMO-NEW",
  "aicte_id": "INST-0001",
  "institution_name": "Riverbend Institute of Technology",
  "bureau": "PGRC",
  "category": "Fee collection",
  "description": "Synthetic complaint",
  "remarks": "Case registered",
  "next_action": "Review complaint",
  "expected_disposal_on": "2026-11-30"
}
~~~

case_code, institution_name and bureau are required. received_on defaults to
DEMO_TODAY; status defaults to pending. officer_id defaults to the acting user
and may instead name another officer in the same bureau. Known exact aicte_id
values resolve to the existing institution. Missing/unknown IDs retain the raw
identity and do not create institutions or links. Extra fields are rejected;
clients cannot set identity_resolved or actor_id. Creation returns HTTP 201 with
the full case and its create audit entry. A duplicate case code returns 409.

POST /cases/{case_id}/actions accepts these variants:

~~~json
{"event_type":"update","remarks":"Reply received","doc_ref":"reply.pdf","next_action":"Review reply"}
{"event_type":"escalate","remarks":"Senior review required"}
{"event_type":"transfer","remarks":"Transfer for RB review","to_bureau":"RB","officer_id":123}
{"event_type":"update","remarks":"Case disposed independently","status":"disposed"}
~~~

123 is an illustrative target officer ID, not a fixed seed ID. Obtain real IDs
from the case register's officer_id values; tests look them up by exact user name.
The acting demo user's numeric ID is sent in the X-User-Id header.

Remarks are required and nonblank. doc_ref is only a simulated file name, with
no upload or filesystem path. event_type defaults to update. Updates may set
status (except escalation/transfer, which require their matching event types),
next_action and expected_disposal_on. Explicit null clears either optional next
step/deadline; omission preserves it. last_action and last_action_on are updated
from remarks and DEMO_TODAY. Audit timestamps continue to use schema.sql's now()
default, distinct from the configurable business date.

Escalation sets status escalated. Transfer requires a different target bureau and
an officer in that bureau, changes bureau/owner, and sets status transferred.
The source bureau loses write access after transfer; the target bureau gains it.
The transfer audit records the acting source officer and bureau. Updates and
closing affect only the selected case. No case links, merges, coordination or
automatic closure of another case are implemented in Slice 2.

Supervisors are read-only. Officers may create/update only cases in their bureau;
access is bureau-based, not restricted to the assigned officer. Missing/invalid
users, supervisor attempts and foreign-bureau attempts return 403 and commit a
denied action_log entry. Valid writes commit their case change and audit row in
one transaction. Invalid bodies return 422; absent resources 404; rejected
validation/conflicts do not make case changes. X-User-Id is a demo identity switch,
not production authentication. No authentication library or new dependency was
added.

Verification keeps all earlier checks. The 37 new tests execute the actual
FastAPI ASGI routes with PostgreSQL SAVEPOINTs inside an outer test transaction;
route commits cannot commit that outer transaction. All test mutations are rolled
back. Python's standard library supplies the ASGI test harness, so no HTTP client
package was added. Live HTTP verification reads case/profile history and makes
three forbidden requests. Those requests intentionally leave three denial audit
rows on each verification run, while keeping all 30 cases unchanged. A separate
PostgreSQL session checks that each denied audit row was committed.

## Seed identity and audit behavior

There is no separate institution-register input file. The explicit demo bootstrap
uses nonempty exact IDs from the bundled synthetic seed_cases.csv to establish
eight institutions, after loading the six users. This is demo master-data setup,
not identity verification against AICTE. The reusable import_case_rows function
only looks up existing exact IDs: unknown/missing IDs stay unresolved even when
the institution name resembles a registered institution. It never creates an
institution. Officer names match exactly and must identify one officer in the
case's bureau; otherwise the seed transaction fails.

Seed reruns skip existing case codes and existing institutions. They never reset
case status, officer work, links or coordination. Conflicting/ambiguous existing
user names fail clearly. New users, institutions and cases each receive a create
action_log row; bootstrap user/institution rows have no case_id and no actor.
The seed is an explicit local administrative operation, not a writable API.
Runtime write permissions are implemented in Slice 2.

Tests seed within per-test PostgreSQL transactions and roll back their mutations.
They do not drop/recreate schema tables, commit synthetic test cases, or change
the supplied four protected inputs. PostgreSQL sequence IDs can advance during
rolled-back tests; tests and UI must not rely on fixed numeric IDs.

## Known input/schema limitation

PGRC-109 has region Central in the CSV but no resolved institution. The unchanged
cases table has no raw-region column. Its API region is therefore null and region
filters use only the registered institution region. The supplied expected Central
total of 5 in Slice 4 includes this unresolved case; the schema retains region for
only the other 4 Central cases. This needs a user decision before Slice 4; neither
the schema nor expected_outcomes.md has been changed to hide the mismatch.

## Configuration and database lifecycle

DATABASE_URL must come from the environment and use postgresql+psycopg://.
DEMO_TODAY defaults to 2026-10-24 and is validated as an ISO date. All future rules
requiring today's date must call backend.config.get_demo_today rather than the
wall clock. Date-relative alerts are scheduled for Slice 4.

Compose exposes PostgreSQL on 127.0.0.1:5432 and mounts the unchanged schema.sql
read-only for initialization of an empty named volume. Restarting preserves data;
changing .env later does not change credentials inside an existing database.
No migrations, create_all calls or additional services are introduced.

~~~powershell
docker compose stop
docker compose start
~~~

## Workflow for all slices

Follow Rules in GPT_kickoff_prompt.md and implement only one slice per prompt.
The assistant writes code and tests, but does not run Docker, install packages or
open a browser. Update scripts/verify.ps1 cumulatively and provide a RUN THIS
block, expected results, unrun checks and a one-line commit message. Await user
output and explicit "proceed to Slice N" before starting another slice.
Do not claim a slice is done. Fix failures from the user's actual output.
