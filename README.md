# CaseBridge - Slice 3

Synthetic data only. Slice 3 adds manual link review, institution-wide repeated-
action warnings, coordination, target-bureau acknowledgment and completion.
Existing health, seeding, filters, case writes, permissions and histories remain.
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
checks six tables, seeds demo data, runs all 118 tests, and starts a temporary backend
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
PASS: Slice 0-3 regression tests
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
PASS: HTTP case reload includes links and coordination requests
PASS: HTTP supervisor link review denied (403; audit persisted)
PASS: HTTP coordination validation and missing resources (422/404)
PASS: Slice 3 HTTP acceptance checks
Verification backend stopped; PostgreSQL left running.
~~~

Also expect these data/test results:

~~~text
6 tables: action_log, case_links, cases, coordination_requests, institutions, users
Seed: 6 users, 8 institutions, 30 cases
118 passed in ...s
~~~

Seeding reports 30 newly inserted cases on a fresh database, or 0 on a rerun.
There are 2 Slice 0 tests, 28 Slice 1 cases, 37 Slice 2 cases, and 51 Slice 3
cases, including parameterized tests. These are author-run on constructed data when executed by the user.
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
closing affect only the selected case. These case actions never merge cases, create links or coordination requests, or
automatically close another case. Link/coordination operations use Slice 3 routes.

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

## Slice 3 links and coordination

All following POSTs require X-User-Id from an existing demo user. Officers must
belong to at least one of the linked cases' current bureaus. Supervisors and
uninvolved bureaus receive 403 with a committed denied audit row. Reads remain
available through GET /cases/{case_id}, now including links and
coordination_requests alongside the existing history. Reloading this endpoint
loads persisted rows from PostgreSQL. No new read endpoint is needed.

Use real database IDs from the case register and returned link/request payloads;
the numeric IDs in the examples below are illustrative only.

### Link review

POST /links accepts:

~~~json
{"case_a":1,"case_b":2,"type":"cross_bureau_overlap","review_state":"confirmed"}
{"case_a":1,"case_b":2,"type":"cross_bureau_overlap","review_state":"rejected","reason":"Unrelated incidents"}
~~~

The pair is canonicalized by numeric ID so reversing it updates the same unique
link. Both cases must have resolved identity and the same institution_id. Missing,
unknown or different institutional identities return 422. Cross-bureau overlap
links require different bureaus. A related_incident link may instead be reviewed
within one bureau. Only confirmed/rejected reviews are accepted from the client;
there is no automatic confirmation or suggestion creation. Rejection requires a
nonblank reason. Reviewed user/time, state and reason are saved; both case histories
receive link_review entries. Cases are never merged or closed by a review.
Institution overlap alerts still depend only on open cases across bureaus, so
rejecting a link does not suppress an institution alert.

### Repeated-action check and save

POST /coordination/check accepts only matching fields:

~~~json
{"link_id":1,"action_type":"Document request","doc_category":"Fee records","period":"2025-26"}
~~~

The link must currently be confirmed. A matching pending request returns:

~~~json
{"warning":true,"existing_request":{"id":1},"choices":["coordinate","proceed_separately"]}
~~~

existing_request in the real response contains the complete database-backed
request, requester, owner, status and dates, not just its ID. With no match, warning
is false, existing_request is null, and choices is an empty array. The check alone
creates no request or successful audit row.

Matching uses the same institution, an existing request on a currently confirmed
link, and exact action_type/doc_category/period, with status requested,
acknowledged or in_progress. Null optional fields match null. Existing requests on
other confirmed pairs at the same institution are also checked. Neither requester
nor target bureau is part of the matching key: a second officer requesting the
same work in the opposite direction still sees the warning. No name/NLP matching
is used. The three text fields are trimmed and blank values are rejected.

POST /coordination accepts the same fields plus to_bureau. The target must be the
other linked bureau, not the acting officer's bureau. Without an existing match,
a new request is saved (HTTP 201):

~~~json
{"link_id":1,"action_type":"Document request","doc_category":"Fee records","period":"2025-26","to_bureau":"PGRC"}
~~~

If the final save finds a match and no decision was supplied, it returns HTTP 409
with the warning payload and creates nothing. The save rechecks under a PostgreSQL
institution-row lock, so a prior clear check is not sufficient to bypass a request
saved by someone else. The same institution lock is used across its different
confirmed links. This concurrency protection is implemented but the tests do not
claim to be a simultaneous multi-process load test.

To coordinate, resubmit with decision coordinate: HTTP 200, outcome coordinated,
request pointing to the existing row, no duplicate. Both case histories record the
choice. If that request has stopped matching, return 409 and ask the caller to
check again instead of silently creating a new request.

To proceed separately, resubmit with decision proceed_separately and a nonblank
proceed_reason. The new row and its reason are stored (HTTP 201, outcome created);
the original request remains unchanged. Missing reasons return 422. Different
action types, periods or document categories do not match and can be saved without
a warning. to_bureau and decision are not accepted by the read-only /check body.

### Acknowledgment and completion

POST /coordination/{request_id}/ack accepts:

~~~json
{"owner_id":1,"follow_up_on":"2026-10-30"}
~~~

Only officers of the request's target bureau may acknowledge; the named owner
must also be an officer of that bureau. Both owner_id and follow_up_on are
required. Only requested items may transition to acknowledged. Owner, follow-up
and acknowledgment timestamp are saved, and both histories receive coord_ack.
Acknowledged requests still trigger repeated-action warnings.

POST /coordination/{request_id}/complete accepts an empty JSON object or remarks:

~~~json
{"remarks":"Requested records received"}
~~~

Only the target bureau may mark a pending item completed. Completed/declined
requests cannot be completed again. Completion uses action_log.event_type update
because the immutable schema has no coord_complete event. Completed requests no
longer warn. Reviewing a link as rejected does not silently close its requests;
the target bureau may still explicitly complete them. Acknowledgment/new requests
require a currently confirmed link. Neither acknowledgment nor completion changes
case status. Timestamp fields use PostgreSQL now(); user-provided follow-up dates
are stored directly. There is no new use of the wall-clock date for business rules.

### Slice 3 verification behavior

The eight-step INST-0001 walkthrough in expected_outcomes.md is an actual
PostgreSQL-backed ASGI test. Other cases cover rejection without suppressing
INST-0003, required reasons, exact identity, reverse pairs, participants/target
bureau permissions and audits, stale checks, coordinate/proceed choices,
null matching, pending versus terminal states, different confirmed pairs, reloads,
and independence after disposing PGRC-101. Per-test transactions roll back all
link/request writes and updates. No seed/schema/expected-outcome edits or new
packages were made.

Live HTTP checks validate reload fields, rejected supervisor link review, and
coordination validation/missing resources. All successful workflow writes run in
the rollback-isolated tests, preserving the shared demo. Combined live checks add
four denial rows per full verification run (three from Slice 2, one from Slice 3)
and do not add or change cases, links or coordination requests.

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
