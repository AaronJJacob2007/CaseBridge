# CaseBridge frontend - Slice 7

React + React DOM, Vite and recharts only. Plain CSS, native fetch and built-in
Node tests; no new package or router dependency was added. Native hash routes:
Overview, case register, case workspace, institution profile and overlap comparison.
Reports/reset UI is reserved for Slice 8.

## Run from Windows PowerShell

If a prior scripts/dev.ps1 session is still running, press Ctrl+C there first.
Then from the repository root:

~~~powershell
cd C:\SIH26\CaseBridge
.\scripts\verify.ps1
if ($?) { .\scripts\dev.ps1 }
~~~

Expected key results: 175 backend tests passed; production build successful;
29 frontend tests passed; PASS: Frontend overview, case and coordination checks (29 tests).
All earlier HTTP checks remain. Verification stops its temporary servers. Dev
starts both again for your browser check, prints http://127.0.0.1:5173 and keeps
running until Ctrl+C. Open the URL yourself; no browser is opened automatically.

Individual commands from frontend/:

~~~powershell
npm.cmd run build
npm.cmd test
~~~

Tests require a successful build and the real Vite/backend/PostgreSQL services
running. They do not mock API responses. The assistant ran the local build using
previously installed dependencies, but did not install packages, start Docker,
open a browser or run database-backed integration checks. A build/API tests do
not prove rendering/click behavior; complete the checklist below.

## Slice 6 browser checklist (keep the 30-case reference data)

1. Select Anita Rao and open Case register. It should show 30 cases. New case is
   available for this officer. Open it, enter existing case code PGRC-101,
   institution name Riverbend Institute of Technology and AICTE ID INST-0001,
   then Save case. Expect 409: Case code already exists, with no new case. Cancel.
   This checks the actual form submit without adding a 31st persistent case.
2. Apply institution name Riverbend -> 7 cases. Clear filters, AICTE Permanent ID
   INST-0001 -> 5. Clear, region West -> 12. Clear between checks. Other criteria:
   PGRC bureau -> 17; Fee collection category -> 4; Disposed status -> 5;
   PGRC-109 code -> 1; received 2026-10-01 through 2026-10-09 -> 3. Empty/unmatched
   searches show a clear empty state. Invalid/reversed date ranges are rejected.
3. Clear filters and open PGRC-101 by its case code. Owner Anita Rao, next action,
   expected disposal and chronological history must be visible. In Add an action,
   keep Add note / update status and Keep current status. Enter remarks
   Slice 6 browser persistence check and document reference slice6-note.pdf.
   Leave the prefilled next action/deadline unchanged and Save action.
4. The success notice and new history entry must show the remarks, file-name text,
   actor and date. Reload the browser at its same #cases/ID address: the entry
   must remain. No uploaded file/download is simulated beyond reference text.
5. Click the institution name. The exact INST-0001 profile should show the Pune
   address, West region, PGRC/RB, and five cases including disposed records.
   Expand PGRC-101 under Case histories and find the saved note. Clicking case
   codes returns to their workspaces. Browser Back/Forward should also work.
6. Open PGRC-109. Its raw typo name is retained, Central region is shown and
   identity is unresolved. There is no guessed institution-profile link.
7. Select Rahul while viewing PGRC-101: its action form is replaced with an
   explanation that the case belongs to PGRC. Select Dr. R. K. Sharma: read-only
   explanation; Case register has no New case button. Reads remain available.
8. Switch users quickly and check the selected user matches visible forms. During
   a save, the selector/navigation are disabled. Check keyboard focus and mobile
   layout; the wide register may scroll inside its table container, not the page.
9. Return to Overview. The earlier role checks and totals must remain: global 30;
   Anita PGRC 17/7 assigned open, Rahul RB 11/5, supervisor 25 open/8 institutions/3
   bureaus, chart PGRC 17/RB 11/OTHER 2. Requests after initial user discovery use
   X-User-Id. The saved note should not change reference status/count totals.

Successful new-case creation is tested automatically inside rollback transactions.
For this main reference database, use the duplicate-case check above rather than
saving an extra case: an extra persistent case changes the fixed seed counts.
Do not change expected outcomes to hide it. If you deliberately create one, tell
the assistant before the next verification; there is no reset/delete UI yet.

