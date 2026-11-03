#!/usr/bin/env python3
"""The Pool Shack: the 2 Google Ads call tracking numbers Frank bought (03/11, Rob approved).

    ./.venv/bin/python scripts/ps_ads_lines.py plan
    ./.venv/bin/python scripts/ps_ads_lines.py test --to pedro@poolprofits.com
    ./.venv/bin/python scripts/ps_ads_lines.py apply

Lines: Weekly Pool Maintenance (480) 418-1231 and Repairs / Installs (480) 568-3370. Both forward to Rob's Google Voice
(480) 798-2888 like the main line (forwarding is set in Settings → Phone Numbers: no API for it). The account's own
"Answered/Missed Incoming Call To Pipeline" already tag every caller and open a card; on top of that one workflow per
line, the same route as the landing page forms (ps_ads_forms.py) and the YardSpring ad line (ys_ads_line.py):
  Spam / DND          → nothing.
  In the last 24 h    → nothing (every call fires the trigger: one alert per caller per day).
  Current customer    → tags, alerts to Rob marked existing customer; no card.
  New lead            → tags `google ads` + `weekly|repairs` + `google ads - call` + `new lead` + `adwords`, card in Pool
                        Leads → New Lead (source "Google Ads Call - Weekly|Repairs"), Google Ads conversion (empty until
                        Google Ads is connected), text + email to Rob, task "Call back" due today.
Every branch: wait 1 day → remove the 24 h tag.
Basic fixes (backup first): "AdWords Call In - New Lead" (a Clear Pool Tucson copy listening to Clear Pool's number,
"Clear Pool" text) and "Sequential Call Routing" (a BluVantage copy listening to BluVantage's numbers, ringing their
users) are published here but can never fire for The Pool Shack → draft.
test: temporary copies (alerts by email to --to, no text to Rob, no conversion), API-enrolled contacts for every branch
+ a repeat; checks tags/cards/tasks, then deletes everything.
"""
from __future__ import annotations

import argparse
import json
import sys
import time

from _common import ROOT, load_dotenv
from ps_ads_forms import CUSTOMER, LOC, P, PIPELINE, NEW_LEAD, ROB, ROB_EMAIL, SPAM, cond, if_else, outline
from pp_source_tags import refs_ok

from cli_anything.gohighlevel.utils.agency import BACKEND, SERVICES, Agency

FOLDER_OF = "Google Ads LP - Weekly"
LINES = {"weekly": {"line": "+14804181231", "show": "(480) 418-1231", "flow": "Google Ads Call - Weekly", "label": "Weekly Pool Maintenance"},
         "repairs": {"line": "+14805683370", "show": "(480) 568-3370", "flow": "Google Ads Call - Repairs", "label": "Repairs / Installs"}}
STALE = {"AdWords Call In - New Lead": "+15207771392", "Sequential Call Routing": "+14047775712"}
BDIR = ROOT / "backup" / "the-pool-shack"


def build(key: str, test_to: str | None = None) -> list[dict]:
    ln = LINES[key]
    recent = f"google ads call {key} 24h"
    rows = [("Name", "{{contact.name}}"), ("Phone", "{{contact.phone}}"), ("Line", f"Google Ads – {ln['label']} {ln['show']}")]
    todo = "If you didn't talk to them, call back."

    def alerts(customer: bool) -> list:
        head = f"📞 NEW GOOGLE ADS CALL - {ln['label'].upper()}" + (" (EXISTING CUSTOMER)" if customer else "")
        email = ("internal_notification", "Email Rob", {"type": "email", "email": {
            "userType": "custom_email", "to": test_to or ROB_EMAIL,
            "subject": ("[TEST] " if test_to else "") + f"📞 New Google Ads call ({ln['label']}): {{{{contact.name}}}} {{{{contact.phone}}}}",
            "html": P.format(head + ":") + "".join(P.format(f"<b>{a}:</b> {b}") for a, b in rows) + P.format(todo)}})
        if test_to:
            return [email]
        sms = ("internal_notification", "Text Rob", {"type": "sms", "sms": {
            "body": f"{head}\n\n" + "\n".join(f"{a}: {b}" for a, b in rows) + f"\n\n{todo}",
            "userType": "user", "selectedUser": [ROB], "attachments": []}})
        return [sms, email]

    release = [("wait", "Wait 1 day", {"type": "time", "startAfter": {"type": "days", "value": 1, "when": "after"},
                                       "name": "Wait 1 day", "cat": "", "isHybridAction": True, "hybridActionType": "wait",
                                       "convertToMultipath": False, "transitions": []}),
               ("remove_contact_tag", "Remove 24 h tag", {"type": "remove_contact_tag", "tags": [recent]})]
    base = ["google ads", key, "google ads - call", recent]
    card = ("create_opportunity", "Card in New Lead", {
        "fields": [], "type": "create_opportunity", "pipeline_id": PIPELINE, "pipeline_stage_id": NEW_LEAD,
        "opportunity_name": "{{contact.name}}", "opportunity_source": f"Google Ads Call - {key.title()}", "monetary_value": "",
        "opportunity_status": "open"})
    conversion = ("google_adword", "Google Ads conversion", {
        "type": "google_adword", "currency": "USD", "conversion_value": "1", "conversion_type": "", "conversion_name": "",
        "conversion_action_id": "", "customMapping": {"gclid": "{{contact.attributionSource.gclid}}"}, "isCustomMappingEnabled": True})
    task = ("task-notification", "Task: call back google ads lead", {
        "type": "task_notification", "title": "Call back Google Ads lead: {{contact.name}} {{contact.phone}}",
        "body": f"<p style=\"margin:0px\">New Google Ads call ({ln['label']}).</p>"
                f"<p style=\"margin:0px\">{todo} Then move the card down the pipeline.</p>",
        "assignedTo": ROB, "dueDate": {"duration": 0, "unit": "days"}})
    lead = [("add_contact_tag", "Add Tags", {"type": "add_contact_tag", "tags": [*base, "new lead", "adwords"]}), card,
            *([] if test_to else [conversion]), *alerts(False), task, *release]
    customer = [("add_contact_tag", "Add Tags", {"type": "add_contact_tag", "tags": base}), *alerts(True), *release]
    nodes, _ = if_else("Route the call", [
        ("Spam / DND", [cond("tags", "index-of-true", [t]) for t in SPAM], []),
        ("In the last 24 h", [cond("tags", "index-of-true", [recent])], []),
        ("Current customer", [cond("tags", "index-of-true", [t]) for t in CUSTOMER], customer),
    ], "New lead", lead)
    return nodes


