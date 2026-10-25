"""Live Slice 4 acceptance, including the unchanged original regional targets."""
import csv
from io import StringIO
from urllib.request import urlopen

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.config import get_demo_today
from backend.db import engine
from backend.models import CoordinationRequest
from backend.analytics import REPORT_TYPES
from backend.verify_http import BASE, get


def check_summary():
    data = get("/dashboard/summary")
    expected = {"total": 30, "pending": 10, "under_process": 12, "escalated": 2,
                "transferred": 1, "disposed": 5, "overdue": 7, "due_within_7_days": 7}
    for key, value in expected.items():
        assert data[key] == value, f"{key}: expected {value}, got {data[key]}"
    assert data["as_of"] == "2026-10-24"
    assert {row["bureau"]: row["total"] for row in data["bureau_wise"]} == {"PGRC": 17, "RB": 11, "OTHER": 2}
    assert sum(row["total"] for row in data["institution_wise"]) == 30


def check_alerts():
    data = get("/alerts")
    for name, codes in {
        "overdue": {"PGRC-103", "PGRC-106", "PGRC-108", "RB-205", "PGRC-111", "OTH-302", "PGRC-117"},
        "due_within_7_days": {"PGRC-104", "OTH-301", "RB-208", "PGRC-113", "RB-209", "PGRC-116", "RB-210"},
        "pending_too_long": {"RB-201", "PGRC-103", "PGRC-106", "PGRC-111", "RB-209", "OTH-302"},
        "escalated": {"PGRC-108", "PGRC-116"},
    }.items():
        assert {row["case_code"] for row in data[name]} == codes, name
    assert {row["aicte_id"] for row in data["overlap"]} == {"INST-0001", "INST-0003", "INST-0006", "INST-0008"}
    with Session(engine) as db:
        check_unacknowledged(data, db)


def check_unacknowledged(data, db):
    """Validate live alerts against persisted requests, including browser work.

    Seed-only ASGI tests still require an empty list. Live verification must
    also accept legitimate past-due requests without completing/deleting them.
    Derive expected IDs independently from all stored requests in Python.
    """
    today = get_demo_today()
    assert data["as_of"] == today.isoformat(), "Alert reference date differs"
    requests = db.scalars(select(CoordinationRequest)).all()
    expected = sorted((request for request in requests
                       if request.status == "requested" and request.acknowledged_at is None
                       and request.follow_up_on is not None and request.follow_up_on < today),
                      key=lambda request: (request.follow_up_on, request.id))
    actual = data["unacknowledged"]
    assert [row["id"] for row in actual] == [request.id for request in expected], "Unacknowledged alert IDs/order differ from saved requests"
    for row, request in zip(actual, expected):
        for field in ("link_id", "institution_id", "requested_by", "to_bureau", "action_type",
                      "doc_category", "period", "status", "owner_id"):
            assert row[field] == getattr(request, field), f"Request {request.id}: {field} differs"
        assert row["acknowledged_at"] is None
        assert row["follow_up_on"] == request.follow_up_on.isoformat()
        assert row["days_past_follow_up"] == (today - request.follow_up_on).days


def check_reports():
    for report_type in REPORT_TYPES:
        data = get(f"/reports/{report_type}")
        assert data["type"] == report_type and data["rows"]
        with urlopen(BASE + f"/reports/{report_type}.csv", timeout=10) as response:
            assert response.status == 200
            assert response.headers.get_content_type() == "text/csv"
            assert response.headers["Content-Disposition"] == f'attachment; filename="casebridge-{report_type}.csv"'
            reader = csv.DictReader(StringIO(response.read().decode("utf-8")))
            rows = list(reader)
            assert reader.fieldnames == data["columns"] and len(rows) == len(data["rows"])
            for csv_row, json_row in zip(rows, data["rows"]):
                assert csv_row == {key: "" if value is None else str(value) for key, value in json_row.items()}


def check_original_regions():
    expected = {"Central": 5, "East": 6, "North": 2, "South": 5, "West": 12}
    actual = {row["region"]: row["total"] for row in get("/dashboard/summary")["region_wise"]}
    assert actual == expected, f"Expected regions {expected}; got {actual}"
    case = get("/cases", case_code="PGRC-109")[0]
    assert case["region"] == case["raw_region"] == "Central"
    assert case["identity_resolved"] is False and case["institution_id"] is None
    assert case["aicte_id"] is None
    central = get("/cases", region="Central")
    assert len(central) == 5 and "PGRC-109" in {row["case_code"] for row in central}
    report = get("/reports/region-wise")
    assert {row["region"]: row["total"] for row in report["rows"]} == expected



if __name__ == "__main__":
    for name, check in (
        ("HTTP dashboard totals and bureau workload", check_summary),
        ("HTTP computed alert case lists", check_alerts),
        ("HTTP seven JSON reports and downloadable CSVs", check_reports),
        ("Original Slice 4 regional acceptance", check_original_regions),
    ):
        try:
            check()
        except Exception:
            print(f"FAIL: {name}", flush=True)
            raise
        print(f"PASS: {name}", flush=True)
