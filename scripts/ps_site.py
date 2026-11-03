#!/usr/bin/env python3
"""The Pool Shack: the 2 WPForms forms of thepoolshackarizona.com → the Pool Shack GHL (same design as Bluewater).

    set -a; . <scratchpad>/poolshack-wp.env; set +a     # PS_WP_URL, PS_WP_USER, PS_WP_APP_PASSWORD (Application Password)
    ./.venv/bin/python scripts/ps_site.py plan            # WordPress access, plugins, snippet state, GHL workflows, local PHP test
    ./.venv/bin/python scripts/ps_site.py ghl-test        # ZZ TEST copies (no card/alert), 1 POST per form, checked, deleted
    ./.venv/bin/python scripts/ps_site.py ghl-live        # "Website Form - <form>" published; URLs → backup/the-pool-shack/
    ./.venv/bin/python scripts/ps_site.py apply           # Code Snippets (installed if missing) + snippet active
    ./.venv/bin/python scripts/ps_site.py test            # each form's mapping run by the snippet on the site (dry)
    ./.venv/bin/python scripts/ps_site.py ghl-test --via-site   # site → GHL for real, into the ZZ TEST copies (no alerts)
    ./.venv/bin/python scripts/ps_site.py status          # last sends logged by the snippet
    ./.venv/bin/python scripts/ps_site.py off             # deactivate the snippet (the site goes back to WPForms e-mail only)
    ./.venv/bin/python scripts/ps_site.py render --out <file>   # code to paste by hand (Snippets → Add New)

Site: WPForms 440 "Request a Quote" (Name, Phone, Are You a New Customer?, Service Needed) and 443 "Main Contact /
Service Form" (Full Name, Phone, Email, Address, Postal Code, Service Needed, Message, consent). Nothing reached GHL.
One PHP snippet (site/poolshack/ps-ghl.php, hook wpforms_process_complete: after WPForms' own e-mails/confirmation)
posts each accepted submission as flat JSON to the form's inbound webhook:
    440  first_name, last_name, phone, new_customer, service, page
    443  first_name, last_name, phone, email, address, postal_code, service, message, page

GHL, one workflow per form ("Website Form - <form>", folder of "Website Form Fill To Pipeline"): create/update contact
→ custom fields that already exist in the account (Service Needed, Are You A New Customer, Message) → tags
`website form fill` + `new lead` → "Add to workflow" "Website Form Fill To Pipeline". That existing workflow is what the
GHL forms already set off (card in Pool Leads → New Lead, source "Website Form", tags new lead/form fill, SMS to Rob,
task); it listens to GHL form submissions only (no tag trigger: nothing in the account listens to `website form fill`
or `new lead`), so website leads go through it once, with the same card/alert as every other form and no second copy.
Test copies point the "Add to workflow" at a ZZ TEST target that only adds a tag, so Rob gets nothing.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import secrets
import subprocess
import sys
import time
import uuid

import requests

from _common import ROOT, load_dotenv

from cli_anything.gohighlevel.utils.agency import BACKEND, SERVICES, Agency

LOC = "3CozZ1NfujYWEPIYgzx0"
SNIPPET = "The Pool Shack forms → GHL (Pool Profits)"
PHP = ROOT / "site" / "poolshack" / "ps-ghl.php"
BDIR = ROOT / "backup" / "the-pool-shack"
URLS = BDIR / "webhook-urls.json"
KEY_FILE = BDIR / "site-key.txt"
HOOK = "https://services.leadconnectorhq.com/hooks/{loc}/webhook-trigger/{tid}"
W = "{{inboundWebhookRequest.%s}}"
EXISTING = "Website Form Fill To Pipeline"   # card + SMS/task to Rob (form_submission trigger, GHL forms)
TAGS = ["website form fill", "new lead"]
TEST_TAG = "zz test website form"
TEST_TARGET = "ZZ TEST Website Form Target"

FORMS = {  # WPForms id → workflow, contact fields, custom fields (payload key → field name in the account)
    "440": {"title": "Request a Quote", "hook": "QUOTE", "contact": ["first_name", "last_name", "phone"],
            "fields": {"service": "Service Needed", "new_customer": "Are You A New Customer"}},
    "443": {"title": "Main Contact / Service Form", "hook": "CONTACT",
            "contact": ["first_name", "last_name", "email", "phone", "address", "postal_code"],
            "fields": {"service": "Service Needed", "message": "Message"}},
}
STD = {"first_name": ("firstName", "First Name"), "last_name": ("lastName", "Last Name"), "email": ("email", "Email"),
       "phone": ("phone", "Phone"), "address": ("address1", "Street Address"), "postal_code": ("postalCode", "Postal Code")}
CONTACT_KEY = {"first_name": "firstName", "last_name": "lastName", "email": "email", "phone": "phone",
               "address": "address1", "postal_code": "postalCode"}

# Site-side input (field id → value, as WPForms has it) and the payload it must become (= what ghl-test posts).
SITE_SAMPLES = {
    "440": {"page": "/", "fields": {"1": "ZZ Test Quote", "2": "(480) 555-0140", "3": "Yes", "4": "Green Pool Clean"}},
    "443": {"page": "/contact/", "fields": {"1": "ZZ Test Contact Form", "2": "(480) 555-0143", "3": "ps-site-test@example.com",
                                            "4": "1 Test St, Scottsdale", "5": "85251", "6": "Equipment Repair",
                                            "7": "Test message from the website contact form (Pool Profits).",
                                            "8": "consent"}},
}
SAMPLES = {
    "440": {"first_name": "ZZ", "last_name": "Test Quote", "phone": "+14805550140", "new_customer": "Yes",
            "service": "Green Pool Clean", "page": "/"},
    "443": {"first_name": "ZZ", "last_name": "Test Contact Form", "phone": "+14805550143", "email": "ps-site-test@example.com",
            "address": "1 Test St, Scottsdale", "postal_code": "85251", "service": "Equipment Repair",
            "message": "Test message from the website contact form (Pool Profits).", "page": "/contact/"},
}


def name_of(fid: str, test: bool = False) -> str:
    return ("ZZ TEST " if test else "") + "Website Form - " + FORMS[fid]["title"]


def nid() -> str:
    return str(uuid.uuid4())


# ── GHL ──────────────────────────────────────────────────────────────────

def steps(fid: str, cf: dict[str, str], target: str, test: bool) -> list[dict]:
    f = FORMS[fid]
    chain = [
        {"name": "Create / update contact", "type": "create_update_contact", "attributes": {
            "type": "create_update_contact",
            "fields": [{"field": STD[k][0], "value": W % k, "title": STD[k][1], "type": "text"} for k in f["contact"]]}},
        {"name": "Save form answers", "type": "update_contact_field", "attributes": {
            "type": "update_contact_field", "actionType": "update_field_data",
            "fields": [{"field": cf[n], "value": W % k, "title": n, "type": "text", "date": ""} for k, n in f["fields"].items()]}},
        {"name": "Add Tag " + ", ".join(TAGS + ([TEST_TAG] if test else [])), "type": "add_contact_tag",
         "attributes": {"type": "add_contact_tag", "tags": TAGS + ([TEST_TAG] if test else [])}},
        {"name": f"Add to {TEST_TARGET if test else EXISTING}", "type": "add_to_workflow",
         "attributes": {"input_trigger_params": False, "type": "add_to_workflow", "workflow_id": target}},
    ]
    out, prev = [], None
    for i, s in enumerate(chain):
        s = dict(s, id=nid(), order=i)
        if prev:
            s["parentKey"] = prev["id"]
            prev["next"] = s["id"]
        out.append(s)
        prev = s
    return out


def put_flow(a: Agency, name: str, parent: str | None, tpl: list[dict], webhook: bool) -> tuple[str, str | None]:
    """Create (or update in place, with backup) a published workflow; with webhook=True, one inbound webhook trigger."""
    have = {w["name"]: w["id"] for w in a.workflows(LOC)}
    wid = have.get(name)
    if wid:
        live = a.workflow(LOC, wid)
        (BDIR / f"workflow-{wid}-{time.strftime('%Y%m%d-%H%M%S')}.json").write_text(json.dumps(live))
        version = live.get("version", 1)
    else:
        res = a.call("POST", BACKEND, f"/workflow/{LOC}", body={"name": name, "parentId": parent, "status": "draft"})
        wid, version = res.get("id") or res.get("_id"), 1
    a.call("PUT", BACKEND, f"/workflow/{LOC}/{wid}", body={
        "name": name, "version": version, "status": "published", "parentId": parent, "allowMultiple": True,
        "allowMultipleOpportunity": True, "workflowData": {"templates": tpl}})
    if not webhook:
        return wid, None
    hooks = [t for t in a.triggers(LOC, wid) if not t.get("deleted") and t["type"] == "inbound_webhook"]
    trig = {"type": "inbound_webhook", "name": "Website form (thepoolshackarizona.com)", "masterType": "highlevel",
            "schedule_config": {}, "conditions": [], "workflowId": wid, "workflow_id": wid, "location_id": LOC,
            "actions": [{"workflow_id": wid, "type": "add_to_workflow"}], "targetActionId": tpl[0]["id"]}
    if hooks:
        tid = hooks[0]["id"]
        (BDIR / f"trigger-{tid}-{time.strftime('%Y%m%d-%H%M%S')}.json").write_text(json.dumps(hooks[0]))
    else:
        tid = a.call("POST", BACKEND, f"/workflow/{LOC}/trigger", body=trig)["id"]
    a.call("PUT", BACKEND, f"/workflow/{LOC}/trigger/{tid}", body={**trig, "id": tid})
    return wid, tid


def drop_flow(a: Agency, wid: str) -> None:
    live = a.workflow(LOC, wid)
    a.call("PUT", BACKEND, f"/workflow/{LOC}/{wid}", body={"name": live["name"], "version": live.get("version", 1),
                                                         "status": "draft", "workflowData": live.get("workflowData") or {}})
    a.call("DELETE", BACKEND, f"/workflow/{LOC}/{wid}")


def ensure_tags(a: Agency, names: list[str]) -> None:
    have = {t["name"].lower() for t in a.tags(LOC)}
    for t in names:
        if t not in have:
            a.call("POST", BACKEND, f"/workflow/{LOC}/tags/create", body={"tag": t})
            print(f"   + tag {t}")


def find_contacts(a: Agency, sample: dict) -> list[dict]:
    out = {}
    for q in filter(None, [sample.get("email"), sample.get("phone", "")[-10:]]):
        for c in a.call("GET", SERVICES, "/contacts/", params={"locationId": LOC, "query": q}).get("contacts", []):
            if c.get("email") == sample.get("email") and sample.get("email") or (c.get("phone") or "") == sample.get("phone"):
                out[c["id"]] = c
    return list(out.values())


def cleanup(a: Agency) -> int:
    n = 0
    for s in SAMPLES.values():
        for c in find_contacts(a, s):
            for o in a.call("GET", SERVICES, "/opportunities/search",
                            params={"location_id": LOC, "contact_id": c["id"]}).get("opportunities", []):
                a.call("DELETE", SERVICES, f"/opportunities/{o['id']}")
            a.call("DELETE", SERVICES, f"/contacts/{c['id']}")
            n += 1
    return n


def check(a: Agency, fid: str, cf: dict[str, str], want_tags: set[str]) -> list[str]:
    sample = SAMPLES[fid]
    found = find_contacts(a, sample)
    if len(found) != 1:
        return [f"{len(found)} contatos achados"]
    c = a.call("GET", SERVICES, f"/contacts/{found[0]['id']}")["contact"]
    probs = [f"{CONTACT_KEY[k]} = {c.get(CONTACT_KEY[k])!r} (esperado {sample[k]!r})"
             for k in FORMS[fid]["contact"] if (c.get(CONTACT_KEY[k]) or "") != sample[k]]
    vals = {f["id"]: f.get("value") for f in c.get("customFields") or []}
    probs += [f"{n} = {vals.get(cf[n])!r} (esperado {sample[k]!r})"
              for k, n in FORMS[fid]["fields"].items() if str(vals.get(cf[n])) != sample[k]]
    missing = want_tags - set(c.get("tags") or [])
    if missing:
        probs.append(f"faltam tags {sorted(missing)}")
    opps = a.call("GET", SERVICES, "/opportunities/search", params={"location_id": LOC, "contact_id": c["id"]}).get("opportunities", [])
    if opps:
        probs.append(f"{len(opps)} card(s) na cópia de teste")
    return probs


def ghl_context(a: Agency) -> tuple[dict, dict, str | None]:
    if a.location(LOC)["name"] != "The Pool Shack":
        sys.exit("sub-conta errada")
    BDIR.mkdir(parents=True, exist_ok=True)
    cf = {c["name"]: c["id"] for c in a.custom_fields(LOC)}
    need = {n for f in FORMS.values() for n in f["fields"].values()}
    if need - set(cf):
        sys.exit(f"campos que não existem na conta: {sorted(need - set(cf))} (não crio campo)")
    flows = {w["name"]: w["id"] for w in a.workflows(LOC)}
    if EXISTING not in flows:
        sys.exit(f'"{EXISTING}" não existe na conta')
    parent = a.workflow(LOC, flows[EXISTING]).get("parentId")
    return cf, flows, parent


def ghl_test(a: Agency, via_site: bool) -> int:
    cf, flows, parent = ghl_context(a)
    print(f"   limpeza antes: {cleanup(a)} contato(s) de teste")
    target, _ = put_flow(a, TEST_TARGET, parent, [{
        "id": nid(), "order": 0, "name": "Add Tag " + TEST_TAG + " target", "type": "add_contact_tag",
        "attributes": {"type": "add_contact_tag", "tags": [TEST_TAG + " target"]}}], webhook=False)
    made, bad = {target: TEST_TARGET}, 0
    try:
        hooks = {}
        for fid in FORMS:
            wid, tid = put_flow(a, name_of(fid, True), parent, steps(fid, cf, target, True), webhook=True)
            made[wid], hooks[fid] = name_of(fid, True), tid
            print(f"   ✓ {name_of(fid, True)} publicado")
        time.sleep(5)
        site = Keyed() if via_site else None
        for fid in FORMS:
            if via_site:
                out = site("POST", "/ps-ghl/v1/test", json={"form_id": fid, **SITE_SAMPLES[fid], "send": True,
                                                            "hook": hooks[fid]})
                ok = out.get("data") == SAMPLES[fid] and out.get("sent") == 200
                bad += not ok
                print(f"   {'✓' if ok else '✗'} site → GHL {fid}: HTTP {out.get('sent')}"
                      + ("" if ok else f"\n      saiu    {out.get('data')}\n      esperado {SAMPLES[fid]}"))
            else:
                r = requests.post(HOOK.format(loc=LOC, tid=hooks[fid]), json=SAMPLES[fid], timeout=30)
                bad += r.status_code != 200
                print(f"   POST {fid}: HTTP {r.status_code}")
        time.sleep(45)
        for fid in FORMS:
            probs = check(a, fid, cf, set(TAGS) | {TEST_TAG, TEST_TAG + " target"})
            if probs and "contatos achados" in probs[0]:  # contact search lags after writes
                time.sleep(30)
                probs = check(a, fid, cf, set(TAGS) | {TEST_TAG, TEST_TAG + " target"})
            bad += bool(probs)
            print(f"   {'✓' if not probs else '✗'} GHL {name_of(fid)}" + (f": {probs}" if probs else
                  ": contato, campos, tags e 'Add to workflow' ok, sem card"))
    finally:
        print(f"   limpeza: {cleanup(a)} contato(s) apagado(s)")
        for wid, name in made.items():
            drop_flow(a, wid)
            print(f"   - {name} apagado")
        for t in a.tags(LOC):
            if t["name"].startswith(TEST_TAG):
                a.call("DELETE", SERVICES, f"/locations/{LOC}/tags/{t['id']}")
                print(f"   - tag {t['name']} apagada")
    return 1 if bad else 0


def ghl_live(a: Agency) -> int:
    cf, flows, parent = ghl_context(a)
    ensure_tags(a, TAGS)
    urls = json.loads(URLS.read_text()) if URLS.exists() else {}
    for fid in FORMS:
        _, tid = put_flow(a, name_of(fid), parent, steps(fid, cf, flows[EXISTING], False), webhook=True)
        urls[fid] = {"name": name_of(fid), "url": HOOK.format(loc=LOC, tid=tid)}
        print(f"   ✓ {name_of(fid)} publicado")
    URLS.write_text(json.dumps(urls, indent=1))
    print(f"   URLs → {URLS.relative_to(ROOT)}")
    return 0


# ── WordPress ────────────────────────────────────────────────────────────

def site_url() -> str:
    return (os.environ.get("PS_WP_URL") or "https://thepoolshackarizona.com").rstrip("/")


class WP:
    def __init__(self) -> None:
        user, pw = os.environ.get("PS_WP_USER"), os.environ.get("PS_WP_APP_PASSWORD")
        if not user or not pw:
            sys.exit("faltam PS_WP_USER / PS_WP_APP_PASSWORD (carregar poolshack-wp.env)")
        self.s = requests.Session()
        self.s.auth = (user, pw.replace(" ", ""))
        self.s.headers["User-Agent"] = "Mozilla/5.0 (Pool Profits ps_site)"

    def __call__(self, method: str, path: str, ok: tuple = (200, 201), **kw):
        r = self.s.request(method, site_url() + "/wp-json" + path, timeout=60, **kw)
        if r.status_code not in ok:
            raise SystemExit(f"{method} {path}: HTTP {r.status_code} {r.text[:300]}")
        return r.json() if r.text else None


def site_key() -> str:
    if not KEY_FILE.exists():
        BDIR.mkdir(parents=True, exist_ok=True)
        KEY_FILE.write_text(secrets.token_urlsafe(24))
        KEY_FILE.chmod(0o600)
    return KEY_FILE.read_text().strip()


class Keyed:
    """The snippet's own routes, authorised by ?key= (no WordPress login needed)."""

    def __call__(self, method: str, path: str, ok: tuple = (200, 201), **kw):
        kw.setdefault("params", {})["key"] = site_key()
        r = requests.request(method, site_url() + "/wp-json" + path, timeout=60,
                             headers={"User-Agent": "Mozilla/5.0 (Pool Profits ps_site)"}, **kw)
        if r.status_code not in ok:
            raise SystemExit(f"{method} {path}: HTTP {r.status_code} {r.text[:300]}")
        return r.json() if r.text else None


