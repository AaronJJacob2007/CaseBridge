"""Production frontend payloads and submission flow against real rollback PostgreSQL."""
import json
from pathlib import Path
import subprocess

from sqlalchemy import func, select
from backend.models import ActionLog, CoordinationRequest
from backend.tests.test_slice3 import identity

ROOT = Path(__file__).resolve().parents[2]
MODULE = (ROOT / "frontend/src/coordinationTools.js").as_uri()


def body(function, *args):
    driver = (
        "const m=await import(" + json.dumps(MODULE) + ");"
        "let s='';for await(const c of process.stdin)s+=c;"
        "process.stdout.write(JSON.stringify(m[process.argv[1]](...JSON.parse(s))));"
    )
    result = subprocess.run(["node", "--input-type=module", "-e", driver, function],
                            input=json.dumps(args), capture_output=True, encoding="utf-8",
                            timeout=15, cwd=ROOT)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def flow(api, payload, actor, before_save=None):
    # Line protocol bridges JS API calls to the actual ASGI/PostgreSQL fixture.
    # No fake responses; route commits are inside the fixture's outer rollback.
    driver = (
        "setTimeout(()=>process.exit(2),15000).unref();import {createInterface} from 'node:readline';"
        "const lines=createInterface({input:process.stdin})[Symbol.asyncIterator]();"
        "const m=await import(" + json.dumps(MODULE) + ");"
        "const api=async(path,options)=>{console.log(JSON.stringify({path,...options}));"
        "const r=JSON.parse((await lines.next()).value);"
        "if(r.status>=400){const e=new Error(r.data.detail||'Request blocked');"
        "e.status=r.status;e.data=r.data;throw e;}return r.data;};"
        "const result=await m.submitCoordination(api,JSON.parse(process.argv[1]));"
        "console.log(JSON.stringify({result}));process.exit(0);"
    )
    process = subprocess.Popen(["node", "--input-type=module", "-e", driver, json.dumps(payload)],
                               stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               text=True, encoding="utf-8", cwd=ROOT)
    calls = []
    try:
        for line in process.stdout:
            message = json.loads(line)
            if "result" in message:
                assert process.wait(timeout=15) == 0
                return message["result"], calls
            calls.append(message["path"])
            if message["path"] == "/coordination" and before_save is not None:
                before_save()
            status, data = api.request(message["method"], message["path"], message["body"], api.user(actor))
            process.stdin.write(json.dumps({"status": status, "data": data}) + "\n")
            process.stdin.flush()
        raise AssertionError(process.stderr.read())
    finally:
        if process.poll() is None:
            process.kill()
        process.communicate(timeout=15)


def link(api, codes=("PGRC-101", "RB-201"), state="confirmed", reason=""):
    payload = body("buildLinkReview", identity(api, codes[0]), identity(api, codes[1]), state, reason)
    status, saved = api.request("POST", "/links", payload, api.user("Rahul Mehta"))
    assert status == 200
    return saved


def draft(link_id, target="PGRC", **changes):
    return body("buildCoordination", link_id, {
        "action_type": "Document request", "doc_category": "Fee records", "period": "2025-26",
        "to_bureau": target, **changes,
    })


