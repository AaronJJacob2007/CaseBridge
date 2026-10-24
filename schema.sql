-- CaseBridge schema (PostgreSQL). Synthetic data only.
-- Run once per database (dev and demo), then run the seed script.

CREATE TABLE institutions (
  id          SERIAL PRIMARY KEY,
  aicte_id    TEXT UNIQUE NOT NULL,          -- AICTE Permanent ID
  name        TEXT NOT NULL,
  address     TEXT,
  region      TEXT,
  campus      TEXT
);

CREATE TABLE users (
  id          SERIAL PRIMARY KEY,
  name        TEXT NOT NULL,
  role        TEXT NOT NULL CHECK (role IN ('officer', 'supervisor')),
  bureau      TEXT NOT NULL CHECK (bureau IN ('RB', 'PGRC', 'OTHER')),
  region      TEXT
);

CREATE TABLE cases (
  id                    SERIAL PRIMARY KEY,
  case_code             TEXT UNIQUE NOT NULL,           -- e.g. PGRC-101
  institution_id        INTEGER REFERENCES institutions(id),  -- NULL when identity unresolved
  identity_resolved     BOOLEAN NOT NULL DEFAULT TRUE,
  raw_aicte_id          TEXT,                           -- kept when unresolved
  raw_institution_name  TEXT,
  bureau                TEXT NOT NULL CHECK (bureau IN ('RB', 'PGRC', 'OTHER')),
  officer_id            INTEGER REFERENCES users(id),
  category              TEXT,
  description           TEXT,
  received_on           DATE NOT NULL,
  status                TEXT NOT NULL CHECK (status IN
                          ('pending', 'under_process', 'escalated', 'transferred', 'disposed')),
  last_action           TEXT,
  last_action_on        DATE,
  next_action           TEXT,
  expected_disposal_on  DATE
);
CREATE INDEX idx_cases_inst ON cases (institution_id, bureau, status);

CREATE TABLE case_links (
  id           SERIAL PRIMARY KEY,
  case_a       INTEGER NOT NULL REFERENCES cases(id),
  case_b       INTEGER NOT NULL REFERENCES cases(id),
  type         TEXT NOT NULL CHECK (type IN ('cross_bureau_overlap', 'related_incident')),
  review_state TEXT NOT NULL CHECK (review_state IN ('suggested', 'confirmed', 'rejected')),
  reviewed_by  INTEGER REFERENCES users(id),
  reason       TEXT,                                    -- required when rejected
  reviewed_at  TIMESTAMPTZ,
  CHECK (case_a < case_b),
  UNIQUE (case_a, case_b)
);

CREATE TABLE coordination_requests (
  id              SERIAL PRIMARY KEY,
  link_id         INTEGER NOT NULL REFERENCES case_links(id),
  institution_id  INTEGER NOT NULL REFERENCES institutions(id),
  requested_by    INTEGER NOT NULL REFERENCES users(id),
  to_bureau       TEXT NOT NULL CHECK (to_bureau IN ('RB', 'PGRC', 'OTHER')),
  action_type     TEXT NOT NULL,
  doc_category    TEXT,
  period          TEXT,                                 -- e.g. 2025-26
  status          TEXT NOT NULL DEFAULT 'requested' CHECK (status IN
                    ('requested', 'acknowledged', 'in_progress', 'completed', 'declined')),
  owner_id        INTEGER REFERENCES users(id),
  follow_up_on    DATE,
  proceed_reason  TEXT,                                 -- set when warning was overridden
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  acknowledged_at TIMESTAMPTZ
);
CREATE INDEX idx_coord_match ON coordination_requests (institution_id, action_type, doc_category, period, status);

CREATE TABLE action_log (
  id          SERIAL PRIMARY KEY,
  case_id     INTEGER REFERENCES cases(id),
  actor_id    INTEGER REFERENCES users(id),
  bureau      TEXT,
  event_type  TEXT NOT NULL CHECK (event_type IN
                ('create', 'update', 'transfer', 'escalate', 'link_review',
                 'coord_request', 'coord_ack', 'denied')),
  remarks     TEXT,
  doc_ref     TEXT,                                     -- file name only (simulated)
  at          TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_log_case ON action_log (case_id, at);
