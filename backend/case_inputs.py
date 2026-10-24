"""Validated request bodies; no identity normalization or extra fields."""
from datetime import date
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from backend.config import get_demo_today

Bureau = Literal["RB", "PGRC", "OTHER"]
Status = Literal["pending", "under_process", "escalated", "transferred", "disposed"]
OfficerId = Annotated[int, Field(gt=0)]


class CaseCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    case_code: str = Field(min_length=1)
    aicte_id: str | None = None
    institution_name: str = Field(min_length=1)
    raw_region: str | None = None
    bureau: Bureau
    officer_id: OfficerId | None = None
    category: str | None = None
    description: str | None = None
    received_on: date = Field(default_factory=get_demo_today)
    status: Status = "pending"
    remarks: str = "Case registered"
    next_action: str | None = None
    expected_disposal_on: date | None = None

    @field_validator("case_code", "institution_name", "remarks")
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError("Must not be blank")
        return value.strip()


    @field_validator("raw_region")
    @classmethod
    def nonblank_region(cls, value):
        if value is not None and not value.strip():
            raise ValueError("raw_region must be nonblank or null")
        return value.strip() if value is not None else None


class CaseAction(BaseModel):
    model_config = ConfigDict(extra="forbid")
    event_type: Literal["update", "transfer", "escalate"] = "update"
    remarks: str = Field(min_length=1)
    doc_ref: str | None = None
    status: Status | None = None
    next_action: str | None = None
    expected_disposal_on: date | None = None
    to_bureau: Bureau | None = None
    officer_id: OfficerId | None = None

    @field_validator("remarks")
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError("Remarks are required")
        return value.strip()

    @field_validator("doc_ref")
    @classmethod
    def filename_only(cls, value):
        if value is not None and (not value.strip() or "/" in value or "\\" in value or ":" in value or value in {".", ".."}):
            raise ValueError("doc_ref must be a file name only")
        return value

    @model_validator(mode="after")
    def action_fields(self):
        if self.event_type == "transfer":
            if self.to_bureau is None or self.officer_id is None:
                raise ValueError("Transfers require to_bureau and a target officer_id")
            if self.status not in (None, "transferred"):
                raise ValueError("Transfer status must be transferred")
        else:
            if self.to_bureau is not None or self.officer_id is not None:
                raise ValueError("Only transfers may change bureau or officer")
            if self.event_type == "escalate" and self.status not in (None, "escalated"):
                raise ValueError("Escalation status must be escalated")
            if self.event_type == "update" and self.status in {"escalated", "transferred"}:
                raise ValueError("Use the matching transfer or escalate event_type")
        return self
