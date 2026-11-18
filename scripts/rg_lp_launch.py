#!/usr/bin/env python3
"""Reign: the 3 Google Ads landing pages Atif built (ClickUp 86bd2jrc6, 18/11) → CRM.

    python3 scripts/rg_lp_launch.py plan
    python3 scripts/rg_lp_launch.py test       # ZZ TEST copies of the tag flows + ZZ TEST contacts, all deleted
    python3 scripts/rg_lp_launch.py apply

Atif's forms (LP - Weekly Pool Service / Green to Clean / Equipment Repairs) were not on any workflow trigger.
1. They join the trigger of "AdWords Form - New Lead" (tags new lead / new form fill / adwords, card in New Lead, SMS
   alert to Stephen, thank-you text) — same path as the Ads form already live.
2. One small flow per form ("Google Ads LP <service> - Tags"): the brief's tags (Reign - Google Ads - <service> +
   google ads) and a ZIP check against the 8 target ZIPs → `service area zip` or `outside service area`.
Nothing touches existing contacts (only new submissions of these 3 forms). GET + backup before every PUT.
"""
from __future__ import annotations

import argparse
import json
import sys
import time

from _common import ROOT, load_dotenv
import ps_ads_forms as ps
from ps_ads_forms import cond, tags

from cli_anything.gohighlevel.utils.agency import BACKEND, SERVICES, Agency

LOC = "jvu0xE8rfMFiT00he8m7"
ps.LOC = LOC
MAIN = "AdWords Form - New Lead"
ZIPS = ["92881", "92880", "92883", "92882", "92532", "92530", "92587", "92584"]
FORMS = [
    {"id": "EQP4r8ycAqCMx0KHqjbO", "flow": "Google Ads LP Weekly - Tags", "tags": ["reign - google ads - weekly service", "google ads"]},
    {"id": "4vRg97Bft3RASZm9Mauh", "flow": "Google Ads LP Green to Clean - Tags", "tags": ["reign - google ads - green to clean", "google ads"]},
    {"id": "dZWvLMMQdk2Hd6waVYvN", "flow": "Google Ads LP Repairs - Tags", "tags": ["reign - google ads - repairs", "google ads"]},
]
AREA_TAGS = ["service area zip", "outside service area"]
BDIR = ROOT / "backup" / "reign-pool-services"


def backup(name: str, data) -> None:
    BDIR.mkdir(parents=True, exist_ok=True)
    (BDIR / f"{name}-{int(time.time())}.json").write_text(json.dumps(data, indent=1))


def _chain(f: dict) -> list[dict]:
    first = ps.chain([tags(f["tags"])])
    sub, head = ps.if_else("ZIP in the service area?",
                           [("Service area ZIP", [cond("postal_code", "==", z) for z in ZIPS], [tags(["service area zip"])])],
                           "Outside the area", [tags(["outside service area"])], parent_key=first[0]["id"], order=1)
    first[0]["next"] = head
    return first + sub


def ensure_tags(a: Agency, wanted: list[str], apply: bool) -> None:
    have = {t["name"].lower() for t in a.tags(LOC)}
    for t in wanted:
        if t.lower() not in have:
            print(f"   tag nova: {t}")
            if apply:
                a.call("POST", BACKEND, f"/workflow/{LOC}/tags/create", body={"tag": t})


def make_flow(a: Agency, name: str, tpl: list[dict], form_id: str | None) -> str:
    wid = ps.create_flow(a, name, None, tpl, publish=False)
    if form_id:
        ps_body = ps.trigger_body(wid, form_id, tpl[0]["id"])
        t = a.call("POST", BACKEND, f"/workflow/{LOC}/trigger", body=ps_body)
        a.call("PUT", BACKEND, f"/workflow/{LOC}/trigger/{t['id']}", body={**ps_body, "id": t["id"]})
        time.sleep(2)
    live = a.workflow(LOC, wid)
    a.call("PUT", BACKEND, f"/workflow/{LOC}/{wid}", body={"name": name, "version": live.get("version", 1),
           "status": "published", "parentId": None, "allowMultiple": True,
           "workflowData": {"templates": live["workflowData"]["templates"]}})
    time.sleep(3)
    return wid


