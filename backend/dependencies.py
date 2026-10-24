"""Request-scoped database access and demo identity (not authentication)."""
from typing import Annotated

from fastapi import Depends, Header
from sqlalchemy.orm import Session

from backend.db import engine
from backend.models import User
from backend.permissions import deny_write


def get_db():
    with Session(engine) as session:
        yield session


def get_demo_user(
    db: Annotated[Session, Depends(get_db)],
    x_user_id: Annotated[str | None, Header(alias="X-User-Id")] = None,
):
    try:
        user_id = int(x_user_id) if x_user_id is not None else None
    except ValueError:
        user_id = None
    actor = db.get(User, user_id) if user_id is not None else None
    if actor is None:
        deny_write(db, None, "Missing or unknown demo user (X-User-Id)")
    return actor
