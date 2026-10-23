#!/usr/bin/env python3
"""The Pool Shack: 2 Google Ads landing pages (Val/Atif brief, 23/10). One form per page, its tags and its lead workflow.

    ./.venv/bin/python scripts/ps_ads_forms.py plan
    ./.venv/bin/python scripts/ps_ads_forms.py fields                      # custom fields + tags only
    ./.venv/bin/python scripts/ps_ads_forms.py test --to pedro@poolprofits.com
    ./.venv/bin/python scripts/ps_ads_forms.py apply                       # forms + published workflows

Forms "GOOGLE ADS – WEEKLY" and "GOOGLE ADS – REPAIRS", built from the newest version of "Landing Page - Optin Form"
(same look, Terms/Privacy header): Full Name, Phone (US country picker), Email, Property Address (search), ZIP Code, all
required; Repairs adds "Service Requested" (dropdown: pumps, filters, heaters, automation, installation/upgrade, other)
and an optional description (field "Message"). One required consent checkbox: the transactional-messages text (the
confirmation text and the follow-up about the request are transactional; marketing consent is not asked here). The CTA
of each page on the button. Thank-you message until Atif sends the thank-you page URLs (then redirectUrl+redirect_url).

Workflows "Google Ads LP - Weekly" / "Google Ads LP - Repairs" (folder of "AdWords Form - New Lead"), one if/else first:
  Spam / DND               → nothing.
  Sent in the last 24 h    → nothing (a second submit of the same form within a day: no second card, alert or text).
  Current customer         → tags, fields, alerts to Rob (marked existing customer), confirmations; no card, so their
                             Won/Recurring card is never pulled back to New Lead.
  New lead                 → tags, fields, card in Pool Leads → New Lead (create/update: one card per contact),
                             Google Ads conversion (works once Google Ads is connected in GHL), text + email to Rob,
                             confirmation text + email to the lead; Weekly also tags whether the ZIP is one of Rob's 7
                             route ZIPs ("weekly route zip" / "outside weekly route").
Every branch ends with: wait 1 day → remove the 24 h tag. Tags: google ads + weekly|repairs (brief), new lead.
Fields: Service Requested (Weekly → "Weekly Pool Maintenance"), Landing Page, ZIP (postal code on the contact).
test: temporary copies with alerts to --to, no texts to Rob, no conversion; contacts enrolled through the API cover
every branch; checks tags, fields, cards and the repeat guard, then deletes everything. A real submission (Turnstile
blocks scripts) is the last check, by hand, once the pages are up.
"""
from __future__ import annotations

import argparse
import copy
import json
import re
import sys
import time
import uuid

from _common import ROOT, keep_redirect, load_dotenv
from bv_service_forms import latest_form_data
from pp_source_tags import refs_ok
from pp_won_stage import IS_OPS, NEST

from cli_anything.gohighlevel.utils.agency import BACKEND, SERVICES, Agency

LOC = "3CozZ1NfujYWEPIYgzx0"
BASE_FORM = "tDG9UG5oteefoJChUDwt"  # Landing Page - Optin Form
FOLDER_OF = "AdWords Form - New Lead"
ROB = "aLOlBW4qUvVVf1GOopah"
ROB_EMAIL = "thepoolshackaz@gmail.com"
PIPELINE, NEW_LEAD = "YAWctFyQuPj6SncrCYJL", "f682f58d-ae36-436b-99bd-9d116e5a3a63"
SERVICE_FIELD, PAGE_FIELD, MESSAGE_FIELD = "Service Requested", "Landing Page", "Message"
WEEKLY_SERVICE = "Weekly Pool Maintenance"
REPAIR_OPTIONS = ["Pool Pump Repair / Replacement", "Pool Filter Repair / Replacement", "Pool Heater Repair / Replacement",
                  "Pool Automation System / Upgrade", "Equipment Installation / Upgrade", "Other Equipment Issue"]
