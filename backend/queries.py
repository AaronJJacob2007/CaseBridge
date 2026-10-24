"""Read-only PostgreSQL queries for the case register and overlap alerts."""
from datetime import date

from sqlalchemy import distinct, func, select
from sqlalchemy.orm import Session

from backend.models import Case, Institution, User

OVERLAP_MESSAGE = "Potential Overlapping Cases - Coordination Required"


def case_payload(case, institution, officer):
    return {
        "id": case.id, "case_code": case.case_code,
        "institution_id": case.institution_id,
        "identity_resolved": case.identity_resolved,
        "aicte_id": institution.aicte_id if institution else None,
        "institution_name": institution.name if institution else case.raw_institution_name,
        "raw_aicte_id": case.raw_aicte_id,
        "raw_institution_name": case.raw_institution_name,
        "address": institution.address if institution else None,
        "region": institution.region if institution else None,
        "bureau": case.bureau, "officer_id": case.officer_id,
        "officer": officer.name if officer else None,
        "category": case.category, "description": case.description,
        "received_on": case.received_on, "status": case.status,
        "last_action": case.last_action, "last_action_on": case.last_action_on,
        "next_action": case.next_action,
        "expected_disposal_on": case.expected_disposal_on,
    }


def query_cases(session: Session, *, institution_name: str | None = None,
                aicte_id: str | None = None, case_code: str | None = None,
                bureau: str | None = None, region: str | None = None,
                category: str | None = None, status: str | None = None,
                received_from: date | None = None, received_to: date | None = None):
    statement = select(Case, Institution, User).outerjoin(
        Institution, Case.institution_id == Institution.id
    ).outerjoin(User, Case.officer_id == User.id)
    if institution_name is not None:
        # Literal, case-insensitive substring; user % and _ are not wildcards.
        statement = statement.where(func.coalesce(Institution.name, Case.raw_institution_name).icontains(institution_name, autoescape=True))
    for column, value in (
        (Institution.aicte_id, aicte_id), (Case.case_code, case_code),
        (Case.bureau, bureau), (Institution.region, region),
        (Case.category, category), (Case.status, status),
    ):
        if value is not None:
            statement = statement.where(column == value)
    if received_from is not None:
        statement = statement.where(Case.received_on >= received_from)
    if received_to is not None:
        statement = statement.where(Case.received_on <= received_to)
    return [case_payload(*row) for row in session.execute(statement.order_by(Case.case_code))]


def query_overlaps(session: Session):
    eligible = select(Case.institution_id).where(
        Case.identity_resolved.is_(True), Case.institution_id.is_not(None),
        Case.status != "disposed",
    ).group_by(Case.institution_id).having(func.count(distinct(Case.bureau)) >= 2)
    statement = select(Case, Institution, User).join(
        Institution, Institution.id == Case.institution_id
    ).outerjoin(User, User.id == Case.officer_id).where(
        Case.institution_id.in_(eligible), Case.identity_resolved.is_(True),
        Case.status != "disposed",
    ).order_by(Institution.aicte_id, Case.case_code)
    groups = {}
    for case, institution, officer in session.execute(statement):
        group = groups.setdefault(institution.id, {
            "institution_id": institution.id, "aicte_id": institution.aicte_id,
            "institution_name": institution.name, "message": OVERLAP_MESSAGE,
            "cases": [],
        })
        group["cases"].append(case_payload(case, institution, officer))
    return list(groups.values())
