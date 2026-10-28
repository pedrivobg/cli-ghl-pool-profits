#!/usr/bin/env python3
"""Clear Pool Solutions Tucson: review request timed by service type, stays in DRAFT (Derek's call, 27/10).

    ./.venv/bin/python scripts/cp_review_request.py plan
    ./.venv/bin/python scripts/cp_review_request.py apply

Pool Brain has no public "job completed" event (docs/poolbrain-review-integration.md), so the ask goes by time after the
Won stage. The account already has the snapshot's "Review Request" (draft): Won stage → wait → rating text (NPS form) →
5 = Google review link (email + SMS), lower = text to the team, no link. Only the timing changes:
- 🎉 Won Customer (weekly): 14 → 30 days after the stage (after a month of service);
- Won Customer – One Time Repair: 1 → 2 days (the job is done by then);
- + 6 months after the review request, the review SMS once more (Derek: "every 6 months"; GHL can't see who already
  left a review, so it is one repeat, not a loop);
- custom value "Google Review Link" (empty) → the account's own Google place.
Status stays draft; publishing is Derek's decision. GET + backup before the PUT.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import uuid

from _common import ROOT, load_dotenv
from pp_review_fix import REVIEW, read
from pp_source_tags import refs_ok

from cli_anything.gohighlevel.utils.agency import BACKEND, SERVICES, Agency

LOC = "ghUi89uCpNyNunNpbtAt"
FLOW = "Review Request"
WAITS = {"Won": 30, "One Time": 2}  # branch name → days before the rating text
REPEAT = "SMS - Review Request (6 months)"
BDIR = ROOT / "backup" / "clear-pool-solutions-tucson"


def retime(tpl: list[dict]) -> tuple[list[dict], list[str]]:
    out = json.loads(json.dumps(tpl))
    by = {s["id"]: s for s in out}
    notes = []
    for s in out:
        if s["type"] != "wait" or s.get("name") != "Wait Before NPS Request":
            continue
        branch = by[s["parent"]]["name"]
        days = WAITS[branch]
        if s["attributes"]["startAfter"]["value"] != days:
            notes.append(f"{branch}: {s['attributes']['startAfter']['value']} → {days} dias")
            s["attributes"]["startAfter"] = {"type": "days", "value": days, "when": "after"}
    if any(s.get("name") == REPEAT for s in out):
        return out, notes
    sms = next(s for s in out if s["type"] == "review_request" and s["attributes"].get("review_type") == "sms")
    wait = next(s for s in out if s.get("name") == "Wait Before NPS Request")
    w = {"id": str(uuid.uuid4()), "name": "Wait 6 months", "type": "wait", "parent": sms["parent"], "parentKey": sms["id"],
         "order": sms.get("order", 0) + 1,
         "attributes": {**json.loads(json.dumps(wait["attributes"])), "name": "Wait 6 months",
                        "startAfter": {"type": "days", "value": 182, "when": "after"}}}
    again = {"id": str(uuid.uuid4()), "name": REPEAT, "type": "review_request", "parent": sms["parent"], "parentKey": w["id"],
             "order": sms.get("order", 0) + 2, "attributes": json.loads(json.dumps(sms["attributes"]))}
    sms["next"], w["next"] = w["id"], again["id"]
    notes.append("+ espera 6 meses → SMS de review de novo (uma vez)")
    return [*out, w, again], notes


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("mode", choices=["plan", "apply"])
    args = parser.parse_args()
    load_dotenv()
    a = Agency()
    loc = a.location(LOC)
    if not loc["name"].startswith("Clear Pool Solutions"):
        sys.exit("sub-conta errada")
    wid = next(w["id"] for w in a.workflows(LOC) if w["name"] == FLOW)
    live = read(a, LOC, wid)
    trig = {t["id"] for t in a.triggers(LOC, wid) if not t.get("deleted")}
    refs = {c["conditionValue"] for s in live["workflowData"]["templates"] if s.get("nodeType") == "condition-node"
            for b in s["attributes"].get("branches", []) for g in b.get("segments", []) for c in g["conditions"]
            if c.get("conditionType") == "trigger"}
    if not refs <= trig:
        sys.exit(f"if/else por gatilho aponta para gatilho que não existe: {refs - trig}")
    tpl, notes = retime(live["workflowData"]["templates"])
    link = REVIEW + loc["googlePlacesId"]
    cv = next(c for c in a.call("GET", SERVICES, f"/locations/{LOC}/customValues")["customValues"] if c["name"] == "Google Review Link")
    if not cv.get("value"):
        notes.append(f"custom value Google Review Link: vazio → {link}")
    print(f"   {FLOW} ({live['status']}):", *notes or ["já feito"], sep="\n      ")
    if args.mode != "apply" or not notes:
        return 0
    BDIR.mkdir(parents=True, exist_ok=True)
    (BDIR / f"workflow-{wid}-{time.strftime('%Y%m%d-%H%M%S')}.json").write_text(json.dumps(live))
    a.call("PUT", BACKEND, f"/workflow/{LOC}/{wid}", body={"name": live["name"], "version": live.get("version", 1),
                                                         "status": "draft", "parentId": live.get("parentId"),
                                                         "workflowData": {"templates": tpl}})
    if not cv.get("value"):
        (BDIR / f"customvalue-{cv['id']}.json").write_text(json.dumps(cv))
        a.call("PUT", SERVICES, f"/locations/{LOC}/customValues/{cv['id']}", body={"name": cv["name"], "value": link})
    time.sleep(3)
    got = read(a, LOC, wid)
    t = got["workflowData"]["templates"]
    waits = {s["attributes"]["startAfter"]["value"] for s in t if s.get("name") == "Wait Before NPS Request"}
    ok = refs_ok(t) and got["status"] == "draft" and waits == set(WAITS.values()) and any(s.get("name") == REPEAT for s in t)
    print(f"      {'✓' if ok else '✗ VERIFICAR'} {got['status']} · esperas {sorted(waits)}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
