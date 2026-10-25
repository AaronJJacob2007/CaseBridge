"""Calendar and counting checks that do not require a running database."""
from datetime import date

import pytest

import backend.performance as performance


@pytest.mark.parametrize("kind,year,period,start,end,through", [
    ("monthly", 2024, 2, "2024-02-01", "2024-02-29", "2024-02-29"),
    ("quarterly", 2024, 1, "2024-01-01", "2024-03-31", "2024-03-31"),
    ("quarterly", 2026, 4, "2026-10-01", "2026-12-31", "2026-10-24"),
])
def test_calendar_bounds_sent_to_case_query(monkeypatch, kind, year, period, start, end, through):
    monkeypatch.setattr(performance, "get_demo_today", lambda: date(2026, 10, 24))
    calls = []
    def query(db, **filters):
        calls.append(filters)
        return []
    monkeypatch.setattr(performance, "query_cases", query)
    result = performance.performance_report(None, kind, year, period)
    assert calls == [{"received_from": date.fromisoformat(start), "received_to": date.fromisoformat(through)}]
    assert result["rows"][0]["period_end"].isoformat() == end
    assert result["partial_period"] == (through != end)


def test_each_open_status_and_unresolved_case_are_in_current_cohort(monkeypatch):
    monkeypatch.setattr(performance, "get_demo_today", lambda: date(2026, 10, 24))
    rows = [{"status": status, "bureau": "RB", "identity_resolved": False}
            for status in ["pending", "under_process", "escalated", "transferred", "disposed"]]
    monkeypatch.setattr(performance, "query_cases", lambda *args, **kwargs: rows)
    data = performance.performance_report(None)
    assert (data["rows"][0]["received"], data["rows"][0]["disposed"], data["rows"][0]["outstanding"]) == (5, 1, 4)
    assert data["rows"][2]["received"] == 5
    assert data["rows"][1]["received"] == data["rows"][3]["received"] == 0