Transfer, escalation and disposal are implemented in the action form and covered
in rollback tests. They intentionally change case ownership/status and therefore
reference counts. For this checklist use a note only; test status changes on a
throwaway database or after the planned reset workflow is available.

## Behavior and permissions

Case filters are applied server-side, combine with AND, and use the existing eight
criteria (the date range has two inputs). Apply filters sends query parameters;
Clear resets them. Categories/regions are suggestions from real cases, not fixed
institution or case fixtures. Case codes and institutions link through exact IDs.
Reported names/regions do not resolve identity, and missing/unknown AICTE IDs
remain unresolved. AICTE ID text is not trimmed into a different identity.

Registration is restricted to the selected officer's bureau. Officer choices come
from the real user catalog in that bureau. Received date can be blank so the
backend uses DEMO_TODAY; no client wall-clock default is introduced. Blank optional
next steps/deadlines are null. The backend remains authoritative for role, bureau,
owner, duplicate-code and identity validation; 403/409/422 messages are displayed.

Workspace writes require officer role and matching case bureau; supervisors and
foreign bureaus read without a form. Update supports optional status, note, file
name, next action and deadline; escalation sets escalated; transfer requires a
new bureau and its officer and sets transferred. Hidden transfer/status fields
are omitted from other action payloads. After transfer the source bureau loses
write access immediately. Every saved operation/history comes from PostgreSQL.
The UI never appends a fabricated audit entry, merges cases or closes another case.

Reads cancel on user/page change and guard against stale results. Pages are keyed
by user and route. Explicit saves are single-flight, do not automatically retry or
cancel a potentially committed write, and ignore completion navigation after
unmount. Selector/header navigation are disabled while saving. If a network error
leaves a save outcome uncertain, use Refresh case/history before resubmitting.
Hash URLs preserve the selected record on reload; Demo login itself resets to the
first database user on a full browser reload, as in Slice 5.

## Test coverage

The 21 Node checks include the earlier eight overview checks plus 13 new checks:
all filters, combined/reset queries, Central unresolved identity, case reload and
chronology, profiles, real role/bureau write gating, production form payloads,
transfer/escalation hidden fields, date validation, empty/404 states, hash routes,
and an actual duplicate POST returning 409 without adding a case. All API data is
real PostgreSQL-backed data through Vite; successful live writes are avoided.

Five new pytest cases use Node to execute the exact production form builders, then
submit their JSON to the real FastAPI ASGI app/PostgreSQL inside the established
SAVEPOINT fixture. They cover known/unknown ID creation, save/reload of an action
and document reference, transfer independence, and exact untrimmed ID behavior.
All test writes roll back. Earlier backend permission/audit tests remain unchanged.
No new Python, UI, router, form or testing package was added. Route-level loading
splits the previously large overview/chart code from the other workspace pages.

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


## Slice 8 Reports and exports

Open #reports from the Reports navigation item. All seven report tables come from
the existing PostgreSQL-backed endpoints and are global for both demo roles.
Report selection cancels the previous load; user changes remount the page and
cancel any unfinished download. CSV requests use the same X-User-Id client,
retain JSON HTTP errors, validate the CSV content type and clean up object URLs.
Visible report columns and browser-downloaded CSVs omit internal institution IDs,
place public institution identity first, and preserve nulls, false and zero.

Run the cumulative scripts/verify.ps1 from the repository root: expected 188
backend tests and 41 Node tests. Then scripts/dev.ps1 starts the app for actual
browser clicks. Check all seven reports, real downloaded files, supervisor access,
rapid switching, direct #reports reload, keyboard selection and narrow screens.
The root README has the exact expected reference counts and clean setup commands.

scripts/reset_demo.ps1 is an explicit destructive operation for the local synthetic
database. Stop dev first. It removes all saved case work, links, coordination and
audits, recreates six tables, applies the approved migration and reseeds. It is
never invoked by the UI or routine verification; reset regression tests roll back
all table recreation. Follow the root README reset walkthrough when ready to
replace the demo. Reload afterward; old IDs may be invalid.
