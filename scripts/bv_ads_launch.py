#!/usr/bin/env python3
"""Bonneville Pool Maintenance: Google Ads lead form + SMS asset + call line, CRM side (Val, ClickUp 86bcwer98, 19/11).

    python3 scripts/bv_ads_launch.py plan
    python3 scripts/bv_ads_launch.py test --to pedro@poolprofits.com
    python3 scripts/bv_ads_launch.py apply

1. "Google Ads Lead Form - New Lead": Google Lead Form Submitted (ad account 921-178-5517) → spam/DND or already in the
   last 24 h → nothing; current customer → tags + alert marked EXISTING CUSTOMER (no card, no auto text); new lead →
   tags google ads / google ads lead form / new lead / adwords, Landing Page = "Google Ads Lead Form", card in New Lead,
   SMS + e-mail alert to Justin, confirmation SMS + e-mail (same wording as the LP flows), then the service tag from
   Service Requested (weekly → "google ads lead form - weekly pool service", repair / hot tub → "... - pool and hot tub
   repair"; the form's service question has to be mapped to Service Requested in Integrations → Google Ads).
2. "Google Ads SMS - New Lead": a text to the Google Ads line (385) 503-7952 → tags google ads / google ads sms / new
   lead / adwords + card in New Lead. Justin's alert comes from "Inbound SMS - Notify Owner" (every text, already live).
3. "Google Ads Call - Tag": a call to the Google Ads line → tags google ads / google ads call / adwords (the card and
   the review task come from "Answered/Missed Incoming Call To Pipeline", already live).
All three skip spam/DND, current customers (SMS/call) and repeats within 24 h. GET + backup before any write.
"""
from __future__ import annotations

import argparse
import sys
import time

from _common import load_dotenv
from pd_lwr_google_leads import set_status
from ps_ads_forms import P, cond, if_else, outline, tags, wait_day
from pp_source_tags import refs_ok

import pd_lwr_google_leads as lwr
from cli_anything.gohighlevel.utils.agency import BACKEND, SERVICES, Agency

LOC = "DeSfqW31OleIiU7eUt35"
lwr.LOC = LOC
LINE = "+13855037952"
JUSTIN, JUSTIN_EMAIL = "XzSsxDcxzMQl64Bvost3", "service@bonnevillepool.com"
PIPELINE, NEW_LEAD = "M1FAiKCvISskDdl8O8Cw", "66605aff-c98c-45a3-bf7e-9a9b3b6829e2"
SERVICE_F, PAGE_F = "PK9IHoSdesbG5wqe5IYP", "TvKcZSo5cWbHyuUpImUY"
FOLDER_OF = "Google Ads LP - Weekly Pool Service"
SPAM = ["spam", "spam likely", "dnd"]
CUSTOMER = ["current customer", "existing customer", "active client"]
WEEKLY_TAG = "google ads lead form - weekly pool service"
REPAIR_TAG = "google ads lead form - pool and hot tub repair"
SMS_TEXT = ("Hi {{contact.first_name}}, thanks for requesting a quote from Bonneville Pool Maintenance! We received your "
            "info and will reach out shortly. Questions? Call or text {{custom_values.a2p_verification_number}}. "
            "Reply STOP to opt out.")
EMAIL_HTML = "".join(P.format(x) for x in (
    "Hi {{contact.first_name}},",
    "Thanks for reaching out to Bonneville Pool Maintenance. We received your request and will contact you shortly to "
    "go over your pool or hot tub and your personalized quote.",
    "If you need us sooner, call or text us at {{custom_values.a2p_verification_number}}.",
    "Thank you,<br>Bonneville Pool Maintenance"))
FLOWS = {
    "form": {"flow": "Google Ads Lead Form - New Lead", "source": "Google Ads Lead Form", "recent": "google ads lead form 24h",
             "tags": ["google ads", "google ads lead form", "new lead", "adwords"]},
    "sms": {"flow": "Google Ads SMS - New Lead", "source": "Google Ads - SMS", "recent": "google ads sms 24h",
            "tags": ["google ads", "google ads sms", "new lead", "adwords"]},
    "call": {"flow": "Google Ads Call - Tag", "recent": "google ads call 24h", "tags": ["google ads", "google ads call", "adwords"]},
}


