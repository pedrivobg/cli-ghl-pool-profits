#!/usr/bin/env python3
"""Import the CSV made by pp_import_skimmer.py (<stem>-ghl.csv) into one sub-account, sending nothing.

    python3 scripts/pp_import_apply.py <customers-ghl.csv> --only "West Coast Pool Care"           # plan
    python3 scripts/pp_import_apply.py <customers-ghl.csv> --only "West Coast Pool Care" --apply

Per row: POST services /contacts/upsert WITHOUT tags (matches by phone/e-mail; tags in upsert REPLACE the contact's)
→ POST /contacts/{id}/tags with the Tags column → POST /contacts/{id}/notes with Notes + additional phones/e-mails.
Before --apply, check that no published workflow fires on these tags or on contact created (except an owner-assign
step) — the plan lists the account's published contact_tag / contact_created triggers to compare.
Created ids → backup/<slug>/skimmer-import-<stamp>.json (to undo: delete those ids where "new" is true).
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import os
import sys
import time

from _common import ROOT, Agency, load_dotenv
from cli_anything.gohighlevel.utils.agency import SERVICES, match_location, slugify


def body_of(r: dict, loc: str) -> dict:
    b = {"locationId": loc, "firstName": r["First Name"], "lastName": r["Last Name"], "companyName": r["Company Name"],
         "phone": r["Phone"], "email": r["Email"], "address1": r["Address"], "city": r["City"], "state": r["State"],
         "postalCode": r["Postal Code"], "source": r.get("Source") or "skimmer import"}
    return {k: v for k, v in b.items() if v}


def note_of(r: dict) -> str:
    parts = [r.get("Notes") or ""]
    if r.get("Additional Phones"):
        parts.append(f"Other phones: {r['Additional Phones']}")
    if r.get("Additional Emails"):
        parts.append(f"Other e-mails: {r['Additional Emails']}")
    return "\n".join(p for p in parts if p).strip()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv")
    ap.add_argument("--only", required=True)
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    load_dotenv()
    a = Agency()
    loc = match_location(a.locations(), args.only)
    if not loc:
        sys.exit(f"not found: {args.only}")
    rows = list(csv.DictReader(open(args.csv, newline="", encoding="utf-8-sig")))
    tags = sorted({t.strip() for r in rows for t in r["Tags"].split(",") if t.strip()})
    print(f"== {loc['name']}: {len(rows)} rows · tags {tags}")
    if not args.apply:
        for w in a.workflows(loc["id"]):
            if w.get("status") != "published":
                continue
            for t in a.triggers(loc["id"], w["id"]):
                if t.get("type") in ("contact_tag", "contact_created"):
                    print(f"   trigger {t['type']:16} {w['name']}: {json.dumps(t.get('conditions'))[:160]}")
        for r in rows[:3]:
            print("  ", json.dumps(body_of(r, loc["id"])), "|", r["Tags"], "|", note_of(r)[:80])
        return 0
    done = []
    for i, r in enumerate(rows, 1):
        try:
            res = a.call("POST", SERVICES, "/contacts/upsert", body=body_of(r, loc["id"]))
            cid = (res.get("contact") or {}).get("id")
            if not cid:
                raise RuntimeError(json.dumps(res)[:200])
            rt = [t.strip() for t in r["Tags"].split(",") if t.strip()]
            a.call("POST", SERVICES, f"/contacts/{cid}/tags", body={"tags": rt})
            n = note_of(r)
            if n:
                a.call("POST", SERVICES, f"/contacts/{cid}/notes", body={"body": n})
            done.append({"row": i, "id": cid, "new": bool(res.get("new")), "name": f"{r['First Name']} {r['Last Name']}"})
        except Exception as e:  # noqa: BLE001
            done.append({"row": i, "error": str(e)[:200], "name": f"{r['First Name']} {r['Last Name']}"})
        time.sleep(0.2)
    d = os.path.join(ROOT, "backup", slugify(loc["name"]))
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, f"skimmer-import-{dt.datetime.now():%Y%m%d-%H%M}.json")
    json.dump(done, open(p, "w"), indent=1)
    err = [x for x in done if x.get("error")]
    print(f"   {sum(1 for x in done if x.get('new'))} new, {sum(1 for x in done if x.get('id') and not x.get('new'))} "
          f"existing, {len(err)} errors → {p}")
    for x in err:
        print("   !!", x)
    return 1 if err else 0


if __name__ == "__main__":
    raise SystemExit(main())
