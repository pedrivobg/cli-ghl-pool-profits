#!/usr/bin/env python3
"""Stay Fresh: follow-ups stop when the card moves on (Frank, 27/10; Pedro OK 28/10).

    ./.venv/bin/python scripts/sf_stop_followups.py plan
    ./.venv/bin/python scripts/sf_stop_followups.py test --to pedro@poolprofits.com
    ./.venv/bin/python scripts/sf_stop_followups.py apply

Quote Sent, No Response and No-Show kept running after the card went to Won/Scheduled/…, and at the end moved the card
to ❌ Lost (status lost): a won customer got quote texts and turned Lost days later. Missed New Lead too (its SMS 2 adds
`follow-up` → No Response). Fix:
- new "Stage Changed -> Stop Follow-ups": card enters Scheduled, In Communication, the 3 Won, Recurring, Not Qualified,
  Lost or Spam → remove from the 4 follow-ups + remove tags `follow-up`, `no-show` (so a later follow-up can start again);
- first step of Quote Sent / No Response / No-Show: remove from the other follow-ups (No-Show's existing step gets them).
A follow-up's own move to In Communication (on reply) or to Lost fires the stop flow too, which only ends what is
already ending. Re-entry, waits and texts unchanged. GET + backup before every PUT.
test: copy of Quote Sent with 1-minute waits + copy of the stop flow pointing at it; contact A's card moves to Scheduled
right after entering (must stay in Scheduled), contact B is left alone (control: ends in Lost); everything deleted.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import uuid

from _common import ROOT, load_dotenv
from pp_lead_alerts import retarget
from pp_review_fix import read
from pp_source_tags import fresh_ids, refs_ok

from cli_anything.gohighlevel.utils.agency import BACKEND, SERVICES, Agency

LOC = "DdTE6mF11dqgoI5Cv7XN"
PIPELINE = "5lyzLFECNQGtANjpnKc6"
FOLLOW = ["Missed New Lead - Initial SMS Follow-up", "No Response Follow-up", "Quote Sent Follow-up", "No-Show Follow-up"]
OTHERS = {"Quote Sent Follow-up": ["Missed New Lead - Initial SMS Follow-up", "No Response Follow-up", "No-Show Follow-up"],
          "No Response Follow-up": ["Quote Sent Follow-up", "No-Show Follow-up"],
          "No-Show Follow-up": ["Missed New Lead - Initial SMS Follow-up", "No Response Follow-up", "Quote Sent Follow-up"]}
STOP_STAGES = ["📅 Scheduled", "💬 In Communication", "🏆 Won - Weekly Pool Service", "🏆 Won - One Time Repair or Install",
               "🏆 Won - Pool Construction or Remodeling", "🔄 Recurring Customer", "❄ Not Qualified Stage", "❌ Lost", "🚫 Spam"]
FLOW = "Stage Changed -> Stop Follow-ups"
BDIR = ROOT / "backup" / "stay-fresh-pools"


def remove_step(wids: list[str]) -> dict:
    return {"id": str(uuid.uuid4()), "order": 0, "name": "Stop other follow-ups", "type": "remove_from_workflow",
            "attributes": {"type": "remove_from_workflow", "workflow_id": wids}}


def stop_steps(wids: list[str]) -> list[dict]:
    rm = remove_step(wids)
    rm["name"] = "Stop follow-ups"
    tag = {"id": str(uuid.uuid4()), "order": 1, "name": "Remove follow-up tags", "type": "remove_contact_tag",
           "parentKey": rm["id"], "attributes": {"type": "remove_contact_tag", "tags": ["follow-up", "no-show"]}}
    rm["next"] = tag["id"]
    return [rm, tag]


def prepend(tpl: list[dict], wids: list[str]) -> list[dict] | None:
    out = json.loads(json.dumps(tpl))
    root = next(s for s in out if not s.get("parentKey") and not s.get("parent"))
    if root["type"] == "remove_from_workflow":
        have = root["attributes"]["workflow_id"]
        if set(wids) <= set(have):
            return None
        root["attributes"]["workflow_id"] = have + [w for w in wids if w not in have]
        root["name"] = "Stop other follow-ups"
        return out
    st = remove_step(wids)
    st["next"] = root["id"]
    root["parentKey"] = st["id"]
    for s in out:
        s["order"] = s.get("order", 0) + 1
    return [st, *out]


def put(a: Agency, wid: str, live: dict, tpl: list[dict], status: str | None = None) -> dict:
    BDIR.mkdir(parents=True, exist_ok=True)
    (BDIR / f"workflow-{wid}-{time.strftime('%Y%m%d-%H%M%S')}.json").write_text(json.dumps(live))
    a.call("PUT", BACKEND, f"/workflow/{LOC}/{wid}", body={"name": live["name"], "version": live.get("version", 1),
                                                         "status": status or live["status"], "parentId": live.get("parentId"),
                                                         "workflowData": {"templates": tpl}})
    time.sleep(2)
    return read(a, LOC, wid)


def create_flow(a: Agency, name: str, tpl: list[dict], stages: list[str], parent: str | None) -> str:
    res = a.call("POST", BACKEND, f"/workflow/{LOC}", body={"name": name, "parentId": parent, "status": "draft"})
    wid = res.get("id") or res.get("_id")
    body = {"name": name, "version": 1, "status": "draft", "parentId": parent, "allowMultiple": True,
            "workflowData": {"templates": tpl}}
    a.call("PUT", BACKEND, f"/workflow/{LOC}/{wid}", body=body)
    for sid in stages:
        trig = {"type": "pipeline_stage_updated", "name": "Pipeline Stage Changed", "masterType": "highlevel",
                "schedule_config": {}, "workflowId": wid, "workflow_id": wid, "location_id": LOC,
                "actions": [{"workflow_id": wid, "type": "add_to_workflow"}], "targetActionId": tpl[0]["id"],
                "conditions": [{"operator": "==", "field": "opportunity.pipelineId", "value": PIPELINE, "title": "In pipeline", "type": "select"},
                               {"operator": "==", "field": "opportunity.pipelineStageId", "value": sid, "title": "Pipeline stage", "type": "select"}]}
        t = a.call("POST", BACKEND, f"/workflow/{LOC}/trigger", body=trig)
        a.call("PUT", BACKEND, f"/workflow/{LOC}/trigger/{t['id']}", body={**trig, "id": t["id"]})
    live = a.workflow(LOC, wid)
    a.call("PUT", BACKEND, f"/workflow/{LOC}/{wid}", body={**body, "status": "published", "version": live.get("version", 1),
                                                         "workflowData": {"templates": live["workflowData"]["templates"]}})
    return wid


def drop_flow(a: Agency, wid: str) -> None:
    live = a.workflow(LOC, wid)
    a.call("PUT", BACKEND, f"/workflow/{LOC}/{wid}", body={"name": live["name"], "version": live.get("version", 1), "status": "draft",
                                                         "workflowData": {"templates": live["workflowData"]["templates"]}})
    a.call("DELETE", BACKEND, f"/workflow/{LOC}/{wid}")


def test(a: Agency, flows: dict, stages: dict, to: str) -> int:
    q = read(a, LOC, flows["Quote Sent Follow-up"])
    tpl = fresh_ids(q["workflowData"]["templates"])
    for s in tpl:
        if s["type"] == "wait":
            s["attributes"]["startAfter"] = {"type": "minutes", "value": 1, "when": "after"}
    # the SMS steps stay (the reply waits must point at one); the test contacts have no phone, so nothing is texted
    made, wids = {}, []
    try:
        tq = create_flow(a, "ZZ TEST quote copy", tpl, [], q.get("parentId"))
        wids.append(tq)
        wids.append(create_flow(a, "ZZ TEST stop copy", stop_steps([tq]), [stages[s] for s in STOP_STAGES], q.get("parentId")))
        time.sleep(5)
        stamp = int(time.time())
        for case in ("moved", "control"):
            cid = a.call("POST", SERVICES, "/contacts/", body={"locationId": LOC, "firstName": "ZZ Test", "lastName": f"stop {case}",
                                                               "email": to.replace("@", f"+sf-stop-{case}-{stamp}@")})["contact"]["id"]
            o = a.call("POST", SERVICES, "/opportunities/", body={"locationId": LOC, "pipelineId": PIPELINE, "contactId": cid,
                                                                  "pipelineStageId": stages["🆕 New Lead"], "name": f"ZZ Test stop {case}",
                                                                  "status": "open"})
            made[case] = (cid, (o.get("opportunity") or o)["id"])
        time.sleep(5)
        for cid, _ in made.values():
            a.call("POST", SERVICES, f"/contacts/{cid}/workflow/{tq}", body={})
        time.sleep(20)
        a.call("PUT", SERVICES, f"/opportunities/{made['moved'][1]}", body={"pipelineId": PIPELINE, "pipelineStageId": stages["📅 Scheduled"]})
        time.sleep(420)  # 1 + 1 + 1 min waits, with slack
        names = {v: k for k, v in stages.items()}
        bad = 0
        for case, (cid, oid) in made.items():
            o = a.call("GET", SERVICES, f"/opportunities/{oid}")["opportunity"]
            tags = a.call("GET", SERVICES, f"/contacts/{cid}")["contact"].get("tags") or []
            got = (names.get(o["pipelineStageId"]), o["status"])
            want = ("📅 Scheduled", "open") if case == "moved" else ("❌ Lost", "lost")
            ok = got[0] == want[0]
            bad += not ok
            print(f"   {'✓' if ok else '✗'} {case}: {got} · tags {sorted(tags)}")
        return 1 if bad else 0
    finally:
        for cid, oid in made.values():
            for call in (("DELETE", f"/opportunities/{oid}"), ("DELETE", f"/contacts/{cid}")):
                try:
                    a.call(call[0], SERVICES, call[1])
                except Exception:  # noqa: BLE001
                    pass
        for wid in wids:
            drop_flow(a, wid)
        print("   limpo.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("mode", choices=["plan", "test", "apply"])
    parser.add_argument("--to")
    args = parser.parse_args()
    load_dotenv()
    a = Agency()
    if not a.location(LOC)["name"].startswith("Stay Fresh"):
        sys.exit("sub-conta errada")
    flows = {w["name"]: w["id"] for w in a.workflows(LOC)}
    stages = {s["name"]: s["id"] for s in next(p for p in a.pipelines(LOC) if p["id"] == PIPELINE)["stages"]}
    if args.mode == "test":
        if not args.to:
            parser.error("--to is required in test mode")
        return test(a, flows, stages, args.to)
    apply = args.mode == "apply"
    print(f"   {FLOW}: {'existe' if FLOW in flows else 'cria (' + str(len(STOP_STAGES)) + ' etapas)'}")
    if apply and FLOW not in flows:
        parent = a.workflow(LOC, flows["Quote Sent Follow-up"]).get("parentId")
        wid = create_flow(a, FLOW, stop_steps([flows[n] for n in FOLLOW]), [stages[s] for s in STOP_STAGES], parent)
        time.sleep(3)
        trs = [t for t in a.triggers(LOC, wid) if not t.get("deleted")]
        print(f"      {'✓' if a.workflow(LOC, wid)['status'] == 'published' and len(trs) == len(STOP_STAGES) and all(t.get('active') for t in trs) else '✗ VERIFICAR'}"
              f" publicado, {len(trs)} gatilhos")
    for name, others in OTHERS.items():
        live = read(a, LOC, flows[name])
        tpl = prepend(live["workflowData"]["templates"], [flows[n] for n in others])
        print(f"   {name}: {'+ tira de ' + ', '.join(others) if tpl else 'já feito'}")
        if tpl and apply:
            first = tpl[0]["id"]
            got = put(a, flows[name], live, tpl)
            retarget(a, LOC, flows[name], first)
            trs = [t for t in a.triggers(LOC, flows[name]) if not t.get("deleted")]
            ok = refs_ok(got["workflowData"]["templates"]) and got["status"] == live["status"] and all(t.get("targetActionId") == first for t in trs)
            print(f"      {'✓' if ok else '✗ VERIFICAR'} {got['status']} · re-entry {got.get('allowMultiple')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