def trigger(wid: str, first: str, line: str) -> dict:
    return {"type": "call_status", "name": "Call Status", "masterType": "highlevel", "schedule_config": {},
            "conditions": [{"field": "message.direction", "operator": "==", "value": "inbound", "title": "Call Direction", "type": "select"},
                           {"field": "inbound_number", "operator": "contains-any", "id": "inbound-twilio-number", "value": [line],
                            "title": "In Phone Number", "type": "multiselect"}],
            "workflowId": wid, "workflow_id": wid, "location_id": LOC,
            "actions": [{"workflow_id": wid, "type": "add_to_workflow"}], "targetActionId": first}


def create(a: Agency, name: str, parent: str | None, tpl: list[dict], line: str | None) -> dict:
    res = a.call("POST", BACKEND, f"/workflow/{LOC}", body={"name": name, "parentId": parent, "status": "draft"})
    wid = res.get("id") or res.get("_id")
    a.call("PUT", BACKEND, f"/workflow/{LOC}/{wid}", body={"name": name, "version": 1, "status": "draft", "parentId": parent,
                                                         "allowMultiple": True, "workflowData": {"templates": tpl}})
    if not line:  # test copy: contacts are enrolled through the API
        return set_status(a, wid, "published")
    t = trigger(wid, tpl[0]["id"], line)
    r = a.call("POST", BACKEND, f"/workflow/{LOC}/trigger", body=t)
    a.call("PUT", BACKEND, f"/workflow/{LOC}/trigger/{r['id']}", body={**t, "id": r["id"]})
    return set_status(a, wid, "published")


def set_status(a: Agency, wid: str, status: str) -> dict:
    live = a.workflow(LOC, wid)
    a.call("PUT", BACKEND, f"/workflow/{LOC}/{wid}", body={"name": live["name"], "version": live.get("version", 1), "status": status,
           "parentId": live.get("parentId"), "workflowData": {"templates": live["workflowData"]["templates"]}})
    time.sleep(3)
    return a.workflow(LOC, wid)