def card(f: dict) -> tuple[str, str, dict]:
    return ("create_opportunity", "Card in New Lead", {
        "fields": [], "type": "create_opportunity", "pipeline_id": PIPELINE, "pipeline_stage_id": NEW_LEAD,
        "opportunity_name": "{{contact.name}}", "opportunity_source": f["source"], "monetary_value": "",
        "opportunity_status": "open"})


def alerts(customer: bool, test_to: str | None) -> list[tuple[str, str, dict]]:
    title = "🚨 NEW GOOGLE ADS LEAD - LEAD FORM 🚨" + (" (EXISTING CUSTOMER)" if customer else "")
    rows = [("Name", "{{contact.name}}"), ("Phone", "{{contact.phone}}"), ("Email", "{{contact.email}}"),
            ("ZIP", "{{contact.postal_code}}"), ("Service", "{{contact.service_requested}}"),
            ("Source", "Google Ads lead form")]
    html = P.format("New lead from the Google Ads lead form" + (" <b>(existing customer)</b>" if customer else "") + ":") + \
        "".join(P.format(f"<b>{k}:</b> {v}") for k, v in rows)
    subject = "🚨 New Google Ads lead (Lead Form): {{contact.name}}"
    if test_to:
        return [("internal_notification", "Email tester", {"type": "email", "email": {
            "userType": "custom_email", "to": test_to, "subject": "ZZ TEST " + subject, "html": html}})]
    return [("internal_notification", "Text Justin", {"type": "sms", "sms": {
                "body": title + "\n\n" + "\n".join(f"{k}: {v}" for k, v in rows), "userType": "user",
                "selectedUser": [JUSTIN], "attachments": []}}),
            ("internal_notification", "Email Justin", {"type": "email", "email": {
                "userType": "custom_email", "to": JUSTIN_EMAIL, "subject": subject, "html": html}})]


def page_field() -> tuple[str, str, dict]:
    return ("update_contact_field", "Set Landing Page", {
        "type": "update_contact_field", "actionType": "update_field_data",
        "fields": [{"field": PAGE_F, "value": "Google Ads Lead Form", "title": "Landing Page", "type": "text", "date": ""}]})


def svc(op: str, value: str) -> dict:
    c = cond(SERVICE_F, op, value)
    return c


def build(key: str, test_to: str | None = None) -> list[dict]:
    f = FLOWS[key]
    release = [wait_day(), ("remove_contact_tag", "Remove 24 h tag", {"type": "remove_contact_tag", "tags": [f["recent"]]})]
    if key == "form":
        confirm = [] if test_to else [
            ("sms", "Confirmation text", {"body": SMS_TEXT, "attachments": []}),
            ("email", "Confirmation email", {"subject": "We received your request", "html": EMAIL_HTML,
                                             "from_name": "{{custom_values.friendly_business_name}}", "from_email": "",
                                             "attachments": []})]
        service = ("ifelse", "Service requested", [
            ("Weekly service", [svc("contains", "Weekly"), svc("contains", "weekly")], [tags([WEEKLY_TAG]), *release]),
            ("Repair / hot tub", [svc("contains", x) for x in ("Repair", "repair", "Hot Tub", "hot tub", "Hot tub")],
             [tags([REPAIR_TAG]), *release]),
        ], "Not given", list(release))
        lead = [tags([*f["tags"], f["recent"]]), page_field(), card(f), *alerts(False, test_to), *confirm, service]
        customer = [tags([*f["tags"][:2], f["recent"]]), page_field(), *alerts(True, test_to), *release]
    elif key == "sms":
        lead = [tags([*f["tags"], f["recent"]]), card(f), *release]
        customer = []
    else:
        lead = [tags([*f["tags"], f["recent"]]), *release]
        customer = []
    nodes, _ = if_else("Route the lead", [
        ("Spam / DND", [cond("tags", "index-of-true", [t]) for t in SPAM], []),
        ("Sent in the last 24 h", [cond("tags", "index-of-true", [f["recent"]])], []),
        ("Current customer", [cond("tags", "index-of-true", [t]) for t in CUSTOMER], customer),
    ], "New lead", lead)
    return nodes


