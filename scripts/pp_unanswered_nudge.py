#!/usr/bin/env python3
"""One-off reminder to the account's owner for every conversation still waiting on a reply (Ed, call 16/11: "for Stay
Fresh pools, anything they didn't respond to in the last 10–11 days"; only that account).

Finds conversations whose LAST message is inbound (SMS / call / email / chat from the contact, not a Google review)
since --days ago, skipping contacts tagged spam / dnd / zz test. For each, an internal SMS goes to --user (nothing goes
to the contact): a temporary workflow "Unanswered - Reminder to Owner (one-off)" with one internal notification step,
contacts added through the API, then the workflow goes back to draft.

  python3 scripts/pp_unanswered_nudge.py --only "Stay Fresh" --user Kris --days 11            # plan
  python3 scripts/pp_unanswered_nudge.py --only "Stay Fresh" --user Kris --days 11 --apply    # send + check delivery
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import uuid

from _common import ROOT, Agency, load_dotenv, select, slugify
from cli_anything.gohighlevel.utils.agency import BACKEND, SERVICES

NAME = "Unanswered - Reminder to Owner (one-off)"
SKIP = {"spam", "dnd", "zz test", "spam contact"}
BODY = ("⏰ Still waiting on a reply\n\n{{contact.name}} ({{contact.phone}}) messaged {{location.name}} and hasn't "
        "gotten an answer yet.\n\nOpen Conversations in the app to reply.")


def waiting(a: Agency, loc: str, days: int) -> list[dict]:
    since = (time.time() - days * 86400) * 1000
    out = []
    r = a.get(SERVICES, "/conversations/search", {"locationId": loc, "limit": 100, "sort": "desc", "sortBy": "last_message_date"})
    for c in r.get("conversations", []):
        if (c.get("lastMessageDate") or 0) < since:
            break
        if c.get("lastMessageDirection") != "inbound" or c.get("lastMessageType") == "TYPE_REVIEW" or not c.get("contactId"):
            continue
        if SKIP & {t.lower() for t in (c.get("tags") or [])}:
            continue
        out.append(c)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", required=True)
    ap.add_argument("--user", required=True)
    ap.add_argument("--days", type=int, default=11)
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    load_dotenv()
    a = Agency()
    l = select(a.locations(), [args.only], False, False)[0]
    loc, nm = l["id"], l["name"].strip()
    user = next((u for u in a.users(loc) if args.user.lower() in (u.get("name") or "").lower()), None)
    if not user or not user.get("phone"):
        sys.exit(f"user '{args.user}' not found or without phone")
    cs = waiting(a, loc, args.days)
    print(f"{nm}: {len(cs)} waiting on a reply → reminder to {user['name']} {user['phone']}")
    for c in cs:
        print(f"   {time.strftime('%m-%d %H:%M', time.gmtime(c['lastMessageDate'] / 1000))} {c.get('fullName') or c.get('phone')}"
              f" [{c.get('lastMessageType')}] {(c.get('lastMessageBody') or '')[:60]!r}")
    if not args.apply or not cs:
        return 0
    d = ROOT / "backup" / slugify(nm)
    d.mkdir(parents=True, exist_ok=True)
    (d / f"unanswered-nudge-{time.strftime('%Y%m%d-%H%M%S')}.json").write_text(json.dumps(cs, indent=1))
    r = a.call("POST", BACKEND, f"/workflow/{loc}", body={"name": NAME, "status": "draft"})
    wid = r.get("id") or r.get("_id")
    step = {"id": str(uuid.uuid4()), "order": 0, "name": "Text Owner - Unanswered",
            "type": "internal_notification", "attributes": {"type": "sms", "sms": {
                "body": BODY, "userType": "user", "selectedUser": [user["id"]], "attachments": []}}}
    a.call("PUT", BACKEND, f"/workflow/{loc}/{wid}", body={"name": NAME, "version": 1, "status": "published",
                                                           "allowMultiple": True, "workflowData": {"templates": [step]}})
    time.sleep(5)
    for c in cs:
        a.call("POST", SERVICES, f"/contacts/{c['contactId']}/workflow/{wid}", body={})
        time.sleep(2)
    print(f"   workflow {wid} published, {len(cs)} contacts added; checking delivery…")
    time.sleep(60)
    # the internal SMS shows up in the conversation of the user's phone (CLAUDE.md)
    digits = "".join(ch for ch in user["phone"] if ch.isdigit())[-10:]
    sent = 0
    r = a.get(SERVICES, "/conversations/search", {"locationId": loc, "query": digits, "limit": 5})
    for conv in r.get("conversations", []):
        m = a.get(SERVICES, f"/conversations/{conv['id']}/messages", {"limit": 20}).get("messages", {})
        for x in (m.get("messages") if isinstance(m, dict) else m) or []:
            if "Still waiting on a reply" in (x.get("body") or "") and x.get("dateAdded", "") >= time.strftime("%Y-%m-%d", time.gmtime()):
                sent += 1
                print(f"   ✓ {x.get('status')} {x.get('dateAdded')} {(x.get('body') or '')[30:90]!r}")
    live = a.workflow(loc, wid)
    a.call("PUT", BACKEND, f"/workflow/{loc}/{wid}", body={"name": NAME, "version": live.get("version", 2), "status": "draft",
                                                           "allowMultiple": True, "workflowData": live["workflowData"]})
    print(f"   {sent}/{len(cs)} reminders found in {user['name']}'s conversation; workflow back to draft")
    return 0 if sent == len(cs) else 1


if __name__ == "__main__":
    raise SystemExit(main())
