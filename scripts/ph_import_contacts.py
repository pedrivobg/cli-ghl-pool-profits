#!/usr/bin/env python3
"""Poolheads: contacts exported from the old GHL account → the new one (Frank's CSV, 27/10).

    ./.venv/bin/python scripts/ph_import_contacts.py <csv> plan
    ./.venv/bin/python scripts/ph_import_contacts.py <csv> apply [--limit N]

Columns: Contact Id, First Name, Last Name, Phone, Email, Business Name, Created, Last Activity, Tags.
POST services /contacts/upsert **without tags** (matches an existing contact by phone/email: no duplicates of the
30-odd contacts the new account already has; upsert with `tags` REPLACES the contact's tags — erased a caller's
`new lead`/`inbound call` in the first test, restored), then POST /contacts/{id}/tags (adds). Tags: the old ones + `old account import`; old service tags (weekly service, full service,
repair-only, card on file…) also get `existing customer`, so lead automations treat them as customers. Before importing:
no published workflow of the new account fires on these tags (only "Contact Created -> add owner" runs: assigns Felipe,
sends nothing). Results (old id → new id / error) in reports/poolheads-import-<stamp>.json.
"""
from __future__ import annotations

import argparse
import csv
import json
import time

from _common import ROOT, load_dotenv

from cli_anything.gohighlevel.utils.agency import SERVICES, Agency

LOC = "PeUynYCMm8e6PJMy785O"
IMPORT_TAG = "old account import"
CUSTOMER_TAGS = {"weekly service", "full service", "repair-only", "card on file", "poolrx", "management plan", "seasonal",
                 "filter wash", "pool recovery", "leak repair", "tenant", "rental", "unoccupied"}


def body(r: dict) -> dict:
    tags = [t.strip() for t in (r.get("Tags") or "").split(",") if t.strip()]
    tags.append(IMPORT_TAG)
    if CUSTOMER_TAGS & set(tags):
        tags.append("existing customer")
    out = {"locationId": LOC, "firstName": (r.get("First Name") or "").strip(), "lastName": (r.get("Last Name") or "").strip(),
           "phone": (r.get("Phone") or "").strip(), "email": (r.get("Email") or "").strip().lower(),
           "companyName": (r.get("Business Name") or "").strip(), "tags": tags, "source": "Old Poolheads account"}
    return {k: v for k, v in out.items() if v}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("csv")
    parser.add_argument("mode", choices=["plan", "apply"])
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()
    rows = list(csv.DictReader(open(args.csv, encoding="utf-8-sig")))
    rows = [r for r in rows if (r.get("Phone") or r.get("Email") or "").strip()]
    if args.limit:
        rows = rows[:args.limit]
    cust = sum(1 for r in rows if "existing customer" in body(r)["tags"])
    print(f"   {len(rows)} contatos com telefone ou e-mail · {cust} com tag de serviço → existing customer")
    if args.mode == "plan":
        return 0
    load_dotenv()
    a = Agency()
    if a.location(LOC)["name"].lower().find("poolheads") < 0:
        raise SystemExit("sub-conta errada")
    out, new, upd, bad = {}, 0, 0, 0
    for i, r in enumerate(rows, 1):
        for attempt in range(4):
            try:
                b = body(r)
                tags = b.pop("tags")
                res = a.call("POST", SERVICES, "/contacts/upsert", body=b)
                cid = (res.get("contact") or {}).get("id")
                a.call("POST", SERVICES, f"/contacts/{cid}/tags", body={"tags": tags})
                out[r["Contact Id"]] = cid
                new += bool(res.get("new"))
                upd += not res.get("new")
                break
            except Exception as e:  # noqa: BLE001
                if attempt == 3 or "429" not in str(e) and "503" not in str(e):
                    out[r["Contact Id"]] = f"ERRO {str(e)[:200]}"
                    bad += 1
                    break
                time.sleep(5 * (attempt + 1))
        if i % 100 == 0:
            print(f"   {i}/{len(rows)}", flush=True)
    rep = ROOT / "reports" / f"poolheads-import-{time.strftime('%Y%m%d-%H%M%S')}.json"
    rep.parent.mkdir(exist_ok=True)
    rep.write_text(json.dumps(out, indent=1))
    print(f"   novos {new} · já existiam (atualizados) {upd} · erros {bad} → {rep.name}")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
