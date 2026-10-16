#!/usr/bin/env python3
"""Chatbot test sites (Atif/Frank, 16/10): an inbound webhook per test sub-account for lead capture.

    ./.venv/bin/python scripts/pp_chatbot_webhook.py            # plan
    ./.venv/bin/python scripts/pp_chatbot_webhook.py --apply    # create + publish + one test POST each

Uses the two existing test sub-accounts (no new, billable sub-account): "Test Snapshot" and "test inc".
The chatbot POSTs JSON to the URL printed here:
    {"first_name", "last_name", "email", "phone", "address", "message", "page", "site"}
→ contact (create/update), tags "chatbot lead" + "new lead", card in the account's pipeline (first
"New Lead" stage, source "Chatbot"), e-mail to NOTIFY with every field. Same shape as Passion's live
"Website Webhook Lead To Pipeline" (inbound_webhook trigger + create_update_contact).
"""
from __future__ import annotations

import argparse
import time
import uuid

import requests

from _common import load_dotenv

from cli_anything.gohighlevel.utils.agency import BACKEND, SERVICES, Agency

SITES = {"hmzX5j1dPhOQKX2dH4kf": "Chatbot test site 1", "6lzYFANJTxKkAUA8Z18b": "Chatbot test site 2"}
NAME = "Chatbot Lead (Webhook)"
TAGS = ["chatbot lead", "new lead"]
NOTIFY = "atif@poolprofits.com"
FIELDS = [("firstName", "first_name", "First Name"), ("lastName", "last_name", "Last Name"),
          ("email", "email", "Email"), ("phone", "phone", "Phone"), ("address1", "address", "Address")]
P = '<p style="margin:0px;font-family:verdana,geneva,sans-serif;font-size:15px;">{}</p>'


def lead_stage(pipeline: dict) -> dict:
    """"New Lead" stage (test inc's first stage is "Current Customer"), else the first one."""
    return next((s for s in pipeline["stages"] if "new lead" in s["name"].lower()), pipeline["stages"][0])


def steps(pipeline: dict, site: str) -> list[dict]:
    w = "{{inboundWebhookRequest.%s}}"
    html = P.format(f"<strong>🤖 NEW CHATBOT LEAD — {site}</strong>") + "<br/>" + "".join(P.format(x) for x in [
        "Name: {{contact.name}}", "Phone: {{contact.phone}}", "Email: {{contact.email}}",
        "Address: " + w % "address", "Question / message: " + w % "message", "Page: " + w % "page",
        "Site: " + w % "site"])
    out = [
        {"name": "Create Contact", "type": "create_update_contact", "attributes": {
            "type": "create_update_contact",
            "fields": [{"field": f, "value": w % k, "title": t, "type": "text"} for f, k, t in FIELDS]}},
        {"name": "Add Tag chatbot lead", "type": "add_contact_tag",
         "attributes": {"tags": TAGS, "type": "add_contact_tag"}},
        {"name": "Create New Lead", "type": "create_opportunity", "attributes": {
            "fields": [], "type": "create_opportunity", "pipeline_id": pipeline["id"],
            "pipeline_stage_id": lead_stage(pipeline)["id"], "opportunity_name": "{{contact.name}}",
            "opportunity_source": "Chatbot", "monetary_value": "", "opportunity_status": "open"}},
        {"name": "Email Atif", "type": "internal_notification", "attributes": {"type": "email", "email": {
            "isCloned": False, "userType": "custom_email", "to": NOTIFY, "attachments": [],
            "subject": "🤖 Chatbot lead ({site}): {{contact.name}}".replace("{site}", site), "html": html}}},
    ]
    for i, s in enumerate(out):
        s.update(id=str(uuid.uuid4()), order=i)
        if i:
            s["parentKey"] = out[i - 1]["id"]
            out[i - 1]["next"] = s["id"]
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    load_dotenv()
    a = Agency()
    bad = 0
    for loc, site in SITES.items():
        flows = {w["name"]: w["id"] for w in a.workflows(loc)}
        pipe = a.pipelines(loc)[0]
        print(f"== {site} ({loc}): pipeline '{pipe['name']}' / '{lead_stage(pipe)['name']}'")
        if NAME in flows:
            trs = [t for t in a.triggers(loc, flows[NAME]) if not t.get("deleted") and t["type"] == "inbound_webhook"]
            for t in trs:
                print(f"   já existe · URL https://services.leadconnectorhq.com/hooks/{loc}/webhook-trigger/{t['id']}")
            continue
        if not args.apply:
            print(f"   + {NAME}: webhook → contato, tags {TAGS}, card, e-mail para {NOTIFY}")
            continue
        for tag in TAGS:
            try:
                a.call("POST", BACKEND, f"/workflow/{loc}/tags/create", body={"tag": tag})
            except Exception:  # noqa: BLE001 — already exists
                pass
        res = a.call("POST", BACKEND, f"/workflow/{loc}", body={"name": NAME, "status": "draft"})
        wid = res.get("id") or res.get("_id")
        tpl = steps(pipe, site)
        a.call("PUT", BACKEND, f"/workflow/{loc}/{wid}", body={
            "name": NAME, "version": 1, "status": "published", "allowMultiple": True,
            "workflowData": {"templates": tpl}})
        trig = {"type": "inbound_webhook", "name": f"Inbound Webhook - {site}", "masterType": "highlevel",
                "schedule_config": {}, "conditions": [], "workflowId": wid, "workflow_id": wid, "location_id": loc,
                "actions": [{"workflow_id": wid, "type": "add_to_workflow"}], "targetActionId": tpl[0]["id"]}
        t = a.call("POST", BACKEND, f"/workflow/{loc}/trigger", body=trig)
        a.call("PUT", BACKEND, f"/workflow/{loc}/trigger/{t['id']}", body={**trig, "id": t["id"]})
        url = f"https://services.leadconnectorhq.com/hooks/{loc}/webhook-trigger/{t['id']}"
        time.sleep(5)
        email = f"chatbot-test-{loc[:6].lower()}@example.com"
        r = requests.post(url, json={"first_name": "TEST", "last_name": "Chatbot setup (Pool Profits)", "email": email,
                                     "phone": "+14805550199", "address": "123 Test St, Scottsdale, AZ",
                                     "message": "Test lead from the chatbot setup — please ignore.",
                                     "page": "https://example.com/", "site": site}, timeout=30)
        time.sleep(20)
        found = a.call("GET", SERVICES, "/contacts/", params={"locationId": loc, "query": email}).get("contacts", [])
        c = a.call("GET", SERVICES, f"/contacts/{found[0]['id']}")["contact"] if found else {}
        ops = a.call("GET", SERVICES, "/opportunities/search",
                     params={"location_id": loc, "contact_id": c["id"]}).get("opportunities", []) if c else []
        ok = r.ok and set(TAGS) <= set(c.get("tags") or []) and any(o.get("source") == "Chatbot" for o in ops)
        bad += not ok
        print(f"   {'✓' if ok else '✗ VERIFICAR'} publicado · teste HTTP {r.status_code} · tags {c.get('tags')} · card {len(ops)}")
        print(f"   URL: {url}")
        if c:  # keep the test account clean
            a.call("DELETE", SERVICES, f"/contacts/{c['id']}")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
