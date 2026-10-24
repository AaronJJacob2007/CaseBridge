"""Case writes with explicit permission checks, plus details and history."""
from fastapi import HTTPException
from sqlalchemy import select

from backend.coordination_queries import case_links_and_requests
from backend.config import get_demo_today
from backend.models import ActionLog, Case, Institution, User
from backend.permissions import require_officer
from backend.queries import case_payload, query_cases


def require_case(db, case_id):
    case = db.get(Case, case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found")
    return case


def case_history(db, case_id):
    rows = db.execute(select(ActionLog, User).outerjoin(
        User, User.id == ActionLog.actor_id
    ).where(ActionLog.case_id == case_id).order_by(ActionLog.at, ActionLog.id))
    return [{
        "id": entry.id, "case_id": entry.case_id, "actor_id": entry.actor_id,
        "actor": actor.name if actor else None, "bureau": entry.bureau,
        "event_type": entry.event_type, "remarks": entry.remarks,
        "doc_ref": entry.doc_ref, "at": entry.at,
    } for entry, actor in rows]


def case_detail(db, case_id):
    case = require_case(db, case_id)
    institution = db.get(Institution, case.institution_id) if case.institution_id is not None else None
    officer = db.get(User, case.officer_id) if case.officer_id is not None else None
    result = case_payload(case, institution, officer)
    result["history"] = case_history(db, case_id)
    result["links"], result["coordination_requests"] = case_links_and_requests(db, case_id)
    return result


def institution_profile(db, institution_id):
    institution = db.get(Institution, institution_id)
    if institution is None:
        raise HTTPException(status_code=404, detail="Institution not found")
    cases = query_cases(db, aicte_id=institution.aicte_id)
    bureaus = set()
    for case in cases:
        case["history"] = case_history(db, case["id"])
        bureaus.add(case["bureau"])
        bureaus.update(entry["bureau"] for entry in case["history"] if entry["bureau"] is not None and entry["event_type"] != "denied")
    return {
        "id": institution.id, "aicte_id": institution.aicte_id,
        "name": institution.name, "address": institution.address,
        "region": institution.region, "campus": institution.campus,
        "bureaus_involved": sorted(bureaus), "cases": cases,
    }


def validate_owner(db, officer_id, bureau):
    officer = db.get(User, officer_id)
    if officer is None or officer.role != "officer" or officer.bureau != bureau:
        raise HTTPException(status_code=422, detail="Owner must be an officer in the case bureau")
    return officer


def create_case(db, actor, data):
    require_officer(db, actor, data.bureau)
    if db.scalar(select(Case.id).where(Case.case_code == data.case_code)) is not None:
        raise HTTPException(status_code=409, detail="Case code already exists")
    owner = validate_owner(db, data.officer_id or actor.id, data.bureau)
    institution = db.scalar(select(Institution).where(Institution.aicte_id == data.aicte_id)) if data.aicte_id else None
    case = Case(
        case_code=data.case_code, institution_id=institution.id if institution else None,
        identity_resolved=institution is not None, raw_aicte_id=data.aicte_id or None,
        raw_institution_name=data.institution_name, bureau=data.bureau, officer_id=owner.id,
        category=data.category, description=data.description, received_on=data.received_on,
        status=data.status, last_action=data.remarks, last_action_on=get_demo_today(),
        next_action=data.next_action, expected_disposal_on=data.expected_disposal_on,
    )
    db.add(case)
    db.flush()
    db.add(ActionLog(case_id=case.id, actor_id=actor.id, bureau=actor.bureau,
                     event_type="create", remarks=data.remarks))
    db.flush()
    return case.id


def add_case_action(db, actor, case_id, data):
    # Serialize actions on one case, then check its current bureau before mutation.
    case = db.scalar(select(Case).where(Case.id == case_id).with_for_update())
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found")
    require_officer(db, actor, case.bureau, case=case)
    if data.event_type == "transfer":
        if data.to_bureau == case.bureau:
            raise HTTPException(status_code=422, detail="Choose a different target bureau")
        owner = validate_owner(db, data.officer_id, data.to_bureau)
        case.bureau = data.to_bureau
        case.officer_id = owner.id
        case.status = "transferred"
    elif data.event_type == "escalate":
        case.status = "escalated"
    elif data.status is not None:
        case.status = data.status
    case.last_action = data.remarks
    case.last_action_on = get_demo_today()
    for field in ("next_action", "expected_disposal_on"):
        if field in data.model_fields_set:
            setattr(case, field, getattr(data, field))
    db.add(ActionLog(case_id=case.id, actor_id=actor.id, bureau=actor.bureau,
                     event_type=data.event_type, remarks=data.remarks, doc_ref=data.doc_ref))
    db.flush()
    return case.id
