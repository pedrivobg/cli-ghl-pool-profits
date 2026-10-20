#!/usr/bin/env python3
"""Fill a new sub-account's custom values from its onboarding survey answers.

    ./.venv/bin/python scripts/pp_onboarding_fill.py --submission 6ad571b33f62d712d3cc45bb --loc InG8k1ETTG5uVwcAByj6
    ./.venv/bin/python scripts/pp_onboarding_fill.py --submission … --loc … --apply

New clients answer the onboarding survey (efErcbOr4GAKXzZ28J4S, "Pool Profits" sub-account); the survey
creates the sub-account and an automation fills its custom values. Poolheads (Frank, 20/10) answered
twice → two sub-accounts; the one kept (18/10) came without custom values. Same mapping the automation
used on the first one (its values = the 16/10 answers), except that unanswered fields stay empty
instead of the literal "None" it writes. --timezone also sets the location's time zone from the
survey's "Timezone" answer (sub-accounts are created in America/Sao_Paulo). Backup in backup/<slug>/.
"""
from __future__ import annotations

import argparse
import json
import re
import time

from _common import ROOT, load_dotenv, slugify

from cli_anything.gohighlevel.utils.agency import SERVICES, Agency

ONBOARDING_LOC = "wohRifObKPEykgu17LJu"  # "Pool Profits"


def phone(v: str) -> str:
    d = re.sub(r"\D", "", v or "")[-10:]
    return f"({d[:3]}) {d[3:6]}-{d[6:]}" if len(d) == 10 else (v or "")


def logo(v) -> str:
    files = list((v or {}).values()) if isinstance(v, dict) else []
    return files[0].get("url", "") if files else ""


def site(v: str) -> str:
    v = (v or "").strip()
    return v if not v or v.startswith("http") else "https://" + v


# custom value → answer (survey field ids are the onboarding survey's)
MAPPING = {
    "Friendly Business Name": lambda o: o.get("UUc0Lc3Bps8PZm8g5Y1I"),
    "Legal Business Name": lambda o: o.get("Er4JquP5hSCM8Jna1VOj"),
    "Owner First Name": lambda o: (o.get("full_name") or "").split(" ")[0],
    "Business Phone": lambda o: phone(o.get("phone")),
    "Business Email": lambda o: o.get("email"),
    "Client Domain Name": lambda o: site(o.get("website")),
    "Business Address": lambda o: ", ".join(x for x in (o.get("address"), o.get("city"), o.get("state"),
                                                        o.get("postal_code")) if x),
    "Google Review Link": lambda o: o.get("uj4lNw4lBYeEnxwbZLyH"),
    "Weekly Service Price": lambda o: o.get("Tm0PIoVNLJspqISncPe7"),
    "Chemical Only Price": lambda o: o.get("pJ890VRyYrbzGGygJeMe"),
    "Green to Clean Price": lambda o: o.get("AxCyaL12L44oWwd9eo1O"),
    "Logo URL": lambda o: logo(o.get("h7JQ7TiA6rRoZYpH1KkD")),
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--submission", required=True, help="survey submission id")
    parser.add_argument("--loc", required=True, help="sub-account to fill")
    parser.add_argument("--timezone", action="store_true", help="also set the location time zone")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    load_dotenv()
    a = Agency()
    subs = a.call("GET", SERVICES, "/surveys/submissions", params={"locationId": ONBOARDING_LOC, "limit": 100})
    sub = next((s for s in subs.get("submissions", []) if s["id"] == args.submission), None)
    if not sub:
        raise SystemExit(f"submissão {args.submission} não encontrada")
    answers = sub.get("others") or {}
    loc = a.location(args.loc)
    cvs = {c["name"]: c for c in a.custom_values(args.loc)}
    print(f"== {loc['name']} ({args.loc}) ← respostas de {sub.get('createdAt')}")
    changes = []
    for name, get in MAPPING.items():
        value = (get(answers) or "").strip()
        cur = (cvs.get(name) or {}).get("value") or ""
        if value and value != cur:
            changes.append((name, cur, value))
            print(f"   {name}: {cur!r} → {value!r}")
    tz = (answers.get("Timezone") or "").split(" ")[0]
    if args.timezone and tz and tz != loc.get("timezone"):
        print(f"   fuso: {loc.get('timezone')} → {tz}")
    if not args.apply:
        return 0
    bdir = ROOT / "backup" / slugify(loc["name"])
    bdir.mkdir(parents=True, exist_ok=True)
    (bdir / f"custom-values-{args.loc}-{time.strftime('%Y%m%d-%H%M%S')}.json").write_text(
        json.dumps({"location": loc, "customValues": list(cvs.values())}, ensure_ascii=False))
    for name, _, value in changes:
        if name in cvs:
            a.call("PUT", SERVICES, f"/locations/{args.loc}/customValues/{cvs[name]['id']}",
                   body={"name": name, "value": value})
        else:
            a.call("POST", SERVICES, f"/locations/{args.loc}/customValues", body={"name": name, "value": value})
    if args.timezone and tz and tz != loc.get("timezone"):
        a.call("PUT", SERVICES, f"/locations/{args.loc}", body={"timezone": tz})
    time.sleep(3)
    got = {c["name"]: c.get("value") for c in a.custom_values(args.loc)}
    bad = [n for n, _, v in changes if got.get(n) != v]
    tz_now = a.location(args.loc).get("timezone")
    print(f"   {'✓' if not bad else '✗ VERIFICAR ' + str(bad)} {len(changes) - len(bad)}/{len(changes)} custom values"
          + (f" · fuso {tz_now}" if args.timezone else ""))
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