def render() -> str:
    if not URLS.exists():
        sys.exit("rodar ghl-live antes (backup/the-pool-shack/webhook-urls.json)")
    urls = json.loads(URLS.read_text())
    code = PHP.read_text().replace("__KEY__", site_key())
    for fid, f in FORMS.items():
        code = code.replace(f"__HOOK_{f['hook']}__", urls[fid]["url"].rsplit("/", 1)[1])
    if re.search(r"__HOOK_[A-Z]+__", code):
        sys.exit("sobrou placeholder no snippet")
    return code.removeprefix("<?php").lstrip("\n")


def local_test() -> bool:
    r = subprocess.run(["php", "-d", "error_log=/dev/null", str(PHP.parent / "test-ps-ghl.php")],
                       capture_output=True, text=True)
    print("   teste local do PHP: " + ("ok" if r.returncode == 0 else "FALHOU\n" + r.stdout + r.stderr))
    return r.returncode == 0


def snippet(wp: WP) -> dict | None:
    return next((s for s in wp("GET", "/code-snippets/v1/snippets") if s.get("name") == SNIPPET), None)


def plugins(wp: WP) -> dict[str, dict]:
    return {p["plugin"]: p for p in wp("GET", "/wp/v2/plugins")}


def site_ok() -> bool:
    r = requests.get(site_url() + "/", headers={"User-Agent": "Mozilla/5.0"}, timeout=60)
    return r.status_code == 200 and all(f"wpforms-form-{fid}" in r.text for fid in FORMS)


