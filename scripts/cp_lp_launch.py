#!/usr/bin/env python3
"""Clear Pool Solutions Tucson: the 2 new Google Ads landing pages (Val, ClickUp 86bc6vvha, 20/11) → CRM side.

    python3 scripts/cp_lp_launch.py plan
    python3 scripts/cp_lp_launch.py test       # ZZ TEST copy of a tag flow + ZZ TEST contacts, all deleted
    python3 scripts/cp_lp_launch.py apply
    python3 scripts/cp_lp_launch.py apply --thanks-weekly URL --thanks-repairs URL   # Atif's dedicated thank-you pages

1. Two forms copied from the live "FORM - GOOGLE ADS" (kX2E…): Full Name, Phone (country picker), Email, Property Address,
   ZIP Code (+ "Service Needed" dropdown on Repairs: Pump Repair / Pump Installation / Heater Repair / Heater Installation /
   Other, new contact field), transactional SMS consent with the privacy policy link, the brief's CTA, redirect to the
   thank-you page (the Ads one until Atif sends the dedicated ones).
2. Both join the trigger of "AdWords Form - New Lead" (assign Derek, spam/customer check, tags new lead / new form fill /
   adwords, card in New Lead with source "AdWords - PPC - Form Fill", SMS + e-mail alert to Derek, thank-you text) — the
   same path as the Ads form already live, so Won attribution ("adwords" tag + gclid) works as today.
3. One small flow per form ("Google Ads LP <service> - Tags") with the brief's tags (google ads + weekly pool service /
   pool equipment repairs). Calls stay on the Google Ads line 520-777-1392 ("AdWords Call In - New Lead").
Nothing touches existing contacts (only new submissions of these 2 forms). GET + backup before every PUT.
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
import time

from _common import ROOT, keep_redirect, load_dotenv
import ps_ads_forms as ps
from ps_ads_forms import tags
from sc_ads_launch import latest_form, save_form, std

from cli_anything.gohighlevel.utils.agency import BACKEND, SERVICES, Agency

LOC = "ghUi89uCpNyNunNpbtAt"
ps.LOC = LOC
MAIN, BASE_FORM = "AdWords Form - New Lead", "kX2EMO7WMmD34wjFgahg"
THANKS = "https://go.clearpooltucson.com/ty-page-2934"
PRIVACY = "https://clearpooltucson.com/privacy-policy/"
SERVICE_FIELD = "Service Needed"
SERVICES_OPTS = ["Pump Repair", "Pump Installation", "Heater Repair", "Heater Installation", "Other"]
FORMS = [
    {"key": "weekly", "form": "FORM - GOOGLE ADS - WEEKLY POOL SERVICE", "cta": "GET MY FREE POOL SERVICE QUOTE",
     "flow": "Google Ads LP Weekly - Tags", "tags": ["google ads", "weekly pool service"]},
    {"key": "repairs", "form": "FORM - GOOGLE ADS - PUMP & HEATER REPAIRS", "cta": "REQUEST MY FREE ESTIMATE",
     "flow": "Google Ads LP Repairs - Tags", "tags": ["google ads", "pool equipment repairs"]},
]
BDIR = ROOT / "backup" / "clear-pool-solutions-tucson"


def backup(name: str, data) -> None:
    BDIR.mkdir(parents=True, exist_ok=True)
    (BDIR / f"{name}-{int(time.time())}.json").write_text(json.dumps(data, indent=1))


def ensure_field(a: Agency, apply: bool) -> dict | None:
    cfs = {c["name"]: c for c in a.custom_fields(LOC)}
    if SERVICE_FIELD not in cfs:
        print(f"   campo novo: {SERVICE_FIELD} {SERVICES_OPTS}")
        if not apply:
            return None
        res = a.call("POST", SERVICES, f"/locations/{LOC}/customFields",
                     body={"name": SERVICE_FIELD, "placeholder": "", "position": 0, "model": "contact",
                           "dataType": "SINGLE_OPTIONS", "options": SERVICES_OPTS})
        cfs[SERVICE_FIELD] = res.get("customField") or res
        print(f"   ✓ campo {SERVICE_FIELD} ({cfs[SERVICE_FIELD].get('fieldKey')})")
    return cfs[SERVICE_FIELD]


def build_form(base: dict, p: dict, cf: dict | None, thanks: str) -> dict:
    fd = copy.deepcopy(base)
    f = fd["form"]
    by = {x["tag"]: x for x in f["fields"]}
    name, phone, email, zip_, consent, button = (copy.deepcopy(by[k]) for k in (
        "full_name", "phone", "email", "postal_code", "terms_and_conditions", "button"))
    street = {**std("address", "Property Address"), "category": "address"}
    phone.update(required=True, label="Phone Number", placeholder="Phone Number", enableCountryPicker=True)
    email.update(required=True, label="Email Address", placeholder="Email Address")
    zip_.update(required=True, label="ZIP Code", placeholder="ZIP Code", title="ZIP Code")
    consent.update(required=True)
    consent.pop("placeholder2", None)
    if PRIVACY not in consent["placeholder"]:
        consent["placeholder"] = consent["placeholder"].rsplit("</p>", 1)[0] + (
            f'<span style="font-size: 10px"> See our <a href="{PRIVACY}" target="_blank" rel="noopener">Privacy Policy</a>.'
            '</span></p>')
    button["label"] = f"<p>{p['cta']}</p>"
    extra = []
    if p["key"] == "repairs" and cf:
        extra = [{"dataType": "SINGLE_OPTIONS", "fieldKey": cf["fieldKey"], "fieldName": SERVICE_FIELD,
                  "hiddenFieldQueryKey": cf["fieldKey"].split(".")[-1], "id": cf["id"], "label": SERVICE_FIELD,
                  "locationId": LOC, "model": "contact", "name": SERVICE_FIELD, "picklistOptions": SERVICES_OPTS,
                  "placeholder": "Select a service", "position": 0, "required": True, "tag": cf["id"],
                  "type": "single_options", "fieldWidthPercentage": 100}]
    f["fields"] = [name, phone, email, street, zip_, *extra, consent, button]
    f["formAction"] = {**(f.get("formAction") or {}), "actionType": "1", "redirectUrl": thanks, "redirect_url": thanks}
    return keep_redirect(fd)


def make_flow(a: Agency, name: str, folder: str | None, tpl: list[dict], form_id: str | None) -> str:
    wid = ps.create_flow(a, name, folder, tpl, publish=False)
    if form_id:
        body = ps.trigger_body(wid, form_id, tpl[0]["id"])
        t = a.call("POST", BACKEND, f"/workflow/{LOC}/trigger", body=body)
        a.call("PUT", BACKEND, f"/workflow/{LOC}/trigger/{t['id']}", body={**body, "id": t["id"]})
        time.sleep(2)
    live = a.workflow(LOC, wid)
    a.call("PUT", BACKEND, f"/workflow/{LOC}/{wid}", body={"name": name, "version": live.get("version", 1),
           "status": "published", "parentId": folder, "allowMultiple": True,
           "workflowData": {"templates": live["workflowData"]["templates"]}})
    time.sleep(3)
    return wid


def main_trigger(a: Agency, wid: str, ids: list[str], apply: bool) -> None:
    trs = [t for t in a.triggers(LOC, wid) if not t.get("deleted") and t.get("type") == "form_submission"]
    t = trs[0]
    c = next(c for c in t["conditions"] if c.get("field") == "form.id")
    want = [*c["value"], *[i for i in ids if i and i not in c["value"]]]
    print(f"   {MAIN}: forms {c['value']} → {want}")
    if apply and want != c["value"]:
        backup(f"triggers-{wid}", trs)
        c["value"] = want
        body = {k: t[k] for k in ("type", "name", "masterType", "conditions", "targetActionId") if k in t}
        a.call("PUT", BACKEND, f"/workflow/{LOC}/trigger/{t['id']}", body={**body, "schedule_config": {}, "id": t["id"],
               "workflowId": wid, "workflow_id": wid, "location_id": LOC,
               "actions": [{"workflow_id": wid, "type": "add_to_workflow"}]})
        time.sleep(3)
        got = next(x for x in a.triggers(LOC, wid) if x["id"] == t["id"])
        ok = next(c for c in got["conditions"] if c.get("field") == "form.id")["value"] == want
        print(f"   {'✓' if ok else '✗'} gatilho atualizado")


def test(a: Agency) -> int:
    bad, stamp = 0, int(time.time())
    wid = make_flow(a, f"ZZ TEST {FORMS[1]['flow']}", None, ps.chain([tags(FORMS[1]["tags"])]), None)
    cid = a.call("POST", SERVICES, "/contacts/", body={
        "locationId": LOC, "firstName": "ZZ Test", "lastName": "cp lp", "tags": ["zz test"], "postalCode": "85742",
        "email": f"pedro+cp-lp-{stamp}@poolprofits.com"})["contact"]["id"]
    time.sleep(3)
    a.call("POST", SERVICES, f"/contacts/{cid}/workflow/{wid}", body={})
    time.sleep(40)
    tg = set(a.call("GET", SERVICES, f"/contacts/{cid}")["contact"].get("tags") or [])
    ok = set(FORMS[1]["tags"]) <= tg
    bad += not ok
    print(f"   {'✓' if ok else '✗'} tags {sorted(tg)}")
    a.call("DELETE", SERVICES, f"/contacts/{cid}")
    ps.drop_flow(a, wid)
    print("   limpo (contato + fluxo ZZ TEST apagados)")
    return 1 if bad else 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("mode", choices=["plan", "test", "apply"])
    p.add_argument("--thanks-weekly", default=THANKS)
    p.add_argument("--thanks-repairs", default=THANKS)
    args = p.parse_args()
    load_dotenv()
    a = Agency()
    if not a.location(LOC)["name"].lower().startswith("clear pool solutions tucson"):
        sys.exit("sub-conta errada")
    apply = args.mode == "apply"
    if args.mode != "plan":
        for t in {t for f in FORMS for t in f["tags"]}:
            try:
                a.call("POST", BACKEND, f"/workflow/{LOC}/tags/create", body={"tag": t})
            except Exception:  # noqa: BLE001 — already exists
                pass
    if args.mode == "test":
        return test(a)
    flows = {w["name"]: w["id"] for w in a.workflows(LOC)}
    folder = a.workflow(LOC, flows[MAIN]).get("parentId")
    cf = ensure_field(a, apply)
    existing = {f["name"]: f["_id"] for f in a.call("GET", BACKEND, "/forms/", params={"locationId": LOC, "limit": 100}).get("forms", [])}
    base = latest_form(a, BASE_FORM)["formData"]
    thanks = {"weekly": args.thanks_weekly, "repairs": args.thanks_repairs}
    ids = []
    for f in FORMS:
        fd = build_form(base, f, cf, thanks[f["key"]])
        fid = existing.get(f["form"])
        print(f"   {f['form']}: {'existe ' + fid if fid else 'cria'} · campos {[x['tag'] for x in fd['form']['fields']]}"
              f" · redirect {thanks[f['key']]}")
        if not apply:
            ids.append(fid)
            continue
        if fid:
            backup(f"form-{fid}", latest_form(a, fid))
        else:
            fid = a.call("POST", BACKEND, "/forms/", body={"name": f["form"], "locationId": LOC, "formData": fd})["form"]["_id"]
            time.sleep(5)
        save_form(a, fid, f["form"], fd)  # create drops redirect_url
        ids.append(fid)
        if f["flow"] in flows:
            print(f"   {f['flow']}: já existe")
        else:
            wid = make_flow(a, f["flow"], folder, ps.chain([tags(f["tags"])]), fid)
            trs = [t for t in a.triggers(LOC, wid) if not t.get("deleted")]
            print(f"   ✓ {f['flow']} {wid} {a.workflow(LOC, wid).get('status')} · gatilhos "
                  f"{[(t.get('type'), t.get('active')) for t in trs]}")
    main_trigger(a, flows[MAIN], ids, apply)
    return 0


if __name__ == "__main__":
    sys.exit(main())
