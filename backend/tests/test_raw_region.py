"""Regressions for the user-approved nullable source-region extension."""
import pytest
from sqlalchemy import func, inspect, select

from backend.migrate_raw_region import apply_migration
from backend.models import ActionLog, Case
from backend.queries import query_cases
from backend.seed import read_rows


def test_migration_is_repeatable_without_new_rows_or_audits(db):
    before = db.scalar(select(func.count()).select_from(ActionLog))
    assert apply_migration(db.connection(), read_rows("seed_cases.csv")) == (False, 0)
    assert apply_migration(db.connection(), read_rows("seed_cases.csv")) == (False, 0)
    assert db.scalar(select(func.count()).select_from(ActionLog)) == before
    columns = {column["name"]: column for column in inspect(db.connection()).get_columns("cases")}
    assert columns["raw_region"]["nullable"] is True


def test_legacy_backfill_changes_only_region_and_records_one_audit(db):
    case = db.scalar(select(Case).where(Case.case_code == "PGRC-109"))
    case.raw_region = None
    db.flush()
    before = {column.name: getattr(case, column.name) for column in Case.__table__.columns if column.name != "raw_region"}
    log_count = db.scalar(select(func.count()).select_from(ActionLog))
    assert apply_migration(db.connection(), read_rows("seed_cases.csv")) == (False, 1)
    db.expire_all()
    assert case.raw_region == "Central"
    assert {name: getattr(case, name) for name in before} == before
    assert case.identity_resolved is False and case.institution_id is None
    assert db.scalar(select(func.count()).select_from(ActionLog)) == log_count + 1
    entry = db.scalar(select(ActionLog).order_by(ActionLog.id.desc()))
    assert entry.event_type == "update" and entry.case_id == case.id
    assert entry.actor_id is None and "seed_cases.csv: Central" in entry.remarks
    assert apply_migration(db.connection(), read_rows("seed_cases.csv")) == (False, 0)
    assert db.scalar(select(func.count()).select_from(ActionLog)) == log_count + 1


def test_backfill_uses_exact_case_code_and_preserves_nonnull_values(api):
    status, other = api.request("POST", "/cases", {
        "case_code": "PGRC-109-OTHER", "institution_name": "Greenfeild Engg College", "bureau": "PGRC",
    }, api.user("Anita Rao"))
    assert status == 201
    case = api.db.scalar(select(Case).where(Case.case_code == "PGRC-109"))
    registered = api.db.scalar(select(Case).where(Case.case_code == "PGRC-101"))
    case.raw_region = None
    registered.raw_region = "Preserve user-entered source region"
    api.db.flush()
    assert apply_migration(api.db.connection(), read_rows("seed_cases.csv")) == (False, 1)
    api.db.expire_all()
    assert case.raw_region == "Central"
    assert registered.raw_region == "Preserve user-entered source region"
    assert api.db.get(Case, other["id"]).raw_region is None


def test_seed_import_preserves_csv_source_region_for_every_case(db):
    cases = {case.case_code: case for case in db.scalars(select(Case))}
    for row in read_rows("seed_cases.csv"):
        assert cases[row["case_code"]].raw_region == (row["region"] or None)
    assert cases["PGRC-109"].institution_id is None
    assert cases["PGRC-109"].identity_resolved is False


def test_new_unresolved_case_retains_reported_region_without_linking(api):
    status, case = api.request("POST", "/cases", {
        "case_code": "RAW-NEW", "institution_name": "Greenfield Engineering College",
        "aicte_id": "UNKNOWN-ID", "raw_region": "Central", "bureau": "PGRC",
    }, api.user("Anita Rao"))
    assert status == 201
    assert case["region"] == case["raw_region"] == "Central"
    assert case["identity_resolved"] is False and case["institution_id"] is None
    assert case["id"] in {row["id"] for row in query_cases(api.db, region="Central")}
    _, overlaps = api.request("GET", "/overlaps")
    assert all(row["id"] != case["id"] for group in overlaps for row in group["cases"])


def test_registered_institution_region_takes_precedence_over_reported_region(api):
    status, case = api.request("POST", "/cases", {
        "case_code": "RAW-REGISTERED", "institution_name": "Synthetic source name",
        "aicte_id": "INST-0001", "raw_region": "Central", "bureau": "PGRC",
    }, api.user("Anita Rao"))
    assert status == 201 and case["raw_region"] == "Central" and case["region"] == "West"
    assert case["id"] not in {row["id"] for row in query_cases(api.db, region="Central")}
    assert case["id"] in {row["id"] for row in query_cases(api.db, region="West")}


@pytest.mark.parametrize("region", ["", "   "])
def test_blank_source_region_is_rejected(api, region):
    status, _ = api.request("POST", "/cases", {
        "case_code": "RAW-BLANK", "institution_name": "Synthetic", "bureau": "PGRC", "raw_region": region,
    }, api.user("Anita Rao"))
    assert status == 422
    assert api.db.scalar(select(Case.id).where(Case.case_code == "RAW-BLANK")) is None


def test_unreported_region_still_has_visible_unknown_bucket(api):
    status, case = api.request("POST", "/cases", {
        "case_code": "RAW-NONE", "institution_name": "Synthetic unknown", "bureau": "PGRC",
    }, api.user("Anita Rao"))
    assert status == 201 and case["region"] is None and case["raw_region"] is None
    _, summary = api.request("GET", "/dashboard/summary")
    regions = {row["region"]: row["total"] for row in summary["region_wise"]}
    assert regions["Central"] == 5 and regions["Unknown"] == 1
