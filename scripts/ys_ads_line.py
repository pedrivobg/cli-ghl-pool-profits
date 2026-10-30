#!/usr/bin/env python3
"""YardSpring: Google Ads leads — the landing pages' number (678) 448-4007 (calls, SMS asset) and the Google Ads lead form
"Leads Form - Google Ads" (Val, 29–30/10).

    ./.venv/bin/python scripts/ys_ads_line.py plan
    ./.venv/bin/python scripts/ys_ads_line.py test --to pedro@poolprofits.com
    ./.venv/bin/python scripts/ys_ads_line.py apply

The line rings like the main line (no forwarding/IVR on either; "Incoming Call To Pipeline" already tags every caller
`new lead`, opens a card and the account's own new-lead text goes out). On top of that, one if/else per channel:
  Spam / DND             → nothing.
  In the last 24 h       → nothing (one alert per lead per day: every call / every text fires the trigger).
  Current customer       → tag, alerts to Joe marked existing customer; no card.
  New lead               → tags `google ads - call|sms` + `new lead` + `adwords`, owner Joe (if none), card in Pool Leads →
                           New Lead (source "Google Ads - Call|SMS"), Google Ads conversion, text + email to Joe,
                           task "Call back / Reply" due today.
Every branch: wait 1 day → remove the 24 h tag. Workflows:
- calls: "AdWords Call In - New Lead" (published) was a copy of Clear Pool Tucson's — trigger on Clear Pool's number, card
  in Clear Pool's pipeline, text "Thank you for reaching out to Clear Pool Solutions Tucson" — so it never fired here.
  Its trigger now listens to this line and its steps are replaced by the chain above (backup first);
- texts: new "Google Ads SMS - New Lead" (Customer Replied, SMS, in phone number = this line), as at Southern;
- lead form: new "Google Lead Form - New Lead" (Google Lead Form Submitted; no ad-account filter: the Google Lead Ads app
  leaves googleAdwordsId empty, as at LWR). Tags `new lead`, `new form fill`, `adwords` (Val) + `google ads - lead form`;
  no conversion step (the lead already counts in Google Ads); "Service Requested" in the alert when the form asks it.
  The account's own "New Lead - Initial SMS Follow-up" (tag `new lead`) texts the lead, as for every new lead.
test: temporary copies (alerts by email to --to, no text to Joe, no conversion), contacts enrolled through the API for
every branch + a repeat; checks tags/cards/tasks, then deletes everything.
"""
from __future__ import annotations

import argparse
import json
import sys
import time

from _common import ROOT, load_dotenv
from ps_ads_forms import P, cond, if_else, outline
from pp_source_tags import refs_ok

from cli_anything.gohighlevel.utils.agency import BACKEND, SERVICES, Agency

LOC = "FpRTQZR56xwp1Wg5NQCq"
LINE = "+16784484007"
JOE, JOE_EMAIL = "vBIKogeCqW1ZuXXNpCSt", "joe@yardspring.com"
PIPELINE, NEW_LEAD = "BH1KjxcRp1sgMc6bJfpW", "ad759d56-3e34-48ec-a0a0-161e476326e5"
CALL_FLOW, SMS_FLOW, FOLDER_OF = "AdWords Call In - New Lead", "Google Ads SMS - New Lead", "AdWords Form - New Lead"
FORM_FLOW = "Google Lead Form - New Lead"
SPAM, CUSTOMER = ["spam", "dnd"], ["existing customer", "recurring customer", "current customer", "won"]
KIND = {"call": {"tag": "google ads - call", "recent": "google ads call 24h", "source": "Google Ads - Call",
                 "head": "📞 NEW GOOGLE ADS CALL", "what": "call", "extra": [],
                 "todo": "If you didn't talk to them, call back.", "task": "Call back Google Ads lead"},
        "sms": {"tag": "google ads - sms", "recent": "google ads sms 24h", "source": "Google Ads - SMS",
                "head": "📱 NEW GOOGLE ADS TEXT", "what": "text", "extra": [("Message", "{{message.body}}")],
                "todo": "Reply from the CRM so it goes out from the Google Ads number.", "task": "Reply to Google Ads text lead"},
        "form": {"tag": "google ads - lead form", "recent": "google lead form 24h", "source": "Google Ads - Lead Form",
                 "head": "📝 NEW GOOGLE ADS LEAD FORM", "what": "lead form",
                 "extra": [("Email", "{{contact.email}}"), ("ZIP", "{{contact.postal_code}}"), ("Service", "{{contact.service_requested}}")],
                 "todo": "Call them back as soon as you can.", "task": "Call Google Ads lead form lead"}}
