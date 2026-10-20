#!/usr/bin/env python3
"""Put back the workflow settings our PUTs reset (allow re-entry, send window, time zone mode).

    ./.venv/bin/python scripts/pp_wf_settings.py --only Poolheads                 # plan
    ./.venv/bin/python scripts/pp_wf_settings.py --only Poolheads --apply
    ./.venv/bin/python scripts/pp_wf_settings.py --all                            # every account with backups

Found 20/10: the workflow PUT resets to the default every setting the body leaves out, and our
scripts sent only name/status/steps — so each workflow they re-saved lost "allow re-entry"
(allowMultiple / allowMultipleOpportunity → false: a lead who had been through it once never got it
again, e.g. a second form or a second missed call) and, where it had one, its send window
(window → none, timezone contact → account). Agency.call now keeps them on every PUT.

Reference = the oldest backup of the workflow (taken right before our first write). Workflows we
created have no backup: re-entry comes from the master snapshot's workflow of the same name (or the
one it was copied from), else it is left alone. Only values at the reset default are put back
(false / no window / "account"), so a setting someone changed by hand later is kept.
"""
from __future__ import annotations

import argparse
import json
import time

from _common import ROOT, load_dotenv, location_dirs
from pp_audit import load

from cli_anything.gohighlevel.utils.agency import BACKEND, Agency

MASTER = "snapshot-pool-profits"
COPIED_FROM = {  # workflows we created → the snapshot workflow they were copied from
    "Missed Incoming Call To Pipeline": "Incoming Call To Pipeline",
    "Answered Incoming Call To Pipeline": "Incoming Call To Pipeline",
    "Missed New Lead - Initial SMS Follow-up": "New Lead - Initial SMS Follow-up",
}
FLAGS = ("allowMultiple", "allowMultipleOpportunity")


def oldest_backups(slug: str) -> dict[str, dict]:
    out: dict[str, dict] = {}
    files = sorted((ROOT / "backup" / slug).glob("workflow-*.json"), key=lambda f: f.stat().st_mtime)
    for f in files:
        try:
            data = json.loads(f.read_text())
        except ValueError:
            continue
        wf = data.get("workflow", data) if isinstance(data, dict) else {}
        wid = wf.get("id") or wf.get("_id")
        if wid and "allowMultiple" in wf and wf.get("allowMultipleOpportunity") is not None:
            out.setdefault(wid, wf)  # (None there = a workflow we had just created: no reference)
    return out


def wanted(live: dict, ref: dict | None, master: dict | None) -> dict:
    """Settings to put back: only where the live value is the default a PUT leaves behind."""
    fix = {}
    src = ref or master or {}
    for k in FLAGS:
        if src.get(k) is True and live.get(k) is not True:
            fix[k] = True
    if ref and ref.get("window") and not live.get("window"):
        fix["window"] = ref["window"]
    if ref and ref.get("timezone") and ref["timezone"] != live.get("timezone") and live.get("timezone") == "account":
        fix["timezone"] = ref["timezone"]
    return fix


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--only", action="append")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    if not args.only and not args.all:
        parser.error("--only or --all")
    load_dotenv()
    a = Agency()
    mdir = location_dirs([MASTER])[0]
    master = {w["name"]: load(mdir / "workflows" / f"{w['id']}.json", {})
              for w in load(mdir / "workflows" / "_index.json", [])}
    dirs = [d for d in location_dirs(args.only) if d.name != MASTER and (ROOT / "backup" / d.name).exists()]
    bad = total = 0
    for d in dirs:
        loc = load(d / "location.json", {})["id"]
        refs = oldest_backups(d.name)
        plan = []
        for w in a.workflows(loc):
            live = a.workflow(loc, w["id"])
            m = master.get(w["name"]) or master.get(COPIED_FROM.get(w["name"], ""))
            fix = wanted(live, refs.get(w["id"]), None if w["id"] in refs else m)
            if fix:
                plan.append((w, live, fix))
        print(f"== {d.name}: {len(plan)} workflow(s)")
        for w, live, fix in plan:
            print(f"   {w['name']} [{live['status']}]: " + ", ".join(
                f"{k} {json.dumps(live.get(k))} → {json.dumps(v)}" for k, v in fix.items()))
        if not args.apply or not plan:
            continue
        bdir = ROOT / "backup" / d.name
        stamp = time.strftime("%Y%m%d-%H%M%S")
        for w, live, fix in plan:
            total += 1
            (bdir / f"workflow-{w['id']}-{stamp}.json").write_text(json.dumps({"workflow": live}))
            a.call("PUT", BACKEND, f"/workflow/{loc}/{w['id']}", body={
                "name": live["name"], "version": live.get("version", 1), "status": live["status"],
                "parentId": live.get("parentId"), "workflowData": live["workflowData"], **fix})
        time.sleep(3)
        for w, live, fix in plan:
            got = a.workflow(loc, w["id"])
            ok = all(got.get(k) == v for k, v in fix.items()) and got["status"] == live["status"] and \
                len(got["workflowData"]["templates"]) == len(live["workflowData"]["templates"])
            bad += not ok
            if not ok:
                print(f"   ✗ VERIFICAR {w['name']}: " + ", ".join(f"{k}={json.dumps(got.get(k))}" for k in fix))
        print(f"   ✓ {len(plan) - bad} conferidos")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
