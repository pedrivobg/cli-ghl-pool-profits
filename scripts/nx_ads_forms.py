#!/usr/bin/env python3
"""NorTex Pools: 2 Google Ads/Meta landing pages (Val/Atif brief, 27/10). One form per page, its tags and lead workflow,
plus the pages' phone line.

    ./.venv/bin/python scripts/nx_ads_forms.py plan
    ./.venv/bin/python scripts/nx_ads_forms.py test --to pedro@poolprofits.com
    ./.venv/bin/python scripts/nx_ads_forms.py apply                       # forms + published workflows + line

Forms "GOOGLE ADS – WEEKLY" / "GOOGLE ADS – REPAIR", built from the newest version of "Landing Page - Optin Form": First
Name, Last Name, Phone (US country picker), Email, Street Address, City, ZIP Code, all required, plain fields. Repair adds
"What equipment needs repair?" (Pool Pump / Heater / Filter / Light / Salt System / Other Pool Equipment) and, right above
the button, "A $150 diagnostic visit fee applies. This fee is waived if you approve the repair." One required consent
checkbox (transactional). The page's CTA on the button. Redirect to the page's thank-you URL on nortexpools.com.

Workflows "Google Ads LP - Weekly|Repair" (folder of "AdWords Form - New Lead"), one if/else first:
  Spam / DND             → nothing.
  Sent in the last 24 h  → nothing (a second submit of the same form within a day: no second card, alert or text).
  Current customer       → tags, fields, alerts to Fareed (marked existing customer), confirmations; no card.
  New lead               → tags, fields, card in Pool Leads → New Lead (source = the page), Google Ads conversion
                           (works once Google Ads is connected in GHL), text + email to Fareed (name, phone, service,
                           equipment, source), confirmation text + email to the lead.
Every branch ends with: wait 1 day → remove the 24 h tag. Tags (brief): google ads - weekly|repair, plus the account's
own "new lead" and "adwords". Fields: Service (account's dropdown), Equipment Needing Repair (new), Landing Page (new).
Line +1 469-218-3416 ("Google Adwords", bought 27/10, routed nowhere): joins the "IVR SPAM Detection" trigger (press 1 →
Fareed, like the main line; cards/missed-call text come from the account's call workflows) and "Google Ads Call - Tag"
tags its callers `google ads call` + `adwords`.
test: temporary copies with alerts to --to, no texts to Fareed, no conversion; contacts enrolled through the API cover
every branch; checks tags, fields, cards and the repeat guard, then deletes everything.
"""
from __future__ import annotations

import argparse
import copy
import json
import re
import sys
import time

from _common import ROOT, keep_redirect, load_dotenv
from bv_service_forms import latest_form_data
from ps_ads_forms import P, chain, cond, if_else, outline, tags, wait_day
from pp_won_stage import DROP
from pp_source_tags import refs_ok

from cli_anything.gohighlevel.utils.agency import BACKEND, SERVICES, Agency

LOC = "k6nDPHktS2PySJoJuwpG"
BASE_FORM = "q8Z04TylS61aJrEeA9V7"  # Landing Page - Optin Form
FOLDER_OF = "AdWords Form - New Lead"
FAREED, FAREED_EMAIL = "L9rAwvOd8DjsUnw4m5tX", "f.alayoub@nortexpools.com"  # Fareed (only user)
PIPELINE, NEW_LEAD = "6cVcvhrosWlJHPrWLMx5", "cc31ee8a-8a37-4c69-8d28-a771df8b1f41"
SERVICE_FIELD, PAGE_FIELD, EQUIP_FIELD = "Service", "Landing Page", "Equipment Needing Repair"
EQUIPMENT = ["Pool Pump", "Pool Heater", "Pool Filter", "Pool Light", "Salt System", "Other Pool Equipment"]
NOTICE = "A $150 diagnostic visit fee applies. This fee is waived if you approve the repair."
SITE = "https://nortexpools.com"
LINE, IVR, CALL_FLOW = "+14692183416", "IVR SPAM Detection", "Google Ads Call - Tag"
SPAM = ["spam", "dnd"]
CUSTOMER = ["existing customer", "recurring customer", "won"]
NUMBER = "{{custom_values.a2p_verification_number}}"
BDIR = ROOT / "backup" / "nortex-pools"

