#!/usr/bin/env python3
"""Sub-accounts created in America/Sao_Paulo → the client's own time zone (20/10).

    ./.venv/bin/python scripts/pp_timezone_fix.py            # plan
    ./.venv/bin/python scripts/pp_timezone_fix.py --apply

The onboarding creates sub-accounts in America/Sao_Paulo (the agency's default), so business hours
and workflow time windows ("09:00–17:00", account time zone) run 2–4 h early for US clients. Time
zone = the client's answer in the onboarding survey (matched by e-mail), else by state. Skips the
snapshot account. Backup of each location in backup/<slug>/.
"""
from __future__ import annotations

import argparse
import json
import time

from _common import ROOT, load_dotenv, slugify

from cli_anything.gohighlevel.utils.agency import SERVICES, Agency

ONBOARDING_LOC = "wohRifObKPEykgu17LJu"
SKIP = {"Kvdj7o189zlS3caaCNuX",  # Snapshot Pool Profits
        "PeUynYCMm8e6PJMy785O"}  # Poolheads duplicate (first survey, 16/10) — to be deleted
OVERRIDE = {"Sk6BacCVS1fHPfcuAmOU": "America/New_York"}  # Cleverblu: survey said Chicago; Altamonte Springs FL, 407
STATE_TZ = {"AZ": "America/Phoenix", "ARIZONA": "America/Phoenix", "NC": "America/New_York",
            "FL": "America/New_York", "FLORIDA": "America/New_York", "TN": "America/Chicago",
            "IL": "America/Chicago", "TX": "America/Chicago", "TEXAS": "America/Chicago"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    load_dotenv()
    a = Agency()
    subs = a.call("GET", SERVICES, "/surveys/submissions", params={"locationId": ONBOARDING_LOC, "limit": 100})
    by_email = {}
    for s in sorted(subs.get("submissions", []), key=lambda s: s.get("createdAt") or ""):
        o = s.get("others") or {}
        if o.get("email") and o.get("Timezone"):
            by_email[o["email"].lower()] = o["Timezone"].split(" ")[0]
    bad = 0
    for loc in a.locations():
        if loc.get("timezone") != "America/Sao_Paulo" or loc["id"] in SKIP:
            continue
        tz = OVERRIDE.get(loc["id"]) or by_email.get((loc.get("email") or "").lower()) or \
            STATE_TZ.get((loc.get("state") or "").strip().upper())
        src = "endereço" if loc["id"] in OVERRIDE else "survey" if (loc.get("email") or "").lower() in by_email else "estado"
        print(f"   {loc['name'][:32]:32} {loc.get('state') or '?':10} {loc['timezone']} → {tz or '??'} ({src})")
        if not args.apply or not tz:
            continue
        bdir = ROOT / "backup" / slugify(loc["name"])
        bdir.mkdir(parents=True, exist_ok=True)
        full = a.location(loc["id"])
        (bdir / f"location-{loc['id']}-{time.strftime('%Y%m%d-%H%M%S')}.json").write_text(json.dumps(full))
        a.call("PUT", SERVICES, f"/locations/{loc['id']}", body={"timezone": tz})
        time.sleep(1)
        ok = a.location(loc["id"]).get("timezone") == tz
        bad += not ok
        print(f"      {'✓' if ok else '✗ VERIFICAR'}")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
