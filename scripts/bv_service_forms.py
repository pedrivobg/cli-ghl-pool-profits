#!/usr/bin/env python3
"""BluVantage: 3 Google Ads landing pages (Val/Atif, 22/10). One form per service, its tag and its lead workflow.

    ./.venv/bin/python scripts/bv_service_forms.py plan
    ./.venv/bin/python scripts/bv_service_forms.py apply
    ./.venv/bin/python scripts/bv_service_forms.py test --to pedro@poolprofits.com

Forms: Full Name, Phone (US country picker), Email, Property ZIP Code (required), optional message (custom field
"Additional Details"), the SMS consent of the current "FORM - GOOGLE ADS" (names the business) and the page's CTA on
the button. Built from the NEWEST version of that form (versionHistory is newest first), without its address/city
fields; after submit, the same thank-you page as the current landing (redirectUrl + redirect_url). Atif styles them
with CSS on the pages. `apply --refresh-forms` rebuilds the existing forms (same ids/links).
Workflows: a copy of "AdWords Form - New Lead" for each form, with the same spam/customer guard, Google Ads
conversion, text to the 5 team users, emails to Vanessa and Paul, card in New Lead and reply text. Each has its own
form trigger, the service tag (Val's names; GHL stores tags in lower case), Service Requested = <service> on the
contact (new TEXT field), card source "Google Ads LP - <service>" and the service in the alerts.
test: the same chains as temporary copies with alerts diverted to --to (no team texts, no reply, no conversion).
A test contact is put in through the API; its tags, field and card are checked, then everything is deleted.
A real submission (Turnstile blocks scripts) is the last check, by hand, once the pages are up.
"""
from __future__ import annotations

import argparse
import copy
import json
import re
import sys
import time
import uuid

from _common import ROOT, load_dotenv
from pp_source_tags import drop_step, fresh_ids, refs_ok

from cli_anything.gohighlevel.utils.agency import BACKEND, SERVICES, Agency

LOC = "KLFYmoVapqQgX3T0AnLn"
BASE_FORM = "NbXKwS0EWcYzxW7LtCKE"  # FORM - GOOGLE ADS (go.bluvantagepools.com)
BASE_FLOW = "AdWords Form - New Lead"
MESSAGE_FIELD = "Additional Details"
SERVICE_FIELD = "Service Requested"
BASE_TAGS = ["new lead", "adwords", "adwords form fill"]
SERVICES_LP = [
    {"service": "Pool Heater & Equipment Repair", "form": "BluVantage — Pool Heater & Equipment Repair",
     "tag": "google ads form - heater & equipment repair", "cta": "Schedule Pool Equipment Repair",
     "flow": "AdWords Form - Heater & Equipment Repair"},
    {"service": "Winter Pool Maintenance", "form": "BluVantage — Winter Pool Maintenance",
     "tag": "google ads form - winter maintenance", "cta": "Request Pool Maintenance",
     "flow": "AdWords Form - Winter Maintenance"},
    {"service": "Pool Closing & Winterization", "form": "BluVantage — Pool Closing & Winterization",
     "tag": "google ads form - closing & winterization", "cta": "Schedule Pool Closing",
     "flow": "AdWords Form - Closing & Winterization"},
]
THANKS = "Thank you! We received your request and will contact you shortly."
BDIR = ROOT / "backup" / "bluvantage-pool-service"


def latest_form_data(a: Agency, fid: str) -> tuple[dict, dict]:
    """The GET's formData lags minutes behind; the newest version file is the real content."""
    f = a.call("GET", BACKEND, f"/forms/{fid}")
    f = f.get("form", f)
    versions = [v for v in f.get("versionHistory") or [] if v.get("formDataDownloadUrl")]
    url = max(versions, key=lambda v: v.get("updatedAt") or "")["formDataDownloadUrl"] if versions else None  # newest
    return f, (a.session.get(url, timeout=30).json() if url else f["formData"])


def message_field(cf: dict) -> dict:
    return {"label": "Message (optional)", "tag": cf["id"], "id": cf["id"], "hiddenFieldQueryKey": cf["fieldKey"].split(".")[-1],
            "type": "large_text", "dataType": "LARGE_TEXT", "typeLabel": "Multi Line",
            "placeholder": "Tell us about your pool or what you need", "required": False, "standard": False,
            "custom": True, "category": "text", "model": "contact", "name": cf["name"], "fieldKey": cf["fieldKey"],
            "parentId": cf.get("parentId"), "locationId": LOC,
            "preview": "<span style=\"color: #000000;\">Tell us about your pool or what you need</span>"}


