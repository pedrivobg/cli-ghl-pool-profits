#!/usr/bin/env python3
"""Pool Duck Lakewood Ranch: Google Ads line +1 941-541-5942 rings through the main phone menu (Val, 09/11), like the
main line 941-588-2227. Adds the number to the "Start IVR Trigger" of "Active - Phone Tree IVR" (same as
bv_call_numbers.py). "Google AdWords - Qualified Lead (Call In)" (call_status on that number) keeps firing with IVR.

    GHL_AGENCY=poolduck ./.venv/bin/python scripts/pd_lwr_ads_ivr.py plan|apply
GET + backup before the PUT; then re-reads the trigger and the line (inboundCallService should become the IVR).
"""
from __future__ import annotations

import json
import sys
import time

from _common import ROOT, load_dotenv
from pp_won_stage import DROP

from cli_anything.gohighlevel.utils.agency import BACKEND, SERVICES, Agency

LOC, IVR, NUMBER = "MosKIX4oux96vchwHZ5W", "Active - Phone Tree IVR", "+19415415942"
BDIR = ROOT / "backup" / "pool-duck-lakewood-ranch"


def line(a: Agency) -> dict:
    return next(n for n in a.call("GET", SERVICES, f"/phone-system/numbers/location/{LOC}").get("numbers", [])
                if n.get("phoneNumber") == NUMBER)


def main() -> int:
    apply = sys.argv[1:] == ["apply"]
    load_dotenv()
    a = Agency()
    if a.location(LOC)["name"] != "Pool Duck Lakewood Ranch":
        sys.exit("sub-conta errada")
    wid = next(w["id"] for w in a.workflows(LOC) if w["name"] == IVR and w.get("status") == "published")
    for t in [x for x in a.triggers(LOC, wid) if not x.get("deleted")]:
        cond = next(c for c in t["conditions"] if c.get("field") == "inbound_number")
        print(f"   {t['name']}: {cond['value']}")
        if NUMBER in cond["value"] or not apply:
            continue
        BDIR.mkdir(parents=True, exist_ok=True)
        (BDIR / f"trigger-{t['id']}-{time.strftime('%Y%m%d-%H%M%S')}.json").write_text(json.dumps(t))
        cond["value"] = [*cond["value"], NUMBER]
        body = {k: v for k, v in t.items() if k not in DROP}
        body.update({"workflowId": wid, "workflow_id": wid, "location_id": LOC})
        a.call("PUT", BACKEND, f"/workflow/{LOC}/trigger/{t['id']}", body=body)
    if apply:
        time.sleep(15)
        for t in a.triggers(LOC, wid):
            print(f"   reread {t['name']}: active={t.get('active')} {[c['value'] for c in t['conditions']]}")
    n = line(a)
    print(f"   line {NUMBER}: fwd={n.get('forwardingNumber')!r} inbound={n.get('inboundCallService')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