PAGES = [
    {"key": "weekly", "form": "GOOGLE ADS – WEEKLY", "flow": "Google Ads LP - Weekly", "tag": "google ads - weekly",
     "cta": "Get My Free Quote", "service": "Weekly Pool Cleaning", "label": "Premium Weekly Pool Cleaning", "value": "280",
     "page": "Google Ads LP - Premium Weekly Pool Cleaning (/premium-weekly-pool-cleaning/)", "thanks": "/thank-you-weekly-service/",
     "sms": "Hi {{contact.first_name}}, thanks for requesting a free quote for premium weekly pool service from NorTex "
            "Pools! We received your info and will reach out shortly. Questions? Call or text " + NUMBER + ". "
            "Reply STOP to opt out.",
     "subject": "We received your weekly pool service request",
     "email": "Thanks for reaching out to NorTex Pools about premium weekly pool service. We received your request and "
              "will contact you shortly to go over your pool and your free quote."},
    {"key": "repair", "form": "GOOGLE ADS – REPAIR", "flow": "Google Ads LP - Repair", "tag": "google ads - repair",
     "cta": "Schedule a Repair Visit", "service": "Equipment Repair", "label": "Pool Equipment Repair", "value": "150",
     "page": "Google Ads LP - Pool Equipment Repair (/pool-equipment-repair/)", "thanks": "/thank-you-equipment-repair/",
     "sms": "Hi {{contact.first_name}}, thanks for your pool equipment repair request with NorTex Pools! We received "
            "your info and will reach out shortly to schedule a diagnostic visit. Questions? Call or text " + NUMBER + ". "
            "Reply STOP to opt out.",
     "subject": "We received your pool equipment repair request",
     "email": "Thanks for reaching out to NorTex Pools about your pool equipment ({{contact.equipment_needing_repair}}). "
              "We received your request and will contact you shortly to schedule a diagnostic visit. As a reminder, the "
              "diagnostic visit is $150, and the fee is waived if you approve the repair."},
]


# ── forms ─────────────────────────────────────────────────────────────────

def std(tag: str, label: str) -> dict:
    return {"fieldWidthPercentage": 100, "hiddenFieldQueryKey": tag, "label": label, "placeholder": label,
            "required": True, "standard": True, "tag": tag, "title": label, "type": "text", "typeLabel": "Text"}


def build_form(base: dict, p: dict, cfs: dict) -> dict:
    fd = copy.deepcopy(base)
    f = fd["form"]
    by = {x["tag"]: x for x in f["fields"]}
    header = [copy.deepcopy(x) for x in f["fields"] if x.get("type") == "h1"]
    phone, email, city, zip_, consent, button = (copy.deepcopy(by[k]) for k in (
        "phone", "email", "city", "postal_code", "terms_and_conditions", "button"))
    first, last = std("first_name", "First Name"), std("last_name", "Last Name")
    first["fieldWidthPercentage"] = last["fieldWidthPercentage"] = 50
    street = {**std("address", "Street Address"), "category": "address"}
    phone.update(required=True, placeholder="Phone", enableCountryPicker=True)
    email.update(required=True)
    city.update(required=True, label="City", placeholder="City", title="City", fieldWidthPercentage=50)
    zip_.update(required=True, label="ZIP Code", placeholder="ZIP Code", title="ZIP Code", fieldWidthPercentage=50)
    consent.update(required=True)
    consent.pop("placeholder2", None)  # transactional consent only (one required box)
    button["label"] = re.sub(r"<strong>[^<]*</strong>", f"<strong>{p['cta'].upper()}</strong>", button["label"], count=1)
    extra = []
    if p["key"] == "repair":
        cf = cfs[EQUIP_FIELD]
        extra = [{"dataType": "SINGLE_OPTIONS", "fieldKey": cf["fieldKey"], "fieldName": EQUIP_FIELD,
                  "hiddenFieldQueryKey": cf["fieldKey"].split(".")[-1], "id": cf["id"], "label": "What equipment needs repair?",
                  "locationId": LOC, "model": "contact", "name": EQUIP_FIELD, "picklistOptions": EQUIPMENT,
                  "placeholder": "Select equipment", "position": 0, "required": True, "tag": cf["id"],
                  "type": "single_options", "fieldWidthPercentage": 100}]
    notice = [{"align": "left", "bgColor": "FFFFFF00", "border": {"border": 0, "color": "FFFFFF", "radius": 0, "type": "none"},
               "hiddenFieldQueryKey": "header_2", "label": f'<p style="text-align: center;padding-left: 0px!important;"><strong>{NOTICE}</strong></p>',
               "padding": {"bottom": 5, "left": 0, "right": 0, "top": 5}, "placeholder": "header",
               "shadow": {"blur": 0, "color": "FFFFFF", "horizontal": 0, "spread": 0, "vertical": 0}, "standard": True,
               "tag": "header_notice", "type": "h1", "typeLabel": "Text", "weight": 400}] if p["key"] == "repair" else []
    f["fields"] = [first, last, phone, email, street, city, zip_, *extra, consent, *notice, button, *header]
    url = SITE + p["thanks"]
    f["formAction"] = {**(f.get("formAction") or {}), "actionType": "1", "redirectUrl": url, "redirect_url": url}
    return keep_redirect(fd)


