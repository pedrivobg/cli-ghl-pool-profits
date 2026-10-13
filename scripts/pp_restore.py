#!/usr/bin/env python3
"""Put back any object saved in backup/ before a write.

    ./.venv/bin/python scripts/pp_restore.py --list "Bahama Blue"
    ./.venv/bin/python scripts/pp_restore.py --file backup/bahama-blue-pool-spa/workflow-<id>-<stamp>.json
    ./.venv/bin/python scripts/pp_restore.py --file ... --apply

Backups are named <kind>-<id>-<stamp>.json, kind = workflow | snippet | trigger |
pipeline | location. The oldest stamp of an id is its state before this
project touched it. Without --apply it only shows what would be written.
A deleted trigger is recreated (GHL gives it a new id).
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from _common import ROOT, load_dotenv, location_dirs
from pp_audit import load

from cli_anything.gohighlevel.utils.agency import BACKEND, SERVICES, Agency

DROP = ("_id", "date_added", "date_updated", "deleted", "origin_id", "company_id",
        "company_age", "last_conditions_change_at", "belongs_to")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--list")
    parser.add_argument("--file")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    if args.list:
        d = location_dirs([args.list])[0]
        for f in sorted((ROOT / "backup" / d.name).glob("*.json")):
            data = json.loads(f.read_text())
            print(f"  {f.name:75} {data.get('name') or data.get('type') or ''}")
        return 0

    path = Path(args.file)
    data = json.loads(path.read_text())
    kind, obj_id = re.match(r"(\w+)-(.+)-\d{8}-\d{6}\.json$", path.name).groups()
    loc = (obj_id if kind == "location" else None) or data.get("locationId") or data.get("location_id") \
        or load(ROOT / "dump" / path.parent.name / "location.json", {}).get("id")
    print(f"{kind} {obj_id} → location {loc}: {data.get('name') or data.get('type')}")
    if not args.apply:
        print("(dry-run — use --apply)")
        return 0
    load_dotenv()
    a = Agency()
    if kind == "workflow":
        live = a.workflow(loc, obj_id)
        a.call("PUT", BACKEND, f"/workflow/{loc}/{obj_id}", body={
            "name": data["name"], "version": live.get("version", 1), "status": data.get("status") or "draft",
            "parentId": data.get("parentId"),
            "workflowData": {"templates": (data.get("workflowData") or {}).get("templates") or []}})
    elif kind == "snippet":
        a.call("PUT", BACKEND, f"/snippets/{loc}/{obj_id}",
               body={"name": data["name"], "type": data["type"], "template": data["template"]})
    elif kind == "trigger":
        body = {k: v for k, v in data.items() if k not in DROP}
        wid = data["workflow_id"]
        if any(t["id"] == obj_id for t in a.triggers(loc, wid)):
            a.call("PUT", BACKEND, f"/workflow/{loc}/trigger/{obj_id}", body=body)
        else:
            body.pop("id", None)
            res = a.call("POST", BACKEND, f"/workflow/{loc}/trigger", body={**body, "workflowId": wid})
            a.call("PUT", BACKEND, f"/workflow/{loc}/trigger/{res['id']}", body={**body, "id": res["id"]})
    elif kind == "pipeline":
        keep = ("id", "name", "showInFunnel", "showInPieChart", "color", "position")
        a.call("PUT", SERVICES, f"/opportunities/pipelines/{obj_id}",
               body={"name": data["name"], "stages": [{k: s[k] for k in keep if k in s} for s in data["stages"]]})
    elif kind == "location":
        a.call("PUT", SERVICES, f"/locations/{obj_id}", body={"enableMissedCallText": data.get("enableMissedCallText")})
    print("✓ restaurado")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
