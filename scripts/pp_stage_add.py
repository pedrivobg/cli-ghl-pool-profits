#!/usr/bin/env python3
"""Add a stage to an account's lead pipeline (existing stage ids are kept).

    ./.venv/bin/python scripts/pp_stage_add.py --only "Passion" --name "📍 Out Of Area" --after "not qualified"
    ./.venv/bin/python scripts/pp_stage_add.py --only "Passion" --name "📍 Out Of Area" --after "not qualified" --apply

Frank (17/10, Passion): "Lets add an Out Of Area tab on the pipeline". Same idea as BluVantage's
"Out of Service Area". --after matches part of a stage name (case-insensitive); without it the stage
goes before Lost. Backup of the pipeline in backup/<slug>/ before the PUT.
"""
from __future__ import annotations

import argparse
import json
import time

from _common import ROOT, load_dotenv, location_dirs
from pp_audit import load

from cli_anything.gohighlevel.utils.agency import SERVICES, Agency


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--only", action="append", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--after", help="part of the stage name to insert after (default: before Lost)")
    parser.add_argument("--pipeline", help="part of the pipeline name (default: the first one)")
    parser.add_argument("--color", default="#64748B")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    load_dotenv()
    a = Agency()
    bad = 0
    for d in location_dirs(args.only):
        loc = load(d / "location.json", {})["id"]
        pipes = a.pipelines(loc)
        p = next((p for p in pipes if args.pipeline.lower() in p["name"].lower()), None) if args.pipeline else pipes[0]
        if not p:
            raise SystemExit(f"{d.name}: pipeline {args.pipeline!r} não encontrado")
        stages = p["stages"]
        names = [s["name"] for s in stages]
        print(f"== {d.name}: {p['name']}\n   antes:  {' | '.join(names)}")
        if any(args.name.lower().strip() == n.lower().strip() for n in names):
            print("   já existe")
            continue
        if args.after:
            at = next((i + 1 for i, s in enumerate(stages) if args.after.lower() in s["name"].lower()), None)
            if at is None:
                raise SystemExit(f"{d.name}: etapa {args.after!r} não encontrada")
        else:
            at = next((i for i, s in enumerate(stages) if "lost" in s["name"].lower()), len(stages))
        new = [dict(s) for s in stages]
        new[at:at] = [{"name": args.name, "color": args.color, "stageWinProbability": 0,
                       "showInFunnel": True, "showInPieChart": True}]
        for i, s in enumerate(new):
            s["position"] = i
        after = [s["name"] for s in new]
        print(f"   depois: {' | '.join(after)}")
        if not args.apply:
            continue
        bdir = ROOT / "backup" / d.name
        bdir.mkdir(parents=True, exist_ok=True)
        (bdir / f"pipeline-{p['id']}-{time.strftime('%Y%m%d-%H%M%S')}.json").write_text(json.dumps(p, ensure_ascii=False))
        a.call("PUT", SERVICES, f"/opportunities/pipelines/{p['id']}", body={"name": p["name"], "stages": new})
        for _ in range(24):  # reads lag behind the write (Passion 17/10: ~1 min)
            got = next(x for x in a.pipelines(loc) if x["id"] == p["id"])
            if [s["name"] for s in got["stages"]] == after:
                break
            time.sleep(5)
        kept = {s["id"] for s in stages} <= {s["id"] for s in got["stages"]}
        ok = [s["name"] for s in got["stages"]] == after and kept
        bad += not ok
        print(f"   {'✓' if ok else '✗ VERIFICAR'} etapa criada; ids antigos preservados: {kept}")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
