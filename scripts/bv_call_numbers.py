#!/usr/bin/env python3
"""BluVantage: one tracking number per Google Ads landing page (Val, 26/10). Calls ring the team like every line and are
tagged/counted by service.

    ./.venv/bin/python scripts/bv_call_numbers.py plan
    ./.venv/bin/python scripts/bv_call_numbers.py apply

Numbers: Weekly +1 470-470-8874 (already live), Repairs +1 470-450-6322 and Winter +1 470-450-4427 (bought 26/10).
- IVR: the new numbers join the "Sequential Call Routing" trigger (Vanessa → Fred → Paul → voicemail), like the others.
- Conversion: they join the trigger of "Google Ads - Call from Landing to GHL" (Val's conversion action).
- Tracking: "AdWords Call In - Repairs" / "- Winter", copies of "AdWords Call In - New Lead" (guard, conversion, tags,
  card, thank-you text 5 min later) on their own number, with the service tag and card source; the Weekly one gets its
  service tag too. No "NEW LEAD" text for calls (Paul, 14/10: the IVR already rings the team).
GET + backup before every write.
"""
from __future__ import annotations

import argparse
import json
import sys
import time

from _common import ROOT, load_dotenv
from pp_review_fix import read
from pp_source_tags import fresh_ids, refs_ok
from pp_won_stage import DROP

from cli_anything.gohighlevel.utils.agency import BACKEND, Agency

LOC = "KLFYmoVapqQgX3T0AnLn"
IVR, CONVERSION, BASE = "Sequential Call Routing", "Google Ads - Call from Landing to GHL", "AdWords Call In - New Lead"
LINES = [{"key": "weekly", "number": "+14704708874", "flow": BASE, "tag": "google ads call - weekly"},
         {"key": "repairs", "number": "+14704506322", "flow": "AdWords Call In - Repairs", "tag": "google ads call - repairs"},
         {"key": "winter", "number": "+14704504427", "flow": "AdWords Call In - Winter", "tag": "google ads call - winter"}]
NEW = [x["number"] for x in LINES[1:]]
BDIR = ROOT / "backup" / "bluvantage-pool-service"


def backup(kind: str, oid: str, obj) -> None:
    BDIR.mkdir(parents=True, exist_ok=True)
    (BDIR / f"{kind}-{oid}-{time.strftime('%Y%m%d-%H%M%S')}.json").write_text(json.dumps(obj))


def add_numbers(a: Agency, wid: str, field: str, apply: bool) -> str:
    """Add NEW to the number list of the workflow's trigger(s)."""
    out = []
    for t in [x for x in a.triggers(LOC, wid) if not x.get("deleted")]:
        cond = next(c for c in t["conditions"] if c.get("field") == field)
        missing = [n for n in NEW if n not in cond["value"]]
        out.append(f"+{len(missing)} número(s)")
        if missing and apply:
            backup("trigger", t["id"], t)
            cond["value"] = [*cond["value"], *missing]
            body = {k: v for k, v in t.items() if k not in DROP}
            body.update({"workflowId": wid, "workflow_id": wid, "location_id": LOC})
            a.call("PUT", BACKEND, f"/workflow/{LOC}/trigger/{t['id']}", body=body)
    return ", ".join(out)