BDIR = ROOT / "backup" / "yardspring-pools"


def build(kind: str, test_to: str | None = None) -> list[dict]:
    k = KIND[kind]
    rows = [("Name", "{{contact.name}}"), ("Phone", "{{contact.phone}}"), *k["extra"]] + \
        ([("Line", "Google Ads landing pages (678) 448-4007")] if kind != "form" else [("Source", "Google Ads lead form")])

    def alerts(customer: bool) -> list:
        head = k["head"] + (" (EXISTING CUSTOMER)" if customer else "")
        email = ("internal_notification", "Email Joe", {"type": "email", "email": {
            "userType": "custom_email", "to": test_to or JOE_EMAIL,
            "subject": ("[TEST] " if test_to else "") + f"{k['head'].split(' ', 1)[0]} New Google Ads {k['what']}: {{{{contact.name}}}} {{{{contact.phone}}}}",
            "html": P.format(head + ":") + "".join(P.format(f"<b>{a}:</b> {b}") for a, b in rows) + P.format(k["todo"])}})
        if test_to:
            return [email]
        sms = ("internal_notification", "Text Joe", {"type": "sms", "sms": {
            "body": f"{head}\n\n" + "\n".join(f"{a}: {b}" for a, b in rows) + f"\n\n{k['todo']}",
            "userType": "user", "selectedUser": [JOE], "attachments": []}})
        return [sms, email]

    release = [("wait", "Wait 1 day", {"type": "time", "startAfter": {"type": "days", "value": 1, "when": "after"},
                                       "name": "Wait 1 day", "cat": "", "isHybridAction": True, "hybridActionType": "wait",
                                       "convertToMultipath": False, "transitions": []}),
               ("remove_contact_tag", "Remove 24 h tag", {"type": "remove_contact_tag", "tags": [k["recent"]]})]
    tags = ("add_contact_tag", "Add Tags", {"type": "add_contact_tag",
                                           "tags": [k["tag"], "new lead", "adwords", k["recent"]] + {"call": ["adwords call in"], "sms": [],
                                                                                                  "form": ["new form fill"]}[kind]})
    owner = ("assign_user", "Assign to Joe", {"type": "assign_user", "only_unassigned_contact": True, "traffic_split": "equally",
                                              "user_list": [JOE], "traffic_weightage": {JOE: 1}, "total_index": 1,
                                              "traffic_index": [{"id": JOE, "indexes": [1]}]})
    card = ("create_opportunity", "Card in New Lead", {
        "fields": [], "type": "create_opportunity", "pipeline_id": PIPELINE, "pipeline_stage_id": NEW_LEAD,
        "opportunity_name": "{{contact.name}}", "opportunity_source": k["source"], "monetary_value": "", "opportunity_status": "open"})
    conversion = ("google_adword", "Google Ads conversion", {
        "type": "google_adword", "currency": "USD", "conversion_value": "1", "conversion_type": "", "conversion_name": "",
        "conversion_action_id": "", "customMapping": {"gclid": "{{contact.attributionSource.gclid}}"}, "isCustomMappingEnabled": True})
    task = ("task-notification", f"Task: {k['task'].lower()}", {
        "type": "task_notification", "title": f"{k['task']}: {{{{contact.name}}}} {{{{contact.phone}}}}",
        "body": f"<p style=\"margin:0px\">New Google Ads {k['what']} lead.</p>"
                f"<p style=\"margin:0px\">{k['todo']} Then move the card down the pipeline.</p>",
        "assignedTo": JOE, "dueDate": {"duration": 0, "unit": "days"}})
    lead = [tags, owner, card, *([] if test_to or kind == "form" else [conversion]), *alerts(False), task, *release]
    customer = [("add_contact_tag", "Add Tags", {"type": "add_contact_tag", "tags": [k["tag"], k["recent"]]}), *alerts(True), *release]
    nodes, _ = if_else(f"Route the {k['what']}", [
        ("Spam / DND", [cond("tags", "index-of-true", [t]) for t in SPAM], []),
        ("In the last 24 h", [cond("tags", "index-of-true", [k["recent"]])], []),
        ("Current customer", [cond("tags", "index-of-true", [t]) for t in CUSTOMER], customer),
    ], "New lead", lead)
    return nodes


