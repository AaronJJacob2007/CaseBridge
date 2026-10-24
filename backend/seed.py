"""Explicit demo bootstrap; reruns insert missing rows without overwriting work.

The supplied demo CSV bootstraps the institution register. The reusable case
importer below NEVER creates institutions: unknown/missing IDs stay unresolved.
No runtime endpoint writes are implemented in Slice 1.
"""
import csv
from datetime import date
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.db import engine
from backend.models import ActionLog, Case, Institution, User

ROOT = Path(__file__).resolve().parents[1]


def read_rows(filename):
    with (ROOT / filename).open(newline="", encoding="utf-8-sig") as source:
        return list(csv.DictReader(source))


def log_creation(session, remarks, *, case=None, actor=None, bureau=None):
    session.add(ActionLog(
        event_type="create", remarks=remarks,
        case_id=case.id if case is not None else None,
        actor_id=actor.id if actor is not None else None, bureau=bureau,
    ))


def load_users(session, rows):
    for row in rows:
        matches = session.scalars(select(User).where(User.name == row["name"])).all()
        if len(matches) > 1:
            raise ValueError(f"Ambiguous officer name: {row['name']}")
        if matches:
            if any(getattr(matches[0], key) != row[key] for key in ("role", "bureau", "region")):
                raise ValueError(f"Existing demo user differs from CSV: {row['name']}")
            continue
        user = User(**row)
        session.add(user)
        session.flush()
        log_creation(session, f"Demo bootstrap: user {user.name}", bureau=user.bureau)


def bootstrap_institutions(session, rows):
    """Only the bundled synthetic CSV is the trusted demo institution source."""
    register = {}
    for row in rows:
        aicte_id = row["aicte_id"]
        if not aicte_id:
            continue
        fields = {"name": row["institution_name"], "address": row["address"], "region": row["region"]}
        if aicte_id in register and register[aicte_id] != fields:
            raise ValueError(f"Conflicting institution metadata for {aicte_id}")
        register[aicte_id] = fields
    for aicte_id, fields in register.items():
        existing = session.scalar(select(Institution).where(Institution.aicte_id == aicte_id))
        if existing is None:
            session.add(Institution(aicte_id=aicte_id, **fields))
            session.flush()
            log_creation(session, f"Demo bootstrap: institution {aicte_id}")


def import_case_rows(session, rows):
    """Resolve ONLY exact IDs in the existing register; preserve raw identity."""
    inserted = 0
    for row in rows:
        if session.scalar(select(Case.id).where(Case.case_code == row["case_code"])) is not None:
            continue
        institution = session.scalar(select(Institution).where(Institution.aicte_id == row["aicte_id"])) if row["aicte_id"] else None
        officers = session.scalars(select(User).where(User.name == row["officer"])).all()
        if len(officers) != 1:
            raise ValueError(f"Unknown or ambiguous officer: {row['officer']}")
        officer = officers[0]
        if officer.role != "officer" or officer.bureau != row["bureau"]:
            raise ValueError(f"Officer/bureau mismatch for {row['case_code']}")
        case = Case(
            case_code=row["case_code"],
            institution_id=institution.id if institution is not None else None,
            identity_resolved=institution is not None,
            raw_aicte_id=row["aicte_id"] or None,
            raw_institution_name=row["institution_name"], raw_region=row.get("region") or None,
            bureau=row["bureau"], officer_id=officer.id,
            category=row["category"], description=row["description"],
            received_on=date.fromisoformat(row["received_on"]), status=row["status"],
            last_action=row["last_action"],
            last_action_on=date.fromisoformat(row["last_action_on"]) if row["last_action_on"] else None,
            next_action=row["next_action"],
            expected_disposal_on=date.fromisoformat(row["expected_disposal_on"]) if row["expected_disposal_on"] else None,
        )
        session.add(case)
        session.flush()
        log_creation(session, "Demo case import", case=case, actor=officer, bureau=case.bureau)
        inserted += 1
    return inserted


def seed_demo(session):
    load_users(session, read_rows("seed_users.csv"))
    rows = read_rows("seed_cases.csv")
    bootstrap_institutions(session, rows)
    inserted = import_case_rows(session, rows)
    session.flush()
    return inserted


if __name__ == "__main__":
    with Session(engine) as session, session.begin():
        inserted = seed_demo(session)
        users = session.scalar(select(func.count()).select_from(User))
        institutions = session.scalar(select(func.count()).select_from(Institution))
        cases = session.scalar(select(func.count()).select_from(Case))
    print(f"Seed: {users} users, {institutions} institutions, {cases} cases")
    print(f"Inserted {inserted} cases; existing cases and history preserved")
