"""Slice 3 request bodies; schema and dependencies remain unchanged."""
from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from backend.case_inputs import Bureau


class LinkReview(BaseModel):
    model_config = ConfigDict(extra="forbid")
    case_a: int = Field(gt=0)
    case_b: int = Field(gt=0)
    type: Literal["cross_bureau_overlap", "related_incident"] = "cross_bureau_overlap"
    review_state: Literal["confirmed", "rejected"]
    reason: str | None = None

    @model_validator(mode="after")
    def validate_pair_and_reason(self):
        if self.case_a == self.case_b:
            raise ValueError("Choose two different cases")
        if self.reason is not None:
            self.reason = self.reason.strip()
        if self.review_state == "rejected" and not self.reason:
            raise ValueError("A rejection reason is required")
        return self


class CoordinationCheck(BaseModel):
    model_config = ConfigDict(extra="forbid")
    link_id: int = Field(gt=0)
    action_type: str = Field(min_length=1)
    doc_category: str | None = None
    period: str | None = None

    @field_validator("action_type", "doc_category", "period")
    @classmethod
    def nonblank(cls, value):
        if value is None:
            return value
        if not value.strip():
            raise ValueError("Use a nonblank value or null for optional fields")
        return value.strip()


class CoordinationCreate(CoordinationCheck):
    to_bureau: Bureau
    follow_up_on: date | None = None
    decision: Literal["coordinate", "proceed_separately"] | None = None
    proceed_reason: str | None = None

    @model_validator(mode="after")
    def validate_decision(self):
        if self.proceed_reason is not None:
            self.proceed_reason = self.proceed_reason.strip()
        if self.decision == "proceed_separately" and not self.proceed_reason:
            raise ValueError("A reason is required to proceed separately")
        if self.decision != "proceed_separately" and self.proceed_reason is not None:
            raise ValueError("proceed_reason requires proceed_separately")
        return self


class CoordinationAck(BaseModel):
    model_config = ConfigDict(extra="forbid")
    owner_id: int = Field(gt=0)
    follow_up_on: date


class CoordinationComplete(BaseModel):
    model_config = ConfigDict(extra="forbid")
    remarks: str = "Coordination request completed"

    @field_validator("remarks")
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError("Completion remarks must not be blank")
        return value.strip()
