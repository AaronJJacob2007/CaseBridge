"""Slice 4 analytics with the user-approved source-region migration.

Original regional targets are retained; source region does not resolve identity.
"""
import csv
from datetime import date, timedelta
from io import StringIO

import pytest
from sqlalchemy import delete, func, select

from backend.analytics import REPORT_TYPES
from backend.models import ActionLog, Case, CaseLink, CoordinationRequest


def read(api, path):
    status, result = api.request("GET", path)
    assert status == 200
    return result


def test_dashboard_seed_counts_and_workload(api):
    summary = read(api, "/dashboard/summary")
    for key, expected in {"total": 30, "pending": 10, "under_process": 12, "escalated": 2,
                          "transferred": 1, "disposed": 5, "open": 25,
                          "overdue": 7, "due_within_7_days": 7, "unresolved_cases": 1}.items():
        assert summary[key] == expected
    assert summary["as_of"] == "2026-10-24"
    assert {row["bureau"]: row["total"] for row in summary["bureau_wise"]} == {"PGRC": 17, "RB": 11, "OTHER": 2}
    assert sum(row["total"] for row in summary["institution_wise"]) == 30
    assert len(summary["institution_wise"]) == 9
    row = next(row for row in summary["institution_wise"] if row["aicte_id"] == "INST-0001")
    assert row["total"] == 5 and row["disposed"] == 2


def test_region_counts_match_original_targets_without_resolving_identity(api):
    summary = read(api, "/dashboard/summary")
    actual = {row["region"]: row["total"] for row in summary["region_wise"]}
    assert actual == {"Central": 5, "East": 6, "North": 2, "South": 5, "West": 12}
    assert sum(actual.values()) == summary["total"]
    unresolved = next(row for row in summary["institution_wise"] if not row["identity_resolved"])
    assert unresolved["aicte_id"] is None and unresolved["institution_id"] is None
    assert unresolved["region"] == "Central" and unresolved["unresolved_case_code"] == "PGRC-109"


def test_alerts_match_expected_case_lists(api):
    data = read(api, "/alerts")
    assert data["as_of"] == "2026-10-24"
    for name, expected in {
        "overdue": {"PGRC-103", "PGRC-106", "PGRC-108", "RB-205", "PGRC-111", "OTH-302", "PGRC-117"},
        "due_within_7_days": {"PGRC-104", "OTH-301", "RB-208", "PGRC-113", "RB-209", "PGRC-116", "RB-210"},
        "pending_too_long": {"RB-201", "PGRC-103", "PGRC-106", "PGRC-111", "RB-209", "OTH-302"},
        "escalated": {"PGRC-108", "PGRC-116"},
    }.items():
        assert {row["case_code"] for row in data[name]} == expected
    assert {row["aicte_id"] for row in data["overlap"]} == {"INST-0001", "INST-0003", "INST-0006", "INST-0008"}
    assert data["unacknowledged"] == []


def new_case(api, **fields):
    status, result = api.request("POST", "/cases", {
        "case_code": "SLICE4-BOUNDARY", "institution_name": "Synthetic boundary case",
        "bureau": "PGRC", **fields,
    }, api.user("Anita Rao"))
    assert status == 201
    return result


@pytest.mark.parametrize("offset,overdue,due", [(-1, True, False), (0, False, True), (7, False, True), (8, False, False)])
def test_due_boundaries_are_inclusive_and_disjoint(api, offset, overdue, due):
    today = date(2026, 10, 24)
    case = new_case(api, expected_disposal_on=(today + timedelta(days=offset)).isoformat())
    data = read(api, "/alerts")
    assert (case["id"] in {row["id"] for row in data["overdue"]}) is overdue
    assert (case["id"] in {row["id"] for row in data["due_within_7_days"]}) is due


@pytest.mark.parametrize("age,expected", [(30, False), (31, True)])
def test_pending_more_than_30_is_strict(api, age, expected):
    case = new_case(api, received_on=(date(2026, 10, 24) - timedelta(days=age)).isoformat())
    data = read(api, "/alerts")
    assert (case["id"] in {row["id"] for row in data["pending_too_long"]}) is expected


def test_disposed_cases_do_not_generate_case_alerts(api):
    case = new_case(api, status="disposed", received_on="2026-01-01", expected_disposal_on="2026-01-02")
    data = read(api, "/alerts")
    for name in ("overdue", "due_within_7_days", "pending_too_long", "escalated"):
        assert case["id"] not in {row["id"] for row in data[name]}


def test_analytics_use_configured_date_on_each_read(api, monkeypatch):
    assert "PGRC-116" in {row["case_code"] for row in read(api, "/alerts")["due_within_7_days"]}
    monkeypatch.setenv("DEMO_TODAY", "2026-11-01")
    assert read(api, "/dashboard/summary")["as_of"] == "2026-11-01"
    data = read(api, "/alerts")
    assert "PGRC-116" in {row["case_code"] for row in data["overdue"]}
    assert "PGRC-116" not in {row["case_code"] for row in data["due_within_7_days"]}
    assert read(api, "/reports/ageing-buckets")["as_of"] == "2026-11-01"


def make_request(api, follow_up):
    pair = [api.db.scalar(select(Case.id).where(Case.case_code == code)) for code in ("PGRC-101", "RB-201")]
    status, link = api.request("POST", "/links", {"case_a": pair[0], "case_b": pair[1], "review_state": "confirmed"}, api.user("Rahul Mehta"))
    assert status == 200
    status, result = api.request("POST", "/coordination", {
        "link_id": link["id"], "action_type": "Document request", "doc_category": "Fee records",
        "period": "2025-26", "to_bureau": "PGRC", "follow_up_on": follow_up,
    }, api.user("Rahul Mehta"))
    assert status == 201
    return result["request"]


