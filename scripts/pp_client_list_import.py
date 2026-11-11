#!/usr/bin/env python3
"""Client list (CSV) → contacts in one sub-account, tagged as customers (Frank 11/11: Bahama Blue + Smart Chem).

    python3 scripts/pp_client_list_import.py <list.csv> --only "Bahama Blue Pool & Spa"            # plan
    python3 scripts/pp_client_list_import.py <list.csv> --only "Bahama Blue Pool & Spa" --apply

Columns by header: "Customers" (full name; last word = last name) or "First Name"/"Last Name"; Phone; Email; Address;
City; State; Zip/Postal Code; Business Name; Status (blank / "NEW … START" = active, "not active"/"inactive" = past).
Phone → +1 E.164 (invalid → row skipped, listed); ALL CAPS → Title Case ("70TH" → "70th"). Rows without a real phone
and e-mail, or named "test", are skipped.
Write: POST services /contacts/upsert WITHOUT tags (matches by phone/e-mail; tags in upsert REPLACE the contact's), then
POST /contacts/{id}/tags: active → `active client`, `existing customer`; past → `past client`; all → `client list import`.
Before applying: no published workflow of the account may fire on these tags / on contact created except "Contact
Created -> add owner" (assigns the owner, sends nothing). Created ids → backup/<slug>/client-list-import-<stamp>.json.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
from cli_anything.gohighlevel.utils.agency import SERVICES, Agency, match_location, slugify  # noqa: E402

IMPORT_TAG = "client list import"
ACTIVE_TAGS = ["active client", "existing customer"]
PAST_TAGS = ["past client"]


def squash(s) -> str:
    return re.sub(r"\s+", " ", str(s or "").replace("\xa0", " ")).strip()


def phone(s: str) -> str:
    d = re.sub(r"\D", "", s or "")
    if len(d) == 10 and d[0] not in "01":
        return "+1" + d
    if len(d) == 11 and d[0] == "1" and d[1] not in "01":
        return "+" + d
    return ""


def title(s: str) -> str:
    s = squash(s)
    if not s.isupper():
        return s
    return " ".join(w.lower() if re.fullmatch(r"\d+(ST|ND|RD|TH)", w) else w.capitalize() for w in s.split())


def pick(row: dict, *names: str) -> str:
    low = {k.strip().lower(): v for k, v in row.items() if k}
    for n in names:
        if low.get(n):
            return squash(low[n])
    return ""


def build(rows: list[dict], loc: str) -> tuple[list[dict], list[str]]:
    out, skipped, seen = [], [], set()
    for i, r in enumerate(rows, start=2):
        full = pick(r, "customers", "customer", "name")
        if full:
            parts = title(full).split()
            first, last = " ".join(parts[:-1]) or parts[0], (parts[-1] if len(parts) > 1 else "")
        else:
            first, last = title(pick(r, "first name")), title(pick(r, "last name"))
        raw_phone = pick(r, "phone")
        ph, em = phone(raw_phone), pick(r, "email").lower()
        name = f"{first} {last}".strip()
        if "test" in name.lower():
            skipped.append(f"line {i}: {name!r} (test contact)")
            continue
        if raw_phone and not ph:
            skipped.append(f"line {i}: {name or '(no name)'} invalid phone {raw_phone!r}" + (" — kept by e-mail" if em else ""))
            if not em:
                continue
        if not ph and not em:
            skipped.append(f"line {i}: {name or '(no name)'} no phone/e-mail")
            continue
        key = ph or em
        if key in seen:
            skipped.append(f"line {i}: {name} duplicate of {key}")
            continue
        seen.add(key)
        status = pick(r, "status").lower()
        past = "not active" in status or "inactive" in status
        body = {"locationId": loc, "firstName": first, "lastName": last, "phone": ph, "email": em,
                "companyName": pick(r, "business name", "company"), "address1": title(pick(r, "address")).rstrip(", "),
                "city": title(pick(r, "city")), "state": pick(r, "state").upper(),
                "postalCode": pick(r, "zip", "postal code"), "source": "Client list (11/11)"}
        if body["address1"] or body["city"]:
            body["country"] = "US"
        body = {k: v for k, v in body.items() if v}
        out.append({"line": i, "body": body, "tags": [IMPORT_TAG] + (PAST_TAGS if past else ACTIVE_TAGS),
                    "status": status})
    return out, skipped


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    ap.add_argument("--only", required=True)
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    a = Agency()
    loc = match_location(a.locations(), args.only)
    if not loc:
        sys.exit(f"not found: {args.only}")
    with open(args.csv, newline="", encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))
    items, skipped = build(rows, loc["id"])
    act = sum(1 for x in items if "active client" in x["tags"])
    print(f"== {loc['name']}: {len(rows)} rows → {len(items)} contacts ({act} active, {len(items) - act} past), "
          f"{len(skipped)} skipped")
    for s in skipped:
        print("   skip", s)
    if not args.apply:
        for x in items[:5]:
            print("  ", json.dumps(x["body"]), x["tags"])
        return
    done = []
    for x in items:
        r = a.call("POST", SERVICES, "/contacts/upsert", body=x["body"])
        c = r.get("contact") or {}
        cid = c.get("id")
        if not cid:
            done.append({"line": x["line"], "error": json.dumps(r)[:200]})
            continue
        a.call("POST", SERVICES, f"/contacts/{cid}/tags", body={"tags": x["tags"]})
        done.append({"line": x["line"], "id": cid, "new": bool(r.get("new")), "tags": x["tags"]})
    folder = os.path.join(ROOT, "backup", slugify(loc["name"]))
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, f"client-list-import-{dt.datetime.now():%Y%m%d-%H%M}.json")
    with open(path, "w") as fh:
        json.dump(done, fh, indent=1)
    print(f"   {sum(1 for d in done if d.get('new'))} new, {sum(1 for d in done if d.get('id') and not d.get('new'))} "
          f"existing, {sum(1 for d in done if d.get('error'))} errors → {path}")


if __name__ == "__main__":
    main()
