#!/usr/bin/env python3
"""Pool Duck, every sub-account (Pedro 23/11, after LWR): do leads land only in the V9 pipeline ("Pool Leads" /
"01. Pool Leads")? Read-only.

    GHL_AGENCY=poolduck python3 scripts/pd_pipeline_audit.py

Per account: pipelines; PUBLISHED workflows whose steps or triggers use another pipeline (create/update card, stage
triggers); cards per pipeline (open ones outside the V9 pipeline listed, with test-looking names flagged).
"""
from __future__ import annotations

import collections
import json
import re
import time

from _common import Agency, load_dotenv
from cli_anything.gohighlevel.utils.agency import SERVICES

TEST = re.compile(r"\btest\b|please ignore|zz test", re.I)


def v9(pipes: list[dict]) -> dict | None:
    return next((p for p in pipes if re.sub(r"^\d+\.\s*", "", p["name"]).strip() == "Pool Leads"), None)


def retry(f, *a):
    for i in range(4):
        try:
            return f(*a)
        except Exception:  # noqa: BLE001
            if i == 3:
                raise
            time.sleep(3)


def main() -> int:
    load_dotenv()
    a = Agency()
    for loc in sorted(a.locations(), key=lambda x: x["name"]):
        lid = loc["id"]
        pipes = retry(lambda: a.call("GET", SERVICES, "/opportunities/pipelines", params={"locationId": lid})["pipelines"])
        new = v9(pipes)
        print(f"\n== {loc['name']} ({lid}) · pipelines: {[p['name'] for p in pipes]}")
        if not new:
            print("   (no V9 'Pool Leads' pipeline)")
            continue
        others = {p["id"]: p["name"] for p in pipes if p["id"] != new["id"]}
        pub = [w for w in a.workflows(lid) if w["status"] == "published"]
        for w in pub:
            wf = retry(a.workflow, lid, w["id"])
            trs = retry(a.triggers, lid, w["id"])
            blob = json.dumps(wf.get("workflowData")) + json.dumps(trs)
            used = [n for pid, n in others.items() if pid in blob]
            if used:
                kinds = sorted({s["type"] for s in wf["workflowData"]["templates"]
                                if any(pid in json.dumps(s.get("attributes")) for pid in others)})
                tk = sorted({t.get("type") for t in trs if any(pid in json.dumps(t) for pid in others)})
                print(f"   !! published '{w['name']}' uses {used} · steps {kinds} · triggers {tk}")
        opps, page = [], 1
        while True:
            r = retry(lambda: a.call("GET", SERVICES, "/opportunities/search",
                                     params={"location_id": lid, "limit": 100, "page": page}))
            opps += r.get("opportunities", [])
            if len(r.get("opportunities", [])) < 100:
                break
            page += 1
        names = {p["id"]: p["name"] for p in pipes}
        print(f"   published {len(pub)} · cards {dict(collections.Counter(names.get(o['pipelineId']) for o in opps))}")
        for o in opps:
            if o["pipelineId"] != new["id"]:
                flag = " [TEST?]" if TEST.search(o.get("name") or "") else ""
                print(f"     - {names.get(o['pipelineId'])} · {o.get('status')} · {o.get('createdAt', '')[:10]} · "
                      f"{o.get('name') or '(no name)'}{flag}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
