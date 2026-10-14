#!/usr/bin/env python3
"""Won Stage for the 3 Won stages (Ed, 14/10): weekly service, one-time repair/install, construction.

    ./.venv/bin/python scripts/pp_won_stage.py --only "Test Snapshot"            # plan
    ./.venv/bin/python scripts/pp_won_stage.py --only "Test Snapshot" --apply

Until now "Won Stage" fired only on "🏆 Won - Weekly Pool Service". Adding the other two stages
to its trigger alone would be wrong: the workflow tags "recurring customer", sets the card to
the Weekly stage and sends the weekly-service welcome. So it now branches on which trigger fired
(same "trigger" condition the Review Request workflow uses for these stages):
- Weekly: what it did before, plus tag "won weekly";
- Repairs/Installs: tags "won" + "won repairs and installs", card marked won in its own stage;
- Construction: tags "won" + "won construction", card marked won in its own stage.
All three triggers keep the "Doesn't Have Tag: existing customer" filter.
Accounts whose pipeline has a single "🏆 Won" stage are left alone (already covered).
"""
from __future__ import annotations

import argparse
import json
import time
import uuid

from _common import ROOT, load_dotenv, location_dirs
from pp_audit import load

from cli_anything.gohighlevel.utils.agency import BACKEND, Agency

STAGES = [("weekly", "Weekly", "won weekly"), ("one time", "Repairs / Installs", "won repairs and installs"),
          ("construction", "Construction", "won construction")]
DROP = ("_id", "date_added", "date_updated", "deleted", "origin_id", "company_id", "company_age",
        "last_conditions_change_at", "belongs_to")
NEST = ["inboundWebhookRequest", "sheet", "datetime_formatter", "custom_webhook", "array_functions", "ivr_gather",
        "ivr_connect_call", "custom_code", "ai_agent", "task-notification", "event"]
IS_OPS = ["contact_reply", "inboundWebhookRequest", "custom_webhook", "custom_code", "ai_agent", "contact_detail",
          "array_functions", "appointment", "service_booking", "rental_booking"]


def nid() -> str:
    return str(uuid.uuid4())


def won_stages(a: Agency, loc: str) -> tuple[str, dict]:
    for p in a.pipelines(loc):
        found = {}
        for key, _, _ in STAGES:
            st = next((s for s in p["stages"] if "won" in s["name"].lower() and key in s["name"].lower()), None)
            if st:
                found[key] = st["id"]
        if len(found) == 3:
            return p["id"], found
    return "", {}


def stage_of(trigger: dict) -> str | None:
    return next((c["value"] for c in trigger["conditions"] if c.get("field") == "opportunity.pipelineStageId"), None)


