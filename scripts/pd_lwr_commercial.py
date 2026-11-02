#!/usr/bin/env python3
"""Pool Duck Lakewood Ranch: commercial pool service lead form + workflow (Val brief, 02/11). Pool Duck token.

    set -a; . <poolduck.env>; set +a
    ./.venv/bin/python scripts/pd_lwr_commercial.py plan
    ./.venv/bin/python scripts/pd_lwr_commercial.py test --to pedro@poolprofits.com
    ./.venv/bin/python scripts/pd_lwr_commercial.py apply

Form "Google Ads - Commercial" (for Atif's commercial landing page), built from the newest version of the LWR "Google
AdWords" form (same look): title "Request a Commercial Pool Service Quote", Full Name, Email, Phone (US picker), Property
Address with Google autocomplete (fills street, city, state, ZIP), all required; the LWR consent checkbox; button "Get a
Commercial Pool Service Quote". After submit: thank-you message until the commercial thank-you page exists.
Workflow "Google Ads Commercial - Qualified Lead" (folder of "Google AdWords - Qualified Lead (Form Fill)"), the same
route as the other LWR ad leads (pd_lwr_google_leads.py): spam/DND → nothing; sent in the last 24 h → nothing; current
customer → alert marked existing customer; new → tags `commercial pool lead` + `new lead` + `google adwords` +
`lakewood ranch`, card in "Leads --> Sales Pipeline" / Lead (source "Google Ads - Commercial", no value: contracts vary),
SMS alert to Kenton + Pool Duck Service with name, phone, email and property address. No residential auto-text to the lead.
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
import time

from _common import ROOT, keep_redirect, load_dotenv
from bv_service_forms import latest_form_data
from pd_lwr_google_leads import LOC, build, create, set_status
from pp_source_tags import refs_ok

from cli_anything.gohighlevel.utils.agency import BACKEND, SERVICES, Agency

BASE_FORM = "L35gq3SnSDyoda4Kl9D4"  # "Google AdWords" (LWR)
FORM = "Google Ads - Commercial"
FOLDER_OF = "Google AdWords - Qualified Lead (Form Fill)"
F = {"key": "commercial", "flow": "Google Ads Commercial - Qualified Lead", "source": "Google Ads - Commercial",
     "tags": ["commercial pool lead", "new lead", "google adwords", "lakewood ranch"], "recent": "commercial lead 24h",
     "title": "New COMMERCIAL Pool Lead from Google Ads for Pool Duck Lakewood Ranch",
     "body": "\n\nName: {{contact.name}}\nPhone: {{contact.phone}}\nEmail: {{contact.email}}\n"
             "Property: {{contact.address1}}, {{contact.city}} {{contact.postal_code}}"}
THANKS = ("<p style='font-family: Inter, sans-serif; font-size: 18px; font-weight: 600; text-align: center;'>Thank you! "
          "A Pool Duck commercial pool specialist will contact you shortly to discuss your property's needs.</p>")
BDIR = ROOT / "backup" / "poolduck-lakewood-ranch"


def build_form(base: dict) -> dict:
    fd = copy.deepcopy(base)
    f = fd["form"]
    by = {x["tag"]: x for x in f["fields"]}
    header = {"active": False, "align": "center", "bgColor": "FFFFFF00", "hiddenFieldQueryKey": "header_1", "placeholder": "header",
              "label": '<h1 style="text-align: center;padding-left: 0px!important;"><span style="font-size: 24px">'
                       'Request a Commercial Pool Service Quote</span></h1>',
              "padding": {"bottom": 0, "left": 0, "right": 0, "top": 0}, "standard": True, "tag": "header", "type": "h1",
              "typeLabel": "Text", "weight": 600,
              "border": {"border": 0, "color": "FFFFFF", "radius": 0, "type": "none"},
              "shadow": {"blur": 0, "color": "FFFFFF", "horizontal": 0, "spread": 0, "vertical": 0}}
    phone = copy.deepcopy(by["phone"])
    phone["enableCountryPicker"] = True
    group = copy.deepcopy(by["group_address"])
    group.update(label="Property Address", placeholder="Start typing the property address", title="Property Address", required=True)
    button = copy.deepcopy(by["button"])
    button["label"] = '<p style="text-align: center;padding-left: 0px!important;"><strong>Get a Commercial Pool Service Quote</strong></p>'
    children = [copy.deepcopy(by[t]) for t in ("address", "city", "state", "postal_code")]
    f["fields"] = [header, copy.deepcopy(by["full_name"]), copy.deepcopy(by["email"]), phone, group, *children,
                   copy.deepcopy(by["terms_and_conditions"]), button]
    if isinstance(f.get("address"), dict):
        f["address"].update(label="Property Address", required=True)
    f["formAction"] = {**f["formAction"], "actionType": "2", "thankyouText": THANKS, "redirectUrl": "", "redirect_url": ""}
    return fd


def flow_tpl(test_to: str | None = None) -> list[dict]:
    tpl = build(F, test_to)
    for s in tpl:
        if s["type"] == "create_opportunity":
            s["attributes"]["monetary_value"] = ""
    return tpl


def form_trigger(wid: str, first: str, form_id: str) -> dict:
    return {"type": "form_submission", "name": "Form Submitted", "masterType": "highlevel", "schedule_config": {},
            "conditions": [{"operator": "is-any-of", "field": "form.id", "value": [form_id], "title": "Form is", "type": "select"}],
            "workflowId": wid, "workflow_id": wid, "location_id": LOC,
            "actions": [{"workflow_id": wid, "type": "add_to_workflow"}], "targetActionId": first}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("mode", choices=["plan", "test", "apply"])
    parser.add_argument("--to")
    args = parser.parse_args()
    if args.mode == "test" and not args.to:
        parser.error("--to is required in test mode")
    load_dotenv()
    a = Agency()
    if a.location(LOC)["name"] != "Pool Duck Lakewood Ranch":
        sys.exit("sub-conta errada")
    flows = {w["name"]: w["id"] for w in a.workflows(LOC)}
    folder = a.workflow(LOC, flows[FOLDER_OF]).get("parentId")
    forms = {f["name"]: f.get("id") or f.get("_id") for f in a.call("GET", SERVICES, "/forms/", params={"locationId": LOC, "limit": 100}).get("forms", [])}
    _, base = latest_form_data(a, BASE_FORM)
    if args.mode == "plan":
        print(f"   form {FORM}: {'existe' if FORM in forms else 'cria'} · {[x['tag'] for x in build_form(base)['form']['fields']]}")
        print(f"   {F['flow']}: {'existe' if F['flow'] in flows else 'cria'} · {len(flow_tpl())} passos")
        return 0
    for t in [*F["tags"], F["recent"]]:
        try:
            a.call("POST", BACKEND, f"/workflow/{LOC}/tags/create", body={"tag": t})
        except Exception:  # noqa: BLE001 — already exists
            pass
    if args.mode == "test":
        wid = create(a, f"ZZ TEST {F['flow']}", folder, flow_tpl(args.to))
        set_status(a, wid, "published")
        stamp, made, bad = int(time.time()), {}, 0
        try:
            for case, extra in (("new", []), ("customer", ["active residential client"]), ("spam", ["spam likely"])):
                made[case] = a.call("POST", SERVICES, "/contacts/", body={
                    "locationId": LOC, "firstName": "ZZ Test", "lastName": f"commercial {case}", "tags": extra,
                    "email": args.to.replace("@", f"+lwr-com-{case}-{stamp}@"), "address1": "1 Test Way",
                    "city": "Lakewood Ranch", "postalCode": "34202"})["contact"]["id"]
            time.sleep(3)
            for cid in made.values():
                a.call("POST", SERVICES, f"/contacts/{cid}/workflow/{wid}", body={})
            time.sleep(30)
            a.call("POST", SERVICES, f"/contacts/{made['new']}/workflow/{wid}", body={})  # a second submit
            time.sleep(30)
            want = {"new": (set(F["tags"]) | {F["recent"]}, 1), "customer": (set(F["tags"]) - {"new lead"}, 0), "spam": (set(), 0)}
            for case, cid in made.items():
                tg = set(a.call("GET", SERVICES, f"/contacts/{cid}")["contact"].get("tags") or [])
                opps = a.call("GET", SERVICES, "/opportunities/search", params={"location_id": LOC, "contact_id": cid}).get("opportunities", [])
                exp, cards = want[case]
                ok = exp <= tg and len(opps) == cards and all(o.get("source") == F["source"] for o in opps) and \
                    (case != "spam" or "commercial pool lead" not in tg)
                bad += not ok
                print(f"   {'✓' if ok else '✗'} {case}: tags {sorted(tg)} · cards {[(o.get('source'), o.get('monetaryValue')) for o in opps]}")
        finally:
            for cid in made.values():
                for o in a.call("GET", SERVICES, "/opportunities/search", params={"location_id": LOC, "contact_id": cid}).get("opportunities", []):
                    a.call("DELETE", SERVICES, f"/opportunities/{o['id']}")
                a.call("DELETE", SERVICES, f"/contacts/{cid}")
            set_status(a, wid, "draft")
            a.call("DELETE", BACKEND, f"/workflow/{LOC}/{wid}")
        print(f"   limpo. Esperado em {args.to}: 1 alerta do novo (não 2), 1 do cliente (EXISTING CUSTOMER), 0 do spam.")
        return 1 if bad else 0
    if FORM in forms:
        fid = forms[FORM]
        f, cur = latest_form_data(a, fid)
        if (cur["form"].get("address") or {}).get("label") != "Property Address":
            (BDIR / f"form-{fid}-{time.strftime('%Y%m%d-%H%M%S')}.json").write_text(json.dumps({"form": f, "formData": cur}))
            cur["form"]["address"].update(label="Property Address", required=True)
            for wait in (0, 30, 60, 120, 240):  # a new form answers 404 to updates for a few minutes
                time.sleep(wait)
                try:
                    a.call("POST", BACKEND, f"/forms/{fid}", body={"name": FORM, "formData": cur})
                    break
                except Exception:  # noqa: BLE001
                    pass
        print(f"   form {FORM}: já existe ({fid}) · endereço: {latest_form_data(a, fid)[1]['form']['address'].get('label')}")
    else:
        res = a.call("POST", BACKEND, "/forms/", body={"name": FORM, "locationId": LOC, "formData": keep_redirect(build_form(base))})
        fid = (res.get("form") or res).get("_id") or (res.get("form") or res).get("id")
        print(f"   ✓ form {FORM}: {fid} · https://api.leadconnectorhq.com/widget/form/{fid}")
    if F["flow"] in flows:
        print(f"   {F['flow']}: já existe")
        return 0
    tpl = flow_tpl()
    wid = create(a, F["flow"], folder, tpl)
    t = form_trigger(wid, tpl[0]["id"], fid)
    r = a.call("POST", BACKEND, f"/workflow/{LOC}/trigger", body=t)
    a.call("PUT", BACKEND, f"/workflow/{LOC}/trigger/{r['id']}", body={**t, "id": r["id"]})
    got = set_status(a, wid, "published")
    trs = [x for x in a.triggers(LOC, wid) if not x.get("deleted")]
    ok = got["status"] == "published" and refs_ok(got["workflowData"]["templates"]) and len(trs) == 1 and trs[0].get("active")
    print(f"   {'✓' if ok else '✗ VERIFICAR'} {F['flow']}: {got['status']} · gatilho form {fid}")
    BDIR.mkdir(parents=True, exist_ok=True)
    (BDIR / "commercial-ids.json").write_text(json.dumps({"form": fid, "workflow": wid}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