ROUTE_ZIPS = ["85250", "85251", "85253", "85254", "85257", "85258", "85260"]  # Rob's weekly route (brief)
SPAM = ["spam", "dnd"]
CUSTOMER = ["existing customer", "recurring customer", "won"]
THANKS = "Thank you! We received your request and will contact you shortly."
NUMBER = "{{custom_values.a2p_verification_number}}"
BDIR = ROOT / "backup" / "the-pool-shack"

PAGES = [
    {"key": "weekly", "form": "GOOGLE ADS – WEEKLY", "flow": "Google Ads LP - Weekly", "tag": "weekly",
     "cta": "Get a Weekly Pool Service Quote", "page": "Google Ads LP - Weekly Pool Maintenance (Scottsdale & Paradise Valley)",
     "source": "Google Ads LP - Weekly", "value": "180.00", "label": "WEEKLY SERVICE",
     "sms": "Hi {{contact.first_name}}, thanks for requesting a weekly pool service quote from The Pool Shack! We received "
            "your info and will reach out shortly. Questions? Call or text us at " + NUMBER + ". Reply STOP to opt out.",
     "subject": "We received your weekly pool service request",
     "email": ["Hi {{contact.first_name}},",
               "Thanks for reaching out to The Pool Shack about weekly pool service. We received your request and will "
               "contact you shortly to go over your pool and get you a quote.",
               "If you need us sooner, call or text us at " + NUMBER + ".",
               "Thank you,<br>The Pool Shack"]},
    {"key": "repairs", "form": "GOOGLE ADS – REPAIRS", "flow": "Google Ads LP - Repairs", "tag": "repairs",
     "cta": "Request an Equipment Repair Quote", "page": "Google Ads LP - Pool Equipment Repairs & Installations (Phoenix Metro)",
     "source": "Google Ads LP - Repairs", "value": "", "label": "EQUIPMENT REPAIR",
     "sms": "Hi {{contact.first_name}}, thanks for your pool equipment request with The Pool Shack! We received your "
            "details and will reach out shortly. Questions? Call or text us at " + NUMBER + ". Reply STOP to opt out.",
     "subject": "We received your pool equipment request",
     "email": ["Hi {{contact.first_name}},",
               "Thanks for reaching out to The Pool Shack about your pool equipment. We received your request "
               "({{contact.service_requested}}) and will contact you shortly to go over it and get you a quote.",
               "If you need us sooner, call or text us at " + NUMBER + ".",
               "Thank you,<br>The Pool Shack"]},
]
P = '<p style="margin:0 0 12px 0;font-family:Arial,Helvetica,sans-serif;font-size:15px;line-height:1.5;">{}</p>'


def nid() -> str:
    return str(uuid.uuid4())


# ── forms ─────────────────────────────────────────────────────────────────

def dropdown(cf: dict) -> dict:
    return {"dataType": "SINGLE_OPTIONS", "fieldKey": cf["fieldKey"], "fieldName": SERVICE_FIELD,
            "hiddenFieldQueryKey": cf["fieldKey"].split(".")[-1], "id": cf["id"], "label": SERVICE_FIELD,
            "locationId": LOC, "model": "contact", "name": SERVICE_FIELD, "picklistOptions": REPAIR_OPTIONS,
            "placeholder": "Select a service", "position": 0, "required": True, "tag": cf["id"], "type": "single_options",
            "fieldWidthPercentage": 100}


def message(cf: dict) -> dict:
    return {"label": "Describe the issue (optional)", "tag": cf["id"], "id": cf["id"],
            "hiddenFieldQueryKey": cf["fieldKey"].split(".")[-1], "type": "large_text", "dataType": "LARGE_TEXT",
            "typeLabel": "Multi Line", "placeholder": "Equipment brand/model, what it's doing, error codes…",
            "required": False, "standard": False, "custom": True, "category": "text", "model": "contact",
            "name": cf["name"], "fieldKey": cf["fieldKey"], "locationId": LOC,
            "preview": "<span style=\"color: #000000;\">Equipment brand/model, what it's doing, error codes…</span>"}


