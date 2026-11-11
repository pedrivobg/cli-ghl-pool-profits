#!/usr/bin/env python3
"""Standard dashboard in every sub-account (Pedro 10/11: "the one from the meeting" = SwimReady's).

Source = "Pool Profits Dashboard" in the snapshot master (Snapshot Pool Profits), copied there from SwimReady's
default dashboard. For each target account:
  1. backup of the dashboard list (backup/<slug>/dashboards-<date>.json)
  2. POST services /reporting/dashboards/{src}/duplicate {locationId: <src loc>, targetLocationId, title, isPrivate}
     (the copy always comes back private, whatever the body says)
  3. POST /reporting/dashboards/{new}/permissions {locationId, permissionAccess, isPrivate: false} (same as SwimReady:
     agency users full, account users read)
  4. POST /reporting/dashboards/{new}/set-default {locationId}  (403 "set_default_dashboard_role_view" while private)
Existing dashboards stay; the copy only becomes the default. Re-running skips accounts that already have the title.

  python3 scripts/pp_dashboard.py                 # plan for all client accounts
  python3 scripts/pp_dashboard.py --only Corolla --apply
  python3 scripts/pp_dashboard.py --apply
  python3 scripts/pp_dashboard.py --apply --replace   # copy with SwimReady embeds: new clean copy as default, old one deleted
                                                      # (Pedro approved 11/11; master: --only "Snapshot Pool Profits")
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
from cli_anything.gohighlevel.utils.agency import SERVICES, Agency, GHLError, match_location, slugify  # noqa: E402

# Source (11/11): Smart Chem's copy, cleaned by Frank in the UI. The master copy (Snapshot Pool Profits 6af373efd621ce6c86db0b2b)
# and SwimReady's original carry 2 "object-embed" widgets with SwimReady's own reports (Local Heat Map = Local Dominator,
# Local Reporting = local-marketing-reports.com): every account copied on 10/11 showed SwimReady's local report.
SRC_LOC = "Ykjw1clNFPkr4izP9Uaq"        # Smart Chem Pools LLC
SRC_DASH = "6af374b6221fe50f64ae0b4c"   # Pool Profits Dashboard, 14 widgets, no embeds
FOREIGN_EMBEDS = ("taskId=70004&", "e934480d3dd485e026b40bd97bfb6c871c17e276")  # SwimReady's heat map / local report
TITLE = "Pool Profits Dashboard"
PERMS = [{"role": "agency_user", "permission": "full"}, {"role": "account_user", "permission": "read"}]

# Not client accounts (internal, test, billing, old snapshot, the source itself).
SKIP = {
    "Kvdj7o189zlS3caaCNuX",  # Snapshot Pool Profits (old source, still has the SwimReady embeds)
    "Ykjw1clNFPkr4izP9Uaq",  # Smart Chem Pools LLC (source)
    "OVQ4nVT6Ik0xlcSacRGL",  # SWIMREADY (origin, already its default)
    "9RRhRHphfPCXM1glTaqL",  # Damon's Pool Care - Billing Only
    "ry6sFIgFjqY8XLwTVYEj",  # Master Pool Service Snapshot V1
    "rl4GRgHWSLSFdbQcdN0n",  # Nathan Taylor's Account
    "wohRifObKPEykgu17LJu",  # Pool Profits
    "XsIvrTZqKIhSR28TAvOe",  # Pool Profits (Sales)
    "XPTb5f0mJ9i1rEuGcbMx",  # Pool Profits - Sample
    "hmzX5j1dPhOQKX2dH4kf",  # Test Snapshot
    "6lzYFANJTxKkAUA8Z18b",  # test inc
}


def dash_list(a: Agency, loc: str) -> dict:
    return a.get(SERVICES, "/reporting/dashboards", {"locationId": loc}).get("data") or {}


def all_dashboards(data: dict) -> list[dict]:
    out, seen = [], set()
    for key, val in data.items():
        if isinstance(val, list):
            for d in val:
                if isinstance(d, dict) and d.get("_id") and d["_id"] not in seen:
                    seen.add(d["_id"])
                    out.append(d)
    return out


def replace(a: Agency, lid: str, name: str, old: dict, data: dict) -> str:
    """New clean copy as default first, then DELETE the old copy (backup of list + detail)."""
    folder = os.path.join(ROOT, "backup", slugify(name))
    os.makedirs(folder, exist_ok=True)
    with open(os.path.join(folder, f"dashboard-{old['_id']}-{dt.date.today():%Y%m%d}.json"), "w") as fh:
        json.dump({"list": data, "detail": old}, fh, indent=1)
    r = a.call("POST", SERVICES, f"/reporting/dashboards/{SRC_DASH}/duplicate",
               body={"locationId": SRC_LOC, "targetLocationId": lid, "title": TITLE, "isPrivate": False,
                     "permissionAccess": PERMS})
    new_id = (r.get("data") or {}).get("targetDashboardId")
    if not new_id:
        return f"ERROR duplicate: {json.dumps(r)[:200]}"
    a.call("POST", SERVICES, f"/reporting/dashboards/{new_id}/permissions",
           body={"locationId": lid, "permissionAccess": PERMS, "isPrivate": False})
    a.call("POST", SERVICES, f"/reporting/dashboards/{new_id}/set-default", body={"locationId": lid})
    check = dash_list(a, lid).get("defaultDashboardId")
    if check != new_id:
        return f"ERROR new copy {new_id} not default ({check}); old copy kept"
    ver = old.get("version") or 1
    a.call("DELETE", SERVICES, f"/reporting/dashboards/{old['_id']}", body={"locationId": lid, "version": ver - 1})
    left = [d["_id"] for d in all_dashboards(dash_list(a, lid)) if d.get("title") == TITLE]
    det = a.get(SERVICES, f"/reporting/dashboards/{new_id}", {"locationId": lid})["data"]
    bad = [w.get("title") for w in det.get("widgets") or []
           if any(f in json.dumps(w.get("objectWidgetOptions") or {}) for f in FOREIGN_EMBEDS)]
    return f"replaced {old['_id']} -> {new_id} (default yes, {len(det.get('widgets') or [])} widgets, " \
           f"embeds {bad or 'none'}, copies now {left})"


def run(a: Agency, loc: dict, apply: bool, do_replace: bool = False) -> str:
    lid, name = loc["id"], loc.get("name", "")
    data = dash_list(a, lid)
    dashes = all_dashboards(data)
    mine = [d for d in dashes if d.get("title") == TITLE]
    default = data.get("defaultDashboardId")
    if mine:
        det = a.get(SERVICES, f"/reporting/dashboards/{mine[0]['_id']}", {"locationId": lid})["data"]
        bad = [w.get("title") for w in det.get("widgets") or []
               if any(f in json.dumps(w.get("objectWidgetOptions") or {}) for f in FOREIGN_EMBEDS)]
        if bad:
            if apply and do_replace:
                return replace(a, lid, name, det, data)
            return f"FOREIGN EMBEDS (SwimReady): {bad} -> --apply --replace (or remove in the UI)"
    if mine and default == mine[0]["_id"]:
        return "ok (already default)"
    if not apply:
        return ("would set existing copy as default" if mine else "would copy + set default") + \
               f" (now: {len(dashes)} dashboards, default {default})"
    folder = os.path.join(ROOT, "backup", slugify(name))
    os.makedirs(folder, exist_ok=True)
    with open(os.path.join(folder, f"dashboards-{dt.date.today():%Y%m%d}.json"), "w") as fh:
        json.dump(data, fh, indent=1)
    if mine:
        new_id = mine[0]["_id"]
    else:
        r = a.call("POST", SERVICES, f"/reporting/dashboards/{SRC_DASH}/duplicate",
                   body={"locationId": SRC_LOC, "targetLocationId": lid, "title": TITLE, "isPrivate": False,
                         "permissionAccess": PERMS})
        new_id = (r.get("data") or {}).get("targetDashboardId")
        if not new_id:
            return f"ERROR duplicate: {json.dumps(r)[:200]}"
    a.call("POST", SERVICES, f"/reporting/dashboards/{new_id}/permissions",
           body={"locationId": lid, "permissionAccess": PERMS, "isPrivate": False})
    a.call("POST", SERVICES, f"/reporting/dashboards/{new_id}/set-default", body={"locationId": lid})
    check = dash_list(a, lid).get("defaultDashboardId")
    widgets = len(a.get(SERVICES, f"/reporting/dashboards/{new_id}", {"locationId": lid})["data"].get("widgets") or [])
    return f"{'copied' if not mine else 'existing'} {new_id}, default={'yes' if check == new_id else 'NO ' + str(check)}, " \
           f"{widgets} widgets"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", action="append", help="account name or id (repeatable)")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--replace", action="store_true", help="with --apply: swap copies that carry SwimReady embeds")
    args = ap.parse_args()
    a = Agency()
    locs = a.locations()
    if args.only:
        targets = [match_location(locs, o) for o in args.only]
        if None in targets:
            sys.exit(f"not found: {[o for o, t in zip(args.only, targets) if t is None]}")
    else:
        targets = [l for l in locs if l["id"] not in SKIP]
    for loc in sorted(targets, key=lambda l: l.get("name", "")):
        try:
            res = run(a, loc, args.apply, args.replace)
        except GHLError as exc:
            res = f"ERROR {exc}"
        print(f"{loc.get('name', '')[:38]:38} {res}")


if __name__ == "__main__":
    main()
