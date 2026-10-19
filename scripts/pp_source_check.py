#!/usr/bin/env python3
"""Did the source-tag workflows run on real traffic? (19/10, after pp_source_tags.py)

    ./.venv/bin/python scripts/pp_source_check.py --only Sunwave --since 2026-10-19T17:00

Every inbound call/text since --since: the line (number name; IVR calls: meta.ivr), the call
triggers it fired (meta.callStatusTriggerFired → workflow name) and the contact's tags now, with
✓ when the line's source tag is there, "pulado" when the contact has a tag the workflow skips
(customer/internal/spam) and ✗ otherwise. Read-only.
"""
from __future__ import annotations

import argparse
import datetime

from _common import load_dotenv, location_dirs
from pp_audit import load
from pp_source_tags import ACCOUNTS

from cli_anything.gohighlevel.utils.agency import SERVICES, Agency


def expected(cfg: dict, line_name: str, kind: str) -> tuple[list[str], list[str]] | None:
    """(tags the line should give, tags that make the workflow skip)."""
    low = line_name.lower()
    for spec in cfg.get("line_tags", {}).values():
        if spec["line"] in low and kind in spec["kinds"]:
            return spec["tags"], cfg.get("skip", [])
    for spec in cfg.get("copy", {}).values():
        if spec.get("line") and spec["line"] in low and kind == "call":
            return spec["tags"], []
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--only", action="append", required=True, help="account (key of pp_source_tags.ACCOUNTS)")
    parser.add_argument("--since", required=True, help="UTC, e.g. 2026-10-19T17:00")
    args = parser.parse_args()
    load_dotenv()
    a = Agency()
    since = args.since if args.since.endswith("Z") else args.since + ":00Z"
    for key in args.only:
        cfg = ACCOUNTS[key]
        d = location_dirs([key])[0]
        loc = load(d / "location.json", {})["id"]
        nums = a.call("GET", SERVICES, f"/phone-system/numbers/location/{loc}").get("numbers", [])
        lines = {n["phoneNumber"]: n.get("friendlyName") or n["phoneNumber"] for n in nums}
        names = {}
        for w in a.workflows(loc):
            try:
                for t in a.triggers(loc, w["id"]):
                    names[t["id"]] = w["name"]
            except Exception:  # noqa: BLE001 — a few workflows answer 503 here; their names just stay ids
                pass
        convs = a.call("GET", SERVICES, "/conversations/search", params={
            "locationId": loc, "limit": 100, "sort": "desc", "sortBy": "last_message_date"}).get("conversations", [])
        cutoff = datetime.datetime.fromisoformat(since.replace("Z", "+00:00")).timestamp() * 1000
        print(f"== {d.name} desde {since}")
        seen = 0
        for conv in [c for c in convs if (c.get("lastMessageDate") or 0) >= cutoff]:
            m = a.call("GET", SERVICES, f"/conversations/{conv['id']}/messages", params={"limit": 30})
            msgs = m["messages"]["messages"] if isinstance(m.get("messages"), dict) else m.get("messages", [])
            for x in sorted(msgs, key=lambda x: x["dateAdded"]):
                if x["dateAdded"] < since or x.get("direction") != "inbound" or x.get("type") not in (1, 2, 24):
                    continue
                kind = "sms" if x["type"] == 2 else "call"
                det = a.call("GET", SERVICES, f"/conversations/messages/{x['id']}")
                det = det.get("message", det)
                to = det.get("to") or ""
                if to not in lines:
                    to = next((v.get("to") for v in ((det.get("meta") or {}).get("ivr") or {}).values()
                               if v.get("to") in lines), to)
                fired = [names.get(i, i) for i in (x.get("meta") or {}).get("callStatusTriggerFired") or []]
                line = lines.get(to) or next((f.split(" - ", 1)[1] for f in fired if f.startswith("Lead Source - ")), to)
                tags = a.call("GET", SERVICES, f"/contacts/{conv['contactId']}")["contact"].get("tags") or []
                exp = expected(cfg, line, kind)
                if exp is None:
                    verdict = "· (linha sem workflow de origem)"
                elif set(exp[0]) <= set(tags):
                    verdict = f"✓ {exp[0]}"
                elif set(exp[1]) & set(tags):
                    verdict = f"pulado ({sorted(set(exp[1]) & set(tags))})"
                else:
                    verdict = f"✗ falta {exp[0]}"
                who = (conv.get("fullName") or conv.get("contactName") or "")[:18]
                print(f"   {x['dateAdded'][5:16]} {kind:4} {line[:16]:16} {who:18} {verdict}"
                      + (f" · disparou {fired}" if fired else ""))
                seen += 1
        if not seen:
            print("   nenhuma ligação/SMS de entrada ainda")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
