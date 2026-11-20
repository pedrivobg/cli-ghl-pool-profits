#!/usr/bin/env python3
"""Add one more person to the team alerts of an account (Frank 20/11: Passion, Brad gets the lead alerts too).

For every PUBLISHED workflow of the location:
  - each internal SMS to a typed number (`custom_sms`, to == --match-phone) gets a copy right after it to --phone;
  - each internal e-mail to a typed address (`custom_email`, to == --match-email) gets a copy right after it to --email;
  - each internal SMS to users (`userType: user`) that has --match-user gets --user added to selectedUser.
Nothing else changes (same text, same branch; the copy is linked mid-chain: parentKey = original, next = original's
next). Already there = skipped, so it can run twice. Backup of every workflow before the PUT.

  python3 scripts/pp_add_alert_recipient.py plan  --loc d03SMzI37dxTBeuoTJ13 --match-phone "+1 615-624-7624" \
      --phone "+1 615-427-9882" --match-email passionpoolcare@gmail.com --email bradlydixon@gmail.com \
      --match-user GVVbliQtPcq9CQPSM3Bj --user nHQZ7Ym3M6lTngLvNC4q --label Brad
  python3 scripts/pp_add_alert_recipient.py apply ...
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import re
import sys
import time
import uuid

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
from cli_anything.gohighlevel.utils.agency import BACKEND, Agency, slugify  # noqa: E402


def digits(s: str | None) -> str:
    return re.sub(r"\D", "", s or "")[-10:]


def plan_workflow(tpl: list[dict], args) -> tuple[list[dict], list[str]]:
    out = copy.deepcopy(tpl)
    by_id = {s["id"]: s for s in out}
    notes: list[str] = []
    for s in list(out):
        if s.get("type") != "internal_notification":
            continue
        at = s.get("attributes", {})
        kind, new_at = None, None
        sms, em = at.get("sms") or {}, at.get("email") or {}
        if at.get("type") == "sms" and sms.get("userType") == "custom_sms" and args.phone \
                and digits(sms.get("to")) == digits(args.match_phone):
            twin = any(x.get("attributes", {}).get("sms", {}).get("to") and
                       digits(x["attributes"]["sms"]["to"]) == digits(args.phone) for x in out)
            if not twin:
                kind = "sms"
                new_at = copy.deepcopy(at)
                new_at["sms"]["to"] = args.phone
        elif at.get("type") == "email" and em.get("userType") == "custom_email" and args.email \
                and (em.get("to") or "").lower() == (args.match_email or "").lower():
            twin = any((x.get("attributes", {}).get("email") or {}).get("to", "").lower() == args.email.lower()
                       and (x["attributes"]["email"].get("subject") == em.get("subject")) for x in out)
            if not twin:
                kind = "email"
                new_at = copy.deepcopy(at)
                new_at["email"]["to"] = args.email
        elif at.get("type") == "sms" and sms.get("userType") == "user" and args.user \
                and args.match_user in (sms.get("selectedUser") or []) and args.user not in sms["selectedUser"]:
            sms["selectedUser"].append(args.user)
            notes.append(f"  + {args.label} in users of '{s.get('name')}'")
            continue
        if not kind:
            continue
        nid = str(uuid.uuid4())
        new = {k: copy.deepcopy(v) for k, v in s.items() if k not in ("id", "next", "parentKey", "attributes")}
        new.update({"id": nid, "name": f"{s.get('name')} - {args.label}", "attributes": new_at, "parentKey": s["id"]})
        nxt = s.get("next")
        if nxt:
            new["next"] = nxt
            if isinstance(nxt, str) and nxt in by_id and by_id[nxt].get("parentKey") == s["id"]:
                by_id[nxt]["parentKey"] = nid
        s["next"] = nid
        out.insert(out.index(s) + 1, new)
        by_id[nid] = new
        notes.append(f"  + {kind} copy '{new['name']}' after '{s.get('name')}'")
    ids = {s["id"] for s in out}
    refs = [r for s in out for r in ([s.get("next")] if isinstance(s.get("next"), str) else s.get("next") or [])]
    refs += [s[k] for s in out for k in ("parent", "parentKey") if s.get(k)]
    if not all(r in ids for r in refs):
        raise SystemExit("dangling next/parent after insert — not saving")
    return out, notes


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("mode", choices=["plan", "apply"])
    p.add_argument("--loc", required=True)
    p.add_argument("--match-phone"); p.add_argument("--phone")
    p.add_argument("--match-email"); p.add_argument("--email")
    p.add_argument("--match-user"); p.add_argument("--user")
    p.add_argument("--label", default="extra")
    args = p.parse_args()
    a = Agency()
    loc_name = a.location(args.loc).get("name", args.loc)
    bdir = os.path.join(ROOT, "backup", slugify(loc_name))
    os.makedirs(bdir, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    print(f"== {loc_name}")
    for w in a.workflows(args.loc):
        if w.get("status") != "published":
            continue
        live = a.workflow(args.loc, w["id"])
        tpl = live.get("workflowData", {}).get("templates", [])
        new, notes = plan_workflow(tpl, args)
        if not notes:
            continue
        print(f"- {w['name']}"); print("\n".join(notes))
        if args.mode == "apply":
            with open(os.path.join(bdir, f"workflow-{w['id']}-{stamp}.json"), "w") as f:
                json.dump(live, f)
            a.call("PUT", BACKEND, f"/workflow/{args.loc}/{w['id']}", body={
                "name": live["name"], "version": live.get("version", 1), "status": live["status"],
                "parentId": live.get("parentId"), "allowMultiple": live.get("allowMultiple", False),
                "workflowData": {"templates": new}})
            print("  saved")


if __name__ == "__main__":
    main()
