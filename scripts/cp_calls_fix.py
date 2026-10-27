#!/usr/bin/env python3
"""Clear Pool Solutions Tucson: calls (Pedro, 27/10 — Derek complains about the calls he gets).

    ./.venv/bin/python scripts/cp_calls_fix.py plan
    ./.venv/bin/python scripts/cp_calls_fix.py test --to pedro@poolprofits.com
    ./.venv/bin/python scripts/cp_calls_fix.py apply

The 3 lines (Google Ads, Website/GBP, Email Follow Up) ring Derek through "IVR SPAM Detection" (press 1). Every call ends
"completed", so each line's call workflow ran the same way for every call: answered, not answered, hung up in the IVR,
spam or current customer. 29/09-27/10: 46 calls, 13 not answered + 14 hung up in the IVR without any missed-call tag or
text; the Google Ads one texted "Wanted to make sure that we were able to answer all your questions earlier" and counted
a conversion after every call; Website/GBP pulled spam and customers into New Lead with a task.
- IVR: pressed 1 → remove `ivr call missed`, tag `ivr pressed 1`; Derek didn't answer → tag `ivr call missed` (then
  voicemail as before). Connect call without voicemail detection (it marked 7 answered calls as "machine").
- "AdWords Call In - New Lead", "Incoming Call To Pipeline", "Incoming Email follow-up" (trigger unchanged; they run when
  the call ends): if/else "Route the call":
    Spam / DND / current customer → nothing.
    Pressed 1 → answered (no `ivr call missed`): remove the IVR tags, then the steps the workflow had;
                not answered: missed (below).
    Didn't press 1 (hung up in the IVR / no key) → missed.
  Missed: remove the IVR tags, tags of the line + `missed call`, card in New Lead, task "Missed call — call back"
  (Derek), and — at most once per 24 h per caller — the missed-call text.
test: copies (no conversion, alerts none), 5 contacts without phone (answered, pressed-not-answered, no key, spam, current
customer) through each copy; checks tags/cards/tasks; deletes everything.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import uuid

from _common import ROOT, load_dotenv
from pp_lead_alerts import retarget
from ps_ads_forms import cond, if_else, outline, wait_day
from pp_review_fix import read
from pp_source_tags import refs_ok

from cli_anything.gohighlevel.utils.agency import BACKEND, SERVICES, Agency

LOC = "ghUi89uCpNyNunNpbtAt"
DEREK = "zUhz5NEJu5i2WSMQBl1S"
IVR = "IVR SPAM Detection"
FLOWS = ["AdWords Call In - New Lead", "Incoming Call To Pipeline", "Incoming Email follow-up"]
PRESSED, MISSED_IVR, TEXTED = "ivr pressed 1", "ivr call missed", "missed call text 24h"
SKIP = ["spam", "dnd", "current customer", "won"]
TEXT = ("Hi, this is Clear Pool Solutions Tucson. Sorry we missed your call! How can we help with your pool? "
        "Reply here or call us back at this number.")
BDIR = ROOT / "backup" / "clear-pool-solutions-tucson"


def step(kind: str, name: str, attrs: dict) -> tuple[str, str, dict]:
    return (kind, name, {"type": kind, **attrs})


def chain_items(tpl: list[dict]) -> tuple[list[tuple], list[str]]:
    """The workflow's steps as (type, name, attributes), skipping an old guard; and the tags it adds."""
    body = [s for s in tpl if s["type"] != "if_else"]
    by = {s["id"]: s for s in body}
    first = next(s for s in body if s.get("parentKey") not in by)
    out = [first]
    while isinstance(out[-1].get("next"), str) and out[-1]["next"] in by:
        out.append(by[out[-1]["next"]])
    if len(out) != len(body):
        raise SystemExit("cadeia inesperada")
    items = [(s["type"], s.get("name") or s["type"], json.loads(json.dumps(s.get("attributes") or {}))) for s in out]
    tags = next(s["attributes"]["tags"] for s in out if s["type"] == "add_contact_tag")
    return items, tags


