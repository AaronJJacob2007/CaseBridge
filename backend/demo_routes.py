"""Read-only database-backed demo user discovery for the overview UI."""
from typing import Annotated

from fastapi import APIRouter, Header, HTTPException
from sqlalchemy import select

from backend.case_routes import Database
from backend.models import User

router = APIRouter()


def user_payload(user):
    return {key: getattr(user, key) for key in ("id", "name", "role", "bureau", "region")}


@router.get("/demo/users")
def demo_users(db: Database):
    # Bootstrap cannot know a user ID until this read-only discovery succeeds.
    return [user_payload(user) for user in db.scalars(select(User).order_by(User.id))]


@router.get("/demo/me")
def demo_me(db: Database, x_user_id: Annotated[str | None, Header(alias="X-User-Id")] = None):
    try:
        user_id = int(x_user_id) if x_user_id is not None else None
    except ValueError:
        user_id = None
    user = db.get(User, user_id) if user_id is not None else None
    if user is None:
        # A failed identity read is not a write attempt; it creates no audit row.
        raise HTTPException(status_code=403, detail="Select a valid demo user")
    return user_payload(user)
