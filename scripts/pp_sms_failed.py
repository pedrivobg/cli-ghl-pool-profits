#!/usr/bin/env python3
"""Weekly audit: outbound SMS that failed since a date (A2P / carrier blocks). Read-only.

    python3 scripts/pp_sms_failed.py 2026-11-19 [--only NAME] [--convs 40]

Per client sub-account: the most recent conversations (default 40), their outbound SMS since the date, counted by
status; failed/undelivered ones listed with the error text.
"""
from __future__ import annotations

import argparse
import collections
import re
import time

from _common import Agency, load_dotenv
from cli_anything.gohighlevel.utils.agency import SERVICES

# 30006 landline, 30003 unreachable, 30005 unknown number, 30004 blocked by recipient: normal noise, not A2P
BENIGN = {"30003", "30004", "30005", "30006"}
SKIP = ("test", "snapshot", "sample", "master", "billing only", "portal", "franchising", "hq", "marketplace")


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
    ap.add_argument("--convs", type=int, default=40)
    args = ap.parse_args()
    load_dotenv()
    a = Agency()
    for loc in sorted(a.locations(), key=lambda x: x["name"]):
        n, lid = loc["name"], loc["id"]
        if args.only and args.only.lower() not in n.lower():
            continue
        if not args.only and any(s in n.lower() for s in SKIP):
            continue
        convs = retry(a.call, "GET", SERVICES, "/conversations/search",
                      params={"locationId": lid, "limit": args.convs, "sort": "desc", "sortBy": "last_message_date"})
        st, bad, codes = collections.Counter(), [], collections.Counter()
        for c in convs.get("conversations", []):
            ms = retry(a.call, "GET", SERVICES, f"/conversations/{c['id']}/messages", params={"limit": 20})
            for m in (ms.get("messages") or {}).get("messages", []):
                if m.get("dateAdded", "") < args.since or m.get("direction") != "outbound":
                    continue
                if m.get("messageType") not in ("TYPE_SMS", None) or m.get("type") not in (2, None):
                    continue
                if m.get("type") != 2:
                    continue
                s = m.get("status") or "?"
                st[s] += 1
                if s in ("failed", "undelivered"):
                    err = str(m.get("error") or (m.get("meta") or {}).get("error") or "")
                    code = (re.search(r"(\d{5})", err) or [None, "?"])[1]
                    codes[code] += 1
                    if code not in BENIGN:
                        bad.append((m["dateAdded"][:16], err[:90], (m.get("body") or "")[:50].replace("\n", " ")))
        if not st:
            continue
        print(f"{'!!' if bad else 'ok'} {n}: {dict(st)} codes {dict(codes)}")
        for b in bad[:5]:
            print("     -", *b)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