def build_form(base: dict, s: dict, msg_cf: dict) -> dict:
    fd = copy.deepcopy(base)
    f = fd["form"]
    by = {x["tag"]: x for x in f["fields"]}
    name, phone, email, zip_, consent, button = (copy.deepcopy(by[k]) for k in (
        "full_name", "phone", "email", "postal_code", "terms_and_conditions", "button"))
    phone.update(placeholder="Phone", enableCountryPicker=True)
    zip_.update(label="Property ZIP Code", placeholder="ZIP Code", required=True, title="Property ZIP Code")
    button["label"] = re.sub(r">[^<]*<", f">{s['cta']}<", button["label"], count=1) if "<" in button["label"] \
        else f"<p>{s['cta']}</p>"
    f["fields"] = [name, phone, email, zip_, message_field(msg_cf), consent, button]
    action = dict(f.get("formAction") or {})
    if action.get("actionType") == "1" and (action.get("redirectUrl") or action.get("redirect_url")):
        url = action.get("redirect_url") or action.get("redirectUrl")  # same thank-you page as the current landing
        action.update(redirectUrl=url, redirect_url=url)  # the widget reads redirect_url
    else:
        action.update(actionType="2", thankyouText=THANKS)
    f["formAction"] = action
    return fd


def insert_after(tpl: list[dict], after_id: str, step: dict) -> list[dict]:
    """Put `step` right after `after_id` in its chain (same branch); later steps move down one."""
    by = {s["id"]: s for s in tpl}
    prev = by[after_id]
    nxt = prev.get("next")
    step = {**step, "id": str(uuid.uuid4()), "order": prev.get("order", 0) + 1, "parentKey": after_id}
    if prev.get("parent"):
        step["parent"] = prev["parent"]
    cur = by.get(nxt) if isinstance(nxt, str) else None
    if cur:
        step["next"] = nxt
        cur["parentKey"] = step["id"]
    prev["next"] = step["id"]
    while cur:
        cur["order"] = cur.get("order", 0) + 1
        cur = by.get(cur.get("next")) if isinstance(cur.get("next"), str) else None
    return [*tpl, step]


def build_flow(src: list[dict], s: dict, service_cf: str) -> list[dict]:
    tpl = fresh_ids(src)
    for st in tpl:
        a = st.get("attributes") or {}
        if st["type"] == "add_contact_tag":
            a["tags"] = [*BASE_TAGS, s["tag"]]
            st["name"] = "Add Tag"
        elif st["type"] == "create_opportunity":
            a["opportunity_source"] = f"Google Ads LP - {s['service']}"
        elif st["type"] == "internal_notification" and a.get("type") == "sms":
            body = a["sms"]["body"]
            head = body.split("\n", 1)[0]
            a["sms"]["body"] = body.replace(head, f"{head}\n\nService: {s['service']}", 1)
        elif st["type"] == "internal_notification" and a.get("type") == "email":
            e = a["email"]
            e["subject"] = f"🚨 New Google Ads lead ({s['service']}): {{{{contact.name}}}}"
            e["html"] = e["html"].replace("Form: Google Ads landing page (go.bluvantagepools.com)",
                                          f"Service: {s['service']}</p><p style=\"margin:0px;font-family:verdana,"
                                          f"geneva,sans-serif;font-size:16px;\">Form: {s['form']} (Google Ads landing page)")
    tag = next(st for st in tpl if st["type"] == "add_contact_tag")
    field = {"name": f"Set {SERVICE_FIELD}", "type": "update_contact_field", "attributes": {
        "type": "update_contact_field", "actionType": "update_field_data",
        "fields": [{"field": service_cf, "value": s["service"], "title": SERVICE_FIELD, "type": "text", "date": ""}]}}
    return insert_after(tpl, tag["id"], field)


def diverted(tpl: list[dict], to: str) -> list[dict]:
    """Test copy: emails to `to` (one), no team text, no reply text, no Google Ads conversion."""
    out = json.loads(json.dumps(tpl))
    emails = [st for st in out if st["type"] == "internal_notification" and st["attributes"].get("type") == "email"]
    for st in emails:
        st["attributes"]["email"]["to"] = to
        st["attributes"]["email"]["subject"] = "[TEST] " + st["attributes"]["email"]["subject"]
    gone = [st["id"] for st in out if st["type"] in ("google_adword", "sms")
            or (st["type"] == "internal_notification" and st["attributes"].get("type") == "sms")] + [e["id"] for e in emails[1:]]
    for sid in gone:
        out = drop_step(out, sid)
    return out


