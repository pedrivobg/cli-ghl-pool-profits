#!/usr/bin/env python3
"""West Coast Pool Care: "Main Website Form" for the Lovable site (westcoastchemicalcompany.pool-profits.com),
copied from Bonneville's (approved 13/11): same fields/design, custom fields of this account, thank-you with
the West Coast phone. Then `pp_forms.py --only "West Coast Pool Care" --apply` hooks it to Website Form Fill.

    python3 scripts/wc_site_form.py            # plan
    python3 scripts/wc_site_form.py --apply
"""
from __future__ import annotations

import argparse
import copy
import json
import time

import requests

from _common import ROOT, keep_redirect, load_dotenv
from cli_anything.gohighlevel.utils.agency import BACKEND, SERVICES, Agency

SRC_LOC, SRC_FORM = "DeSfqW31OleIiU7eUt35", "eV0Jsarv8dTp59rEiZv5"   # Bonneville Main Website Form
LOC, NAME = "63COocPIEK6XLvRikVK9", "Main Website Form"
PHONE_OLD, PHONE_NEW = "(801) 915-8582", "(323) 695-6810"
FIELDS = {"contact.service_requested": ("Service Requested", "TEXT"), "contact.pool_details": ("Pool Details", "LARGE_TEXT")}


def latest(a: Agency, fid: str) -> dict:
    d = a.get(BACKEND, f"/forms/{fid}")
    d = d.get("form", d)
    vh = sorted(d.get("versionHistory") or [], key=lambda v: v.get("updatedAt", ""))
    if vh:
        d["formData"] = requests.get(vh[-1]["formDataDownloadUrl"], timeout=30).json()
    return d


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    load_dotenv()
    a = Agency()
    src = latest(a, SRC_FORM)
    mine = {f.get("fieldKey"): f for f in a.custom_fields(LOC)}
    existing = [f for f in a.forms(LOC) if f.get("name") == NAME]
    print("existe:", [f.get("_id") or f.get("id") for f in existing])
    for key, (name, dt) in FIELDS.items():
        if key not in mine:
            print("cria campo", name, dt)
            if args.apply:
                res = a.call("POST", SERVICES, f"/locations/{LOC}/customFields",
                             body={"name": name, "dataType": dt, "placeholder": "", "position": 0, "model": "contact"})
                mine[key] = res.get("customField") or res
    fd = copy.deepcopy(src["formData"])
    for fld in fd["form"]["fields"]:
        key = fld.get("fieldKey")
        if key in FIELDS:
            new = mine.get(key, {"id": "<novo>"})
            fld.update(tag=new["id"], id=new["id"], locationId=LOC)
    act = fd["form"]["formAction"]
    act["thankyouText"] = act["thankyouText"].replace(PHONE_OLD, PHONE_NEW)
    s = json.dumps(fd)
    assert SRC_LOC not in s and PHONE_OLD not in s, "sobrou dado da Bonneville"
    print("campos:", [(f.get("label"), f.get("tag")) for f in fd["form"]["fields"]][:6])
    print("obrigado:", act["thankyouText"])
    if not args.apply or existing:
        return 0
    res = a.call("POST", BACKEND, "/forms/", body={"name": NAME, "locationId": LOC, "formData": keep_redirect(fd)})
    fid = (res.get("form") or res).get("_id") or (res.get("form") or res).get("id")
    print("✓ form", fid)
    bk = ROOT / "backup" / "west-coast-pool-care"
    bk.mkdir(parents=True, exist_ok=True)
    (bk / f"form-{fid}-created.json").write_text(json.dumps(res, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
