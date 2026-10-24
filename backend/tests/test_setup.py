"""Read-only checks against real PostgreSQL; no seed data needed."""
from backend.check_db import EXPECTED_TABLES, check_tables
from backend.main import health


def test_schema_has_exactly_the_six_expected_tables():
    assert set(check_tables()) == EXPECTED_TABLES


def test_health_confirms_live_database_connection():
    assert health() == {"status": "ok", "database": "ok"}
