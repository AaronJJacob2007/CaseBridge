"""Live HTTP reads and denial persistence; leaves demo cases/counts unchanged.

Successful writes are covered by PostgreSQL-backed ASGI tests with rollback.
Denied writes intentionally add persistent audit rows to the demo database.
"""
import json
from uuid import uuid4
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.db import engine
from backend.models import ActionLog, Case, User
from backend.verify_http import BASE, get


def check_details():
    case = get("/cases", case_code="PGRC-101")[0]
    detail = get(f"/cases/{case['id']}")
    assert detail["case_code"] == "PGRC-101" and detail["officer"] == "Anita Rao"
    assert detail["history"] and detail["history"][0]["event_type"] == "create"
    assert detail["history"] == sorted(detail["history"], key=lambda entry: (entry["at"], entry["id"]))


def check_profile():
    case = get("/cases", case_code="PGRC-101")[0]
    profile = get(f"/institutions/{case['institution_id']}")
    assert profile["aicte_id"] == "INST-0001"
    assert profile["address"] == "12 Lake Road, Pune" and profile["region"] == "West"
    assert profile["bureaus_involved"] == ["PGRC", "RB"]
    assert len(profile["cases"]) == 5
    assert all(item["history"] for item in profile["cases"])


def check_denied(actor_name, *, create=False):
    with Session(engine) as db:
        actor_id = db.scalar(select(User.id).where(User.name == actor_name))
        assert actor_id is not None
        last_log_id = db.scalar(select(func.max(ActionLog.id))) or 0
    case = get("/cases", case_code="RB-201")[0]
    before = get(f"/cases/{case['id']}")
    case_id = None if create else case["id"]
    path = "/cases" if create else f"/cases/{case_id}/actions"
    payload = {
        "case_code": "VERIFY-DENIED-" + uuid4().hex,
        "institution_name": "Synthetic rejected case", "bureau": "PGRC",
    } if create else {"remarks": "Verification: forbidden action"}
    request = Request(BASE + path, data=json.dumps(payload).encode(), method="POST",
                      headers={"Content-Type": "application/json", "X-User-Id": str(actor_id)})
    try:
        with urlopen(request, timeout=10) as response:
            raise AssertionError(f"Expected 403; received {response.status}")
    except HTTPError as error:
        assert error.code == 403, f"Expected 403; received {error.code}"
        assert json.load(error)["detail"]
    # A separate PostgreSQL session must see the committed denial evidence.
    with Session(engine) as db:
        entry = db.scalar(select(ActionLog).where(
            ActionLog.id > last_log_id, ActionLog.actor_id == actor_id,
            ActionLog.case_id == case_id, ActionLog.event_type == "denied",
        ).order_by(ActionLog.id.desc()))
        assert entry is not None and entry.remarks
        assert db.scalar(select(func.count()).select_from(Case)) == 30
    after = get(f"/cases/{case['id']}")
    assert {key: value for key, value in after.items() if key != "history"} == {
        key: value for key, value in before.items() if key != "history"
    }
    if not create:
        assert len(after["history"]) == len(before["history"]) + 1
        assert after["history"][-1]["event_type"] == "denied"


if __name__ == "__main__":
    for name, check in (
        ("HTTP case detail and chronological history", check_details),
        ("HTTP institution profile and bureau history", check_profile),
        ("HTTP supervisor creation denied (403; audit persisted)", lambda: check_denied("Dr. R. K. Sharma", create=True)),
        ("HTTP supervisor action denied (403; audit persisted)", lambda: check_denied("Dr. R. K. Sharma")),
        ("HTTP PGRC-to-RB action denied (403; audit persisted)", lambda: check_denied("Anita Rao")),
    ):
        try:
            check()
        except Exception:
            print(f"FAIL: {name}", flush=True)
            raise
        print(f"PASS: {name}", flush=True)