def trigger(key: str, wid: str, first: str, loc: dict) -> dict:
    if key == "sms":
        conds = [{"operator": "==", "field": "message.type", "value": 2, "title": "Reply channel", "type": "select"},
                 {"operator": "contains-any", "field": "inbound_number", "value": [LINE], "title": "In phone number",
                  "type": "multiselect", "id": "inbound-twilio-number"}]
        kind, name, master = "customer_reply", "Customer Replied", "highlevel"
    elif key == "call":
        conds = [{"field": "message.direction", "operator": "==", "value": "inbound", "title": "Call Direction", "type": "select"},
                 {"field": "inbound_number", "operator": "contains-any", "id": "inbound-twilio-number", "value": [LINE],
                  "title": "In Phone Number", "type": "multiselect"}]
        kind, name, master = "call_status", "Call Status", "highlevel"
    else:
        conds = [{"field": "adAccountId", "operator": "==", "value": loc["googleAdwordsId"], "id": "adAccountId",
                  "type": "select"}] if loc.get("googleAdwordsId") else []
        kind, name, master = "google_lead_form_submitted", "Google Lead Form Submitted", "internal"
    return {"type": kind, "name": name, "masterType": master, "schedule_config": {}, "conditions": conds,
            "workflowId": wid, "workflow_id": wid, "location_id": LOC,
            "actions": [{"workflow_id": wid, "type": "add_to_workflow"}], "targetActionId": first}


def first_id(tpl: list[dict]) -> str:
    return next(s["id"] for s in tpl if not s.get("parentKey") and not s.get("parent"))


def check(a: Agency, wid: str, name: str) -> bool:
    got = a.workflow(LOC, wid)
    trs = [x for x in a.triggers(LOC, wid) if not x.get("deleted")]
    ok = got["status"] == "published" and refs_ok(got["workflowData"]["templates"]) and bool(trs) and all(t.get("active") for t in trs)
    print(f"   {'✓' if ok else '✗ VERIFICAR'} {name}: {got['status']} · gatilhos {[t['type'] for t in trs]}")
    return ok


