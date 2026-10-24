"""Approved Slice 4 extension; run before seeding or starting the application.

python -m backend.migrate_raw_region
Original schema.sql stays unchanged. The migration is transactional and repeatable.
"""
from sqlalchemy import Text, func, inspect, select, text
from sqlalchemy.orm import Session

from backend.db import engine
from backend.models import ActionLog, Case
from backend.seed import read_rows


def backfill_raw_regions(db, rows):
    """Fill null source regions by exact case code, never by institution/name."""
    changed = 0
    for row in rows:
        region = row.get("region") or None
        if region is None:
            continue
        case = db.scalar(select(Case).where(
            Case.case_code == row["case_code"], Case.raw_region.is_(None),
        ).with_for_update().execution_options(populate_existing=True))
        if case is None:
            continue
        case.raw_region = region
        db.add(ActionLog(
            case_id=case.id, bureau=case.bureau, event_type="update",
            remarks=f"Source region backfilled from seed_cases.csv: {region}",
        ))
        db.flush()
        changed += 1
    return changed


def apply_migration(connection, rows):
    # Serialize two verification runs without adding a migration table/service.
    connection.execute(select(func.pg_advisory_xact_lock(2626401)))
    columns = {column["name"]: column for column in inspect(connection).get_columns("cases", schema="public")}
    added = "raw_region" not in columns
    if added:
        connection.execute(text("ALTER TABLE public.cases ADD COLUMN IF NOT EXISTS raw_region TEXT"))
    elif not isinstance(columns["raw_region"]["type"], Text) or not columns["raw_region"]["nullable"]:
        raise RuntimeError("Existing cases.raw_region must be nullable TEXT")
    # A SAVEPOINT also allows migration regression tests to roll everything back.
    with Session(bind=connection, join_transaction_mode="create_savepoint") as db, db.begin():
        if added:
            db.add(ActionLog(event_type="update", remarks="Schema migration: add nullable cases.raw_region"))
        filled = backfill_raw_regions(db, rows)
    return added, filled


if __name__ == "__main__":
    rows = read_rows("seed_cases.csv")
    with engine.begin() as connection:
        added, filled = apply_migration(connection, rows)
    print("Migration: cases.raw_region nullable TEXT available")
    print(f"Column added: {str(added).lower()}; source regions backfilled: {filled}")
