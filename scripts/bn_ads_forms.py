#!/usr/bin/env python3
"""Bonneville Pool Maintenance: 2 Google Ads landing pages (Val/Atif brief, ClickUp 86bcwer98, 12/11). One form per page,
its tag, lead alerts and Google Ads conversion.

    ./.venv/bin/python scripts/bn_ads_forms.py plan
    ./.venv/bin/python scripts/bn_ads_forms.py test --to pedro@poolprofits.com
    ./.venv/bin/python scripts/bn_ads_forms.py apply [--thanks-weekly URL --thanks-repair URL]

Forms (names from the brief), built from the newest version of "Landing Page - Optin Form" (same look):
  "Bonneville — Weekly Pool Service": Full Name*, Phone* (US picker), Email, Service ZIP*, Pool details (optional).
  "Bonneville — Pool Equipment & Hot Tub Repair": Full Name*, Phone*, Email, Service ZIP*, Repair type* (Pool Equipment /
  Hot Tub), What's happening?*, Brand / model (optional).
  One required consent checkbox (transactional). The page's CTA on the button. Thank-you: inline message until the pages'
  thank-you URLs exist (then --thanks-*: redirectUrl + redirect_url).
Workflows "Google Ads LP - Weekly Pool Service" / "Google Ads LP - Pool & Hot Tub Repair" (folder of "AdWords Form - New
Lead"), one if/else first:
  Spam / DND             → nothing.
  Sent in the last 24 h  → nothing (second submit the same day: no second card, alert or text).
  Current customer       → tags, fields, alerts to Justin (marked existing customer), confirmations; no card.
  New lead               → tags, fields, card in Pool Leads → New Lead (source = the page), Google Ads conversion (needs
                           Google Ads connected in GHL; then pick the conversion action), text + email to Justin (name,
                           phone, ZIP, repair type, issue, brand/model), confirmation text + email to the lead; ZIP in the
                           brief's 5 → "service area zip", else "outside service area".
Every branch: wait 1 day → remove the 24 h tag. Tags (brief): "Google Ads form - Weekly Pool Service" / "Google Ads form -
Pool and Hot Tub Repair" (GHL keeps tags lowercase) + the account's "new lead" and "adwords".
Alert e-mail: service@bonnevillepool.com (Justin's login and Basecamp address; the site's other one, bonnevillepools.com,
is a typo of the domain).
test: temporary copies, alerts by e-mail to --to only (no text to Justin, no conversion), contacts without phone enrolled
through the API for every branch + a repeat; checks tags, fields, cards, then deletes everything.
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
from ps_ads_forms import P, cond, if_else, outline, tags, wait_day
from pp_source_tags import refs_ok

from cli_anything.gohighlevel.utils.agency import BACKEND, SERVICES, Agency

LOC = "DeSfqW31OleIiU7eUt35"
BASE_FORM = "n1jMgk9402G69dgVT4AT"  # Landing Page - Optin Form
FOLDER_OF = "AdWords Form - New Lead"
JUSTIN, JUSTIN_EMAIL = "XzSsxDcxzMQl64Bvost3", "service@bonnevillepool.com"
PIPELINE, NEW_LEAD = "M1FAiKCvISskDdl8O8Cw", "66605aff-c98c-45a3-bf7e-9a9b3b6829e2"
ZIPS = ["84037", "84040", "84041", "84025", "84075"]
REPAIR_TYPES = ["Pool Equipment", "Hot Tub"]
SPAM = ["spam", "dnd"]
CUSTOMER = ["existing customer", "recurring customer", "won"]
NUMBER = "{{custom_values.a2p_verification_number}}"
BDIR = ROOT / "backup" / "bonneville-pool-maintenance"
# name → (dataType, extra)
FIELDS = {"Service Requested": ("TEXT", {}), "Landing Page": ("TEXT", {}), "Pool Details": ("LARGE_TEXT", {}),
          "Repair Type": ("SINGLE_OPTIONS", {"options": REPAIR_TYPES}), "Issue Description": ("LARGE_TEXT", {}),
          "Brand / Model": ("TEXT", {})}

PAGES = [
    {"key": "weekly", "form": "Bonneville — Weekly Pool Service", "flow": "Google Ads LP - Weekly Pool Service",
     "tag": "google ads form - weekly pool service", "cta": "Request My Weekly Pool Service Quote",
     "service": "Weekly Pool Service", "page": "Google Ads LP - Weekly Pool Service (/weekly-pool-service)",
     "source": "Google Ads LP - Weekly Pool Service",
     "sms": "Hi {{contact.first_name}}, thanks for requesting a weekly pool service quote from Bonneville Pool "
            "Maintenance! We received your info and will reach out shortly. Questions? Call or text " + NUMBER + ". "
            "Reply STOP to opt out.",
     "subject": "We received your weekly pool service request",
     "email": "Thanks for reaching out to Bonneville Pool Maintenance about weekly pool service. We received your "
              "request and will contact you shortly to go over your pool and your personalized quote."},
    {"key": "repair", "form": "Bonneville — Pool Equipment & Hot Tub Repair", "flow": "Google Ads LP - Pool & Hot Tub Repair",
     "tag": "google ads form - pool and hot tub repair", "cta": "Request My Repair Quote",
     "service": "Pool Equipment & Hot Tub Repair", "page": "Google Ads LP - Pool Equipment & Hot Tub Repair (/pool-and-hot-tub-repair)",
     "source": "Google Ads LP - Pool & Hot Tub Repair",
     "sms": "Hi {{contact.first_name}}, thanks for your repair request with Bonneville Pool Maintenance! We received "
            "your info and will reach out shortly. Questions? Call or text " + NUMBER + ". Reply STOP to opt out.",
     "subject": "We received your repair request",
     "email": "Thanks for reaching out to Bonneville Pool Maintenance about your {{contact.repair_type}} repair. We "
              "received your request and will contact you shortly to go over the problem and your repair quote."},
]


# ── forms ─────────────────────────────────────────────────────────────────

def custom(cf: dict, label: str, kind: str, required: bool, placeholder: str) -> dict:
    types = {"TEXT": ("text", "Single Line"), "LARGE_TEXT": ("large_text", "Multi Line"),
             "SINGLE_OPTIONS": ("single_options", "Dropdown (Single)")}
    t, tl = types[kind]
    out = {"label": label, "tag": cf["id"], "id": cf["id"], "hiddenFieldQueryKey": cf["fieldKey"].split(".")[-1],
           "type": t, "dataType": kind, "typeLabel": tl, "placeholder": placeholder, "required": required,
           "standard": False, "custom": True, "model": "contact", "name": cf["name"], "fieldName": cf["name"],
           "fieldKey": cf["fieldKey"], "locationId": LOC, "position": 0, "fieldWidthPercentage": 100}
    if kind == "SINGLE_OPTIONS":
        out["picklistOptions"] = REPAIR_TYPES
    return out


def build_form(base: dict, p: dict, cfs: dict, thanks: str | None) -> dict:
    fd = copy.deepcopy(base)
    f = fd["form"]
    by = {x["tag"]: x for x in f["fields"]}
    header = [copy.deepcopy(x) for x in f["fields"] if x.get("type") == "h1"]
    name, phone, email, zip_, consent, button = (copy.deepcopy(by[k]) for k in (
        "full_name", "phone", "email", "postal_code", "terms_and_conditions", "button"))
    name.update(required=True)
    phone.update(required=True, placeholder="Phone", enableCountryPicker=True)
    email.update(required=False)
    zip_.update(required=True, label="Service ZIP Code", placeholder="Service ZIP Code", title="Service ZIP Code")
    consent.update(required=True)
    consent.pop("placeholder2", None)  # transactional consent only (one required box)
    button["label"] = re.sub(r"<strong>[^<]*</strong>", f"<strong>{p['cta'].upper()}</strong>", button["label"], count=1) \
        if "<strong>" in (button.get("label") or "") else p["cta"]
    if p["key"] == "weekly":
        extra = [custom(cfs["Pool Details"], "Pool details (optional)", "LARGE_TEXT", False,
                        "Pool size, type, anything we should know")]
    else:
        extra = [custom(cfs["Repair Type"], "What needs repair?", "SINGLE_OPTIONS", True, "Pool Equipment / Hot Tub"),
                 custom(cfs["Issue Description"], "What's happening?", "LARGE_TEXT", True,
                        "Describe the issue (error code if you see one)"),
                 custom(cfs["Brand / Model"], "Brand / model (optional)", "TEXT", False, "Brand / model")]
    f["fields"] = [name, phone, email, zip_, *extra, consent, button, *header]
    if thanks:
        f["formAction"] = {**(f.get("formAction") or {}), "actionType": "1", "redirectUrl": thanks, "redirect_url": thanks}
    else:
        f["formAction"] = {**(f.get("formAction") or {}), "actionType": "2", "redirect_url": "",
                           "thankyouText": "Thank you! We received your request and will reach out shortly."}
    return keep_redirect(fd)


# ── workflow ──────────────────────────────────────────────────────────────

def set_fields(cfs: dict, p: dict) -> tuple[str, str, dict]:
    vals = [("Service Requested", p["service"]), ("Landing Page", p["page"])]
    return ("update_contact_field", "Set Service Requested / Landing Page", {
        "type": "update_contact_field", "actionType": "update_field_data",
        "fields": [{"field": cfs[n]["id"], "value": v, "title": n, "type": "text", "date": ""} for n, v in vals]})


def details(p: dict, cfs: dict) -> list[tuple[str, str]]:
    k = {n: "{{" + cfs[n]["fieldKey"] + "}}" for n in FIELDS}
    rows = [("Name", "{{contact.name}}"), ("Phone", "{{contact.phone}}"), ("Service ZIP", "{{contact.postal_code}}"),
            ("Service", p["service"])]
    if p["key"] == "weekly":
        rows += [("Pool details", k["Pool Details"])]
    else:
        rows += [("Repair type", k["Repair Type"]), ("Issue", k["Issue Description"]), ("Brand / model", k["Brand / Model"])]
    return rows + [("Email", "{{contact.email}}"), ("Source", "Google Ads landing page")]


def alert_sms(p: dict, cfs: dict, customer: bool) -> tuple[str, str, dict]:
    body = f"🚨 NEW GOOGLE ADS LEAD - {p['service'].upper()} 🚨" + (" (EXISTING CUSTOMER)" if customer else "") + "\n\n" + \
        "\n".join(f"{a}: {b}" for a, b in details(p, cfs))
    return ("internal_notification", "Text Justin", {"type": "sms", "sms": {
        "body": body, "userType": "user", "selectedUser": [JUSTIN], "attachments": []}})


def alert_email(p: dict, cfs: dict, customer: bool, to: str = JUSTIN_EMAIL) -> tuple[str, str, dict]:
    html = P.format("New lead from a Google Ads landing page" + (" <b>(existing customer)</b>" if customer else "") + ":") + \
        "".join(P.format(f"<b>{a}:</b> {b}") for a, b in details(p, cfs))
    return ("internal_notification", "Email Justin", {"type": "email", "email": {
        "userType": "custom_email", "to": to, "subject": f"🚨 New Google Ads lead ({p['service']}): {{{{contact.name}}}}",
        "html": html}})


def confirm(p: dict) -> list[tuple[str, str, dict]]:
    paras = ["Hi {{contact.first_name}},", p["email"], "If you need us sooner, call or text us at " + NUMBER + ".",
             "Thank you,<br>Bonneville Pool Maintenance"]
    return [("sms", "Confirmation text", {"body": p["sms"], "attachments": []}),
            ("email", "Confirmation email", {"subject": p["subject"], "html": "".join(P.format(x) for x in paras),
                                             "from_name": "{{custom_values.friendly_business_name}}", "from_email": "",
                                             "attachments": []})]


def build_flow(p: dict, cfs: dict, test_to: str | None = None) -> list[dict]:
    recent = f"google ads lp {p['key']} 24h"
    release = [wait_day(), ("remove_contact_tag", "Remove 24 h tag", {"type": "remove_contact_tag", "tags": [recent]})]
    base_tags = [p["tag"], "new lead", "adwords", recent]

    def alerts(customer: bool) -> list:
        if test_to:
            return [alert_email(p, cfs, customer, test_to)]
        return [alert_sms(p, cfs, customer), alert_email(p, cfs, customer)]

    card = ("create_opportunity", "Card in New Lead", {
        "fields": [], "type": "create_opportunity", "pipeline_id": PIPELINE, "pipeline_stage_id": NEW_LEAD,
        "opportunity_name": "{{contact.name}}", "opportunity_source": p["source"], "monetary_value": "",
        "opportunity_status": "open"})
    conversion = ("google_adword", "Google Ads conversion", {
        "type": "google_adword", "currency": "USD", "conversion_value": "1", "conversion_type": "",
        "conversion_name": "", "conversion_action_id": "", "customMapping": {"gclid": "{{contact.attributionSource.gclid}}"},
        "isCustomMappingEnabled": True})
    zip_check = ("ifelse", "ZIP in the service area?",
                 [("Service area ZIP", [cond("postal_code", "==", z) for z in ZIPS],
                   [tags(["service area zip"]), *release])],
                 "Outside the area", [tags(["outside service area"]), *release])
    lead = [tags(base_tags), set_fields(cfs, p), card, *([] if test_to else [conversion]), *alerts(False), *confirm(p),
            zip_check]
    customer = [tags(base_tags), set_fields(cfs, p), *alerts(True), *confirm(p), *release]
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
    for name, (kind, extra) in FIELDS.items():
        if name not in cfs:
            res = a.call("POST", SERVICES, f"/locations/{LOC}/customFields",
                         body={"name": name, "placeholder": "", "position": 0, "model": "contact", "dataType": kind, **extra})
            cfs[name] = res.get("customField") or res
            print(f"   ✓ campo {name} ({cfs[name].get('fieldKey')})")
    for t in {"new lead", "adwords", "service area zip", "outside service area", *(p["tag"] for p in PAGES),
              *(f"google ads lp {p['key']} 24h" for p in PAGES)}:
        try:
            a.call("POST", BACKEND, f"/workflow/{LOC}/tags/create", body={"tag": t})
        except Exception:  # noqa: BLE001 — already exists
            pass
    return cfs


def contact_state(a: Agency, cid: str, cfs: dict) -> tuple[list, dict, list]:
    c = a.call("GET", SERVICES, f"/contacts/{cid}")["contact"]
    vals = {n: next((f.get("value") for f in c.get("customFields", []) if f.get("id") == cfs[n]["id"]), None)
            for n in ("Service Requested", "Landing Page")}
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
        for case, extra, zip_ in (("new", {}, "84037"), ("outside", {}, "84101"),
                                  ("customer", {"tags": ["existing customer"]}, "84040"), ("spam", {"tags": ["spam"]}, "84040")):
            body = {"locationId": LOC, "firstName": "ZZ Test", "lastName": f"{p['key']} {case}", "postalCode": zip_,
                    "email": to.replace("@", f"+bn-{p['key']}-{case}-{stamp}@"), **extra}
            body["customFields"] = ([{"id": cfs["Pool Details"]["id"], "field_value": "ZZ test: 20k gal plaster pool"}]
                                    if p["key"] == "weekly" else
                                    [{"id": cfs["Repair Type"]["id"], "field_value": "Hot Tub" if case == "outside" else "Pool Equipment"},
                                     {"id": cfs["Issue Description"]["id"], "field_value": "ZZ test: heater shows error code IF"},
                                     {"id": cfs["Brand / Model"]["id"], "field_value": "ZZ Pentair MasterTemp"}])
            made[case] = a.call("POST", SERVICES, "/contacts/", body=body)["contact"]["id"]
        time.sleep(3)
        for cid in made.values():
            a.call("POST", SERVICES, f"/contacts/{cid}/workflow/{wid}", body={})
        time.sleep(45)
        a.call("POST", SERVICES, f"/contacts/{made['new']}/workflow/{wid}", body={})  # same form again
        time.sleep(45)
        n = emails_sent(a, made["new"])
        bad += n != 1
        print(f"   {'✓' if n == 1 else '✗'} {p['key']}/repeat: {n} e-mail(s) de confirmação depois de 2 envios")
        base = {p["tag"], "new lead", "adwords"}
        want = {"new": (base | {"service area zip"}, 1), "outside": (base | {"outside service area"}, 1),
                "customer": (base, 0), "spam": (set(), 0)}
        for case, cid in made.items():
            tg, vals, opps = contact_state(a, cid, cfs)
            exp_tags, exp_cards = want[case]
            ok = exp_tags <= set(tg) and len(opps) == exp_cards and \
                (case == "spam" and p["tag"] not in tg or case != "spam" and vals == {"Service Requested": p["service"], "Landing Page": p["page"]}) and \
                all(o.get("source") == p["source"] for o in opps)
            bad += not ok
            print(f"   {'✓' if ok else '✗'} {p['key']}/{case}: tags {sorted(tg)} · {vals if case != 'spam' else ''} · "
                  f"cards {[o.get('source') for o in opps]}")
        for cid in made.values():
            for o in contact_state(a, cid, cfs)[2]:
                a.call("DELETE", SERVICES, f"/opportunities/{o['id']}")
            a.call("DELETE", SERVICES, f"/contacts/{cid}")
        drop_flow(a, wid)
    print(f"   limpo; alertas + confirmações em {to}. Esperado por página: new 1 alerta (repeat barrado), outside 1, "
          "customer 1 com 'existing customer', spam 0.")
    return 1 if bad else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("mode", choices=["plan", "test", "apply"])
    parser.add_argument("--to", help="test: inbox that gets the lead alerts and confirmations")
    parser.add_argument("--thanks-weekly")
    parser.add_argument("--thanks-repair")
    args = parser.parse_args()
    if args.mode == "test" and not args.to:
        parser.error("--to is required in test mode")
    thanks = {"weekly": args.thanks_weekly, "repair": args.thanks_repair}
    load_dotenv()
    a = Agency()
    if a.location(LOC)["name"] != "Bonneville Pool Maintenance":
        sys.exit("sub-conta errada")
    BDIR.mkdir(parents=True, exist_ok=True)
    forms = {f["name"]: f.get("_id") or f.get("id") for f in a.forms(LOC)}
    flows = {w["name"]: w["id"] for w in a.workflows(LOC)}
    folder = a.workflow(LOC, flows[FOLDER_OF]).get("parentId")
    _, base = latest_form_data(a, BASE_FORM)

    if args.mode == "plan":
        cfs = {c["name"]: c for c in a.custom_fields(LOC)}
        for n in FIELDS:
            cfs.setdefault(n, {"id": f"<{n}>", "name": n, "fieldKey": "contact." + re.sub(r"\W+", "_", n.lower()).strip("_")})
        for p in PAGES:
            fd = build_form(base, p, cfs, thanks[p["key"]])
            act = fd["form"]["formAction"]
            print(f"\n== {p['form']}: {'existe' if p['form'] in forms else 'cria'} → "
                  f"{act.get('redirect_url') or act.get('thankyouText')}")
            print("   campos:", " · ".join(f"{re.sub('<[^>]+>', '', x.get('label') or '')}{'*' if x.get('required') else ''}"
                                         for x in fd["form"]["fields"]))
            print(f"   {p['flow']}: {'existe' if p['flow'] in flows else 'cria'}\n{outline(build_flow(p, cfs))}")
        return 0

    cfs = ensure_fields(a)
    if args.mode == "test":
        return test(a, cfs, folder, args.to)

    for p in PAGES:
        fd = build_form(base, p, cfs, thanks[p["key"]])
        if p["form"] in forms:
            fid = forms[p["form"]]
            cur, cur_fd = latest_form_data(a, fid)
            (BDIR / f"form-{fid}-{time.strftime('%Y%m%d-%H%M%S')}.json").write_text(json.dumps({"form": cur, "formData": cur_fd}))
            a.call("POST", BACKEND, f"/forms/{fid}", body={"name": p["form"], "formData": fd})
            print(f"   ✓ form {p['form']} refeito ({fid})")
        else:
            res = a.call("POST", BACKEND, "/forms/", body={"name": p["form"], "locationId": LOC, "formData": fd})
            fid = forms[p["form"]] = (res.get("form") or res).get("_id") or (res.get("form") or res).get("id")
            for wait in (10, 30, 60, 120, 240):  # create drops redirect_url; a new form answers 404 for a few minutes
                time.sleep(wait)
                try:
                    a.call("POST", BACKEND, f"/forms/{fid}", body={"name": p["form"], "formData": fd})
                    break
                except Exception:  # noqa: BLE001
                    pass
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
    print("\n   links:", {p["form"]: f"https://link.poolprofits.com/widget/form/{forms[p['form']]}" for p in PAGES})
    return 0


if __name__ == "__main__":
    sys.exit(main())
