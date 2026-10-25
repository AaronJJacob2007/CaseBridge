"""Slice 3: author-run on constructed data; real PostgreSQL, rolled-back ASGI writes."""
import pytest
from sqlalchemy import func, select

from backend.models import ActionLog, Case, CaseLink, CoordinationRequest


def identity(api, code):
    return api.db.scalar(select(Case.id).where(Case.case_code == code))


def review(api, *, codes=("PGRC-101", "RB-201"), actor="Rahul Mehta", **changes):
    return api.request("POST", "/links", {
        "case_a": identity(api, codes[0]), "case_b": identity(api, codes[1]),
        "review_state": "confirmed", **changes,
    }, api.user(actor))


def check_body(link_id, **changes):
    return {"link_id": link_id, "action_type": "Document request",
            "doc_category": "Fee records", "period": "2025-26", **changes}


def post_check(api, link_id, **changes):
    return api.request("POST", "/coordination/check", check_body(link_id, **changes), api.user("Anita Rao"))


def requests_count(api):
    return api.db.scalar(select(func.count()).select_from(CoordinationRequest))


@pytest.fixture
def confirmed_link(api):
    status, link = review(api)
    assert status == 200 and link["review_state"] == "confirmed"
    return link


@pytest.fixture
def pending_request(api, confirmed_link):
    status, result = api.request("POST", "/coordination", {
        **check_body(confirmed_link["id"]), "to_bureau": "PGRC",
    }, api.user("Rahul Mehta"))
    assert status == 201 and result["outcome"] == "created"
    return result["request"]


def test_expected_outcomes_eight_step_walkthrough(api, confirmed_link, pending_request):
    link_id = confirmed_link["id"]
    request_id = pending_request["id"]
    assert pending_request["requester"] == "Rahul Mehta"
    assert pending_request["status"] == "requested"
    # Steps 1-2 are the link and request fixtures. Step 3 must warn, not insert.
    status, warning = post_check(api, link_id)
    assert status == 200 and warning["warning"] is True
    assert warning["existing_request"]["id"] == request_id
    assert warning["choices"] == ["coordinate", "proceed_separately"]
    status, repeated = api.request("POST", "/coordination", {
        **check_body(link_id), "to_bureau": "RB",
    }, api.user("Anita Rao"))
    assert status == 409 and repeated["existing_request"]["id"] == request_id
    assert requests_count(api) == 1
    # Steps 4 and 5 change one matching key at a time.
    assert post_check(api, link_id, period="2024-25")[1]["warning"] is False
    assert post_check(api, link_id, doc_category="Salary records")[1]["warning"] is False
    # Step 6 requires target bureau, owner and follow-up; step 7 still warns.
    status, acknowledged = api.request("POST", f"/coordination/{request_id}/ack", {
        "owner_id": api.user("Anita Rao"), "follow_up_on": "2026-10-30",
    }, api.user("Anita Rao"))
    assert status == 200 and acknowledged["status"] == "acknowledged"
    assert acknowledged["owner"] == "Anita Rao"
    assert acknowledged["follow_up_on"] == "2026-10-30" and acknowledged["acknowledged_at"]
    assert post_check(api, link_id)[1]["existing_request"]["status"] == "acknowledged"
    # Step 8: completion removes the warning without closing either case.
    status, completed = api.request("POST", f"/coordination/{request_id}/complete", {}, api.user("Anita Rao"))
    assert status == 200 and completed["status"] == "completed"
    assert post_check(api, link_id)[1] == {"warning": False, "existing_request": None, "choices": []}
    for code in ("PGRC-101", "RB-201"):
        _, detail = api.request("GET", f"/cases/{identity(api, code)}")
        assert detail["links"][0]["id"] == link_id
        assert detail["coordination_requests"][0]["status"] == "completed"
        events = [entry["event_type"] for entry in detail["history"]]
        assert "link_review" in events and "coord_request" in events and "coord_ack" in events
        assert any(entry["event_type"] == "update" and f"Request {request_id} completed" in entry["remarks"] for entry in detail["history"])
    assert api.db.get(Case, identity(api, "RB-201")).status == "pending"


def test_reverse_pair_updates_one_link_and_keeps_cases_independent(api, confirmed_link):
    status, link = review(api, codes=("RB-201", "PGRC-101"), actor="Anita Rao",
                          review_state="rejected", reason="Unrelated incidents")
    assert status == 200 and link["id"] == confirmed_link["id"]
    assert link["case_a"] < link["case_b"]
    assert link["reason"] == "Unrelated incidents" and link["reviewed_at"]
    assert link["reviewed_by"] == api.user("Anita Rao")
    assert api.db.scalar(select(func.count()).select_from(CaseLink)) == 1
    assert api.db.get(Case, identity(api, "PGRC-101")).status == "under_process"
    assert api.db.get(Case, identity(api, "RB-201")).status == "pending"


