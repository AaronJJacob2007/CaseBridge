# CaseBridge: GPT kickoff prompt (paste at the start of every session)

You are helping me build a hackathon prototype in 2 days. Synthetic data only. Keep every change small and runnable.

## Product
CaseBridge: a role-based dashboard for AICTE officials (PS 26264). It tracks institution-related complaint cases across bureaus (RB, PGRC, other), raises an overlap alert, lets officials confirm or reject case links, records acknowledged coordination requests, and warns before a repeated request.

## Stack (do not add anything else)
React (Vite) + recharts, FastAPI, SQLAlchemy, PostgreSQL (psycopg), pytest. Database URL comes from the DATABASE_URL environment variable. Use SQLAlchemy for all queries; no SQLite-only features.

## Schema
Use the attached schema.sql exactly (institutions, users, cases, case_links, coordination_requests, action_log).

## Rules (must follow)
1. Identity resolution: match institutions on aicte_id exactly. Missing or unknown ID -> identity_resolved = false, never auto-linked. No fuzzy or NLP matching.
2. Overlap alert: an institution with open cases (status != disposed) in 2+ different bureaus shows "Potential Overlapping Cases - Coordination Required" with AICTE Permanent ID, case codes, bureaus, statuses, officers. Independent of description or category text.
3. Link review: an officer confirms or rejects a link between two cases (reason required for rejection). Nothing is merged or closed automatically. Closing one case never changes the other.
4. Coordination: on a confirmed link, an officer raises a request (action_type, doc_category, period, to_bureau); the target officer acknowledges with owner and follow_up_on.
5. Repeated-action check before saving a request: same institution + confirmed link + same action_type + same doc_category + same period + pending status (requested, acknowledged, in_progress) -> return the existing request as a warning; the officer chooses "coordinate" or "proceed separately" (reason required). Different period or document category = no warning.
6. Permissions: demo user is sent in an X-User-Id header. Backend checks role and bureau on every write. Supervisors are read-only; a denied write returns 403 and adds an action_log row with event_type 'denied'.
7. Alerts are computed on page load: overlap, pending too long, due within 7 days, overdue, escalated, unacknowledged request past follow_up_on.
8. Every write adds an action_log row.

## Endpoints
GET /dashboard/summary; GET /cases (filters: institution name, aicte_id, case_code, bureau, region, category, status, date range); POST /cases; GET /cases/{id}; POST /cases/{id}/actions; GET /institutions/{id}; GET /overlaps; POST /links; POST /coordination/check; POST /coordination; POST /coordination/{id}/ack; GET /alerts; GET /reports/{type}; GET /reports/{type}.csv

## How we work
- One slice per prompt. Edit the files in the repo, run the tests, then summarise what you changed.
- After each slice, give me a curl command or a pytest test I can run to check it.
- Do not add authentication libraries, Docker, extra services, NLP, email/SMS or new features.

## Slice 1 (start here)
1. FastAPI project skeleton with SQLAlchemy models matching schema.sql and a DATABASE_URL config.
2. A seed script that first loads seed_users.csv (name, role, bureau, region) and then seed_cases.csv, matching officer names to users. The cases CSV has columns: aicte_id, institution_name, address, region, case_code, bureau, category, description, received_on, status, officer, last_action, last_action_on, next_action, expected_disposal_on. Rows with an unknown aicte_id become unresolved cases.
3. GET /cases with all eight filters, and GET /overlaps using rule 2.
4. A DEMO_TODAY environment variable (default 2026-10-24) used everywhere the app needs 'today', so dashboard and alert counts stay stable.
5. pytest tests for the overlap rule and the unresolved-identity rule, checked against expected_outcomes.md (the overlap list and the unresolved case PGRC-109). Do not change expected_outcomes.md to make tests pass.
