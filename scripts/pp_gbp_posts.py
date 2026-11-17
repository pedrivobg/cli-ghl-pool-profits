#!/usr/bin/env python3
"""Schedule Google Business Profile posts through the account's Social Planner (ClickUp 86bd1xdbu, Frank 11/11).

Config: config/gbp_posts/<name>.json ({location, time_utc, action, user_id, posts: [{date, text, image?}]}).
Skips a post whose text is already scheduled/published for that date (safe to re-run).

  python3 scripts/pp_gbp_posts.py config/gbp_posts/bluvantage.json            # plan
  python3 scripts/pp_gbp_posts.py config/gbp_posts/bluvantage.json --apply    # schedule + list what is scheduled
"""
from __future__ import annotations

import argparse
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
from cli_anything.gohighlevel.utils.agency import SERVICES, Agency, match_location  # noqa: E402


def gbp_account(a: Agency, lid: str) -> str:
    accs = a.get(SERVICES, f"/social-media-posting/{lid}/accounts")["results"]["accounts"]
    g = [x for x in accs if x.get("platform") == "google" and x.get("active") and not x.get("deleted")]
    if not g:
        sys.exit("no active Google Business Profile in Social Planner")
    if any(x.get("isExpired") for x in g):
        print("WARNING: GBP connection marked expired — reconnect in Social Planner")
    return g[0]["id"]


def listed(a: Agency, lid: str, acc: str) -> list[dict]:
    out = []
    for t in ("scheduled", "published"):
        r = a.call("POST", SERVICES, f"/social-media-posting/{lid}/posts/list", body={
            "type": t, "accounts": acc, "skip": "0", "limit": "100", "fromDate": "2026-01-01T00:00:00.000Z",
            "toDate": "2027-12-31T00:00:00.000Z", "includeUsers": "false"})
        out += (r.get("results") or {}).get("posts") or []
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("config")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    cfg = json.load(open(args.config))
    a = Agency()
    loc = match_location(a.locations(), cfg["location"]) or sys.exit("location not found")
    lid = loc["id"]
    acc = gbp_account(a, lid)
    have = {((p.get("displayDate") or p.get("scheduleDate") or p.get("publishedAt") or "")[:10], (p.get("summary") or "").strip()) for p in listed(a, lid, acc)}
    for p in cfg["posts"]:
        when = f"{p['date']}T{cfg['time_utc']}:00.000Z"
        if (p["date"], p["text"].strip()) in have:
            print(f"= {p['date']} already there")
            continue
        print(f"+ {p['date']} {p['text'][:70]}…")
        if not args.apply:
            continue
        body = {"accountIds": [acc], "summary": p["text"], "type": "post", "status": "scheduled", "scheduleDate": when,
                "media": [{"url": p["image"], "type": "image/jpeg"}] if p.get("image") else [],
                "gmbPostDetails": {"gmbEventType": "STANDARD", "actionType": cfg.get("action", "call")},
                "userId": cfg["user_id"]}
        a.call("POST", SERVICES, f"/social-media-posting/{lid}/posts", body=body)
    if args.apply:
        now = listed(a, lid, acc)
        print(f"\n{loc['name']}: {len(now)} scheduled/published posts")
        for p in sorted(now, key=lambda x: x.get("displayDate") or ""):
            print(f"   {p.get('status'):10} {p.get('displayDate')} {(p.get('summary') or '')[:60]}")


if __name__ == "__main__":
    main()
