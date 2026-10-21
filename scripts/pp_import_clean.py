#!/usr/bin/env python3
"""Customer list sent by a client (CSV) → GHL import CSV + list of rows to check. Read-only on GHL.

    ./.venv/bin/python scripts/pp_import_clean.py <list.csv> --only "Stay Fresh Pools" --out <dir>

Columns are found by header name (customer/name, first, last, phone, email, address).
- Name: the last word is the last name ("Doris Ann Smith" → Doris Ann / Smith); extra spaces removed.
- Phone: +1 E.164 (Excel's leading apostrophe removed); e-mail lowercased.
- Address: "street City, ST 12345" is split only when the city/state/ZIP are written; ALL CAPS → Title Case.
  Nothing is guessed (no city or state is filled in when the client didn't write one).
- Flags: same e-mail or phone on 2+ rows (GHL merges them into one contact, the second row overwrites the
  first), the business's own e-mail, no phone (no SMS), no e-mail, one-word name, couples/companies, and
  rows already in GHL (with their tags, e.g. someone tagged "active client" on an "inactive" list).
Writes <stem>-ghl.csv (to upload; tags are added in the import screen) and <stem>-review.csv (rows to
check, with the reason). Client data: keep both out of git.
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
from collections import defaultdict
from pathlib import Path

from _common import load_dotenv, location_dirs
from pp_audit import load

from cli_anything.gohighlevel.utils.agency import SERVICES, Agency

OUT_COLS = ["First Name", "Last Name", "Company Name", "Phone", "Email", "Address", "City", "State", "Postal Code",
            "Notes"]
STATES = {"AZ", "CA", "TX", "FL", "NV", "UT", "CO", "NM", "OR", "WA", "GA", "SC", "NC", "TN", "AL", "LA", "OK"}
GENERIC = {"pool", "pools", "llc", "inc", "co", "company", "the", "service", "services", "care"}
SUFFIX = r"(St|Street|Ave|Avenue|Dr|Drive|Rd|Road|Ln|Lane|Way|Pl|Place|Ct|Court|Pkwy|Parkway|Blvd|Cir|Circle|Trl|Trail)\.?"
COMPANY = re.compile(r"\s+(P?LLC|Inc\.?|Corp\.?|PC|PLLC)$", re.I)
TAIL = re.compile(r"^(?P<street>.*?)[\s,]+(?P<city>[A-Za-z .]+?),?\s+(?P<state>[A-Za-z]{2})\.?\s*(?P<zip>\d{5})?"
                  r"(?:\s+United States)?\s*$")


def squash(s: str | None) -> str:
    return re.sub(r"\s+", " ", (s or "").replace(" ", " ")).strip()


def phone(s: str) -> str:
    d = re.sub(r"\D", "", s or "")
    if len(d) == 10:
        return "+1" + d
    if len(d) == 11 and d.startswith("1"):
        return "+" + d
    return ""


def title(s: str) -> str:
    return " ".join(w.capitalize() if w.isalpha() or w.rstrip(".").isalpha() else w for w in s.split()) \
        if s.isupper() else s


def address(raw: str) -> tuple[str, str, str, str]:
    raw = squash(raw).rstrip(",")
    m = TAIL.match(raw)
    if m and m["state"].upper() in STATES:
        # "6795 S Sapphire Way Chandler Az 85249", "2676 E Bridgeport Pkwy Gilbert, AZ 85295": the city is
        # the word(s) after the last street suffix
        words, street, city = f"{m['street']} {m['city']}".replace(",", " ").split(), "", ""
        for i in range(len(words) - 1, 0, -1):
            if re.fullmatch(SUFFIX, words[i], re.I):
                street, city = " ".join(words[:i + 1]), " ".join(words[i + 1:])
                break
        if city:
            return title(street), title(city), m["state"].upper(), m["zip"] or ""
    return title(raw), "", "", ""


def norm_name(row: dict) -> str:
    return re.sub(r"[^a-z]", "", f"{row['First Name']}{row['Last Name']}".lower())


def dedupe(out: list[dict], flags: dict) -> list[dict]:
    """GHL matches contacts by e-mail and phone: rows that would land on one contact are resolved here.
    Same person (same name) → one row, the other address/e-mail in Notes. Different people sharing an
    e-mail or phone → it stays on the row whose first name is in the e-mail (else the first row)."""
    for key in ("Email", "Phone"):
        groups = defaultdict(list)
        for row in out:
            if row[key]:
                groups[row[key].lower()].append(row)
        for value, same in groups.items():
            people = {norm_name(r) for r in same}
            if len(same) < 2 or len(people) == 1:
                continue
            keep = next((r for r in same if r["First Name"].split()[0].lower() in value), same[0])
            for r in same:
                if r is not keep:
                    r[key] = ""
                    r["Notes"] = (r["Notes"] + " " if r["Notes"] else "") + \
                        f"{key} on the client's list was also {keep['First Name']} {keep['Last Name']}'s ({value})."
                    flags[r["_line"]].append(f"{'e-mail' if key == 'Email' else 'telefone'} de {keep['First Name']} "
                                             f"{keep['Last Name']} (linha {keep['_line']}) — tirado desta linha")
    merged, seen = [], {}
    for row in out:
        k = norm_name(row)
        first = seen.get(k)
        same_contact = first and (any(row[c] and row[c].lower() == first[c].lower() for c in ("Email", "Phone"))
                                  or row["Address"].rstrip(".").lower() == first["Address"].rstrip(".").lower())
        if not same_contact:
            if first:
                flags[row["_line"]].append(f"mesmo nome que a linha {first['_line']} (outros dados: pessoas diferentes?)")
            seen.setdefault(k, row)
            merged.append(row)
            continue
        extra = []
        for c in ("Phone", "Email", "Address"):
            if row[c] and not first[c]:
                first[c] = row[c]
            elif row[c] and row[c].rstrip(".").lower() != first[c].rstrip(".").lower():
                extra.append(f"other {c.lower()} on the list: {row[c]}")
        if extra:
            first["Notes"] = (first["Notes"] + " " if first["Notes"] else "") + (lambda t: t[0].upper() + t[1:])("; ".join(extra)) + "."
        flags[first["_line"]].append(f"linha {row['_line']} é a mesma pessoa — juntada nesta" +
                                     (f" ({'; '.join(extra)})" if extra else ""))
        flags.pop(row["_line"], None)
    return merged


def column(header: list[str], *names: str) -> int | None:
    for i, h in enumerate(header):
        if any(n in h.strip().lower() for n in names):
            return i
    return None


def ghl_contacts(a: Agency, loc: str) -> list[dict]:
    out, page = [], 1
    while True:
        r = a.call("POST", SERVICES, "/contacts/search", body={"locationId": loc, "pageLimit": 100, "page": page})
        out += r.get("contacts", [])
        if not r.get("contacts") or len(out) >= r.get("total", 0):
            return out
        page += 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("csv")
    parser.add_argument("--only", required=True, help="sub-account to check the list against")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    load_dotenv()
    rows = list(csv.reader(open(args.csv, newline="", encoding="utf-8-sig")))
    header, body = rows[0], [r for r in rows[1:] if any(c.strip() for c in r)]
    ci = {k: column(header, *n) for k, n in {"name": ("customer", "name"), "first": ("first",), "last": ("last",),
                                            "phone": ("phone", "mobile", "cell"), "email": ("email", "e-mail"),
                                            "address": ("address", "street")}.items()}
    if ci["first"] is not None:
        ci["name"] = None

    d = location_dirs([args.only])[0]
    loc = load(d / "location.json", {})
    users = load(d / "users.json", [])
    own_emails = {(loc.get("email") or "").lower()} | {(u.get("email") or "").lower() for u in users}
    brand = "".join(w for w in re.findall(r"[a-z]+", loc["name"].lower()) if w not in GENERIC)

    out, flags = [], defaultdict(list)
    for n, r in enumerate(body, start=2):
        get = lambda k: r[ci[k]] if ci[k] is not None and ci[k] < len(r) else ""  # noqa: E731
        company = ""
        if ci["name"] is not None:
            full = squash(get("name"))
            if COMPANY.search(full):
                company, full = full, COMPANY.sub("", full)
            parts = full.split(" ")
            first, last = (" ".join(parts[:-1]), parts[-1]) if len(parts) > 1 else (parts[0], "")
        else:
            first, last = squash(get("first")), squash(get("last"))
        email = squash(get("email")).lower()
        street, city, state, zip_ = address(get("address"))
        row = {"First Name": first, "Last Name": last, "Company Name": company, "Phone": phone(get("phone")), "Email": email,
               "Address": street, "City": city, "State": state, "Postal Code": zip_, "Notes": "", "_line": n}
        who = f"{first} {last}".strip()
        if get("phone").strip() and not row["Phone"]:
            flags[n].append(f"telefone inválido {get('phone')!r}")
        if email and (email in own_emails or (len(brand) >= 5 and brand in email.replace(".", ""))):
            flags[n].append(f"e-mail da própria empresa ({email}) — tirado")
            row["Email"] = ""
        if not last:
            flags[n].append("só um nome")
        if re.search(r"(\band\b|&)", who) or company:
            flags[n].append("casal/empresa no nome")
        if not row["Phone"]:
            flags[n].append("sem telefone (só e-mail)")
        if not row["Email"]:
            flags[n].append("sem e-mail")
        out.append(row)

    out = dedupe(out, flags)

    a = Agency()
    have = ghl_contacts(a, loc["id"])
    index = {}
    for c in have:
        for v in (c.get("email"), c.get("phone"), *(c.get("additionalEmails") or [])):
            if isinstance(v, dict):
                v = v.get("email")
            if v:
                index[v.lower()] = c
    in_ghl = 0
    for row in out:
        c = index.get(row["Email"]) or index.get(row["Phone"].lower() if row["Phone"] else "")
        if c:
            in_ghl += 1
            tags = ", ".join(c.get("tags") or []) or "sem tags"
            flags[row["_line"]].append(f"já está no GHL como {c.get('firstName') or ''} {c.get('lastName') or ''}"
                                       f" ({tags})")

    outdir = Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)
    stem = Path(args.csv).stem
    with open(outdir / f"{stem}-ghl.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=OUT_COLS, extrasaction="ignore")
        w.writeheader()
        w.writerows(out)
    with open(outdir / f"{stem}-review.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Line", "First Name", "Last Name", "Phone", "Email", "Address", "Check"])
        for row in out:
            if flags[row["_line"]]:
                w.writerow([row["_line"], row["First Name"], row["Last Name"], row["Phone"], row["Email"],
                            row["Address"], " · ".join(flags[row["_line"]])])
    kinds = defaultdict(int)
    for fl in flags.values():
        for x in fl:
            kinds[re.sub(r" \(.*| que outra.*| —.*|: .*", "", x)] += 1
    print(f"== {loc['name']}: {len(out)} linhas · {len(have)} contatos no GHL · {in_ghl} da lista já estão lá")
    for k, v in sorted(kinds.items(), key=lambda kv: -kv[1]):
        print(f"   {v:3} {k}")
    print(f"   → {outdir / (stem + '-ghl.csv')}\n   → {outdir / (stem + '-review.csv')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
