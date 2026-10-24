"""Read-only Slice 0 acceptance check: python -m backend.check_db."""
from sqlalchemy import inspect

from backend.db import engine

EXPECTED_TABLES = {
    "institutions", "users", "cases", "case_links",
    "coordination_requests", "action_log",
}


def check_tables():
    actual = set(inspect(engine).get_table_names(schema="public"))
    if actual != EXPECTED_TABLES:
        raise RuntimeError(
            f"Table mismatch: missing={sorted(EXPECTED_TABLES - actual)}, "
            f"unexpected={sorted(actual - EXPECTED_TABLES)}"
        )
    return sorted(actual)


if __name__ == "__main__":
    tables = check_tables()
    print(f"{len(tables)} tables: {', '.join(tables)}")
