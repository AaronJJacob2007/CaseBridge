"""Manual link review and institution-scoped, serialized coordination writes."""
from fastapi import HTTPException
from sqlalchemy import func, select

from backend.case_service import validate_owner
from backend.coordination_queries import link_payload, request_payload
from backend.models import ActionLog, Case, CaseLink, CoordinationRequest, Institution
from backend.permissions import deny_write, require_officer

PENDING = ("requested", "acknowledged", "in_progress")


def get_pair(db, case_a, case_b, *, lock=False):
    statement = select(Case).where(Case.id.in_([case_a, case_b])).order_by(Case.id)
    if lock:
        statement = statement.with_for_update().execution_options(populate_existing=True)
    cases = db.scalars(statement).all()
    if len(cases) != 2:
        raise HTTPException(status_code=404, detail="One or both linked cases were not found")
    return cases


def require_participant(db, actor, cases):
    own_case = next((case for case in cases if case.bureau == actor.bureau), cases[0])
    if actor.role != "officer":
        deny_write(db, actor, "Supervisors are read-only", case=own_case)
    if actor.bureau not in {case.bureau for case in cases}:
        deny_write(db, actor, "Only officers in a linked case's bureau may coordinate", case=own_case)


def validate_identity(cases):
    if any(not case.identity_resolved or case.institution_id is None for case in cases):
        raise HTTPException(status_code=422, detail="Unresolved cases cannot be linked")
    if cases[0].institution_id != cases[1].institution_id:
        raise HTTPException(status_code=422, detail="Cases must have the same exact institution ID")


def lock_pair(db, actor, cases):
    require_participant(db, actor, cases)
    validate_identity(cases)
    institution_id = cases[0].institution_id
    # Common lock order: institution, cases in ID order, link, then request.
    # This serializes the final duplicate check/save across the institution's links.
    db.scalar(select(Institution).where(Institution.id == institution_id).with_for_update())
    cases = get_pair(db, cases[0].id, cases[1].id, lock=True)
    require_participant(db, actor, cases)
    validate_identity(cases)
    return cases


def audit_pair(db, actor, cases, event_type, remarks):
    for case in cases:
        db.add(ActionLog(case_id=case.id, actor_id=actor.id, bureau=actor.bureau,
                         event_type=event_type, remarks=remarks))
    db.flush()


def review_link(db, actor, data):
    cases = lock_pair(db, actor, get_pair(db, data.case_a, data.case_b))
    if data.type == "cross_bureau_overlap" and cases[0].bureau == cases[1].bureau:
        raise HTTPException(status_code=422, detail="Cross-bureau links require different bureaus")
    link = db.scalar(select(CaseLink).where(
        CaseLink.case_a == cases[0].id, CaseLink.case_b == cases[1].id,
    ).with_for_update())
    if link is None:
        link = CaseLink(case_a=cases[0].id, case_b=cases[1].id)
        db.add(link)
    link.type = data.type
    link.review_state = data.review_state
    link.reviewed_by = actor.id
    link.reason = data.reason
    link.reviewed_at = func.now()
    db.flush()
    audit_pair(db, actor, cases, "link_review",
               f"Link {link.id}: {data.review_state}; reason: {data.reason or 'not supplied'}")
    return link


def link_context(db, actor, link_id, *, confirmed=True):
    link = db.get(CaseLink, link_id)
    if link is None:
        raise HTTPException(status_code=404, detail="Link not found")
    cases = lock_pair(db, actor, get_pair(db, link.case_a, link.case_b))
    link = db.scalar(select(CaseLink).where(CaseLink.id == link_id).with_for_update().execution_options(populate_existing=True))
    if confirmed and link.review_state != "confirmed":
        raise HTTPException(status_code=409, detail="Coordination requires a confirmed link")
    return link, cases