# ── workflow ──────────────────────────────────────────────────────────────

def fields(cfs: dict, p: dict) -> tuple[str, str, dict]:
    vals = [(SERVICE_FIELD, p["service"]), (PAGE_FIELD, p["page"])]
    return ("update_contact_field", "Set Service / Landing Page", {
        "type": "update_contact_field", "actionType": "update_field_data",
        "fields": [{"field": cfs[n]["id"], "value": v, "title": n, "type": "select" if n == SERVICE_FIELD else "text",
                    "date": ""} for n, v in vals]})


def label(p: dict) -> str:
    return p["label"].upper()


def alert_sms(p: dict, customer: bool) -> tuple[str, str, dict]:
    body = (f"🚨 NEW GOOGLE ADS LEAD - {label(p)} 🚨" + (" (EXISTING CUSTOMER)" if customer else "") +
            "\n\nName: {{contact.name}}\nPhone: {{contact.phone}}\nService: " + p["service"] +
            ("\nEquipment: {{contact.equipment_needing_repair}}" if p["key"] == "repair" else "") +
            "\nSource: Google Ads landing page\nEmail: {{contact.email}}\n"
            "Address: {{contact.address1}}, {{contact.city}} {{contact.postal_code}}")
    return ("internal_notification", "Text Fareed", {"type": "sms", "sms": {
        "body": body, "userType": "user", "selectedUser": [FAREED], "attachments": []}})


def alert_email(p: dict, customer: bool, to: str = FAREED_EMAIL) -> tuple[str, str, dict]:
    rows = [("Name", "{{contact.name}}"), ("Phone", "{{contact.phone}}"), ("Service", p["label"])] + \
        ([("Equipment", "{{contact.equipment_needing_repair}}")] if p["key"] == "repair" else []) + [
            ("Source", f"Google Ads landing page – {p['page']}"), ("Email", "{{contact.email}}"),
            ("Address", "{{contact.address1}}, {{contact.city}} {{contact.postal_code}}")]
    html = P.format("New lead from a Google Ads landing page" + (" <b>(existing customer)</b>" if customer else "") + ":") + \
        "".join(P.format(f"<b>{k}:</b> {v}") for k, v in rows)
    return ("internal_notification", "Email Fareed", {"type": "email", "email": {
        "userType": "custom_email", "to": to, "subject": f"🚨 New Google Ads lead ({p['label']}): {{{{contact.name}}}}",
        "html": html}})


def confirm(p: dict) -> list[tuple[str, str, dict]]:
    paras = ["Hi {{contact.first_name}},", p["email"], "If you need us sooner, call or text us at " + NUMBER + ".",
             "Thank you,<br>NorTex Pools"]
    return [("sms", "Confirmation text", {"body": p["sms"], "attachments": []}),
            ("email", "Confirmation email", {"subject": p["subject"], "html": "".join(P.format(x) for x in paras),
                                             "from_name": "{{custom_values.friendly_business_name}}", "from_email": "",
                                             "attachments": []})]