def test_rejecting_inst0003_link_does_not_remove_overlap_alert(api):
    status, link = review(api, codes=("PGRC-104", "RB-203"), actor="Anita Rao",
                          review_state="rejected", reason="Unrelated incidents")
    assert status == 200 and link["review_state"] == "rejected"
    assert link["reason"] == "Unrelated incidents"
    _, alerts = api.request("GET", "/overlaps")
    assert "INST-0003" in {alert["aicte_id"] for alert in alerts}


@pytest.mark.parametrize("reason", [None, "", "   "])
def test_rejection_requires_reason_without_creating_link(api, reason):
    status, _ = review(api, review_state="rejected", reason=reason)
    assert status == 422
    assert api.db.scalar(select(func.count()).select_from(CaseLink)) == 0


@pytest.mark.parametrize("codes", [("PGRC-109", "RB-206"), ("PGRC-101", "RB-203")])
def test_unresolved_or_different_institutions_cannot_be_linked(api, codes):
    status, _ = review(api, codes=codes, actor="Anita Rao")
    assert status == 422
    assert api.db.scalar(select(func.count()).select_from(CaseLink)) == 0


def test_same_case_or_same_bureau_overlap_link_rejected(api):
    assert review(api, codes=("PGRC-101", "PGRC-101"), actor="Anita Rao")[0] == 422
    assert review(api, codes=("PGRC-101", "PGRC-112"), actor="Anita Rao")[0] == 422
    status, link = review(api, codes=("PGRC-101", "PGRC-112"), actor="Anita Rao", type="related_incident")
    assert status == 200 and link["type"] == "related_incident"


@pytest.mark.parametrize("actor", ["Dr. R. K. Sharma", "Sneha Iyer"])
def test_only_involved_bureau_officers_can_review_links(api, actor):
    before = api.db.scalar(select(func.count()).select_from(ActionLog))
    status, _ = review(api, actor=actor)
    assert status == 403
    assert api.db.scalar(select(func.count()).select_from(CaseLink)) == 0
    assert api.db.scalar(select(func.count()).select_from(ActionLog)) == before + 1
    entry = api.db.scalar(select(ActionLog).order_by(ActionLog.id.desc()))
    assert entry.event_type == "denied" and entry.actor_id == api.user(actor)


def test_coordinate_choice_reuses_request_and_is_audited(api, confirmed_link, pending_request):
    status, result = api.request("POST", "/coordination", {
        **check_body(confirmed_link["id"]), "to_bureau": "RB", "decision": "coordinate",
    }, api.user("Anita Rao"))
    assert status == 200 and result["outcome"] == "coordinated"
    assert result["request"]["id"] == pending_request["id"] and requests_count(api) == 1
    assert api.db.scalar(select(ActionLog.id).where(ActionLog.remarks.contains("Coordinate with existing request"))) is not None


@pytest.mark.parametrize("reason", [None, "", "   "])
def test_proceed_separately_requires_reason(api, confirmed_link, pending_request, reason):
    status, _ = api.request("POST", "/coordination", {
        **check_body(confirmed_link["id"]), "to_bureau": "RB", "decision": "proceed_separately", "proceed_reason": reason,
    }, api.user("Anita Rao"))
    assert status == 422 and requests_count(api) == 1


def test_proceed_separately_stores_reason_and_leaves_original_unchanged(api, confirmed_link, pending_request):
    status, result = api.request("POST", "/coordination", {
        **check_body(confirmed_link["id"]), "to_bureau": "RB", "decision": "proceed_separately",
        "proceed_reason": "Separate statutory deadline",
    }, api.user("Anita Rao"))
    assert status == 201 and requests_count(api) == 2
    assert result["request"]["proceed_reason"] == "Separate statutory deadline"
    assert result["request"]["id"] != pending_request["id"]
    assert api.db.get(CoordinationRequest, pending_request["id"]).status == "requested"
    assert post_check(api, confirmed_link["id"])[1]["existing_request"]["id"] == pending_request["id"]


