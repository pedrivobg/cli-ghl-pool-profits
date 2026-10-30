#!/usr/bin/env python3
"""NorTex landing page forms look like the website's quote form (client via Val, 30/10).

    ./.venv/bin/python scripts/nx_ads_form_style.py preview     # temporary form with the WEEKLY layout + screenshots
    ./.venv/bin/python scripts/nx_ads_form_style.py apply

Built from the newest version of "New Website Form" (the one on nortexpools.com): navy box with gold border, white
"GET YOUR SERVICE QUOTE" title, Full Name / Phone (country picker) / Email, gold button. Each landing page form keeps
what is its own: name, redirect to the booking calendar (nx_ads_booking.py), email settings, the button text, and
the consent checkbox + Terms/Privacy links (A2P), in white for the dark box. REPAIR also keeps "What equipment needs
repair?" and the $150 diagnostic note. Street/City/ZIP go away, as on the website (the lead workflows only print them
in Fareed's alert). Backup of each form before saving; both redirect fields kept (keep_redirect).
"""
from __future__ import annotations

import argparse
import copy
import json
import subprocess
import sys
import time

from _common import ROOT, keep_redirect, load_dotenv
from bv_service_forms import latest_form_data

from cli_anything.gohighlevel.utils.agency import BACKEND, Agency

LOC = "k6nDPHktS2PySJoJuwpG"
SITE_FORM = "oXWnLdsRNgpoUXUqIQE6"
FORMS = {"lxtvCbfxc4lDxC50Sifc": {"title": "GET YOUR SERVICE QUOTE", "cta": "GET MY FREE QUOTE"},
         "L3f9uKoFBk7QmOtl0hkq": {"title": "SCHEDULE A REPAIR VISIT", "cta": "SCHEDULE A REPAIR VISIT"}}
EQUIPMENT = "xQQ0Am5xSXEl5adEYvn3"
WHITE = "rgba(255,255,255,1)"
BDIR = ROOT / "backup" / "nortex-pools"


def white(html: str) -> str:
    return html.replace("color: rgb(13, 14, 15)", f"color: {WHITE}").replace('<span style="font-size: 14px">',
                                                                            f'<span style="font-size: 14px; color: {WHITE}">')


def build(site: dict, lp: dict, spec: dict) -> dict:
    fd = copy.deepcopy(site)
    for k in ("emailNotifications", "autoResponder", "parentFolderId", "parentFolderName"):
        if k in lp:
            fd[k] = copy.deepcopy(lp[k])
    form = fd["form"]
    form["formAction"] = copy.deepcopy(lp["form"]["formAction"])
    by = {x["tag"]: x for x in site["form"]["fields"]}
    own = {x["tag"]: x for x in lp["form"]["fields"]}
    title = copy.deepcopy(by["header"])
    title["label"] = title["label"].replace("GET YOUR SERVICE QUOTE", spec["title"])
    button = copy.deepcopy(by["button"])
    button["label"] = button["label"].replace("GET A QUOTE", spec["cta"])
    fields = [title, *(copy.deepcopy(by[t]) for t in ("full_name", "phone", "email"))]
    if EQUIPMENT in own:
        fields.append(copy.deepcopy(own[EQUIPMENT]))
    consent = copy.deepcopy(own["terms_and_conditions"])
    for k in ("placeholder", "preview"):
        if k in consent:
            consent[k] = consent[k].replace("color: rgb(13, 14, 15)", f"color: {WHITE}").replace("color: #000000;", f"color: {WHITE};")
    fields.append(consent)
    if "header_notice" in own:
        note = copy.deepcopy(own["header_notice"])
        note["label"] = note["label"].replace("<strong>", f'<strong style="color: {WHITE}">')
        fields.append(note)
    fields.append(button)
    links = next(x for x in lp["form"]["fields"] if x["type"] == "h1" and "terms_of_use" in x.get("label", ""))
    links = copy.deepcopy(links)
    links["label"] = white(links["label"])
    links["tag"] = "header_links"
    fields.append(links)
    form["fields"] = fields
    return fd


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("mode", choices=["preview", "apply"])
    args = parser.parse_args()
    load_dotenv()
    a = Agency()
    if not a.location(LOC)["name"].lower().startswith("nortex"):
        sys.exit("sub-conta errada")
    _, site = latest_form_data(a, SITE_FORM)
    if args.mode == "preview":
        out = ROOT / "reports" / "nortex-pools"
        out.mkdir(parents=True, exist_ok=True)
        made = []
        try:
            for fid, spec in FORMS.items():
                _, lp = latest_form_data(a, fid)
                fd = build(site, lp, spec)
                res = a.call("POST", BACKEND, "/forms/", body={"name": f"ZZ TEST style {spec['title']}", "locationId": LOC, "formData": fd})
                nid = (res.get("form") or res).get("_id") or (res.get("form") or res).get("id")
                made.append(nid)
                url = f"https://link.nortexpools.com/widget/form/{nid}"
                png = out / f"form-style-{fid}.png"
                time.sleep(5)
                subprocess.run(["/opt/pw-browsers/chromium", "--headless", "--no-sandbox", "--hide-scrollbars",
                                "--window-size=620,1100", "--virtual-time-budget=15000", f"--screenshot={png}", url],
                               capture_output=True, timeout=90)
                print(f"   {spec['title']}: {png}")
        finally:
            for nid in made:
                try:
                    a.call("DELETE", BACKEND, f"/forms/{nid}")
                except Exception as e:  # noqa: BLE001
                    print(f"   apagar {nid} à mão: {e}")
        return 0
    BDIR.mkdir(parents=True, exist_ok=True)
    for fid, spec in FORMS.items():
        f, lp = latest_form_data(a, fid)
        (BDIR / f"form-{fid}-{time.strftime('%Y%m%d-%H%M%S')}.json").write_text(json.dumps({"form": f, "formData": lp}))
        fd = build(site, lp, spec)
        a.call("POST", BACKEND, f"/forms/{fid}", body={"name": f["name"], "formData": keep_redirect(fd)})
        time.sleep(5)
        _, got = latest_form_data(a, fid)
        act = got["form"]["formAction"]
        tags = [x["tag"] for x in got["form"]["fields"]]
        ok = act.get("redirect_url") == lp["form"]["formAction"].get("redirect_url") and \
            got["form"]["style"] == site["form"]["style"] and "full_name" in tags
        print(f"   {'✓' if ok else '✗ VERIFICAR'} {f['name']}: {tags}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
