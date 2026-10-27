#!/usr/bin/env python3
"""Clear Pool Solutions Tucson: Derek gets a text + email for every call he misses (Pedro, 27/10).

    ./.venv/bin/python scripts/cp_missed_notify.py plan
    ./.venv/bin/python scripts/cp_missed_notify.py test --to pedro@poolprofits.com
    ./.venv/bin/python scripts/cp_missed_notify.py apply

He asked for a notice "when I don't answer and they leave a voicemail". The voicemail is an audio attachment on the call
message; no workflow trigger or condition sees it, so the notice goes for every missed call and points him to the
recording in Conversations. In the 3 call workflows ("Route the call", cp_calls_fix.py):
- every missed-call chain (after "Task: missed call — call back"): text to Derek + email to tucson@clearpoolsolutions.com;
- "Spam / DND / current customer" splits: spam/DND → nothing; new branch "Current customer" → if Derek missed it
  (`ivr call missed`): the same notice marked CURRENT CUSTOMER (no card, no text to the customer); then the IVR tags go.
test: copies with the notices sent by email to --to, contacts for new-lead missed / customer missed / customer answered /
spam; checks tags and cards; deletes everything.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import uuid

from _common import ROOT, load_dotenv
from ps_ads_forms import P, attach, cond
from pp_review_fix import read
from pp_source_tags import fresh_ids, refs_ok

from cli_anything.gohighlevel.utils.agency import BACKEND, SERVICES, Agency

LOC = "ghUi89uCpNyNunNpbtAt"
DEREK, DEREK_EMAIL = "zUhz5NEJu5i2WSMQBl1S", "tucson@clearpoolsolutions.com"
FLOWS = {"AdWords Call In - New Lead": "Google Ads line", "Incoming Call To Pipeline": "Website/GBP line",
         "Incoming Email follow-up": "Email follow-up line"}
PRESSED, MISSED_IVR = "ivr pressed 1", "ivr call missed"
SPAM, CUSTOMER = ["spam", "dnd"], ["current customer", "won"]
BDIR = ROOT / "backup" / "clear-pool-solutions-tucson"


def notices(line: str, customer: bool, test_to: str | None) -> list[dict]:
    who = " (CURRENT CUSTOMER)" if customer else ""
    text = (f"📞 MISSED CALL{who}\n\n{{{{contact.name}}}}\n{{{{contact.phone}}}}\n{line}\n\n"
            "If they left a voicemail, it's in Conversations in the GHL app.")
    html = (P.format(f"<b>Missed call{who.title()}</b> on the {line}.") +
            P.format("<b>Name:</b> {{contact.name}}<br><b>Phone:</b> {{contact.phone}}") +
            P.format("If they left a voicemail, you can listen to it in Conversations in the GHL app."))
    email = {"id": str(uuid.uuid4()), "name": "Email Derek: missed call", "type": "internal_notification",
             "attributes": {"type": "email", "email": {"userType": "custom_email", "to": test_to or DEREK_EMAIL,
                                                       "subject": f"📞 Missed call{who.title()}: {{{{contact.name}}}} {{{{contact.phone}}}}",
                                                       "html": html}}}
    if test_to:
        return [email]
    sms = {"id": str(uuid.uuid4()), "name": "Text Derek: missed call", "type": "internal_notification",
           "attributes": {"type": "sms", "sms": {"body": text, "userType": "user", "selectedUser": [DEREK], "attachments": []}}}
    return [sms, email]


def add_notices(tpl: list[dict], line: str, test_to: str | None = None) -> list[dict] | None:
    out = json.loads(json.dumps(tpl))
    if any((s.get("name") or "").startswith(("Text Derek: missed", "Email Derek: missed")) for s in out):
        return None
    by = {s["id"]: s for s in out}
    new = []
    for task in [s for s in out if (s.get("name") or "").startswith("Task: missed call")]:
        steps = notices(line, False, test_to)
        nxt = task.get("next")
        prev = task
        for i, st in enumerate(steps):
            st.update(parent=task.get("parent"), parentKey=prev["id"], order=task.get("order", 0) + 1 + i)
            prev["next"] = st["id"]
            prev = st
        if nxt:
            prev["next"] = nxt
            by[nxt]["parentKey"] = prev["id"]
        new += steps
    # split spam / customer: the customer branch notices a missed call
    head = next(s for s in out if s.get("name") == "Route the call" and s.get("nodeType") == "condition-node")
    first = head["attributes"]["branches"][0]
    first["name"] = "Spam / DND"
    first["segments"][0]["conditions"] = [c for c in first["segments"][0]["conditions"] if c["conditionValue"][0] in SPAM]
    by[first["id"]]["name"] = "Spam / DND"
    bid = str(uuid.uuid4())
    head["attributes"]["branches"].insert(1, {"id": bid, "name": "Current customer", "operator": "and", "showErrors": False,
                                              "branchNameError": "Branch name cannot be empty!",
                                              "segments": [{"__segmentId": str(uuid.uuid4()), "operator": "or",
                                                            "conditions": [cond("tags", "index-of-true", [t]) for t in CUSTOMER]}]})
    head["next"].insert(1, bid)
    branch = {"id": bid, "parent": head["id"], "parentKey": head["id"], "order": 1, "name": "Current customer",
              "type": "if_else", "cat": "conditions", "nodeType": "branch-yes", "sibling": [x for x in head["next"] if x != bid],
              "attributes": {"if": False, "conditionName": "Condition", "operator": "and", "branches": []}}
    for sid in head["next"]:
        if sid != bid:
            by[sid]["sibling"] = [x for x in head["next"] if x != sid]
    clear = ("remove_contact_tag", "Remove IVR tags", {"type": "remove_contact_tag", "tags": [PRESSED, MISSED_IVR]})
    missed = [(s["type"], s["name"], s["attributes"]) for s in notices(line, True, test_to)]
    body = attach([("ifelse", "Did Derek answer?", [("Missed", [cond("tags", "index-of-true", [MISSED_IVR])], [*missed, clear])],
                    "Answered", [clear])], bid)
    branch["next"] = body[0]["id"]
    return [*out, *new, branch, *body]


def put(a: Agency, wid: str, live: dict, tpl: list[dict]) -> dict:
    BDIR.mkdir(parents=True, exist_ok=True)
    (BDIR / f"workflow-{wid}-{time.strftime('%Y%m%d-%H%M%S')}.json").write_text(json.dumps(live))
    a.call("PUT", BACKEND, f"/workflow/{LOC}/{wid}", body={"name": live["name"], "version": live.get("version", 1),
                                                         "status": live["status"], "parentId": live.get("parentId"),
                                                         "workflowData": {"templates": tpl}})
    time.sleep(2)
    return read(a, LOC, wid)


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
        name = "Incoming Call To Pipeline"
        tpl = add_notices(read(a, LOC, flows[name])["workflowData"]["templates"], FLOWS[name], args.to)
        tpl = [s for s in fresh_ids(tpl)]
        for s in tpl:  # no texts to anyone from the test copy
            if s["type"] == "sms":
                s["attributes"]["body"] = "TEST"
        res = a.call("POST", BACKEND, f"/workflow/{LOC}", body={"name": "ZZ TEST missed notice", "status": "draft"})
        wid = res.get("id") or res.get("_id")
        body = {"name": "ZZ TEST missed notice", "version": 1, "status": "draft", "allowMultiple": True, "workflowData": {"templates": tpl}}
        a.call("PUT", BACKEND, f"/workflow/{LOC}/{wid}", body=body)
        live = a.workflow(LOC, wid)
        a.call("PUT", BACKEND, f"/workflow/{LOC}/{wid}", body={**body, "status": "published", "version": live.get("version", 1),
                                                             "workflowData": {"templates": live["workflowData"]["templates"]}})
        stamp, made, bad = int(time.time()), {}, 0
        cases = {"lead missed": [PRESSED, MISSED_IVR], "customer missed": ["current customer", PRESSED, MISSED_IVR],
                 "customer answered": ["current customer", PRESSED], "spam": ["spam", PRESSED]}
        for case, tags in cases.items():
            made[case] = a.call("POST", SERVICES, "/contacts/", body={"locationId": LOC, "firstName": "ZZ Test", "lastName": case,
                                                                      "tags": tags, "email": args.to.replace("@", f"+cp-mn-{case.replace(' ', '')}-{stamp}@")})["contact"]["id"]
        time.sleep(3)
        for cid in made.values():
            a.call("POST", SERVICES, f"/contacts/{cid}/workflow/{wid}", body={})
        time.sleep(40)
        for case, cid in made.items():
            tg = set(a.call("GET", SERVICES, f"/contacts/{cid}")["contact"].get("tags") or [])
            opps = a.call("GET", SERVICES, "/opportunities/search", params={"location_id": LOC, "contact_id": cid}).get("opportunities", [])
            if case == "lead missed":
                ok = "missed call" in tg and len(opps) == 1 and not {PRESSED, MISSED_IVR} & tg
            elif case.startswith("customer"):
                ok = not opps and not {PRESSED, MISSED_IVR} & tg and "missed call" not in tg
            else:
                ok = not opps and PRESSED in tg
            bad += not ok
            print(f"   {'✓' if ok else '✗'} {case:18}: tags {sorted(tg)} · cards {len(opps)}")
            for o in opps:
                a.call("DELETE", SERVICES, f"/opportunities/{o['id']}")
            a.call("DELETE", SERVICES, f"/contacts/{cid}")
        live = a.workflow(LOC, wid)
        a.call("PUT", BACKEND, f"/workflow/{LOC}/{wid}", body={"name": live["name"], "version": live.get("version", 1),
               "status": "draft", "workflowData": {"templates": live["workflowData"]["templates"]}})
        a.call("DELETE", BACKEND, f"/workflow/{LOC}/{wid}")
        print(f"   limpo. Esperado em {args.to}: 2 e-mails (lead missed; customer missed com CURRENT CUSTOMER).")
        return 1 if bad else 0
    for name, line in FLOWS.items():
        live = read(a, LOC, flows[name])
        tpl = add_notices(live["workflowData"]["templates"], line)
        print(f"   {name}: {'+ aviso de chamada perdida (lead e cliente)' if tpl else 'já feito'}")
        if tpl and args.mode == "apply":
            got = put(a, flows[name], live, tpl)
            print(f"      {'✓' if refs_ok(got['workflowData']['templates']) and got['status'] == live['status'] else '✗ VERIFICAR'} {got['status']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