def build_flow(p: dict, cfs: dict, test_to: str | None = None) -> list[dict]:
    recent = f"google ads lp {p['key']} 24h"
    release = [wait_day(), ("remove_contact_tag", "Remove 24 h tag", {"type": "remove_contact_tag", "tags": [recent]})]
    base_tags = [p["tag"], "new lead", "adwords", recent]

    def alerts(customer: bool) -> list:
        if test_to:  # test copy: one email to the tester, nothing to Fareed
            return [alert_email(p, customer, test_to)]
        return [alert_sms(p, customer), alert_email(p, customer)]

    card = ("create_opportunity", "Card in New Lead", {
        "fields": [], "type": "create_opportunity", "pipeline_id": PIPELINE, "pipeline_stage_id": NEW_LEAD,
        "opportunity_name": "{{contact.name}}", "opportunity_source": f"Google Ads LP - {p['key'].title()}",
        "monetary_value": p["value"], "opportunity_status": "open"})
    conversion = ("google_adword", "Google Ads conversion", {
        "type": "google_adword", "currency": "USD", "conversion_value": p["value"] or "1", "conversion_type": "",
        "conversion_name": "", "conversion_action_id": "", "customMapping": {"gclid": "{{contact.attributionSource.gclid}}"},
        "isCustomMappingEnabled": True})
    lead = [tags(base_tags), fields(cfs, p), card, *([] if test_to else [conversion]), *alerts(False), *confirm(p),
            *release]
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
    for name, spec in ((PAGE_FIELD, {"dataType": "TEXT"}), (EQUIP_FIELD, {"dataType": "SINGLE_OPTIONS", "options": EQUIPMENT})):
        if name not in cfs:
            res = a.call("POST", SERVICES, f"/locations/{LOC}/customFields",
                         body={"name": name, "placeholder": "", "position": 0, "model": "contact", **spec})
            cfs[name] = res.get("customField") or res
            print(f"   ✓ campo {name} ({cfs[name].get('fieldKey')})")
    for t in {"new lead", "adwords", "google ads call", *(p["tag"] for p in PAGES),
              *(f"google ads lp {p['key']} 24h" for p in PAGES)}:
        try:
            a.call("POST", BACKEND, f"/workflow/{LOC}/tags/create", body={"tag": t})
        except Exception:  # noqa: BLE001 — already exists
            pass
    return cfs


def contact_state(a: Agency, cid: str, cfs: dict) -> tuple[list, dict, list]:
    c = a.call("GET", SERVICES, f"/contacts/{cid}")["contact"]
    vals = {n: next((f.get("value") for f in c.get("customFields", []) if f.get("id") == cfs[n]["id"]), None)
            for n in (SERVICE_FIELD, PAGE_FIELD)}
    opps = a.call("GET", SERVICES, "/opportunities/search", params={"location_id": LOC, "contact_id": cid}).get("opportunities", [])
    return c.get("tags", []), vals, opps


def emails_sent(a: Agency, cid: str) -> int:
    n = 0
    for c in a.call("GET", SERVICES, "/conversations/search", params={"locationId": LOC, "contactId": cid}).get("conversations", []):
        r = a.call("GET", SERVICES, f"/conversations/{c['id']}/messages").get("messages", {})
        for m in (r.get("messages", []) if isinstance(r, dict) else r):
            n += m.get("direction") == "outbound" and (m.get("messageType") == "TYPE_EMAIL" or m.get("type") == 3)
    return n


