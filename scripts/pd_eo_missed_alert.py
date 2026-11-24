#!/usr/bin/env python3
"""Pool Duck East Orlando (24/11): owner gets a text for every missed call (Ed: calls must alert the business owner).

    GHL_AGENCY=poolduck python3 scripts/pd_eo_missed_alert.py            # plan
    GHL_AGENCY=poolduck python3 scripts/pd_eo_missed_alert.py --apply

"Missed Incoming Call To Pipeline" only created the card + a task 1 h later. Adds "Missed Call SMS - Owner" right after the
card step (same branch, so the flow's own spam/customer guard still applies) → user "Pool Duck East Orlando" (Luis's
login; his cell is on the user). Same step shape as the live WC alert (pd_wc_lead_alerts.py). Backup before the PUT.
"""
from __future__ import annotations

import argparse
import json
import os
import time

from _common import ROOT, Agency, load_dotenv
from pd_wc_lead_alerts import after
from pp_lead_alerts import nid, put_workflow

LOC = "m2glhRgphyM7uXh4Rc8u"
OWNER = "BjM7yUTmnomeYqNqnkee"
FLOW = "Missed Incoming Call To Pipeline"
NAME = "Missed Call SMS - Owner"


def alert() -> dict:
    return {"id": nid(), "name": NAME, "type": "internal_notification", "attributes": {"type": "sms", "sms": {
        "body": "\U0001f4de MISSED CALL - new lead\n\nName: {{contact.name}}\nPhone: {{contact.phone}}\n\nCall them back from the "
                "Pool Duck app.", "selectedUser": [OWNER], "userType": "user", "attachments": []}}}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    load_dotenv()
    a = Agency()
    wid = next(w["id"] for w in a.workflows(LOC) if w["name"] == FLOW)
    live = a.workflow(LOC, wid)
    t = json.loads(json.dumps(live["workflowData"]["templates"]))
    if any(s.get("name") == NAME for s in t):
        print("already there")
        return 0
    card = next(s for s in t if s["type"] == "create_opportunity")
    after(t, card, alert())
    ids = {s["id"] for s in t}
    for s in t:
        for r in ([s["next"]] if isinstance(s.get("next"), str) else s.get("next") or []) + [x for x in (s.get("parent"), s.get("parentKey")) if x]:
            assert r in ids, f"dangling {r}"
    for s in t:
        print(f"   {s.get('order')} {s['type']:22} {s.get('name')}  parent={str(s.get('parent'))[:8]}")
    if args.apply:
        d = os.path.join(ROOT, "backup", "pool-duck-east-orlando")
        os.makedirs(d, exist_ok=True)
        json.dump(live, open(os.path.join(d, f"{wid}-{time.strftime('%Y%m%d-%H%M%S')}.json"), "w"))
        put_workflow(a, LOC, wid, live, t)
        time.sleep(4)
        now = a.workflow(LOC, wid)
        print("saved:", now["status"], [s.get("name") for s in now["workflowData"]["templates"] if s["type"] == "internal_notification"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
