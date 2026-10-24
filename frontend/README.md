# CaseBridge frontend - Slice 6

React + React DOM, Vite and recharts only. Plain CSS, native fetch and built-in
Node tests; no new package or router dependency was added. Native hash routes:
Overview, case register, case workspace and institution profile. Link review and
coordination UI are reserved for Slice 7; Reports/reset UI for Slice 8.

## Run from Windows PowerShell

If a prior scripts/dev.ps1 session is still running, press Ctrl+C there first.
Then from the repository root:

~~~powershell
cd C:\SIH26\CaseBridge
.\scripts\verify.ps1
if ($?) { .\scripts\dev.ps1 }
~~~

Expected key results: 169 backend tests passed; production build successful;
21 frontend tests passed; PASS: Frontend overview and case checks (21 tests).
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
