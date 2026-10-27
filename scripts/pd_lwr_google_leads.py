#!/usr/bin/env python3
"""Pool Duck Lakewood Ranch: Google Ads lead form + Google Ads SMS into GHL (Val, 27/10). Pool Duck token.

    set -a; . <poolduck.env>; set +a
    ./.venv/bin/python scripts/pd_lwr_google_leads.py plan
    ./.venv/bin/python scripts/pd_lwr_google_leads.py test --to pedro@poolprofits.com
    ./.venv/bin/python scripts/pd_lwr_google_leads.py apply

"Google Ads Lead Form - Qualified Lead": trigger Google Lead Form Submitted (form "Weekly pool service done right"
mapped + Active in the Google Lead Ads app). The app (connected by Val 27/10) leaves location.googleAdwordsId empty, so
the trigger has no ad-account filter (the location has one ad account); the API accepts it.
"Google Ads SMS - New Lead": trigger Customer Replied, SMS, In phone number = the Google Ads line +1 941-541-5942.
Both: one if/else first — Spam / DND → nothing; already sent in the last 24 h → nothing (every text of a conversation
fires the SMS trigger); current customer → alert marked existing customer, no card; new lead → tags, card in "Leads -->
Sales Pipeline" / Lead, SMS alert to Kenton + Pool Duck Service (same as the AdWords/Facebook form alerts); the lead form
lead also gets the Facebook flow's text ("we will call you in the next few minutes"). Every branch: wait 1 day → remove the
24 h tag.
test: temporary copies (alert by email to --to instead of the texts to Kenton/Service; no text to the lead), contacts
enrolled through the API for every branch; checks tags/cards and the repeat guard, then deletes everything.
"""
from __future__ import annotations

import argparse
import json
import sys
import time

from _common import load_dotenv
from ps_ads_forms import P, cond, if_else, outline, tags, wait_day
from pp_source_tags import refs_ok

from cli_anything.gohighlevel.utils.agency import BACKEND, SERVICES, Agency

LOC = "MosKIX4oux96vchwHZ5W"
LINE = "+19415415942"
ALERT_TO = ["Fpwm492Y2wyKFa0xJgVC", "DZkEc4SNZd1bAeBiT2LG"]  # Kenton, Pool Duck Service
PIPELINE, LEAD = "bBmO8YBJXxiKgEJEN3Ol", "f6512503-5228-4e2e-a9e1-c1dd7e8f232e"
FOLDER_OF = "Google AdWords - Qualified Lead (Form Fill)"
SPAM = ["spam", "spam likely", "dnd"]
CUSTOMER = ["active residential client", "new residential client", "pool duck customer", "turtle rock"]
LEAD_TEXT = ("Hi {{contact.first_name}}, this is Pool Duck in Lakewood Ranch. Got your request for pool service. We will "
             "call you in the next few minutes from this number. If now is bad, reply with a better time, and we will "
             "work around you.")

FLOWS = [
    {"key": "form", "flow": "Google Ads Lead Form - Qualified Lead", "source": "Google Ads - Lead Form",
     "tags": ["new lead", "google adwords", "google ads lead form", "lakewood ranch"], "recent": "google ads lead form 24h",
     "title": "New Lead from Google Ads Lead Form for Pool Duck Lakewood Ranch",
     "body": "\n\nName: {{contact.name}}\nPhone: {{contact.phone}}\nEmail: {{contact.email}}\nZip: {{contact.postal_code}}"},
    {"key": "sms", "flow": "Google Ads SMS - New Lead", "source": "Google Ads - SMS",
     "tags": ["new lead", "google adwords", "google ads - sms", "lakewood ranch"], "recent": "google ads sms 24h",
     "title": "New Lead from Google Ads TEXT for Pool Duck Lakewood Ranch",
     "body": "\n\nName: {{contact.name}}\nPhone: {{contact.phone}}\nMessage: {{message.body}}\n\nReply to them from the "
             "Google Ads line (941) 541-5942 in the GHL app."},
]