@pytest.mark.parametrize("state,warning", [
    ("requested", True), ("acknowledged", True), ("in_progress", True),
    ("completed", False), ("declined", False),
])
def test_only_pending_statuses_warn(api, confirmed_link, pending_request, state, warning):
    request = api.db.get(CoordinationRequest, pending_request["id"])
    request.status = state
    api.db.commit()
    status, result = post_check(api, confirmed_link["id"])
    assert status == 200 and result["warning"] is warning
    assert (result["existing_request"] is not None) is warning


def test_different_period_and_document_category_can_be_saved_without_warning(api, confirmed_link, pending_request):
    for changes in ({"period": "2024-25"}, {"doc_category": "Salary records"}):
        status, result = api.request("POST", "/coordination", {
            **check_body(confirmed_link["id"], **changes), "to_bureau": "RB",
        }, api.user("Anita Rao"))
        assert status == 201 and result["outcome"] == "created"
    assert requests_count(api) == 3


@pytest.mark.parametrize("doc,period", [(None, None), (None, "2025-26"), ("Fee records", None)])
def test_optional_matching_fields_are_null_safe(api, confirmed_link, pending_request, doc, period):
    request = api.db.get(CoordinationRequest, pending_request["id"])
    request.doc_category, request.period = doc, period
    api.db.commit()
    status, result = post_check(api, confirmed_link["id"], doc_category=doc, period=period)
    assert status == 200 and result["warning"] is True
    assert result["existing_request"]["id"] == pending_request["id"]
    assert post_check(api, confirmed_link["id"], doc_category="Another category", period=period)[1]["warning"] is False


def test_another_confirmed_link_at_same_institution_cannot_bypass_warning(api, pending_request):
    status, other_link = review(api, codes=("PGRC-101", "RB-210"), actor="Anita Rao")
    assert status == 200
    status, warning = post_check(api, other_link["id"])
    assert status == 200 and warning["existing_request"]["id"] == pending_request["id"]


def test_same_action_at_different_institution_does_not_warn(api, pending_request):
    status, other_link = review(api, codes=("PGRC-104", "RB-203"), actor="Anita Rao")
    assert status == 200
    assert post_check(api, other_link["id"])[1]["warning"] is False


@pytest.mark.parametrize("state", ["rejected", "suggested"])
def test_requests_require_currently_confirmed_link(api, confirmed_link, state):
    link = api.db.get(CaseLink, confirmed_link["id"])
    link.review_state = state
    api.db.commit()
    assert post_check(api, link.id)[0] == 409
    status, _ = api.request("POST", "/coordination", {**check_body(link.id), "to_bureau": "RB"}, api.user("Anita Rao"))
    assert status == 409 and requests_count(api) == 0


@pytest.mark.parametrize("path_kind", ["check", "create", "ack", "complete"])
@pytest.mark.parametrize("actor", ["Dr. R. K. Sharma", "Sneha Iyer"])
def test_supervisor_and_uninvolved_bureau_cannot_coordinate(api, confirmed_link, pending_request, path_kind, actor):
    body = check_body(confirmed_link["id"])
    path = "/coordination/check"
    if path_kind == "create":
        path, body = "/coordination", {**body, "to_bureau": "PGRC"}
    elif path_kind == "ack":
        path, body = f"/coordination/{pending_request['id']}/ack", {"owner_id": api.user("Anita Rao"), "follow_up_on": "2026-10-30"}
    elif path_kind == "complete":
        path, body = f"/coordination/{pending_request['id']}/complete", {}
    before = api.db.scalar(select(func.count()).select_from(ActionLog))
    status, _ = api.request("POST", path, body, api.user(actor))
    assert status == 403 and requests_count(api) == 1
    assert api.db.get(CoordinationRequest, pending_request["id"]).status == "requested"
    assert api.db.scalar(select(func.count()).select_from(ActionLog)) == before + 1


def test_only_target_bureau_can_acknowledge_or_complete(api, pending_request):
    request_id = pending_request["id"]
    for suffix, body in (("ack", {"owner_id": api.user("Anita Rao"), "follow_up_on": "2026-10-30"}), ("complete", {})):
        status, _ = api.request("POST", f"/coordination/{request_id}/{suffix}", body, api.user("Rahul Mehta"))
        assert status == 403
    assert api.db.get(CoordinationRequest, request_id).status == "requested"


@pytest.mark.parametrize("owner", ["Rahul Mehta", "Dr. R. K. Sharma"])
def test_ack_owner_must_be_target_bureau_officer(api, pending_request, owner):
    status, _ = api.request("POST", f"/coordination/{pending_request['id']}/ack", {
        "owner_id": api.user(owner), "follow_up_on": "2026-10-30",
    }, api.user("Anita Rao"))
    assert status == 422 and api.db.get(CoordinationRequest, pending_request["id"]).status == "requested"


