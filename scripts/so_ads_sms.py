#!/usr/bin/env python3
"""Southern: texts to the Google Ads line (972) 632-3259 become leads (Val, 27/10: SMS asset in Google Ads).

    ./.venv/bin/python scripts/so_ads_sms.py plan
    ./.venv/bin/python scripts/so_ads_sms.py test --to pedro@poolprofits.com
    ./.venv/bin/python scripts/so_ads_sms.py apply

GHL already receives the texts (the number is ours, SMS-capable) and creates/updates the contact by itself. Workflow
"Google Ads SMS - New Lead": trigger "Customer Replied", channel SMS, In phone number = the Google Ads line; one if/else:
  Spam / DND             → nothing.
  Sent in the last 24 h  → nothing (every text of a conversation fires the trigger: one alert per lead per day).
  Current customer       → tag, alerts to Brett marked existing customer; no card.
  New lead               → tags `google ads - sms` + `new lead` + `adwords`, owner Brett, card in Pool Leads → New Lead
                           (source "Google Ads - SMS"), Google Ads conversion, text + email to Brett with the message,
                           task "Reply to the Google Ads text lead" due today (the API takes days only).
Every branch: wait 1 day → remove the 24 h tag. No automatic reply to the lead (not asked; easy to add).
test: a temporary copy (alerts by email to --to, no text to Brett, no conversion), contacts enrolled through the API
for every branch; checks tags/cards/owner/task and the repeat guard, then deletes everything.
"""
from __future__ import annotations

import argparse
import json
import sys
import time

from _common import ROOT, load_dotenv
from ps_ads_forms import P, chain, cond, if_else, outline
from pp_source_tags import refs_ok

from cli_anything.gohighlevel.utils.agency import BACKEND, SERVICES, Agency

LOC = "SylIOZiJ6YQsZOypUI8Z"
LINE = "+19726323259"
BRETT, BRETT_EMAIL = "kEgTwHiRvCqAUP63kQXN", "brett@southernpoolandoutdoors.com"
PIPELINE, NEW_LEAD = "O2ckLSY6ANgJ41oVEgS7", None  # stage looked up by name
FLOW, FOLDER_OF = "Google Ads SMS - New Lead", "AdWords Form - New Lead"
TAG, RECENT = "google ads - sms", "google ads sms 24h"
SPAM, CUSTOMER = ["spam", "dnd"], ["existing customer", "recurring customer", "won"]
BDIR = ROOT / "backup" / "southern-pool-outdoors"


