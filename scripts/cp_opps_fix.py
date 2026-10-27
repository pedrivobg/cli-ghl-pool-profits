#!/usr/bin/env python3
"""Clear Pool Solutions Tucson: only real open leads stay "open"; every card worth $150 (Derek via Pedro, 27/10).

    ./.venv/bin/python scripts/cp_opps_fix.py plan
    ./.venv/bin/python scripts/cp_opps_fix.py test --to pedro@poolprofits.com
    ./.venv/bin/python scripts/cp_opps_fix.py apply

Status by stage: Lost Customer → lost; SPAM and Out of Scope → abandoned; the 2 Won stages → won; New Lead, In
Communications, Booked Inspection → open. Value $150 on every card (Derek's average).
- Workflows: "Lost Lead" (stage Lost) starts with "Update opportunity: status lost"; "DND Contact" (stage SPAM) with
  "status abandoned"; new "Out of Scope - Close" (stage Out of Scope → status abandoned). Every "Create Or Update
  Opportunity" of the intake workflows: value 150 (Google Ads ones had 180) and status open, so a caller whose card was
  closed comes back as an open New Lead.
- Existing cards: PUT /opportunities/{id} {status, monetaryValue} only (no stage → no stage workflow fires).
test: after the workflow edits, a contact's card is moved to each closing stage (Lost, SPAM, Out of Scope) and the status
is checked; the contact is deleted (the "Lost Lead" email waits 2 days, so nothing goes out).
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
import time
import uuid

from _common import ROOT, load_dotenv
from pp_review_fix import read
from pp_source_tags import refs_ok

from cli_anything.gohighlevel.utils.agency import BACKEND, SERVICES, Agency

LOC = "ghUi89uCpNyNunNpbtAt"
PIPELINE = "3efxD12t1FgWeOkp11yA"
VALUE = 150
STATUS = {"Lost Customer": "lost", "SPAM": "abandoned", "Out of Scope": "abandoned",
          "🎉 Won Customer": "won", "Won Customer – One Time Repair": "won"}
CLOSERS = {"Lost Lead": "lost", "DND Contact": "abandoned"}
NEW_FLOW = "Out of Scope - Close"
BDIR = ROOT / "backup" / "clear-pool-solutions-tucson"


def update_step(status: str) -> dict:
    return {"id": str(uuid.uuid4()), "order": 0, "name": f"Update opportunity: {status}",
            "type": "internal_update_opportunity", "workflowsActionType": "INTERNAL",
            "attributes": {"allowBackward": False, "type": "internal_update_opportunity", "__customInputs__": {},
                           "__customInputFields__": [{"__customInputs__": {}, "dataType": "SINGLE_OPTIONS",
                                                      "filterField": "status", "value": status,
                                                      "valueFieldType": "select"}]}}


def prepend(tpl: list[dict], status: str) -> list[dict] | None:
    out = json.loads(json.dumps(tpl))
    if any(s["type"] == "internal_update_opportunity" for s in out):
        return None
    root = next(s for s in out if not s.get("parentKey"))
    st = update_step(status)
    st["next"] = root["id"]
    root["parentKey"] = st["id"]
    for s in out:
        s["order"] = s.get("order", 0) + 1
    return [st, *out]


def intake(tpl: list[dict]) -> list[dict] | None:
    out = json.loads(json.dumps(tpl))
    hit = False
    for s in out:
        a = s.get("attributes") or {}
        if s["type"] == "create_opportunity" and (str(a.get("monetary_value")) not in ("150", "150.00")
                                                  or a.get("opportunity_status") != "open"):
            a.update(monetary_value=f"{VALUE}.00", opportunity_status="open")
            hit = True
    return out if hit else None


def put(a: Agency, wid: str, live: dict, tpl: list[dict], status: str | None = None) -> dict:
    BDIR.mkdir(parents=True, exist_ok=True)
    (BDIR / f"workflow-{wid}-{time.strftime('%Y%m%d-%H%M%S')}.json").write_text(json.dumps(live))
    a.call("PUT", BACKEND, f"/workflow/{LOC}/{wid}", body={"name": live["name"], "version": live.get("version", 1),
                                                         "status": status or live["status"], "parentId": live.get("parentId"),
                                                         "workflowData": {"templates": tpl}})
    time.sleep(2)
    return read(a, LOC, wid)


def opps(a: Agency) -> list[dict]:
    out, page = [], 1
    while True:
        o = a.call("GET", SERVICES, "/opportunities/search", params={"location_id": LOC, "pipeline_id": PIPELINE,
                                                                     "limit": 100, "page": page}).get("opportunities", [])
        out += o
        if len(o) < 100:
            return out
        page += 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("mode", choices=["plan", "test", "apply", "cards"])
    parser.add_argument("--to")
    args = parser.parse_args()
    load_dotenv()
    a = Agency()
    if not a.location(LOC)["name"].startswith("Clear Pool Solutions"):
        sys.exit("sub-conta errada")
    flows = {w["name"]: w["id"] for w in a.workflows(LOC)}
    stages = {s["name"]: s["id"] for s in next(p for p in a.pipelines(LOC) if p["id"] == PIPELINE)["stages"]}
    names = {v: k for k, v in stages.items()}
    if args.mode in ("plan", "apply"):
        for name, status in CLOSERS.items():
            live = read(a, LOC, flows[name])
            tpl = prepend(live["workflowData"]["templates"], status)
            print(f"   {name}: {'+ status ' + status if tpl else 'já feito'}")
            if tpl and args.mode == "apply":
                got = put(a, flows[name], live, tpl)
                print(f"      {'✓' if refs_ok(got['workflowData']['templates']) and got['status'] == live['status'] else '✗'} {got['status']}")
        print(f"   {NEW_FLOW}: {'existe' if NEW_FLOW in flows else 'cria'}")
        if args.mode == "apply" and NEW_FLOW not in flows:
            parent = a.workflow(LOC, flows["Lost Lead"]).get("parentId")
            res = a.call("POST", BACKEND, f"/workflow/{LOC}", body={"name": NEW_FLOW, "parentId": parent, "status": "draft"})
            wid = res.get("id") or res.get("_id")
            tpl = [update_step("abandoned")]
            body = {"name": NEW_FLOW, "version": 1, "status": "draft", "parentId": parent, "allowMultiple": True,
                    "workflowData": {"templates": tpl}}
            a.call("PUT", BACKEND, f"/workflow/{LOC}/{wid}", body=body)
            trig = {"type": "pipeline_stage_updated", "name": "Pipeline Stage Changed", "masterType": "highlevel",
                    "schedule_config": {}, "workflowId": wid, "workflow_id": wid, "location_id": LOC,
                    "actions": [{"workflow_id": wid, "type": "add_to_workflow"}], "targetActionId": tpl[0]["id"],
                    "conditions": [{"operator": "==", "field": "opportunity.pipelineId", "value": PIPELINE, "title": "In pipeline", "type": "select"},
                                   {"operator": "==", "field": "opportunity.pipelineStageId", "value": stages["Out of Scope"],
                                    "title": "Pipeline stage", "type": "select"}]}
            t = a.call("POST", BACKEND, f"/workflow/{LOC}/trigger", body=trig)
            a.call("PUT", BACKEND, f"/workflow/{LOC}/trigger/{t['id']}", body={**trig, "id": t["id"]})
            live = a.workflow(LOC, wid)
            got = put(a, wid, live, live["workflowData"]["templates"], "published")
            trs = [x for x in a.triggers(LOC, wid) if not x.get("deleted")]
            print(f"      {'✓' if got['status'] == 'published' and len(trs) == 1 and trs[0].get('active') else '✗'} {got['status']}")
        for name, wid in flows.items():
            live = read(a, LOC, wid)
            tpl = intake(live["workflowData"]["templates"])
            if tpl:
                print(f"   {name}: card $150 + open")
                if args.mode == "apply":
                    got = put(a, wid, live, tpl)
                    print(f"      {'✓' if refs_ok(got['workflowData']['templates']) and got['status'] == live['status'] else '✗'} {got['status']}")
    if args.mode == "test":
        stamp = int(time.time())
        cid = a.call("POST", SERVICES, "/contacts/", body={"locationId": LOC, "firstName": "ZZ Test", "lastName": "status",
                                                           "email": args.to.replace("@", f"+cp-status-{stamp}@")})["contact"]["id"]
        time.sleep(3)
        o = a.call("POST", SERVICES, "/opportunities/", body={"locationId": LOC, "pipelineId": PIPELINE, "contactId": cid,
                                                              "pipelineStageId": stages["🚨 New Lead"], "name": "ZZ Test status",
                                                              "status": "open", "monetaryValue": VALUE})
        oid = (o.get("opportunity") or o)["id"]
        bad = 0
        for stage in ("Lost Customer", "SPAM", "Out of Scope"):
            a.call("PUT", SERVICES, f"/opportunities/{oid}", body={"pipelineId": PIPELINE, "pipelineStageId": stages[stage], "status": "open"})
            time.sleep(25)
            got = a.call("GET", SERVICES, f"/opportunities/{oid}").get("opportunity", {})
            ok = got.get("status") == STATUS[stage]
            bad += not ok
            print(f"   {'✓' if ok else '✗'} {stage}: status {got.get('status')} · valor {got.get('monetaryValue')}")
        a.call("DELETE", SERVICES, f"/opportunities/{oid}")
        a.call("DELETE", SERVICES, f"/contacts/{cid}")
        print("   limpo.")
        return 1 if bad else 0
    if args.mode in ("plan", "cards"):
        todo = [(o, STATUS.get(names.get(o["pipelineStageId"]), "open")) for o in opps(a)]
        todo = [(o, s) for o, s in todo if o["status"] != s or o.get("monetaryValue") != VALUE]
        print(f"   cards a acertar: {len(todo)} · {collections.Counter((names.get(o['pipelineStageId']), o['status'], s) for o, s in todo)}")
        if args.mode == "cards":
            (BDIR / f"opportunities-{time.strftime('%Y%m%d-%H%M%S')}.json").write_text(json.dumps([o for o, _ in todo]))
            for o, s in todo:
                a.call("PUT", SERVICES, f"/opportunities/{o['id']}", body={"status": s, "monetaryValue": VALUE})
            time.sleep(5)
            left = [o for o in opps(a) if o["status"] != STATUS.get(names.get(o["pipelineStageId"]), "open") or o.get("monetaryValue") != VALUE]
            print(f"   faltando: {len(left)} · {collections.Counter((names.get(o['pipelineStageId']), o['status']) for o in opps(a))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
