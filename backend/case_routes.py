"""Slice 2 routes. Successful writes and denial audits survive new requests."""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.case_inputs import CaseAction, CaseCreate
from backend.case_service import add_case_action, case_detail, create_case, institution_profile
from backend.dependencies import get_db, get_demo_user
from backend.models import User

router = APIRouter()
Database = Annotated[Session, Depends(get_db)]
DemoUser = Annotated[User, Depends(get_demo_user)]


@router.post("/cases", status_code=201)
def post_case(data: CaseCreate, db: Database, actor: DemoUser):
    try:
        case_id = create_case(db, actor, data)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Case conflicts with an existing record") from None
    return case_detail(db, case_id)


@router.get("/cases/{case_id}")
def get_case(case_id: int, db: Database):
    return case_detail(db, case_id)


@router.post("/cases/{case_id}/actions")
def post_action(case_id: int, data: CaseAction, db: Database, actor: DemoUser):
    add_case_action(db, actor, case_id, data)
    db.commit()
    return case_detail(db, case_id)


@router.get("/institutions/{institution_id}")
def get_institution(institution_id: int, db: Database):
    return institution_profile(db, institution_id)