def tagged(tpl: list[dict], line: dict) -> list[dict]:
    for st in tpl:
        a = st.get("attributes") or {}
        if st["type"] == "add_contact_tag" and line["tag"] not in a.get("tags", []):
            a["tags"] = [*a.get("tags", []), line["tag"]]
        if st["type"] == "create_opportunity":
            a["opportunity_source"] = f"Google Ads LP Call - {line['key'].title()}"
    return tpl


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("mode", choices=["plan", "apply"])
    args = parser.parse_args()
    load_dotenv()
    a = Agency()
    if a.location(LOC)["name"] != "BluVantage Pool Service":
        sys.exit("sub-conta errada")
    apply = args.mode == "apply"
    flows = {w["name"]: w["id"] for w in a.workflows(LOC)}
    print(f"   {IVR}: {add_numbers(a, flows[IVR], 'inbound_number', apply)}")
    print(f"   {CONVERSION}: {add_numbers(a, flows[CONVERSION], 'inbound_number', apply)}")
    base = read(a, LOC, flows[BASE])
    base_trig = next(t for t in a.triggers(LOC, flows[BASE]) if not t.get("deleted"))
    for t in [*NEW, *(x["tag"] for x in LINES)]:
        if apply and t.startswith("google"):
            try:
                a.call("POST", BACKEND, f"/workflow/{LOC}/tags/create", body={"tag": t})
            except Exception:  # noqa: BLE001 — already exists
                pass
    for line in LINES:
        if line["flow"] == BASE:  # the Weekly one: only the service tag and card source
            tpl = tagged(json.loads(json.dumps(base["workflowData"]["templates"])), line)
            print(f"   {BASE}: tag '{line['tag']}' + origem do card")
            if apply:
                backup("workflow", flows[BASE], base)
                a.call("PUT", BACKEND, f"/workflow/{LOC}/{flows[BASE]}", body={
                    "name": base["name"], "version": base.get("version", 1), "status": base["status"],
                    "parentId": base.get("parentId"), "workflowData": {"templates": tpl}})
            continue
        if line["flow"] in flows:
            print(f"   {line['flow']}: já existe")
            continue
        tpl = tagged(fresh_ids(base["workflowData"]["templates"]), line)
        print(f"   {line['flow']}: cria ({len(tpl)} passos, número {line['number']}, tag '{line['tag']}')")
        if not apply:
            continue
        res = a.call("POST", BACKEND, f"/workflow/{LOC}", body={"name": line["flow"], "parentId": base.get("parentId"), "status": "draft"})
        wid = res.get("id") or res.get("_id")
        body = {"name": line["flow"], "version": 1, "status": "draft", "parentId": base.get("parentId"),
                "allowMultiple": base.get("allowMultiple", True), "workflowData": {"templates": tpl}}
        a.call("PUT", BACKEND, f"/workflow/{LOC}/{wid}", body=body)
        trig = {k: v for k, v in base_trig.items() if k not in {*DROP, "id", "workflow_id", "workflowId", "targetActionId"}}
        trig = json.loads(json.dumps(trig))
        next(c for c in trig["conditions"] if c.get("field") == "inbound_number")["value"] = [line["number"]]
        root = next(s["id"] for s in tpl if not s.get("parentKey") and not s.get("parent"))
        trig.update({"workflowId": wid, "workflow_id": wid, "location_id": LOC, "targetActionId": root,
                     "actions": [{"workflow_id": wid, "type": "add_to_workflow"}]})
        t = a.call("POST", BACKEND, f"/workflow/{LOC}/trigger", body=trig)
        a.call("PUT", BACKEND, f"/workflow/{LOC}/trigger/{t['id']}", body={**trig, "id": t["id"]})
        live = a.workflow(LOC, wid)
        a.call("PUT", BACKEND, f"/workflow/{LOC}/{wid}", body={**body, "status": "published", "version": live.get("version", 1),
                                                             "workflowData": {"templates": live["workflowData"]["templates"]}})
        time.sleep(3)
        got = a.workflow(LOC, wid)
        trs = [x for x in a.triggers(LOC, wid) if not x.get("deleted")]
        ok = got["status"] == "published" and refs_ok(got["workflowData"]["templates"]) and len(trs) == 1 and \
            trs[0].get("active") and line["number"] in json.dumps(trs[0]["conditions"])
        print(f"      {'✓' if ok else '✗ VERIFICAR'} {got['status']} · gatilho {line['number']}")
    if apply:
        time.sleep(3)
        for name in (IVR, CONVERSION):
            vals = [c["value"] for t in a.triggers(LOC, flows[name]) if not t.get("deleted") for c in t["conditions"]
                    if c.get("field") == "inbound_number"]
            print(f"   conferido {name}: {'✓' if all(n in vals[0] for n in NEW) else '✗'} {vals}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
