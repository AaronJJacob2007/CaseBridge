"""Author-run on constructed data; expectations from expected_outcomes.md.

No mocks, skipped tests, SQLite, new tables, or committed test mutations.
"""
from datetime import date

import pytest
from fastapi import HTTPException
from sqlalchemy import func, inspect, select, update

from backend.config import get_demo_today
from backend.main import list_cases
from backend.models import ActionLog, Base, Case, Institution, User
from backend.queries import OVERLAP_MESSAGE, query_cases, query_overlaps
from backend.seed import import_case_rows, read_rows, seed_demo

EXPECTED_OVERLAPS = {
    "INST-0001": {"PGRC-101", "RB-201", "RB-210"},
    "INST-0003": {"OTH-301", "PGRC-104", "PGRC-111", "PGRC-117", "RB-203"},
    "INST-0006": {"OTH-302", "PGRC-108", "RB-205", "RB-209"},
    "INST-0008": {"PGRC-110", "PGRC-116", "RB-207"},
}


def overlap_codes(db):
    return {item["aicte_id"]: {case["case_code"] for case in item["cases"]} for item in query_overlaps(db)}


def test_models_match_existing_schema_columns_and_foreign_keys(db):
    inspector = inspect(db.connection())
    for name, table in Base.metadata.tables.items():
        actual = {column["name"]: column for column in inspector.get_columns(name)}
        assert set(actual) == set(table.columns.keys())
        for column in table.columns:
            assert actual[column.name]["nullable"] == column.nullable
            assert actual[column.name]["type"]._type_affinity == column.type._type_affinity
        actual_fks = {
            (tuple(fk["constrained_columns"]), fk["referred_table"], tuple(fk["referred_columns"]))
            for fk in inspector.get_foreign_keys(name)
        }
        model_fks = {
            (tuple(fk.column_keys), next(iter(fk.elements)).column.table.name,
             tuple(element.column.name for element in fk.elements))
            for fk in table.foreign_key_constraints
        }
        assert actual_fks == model_fks


def test_seed_counts_and_exact_officer_assignment(db):
    assert db.scalar(select(func.count()).select_from(User)) == 6
    assert db.scalar(select(func.count()).select_from(Institution)) == 8
    assert db.scalar(select(func.count()).select_from(Case)) == 30
    officers = {user.name: user for user in db.scalars(select(User))}
    cases = {case.case_code: case for case in db.scalars(select(Case))}
    for row in read_rows("seed_cases.csv"):
        case = cases[row["case_code"]]
        assert case.officer_id == officers[row["officer"]].id
        assert case.bureau == officers[row["officer"]].bureau


def test_seed_repeat_is_noop_and_preserves_case_work(db):
    case = db.scalar(select(Case).where(Case.case_code == "PGRC-101"))
    case.last_action = "Officer work must survive seeding"
    db.flush()
    before = db.scalar(select(func.count()).select_from(ActionLog))
    assert seed_demo(db) == 0
    db.refresh(case)
    assert case.last_action == "Officer work must survive seeding"
    assert db.scalar(select(func.count()).select_from(Case)) == 30
    assert db.scalar(select(func.count()).select_from(ActionLog)) == before


def test_seed_case_creations_have_audit_rows(db):
    for case in db.scalars(select(Case)):
        entry = db.scalar(select(ActionLog).where(
            ActionLog.case_id == case.id, ActionLog.event_type == "create",
            ActionLog.remarks == "Demo case import",
        ))
        assert entry is not None
        assert entry.actor_id == case.officer_id
        assert entry.bureau == case.bureau


def test_overlaps_match_exact_expected_institutions_and_cases(db):
    assert overlap_codes(db) == EXPECTED_OVERLAPS


def test_overlap_contains_required_display_details(db):
    for alert in query_overlaps(db):
        assert alert["message"] == OVERLAP_MESSAGE
        assert alert["institution_name"]
        assert len({case["bureau"] for case in alert["cases"]}) >= 2
        for case in alert["cases"]:
            assert case["case_code"] and case["bureau"] and case["officer"]
            assert case["status"] != "disposed"
            assert case["identity_resolved"] is True
            assert case["aicte_id"] == alert["aicte_id"]


