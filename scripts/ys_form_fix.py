#!/usr/bin/env python3
"""YardSpring landing page forms: Val's test fixes (30/10).

    ./.venv/bin/python scripts/ys_form_fix.py plan
    ./.venv/bin/python scripts/ys_form_fix.py apply

- Thank-you redirect: the forms sent people to yardspringpools.com/thank-you-… (WordPress, 404). Atif's thank-you pages
  are in the same GHL funnel as the landing pages ("Google Ads Landing Pages", go.yardspringpools.com) → redirect there
  (redirectUrl + redirect_url).
- Full Name instead of First/Last (GHL splits it into first/last on the contact; the texts keep {{contact.first_name}}).
- Address autocomplete: Street/City/ZIP → the standard "Property Address" group (Google search; fills street, city,
  state and ZIP on the contact), as on Pool Shack's forms.
Everything else on each form stays (style, consent, button). Latest version read first; backup before saving.
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
import time

from _common import ROOT, keep_redirect, load_dotenv
from bv_service_forms import latest_form_data

from cli_anything.gohighlevel.utils.agency import BACKEND, Agency

LOC = "FpRTQZR56xwp1Wg5NQCq"
SITE = "https://go.yardspringpools.com"
FORMS = {"9iaWMGXpWLX2Gscp8fvv": "/weekly-pool-service-3356",   # Thank You - Weekly Pool Service
         "roBFeBcQq9CksEMRswQz": "/weekly-pool-service-8572",   # Thank You - Pool Closing & Winterization
         "jWtZJgbvadbLwWwjcTMX": "/weekly-pool-service-6305"}   # Thank You - Pool Equipment Repair
FULL = {"active": False, "fieldWidthPercentage": 100, "hiddenFieldQueryKey": "full_name", "label": "Full Name",
        "placeholder": "Full Name", "required": True, "standard": True, "tag": "full_name", "type": "text", "typeLabel": "Text"}
ADDRESS = {"active": False, "hiddenFieldQueryKey": "group_address", "label": "Property Address", "placeholder": "Property Address",
           "required": True, "standard": True, "tag": "group_address", "title": "Property Address", "type": "group"}
BDIR = ROOT / "backup" / "yardspring-pools"


def fix(fd: dict, url: str) -> dict:
    out = copy.deepcopy(fd)
    f = out["form"]
    fields = []
    for x in f["fields"]:
        if x["tag"] == "first_name":
            fields.append(copy.deepcopy(FULL))
        elif x["tag"] == "address":
            fields.append(copy.deepcopy(ADDRESS))
        elif x["tag"] not in ("last_name", "city", "postal_code"):
            fields.append(x)
    f["fields"] = fields
    f["formAction"].update(actionType="1", redirectUrl=url, redirect_url=url)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("mode", choices=["plan", "apply"])
    args = parser.parse_args()
    load_dotenv()
    a = Agency()
    if not a.location(LOC)["name"].lower().startswith("yardspring"):
        sys.exit("sub-conta errada")
    BDIR.mkdir(parents=True, exist_ok=True)
    for fid, path in FORMS.items():
        f, fd = latest_form_data(a, fid)
        new = fix(fd, SITE + path)
        print(f"   {f['name']}: {[x['tag'] for x in fd['form']['fields']]} → {[x['tag'] for x in new['form']['fields']]}"
              f" · obrigado → {SITE + path}")
        if args.mode != "apply":
            continue
        (BDIR / f"form-{fid}-{time.strftime('%Y%m%d-%H%M%S')}.json").write_text(json.dumps({"form": f, "formData": fd}))
        a.call("POST", BACKEND, f"/forms/{fid}", body={"name": f["name"], "formData": keep_redirect(new)})
        time.sleep(5)
        _, got = latest_form_data(a, fid)
        act, tags = got["form"]["formAction"], [x["tag"] for x in got["form"]["fields"]]
        ok = act.get("redirect_url") == SITE + path == act.get("redirectUrl") and "full_name" in tags and "group_address" in tags
        print(f"      {'✓' if ok else '✗ VERIFICAR'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
