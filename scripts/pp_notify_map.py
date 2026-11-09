#!/usr/bin/env python3
"""Who gets notified in a sub-account, live (read-only): phone lines (forwarding / IVR / ring users), users, and every
step of every PUBLISHED workflow that reaches a person (internal SMS/e-mail, tasks, assignment), with the recipient.

    ./.venv/bin/python scripts/pp_notify_map.py <locationId> [...]   (GHL_AGENCY=poolduck for Pool Duck accounts)
"""
from __future__ import annotations

import json
import sys

from _common import Agency, load_dotenv
from cli_anything.gohighlevel.utils.agency import SERVICES


def walk(steps):
    for s in steps or []:
        yield s
        for k in ("branches", "next", "children"):
            v = s.get(k)
            if isinstance(v, list) and v and isinstance(v[0], dict):
                yield from walk(v)


def recip(s, users):
    at, t = s.get("attributes") or {}, s.get("type")
    name = lambda ids: ", ".join(users.get(i, f"?{i}") for i in (ids if isinstance(ids, list) else [ids]) if i) or "—"
    if t == "internal_notification":
        kind = at.get("type")
        sub = at.get(kind) or {}
        ut = sub.get("userType")
        if ut == "user":
            return f"{kind} → user {name(sub.get('selectedUser') or [])}"
        if ut in ("custom_email", "custom_phone", "custom"):
            return f"{kind} → {sub.get('to') or sub.get('phone') or sub.get('customPhone') or sub.get('customEmail')}"
        return f"{kind} → {ut}: {json.dumps({k: v for k, v in sub.items() if k in ('to', 'phone', 'selectedUser')})}"
    if t in ("task-notification", "task_notification", "add_task", "task"):
        return f"task → {name(at.get('assignedTo') or at.get('assigned_to') or [])}"
    if t in ("assign_user",):
        return f"assign → {name(at.get('user_list') or at.get('userList') or at.get('users') or [])}"
    if t == "ivr_connect_call":
        return f"ivr connect → users {name(at.get('users') or [])} numbers {[n.get('phone') for n in at.get('customNumbers') or []]}"
    return None


def main(locs):
    load_dotenv()
    a = Agency()
    for loc in locs:
        L = a.location(loc)
        print(f"\n######## {L.get('name')} ({loc}) tz={L.get('timezone')} missedText={L.get('enableMissedCallText')}")
        users = {}
        for u in a.users(loc):
            users[u["id"]] = u.get("name") or f"{u.get('firstName')} {u.get('lastName')}"
            print(f"  user {u['id']} {users[u['id']]} <{u.get('email')}> {u.get('phone')} role={(u.get('roles') or {}).get('role')}")
        for n in a.call("GET", SERVICES, f"/phone-system/numbers/location/{loc}").get("numbers", []):
            print(f"  line {n.get('phoneNumber')} {n.get('friendlyName')!r} fwd={n.get('forwardingNumber')} "
                  f"inbound={n.get('inboundCallService')} ring={n.get('ringAllUsers') or n.get('users')}")
        for w in a.workflows(loc):
            if w.get("status") != "published":
                continue
            wf = a.workflow(loc, w["id"])
            rows = [(s.get("name"), r) for s in walk(wf.get("workflowData", {}).get("templates") or wf.get("templates") or [])
                    if (r := recip(s, users))]
            if rows:
                print(f"  [{w.get('name')}]")
                for nm, r in rows:
                    print(f"     - {nm}: {r}")


if __name__ == "__main__":
    main(sys.argv[1:])
