"""Slice 3: cases, link review and acknowledged coordination."""
from datetime import date
from typing import Annotated, Literal

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.case_routes import router as case_router
from backend.coordination_routes import router as coordination_router
from backend.dependencies import get_db
from backend.config import get_demo_today
from backend.db import engine
from backend.queries import query_cases, query_overlaps

app = FastAPI(title="CaseBridge")
app.include_router(case_router)
app.include_router(coordination_router)
# Validate configuration at startup/import, without reading the wall clock.
get_demo_today()


@app.get("/health")
def health():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1")).scalar_one()
    except SQLAlchemyError:
        return JSONResponse(status_code=503, content={"status": "error", "database": "unavailable"})
    return {"status": "ok", "database": "ok"}


@app.get("/cases")
def list_cases(
    db: Annotated[Session, Depends(get_db)],
    institution_name: str | None = None, aicte_id: str | None = None,
    case_code: str | None = None,
    bureau: Literal["RB", "PGRC", "OTHER"] | None = None,
    region: str | None = None, category: str | None = None,
    status: Literal["pending", "under_process", "escalated", "transferred", "disposed"] | None = None,
    received_from: date | None = None, received_to: date | None = None,
):
    if received_from is not None and received_to is not None and received_from > received_to:
        raise HTTPException(status_code=422, detail="received_from must be on or before received_to")
    return query_cases(
        db, institution_name=institution_name, aicte_id=aicte_id, case_code=case_code,
        bureau=bureau, region=region, category=category, status=status,
        received_from=received_from, received_to=received_to,
    )


@app.get("/overlaps")
def list_overlaps(db: Annotated[Session, Depends(get_db)]):
    return query_overlaps(db)