def sms_trigger(wid: str, first: str) -> dict:
    return {"type": "customer_reply", "name": "Customer Replied", "masterType": "highlevel", "schedule_config": {},
            "conditions": [{"operator": "==", "field": "message.type", "value": 2, "title": "Reply channel", "type": "select"},
                           {"operator": "contains-any", "field": "inbound_number", "value": [LINE], "title": "In phone number",
                            "type": "multiselect", "id": "inbound-twilio-number"}],
            "workflowId": wid, "workflow_id": wid, "location_id": LOC,
            "actions": [{"workflow_id": wid, "type": "add_to_workflow"}], "targetActionId": first}


def form_trigger(wid: str, first: str) -> dict:
    return {"type": "google_lead_form_submitted", "name": "Google Lead Form Submitted", "masterType": "internal",
            "schedule_config": {}, "conditions": [], "workflowId": wid, "workflow_id": wid, "location_id": LOC,
            "actions": [{"workflow_id": wid, "type": "add_to_workflow"}], "targetActionId": first}


def create(a: Agency, name: str, parent: str | None, tpl: list[dict]) -> str:
    res = a.call("POST", BACKEND, f"/workflow/{LOC}", body={"name": name, "parentId": parent, "status": "draft"})
    wid = res.get("id") or res.get("_id")
    a.call("PUT", BACKEND, f"/workflow/{LOC}/{wid}", body={"name": name, "version": 1, "status": "draft", "parentId": parent,
                                                         "allowMultiple": True, "workflowData": {"templates": tpl}})
    return wid


def publish(a: Agency, wid: str, tpl: list[dict] | None = None) -> dict:
    live = a.workflow(LOC, wid)
    a.call("PUT", BACKEND, f"/workflow/{LOC}/{wid}", body={
        "name": live["name"], "version": live.get("version", 1), "status": "published", "parentId": live.get("parentId"),
        "allowMultiple": True, "workflowData": {"templates": tpl or live["workflowData"]["templates"]}})
    time.sleep(3)
    return a.workflow(LOC, wid)


def drop(a: Agency, wid: str) -> None:
    live = a.workflow(LOC, wid)
    a.call("PUT", BACKEND, f"/workflow/{LOC}/{wid}", body={"name": live["name"], "version": live.get("version", 1), "status": "draft",
                                                         "workflowData": {"templates": live["workflowData"]["templates"]}})
    a.call("DELETE", BACKEND, f"/workflow/{LOC}/{wid}")


