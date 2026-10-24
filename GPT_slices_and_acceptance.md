# Supervising GPT: slices, "done when" checks and red flags

GPT writes all the code, including the database setup. You supervise. Work from the files in the repo: `schema.sql`, `seed_cases.csv`, `seed_users.csv`, `expected_outcomes.md`, and the rules in `GPT_kickoff_prompt.md` (paste that file at the start of every session, or save its Rules section as AGENTS.md in the repo root).

## Your supervisor loop (for every slice)
1. Paste the slice prompt. Tell GPT: "Run the tests and show me the output. Do not say done until they pass."
2. Run the one command in "Done when" yourself and compare with the expected numbers. Do not accept "this should work".
3. Look at the diff for the red flags below.
4. If it fails, paste the real error output back, not a description. If it fails twice, ask GPT to explain the cause first, then fix.
5. Commit only when green: `git add -A && git commit -m "slice N"`. Tag the end of each day: `git tag day1-green`.

## Red flags in a diff (ask GPT to undo these)
- A new library or service not in the stack (React, Vite, recharts, FastAPI, SQLAlchemy, psycopg, pytest).
- `expected_outcomes.md`, the seed CSVs or the tests were edited to make a failure go away.
- Endpoints that return hard-coded or mock data instead of querying PostgreSQL.
- Tests that assert nothing (for example, only check status code 200) or are skipped.
- Secrets or the database URL written into code or committed (`.env` must be in `.gitignore`).
- Broad `try/except: pass` that hides errors, or changes to files you did not ask about.
- Fuzzy name matching, NLP, or a similarity score anywhere in the overlap logic.

## What only you can do
- Create or install the database (see Slice 0) and put the connection string in `.env`.
- Run the commands on your own machine and open the app in a browser.
- Judge whether the screens are readable, and click through the four differentiators.
- Record the demo video.
- Check whether your GPT/Codex environment can reach your database. If it runs in a cloud sandbox, it may not see a database on your laptop; in that case let it run its tests against a PostgreSQL started inside its own environment, and you run the same tests locally.

---

