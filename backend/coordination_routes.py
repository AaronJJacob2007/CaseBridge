"""Slice 3 endpoints, using the existing demo identity and DB dependencies."""
from fastapi import APIRouter
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from backend.case_routes import Database, DemoUser
from backend.coordination_inputs import (
    CoordinationAck, CoordinationCheck, CoordinationComplete, CoordinationCreate, LinkReview,
)
from backend.coordination_queries import link_payload, request_payload
from backend.coordination_service import (
    acknowledge, check_coordination, complete, create_coordination, review_link,
)

router = APIRouter()


@router.post("/links")
def post_link(data: LinkReview, db: Database, actor: DemoUser):
    link = review_link(db, actor, data)
    db.commit()
    return link_payload(link)


@router.post("/coordination/check")
def post_check(data: CoordinationCheck, db: Database, actor: DemoUser):
    return check_coordination(db, actor, data)


@router.post("/coordination")
def post_coordination(data: CoordinationCreate, db: Database, actor: DemoUser):
    result, status = create_coordination(db, actor, data)
    db.commit()
    return JSONResponse(status_code=status, content=jsonable_encoder(result))


@router.post("/coordination/{request_id}/ack")
def post_ack(request_id: int, data: CoordinationAck, db: Database, actor: DemoUser):
    request = acknowledge(db, actor, request_id, data)
    db.commit()
    return request_payload(db, request)


@router.post("/coordination/{request_id}/complete")
def post_complete(request_id: int, data: CoordinationComplete, db: Database, actor: DemoUser):
    request = complete(db, actor, request_id, data)
    db.commit()
    return request_payload(db, request)