def build(items: list[tuple], tags: list[str], test: bool = False) -> list[dict]:
    clear = step("remove_contact_tag", "Remove IVR tags", {"tags": [PRESSED, MISSED_IVR]})
    if test:
        items = [i for i in items if i[0] != "google_adword"]
    card = next(i for i in items if i[0] == "create_opportunity")
    answered = [clear, *items]
    missed = [clear, step("add_contact_tag", "Add Tags (missed call)", {"tags": [*tags, "missed call"]}), card,
              step("task_notification", "Task: missed call — call back", {
                  "title": "Missed call — call back: {{contact.name}} {{contact.phone}}",
                  "body": "This caller didn't reach you (no answer or hung up during the phone menu). Please call back.",
                  "assignedTo": DEREK, "dueDate": {"duration": 0, "unit": "days"}, "__customInputs__": {}}),
              ("ifelse", "Texted in the last 24 h?",
               [("Already texted", [cond("tags", "index-of-true", [TEXTED])], [])],
               "Text back", [step("sms", "Missed-call text", {"body": TEXT, "attachments": []}),
                             step("add_contact_tag", "Add 24 h tag", {"tags": [TEXTED]}), wait_day(),
                             step("remove_contact_tag", "Remove 24 h tag", {"tags": [TEXTED]})])]
    nodes, _ = if_else("Route the call", [
        ("Spam / DND / current customer", [cond("tags", "index-of-true", [t]) for t in SKIP], []),
        ("Pressed 1", [cond("tags", "index-of-true", [PRESSED])],
         [("ifelse", "Did Derek answer?", [("Not answered", [cond("tags", "index-of-true", [MISSED_IVR])], missed)],
           "Answered", answered)]),
    ], "Didn't press 1", missed)
    for n in nodes:  # the GHL step type for tasks is "task-notification"
        if n["type"] == "task_notification":
            n["type"] = "task-notification"
    return nodes