def build(stage: str, test_to: str | None = None) -> list[dict]:
    def alerts(customer: bool) -> list:
        head = "📱 NEW GOOGLE ADS TEXT LEAD" + (" (EXISTING CUSTOMER)" if customer else "")
        email = ("internal_notification", "Email Brett", {"type": "email", "email": {
            "userType": "custom_email", "to": test_to or BRETT_EMAIL,
            "subject": ("[TEST] " if test_to else "") + "📱 New Google Ads text lead: {{contact.name}} {{contact.phone}}",
            "html": P.format(head + ":") + "".join(P.format(f"<b>{k}:</b> {v}") for k, v in [
                ("Name", "{{contact.name}}"), ("Phone", "{{contact.phone}}"), ("Message", "{{message.body}}")]) +
            P.format("Reply from the Conversations tab in the CRM (it goes out from the Google Ads number).")}})
        if test_to:
            return [email]
        return [("internal_notification", "Text Brett", {"type": "sms", "sms": {
            "body": f"{head}\n\nName: {{{{contact.name}}}}\nPhone: {{{{contact.phone}}}}\nMessage: {{{{message.body}}}}\n\n"
                    "Reply from the CRM so it goes out from the Google Ads number.",
            "userType": "user", "selectedUser": [BRETT], "attachments": []}}), email]

    release = [("wait", "Wait 1 day", {"type": "time", "startAfter": {"type": "days", "value": 1, "when": "after"},
                                       "name": "Wait 1 day", "cat": "", "isHybridAction": True, "hybridActionType": "wait",
                                       "convertToMultipath": False, "transitions": []}),
               ("remove_contact_tag", "Remove 24 h tag", {"type": "remove_contact_tag", "tags": [RECENT]})]
    tags = ("add_contact_tag", "Add Tags", {"type": "add_contact_tag", "tags": [TAG, "new lead", "adwords", RECENT]})
    owner = ("assign_user", "Assign to Brett", {"type": "assign_user", "only_unassigned_contact": True,
                                                "traffic_split": "equally", "user_list": [BRETT],
                                                "traffic_weightage": {BRETT: 1}, "total_index": 1,
                                                "traffic_index": [{"id": BRETT, "indexes": [1]}]})
    card = ("create_opportunity", "Card in New Lead", {
        "fields": [], "type": "create_opportunity", "pipeline_id": PIPELINE, "pipeline_stage_id": stage,
        "opportunity_name": "{{contact.name}}", "opportunity_source": "Google Ads - SMS", "monetary_value": "",
        "opportunity_status": "open"})
    conversion = ("google_adword", "Google Ads conversion", {
        "type": "google_adword", "currency": "USD", "conversion_value": "1", "conversion_type": "", "conversion_name": "",
        "conversion_action_id": "", "customMapping": {"gclid": "{{contact.attributionSource.gclid}}"},
        "isCustomMappingEnabled": True})
    task = ("task-notification", "Task: reply to the text lead", {
        "type": "task_notification", "title": "Reply to Google Ads text lead: {{contact.name}} {{contact.phone}}",
        "body": "<p style=\"margin:0px\">New text from the Google Ads number: {{message.body}}</p>"
                "<p style=\"margin:0px\">Reply from Conversations and move the card down the pipeline.</p>",
        "assignedTo": BRETT, "dueDate": {"duration": 0, "unit": "days"}})
    lead = [tags, owner, card, *([] if test_to else [conversion]), *alerts(False), task, *release]
    customer = [("add_contact_tag", "Add Tags", {"type": "add_contact_tag", "tags": [TAG, RECENT]}), *alerts(True),
                *release]
    nodes, _ = if_else("Route the text", [
        ("Spam / DND", [cond("tags", "index-of-true", [t]) for t in SPAM], []),
        ("Sent in the last 24 h", [cond("tags", "index-of-true", [RECENT])], []),
        ("Current customer", [cond("tags", "index-of-true", [t]) for t in CUSTOMER], customer),
    ], "New lead", lead)
    return nodes


def trigger(wid: str, first: str) -> dict:
    return {"type": "customer_reply", "name": "Customer Replied", "masterType": "highlevel", "schedule_config": {},
            "conditions": [{"operator": "==", "field": "message.type", "value": 2, "title": "Reply channel", "type": "select"},
                           {"operator": "contains-any", "field": "inbound_number", "value": [LINE], "title": "In phone number",
                            "type": "multiselect", "id": "inbound-twilio-number"}],
            "workflowId": wid, "workflow_id": wid, "location_id": LOC,
            "actions": [{"workflow_id": wid, "type": "add_to_workflow"}], "targetActionId": first}


def create(a: Agency, name: str, parent: str | None, tpl: list[dict]) -> str:
    res = a.call("POST", BACKEND, f"/workflow/{LOC}", body={"name": name, "parentId": parent, "status": "draft"})
    wid = res.get("id") or res.get("_id")
    a.call("PUT", BACKEND, f"/workflow/{LOC}/{wid}", body={"name": name, "version": 1, "status": "draft", "parentId": parent,
                                                         "allowMultiple": True, "workflowData": {"templates": tpl}})
    return wid


