#!/usr/bin/env python3
"""Pool Duck Wesley Chapel (Justin, meeting 19/11): Justin gets a text for every NEW lead, from any source, on top of
Debbie — not for every call/SMS.

    GHL_AGENCY=poolduck python3 scripts/pd_wc_lead_alerts.py            # plan
    GHL_AGENCY=poolduck python3 scripts/pd_wc_lead_alerts.py --apply

Before (live 19/11): Justin already in the FB form, Google Ads form and Google lead form texts and the chat widget
alert. Missing:
- "Website Form Fill To Pipeline": "New Lead SMS" only to Debbie (service@) → Justin added to selectedUser.
- "Answered/Missed Incoming Call To Pipeline" (main line, already inside "Not spam / not a customer?"): no text at all
  → a "New Lead SMS - Justin" right after the card is created (before the 1 h wait + task).
- FB / Google Ads / LSA call-in flows (tracking numbers, no guard): → at the end, an if/else (no spam, dnd,
  existing customer, pre-snapshot) with the "New Lead SMS - Justin" in the Lead branch.
Backup of each workflow in backup/pool-duck-wesley-chapel/<id>.json before the PUT. Repeat calls from the same lead
(not a customer yet) text again, as the form alerts do.
"""
from __future__ import annotations

import argparse
import json
import os

from _common import ROOT, Agency, load_dotenv
from pp_lead_alerts import guard_nodes, nid, put_workflow

LOC = "uJr8H2qaQM5ffZxeYFqn"
JUSTIN = "jvUZogU0flQa5usvpnpp"
SKIP = ["spam", "dnd", "existing customer", "pre-snapshot"]
FORM = "2bf53448-c4e3-4deb-b4e5-19b9a690f908"
MAIN = {"82786d9c-15f5-4beb-b0ca-d5d36b8c9593": "Inbound call (main line)",
        "00814c76-5116-4be4-ad46-435a6582ea2d": "Missed call (main line)"}
ADS = {"8362de90-22ee-4ff3-b526-488291cd6456": "Facebook ad call",
       "1b977a62-b7b4-4d3f-9411-601d207dc800": "Google Ads call",
       "fecf9aff-527d-4ed3-a92c-b5532f9134dd": "Google LSA call"}
NAME = "New Lead SMS - Justin"


def alert(source: str) -> dict:
    return {"id": nid(), "name": NAME, "type": "internal_notification", "attributes": {"type": "sms", "sms": {
        "body": f"\U0001f6a8 NEW LEAD - {source}\n\nName: {{{{contact.name}}}}\nPhone: {{{{contact.phone}}}}\n"
                f"Email: {{{{contact.email}}}}\nCity: {{{{contact.city}}}}\n\nSource: {source}",
        "selectedUser": [JUSTIN], "userType": "user", "attachments": []}}}


def chain(t: list[dict], start: dict) -> list[dict]:
    by = {s["id"]: s for s in t}
    out = [start]
    while isinstance(out[-1].get("next"), str) and out[-1]["next"] in by:
        out.append(by[out[-1]["next"]])
    return out


def after(t: list[dict], prev: dict, node: dict) -> None:
    """Insert node right after prev in the same branch; renumber the rest of that branch."""
    nxt = prev.get("next")
    node.update(parent=prev.get("parent"), parentKey=prev["id"], order=prev.get("order", 0) + 1)
    if nxt:
        node["next"] = nxt
        for s in t:
            if s["id"] == nxt:
                s["parentKey"] = node["id"]
        for s in chain(t, next(s for s in t if s["id"] == nxt)):
            s["order"] = s.get("order", 0) + 1
    prev["next"] = node["id"]
    t.append(node)


def build(wid: str, t: list[dict]) -> list[dict]:
    t = json.loads(json.dumps(t))
    if any(s.get("name") == NAME for s in t):
        return t
    if wid == FORM:
        s = next(s for s in t if s.get("name") == "New Lead SMS")
        s["attributes"]["sms"]["selectedUser"] = list(dict.fromkeys(s["attributes"]["sms"]["selectedUser"] + [JUSTIN]))
    elif wid in MAIN:
        after(t, next(s for s in t if s["type"] == "create_opportunity"), alert(MAIN[wid]))
    else:
        if any(s["type"] == "if_else" for s in t):
            raise SystemExit(f"{wid}: has if/else — not touching blindly")
        last = chain(t, next(s for s in t if not s.get("parentKey")))[-1]
        c, y, n = guard_nodes(last["id"], last.get("parent"), last.get("order", 0) + 1, SKIP)
        last["next"] = c["id"]
        a = alert(ADS[wid])
        a.update(parent=y["id"], parentKey=y["id"], order=0)
        y["next"] = a["id"]
        t += [c, y, n, a]
    ids = {s["id"] for s in t}
    for s in t:
        for r in ([s["next"]] if isinstance(s.get("next"), str) else s.get("next") or []) + \
                 [x for x in (s.get("parent"), s.get("parentKey")) if x]:
            if r not in ids:
                raise SystemExit(f"{wid}: dangling ref {r} in {s.get('name')}")
    return t


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    load_dotenv()
    a = Agency()
    bdir = os.path.join(ROOT, "backup", "pool-duck-wesley-chapel")
    os.makedirs(bdir, exist_ok=True)
    for wid in [FORM, *MAIN, *ADS]:
        live = a.workflow(LOC, wid)
        t = live["workflowData"]["templates"]
        new = build(wid, t)
        print(f"== {live['name']} ({live['status']}): {len(t)} → {len(new)} steps")
        for s in chain(new, next(s for s in new if not s.get("parentKey"))):
            print(f"     {s.get('order')} {s['type']:22} {s.get('name')}")
        for s in new:
            if s["type"] == "internal_notification":
                print(f"     alert '{s.get('name')}' → {s['attributes']['sms'].get('selectedUser')} (parent {str(s.get('parent'))[:8]})")
        if args.apply and new != t:
            json.dump(live, open(os.path.join(bdir, f"{wid}.json"), "w"), indent=1)
            put_workflow(a, LOC, wid, live, new)
            print("     saved")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