def test_production_flow_eight_step_walkthrough_and_reload(api):
    saved = link(api)
    created, calls = flow(api, draft(saved["id"]), "Rahul Mehta")
    assert calls == ["/coordination/check", "/coordination"]
    assert created["outcome"] == "created"
    request = created["request"]
    payload = draft(saved["id"], "RB")
    warned, calls = flow(api, payload, "Anita Rao")
    assert calls == ["/coordination/check"] and warned["outcome"] == "warning"
    assert warned["existing_request"]["id"] == request["id"]
    for changes in ({"period": "2024-25"}, {"doc_category": "Salary records"}):
        check = draft(saved["id"], "RB", **changes)
        check.pop("to_bureau")
        check.pop("follow_up_on")
        status, result = api.request("POST", "/coordination/check", check, api.user("Anita Rao"))
        assert status == 200 and result["warning"] is False
    status, acknowledged = api.request("POST", f"/coordination/{request['id']}/ack",
        body("buildAcknowledgment", str(api.user("Anita Rao")), "2026-10-30"), api.user("Anita Rao"))
    assert status == 200 and acknowledged["owner"] == "Anita Rao" and acknowledged["status"] == "acknowledged"
    warned, calls = flow(api, payload, "Anita Rao")
    assert warned["existing_request"]["status"] == "acknowledged"
    status, completed = api.request("POST", f"/coordination/{request['id']}/complete",
        {"remarks": "Synthetic records coordinated"}, api.user("Anita Rao"))
    assert status == 200 and completed["status"] == "completed"
    check = {key: payload[key] for key in ("link_id", "action_type", "doc_category", "period")}
    assert api.request("POST", "/coordination/check", check, api.user("Anita Rao"))[1]["warning"] is False
    for code in ("PGRC-101", "RB-201"):
        _, reloaded = api.request("GET", f"/cases/{identity(api, code)}")
        assert reloaded["links"][0]["id"] == saved["id"]
        assert reloaded["coordination_requests"][0]["status"] == "completed"
        assert {"link_review", "coord_request", "coord_ack"} <= {row["event_type"] for row in reloaded["history"]}


def test_production_coordinate_rechecks_and_reuses_existing_request(api):
    saved = link(api)
    original, _ = flow(api, draft(saved["id"]), "Rahul Mehta")
    payload = draft(saved["id"], "RB")
    payload["decision"] = "coordinate"
    coordinated, calls = flow(api, payload, "Anita Rao")
    assert calls == ["/coordination/check", "/coordination"]
    assert coordinated["outcome"] == "coordinated"
    assert coordinated["request"]["id"] == original["request"]["id"]
    assert api.db.scalar(select(func.count()).select_from(CoordinationRequest)) == 1


def test_production_proceed_separately_keeps_reason_and_original(api):
    saved = link(api)
    original, _ = flow(api, draft(saved["id"]), "Rahul Mehta")
    payload = body("buildCoordination", saved["id"], {
        "action_type": "Document request", "doc_category": "Fee records", "period": "2025-26",
        "to_bureau": "RB", "proceed_reason": "Different supporting documents required",
    }, "proceed_separately")
    separate, _ = flow(api, payload, "Anita Rao")
    assert separate["request"]["id"] != original["request"]["id"]
    assert separate["request"]["proceed_reason"] == "Different supporting documents required"
    assert api.db.get(CoordinationRequest, original["request"]["id"]).status == "requested"


def test_production_rejection_keeps_institution_alert(api):
    saved = link(api, ("PGRC-104", "RB-203"), "rejected", "Unrelated incidents")
    _, reloaded = api.request("GET", f"/cases/{identity(api, 'PGRC-104')}")
    assert next(row for row in reloaded["links"] if row["id"] == saved["id"])["reason"] == "Unrelated incidents"
    _, groups = api.request("GET", "/overlaps")
    assert "INST-0003" in {row["aicte_id"] for row in groups}


def test_production_supervisor_payload_denied_and_audited(api):
    payload = body("buildLinkReview", identity(api, "PGRC-101"), identity(api, "RB-201"), "confirmed")
    before = api.db.scalar(select(func.count()).select_from(ActionLog).where(ActionLog.event_type == "denied"))
    status, result = api.request("POST", "/links", payload, api.user("Dr. R. K. Sharma"))
    assert status == 403 and result["detail"] == "Supervisors are read-only"
    after = api.db.scalar(select(func.count()).select_from(ActionLog).where(ActionLog.event_type == "denied"))
    assert after == before + 1


def test_production_flow_surfaces_real_race_warning_instead_of_hiding_409(api):
    saved = link(api)
    payload = draft(saved["id"])
    def competing_save():
        status, result = api.request("POST", "/coordination", payload, api.user("Rahul Mehta"))
        assert status == 201 and result["outcome"] == "created"
    result, calls = flow(api, payload, "Rahul Mehta", before_save=competing_save)
    assert calls == ["/coordination/check", "/coordination"]
    assert result["outcome"] == "warning" and result["existing_request"]["status"] == "requested"
    assert api.db.scalar(select(func.count()).select_from(CoordinationRequest)) == 1