def test(a: Agency, cfs: dict, folder: str | None, to: str) -> int:
    stamp, bad = int(time.time()), 0
    for p in PAGES:
        wid = create_flow(a, f"ZZ TEST {p['flow']}", folder, build_flow(p, cfs, to), True)
        made = {}
        for case, extra in (("new", {}), ("customer", {"tags": ["existing customer"]}), ("spam", {"tags": ["spam"]})):
            body = {"locationId": LOC, "firstName": "ZZ Test", "lastName": f"{p['key']} {case}", "postalCode": "75034",
                    "email": to.replace("@", f"+nx-{p['key']}-{case}-{stamp}@"), "address1": "1 Test St", "city": "Frisco",
                    **extra}
            if p["key"] == "repair":
                body["customFields"] = [{"id": cfs[EQUIP_FIELD]["id"], "field_value": EQUIPMENT[1]}]
            made[case] = a.call("POST", SERVICES, "/contacts/", body=body)["contact"]["id"]
        time.sleep(3)
        for cid in made.values():
            a.call("POST", SERVICES, f"/contacts/{cid}/workflow/{wid}", body={})
        time.sleep(40)
        a.call("POST", SERVICES, f"/contacts/{made['new']}/workflow/{wid}", body={})  # same form again
        time.sleep(40)
        n = emails_sent(a, made["new"])
        bad += n != 1
        print(f"   {'✓' if n == 1 else '✗'} {p['key']}/repeat: {n} e-mail(s) de confirmação depois de 2 envios")
        base = {p["tag"], "new lead", "adwords"}
        want = {"new": (base, 1), "customer": (base, 0), "spam": (set(), 0)}
        for case, cid in made.items():
            tg, vals, opps = contact_state(a, cid, cfs)
            exp_tags, exp_cards = want[case]
            ok = exp_tags <= set(tg) and len(opps) == exp_cards and \
                (case == "spam" and p["tag"] not in tg or case != "spam" and vals == {SERVICE_FIELD: p["service"], PAGE_FIELD: p["page"]}) and \
                all(o.get("source") == f"Google Ads LP - {p['key'].title()}" for o in opps)
            bad += not ok
            print(f"   {'✓' if ok else '✗'} {p['key']}/{case}: tags {sorted(tg)} · {vals if case != 'spam' else ''} · "
                  f"cards {[(o.get('source'), o.get('monetaryValue')) for o in opps]}")
        for cid in made.values():
            for o in contact_state(a, cid, cfs)[2]:
                a.call("DELETE", SERVICES, f"/opportunities/{o['id']}")
            a.call("DELETE", SERVICES, f"/contacts/{cid}")
        drop_flow(a, wid)
    print(f"   limpo; e-mails (alertas + confirmações) em {to}. Esperado por página: new 1 alerta (o repeat é barrado), "
          "customer 1 com 'existing customer', spam 0.")
    return 1 if bad else 0


