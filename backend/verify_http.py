"""Real HTTP acceptance checks using only Python's standard library."""
import json
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import urlopen

BASE = "http://127.0.0.1:8000"


def get(path, **filters):
    suffix = "?" + urlencode(filters) if filters else ""
    with urlopen(BASE + path + suffix, timeout=10) as response:
        assert response.status == 200, f"Unexpected HTTP status: {response.status}"
        return json.load(response)


def check_health():
    assert get("/health") == {"status": "ok", "database": "ok"}


def check_cases():
    assert len(get("/cases")) == 30
    checks = [
        ({"institution_name": "Riverbend"}, 7),
        ({"aicte_id": "INST-0001"}, 5),
        ({"case_code": "PGRC-109"}, 1),
        ({"bureau": "PGRC"}, 17),
        ({"region": "West"}, 12),
        ({"category": "Fee collection"}, 4),
        ({"status": "disposed"}, 5),
        ({"received_from": "2026-10-01", "received_to": "2026-10-09"}, 3),
    ]
    for filters, count in checks:
        actual = len(get("/cases", **filters))
        assert actual == count, f"Filter {filters}: expected {count}, got {actual}"


def check_overlaps():
    alerts = get("/overlaps")
    actual = {alert["aicte_id"]: {case["case_code"] for case in alert["cases"]} for alert in alerts}
    assert actual == {
        "INST-0001": {"PGRC-101", "RB-201", "RB-210"},
        "INST-0003": {"OTH-301", "PGRC-104", "PGRC-111", "PGRC-117", "RB-203"},
        "INST-0006": {"OTH-302", "PGRC-108", "RB-205", "RB-209"},
        "INST-0008": {"PGRC-110", "PGRC-116", "RB-207"},
    }, f"Unexpected overlap cases: {actual}"
    for alert in alerts:
        assert alert["message"] == "Potential Overlapping Cases - Coordination Required"
        assert alert["institution_name"]
        for case in alert["cases"]:
            assert case["officer"] and case["bureau"] and case["status"] != "disposed"


def check_unresolved():
    rows = get("/cases", case_code="PGRC-109")
    assert len(rows) == 1
    case = rows[0]
    assert case["identity_resolved"] is False
    assert case["institution_id"] is None and case["aicte_id"] is None
    assert case["raw_institution_name"] == "Greenfeild Engg College"
    assert all(item["case_code"] != "PGRC-109" for alert in get("/overlaps") for item in alert["cases"])


def check_validation():
    for filters in (
        {"received_from": "2026-10-09", "received_to": "2026-10-01"},
        {"received_from": "not-a-date"}, {"bureau": "INVALID"}, {"status": "INVALID"},
    ):
        try:
            get("/cases", **filters)
        except HTTPError as error:
            assert error.code == 422, f"Expected 422, got {error.code}"
            assert json.load(error)["detail"]
        else:
            raise AssertionError(f"Invalid filters accepted: {filters}")


if __name__ == "__main__":
    for name, check in (
        ("HTTP /health (200; database ok)", check_health),
        ("HTTP /cases (30 cases; all eight filters)", check_cases),
        ("HTTP /overlaps (INST-0001, INST-0003, INST-0006, INST-0008)", check_overlaps),
        ("HTTP PGRC-109 unresolved; excluded from overlaps", check_unresolved),
        ("HTTP invalid filters rejected (422)", check_validation),
    ):
        try:
            check()
        except Exception:
            print(f"FAIL: {name}", flush=True)
            raise
        print(f"PASS: {name}", flush=True)
