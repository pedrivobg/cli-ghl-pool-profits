#!/usr/bin/env python3
"""Stay Fresh: STOP / unsubscribe replies do not become New Leads (Val, 04/11).

    ./.venv/bin/python scripts/sf_stop_guard.py plan
    ./.venv/bin/python scripts/sf_stop_guard.py test      # copy with a tag trigger: a non-STOP contact still gets the card
    ./.venv/bin/python scripts/sf_stop_guard.py apply

Val: "Can we exclude STOP/unsubscribe replies from automatically creating New Lead opportunities?". The 2 reply
workflows ("Drain & Wash Campaign - Replies", "SMS Customer Reply to pipeline") run a linear chain (card in New Lead,
`new lead`, alerts to Mike/Kris). This wraps the whole chain in an if/else "STOP reply?":
- branch "STOP / unsubscribe": reply is exactly one of the opt-out words, or contains "unsubscribe" → nothing
  (GHL already sets DND on a STOP).
- none branch "Real reply": the old chain, unchanged (same step ids).
The condition is the reply-body condition already used live in other accounts (`contact_reply` / `message.body`).
A reply can't be simulated through the API: `test` only proves the "Real reply" path still runs (tag-trigger copy,
no reply body → none branch → card); the STOP path needs a real text (Pedro).
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import uuid

from _common import ROOT, load_dotenv
from pp_lead_alerts import IS_OPS, NEST, retarget
from pp_review_fix import read
from pp_source_tags import fresh_ids, refs_ok
from sf_campaign_replies import BDIR, DW, LOC, NEW_LEAD, REPLY, create_copy, drop_flow, put

from cli_anything.gohighlevel.utils.agency import SERVICES, Agency

NAME = "STOP reply?"
WORDS = "stop,stop all,stopall,unsubscribe,cancel,end,quit,remove,remove me,opt out,optout"


def nid() -> str:
    return str(uuid.uuid4())


def cond(sub_op: str, value: str) -> dict:
    return {"conditionType": "contact_reply", "conditionSubType": "message.body", "conditionOperator": sub_op,
            "conditionValue": value, "__conditionId": nid(), "ifElseNodeId": "", "__customFieldType__": "standard",
            "isWait": False, "nestedDropdownTypes": NEST, "allowIsOperatorTypes": IS_OPS}


def linear(templates: list[dict]) -> list[dict]:
    by = {s["id"]: s for s in templates}
    first = next(s for s in templates if not s.get("parentKey"))
    out = [first]
    while isinstance(out[-1].get("next"), str):
        out.append(by[out[-1]["next"]])
    if len(out) != len(templates):
        raise SystemExit("not a linear chain — not rebuilding blindly")
    return json.loads(json.dumps(out))


def wrap(templates: list[dict]) -> list[dict] | None:
    if any(s.get("name") == NAME for s in templates):
        return None
    chain = linear(templates)
    c, stop, real = nid(), nid(), nid()
    node = {"id": c, "order": 0, "name": NAME, "type": "if_else", "cat": "conditions", "nodeType": "condition-node",
            "comments": [], "next": [stop, real],
            "attributes": {"currentRecipeType": "CUSTOM", "operator": "and", "if": True, "conditionName": NAME,
                           "version": 2, "noneBranchName": "Real reply",
                           "branches": [{"id": stop, "name": "STOP / unsubscribe", "operator": "and",
                                         "showErrors": False, "branchNameError": "Branch name cannot be empty!",
                                         "segments": [{"__segmentId": nid(), "operator": "or",
                                                       "conditions": [cond("is-any-of", WORDS),
                                                                      cond("contain", "unsubscribe")]}]}]}}
    yes = {"id": stop, "parent": c, "parentKey": c, "order": 1, "name": "STOP / unsubscribe", "type": "if_else",
           "cat": "conditions", "sibling": [real], "comments": [], "nodeType": "branch-yes",
           "attributes": {"if": False, "conditionName": "Condition", "operator": "and", "branches": []}}
    none = {"id": real, "parent": c, "parentKey": c, "order": 1, "name": "Real reply", "type": "if_else",
            "cat": "conditions", "sibling": [stop], "comments": [], "nodeType": "branch-no",
            "attributes": {"else": True}, "next": chain[0]["id"]}
    for i, s in enumerate(chain):
        s.update(order=i, parent=real, parentKey=chain[i - 1]["id"] if i else real)
    return [node, yes, none, *chain]


def test(a: Agency, flows: dict) -> int:
    stamp = int(time.time())
    live = read(a, LOC, flows[DW])
    tpl = wrap(live["workflowData"]["templates"])
    if tpl is None:
        tpl = live["workflowData"]["templates"]
    keep = [s for s in json.loads(json.dumps(tpl)) if s["type"] != "internal_notification"]  # no alerts from a test
    for s in keep:  # re-link the chain without the dropped alerts
        if isinstance(s.get("next"), str) and s["next"] not in {k["id"] for k in keep}:
            s.pop("next")
    ids = {k["id"] for k in keep}
    kept = [s for s in keep if s["type"] != "if_else"]
    for i, s in enumerate(kept):
        s["parentKey"] = kept[i - 1]["id"] if i else s["parent"]
        if i < len(kept) - 1:
            s["next"] = kept[i + 1]["id"]
        else:
            s.pop("next", None)
    assert all(s.get("parentKey") in ids or not s.get("parentKey") for s in keep)
    tag, wid, cid = f"zz sf stop guard {stamp}", None, None
    try:
        wid = create_copy(a, "ZZ TEST stop guard copy", keep, tag, live.get("parentId"))
        time.sleep(8)
        cid = a.call("POST", SERVICES, "/contacts/", body={"locationId": LOC, "firstName": "ZZ Test",
                                                              "lastName": "stop guard",
                                                              "email": f"pedro+sf-stop-{stamp}@poolprofits.com"})["contact"]["id"]
        time.sleep(5)
        a.call("POST", SERVICES, f"/contacts/{cid}/tags", body={"tags": [tag]})
        time.sleep(60)
        opps = [o for o in a.call("GET", SERVICES, "/opportunities/search",
                                  params={"location_id": LOC, "limit": 100})["opportunities"] if o["contactId"] == cid]
        tags = set(a.call("GET", SERVICES, f"/contacts/{cid}")["contact"].get("tags") or [])
        ok = len(opps) == 1 and opps[0]["pipelineStageId"] == NEW_LEAD and "new lead" in tags
        print(f"   {'✓' if ok else '✗'} real-reply path: cards {len(opps)} · tags {sorted(t for t in tags if not t.startswith('zz'))}")
        return 0 if ok else 1
    finally:
        if cid:
            for o in a.call("GET", SERVICES, "/opportunities/search", params={"location_id": LOC, "limit": 100})["opportunities"]:
                if o["contactId"] == cid:
                    a.call("DELETE", SERVICES, f"/opportunities/{o['id']}")
            a.call("DELETE", SERVICES, f"/contacts/{cid}")
        if wid:
            drop_flow(a, wid)
        print("   limpo.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("mode", choices=["plan", "test", "apply"])
    args = parser.parse_args()
    load_dotenv()
    a = Agency()
    if not a.location(LOC)["name"].startswith("Stay Fresh"):
        sys.exit("sub-conta errada")
    flows = {w["name"]: w["id"] for w in a.workflows(LOC)}
    if args.mode == "test":
        return test(a, flows)
    bad = 0
    for name in (DW, REPLY):
        live = read(a, LOC, flows[name])
        tpl = wrap(live["workflowData"]["templates"])
        print(f"   {name}: {'já feito' if tpl is None else f'{len(tpl)} nós (if/else + {len(tpl) - 3} passos)'}")
        if tpl is None or args.mode != "apply":
            continue
        got = put(a, flows[name], live, tpl)
        retarget(a, LOC, flows[name], tpl[0]["id"])
        trs = [t for t in a.triggers(LOC, flows[name]) if not t.get("deleted")]
        t2 = got["workflowData"]["templates"]
        ok = refs_ok(t2) and len(t2) == len(tpl) and got["status"] == live["status"] and \
            got.get("allowMultiple") == live.get("allowMultiple") and \
            all(t.get("targetActionId") == tpl[0]["id"] and t.get("active") for t in trs)
        bad += not ok
        print(f"      {'✓' if ok else '✗ VERIFICAR'} {got['status']} · re-entry {got.get('allowMultiple')} · {len(t2)} nós")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
