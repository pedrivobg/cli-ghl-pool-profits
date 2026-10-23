#!/usr/bin/env python3
"""If/else "which trigger fired?" pointing at triggers of ANOTHER workflow (found 23/10).

    ./.venv/bin/python scripts/pp_trigger_ref_fix.py                       # plan, every sub-account the token opens
    ./.venv/bin/python scripts/pp_trigger_ref_fix.py --only "Test Snapshot" --apply
    ./.venv/bin/python scripts/pp_trigger_ref_fix.py --apply
    ... --save-index idx.json      (Pool Profits) → ... --index idx.json --apply   (BurchTech: ids of the other agency)

Won Stage ("Which Won stage?") and Review Request ("Won") branch with `conditionType: "trigger"`, `conditionValue: <trigger
id>`. Workflows copied by the mirror or loaded from the snapshot kept the trigger ids of the source workflow, which do not
exist in the target: no branch ever matches, so a Won card gets no welcome and no rating/review request (silently).
Fix: each foreign id → the workflow's own trigger on the stage with the same name (the source trigger's stage is
looked up in every sub-account the token opens). Only those values change; GET + backup before each PUT.
Read triggers with `Agency.triggers` (the workflow GET does not include them).
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from _common import ROOT, load_dotenv, slugify
from pp_review_fix import read

from cli_anything.gohighlevel.utils.agency import BACKEND, Agency, GHLError

NAMES = ("won stage", "review request")


def trigger_conds(o):
    if isinstance(o, dict):
        if o.get("conditionType") == "trigger":
            yield o
        for v in o.values():
            yield from trigger_conds(v)
    elif isinstance(o, list):
        for v in o:
            yield from trigger_conds(v)


def stage_of(t: dict, stages: dict[str, str]) -> str | None:
    sid = next((c.get("value") for c in t.get("conditions") or [] if c.get("field") == "opportunity.pipelineStageId"), None)
    return stages.get(sid)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--only", action="append", default=[], help="sub-account name contains this (repeatable)")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--save-index", help="write trigger id → stage of this agency to a JSON file")
    parser.add_argument("--index", help="extra trigger id → stage (JSON from --save-index of another agency)")
    args = parser.parse_args()
    load_dotenv()
    a = Agency()
    stamp = time.strftime("%Y%m%d-%H%M%S")
    found, index = [], {}  # index: trigger id → stage name, from every account
    for loc in sorted(a.locations(), key=lambda l: l["name"].lower()):
        try:
            flows = [w for w in a.workflows(loc["id"]) if w["name"].lower() in NAMES]
            stages = {s["id"]: s["name"] for p in a.pipelines(loc["id"]) for s in p.get("stages") or []} if flows else {}
        except GHLError as e:
            print(f"   ? {loc['name']}: {e.status}")
            continue
        for w in flows:
            trigs = [t for t in a.triggers(loc["id"], w["id"]) if not t.get("deleted")]
            for t in trigs:
                index[t["id"]] = stage_of(t, stages)
            found.append((loc, w, trigs, stages))
    if args.save_index:
        Path(args.save_index).write_text(json.dumps(index))
    if args.index:
        index = {**json.loads(Path(args.index).read_text()), **index}
    fixed = bad = 0
    for loc, w, trigs, stages in found:
        if args.only and not any(o.lower() in loc["name"].lower() for o in args.only):
            continue
        own = {t["id"] for t in trigs}
        by_stage = {stage_of(t, stages): t["id"] for t in trigs}
        live = read(a, loc["id"], w["id"])
        tpl = json.loads(json.dumps(live["workflowData"]["templates"]))
        alien = [c for st in tpl for c in trigger_conds(st.get("attributes") or {}) if c.get("conditionValue") not in own]
        if not alien:
            continue
        plan = [(c, index.get(c.get("conditionValue")), by_stage.get(index.get(c.get("conditionValue")))) for c in alien]
        missing = [str(src) for c, src, new in plan if not new]
        print(f"   {loc['name']} / {w['name']} [{live['status']}]: {len(alien)} id(s) de outro workflow → "
              + ", ".join(f"{src}" for _, src, _ in plan) + (f"  ✗ sem par: {missing}" if missing else ""))
        if missing or not args.apply:
            bad += bool(missing)
            continue
        bdir = ROOT / "backup" / slugify(loc["name"])
        bdir.mkdir(parents=True, exist_ok=True)
        (bdir / f"workflow-{w['id']}-{stamp}.json").write_text(json.dumps(live))
        for c, _, new in plan:
            c["conditionValue"] = new
        a.call("PUT", BACKEND, f"/workflow/{loc['id']}/{w['id']}", body={
            "name": live["name"], "version": live.get("version", 1), "status": live["status"],
            "parentId": live.get("parentId"), "workflowData": {"templates": tpl}})
        time.sleep(2)
        got = read(a, loc["id"], w["id"])
        left = [c for st in got["workflowData"]["templates"] for c in trigger_conds(st.get("attributes") or {})
                if c.get("conditionValue") not in own]
        ok = not left and got["status"] == live["status"] and len(got["workflowData"]["templates"]) == len(tpl) \
            and got.get("allowMultiple") == live.get("allowMultiple")
        fixed += ok
        bad += not ok
        print(f"      {'✓' if ok else '✗ VERIFICAR'} {got['status']} · re-entry {got.get('allowMultiple')}")
    if args.apply:
        print(f"{fixed} corrigido(s), {bad} a verificar")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