@pytest.mark.parametrize("follow_up,expected", [("2026-10-23", True), ("2026-10-24", False), ("2026-10-25", False), (None, False)])
def test_unacknowledged_alert_requires_past_followup(api, follow_up, expected):
    request = make_request(api, follow_up)
    data = read(api, "/alerts")
    assert (request["id"] in {row["id"] for row in data["unacknowledged"]}) is expected
    if expected:
        assert data["unacknowledged"][0]["days_past_follow_up"] == 1


def test_acknowledgment_and_completion_remove_unacknowledged_alert(api):
    request = make_request(api, "2026-10-23")
    assert read(api, "/alerts")["unacknowledged"]
    status, _ = api.request("POST", f"/coordination/{request['id']}/ack", {
        "owner_id": api.user("Anita Rao"), "follow_up_on": "2026-10-23",
    }, api.user("Anita Rao"))
    assert status == 200 and read(api, "/alerts")["unacknowledged"] == []
    status, _ = api.request("POST", f"/coordination/{request['id']}/complete", {}, api.user("Anita Rao"))
    assert status == 200 and read(api, "/alerts")["unacknowledged"] == []


@pytest.mark.parametrize("report_type", list(REPORT_TYPES))
def test_each_report_returns_query_rows_and_downloadable_matching_csv(api, report_type):
    data = read(api, f"/reports/{report_type}")
    assert data["type"] == report_type and data["as_of"] == "2026-10-24"
    assert data["rows"] and data["columns"]
    assert all(set(row) == set(data["columns"]) for row in data["rows"])
    status, body, headers = api.request("GET", f"/reports/{report_type}.csv", raw=True)
    assert status == 200 and headers["content-type"].startswith("text/csv")
    assert headers["content-disposition"] == f'attachment; filename="casebridge-{report_type}.csv"'
    reader = csv.DictReader(StringIO(body))
    csv_rows = list(reader)
    assert reader.fieldnames == data["columns"] and len(csv_rows) == len(data["rows"])
    for csv_row, json_row in zip(csv_rows, data["rows"]):
        assert csv_row == {key: "" if value is None else str(value) for key, value in json_row.items()}


def test_report_counts_ageing_disposal_and_overlaps(api):
    for report_type in ("institution-wise", "bureau-wise", "region-wise", "status-wise"):
        assert sum(row["total"] for row in read(api, f"/reports/{report_type}")["rows"]) == 30
    ageing = read(api, "/reports/ageing-buckets")["rows"]
    assert {row["bucket"]: row["total"] for row in ageing} == {
        "0-7 days": 0, "8-30 days": 6, "31-60 days": 6, "61-90 days": 4, "91+ days": 9,
    }
    rates = {row["bureau"]: row for row in read(api, "/reports/disposal-rate")["rows"]}
    assert rates["All"] == {"bureau": "All", "total": 30, "disposed": 5, "disposal_rate_percent": 16.67}
    assert rates["PGRC"]["disposal_rate_percent"] == 17.65
    assert rates["RB"]["disposal_rate_percent"] == 18.18
    overlaps = read(api, "/reports/overlapping-cases")["rows"]
    assert len(overlaps) == 15 and all(row["status"] != "disposed" for row in overlaps)
    assert "PGRC-109" not in {row["case_code"] for row in overlaps}


@pytest.mark.parametrize("suffix", ["", ".csv"])
def test_unknown_report_type_returns_404(api, suffix):
    status, result = api.request("GET", f"/reports/not-a-report{suffix}")
    assert status == 404 and result["detail"] == "Unknown report type"


def test_csv_prevents_formulas_without_changing_stored_text(api):
    name = '=HYPERLINK("https://example.invalid")'
    new_case(api, institution_name=name)
    data = read(api, "/reports/institution-wise")
    assert name in {row["institution_name"] for row in data["rows"]}
    status, body, _ = api.request("GET", "/reports/institution-wise.csv", raw=True)
    assert status == 200
    names = {row["institution_name"] for row in csv.DictReader(StringIO(body))}
    assert "'" + name in names and name not in names


def test_unresolved_similar_names_are_separate_in_institution_report(api):
    for code in ("SLICE4-RAW1", "SLICE4-RAW2"):
        new_case(api, case_code=code, institution_name="Same unresolved name")
    data = read(api, "/reports/institution-wise")
    records = [row for row in data["rows"] if row["institution_name"] == "Same unresolved name"]
    assert len(records) == 2 and all(row["total"] == 1 and not row["identity_resolved"] for row in records)


def test_analytics_reads_do_not_write_audit_or_case_data(api):
    before = api.db.scalar(select(func.count()).select_from(ActionLog))
    for path in ("/dashboard/summary", "/alerts", "/reports/status-wise"):
        status, _ = api.request("GET", path, user=api.user("Dr. R. K. Sharma"))
        assert status == 200
    assert api.db.scalar(select(func.count()).select_from(ActionLog)) == before
    assert api.db.scalar(select(func.count()).select_from(Case)) == 30


def test_empty_case_database_has_zero_totals_and_no_division_error(api):
    # Test-only deletes are inside the fixture's outer rollback transaction.
    for model in (CoordinationRequest, CaseLink, ActionLog, Case):
        api.db.execute(delete(model))
    api.db.commit()
    summary = read(api, "/dashboard/summary")
    assert summary["total"] == summary["disposed"] == summary["overdue"] == 0
    data = read(api, "/alerts")
    assert all(data[key] == [] for key in ("overlap", "overdue", "due_within_7_days", "pending_too_long", "escalated", "unacknowledged"))
    rate = read(api, "/reports/disposal-rate")["rows"][0]
    assert rate["total"] == 0 and rate["disposal_rate_percent"] == 0.0
