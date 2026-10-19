#!/usr/bin/env python3
"""Where did the untagged contacts come from? (Val, 19/10: Sunwave and Passion have contacts without tags)

    ./.venv/bin/python scripts/pp_source_audit.py --only "Sunwave"            # report + plan in reports/
    ./.venv/bin/python scripts/pp_source_audit.py --only "Sunwave" --apply    # add the source tags
    ./.venv/bin/python scripts/pp_source_audit.py --only "Sunwave" --leads    # leads with no source tag

A contact without any tag is classified by, in order: the contact's own `source` (QuickBooks sync,
form name, chat widget), then the first message of its conversation — inbound call/text → the line's
source tag (number name → tag, LINE_TAGS), outbound → "outbound (staff)" (the team called/texted first:
vendors, customers); Facebook/Instagram by message type; inbound e-mail → "email inbox" (synced inbox:
vendors, notifications, spam); no conversation → who created it (staff → "added manually"). The
account's own numbers, users' phones and e-mails → "internal".
--leads: contacts tagged as leads by the call/IVR workflows ("new lead" / "inbound call") but with no
source tag → the line of their first inbound call or text (Sunwave: the IVR tags every line the same).
Tags are added, never removed. The plan (contact → tags) goes to reports/<slug>-source-tags[-leads].json
before --apply.
"""
from __future__ import annotations

import argparse
import collections
import datetime
import json

from _common import REPORTS, load_dotenv, location_dirs
from pp_audit import load

from cli_anything.gohighlevel.utils.agency import SERVICES, Agency

# number name (lowercase substring) → tags, first match wins ("{kind}" = call / sms)
LINE_TAGS = [("adwords", ["adwords", "adwords {kind}"]), ("google ads", ["adwords", "adwords {kind}"]),
             ("angi", ["angi"]), ("gbp", ["website & gbp"]), ("website", ["website & gbp"]),
             ("truck", ["trucks & cards"]), ("customer service", ["customer service line"]),
             ("facebook", ["facebook"]), ("lsa", ["google lsa"]), ("yelp", ["yelp"])]
SOURCE_TAGS = {"quickbooks": ["quickbooks"], "chat widget": ["chat widget"]}
FORM_TAGS = {"google ads": ["adwords", "adwords form fill"], "landing page": ["adwords", "adwords form fill"]}
WEBSITE_FORM = ["website form fill"]
OUTBOUND = ["outbound (staff)"]
TYPES = {1: "call", 2: "sms", 3: "email", 4: "sms", 11: "facebook", 18: "instagram", 24: "call", 29: "chat"}
CREATED_BY = {"WEB_USER": ["added manually"]}
LEAD_TAGS = {"new lead", "inbound call", "incoming call"}


def ts(v) -> str:
    if isinstance(v, (int, float)):
        return datetime.datetime.fromtimestamp(v / 1000, datetime.timezone.utc).isoformat()
    return v or ""


def all_contacts(a: Agency, loc: str) -> list[dict]:
    out, page = [], 1
    while True:
        r = a.call("POST", SERVICES, "/contacts/search", body={"locationId": loc, "pageLimit": 100, "page": page})
        out += r.get("contacts", [])
        if len(r.get("contacts", [])) < 100:
            return out
        page += 1


def line_tags(name: str, kind: str) -> list[str] | None:
    tags = next((tags for k, tags in LINE_TAGS if k in name.lower()), None)
    return [t.replace("{kind}", "call in" if kind == "call" else kind) for t in tags] if tags else None


def source_set() -> set[str]:
    """Every tag that names a source (a lead with one of these is already attributed)."""
    out = {t.replace("{kind}", k) for _, tags in LINE_TAGS for t in tags for k in ("call in", "sms")}
    out |= {t for ts in [*SOURCE_TAGS.values(), *FORM_TAGS.values(), WEBSITE_FORM] for t in ts}
    return out | {"google ads lead form", "google leads", "google lead form", "website/gbp", "gbp", "form fill",
                  "adwords form fill", "facebook", "instagram"}