def test(a: Agency, folder: str | None, to: str) -> int:
    stamp, bad = int(time.time()), 0
    cases = {"form": [("weekly", [], "Weekly Pool/Hot Tub Service"), ("repair", [], "Hot Tub Repair"),
                      ("none", [], ""), ("customer", ["current customer"], "Weekly Pool/Hot Tub Service"),
                      ("spam", ["spam"], "")],
             "sms": [("new", [], ""), ("customer", ["current customer"], ""), ("spam", ["spam"], "")],
             "call": [("new", [], ""), ("spam", ["dnd"], "")]}
    for key, f in FLOWS.items():
        wid = lwr.create(a, f"ZZ TEST {f['flow']}", folder, build(key, to))
        set_status(a, wid, "published")
        made = {}
        for case, extra, service in cases[key]:
            body = {"locationId": LOC, "firstName": "ZZ Test", "lastName": f"{key} {case}", "tags": ["zz test", *extra],
                    "email": to.replace("@", f"+bv-{key}-{case}-{stamp}@")}
            if service:
                body["customFields"] = [{"id": SERVICE_F, "field_value": service}]
            made[case] = a.call("POST", SERVICES, "/contacts/", body=body)["contact"]["id"]
        time.sleep(3)
        for cid in made.values():
            a.call("POST", SERVICES, f"/contacts/{cid}/workflow/{wid}", body={})
        time.sleep(30)
        first = next(iter(made))
        a.call("POST", SERVICES, f"/contacts/{made[first]}/workflow/{wid}", body={})  # repeat within 24 h
        time.sleep(30)
        for case, cid in made.items():
            tg = set(a.call("GET", SERVICES, f"/contacts/{cid}")["contact"].get("tags") or [])
            opps = a.call("GET", SERVICES, "/opportunities/search", params={"location_id": LOC, "contact_id": cid}).get("opportunities", [])
            if case == "spam":
                ok = not (tg & set(f["tags"])) and not opps
            elif case == "customer":
                ok = (("google ads lead form" in tg) if key == "form" else not (tg & set(f["tags"]))) and not opps
            else:
                ok = set(f["tags"]) <= tg and f["recent"] in tg and len(opps) == (0 if key == "call" else 1)
                if key == "form":
                    want = {"weekly": WEEKLY_TAG, "repair": REPAIR_TAG}.get(case)
                    ok = ok and (want in tg if want else not ({WEEKLY_TAG, REPAIR_TAG} & tg)) and \
                        not ({WEEKLY_TAG, REPAIR_TAG} - {want} & tg)
                ok = ok and all(o.get("source") == f.get("source") and o.get("pipelineStageId") == NEW_LEAD for o in opps)
            bad += not ok
            print(f"   {'✓' if ok else '✗'} {key}/{case}: tags {sorted(tg)} · cards {[o.get('source') for o in opps]}")
            for o in opps:
                a.call("DELETE", SERVICES, f"/opportunities/{o['id']}")
            a.call("DELETE", SERVICES, f"/contacts/{cid}")
        set_status(a, wid, "draft")
        a.call("DELETE", BACKEND, f"/workflow/{LOC}/{wid}")
    print(f"   limpo. Esperado em {to}: 4 e-mails ZZ TEST do lead form (3 novos + 1 cliente), 0 do spam/repetição.")
    return 1 if bad else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("mode", choices=["plan", "test", "apply"])
    parser.add_argument("--to")
    args = parser.parse_args()
    load_dotenv()
    a = Agency()
    loc = a.location(LOC)
    if not loc["name"].lower().startswith("bonneville"):
        sys.exit("sub-conta errada")
    nums = {n["phoneNumber"]: n for n in a.call("GET", BACKEND, f"/phone-system/numbers/location/{LOC}").get("numbers", [])}
    ln = nums.get(LINE) or {}
    print(f"   Google Ads {loc.get('googleAdwordsId')} · linha {LINE} {ln.get('friendlyName')} sms={ln.get('capabilities', {}).get('sms')}")
    flows = {w["name"]: w["id"] for w in a.workflows(LOC)}
    folder = a.workflow(LOC, flows[FOLDER_OF]).get("parentId")
    if args.mode != "plan":
        for t in {t for f in FLOWS.values() for t in [*f["tags"], f["recent"]]} | {WEEKLY_TAG, REPAIR_TAG, "zz test"}:
            try:
                a.call("POST", BACKEND, f"/workflow/{LOC}/tags/create", body={"tag": t})
            except Exception:  # noqa: BLE001 — already exists
                pass
    if args.mode == "test":
        return test(a, folder, args.to)
    bad = 0
    for key, f in FLOWS.items():
        if f["flow"] in flows:
            print(f"   {f['flow']}: já existe ({flows[f['flow']]})")
            continue
        tpl = build(key)
        if args.mode == "plan":
            print(f"   {f['flow']}: cria\n{outline(tpl)}")
            continue
        wid = lwr.create(a, f["flow"], folder, tpl)
        t = a.call("POST", BACKEND, f"/workflow/{LOC}/trigger", body=trigger(key, wid, first_id(tpl), loc))
        a.call("PUT", BACKEND, f"/workflow/{LOC}/trigger/{t['id']}", body={**trigger(key, wid, first_id(tpl), loc), "id": t["id"]})
        set_status(a, wid, "published")
        bad += not check(a, wid, f["flow"])
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