## Slice 0: project and database setup
Prompt: Create `backend/` and `frontend/` folders, `.gitignore` (include `.env`), `.env.example` with DATABASE_URL and DEMO_TODAY=2026-10-24, and a `README.md` with exact run commands. Add a `docker-compose.yml` that runs only PostgreSQL (nothing else), mounts `schema.sql` so the tables are created on first start, and exposes the port. Add `GET /health` in FastAPI that also checks the database connection.
Done when: `docker compose up -d` starts PostgreSQL; `psql` (or GPT's check script) lists 6 tables: institutions, users, cases, case_links, coordination_requests, action_log; `GET /health` returns ok.
If Docker is not installed: use a free hosted PostgreSQL (for example Neon or Supabase; check their current limits), paste its connection string into `.env`, and have GPT run `schema.sql` against it.

## Slice 1: seed and overlap (see GPT_kickoff_prompt.md, Slice 1)
Done when: the seed script loads 6 users and 30 cases; `GET /overlaps` returns exactly INST-0001, INST-0003, INST-0006 and INST-0008; PGRC-109 has `identity_resolved = false` and appears in no overlap; `pytest` passes.

## Slice 2: cases, permissions and history
Prompt: Implement GET /cases with all eight filters (institution name, AICTE Permanent ID, case code, bureau, region, category, status, date range), POST /cases, GET /cases/{id} with its action_log history, POST /cases/{id}/actions (remarks, doc_ref text, transfer and escalate update status), GET /institutions/{id} with its case history and bureaus involved. Read the demo user from the X-User-Id header. Supervisors are read-only; officers may write only on their own bureau's cases. A denied write returns 403 and adds an action_log row with event_type 'denied'. Every successful write adds an action_log row.
Done when: filtering name 'Riverbend' returns 7 cases; AICTE ID INST-0001 returns 5; region West returns 12; a supervisor POST returns 403 and a 'denied' row exists; a PGRC officer writing to an RB case returns 403.

## Slice 3: links, coordination and repeated-action warning
Prompt: Implement POST /links (confirm or reject between two cases; reason required for rejection; officers only), POST /coordination/check (returns an existing pending request that matches on institution, confirmed link, action_type, doc_category, period, status in requested/acknowledged/in_progress), POST /coordination (saves; if proceeding despite a warning, require proceed_reason), POST /coordination/{id}/ack (owner and follow_up_on; target bureau officers only), and a way to mark a request completed. Log every step in action_log.
Done when: steps 1-8 of section 4 in `expected_outcomes.md` pass as pytest tests (warning on step 3 and step 7; none on steps 4, 5 and 8); rejecting PGRC-104 with RB-203 stores the reason and the INST-0003 alert still shows; marking PGRC-101 disposed leaves RB-201 unchanged (on a throwaway database).

## Slice 4: dashboard, alerts and reports
Prompt: Implement GET /dashboard/summary (total, pending, under_process, escalated, transferred, disposed, overdue, due within 7 days, bureau-wise workload, region-wise counts, institution-wise status), GET /alerts (overlap, pending more than 30 days, due within 7 days, overdue, escalated, unacknowledged request past follow-up), and GET /reports/{type} plus .csv for institution-wise, bureau-wise, region-wise, status-wise, ageing buckets, disposal rate, and overlapping cases. Use DEMO_TODAY for 'today'.
Done when: summary shows total 30, pending 10, under_process 12, escalated 2, transferred 1, disposed 5, overdue 7, due within 7 days 7; bureau PGRC 17, RB 11, OTHER 2; region Central 5, East 6, North 2, South 5, West 12; each report returns rows and a downloadable CSV.

## Slice 5: frontend shell and overview
Prompt: In `frontend/` (React with Vite), build a layout with a demo user switcher (it sends X-User-Id on every request and is labelled "Demo login"), an Overview screen with summary cards, alert flags, and one recharts bar chart (bureau-wise). Officer and supervisor see different home panels (see the plan's role table). Keep styling simple: white background, navy text, teal accent, amber for pending, red for overdue.
Done when: the app starts with the commands in the README; switching user changes the Overview; the numbers match Slice 4.

## Slice 6: case register, case workspace, institution profile
Prompt: Case register with all eight filters and a case entry form; case workspace showing fields, owner, next action and chronological history with an add-action form (remarks, file name text); institution profile with AICTE Permanent ID, address, region, bureaus involved and case history.
Done when: the filters return the same counts as Slice 2; adding an action appears in the history and survives a page reload.

## Slice 7: overlap and coordination screen (your main differentiators)
Prompt: Overlap list showing the banner "Potential Overlapping Cases - Coordination Required" with AICTE Permanent ID, cases, bureaus, statuses and officers. A side-by-side view of two selected cases with Confirm and Reject (reason box). On a confirmed link: a request form (action type, document category, period, target bureau) that calls /coordination/check first and shows the warning panel with "Coordinate" and "Proceed separately (reason required)". An acknowledgment form for the target officer (owner, follow-up date). The supervisor view shows these read-only, and a blocked attempt shows the 403 message.
Done when: you can run the INST-0001 walkthrough in the browser (confirm PGRC-101 and RB-201, create the fee records 2025-26 request, see the warning from the other officer, no warning for 2024-25), and everything is still there after a reload.

## Slice 8: reports tab, polish and reset
Prompt: A Reports tab with the report tables and CSV download buttons; clear empty and error states; a `scripts/reset_demo` command that recreates the tables and reseeds; update the README with the exact commands from a clean machine.
Done when: you can wipe and reseed the database in one command and the Overview numbers are back to the Slice 4 values.

## Order and time
Day 1 target: Slices 0-4 (backend). Day 2 target: Slices 5-7, then record the video. Slice 8 and deployment only if time remains. If behind, cut in this order: Slice 8 reports tab, the chart, pending-reminder flag. Do not cut Slices 1-3 or the screen in Slice 7.
