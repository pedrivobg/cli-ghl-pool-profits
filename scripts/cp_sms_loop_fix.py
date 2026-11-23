#!/usr/bin/env python3
"""Clear Pool Tucson 23/11: owner's own cell (auto-reply) looped with "Inbound SMS - Notify Owner" (Pedro aprovou A).

Tag `owner - no sms alert` on the owner's own contact + Doesn't Have Tag filter on the Customer Replied trigger.
GET + backup before every write.   ./.venv/bin/python scripts/cp_sms_loop_fix.py [plan|apply]
"""
from __future__ import annotations

import json
import sys
import time

from _common import ROOT, Agency, load_dotenv
from cli_anything.gohighlevel.utils.agency import BACKEND, SERVICES

LOC = "ghUi89uCpNyNunNpbtAt"
WID = "ef6fba7d-595c-44de-b595-059fb60178a7"
CONTACT = "SppbFBbeEgyBATuQN4X5"
TAG = "owner - no sms alert"
COND = {"field": "contact.tags", "id": "doesnot-have-tag", "title": "Doesn't Have Tag", "type": "select",
        "operator": "index-of-false", "value": TAG}


def main() -> int:
    write = len(sys.argv) > 1 and sys.argv[1] == "apply"
    load_dotenv()
    a = Agency()
    d = ROOT / "backup" / "clear-pool-solutions-tucson"
    d.mkdir(parents=True, exist_ok=True)
    st = time.strftime("%Y%m%d-%H%M%S")
    c = a.call("GET", SERVICES, f"/contacts/{CONTACT}").get("contact", {})
    print("contato:", c.get("firstName"), c.get("phone"), c.get("tags"))
    trs = a.triggers(LOC, WID)
    print("gatilhos:", [(t.get("type"), [x.get("value") for x in t.get("conditions") or []]) for t in trs])
    if not write:
        return 0
    (d / f"contact-{CONTACT}-{st}.json").write_text(json.dumps(c, indent=1))
    (d / f"{WID}-triggers-{st}.json").write_text(json.dumps(trs, indent=1))
    try:
        a.call("POST", BACKEND, f"/workflow/{LOC}/tags/create", body={"tag": TAG})
    except Exception as e:  # already exists
        print("tag create:", str(e)[:120])
    if TAG not in (c.get("tags") or []):
        a.call("POST", SERVICES, f"/contacts/{CONTACT}/tags", body={"tags": [TAG]})
    for t in trs:
        if t.get("type") != "customer_reply":
            continue
        conds = t.get("conditions") or []
        if any(x.get("value") == TAG for x in conds):
            continue
        body = {**t, "conditions": conds + [COND], "workflowId": WID, "workflow_id": WID, "location_id": LOC}
        a.call("PUT", BACKEND, f"/workflow/{LOC}/trigger/{t['id']}", body=body)
    time.sleep(6)
    c2 = a.call("GET", SERVICES, f"/contacts/{CONTACT}").get("contact", {})
    trs2 = a.triggers(LOC, WID)
    w = a.workflow(LOC, WID)
    ok = TAG in (c2.get("tags") or []) and all(any(x.get("value") == TAG for x in t.get("conditions") or [])
                                               for t in trs2 if t.get("type") == "customer_reply")
    print("depois:", c2.get("tags"), [(t.get("active"), [x.get("value") for x in t.get("conditions") or []]) for t in trs2],
          "status", w.get("status"))
    print("OK" if ok else "DIFERENTE")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
