#!/usr/bin/env python3
"""Bluewater Brokerage: bluewaterbrokerage.com → the GHL webhooks of scripts/bw_forms.py (site side, by us).

    set -a; . <scratchpad>/bluewater-wp.env; set +a    # BW_WP_USER + BW_WP_APP_PASSWORD (WordPress Application Password)
    ./.venv/bin/python scripts/bw_site.py plan          # access, plugins, snippet state, local test of the PHP
    ./.venv/bin/python scripts/bw_site.py apply         # Code Snippets (installed if missing) + snippet active
    ./.venv/bin/python scripts/bw_site.py test          # each form's mapping run by the snippet on the site (dry)
    ./.venv/bin/python scripts/bw_site.py test --send   # same, posted to GHL and checked there (BurchTech token too;
                                                        #   run bw_forms.py test --to <inbox> first, live after)
    ./.venv/bin/python scripts/bw_site.py status        # last sends logged by the snippet
    ./.venv/bin/python scripts/bw_site.py off           # deactivate the snippet (the site goes back to e-mail only)

The site e-mails every form to Bill (Elementor actions and the calculator's /bwb/v1/route-lead endpoint). One
PHP snippet (site/bluewater/bwb-ghl.php) also posts each submission to its webhook, after the site's own handling,
so nothing that works today changes. The webhook ids come from backup/bluewater-brokerage/webhook-urls.json
(written by bw_forms.py, out of git) and are filled in at apply time.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time

import requests

from _common import ROOT, load_dotenv

SITE = "https://bluewaterbrokerage.com"
SNIPPET = "Bluewater forms → GHL (Pool Profits)"
PHP = ROOT / "site" / "bluewater" / "bwb-ghl.php"
URLS = ROOT / "backup" / "bluewater-brokerage" / "webhook-urls.json"
HOOK_KEYS = {"GATE": "Website - Route Calculator Lead", "FIGURES": "Website - Route Calculator Figures",
             "SELLER": "Website - Seller's Guide Download", "BUYER": "Website - Buyer's Guide Download",
             "CONTACT": "Website - Contact Form", "NEWSLETTER": "Website - Newsletter Signup"}

# Site-side input for each form that must come out as bw_forms.SAMPLES (so bw_forms.check() verifies GHL).
CALC_WHO = {"business": "Test Pool Co", "name": "TEST Calculator", "email": "bw-test-calc@example.com",
            "phone": "+18435550101", "city": "Myrtle Beach, SC", "report": True, "talk": True}
SITE_SAMPLES = {
    "Website - Route Calculator Lead": {"calculator": {"type": "gate", "who": CALC_WHO, "figures": None,
                                                       "website": "", "page": "/route-calculator/"}},
    "Website - Route Calculator Figures": {"calculator": {"type": "figures", "who": CALC_WHO, "website": "",
                                                          "page": "/route-calculator/", "figures": {
        "monthly_billing": 42000, "visits_per_week": 310, "quality_score": 6.4, "multiple": 10.2,
        "value_low": 410000, "value_high": 470000, "equipment_value": 85000, "inventory_value": 12000,
        "is_franchise": False, "has_agreements": "Some signed"}}},
    "Website - Seller's Guide Download": {"elementor": {"form_id": "bwr0009", "page": "/resources/", "fields": {
        "name": "TEST Seller Guide", "email": "bw-test-seller@example.com", "opinion": "on", "hp": ""}}},
    "Website - Buyer's Guide Download": {"elementor": {"form_id": "bwr0010", "page": "/resources/", "fields": {
        "name": "TEST Buyer Guide", "email": "bw-test-buyer@example.com", "register": "", "hp": ""}}},
    "Website - Contact Form": {"elementor": {"form_id": "c6411dd", "page": "/contact/", "fields": {
        "name": "TEST Contact", "email": "bw-test-contact@example.com", "phone": "+18435550102",
        "message": "Test message from the website contact form."}}},
    "Website - Newsletter Signup": {"elementor": {"form_id": "36394603", "page": "/", "fields": {
        "email": "bw-test-news@example.com"}}},
}


class WP:
    def __init__(self) -> None:
        user, pw = os.environ.get("BW_WP_USER"), os.environ.get("BW_WP_APP_PASSWORD")
        if not user or not pw:
            sys.exit("faltam BW_WP_USER / BW_WP_APP_PASSWORD (carregar bluewater-wp.env)")
        self.s = requests.Session()
        self.s.auth = (user, pw.replace(" ", ""))
        self.s.headers["User-Agent"] = "Mozilla/5.0 (Pool Profits bw_site)"

    def __call__(self, method: str, path: str, ok: tuple = (200, 201), **kw):
        r = self.s.request(method, SITE + "/wp-json" + path, timeout=60, **kw)
        if r.status_code not in ok:
            raise SystemExit(f"{method} {path}: HTTP {r.status_code} {r.text[:300]}")
        return r.json() if r.text else None


def render() -> str:
    urls = json.loads(URLS.read_text())
    code = PHP.read_text()
    for key, name in HOOK_KEYS.items():
        code = code.replace(f"__HOOK_{key}__", urls[name].rsplit("/", 1)[1])
    if re.search(r"__HOOK_[A-Z]+__", code):
        sys.exit("sobrou placeholder no snippet")
    return code.removeprefix("<?php").lstrip("\n")


def local_test() -> bool:
    r = subprocess.run(["php", str(PHP.parent / "test-bwb-ghl.php")], capture_output=True, text=True)
    print("   teste local do PHP: " + ("ok" if r.returncode == 0 else "FALHOU\n" + r.stdout + r.stderr))
    return r.returncode == 0


def snippet(wp: WP) -> dict | None:
    for s in wp("GET", "/code-snippets/v1/snippets"):
        if s.get("name") == SNIPPET:
            return s
    return None


def plugins(wp: WP) -> dict[str, dict]:
    return {p["plugin"]: p for p in wp("GET", "/wp/v2/plugins")}


def site_ok() -> bool:
    r = requests.get(SITE + "/", headers={"User-Agent": "Mozilla/5.0"}, timeout=60)
    return r.status_code == 200 and "elementor-form" in r.text


def run_tests(wp: WP, send: bool) -> int:
    from bw_forms import SAMPLES  # same payloads the GHL side was tested with
    bad = 0
    for name, body in SITE_SAMPLES.items():
        out = wp("POST", "/bwb-ghl/v1/test", json={**body, "send": send})
        want = SAMPLES[name]
        ok = out.get("data") == want and (not send or out.get("sent") == 200)
        bad += not ok
        print(f"   {'✓' if ok else '✗'} {name}: {out.get('form')}" + (f" · GHL HTTP {out.get('sent')}" if send else "")
              + ("" if ok else f"\n      saiu    {out.get('data')}\n      esperado {want}"))
    return bad


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("mode", choices=["plan", "apply", "test", "status", "off"])
    parser.add_argument("--send", action="store_true", help="test: post to GHL and check the contacts there")
    args = parser.parse_args()
    load_dotenv()
    wp = WP()
    me = wp("GET", "/wp/v2/users/me", params={"context": "edit"})
    caps = me.get("capabilities") or {}
    print(f"== {SITE} · usuário {me.get('username')} ({', '.join(me.get('roles') or [])})")
    if not caps.get("manage_options"):
        sys.exit("o usuário precisa ser Administrator")

    if args.mode == "plan":
        have = plugins(wp)
        for p in have.values():
            print(f"   {p['status']:9} {p['name']} {p.get('version', '')}")
        cs = next((p for k, p in have.items() if k.startswith("code-snippets/")), None)
        print(f"   Code Snippets: {cs['status'] if cs else 'não instalado (apply instala)'}")
        if cs and cs["status"] == "active":
            s = snippet(wp)
            print(f"   snippet: {('ativo' if s.get('active') else 'inativo') if s else 'não existe'}")
        return 0 if local_test() else 1

    if args.mode == "apply":
        if not local_test():
            return 1
        code = render()
        have = plugins(wp)
        cs = next((k for k in have if k.startswith("code-snippets/")), None)
        if not cs:
            wp("POST", "/wp/v2/plugins", json={"slug": "code-snippets", "status": "active"})
            print("   + Code Snippets instalado e ativo")
        elif have[cs]["status"] != "active":
            wp("POST", f"/wp/v2/plugins/{cs}", json={"status": "active"})
            print("   + Code Snippets ativado")
        body = {"name": SNIPPET, "code": code, "scope": "global", "active": True, "priority": 10,
                "tags": ["pool-profits", "ghl"],
                "desc": "Sends each website form to its webhook in Bill's GHL (Bluewater Brokerage). "
                        "Source: pedrivobg/cli-ghl-pool-profits site/bluewater/bwb-ghl.php. Pool Profits."}
        old = snippet(wp)
        if old:
            bdir = ROOT / "backup" / "bluewater-brokerage"
            (bdir / f"snippet-{old['id']}-{time.strftime('%Y%m%d-%H%M%S')}.json").write_text(json.dumps(old))
            made = wp("PUT", f"/code-snippets/v1/snippets/{old['id']}", json=body)
        else:
            made = wp("POST", "/code-snippets/v1/snippets", json=body)
        if made.get("code_error"):
            wp("POST", f"/code-snippets/v1/snippets/{made['id']}/deactivate")
            sys.exit(f"erro no snippet, desativado: {made['code_error']}")
        print(f"   ✓ snippet #{made['id']} {'atualizado' if old else 'criado'} e ativo")
        if not site_ok():
            wp("POST", f"/code-snippets/v1/snippets/{made['id']}/deactivate")
            sys.exit("a home não abriu normal depois do snippet: desativado")
        st = wp("GET", "/bwb-ghl/v1/status")
        print(f"   ✓ site no ar, snippet v{st['version']} respondendo")
        return run_tests(wp, False)

    if args.mode == "test":
        if not args.send:
            return run_tests(wp, False)
        from bw_forms import LOC, check, cleanup
        from cli_anything.gohighlevel.utils.agency import Agency
        a = Agency()
        if a.company_id() != "syjenoyGz1jZ3ndDPkCm":
            sys.exit("--send precisa do token da BurchTech também (carregar burchtech.env)")
        cf = {c["name"]: c["id"] for c in a.custom_fields(LOC)}
        cleanup(a)
        bad = run_tests(wp, True)
        time.sleep(45)
        for name in SITE_SAMPLES:
            probs = check(a, name, SITE_SAMPLES[name].get("elementor", {}).get("fields", {}).get("email")
                          or CALC_WHO["email"], cf)
            bad += bool(probs)
            print(f"   {'✓' if not probs else '✗'} GHL {name}" + (f": {probs}" if probs else ""))
        cleanup(a)
        print("   contatos de teste apagados")
        return 1 if bad else 0

    if args.mode == "status":
        st = wp("GET", "/bwb-ghl/v1/status")
        print(f"   snippet v{st['version']}")
        for when, form, email, code in st["log"]:
            print(f"   {when} {form:10} {code} {email}")
        return 0

    s = snippet(wp)  # off
    if s and s.get("active"):
        wp("POST", f"/code-snippets/v1/snippets/{s['id']}/deactivate")
        print("   snippet desativado")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
