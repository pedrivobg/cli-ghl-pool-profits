#!/usr/bin/env python3
"""Pool Duck franchise → V9, phase 1 (Pedro 11/11; plan in docs/poolduck-snapshot-plan.md). Nothing turned on.

Run with the Pool Duck token:  GHL_AGENCY=poolduck python3 scripts/pd_v9_phase1.py --loc <id> [--apply]

  1. tags: "pre-snapshot" on EVERY existing contact, "existing customer" on clients (QuickBooks contacts or client tags).
     Only tags are added (POST /contacts/{id}/tags); no published workflow of LWR/ODE listens to these tags (checked 11/11).
  2. pipeline "Pool Leads" (model stages) created next to theirs; "Leads --> Sales Pipeline" and its cards untouched.
  3. pp_mirror --model-dir dump/southern-pool-outdoors --keep-status --new-only --apply: fields, templates, tags and every
     V9 workflow the account lacks, ALL as draft; their workflows/templates with the same name are left alone.
  4. V9 custom values that are missing, filled from the account's own ones (Known As Business Name → Friendly Business Name,
     …); prices / owner first name stay empty (Frank).
The guards on the V9 triggers ("Doesn't Have Tag: pre-snapshot") go in at publication time, phase 2.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(__file__))
from _common import load_dotenv  # noqa: E402

load_dotenv()
from cli_anything.gohighlevel.utils.agency import BACKEND, SERVICES, Agency, slugify  # noqa: E402

GUARD, CUSTOMER = "pre-snapshot", "existing customer"
CLIENT_TAGS = {"active residential client", "new residential client", "pool duck customer", "turtle rock"}
MODEL = os.path.join(ROOT, "dump", "southern-pool-outdoors")
CV_MAP = {  # V9 name → the account's own custom value
    "Friendly Business Name": "Known As Business Name", "Business Phone": "CRM Phone Number",
    "Website Phone Number": "CRM Phone Number", "Business Email": "From Email", "Logo URL": "Logo Image URL",
    "Service Area": "Pool Service Area", "Client Domain Name": "Domain", "A2P Domain": "Domain",
    "Privacy Policy": "A2P Privacy Page URL", "Terms of Use": "A2P- Terms of Service URL",
    "Google Review Link": "Public Review Link", "A2P Verification Number": "A2P - LC Phone Number",
    "Legal Business Name": "A2P - Legal Business Name",
}


def contacts(a: Agency, loc: str) -> list[dict]:
    out, page = [], 1
    while True:
        r = a.call("POST", SERVICES, "/contacts/search", body={"locationId": loc, "pageLimit": 100, "page": page})
        out += r.get("contacts", [])
        if len(r.get("contacts", [])) < 100:
            return out
        page += 1


def is_client(c: dict) -> bool:
    tags = {t.lower() for t in c.get("tags") or []}
    return bool(tags & CLIENT_TAGS) or (c.get("source") or "").lower() == "quickbooks" or bool(c.get("qboId"))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--loc", required=True)
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    if os.environ.get("GHL_AGENCY", "").lower() != "poolduck":
        sys.exit("run with GHL_AGENCY=poolduck")
    a = Agency()
    loc = a.location(args.loc)
    name, slug = loc["name"], slugify(loc["name"])
    bdir = os.path.join(ROOT, "backup", f"poolduck-{slug}")
    os.makedirs(bdir, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    print(f"== {name} ({args.loc}) {'APPLY' if args.apply else 'plan'}")

    # 1. guard tags
    cs = contacts(a, args.loc)
    need_guard = [c for c in cs if GUARD not in [t.lower() for t in c.get("tags") or []]]
    need_cust = [c for c in cs if is_client(c) and CUSTOMER not in [t.lower() for t in c.get("tags") or []]]
    print(f"   contacts {len(cs)}: +'{GUARD}' on {len(need_guard)}, +'{CUSTOMER}' on {len(need_cust)} clients")
    if args.apply:
        json.dump([{"id": c["id"], "tags": c.get("tags")} for c in cs], open(os.path.join(bdir, f"contact-tags-{stamp}.json"), "w"))
        for tag in (GUARD, CUSTOMER):
            try:
                a.call("POST", BACKEND, f"/workflow/{args.loc}/tags/create", body={"tag": tag})
            except Exception:  # noqa: BLE001 — already exists
                pass
        cust_ids = {c["id"] for c in need_cust}
        for i, c in enumerate(cs):
            add = ([GUARD] if c in need_guard else []) + ([CUSTOMER] if c["id"] in cust_ids else [])
            if add:
                a.call("POST", SERVICES, f"/contacts/{c['id']}/tags", body={"tags": add})
        left = [c for c in contacts(a, args.loc) if GUARD not in [t.lower() for t in c.get("tags") or []]]
        print(f"   ✓ tagged; contacts still without '{GUARD}': {len(left)}")

    # 2. Pool Leads pipeline next to theirs
    pipes = a.pipelines(args.loc)
    if any("pool leads" in (p.get("name") or "").lower() for p in pipes):
        print("   pipeline Pool Leads: already there")
    else:
        stages = [{"name": s["name"], "position": i, "showInFunnel": s.get("showInFunnel", True),
                   "showInPieChart": s.get("showInPieChart", True)}
                  for i, s in enumerate(json.load(open(os.path.join(MODEL, "pipelines.json")))[0]["stages"])]
        print(f"   pipeline Pool Leads: create ({len(stages)} stages); theirs: {[p['name'] for p in pipes]} untouched")
        if args.apply:
            r = a.call("POST", SERVICES, "/opportunities/pipelines",
                       body={"locationId": args.loc, "name": "Pool Leads", "stages": stages})
            print(f"   ✓ {json.dumps(r)[:160]}")

    # 3. V9 workflows / fields / templates, all draft (re-dump first so the mirror sees the new pipeline)
    if args.apply:
        subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "pp_dump.py"), "--only", name], cwd=ROOT,
                       capture_output=True, text=True)
    cmd = [sys.executable, os.path.join(ROOT, "scripts", "pp_mirror.py"), "--target", name, "--model-dir",
           "dump/southern-pool-outdoors", "--new-only"] + (["--apply"] if args.apply else [])
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    with open(os.path.join(bdir, f"mirror-{stamp}.log"), "w") as fh:
        fh.write(r.stdout + r.stderr)
    for line in r.stdout.splitlines():
        if any(k in line for k in ("cria workflow", "status →", "já existe", "⚠", "◆", "=====", "cria campo", "cria '")):
            print("   " + line.strip())
    if r.returncode:
        print("   MIRROR ERROR:", r.stderr[-800:])

    # 4. missing V9 custom values, filled from the account's own
    have = {c["name"]: c for c in a.custom_values(args.loc)}
    for c in json.load(open(os.path.join(MODEL, "custom_values.json"))):
        if c["name"] in have:
            continue
        src = CV_MAP.get(c["name"])
        val = (have.get(src) or {}).get("value") or "" if src else ""
        if c["name"] == "Google Review Link" and not val and loc.get("googlePlacesId"):
            val = f"https://search.google.com/local/writereview?placeid={loc['googlePlacesId']}"
        print(f"   custom value '{c['name']}' ← {src or '—'}: {str(val)[:60] or '(empty, Frank)'}")
        if args.apply:
            a.call("POST", SERVICES, f"/locations/{args.loc}/customValues", body={"name": c["name"], "value": val})

    if args.apply:  # proof that nothing of theirs changed status and nothing V9 is live
        subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "pp_dump.py"), "--only", name], cwd=ROOT,
                       capture_output=True, text=True)
        print(f"   backup and logs in {bdir}")


if __name__ == "__main__":
    main()
