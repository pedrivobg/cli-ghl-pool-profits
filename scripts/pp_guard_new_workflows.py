#!/usr/bin/env python3
"""Watch a sub-account while a snapshot is loaded into it and put every NEW published workflow in draft at once.

    set -a; . <scratchpad>/burchtech.env; set +a
    ./.venv/bin/python scripts/pp_guard_new_workflows.py --loc KjLd769fprQ2EaBI9Cro --minutes 120

For a live account (BurchTech's The Pool Keepers, 21/10): a snapshot can bring its workflows in published (seen at the
Pool Shack), and they would start firing on real calls and contacts. The workflows that exist when the guard starts
are the baseline and are never touched. Each new one that shows up published is backed up and PUT back as draft.
Stops after --minutes, or 10 minutes after the last new workflow appeared (the load is over).
"""
from __future__ import annotations

import argparse
import json
import sys
import time

from _common import ROOT, load_dotenv, slugify

from cli_anything.gohighlevel.utils.agency import BACKEND, Agency, GHLError


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--loc", required=True)
    parser.add_argument("--minutes", type=int, default=120)
    parser.add_argument("--every", type=int, default=10, help="seconds between checks")
    args = parser.parse_args()
    load_dotenv()
    a = Agency()
    name = a.location(args.loc)["name"]
    base = {w["id"] for w in a.workflows(args.loc)}
    bdir = ROOT / "backup" / slugify(name)
    bdir.mkdir(parents=True, exist_ok=True)
    print(f"{time.strftime('%H:%M:%S')} {name}: {len(base)} workflows na linha de base (não mexo neles)", flush=True)
    seen, drafted, last_new = set(), [], None
    end = time.time() + args.minutes * 60
    while time.time() < end and not (last_new and time.time() - last_new > 600):
        try:
            flows = a.workflows(args.loc)
        except GHLError as e:
            print(f"{time.strftime('%H:%M:%S')} erro lendo: {e}", flush=True)
            time.sleep(args.every)
            continue
        for w in flows:
            if w["id"] in base:
                continue
            if w["id"] not in seen:
                seen.add(w["id"])
                last_new = time.time()
                print(f"{time.strftime('%H:%M:%S')} novo: {w['name']} [{w['status']}]", flush=True)
            if w["status"] != "published":
                continue
            try:
                live = a.workflow(args.loc, w["id"])
                (bdir / f"workflow-{w['id']}-{time.strftime('%Y%m%d-%H%M%S')}.json").write_text(json.dumps(live))
                a.call("PUT", BACKEND, f"/workflow/{args.loc}/{w['id']}", body={
                    "name": live["name"], "version": live.get("version", 1), "status": "draft",
                    "parentId": live.get("parentId"),
                    "workflowData": {"templates": live.get("workflowData", {}).get("templates", [])}})
                drafted.append(live["name"])
                print(f"{time.strftime('%H:%M:%S')}   → draft: {live['name']}", flush=True)
            except GHLError as e:
                print(f"{time.strftime('%H:%M:%S')}   ✗ não consegui pôr em draft {w['name']}: {e}", flush=True)
        time.sleep(args.every)
    final = {w["id"]: w for w in a.workflows(args.loc)}
    still = [w["name"] for i, w in final.items() if i not in base and w["status"] == "published"]
    print(f"{time.strftime('%H:%M:%S')} fim: {len(seen)} novos, {len(drafted)} postos em draft, "
          f"publicados ainda: {still or 'nenhum'}; linha de base intacta: "
          f"{all(final.get(i) for i in base)}", flush=True)
    return 1 if still else 0


if __name__ == "__main__":
    sys.exit(main())
