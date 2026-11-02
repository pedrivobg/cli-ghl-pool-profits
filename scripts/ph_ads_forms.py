#!/usr/bin/env python3
"""Poolheads: 3 Google Ads landing pages — Weekly Pool Service, Pool Repairs, Leak Detection (Val brief, 02/11).

    ./.venv/bin/python scripts/ph_ads_forms.py plan
    ./.venv/bin/python scripts/ph_ads_forms.py test --to pedro@poolprofits.com
    ./.venv/bin/python scripts/ph_ads_forms.py apply                       # forms + published workflows + line
    ./.venv/bin/python scripts/ph_ads_forms.py thanks                      # forms → thank-you pages, once Atif's exist

Forms "GOOGLE ADS – WEEKLY / – REPAIR / – LEAK DETECTION", built from the newest version of "Landing Page - Optin Form"
(same look): Full Name*, Phone* (US picker), ZIP Code*, Email (optional), the page's optional question (repair: "What
equipment needs repair?"; leak: "What problem are you experiencing?"), the consent checkbox, the page's CTA. Until the
thank-you pages exist the form shows a thank-you message (`thanks` switches them to a redirect).
Workflows "Google Ads LP - Weekly|Repair|Leak Detection" (folder of "AdWords Form - New Lead"), one if/else first:
  Spam / DND             → nothing.
  Sent in the last 24 h  → nothing (a second submit of the same form within a day: no second card or alert).
  Current customer       → tags, fields, alerts to Felipe marked existing customer; no card.
  New lead               → tags `google ads`, `poolheads`, `landing page lead`, `pool service|pool repair|leak detection`,
                           `new lead`; fields Service Requested + Landing Page (+ the page's answer); card in Pool Leads →
                           New Lead (source "Google Ads LP - …"); Google Ads conversion (works once Google Ads is
                           connected in GHL); text + email to Felipe with the service.
Every branch: wait 1 day → remove the 24 h tag. No automatic text to the lead (not asked; easy to add).
Line (936) 301-0309 ("Google Adwords", routed nowhere): joins "Business Hours Call Routing" (rings like the main lines;
cards/missed-call text come from the account's call workflows) and "Google Ads Call - Tag" tags its callers
`google ads call` + `google ads`.
test: temporary copies with alerts to --to, no text to Felipe, no conversion; contacts through the API for every branch
+ a repeat; checks tags, fields and cards, then deletes everything.
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

LOC = "PeUynYCMm8e6PJMy785O"
BASE_FORM = "oz7TXXdom7c5r49emChQ"  # Landing Page - Optin Form
FOLDER_OF = "AdWords Form - New Lead"
FELIPE, FELIPE_EMAIL = "PTRbzJWOILyLyoz9aOfK", "felipe.cobo4@gmail.com"  # Val: confirm Felipe's preferred email
PIPELINE, NEW_LEAD = "G9rTMfwWHDIzU5NOtlbv", "7c193a0d"  # stage id prefix, resolved at run time
SERVICE_FIELD, PAGE_FIELD = "Service Requested", "Landing Page"
LINE, IVR, CALL_FLOW = "+19363010309", "Business Hours Call Routing", "Google Ads Call - Tag"
SITE = "https://go.poolheadscare.com"
SPAM = ["spam", "dnd"]
CUSTOMER = ["existing customer", "recurring customer", "current customer", "won"]
COMMON = ["google ads", "poolheads", "landing page lead", "new lead"]
BDIR = ROOT / "backup" / "poolheads"

PAGES = [
    {"key": "weekly", "form": "GOOGLE ADS – WEEKLY", "flow": "Google Ads LP - Weekly", "tag": "pool service",
     "cta": "Get My Free Pool Service Quote", "service": "Weekly Pool Service", "source": "Google Ads LP - Weekly",
     "page": "Google Ads LP - Weekly Pool Service", "thanks": "/thank-you-pool-service", "question": None},
    {"key": "repair", "form": "GOOGLE ADS – REPAIR", "flow": "Google Ads LP - Repair", "tag": "pool repair",
     "cta": "Get My Pool Repair Quote", "service": "Pool Repair", "source": "Google Ads LP - Repair",
     "page": "Google Ads LP - Pool Repairs", "thanks": "/thank-you-pool-repair",
     "question": ("Equipment Needing Repair", "What equipment needs repair?", "Select equipment (optional)",
                  ["Pool Pump", "Pool Heater", "Pool Filter", "Plumbing / Valves", "Electrical", "Automation System",
                   "Not Sure / Other"])},
    {"key": "leak", "form": "GOOGLE ADS – LEAK DETECTION", "flow": "Google Ads LP - Leak Detection", "tag": "leak detection",
     "cta": "Request My Leak Detection Quote", "service": "Leak Detection", "source": "Google Ads LP - Leak Detection",
     "page": "Google Ads LP - Pool Leak Detection", "thanks": "/thank-you-leak-detection",
     "question": ("Leak Problem", "What problem are you experiencing?", "Select a problem (optional)",
                  ["Pool losing water faster than normal", "Constantly refilling the pool", "High water bills",
                   "Suspected underground plumbing leak", "Water around fittings or equipment", "Other"])},
]
THANKS = ("<p style='font-family: Inter, sans-serif; font-size: 18px; font-weight: 600; text-align: center;'>Thank you! "
          "We received your request and a Poolheads team member will reach out shortly.</p>")


def recent(p: dict) -> str:
    return f"google ads lp {p['key']} 24h"


# ── forms ─────────────────────────────────────────────────────────────────

def question_field(p: dict, cfs: dict) -> list[dict]:
    if not p["question"]:
        return []
    name, label, placeholder, options = p["question"]
    cf = cfs[name]
    return [{"dataType": "SINGLE_OPTIONS", "fieldKey": cf["fieldKey"], "fieldName": name,
             "hiddenFieldQueryKey": cf["fieldKey"].split(".")[-1], "id": cf["id"], "label": label, "locationId": LOC,
             "model": "contact", "name": name, "picklistOptions": options, "placeholder": placeholder, "position": 0,
             "required": False, "tag": cf["id"], "type": "single_options", "fieldWidthPercentage": 100}]


def build_form(base: dict, p: dict, cfs: dict, redirect: bool = False) -> dict:
    fd = copy.deepcopy(base)
    f = fd["form"]
    by = {x["tag"]: x for x in f["fields"]}
    header = [copy.deepcopy(x) for x in f["fields"] if x.get("type") == "h1"]
    name, phone, email, zip_, consent, button = (copy.deepcopy(by[k]) for k in (
        "full_name", "phone", "email", "postal_code", "terms_and_conditions", "button"))
    name.update(required=True, label="Full Name", placeholder="Full Name")
    phone.update(required=True, placeholder="Phone", enableCountryPicker=True)
    zip_.update(required=True, label="ZIP Code", placeholder="ZIP Code", title="ZIP Code", fieldWidthPercentage=100)
    email.update(required=False, label="Email (optional)", placeholder="Email")
    consent.update(required=True)
    consent.pop("placeholder2", None)  # transactional consent only (one required box)
    if "<strong>" in button["label"]:
        button["label"] = re.sub(r"<strong>[^<]*</strong>", f"<strong>{p['cta'].upper()}</strong>", button["label"], count=1)
    else:
        button["label"] = f'<p style="text-align: center;padding-left: 0px!important;"><strong>{p["cta"].upper()}</strong></p>'
    f["fields"] = [name, phone, zip_, email, *question_field(p, cfs), consent, button, *header]
    if redirect:
        url = SITE + p["thanks"]
        f["formAction"] = {**(f.get("formAction") or {}), "actionType": "1", "redirectUrl": url, "redirect_url": url}
    else:
        f["formAction"] = {**(f.get("formAction") or {}), "actionType": "2", "thankyouText": THANKS, "redirectUrl": "", "redirect_url": ""}
    return keep_redirect(fd)


# ── workflow ──────────────────────────────────────────────────────────────

def fields(cfs: dict, p: dict) -> tuple[str, str, dict]:
    vals = [(SERVICE_FIELD, p["service"]), (PAGE_FIELD, p["page"])]
    return ("update_contact_field", "Set Service Requested / Landing Page", {
        "type": "update_contact_field", "actionType": "update_field_data",
        "fields": [{"field": cfs[n]["id"], "value": v, "title": n, "type": "text", "date": ""} for n, v in vals]})


def rows(p: dict, cfs: dict) -> list[tuple[str, str]]:
    out = [("Name", "{{contact.name}}"), ("Phone", "{{contact.phone}}"), ("Service", p["service"])]
    if p["question"]:
        out.append((p["question"][1].rstrip("?"), "{{" + cfs[p["question"][0]]["fieldKey"] + "}}"))
    return out + [("ZIP", "{{contact.postal_code}}"), ("Email", "{{contact.email}}"), ("Source", f"Google Ads – {p['page']}")]


def alert_sms(p: dict, cfs: dict, customer: bool) -> tuple[str, str, dict]:
    body = (f"🚨 NEW GOOGLE ADS LEAD - {p['service'].upper()} 🚨" + (" (EXISTING CUSTOMER)" if customer else "") + "\n\n" +
            "\n".join(f"{k}: {v}" for k, v in rows(p, cfs)))
    return ("internal_notification", "Text Felipe", {"type": "sms", "sms": {
        "body": body, "userType": "user", "selectedUser": [FELIPE], "attachments": []}})


def alert_email(p: dict, cfs: dict, customer: bool, to: str = FELIPE_EMAIL) -> tuple[str, str, dict]:
    html = P.format("New lead from a Google Ads landing page" + (" <b>(existing customer)</b>" if customer else "") + ":") + \
        "".join(P.format(f"<b>{k}:</b> {v}") for k, v in rows(p, cfs))
    return ("internal_notification", "Email Felipe", {"type": "email", "email": {
        "userType": "custom_email", "to": to, "subject": f"🚨 New Google Ads lead ({p['service']}): {{{{contact.name}}}}",
        "html": html}})


def build_flow(p: dict, cfs: dict, stage: str, test_to: str | None = None) -> list[dict]:
    release = [wait_day(), ("remove_contact_tag", "Remove 24 h tag", {"type": "remove_contact_tag", "tags": [recent(p)]})]
    all_tags = [*COMMON, p["tag"], recent(p)]

    def alerts(customer: bool) -> list:
        if test_to:  # test copy: one email to the tester, nothing to Felipe
            return [alert_email(p, cfs, customer, test_to)]
        return [alert_sms(p, cfs, customer), alert_email(p, cfs, customer)]

    card = ("create_opportunity", "Card in New Lead", {
        "fields": [], "type": "create_opportunity", "pipeline_id": PIPELINE, "pipeline_stage_id": stage,
        "opportunity_name": "{{contact.name}}", "opportunity_source": p["source"], "monetary_value": "",
        "opportunity_status": "open"})
    conversion = ("google_adword", "Google Ads conversion", {
        "type": "google_adword", "currency": "USD", "conversion_value": "1", "conversion_type": "",
        "conversion_name": "", "conversion_action_id": "", "customMapping": {"gclid": "{{contact.attributionSource.gclid}}"},
        "isCustomMappingEnabled": True})
    lead = [tags(all_tags), fields(cfs, p), card, *([] if test_to else [conversion]), *alerts(False), *release]
    customer = [tags([t for t in all_tags if t != "new lead"]), fields(cfs, p), *alerts(True), *release]
    nodes, _ = if_else("Route the lead", [
        ("Spam / DND", [cond("tags", "index-of-true", [t]) for t in SPAM], []),
        ("Sent in the last 24 h", [cond("tags", "index-of-true", [recent(p)])], []),
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
    specs = [(SERVICE_FIELD, {"dataType": "TEXT"}), (PAGE_FIELD, {"dataType": "TEXT"})] + \
        [(p["question"][0], {"dataType": "SINGLE_OPTIONS", "options": p["question"][3]}) for p in PAGES if p["question"]]
    for name, spec in specs:
        if name not in cfs:
            res = a.call("POST", SERVICES, f"/locations/{LOC}/customFields",
                         body={"name": name, "placeholder": "", "position": 0, "model": "contact", **spec})
            cfs[name] = res.get("customField") or res
            print(f"   ✓ campo {name} ({cfs[name].get('fieldKey')})")
    for t in {*COMMON, "google ads call", *(p["tag"] for p in PAGES), *(recent(p) for p in PAGES)}:
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


def test(a: Agency, cfs: dict, stage: str, folder: str | None, to: str) -> int:
    stamp, bad = int(time.time()), 0
    for p in PAGES:
        wid = create_flow(a, f"ZZ TEST {p['flow']}", folder, build_flow(p, cfs, stage, to), True)
        made = {}
        try:
            for case, extra in (("new", {}), ("customer", {"tags": ["existing customer"]}), ("spam", {"tags": ["spam"]})):
                made[case] = a.call("POST", SERVICES, "/contacts/", body={
                    "locationId": LOC, "firstName": "ZZ Test", "lastName": f"{p['key']} {case}", "postalCode": "77380",
                    "email": to.replace("@", f"+ph-{p['key']}-{case}-{stamp}@"), **extra})["contact"]["id"]
            time.sleep(3)
            for cid in made.values():
                a.call("POST", SERVICES, f"/contacts/{cid}/workflow/{wid}", body={})
            time.sleep(30)
            a.call("POST", SERVICES, f"/contacts/{made['new']}/workflow/{wid}", body={})  # same form again
            time.sleep(30)
            want = {"new": ({*COMMON, p["tag"], recent(p)}, 1), "customer": ({p["tag"], "google ads"}, 0), "spam": (set(), 0)}
            for case, cid in made.items():
                tg, vals, opps = contact_state(a, cid, cfs)
                exp_tags, exp_cards = want[case]
                ok = exp_tags <= set(tg) and len(opps) == exp_cards and \
                    (case == "spam" and p["tag"] not in tg or case != "spam" and vals == {SERVICE_FIELD: p["service"], PAGE_FIELD: p["page"]}) and \
                    all(o.get("source") == p["source"] for o in opps)
                bad += not ok
                print(f"   {'✓' if ok else '✗'} {p['key']}/{case}: tags {sorted(tg)} · cards {[o.get('source') for o in opps]}")
        finally:
            for cid in made.values():
                for o in contact_state(a, cid, cfs)[2]:
                    a.call("DELETE", SERVICES, f"/opportunities/{o['id']}")
                a.call("DELETE", SERVICES, f"/contacts/{cid}")
            drop_flow(a, wid)
    print(f"   limpo; alertas em {to}. Esperado por página: new 1 (o repeat é barrado), customer 1 'existing customer', spam 0.")
    return 1 if bad else 0


def line(a: Agency, flows: dict, apply: bool) -> None:
    """LINE into the IVR trigger (rings like the main lines) + a call workflow that tags its callers."""
    t = next(x for x in a.triggers(LOC, flows[IVR]) if not x.get("deleted"))
    c = next(x for x in t["conditions"] if x.get("field") == "inbound_number")
    print(f"   {IVR}: {LINE} {'já está' if LINE in c['value'] else 'entra no gatilho'} ({c['value']})")
    if apply and LINE not in c["value"]:
        (BDIR / f"trigger-{t['id']}-{time.strftime('%Y%m%d-%H%M%S')}.json").write_text(json.dumps(t))
        c["value"] = [*c["value"], LINE]
        body = {k: v for k, v in t.items() if k not in DROP}
        body.update({"workflowId": flows[IVR], "workflow_id": flows[IVR], "location_id": LOC})
        a.call("PUT", BACKEND, f"/workflow/{LOC}/trigger/{t['id']}", body=body)
    print(f"   {CALL_FLOW}: {'existe' if CALL_FLOW in flows else 'cria'} (tags google ads call + google ads)")
    if apply and CALL_FLOW not in flows:
        tpl = chain([tags(["google ads call", "google ads"])])
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


def save_form(a: Agency, fid: str, name: str, fd: dict) -> None:
    for wait in (0, 10, 30, 60, 120, 240):  # a new form answers 404 to updates for a few minutes
        time.sleep(wait)
        try:
            a.call("POST", BACKEND, f"/forms/{fid}", body={"name": name, "formData": fd})
            return
        except Exception:  # noqa: BLE001
            pass
    print(f"   ✗ form {name}: não gravou, refazer")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("mode", choices=["plan", "test", "apply", "thanks"])
    parser.add_argument("--to", help="test: inbox that gets the lead alerts")
    args = parser.parse_args()
    if args.mode == "test" and not args.to:
        parser.error("--to is required in test mode")
    load_dotenv()
    a = Agency()
    if a.location(LOC)["name"].lower() != "poolheads":
        sys.exit(f"sub-conta errada: {a.location(LOC)['name']}")
    BDIR.mkdir(parents=True, exist_ok=True)
    forms = {f["name"]: f.get("_id") or f.get("id") for f in a.forms(LOC)}
    flows = {w["name"]: w["id"] for w in a.workflows(LOC)}
    folder = a.workflow(LOC, flows[FOLDER_OF]).get("parentId")
    stage = next(s["id"] for p in a.pipelines(LOC) if p["id"] == PIPELINE for s in p["stages"] if s["id"].startswith(NEW_LEAD))
    _, base = latest_form_data(a, BASE_FORM)

    if args.mode == "plan":
        cfs = {c["name"]: c for c in a.custom_fields(LOC)}
        for n in (SERVICE_FIELD, PAGE_FIELD, *(p["question"][0] for p in PAGES if p["question"])):
            cfs.setdefault(n, {"id": f"<{n}>", "fieldKey": f"contact.<{n}>"})
        for p in PAGES:
            fd = build_form(base, p, cfs)
            print(f"\n== {p['form']}: {'existe' if p['form'] in forms else 'cria'}")
            print("   campos:", " · ".join(f"{re.sub('<[^>]+>', '', x.get('label') or '')}{'*' if x.get('required') else ''}"
                                         for x in fd["form"]["fields"] if x.get("type") != "h1"))
            print(f"   {p['flow']}: {'existe' if p['flow'] in flows else 'cria'}\n{outline(build_flow(p, cfs, stage))}")
        line(a, flows, False)
        return 0

    cfs = ensure_fields(a)
    if args.mode == "test":
        return test(a, cfs, stage, folder, args.to)
    if args.mode == "thanks":
        for p in PAGES:
            fid = forms[p["form"]]
            cur, cur_fd = latest_form_data(a, fid)
            (BDIR / f"form-{fid}-{time.strftime('%Y%m%d-%H%M%S')}.json").write_text(json.dumps({"form": cur, "formData": cur_fd}))
            save_form(a, fid, p["form"], build_form(base, p, cfs, redirect=True))
            print(f"   {p['form']} → {SITE + p['thanks']}")
        return 0

    for p in PAGES:
        if p["form"] in forms:
            fid = forms[p["form"]]
            print(f"   form {p['form']}: já existe ({fid})")
        else:
            res = a.call("POST", BACKEND, "/forms/", body={"name": p["form"], "locationId": LOC, "formData": build_form(base, p, cfs)})
            fid = forms[p["form"]] = (res.get("form") or res).get("_id") or (res.get("form") or res).get("id")
            print(f"   ✓ form {p['form']}: {fid}")
        if p["flow"] in flows:
            print(f"   {p['flow']}: já existe")
            continue
        tpl = build_flow(p, cfs, stage)
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
        ok = got["status"] == "published" and refs_ok(got["workflowData"]["templates"]) and len(trs) == 1 and \
            trs[0].get("active") and trs[0]["conditions"][0]["value"] == [fid]
        print(f"   {'✓' if ok else '✗ VERIFICAR'} {p['flow']}: {got['status']} · {len(tpl)} passos · form {fid}")
    line(a, flows, True)
    print("\n   forms:", {p["form"]: forms[p["form"]] for p in PAGES})
    return 0


if __name__ == "__main__":
    sys.exit(main())