def run_tests(site) -> int:
    bad = 0
    for fid, body in SITE_SAMPLES.items():
        out = site("POST", "/ps-ghl/v1/test", json={"form_id": fid, **body})
        ok = out.get("data") == SAMPLES[fid]
        bad += not ok
        print(f"   {'✓' if ok else '✗'} {fid} {FORMS[fid]['title']} (mapeamento no site)"
              + ("" if ok else f"\n      saiu    {out.get('data')}\n      esperado {SAMPLES[fid]}"))
    return bad


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("mode", choices=["plan", "ghl-test", "ghl-live", "apply", "test", "status", "off", "render"])
    parser.add_argument("--via-site", action="store_true", help="ghl-test: post through the snippet on the site")
    parser.add_argument("--out", help="render: file to write the code to")
    args = parser.parse_args()
    load_dotenv()
    if args.mode in ("ghl-test", "ghl-live"):
        a = Agency()
        return ghl_test(a, args.via_site) if args.mode == "ghl-test" else ghl_live(a)
    if args.mode == "render":
        if not local_test():
            return 1
        open(args.out, "w").write(render() + "\n")
        print(f"   código para colar → {args.out}")
        return 0
    if args.mode in ("test", "status"):
        site = Keyed()
        st = site("GET", "/ps-ghl/v1/status")
        print(f"== {site_url()} · snippet v{st['version']} no ar")
        if args.mode == "status":
            for when, form, kind, who, code in st["log"]:
                print(f"   {when} {form} {kind:4} {code} {who}")
            return 0
        return 1 if run_tests(site) else 0

    wp = WP()
    me = wp("GET", "/wp/v2/users/me", params={"context": "edit"})
    print(f"== {site_url()} · usuário {me.get('username')} ({', '.join(me.get('roles') or [])})")
    if not (me.get("capabilities") or {}).get("manage_options"):
        sys.exit("o usuário precisa ser Administrator")

    if args.mode == "plan":
        have = plugins(wp)
        for k in ("wpforms/", "code-snippets/"):
            p = next((p for key, p in have.items() if key.startswith(k)), None)
            print(f"   {k.rstrip('/')}: {p['status'] + ' ' + p.get('version', '') if p else 'não instalado'}")
        cs = next((p for k, p in have.items() if k.startswith("code-snippets/")), None)
        if cs and cs["status"] == "active":
            s = snippet(wp)
            print(f"   snippet: {('ativo' if s.get('active') else 'inativo') if s else 'não existe'}")
        for f in wp("GET", "/wpforms/v1/forms"):
            print(f"   WPForms {f['ID']} {f['post_title']}: "
                  + ", ".join(f"{k}:{v['type']}" for k, v in json.loads(f["post_content"])["fields"].items()))
        a = Agency()
        flows = {w["name"] for w in a.workflows(LOC)}
        for fid in FORMS:
            print(f"   GHL {name_of(fid)}: {'existe' if name_of(fid) in flows else 'não existe (ghl-live cria)'}")
            print("      " + " → ".join(s["name"] for s in steps(fid, {n: f"<{n}>" for n in FORMS[fid]['fields'].values()},
                                                                   "<" + EXISTING + ">", False)))
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
                "desc": "Sends each WPForms submission (forms 440 and 443) to its webhook in The Pool Shack GHL, after "
                        "WPForms' own e-mails. Source: pedrivobg/cli-ghl-pool-profits site/poolshack/ps-ghl.php. Pool Profits."}
        old = snippet(wp)
        if old:
            (BDIR / f"wp-snippet-{old['id']}-{time.strftime('%Y%m%d-%H%M%S')}.json").write_text(json.dumps(old))
            made = wp("PUT", f"/code-snippets/v1/snippets/{old['id']}", json=body)
        else:
            made = wp("POST", "/code-snippets/v1/snippets", json=body)
        if made.get("code_error"):
            wp("POST", f"/code-snippets/v1/snippets/{made['id']}/deactivate")
            sys.exit(f"erro no snippet, desativado: {made['code_error']}")
        if not made.get("active"):
            sys.exit(f"snippet #{made['id']} gravado mas não ativo: {json.dumps(made)[:300]}")
        print(f"   ✓ snippet #{made['id']} {'atualizado' if old else 'criado'} e ativo")
        if not site_ok():
            wp("POST", f"/code-snippets/v1/snippets/{made['id']}/deactivate")
            sys.exit("a home não abriu normal (ou sem os 2 forms) depois do snippet: desativado")
        st = Keyed()("GET", "/ps-ghl/v1/status")
        print(f"   ✓ site no ar com os 2 forms, snippet v{st['version']} respondendo")
        return 1 if run_tests(wp) else 0

    s = snippet(wp)  # off
    if s and s.get("active"):
        wp("POST", f"/code-snippets/v1/snippets/{s['id']}/deactivate")
        print("   snippet desativado")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