def test_missing_id_retains_raw_name_and_is_never_linked(db):
    case = query_cases(db, case_code="PGRC-109")[0]
    assert case["identity_resolved"] is False
    assert case["institution_id"] is None
    assert case["raw_aicte_id"] is None
    assert case["raw_institution_name"] == "Greenfeild Engg College"
    assert case["institution_name"] == "Greenfeild Engg College"
    assert case["aicte_id"] is None
    assert all("PGRC-109" not in codes for codes in overlap_codes(db).values())
    assert len(query_cases(db, institution_name="Greenfeild")) == 1


@pytest.mark.parametrize("raw_id", ["INST-9999", "inst-0007", " INST-0007"])
def test_unknown_and_nonexact_ids_never_create_institutions(db, raw_id):
    row = read_rows("seed_cases.csv")[0].copy()
    row.update(case_code="TEST-UNKNOWN", aicte_id=raw_id,
               institution_name="Greenfield Engineering College")
    assert import_case_rows(db, [row]) == 1
    case = query_cases(db, case_code="TEST-UNKNOWN")[0]
    assert case["identity_resolved"] is False
    assert case["institution_id"] is None
    assert case["raw_aicte_id"] == raw_id
    assert db.scalar(select(func.count()).select_from(Institution)) == 8
    assert overlap_codes(db) == EXPECTED_OVERLAPS


def test_exact_id_resolves_without_matching_name(db):
    row = read_rows("seed_cases.csv")[0].copy()
    row.update(case_code="TEST-EXACT", institution_name="A completely different name")
    import_case_rows(db, [row])
    case = query_cases(db, case_code="TEST-EXACT")[0]
    assert case["identity_resolved"] is True
    assert case["aicte_id"] == "INST-0001"
    assert case["institution_name"] == "Riverbend Institute of Technology"


def test_overlap_is_independent_of_category_and_description(db):
    db.execute(update(Case).values(category="Same category", description="Same text"))
    assert overlap_codes(db) == EXPECTED_OVERLAPS


@pytest.mark.parametrize("filters,expected", [
    ({"institution_name": "riverbend"}, 7),
    ({"aicte_id": "INST-0001"}, 5),
    ({"case_code": "PGRC-109"}, 1),
    ({"bureau": "PGRC"}, 17),
    ({"region": "West"}, 12),
    ({"category": "Fee collection"}, 4),
    ({"status": "disposed"}, 5),
    ({"received_from": date(2026, 10, 1), "received_to": date(2026, 10, 9)}, 3),
    ({"aicte_id": "INST-0001", "bureau": "RB", "status": "pending"}, 1),
    ({"institution_name": "%"}, 0),
    ({"aicte_id": "INST-NOT-FOUND"}, 0),
])
def test_all_eight_filters_and_combinations(db, filters, expected):
    assert len(query_cases(db, **filters)) == expected


def test_received_date_bounds_are_inclusive(db):
    result = query_cases(db, received_from=date(2026, 10, 9), received_to=date(2026, 10, 9))
    assert [case["case_code"] for case in result] == ["PGRC-109"]


def test_reversed_date_range_is_rejected(db):
    with pytest.raises(HTTPException) as error:
        list_cases(db=db, received_from=date(2026, 10, 9), received_to=date(2026, 10, 1))
    assert error.value.status_code == 422
    assert "received_from" in error.value.detail


def test_demo_today_defaults_to_reference_date(monkeypatch):
    monkeypatch.delenv("DEMO_TODAY", raising=False)
    assert get_demo_today() == date(2026, 10, 24)


def test_demo_today_uses_environment(monkeypatch):
    monkeypatch.setenv("DEMO_TODAY", "2027-01-02")
    assert get_demo_today() == date(2027, 1, 2)


def test_invalid_demo_today_fails_clearly(monkeypatch):
    monkeypatch.setenv("DEMO_TODAY", "not-a-date")
    with pytest.raises(ValueError):
        get_demo_today()
