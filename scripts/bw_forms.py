#!/usr/bin/env python3
"""Bluewater Brokerage (BurchTech agency): the website's forms into Bill's GHL (ClickUp "GHL Form Mapping").

    set -a; . <scratchpad>/burchtech.env; set +a      # BurchTech token, GHL_DUMP_DIR=dump/burchtech
    ./.venv/bin/python scripts/bw_forms.py plan
    ./.venv/bin/python scripts/bw_forms.py test --to pedro@poolprofits.com   # build in test mode + 1 POST per form
    ./.venv/bin/python scripts/bw_forms.py live                               # alerts go to Bill by SMS

bluewaterbrokerage.com (WordPress, Vik) e-mails every form to Bill; nothing reached GHL. One workflow per
form, each with its own inbound webhook. The site posts flat JSON (contract in docs/bluewater-form-mapping.md):
    route-calculator-gate     first_name, last_name, email, phone, business, city, report, talk, page
    route-calculator-figures  first_name, last_name, email + the 10 figures
    sellers-guide             first_name, last_name, email, opinion, page
    buyers-guide              first_name, last_name, email, register, page
    contact                   first_name, last_name, email, phone, message, page
    newsletter                email, page
Checkboxes arrive as "yes"/"no" and are kept in contact fields; the if/else reads those fields. Tags follow the
client's file (route-calculator, bluewater-report, wants-confidential-call) and the same style for the rest.
Cards go to "Marketing Pipeline" (Seller / Buyer / Other), like the account's own "Website Form Submitted".
Bill (the only user who sells) gets an SMS per lead and a task due today when someone asks to talk or for an
opinion of value, and for every contact-form message. Existing workflows, fields and tags are not touched.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import uuid

import requests

from _common import ROOT, load_dotenv

from cli_anything.gohighlevel.utils.agency import BACKEND, SERVICES, Agency

LOC = "M6eDjuSa3RdwukFl2rW2"           # Bluewater Brokerage
BILL = "ruPumLvAEYxeBXoHobu5"          # Bill Burch (user)
PIPELINE = "QGMHVVIqMh3DPyrsFHK0"      # Marketing Pipeline
STAGE = {"seller": "ff5800a3-5771-4cdc-9323-375f758b8bb5", "buyer": "0435d8b5-4136-47fc-aa4d-afc8bf4f0624",
         "other": "22f3b52f-714c-4719-b620-8f99a1e587e0"}
HOOK = "https://services.leadconnectorhq.com/hooks/{loc}/webhook-trigger/{tid}"
W = "{{inboundWebhookRequest.%s}}"

FIELDS = {  # name → dataType (contact custom fields this creates)
    "Route Report Opt-in": "TEXT", "Wants Confidential Call": "TEXT", "Wants Opinion of Value": "TEXT",
    "Buyer Registration Request": "TEXT", "Website Form Page": "TEXT", "Website Message": "LARGE_TEXT",
    "Route Monthly Billing": "TEXT", "Route Visits per Week": "TEXT", "Route Quality Score": "TEXT",
    "Route Multiple": "TEXT", "Route Value Low": "TEXT", "Route Value High": "TEXT",
    "Route Equipment Value": "TEXT", "Route Inventory Value": "TEXT", "Route Is Franchise": "TEXT",
    "Route Agreements": "TEXT",
}
FIGURES = {"monthly_billing": "Route Monthly Billing", "visits_per_week": "Route Visits per Week",
           "quality_score": "Route Quality Score", "multiple": "Route Multiple", "value_low": "Route Value Low",
           "value_high": "Route Value High", "equipment_value": "Route Equipment Value",
           "inventory_value": "Route Inventory Value", "is_franchise": "Route Is Franchise",
           "agreements": "Route Agreements"}
TAGS = ["route-calculator", "bluewater-report", "wants-confidential-call", "sellers-guide", "wants-opinion-of-value",
        "buyers-guide", "buyer-registered", "website-contact", "source-website"]


def nid() -> str:
    return str(uuid.uuid4())


# ── steps ────────────────────────────────────────────────────────────────

def contact(*keys: str) -> dict:
    std = {"first_name": ("firstName", "First Name"), "last_name": ("lastName", "Last Name"),
           "email": ("email", "Email"), "phone": ("phone", "Phone"), "business": ("companyName", "Business Name"),
           "city": ("city", "City")}
    return {"name": "Create / update contact", "type": "create_update_contact", "attributes": {
        "type": "create_update_contact",
        "fields": [{"field": std[k][0], "value": W % k, "title": std[k][1], "type": "text"} for k in keys]}}


def set_fields(cf: dict, pairs: dict[str, str]) -> dict:
    """pairs: payload key → custom field name."""
    return {"name": "Save form answers", "type": "update_contact_field", "attributes": {
        "type": "update_contact_field", "actionType": "update_field_data",
        "fields": [{"field": cf[name], "value": W % key, "title": name, "type": "text", "date": ""}
                   for key, name in pairs.items()]}}


def tag(*tags: str) -> dict:
    return {"name": "Add Tag " + ", ".join(tags), "type": "add_contact_tag",
            "attributes": {"tags": list(tags), "type": "add_contact_tag"}}


def card(stage: str, label: str) -> dict:
    return {"name": f"Card - {label}", "type": "create_opportunity", "attributes": {
        "fields": [], "type": "create_opportunity", "pipeline_id": PIPELINE, "pipeline_stage_id": STAGE[stage],
        "opportunity_name": "{{contact.name}} - " + label, "opportunity_source": "Website - " + label,
        "monetary_value": "", "opportunity_status": "open", "allow_backward": True}}


def alert(text: str, test_to: str | None) -> dict:
    """SMS to Bill (live) / the same text by e-mail to the tester (test mode, so Bill gets no test texts)."""
    if test_to:
        html = "".join(f'<p style="margin:0px">{line}</p>' for line in text.split("\n"))
        return {"name": "Alert Bill (TEST → e-mail)", "type": "internal_notification", "attributes": {
            "type": "email", "email": {"isCloned": False, "userType": "custom_email", "to": test_to,
                                       "subject": "[TEST Bluewater] " + text.split("\n")[0], "html": html,
                                       "attachments": []}}}
    return {"name": "SMS Bill", "type": "internal_notification", "attributes": {
        "type": "sms", "sms": {"body": text, "selectedUser": [BILL], "userType": "user", "attachments": []}}}


def task(title: str, body: str) -> dict:
    return {"name": "Task for Bill (due today)", "type": "task-notification", "attributes": {
        "title": title, "body": body, "assignedTo": BILL, "type": "task_notification",
        "dueDate": {"duration": 0, "unit": "days"}, "__customInputs__": {}}}


def yes_if(cf_id: str, label: str, yes: list, no: list) -> tuple:
    return ("if", cf_id, label, yes, no)


# ── tree → GHL templates ─────────────────────────────────────────────────

NEST = ["inboundWebhookRequest", "sheet", "datetime_formatter", "custom_webhook", "array_functions", "ivr_gather",
        "ivr_connect_call", "custom_code"]
IS_OPS = ["contact_reply", "inboundWebhookRequest", "custom_webhook", "custom_code", "contact_detail",
          "array_functions", "appointment", "service_booking"]


def build(chain: list, parent: str | None = None, prev: str | None = None) -> list[dict]:
    """Linear steps; an ("if", …) item may only be last (GHL branches do not join again)."""
    out, order = [], 0
    for item in chain:
        if isinstance(item, tuple):
            _, field, label, yes, no = item
            cond, ybr, nbr = nid(), nid(), nid()
            c = {"id": cond, "order": order, "name": label + "?", "type": "if_else", "cat": "conditions",
                 "nodeType": "condition-node", "comments": [], "next": [ybr, nbr],
                 "attributes": {"currentRecipeType": "CUSTOM", "operator": "and", "if": True, "conditionName": label,
                                "version": 2, "noneBranchName": "No", "branches": [{
                                    "id": ybr, "name": "Yes", "operator": "and", "showErrors": False,
                                    "branchNameError": "Branch name cannot be empty!",
                                    "segments": [{"__segmentId": nid(), "operator": "and", "conditions": [{
                                        "conditionType": "contact_detail", "conditionSubType": field,
                                        "conditionOperator": "==", "conditionValue": "yes", "__conditionId": nid(),
                                        "ifElseNodeId": "", "__customFieldType__": "standard", "isWait": False,
                                        "nestedDropdownTypes": NEST, "allowIsOperatorTypes": IS_OPS}]}]}]}}
            if prev:
                c["parentKey"] = prev
                if out:
                    out[-1]["next"] = cond
            if parent:
                c["parent"] = parent
            y = {"id": ybr, "parent": cond, "parentKey": cond, "order": order + 1, "name": "Yes", "type": "if_else",
                 "cat": "conditions", "sibling": [nbr], "comments": [], "nodeType": "branch-yes",
                 "attributes": {"if": False, "conditionName": "Condition", "operator": "and", "branches": []}}
            n = {"id": nbr, "parent": cond, "parentKey": cond, "order": order + 1, "name": "No", "type": "if_else",
                 "cat": "conditions", "sibling": [ybr], "comments": [], "nodeType": "branch-no",
                 "attributes": {"else": True}}
            out += [c, y, n]
            for br, steps in ((y, yes), (n, no)):
                sub = build(steps, br["id"], br["id"])
                if sub:
                    br["next"] = sub[0]["id"]
                out += sub
            return out
        s = dict(item, id=nid(), order=order)
        if prev:
            s["parentKey"] = prev
            if out:
                out[-1]["next"] = s["id"]
        if parent:
            s["parent"] = parent
        out.append(s)
        prev, order = s["id"], order + 1
    return out


def flows(cf: dict, test_to: str | None) -> dict[str, list]:
    who = "{{contact.name}}\nPhone: {{contact.phone}}\nEmail: {{contact.email}}"
    report = yes_if(cf["Route Report Opt-in"], "Bluewater Report opt-in", [tag("bluewater-report")], [])
    return {
        "Website - Route Calculator Lead": [
            contact("first_name", "last_name", "email", "phone", "business", "city"),
            set_fields(cf, {"report": "Route Report Opt-in", "talk": "Wants Confidential Call", "page": "Website Form Page"}),
            tag("route-calculator", "source-website"), card("seller", "Route Calculator"),
            alert("🧮 Route calculator lead\n" + who + "\nBusiness: {{contact.company_name}}\nCity: {{contact.city}}"
                  "\nWants a confidential call: " + W % "talk" + "\nBluewater Report: " + W % "report", test_to),
            yes_if(cf["Wants Confidential Call"], "Wants a confidential call",
                   [tag("wants-confidential-call"),
                    task("Call {{contact.name}} - confidential conversation (route calculator)",
                         "Asked for a confidential conversation about their business on the Route Value "
                         "Calculator. Phone: {{contact.phone}} · Email: {{contact.email}}"),
                    report], [report])],
        "Website - Route Calculator Figures": [
            contact("first_name", "last_name", "email"), set_fields(cf, FIGURES), tag("route-calculator")],
        "Website - Seller's Guide Download": [
            contact("first_name", "last_name", "email"),
            set_fields(cf, {"opinion": "Wants Opinion of Value", "page": "Website Form Page"}),
            tag("sellers-guide", "source-website"), card("seller", "Seller's Guide"),
            alert("📘 Seller's Guide download\n" + who + "\nWants an opinion of value: " + W % "opinion", test_to),
            yes_if(cf["Wants Opinion of Value"], "Wants an opinion of value",
                   [tag("wants-opinion-of-value"),
                    task("Opinion of value for {{contact.name}}",
                         "Downloaded the Seller's Guide and asked for a confidential opinion of value. "
                         "Email: {{contact.email}}")], [])],
        "Website - Buyer's Guide Download": [
            contact("first_name", "last_name", "email"),
            set_fields(cf, {"register": "Buyer Registration Request", "page": "Website Form Page"}),
            tag("buyers-guide", "source-website"), card("buyer", "Buyer's Guide"),
            alert("📗 Buyer's Guide download\n" + who + "\nRegister as a buyer: " + W % "register", test_to),
            yes_if(cf["Buyer Registration Request"], "Register as a buyer", [tag("buyer-registered")], [])],
        "Website - Contact Form": [
            contact("first_name", "last_name", "email", "phone"),
            set_fields(cf, {"message": "Website Message", "page": "Website Form Page"}),
            tag("website-contact", "source-website"), card("other", "Contact Form"),
            alert("✉️ Website contact form\n" + who + "\nMessage: " + W % "message", test_to),
            task("Reply to {{contact.name}} (website contact form)",
                 "Message: " + W % "message" + " · Phone: {{contact.phone}} · Email: {{contact.email}}")],
        "Website - Newsletter Signup": [
            contact("email"), set_fields(cf, {"page": "Website Form Page"}), tag("bluewater-report", "source-website")],
    }


SAMPLES = {  # one test POST per form (test mode)
    "Website - Route Calculator Lead": {"first_name": "TEST", "last_name": "Calculator", "email": "bw-test-calc@example.com",
                                        "phone": "+18435550101", "business": "Test Pool Co", "city": "Myrtle Beach, SC",
                                        "report": "yes", "talk": "yes", "page": "/route-calculator/"},
    "Website - Route Calculator Figures": {"first_name": "TEST", "last_name": "Calculator", "email": "bw-test-calc@example.com",
                                           "monthly_billing": "42000", "visits_per_week": "310", "quality_score": "6.4",
                                           "multiple": "10.2", "value_low": "410000", "value_high": "470000",
                                           "equipment_value": "85000", "inventory_value": "12000", "is_franchise": "no",
                                           "agreements": "Some signed", "page": "/route-calculator/"},
    "Website - Seller's Guide Download": {"first_name": "TEST", "last_name": "Seller Guide", "email": "bw-test-seller@example.com",
                                          "opinion": "yes", "page": "/resources/"},
    "Website - Buyer's Guide Download": {"first_name": "TEST", "last_name": "Buyer Guide", "email": "bw-test-buyer@example.com",
                                         "register": "no", "page": "/resources/"},
    "Website - Contact Form": {"first_name": "TEST", "last_name": "Contact", "email": "bw-test-contact@example.com",
                               "phone": "+18435550102", "message": "Test message from the website contact form.",
                               "page": "/contact/"},
    "Website - Newsletter Signup": {"email": "bw-test-news@example.com", "page": "/"},
}
EXPECT = {  # tags each sample must end with
    "Website - Route Calculator Lead": {"route-calculator", "source-website", "wants-confidential-call", "bluewater-report"},
    "Website - Route Calculator Figures": {"route-calculator"},
    "Website - Seller's Guide Download": {"sellers-guide", "source-website", "wants-opinion-of-value"},
    "Website - Buyer's Guide Download": {"buyers-guide", "source-website"},
    "Website - Contact Form": {"website-contact", "source-website"},
    "Website - Newsletter Signup": {"bluewater-report", "source-website"},
}


# ── apply ────────────────────────────────────────────────────────────────

def ensure_fields(a: Agency) -> dict[str, str]:
    have = {c["name"]: c["id"] for c in a.custom_fields(LOC)}
    for name, dtype in FIELDS.items():
        if name not in have:
            made = a.call("POST", SERVICES, f"/locations/{LOC}/customFields",
                          body={"name": name, "dataType": dtype, "model": "contact"})
            have[name] = (made.get("customField") or made)["id"]
            print(f"   + campo {name}")
    return have


def ensure_tags(a: Agency) -> None:
    have = {t["name"].lower() for t in a.tags(LOC)}
    for t in TAGS:
        if t not in have:
            a.call("POST", BACKEND, f"/workflow/{LOC}/tags/create", body={"tag": t})
            print(f"   + tag {t}")


def upsert(a: Agency, name: str, tpl: list[dict]) -> str:
    """Create (or update in place) the workflow, published, with one inbound webhook trigger. Returns the URL."""
    existing = {w["name"]: w["id"] for w in a.workflows(LOC)}
    wid = existing.get(name)
    bdir = ROOT / "backup" / "bluewater-brokerage"
    bdir.mkdir(parents=True, exist_ok=True)
    if wid:
        live = a.workflow(LOC, wid)
        (bdir / f"workflow-{wid}-{time.strftime('%Y%m%d-%H%M%S')}.json").write_text(json.dumps(live))
        version = live.get("version", 1)
    else:
        wid = (lambda r: r.get("id") or r.get("_id"))(a.call("POST", BACKEND, f"/workflow/{LOC}",
                                                             body={"name": name, "status": "draft"}))
        version = 1
    a.call("PUT", BACKEND, f"/workflow/{LOC}/{wid}", body={
        "name": name, "version": version, "status": "published", "allowMultiple": True,
        "allowMultipleOpportunity": True, "workflowData": {"templates": tpl}})
    hooks = [t for t in a.triggers(LOC, wid) if not t.get("deleted") and t["type"] == "inbound_webhook"]
    trig = {"type": "inbound_webhook", "name": "Website form (bluewaterbrokerage.com)", "masterType": "highlevel",
            "schedule_config": {}, "conditions": [], "workflowId": wid, "workflow_id": wid, "location_id": LOC,
            "actions": [{"workflow_id": wid, "type": "add_to_workflow"}], "targetActionId": tpl[0]["id"]}
    if hooks:
        tid = hooks[0]["id"]
        a.call("PUT", BACKEND, f"/workflow/{LOC}/trigger/{tid}", body={**trig, "id": tid})
    else:
        tid = a.call("POST", BACKEND, f"/workflow/{LOC}/trigger", body=trig)["id"]
        a.call("PUT", BACKEND, f"/workflow/{LOC}/trigger/{tid}", body={**trig, "id": tid})
    return HOOK.format(loc=LOC, tid=tid)


def check(a: Agency, name: str, email: str, cf: dict) -> list[str]:
    found = a.call("GET", SERVICES, "/contacts/", params={"locationId": LOC, "query": email}).get("contacts", [])
    if not found:
        return ["contato não criado"]
    c = a.call("GET", SERVICES, f"/contacts/{found[0]['id']}")["contact"]
    probs = []
    missing = EXPECT[name] - set(c.get("tags") or [])
    if missing:
        probs.append(f"faltam tags {sorted(missing)}")
    vals = {f["id"]: f.get("value") for f in c.get("customFields") or []}
    sample = SAMPLES[name]
    for key, field in {**FIGURES, "report": "Route Report Opt-in", "talk": "Wants Confidential Call",
                       "opinion": "Wants Opinion of Value", "register": "Buyer Registration Request",
                       "message": "Website Message"}.items():
        if key in sample and str(vals.get(cf[field])) != sample[key]:
            probs.append(f"{field} = {vals.get(cf[field])!r} (esperado {sample[key]!r})")
    if sample.get("phone") and (c.get("phone") or "") != sample["phone"]:
        probs.append(f"telefone {c.get('phone')!r}")
    return probs


def cleanup(a: Agency) -> None:
    for email in {s["email"] for s in SAMPLES.values()}:
        for c in a.call("GET", SERVICES, "/contacts/", params={"locationId": LOC, "query": email}).get("contacts", []):
            if c.get("email") == email:
                for o in a.call("GET", SERVICES, "/opportunities/search",
                                params={"location_id": LOC, "contact_id": c["id"]}).get("opportunities", []):
                    a.call("DELETE", SERVICES, f"/opportunities/{o['id']}")
                a.call("DELETE", SERVICES, f"/contacts/{c['id']}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("mode", choices=["plan", "test", "live"])
    parser.add_argument("--to", help="test: inbox that gets Bill's alerts instead of his phone")
    args = parser.parse_args()
    load_dotenv()
    a = Agency()
    if a.company_id() != "syjenoyGz1jZ3ndDPkCm":
        sys.exit("token não é o da BurchTech (carregar burchtech.env)")
    if args.mode == "plan":
        cf = {name: f"<{name}>" for name in FIELDS}
        for name, chain in flows(cf, None).items():
            tpl = build(chain)
            print(f"== {name}: {len(tpl)} nós · " + " → ".join(s["name"] for s in tpl if s.get("nodeType") is None))
        return 0
    if args.mode == "test" and not args.to:
        parser.error("--to is required in test mode")
    print("== campos e tags")
    cf = ensure_fields(a)
    ensure_tags(a)
    urls, bad = {}, 0
    for name, chain in flows(cf, args.to if args.mode == "test" else None).items():
        urls[name] = upsert(a, name, build(chain))
        print(f"   ✓ {name} publicado")
    if args.mode == "test":
        cleanup(a)
        time.sleep(5)
        for name, body in SAMPLES.items():
            r = requests.post(urls[name], json=body, timeout=30)
            print(f"   POST {name}: HTTP {r.status_code}")
            time.sleep(4 if "Lead" in name else 1)
        time.sleep(40)
        for name in SAMPLES:
            probs = check(a, name, SAMPLES[name]["email"], cf)
            bad += bool(probs)
            print(f"   {'✓' if not probs else '✗'} {name}" + (f": {probs}" if probs else ""))
    (ROOT / "backup" / "bluewater-brokerage" / "webhook-urls.json").write_text(json.dumps(urls, indent=1))
    print("\nURLs:")
    for name, url in urls.items():
        print(f"   {name}: {url}")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