def alert(f: dict, customer: bool, test_to: str | None) -> tuple[str, str, dict]:
    title = f["title"] + (" (EXISTING CUSTOMER)" if customer else "")
    if test_to:
        return ("internal_notification", "Email tester", {"type": "email", "email": {
            "userType": "custom_email", "to": test_to, "subject": title,
            "html": P.format(title + f["body"].replace("\n", "<br>"))}})
    return ("internal_notification", "Text Kenton + Service", {"type": "sms", "sms": {
        "body": title + f["body"], "selectedUser": ALERT_TO, "userType": "user", "attachments": []}})


def build(f: dict, test_to: str | None = None) -> list[dict]:
    release = [wait_day(), ("remove_contact_tag", "Remove 24 h tag", {"type": "remove_contact_tag", "tags": [f["recent"]]})]
    card = ("create_opportunity", "Card in Lead", {
        "fields": [], "type": "create_opportunity", "pipeline_id": PIPELINE, "pipeline_stage_id": LEAD,
        "opportunity_name": "{{contact.name}}", "opportunity_source": f["source"], "monetary_value": "150.00",
        "opportunity_status": "open"})
    reply = [("sms", "Text the lead", {"body": LEAD_TEXT, "attachments": []})] if f["key"] == "form" and not test_to else []
    lead = [tags([*f["tags"], f["recent"]]), card, alert(f, False, test_to), *reply, *release]
    customer = [tags([t for t in f["tags"] if t != "new lead"] + [f["recent"]]), alert(f, True, test_to), *release]
    nodes, _ = if_else("Route the lead", [
        ("Spam / DND", [cond("tags", "index-of-true", [t]) for t in SPAM], []),
        ("Sent in the last 24 h", [cond("tags", "index-of-true", [f["recent"]])], []),
        ("Current customer", [cond("tags", "index-of-true", [t]) for t in CUSTOMER], customer),
    ], "New lead", lead)
    return nodes


def trigger(f: dict, wid: str, first: str, loc: dict) -> dict | None:
    if f["key"] == "sms":
        cond_ = [{"operator": "==", "field": "message.type", "value": 2, "title": "Reply channel", "type": "select"},
                 {"operator": "contains-any", "field": "inbound_number", "value": [LINE], "title": "In phone number",
                  "type": "multiselect", "id": "inbound-twilio-number"}]
        kind, name, master = "customer_reply", "Customer Replied", "highlevel"
    else:
        # the Google Lead Ads app (27/10) leaves location.googleAdwordsId empty: no filter (one ad account here)
        cond_ = [{"field": "adAccountId", "operator": "==", "value": loc["googleAdwordsId"], "id": "adAccountId",
                  "type": "select"}] if loc.get("googleAdwordsId") else []
        kind, name, master = "google_lead_form_submitted", "Google Lead Form Submitted", "internal"
    return {"type": kind, "name": name, "masterType": master, "schedule_config": {}, "conditions": cond_,
            "workflowId": wid, "workflow_id": wid, "location_id": LOC,
            "actions": [{"workflow_id": wid, "type": "add_to_workflow"}], "targetActionId": first}


def create(a: Agency, name: str, parent: str | None, tpl: list[dict]) -> str:
    res = a.call("POST", BACKEND, f"/workflow/{LOC}", body={"name": name, "parentId": parent, "status": "draft"})
    wid = res.get("id") or res.get("_id")
    a.call("PUT", BACKEND, f"/workflow/{LOC}/{wid}", body={"name": name, "version": 1, "status": "draft", "parentId": parent,
                                                         "allowMultiple": True, "workflowData": {"templates": tpl}})
    return wid


def set_status(a: Agency, wid: str, status: str) -> dict:
    live = a.workflow(LOC, wid)
    a.call("PUT", BACKEND, f"/workflow/{LOC}/{wid}", body={
        "name": live["name"], "version": live.get("version", 1), "status": status, "parentId": live.get("parentId"),
        "allowMultiple": True, "workflowData": {"templates": live["workflowData"]["templates"]}})
    time.sleep(3)
    return a.workflow(LOC, wid)


