#!/usr/bin/env python3
"""Poolheads: structure changes from Felipe's CRM guide answers (12/11). Texts are in config/poolheads_wording.json (pp_wording).

    ./.venv/bin/python scripts/ph_guide_flows.py [--apply]

- Quote Sent Follow-up: M6 3 days after the card moves (was 1), M7 7 days after (reply wait 2 → 4 days); re-entry off.
- No Response Follow-up: re-entry off (decision "start over when the card moves back?" = NO).
- Reactivation Campaign - SMS: M20 removed; M21 2 weeks after M19 (SMS 1 → wait 14 days → SMS 3 → tag).
- Reactivation Campaign - Email: M23 and M24 removed (Email 1 → tag).
All four are drafts in Poolheads (go-live pending); status, triggers and every other step are kept. Backup first.
"""
from __future__ import annotations

import argparse
import json
import sys
import time

from _common import ROOT, load_dotenv

from cli_anything.gohighlevel.utils.agency import BACKEND, Agency

LOC = "PeUynYCMm8e6PJMy785O"


def drop(tpl: list[dict], ids: list[str]) -> list[dict]:
    """Remove linear steps: whoever pointed at a removed step now points at its `next`."""
    by = {s["id"]: s for s in tpl}
    for i in ids:
        s = by[i]
        nxt, parent = s.get("next"), s.get("parentKey")
        for o in tpl:
            if o.get("next") == i:
                o["next"] = nxt
        if nxt and nxt in by:
            by[nxt]["parentKey"] = parent
    return [s for s in tpl if s["id"] not in ids]


def wait_days(s: dict, days: int, name: str | None = None) -> None:
    s["attributes"]["startAfter"]["value"] = days
    s["attributes"]["startAfter"]["type"] = "days"
    if name:
        s["name"] = name


def edit(name: str, tpl: list[dict], wf: dict) -> list[str]:
    by = {s.get("name"): s for s in tpl}
    sid = {s["id"][:8]: s for s in tpl}
    log = []
    if name == "Quote Sent Follow-up":
        wait_days(by["Wait 1 day"], 3, "Wait 3 days"); log.append("Wait 1 day → 3 days")
        wait_days(sid["0dd462a6"], 4); log.append("reply wait after SMS 1: 2 → 4 days (SMS 2 = day 7)")
    if name == "Reactivation Campaign - SMS":
        tpl[:] = drop(tpl, [sid["79a03f07"]["id"], sid["9bb308b5"]["id"]])
        wait_days(sid["ce656654"], 14, "Wait 2 weeks"); log.append("SMS 2 + Wait 4 days removed; Wait 3 days → 2 weeks")
    if name == "Reactivation Campaign - Email":
        tpl[:] = drop(tpl, [sid[k]["id"] for k in ("ce656654", "3c8d0517", "9bb308b5", "f10a8aba")])
        log.append("Email 2, Email 3 and their waits removed")
    if name in ("Quote Sent Follow-up", "No Response Follow-up") and wf.get("allowMultiple") is not False:
        log.append("re-entry off")
    return log


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    load_dotenv()
    a = Agency()
    names = ["Quote Sent Follow-up", "No Response Follow-up", "Reactivation Campaign - SMS", "Reactivation Campaign - Email"]
    flows = {w["name"]: w for w in a.workflows(LOC) if w["name"] in names}
    bdir = ROOT / "backup" / "poolheads"
    bdir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    for n in names:
        wf = a.workflow(LOC, flows[n]["id"])
        tpl = json.loads(json.dumps(wf["workflowData"]["templates"]))
        try:
            log = edit(n, tpl, wf)
        except KeyError as e:
            print(f"  = {n}: já aplicado? ({e})")
            continue
        print(f"  {'✓' if args.apply else '→'} {n} [{wf['status']}]: {'; '.join(log) or 'nada'}")
        if not args.apply or not log:
            continue
        (bdir / f"workflow-{wf['id']}-{stamp}.json").write_text(json.dumps(wf, ensure_ascii=False))
        body = {"name": wf["name"], "version": wf.get("version", 1), "status": wf["status"], "parentId": wf.get("parentId"),
                "allowMultiple": False if n in ("Quote Sent Follow-up", "No Response Follow-up") else wf.get("allowMultiple", True),
                "workflowData": {"templates": tpl}}
        a.call("PUT", BACKEND, f"/workflow/{LOC}/{wf['id']}", body=body)
        time.sleep(2)
        got = a.workflow(LOC, wf["id"])
        ok = [s["id"] for s in got["workflowData"]["templates"]] == [s["id"] for s in tpl] and got["status"] == wf["status"]
        if n in ("Quote Sent Follow-up", "No Response Follow-up"):
            ok = ok and got.get("allowMultiple") is False
        print(f"     relido: {'ok' if ok else 'DIFERENTE — conferir'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
