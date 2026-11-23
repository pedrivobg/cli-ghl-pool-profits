#!/usr/bin/env python3
"""Pool Duck Lakewood Ranch (Pedro 23/11): leads only in the new pipeline.

    GHL_AGENCY=poolduck python3 scripts/pd_lwr_pipeline_fix.py           # plan
    GHL_AGENCY=poolduck python3 scripts/pd_lwr_pipeline_fix.py --apply

Found: the 6 published lead flows (Google Ads form / call / SMS / lead form / commercial, Facebook form) created the card
in the OLD pipeline "Leads --> Sales Pipeline" (stage Lead); the V9 "Pool Leads" was only used by drafts and by
"Won -> Google Ads". Fix (backup of every workflow, card and contact in backup/pool-duck-lakewood-ranch/):
1. create_opportunity of those 6 → "Pool Leads" / 🆕 New Lead (nothing else in them changes).
2. "Pool Leads" renamed "01. Pool Leads" (ids kept), so it is listed first.
3. Cards in the old pipeline: 4 tests deleted with their contacts; existing customers → 🔄 Recurring Customer; the
   wrong-number SMS → 🚫 Spam; the rest → 🆕 New Lead.
"""
from __future__ import annotations

import argparse
import json
import os
import time

from _common import ROOT, Agency, load_dotenv
from cli_anything.gohighlevel.utils.agency import BACKEND, SERVICES

LOC = "MosKIX4oux96vchwHZ5W"
OLD, NEW = "bBmO8YBJXxiKgEJEN3Ol", "IyN7Ou1NgG2zA4qvj4ZS"
FLOWS = ["19907be2-0c1a-487e-a2bc-57cc8020d3c7", "591aa80b-9d73-401b-bc45-e13eb60635c2",
         "a0ea323f-f54f-4766-9129-fd7ecbe08bab", "c1aef099-092d-4538-83c0-384a2c0f01fe",
         "2ade8916-97b7-44cf-8f07-b24072586bc6", "de710a33-40d0-4509-ba2d-864f1e340875"]
TESTS = {"8lYJT0EHajd97bbzqJwf": "pkiVVQRZKYCPgjn2De4B", "391KdLNMzFDVSCfLe7wX": "6PnmtVsYMENNHdWzl0lw",
         "BiDrbo6IqcSRUTkJYiOW": "9W3HqWvWJJPnUiz9nVk5", "9Qr56ATilwm28fyIRiO1": "yNhCSqr3TpzJGmNleitc"}
SPAM_OPPS = {"53QlroS4MNjFfrPJJRGC"}  # "Hi Tyler ... dental insurance" — wrong number
NEW_NAME = "01. Pool Leads"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    load_dotenv()
    a = Agency()
    bdir = os.path.join(ROOT, "backup", "pool-duck-lakewood-ranch", f"pipeline-fix-{time.strftime('%Y%m%d-%H%M%S')}")
    pipes = {p["id"]: p for p in a.call("GET", SERVICES, "/opportunities/pipelines", params={"locationId": LOC})["pipelines"]}
    stage = {s["name"]: s["id"] for s in pipes[NEW]["stages"]}
    new_lead, recurring, spam = stage["🆕 New Lead"], stage["🔄 Recurring Customer"], stage["🚫 Spam"]
    if args.apply:
        os.makedirs(bdir, exist_ok=True)
        json.dump(pipes, open(os.path.join(bdir, "pipelines.json"), "w"), indent=1)

    for wid in FLOWS:  # 1. lead flows → new pipeline
        live = a.workflow(LOC, wid)
        t = json.loads(json.dumps(live["workflowData"]["templates"]))
        n = 0
        for s in t:
            at = s.get("attributes") or {}
            if s["type"] == "create_opportunity" and at.get("pipeline_id") == OLD:
                at.update(pipeline_id=NEW, pipeline_stage_id=new_lead)
                n += 1
        left = OLD in json.dumps(t)
        print(f"   {live['name']} ({live['status']}): {n} card step(s) → {NEW_NAME} / New Lead" + ("  !! old id still in it" if left else ""))
        if args.apply and n:
            json.dump(live, open(os.path.join(bdir, f"{wid}.json"), "w"), indent=1)
            a.call("PUT", BACKEND, f"/workflow/{LOC}/{wid}", body={
                "name": live["name"], "version": live.get("version", 1), "status": live["status"],
                "parentId": live.get("parentId"), "allowMultiple": live.get("allowMultiple", False),
                "workflowData": {"templates": t}})

    p = pipes[NEW]  # 2. rename
    print(f"   pipeline '{p['name']}' → '{NEW_NAME}'")
    if args.apply and p["name"] != NEW_NAME:
        a.call("PUT", SERVICES, f"/opportunities/pipelines/{NEW}", body={"name": NEW_NAME, "stages": p["stages"]})

    r = a.call("GET", SERVICES, "/opportunities/search", params={"location_id": LOC, "pipeline_id": OLD, "limit": 100})
    for o in r.get("opportunities", []):  # 3. cards
        cid = o.get("contactId") or (o.get("contact") or {}).get("id")
        tags = (o.get("contact") or {}).get("tags") or []
        if o["id"] in TESTS:
            print(f"   delete test card + contact: {o.get('name')}")
            if args.apply:
                c = a.call("GET", SERVICES, f"/contacts/{cid}")
                json.dump({"opportunity": o, "contact": c}, open(os.path.join(bdir, f"test-{o['id']}.json"), "w"), indent=1)
                a.call("DELETE", SERVICES, f"/opportunities/{o['id']}")
                a.call("DELETE", SERVICES, f"/contacts/{TESTS[o['id']]}")
            continue
        to = spam if o["id"] in SPAM_OPPS else recurring if "existing customer" in tags else new_lead
        label = "Spam" if to == spam else "Recurring Customer" if to == recurring else "New Lead"
        print(f"   move: {o.get('name') or '(no name)'} → {label}")
        if args.apply:
            json.dump(o, open(os.path.join(bdir, f"opp-{o['id']}.json"), "w"), indent=1)
            a.call("PUT", SERVICES, f"/opportunities/{o['id']}", body={"pipelineId": NEW, "pipelineStageId": to})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