def test(a: Agency, folder: str | None, to: str) -> int:
    stamp, bad = int(time.time()), 0
    for f in FLOWS:
        wid = create(a, f"ZZ TEST {f['flow']}", folder, build(f, to))
        set_status(a, wid, "published")
        made = {}
        for case, extra in (("new", []), ("customer", ["active residential client"]), ("spam", ["spam likely"])):
            made[case] = a.call("POST", SERVICES, "/contacts/", body={
                "locationId": LOC, "firstName": "ZZ Test", "lastName": f"{f['key']} {case}", "tags": extra,
                "email": to.replace("@", f"+lwr-{f['key']}-{case}-{stamp}@")})["contact"]["id"]
        time.sleep(3)
        for cid in made.values():
            a.call("POST", SERVICES, f"/contacts/{cid}/workflow/{wid}", body={})
        time.sleep(30)
        a.call("POST", SERVICES, f"/contacts/{made['new']}/workflow/{wid}", body={})  # a second submit / text
        time.sleep(30)
        want = {"new": (set(f["tags"]) | {f["recent"]}, 1), "customer": (set(f["tags"]) - {"new lead"}, 0), "spam": (set(), 0)}
        for case, cid in made.items():
            c = a.call("GET", SERVICES, f"/contacts/{cid}")["contact"]
            tg = set(c.get("tags") or [])
            opps = a.call("GET", SERVICES, "/opportunities/search", params={"location_id": LOC, "contact_id": cid}).get("opportunities", [])
            exp, cards = want[case]
            ok = exp <= tg and len(opps) == cards and (case != "spam" or "google adwords" not in tg) and \
                all(o.get("source") == f["source"] for o in opps)
            bad += not ok
            print(f"   {'✓' if ok else '✗'} {f['key']}/{case}: tags {sorted(tg)} · cards {[o.get('source') for o in opps]}")
            for o in opps:
                a.call("DELETE", SERVICES, f"/opportunities/{o['id']}")
            a.call("DELETE", SERVICES, f"/contacts/{cid}")
        set_status(a, wid, "draft")
        a.call("DELETE", BACKEND, f"/workflow/{LOC}/{wid}")
    print(f"   limpo. Esperado em {to}: por fluxo 1 alerta do novo (não 2), 1 do cliente (EXISTING CUSTOMER), 0 do spam.")
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
    loc = a.location(LOC)
    if loc["name"] != "Pool Duck Lakewood Ranch":
        sys.exit("sub-conta errada (token da Pool Duck?)")
    flows = {w["name"]: w["id"] for w in a.workflows(LOC)}
    folder = a.workflow(LOC, flows[FOLDER_OF]).get("parentId")
    print(f"   Google Ads no GHL da LWR: {loc.get('googleAdwordsId') or 'NÃO conectado'}")
    if args.mode == "plan":
        for f in FLOWS:
            print(f"   {f['flow']}: {'existe' if f['flow'] in flows else 'cria'}\n{outline(build(f))}")
        return 0
    for t in {"google ads lead form", "google ads - sms", *(f["recent"] for f in FLOWS)}:
        try:
            a.call("POST", BACKEND, f"/workflow/{LOC}/tags/create", body={"tag": t})
        except Exception:  # noqa: BLE001 — already exists
            pass
    if args.mode == "test":
        return test(a, folder, args.to)
    for f in FLOWS:
        if f["flow"] in flows:
            wid = flows[f["flow"]]
            tpl = a.workflow(LOC, wid)["workflowData"]["templates"]
        else:
            tpl = build(f)
            wid = create(a, f["flow"], folder, tpl)
        if [t for t in a.triggers(LOC, wid) if not t.get("deleted")]:
            print(f"   {f['flow']}: já tem gatilho ({a.workflow(LOC, wid)['status']})")
            continue
        first = next(s["id"] for s in tpl if not s.get("parentKey") and not s.get("parent"))
        trig = trigger(f, wid, first, loc)
        if trig is None:
            print(f"   {f['flow']}: criado em draft, sem gatilho (falta conectar o Google Ads no GHL da LWR)")
            continue
        t = a.call("POST", BACKEND, f"/workflow/{LOC}/trigger", body=trig)
        a.call("PUT", BACKEND, f"/workflow/{LOC}/trigger/{t['id']}", body={**trig, "id": t["id"]})
        got = set_status(a, wid, "published")
        trs = [x for x in a.triggers(LOC, wid) if not x.get("deleted")]
        ok = got["status"] == "published" and refs_ok(got["workflowData"]["templates"]) and len(trs) == 1 and trs[0].get("active")
        print(f"   {'✓' if ok else '✗ VERIFICAR'} {f['flow']}: {got['status']} · gatilho {trs[0]['type'] if trs else '-'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