def publish(a: Agency, wid: str) -> dict:
    live = a.workflow(LOC, wid)
    a.call("PUT", BACKEND, f"/workflow/{LOC}/{wid}", body={
        "name": live["name"], "version": live.get("version", 1), "status": "published", "parentId": live.get("parentId"),
        "allowMultiple": True, "workflowData": {"templates": live["workflowData"]["templates"]}})
    time.sleep(3)
    return a.workflow(LOC, wid)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("mode", choices=["plan", "test", "apply"])
    parser.add_argument("--to")
    args = parser.parse_args()
    if args.mode == "test" and not args.to:
        parser.error("--to is required in test mode")
    load_dotenv()
    a = Agency()
    if not a.location(LOC)["name"].startswith("Southern"):
        sys.exit("sub-conta errada")
    pipe = next(p for p in a.pipelines(LOC) if p["id"] == PIPELINE)
    stage = next(s["id"] for s in pipe["stages"] if "new lead" in s["name"].lower())
    flows = {w["name"]: w["id"] for w in a.workflows(LOC)}
    folder = a.workflow(LOC, flows[FOLDER_OF]).get("parentId")
    if args.mode == "plan":
        print(f"   {FLOW}: {'existe' if FLOW in flows else 'cria'} · gatilho SMS recebido em {LINE}\n{outline(build(stage))}")
        return 0
    for t in (TAG, RECENT):
        try:
            a.call("POST", BACKEND, f"/workflow/{LOC}/tags/create", body={"tag": t})
        except Exception:  # noqa: BLE001 — already exists
            pass
    if args.mode == "test":
        wid = create(a, f"ZZ TEST {FLOW}", folder, build(stage, args.to))
        publish(a, wid)
        ts, made, bad = int(time.time()), {}, 0
        for case, tags in (("new", []), ("customer", ["existing customer"]), ("spam", ["spam"])):
            made[case] = a.call("POST", SERVICES, "/contacts/", body={
                "locationId": LOC, "firstName": "ZZ Test", "lastName": f"sms {case}", "tags": tags,
                "email": args.to.replace("@", f"+so-sms-{case}-{ts}@")})["contact"]["id"]
        time.sleep(3)
        for cid in made.values():
            a.call("POST", SERVICES, f"/contacts/{cid}/workflow/{wid}", body={})
        time.sleep(30)
        a.call("POST", SERVICES, f"/contacts/{made['new']}/workflow/{wid}", body={})  # a second text
        time.sleep(30)
        want = {"new": ({TAG, "new lead", "adwords", RECENT}, 1, True), "customer": ({TAG, RECENT}, 0, False),
                "spam": (set(), 0, False)}
        for case, cid in made.items():
            c = a.call("GET", SERVICES, f"/contacts/{cid}")["contact"]
            opps = a.call("GET", SERVICES, "/opportunities/search", params={"location_id": LOC, "contact_id": cid}).get("opportunities", [])
            tasks = a.call("GET", SERVICES, f"/contacts/{cid}/tasks").get("tasks", [])
            exp_tags, exp_cards, exp_owner = want[case]  # owner: the account's own flow assigns Brett to every contact
            ok = exp_tags <= set(c.get("tags", [])) and len(opps) == exp_cards and \
                (c.get("assignedTo") == BRETT or not exp_owner) and \
                len(tasks) == (1 if case == "new" else 0) and \
                (case != "spam" or TAG not in c.get("tags", []))
            bad += not ok
            print(f"   {'✓' if ok else '✗'} {case}: tags {sorted(c.get('tags', []))} · cards {[o.get('source') for o in opps]} · "
                  f"dono {'Brett' if c.get('assignedTo') == BRETT else c.get('assignedTo')} · tarefas {len(tasks)}")
            for o in opps:
                a.call("DELETE", SERVICES, f"/opportunities/{o['id']}")
            a.call("DELETE", SERVICES, f"/contacts/{cid}")
        live = a.workflow(LOC, wid)
        a.call("PUT", BACKEND, f"/workflow/{LOC}/{wid}", body={"name": live["name"], "version": live.get("version", 1),
               "status": "draft", "workflowData": {"templates": live["workflowData"]["templates"]}})
        a.call("DELETE", BACKEND, f"/workflow/{LOC}/{wid}")
        print(f"   limpo. Esperado em {args.to}: 2 e-mails (novo: 1, apesar de 2 textos; cliente: 1), nenhum do spam.")
        return 1 if bad else 0
    if FLOW in flows:
        print(f"   {FLOW}: já existe")
        return 0
    tpl = build(stage)
    wid = create(a, FLOW, folder, tpl)
    trig = trigger(wid, tpl[0]["id"])
    t = a.call("POST", BACKEND, f"/workflow/{LOC}/trigger", body=trig)
    a.call("PUT", BACKEND, f"/workflow/{LOC}/trigger/{t['id']}", body={**trig, "id": t["id"]})
    got = publish(a, wid)
    trs = [x for x in a.triggers(LOC, wid) if not x.get("deleted")]
    ok = got["status"] == "published" and refs_ok(got["workflowData"]["templates"]) and len(trs) == 1 and trs[0].get("active")
    print(f"   {'✓' if ok else '✗ VERIFICAR'} {FLOW}: {got['status']} · {len(tpl)} passos · gatilho {LINE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
