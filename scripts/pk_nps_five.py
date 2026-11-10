#!/usr/bin/env python3
"""The Pool Keepers (BurchTech, live client account): only a 5-star rating gets the Google review request; anything
below 5 goes to the negative-feedback follow-up to Nathan (Nathan on the Zoom call, Frank DM 10/11/2026).

    set -a; . <scratchpad>/burchtech.env; set +a     # or GHL_AGENCY=burchtech
    ./.venv/bin/python scripts/pk_nps_five.py           # plan
    ./.venv/bin/python scripts/pk_nps_five.py --test    # ZZ TEST copy of the score check (tags only), score 4 and 5
    ./.venv/bin/python scripts/pk_nps_five.py --apply   # Review Request: "Low NPS Score Detected" = score != 5

Before: Low = score != 5 AND score != 4 (1-3 -> Nathan, 4-5 -> Google review). After: Low = score != 5.
Status is kept (Review Request is still DRAFT here; publishing is agreed with Frank/Nathan). GET + backup before PUT.
"""
from __future__ import annotations

import argparse
import copy
import json
import time
import uuid

from _common import ROOT, load_dotenv

from cli_anything.gohighlevel.utils.agency import BACKEND, SERVICES, Agency

LOC = "KjLd769fprQ2EaBI9Cro"
WID = "4a47d556-63da-4942-bc78-846fce367c1c"  # Review Request
SCORE = "6ud9cTZ3iua6Dy52f5ir"  # NPS Score (this account)
LOW = "Low NPS Score Detected"
BDIR = ROOT / "backup" / "the-pool-keepers"


def check_node(tpl: list[dict]) -> dict:
    return next(s for s in tpl if s["type"] == "if_else" and any(
        b.get("name") == LOW for b in (s.get("attributes") or {}).get("branches", [])))


def values(node: dict) -> list[tuple]:
    b = next(b for b in node["attributes"]["branches"] if b["name"] == LOW)
    return [(c["conditionOperator"], c.get("conditionValue")) for seg in b["segments"] for c in seg["conditions"]]


def five_only(node: dict) -> bool:
    """Keep only the `!= 5` condition of the Low branch. Returns True if something changed."""
    b = next(b for b in node["attributes"]["branches"] if b["name"] == LOW)
    changed = False
    for seg in b["segments"]:
        keep = [c for c in seg["conditions"] if not (c.get("conditionSubType") == SCORE
                                                      and c["conditionOperator"] == "!=" and c.get("conditionValue") != "5")]
        changed |= len(keep) != len(seg["conditions"])
        seg["conditions"] = keep
    return changed


