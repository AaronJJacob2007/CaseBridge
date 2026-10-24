# CaseBridge - Slice 0

Synthetic data only. This slice provides PostgreSQL setup and a database-aware
FastAPI health endpoint. The supplied schema and seed files are unchanged.
Business logic, models, seeding, and frontend UI belong to later slices.

## Windows PowerShell setup

Run from `C:\SIH26\CaseBridge`. Start Docker Desktop with its Linux container
engine running. Python 3.11+ is required. PostgreSQL runs in Docker; Python runs
locally. No global PostgreSQL or psql installation is needed.

```powershell
Copy-Item .env.example .env
notepad .env
```

Replace `replace_with_local_password` in BOTH `POSTGRES_PASSWORD` and
`DATABASE_URL` with the same local password. Use letters and digits to avoid URL
escaping issues. Do not commit `.env`. If `.env` already exists, keep it instead
of overwriting it. The application takes DATABASE_URL from the process environment;
the script below loads it without adding a dotenv dependency.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
. .\scripts\load_env.ps1
docker compose up -d
docker compose ps
```

Wait for the database to report `healthy`. Then run the acceptance checks:

```powershell
.\.venv\Scripts\python.exe -m backend.check_db
.\.venv\Scripts\python.exe -m pytest backend\tests -q
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

In a second PowerShell terminal:

```powershell
curl.exe -i http://127.0.0.1:8000/health
```

Expected: HTTP 200 with `{"status":"ok","database":"ok"}`. A failed database
connection returns HTTP 503 with `{"status":"error","database":"unavailable"}`.
The table check must report exactly these six public tables: action_log,
case_links, cases, coordination_requests, institutions, users. Tests are read-only
integration checks and require the running database. Nothing is seeded in Slice 0.

## Database lifecycle

Compose exposes PostgreSQL only on `127.0.0.1:5432`. It mounts the original
`schema.sql` read-only into PostgreSQL's initialization directory. That file runs
only when the named data volume is empty. Restarting preserves the tables and data;
changing `.env` later does not reset existing database credentials.

```powershell
docker compose stop
docker compose start
```

These stop/start only the database. Stop the foreground backend with Ctrl+C.

## Frontend and project rules

`frontend/` is reserved for React + Vite + recharts in Slice 5, on port **5173**.
There is no frontend server to start in Slice 0. FastAPI uses port **8000**.
DEMO_TODAY is supplied as `2026-10-24` for later date-based logic; health has no
date-based behavior. Follow Rules and How we work in `GPT_kickoff_prompt.md`
throughout the project. Docker is used only for PostgreSQL, as explicitly required
by Slice 0. Uvicorn is the local ASGI runner for FastAPI, not another service.

## Verification workflow (all slices)

The assistant writes code and tests but does not run Docker or install packages.
For each slice, provide one ordered RUN THIS PowerShell block and save the same
commands in scripts/verify.ps1, with expected passing output below each command.
List checks the assistant could not run. The user runs verification locally and
pastes actual output; fix failures from that evidence. Do not claim a slice is
done before the user supplies passing output.

For Slice 0, scripts/verify.ps1 checks Docker, installs dependencies, waits for
PostgreSQL, verifies six tables, runs the two tests, and checks HTTP /health with
a temporary backend on port 8000. It preserves .env if present, stops on failure,
and stops only its own backend afterward. PostgreSQL remains running.
