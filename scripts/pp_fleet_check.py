#!/usr/bin/env python3
"""Is every client account on the current model? (Frank 10/11, Corolla was on the old snapshot.)

Live read, nothing written. Per account vs Southern (the model):
  stages     model stages of "Pool Leads" missing in the account (No Response, No Show, Won by service type…)
  workflows  pp_mirror CONTENT workflows missing, or with a different status than the model
  gate       Review Request asks the NPS score first and sends only 5 to Google (pp_review_gate.py)
  dash       "Pool Profits Dashboard" is the default (pp_dashboard.py)
Accounts with a wording config (pp_wording) or their own setup are flagged, since pp_mirror would overwrite them.

  python3 scripts/pp_fleet_check.py [--only <name>] [--json reports/fleet-<date>.json]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(__file__))
from cli_anything.gohighlevel.utils.agency import SERVICES, Agency, GHLError, match_location, slugify  # noqa: E402
import pp_dashboard  # noqa: E402
import pp_review_gate  # noqa: E402
from pp_mirror import ALIASES, CONTENT, STAGE_ALIASES  # noqa: E402

MODEL = "SylIOZiJ6YQsZOypUI8Z"


def norm(s: str) -> str:
    return " ".join((s or "").replace(" ", " ").split()).lower()


def stage_names(a: Agency, loc: str) -> list[str] | None:
    pipes = a.pipelines(loc)
    p = next((p for p in pipes if "pool leads" in norm(p.get("name"))), None) or (pipes[0] if len(pipes) == 1 else None)
    return [s["name"] for s in p["stages"]] if p else None


def check(a: Agency, loc: dict, model: dict) -> dict:
    lid = loc["id"]
    row = {"name": loc.get("name"), "id": lid}
    st = stage_names(a, lid)
    if st is None:
        row["stages"] = ["NO Pool Leads pipeline"]
    else:
        have = {norm(s) for s in st}
        row["stages"] = [m for m in model["stages"]
                         if norm(m) not in have and not any(norm(x) in have for x in STAGE_ALIASES.get(m, []))]
    wfs = a.workflows(lid)
    by = {}
    for w in wfs:
        by.setdefault(norm(w.get("name")), []).append(w)
    miss, diff = [], []
    for name in CONTENT:
        found = by.get(norm(name)) or next((by[norm(x)] for x in ALIASES.get(name, []) if norm(x) in by), None)
        if not found:
            miss.append(name)
        elif not any(w.get("status") == model["status"].get(name) for w in found):
            diff.append(f"{name} ({found[0].get('status')})")
    row["wf_missing"], row["wf_status"] = miss, diff
    row["gate"] = pp_review_gate.plan(a, loc, False)
    d = pp_dashboard.dash_list(a, lid)
    mine = [x for x in pp_dashboard.all_dashboards(d) if x.get("title") == pp_dashboard.TITLE]
    row["dash"] = bool(mine and d.get("defaultDashboardId") == mine[0]["_id"])
    row["wording"] = os.path.exists(os.path.join(ROOT, "config", f"{slugify(loc.get('name', '')).split('-pool')[0]}_wording.json"))
    row["contacts"] = (a.get(SERVICES, "/contacts/", {"locationId": lid, "limit": 1}).get("meta") or {}).get("total")
    return row


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", action="append")
    ap.add_argument("--json")
    args = ap.parse_args()
    a = Agency(sleep=0.05)
    locs = a.locations()
    mwfs = a.workflows(MODEL)
    model = {"stages": stage_names(a, MODEL),
             "status": {n: next((w.get("status") for w in mwfs if norm(w.get("name")) == norm(n)), None) for n in CONTENT}}
    if args.only:
        targets = [match_location(locs, o) or sys.exit(f"not found: {o}") for o in args.only]
    else:
        targets = [l for l in locs if l["id"] not in pp_dashboard.SKIP and l["id"] != MODEL]
    rows = []
    for loc in sorted(targets, key=lambda l: l.get("name", "")):
        try:
            r = check(a, loc, model)
        except GHLError as exc:
            r = {"name": loc.get("name"), "id": loc["id"], "error": str(exc)[:200]}
        rows.append(r)
        if "error" in r:
            print(f"{r['name'][:30]:30} ERROR {r['error']}")
            continue
        ok = not r["stages"] and not r["wf_missing"] and "ok" in r["gate"] and r["dash"]
        print(f"{r['name'][:30]:30} {'OK ' if ok else 'GAP'} contacts {r['contacts']}"
              + (f" | stages missing: {', '.join(r['stages'])}" if r["stages"] else "")
              + (f" | wf missing: {', '.join(r['wf_missing'])}" if r["wf_missing"] else "")
              + (f" | wf status: {', '.join(r['wf_status'])}" if r["wf_status"] else "")
              + f" | gate: {r['gate']}" + ("" if r["dash"] else " | dash NOT default")
              + (" | wording config" if r["wording"] else ""))
    if args.json:
        os.makedirs(os.path.dirname(os.path.abspath(args.json)), exist_ok=True)
        json.dump({"date": dt.datetime.now().isoformat(), "model": model, "rows": rows}, open(args.json, "w"), indent=1)


if __name__ == "__main__":
    main()
