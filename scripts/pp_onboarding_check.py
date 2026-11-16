#!/usr/bin/env python3
"""Check the ClickUp onboarding checklist items (Frank's template: Intro / In Communications / Won / Lost / Review
Request / Drip / Customize Pipeline / GHL Integrations) against what is live in each sub-account (16/11, Pedro: close
the template tasks that are really done, keep only what still needs work).

Reads dump/<slug>/ (run pp_dump.py first) plus the location's integrations. Read-only. Output: one JSON per account with
done / open + reason per item, used to update the ClickUp tasks.

  python3 scripts/pp_onboarding_check.py --only "Bonneville" --only "Capital Lawn"
  python3 scripts/pp_onboarding_check.py --json reports/onboarding-check.json      # every account in ACCOUNTS
"""
from __future__ import annotations

import argparse
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
from cli_anything.gohighlevel.utils.agency import SERVICES, Agency, match_location, slugify  # noqa: E402

ITEMS = {
    "Intro Message": ["Website Form Fill To Pipeline", "Missed New Lead - Initial SMS Follow-up"],
    "Won Customer Message": ["Won Stage"],
    "Lost Customer Message": ["Lost Stage"],
    "Review Request": ["Review Request"],
    "Drip Campaign": ["No Response Follow-up"],
}


def wf_index(slug: str) -> list[dict]:
    p = os.path.join(ROOT, "dump", slug, "workflows", "_index.json")
    return json.load(open(p)) if os.path.exists(p) else []


def check(a: Agency, loc: dict) -> dict:
    slug = slugify(loc["name"])
    wfs = wf_index(slug)
    by = {}
    for w in wfs:
        by.setdefault(w["name"].strip().lower(), []).append(w["status"])
    out = {}
    for item, names in ITEMS.items():
        hits = {n: by.get(n.lower(), []) for n in names}
        pub = [n for n, st in hits.items() if "published" in st]
        if pub:
            out[item] = ["done", f"live: {', '.join(pub)}"]
        elif any(hits.values()):
            out[item] = ["open", f"in draft: {', '.join(n for n, st in hits.items() if st)}"]
        else:
            out[item] = ["open", "workflow missing"]
    ic = by.get("in communication stage", [])
    out["In Communications Message"] = (["done", "standard setup (Quote Sent / No Response follow-ups cover this stage)"]
                                        if ic or by.get("quote sent follow-up") else ["open", "workflow missing"])
    pp = os.path.join(ROOT, "dump", slug, "pipelines.json")
    pipes = json.load(open(pp)) if os.path.exists(pp) else []
    best = max(pipes, key=lambda p: len(p.get("stages") or []), default=None)
    out["Customize Pipeline & Opportunity Board"] = (["done", f"pipeline '{best['name']}' with {len(best['stages'])} stages"]
                                                     if best and len(best.get("stages") or []) >= 5 else ["open", "no full pipeline"])
    full = a.location(loc["id"])
    ads, ga = full.get("googleAdwordsId"), full.get("googleAnalytics4PropertyId")
    gbp = False
    try:
        accs = a.get(SERVICES, f"/social-media-posting/{loc['id']}/accounts")["results"]["accounts"]
        gbp = any(x.get("platform") == "google" and x.get("active") for x in accs)
    except Exception:  # noqa: BLE001
        pass
    have = [n for n, ok in (("Google Ads", ads), ("GA4", ga), ("GBP", gbp)) if ok]
    miss = [n for n, ok in (("Google Ads", ads), ("GA4", ga), ("GBP", gbp)) if not ok]
    out["GHL Integrations (GBP, Analytics, AdWords, Facebook, etc..)"] = (
        ["done", f"connected: {', '.join(have)}"] if not miss else ["open", f"connected: {', '.join(have) or 'none'}; missing: {', '.join(miss)}"])
    return {"account": loc["name"], "id": loc["id"], "items": out}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", action="append", required=True)
    ap.add_argument("--json")
    args = ap.parse_args()
    a = Agency()
    locs = a.locations()
    res = []
    for o in args.only:
        loc = match_location(locs, o)
        if not loc:
            print(f"!! not found: {o}")
            continue
        r = check(a, loc)
        res.append({"query": o, **r})
        print(f"== {r['account']}")
        for k, (st, why) in r["items"].items():
            print(f"   {'✓' if st == 'done' else '·'} {k}: {why}")
    if args.json:
        json.dump(res, open(args.json, "w"), indent=1, ensure_ascii=False)


if __name__ == "__main__":
    main()
