"""Slice 2 HTTP/transaction tests on real PostgreSQL; all changes rolled back."""
import pytest
from sqlalchemy import func, select

from backend.config import get_demo_today
from backend.models import ActionLog, Case, Institution


def case_id(api, code="PGRC-101"):
    return api.db.scalar(select(Case.id).where(Case.case_code == code))


def payload(**changes):
    return {"case_code": "SLICE2-NEW", "institution_name": "Synthetic institution",
            "aicte_id": "INST-0001", "bureau": "PGRC", **changes}


def count(api, model):
    return api.db.scalar(select(func.count()).select_from(model))


def test_create_case_survives_new_request_and_has_audit(api):
    actor = api.user("Anita Rao")
    code, created = api.request("POST", "/cases", payload(description="Synthetic case"), actor)
    assert code == 201
    assert created["identity_resolved"] is True
    assert created["officer_id"] == actor
    assert created["aicte_id"] == "INST-0001"
    status, fetched = api.request("GET", f"/cases/{created['id']}")
    assert status == 200 and fetched == created
    assert fetched["received_on"] == get_demo_today().isoformat()
    assert fetched["last_action_on"] == get_demo_today().isoformat()
    assert len(fetched["history"]) == 1
    entry = fetched["history"][0]
    assert (entry["event_type"], entry["actor_id"], entry["bureau"]) == ("create", actor, "PGRC")
    assert entry["remarks"] == "Case registered"


@pytest.mark.parametrize("raw_id", [None, "", "INST-UNKNOWN", "inst-0001"])
def test_create_missing_unknown_or_nonexact_id_stays_unresolved(api, raw_id):
    status, created = api.request("POST", "/cases", payload(
        aicte_id=raw_id, institution_name="Riverbend Institute of Technology"), api.user("Anita Rao"))
    assert status == 201
    assert created["identity_resolved"] is False
    assert created["institution_id"] is None
    assert created["raw_aicte_id"] == (raw_id or None)
    assert created["raw_institution_name"] == "Riverbend Institute of Technology"
    assert count(api, Institution) == 8
    _, overlaps = api.request("GET", "/overlaps")
    assert all(item["id"] != created["id"] for group in overlaps for item in group["cases"])


def test_create_exact_id_does_not_require_name_match(api):
    status, created = api.request("POST", "/cases", payload(institution_name="Different name"), api.user("Anita Rao"))
    assert status == 201
    assert created["identity_resolved"] is True
    assert created["institution_name"] == "Riverbend Institute of Technology"
    assert created["raw_institution_name"] == "Different name"


@pytest.mark.parametrize("actor_name", ["Dr. R. K. Sharma", "Rahul Mehta"])
def test_supervisor_and_wrong_bureau_cannot_create_and_denials_persist(api, actor_name):
    actor = api.user(actor_name)
    before = count(api, ActionLog)
    status, result = api.request("POST", "/cases", payload(), actor)
    assert status == 403 and result["detail"]
    assert count(api, Case) == 30
    assert count(api, ActionLog) == before + 1
    api.db.expire_all()
    entry = api.db.scalar(select(ActionLog).order_by(ActionLog.id.desc()))
    assert entry.event_type == "denied" and entry.actor_id == actor
    assert entry.case_id is None


@pytest.mark.parametrize("header", [None, "not-an-id", "99999999"])
def test_missing_invalid_and_unknown_demo_users_are_denied_and_logged(api, header):
    before = count(api, ActionLog)
    status, result = api.request("POST", "/cases", payload(), header)
    assert status == 403 and "X-User-Id" in result["detail"]
    assert count(api, ActionLog) == before + 1
    entry = api.db.scalar(select(ActionLog).order_by(ActionLog.id.desc()))
    assert entry.event_type == "denied" and entry.actor_id is None
    assert count(api, Case) == 30


@pytest.mark.parametrize("owner", ["Rahul Mehta", "Dr. R. K. Sharma"])
def test_invalid_owner_rejected_without_partial_case_or_log(api, owner):
    before = count(api, ActionLog)
    status, result = api.request("POST", "/cases", payload(officer_id=api.user(owner)), api.user("Anita Rao"))
    assert status == 422 and result["detail"]
    assert count(api, Case) == 30 and count(api, ActionLog) == before


