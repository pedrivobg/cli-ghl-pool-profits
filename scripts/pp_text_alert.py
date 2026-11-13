#!/usr/bin/env python3
"""Owner gets a text for every SMS a contact sends to any of the account's numbers (Ed, 13/11, Sparkling Clear).

    python3 scripts/pp_text_alert.py --loc G9jACRTK8rh04j29ZTQf --user jNSBqifkH0ga5nr1NlRr            # plan
    python3 scripts/pp_text_alert.py --loc G9jACRTK8rh04j29ZTQf --user jNSBqifkH0ga5nr1NlRr --apply

Why: in the V9 a text straight to a tracking number only alerts someone in "SMS Customer Reply to pipeline", which
needs the `reactivation` tag (and goes to the contact owner, usually empty); "Incoming SMS To Pipeline" (older accounts)
makes a card with no alert. Owners who never open GHL miss text-only leads. This adds one published workflow:
Customer Replied (SMS, any number; filters Doesn't Have Tag spam / dnd) → internal SMS to the user, re-entry on.
New workflow only: nothing existing is touched, nothing is sent to contacts. Publishing on a client account = only
with Pedro's OK (the session classifier blocked the --apply on 13/11).
"""
from __future__ import annotations

import argparse
import time
import uuid

from _common import load_dotenv

from cli_anything.gohighlevel.utils.agency import BACKEND, Agency

NAME = "New Text - Alert Owner"
BODY = ("💬 NEW TEXT from {{contact.name}} {{contact.phone}}\n\n\"{{message.body}}\"\n\n"
        "Text or call them back. They texted your business line, not your cell.")
SKIP = ["spam", "dnd"]


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--loc", required=True)
    p.add_argument("--user", action="append", required=True, help="user id(s) that get the text")
    p.add_argument("--folder-of", default="Website Form Fill To Pipeline", help="put it in this workflow's folder")
    p.add_argument("--apply", action="store_true")
    args = p.parse_args()
    load_dotenv()
    a = Agency()
    loc = args.loc
    flows = {w["name"]: w for w in a.workflows(loc)}
    if NAME in flows:
        print(f"{NAME} já existe ({flows[NAME]['id']}, {flows[NAME].get('status')})")
        return 0
    print(f"+ {NAME}: SMS recebido (qualquer número, sem tag {SKIP}) → SMS interno para {args.user}")
    if not args.apply:
        return 0
    parent = a.workflow(loc, flows[args.folder_of]["id"]).get("parentId") if args.folder_of in flows else None
    res = a.call("POST", BACKEND, f"/workflow/{loc}", body={"name": NAME, "parentId": parent, "status": "draft"})
    wid = res.get("id") or res.get("_id")
    step = {"id": str(uuid.uuid4()), "order": 0, "name": "Text the owner", "type": "internal_notification",
            "attributes": {"type": "sms", "sms": {"body": BODY, "selectedUser": args.user, "userType": "user",
                                                    "attachments": []}}}
    a.call("PUT", BACKEND, f"/workflow/{loc}/{wid}", body={
        "name": NAME, "version": 1, "status": "published", "parentId": parent, "allowMultiple": True,
        "workflowData": {"templates": [step]}})
    conds = [{"field": "message.type", "operator": "==", "value": 2, "title": "Reply channel", "type": "select"}]
    conds += [{"field": "contact.tags", "id": "doesnot-have-tag", "title": "Doesn't Have Tag", "type": "select",
               "operator": "index-of-false", "value": t} for t in SKIP]
    trig = {"type": "customer_reply", "name": "Customer Replied", "masterType": "highlevel", "schedule_config": {},
            "conditions": conds, "actions": [{"workflow_id": wid, "type": "add_to_workflow"}], "workflowId": wid,
            "workflow_id": wid, "location_id": loc, "targetActionId": step["id"]}
    t = a.call("POST", BACKEND, f"/workflow/{loc}/trigger", body=trig)
    a.call("PUT", BACKEND, f"/workflow/{loc}/trigger/{t['id']}", body={**trig, "id": t["id"]})
    time.sleep(5)
    after = a.workflow(loc, wid)
    trs = [x for x in a.triggers(loc, wid) if not x.get("deleted")]
    st = after["workflowData"]["templates"]
    ok = after.get("status") == "published" and len(trs) == 1 and trs[0].get("active") and len(st) == 1 \
        and st[0]["attributes"]["sms"]["selectedUser"] == args.user and after.get("allowMultiple") is True
    print(f"{'✓' if ok else '✗ VERIFICAR'} {wid} {after.get('status')} re-entry={after.get('allowMultiple')} "
          f"gatilho={[(c['field'], c['value']) for c in trs[0]['conditions']] if trs else None}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
