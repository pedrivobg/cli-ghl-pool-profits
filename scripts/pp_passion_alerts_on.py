#!/usr/bin/env python3
"""Passion Pool Care: lead alerts back on, texts to customers stay off (Frank 17/11, after the 19 workflows went to draft:
"We need to make sure we keep lead alerts, the only thing that needs to be in draft is any text messages automations").

- ALERT_ONLY: drafted workflows with no customer message (alerts / card / task only) -> published as they are.
- STRIP_SMS: the 3 "AdWords * - New Lead" flows end in wait -> SMS to the lead: those two last steps are removed (the
  alert, tag and card stay) and the flow is published.
Plan by default; --apply writes (GET + backup in backup/passion-pool-care/ first).

  python3 scripts/pp_passion_alerts_on.py [--apply]
"""
from __future__ import annotations

import argparse
import json
import time

from _common import ROOT, Agency, load_dotenv
from cli_anything.gohighlevel.utils.agency import BACKEND

LOC = "d03SMzI37dxTBeuoTJ13"
ALERT_ONLY = ["Answered Incoming Call To Pipeline", "Inbound SMS - Notify Owner", "SMS Customer Reply to pipeline",
              "Website & GBP Call - Lead Email", "Website & GBP SMS - Lead Email", "Website Form Fill To Pipeline"]
STRIP_SMS = ["AdWords Call In - New Lead", "AdWords Form - New Lead", "AdWords SMS - New Lead"]
CUSTOMER = {"sms", "email", "send_sms", "send_email", "voicemail", "messenger", "gmb", "whatsapp"}


def strip_tail(templates: list[dict]) -> list[dict]:
    """Drop the final wait -> sms pair; the step before it becomes the end of its branch."""
    by_id = {s["id"]: s for s in templates}
    sms = [s for s in templates if s["type"] == "sms" and not s.get("next")]
    assert len(sms) == 1, "expected one final SMS step"
    wait = by_id[sms[0]["parentKey"]]
    assert wait["type"] == "wait" and wait.get("next") == sms[0]["id"], "expected wait -> sms at the end"
    prev = by_id[wait["parentKey"]]
    out = [s for s in templates if s["id"] not in (sms[0]["id"], wait["id"])]
    for s in out:
        if s["id"] == prev["id"]:
            s.pop("next", None)
    return out


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--apply", action="store_true")
    args = p.parse_args()
    load_dotenv()
    a = Agency()
    flows = {w["name"]: w for w in a.workflows(LOC)}
    bdir = ROOT / "backup" / "passion-pool-care"
    bdir.mkdir(parents=True, exist_ok=True)
    for name in ALERT_ONLY + STRIP_SMS:
        w = flows[name]
        live = a.workflow(LOC, w["id"])
        tpl = live["workflowData"]["templates"]
        if name in STRIP_SMS:
            tpl = strip_tail(json.loads(json.dumps(tpl)))
        left = [s["type"] for s in tpl if s["type"] in CUSTOMER]
        print(f"{w.get('status'):9} -> published  {name}  ({len(live['workflowData']['templates'])} -> {len(tpl)} steps;"
              f" customer messages left: {left or 'none'})")
        assert not left, name
        if not args.apply:
            continue
        (bdir / f"{w['id']}-{time.strftime('%Y%m%d-%H%M%S')}.json").write_text(json.dumps(live))
        a.call("PUT", BACKEND, f"/workflow/{LOC}/{w['id']}", body={
            "name": live["name"], "version": live.get("version", 1), "status": "published",
            "parentId": live.get("parentId"), "workflowData": {"templates": tpl}})
        time.sleep(2)
    if args.apply:
        time.sleep(5)
        for name in ALERT_ONLY + STRIP_SMS:
            live = a.workflow(LOC, flows[name]["id"])
            trig = [(t.get("type"), t.get("active")) for t in a.triggers(LOC, flows[name]["id"])]
            print(f"  now {live.get('status')}: {name} | steps {[s['type'] for s in live['workflowData']['templates']]} | {trig}")


if __name__ == "__main__":
    main()
