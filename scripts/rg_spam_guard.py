#!/usr/bin/env python3
"""Reign: calls that never press 1 in the "IVR SPAM Detection" stop becoming leads (Val, 27/10: "a lot of spam calls").

    ./.venv/bin/python scripts/rg_spam_guard.py plan
    ./.venv/bin/python scripts/rg_spam_guard.py apply

The IVR on the 3 lines already asks "press 1 to be connected"; robocalls don't, so Stephen's phone never rings for them.
But every call (pressed or not) fired the per-line call workflows: card in 🚨 New Lead, task for Stephen and, on the
Google Ads line, a Google Ads conversion and a thank-you text to the caller. Live 12-26/10: 38 calls, ~20 never pressed.
- IVR: "None" (no key) → tag `ivr no key`; "NOT SPAM" (pressed 1) → remove that tag, then ring Stephen as before.
- The 4 call workflows (AdWords Call In, Google Ads / Website-GBP / YELP Incoming Call To Pipeline): the whole chain moves
  under an if/else "Pressed 1 in the IVR?" (contact without `ivr no key`); otherwise nothing. Their triggers point at it.
Contact, call log and recording stay. GET + backup before each PUT.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import uuid

from _common import ROOT, load_dotenv
from pp_lead_alerts import guard_nodes, retarget
from pp_review_fix import read
from pp_source_tags import refs_ok

from cli_anything.gohighlevel.utils.agency import BACKEND, Agency

LOC_NAME = "Reign Pool Services"
TAG = "ivr no key"
IVR = "IVR SPAM Detection"
CALL_FLOWS = ["AdWords Call In - New Lead", "Google Ads Incoming Call To Pipeline",
              "Website/ GBP Incoming Call To Pipeline", "YELP Incoming Call To Pipeline"]
NAME = "Pressed 1 in the IVR?"
BDIR = ROOT / "backup" / "reign-pool-services"


def wrapped(tpl: list[dict]) -> list[dict] | None:
    """Linear chain → the same steps under the guard's "Lead" branch; None if already guarded or not linear."""
    if any(s["type"] == "if_else" for s in tpl):
        return None
    by = {s["id"]: s for s in tpl}
    chain = [next(s for s in tpl if not s.get("parentKey"))]
    while isinstance(chain[-1].get("next"), str) and chain[-1]["next"] in by:
        chain.append(by[chain[-1]["next"]])
    if len(chain) != len(tpl):
        return None
    c, y, n = guard_nodes(None, None, 0, skip=[TAG])
    for node in (c, y, n):
        node["name"] = NAME if node is c else node["name"]
    c["attributes"]["conditionName"] = NAME
    c["attributes"]["noneBranchName"] = n["name"] = "No key pressed (spam)"
    y["name"] = c["attributes"]["branches"][0]["name"] = "Pressed 1"
    chain = json.loads(json.dumps(chain))
    for i, s in enumerate(chain):
        s.update(order=i, parent=y["id"], parentKey=chain[i - 1]["id"] if i else y["id"])
    y["next"] = chain[0]["id"]
    return [c, y, n, *chain]


def ivr_tagged(tpl: list[dict]) -> list[dict] | None:
    out = json.loads(json.dumps(tpl))
    if any(s["type"] in ("add_contact_tag", "remove_contact_tag") for s in out):
        return None
    trans = {s["name"]: s for s in out if s["type"] == "transition"}
    none, ok = trans["None"], trans["NOT SPAM"]
    add = {"id": str(uuid.uuid4()), "order": 0, "name": f"Tag {TAG}", "type": "add_contact_tag", "parent": none["id"],
           "parentKey": none["id"], "attributes": {"type": "add_contact_tag", "tags": [TAG]}}
    none["next"] = add["id"]
    connect = next(s for s in out if s["id"] == ok["next"])
    rem = {"id": str(uuid.uuid4()), "order": 0, "name": f"Remove {TAG}", "type": "remove_contact_tag", "parent": ok["id"],
           "parentKey": ok["id"], "next": connect["id"], "attributes": {"type": "remove_contact_tag", "tags": [TAG]}}
    ok["next"] = rem["id"]
    connect.update(parentKey=rem["id"], order=1)
    return [*out, add, rem]


def put(a: Agency, loc: str, wid: str, live: dict, tpl: list[dict]) -> dict:
    (BDIR / f"workflow-{wid}-{time.strftime('%Y%m%d-%H%M%S')}.json").write_text(json.dumps(live))
    a.call("PUT", BACKEND, f"/workflow/{loc}/{wid}", body={"name": live["name"], "version": live.get("version", 1),
                                                         "status": live["status"], "parentId": live.get("parentId"),
                                                         "workflowData": {"templates": tpl}})
    time.sleep(2)
    return read(a, loc, wid)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("mode", choices=["plan", "apply"])
    args = parser.parse_args()
    load_dotenv()
    a = Agency()
    loc = next(l["id"] for l in a.locations() if l["name"] == LOC_NAME)
    flows = {w["name"]: w["id"] for w in a.workflows(loc)}
    BDIR.mkdir(parents=True, exist_ok=True)
    if args.mode == "apply":
        try:
            a.call("POST", BACKEND, f"/workflow/{loc}/tags/create", body={"tag": TAG})
        except Exception:  # noqa: BLE001 — already exists
            pass
    live = read(a, loc, flows[IVR])
    tpl = ivr_tagged(live["workflowData"]["templates"])
    print(f"   {IVR}: {'sem tecla → tag; tecla 1 → tira a tag' if tpl else 'já tem (nada a fazer)'}")
    if tpl and args.mode == "apply":
        got = put(a, loc, flows[IVR], live, tpl)
        print(f"      {'✓' if refs_ok(got['workflowData']['templates']) and got['status'] == live['status'] else '✗'} {got['status']}")
    for name in CALL_FLOWS:
        live = read(a, loc, flows[name])
        tpl = wrapped(live["workflowData"]["templates"])
        print(f"   {name}: {'cadeia de ' + str(len(live['workflowData']['templates'])) + ' passos sob a condição' if tpl else 'já tem if/else (nada a fazer)'}")
        if tpl and args.mode == "apply":
            got = put(a, loc, flows[name], live, tpl)
            retarget(a, loc, flows[name], tpl[0]["id"])
            trs = [t for t in a.triggers(loc, flows[name]) if not t.get("deleted")]
            ok = refs_ok(got["workflowData"]["templates"]) and got["status"] == live["status"] and \
                got.get("allowMultiple") == live.get("allowMultiple") and all(t.get("targetActionId") == tpl[0]["id"] for t in trs)
            print(f"      {'✓' if ok else '✗ VERIFICAR'} {got['status']} · re-entry {got.get('allowMultiple')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