def first_touch(a: Agency, loc: str, cid: str, lines: dict[str, str], inbound_only: bool = False) -> tuple[str, list[str]]:
    convs = a.call("GET", SERVICES, "/conversations/search", params={"locationId": loc, "contactId": cid}).get(
        "conversations", [])
    msgs = []
    for conv in convs:
        m = a.call("GET", SERVICES, f"/conversations/{conv['id']}/messages", params={"limit": 100})
        msgs += m["messages"]["messages"] if isinstance(m.get("messages"), dict) else m.get("messages", [])
    msgs = [x for x in msgs if x.get("type") in TYPES]
    if inbound_only:
        msgs = [x for x in msgs if x.get("direction") == "inbound" and TYPES[x["type"]] in ("call", "sms")]
    if not msgs:
        return "no activity", []
    x = min(msgs, key=lambda x: x["dateAdded"])
    kind = TYPES[x["type"]]
    if kind in ("facebook", "instagram"):
        return kind, [kind]
    if kind == "chat":
        return "chat", ["chat widget"]
    if x.get("direction") == "outbound":
        return f"outbound {kind}", OUTBOUND
    if kind == "email":
        return "inbound email", ["email inbox"]
    d = a.call("GET", SERVICES, f"/conversations/messages/{x['id']}")
    d = d.get("message", d)
    to = d.get("to") or ""
    if to not in lines:  # IVR calls: "to" is the account's name; the dialed number is in meta.ivr
        to = next((v.get("to") for v in ((d.get("meta") or {}).get("ivr") or {}).values() if v.get("to") in lines), to)
    name = lines.get(to)
    if not name:
        return f"inbound {kind} → {to}", []
    return f"inbound {kind} → {name}", line_tags(name, kind) or [name.lower()]


def classify(a: Agency, loc: str, c: dict, lines: dict[str, str], own: set[str]) -> tuple[str, list[str]]:
    if {c.get("phone"), (c.get("email") or "").lower()} & own:
        return "internal (own number / user)", ["internal"]
    src = (c.get("source") or "").strip()
    low = src.lower()
    if low in SOURCE_TAGS:
        return f"source: {src}", SOURCE_TAGS[low]
    if src:  # a form's name
        tags = next((t for k, t in FORM_TAGS.items() if k in low), WEBSITE_FORM)
        return f"form: {src}", tags
    why, tags = first_touch(a, loc, c["id"], lines)
    if why == "no activity":
        by = (a.call("GET", SERVICES, f"/contacts/{c['id']}")["contact"].get("createdBy") or {}).get("source")
        return f"no activity (created by {by})", CREATED_BY.get(by, [])
    return why, tags


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--only", action="append", required=True)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--leads", action="store_true", help="leads without a source tag (instead of untagged)")
    args = parser.parse_args()
    load_dotenv()
    a = Agency()
    for d in location_dirs(args.only):
        loc = load(d / "location.json", {})["id"]
        nums = a.call("GET", SERVICES, f"/phone-system/numbers/location/{loc}").get("numbers", [])
        lines = {n["phoneNumber"]: n.get("friendlyName") or n["phoneNumber"] for n in nums}
        own = set(lines) | {n.get("forwardingNumber") for n in nums} | \
            {x for u in a.users(loc) for x in (u.get("phone"), (u.get("email") or "").lower())}
        own.discard(None)
        own.discard("")
        contacts = all_contacts(a, loc)
        sources = source_set()
        if args.leads:
            bare = [c for c in contacts if LEAD_TAGS & set(c.get("tags") or []) and not sources & set(c.get("tags") or [])]
        else:
            bare = [c for c in contacts if not c.get("tags")]
        print(f"== {d.name}: {len(contacts)} contatos, {len(bare)} {'leads sem origem' if args.leads else 'sem tag'}"
              f" · linhas {lines}")
        plan_path = REPORTS / f"{d.name}-source-tags{'-leads' if args.leads else ''}.json"
        if args.apply:
            plan = json.loads(plan_path.read_text())
        else:
            plan = []
            for i, c in enumerate(bare):
                why, tags = first_touch(a, loc, c["id"], lines, inbound_only=True) if args.leads \
                    else classify(a, loc, c, lines, own)
                plan.append({"id": c["id"], "name": c.get("contactName") or c.get("firstNameLowerCase") or "",
                             "added": ts(c.get("dateAdded"))[:10], "why": why, "tags": tags})
                if i % 100 == 99:
                    print(f"   … {i + 1}/{len(bare)}", flush=True)
            REPORTS.mkdir(exist_ok=True)
            plan_path.write_text(json.dumps(plan, ensure_ascii=False, indent=1))
        by = collections.Counter((p["why"].split(" → ")[0] if p["why"].startswith("inbound") and not p["tags"]
                                  else p["why"], tuple(p["tags"])) for p in plan)
        for (why, tags), n in by.most_common():
            print(f"   {n:5}  {why:45} → {list(tags) or '(sem tag de origem)'}")
        print(f"   plano: {plan_path}")
        if not args.apply:
            continue
        done = bad = 0
        for p in plan:
            if not p["tags"]:
                continue
            live = a.call("GET", SERVICES, f"/contacts/{p['id']}")["contact"]
            if (sources & set(live.get("tags") or [])) if args.leads else live.get("tags"):
                continue  # got tags since the plan — leave it
            try:
                a.call("POST", SERVICES, f"/contacts/{p['id']}/tags", body={"tags": p["tags"]})
                done += 1
            except Exception as e:  # noqa: BLE001
                bad += 1
                print(f"   ✗ {p['id']}: {str(e)[:100]}")
        print(f"   ✓ tags de origem em {done} contatos" + (f" · {bad} falhas" if bad else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
