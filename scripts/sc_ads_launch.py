#!/usr/bin/env python3
"""Sparkling Clear: Google Ads launch, CRM side (Val, ClickUp 18/11).

    ./.venv/bin/python scripts/sc_ads_launch.py plan
    ./.venv/bin/python scripts/sc_ads_launch.py test --to pedro@poolprofits.com
    ./.venv/bin/python scripts/sc_ads_launch.py apply

1. Val created the offline conversion "Converted Lead - WON" (UPLOAD). It goes into the "Add to Google Ads" step of
   "Adword Call - Conversion" and "Adword Form - Conversion" (they only fire for contacts tagged adwords call / adwords
   form, gclid from {{contact.attributionSource.gclid}}), and both also listen to "Won - One Time Repair or Install"
   (the campaign covers repairs). The qualified-lead steps stay as they are: there is no qualified conversion action.
2. "AdWords SMS - New Lead": a text to the Adwords line (469) 617-2308 → tags new lead / adwords / adwords sms + card in
   New Lead (the alert to Robert comes from "Inbound SMS - Notify Owner", already on every text).
   "AdWords Lead Form - New Lead": Google Lead Form Submitted → tags new lead / adwords / adwords lead form + card +
   SMS alert to Robert + the same thank-you text as the Ads LP form. Both: spam/DND → nothing; current/existing customer →
   nothing; already in the last 24 h → nothing (every text of a conversation fires the SMS trigger).
3. Two dedicated forms for the new LPs (Weekly + Repairs): Full Name, Phone, Email, Address, ZIP, consent with the
   privacy policy link, the CTA from the brief, redirect to the Ads thank-you page. Both join the trigger of
   "AdWords Form - New Lead" (tags, card, alert, thank-you text, WON conversion) and each one has a small flow adding the
   brief's tags (google ads + weekly service / pool repairs).
GET + backup before every PUT; workflow settings are kept by Agency.call.
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
import time

from _common import ROOT, keep_redirect, load_dotenv
from pd_lwr_google_leads import set_status
from ps_ads_forms import P, cond, if_else, outline, tags, wait_day
from pp_source_tags import refs_ok

import pd_lwr_google_leads as lwr
from cli_anything.gohighlevel.utils.agency import BACKEND, SERVICES, Agency

LOC = "G9jACRTK8rh04j29ZTQf"
lwr.LOC = LOC
LINE = "+14696172308"
ROBERT = "jNSBqifkH0ga5nr1NlRr"
PIPELINE, NEW_LEAD = "9C7htZuoGLSvhAmxgDeu", "a30cc468-e0b3-41b6-892f-c3fc4efca668"
WON_WEEKLY, WON_REPAIR = "b083add9-194a-49db-aa91-4048d12e5165", "2e17a2f4"
WON_CONV = "Converted Lead - WON"
CONV_FLOWS = ("Adword Call - Conversion", "Adword Form - Conversion")
FORM_FLOW, BASE_FORM = "AdWords Form - New Lead", "nr56OGGIce0R67gr2m19"
THANKS = "https://go.sparklingclearpool.com/ty-page-2934"
PRIVACY = "https://sparklingclearpool.com/privacy-policy/"
SPAM = ["spam", "spam likely", "dnd"]
CUSTOMER = ["current customer", "existing customer"]
BDIR = ROOT / "backup" / "sparkling-clear-pool-service"
LEAD_TEXT = ("Thank you for reaching out to {{location.name}}. We received your request for more information and will be "
             "getting back to you shortly. For immediate assistance or quoting, please call this number.")
LEADS = [
    {"key": "sms", "flow": "AdWords SMS - New Lead", "source": "AdWords - PPC - SMS",
     "tags": ["new lead", "adwords", "adwords sms"], "recent": "adwords sms 24h"},
    {"key": "form", "flow": "AdWords Lead Form - New Lead", "source": "AdWords - Google Lead Form",
     "tags": ["new lead", "adwords", "adwords lead form"], "recent": "adwords lead form 24h"},
]
FORMS = [
    {"key": "weekly", "form": "FORM - GOOGLE ADS - WEEKLY SERVICE", "cta": "GET MY FREE POOL QUOTE",
     "flow": "Google Ads LP Weekly - Tags", "tags": ["google ads", "weekly service"]},
    {"key": "repairs", "form": "FORM - GOOGLE ADS - POOL REPAIRS", "cta": "GET MY FREE REPAIR QUOTE",
     "flow": "Google Ads LP Repairs - Tags", "tags": ["google ads", "pool repairs"]},
]


def backup(name: str, data) -> None:
    BDIR.mkdir(parents=True, exist_ok=True)
    (BDIR / f"{name}-{time.strftime('%Y%m%d-%H%M%S')}.json").write_text(json.dumps(data))


# ── 1. WON conversion ─────────────────────────────────────────────────────

def won_trigger_fix(a: Agency, wid: str, apply: bool) -> str:
    trs = [t for t in a.triggers(LOC, wid) if not t.get("deleted")]
    stages = [c["value"] for t in trs for c in t.get("conditions") or [] if c.get("field") == "opportunity.pipelineStageId"]
    if any(s.startswith(WON_REPAIR) for s in stages):
        return "já ouve Won - Repair"
    if not apply:
        return "+ gatilho Won - One Time Repair"
    stage = next(s["id"] for p in a.call("GET", SERVICES, "/opportunities/pipelines", params={"locationId": LOC})["pipelines"]
                 for s in p["stages"] if s["id"].startswith(WON_REPAIR))
    src = trs[0]
    backup(f"triggers-{wid}", trs)
    conds = [({**c, "value": stage} if c.get("field") == "opportunity.pipelineStageId" else c) for c in src["conditions"]]
    body = {"type": src["type"], "name": src.get("name", "Pipeline Stage Changed"), "masterType": src.get("masterType", "highlevel"),
            "schedule_config": {}, "conditions": conds, "workflowId": wid, "workflow_id": wid, "location_id": LOC,
            "actions": [{"workflow_id": wid, "type": "add_to_workflow"}], "targetActionId": src.get("targetActionId")}
    t = a.call("POST", BACKEND, f"/workflow/{LOC}/trigger", body=body)
    a.call("PUT", BACKEND, f"/workflow/{LOC}/trigger/{t['id']}", body={**body, "id": t["id"]})
    return "gatilho Won - Repair criado"


def won(a: Agency, flows: dict, cid: str, apply: bool) -> None:
    for name in CONV_FLOWS:
        wid = flows[name]
        wf = a.workflow(LOC, wid)
        tpl = copy.deepcopy(wf["workflowData"]["templates"])
        for s in tpl:
            if s["type"] == "google_adword":
                s["attributes"].update(conversion_name=WON_CONV, conversion_type=WON_CONV, conversion_action_id=cid)
        changed = tpl != wf["workflowData"]["templates"]
        if apply and changed:
            backup(f"workflow-{wid}", wf)
            a.call("PUT", BACKEND, f"/workflow/{LOC}/{wid}", body={"name": wf["name"], "version": wf.get("version", 1),
                   "status": wf["status"], "workflowData": {"templates": tpl}})
        msg = won_trigger_fix(a, wid, apply)
        time.sleep(3 if apply else 0)
        got = a.workflow(LOC, wid)
        st = [(s["attributes"].get("conversion_name"), s["attributes"].get("conversion_action_id"))
              for s in got["workflowData"]["templates"] if s["type"] == "google_adword"]
        print(f"   {name} ({got['status']}): {st} · {msg}{' · (mudaria o passo)' if changed and not apply else ''}")


# ── 2. SMS + Google lead form ─────────────────────────────────────────────

def alert(test_to: str | None, customer_note: str = "") -> tuple[str, str, dict]:
    title = "🚨 NEW LEAD FROM GOOGLE ADS LEAD FORM 🚨" + customer_note
    body = "\n\nName: {{contact.name}}\n\nPhone: {{contact.phone}}\n\nEmail: {{contact.email}}\n\nZip Code: {{contact.postal_code}}"
    if test_to:
        return ("internal_notification", "Email tester", {"type": "email", "email": {
            "userType": "custom_email", "to": test_to, "subject": "ZZ TEST " + title,
            "html": P.format((title + body).replace("\n", "<br>"))}})
    return ("internal_notification", "SMS Notification", {"type": "sms", "sms": {
        "body": title + body, "selectedUser": [ROBERT], "userType": "user", "attachments": []}})


def build(f: dict, test_to: str | None = None) -> list[dict]:
    release = [wait_day(), ("remove_contact_tag", "Remove 24 h tag", {"type": "remove_contact_tag", "tags": [f["recent"]]})]
    card = ("create_opportunity", "Create Or Update Opportunity", {
        "fields": [], "type": "create_opportunity", "pipeline_id": PIPELINE, "pipeline_stage_id": NEW_LEAD,
        "opportunity_name": "{{contact.name}}", "opportunity_source": f["source"], "monetary_value": "180.00",
        "opportunity_status": "open"})
    extra = [alert(test_to)] if f["key"] == "form" else []
    if f["key"] == "form" and not test_to:
        extra.append(("sms", "Thank-you text", {"body": LEAD_TEXT, "attachments": []}))
    lead = [tags([*f["tags"], f["recent"]]), card, *extra, *release]
    nodes, _ = if_else("Route the lead", [
        ("Spam / DND", [cond("tags", "index-of-true", [t]) for t in SPAM], []),
        ("Sent in the last 24 h", [cond("tags", "index-of-true", [f["recent"]])], []),
        ("Current customer", [cond("tags", "index-of-true", [t]) for t in CUSTOMER], []),
    ], "New lead", lead)
    return nodes


def trigger(f: dict, wid: str, first: str, loc: dict) -> dict:
    if f["key"] == "sms":
        conds = [{"operator": "==", "field": "message.type", "value": 2, "title": "Reply channel", "type": "select"},
                 {"operator": "contains-any", "field": "inbound_number", "value": [LINE], "title": "In phone number",
                  "type": "multiselect", "id": "inbound-twilio-number"}]
        kind, name, master = "customer_reply", "Customer Replied", "highlevel"
    else:
        conds = [{"field": "adAccountId", "operator": "==", "value": loc["googleAdwordsId"], "id": "adAccountId",
                  "type": "select"}] if loc.get("googleAdwordsId") else []
        kind, name, master = "google_lead_form_submitted", "Google Lead Form Submitted", "internal"
    return {"type": kind, "name": name, "masterType": master, "schedule_config": {}, "conditions": conds,
            "workflowId": wid, "workflow_id": wid, "location_id": LOC,
            "actions": [{"workflow_id": wid, "type": "add_to_workflow"}], "targetActionId": first}


def add_trigger(a: Agency, wid: str, body: dict) -> None:
    t = a.call("POST", BACKEND, f"/workflow/{LOC}/trigger", body=body)
    a.call("PUT", BACKEND, f"/workflow/{LOC}/trigger/{t['id']}", body={**body, "id": t["id"]})


def first_id(tpl: list[dict]) -> str:
    return next(s["id"] for s in tpl if not s.get("parentKey") and not s.get("parent"))


def check(a: Agency, wid: str, name: str) -> None:
    got = a.workflow(LOC, wid)
    trs = [x for x in a.triggers(LOC, wid) if not x.get("deleted")]
    ok = got["status"] == "published" and refs_ok(got["workflowData"]["templates"]) and trs and all(t.get("active") for t in trs)
    print(f"   {'✓' if ok else '✗ VERIFICAR'} {name}: {got['status']} · gatilhos {[t['type'] for t in trs]}")


def leads(a: Agency, flows: dict, folder: str | None, loc: dict, apply: bool) -> None:
    for f in LEADS:
        if f["flow"] in flows:
            print(f"   {f['flow']}: já existe")
            continue
        if not apply:
            print(f"   {f['flow']}: cria\n{outline(build(f))}")
            continue
        tpl = build(f)
        wid = lwr.create(a, f["flow"], folder, tpl)
        add_trigger(a, wid, trigger(f, wid, first_id(tpl), loc))
        set_status(a, wid, "published")
        check(a, wid, f["flow"])


# ── 3. LP forms ───────────────────────────────────────────────────────────

def std(tag: str, label: str, required: bool = True) -> dict:
    return {"fieldWidthPercentage": 100, "hiddenFieldQueryKey": tag, "label": label, "placeholder": label,
            "required": required, "standard": True, "tag": tag, "title": label, "type": "text", "typeLabel": "Text"}


def build_form(base: dict, p: dict) -> dict:
    fd = copy.deepcopy(base)
    f = fd["form"]
    by = {x["tag"]: x for x in f["fields"]}
    name, phone, email, zip_, consent, button = (copy.deepcopy(by[k]) for k in (
        "full_name", "phone", "email", "postal_code", "terms_and_conditions", "button"))
    street = {**std("address", "Address"), "category": "address"}
    phone.update(required=True, placeholder="Phone Number", enableCountryPicker=True)
    zip_.update(required=True, label="ZIP Code", placeholder="ZIP Code", title="ZIP Code")
    consent.update(required=True)
    consent.pop("placeholder2", None)
    link = (f'<span style="font-size: 10px"> See our <a href="{PRIVACY}" target="_blank" rel="noopener">Privacy Policy</a>.'
            '</span></p>')
    if PRIVACY not in consent["placeholder"]:
        consent["placeholder"] = consent["placeholder"].rsplit("</p>", 1)[0] + link
    button["label"] = f"<p>{p['cta']}</p>"
    f["fields"] = [name, phone, email, street, zip_, consent, button]
    f["formAction"] = {**(f.get("formAction") or {}), "actionType": "1", "redirectUrl": THANKS, "redirect_url": THANKS}
    return keep_redirect(fd)


def latest_form(a: Agency, fid: str) -> dict:
    f = a.call("GET", BACKEND, f"/forms/{fid}")["form"]
    hist = sorted(f.get("versionHistory") or [], key=lambda h: h.get("updatedAt", ""))
    if hist and hist[-1].get("formDataDownloadUrl"):
        import requests
        f["formData"] = requests.get(hist[-1]["formDataDownloadUrl"], timeout=30).json()
    return f


def save_form(a: Agency, fid: str, name: str, fd: dict) -> None:
    for i in range(8):
        try:
            a.call("POST", BACKEND, f"/forms/{fid}", body={"name": name, "formData": fd})
            return
        except Exception:  # noqa: BLE001 — new form answers 404 for a few minutes
            if i == 7:
                raise
            time.sleep(30)


def forms(a: Agency, flows: dict, folder: str | None, apply: bool) -> dict:
    existing = {f["name"]: f["_id"] for f in a.call("GET", BACKEND, "/forms/", params={"locationId": LOC, "limit": 100}).get("forms", [])}
    base = latest_form(a, BASE_FORM)["formData"]
    ids = {}
    for p in FORMS:
        fd = build_form(base, p)
        fid = existing.get(p["form"])
        if not apply:
            print(f"   {p['form']}: {'existe' if fid else 'cria'} · campos {[x['tag'] for x in fd['form']['fields']]}")
            ids[p["key"]] = fid
            continue
        if not fid:
            fid = a.call("POST", BACKEND, "/forms/", body={"name": p["form"], "locationId": LOC, "formData": fd})["form"]["_id"]
            time.sleep(5)
        save_form(a, fid, p["form"], fd)  # create drops redirect_url
        ids[p["key"]] = fid
        got = a.call("GET", BACKEND, f"/forms/{fid}")["form"]
        act = got["formData"]["form"].get("formAction") or {}
        print(f"   ✓ {p['form']} {fid} · redirect {act.get('redirectUrl')}")
        if p["flow"] not in flows:
            tpl = lwr_chain([tags(p["tags"])])
            wid = lwr.create(a, p["flow"], folder, tpl)
            add_trigger(a, wid, {"type": "form_submission", "name": "Form Submitted", "masterType": "highlevel",
                                 "schedule_config": {}, "conditions": [{"operator": "is-any-of", "field": "form.id",
                                 "value": [fid], "title": "Form is", "type": "string"}], "workflowId": wid, "workflow_id": wid,
                                 "location_id": LOC, "actions": [{"workflow_id": wid, "type": "add_to_workflow"}],
                                 "targetActionId": tpl[0]["id"]})
            set_status(a, wid, "published")
            check(a, wid, p["flow"])
    # the main Ads form flow listens to the new forms too
    wid = flows[FORM_FLOW]
    trs = [t for t in a.triggers(LOC, wid) if not t.get("deleted") and t.get("type") == "form_submission"]
    t = trs[0]
    c = next(c for c in t["conditions"] if c.get("field") == "form.id")
    want = [*c["value"], *[i for i in ids.values() if i and i not in c["value"]]]
    print(f"   {FORM_FLOW}: forms {c['value']} → {want}")
    if apply and want != c["value"]:
        backup(f"triggers-{wid}", trs)
        c["value"] = want
        body = {k: t[k] for k in ("type", "name", "masterType", "conditions", "targetActionId") if k in t}
        a.call("PUT", BACKEND, f"/workflow/{LOC}/trigger/{t['id']}", body={**body, "schedule_config": {}, "id": t["id"],
               "workflowId": wid, "workflow_id": wid, "location_id": LOC,
               "actions": [{"workflow_id": wid, "type": "add_to_workflow"}]})
        time.sleep(3)
        got = next(x for x in a.triggers(LOC, wid) if x["id"] == t["id"])
        print(f"   {'✓' if next(c for c in got['conditions'] if c.get('field') == 'form.id')['value'] == want else '✗'} gatilho atualizado")
    return ids


def lwr_chain(items: list) -> list[dict]:
    from ps_ads_forms import chain
    return chain(items)


# ── test ──────────────────────────────────────────────────────────────────

def test(a: Agency, folder: str | None, to: str) -> int:
    stamp, bad = int(time.time()), 0
    for f in LEADS:
        tpl = build(f, to)
        wid = lwr.create(a, f"ZZ TEST {f['flow']}", folder, tpl)
        set_status(a, wid, "published")
        made = {}
        for case, extra in (("new", ["zz test"]), ("customer", ["zz test", "current customer"]), ("spam", ["zz test", "spam"])):
            made[case] = a.call("POST", SERVICES, "/contacts/", body={
                "locationId": LOC, "firstName": "ZZ Test", "lastName": f"{f['key']} {case}", "tags": extra,
                "email": to.replace("@", f"+sc-{f['key']}-{case}-{stamp}@")})["contact"]["id"]
        time.sleep(3)
        for cid in made.values():
            a.call("POST", SERVICES, f"/contacts/{cid}/workflow/{wid}", body={})
        time.sleep(30)
        a.call("POST", SERVICES, f"/contacts/{made['new']}/workflow/{wid}", body={})  # second text / submit
        time.sleep(30)
        want = {"new": (set(f["tags"]) | {f["recent"]}, 1), "customer": (set(), 0), "spam": (set(), 0)}
        for case, cid in made.items():
            tg = set(a.call("GET", SERVICES, f"/contacts/{cid}")["contact"].get("tags") or [])
            opps = a.call("GET", SERVICES, "/opportunities/search", params={"location_id": LOC, "contact_id": cid}).get("opportunities", [])
            exp, cards = want[case]
            ok = exp <= tg and len(opps) == cards and (case == "new" or "adwords" not in tg) and \
                all(o.get("source") == f["source"] and o.get("pipelineStageId") == NEW_LEAD for o in opps)
            bad += not ok
            print(f"   {'✓' if ok else '✗'} {f['key']}/{case}: tags {sorted(tg)} · cards {[o.get('source') for o in opps]}")
            for o in opps:
                a.call("DELETE", SERVICES, f"/opportunities/{o['id']}")
            a.call("DELETE", SERVICES, f"/contacts/{cid}")
        set_status(a, wid, "draft")
        a.call("DELETE", BACKEND, f"/workflow/{LOC}/{wid}")
    print(f"   limpo. Esperado em {to}: 1 e-mail ZZ TEST do lead form (não 2), 0 do cliente/spam.")
    return 1 if bad else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("mode", choices=["plan", "test", "apply"])
    parser.add_argument("--to")
    args = parser.parse_args()
    load_dotenv()
    a = Agency()
    loc = a.location(LOC)
    if not loc["name"].lower().startswith("sparkling clear"):
        sys.exit("sub-conta errada")
    conv = {r["conversion_name"]: r["conversion_action_id"]
            for r in a.call("GET", SERVICES, "/ad-publishing/google/conversions", params={"locationId": LOC})}
    print(f"   Google Ads {loc.get('googleAdwordsId')} · conversões {conv}")
    flows = {w["name"]: w["id"] for w in a.workflows(LOC)}
    folder = a.workflow(LOC, flows[FORM_FLOW]).get("parentId")
    for t in {"adwords sms", "adwords lead form", "google ads", "weekly service", "pool repairs",
              *(f["recent"] for f in LEADS)}:
        if args.mode != "plan":
            try:
                a.call("POST", BACKEND, f"/workflow/{LOC}/tags/create", body={"tag": t})
            except Exception:  # noqa: BLE001 — already exists
                pass
    if args.mode == "test":
        return test(a, folder, args.to)
    apply = args.mode == "apply"
    if WON_CONV not in conv:
        sys.exit(f"conversão {WON_CONV} não aparece no CRM")
    won(a, flows, conv[WON_CONV], apply)
    leads(a, flows, folder, loc, apply)
    forms(a, flows, folder, apply)
    return 0


if __name__ == "__main__":
    sys.exit(main())
