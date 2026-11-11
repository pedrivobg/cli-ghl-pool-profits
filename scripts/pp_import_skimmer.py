#!/usr/bin/env python3
"""Import a client's Skimmer customer export (.xlsx) as customers (Aqua Clear, 11/11).

    python3 scripts/pp_import_skimmer.py <xlsx> --loc <locationId> plan
    python3 scripts/pp_import_skimmer.py <xlsx> --loc <locationId> apply [--limit N]

POST services /contacts/upsert WITHOUT tags (matches existing contacts by phone/email; tags in the upsert REPLACE the
contact's tags), then POST /contacts/{id}/tags (adds): `skimmer import` + `existing customer` (Status Active) or
`former customer` (Inactive). Skimmer's own TagList (zip, RESIDENTIAL, SWEEP…) is NOT copied, so no tag-triggered
workflow fires. Check before importing that only "Contact Created -> add owner" (assign user) fires on new contacts.
Results in reports/import-<slug>-<stamp>.json.
"""
from __future__ import annotations

import argparse
import json
import time

import openpyxl

from _common import ROOT, load_dotenv

from cli_anything.gohighlevel.utils.agency import SERVICES, Agency


def rows(path: str) -> list[dict]:
    ws = openpyxl.load_workbook(path, read_only=True).worksheets[0]
    data = list(ws.iter_rows(values_only=True))
    return [dict(zip(data[0], r)) for r in data[1:] if any(r)]


def s(v) -> str:
    return str(v).strip() if v is not None else ""


def body(r: dict, loc: str) -> dict:
    phone = s(r.get("MobilePhone1")) or s(r.get("HomePhone")) or s(r.get("WorkPhone")) or s(r.get("MobilePhone2"))
    out = {"locationId": loc, "firstName": s(r.get("FirstName")), "lastName": s(r.get("LastName")), "phone": phone,
           "email": s(r.get("Email1")).lower(), "companyName": s(r.get("CompanyName")),
           "address1": s(r.get("LocationAddress")) or s(r.get("BillingAddress")),
           "city": s(r.get("LocationCity")) or s(r.get("BillingCity")),
           "state": s(r.get("LocationState")) or s(r.get("BillingState")),
           "postalCode": s(r.get("LocationZip")) or s(r.get("BillingZip")), "source": "Skimmer customer list"}
    if not out["firstName"] and not out["lastName"]:
        out["firstName"] = s(r.get("FullName"))
    return {k: v for k, v in out.items() if v}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("xlsx")
    ap.add_argument("--loc", required=True)
    ap.add_argument("mode", choices=["plan", "apply"])
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()
    load_dotenv()
    a = Agency()
    rs = rows(args.xlsx)
    if args.limit:
        rs = rs[: args.limit]
    out, ok = [], 0
    for r in rs:
        b = body(r, args.loc)
        tags = ["skimmer import", "existing customer" if s(r.get("Status")).lower() == "active" else "former customer"]
        if not (b.get("phone") or b.get("email")):
            out.append({"name": s(r.get("FullName")), "error": "no phone/email"})
            continue
        if args.mode == "plan":
            out.append({"body": b, "tags": tags})
            continue
        try:
            res = a.call("POST", SERVICES, "/contacts/upsert", body=b)
            cid = (res.get("contact") or {}).get("id")
            a.call("POST", SERVICES, f"/contacts/{cid}/tags", body={"tags": tags})
            out.append({"name": s(r.get("FullName")), "id": cid, "new": res.get("new"), "tags": tags})
            ok += 1
        except Exception as e:  # keep going, report at the end
            out.append({"name": s(r.get("FullName")), "error": str(e)[:300]})
        time.sleep(0.2)
    errs = [o for o in out if "error" in o]
    print(f"{len(rs)} rows, {ok} imported, {len(errs)} skipped/errors")
    for e in errs:
        print("  ", e)
    if args.mode == "plan":
        print(json.dumps(out[:2], indent=1))
    else:
        p = ROOT / "reports" / f"import-{args.loc}-{time.strftime('%Y%m%d-%H%M%S')}.json"
        p.parent.mkdir(exist_ok=True)
        p.write_text(json.dumps(out, indent=1))
        print(p)


if __name__ == "__main__":
    main()
