#!/usr/bin/env python3
"""Customer export from Skimmer (xlsx/csv) → GHL import CSV + rows to check. Read-only on GHL.

    python3 scripts/pp_import_skimmer.py <Customers.xlsx> --only "Bonneville Pool Maintenance" --out <dir>

Skimmer columns: FirstName, LastName, CompanyName, DisplayAsCompany, MobilePhone1/2, HomePhone, WorkPhone, Email1-4,
Billing*/Location* address, Status (Active/Inactive), TagList, LeadSource, CustomerNotes, Rate, RateType.
- Phone: first of MobilePhone1, MobilePhone2, HomePhone, WorkPhone → +1 E.164; the others go to "Additional Phones".
- E-mail: Email1 lowercased (the next ones go to "Additional Emails").
- Address: the service location (Location*), billing address when there is none.
- Tags column (map it to Tags in the import screen): Active → "active client, existing customer" (lead automations
  skip them; Won/Review triggers filter on "existing customer"), Inactive → "past client", + "skimmer import"
  + the Skimmer TagList.
- Notes: lead source, rate, Skimmer notes.
- Partner referrals (Bonneville: "Adam Dayton | Blue Wave" + drew@bluewavespas.com): partner name taken out of the
  last name, e-mail domains on 3+ rows (not gmail etc.) moved to Notes, tag "blue wave referral". Placeholder rows
  ("Schedule Available (4 jobs)") skipped.
Same phone/e-mail on 2+ rows (one customer, several properties) → one row, other addresses in Notes. Rows with no phone
and no e-mail go to <stem>-no-phone-no-email.csv (GHL import needs one of them).
Flags rows to check: no phone, no e-mail, already in GHL (with tags).
Client data: the output stays out of git.
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
from collections import defaultdict
from pathlib import Path

from _common import load_dotenv

from cli_anything.gohighlevel.utils.agency import SERVICES, Agency

OUT = ["First Name", "Last Name", "Company Name", "Phone", "Additional Phones", "Email", "Additional Emails",
       "Address", "City", "State", "Postal Code", "Tags", "Notes"]


PLACEHOLDER = re.compile(r"schedule available|\(\d+ jobs?\)", re.I)
PARTNER_IN_NAME = re.compile(r"blue ?wave", re.I)
FREEMAIL = {"gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "icloud.com", "aol.com", "msn.com", "live.com",
            "comcast.net", "me.com"}


def rows_of(path: Path) -> list[dict]:
    if path.suffix.lower() in (".xlsx", ".xlsm"):
        import openpyxl
        ws = openpyxl.load_workbook(path, read_only=True).worksheets[0]
        it = ws.iter_rows(values_only=True)
        head = [str(h or "").strip() for h in next(it)]
        return [{h: ("" if v is None else str(v)).strip() for h, v in zip(head, r)} for r in it if any(r)]
    return [{k: (v or "").strip() for k, v in r.items()} for r in csv.DictReader(open(path, newline="", encoding="utf-8-sig"))]


def phone(v: str) -> str:
    d = re.sub(r"\D", "", v or "")
    if len(d) == 11 and d.startswith("1"):
        d = d[1:]
    return f"+1{d}" if len(d) == 10 else ""


def title(v: str) -> str:
    v = re.sub(r"\s+", " ", v or "").strip()
    return v.title() if (v.isupper() and len(v) > 3) or (v.islower() and not re.search(r"\d", v)) else v


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("file")
    p.add_argument("--only", required=True, help="sub-account to check the list against")
    p.add_argument("--out", required=True)
    args = p.parse_args()
    load_dotenv()
    src = rows_of(Path(args.file))

    # e-mail domains on 3+ rows = a partner/dealer's address (Blue Wave Spas referrals), never the customer's
    doms = defaultdict(set)
    for r in src:
        for i in range(1, 5):
            e = r.get(f"Email{i}", "").lower()
            if "@" in e:
                doms[e.split("@")[-1]].add(e)
    counts = defaultdict(int)
    for r in src:
        for e in {r.get(f"Email{i}", "").lower() for i in range(1, 5)}:
            if "@" in e:
                counts[e.split("@")[-1]] += 1
    shared_domains = {d for d, c in counts.items() if c >= 3 and d not in FREEMAIL}
    shared_domains |= {d for d in doms if re.match(r"blu\w*wave", d)}  # typos of the partner's domain
    if shared_domains:
        print(f"   partner e-mail domains (moved to Notes): {', '.join(sorted(shared_domains))}")

    out, flags = [], defaultdict(list)
    for n, r in enumerate(src, start=2):
        phones = [x for x in dict.fromkeys(phone(r.get(k, "")) for k in
                                           ("MobilePhone1", "MobilePhone2", "HomePhone", "WorkPhone")) if x]
        emails = [x for x in dict.fromkeys(r.get(f"Email{i}", "").lower() for i in range(1, 5)) if "@" in x]
        loc = "Location" if r.get("LocationAddress") else "Billing"
        company = r.get("CompanyName", "") if r.get("DisplayAsCompany", "").lower() == "true" else ""
        first, last = title(r.get("FirstName", "")), title(r.get("LastName", ""))
        if not first and not last:
            first = title(r.get("FullName", ""))
        if PLACEHOLDER.search(f"{first} {last}"):
            print(f"   skipped line {n}: placeholder {first} {last!r}")
            continue
        partner = ""
        m = PARTNER_IN_NAME.search(last)
        if m and m.start() == 0:  # "Adam Dayton" / "Blue Wave" → Adam / Dayton, referral of Blue Wave
            partner = title(last).strip()
            parts = first.split(" ")
            first, last = (" ".join(parts[:-1]), parts[-1]) if len(parts) > 1 else (first, "")
        dealer = [e for e in emails if e.split("@")[-1] in shared_domains]
        emails = [e for e in emails if e not in dealer]
        status = r.get("Status", "").lower()
        tags = ["active client", "existing customer"] if status == "active" else ["past client"]
        if partner or dealer or "blue wave" in r.get("LeadSource", "").lower():
            tags.append("blue wave referral")
        tags += ["skimmer import"] + [t.strip().lower() for t in r.get("TagList", "").split(",") if t.strip()]
        notes = []
        if r.get("LeadSource"):
            notes.append(f"Lead source: {r['LeadSource']}")
        if r.get("Rate") not in ("", "0", "0.0") and r.get("RateType", "None") != "None":
            notes.append(f"Rate: ${r['Rate']} {r['RateType']}")
        if dealer:
            notes.append(f"Referral contact (not the customer): {', '.join(dealer)}")
        for k in ("CustomerNotes", "LocationNotes"):
            if r.get(k):
                notes.append(r[k])
        row = {"First Name": first, "Last Name": last, "Company Name": company,
               "Phone": phones[0] if phones else "", "Additional Phones": ", ".join(phones[1:]),
               "Email": emails[0] if emails else "", "Additional Emails": ", ".join(emails[1:]),
               "Address": title(r.get(f"{loc}Address", "")), "City": title(r.get(f"{loc}City", "")),
               "State": r.get(f"{loc}State", "").upper(), "Postal Code": r.get(f"{loc}Zip", ""),
               "Tags": ", ".join(dict.fromkeys(tags)), "Notes": " | ".join(notes), "_line": n,
               "_status": status or "?"}
        if not row["Phone"]:
            flags[n].append("no phone (no SMS)")
        if not row["Email"]:
            flags[n].append("no email")
        if status not in ("active", "inactive"):
            flags[n].append(f"status {r.get('Status')!r}")
        out.append(row)

    # same phone/e-mail = same person with more than one property (GHL would merge them, last row wins): one row,
    # the other addresses in Notes, "active client" if any of the properties is active
    merged, by_key = [], {}
    for row in out:
        keys = [k for k in (row["Phone"], row["Email"]) if k]
        hit = next((by_key[k] for k in keys if k in by_key), None)
        if hit is None:
            merged.append(row)
            for k in keys:
                by_key[k] = row
            continue
        addr = ", ".join(x for x in (row["Address"], row["City"], row["State"], row["Postal Code"]) if x)
        if addr and row["Address"] != hit["Address"] and f"Also: {addr} " not in hit["Notes"]:
            hit["Notes"] = " | ".join(x for x in (hit["Notes"], f"Also: {addr} ({row['_status']})") if x)
        if row["_status"] == "active" and hit["_status"] != "active":
            hit["Tags"] = hit["Tags"].replace("past client", "active client, existing customer")
            hit["_status"] = "active"
        flags[hit["_line"]].append(f"merged with line {row['_line']} (same phone/email)")
        flags.pop(row["_line"], None)
        for k in keys:
            by_key.setdefault(k, hit)
    out = merged
    # GHL import needs a phone or an e-mail: rows with neither go to a separate file
    nocontact = [r for r in out if not r["Phone"] and not r["Email"]]
    out = [r for r in out if r["Phone"] or r["Email"]]
    for r in nocontact:
        flags.pop(r["_line"], None)

    a = Agency()
    locs = [x for x in a.locations() if x.get("name", "").lower().startswith(args.only.lower())]
    if len(locs) != 1:
        sys.exit(f"sub-account {args.only!r}: {len(locs)} matches")
    lid = locs[0]["id"]
    have, page = [], 1
    while True:
        r = a.call("POST", SERVICES, "/contacts/search", body={"locationId": lid, "pageLimit": 100, "page": page})
        have += r.get("contacts", [])
        if not r.get("contacts") or len(have) >= r.get("total", 0):
            break
        page += 1
    index = {}
    for c in have:
        for v in (c.get("email"), c.get("phone")):
            if v:
                index[v.lower()] = c
    in_ghl = 0
    for row in out:
        c = index.get(row["Email"]) or index.get(row["Phone"].lower() if row["Phone"] else "")
        if c:
            in_ghl += 1
            flags[row["_line"]].append(f"already in GHL ({', '.join(c.get('tags') or []) or 'no tags'})")

    d = Path(args.out)
    d.mkdir(parents=True, exist_ok=True)
    stem = re.sub(r"\W+", "-", Path(args.file).stem).strip("-").lower()
    with open(d / f"{stem}-ghl.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=OUT, extrasaction="ignore")
        w.writeheader()
        w.writerows(out)
    with open(d / f"{stem}-no-phone-no-email.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=OUT, extrasaction="ignore")
        w.writeheader()
        w.writerows(nocontact)
    with open(d / f"{stem}-review.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Line", "First Name", "Last Name", "Phone", "Email", "Status", "Check"])
        for row in out:
            if flags[row["_line"]]:
                w.writerow([row["_line"], row["First Name"], row["Last Name"], row["Phone"], row["Email"],
                            row["_status"], " · ".join(flags[row["_line"]])])
    st = defaultdict(int)
    for row in out:
        st[row["_status"]] += 1
    kinds = defaultdict(int)
    for fl in flags.values():
        for x in fl:
            kinds[re.sub(r" \(.*| line \d+.*", lambda m: "", x)] += 1
    print(f"   {len(nocontact)} rows without phone and e-mail → {stem}-no-phone-no-email.csv (not importable)")
    print(f"== {locs[0]['name']}: {len(out)} rows ({dict(st)}) · {len(have)} contacts in GHL · {in_ghl} already there")
    for k, v in sorted(kinds.items(), key=lambda kv: -kv[1]):
        print(f"   {v:3} {k}")
    print(f"   → {d / (stem + '-ghl.csv')}\n   → {d / (stem + '-review.csv')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