def ivr(tpl: list[dict]) -> list[dict] | None:
    out = json.loads(json.dumps(tpl))
    if any(PRESSED in json.dumps(s.get("attributes")) for s in out):
        return None
    by = {s["id"]: s for s in out}
    ok = next(s for s in out if s["type"] == "transition" and s["name"] == "NOT SPAM")
    connect = by[ok["next"]]
    connect["attributes"]["detectVoicemail"] = False
    rem = {"id": str(uuid.uuid4()), "order": 0, "name": f"Remove {MISSED_IVR}", "type": "remove_contact_tag",
           "parent": ok["id"], "parentKey": ok["id"], "attributes": {"type": "remove_contact_tag", "tags": [MISSED_IVR]}}
    add = {"id": str(uuid.uuid4()), "order": 1, "name": f"Tag {PRESSED}", "type": "add_contact_tag", "parent": ok["id"],
           "parentKey": rem["id"], "next": connect["id"], "attributes": {"type": "add_contact_tag", "tags": [PRESSED]}}
    rem["next"] = add["id"]
    ok["next"] = rem["id"]
    connect.update(parentKey=add["id"], order=2)
    for s in out:  # the after-connect if/else hangs off connect; its order moves with it
        if s.get("parentKey") == connect["id"]:
            s["order"] = 3
    branch = next(s for s in out if s["type"] == "if_else" and s.get("nodeType") == "branch-yes"
                  and by.get(s.get("next"), {}).get("type") == "goto")
    goto = by[branch["next"]]
    miss = {"id": str(uuid.uuid4()), "order": 0, "name": f"Tag {MISSED_IVR}", "type": "add_contact_tag",
            "parent": branch["id"], "parentKey": branch["id"], "next": goto["id"],
            "attributes": {"type": "add_contact_tag", "tags": [MISSED_IVR]}}
    branch["next"] = miss["id"]
    goto.update(parentKey=miss["id"], order=1)
    return [*out, rem, add, miss]


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
    cases = {"answered": [PRESSED], "not answered": [PRESSED, MISSED_IVR], "no key": [], "spam": ["spam"],
             "customer": ["current customer"]}
    for name in FLOWS:
        items, tags = chain_items(read(a, LOC, flows[name])["workflowData"]["templates"])
        tpl = build(items, tags, test=True)
        res = a.call("POST", BACKEND, f"/workflow/{LOC}", body={"name": f"ZZ TEST {name}", "status": "draft"})
        wid = res.get("id") or res.get("_id")
        body = {"name": f"ZZ TEST {name}", "version": 1, "status": "draft", "allowMultiple": True,
                "workflowData": {"templates": tpl}}
        a.call("PUT", BACKEND, f"/workflow/{LOC}/{wid}", body=body)
        live = a.workflow(LOC, wid)
        a.call("PUT", BACKEND, f"/workflow/{LOC}/{wid}", body={**body, "status": "published", "version": live.get("version", 1),
                                                             "workflowData": {"templates": live["workflowData"]["templates"]}})
        made = {}
        for case, t in cases.items():
            made[case] = a.call("POST", SERVICES, "/contacts/", body={
                "locationId": LOC, "firstName": "ZZ Test", "lastName": case, "tags": t,
                "email": to.replace("@", f"+cp-{case.replace(' ', '')}-{stamp}@")})["contact"]["id"]
        time.sleep(3)
        for cid in made.values():
            a.call("POST", SERVICES, f"/contacts/{cid}/workflow/{wid}", body={})
        time.sleep(40)
        for case, cid in made.items():
            c = a.call("GET", SERVICES, f"/contacts/{cid}")["contact"]
            tg = set(c.get("tags") or [])
            opps = a.call("GET", SERVICES, "/opportunities/search", params={"location_id": LOC, "contact_id": cid}).get("opportunities", [])
            tasks = a.call("GET", SERVICES, f"/contacts/{cid}/tasks").get("tasks", [])
            missed = case in ("not answered", "no key")
            if case in ("spam", "customer"):
                ok = not opps and not tasks and not (set(tags) - {"new lead"}) & tg
            elif missed:
                ok = {"missed call", TEXTED, *tags} <= tg and len(opps) == 1 and any("Missed call" in t.get("title", "") for t in tasks) \
                    and not {PRESSED, MISSED_IVR} & tg
            else:
                ok = set(tags) <= tg and "missed call" not in tg and len(opps) == 1 and not {PRESSED, MISSED_IVR} & tg
            bad += not ok
            print(f"   {'✓' if ok else '✗'} {name[:26]:26} {case:12}: tags {sorted(tg)} · cards {len(opps)} · "
                  f"tarefas {[t.get('title', '')[:24] for t in tasks]}")
            for o in opps:
                a.call("DELETE", SERVICES, f"/opportunities/{o['id']}")
            a.call("DELETE", SERVICES, f"/contacts/{cid}")
        live = a.workflow(LOC, wid)
        a.call("PUT", BACKEND, f"/workflow/{LOC}/{wid}", body={"name": live["name"], "version": live.get("version", 1),
               "status": "draft", "workflowData": {"templates": live["workflowData"]["templates"]}})
        a.call("DELETE", BACKEND, f"/workflow/{LOC}/{wid}")
    print("   limpo.")
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
    if args.mode != "plan":
        for t in (PRESSED, MISSED_IVR, TEXTED, "missed call"):
            try:
                a.call("POST", BACKEND, f"/workflow/{LOC}/tags/create", body={"tag": t})
            except Exception:  # noqa: BLE001 — already exists
                pass
    if args.mode == "test":
        if not args.to:
            parser.error("--to is required in test mode")
        return test(a, flows, args.to)
    live = read(a, LOC, flows[IVR])
    new = ivr(live["workflowData"]["templates"])
    print(f"   {IVR}: {'tecla 1 → ivr pressed 1; sem atender → ivr call missed; sem detecção de caixa postal' if new else 'já feito'}")
    if new and args.mode == "apply":
        got = put(a, flows[IVR], live, new)
        print(f"      {'✓' if refs_ok(got['workflowData']['templates']) and got['status'] == 'published' else '✗ VERIFICAR'} {got['status']}")
    for name in FLOWS:
        live = read(a, LOC, flows[name])
        tpl0 = live["workflowData"]["templates"]
        if any(s.get("name") == "Route the call" for s in tpl0):
            print(f"   {name}: já feito")
            continue
        items, tags = chain_items(tpl0)
        tpl = build(items, tags)
        print(f"   {name}: tags {tags}\n{outline(tpl)}")
        if args.mode == "apply":
            got = put(a, flows[name], live, tpl)
            retarget(a, LOC, flows[name], tpl[0]["id"])
            trs = [t for t in a.triggers(LOC, flows[name]) if not t.get("deleted")]
            ok = refs_ok(got["workflowData"]["templates"]) and got["status"] == live["status"] and \
                all(t.get("targetActionId") == tpl[0]["id"] for t in trs)
            print(f"      {'✓' if ok else '✗ VERIFICAR'} {got['status']} · re-entry {got.get('allowMultiple')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
