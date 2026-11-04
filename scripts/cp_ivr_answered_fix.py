#!/usr/bin/env python3
"""Clear Pool Tucson: answered calls were handled as missed (Derek via Frank, 04/11).

    ./.venv/bin/python scripts/cp_ivr_answered_fix.py plan
    ./.venv/bin/python scripts/cp_ivr_answered_fix.py test --to pedro@poolprofits.com
    ./.venv/bin/python scripts/cp_ivr_answered_fix.py apply

Since 27/10 ("no press 1") the IVR starts with two plain steps (remove `ivr call missed`, tag `ivr pressed 1`) before
"Connect call". The IVR engine starts at the first IVR step, so those two never run: no caller gets `ivr pressed 1`, and
"Route the call" in the 3 call workflows sent every non-spam, non-customer call to "Didn't press 1" = missed (text to the
caller, card, task, alert). 29/10, 02/11 and 04/11: answered calls (IVR status completed, 34-46 s) all got the text.
`ivr call missed` comes from the IVR's "not answered" branch (after Connect call), which does run.

Fix: in "Route the call" the "Pressed 1" branch (renamed "Reached Derek's phone") takes every caller left after spam/DND
and current customer (condition: doesn't have tag `spam`); inside it "Did Derek answer?" (`ivr call missed`) decides.
Nothing else changes (step ids, triggers, re-entry). A caller who hangs up while it's still ringing (< 10 s) has no
`ivr call missed` and counts as answered (no text; the 1 h "How was the call" task still reminds Derek).
test: copies (no Google Ads conversion, internal texts removed, internal emails to --to), contacts: answered (no IVR tag),
not answered, spam, customer answered/missed; checks tags/cards/tasks; deletes everything.
"""
from __future__ import annotations

import argparse
import json
import sys
import time

from _common import ROOT, load_dotenv
from ps_ads_forms import cond
from pp_review_fix import read
from pp_source_tags import fresh_ids, refs_ok

from cli_anything.gohighlevel.utils.agency import BACKEND, SERVICES, Agency

LOC = "ghUi89uCpNyNunNpbtAt"
FLOWS = ["AdWords Call In - New Lead", "Incoming Call To Pipeline", "Incoming Email follow-up"]
PRESSED, MISSED_IVR, TEXTED = "ivr pressed 1", "ivr call missed", "missed call text 24h"
NEW_NAME = "Reached Derek's phone"
BDIR = ROOT / "backup" / "clear-pool-solutions-tucson"


def fix(tpl: list[dict]) -> list[dict] | None:
    out = json.loads(json.dumps(tpl))
    route = next(s for s in out if s.get("name") == "Route the call" and s.get("nodeType") == "condition-node")
    br = next((b for b in route["attributes"]["branches"] if b["name"] in ("Pressed 1", NEW_NAME)), None)
    if br is None or br["name"] == NEW_NAME:
        return None
    br["name"] = NEW_NAME
    br["segments"] = [{"__segmentId": br["segments"][0]["__segmentId"], "operator": "or",
                       "conditions": [cond("tags", "index-of-false", ["spam"])]}]
    node = next(s for s in out if s["id"] == br["id"])
    node["name"] = NEW_NAME
    return out


def for_test(tpl: list[dict], to: str) -> list[dict]:
    """Copy for the test: no conversion, no internal text to Derek, internal emails to `to`."""
    out = json.loads(json.dumps(tpl))
    drop = [s for s in out if s["type"] == "google_adword"
            or (s["type"] == "internal_notification" and s["attributes"].get("type") == "sms")]
    for s in drop:
        out = unlink(out, s["id"])
    for s in out:
        if s["type"] == "internal_notification" and s["attributes"].get("type") == "email":
            s["attributes"]["email"]["to"] = to
    return fresh_ids(out)


def unlink(tpl: list[dict], sid: str) -> list[dict]:
    by = {s["id"]: s for s in tpl}
    gone = by.pop(sid)
    nxt = gone.get("next")
    for s in by.values():
        if s.get("next") == sid:
            s["next"] = nxt
    if isinstance(nxt, str) and nxt in by:
        by[nxt]["parentKey"] = gone.get("parentKey")
    return list(by.values())


def put(a: Agency, wid: str, live: dict, tpl: list[dict]) -> dict:
    BDIR.mkdir(parents=True, exist_ok=True)
    (BDIR / f"workflow-{wid}-{time.strftime('%Y%m%d-%H%M%S')}.json").write_text(json.dumps(live))
    a.call("PUT", BACKEND, f"/workflow/{LOC}/{wid}", body={"name": live["name"], "version": live.get("version", 1),
                                                         "status": live["status"], "parentId": live.get("parentId"),
                                                         "workflowData": {"templates": tpl}})
    time.sleep(2)
    return read(a, LOC, wid)


