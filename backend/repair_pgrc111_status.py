"""Targeted demo repair; retains all history, links and requests.

Run with python -m backend.repair_pgrc111_status.
Only PGRC-111's disposed -> pending transition is allowed; reruns are a no-op.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.case_inputs import CaseAction
from backend.case_service import add_case_action
from backend.db import engine
from backend.models import Case, Institution, User
from backend.seed import read_rows


def repair(db):
    row = next(row for row in read_rows("seed_cases.csv") if row["case_code"] == "PGRC-111")
    if row["status"] != "pending":
        raise RuntimeError("Reference status changed; refusing this targeted repair.")
    case = db.scalar(select(Case).where(Case.case_code == row["case_code"]).with_for_update())
    if case is None:
        raise RuntimeError("PGRC-111 is missing; no repair applied.")
    institution = db.get(Institution, case.institution_id)
    owner = db.get(User, case.officer_id)
    if (institution is None or institution.aicte_id != row["aicte_id"]
            or not case.identity_resolved or case.bureau != row["bureau"]
            or owner is None or owner.name != row["officer"]):
        raise RuntimeError("PGRC-111 identity/bureau/owner differs; no repair applied.")
    if case.status == "pending":
        return "PGRC-111 already pending; no changes made."
    if case.status != "disposed":
        raise RuntimeError("PGRC-111 is neither disposed nor pending; no repair applied.")
    # Existing service enforces permissions and records an ordinary case action
    # under the assigned demo officer. Omitted deadlines/next actions are kept.
    add_case_action(db, owner, case.id, CaseAction(
        status="pending",
        remarks="Demo reference repair: restore PGRC-111 from disposed to pending "
                "to match seed_cases.csv; previous history retained.",
    ))
    return "PGRC-111 restored: disposed -> pending; repair audit recorded."


if __name__ == "__main__":
    with Session(engine) as session, session.begin():
        message = repair(session)
    print(message)
