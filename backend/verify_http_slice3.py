"""Live Slice 3 reads/validation and a durable supervisor denial.

Successful review/request/ack/completion writes are exercised by the rollback-
isolated PostgreSQL ASGI tests. This live check does not leave links or requests.
"""
import json
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.db import engine
from backend.models import ActionLog, CaseLink, CoordinationRequest, User
from backend.verify_http import BASE, get


def actor_id(name):
    with Session(engine) as db:
        value = db.scalar(select(User.id).where(User.name == name))
        assert value is not None
        return value


def post(path, body, actor, expected):
    request = Request(BASE + path, data=json.dumps(body).encode(), method="POST",
                      headers={"Content-Type": "application/json", "X-User-Id": str(actor)})
    try:
        with urlopen(request, timeout=10) as response:
            status, result = response.status, json.load(response)
    except HTTPError as error:
        status, result = error.code, json.load(error)
    assert status == expected, f"{path}: expected {expected}, got {status}: {result}"
    return result


def check_reload():
    case = get("/cases", case_code="PGRC-101")[0]
    detail = get(f"/cases/{case['id']}")
    assert isinstance(detail["links"], list) and isinstance(detail["coordination_requests"], list)
    assert detail["case_code"] == "PGRC-101"
    for link in detail["links"]:
        assert link["case_a"] < link["case_b"] and link["review_state"]
    for request in detail["coordination_requests"]:
        assert request["link_id"] and request["action_type"] and request["status"]


def check_link_denial():
    actor = actor_id("Dr. R. K. Sharma")
    pair = [get("/cases", case_code=code)[0]["id"] for code in ("PGRC-101", "RB-201")]
    with Session(engine) as db:
        last_id = db.scalar(select(func.max(ActionLog.id))) or 0
        before = db.scalar(select(func.count()).select_from(CaseLink))
    result = post("/links", {"case_a": pair[0], "case_b": pair[1], "review_state": "confirmed"}, actor, 403)
    assert result["detail"]
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(CaseLink)) == before
        assert db.scalar(select(ActionLog.id).where(
            ActionLog.id > last_id, ActionLog.actor_id == actor, ActionLog.event_type == "denied",
        )) is not None


def check_validation():
    actor = actor_id("Anita Rao")
    pair = [get("/cases", case_code=code)[0]["id"] for code in ("PGRC-101", "RB-201")]
    with Session(engine) as db:
        before = (db.scalar(select(func.count()).select_from(CaseLink)),
                  db.scalar(select(func.count()).select_from(CoordinationRequest)))
    assert post("/links", {"case_a": pair[0], "case_b": pair[1], "review_state": "rejected"}, actor, 422)["detail"]
    assert post("/coordination", {"link_id": 2147483647, "action_type": "Document request",
                "to_bureau": "RB", "decision": "proceed_separately"}, actor, 422)["detail"]
    assert post("/coordination/check", {"link_id": 2147483647, "action_type": "Document request"}, actor, 404)["detail"]
    assert post("/coordination/2147483647/ack", {"owner_id": actor, "follow_up_on": "2026-10-30"}, actor, 404)["detail"]
    assert post("/coordination/2147483647/complete", {}, actor, 404)["detail"]
    with Session(engine) as db:
        after = (db.scalar(select(func.count()).select_from(CaseLink)),
                 db.scalar(select(func.count()).select_from(CoordinationRequest)))
        assert after == before


if __name__ == "__main__":
    for name, check in (
        ("HTTP case reload includes links and coordination requests", check_reload),
        ("HTTP supervisor link review denied (403; audit persisted)", check_link_denial),
        ("HTTP coordination validation and missing resources (422/404)", check_validation),
    ):
        try:
            check()
        except Exception:
            print(f"FAIL: {name}", flush=True)
            raise
        print(f"PASS: {name}", flush=True)
