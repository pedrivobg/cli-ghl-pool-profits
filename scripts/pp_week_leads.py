#!/usr/bin/env python3
"""Weekly audit: real leads since a date that have NO card (opportunity). Read-only.

    python3 scripts/pp_week_leads.py 2026-11-19 [--only NAME]
    GHL_AGENCY=poolduck python3 scripts/pp_week_leads.py 2026-11-19

Per client sub-account: contacts added since the date with tag "new lead" (the V9 lead flows add it) and no
spam/dnd/existing-customer tag; prints those without any opportunity, with their source tags.
"""
from __future__ import annotations

import argparse
import datetime as dt
import time

from _common import Agency, load_dotenv
from cli_anything.gohighlevel.utils.agency import SERVICES

SKIP_ACC = ("test", "snapshot", "sample", "master", "billing only", "portal", "franchising", "hq", "marketplace",
            "pool profits (sales)", "pool profits")
SKIP_TAGS = {"spam", "spam likely", "dnd", "existing customer", "zz test", "pre-snapshot"}


def retry(f, *a, **k):
    for i in range(4):
        try:
            return f(*a, **k)
        except Exception:  # noqa: BLE001
            if i == 3:
                raise
            time.sleep(3)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("since")
    ap.add_argument("--only")
    args = ap.parse_args()
    load_dotenv()
    a = Agency()
    since_ms = int(dt.datetime.fromisoformat(args.since).replace(tzinfo=dt.timezone.utc).timestamp() * 1000)
    total = missing = 0
    for loc in sorted(a.locations(), key=lambda x: x["name"]):
        n, lid = loc["name"], loc["id"]
        low = n.lower()
        if args.only and args.only.lower() not in low:
            continue
        if not args.only and (low in SKIP_ACC or any(low.startswith(s) or f" {s}" in low for s in SKIP_ACC[:-1])):
            continue
        leads, page = [], 1
        while True:
            r = retry(a.call, "POST", SERVICES, "/contacts/search", body={
                "locationId": lid, "pageLimit": 100, "page": page,
                "sort": [{"field": "date_added", "direction": "desc"}]})
            cs = r.get("contacts", [])
            def ms(c):
                d = c.get("dateAdded")
                return d if isinstance(d, int) else int(dt.datetime.fromisoformat(str(d).replace("Z", "+00:00")).timestamp() * 1000)
            new = [c for c in cs if ms(c) >= since_ms]
            leads += new
            if len(cs) < 100 or len(new) < len(cs) or page >= 10:
                break
            page += 1
        leads = [c for c in leads if "new lead" in (c.get("tags") or []) and not (set(c.get("tags") or []) & SKIP_TAGS)]
        if not leads:
            continue
        bad = []
        for c in leads:
            o = retry(a.call, "GET", SERVICES, "/opportunities/search", params={"location_id": lid, "contact_id": c["id"]})
            if not o.get("opportunities"):
                bad.append(c)
        total += len(leads)
        missing += len(bad)
        print(f"{'!!' if bad else 'ok'} {n}: {len(leads)} leads, {len(bad)} sem card")
        for c in bad:
            print(f"     - {c['id']} {(c.get('firstName') or '')[:12]} {sorted(c.get('tags') or [])}")
    print(f"TOTAL {total} leads, {missing} sem card")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
