#!/usr/bin/env python3
"""Existing IVR: tag "missed call" when nobody answers, so the missed-call text-back fires.

    ./.venv/bin/python scripts/pp_ivr_missed.py --only "NORTEX" --ivr "IVR SPAM Detection"            # plan
    ./.venv/bin/python scripts/pp_ivr_missed.py --only "NORTEX" --ivr "IVR SPAM Detection" --apply

With an IVR every inbound call ends "completed", so "Missed Incoming Call To Pipeline" (call status)
never fires; "Missed New Lead - Initial SMS Follow-up" starts on the "missed call" tag instead
(Frank, 20/10: Nortex has an IVR and no follow-up texts go out). In every branch that follows a
"connect call" check `dialCallStatus != completed`, an Add Tag "missed call" step goes first, before
the voicemail. New IVRs built by pp_ivr.py already have it. Backup in backup/<slug>/.
"""
from __future__ import annotations

import argparse
import json
import time
import uuid

from _common import ROOT, load_dotenv, location_dirs
from pp_audit import load

from cli_anything.gohighlevel.utils.agency import BACKEND, Agency

TAG = "missed call"


def not_answered_branches(tpl: list[dict]) -> list[dict]:
    """branch-yes nodes of if/else that test the connect call status != completed."""
    out = []
    for c in tpl:
        if c.get("nodeType") != "condition-node":
            continue
        conds = [x for b in (c.get("attributes") or {}).get("branches") or [] for seg in b.get("segments") or []
                 for x in seg.get("conditions") or []]
        if any(x.get("conditionType") == "ivr_connect_call" and "dialCallStatus" in str(x.get("conditionSubType"))
               and x.get("conditionOperator") == "!=" and x.get("conditionValue") == "completed" for x in conds):
            out += [s for s in tpl if s.get("parent") == c["id"] and s.get("nodeType") == "branch-yes"]
    return out


def mark(tpl: list[dict]) -> tuple[list[dict], int]:
    tpl = json.loads(json.dumps(tpl))
    by = {s["id"]: s for s in tpl}
    added = 0
    for br in not_answered_branches(tpl):
        first = by.get(br.get("next")) if isinstance(br.get("next"), str) else None
        if first and first["type"] == "add_contact_tag" and TAG in first["attributes"].get("tags", []):
            continue
        step = {"id": str(uuid.uuid4()), "order": 0, "name": "Add Tag missed call", "type": "add_contact_tag",
                "parent": br["id"], "parentKey": br["id"], "attributes": {"tags": [TAG], "type": "add_contact_tag"}}
        if first:
            step["next"] = first["id"]
            first["parentKey"] = step["id"]
            cur = first
            while cur:  # the rest of the branch moves down one
                cur["order"] = cur.get("order", 0) + 1
                cur = by.get(cur.get("next")) if isinstance(cur.get("next"), str) else None
        br["next"] = step["id"]
        tpl.append(step)
        by[step["id"]] = step
        added += 1
    return tpl, added


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--only", action="append", required=True)
    parser.add_argument("--ivr", required=True, help="IVR workflow name")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    load_dotenv()
    a = Agency()
    bad = 0
    for d in location_dirs(args.only):
        loc = load(d / "location.json", {})["id"]
        w = next(w for w in a.workflows(loc) if w["name"] == args.ivr)
        live = a.workflow(loc, w["id"])
        new, added = mark(live["workflowData"]["templates"])
        print(f"== {d.name} · {args.ivr} [{live['status']}]: {added} ramo(s) 'não atendeu' ganham a tag '{TAG}'")
        if not args.apply or not added:
            continue
        try:
            a.call("POST", BACKEND, f"/workflow/{loc}/tags/create", body={"tag": TAG})
        except Exception:  # noqa: BLE001 — already exists
            pass
        bdir = ROOT / "backup" / d.name
        bdir.mkdir(parents=True, exist_ok=True)
        trs = [t for t in a.triggers(loc, w["id"]) if not t.get("deleted")]
        (bdir / f"workflow-{w['id']}-{time.strftime('%Y%m%d-%H%M%S')}.json").write_text(
            json.dumps({"workflow": live, "triggers": trs}))
        a.call("PUT", BACKEND, f"/workflow/{loc}/{w['id']}", body={
            "name": live["name"], "version": live.get("version", 1), "status": live["status"],
            "parentId": live.get("parentId"), "allowMultiple": live.get("allowMultiple", True),
            "workflowData": {"templates": new}})
        time.sleep(4)
        got = a.workflow(loc, w["id"])
        t2 = got["workflowData"]["templates"]
        ids = {s["id"] for s in t2}
        refs = [r for s in t2 for r in ([s.get("next")] if isinstance(s.get("next"), str) else s.get("next") or [])]
        refs += [s[k] for s in t2 for k in ("parent", "parentKey") if s.get(k)]
        ok = got["status"] == live["status"] and len(t2) == len(new) and all(r in ids for r in refs) and \
            mark(t2)[1] == 0
        bad += not ok
        print(f"   {'✓' if ok else '✗ VERIFICAR'} {got['status']} · {len(t2)} passos")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
