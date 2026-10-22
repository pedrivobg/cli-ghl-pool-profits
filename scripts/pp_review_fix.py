#!/usr/bin/env python3
"""Review Request: the "First Request?" check was inverted since the V9 snapshot (found 22/10, Pedro OK'd the fix).

    ./.venv/bin/python scripts/pp_review_fix.py                 # plan, every sub-account the token opens
    ./.venv/bin/python scripts/pp_review_fix.py --apply
    ./.venv/bin/python scripts/pp_review_fix.py --only "Test Snapshot" --apply

After the wait that follows a Won stage, "First Request?" asked "NPS Score has_value" and its YES branch sends the
rating text. A customer who never rated has an empty score, so they fell into NO and left the workflow: nobody got
the rating text nor the Google review request (tested live on the Test Snapshot: empty → NO, filled → YES). The
intent, by the name, is "no rating yet → ask". Fix: has_value → has_no_value (empty → YES; tested the same way).
Only that condition changes. Status and every other setting stay as they are; GET + backup before each PUT.
BurchTech (The Pool Keepers drafts): load burchtech.env.
"""
from __future__ import annotations

import argparse
import json
import sys
import time

from _common import ROOT, load_dotenv, slugify

from cli_anything.gohighlevel.utils.agency import BACKEND, Agency, GHLError

CHECK = "First Request?"


def inverted(tpl: list[dict]) -> list[dict]:
    """The "First Request?" conditions still on has_value."""
    out = []
    for st in tpl:
        a = st.get("attributes") or {}
        if st.get("type") != "if_else" or a.get("conditionName") != CHECK:
            continue
        for b in a.get("branches") or []:
            for seg in b.get("segments") or []:
                for c in seg.get("conditions") or []:
                    if c.get("conditionType") == "contact_detail" and c.get("conditionOperator") == "has_value":
                        out.append(c)
    return out


def read(a: Agency, loc: str, wid: str) -> dict:
    for i in range(3):  # backend reads sometimes 503 for a moment
        try:
            return a.workflow(loc, wid)
        except GHLError as e:
            if e.status < 500 or i == 2:
                raise
            time.sleep(5)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--only", action="append", default=[], help="sub-account name contains this (repeatable)")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    load_dotenv()
    a = Agency()
    stamp = time.strftime("%Y%m%d-%H%M%S")
    locs = [l for l in a.locations() if not args.only or any(o.lower() in l["name"].lower() for o in args.only)]
    fixed = bad = 0
    for loc in sorted(locs, key=lambda l: l["name"].lower()):
        try:
            flows = [w for w in a.workflows(loc["id"]) if "review request" in w["name"].lower()]
        except GHLError as e:
            print(f"   ? {loc['name']}: {e.status}")
            continue
        for w in flows:
            live = read(a, loc["id"], w["id"])
            tpl = json.loads(json.dumps(live["workflowData"]["templates"]))
            conds = inverted(tpl)
            if not conds:
                continue
            print(f"   {loc['name']} / {live['name']} [{live['status']}]: {len(conds)} condição(ões) has_value → has_no_value")
            if not args.apply:
                continue
            bdir = ROOT / "backup" / slugify(loc["name"])
            bdir.mkdir(parents=True, exist_ok=True)
            (bdir / f"workflow-{w['id']}-{stamp}.json").write_text(json.dumps(live))
            for c in conds:
                c["conditionOperator"] = "has_no_value"
            a.call("PUT", BACKEND, f"/workflow/{loc['id']}/{w['id']}", body={
                "name": live["name"], "version": live.get("version", 1), "status": live["status"],
                "parentId": live.get("parentId"), "workflowData": {"templates": tpl}})
            time.sleep(2)
            got = read(a, loc["id"], w["id"])
            ok = not inverted(got["workflowData"]["templates"]) and got["status"] == live["status"] and \
                len(got["workflowData"]["templates"]) == len(tpl) and got.get("allowMultiple") == live.get("allowMultiple")
            fixed += ok
            bad += not ok
            print(f"      {'✓' if ok else '✗ VERIFICAR'} {got['status']} · re-entry {got.get('allowMultiple')}")
    if args.apply:
        print(f"{fixed} corrigido(s), {bad} a verificar")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
