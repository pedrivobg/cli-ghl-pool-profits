#!/usr/bin/env python3
"""The Pool Keepers in BurchTech (live client account): after the Pool Profits snapshot was loaded (21/10), point what
came from the Pool Profits account at this one. Everything here stays in DRAFT (publishing is agreed with Frank/Nathan).

    set -a; . <scratchpad>/burchtech.env; set +a
    ./.venv/bin/python scripts/pk_bt_adjust.py            # plan
    ./.venv/bin/python scripts/pk_bt_adjust.py --apply

- Nathan (the representative) where the Pool Profits account had its own Nathan: "New Lead SMS" of Website Form Fill
  (came empty, the user doesn't exist here) and "Contact Created -> add owner" (old user id).
- "Notify Team - Negative Feedback" (Review Request) goes to Nathan instead of "all users": here "all" is 8 people,
  BurchTech staff included.
- The 2 calendars the snapshot brought (Pool Service Estimate / Appointment) get Nathan as staff (no staff = no slots);
  they stay inactive. The calendar PUT resets slotInterval, so the current value is sent with it.
Only our 28 workflows are touched (never the client's own); GET + backup before each write.
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
import time

from _common import ROOT, load_dotenv

from cli_anything.gohighlevel.utils.agency import BACKEND, SERVICES, Agency

LOC = "KjLd769fprQ2EaBI9Cro"
NATHAN, OLD_NATHAN = "8eLpUBJkMq5GTZy264Cu", "Yij3Wg088AYE7oNX7Bse"  # here / in the Pool Profits account
CALENDARS = ["3C7K5jP6MY6waSfV9LIJ", "mEHywDIvNVUJXqiZB3x6"]
BDIR = ROOT / "backup" / "the-pool-keepers"


def fix(name: str, tpl: list[dict]) -> list[str]:
    done = []
    for s in tpl:
        a = s.get("attributes") or {}
        if name == "Website Form Fill To Pipeline" and s["name"] == "New Lead SMS" and not a["sms"].get("selectedUser"):
            a["sms"].update({"userType": "user", "selectedUser": [NATHAN]})
            done.append("New Lead SMS → Nathan")
        if name == "Contact Created -> add owner" and s["type"] == "assign_user" and OLD_NATHAN in a.get("user_list", []):
            a["user_list"] = [NATHAN if u == OLD_NATHAN else u for u in a["user_list"]]
            done.append("dono do contato → Nathan")
        if name == "Review Request" and s["name"] == "Notify Team - Negative Feedback" and a["sms"].get("userType") == "all":
            a["sms"].update({"userType": "user", "selectedUser": [NATHAN]})
            done.append("aviso de nota baixa → Nathan (era todos os usuários)")
    return done


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    load_dotenv()
    a = Agency()
    if a.location(LOC)["name"] != "The Pool Keepers" or a.company_id() != "syjenoyGz1jZ3ndDPkCm":
        sys.exit("token/sub-conta errados (carregar burchtech.env)")
    if NATHAN not in {u["id"] for u in a.users(LOC)}:
        sys.exit("Nathan não é usuário aqui")
    BDIR.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    for w in a.workflows(LOC):
        if w["name"] not in ("Website Form Fill To Pipeline", "Contact Created -> add owner", "Review Request"):
            continue
        live = a.workflow(LOC, w["id"])
        if live["status"] != "draft":
            sys.exit(f"{w['name']} não está em draft: parar e conferir")
        tpl = copy.deepcopy(live["workflowData"]["templates"])
        done = fix(w["name"], tpl)
        print(f"   {w['name']}: {', '.join(done) or 'já está'}")
        if done and args.apply:
            (BDIR / f"burchtech-workflow-{w['id']}-{stamp}.json").write_text(json.dumps(live))
            a.call("PUT", BACKEND, f"/workflow/{LOC}/{w['id']}", body={
                "name": live["name"], "version": live.get("version", 1), "status": "draft",
                "parentId": live.get("parentId"), "workflowData": {"templates": tpl}})
    for cid in CALENDARS:
        cal = a.call("GET", SERVICES, f"/calendars/{cid}")
        cal = cal.get("calendar", cal)
        if any(m.get("userId") == NATHAN for m in cal.get("teamMembers") or []):
            print(f"   calendário {cal['name']}: já tem o Nathan")
            continue
        print(f"   calendário {cal['name']}: + Nathan (continua {'ativo' if cal.get('isActive') else 'inativo'})")
        if args.apply:
            (BDIR / f"burchtech-calendar-{cid}-{stamp}.json").write_text(json.dumps(cal))
            a.call("PUT", SERVICES, f"/calendars/{cid}", body={
                "teamMembers": [{"userId": NATHAN, "priority": 0.5, "selected": True, "isZoomAdded": "false",
                                 "zoomOauthId": "", "locationConfigurations": [
                                     {"kind": "custom", "location": "", "position": 0, "zoomOauthId": ""}]}],
                "slotInterval": cal.get("slotInterval")})
    return 0


if __name__ == "__main__":
    sys.exit(main())