def test_duplicate_case_code_returns_409_without_writes(api):
    before = count(api, ActionLog)
    status, result = api.request("POST", "/cases", payload(case_code="PGRC-101"), api.user("Anita Rao"))
    assert status == 409 and result["detail"]
    assert count(api, Case) == 30 and count(api, ActionLog) == before


def test_case_detail_has_chronological_history_and_supervisor_can_read(api):
    status, detail = api.request("GET", f"/cases/{case_id(api)}", user=api.user("Dr. R. K. Sharma"))
    assert status == 200 and detail["case_code"] == "PGRC-101"
    assert detail["officer"] == "Anita Rao"
    assert detail["history"][0]["event_type"] == "create"
    assert detail["history"] == sorted(detail["history"], key=lambda entry: (entry["at"], entry["id"]))


def test_action_and_document_reference_persist_in_history(api):
    identity = case_id(api)
    status, changed = api.request("POST", f"/cases/{identity}/actions", {
        "remarks": "Received synthetic reply", "doc_ref": "reply.pdf", "next_action": "Review reply",
        "expected_disposal_on": "2026-11-20",
    }, api.user("Anita Rao"))
    assert status == 200
    assert changed["last_action"] == "Received synthetic reply"
    assert changed["last_action_on"] == get_demo_today().isoformat()
    assert changed["next_action"] == "Review reply"
    assert changed["expected_disposal_on"] == "2026-11-20"
    _, reloaded = api.request("GET", f"/cases/{identity}")
    assert reloaded == changed
    entry = reloaded["history"][-1]
    assert entry["event_type"] == "update" and entry["doc_ref"] == "reply.pdf"
    assert entry["actor"] == "Anita Rao"


@pytest.mark.parametrize("actor_name", ["Dr. R. K. Sharma", "Anita Rao"])
def test_supervisor_and_pgrc_officer_cannot_write_rb_case(api, actor_name):
    identity = case_id(api, "RB-201")
    _, before = api.request("GET", f"/cases/{identity}")
    status, result = api.request("POST", f"/cases/{identity}/actions", {"remarks": "Forbidden action"}, api.user(actor_name))
    assert status == 403 and result["detail"]
    _, after = api.request("GET", f"/cases/{identity}")
    assert after["last_action"] == before["last_action"] and after["status"] == before["status"]
    assert len(after["history"]) == len(before["history"]) + 1
    assert after["history"][-1]["event_type"] == "denied"
    assert after["history"][-1]["actor"] == actor_name


def test_escalation_sets_status_and_logs_event(api):
    status, result = api.request("POST", f"/cases/{case_id(api)}/actions", {
        "event_type": "escalate", "remarks": "Senior review required",
    }, api.user("Anita Rao"))
    assert status == 200 and result["status"] == "escalated"
    assert result["history"][-1]["event_type"] == "escalate"


def test_transfer_changes_owner_and_enforces_new_bureau(api):
    identity = case_id(api)
    status, result = api.request("POST", f"/cases/{identity}/actions", {
        "event_type": "transfer", "remarks": "Transfer for RB review",
        "to_bureau": "RB", "officer_id": api.user("Rahul Mehta"),
    }, api.user("Anita Rao"))
    assert status == 200
    assert (result["status"], result["bureau"], result["officer"]) == ("transferred", "RB", "Rahul Mehta")
    assert result["history"][-1]["event_type"] == "transfer"
    assert result["history"][-1]["bureau"] == "PGRC"
    status, _ = api.request("POST", f"/cases/{identity}/actions", {"remarks": "Old bureau denied"}, api.user("Anita Rao"))
    assert status == 403
    status, result = api.request("POST", f"/cases/{identity}/actions", {"remarks": "RB received case"}, api.user("Rahul Mehta"))
    assert status == 200 and result["last_action"] == "RB received case"


@pytest.mark.parametrize("owner", ["Anita Rao", "Dr. R. K. Sharma"])
def test_transfer_rejects_wrong_bureau_or_supervisor_owner(api, owner):
    identity = case_id(api)
    before = count(api, ActionLog)
    status, _ = api.request("POST", f"/cases/{identity}/actions", {
        "event_type": "transfer", "remarks": "Invalid owner", "to_bureau": "RB", "officer_id": api.user(owner),
    }, api.user("Anita Rao"))
    assert status == 422
    assert count(api, ActionLog) == before
    assert api.db.get(Case, identity).bureau == "PGRC"