def test(a: Agency, folder: str | None, to: str) -> int:
    bad = 0
    for kind in KIND:
        k = KIND[kind]
        wid = create(a, f"ZZ TEST ys {kind}", folder, build(kind, to))
        publish(a, wid)
        ts, made = int(time.time()), {}
        try:
            for case, tags in (("new", []), ("customer", ["existing customer"]), ("spam", ["spam"])):
                made[case] = a.call("POST", SERVICES, "/contacts/", body={
                    "locationId": LOC, "firstName": "ZZ Test", "lastName": f"{kind} {case}", "tags": tags,
                    "email": to.replace("@", f"+ys-{kind}-{case}-{ts}@")})["contact"]["id"]
            time.sleep(3)
            for cid in made.values():
                a.call("POST", SERVICES, f"/contacts/{cid}/workflow/{wid}", body={})
            time.sleep(30)
            a.call("POST", SERVICES, f"/contacts/{made['new']}/workflow/{wid}", body={})  # a second call/text
            time.sleep(30)
            want = {"new": ({k["tag"], "new lead", "adwords", k["recent"]} | ({"new form fill"} if kind == "form" else set()), 1, 1), "customer": ({k["tag"], k["recent"]}, 0, 0),
                    "spam": (set(), 0, 0)}
            for case, cid in made.items():
                c = a.call("GET", SERVICES, f"/contacts/{cid}")["contact"]
                opps = a.call("GET", SERVICES, "/opportunities/search", params={"location_id": LOC, "contact_id": cid}).get("opportunities", [])
                tasks = a.call("GET", SERVICES, f"/contacts/{cid}/tasks").get("tasks", [])
                exp_tags, exp_cards, exp_tasks = want[case]
                ok = exp_tags <= set(c.get("tags", [])) and len(opps) == exp_cards and len(tasks) == exp_tasks and \
                    (case != "spam" or k["tag"] not in c.get("tags", []))
                bad += not ok
                print(f"   {'✓' if ok else '✗'} {kind} {case}: tags {sorted(c.get('tags', []))} · cards {[o.get('source') for o in opps]} · tarefas {len(tasks)}")
        finally:
            for cid in made.values():
                for o in a.call("GET", SERVICES, "/opportunities/search", params={"location_id": LOC, "contact_id": cid}).get("opportunities", []):
                    a.call("DELETE", SERVICES, f"/opportunities/{o['id']}")
                a.call("DELETE", SERVICES, f"/contacts/{cid}")
            drop(a, wid)
    print(f"   limpo. Esperado em {to}: 6 e-mails (call, sms, form: novo 1 apesar de 2 entradas + cliente 1), nenhum do spam.")
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
    if not a.location(LOC)["name"].lower().startswith("yardspring"):
        sys.exit("sub-conta errada")
    flows = {w["name"]: w["id"] for w in a.workflows(LOC)}
    folder = a.workflow(LOC, flows[FOLDER_OF]).get("parentId")
    call = a.workflow(LOC, flows[CALL_FLOW])
    trig = next(t for t in a.triggers(LOC, flows[CALL_FLOW]) if not t.get("deleted"))
    num = next(c for c in trig["conditions"] if c.get("field") == "inbound_number")
    if args.mode == "plan":
        print(f"   {CALL_FLOW}: gatilho {num['value']} → [{LINE}]; passos {[s.get('name') for s in call['workflowData']['templates']]} →")
        print(outline(build("call")))
        print(f"   {SMS_FLOW}: {'existe' if SMS_FLOW in flows else 'cria'} · SMS recebido em {LINE}")
        print(outline(build("sms")))
        print(f"   {FORM_FLOW}: {'existe' if FORM_FLOW in flows else 'cria'} · Google Lead Form Submitted")
        print(outline(build("form")))
        return 0
    for k in KIND.values():
        for t in (k["tag"], k["recent"]):
            try:
                a.call("POST", BACKEND, f"/workflow/{LOC}/tags/create", body={"tag": t})
            except Exception:  # noqa: BLE001 — already exists
                pass
    if args.mode == "test":
        return test(a, folder, args.to)
    if num["value"] != [LINE]:
        BDIR.mkdir(parents=True, exist_ok=True)
        st = time.strftime("%Y%m%d-%H%M%S")
        (BDIR / f"workflow-{call['id']}-{st}.json").write_text(json.dumps({"workflow": call, "trigger": trig}))
        tpl = build("call")
        got = publish(a, call["id"], tpl)
        num["value"] = [LINE]
        body = {k: v for k, v in trig.items() if k not in ("id", "date_added", "date_updated", "_id")}
        body.update({"workflowId": call["id"], "workflow_id": call["id"], "location_id": LOC, "targetActionId": tpl[0]["id"]})
        a.call("PUT", BACKEND, f"/workflow/{LOC}/trigger/{trig['id']}", body=body)
        time.sleep(3)
        t2 = next(t for t in a.triggers(LOC, call["id"]) if not t.get("deleted"))
        n2 = next(c for c in t2["conditions"] if c.get("field") == "inbound_number")["value"]
        ok = got["status"] == "published" and refs_ok(got["workflowData"]["templates"]) and n2 == [LINE] and \
            t2.get("targetActionId") == tpl[0]["id"] and t2.get("active")
        print(f"   {'✓' if ok else '✗ VERIFICAR'} {CALL_FLOW}: {got['status']} · gatilho {n2}")
    else:
        print(f"   {CALL_FLOW}: já feito")
    for name, kind, trig_of in ((SMS_FLOW, "sms", sms_trigger), (FORM_FLOW, "form", form_trigger)):
        if name in flows:
            print(f"   {name}: já existe")
            continue
        tpl = build(kind)
        wid = create(a, name, folder, tpl)
        t = trig_of(wid, tpl[0]["id"])
        r = a.call("POST", BACKEND, f"/workflow/{LOC}/trigger", body=t)
        a.call("PUT", BACKEND, f"/workflow/{LOC}/trigger/{r['id']}", body={**t, "id": r["id"]})
        got = publish(a, wid)
        trs = [x for x in a.triggers(LOC, wid) if not x.get("deleted")]
        ok = got["status"] == "published" and refs_ok(got["workflowData"]["templates"]) and len(trs) == 1 and trs[0].get("active")
        print(f"   {'✓' if ok else '✗ VERIFICAR'} {name}: {got['status']} · gatilho {trs[0]['type'] if trs else '—'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