def line(a: Agency, flows: dict, apply: bool) -> None:
    """LINE into the IVR trigger (rings Fareed like the main line) + a call workflow that tags its callers."""
    t = next(x for x in a.triggers(LOC, flows[IVR]) if not x.get("deleted"))
    c = next(x for x in t["conditions"] if x.get("field") == "inbound_number")
    print(f"   {IVR}: {LINE} {'já está' if LINE in c['value'] else 'entra no gatilho'}")
    if apply and LINE not in c["value"]:
        (BDIR / f"trigger-{t['id']}-{time.strftime('%Y%m%d-%H%M%S')}.json").write_text(json.dumps(t))
        c["value"] = [*c["value"], LINE]
        body = {k: v for k, v in t.items() if k not in DROP}
        body.update({"workflowId": flows[IVR], "workflow_id": flows[IVR], "location_id": LOC})
        a.call("PUT", BACKEND, f"/workflow/{LOC}/trigger/{t['id']}", body=body)
    print(f"   {CALL_FLOW}: {'existe' if CALL_FLOW in flows else 'cria'} (tags google ads call + adwords)")
    if apply and CALL_FLOW not in flows:
        tpl = chain([tags(["google ads call", "adwords"])])
        wid = create_flow(a, CALL_FLOW, a.workflow(LOC, flows[FOLDER_OF]).get("parentId"), tpl, False)
        trig = {"type": "call_status", "name": "Call Status", "masterType": "highlevel", "schedule_config": {},
                "conditions": [{"field": "message.direction", "operator": "==", "value": "inbound", "title": "Call Direction", "type": "select"},
                               {"field": "inbound_number", "operator": "contains-any", "id": "inbound-twilio-number", "value": [LINE],
                                "title": "In Phone Number", "type": "multiselect"}],
                "workflowId": wid, "workflow_id": wid, "location_id": LOC,
                "actions": [{"workflow_id": wid, "type": "add_to_workflow"}], "targetActionId": tpl[0]["id"]}
        tr = a.call("POST", BACKEND, f"/workflow/{LOC}/trigger", body=trig)
        a.call("PUT", BACKEND, f"/workflow/{LOC}/trigger/{tr['id']}", body={**trig, "id": tr["id"]})
        live = a.workflow(LOC, wid)
        a.call("PUT", BACKEND, f"/workflow/{LOC}/{wid}", body={"name": CALL_FLOW, "version": live.get("version", 1),
               "status": "published", "parentId": live.get("parentId"), "allowMultiple": True,
               "workflowData": {"templates": live["workflowData"]["templates"]}})
    if apply:
        time.sleep(5)
        num = next(n for n in a.call("GET", SERVICES, f"/phone-system/numbers/location/{LOC}").get("numbers", [])
                   if n["phoneNumber"] == LINE)
        print(f"   conferido {LINE}: inboundCallService {num.get('inboundCallService')}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("mode", choices=["plan", "test", "apply"])
    parser.add_argument("--to", help="test: inbox that gets the lead alerts and confirmations")
    args = parser.parse_args()
    if args.mode == "test" and not args.to:
        parser.error("--to is required in test mode")
    load_dotenv()
    a = Agency()
    if a.location(LOC)["name"] != "NORTEX POOLS":
        sys.exit("sub-conta errada")
    BDIR.mkdir(parents=True, exist_ok=True)
    forms = {f["name"]: f.get("_id") or f.get("id") for f in a.forms(LOC)}
    flows = {w["name"]: w["id"] for w in a.workflows(LOC)}
    folder = a.workflow(LOC, flows[FOLDER_OF]).get("parentId")
    _, base = latest_form_data(a, BASE_FORM)

    if args.mode == "plan":
        line(a, flows, False)
        cfs = {c["name"]: c for c in a.custom_fields(LOC)}
        for n in (PAGE_FIELD, EQUIP_FIELD):
            cfs.setdefault(n, {"id": f"<{n}>", "fieldKey": "contact." + n.lower().replace(" ", "_")})
        for p in PAGES:
            fd = build_form(base, p, cfs)
            print(f"\n== {p['form']}: {'existe' if p['form'] in forms else 'cria'} → {fd['form']['formAction']['redirect_url']}")
            print("   campos:", " · ".join(f"{re.sub('<[^>]+>', '', x.get('label') or '')}{'*' if x.get('required') else ''}"
                                         for x in fd["form"]["fields"]))
            print(f"   {p['flow']}: {'existe' if p['flow'] in flows else 'cria'}\n{outline(build_flow(p, cfs))}")
        return 0

    cfs = ensure_fields(a)
    if args.mode == "test":
        return test(a, cfs, folder, args.to)

    for p in PAGES:
        if p["form"] in forms:
            fid = forms[p["form"]]
            cur, cur_fd = latest_form_data(a, fid)
            (BDIR / f"form-{fid}-{time.strftime('%Y%m%d-%H%M%S')}.json").write_text(json.dumps({"form": cur, "formData": cur_fd}))
            for wait in (10, 30, 60, 120, 240):  # a new form answers 404 to updates for a few minutes
                time.sleep(wait)
                try:
                    a.call("POST", BACKEND, f"/forms/{fid}", body={"name": p["form"], "formData": build_form(base, p, cfs)})  # create drops redirect_url
                    break
                except Exception:  # noqa: BLE001
                    pass
            print(f"   ✓ form {p['form']} refeito ({fid})")
        else:
            res = a.call("POST", BACKEND, "/forms/", body={"name": p["form"], "locationId": LOC, "formData": build_form(base, p, cfs)})
            fid = forms[p["form"]] = (res.get("form") or res).get("_id") or (res.get("form") or res).get("id")
            a.call("POST", BACKEND, f"/forms/{fid}", body={"name": p["form"], "formData": build_form(base, p, cfs)})  # create drops redirect_url
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
    line(a, flows, True)
    print("\n   links:", {p["form"]: f"https://link.poolprofits.com/widget/form/{forms[p['form']]}" for p in PAGES})
    return 0


if __name__ == "__main__":
    sys.exit(main())
