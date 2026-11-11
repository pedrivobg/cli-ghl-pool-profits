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
SWIM_PLACE = "ChIJS_4iU3DDGgoRbPjauVQYjNE"  # SwimReady's Google place, left in the GMB widget preference of every copy
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


def fix_gmb(a: Agency, lid: str, dash_id: str, det: dict, apply: bool) -> bool:
    """The GMB widget keeps SwimReady's place as its page filter: point it at the account's own place (or clear it)."""
    prefs = [p for p in det.get("widgetPreferences") or [] if SWIM_PLACE in json.dumps(p)]
    if not prefs or not apply:
        return bool(prefs)
    own = a.location(lid).get("googlePlacesId") or ""
    for p in prefs:
        opts = json.loads(json.dumps(p.get("options") or {}).replace(SWIM_PLACE, own))
        a.call("PUT", SERVICES, f"/reporting/dashboards/{dash_id}/widget-preference",
               body={"locationId": lid, "widgetId": p["widgetId"], "options": opts})
    return True


def run(a: Agency, loc: dict, apply: bool, replace: bool = False) -> str:
    lid, name = loc["id"], loc.get("name", "")
    data = dash_list(a, lid)
    dashes = all_dashboards(data)
    mine = [d for d in dashes if d.get("title") == TITLE]
    default = data.get("defaultDashboardId")
    if len(mine) > 1:  # an interrupted recopy leaves two: keep a clean one as default, delete the ones with embeds
        dets = {d["_id"]: a.get(SERVICES, f"/reporting/dashboards/{d['_id']}", {"locationId": lid})["data"] for d in mine}
        dirty = [i for i, dd in dets.items() if any(f in json.dumps(dd) for f in FOREIGN_EMBEDS)]
        clean = [i for i in dets if i not in dirty]
        if clean and apply and replace:
            res = make_default(a, lid, clean[0], "existing clean")
            for i in dirty:
                a.call("DELETE", SERVICES, f"/reporting/dashboards/{i}",
                       body={"locationId": lid, "version": (dets[i].get("dashboard") or {}).get("curVer", 1) - 1})
            return f"{res}; {len(dirty)} copy(ies) with SwimReady embeds deleted"
        if clean:
            return f"{len(mine)} copies, {len(dirty)} with SwimReady embeds -> --replace-embeds"
        mine = mine[:1]
    if mine:
        det = a.get(SERVICES, f"/reporting/dashboards/{mine[0]['_id']}", {"locationId": lid})["data"]
        bad = [w.get("title") for w in det.get("widgets") or []
               if any(f in json.dumps(w.get("objectWidgetOptions") or {}) for f in FOREIGN_EMBEDS)]
        if bad and not (apply and replace):
            return f"FOREIGN EMBEDS (SwimReady): {bad} -> --replace-embeds to recopy the clean one"
        if bad:  # our own 10/11 copy: delete it and copy the clean source again
            folder = os.path.join(ROOT, "backup", slugify(name))
            os.makedirs(folder, exist_ok=True)
            with open(os.path.join(folder, f"dashboard-{mine[0]['_id']}-{dt.date.today():%Y%m%d}.json"), "w") as fh:
                json.dump(det, fh, indent=1)
            old_id, old_ver = mine[0]["_id"], (det.get("dashboard") or {}).get("curVer", 1)
            res = copy_clean(a, lid)  # the default can't be deleted: new copy becomes default first
            if not res.startswith("copied") or "default=yes" not in res:
                return f"ERROR recopy: {res}"
            a.call("DELETE", SERVICES, f"/reporting/dashboards/{old_id}", body={"locationId": lid, "version": old_ver - 1})
            left = [d for d in all_dashboards(dash_list(a, lid)) if d["_id"] == old_id]
            return f"replaced (SwimReady embeds): {res}; old copy {'STILL THERE' if left else 'deleted'}"
        elif fix_gmb(a, lid, mine[0]["_id"], det, apply):
            if default == mine[0]["_id"]:
                return "ok (already default) + GMB widget → own place" + ("" if apply else " (plan)")
    if mine and default == mine[0]["_id"]:
        return "ok (already default)"
    if not apply:
        return ("would set existing copy as default" if mine else "would copy + set default") + \
               f" (now: {len(dashes)} dashboards, default {default})"
    folder = os.path.join(ROOT, "backup", slugify(name))
    os.makedirs(folder, exist_ok=True)
    with open(os.path.join(folder, f"dashboards-{dt.date.today():%Y%m%d}.json"), "w") as fh:
        json.dump(data, fh, indent=1)
    if not mine:
        return copy_clean(a, lid)
    return make_default(a, lid, mine[0]["_id"], "existing")


def copy_clean(a: Agency, lid: str) -> str:
    r = a.call("POST", SERVICES, f"/reporting/dashboards/{SRC_DASH}/duplicate",
               body={"locationId": SRC_LOC, "targetLocationId": lid, "title": TITLE, "isPrivate": False,
                     "permissionAccess": PERMS})
    new_id = (r.get("data") or {}).get("targetDashboardId")
    if not new_id:
        return f"ERROR duplicate: {json.dumps(r)[:200]}"
    return make_default(a, lid, new_id, "copied")


def make_default(a: Agency, lid: str, new_id: str, how: str) -> str:
    a.call("POST", SERVICES, f"/reporting/dashboards/{new_id}/permissions",
           body={"locationId": lid, "permissionAccess": PERMS, "isPrivate": False})
    a.call("POST", SERVICES, f"/reporting/dashboards/{new_id}/set-default", body={"locationId": lid})
    fix_gmb(a, lid, new_id, a.get(SERVICES, f"/reporting/dashboards/{new_id}", {"locationId": lid})["data"], True)
    check = dash_list(a, lid).get("defaultDashboardId")
    widgets = len(a.get(SERVICES, f"/reporting/dashboards/{new_id}", {"locationId": lid})["data"].get("widgets") or [])
    return f"{how} {new_id}, default={'yes' if check == new_id else 'NO ' + str(check)}, {widgets} widgets"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", action="append", help="account name or id (repeatable)")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--replace-embeds", action="store_true", help="recopy our copies that still carry SwimReady's embeds")
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
            res = run(a, loc, args.apply, args.replace_embeds)
        except Exception as exc:  # noqa: BLE001 — a timeout on one account must not stop the rest
            res = f"ERROR {str(exc)[:200]}"
        print(f"{loc.get('name', '')[:38]:38} {res}", flush=True)


if __name__ == "__main__":
    main()
