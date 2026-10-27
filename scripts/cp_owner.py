#!/usr/bin/env python3
"""Clear Pool Solutions Tucson: Derek owns every contact and every opportunity, however the lead arrives (Pedro, 27/10).

    ./.venv/bin/python scripts/cp_owner.py plan
    ./.venv/bin/python scripts/cp_owner.py apply

A card created by a workflow takes the contact's owner (tested: contact owned by Derek → card assignedTo Derek; the
create-opportunity step has no owner field of its own). So:
- new "Contact Created -> Assign Derek" (trigger Contact Created, step Assign to user = Derek), for any way a contact appears;
- "Assign to Derek" as the first step of every intake workflow that creates a card, so the owner is set before the card
  whichever workflow runs first; their triggers are pointed at the new first step;
- existing contacts and cards without Derek as owner: PUT assignedTo (backup first).
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
from pp_source_tags import refs_ok

from cli_anything.gohighlevel.utils.agency import BACKEND, SERVICES, Agency

LOC = "ghUi89uCpNyNunNpbtAt"
PIPELINE = "3efxD12t1FgWeOkp11yA"
DEREK = "zUhz5NEJu5i2WSMQBl1S"
FLOW = "Contact Created -> Assign Derek"
BDIR = ROOT / "backup" / "clear-pool-solutions-tucson"


def assign_step() -> dict:
    return {"id": str(uuid.uuid4()), "order": 0, "name": "Assign to Derek", "type": "assign_user",
            "attributes": {"type": "assign_user", "only_unassigned_contact": False, "total_index": 1, "traffic_split": "equally",
                           "traffic_weightage": {DEREK: 1}, "traffic_index": [{"id": DEREK, "indexes": [1]}], "user_list": [DEREK]}}


def prepend(tpl: list[dict]) -> list[dict] | None:
    out = json.loads(json.dumps(tpl))
    if any(s["type"] == "assign_user" for s in out):
        return None
    root = next(s for s in out if not s.get("parentKey") and not s.get("parent"))
    st = assign_step()
    st["next"] = root["id"]
    root["parentKey"] = st["id"]
    return [st, *out]


def put(a: Agency, wid: str, live: dict, tpl: list[dict]) -> dict:
    BDIR.mkdir(parents=True, exist_ok=True)
    (BDIR / f"workflow-{wid}-{time.strftime('%Y%m%d-%H%M%S')}.json").write_text(json.dumps(live))
    a.call("PUT", BACKEND, f"/workflow/{LOC}/{wid}", body={"name": live["name"], "version": live.get("version", 1),
                                                         "status": live["status"], "parentId": live.get("parentId"),
                                                         "workflowData": {"templates": tpl}})
    time.sleep(2)
    return read(a, LOC, wid)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("mode", choices=["plan", "apply"])
    args = parser.parse_args()
    load_dotenv()
    a = Agency()
    if not a.location(LOC)["name"].startswith("Clear Pool Solutions"):
        sys.exit("sub-conta errada")
    apply = args.mode == "apply"
    flows = {w["name"]: w for w in a.workflows(LOC)}
    print(f"   {FLOW}: {'existe' if FLOW in flows else 'cria'}")
    if apply and FLOW not in flows:
        res = a.call("POST", BACKEND, f"/workflow/{LOC}", body={"name": FLOW, "status": "draft"})
        wid = res.get("id") or res.get("_id")
        tpl = [assign_step()]
        body = {"name": FLOW, "version": 1, "status": "draft", "allowMultiple": True, "workflowData": {"templates": tpl}}
        a.call("PUT", BACKEND, f"/workflow/{LOC}/{wid}", body=body)
        trig = {"type": "contact_created", "name": "Contact Created", "masterType": "highlevel", "schedule_config": {},
                "conditions": [], "workflowId": wid, "workflow_id": wid, "location_id": LOC,
                "actions": [{"workflow_id": wid, "type": "add_to_workflow"}], "targetActionId": tpl[0]["id"]}
        t = a.call("POST", BACKEND, f"/workflow/{LOC}/trigger", body=trig)
        a.call("PUT", BACKEND, f"/workflow/{LOC}/trigger/{t['id']}", body={**trig, "id": t["id"]})
        live = a.workflow(LOC, wid)
        a.call("PUT", BACKEND, f"/workflow/{LOC}/{wid}", body={**body, "status": "published", "version": live.get("version", 1),
                                                             "workflowData": {"templates": live["workflowData"]["templates"]}})
        time.sleep(3)
        trs = [x for x in a.triggers(LOC, wid) if not x.get("deleted")]
        print(f"      {'✓' if a.workflow(LOC, wid)['status'] == 'published' and trs and trs[0].get('active') else '✗'} publicado")
    for name, w in flows.items():
        if w["status"] != "published" or name == FLOW:
            continue
        live = read(a, LOC, w["id"])
        tpl0 = live["workflowData"]["templates"]
        if not any(s["type"] == "create_opportunity" and (s.get("attributes") or {}).get("opportunity_status") == "open" for s in tpl0):
            continue
        tpl = prepend(tpl0)
        print(f"   {name}: {'+ Assign to Derek no início' if tpl else 'já tem'}")
        if tpl and apply:
            got = put(a, w["id"], live, tpl)
            retarget(a, LOC, w["id"], tpl[0]["id"])
            trs = [t for t in a.triggers(LOC, w["id"]) if not t.get("deleted")]
            ok = refs_ok(got["workflowData"]["templates"]) and got["status"] == "published" and all(t.get("targetActionId") == tpl[0]["id"] for t in trs)
            print(f"      {'✓' if ok else '✗ VERIFICAR'} {got['status']}")
    contacts, page = [], 1
    while True:
        r = a.call("POST", SERVICES, "/contacts/search", body={"locationId": LOC, "pageLimit": 500, "page": page})
        contacts += r.get("contacts", [])
        if len(r.get("contacts", [])) < 500:
            break
        page += 1
    opps, page = [], 1
    while True:
        o = a.call("GET", SERVICES, "/opportunities/search", params={"location_id": LOC, "limit": 100, "page": page}).get("opportunities", [])
        opps += o
        if len(o) < 100:
            break
        page += 1
    c_todo = [c for c in contacts if c.get("assignedTo") != DEREK]
    o_todo = [o for o in opps if o.get("assignedTo") != DEREK]
    print(f"   contatos sem o Derek: {len(c_todo)} de {len(contacts)} · cards sem o Derek: {len(o_todo)} de {len(opps)}")
    if apply:
        (BDIR / f"owners-before-{time.strftime('%Y%m%d-%H%M%S')}.json").write_text(json.dumps(
            {"contacts": {c["id"]: c.get("assignedTo") for c in c_todo}, "opps": {o["id"]: o.get("assignedTo") for o in o_todo}}))
        for c in c_todo:
            a.call("PUT", SERVICES, f"/contacts/{c['id']}", body={"assignedTo": DEREK})
        for o in o_todo:
            a.call("PUT", SERVICES, f"/opportunities/{o['id']}", body={"assignedTo": DEREK})
        time.sleep(5)
        left_o = [o for o in a.call("GET", SERVICES, "/opportunities/search", params={"location_id": LOC, "limit": 100}).get("opportunities", [])
                  if o.get("assignedTo") != DEREK]
        print(f"   feito · cards (1ª página) ainda sem o Derek: {len(left_o)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
