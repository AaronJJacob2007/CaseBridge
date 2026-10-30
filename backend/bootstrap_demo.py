"""Initialize a dedicated synthetic demo database without deleting existing data.

Run explicitly before the first deployment: python -m backend.bootstrap_demo.
Never runs during an API request or application startup.
"""
from pathlib import Path

from sqlalchemy import func, inspect, select
from sqlalchemy.orm import Session

from backend.db import engine
from backend.migrate_raw_region import apply_migration
from backend.seed import read_rows, seed_demo


TABLES = {"institutions", "users", "cases", "case_links", "coordination_requests", "action_log"}


def bootstrap(connection):
    connection.execute(select(func.pg_advisory_xact_lock(2626401)))
    existing = set(inspect(connection).get_table_names(schema="public"))
    if existing and existing != TABLES:
        raise RuntimeError("Database has an unfamiliar or partial schema; no changes made.")
    created = not existing
    if created:
        schema = (Path(__file__).resolve().parents[1] / "schema.sql").read_text(encoding="utf-8")
        connection.exec_driver_sql(schema)
    apply_migration(connection, read_rows("seed_cases.csv"))
    with Session(bind=connection, join_transaction_mode="create_savepoint") as session, session.begin():
        inserted = seed_demo(session)
    return created, inserted


if __name__ == "__main__":
    with engine.begin() as connection:
        created, inserted = bootstrap(connection)
    print(f"Demo schema created: {created}; synthetic cases inserted: {inserted}")
    print("Existing cases, requests and history preserved.")