def test(a: Agency, flows: dict, to: str) -> int:
    stamp, bad = int(time.time()), 0
    cases = {"answered": [], "not answered": [MISSED_IVR], "spam": ["spam"],
             "customer answered": ["current customer"], "customer missed": ["current customer", MISSED_IVR]}
    for name in FLOWS:
        live = read(a, LOC, flows[name])
        tpl = for_test(fix(live["workflowData"]["templates"]) or live["workflowData"]["templates"], to)
        res = a.call("POST", BACKEND, f"/workflow/{LOC}", body={"name": f"ZZ TEST {name}", "status": "draft"})
        wid = res.get("id") or res.get("_id")
        body = {"name": f"ZZ TEST {name}", "version": 1, "status": "draft", "allowMultiple": True,
                "workflowData": {"templates": tpl}}
        a.call("PUT", BACKEND, f"/workflow/{LOC}/{wid}", body=body)
        cur = a.workflow(LOC, wid)
        a.call("PUT", BACKEND, f"/workflow/{LOC}/{wid}", body={**body, "status": "published", "version": cur.get("version", 1),
                                                             "workflowData": {"templates": cur["workflowData"]["templates"]}})
        made = {}
        for case, t in cases.items():
            made[case] = a.call("POST", SERVICES, "/contacts/", body={
                "locationId": LOC, "firstName": "ZZ Test", "lastName": case, "tags": t,
                "email": to.replace("@", f"+cp-{case.replace(' ', '')}-{stamp}@")})["contact"]["id"]
        time.sleep(3)
        for cid in made.values():
            a.call("POST", SERVICES, f"/contacts/{cid}/workflow/{wid}", body={})
        time.sleep(45)
        for case, cid in made.items():
            c = a.call("GET", SERVICES, f"/contacts/{cid}")["contact"]
            tg = set(c.get("tags") or [])
            opps = a.call("GET", SERVICES, "/opportunities/search", params={"location_id": LOC, "contact_id": cid}).get("opportunities", [])
            tasks = a.call("GET", SERVICES, f"/contacts/{cid}/tasks").get("tasks", [])
            missed_task = any("Missed call" in t.get("title", "") for t in tasks)
            if case == "spam":
                ok = not opps and not tasks and "missed call" not in tg
            elif case.startswith("customer"):
                ok = not opps and not tasks and "missed call" not in tg and not {PRESSED, MISSED_IVR} & tg
            elif case == "not answered":
                ok = {"missed call", TEXTED} <= tg and len(opps) == 1 and missed_task and not {PRESSED, MISSED_IVR} & tg
            else:
                ok = "new lead" in tg and "missed call" not in tg and TEXTED not in tg and len(opps) == 1 and not missed_task
            bad += not ok
            print(f"   {'✓' if ok else '✗'} {name[:26]:26} {case:17}: tags {sorted(tg)} · cards {len(opps)} · "
                  f"tarefas {[t.get('title', '')[:24] for t in tasks]}")
            for o in opps:
                a.call("DELETE", SERVICES, f"/opportunities/{o['id']}")
            a.call("DELETE", SERVICES, f"/contacts/{cid}")
        cur = a.workflow(LOC, wid)
        a.call("PUT", BACKEND, f"/workflow/{LOC}/{wid}", body={"name": cur["name"], "version": cur.get("version", 1),
               "status": "draft", "workflowData": {"templates": cur["workflowData"]["templates"]}})
        a.call("DELETE", BACKEND, f"/workflow/{LOC}/{wid}")
    print("   limpo." if not bad else "   limpo (com falhas).")
    return 1 if bad else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("mode", choices=["plan", "test", "apply"])
    parser.add_argument("--to")
    args = parser.parse_args()
    load_dotenv()
    a = Agency()
    if not a.location(LOC)["name"].startswith("Clear Pool Solutions"):
        sys.exit("sub-conta errada")
    flows = {w["name"]: w["id"] for w in a.workflows(LOC)}
    if args.mode == "test":
        if not args.to:
            parser.error("--to is required in test mode")
        return test(a, flows, args.to)
    for name in FLOWS:
        live = read(a, LOC, flows[name])
        new = fix(live["workflowData"]["templates"])
        print(f"   {name}: {'Pressed 1 → ' + NEW_NAME + ' (sem tag spam)' if new else 'já feito'}")
        if new and args.mode == "apply":
            got = put(a, flows[name], live, new)
            trs = [t for t in a.triggers(LOC, flows[name]) if not t.get("deleted")]
            ok = refs_ok(got["workflowData"]["templates"]) and got["status"] == live["status"] and \
                got.get("allowMultiple") == live.get("allowMultiple") and fix(got["workflowData"]["templates"]) is None and \
                all(t.get("targetActionId") for t in trs)
            print(f"      {'✓' if ok else '✗ VERIFICAR'} {got['status']} · re-entry {got.get('allowMultiple')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
