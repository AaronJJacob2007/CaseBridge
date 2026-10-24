"""Frontend form payloads are exercised against real FastAPI/PostgreSQL.

Node executes production payload builders; API commits stay inside the existing
SAVEPOINT fixture. No live demo case/action is left behind by these tests.
"""
import json
from pathlib import Path
import subprocess

import pytest

from backend.config import get_demo_today

ROOT = Path(__file__).resolve().parents[2]
MODULE = (ROOT / "frontend" / "src" / "caseTools.js").as_uri()


def frontend_body(function, *args):
    driver = (
        "const builders = await import(" + json.dumps(MODULE) + ");"
        "let input=''; for await (const chunk of process.stdin) input+=chunk;"
        "const args=JSON.parse(input);"
        "process.stdout.write(JSON.stringify(builders[process.argv[1]](...args)));"
    )
    result = subprocess.run(
        ["node", "--input-type=module", "-e", driver, function], input=json.dumps(args),
        capture_output=True, encoding="utf-8", timeout=15, cwd=ROOT,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def actor(api, name="Anita Rao"):
    status, user = api.request("GET", "/demo/me", user=api.user(name))
    assert status == 200
    return user


@pytest.mark.parametrize("aicte_id,resolved", [("INST-0001", True), ("", False)])
def test_case_entry_payload_saves_and_reloads_without_losing_raw_identity(api, aicte_id, resolved):
    user = actor(api)
    body = frontend_body("buildCaseCreate", {
        "case_code": "SLICE6-FORM", "institution_name": "Synthetic reported name",
        "aicte_id": aicte_id, "raw_region": "Central", "remarks": "Registered through form payload",
        "officer_id": str(user["id"]), "received_on": "", "category": "Fee collection",
        "next_action": "Review synthetic case", "expected_disposal_on": "2026-11-30",
    }, user)
    assert "received_on" not in body
    status, saved = api.request("POST", "/cases", body, user["id"])
    assert status == 201 and saved["identity_resolved"] is resolved
    assert saved["raw_institution_name"] == "Synthetic reported name"
    assert saved["received_on"] == get_demo_today().isoformat()
    assert saved["raw_region"] == "Central"
    assert saved["region"] == ("West" if resolved else "Central")
    status, reloaded = api.request("GET", f"/cases/{saved['id']}")
    assert status == 200 and reloaded == saved
    assert reloaded["history"][-1]["remarks"] == "Registered through form payload"


def test_action_form_payload_persists_document_and_next_step_in_history(api):
    user = actor(api)
    _, records = api.request("GET", "/cases")
    case = next(row for row in records if row["case_code"] == "PGRC-101")
    body = frontend_body("buildCaseAction", {
        "event_type": "update", "remarks": "Slice 6 persisted note", "doc_ref": "slice6-note.pdf",
        "status": "", "next_action": "Review response", "expected_disposal_on": case["expected_disposal_on"],
        "to_bureau": "RB", "officer_id": str(api.user("Rahul Mehta")),
    })
    assert "status" not in body and "to_bureau" not in body and "officer_id" not in body
    status, updated = api.request("POST", f"/cases/{case['id']}/actions", body, user["id"])
    assert status == 200 and updated["status"] == case["status"]
    _, reloaded = api.request("GET", f"/cases/{case['id']}")
    assert reloaded["last_action"] == "Slice 6 persisted note"
    assert reloaded["next_action"] == "Review response"
    entry = reloaded["history"][-1]
    assert entry["remarks"] == "Slice 6 persisted note" and entry["doc_ref"] == "slice6-note.pdf"
    assert entry["actor_id"] == user["id"]


def test_transfer_form_payload_updates_only_target_case_ownership(api):
    user = actor(api)
    _, records = api.request("GET", "/cases")
    case = next(row for row in records if row["case_code"] == "PGRC-101")
    other = next(row for row in records if row["case_code"] == "RB-201")
    _, before = api.request("GET", f"/cases/{other['id']}")
    body = frontend_body("buildCaseAction", {
        "event_type": "transfer", "remarks": "Transfer via form", "status": "disposed",
        "to_bureau": "RB", "officer_id": str(api.user("Rahul Mehta")),
        "next_action": "RB review", "expected_disposal_on": case["expected_disposal_on"],
    })
    assert "status" not in body
    status, updated = api.request("POST", f"/cases/{case['id']}/actions", body, user["id"])
    assert status == 200 and updated["status"] == "transferred"
    assert updated["bureau"] == "RB" and updated["officer_id"] == api.user("Rahul Mehta")
    _, after = api.request("GET", f"/cases/{other['id']}")
    assert after == before


def test_form_does_not_trim_aicte_id_into_a_registered_identity(api):
    user = actor(api)
    body = frontend_body("buildCaseCreate", {
        "case_code": "SLICE6-EXACT-ID", "institution_name": "Riverbend Institute of Technology",
        "aicte_id": " INST-0001 ", "remarks": "Exact ID check", "raw_region": "Central",
    }, user)
    assert body["aicte_id"] == " INST-0001 "
    status, case = api.request("POST", "/cases", body, user["id"])
    assert status == 201 and case["identity_resolved"] is False and case["institution_id"] is None