def build_form(base: dict, p: dict, cfs: dict) -> dict:
    fd = copy.deepcopy(base)
    f = fd["form"]
    by = {x["tag"]: x for x in f["fields"]}
    header = [copy.deepcopy(x) for x in f["fields"] if x.get("type") == "h1"]
    name, phone, email, addr, zip_, consent, button = (copy.deepcopy(by[k]) for k in (
        "full_name", "phone", "email", "group_address", "postal_code", "terms_and_conditions", "button"))
    name.update(required=True)
    phone.update(required=True, placeholder="Phone", enableCountryPicker=True)
    email.update(required=True)
    addr.update(required=True, label="Property Address", placeholder="Property Address", title="Property Address")
    zip_.update(required=True, label="ZIP Code", placeholder="ZIP Code", title="ZIP Code")
    consent.update(required=True)
    consent.pop("placeholder2", None)  # transactional consent only (one required box)
    button["label"] = re.sub(r"<strong>[^<]*</strong>", f"<strong>{p['cta'].upper()}</strong>", button["label"], count=1)
    fields = [name, phone, email, addr, zip_]
    if p["key"] == "repairs":
        fields += [dropdown(cfs[SERVICE_FIELD]), message(cfs[MESSAGE_FIELD])]
    f["fields"] = [*fields, consent, button, *header]
    f["formAction"] = {**(f.get("formAction") or {}), "actionType": "2", "thankyouText": THANKS}
    return keep_redirect(fd)


# ── workflow nodes ────────────────────────────────────────────────────────

def chain(items: list[tuple[str, str, dict]], parent: str | None = None) -> list[dict]:
    ids = [nid() for _ in items]
    out = []
    for i, (kind, name, attrs) in enumerate(items):
        s = {"id": ids[i], "order": i, "name": name, "type": kind, "attributes": attrs}
        if parent:
            s["parent"] = parent
        if i:
            s["parentKey"] = ids[i - 1]
        elif parent:
            s["parentKey"] = parent
        if i + 1 < len(items):
            s["next"] = ids[i + 1]
        out.append(s)
    return out


def cond(sub: str, op: str, value) -> dict:
    return {"conditionType": "contact_detail", "conditionSubType": sub, "conditionOperator": op, "conditionValue": value,
            "__conditionId": nid(), "ifElseNodeId": "", "__customFieldType__": "standard", "isWait": False,
            "nestedDropdownTypes": NEST, "allowIsOperatorTypes": IS_OPS}


def if_else(name: str, branches: list[tuple[str, list[dict], list]], else_name: str, else_items: list,
            parent: str | None = None, parent_key: str | None = None, order: int = 0) -> tuple[list[dict], str]:
    """One condition node; each branch = (name, conditions OR'ed, chain items); returns nodes and the node id."""
    head = nid()
    bids = [nid() for _ in branches] + [nid()]
    node = {"id": head, "order": order, "name": name, "type": "if_else", "cat": "conditions", "nodeType": "condition-node",
            "next": bids, "attributes": {
                "currentRecipeType": "CUSTOM", "operator": "and", "if": True, "conditionName": name, "version": 2,
                "noneBranchName": else_name,
                "branches": [{"id": bids[i], "name": bn, "operator": "and", "showErrors": False,
                              "branchNameError": "Branch name cannot be empty!",
                              "segments": [{"__segmentId": nid(), "operator": "or", "conditions": conds}]}
                             for i, (bn, conds, _) in enumerate(branches)]}}
    if parent:
        node["parent"] = parent
    if parent_key:
        node["parentKey"] = parent_key
    out = [node]
    for i, (bn, _, items) in enumerate([*branches, (else_name, None, else_items)]):
        b = {"id": bids[i], "parent": head, "parentKey": head, "order": order + 1, "name": bn, "type": "if_else",
             "cat": "conditions", "sibling": [x for x in bids if x != bids[i]],
             "nodeType": "branch-no" if i == len(branches) else "branch-yes",
             "attributes": {"else": True} if i == len(branches) else
             {"if": False, "conditionName": "Condition", "operator": "and", "branches": []}}
        out.append(b)
        if items:
            sub = attach(items, bids[i])
            b["next"] = sub[0]["id"]
            out += sub
    return out, head


