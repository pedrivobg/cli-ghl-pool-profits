#!/usr/bin/env python3
"""Poolheads: Felipe first for 25 s, then George's LeadConnector app for 20 s, then the voicemail (Frank asked Felipe
16/11; Felipe 17/11: "For George can we have him to receive calls to the app instead?").

    ./.venv/bin/python scripts/ph_george_routing.py          # plan
    ./.venv/bin/python scripts/ph_george_routing.py --apply  # GET + backup + PUT + re-read

Edits the published "Business Hours Call Routing" IVR in place (only Mon–Fri 9–5 branch):
"Ring the team" (Felipe app + cell) timeout 20 → 25; in its "Not answered" branch a new "Ring George" (users: George,
no custom number = app only) 20 s + "George answered?" — not answered → the same tag `missed call` + voicemail as
before; answered → end. Closed branch untouched. Idempotent (skips if "Ring George" exists).
"""
from __future__ import annotations

import argparse
import copy
import json
import time

from _common import ROOT, load_dotenv
from pp_ivr import nid

from cli_anything.gohighlevel.utils.agency import BACKEND, Agency

LOC = "PeUynYCMm8e6PJMy785O"
WID = "4bdf1654-e687-4f8d-9629-5b34c5f82d91"
GEORGE = "AiGubuOkSiQF2XYwkVJD"
FELIPE_S, GEORGE_S, GEORGE_IDX = 25, 20, 5


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--apply", action="store_true")
    args = p.parse_args()
    load_dotenv()
    a = Agency()
    wf = a.workflow(LOC, WID)
    tpl = wf["workflowData"]["templates"]
    by = {s["name"]: s for s in tpl if s["name"] not in ("Tag missed call", "Record voicemail")}
    if "Ring George" in by:
        print("Ring George já existe — nada a fazer")
        return 0
    ring, answered_q = by["Ring the team"], by["Answered?"]
    not_ans = next(s for s in tpl if s["id"] == answered_q["next"][0])
    tag = next(s for s in tpl if s["id"] == not_ans["next"])
    assert tag["type"] == "add_contact_tag" and ring["attributes"]["timeout"] == 20
    new = copy.deepcopy(tpl)
    idx = {s["id"]: s for s in new}
    idx[ring["id"]]["attributes"]["timeout"] = FELIPE_S

    rg = {"id": nid(), "name": "Ring George", "type": "ivr_connect_call", "stepIndex": GEORGE_IDX, "order": 0,
          "parent": not_ans["id"], "parentKey": not_ans["id"],
          "attributes": {**copy.deepcopy(ring["attributes"]), "timeout": GEORGE_S, "users": [GEORGE], "customNumbers": []}}
    q2, n2, y2 = nid(), nid(), nid()
    cond = copy.deepcopy(answered_q["attributes"])
    br = cond["branches"][0]
    br["id"], br["name"] = n2, "Not answered"
    for seg in br["segments"]:
        seg["__segmentId"] = nid()
        for c in seg["conditions"]:
            c["__conditionId"], c["conditionSubType"] = nid(), f"{GEORGE_IDX}.dialCallStatus"
    gq = {"id": q2, "name": "George answered?", "type": "if_else", "cat": "conditions", "comments": [],
          "nodeType": "condition-node", "next": [n2, y2], "order": 1, "parent": rg["id"], "parentKey": rg["id"],
          "attributes": cond}
    rg["next"] = q2
    nb = {"id": n2, "name": "Not answered", "type": "if_else", "parent": q2, "parentKey": q2, "cat": "conditions",
          "sibling": [y2], "comments": [], "nodeType": "branch-yes", "order": 2, "next": tag["id"],
          "attributes": {"if": False, "conditionName": "Condition", "operator": "and", "branches": []}}
    yb = {"id": y2, "name": "Answered", "type": "if_else", "parent": q2, "parentKey": q2, "cat": "conditions",
          "sibling": [n2], "comments": [], "nodeType": "branch-no", "order": 2, "attributes": {"else": True}}
    idx[not_ans["id"]]["next"] = rg["id"]
    idx[tag["id"]]["parent"] = idx[tag["id"]]["parentKey"] = n2
    pos = next(i for i, s in enumerate(new) if s["id"] == tag["id"])
    new[pos:pos] = [rg, gq, nb, yb]
    print(f"Felipe {ring['attributes']['timeout']}→{FELIPE_S}s · + Ring George ({GEORGE}) {GEORGE_S}s app · "
          f"não atendeu → tag + caixa postal (como antes) · status {wf['status']}")
    if not args.apply:
        return 0
    bdir = ROOT / "backup" / "poolheads"
    bdir.mkdir(parents=True, exist_ok=True)
    bfile = bdir / f"{WID}-george-{time.strftime('%Y%m%d-%H%M%S')}.json"
    bfile.write_text(json.dumps(wf, indent=1))
    a.call("PUT", BACKEND, f"/workflow/{LOC}/{WID}", body={
        "name": wf["name"], "version": wf.get("version", 1), "status": wf["status"], "parentId": wf.get("parentId"),
        "workflowData": {"templates": new}})
    time.sleep(5)
    got = a.workflow(LOC, WID)
    g = {s["name"]: s for s in got["workflowData"]["templates"]}
    ok = "Ring George" in g and g["Ring the team"]["attributes"]["timeout"] == FELIPE_S \
        and g["Ring George"]["attributes"]["users"] == [GEORGE] and got["status"] == wf["status"]
    print(f"{'✓' if ok else '✗ VERIFICAR'} backup {bfile.name} · status {got['status']} · {len(got['workflowData']['templates'])} passos")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