def main_trigger(a: Agency, flows: dict, apply: bool) -> None:
    wid = flows[MAIN]
    trs = [t for t in a.triggers(LOC, wid) if not t.get("deleted") and t.get("type") == "form_submission"]
    t = trs[0]
    c = next(c for c in t["conditions"] if c.get("field") == "form.id")
    want = [*c["value"], *[f["id"] for f in FORMS if f["id"] not in c["value"]]]
    print(f"   {MAIN}: forms {c['value']} → {want}")
    if apply and want != c["value"]:
        backup(f"triggers-{wid}", trs)
        c["value"] = want
        body = {k: t[k] for k in ("type", "name", "masterType", "conditions", "targetActionId") if k in t}
        a.call("PUT", BACKEND, f"/workflow/{LOC}/trigger/{t['id']}", body={**body, "schedule_config": {}, "id": t["id"],
               "workflowId": wid, "workflow_id": wid, "location_id": LOC,
               "actions": [{"workflow_id": wid, "type": "add_to_workflow"}]})
        time.sleep(3)
        got = next(x for x in a.triggers(LOC, wid) if x["id"] == t["id"])
        ok = next(c for c in got["conditions"] if c.get("field") == "form.id")["value"] == want
        print(f"   {'✓' if ok else '✗'} gatilho atualizado")


def test(a: Agency) -> int:
    bad, stamp = 0, int(time.time())
    f = FORMS[0]
    wid = make_flow(a, f"ZZ TEST {f['flow']}", _chain(f), None)
    made = {}
    for case, z in (("in", "92881"), ("out", "90210")):
        made[case] = a.call("POST", SERVICES, "/contacts/", body={
            "locationId": LOC, "firstName": "ZZ Test", "lastName": f"lp {case}", "tags": ["zz test"], "postalCode": z,
            "email": f"pedro+rg-lp-{case}-{stamp}@poolprofits.com"})["contact"]["id"]
    time.sleep(3)
    for cid in made.values():
        a.call("POST", SERVICES, f"/contacts/{cid}/workflow/{wid}", body={})
    time.sleep(40)
    want = {"in": "service area zip", "out": "outside service area"}
    for case, cid in made.items():
        tg = set(a.call("GET", SERVICES, f"/contacts/{cid}")["contact"].get("tags") or [])
        ok = set(f["tags"]) <= tg and want[case] in tg and (set(AREA_TAGS) - {want[case]}).isdisjoint(tg)
        bad += not ok
        print(f"   {'✓' if ok else '✗'} {case}: {sorted(tg)}")
        a.call("DELETE", SERVICES, f"/contacts/{cid}")
    ps.drop_flow(a, wid)
    print("   limpo (contatos + fluxo ZZ TEST apagados)")
    return 1 if bad else 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("mode", choices=["plan", "test", "apply"])
    args = p.parse_args()
    load_dotenv()
    a = Agency()
    flows = {w["name"]: w["id"] for w in a.workflows(LOC)}
    apply = args.mode == "apply"
    ensure_tags(a, [*{t for f in FORMS for t in f["tags"]}, *AREA_TAGS], apply or args.mode == "test")
    if args.mode == "test":
        return test(a)
    for f in FORMS:
        if f["flow"] in flows:
            print(f"   {f['flow']}: já existe")
            continue
        print(f"   {f['flow']}: cria (form {f['id']}, tags {f['tags']} + ZIP check)")
        if apply:
            wid = make_flow(a, f["flow"], _chain(f), f["id"])
            live = a.workflow(LOC, wid)
            trs = [t for t in a.triggers(LOC, wid) if not t.get("deleted")]
            print(f"   ✓ {wid} {live.get('status')} · gatilhos {[(t.get('type'), t.get('active')) for t in trs]}")
    main_trigger(a, flows, apply)
    return 0


if __name__ == "__main__":
    sys.exit(main())