def attach(items: list, parent: str) -> list[dict]:
    """A branch body: plain steps, optionally ending in a nested if_else spec ("ifelse", name, branches, else...)."""
    plain = [x for x in items if x[0] != "ifelse"]
    nested = [x for x in items if x[0] == "ifelse"]
    nodes = chain(plain, parent)
    if nested:
        _, name, branches, else_name, else_items = nested[0]
        sub, head = if_else(name, branches, else_name, else_items, parent=parent,
                            parent_key=nodes[-1]["id"] if nodes else parent, order=len(nodes))
        if nodes:
            nodes[-1]["next"] = head
        nodes += sub
    return nodes


def tags(tag_list: list[str]) -> tuple[str, str, dict]:
    return ("add_contact_tag", "Add Tags", {"type": "add_contact_tag", "tags": tag_list})


def fields(cfs: dict, p: dict) -> tuple[str, str, dict]:
    vals = [(PAGE_FIELD, p["page"])] + ([(SERVICE_FIELD, WEEKLY_SERVICE)] if p["key"] == "weekly" else [])
    return ("update_contact_field", "Set " + " / ".join(n for n, _ in vals), {
        "type": "update_contact_field", "actionType": "update_field_data",
        "fields": [{"field": cfs[n]["id"], "value": v, "title": n, "type": "select" if n == SERVICE_FIELD else "text",
                    "date": ""} for n, v in vals]})


def alert_sms(p: dict, customer: bool) -> tuple[str, str, dict]:
    extra = "\nService: {{contact.service_requested}}\nDetails: {{contact.message}}" if p["key"] == "repairs" else ""
    body = (f"🚨 NEW GOOGLE ADS LEAD - {p['label']} 🚨" + (" (EXISTING CUSTOMER)" if customer else "") +
            "\n\nName: {{contact.name}}\nPhone: {{contact.phone}}\nEmail: {{contact.email}}\n"
            "Address: {{contact.address1}}\nZIP: {{contact.postal_code}}" + extra)
    return ("internal_notification", "Text Rob", {"type": "sms", "sms": {
        "body": body, "userType": "user", "selectedUser": [ROB], "attachments": []}})


def alert_email(p: dict, customer: bool, to: str = ROB_EMAIL) -> tuple[str, str, dict]:
    rows = [("Name", "{{contact.name}}"), ("Phone", "{{contact.phone}}"), ("Email", "{{contact.email}}"),
            ("Address", "{{contact.address1}}, {{contact.city}}"), ("ZIP", "{{contact.postal_code}}"),
            ("Service", "{{contact.service_requested}}")] + \
        ([("Details", "{{contact.message}}")] if p["key"] == "repairs" else []) + [("Page", p["page"])]
    html = P.format(f"New lead from the Google Ads landing page ({p['label'].title()})" +
                    (" <b>(existing customer)</b>" if customer else "") + ":") + \
        "".join(P.format(f"<b>{k}:</b> {v}") for k, v in rows)
    return ("internal_notification", "Email Rob", {"type": "email", "email": {
        "userType": "custom_email", "to": to, "subject": f"🚨 New Google Ads lead ({p['label'].title()}): {{{{contact.name}}}}",
        "html": html}})