def trigger_body(wid: str, form_id: str, first: str) -> dict:
    return {"type": "form_submission", "name": "Form Submitted", "masterType": "highlevel", "schedule_config": {},
            "conditions": [{"operator": "is-any-of", "field": "form.id", "value": [form_id], "title": "Form is",
                            "type": "string"}],
            "workflowId": wid, "workflow_id": wid, "location_id": LOC,
            "actions": [{"workflow_id": wid, "type": "add_to_workflow"}], "targetActionId": first}


def first_id(tpl: list[dict]) -> str:
    return next(st["id"] for st in tpl if not st.get("parentKey") and not st.get("parent"))


def put_flow(a: Agency, name: str, parent: str | None, allow: bool, tpl: list[dict], status: str) -> str:
    res = a.call("POST", BACKEND, f"/workflow/{LOC}", body={"name": name, "parentId": parent, "status": "draft"})
    wid = res.get("id") or res.get("_id")
    body = {"name": name, "version": 1, "status": "draft", "parentId": parent, "allowMultiple": allow,
            "workflowData": {"templates": tpl}}
    a.call("PUT", BACKEND, f"/workflow/{LOC}/{wid}", body=body)
    if status == "published":
        a.call("PUT", BACKEND, f"/workflow/{LOC}/{wid}", body={**body, "status": "published",
                                                               "version": a.workflow(LOC, wid).get("version", 1)})
    return wid


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("mode", choices=["plan", "apply", "test"])
    parser.add_argument("--to", help="test: inbox that gets the lead e-mails")
    parser.add_argument("--refresh-forms", action="store_true", help="apply: rebuild existing forms from the base form")
    args = parser.parse_args()
    if args.mode == "test" and not args.to:
        parser.error("--to is required in test mode")
    load_dotenv()
    a = Agency()
    if a.location(LOC)["name"] != "BluVantage Pool Service":
        sys.exit("sub-conta errada")
    BDIR.mkdir(parents=True, exist_ok=True)
    cfs = {c["name"]: c for c in a.call("GET", SERVICES, f"/locations/{LOC}/customFields")["customFields"]}
    forms = {f["name"]: f.get("_id") or f.get("id") for f in a.forms(LOC)}
    flows = {w["name"]: w["id"] for w in a.workflows(LOC)}
    src = a.workflow(LOC, flows[BASE_FLOW])
    _, base = latest_form_data(a, BASE_FORM)

    if args.mode == "plan":
        print(f"campo {SERVICE_FIELD}: {'existe' if SERVICE_FIELD in cfs else 'cria (TEXT)'}")
        for s in SERVICES_LP:
            fd = build_form(base, s, cfs[MESSAGE_FIELD])
            tpl = build_flow(src["workflowData"]["templates"], s, cfs.get(SERVICE_FIELD, {}).get("id", "<novo>"))
            print(f"\n== {s['form']}: {'existe' if s['form'] in forms else 'cria'}")
            print("   campos:", " · ".join(f"{x['label']}{'*' if x.get('required') else ''}" for x in fd["form"]["fields"]))
            print(f"   {s['flow']}: {'existe' if s['flow'] in flows else 'cria'} · tags {[*BASE_TAGS, s['tag']]}")
            print("   passos:", " → ".join(st["name"] for st in sorted(tpl, key=lambda x: (bool(x.get('parent')), x.get('order', 0)))
                                          if not str(st.get("nodeType", "")).startswith("branch")))
        return 0

    if SERVICE_FIELD not in cfs:
        res = a.call("POST", SERVICES, f"/locations/{LOC}/customFields",
                     body={"name": SERVICE_FIELD, "dataType": "TEXT", "placeholder": "", "position": 0, "model": "contact"})
        cfs[SERVICE_FIELD] = res.get("customField") or res
        print(f"   ✓ campo {SERVICE_FIELD} ({cfs[SERVICE_FIELD].get('fieldKey')})")
    for t in {*BASE_TAGS, *(s["tag"] for s in SERVICES_LP)}:
        try:
            a.call("POST", BACKEND, f"/workflow/{LOC}/tags/create", body={"tag": t})
        except Exception:  # noqa: BLE001 — already exists
            pass

    if args.mode == "apply":
        for s in SERVICES_LP:
            if s["form"] in forms and args.refresh_forms:
                fid = forms[s["form"]]
                cur, cur_fd = latest_form_data(a, fid)
                (BDIR / f"form-{fid}-{time.strftime('%Y%m%d-%H%M%S')}.json").write_text(json.dumps({"form": cur, "formData": cur_fd}))
                a.call("POST", BACKEND, f"/forms/{fid}", body={"name": s["form"], "formData": build_form(base, s, cfs[MESSAGE_FIELD])})
                print(f"   ✓ form {s['form']}: refeito a partir da versão atual do {BASE_FORM}")
            if s["form"] not in forms:
                res = a.call("POST", BACKEND, "/forms/", body={"name": s["form"], "locationId": LOC,
                                                               "formData": build_form(base, s, cfs[MESSAGE_FIELD])})
                forms[s["form"]] = (res.get("form") or res).get("_id") or (res.get("form") or res).get("id")
                print(f"   ✓ form {s['form']}: {forms[s['form']]}")
            if s["flow"] in flows:
                print(f"   {s['flow']}: já existe")
                continue
            tpl = build_flow(src["workflowData"]["templates"], s, cfs[SERVICE_FIELD]["id"])
            wid = put_flow(a, s["flow"], src.get("parentId"), src.get("allowMultiple", True), tpl, "draft")
            trig = trigger_body(wid, forms[s["form"]], first_id(tpl))
            t = a.call("POST", BACKEND, f"/workflow/{LOC}/trigger", body=trig)
            a.call("PUT", BACKEND, f"/workflow/{LOC}/trigger/{t['id']}", body={**trig, "id": t["id"]})
            live = a.workflow(LOC, wid)
            a.call("PUT", BACKEND, f"/workflow/{LOC}/{wid}", body={
                "name": s["flow"], "version": live.get("version", 1), "status": "published", "parentId": src.get("parentId"),
                "allowMultiple": src.get("allowMultiple", True), "workflowData": {"templates": live["workflowData"]["templates"]}})
            time.sleep(4)
            got = a.workflow(LOC, wid)
            trs = [x for x in a.triggers(LOC, wid) if not x.get("deleted")]
            ok = got["status"] == "published" and len(got["workflowData"]["templates"]) == len(tpl) and \
                refs_ok(got["workflowData"]["templates"]) and len(trs) == 1 and trs[0].get("active") and \
                trs[0]["conditions"][0]["value"] == [forms[s["form"]]]
            print(f"   {'✓' if ok else '✗ VERIFICAR'} {s['flow']}: {got['status']} · {len(tpl)} passos · form {forms[s['form']]}")
        print("\n   links:", {s["form"]: f"https://link.poolprofits.com/widget/form/{forms[s['form']]}" for s in SERVICES_LP})
        return 0

    # test: temporary diverted copies, one test contact each, then clean up
    stamp = int(time.time())
    bad = 0
    for s in SERVICES_LP:
        tpl = diverted(build_flow(src["workflowData"]["templates"], s, cfs[SERVICE_FIELD]["id"]), args.to)
        wid = put_flow(a, f"ZZ TEST {s['flow']}", src.get("parentId"), True, tpl, "published")
        contact = a.call("POST", SERVICES, "/contacts/", body={
            "locationId": LOC, "firstName": "ZZ Test", "lastName": s["service"],
            "email": f"zz-e2e-bv-{stamp}-{SERVICES_LP.index(s)}@example.com"})["contact"]
        time.sleep(3)
        a.call("POST", SERVICES, f"/contacts/{contact['id']}/workflow/{wid}", body={})
        got, opps = {}, []
        for _ in range(12):
            time.sleep(10)
            got = a.call("GET", SERVICES, f"/contacts/{contact['id']}")["contact"]
            opps = a.call("GET", SERVICES, "/opportunities/search", params={"location_id": LOC, "contact_id": contact["id"]}).get("opportunities", [])
            if s["tag"] in got.get("tags", []) and opps:
                break
        field = next((f.get("value") for f in got.get("customFields", []) if f.get("id") == cfs[SERVICE_FIELD]["id"]), None)
        ok = set([*BASE_TAGS, s["tag"]]) <= set(got.get("tags", [])) and field == s["service"] and \
            any(o.get("source") == f"Google Ads LP - {s['service']}" for o in opps)
        bad += not ok
        print(f"   {'✓' if ok else '✗'} {s['flow']}: tags {got.get('tags')} · {SERVICE_FIELD}={field!r} · "
              f"cards {[(o.get('pipelineStageId', '')[:8], o.get('source')) for o in opps]}")
        for o in opps:
            a.call("DELETE", SERVICES, f"/opportunities/{o['id']}")
        a.call("DELETE", SERVICES, f"/contacts/{contact['id']}")
        live = a.workflow(LOC, wid)
        a.call("PUT", BACKEND, f"/workflow/{LOC}/{wid}", body={"name": live["name"], "version": live.get("version", 1),
               "status": "draft", "workflowData": {"templates": live["workflowData"]["templates"]}})
        a.call("DELETE", BACKEND, f"/workflow/{LOC}/{wid}")
    print(f"   limpo; e-mails de teste em {args.to}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
