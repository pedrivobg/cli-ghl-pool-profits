#!/usr/bin/env python3
"""Pool Duck (Pedro 23/11): every lead alert / task / owner in a PUBLISHED workflow goes to one user.

    GHL_AGENCY=poolduck python3 scripts/pd_alert_owner.py --loc <id> --email preston@poolduck.com [--apply]

Per published workflow: internal_notification (sms/email/app, userType user) → selectedUser [that user] (email to a
user → same); task-notification → assignedTo (unless it is the contact owner, contact.assigned_user); assign_user → user_list. Steps already sending to custom numbers/emails are
left alone. "... - Steve" flows (Steve left; their forms now feed Website Form Fill To Pipeline) → draft.
Backup in backup/<slug>/alert-owner-<stamp>/.
"""
from __future__ import annotations

import argparse
import json
import os
import time

from _common import ROOT, Agency, load_dotenv
from cli_anything.gohighlevel.utils.agency import BACKEND, slugify


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--loc", required=True)
    ap.add_argument("--email", required=True)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--only-empty", action="store_true", help="only steps with nobody selected (keep existing recipients)")
    args = ap.parse_args()
    load_dotenv()
    a = Agency()
    loc = next(l for l in a.locations() if l["id"] == args.loc)
    users = {u["id"]: u for u in a.users(args.loc)}
    me = next(u["id"] for u in users.values() if (u.get("email") or "").lower() == args.email.lower())
    bdir = os.path.join(ROOT, "backup", slugify(loc["name"]), f"alert-owner-{time.strftime('%Y%m%d-%H%M%S')}")
    for w in sorted(a.workflows(args.loc), key=lambda x: x["name"]):
        if w["status"] != "published":
            continue
        live = a.workflow(args.loc, w["id"])
        t = json.loads(json.dumps(live["workflowData"]["templates"]))
        if w["name"].endswith("- Steve") or w["name"].endswith("- STEVE"):
            print(f"   → draft: {w['name']}")
            if args.apply:
                os.makedirs(bdir, exist_ok=True)
                json.dump(live, open(os.path.join(bdir, f"{w['id']}.json"), "w"), indent=1)
                a.call("PUT", BACKEND, f"/workflow/{args.loc}/{w['id']}", body={**{k: live[k] for k in live if k not in ("_id", "createdAt", "updatedAt", "__v")}, "status": "draft"})
            continue
        changes = []
        for s in t:
            at = s.get("attributes") or {}
            if s["type"] == "internal_notification":
                k = at.get("type")
                sub = at.get(k) if isinstance(at.get(k), dict) else None
                if sub is not None and sub.get("userType") in ("user", None, "") and (sub.get("selectedUser") or []) != [me] \
                        and not (args.only_empty and sub.get("selectedUser")):
                    if sub.get("userType") in ("user", None, "") and not sub.get("to") and not sub.get("smsNumber"):
                        changes.append(f"{s.get('name')} ({k}) {[users.get(x, {}).get('name', x) for x in sub.get('selectedUser') or []]}")
                        sub.update(userType="user", selectedUser=[me])
            elif s["type"] == "task-notification" and at.get("assignedTo") != me and not (args.only_empty and at.get("assignedTo")) and not str(at.get("assignedTo") or "").startswith("contact."):
                changes.append(f"{s.get('name')} (task) {users.get(at.get('assignedTo'), {}).get('name', at.get('assignedTo'))}")
                at["assignedTo"] = me
            elif s["type"] == "assign_user" and (at.get("user_list") or []) != [me] and not (args.only_empty and at.get("user_list")):
                changes.append(f"{s.get('name')} (owner) {[users.get(x, {}).get('name', x) for x in at.get('user_list') or []]}")
                at["user_list"] = [me]
        if changes:
            print(f"   {w['name']}: " + " · ".join(changes) + " → " + users[me]["name"])
            if args.apply:
                os.makedirs(bdir, exist_ok=True)
                json.dump(live, open(os.path.join(bdir, f"{w['id']}.json"), "w"), indent=1)
                a.call("PUT", BACKEND, f"/workflow/{args.loc}/{w['id']}", body={**{k: live[k] for k in live if k not in ("_id", "createdAt", "updatedAt", "__v")}, "workflowData": {**live["workflowData"], "templates": t}})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
