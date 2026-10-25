"""Rollback-isolated receipt-cohort report acceptance checks."""
import csv
from datetime import date
from io import StringIO

import pytest

from backend.models import Case


@pytest.fixture
def cohort(api):
    for code, received, status in [
        ("PERF-JAN", "2024-01-31", "disposed"),
        ("PERF-START", "2024-02-01", "disposed"),
        ("PERF-LEAP", "2024-02-29", "pending"),
        ("PERF-MID", "2024-02-15", "transferred"),
        ("PERF-MAR", "2024-03-01", "under_process"),
    ]:
        api.db.add(Case(case_code=code, received_on=date.fromisoformat(received),
                        status=status, bureau="RB", identity_resolved=False,
                        last_action_on=date(2026, 10, 24)))
    api.db.commit()
    return api


def get(api, query):
    status, result = api.request("GET", "/reports/performance" + query)
    assert status == 200
    return result


def test_month_boundaries_leap_day_and_current_cohort_outcomes(cohort):
    data = get(cohort, "?kind=monthly&year=2024&period=2")
    row = data["rows"][0]
    assert row == {"period_start": "2024-02-01", "period_end": "2024-02-29",
                   "receipts_through": "2024-02-29", "status_as_of": "2026-10-24",
                   "bureau": "All", "received": 3, "disposed": 1, "outstanding": 2}
    assert data["partial_period"] is False
    assert data["rows"][2] == {**row, "bureau": "RB"}
    # Reopening changes the cohort's current outcomes, not its receipt count.
    case = next(case for case in cohort.db.query(Case) if case.case_code == "PERF-START")
    case.status = "under_process"
    cohort.db.commit()
    changed = get(cohort, "?kind=monthly&year=2024&period=2")["rows"][0]
    assert (changed["received"], changed["disposed"], changed["outstanding"]) == (3, 0, 3)


def test_quarter_includes_three_calendar_months_and_all_current_bureaus(cohort):
    data = get(cohort, "?kind=quarterly&year=2024&period=1")
    row = data["rows"][0]
    assert (row["period_start"], row["period_end"]) == ("2024-01-01", "2024-03-31")
    assert (row["received"], row["disposed"], row["outstanding"]) == (5, 2, 3)
    for key in ("received", "disposed", "outstanding"):
        assert row[key] == sum(item[key] for item in data["rows"][1:])


def test_empty_period_still_has_zero_rows_and_csv_headers(api):
    data = get(api, "?year=2023&period=2")
    assert len(data["rows"]) == 4
    assert all(row["received"] == row["disposed"] == row["outstanding"] == 0 for row in data["rows"])


def test_current_period_is_partial_and_excludes_future_receipts(api):
    before = get(api, "")
    api.db.add(Case(case_code="PERF-FUTURE", received_on=date(2026, 10, 25),
                    status="pending", bureau="PGRC", identity_resolved=False))
    api.db.commit()
    data = get(api, "")
    assert data == before
    assert data["kind"] == "monthly" and data["year"] == 2026 and data["period"] == 10
    assert data["partial_period"] is True
    assert data["rows"][0]["receipts_through"] == "2026-10-24"
    quarter = get(api, "?kind=quarterly")
    assert quarter["period"] == 4 and quarter["rows"][0]["period_end"] == "2026-12-31"


@pytest.mark.parametrize("query", ["?kind=weekly", "?year=0", "?year=10000", "?year=no",
                                   "?period=0", "?period=13", "?kind=quarterly&period=5",
                                   "?year=2026&period=11", "?year=2027&period=1"])
def test_invalid_or_future_periods_rejected_in_json_and_csv(api, query):
    for suffix in ("", ".csv"):
        assert api.request("GET", "/reports/performance" + suffix + query)[0] == 422


def test_json_csv_periods_counts_and_supervisor_access_agree(cohort):
    query = "?kind=quarterly&year=2024&period=1"
    data = get(cohort, query)
    status, text, headers = cohort.request("GET", "/reports/performance.csv" + query, raw=True)
    assert status == 200 and headers["content-type"].startswith("text/csv")
    rows = list(csv.DictReader(StringIO(text)))
    assert list(rows[0]) == data["columns"]
    assert rows == [{key: str(value) for key, value in row.items()} for row in data["rows"]]
    assert "institution_id" not in data["columns"]
    assert "not disposals during the period" in data["counting_rules"]
    status, supervisor = cohort.request("GET", "/reports/performance" + query,
                                       user=cohort.user("Dr. R. K. Sharma"))
    assert status == 200 and supervisor == data

