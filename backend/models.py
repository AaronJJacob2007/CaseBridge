"""Mappings of the six existing schema.sql tables; never create/alter tables here."""
from sqlalchemy import (
    Boolean, CheckConstraint, Column, Date, DateTime, ForeignKey, Index,
    Integer, Text, UniqueConstraint, text,
)
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class Institution(Base):
    __tablename__ = "institutions"
    id = Column(Integer, primary_key=True)
    aicte_id = Column(Text, unique=True, nullable=False)
    name = Column(Text, nullable=False)
    address = Column(Text)
    region = Column(Text)
    campus = Column(Text)


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("role IN ('officer', 'supervisor')"),
        CheckConstraint("bureau IN ('RB', 'PGRC', 'OTHER')"),
    )
    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False)
    role = Column(Text, nullable=False)
    bureau = Column(Text, nullable=False)
    region = Column(Text)


class Case(Base):
    __tablename__ = "cases"
    __table_args__ = (
        CheckConstraint("bureau IN ('RB', 'PGRC', 'OTHER')"),
        CheckConstraint("status IN ('pending', 'under_process', 'escalated', 'transferred', 'disposed')"),
        Index("idx_cases_inst", "institution_id", "bureau", "status"),
    )
    id = Column(Integer, primary_key=True)
    case_code = Column(Text, unique=True, nullable=False)
    institution_id = Column(Integer, ForeignKey("institutions.id"))
    identity_resolved = Column(Boolean, nullable=False, server_default=text("TRUE"))
    raw_aicte_id = Column(Text)
    raw_institution_name = Column(Text)
    bureau = Column(Text, nullable=False)
    officer_id = Column(Integer, ForeignKey("users.id"))
    category = Column(Text)
    description = Column(Text)
    received_on = Column(Date, nullable=False)
    status = Column(Text, nullable=False)
    last_action = Column(Text)
    last_action_on = Column(Date)
    next_action = Column(Text)
    expected_disposal_on = Column(Date)


class CaseLink(Base):
    __tablename__ = "case_links"
    __table_args__ = (
        CheckConstraint("type IN ('cross_bureau_overlap', 'related_incident')"),
        CheckConstraint("review_state IN ('suggested', 'confirmed', 'rejected')"),
        CheckConstraint("case_a < case_b"),
        UniqueConstraint("case_a", "case_b"),
    )
    id = Column(Integer, primary_key=True)
    case_a = Column(Integer, ForeignKey("cases.id"), nullable=False)
    case_b = Column(Integer, ForeignKey("cases.id"), nullable=False)
    type = Column(Text, nullable=False)
    review_state = Column(Text, nullable=False)
    reviewed_by = Column(Integer, ForeignKey("users.id"))
    reason = Column(Text)
    reviewed_at = Column(DateTime(timezone=True))


class CoordinationRequest(Base):
    __tablename__ = "coordination_requests"
    __table_args__ = (
        CheckConstraint("to_bureau IN ('RB', 'PGRC', 'OTHER')"),
        CheckConstraint("status IN ('requested', 'acknowledged', 'in_progress', 'completed', 'declined')"),
        Index("idx_coord_match", "institution_id", "action_type", "doc_category", "period", "status"),
    )
    id = Column(Integer, primary_key=True)
    link_id = Column(Integer, ForeignKey("case_links.id"), nullable=False)
    institution_id = Column(Integer, ForeignKey("institutions.id"), nullable=False)
    requested_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    to_bureau = Column(Text, nullable=False)
    action_type = Column(Text, nullable=False)
    doc_category = Column(Text)
    period = Column(Text)
    status = Column(Text, nullable=False, server_default=text("'requested'"))
    owner_id = Column(Integer, ForeignKey("users.id"))
    follow_up_on = Column(Date)
    proceed_reason = Column(Text)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    acknowledged_at = Column(DateTime(timezone=True))


class ActionLog(Base):
    __tablename__ = "action_log"
    __table_args__ = (
        CheckConstraint("event_type IN ('create', 'update', 'transfer', 'escalate', 'link_review', 'coord_request', 'coord_ack', 'denied')"),
        Index("idx_log_case", "case_id", "at"),
    )
    id = Column(Integer, primary_key=True)
    case_id = Column(Integer, ForeignKey("cases.id"))
    actor_id = Column(Integer, ForeignKey("users.id"))
    bureau = Column(Text)
    event_type = Column(Text, nullable=False)
    remarks = Column(Text)
    doc_ref = Column(Text)
    at = Column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