def test_ack_requires_owner_and_followup_and_cannot_repeat(api, pending_request):
    path = f"/coordination/{pending_request['id']}/ack"
    assert api.request("POST", path, {}, api.user("Anita Rao"))[0] == 422
    body = {"owner_id": api.user("Anita Rao"), "follow_up_on": "2026-10-30"}
    assert api.request("POST", path, body, api.user("Anita Rao"))[0] == 200
    assert api.request("POST", path, body, api.user("Anita Rao"))[0] == 409


def test_complete_cannot_repeat_and_stale_coordinate_choice_does_not_create(api, confirmed_link, pending_request):
    assert api.request("POST", f"/coordination/{pending_request['id']}/ack", {
        "owner_id": api.user("Anita Rao"), "follow_up_on": "2026-10-30",
    }, api.user("Anita Rao"))[0] == 200
    path = f"/coordination/{pending_request['id']}/complete"
    assert api.request("POST", path, {}, api.user("Anita Rao"))[0] == 200
    assert api.request("POST", path, {}, api.user("Anita Rao"))[0] == 409
    status, _ = api.request("POST", "/coordination", {
        **check_body(confirmed_link["id"]), "to_bureau": "RB", "decision": "coordinate",
    }, api.user("Anita Rao"))
    assert status == 409 and requests_count(api) == 1


def test_target_must_be_other_linked_bureau(api, confirmed_link):
    for target in ("RB", "OTHER"):
        status, _ = api.request("POST", "/coordination", {
            **check_body(confirmed_link["id"]), "to_bureau": target,
        }, api.user("Rahul Mehta"))
        assert status == 422
    assert requests_count(api) == 0


def test_rejected_existing_link_stops_warning_but_does_not_auto_close_request(api, confirmed_link, pending_request):
    status, other_link = review(api, codes=("PGRC-101", "RB-210"))
    assert status == 200
    assert api.request("POST", f"/coordination/{pending_request['id']}/ack", {
        "owner_id": api.user("Anita Rao"), "follow_up_on": "2026-10-30",
    }, api.user("Anita Rao"))[0] == 200
    assert review(api, review_state="rejected", reason="Unrelated incidents")[0] == 200
    assert post_check(api, other_link["id"])[1]["warning"] is False
    assert api.db.get(CoordinationRequest, pending_request["id"]).status == "acknowledged"
    status, result = api.request("POST", f"/coordination/{pending_request['id']}/complete", {}, api.user("Anita Rao"))
    assert status == 200 and result["status"] == "completed"


def test_disposing_one_confirmed_case_leaves_linked_case_unchanged(api, confirmed_link):
    _, before = api.request("GET", f"/cases/{identity(api, 'RB-201')}")
    status, result = api.request("POST", f"/cases/{identity(api, 'PGRC-101')}/actions", {
        "remarks": "Disposed independently", "status": "disposed",
    }, api.user("Anita Rao"))
    assert status == 200 and result["status"] == "disposed"
    _, after = api.request("GET", f"/cases/{identity(api, 'RB-201')}")
    assert after == before and after["status"] == "pending"


@pytest.mark.parametrize("path,body", [
    ("/links", {"case_a": 2147483646, "case_b": 2147483647, "review_state": "confirmed"}),
    ("/coordination/check", {"link_id": 2147483647, "action_type": "Document request"}),
    ("/coordination/2147483647/ack", {"owner_id": 1, "follow_up_on": "2026-10-30"}),
    ("/coordination/2147483647/complete", {}),
])
def test_missing_links_cases_and_requests_return_404(api, path, body):
    status, result = api.request("POST", path, body, api.user("Anita Rao"))
    assert status == 404 and result["detail"]


def test_save_rechecks_after_a_stale_clear_precheck(api, confirmed_link):
    assert post_check(api, confirmed_link["id"])[1]["warning"] is False
    status, first = api.request("POST", "/coordination", {
        **check_body(confirmed_link["id"]), "to_bureau": "PGRC",
    }, api.user("Rahul Mehta"))
    assert status == 201
    status, result = api.request("POST", "/coordination", {
        **check_body(confirmed_link["id"]), "to_bureau": "RB",
    }, api.user("Anita Rao"))
    assert status == 409 and result["existing_request"]["id"] == first["request"]["id"]
    assert requests_count(api) == 1


def test_different_action_type_does_not_warn(api, confirmed_link, pending_request):
    status, result = post_check(api, confirmed_link["id"], action_type="Inspection")
    assert status == 200 and result["warning"] is False
