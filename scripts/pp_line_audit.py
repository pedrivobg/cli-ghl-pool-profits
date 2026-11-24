#!/usr/bin/env python3
"""Every tracking line: does an inbound call become a card AND alert the business? (Ed 24/11). Read-only.

    python3 scripts/pp_line_audit.py [--only NAME] [--json out.json]
    GHL_AGENCY=poolduck python3 scripts/pp_line_audit.py

Per sub-account and phone number: the PUBLISHED workflows whose trigger fires on an inbound call to that number
(call_status with no inbound_number filter = every line; ivr_incoming_call bound to the number), split by answered
(completed) / missed (busy/no-answer/voicemail/canceled; with an IVR every call is "completed", the IVR's own
missed-call steps count). For each: creates a card (create_opportunity anywhere in the flow) and alerts someone
(internal_notification sms/email/app to a user, the contact owner or a number; a task does NOT count). Verdict per line: CARD+ALERT ok / no card / no alert / nothing.
"""
from __future__ import annotations

import argparse
import json
import time

from _common import Agency, load_dotenv
from cli_anything.gohighlevel.utils.agency import BACKEND

MISSED = {"busy", "no-answer", "voicemail", "canceled", "failed"}
SKIP = ("test", "snapshot", "sample", "master", "billing only", "nathan taylor", "portal", "franchising", "hq",
        "marketplace", "pool profits (sales)")


def retry(f, *a):
    for i in range(4):
        try:
            return f(*a)
        except Exception:  # noqa: BLE001
            if i == 3:
                raise
            time.sleep(3)


def flow_kind(tpl: list[dict]) -> tuple[bool, bool, list[str]]:
    card = any(s["type"] == "create_opportunity" for s in tpl)
    who = []
    for s in tpl:
        at = s.get("attributes") or {}
        if s["type"] == "internal_notification":
            k = at.get("type")
            sub = at.get(k) if isinstance(at.get(k), dict) else {}
            if sub.get("selectedUser") or sub.get("to") or sub.get("smsNumber") or sub.get("userType") in ("assign", "all"):
                who.append(k)
    return card, bool(who), who


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only")
    ap.add_argument("--json")
    args = ap.parse_args()
    load_dotenv()
    a = Agency()
    out = []
    for loc in sorted(a.locations(), key=lambda x: x["name"]):
        n = loc["name"]
        if args.only and args.only.lower() not in n.lower():
            continue
        if not args.only and any(s == n.lower() or n.lower().startswith(s) or f" {s}" in n.lower() for s in SKIP):
            continue
        lid = loc["id"]
        try:
            nums = [x["phoneNumber"] for x in retry(a.get, BACKEND, f"/phone-system/numbers/location/{lid}").get("numbers", [])]
        except Exception as e:  # noqa: BLE001
            print(f"== {n}: numbers ERR {str(e)[:80]}")
            continue
        if not nums:
            continue
        cover = {num: {"answered": [], "missed": []} for num in nums}
        for w in retry(a.workflows, lid):
            if w["status"] != "published":
                continue
            trs = [t for t in retry(a.triggers, lid, w["id"]) if not t.get("deleted") and t.get("active", True)]
            rel = [t for t in trs if t.get("type") in ("call_status", "ivr_incoming_call")]
            if not rel:
                continue
            tpl = retry(a.workflow, lid, w["id"])["workflowData"]["templates"]
            card, alert, _ = flow_kind(tpl)
            for t in rel:
                conds = t.get("conditions") or []
                if any(c.get("field") == "message.direction" and c.get("value") == "outbound" for c in conds):
                    continue
                lines = next((c.get("value") for c in conds if c.get("field") in ("inbound_number", "number")), None)
                lines = lines if isinstance(lines, list) else ([lines] if lines else nums)
                st = next((c.get("value") for c in conds if c.get("field") == "call_status"), None)
                st = set(st if isinstance(st, list) else [st] if st else [])
                kinds = ["answered", "missed"] if t["type"] == "ivr_incoming_call" or not st else \
                    (["answered"] if "completed" in st else []) + (["missed"] if st & MISSED else [])
                for num in lines:
                    if num in cover:
                        for k in kinds:
                            cover[num][k].append({"flow": w["name"], "card": card, "alert": alert, "ivr": t["type"] == "ivr_incoming_call"})
        print(f"== {n}")
        for num, c in cover.items():
            row = {"account": n, "line": num}
            for k in ("answered", "missed"):
                fl = c[k]
                row[k] = {"card": any(f["card"] for f in fl), "alert": any(f["alert"] for f in fl), "flows": [f["flow"] for f in fl]}
            def v(k):
                r = row[k]
                return ("CARD" if r["card"] else "no-card") + "+" + ("ALERT" if r["alert"] else "no-alert")
            bad = not all(row[k]["card"] and row[k]["alert"] for k in ("answered", "missed"))
            print(f"   {'!!' if bad else 'ok'} {num}  answered {v('answered'):17} missed {v('missed'):17} "
                  f"{sorted(set(row['answered']['flows'] + row['missed']['flows']))}")
            out.append(row)
    if args.json:
        json.dump(out, open(args.json, "w"), indent=1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