def confirm(p: dict) -> list[tuple[str, str, dict]]:
    return [("sms", "Confirmation text", {"body": p["sms"], "attachments": []}),
            ("email", "Confirmation email", {"subject": p["subject"], "html": "".join(P.format(x) for x in p["email"]),
                                             "from_name": "{{custom_values.friendly_business_name}}", "from_email": "",
                                             "attachments": []})]


def wait_day() -> tuple[str, str, dict]:
    return ("wait", "Wait 1 day", {"type": "time", "startAfter": {"type": "days", "value": 1, "when": "after"},
                                   "name": "Wait 1 day", "cat": "", "isHybridAction": True, "hybridActionType": "wait",
                                   "convertToMultipath": False, "transitions": []})


def build_flow(p: dict, cfs: dict, test_to: str | None = None) -> list[dict]:
    recent = f"google ads lp {p['key']} 24h"
    release = [wait_day(), ("remove_contact_tag", "Remove 24 h tag", {"type": "remove_contact_tag", "tags": [recent]})]
    base_tags = ["google ads", p["tag"], "new lead", recent]

    def alerts(customer: bool) -> list:
        if test_to:  # test copy: one email to the tester, nothing to Rob
            return [alert_email(p, customer, test_to)]
        return [alert_sms(p, customer), alert_email(p, customer)]

    card = ("create_opportunity", "Card in New Lead", {
        "fields": [], "type": "create_opportunity", "pipeline_id": PIPELINE, "pipeline_stage_id": NEW_LEAD,
        "opportunity_name": "{{contact.name}}", "opportunity_source": p["source"], "monetary_value": p["value"],
        "opportunity_status": "open"})
    conversion = ("google_adword", "Google Ads conversion", {
        "type": "google_adword", "currency": "USD", "conversion_value": p["value"] or "1", "conversion_type": "",
        "conversion_name": "", "conversion_action_id": "", "customMapping": {"gclid": "{{contact.attributionSource.gclid}}"},
        "isCustomMappingEnabled": True})
    lead = [tags(base_tags), fields(cfs, p), card, *([] if test_to else [conversion]), *alerts(False), *confirm(p)]
    if p["key"] == "weekly":
        zip_check = ("ifelse", "ZIP in the weekly route?",
                     [("Route ZIP", [cond("postal_code", "==", z) for z in ROUTE_ZIPS],
                       [tags(["weekly route zip"]), *release])],
                     "Outside the route", [tags(["outside weekly route"]), *release])
        lead.append(zip_check)
    else:
        lead += release
    customer = [tags(base_tags), fields(cfs, p), *alerts(True), *confirm(p), *release]
    nodes, _ = if_else("Route the lead", [
        ("Spam / DND", [cond("tags", "index-of-true", [t]) for t in SPAM], []),
        ("Sent in the last 24 h", [cond("tags", "index-of-true", [recent])], []),
        ("Current customer", [cond("tags", "index-of-true", [t]) for t in CUSTOMER], customer),
    ], "New lead", lead)
    return nodes


def trigger_body(wid: str, form_id: str, first: str) -> dict:
    return {"type": "form_submission", "name": "Form Submitted", "masterType": "highlevel", "schedule_config": {},
            "conditions": [{"operator": "is-any-of", "field": "form.id", "value": [form_id], "title": "Form is", "type": "string"}],
            "workflowId": wid, "workflow_id": wid, "location_id": LOC,
            "actions": [{"workflow_id": wid, "type": "add_to_workflow"}], "targetActionId": first}


def create_flow(a: Agency, name: str, parent: str | None, tpl: list[dict], publish: bool) -> str:
    res = a.call("POST", BACKEND, f"/workflow/{LOC}", body={"name": name, "parentId": parent, "status": "draft"})
    wid = res.get("id") or res.get("_id")
    body = {"name": name, "version": 1, "status": "draft", "parentId": parent, "allowMultiple": True,
            "workflowData": {"templates": tpl}}
    a.call("PUT", BACKEND, f"/workflow/{LOC}/{wid}", body=body)
    if publish:
        live = a.workflow(LOC, wid)
        a.call("PUT", BACKEND, f"/workflow/{LOC}/{wid}", body={**body, "status": "published", "version": live.get("version", 1),
                                                             "workflowData": {"templates": live["workflowData"]["templates"]}})
    return wid


