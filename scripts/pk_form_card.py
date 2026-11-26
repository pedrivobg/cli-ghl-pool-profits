#!/usr/bin/env python3
"""The Pool Keepers (BurchTech, live client account): website quote form -> lead card (Nathan 25/11, Pedro 26/11).

The site's real form is "Pool Service Request a Quote" (RSM0...). The client's own published flow "Submitted Pool Service
Request Form" already texts Nathan + creates a task, so it stays untouched. Our "Website Form Fill To Pipeline" (draft,
listening to 3 snapshot forms that are not on the site) becomes: trigger = RSM0 only, steps = card in Pool Leads >
New Lead (source Website Form) + tags "new lead"/"form fill". No SMS/email/task (no double alert, nothing to the contact).

    GHL_AGENCY=burchtech python3 scripts/pk_form_card.py            # plan
    GHL_AGENCY=burchtech python3 scripts/pk_form_card.py --apply    # GET + backup, PUT, publish
    GHL_AGENCY=burchtech python3 scripts/pk_form_card.py --test     # ZZ TEST contact (no email/address) through the flow
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
import time

from _common import ROOT, load_dotenv

from cli_anything.gohighlevel.utils.agency import BACKEND, SERVICES, Agency

LOC = "KjLd769fprQ2EaBI9Cro"
WID = "c4f01a5b-9930-43b2-b918-346b923bc718"
FORM = "RSM0wRmNwWZeN10iqG2X"
PIPE, STAGE = "WwhrLIXFLCFruCbgHZEW", "7e5d809f-3009-4632-a4cf-66415f760038"
BDIR = ROOT / "backup" / "the-pool-keepers"


def new_steps(tpl: list[dict]) -> list[dict]:
    opp = next(s for s in tpl if s["type"] == "create_opportunity")
    tag = next(s for s in tpl if s["type"] == "add_contact_tag")
    opp, tag = copy.deepcopy(opp), copy.deepcopy(tag)
    opp.pop("parentKey", None)
    opp["order"], opp["next"] = 0, tag["id"]
    tag.update({"order": 1, "parentKey": opp["id"], "next": None})
    return [opp, tag]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--test", action="store_true")
    args = ap.parse_args()
    load_dotenv()
    a = Agency()
    if a.location(LOC)["name"] != "The Pool Keepers":
        sys.exit("token errado (GHL_AGENCY=burchtech)")
    live = a.workflow(LOC, WID)
    tpl = live["workflowData"]["templates"]
    trig = a.triggers(LOC, WID)
    print(live["name"], live["status"], [s["name"] for s in tpl], [t.get("conditions") for t in trig])
    if args.apply:
        BDIR.mkdir(parents=True, exist_ok=True)
        stamp = time.strftime("%Y%m%d-%H%M%S")
        (BDIR / f"workflow-{WID}-{stamp}.json").write_text(json.dumps({"workflow": live, "triggers": trig}))
        steps = new_steps(tpl)
        for t in trig:
            body = {**t, "conditions": [{"operator": "is-any-of", "field": "form.id", "value": [FORM],
                                         "title": "Form is", "type": "string"}],
                    "workflowId": WID, "workflow_id": WID, "location_id": LOC, "targetActionId": steps[0]["id"],
                    "actions": [{"workflow_id": WID, "type": "add_to_workflow"}]}
            a.call("PUT", BACKEND, f"/workflow/{LOC}/trigger/{t['id']}", body=body)
        a.call("PUT", BACKEND, f"/workflow/{LOC}/{WID}", body={
            "name": live["name"], "version": live.get("version", 1), "status": "published",
            "parentId": live.get("parentId"), "workflowData": {"templates": steps}})
        time.sleep(3)
        got = a.workflow(LOC, WID)
        print("depois:", got["status"], [s["name"] for s in got["workflowData"]["templates"]],
              [t.get("conditions") for t in a.triggers(LOC, WID)])
    if args.test:
        c = a.call("POST", SERVICES, "/contacts/", body={"locationId": LOC, "firstName": "ZZ TEST", "lastName": "Form Card",
                                                         "phone": "+15055550147"})
        cid = (c.get("contact") or c)["id"]
        print("contato", cid)
        try:
            a.call("POST", SERVICES, f"/contacts/{cid}/workflow/{WID}", body={})
            opp = None
            for _ in range(12):
                time.sleep(5)
                r = a.get(SERVICES, "/opportunities/search", {"location_id": LOC, "contact_id": cid})
                opps = r.get("opportunities") or []
                if opps:
                    opp = opps[0]
                    break
            ct = a.get(SERVICES, f"/contacts/{cid}").get("contact", {})
            print("card:", opp and (opp.get("pipelineId") == PIPE, opp.get("pipelineStageId") == STAGE, opp.get("source")),
                  "tags:", ct.get("tags"))
            if opp:
                a.call("DELETE", SERVICES, f"/opportunities/{opp['id']}")
        finally:
            a.call("DELETE", SERVICES, f"/contacts/{cid}")
            print("teste apagado")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
