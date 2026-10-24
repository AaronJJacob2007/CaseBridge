# Expected outcomes for the seed data (written before any code)

Reference date: **24 October 2026**. Make the app's 'today' configurable (DEMO_TODAY=2026-10-24) so these counts stay stable on recording day.

Files: `seed_users.csv` (6 demo users) and `seed_cases.csv` (30 cases, 8 institutions). All data is fictional.

**Note on independence:** these expectations were written by the plan's author from the rules, not by an independent tester. Describe any results as 'author-run on constructed data'.

## 1. Dashboard counts at seed

- Total 30; pending 10; under process 12; escalated 2; transferred 1; disposed 5.
- Bureau-wise: PGRC 17, RB 11, OTHER 2.
- Region-wise: Central 5, East 6, North 2, South 5, West 12.
- Overdue (not disposed, expected disposal before 24 Oct 2026): 7 - PGRC-103, PGRC-106, PGRC-108, RB-205, PGRC-111, OTH-302, PGRC-117.
- Due within 7 days (24-31 Oct 2026, not disposed): 7 - PGRC-104, OTH-301, RB-208, PGRC-113, RB-209, PGRC-116, RB-210.
- Pending for more than 30 days: 6 - RB-201, PGRC-103, PGRC-106, PGRC-111, RB-209, OTH-302.

## 2. Overlap alerts (open cases in 2 or more bureaus, matched on AICTE Permanent ID)

Expected: exactly these institutions raise 'Potential Overlapping Cases - Coordination Required'.

- **INST-0001 Riverbend Institute of Technology** - PGRC: PGRC-101; RB: RB-201, RB-210
- **INST-0003 Lakeview College of Engineering** - OTHER: OTH-301; PGRC: PGRC-104, PGRC-111, PGRC-117; RB: RB-203
- **INST-0006 Harbor City Technical University** - OTHER: OTH-302; PGRC: PGRC-108; RB: RB-205, RB-209
- **INST-0008 Eastern Hills Institute of Pharmacy** - PGRC: PGRC-110, PGRC-116; RB: RB-207

Expected NOT to raise an alert, and why:

- INST-0002 Riverbend (Nagpur Campus): open cases in PGRC only. Similar name to INST-0001 but a different ID, so never merged.
- INST-0004 Northgate Polytechnic: two PGRC cases, same bureau, so no cross-bureau overlap.
- INST-0005 Sunrise School of Management: the RB case (RB-204) is disposed, so only PGRC is open.
- INST-0007 Greenfield Engineering College: RB cases only. PGRC-109 has no AICTE ID, so it is stored as identity unresolved and is not linked to INST-0007.

## 3. Identity and search

- PGRC-109 imports with `identity_resolved = false`, `institution_id` empty, raw name 'Greenfeild Engg College' kept. It appears in no overlap alert and is listed for manual review.
- Search institution name 'Riverbend' returns 7 cases (INST-0001 and INST-0002); AICTE ID INST-0001 returns 5; region West returns 12.

## 4. Link review, coordination and repeated-action warning (INST-0001)

1. Rahul Mehta (RB) opens the INST-0001 alert and confirms a link between PGRC-101 and RB-201.
2. Rahul raises a request to PGRC: action 'Document request', category 'Fee records', period '2025-26'. Expected: saved, no warning.
3. Anita Rao (PGRC) tries the same action, category and period. Expected: warning that shows request 2, with 'Coordinate' or 'Proceed separately (reason required)'.
4. Anita tries period '2024-25'. Expected: no warning.
5. Anita tries category 'Salary records', period '2025-26'. Expected: no warning.
6. Anita acknowledges request 2 with an owner and follow-up date. Expected: status acknowledged; an action_log row 'coord_ack'.
7. Anita repeats step 3 again. Expected: the warning still shows (acknowledged counts as pending).
8. Request 2 is marked completed, then step 3 is repeated. Expected: no warning (no longer pending).

## 5. Rejection, independence and permissions

- Reject the link PGRC-104 and RB-203 (INST-0003) with reason 'Unrelated incidents'. Expected: link stored as rejected with the reason; the institution-level overlap alert for INST-0003 still shows.
- On a throwaway copy of the database, mark PGRC-101 disposed. Expected: RB-201 stays pending and unchanged.
- The supervisor (Dr. R. K. Sharma) tries to confirm a link or edit a case. Expected: 403 and an action_log row with event 'denied'.
- A PGRC officer tries to record an action on an RB case. Expected: 403 and a 'denied' log row.
- Reload the app after section 4. Expected: all links, requests and log rows are still present.