def drop_flow(a: Agency, wid: str) -> None:
    live = a.workflow(LOC, wid)
    a.call("PUT", BACKEND, f"/workflow/{LOC}/{wid}", body={"name": live["name"], "version": live.get("version", 1),
                                                         "status": "draft", "workflowData": {"templates": live["workflowData"]["templates"]}})
    a.call("DELETE", BACKEND, f"/workflow/{LOC}/{wid}")


def ensure_fields(a: Agency) -> dict:
    cfs = {c["name"]: c for c in a.custom_fields(LOC)}
    want = {SERVICE_FIELD: {"dataType": "SINGLE_OPTIONS", "options": [WEEKLY_SERVICE, *REPAIR_OPTIONS]},
            PAGE_FIELD: {"dataType": "TEXT"}}
    for name, spec in want.items():
        if name not in cfs:
            res = a.call("POST", SERVICES, f"/locations/{LOC}/customFields",
                         body={"name": name, "placeholder": "", "position": 0, "model": "contact", **spec})
            cfs[name] = res.get("customField") or res
            print(f"   ✓ campo {name} ({cfs[name].get('fieldKey')}) {cfs[name].get('picklistOptions') or ''}")
    for t in {"google ads", "weekly", "repairs", "new lead", "weekly route zip", "outside weekly route",
              *(f"google ads lp {p['key']} 24h" for p in PAGES)}:
        try:
            a.call("POST", BACKEND, f"/workflow/{LOC}/tags/create", body={"tag": t})
        except Exception:  # noqa: BLE001 — already exists
            pass
    return cfs


def outline(tpl: list[dict]) -> str:
    by = {s["id"]: s for s in tpl}

    def walk(sid, depth):
        out = []
        while sid and sid in by:
            s = by[sid]
            if s["type"] == "if_else" and isinstance(s.get("next"), list):
                out.append("  " * depth + f"◆ {s['name']}")
                for b in s["next"]:
                    out.append("  " * (depth + 1) + f"▸ {by[b]['name']}")
                    out += walk(by[b].get("next"), depth + 2)
                break
            out.append("  " * depth + f"- {s['name']}")
            sid = s.get("next") if isinstance(s.get("next"), str) else None
        return out
    root = next(s["id"] for s in tpl if not s.get("parentKey") and not s.get("parent"))
    return "\n".join(walk(root, 1))