def build(old: list[dict], trig: dict, stages: dict) -> list[dict]:
    """Wrap the current Weekly chain in a branch and add the two new branches."""
    old = [s for s in old if not (s["type"] == "if_else" and s.get("name") == "Which Won stage?")]
    if any(s.get("parentKey") in {x["id"] for x in old if x["type"] == "if_else"} for s in old):
        raise SystemExit("Won Stage already has branches — not rebuilding blindly")
    weekly = json.loads(json.dumps(old))
    opp = next(s for s in weekly if s["type"] == "create_opportunity")
    for s in weekly:
        if s["type"] == "add_contact_tag" and "won" in s["attributes"].get("tags", []):
            s["attributes"]["tags"] = list(dict.fromkeys(s["attributes"]["tags"] + ["won weekly"]))
    cond = nid()
    branch_ids = {key: nid() for key, _, _ in STAGES}
    none_id = nid()
    branches = []
    for key, label, _ in STAGES:
        branches.append({"id": branch_ids[key], "name": label, "operator": "and", "showErrors": False,
                         "branchNameError": "Branch name cannot be empty!",
                         "segments": [{"__segmentId": nid(), "operator": "and", "conditions": [{
                             "conditionType": "trigger", "conditionSubType": "trigger", "conditionOperator": "==",
                             "conditionValue": trig[key], "__conditionId": nid(), "ifElseNodeId": "",
                             "__customFieldType__": "standard", "isWait": False, "nestedDropdownTypes": NEST,
                             "allowIsOperatorTypes": IS_OPS}]}]})
    out = [{"id": cond, "order": 0, "name": "Which Won stage?", "type": "if_else", "cat": "conditions",
            "nodeType": "condition-node", "comments": [], "next": [*branch_ids.values(), none_id],
            "attributes": {"currentRecipeType": "CUSTOM", "branches": branches, "operator": "and", "if": True,
                           "conditionName": "Condition", "version": 2, "noneBranchName": "None"}}]
    every = [*branch_ids.values(), none_id]

    def chain(parent: str, steps: list[dict]) -> list[dict]:
        for i, s in enumerate(steps):
            s["order"] = i
            s["parentKey"] = s["parent"] = steps[i - 1]["id"] if i else parent
            if i + 1 < len(steps):
                s["next"] = steps[i + 1]["id"]
            else:
                s.pop("next", None)
        return steps

    for key, label, tag in STAGES:
        bid = branch_ids[key]
        if key == "weekly":
            steps = weekly
        else:
            other = json.loads(json.dumps(opp))
            other.update({"id": nid(), "name": f"Mark won ({label})"})
            other["attributes"]["pipeline_stage_id"] = stages[key]
            steps = [{"id": nid(), "name": f"Add Tag won / {tag}", "type": "add_contact_tag",
                      "attributes": {"tags": ["won", tag]}}, other]
        out.append({"id": bid, "parent": cond, "parentKey": cond, "order": 1, "name": label, "type": "if_else",
                    "cat": "conditions", "next": steps[0]["id"], "sibling": [x for x in every if x != bid],
                    "comments": [], "nodeType": "branch-yes",
                    "attributes": {"if": False, "conditionName": "Condition", "operator": "and", "branches": []}})
        out += chain(bid, steps)
    out.append({"id": none_id, "parent": cond, "parentKey": cond, "order": 1, "name": "None", "type": "if_else",
                "cat": "conditions", "sibling": [x for x in every if x != none_id], "comments": [],
                "nodeType": "branch-no", "attributes": {"else": True}})
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--only", action="append", required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    load_dotenv()
    a = Agency()
    stamp = time.strftime("%Y%m%d-%H%M%S")
    bad = 0
    for d in location_dirs(args.only):
        loc = load(d / "location.json", {})["id"]
        name = load(d / "location.json", {}).get("name")
        pipe, stages = won_stages(a, loc)
        if not stages:
            print(f"== {name}: pipeline sem os 3 Won — nada a fazer")
            continue
        w = next(w for w in a.workflows(loc) if w["name"] == "Won Stage")
        live = a.workflow(loc, w["id"])
        trs = [t for t in a.triggers(loc, w["id"]) if not t.get("deleted")]
        have = {stage_of(t): t for t in trs}
        print(f"== {name}: Won Stage [{live.get('status')}] gatilhos hoje em {len(have)} etapa(s)")
        if not args.apply:
            continue
        bdir = ROOT / "backup" / d.name
        bdir.mkdir(parents=True, exist_ok=True)
        (bdir / f"workflow-{w['id']}-{stamp}.json").write_text(json.dumps({"workflow": live, "triggers": trs}))
        base = next(t for t in trs if stage_of(t) == stages["weekly"])
        link = {"workflowId": w["id"], "workflow_id": w["id"], "location_id": loc,
                "actions": [{"workflow_id": w["id"], "type": "add_to_workflow"}]}
        trig = {"weekly": base["id"]}
        for key in ("one time", "construction"):
            if stages[key] in have:
                trig[key] = have[stages[key]]["id"]
                continue
            body = {k: v for k, v in base.items() if k not in DROP and k != "id"}
            body.update(link)
            body["conditions"] = [{**c, "value": stages[key]} if c.get("field") == "opportunity.pipelineStageId" else c
                                  for c in base["conditions"]]
            res = a.call("POST", BACKEND, f"/workflow/{loc}/trigger", body=body)
            a.call("PUT", BACKEND, f"/workflow/{loc}/trigger/{res['id']}", body={**body, "id": res["id"]})
            trig[key] = res["id"]
        templates = build(live["workflowData"]["templates"], trig, stages)
        a.call("PUT", BACKEND, f"/workflow/{loc}/{w['id']}", body={
            "name": live["name"], "version": live.get("version", 1), "status": live["status"],
            "parentId": live.get("parentId"), "allowMultiple": live.get("allowMultiple", False),
            "workflowData": {"templates": templates}})
        for t in [x for x in a.triggers(loc, w["id"]) if not x.get("deleted")]:  # point every trigger at the first step
            body = {k: v for k, v in t.items() if k not in DROP}
            body.update(link)
            body["targetActionId"] = templates[0]["id"]
            a.call("PUT", BACKEND, f"/workflow/{loc}/trigger/{t['id']}", body=body)
        time.sleep(4)
        after = a.workflow(loc, w["id"])
        trs2 = [t for t in a.triggers(loc, w["id"]) if not t.get("deleted")]
        got = {stage_of(t) for t in trs2}
        filt = all(any(c.get("value") == "existing customer" for c in t["conditions"]) for t in trs2)
        ok = got == set(stages.values()) and filt and len(after["workflowData"]["templates"]) == len(templates)
        bad += not ok
        print(f"   {'✓' if ok else '✗ VERIFICAR'} {after.get('status')} · {len(trs2)} gatilhos (3 Won) · filtro existing customer={filt}")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
