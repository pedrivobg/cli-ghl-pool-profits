#!/usr/bin/env python3
"""Make the review gate (NPS → Google review or team alert) actually work.

    ./.venv/bin/python scripts/pp_nps.py --only "Southern Pool"            # plan
    ./.venv/bin/python scripts/pp_nps.py --only "Southern Pool" --apply

The Review Request workflow texts an NPS request, waits for contact.nps_score and
sends 4-5 to the Google review and 0-3 to the team. Two things broke it:
the SMS had no link to answer (nps_survey_link was empty), and every NPS Form
from the snapshot saved the score into a custom field id that does not exist in
the account, so the score never reached the contact.

Per account this:
1. creates the custom fields NPS Score / NPS Message if missing;
2. creates the NPS Form from the model if the account has none, and points its
   NPS fields at the account's own custom fields;
3. fills the custom value nps_survey_link with the form's link;
4. sets the NPS SMS template to the link, pre-filled with the contact's email and
   phone (so the answer lands on the right contact); first/last name become optional.
Every change is backed up first.
"""
from __future__ import annotations

import argparse
import json
import re
import time

from _common import PRIORITY, ROOT, keep_redirect, load_dotenv, location_dirs
from pp_audit import load

from cli_anything.gohighlevel.utils.agency import BACKEND, SERVICES, Agency

FORM_HOST = "https://link.poolprofits.com/widget/form/"
TEMPLATE = "NPS Survey - SMS Request"
SMS = ("Hi {{contact.first_name}}, thanks again for choosing {{custom_values.friendly_business_name}}! "
       "How did we do? Please take 10 seconds to rate your experience here: "
       "{{custom_values.nps_survey_link}}?email={{contact.email}}&phone={{contact.phone_raw}} "
       "We really appreciate your feedback.")
# Tested live: {{contact.phone}} renders "(480) 555-1234" and names can hold spaces — a space
# ends the link in the SMS. phone_raw has none; liquid filters (| url_encode) make GHL drop
# the message. So the link carries only email + phone, and the name fields are optional.
OPTIONAL = ("first_name", "last_name")
FIELDS = {"contact.nps_score": ("NPS Score", "TEXT"), "contact.nps_message": ("NPS Message", "LARGE_TEXT")}


def backup(slug: str, kind: str, oid: str, data) -> None:
    d = ROOT / "backup" / slug
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{kind}-{oid}-{time.strftime('%Y%m%d-%H%M%S')}.json").write_text(json.dumps(data, ensure_ascii=False, indent=1))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--only", action="append", required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    load_dotenv()
    a = Agency()
    model = load(location_dirs([PRIORITY["model"]])[0] / "location.json", {})["id"]

    for d in location_dirs(args.only):
        loc = load(d / "location.json", {})["id"]
        print(f"== {load(d / 'location.json', {}).get('name')}")

        # 1. custom fields
        cfs = {c.get("fieldKey"): c["id"] for c in a.custom_fields(loc)}
        for key, (name, dtype) in FIELDS.items():
            if key not in cfs:
                print(f"   cria campo {name}")
                if args.apply:
                    made = a.call("POST", SERVICES, f"/locations/{loc}/customFields",
                                  body={"name": name, "dataType": dtype, "model": "contact"})
                    cfs[key] = (made.get("customField") or made)["id"]

        # 2. NPS form
        forms = [f for f in a.forms(loc) if f["name"].strip().lower() == "nps form"]
        if forms:
            fid = sorted(forms, key=lambda f: f.get("dateAdded", ""))[0]["_id"]
            form = a.get(BACKEND, f"/forms/{fid}")
            form = form.get("form", form)
            fd = json.loads(json.dumps(form["formData"]))
        else:
            src = [f for f in a.forms(model) if f["name"].strip().lower() == "nps form"][0]
            form = a.get(BACKEND, f"/forms/{src['_id']}")
            form = form.get("form", form)
            fd = json.loads(json.dumps(form["formData"]).replace(model, loc))
            fid = None
        changed = False
        for fl in fd["form"]["fields"]:
            key = fl.get("fieldKey")
            if key in FIELDS and cfs.get(key) and fl.get("tag") != cfs[key]:
                fl["tag"] = cfs[key]
                changed = True
            if fl.get("tag") in OPTIONAL and fl.get("required"):
                fl["required"] = False
                changed = True
        if fid is None:
            print("   cria NPS Form (cópia do modelo)")
            if args.apply:
                res = None
                for body in ({"name": "NPS Form", "formData": fd, "locationId": loc},
                             {"name": "NPS Form", "formData": fd}):
                    try:
                        res = a.call("POST", BACKEND, "/forms/", body=body)
                        break
                    except Exception as exc:  # noqa: BLE001 — try the next body shape
                        last = exc
                if res is None:
                    print(f"   ✗ não consegui criar o form: {last}")
                    continue
                made = res.get("data") or res.get("form") or res
                fid = made.get("_id") or made.get("id")
                if not any(f["_id"] == fid for f in a.forms(loc)):
                    print(f"   ✗ form criado não aparece na conta: {str(res)[:200]}")
                    continue
        elif changed:
            print(f"   corrige NPS Form {fid}: campos da conta, nome/sobrenome opcionais")
            if args.apply:
                backup(d.name, "form", fid, form)
                a.call("POST", BACKEND, f"/forms/{fid}", body={"name": form["name"], "formData": keep_redirect(fd)})
        if args.apply and fid:
            for _ in range(6):  # GHL reads lag a few seconds behind the write
                time.sleep(3)
                g = a.get(BACKEND, f"/forms/{fid}")
                g = g.get("form", g)
                tags = {x.get("fieldKey"): x.get("tag") for x in g["formData"]["form"]["fields"] if x.get("fieldKey")}
                req = [x.get("tag") for x in g["formData"]["form"]["fields"] if x.get("tag") in OPTIONAL and x.get("required")]
                ok = all(tags.get(k) == cfs.get(k) for k in FIELDS if k in tags) and not req
                if ok:
                    break
            print(f"   {'✓' if ok else '✗ VERIFICAR'} NPS Form {fid}: {tags}")

        # 3. custom value
        link = f"{FORM_HOST}{fid}" if fid else None
        cvs = {(c.get("fieldKey") or "").replace("{{", "").replace("}}", "").strip(): c for c in a.custom_values(loc)}
        cv = cvs.get("custom_values.nps_survey_link")
        if link and (not cv or cv.get("value") != link):
            print(f"   nps_survey_link = {link}")
            if args.apply:
                if cv:
                    backup(d.name, "customvalue", cv["id"], cv)
                    a.call("PUT", SERVICES, f"/locations/{loc}/customValues/{cv['id']}", body={"name": cv["name"], "value": link})
                else:
                    a.call("POST", SERVICES, f"/locations/{loc}/customValues", body={"name": "NPS Survey Link", "value": link})

        # 4. SMS template
        for sn in a.snippets(loc):
            if sn["name"].strip() != TEMPLATE or (sn.get("template") or {}).get("body") == SMS:
                continue
            print(f"   template '{TEMPLATE}' ({sn['_id']}) → link do NPS pré-preenchido")
            if args.apply:
                backup(d.name, "snippet", sn["_id"], sn)
                tpl = dict(sn.get("template") or {})
                tpl["body"] = SMS
                a.call("PUT", BACKEND, f"/snippets/{loc}/{sn['_id']}", body={"name": sn["name"], "type": sn["type"], "template": tpl})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