def contact_state(a: Agency, cid: str, cfs: dict) -> tuple[list, dict, list]:
    c = a.call("GET", SERVICES, f"/contacts/{cid}")["contact"]
    vals = {n: next((f.get("value") for f in c.get("customFields", []) if f.get("id") == cfs[n]["id"]), None)
            for n in (SERVICE_FIELD, PAGE_FIELD)}
    opps = a.call("GET", SERVICES, "/opportunities/search", params={"location_id": LOC, "contact_id": cid}).get("opportunities", [])
    return c.get("tags", []), vals, opps


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("mode", choices=["plan", "fields", "test", "apply"])
    parser.add_argument("--to", help="test: inbox that gets the lead alerts and confirmations")
    args = parser.parse_args()
    if args.mode == "test" and not args.to:
        parser.error("--to is required in test mode")
    load_dotenv()
    a = Agency()
    if a.location(LOC)["name"] != "The Pool Shack":
        sys.exit("sub-conta errada")
    BDIR.mkdir(parents=True, exist_ok=True)
    cfs = {c["name"]: c for c in a.custom_fields(LOC)}
    forms = {f["name"]: f.get("_id") or f.get("id") for f in a.forms(LOC)}
    flows = {w["name"]: w["id"] for w in a.workflows(LOC)}
    folder = a.workflow(LOC, flows[FOLDER_OF]).get("parentId")
    _, base = latest_form_data(a, BASE_FORM)

    if args.mode == "plan":
        fake = {n: {"id": f"<{n}>", "fieldKey": "contact." + n.lower().replace(" ", "_"), "name": n}
                for n in (SERVICE_FIELD, PAGE_FIELD, MESSAGE_FIELD)}
        fake.update({k: v for k, v in cfs.items() if k in fake})
        for p in PAGES:
            fd = build_form(base, p, fake)
            print(f"\n== {p['form']}: {'existe' if p['form'] in forms else 'cria'}")
            print("   campos:", " · ".join(f"{re.sub('<[^>]+>', '', x.get('label') or '')}{'*' if x.get('required') else ''}"
                                         for x in fd["form"]["fields"]))
            print(f"   {p['flow']}: {'existe' if p['flow'] in flows else 'cria'}\n{outline(build_flow(p, fake))}")
        return 0

    cfs = ensure_fields(a)
    if args.mode == "fields":
        return 0

    if args.mode == "test":
        stamp, bad = int(time.time()), 0
        for p in PAGES:
            tpl = build_flow(p, cfs, args.to)
            wid = create_flow(a, f"ZZ TEST {p['flow']}", folder, tpl, True)
            cases = [("new", {}, ["85251"]), ("repeat", {}, None), ("outside", {}, ["85001"]),
                     ("customer", {"tags": ["existing customer"]}, ["85251"]), ("spam", {"tags": ["spam"]}, ["85251"])]
            made = {}
            for case, extra, zip_ in cases:
                if case == "repeat":
                    continue
                body = {"locationId": LOC, "firstName": "ZZ Test", "lastName": f"{p['key']} {case}",
                        "email": args.to.replace("@", f"+ps-{p['key']}-{case}-{stamp}@"), "postalCode": zip_[0],
                        "address1": "1 Test St", "city": "Scottsdale", **extra}
                if p["key"] == "repairs":
                    body["customFields"] = [{"id": cfs[SERVICE_FIELD]["id"], "field_value": REPAIR_OPTIONS[2]}]
                made[case] = a.call("POST", SERVICES, "/contacts/", body=body)["contact"]["id"]
            time.sleep(3)
            for case, cid in made.items():
                a.call("POST", SERVICES, f"/contacts/{cid}/workflow/{wid}", body={})
            time.sleep(40)
            a.call("POST", SERVICES, f"/contacts/{made['new']}/workflow/{wid}", body={})  # same form again
            time.sleep(40)
            want = {"new": ({"google ads", p["tag"], "new lead", f"google ads lp {p['key']} 24h"}
                            | ({"weekly route zip"} if p["key"] == "weekly" else set()), 1),
                    "outside": ({"google ads", p["tag"]} | ({"outside weekly route"} if p["key"] == "weekly" else set()), 1),
                    "customer": ({"google ads", p["tag"]}, 0), "spam": (set(), 0)}
            sent = [m for c in a.call("GET", SERVICES, "/conversations/search", params={"locationId": LOC, "contactId": made["new"]}).get("conversations", [])
                    for m in (lambda r: r.get("messages", r) if isinstance(r, dict) else r)(
                        a.call("GET", SERVICES, f"/conversations/{c['id']}/messages").get("messages", {}))
                    if m.get("direction") == "outbound" and (m.get("messageType") == "TYPE_EMAIL" or m.get("type") == 3)]
            ok = len(sent) == 1
            bad += not ok
            print(f"   {'✓' if ok else '✗'} {p['key']}/repeat: {len(sent)} e-mail(s) de confirmação para o mesmo contato depois de 2 envios")
            for case, cid in made.items():
                tg, vals, opps = contact_state(a, cid, cfs)
                exp_tags, exp_cards = want[case]
                svc = WEEKLY_SERVICE if p["key"] == "weekly" else REPAIR_OPTIONS[2]
                ok = exp_tags <= set(tg) and len(opps) == exp_cards and \
                    (case == "spam" and "google ads" not in tg or case != "spam" and vals[SERVICE_FIELD] == svc and vals[PAGE_FIELD] == p["page"]) and \
                    all(o.get("source") == p["source"] for o in opps)
                bad += not ok
                print(f"   {'✓' if ok else '✗'} {p['key']}/{case}: tags {sorted(tg)} · {vals} · cards {[(o.get('source'), o.get('monetaryValue')) for o in opps]}")
            for cid in made.values():
                for o in contact_state(a, cid, cfs)[2]:
                    a.call("DELETE", SERVICES, f"/opportunities/{o['id']}")
                a.call("DELETE", SERVICES, f"/contacts/{cid}")
            drop_flow(a, wid)
        print(f"   limpo; e-mails (alertas + confirmações) em {args.to}. Esperado: new 1 alerta (não 2: o repeat é barrado), "
              "outside 1, customer 1 com 'existing customer', spam 0.")
        return 1 if bad else 0

    # apply
    out = {}
    for p in PAGES:
        if p["form"] in forms:
            fid = forms[p["form"]]
            cur, cur_fd = latest_form_data(a, fid)
            (BDIR / f"form-{fid}-{time.strftime('%Y%m%d-%H%M%S')}.json").write_text(json.dumps({"form": cur, "formData": cur_fd}))
            a.call("POST", BACKEND, f"/forms/{fid}", body={"name": p["form"], "formData": build_form(base, p, cfs)})
            print(f"   ✓ form {p['form']} refeito ({fid})")
        else:
            res = a.call("POST", BACKEND, "/forms/", body={"name": p["form"], "locationId": LOC, "formData": build_form(base, p, cfs)})
            fid = forms[p["form"]] = (res.get("form") or res).get("_id") or (res.get("form") or res).get("id")
            print(f"   ✓ form {p['form']}: {fid}")
        if p["flow"] in flows:
            print(f"   {p['flow']}: já existe")
            continue
        tpl = build_flow(p, cfs)
        wid = create_flow(a, p["flow"], folder, tpl, False)
        trig = trigger_body(wid, fid, tpl[0]["id"])
        t = a.call("POST", BACKEND, f"/workflow/{LOC}/trigger", body=trig)
        a.call("PUT", BACKEND, f"/workflow/{LOC}/trigger/{t['id']}", body={**trig, "id": t["id"]})
        live = a.workflow(LOC, wid)
        a.call("PUT", BACKEND, f"/workflow/{LOC}/{wid}", body={
            "name": p["flow"], "version": live.get("version", 1), "status": "published", "parentId": folder,
            "allowMultiple": True, "workflowData": {"templates": live["workflowData"]["templates"]}})
        time.sleep(4)
        got = a.workflow(LOC, wid)
        trs = [x for x in a.triggers(LOC, wid) if not x.get("deleted")]
        ok = got["status"] == "published" and len(got["workflowData"]["templates"]) == len(tpl) and \
            refs_ok(got["workflowData"]["templates"]) and len(trs) == 1 and trs[0].get("active") and \
            trs[0]["conditions"][0]["value"] == [fid] and got.get("allowMultiple")
        print(f"   {'✓' if ok else '✗ VERIFICAR'} {p['flow']}: {got['status']} · {len(tpl)} passos · form {fid}")
        out[p["form"]] = fid
    print("\n   links:", {k: f"https://link.poolprofits.com/widget/form/{v}" for k, v in forms.items() if k in {p['form'] for p in PAGES}})
    return 0


if __name__ == "__main__":
    sys.exit(main())
