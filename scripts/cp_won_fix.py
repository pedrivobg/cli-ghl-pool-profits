#!/usr/bin/env python3
"""Clear Pool Solutions Tucson: Won cards were deleted by the "Current Customer" workflow (Pedro, 27/10).

    ./.venv/bin/python scripts/cp_won_fix.py plan
    ./.venv/bin/python scripts/cp_won_fix.py apply

"Current Customer" (trigger: card enters 🎉 Won Customer / Won Customer – One Time Repair) = "Remove Opportunity" →
every won card vanished (37 contacts tagged `won`, 35 without a card). apply: (1) "Current Customer" → draft (backup);
(2) a card for each `won` contact without one, status won, in "Won Customer – One Time Repair" when the contact has
`one time repair`, else 🎉 Won Customer. Creating a card in a Won stage fires the Won workflows (tested: welcome email,
conversion), so those 4 stay in draft while the cards are created and are published again right after.
"""
from __future__ import annotations

import argparse
import json
import sys
import time

from _common import ROOT, load_dotenv

from cli_anything.gohighlevel.utils.agency import BACKEND, SERVICES, Agency

LOC = "ghUi89uCpNyNunNpbtAt"
PIPELINE = "3efxD12t1FgWeOkp11yA"
WON, REPAIR = "b9e8a935-b4b5-4950-a204-34c18efdb339", "5cc343d7-633b-44bd-b45e-4b43be12e33e"
KILLER = "Current Customer"
PAUSE = ["Won Customer", "Repair Customer Won", "Adword Call - Conversion", "Adword Form - Conversion"]
BDIR = ROOT / "backup" / "clear-pool-solutions-tucson"


def status(a: Agency, wid: str, st: str) -> str:
    live = a.workflow(LOC, wid)
    if live["status"] == st:
        return st
    BDIR.mkdir(parents=True, exist_ok=True)
    (BDIR / f"workflow-{wid}-{time.strftime('%Y%m%d-%H%M%S')}.json").write_text(json.dumps(live))
    a.call("PUT", BACKEND, f"/workflow/{LOC}/{wid}", body={"name": live["name"], "version": live.get("version", 1),
                                                         "status": st, "parentId": live.get("parentId"),
                                                         "workflowData": {"templates": live["workflowData"]["templates"]}})
    time.sleep(2)
    return a.workflow(LOC, wid)["status"]


def missing(a: Agency) -> list[dict]:
    opps, page = [], 1
    while True:
        o = a.call("GET", SERVICES, "/opportunities/search", params={"location_id": LOC, "pipeline_id": PIPELINE,
                                                                     "limit": 100, "page": page}).get("opportunities", [])
        opps += o
        if len(o) < 100:
            break
        page += 1
    have = {(o.get("contact") or {}).get("id") or o.get("contactId") for o in opps}
    won = a.call("POST", SERVICES, "/contacts/search", body={"locationId": LOC, "pageLimit": 200, "filters": [
        {"field": "tags", "operator": "contains", "value": "won"}]}).get("contacts", [])
    return [c for c in won if c["id"] not in have and not (c.get("contactName") or "").startswith("zz test")]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("mode", choices=["plan", "apply"])
    args = parser.parse_args()
    load_dotenv()
    a = Agency()
    flows = {w["name"]: w["id"] for w in a.workflows(LOC)}
    todo = missing(a)
    print(f"   {KILLER}: {a.workflow(LOC, flows[KILLER])['status']} → draft · {len(todo)} cards a recriar")
    if args.mode == "plan":
        for c in todo:
            print(f"      {c.get('contactName') or c.get('phone')} · {'One Time Repair' if 'one time repair' in (c.get('tags') or []) else 'Won Customer'}")
        return 0
    print(f"   {KILLER}: {status(a, flows[KILLER], 'draft')}")
    paused = [n for n in PAUSE if a.workflow(LOC, flows[n])["status"] == "published"]
    try:
        for n in paused:
            print(f"   pausa {n}: {status(a, flows[n], 'draft')}")
        time.sleep(5)
        for c in todo:
            name = " ".join(x for x in (c.get("firstName"), c.get("lastName")) if x) or c.get("phone") or c["id"]
            stage = REPAIR if "one time repair" in (c.get("tags") or []) else WON
            a.call("POST", SERVICES, "/opportunities/", body={"locationId": LOC, "pipelineId": PIPELINE, "pipelineStageId": stage,
                                                              "contactId": c["id"], "name": name, "status": "won",
                                                              "source": "Recreated 27/10 (deleted by workflow)"})
        time.sleep(10)
    finally:
        for n in paused:
            print(f"   volta {n}: {status(a, flows[n], 'published')}")
    print(f"   faltando agora: {len(missing(a))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
