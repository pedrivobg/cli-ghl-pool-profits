#!/usr/bin/env python3
"""Sparkling Clear Pool Service: GHL form to replace the WPForms quote form on sparklingclearpool.com (Frank 18/11:
submissions straight into GHL + less spam). Design copied from Bonneville's "Main Website Form" (approved 13/11);
fields as the site form: Full Name, Service Needed (dropdown, site options), Phone (country picker, US default),
ZIP, Email, Are You A New Customer? (the account's own field), SMS consent. Thank-you with the main line.
Then `pp_forms.py --only "Sparkling" --apply` hooks it to Website Form Fill and `pc_form_spam.py --loc sparkling`
adds the spam branch.

    python3 scripts/sp_site_form.py            # plan
    python3 scripts/sp_site_form.py --apply
"""
from __future__ import annotations

import argparse
import copy
import json

from _common import ROOT, keep_redirect, load_dotenv
from cli_anything.gohighlevel.utils.agency import BACKEND, SERVICES, Agency
from wc_site_form import SRC_FORM, SRC_LOC, latest

LOC, NAME = "G9jACRTK8rh04j29ZTQf", "Website Contact Form"
PHONE_OLD, PHONE_NEW = "(801) 915-8582", "(469) 884-4022"
SERVICES_LIST = ["Weekly Pool Service", "Commercial Pool Service", "Equipment Repair", "Equipment Installation",
                 "Green To Clean", "Other"]
NEW_FIELDS = {"contact.service_needed": ("Service Needed", SERVICES_LIST),
              "contact.are_you_a_new_customer": ("Are You A New Customer?", ["Yes", "No"])}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    load_dotenv()
    a = Agency()
    src = latest(a, SRC_FORM)
    cfs = {c.get("fieldKey"): c for c in a.custom_fields(LOC)}
    existing = [f for f in a.forms(LOC) if f.get("name") == NAME]
    print("existe:", [f.get("_id") or f.get("id") for f in existing])
    made = {}
    for key, (name, options) in NEW_FIELDS.items():
        c = cfs.get(key)
        if not c:
            print("cria campo", name, "(SINGLE_OPTIONS)")
            if args.apply:
                res = a.call("POST", SERVICES, f"/locations/{LOC}/customFields", body={
                    "name": name, "dataType": "SINGLE_OPTIONS", "options": options, "placeholder": "",
                    "position": 0, "model": "contact"})
                c = res.get("customField") or res
        made[key] = c or {"id": "<novo>", "fieldKey": key, "name": name}
    svc, newc = made["contact.service_needed"], made["contact.are_you_a_new_customer"]
    fd = copy.deepcopy(src["formData"])
    fields = fd["form"]["fields"]
    by = {f.get("tag"): f for f in fields}
    opt = lambda c, label, options: {  # noqa: E731
        "custom": True, "dataType": "SINGLE_OPTIONS", "fieldKey": c["fieldKey"], "fieldName": c["name"],
        "fieldWidthPercentage": 100, "hiddenFieldQueryKey": c["fieldKey"].split(".")[-1], "id": c["id"],
        "tag": c["id"], "label": label, "locationId": LOC, "model": "contact", "name": c["name"],
        "picklistOptions": options, "placeholder": "Select One", "position": 0, "required": True,
        "standard": False, "type": "single_options", "typeLabel": "Single Options"}
    out = []
    for f in fields:
        key = f.get("fieldKey")
        if key == "contact.service_requested":
            out.append(opt(svc, "Service Needed", SERVICES_LIST))
        elif key == "contact.pool_details":
            out.append(opt(newc, "Are You A New Customer?", ["Yes", "No"]))
        else:
            if f.get("tag") == "postal_code":
                f.update(label="Zip Code", placeholder="Zip Code", title="Zip Code")
            if f.get("tag") == "button":
                f["label"] = f["label"].replace("REQUEST MY QUOTE", "SUBMIT")
            out.append(f)
    order = ["full_name", svc["id"], "phone", "postal_code", "email", newc["id"]]  # same order as the site form
    out = sorted(out, key=lambda f: order.index(f.get("tag")) if f.get("tag") in order else len(order))
    fd["form"]["fields"] = out
    by["phone"]["enableCountryPicker"] = True
    act = fd["form"]["formAction"]
    act["thankyouText"] = act["thankyouText"].replace(PHONE_OLD, PHONE_NEW)
    s = json.dumps(fd)
    assert SRC_LOC not in s and PHONE_OLD not in s and "Bonneville" not in s, "sobrou dado da Bonneville"
    print("campos:", [(f.get("label", "")[:40], f.get("tag")) for f in out])
    print("obrigado:", act["thankyouText"])
    if not args.apply or existing:
        return 0
    res = a.call("POST", BACKEND, "/forms/", body={"name": NAME, "locationId": LOC, "formData": keep_redirect(fd)})
    form = res.get("form") or res
    fid = form.get("_id") or form.get("id")
    print("✓ form", fid)
    bk = ROOT / "backup" / "sparkling-clear-pool-service"
    bk.mkdir(parents=True, exist_ok=True)
    (bk / f"form-{fid}-created.json").write_text(json.dumps(res, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