def test(a: Agency, node: dict) -> int:
    """Copy of the score check alone: Low -> tag `zz nps low`, else -> `zz nps high`. Contacts with score 4 and 5."""
    root = copy.deepcopy(node)
    root.pop("parent", None)
    root.pop("parentKey", None)
    root["order"] = 0
    low_id, high_id = root["next"]
    steps = [root]
    for bid, tag in ((low_id, "zz nps low"), (high_id, "zz nps high")):
        tid = str(uuid.uuid4())
        steps.append({"id": bid, "parent": root["id"], "parentKey": root["id"], "order": 1, "type": "if_else",
                      "cat": "conditions", "name": LOW if bid == low_id else "High",
                      "nodeType": "branch-yes" if bid == low_id else "branch-no",
                      "attributes": {"if": False, "conditionName": "Condition", "operator": "and", "branches": []}
                      if bid == low_id else {"else": True},
                      "sibling": [high_id if bid == low_id else low_id], "next": tid})
        steps.append({"id": tid, "parent": bid, "parentKey": bid, "order": 0, "type": "add_contact_tag",
                      "name": f"TEST {tag}", "attributes": {"type": "add_contact_tag", "tags": [tag]}})
    name = "ZZ TEST NPS five-star check"
    wid, cids, bad = None, [], 0
    try:
        r = a.call("POST", BACKEND, f"/workflow/{LOC}", body={"name": name, "status": "draft"})
        wid = r.get("id") or r.get("_id")
        body = {"name": name, "version": 1, "status": "draft", "allowMultiple": True,
                "workflowData": {"templates": steps}}
        a.call("PUT", BACKEND, f"/workflow/{LOC}/{wid}", body=body)
        live = a.workflow(LOC, wid)
        a.call("PUT", BACKEND, f"/workflow/{LOC}/{wid}", body={**body, "status": "published",
               "version": live.get("version", 1), "workflowData": {"templates": live["workflowData"]["templates"]}})
        want = {"5": "zz nps high", "4": "zz nps low", "1": "zz nps low"}
        for score in want:
            c = a.call("POST", SERVICES, "/contacts/", body={
                "locationId": LOC, "firstName": "ZZ Test", "lastName": f"nps {score}",
                "email": f"zznps{score}-{int(time.time())}@example.com",
                "customFields": [{"id": SCORE, "field_value": score}]})["contact"]["id"]
            cids.append((score, c))
        time.sleep(3)
        for _, c in cids:
            a.call("POST", SERVICES, f"/contacts/{c}/workflow/{wid}", body={})
        t0 = time.time()
        got = {}
        while time.time() - t0 < 180 and len(got) < len(cids):
            time.sleep(10)
            for score, c in cids:
                tg = set(a.call("GET", SERVICES, f"/contacts/{c}")["contact"].get("tags") or [])
                hit = [t for t in tg if t.startswith("zz nps")]
                if hit:
                    got[score] = hit[0]
        for score, tag in want.items():
            ok = got.get(score) == tag
            bad += not ok
            print(f"   {'✓' if ok else '✗'} nota {score} -> {got.get(score)} (esperado {tag})")
    finally:
        for _, c in cids:
            a.call("DELETE", SERVICES, f"/contacts/{c}")
        if wid:
            live = a.workflow(LOC, wid)
            a.call("PUT", BACKEND, f"/workflow/{LOC}/{wid}", body={"name": name, "version": live.get("version", 1),
                   "status": "draft", "workflowData": {"templates": live["workflowData"]["templates"]}})
            a.call("DELETE", BACKEND, f"/workflow/{LOC}/{wid}")
        for t in a.tags(LOC):
            if t["name"].startswith("zz nps"):
                a.call("DELETE", SERVICES, f"/locations/{LOC}/tags/{t['id']}")
        print(f"   limpo (contatos, tags zz nps e {name} apagados)")
    return 1 if bad else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--test", action="store_true")
    args = ap.parse_args()
    load_dotenv()
    a = Agency()
    live = a.workflow(LOC, WID)
    tpl = copy.deepcopy(live["workflowData"]["templates"])
    node = check_node(tpl)
    print(f"Review Request ({WID}): status {live['status']}, re-entry {live.get('allowMultiple')}")
    print(f"   Low agora: {values(node)}")
    changed = five_only(node)
    print(f"   Low novo:  {values(node)}" + ("" if changed else " (já está assim)"))
    if args.test:
        return test(a, node)
    if not args.apply or not changed:
        return 0
    BDIR.mkdir(parents=True, exist_ok=True)
    (BDIR / f"workflow-{WID}-before-five-only-{time.strftime('%Y%m%d-%H%M%S')}.json").write_text(
        json.dumps({"workflow": live, "triggers": a.triggers(LOC, WID)}, ensure_ascii=False))
    a.call("PUT", BACKEND, f"/workflow/{LOC}/{WID}", body={
        "name": live["name"], "version": live.get("version", 1), "status": live["status"],
        "parentId": live.get("parentId"), "allowMultiple": live.get("allowMultiple"), "workflowData": {"templates": tpl}})
    time.sleep(4)
    now = a.workflow(LOC, WID)
    nv = values(check_node(now["workflowData"]["templates"]))
    same = len(now["workflowData"]["templates"]) == len(tpl)
    ok = nv == [("!=", "5")] and now["status"] == live["status"] and same
    print(f"{'✓' if ok else '✗'} gravado: Low {nv}, status {now['status']}, re-entry {now.get('allowMultiple')}, "
          f"{len(now['workflowData']['templates'])} nós")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
