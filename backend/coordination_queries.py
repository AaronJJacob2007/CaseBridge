"""Database-backed link/request payloads for responses and case reloads."""
from sqlalchemy import or_, select

from backend.models import CaseLink, CoordinationRequest, User


def link_payload(link):
    return {key: getattr(link, key) for key in (
        "id", "case_a", "case_b", "type", "review_state", "reviewed_by", "reason", "reviewed_at",
    )}


def request_payload(db, request):
    result = {key: getattr(request, key) for key in (
        "id", "link_id", "institution_id", "requested_by", "to_bureau", "action_type",
        "doc_category", "period", "status", "owner_id", "follow_up_on", "proceed_reason",
        "created_at", "acknowledged_at",
    )}
    actor = db.get(User, request.requested_by)
    owner = db.get(User, request.owner_id) if request.owner_id else None
    result["requester"] = actor.name if actor else None
    result["owner"] = owner.name if owner else None
    return result


def case_links_and_requests(db, case_id):
    links = db.scalars(select(CaseLink).where(or_(
        CaseLink.case_a == case_id, CaseLink.case_b == case_id,
    )).order_by(CaseLink.id)).all()
    if not links:
        return [], []
    requests = db.scalars(select(CoordinationRequest).where(
        CoordinationRequest.link_id.in_([link.id for link in links]),
    ).order_by(CoordinationRequest.created_at, CoordinationRequest.id))
    return [link_payload(link) for link in links], [request_payload(db, row) for row in requests]
