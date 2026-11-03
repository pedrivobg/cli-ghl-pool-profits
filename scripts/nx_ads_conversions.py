#!/usr/bin/env python3
"""NorTex: Google Ads offline conversions "LP Form Submit" and "Appointment Booked" (Val, 03/11).

    ./.venv/bin/python scripts/nx_ads_conversions.py plan
    ./.venv/bin/python scripts/nx_ads_conversions.py apply
    ./.venv/bin/python scripts/nx_ads_conversions.py test    # temporary copy with a fake gclid, reads the execution log

Val created 2 offline (UPLOAD) conversion actions in the NorTex Google Ads account. GHL lists them at
`GET /ad-publishing/google/conversions?locationId` (the step's dropdown). "LP Form Submit" goes into the empty
"Google Ads conversion" step of "Google Ads LP - Weekly" and "Google Ads LP - Repair" (new lead branch, after the card);
"Appointment Booked" is a new last step of "Appointment Booked -> Notify Fareed" (after the alerts, so the trigger's
first step stays the same). The upload uses the click id the contact carries ({{contact.attributionSource.gclid}}):
only contacts that came from an ad click count, so the booking flow can keep firing for every calendar.
GET + backup before each PUT; workflow settings are kept by Agency.call.
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
import time
import uuid

from _common import ROOT, load_dotenv

from cli_anything.gohighlevel.utils.agency import BACKEND, SERVICES, Agency

LOC = "k6nDPHktS2PySJoJuwpG"
LP_FLOWS = ("Google Ads LP - Weekly", "Google Ads LP - Repair")
BOOK_FLOW = "Appointment Booked -> Notify Fareed"
LP_CONV, BOOK_CONV = "LP Form Submit", "Appointment Booked"
GCLID = "{{contact.attributionSource.gclid}}"
BDIR = ROOT / "backup" / "nortex-pools"


def conversions(a: Agency) -> dict[str, str]:
    rows = a.call("GET", SERVICES, "/ad-publishing/google/conversions", params={"locationId": LOC})
    return {r["conversion_name"]: r["conversion_action_id"] for r in rows}


def attrs(name: str, cid: str, gclid: str = GCLID) -> dict:
    return {"type": "google_adword", "currency": "USD", "conversion_value": "1", "conversion_type": name,
            "conversion_name": name, "conversion_action_id": cid, "customMapping": {"gclid": gclid},
            "isCustomMappingEnabled": True}


def with_lp(tpl: list[dict], cid: str) -> list[dict]:
    out = copy.deepcopy(tpl)
    for s in out:
        if s["type"] == "google_adword":
            s["attributes"] = {**s.get("attributes", {}), **attrs(LP_CONV, cid)}
    return out


def with_booking(tpl: list[dict], cid: str, gclid: str = GCLID) -> list[dict]:
    out = copy.deepcopy(tpl)
    if any(s["type"] == "google_adword" for s in out):
        for s in out:
            if s["type"] == "google_adword":
                s["attributes"] = {**s.get("attributes", {}), **attrs(BOOK_CONV, cid, gclid)}
        return out
    last = next(s for s in out if not s.get("next"))
    step = {"id": str(uuid.uuid4()), "order": last.get("order", len(out) - 1) + 1, "name": "Google Ads conversion",
            "type": "google_adword", "parentKey": last["id"], "attributes": attrs(BOOK_CONV, cid, gclid)}
    last["next"] = step["id"]
    return [*out, step]


def put(a: Agency, wid: str, tpl: list[dict]) -> dict:
    live = a.workflow(LOC, wid)
    BDIR.mkdir(parents=True, exist_ok=True)
    (BDIR / f"workflow-{wid}-{time.strftime('%Y%m%d-%H%M%S')}.json").write_text(json.dumps(live))
    a.call("PUT", BACKEND, f"/workflow/{LOC}/{wid}", body={"name": live["name"], "version": live.get("version", 1),
           "status": live["status"], "workflowData": {"templates": tpl}})
    time.sleep(3)
    return a.workflow(LOC, wid)


def steps(wf: dict) -> list[tuple]:
    return [(s["attributes"].get("conversion_name"), s["attributes"].get("conversion_action_id"))
            for s in wf["workflowData"]["templates"] if s["type"] == "google_adword"]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("mode", choices=["plan", "apply", "test"])
    args = parser.parse_args()
    load_dotenv()
    a = Agency()
    if not a.location(LOC)["name"].lower().startswith("nortex"):
        sys.exit("sub-conta errada")
    conv = conversions(a)
    print(f"   conversões no Google Ads: {conv}")
    if LP_CONV not in conv or BOOK_CONV not in conv:
        sys.exit("conversão faltando")
    flows = {w["name"]: w["id"] for w in a.workflows(LOC)}
    if args.mode == "test":
        return test(a, conv)
    for name in (*LP_FLOWS, BOOK_FLOW):
        wid = flows[name]
        wf = a.workflow(LOC, wid)
        tpl = wf["workflowData"]["templates"]
        new = with_lp(tpl, conv[LP_CONV]) if name in LP_FLOWS else with_booking(tpl, conv[BOOK_CONV])
        print(f"   {name} ({wf['status']}): {steps(wf)} → {steps({'workflowData': {'templates': new}})}")
        if args.mode == "apply" and new != tpl:
            got = put(a, wid, new)
            want = LP_CONV if name in LP_FLOWS else BOOK_CONV
            ok = got["status"] == wf["status"] and steps(got) and all(s == (want, conv[want]) for s in steps(got))
            print(f"      {'✓' if ok else '✗ VERIFICAR'} {got['status']} · {steps(got)} · {len(got['workflowData']['templates'])} passos")
    return 0


def test(a: Agency, conv: dict) -> int:
    """Copy of the booking alert's conversion step only, fired for a test contact with a fake click id."""
    res = a.call("POST", BACKEND, f"/workflow/{LOC}", body={"name": "ZZ TEST google ads conversion", "status": "draft"})
    wid = res.get("id") or res.get("_id")
    tpl = [{"id": str(uuid.uuid4()), "order": 0, "name": f"Test {name}", "type": "google_adword",
            "attributes": attrs(name, conv[name], "ZZTEST-fake-gclid")} for name in (LP_CONV, BOOK_CONV)]
    tpl[0]["next"], tpl[1]["parentKey"] = tpl[1]["id"], tpl[0]["id"]
    body = {"name": "ZZ TEST google ads conversion", "version": 1, "status": "draft", "workflowData": {"templates": tpl}}
    a.call("PUT", BACKEND, f"/workflow/{LOC}/{wid}", body=body)
    live = a.workflow(LOC, wid)
    a.call("PUT", BACKEND, f"/workflow/{LOC}/{wid}", body={**body, "status": "published", "version": live.get("version", 1)})
    cid = a.call("POST", SERVICES, "/contacts/", body={"locationId": LOC, "firstName": "ZZ Test", "lastName": "conversion",
                                                       "email": f"zz-test-conv-{int(time.time())}@example.com"})["contact"]["id"]
    try:
        time.sleep(3)
        a.call("POST", SERVICES, f"/contacts/{cid}/workflow/{wid}", body={})
        time.sleep(45)
        for path in (f"/workflow/{LOC}/{wid}/execution-logs", f"/workflow/{LOC}/execution-logs/{wid}",
                     f"/workflow/{LOC}/{wid}/logs", f"/workflow/{LOC}/history"):
            try:
                r = a.call("GET", BACKEND, path, params={"contactId": cid, "workflowId": wid, "limit": 20})
                print(f"   {path}: {json.dumps(r)[:1500]}")
                break
            except Exception as e:  # noqa: BLE001
                print(f"   {path}: {str(e)[:80]}")
    finally:
        a.call("DELETE", SERVICES, f"/contacts/{cid}")
        live = a.workflow(LOC, wid)
        a.call("PUT", BACKEND, f"/workflow/{LOC}/{wid}", body={**body, "status": "draft", "version": live.get("version", 1),
                                                             "workflowData": {"templates": live["workflowData"]["templates"]}})
        a.call("DELETE", BACKEND, f"/workflow/{LOC}/{wid}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