def matching_request(db, institution_id, data):
    # The target bureau and requester are deliberately not matching keys.
    # A different confirmed pair at the SAME institution must not bypass warning.
    return db.scalar(select(CoordinationRequest).join(
        CaseLink, CaseLink.id == CoordinationRequest.link_id,
    ).where(
        CoordinationRequest.institution_id == institution_id,
        CaseLink.review_state == "confirmed",
        CoordinationRequest.action_type == data.action_type,
        CoordinationRequest.doc_category == data.doc_category,
        CoordinationRequest.period == data.period,
        CoordinationRequest.status.in_(PENDING),
    ).order_by(CoordinationRequest.created_at, CoordinationRequest.id).limit(1))


def warning_payload(db, existing):
    return {"warning": existing is not None,
            "existing_request": request_payload(db, existing) if existing else None,
            "choices": ["coordinate", "proceed_separately"] if existing else []}


def check_coordination(db, actor, data):
    _, cases = link_context(db, actor, data.link_id)
    return warning_payload(db, matching_request(db, cases[0].institution_id, data))


def create_coordination(db, actor, data):
    link, cases = link_context(db, actor, data.link_id)
    if data.to_bureau == actor.bureau or data.to_bureau not in {case.bureau for case in cases}:
        raise HTTPException(status_code=422, detail="Target must be the other linked bureau")
    existing = matching_request(db, cases[0].institution_id, data)
    if existing is not None and data.decision is None:
        return warning_payload(db, existing), 409
    if data.decision == "coordinate":
        if existing is None:
            raise HTTPException(status_code=409, detail="No matching pending request remains; check again")
        audit_pair(db, actor, cases, "coord_request", f"Coordinate with existing request {existing.id}; no duplicate created")
        return {"outcome": "coordinated", "request": request_payload(db, existing)}, 200
    request = CoordinationRequest(
        link_id=link.id, institution_id=cases[0].institution_id, requested_by=actor.id,
        to_bureau=data.to_bureau, action_type=data.action_type,
        doc_category=data.doc_category, period=data.period, status="requested",
        proceed_reason=data.proceed_reason, follow_up_on=data.follow_up_on,
    )
    db.add(request)
    db.flush()
    audit_pair(db, actor, cases, "coord_request",
               f"Request {request.id}: {data.action_type}; documents: {data.doc_category}; period: {data.period}; "
               f"target: {data.to_bureau}; follow-up: {data.follow_up_on}; proceed reason: {data.proceed_reason or 'not applicable'}")
    return {"outcome": "created", "request": request_payload(db, request)}, 201


def request_context(db, actor, request_id, *, confirmed=True):
    request = db.get(CoordinationRequest, request_id)
    if request is None:
        raise HTTPException(status_code=404, detail="Coordination request not found")
    _, cases = link_context(db, actor, request.link_id, confirmed=confirmed)
    request = db.scalar(select(CoordinationRequest).where(
        CoordinationRequest.id == request_id,
    ).with_for_update().execution_options(populate_existing=True))
    own_case = next((case for case in cases if case.bureau == request.to_bureau), cases[0])
    require_officer(db, actor, request.to_bureau, case=own_case)
    return request, cases


def acknowledge(db, actor, request_id, data):
    request, cases = request_context(db, actor, request_id)
    if request.status != "requested":
        raise HTTPException(status_code=409, detail="Only a requested item can be acknowledged")
    owner = validate_owner(db, data.owner_id, request.to_bureau)
    request.status = "acknowledged"
    request.owner_id = owner.id
    request.follow_up_on = data.follow_up_on
    request.acknowledged_at = func.now()
    db.flush()
    audit_pair(db, actor, cases, "coord_ack",
               f"Request {request.id} acknowledged; owner: {owner.name}; follow-up: {data.follow_up_on}")
    return request


def complete(db, actor, request_id, data):
    # A rejected link does not auto-close its request; the target can still finish it.
    request, cases = request_context(db, actor, request_id, confirmed=False)
    if request.status not in PENDING:
        raise HTTPException(status_code=409, detail="Request is already completed or declined")
    request.status = "completed"
    db.flush()
    # schema.sql has no coord_complete event; use its allowed 'update' value.
    audit_pair(db, actor, cases, "update", f"Request {request.id} completed: {data.remarks}")
    return request
