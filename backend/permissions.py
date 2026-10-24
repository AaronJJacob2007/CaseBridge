"""All authorization happens before mutation; denied attempts are committed."""
from fastapi import HTTPException

from backend.models import ActionLog


def deny_write(db, actor, reason, *, case=None):
    # Request sessions have not mutated a case before this call. Commit the audit
    # row explicitly: an HTTPException must not roll back the denial evidence.
    db.add(ActionLog(
        case_id=case.id if case is not None else None,
        actor_id=actor.id if actor is not None else None,
        bureau=actor.bureau if actor is not None else None,
        event_type="denied", remarks=reason,
    ))
    db.commit()
    raise HTTPException(status_code=403, detail=reason)


def require_officer(db, actor, bureau, *, case=None):
    if actor.role != "officer":
        deny_write(db, actor, "Supervisors are read-only", case=case)
    if actor.bureau != bureau:
        deny_write(db, actor, "Officers may write only on their own bureau's cases", case=case)
