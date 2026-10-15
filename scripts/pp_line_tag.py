#!/usr/bin/env python3
"""Tag calls by tracking line (Frank, 14/10): the Website & GBP line only got "inbound call".

    ./.venv/bin/python scripts/pp_line_tag.py --only "Pool Shack"            # plan
    ./.venv/bin/python scripts/pp_line_tag.py --only "Pool Shack" --apply

The snapshot's "Answered/Missed Incoming Call To Pipeline" fire for every number and tag only
"new lead" / "inbound call" (/ "missed call"). Instead of touching them, this adds a small published
workflow per account: Call Status inbound on the number whose name contains "GBP" → Add Tag
"website & gbp". Same trigger shape as the live "AdWords Call In - New Lead". Ad lines keep their own
workflows (adwords / facebook tags).
"""
from __future__ import annotations

import argparse
import time
import uuid

from _common import load_dotenv, location_dirs
from pp_audit import load

from cli_anything.gohighlevel.utils.agency import BACKEND, SERVICES, Agency

NAME = "Website & GBP Call - Tag"
TAG = "website & gbp"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--only", action="append", required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    load_dotenv()
    a = Agency()
    bad = 0
    for d in location_dirs(args.only):
        loc = load(d / "location.json", {})["id"]
        name = load(d / "location.json", {}).get("name")
        numbers = a.call("GET", SERVICES, f"/phone-system/numbers/location/{loc}")["numbers"]
        line = [n["phoneNumber"] for n in numbers if "gbp" in (n.get("friendlyName") or "").lower()]
        flows = {w["name"]: w for w in a.workflows(loc)}
        print(f"== {name}: linhas {[(n['phoneNumber'], n.get('friendlyName')) for n in numbers]}")
        if not line:
            print("   sem linha com 'GBP' no nome — nada a fazer")
            continue
        if NAME in flows:
            print(f"   {NAME} já existe")
            continue
        print(f"   + {NAME}: ligação de entrada em {line} → tag '{TAG}'")
        if not args.apply:
            continue
        try:
            a.call("POST", BACKEND, f"/workflow/{loc}/tags/create", body={"tag": TAG})
        except Exception:
            pass  # already exists
        parent = a.workflow(loc, flows["Answered Incoming Call To Pipeline"]["id"]).get("parentId")
        res = a.call("POST", BACKEND, f"/workflow/{loc}", body={"name": NAME, "parentId": parent, "status": "draft"})
        wid = res.get("id") or res.get("_id")
        step = {"id": str(uuid.uuid4()), "order": 0, "name": f"Add Tag {TAG}", "type": "add_contact_tag",
                "attributes": {"tags": [TAG], "type": "add_contact_tag"}}
        a.call("PUT", BACKEND, f"/workflow/{loc}/{wid}", body={
            "name": NAME, "version": 1, "status": "published", "parentId": parent, "allowMultiple": True,
            "workflowData": {"templates": [step]}})
        trig = {"type": "call_status", "name": "Call Details", "masterType": "highlevel", "schedule_config": {},
                "conditions": [{"field": "message.direction", "operator": "==", "value": "inbound",
                                "title": "Call Direction", "type": "select"},
                               {"field": "inbound_number", "operator": "contains-any", "id": "inbound-twilio-number",
                                "value": line, "title": "In Phone Number", "type": "multiselect"}],
                "actions": [{"workflow_id": wid, "type": "add_to_workflow"}], "workflowId": wid,
                "workflow_id": wid, "location_id": loc, "targetActionId": step["id"]}
        t = a.call("POST", BACKEND, f"/workflow/{loc}/trigger", body=trig)
        a.call("PUT", BACKEND, f"/workflow/{loc}/trigger/{t['id']}", body={**trig, "id": t["id"]})
        time.sleep(4)
        after = a.workflow(loc, wid)
        trs = [x for x in a.triggers(loc, wid) if not x.get("deleted")]
        ok = after.get("status") == "published" and len(trs) == 1 and \
            {(c["field"], str(c["value"])) for c in trs[0]["conditions"]} == {(c["field"], str(c["value"])) for c in trig["conditions"]}
        bad += not ok
        print(f"   {'✓' if ok else '✗ VERIFICAR'} {after.get('status')} · gatilho {[(c['field'], c['value']) for c in trs[0]['conditions']] if trs else None}")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
