#!/usr/bin/env python3
"""Google Ads "Converted Lead - WON" on every Won stage (Val 18/11, ClickUp 86bd4kucg).

    ./.venv/bin/python scripts/pp_won_ads.py plan  [--only <loc>]
    ./.venv/bin/python scripts/pp_won_ads.py apply [--only <loc>]
    GHL_AGENCY=poolduck ./.venv/bin/python scripts/pp_won_ads.py plan|apply   # Pool Duck sub-accounts

Same shape as Corolla's "Won -> Google Ads" (11/11): a new workflow with one step "Google Ads: Converted Lead - WON"
(offline upload with {{contact.attributionSource.gclid}}, so only contacts that came from an ad click count) and one
"Pipeline Stage Changed" trigger per Won stage. It only talks to Google Ads (no message, tag or card change), so it is
published. The existing "Adword Call/Form - Conversion" flows are left alone. The conversion must be listed by
GET /ad-publishing/google/conversions (account linked in Settings → Integrations → Google Ads).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import uuid

from _common import ROOT, load_dotenv

from cli_anything.gohighlevel.utils.agency import BACKEND, SERVICES, Agency

FLOW = "Won -> Google Ads"
CONV = "Converted Lead - WON"
GCLID = "{{contact.attributionSource.gclid}}"
ACCOUNTS = {  # Val's active Google Ads list (18/11)
    "default": ["gCv3a9Y76Zzx50EjglGU", "kSQdQ60Qv9JFriZwF1jk", "AjePy51fOb6BM1Kk2QQX", "NwHaw9wVRRVZtSLAqcfe",
                "SylIOZiJ6YQsZOypUI8Z", "GeeXTPcJXAoVUAmzLxfT", "ghUi89uCpNyNunNpbtAt", "jvu0xE8rfMFiT00he8m7",
                "KLFYmoVapqQgX3T0AnLn", "NbOZEj2whuSBHyXtZec1", "d03SMzI37dxTBeuoTJ13", "3CozZ1NfujYWEPIYgzx0",
                "k6nDPHktS2PySJoJuwpG", "FpRTQZR56xwp1Wg5NQCq"],
    "poolduck": ["uJr8H2qaQM5ffZxeYFqn", "MosKIX4oux96vchwHZ5W"],
}


def won_stages(a: Agency, loc: str) -> list[tuple[str, str, str]]:
    out = []
    for p in a.pipelines(loc):
        out += [(p["id"], s["id"], s["name"]) for s in p.get("stages", [])
                if "won" in s["name"].lower() and "lost" not in s["name"].lower()]
    return out


def create(a: Agency, loc: str, cid: str, stages: list[tuple[str, str, str]]) -> str:
    step = {"id": str(uuid.uuid4()), "order": 0, "name": f"Google Ads: {CONV}", "type": "google_adword",
            "attributes": {"type": "google_adword", "currency": "USD", "conversion_value": "1", "conversion_type": CONV,
                           "conversion_name": CONV, "conversion_action_id": cid, "customMapping": {"gclid": GCLID},
                           "isCustomMappingEnabled": True}}
    res = a.call("POST", BACKEND, f"/workflow/{loc}", body={"name": FLOW, "status": "draft"})
    wid = res.get("id") or res.get("_id")
    body = {"name": FLOW, "version": 1, "status": "draft", "allowMultiple": True, "workflowData": {"templates": [step]}}
    a.call("PUT", BACKEND, f"/workflow/{loc}/{wid}", body=body)
    for pid, sid, _ in stages:
        trig = {"type": "pipeline_stage_updated", "name": "Pipeline Stage Changed", "masterType": "highlevel",
                "schedule_config": {}, "workflowId": wid, "workflow_id": wid, "location_id": loc,
                "targetActionId": step["id"], "actions": [{"workflow_id": wid, "type": "add_to_workflow"}],
                "conditions": [{"operator": "==", "field": "opportunity.pipelineId", "value": pid, "title": "In pipeline", "type": "select"},
                               {"operator": "==", "field": "opportunity.pipelineStageId", "value": sid, "title": "Pipeline stage", "type": "select"}]}
        t = a.call("POST", BACKEND, f"/workflow/{loc}/trigger", body=trig)
        a.call("PUT", BACKEND, f"/workflow/{loc}/trigger/{t['id']}", body={**trig, "id": t["id"]})
    live = a.workflow(loc, wid)
    a.call("PUT", BACKEND, f"/workflow/{loc}/{wid}", body={**body, "status": "published", "version": live.get("version", 1),
                                                         "workflowData": {"templates": live["workflowData"]["templates"]}})
    return wid


def check(a: Agency, loc: str, wid: str, cid: str, stages: list) -> str:
    wf = a.workflow(loc, wid)
    st = [s["attributes"] for s in wf["workflowData"]["templates"] if s["type"] == "google_adword"]
    trs = [t for t in a.triggers(loc, wid) if not t.get("deleted")]
    got = {c["value"] for t in trs for c in t.get("conditions", []) if c.get("field") == "opportunity.pipelineStageId"}
    ok = (wf["status"] == "published" and len(st) == 1 and st[0].get("conversion_action_id") == cid
          and got == {s[1] for s in stages} and all(t.get("active") for t in trs))
    return f"{'✓' if ok else '✗ VERIFICAR'} {wf['status']} · conv {st[0].get('conversion_action_id') if st else '-'} · {len(trs)} gatilhos"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("mode", choices=["plan", "apply"])
    parser.add_argument("--only")
    args = parser.parse_args()
    load_dotenv()
    a = Agency()
    locs = [args.only] if args.only else ACCOUNTS.get(os.environ.get("GHL_AGENCY") or "default", [])
    bdir = ROOT / "backup" / "won-ads"
    bdir.mkdir(parents=True, exist_ok=True)
    for loc in locs:
        name = a.location(loc)["name"]
        try:
            rows = a.call("GET", SERVICES, "/ad-publishing/google/conversions", params={"locationId": loc})
        except Exception as e:  # noqa: BLE001
            print(f"✗ {name}: conversões não listam ({str(e)[-80:]})")
            continue
        cid = next((r["conversion_action_id"] for r in rows if r["conversion_name"] == CONV), None)
        stages = won_stages(a, loc)
        have = [w for w in a.workflows(loc) if w["name"] == FLOW]
        print(f"{name}: conv={cid} · Won={[s[2] for s in stages]} · {'existe' if have else 'cria'}")
        if not cid or not stages:
            print("   ✗ sem conversão ou sem etapa Won: pulado")
            continue
        if have:
            print(f"   {check(a, loc, have[0]['id'], cid, stages)}")
            continue
        if args.mode == "apply":
            (bdir / f"{loc}-{time.strftime('%Y%m%d-%H%M%S')}.json").write_text(json.dumps({"conversions": rows, "stages": stages}))
            wid = create(a, loc, cid, stages)
            time.sleep(3)
            print(f"   {check(a, loc, wid, cid, stages)} · {wid}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