def test(a: Agency, folder: str | None, to: str) -> int:
    bad = 0
    for key, ln in LINES.items():
        recent = f"google ads call {key} 24h"
        got = create(a, f"ZZ TEST ps call {key}", folder, build(key, to), None)
        wid, ts, made = got["id"], int(time.time()), {}
        try:
            for case, tags in (("new", []), ("customer", ["existing customer"]), ("spam", ["spam"])):
                made[case] = a.call("POST", SERVICES, "/contacts/", body={
                    "locationId": LOC, "firstName": "ZZ Test", "lastName": f"call {key} {case}", "tags": tags,
                    "email": to.replace("@", f"+ps-call-{key}-{case}-{ts}@")})["contact"]["id"]
            time.sleep(3)
            for cid in made.values():
                a.call("POST", SERVICES, f"/contacts/{cid}/workflow/{wid}", body={})
            time.sleep(30)
            a.call("POST", SERVICES, f"/contacts/{made['new']}/workflow/{wid}", body={})  # a second call
            time.sleep(30)
            base = {"google ads", key, "google ads - call", recent}
            want = {"new": (base | {"new lead", "adwords"}, 1, 1), "customer": (base, 0, 0), "spam": (set(), 0, 0)}
            for case, cid in made.items():
                c = a.call("GET", SERVICES, f"/contacts/{cid}")["contact"]
                opps = a.call("GET", SERVICES, "/opportunities/search", params={"location_id": LOC, "contact_id": cid}).get("opportunities", [])
                tasks = a.call("GET", SERVICES, f"/contacts/{cid}/tasks").get("tasks", [])
                exp, cards, ntask = want[case]
                ok = exp <= set(c.get("tags", [])) and len(opps) == cards and len(tasks) == ntask and \
                    (case != "spam" or "google ads - call" not in c.get("tags", []))
                bad += not ok
                print(f"   {'✓' if ok else '✗'} {key} {case}: tags {sorted(c.get('tags', []))} · cards {[o.get('source') for o in opps]} · tarefas {len(tasks)}")
        finally:
            for cid in made.values():
                for o in a.call("GET", SERVICES, "/opportunities/search", params={"location_id": LOC, "contact_id": cid}).get("opportunities", []):
                    a.call("DELETE", SERVICES, f"/opportunities/{o['id']}")
                a.call("DELETE", SERVICES, f"/contacts/{cid}")
            set_status(a, wid, "draft")
            a.call("DELETE", BACKEND, f"/workflow/{LOC}/{wid}")
    print(f"   limpo. Esperado em {to}: 4 e-mails (por linha: novo 1 apesar de 2 entradas + cliente 1), nenhum do spam.")
    return 1 if bad else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("mode", choices=["plan", "test", "apply"])
    parser.add_argument("--to")
    args = parser.parse_args()
    if args.mode == "test" and not args.to:
        parser.error("--to is required in test mode")
    load_dotenv()
    a = Agency()
    if a.location(LOC)["name"] != "The Pool Shack":
        sys.exit("sub-conta errada")
    nums = {n["phoneNumber"]: n for n in a.call("GET", SERVICES, f"/phone-system/numbers/location/{LOC}")["numbers"]}
    flows = {w["name"]: w for w in a.workflows(LOC)}
    folder = a.workflow(LOC, flows[FOLDER_OF]["id"]).get("parentId")
    for key, ln in LINES.items():
        n = nums.get(ln["line"]) or {}
        print(f"   {ln['label']} {ln['show']}: encaminha para {n.get('forwardingNumber') or '— (configurar na tela)'} · "
              f"{ln['flow']}: {'existe' if ln['flow'] in flows else 'cria'}")
    for name, line in STALE.items():
        w = flows.get(name)
        if w:
            trs = [t for t in a.triggers(LOC, w["id"]) if not t.get("deleted")]
            nums_t = [c.get("value") for t in trs for c in t.get("conditions") or [] if c.get("field") == "inbound_number"]
            print(f"   {name}: {w['status']} · gatilho {nums_t} (não é da Pool Shack) → draft")
    if args.mode == "plan":
        print(outline(build("weekly")))
        return 0
    for key in LINES:
        for t in ("google ads", key, "google ads - call", f"google ads call {key} 24h", "new lead", "adwords"):
            try:
                a.call("POST", BACKEND, f"/workflow/{LOC}/tags/create", body={"tag": t})
            except Exception:  # noqa: BLE001 — already exists
                pass
    if args.mode == "test":
        return test(a, folder, args.to)
    BDIR.mkdir(parents=True, exist_ok=True)
    st = time.strftime("%Y%m%d-%H%M%S")
    for name, line in STALE.items():
        w = flows.get(name)
        if not w or w["status"] != "published":
            continue
        trs = [t for t in a.triggers(LOC, w["id"]) if not t.get("deleted")]
        if any(n in nums for t in trs for c in t.get("conditions") or [] if c.get("field") == "inbound_number" for n in c.get("value") or []):
            print(f"   {name}: gatilho tem número da conta — não mexo")
            continue
        (BDIR / f"workflow-{w['id']}-{st}.json").write_text(json.dumps({"workflow": a.workflow(LOC, w["id"]), "triggers": trs}))
        print(f"   {'✓' if set_status(a, w['id'], 'draft')['status'] == 'draft' else '✗ VERIFICAR'} {name} → draft")
    for key, ln in LINES.items():
        if ln["flow"] in flows:
            print(f"   {ln['flow']}: já existe")
            continue
        got = create(a, ln["flow"], folder, build(key), ln["line"])
        trs = [x for x in a.triggers(LOC, got["id"]) if not x.get("deleted")]
        ok = got["status"] == "published" and refs_ok(got["workflowData"]["templates"]) and len(trs) == 1 and trs[0].get("active")
        print(f"   {'✓' if ok else '✗ VERIFICAR'} {ln['flow']}: {got['status']} · gatilho {ln['show']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