@pytest.mark.parametrize("changes", [
    {"remarks": "   "},
    {"doc_ref": "../reply.pdf"},
    {"doc_ref": "C:\\reply.pdf"},
    {"event_type": "transfer"},
    {"event_type": "escalate", "status": "disposed"},
    {"status": "transferred"},
    {"bureau": "RB"},
])
def test_invalid_action_input_is_rejected_without_writes(api, changes):
    identity = case_id(api)
    before = count(api, ActionLog)
    status, _ = api.request("POST", f"/cases/{identity}/actions", {"remarks": "Valid default", **changes}, api.user("Anita Rao"))
    assert status == 422
    assert count(api, ActionLog) == before
    assert api.db.get(Case, identity).status == "under_process"


def test_disposing_one_case_leaves_other_case_unchanged(api):
    rb_id = case_id(api, "RB-201")
    _, before = api.request("GET", f"/cases/{rb_id}")
    status, changed = api.request("POST", f"/cases/{case_id(api)}/actions", {
        "remarks": "Disposed independently", "status": "disposed",
    }, api.user("Anita Rao"))
    assert status == 200 and changed["status"] == "disposed"
    _, after = api.request("GET", f"/cases/{rb_id}")
    assert after == before and after["status"] == "pending"


def test_institution_profile_includes_bureaus_cases_and_histories(api):
    institution = api.db.scalar(select(Institution).where(Institution.aicte_id == "INST-0001"))
    status, profile = api.request("GET", f"/institutions/{institution.id}")
    assert status == 200 and profile["aicte_id"] == "INST-0001"
    assert profile["address"] == "12 Lake Road, Pune" and profile["region"] == "West"
    assert profile["bureaus_involved"] == ["PGRC", "RB"]
    assert {case["case_code"] for case in profile["cases"]} == {"PGRC-101", "PGRC-112", "RB-201", "RB-202", "RB-210"}
    assert all(case["history"] for case in profile["cases"])


@pytest.mark.parametrize("method,path,data", [
    ("GET", "/cases/2147483647", None),
    ("GET", "/institutions/2147483647", None),
    ("POST", "/cases/2147483647/actions", {"remarks": "Missing case"}),
])
def test_missing_resources_return_404(api, method, path, data):
    status, result = api.request(method, path, data, api.user("Anita Rao"))
    assert status == 404 and "not found" in result["detail"]


def test_created_case_and_actions_use_configured_demo_date(api, monkeypatch):
    monkeypatch.setenv("DEMO_TODAY", "2027-01-02")
    status, case = api.request("POST", "/cases", payload(), api.user("Anita Rao"))
    assert status == 201 and case["received_on"] == "2027-01-02"
    status, case = api.request("POST", f"/cases/{case['id']}/actions", {"remarks": "Configured date"}, api.user("Anita Rao"))
    assert status == 200 and case["last_action_on"] == "2027-01-02"


def test_same_bureau_officers_can_assign_and_update_colleagues_cases(api):
    status, created = api.request("POST", "/cases", payload(officer_id=api.user("Vikram Singh")), api.user("Anita Rao"))
    assert status == 201 and created["officer"] == "Vikram Singh"
    status, updated = api.request("POST", f"/cases/{created['id']}/actions", {"remarks": "Colleague in same bureau"}, api.user("Anita Rao"))
    assert status == 200 and updated["officer"] == "Vikram Singh"
    assert updated["history"][-1]["actor"] == "Anita Rao"


def test_rejected_foreign_bureau_attempt_does_not_add_involved_bureau(api):
    identity = case_id(api, "RB-206")
    case = api.db.get(Case, identity)
    status, _ = api.request("POST", f"/cases/{identity}/actions", {"remarks": "Denied PGRC attempt"}, api.user("Anita Rao"))
    assert status == 403
    status, profile = api.request("GET", f"/institutions/{case.institution_id}")
    assert status == 200
    # Denied attempts do not make the OTHER bureau involved in this institution.
    status, _ = api.request("POST", f"/cases/{identity}/actions", {"remarks": "Denied OTHER attempt"}, api.user("Sneha Iyer"))
    assert status == 403
    _, profile = api.request("GET", f"/institutions/{case.institution_id}")
    assert "OTHER" not in profile["bureaus_involved"]
