#!/usr/bin/env python3
"""Phone menu (IVR) for every line of a sub-account, built like Nortex's "IVR SPAM Detection".

    ./.venv/bin/python scripts/pp_ivr.py --only "Southern Pool"              # plan
    ./.venv/bin/python scripts/pp_ivr.py --only "Southern Pool" --apply      # creates it as DRAFT
    ./.venv/bin/python scripts/pp_ivr.py --only "Southern Pool" --apply --publish

LIVE IN SOUTHERN (14/10): Pedro replaced the spoken menu with a recording (WhatsApp audio) and
Ed set 1 → Brett's cell (214) 893-2315, 2 / no key → company line (214) 308-1744. Do NOT rerun
--apply there: it rebuilds from scratch and drops both. Edit the live version instead.

STAY FRESH (21/10): own menu in MENUS (1 Service → Kris, 2 Construction → Mike), built as DRAFT for Frank;
not published (publishing adds the trigger that ties the lines to the IVR).

Default menu: 1 = new service, repairs or construction quotes; 2 = existing customers; no key = same
as 1 (a real caller is never dropped). Every branch rings the line the number forwards to
today (or the number set in MENUS) and, if nobody answers, tags "missed call" and takes a voicemail.

Why the "missed call" tag lives here: once a number answers with an IVR, GHL reports every
inbound call as "completed" (seen in Nortex since its IVR went live), so the call_status
trigger of "Missed Incoming Call To Pipeline" stops firing. Tagging here keeps the
missed-call text-back ("Missed New Lead - Initial SMS Follow-up", tag trigger) working.
"Answered Incoming Call To Pipeline" keeps creating the New Lead card, as it does today.

The workflow shape (gather → transitions → connect call → if not completed → voicemail) and
the step attributes are copied from the Nortex IVR, so the GHL builder shows it normally.
"""
from __future__ import annotations

import argparse
import json
import time
import uuid

from _common import ROOT, load_dotenv, location_dirs
from pp_audit import load

from cli_anything.gohighlevel.utils.agency import BACKEND, SERVICES, Agency

NAME = "IVR - Main Line Menu"
GREETING = ("Thank you for calling {business}. For new service, repairs, or construction quotes, press 1. "
            "If you are an existing customer, press 2.")
VOICEMAIL = ("We're sorry we missed your call. Please leave a message with your name and the service "
             "you're calling about after the beep. Thank you.")
OPTIONS = [  # (digit, branch name, tag) — digit None = no key pressed
    ("1", "1 - New Service / Repairs / Construction", "ivr - new service"),
    ("2", "2 - Existing Customer", "ivr - existing customer"),
    (None, "No Input", None),
]
# Accounts with their own menu: greeting + (digit, branch, tag, number to ring, who). None = no key pressed.
MENUS = {
    "DdTE6mF11dqgoI5Cv7XN": {  # Stay Fresh Pools — Frank 21/10: Service → Kris, Construction → Mike; DRAFT only,
        # prompts to be replaced by recordings once the wording is final (Ed decides the name of option 2)
        "greeting": "Thank you for calling Stay Fresh Pools. For pool service, press 1. "
                    "For pool construction or remodeling, press 2.",
        "options": [("1", "1 - Service", "ivr - service", "+14807721420", "Kris"),
                    ("2", "2 - Construction / Remodeling", "ivr - construction", "+14803040741", "Mike"),
                    (None, "No Input", None, "+14803040741", "Mike")],
    },
}
# Spoken names: "+" would be read as "plus"
SPOKEN = {"SylIOZiJ6YQsZOypUI8Z": "Southern Pool and Outdoors"}
NEST = ["inboundWebhookRequest", "sheet", "datetime_formatter", "custom_webhook", "array_functions", "ivr_gather",
        "ivr_connect_call", "custom_code", "ai_agent", "task-notification", "event"]
IS_OPS = ["contact_reply", "inboundWebhookRequest", "custom_webhook", "custom_code", "ai_agent", "contact_detail",
          "array_functions", "appointment", "service_booking", "rental_booking"]


def nid() -> str:
    return str(uuid.uuid4())


def link(parent: str, nodes: list[dict]) -> list[dict]:
    """Chain nodes one after another under `parent` (a transition or an if/else branch)."""
    for order, node in enumerate(nodes):
        node["order"] = order
        node["parentKey"] = node["parent"] = nodes[order - 1]["id"] if order else parent
        if order + 1 < len(nodes):
            node["next"] = nodes[order + 1]["id"]
    return nodes


def spoken(number: str) -> str:
    return f"({number[2:5]}) {number[5:8]}-{number[8:]}"


def build(greeting: str, options: list[tuple]) -> list[dict]:
    gather = nid()
    transitions = [{"id": nid(), "name": name, "condition": digit or "None",
                    "conditionType": "user-defined" if digit else "default",
                    "isPrimaryBranch": False, "description": "", "attributes": {}}
                   for digit, name, *_ in options]
    steps = [{"id": gather, "order": 0, "name": "Main menu", "type": "ivr_gather", "cat": "multi-path",
              "stepIndex": 1, "next": [t["id"] for t in transitions],
              "attributes": {"loop": 2, "timeout": 5, "numDigits": 1, "enableFinishOnKey": False,
                             "widgetType": "say", "convertToMultipath": True, "name": "Main menu",
                             "type": "ivr_gather", "language": "en-US", "voice": "woman",
                             "message": greeting, "cat": "multi-path",
                             "transitions": transitions}}]
    index = 2  # stepIndex of IVR nodes; the if/else reads "<stepIndex>.dialCallStatus"
    for t, (digit, name, tag, forward_to, who) in zip(transitions, options):
        connect_index, vm_index = index, index + 1
        index += 2
        cond, yes, no = nid(), nid(), nid()
        branch = []
        if tag:
            branch.append({"id": nid(), "name": f"Tag {tag}", "type": "add_contact_tag",
                           "attributes": {"tags": [tag]}})
        branch.append({"id": nid(), "name": f"Ring {who}", "type": "ivr_connect_call", "stepIndex": connect_index,
                       "attributes": {
                           "timeout": 20, "timeLimit": 3600, "userId": "", "users": [], "detectVoicemail": False,
                           "isSayPlayOn": False, "record": "record-from-answer",
                           "customNumbers": [{"country": "US", "phone": forward_to, "displayValue": spoken(forward_to),
                                              "isValid": True}],
                           "sayPlayAttributes": {"loop": 1, "widgetType": "say",
                                                 "message": "This is an automated call from workflows",
                                                 "language": "en-US", "voice": "woman", "type": "ivr_say"}}})
        branch.append({"id": cond, "name": "Answered?", "type": "if_else", "cat": "conditions", "comments": [],
                       "nodeType": "condition-node", "next": [yes, no],
                       "attributes": {"currentRecipeType": "CUSTOM", "operator": "and", "if": True,
                                      "conditionName": "Condition", "version": 2, "noneBranchName": "Answered",
                                      "branches": [{"id": yes, "name": "Not answered", "operator": "and",
                                                    "showErrors": False,
                                                    "branchNameError": "Branch name cannot be empty!",
                                                    "segments": [{"__segmentId": nid(), "operator": "and",
                                                                  "conditions": [{
                                                                      "conditionType": "ivr_connect_call",
                                                                      "conditionSubType": f"{connect_index}.dialCallStatus",
                                                                      "conditionOperator": "!=",
                                                                      "conditionValue": "completed",
                                                                      "__conditionId": nid(), "ifElseNodeId": "",
                                                                      "__customFieldType__": "standard",
                                                                      "isWait": False, "nestedDropdownTypes": NEST,
                                                                      "allowIsOperatorTypes": IS_OPS}]}]}]}})
        transition = {"id": t["id"], "name": name, "type": "transition", "cat": "transition", "attributes": {},
                      "order": 1, "parent": gather, "parentKey": gather, "next": branch[0]["id"]}
        steps += [transition, *link(t["id"], branch)]
        # if/else branches hang off the condition node; "Not answered" → tag missed call → voicemail
        for bid, bname, kind, sib in ((yes, "Not answered", "branch-yes", no), (no, "Answered", "branch-no", yes)):
            steps.append({"id": bid, "order": len(branch), "name": bname, "type": "if_else", "parent": cond,
                          "parentKey": cond, "cat": "conditions", "sibling": [sib], "comments": [], "nodeType": kind,
                          "attributes": {"if": False, "conditionName": "Condition", "operator": "and",
                                         "branches": []} if kind == "branch-yes" else {"else": True}})
        missed = link(yes, [
            {"id": nid(), "name": "Tag missed call", "type": "add_contact_tag", "attributes": {"tags": ["missed call"]}},
            {"id": nid(), "name": "Record voicemail", "type": "ivr_collect_voicemail", "stepIndex": vm_index,
             "attributes": {"sayPlayAttributes": {"loop": 1, "widgetType": "say", "message": VOICEMAIL,
                                                  "type": "ivr_say", "language": "en-US", "voice": "woman"},
                            "isSayPlayOn": True, "timeout": 5, "finishOnKey": "", "maxLength": 3600,
                            "playBeep": True, "type": "ivr_collect_voicemail"}}])
        next(s for s in steps if s["id"] == yes)["next"] = missed[0]["id"]
        steps += missed
    return steps


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--only", required=True)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--publish", action="store_true", help="go live (changes how the main line answers)")
    args = parser.parse_args()
    load_dotenv()
    a = Agency()
    d = location_dirs([args.only])[0]
    loc = load(d / "location.json", {})["id"]
    numbers = a.call("GET", SERVICES, f"/phone-system/numbers/location/{loc}")["numbers"]
    main_line = next(n for n in numbers if n.get("isDefaultNumber"))
    forward = main_line.get("forwardingNumber")
    business = SPOKEN.get(loc) or load(d / "location.json", {})["name"]
    menu = MENUS.get(loc)
    if menu:
        greeting, options = menu["greeting"], menu["options"]
    else:
        assert forward, "main line has no forwarding number to ring"
        greeting = GREETING.format(business=business)
        options = [(digit, name, tag, forward, "the office") for digit, name, tag in OPTIONS]
    print(f"== {business}: IVR on {[n['phoneNumber'] for n in numbers]} (todas as linhas)")
    print(f"   «{greeting}»")
    for digit, name, _, number, who in options:
        print(f"   {digit or 'sem tecla'}: {name} → {who} {spoken(number)}; sem atender → tag missed call + voicemail")
    steps = build(greeting, options)
    for s in steps:
        print(f"   [{s['type']}] {s['name']}")
    if not args.apply:
        return 0
    bdir = ROOT / "backup" / d.name
    bdir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    (bdir / f"phone-numbers-{stamp}.json").write_text(json.dumps(numbers))
    existing = next((w for w in a.workflows(loc) if w["name"] == NAME), None)
    folders = {v: k for k, v in a.folders(loc).items()}
    parent = folders.get("09 System") or folders.get("01 Incoming Lead")
    if existing:
        live = a.workflow(loc, existing["id"])
        (bdir / f"workflow-{existing['id']}-{stamp}.json").write_text(json.dumps(live))
        wid, version = existing["id"], live.get("version", 1)
    else:
        res = a.call("POST", BACKEND, f"/workflow/{loc}", body={"name": NAME, "parentId": parent, "status": "draft"})
        wid, version = res.get("id") or res.get("_id"), 1
    have = {t["name"].lower() for t in a.tags(loc)}
    for tag in [o[2] for o in options if o[2] and o[2] not in have]:
        a.call("POST", BACKEND, f"/workflow/{loc}/tags/create", body={"tag": tag})
    status = "published" if args.publish else "draft"
    a.call("PUT", BACKEND, f"/workflow/{loc}/{wid}", body={
        "name": NAME, "version": version, "status": status, "parentId": parent, "allowMultiple": True,
        "workflowData": {"templates": steps}})
    trig = {"type": "ivr_incoming_call", "name": "Start IVR Trigger", "masterType": "highlevel", "schedule_config": {},
            "conditions": [{"operator": "contains-any", "field": "inbound_number", "value": [n["phoneNumber"] for n in numbers],
                            "title": "In phone number", "type": "multiselect", "id": "inbound-twilio-number"}],
            "actions": [{"workflow_id": wid, "type": "add_to_workflow"}], "workflowId": wid, "workflow_id": wid,
            "location_id": loc, "targetActionId": steps[0]["id"]}
    current = [t for t in a.triggers(loc, wid) if not t.get("deleted")]
    if not args.publish:
        pass  # no trigger on a draft: the trigger is what ties the number to the IVR
    elif current:
        a.call("PUT", BACKEND, f"/workflow/{loc}/trigger/{current[0]['id']}", body={**trig, "id": current[0]["id"]})
    else:
        res = a.call("POST", BACKEND, f"/workflow/{loc}/trigger", body=trig)
        if res.get("id"):
            a.call("PUT", BACKEND, f"/workflow/{loc}/trigger/{res['id']}", body={**trig, "id": res["id"]})
    time.sleep(4)
    after = a.workflow(loc, wid)
    got = (after.get("workflowData") or {}).get("templates") or []
    trs = [t for t in a.triggers(loc, wid) if not t.get("deleted")]
    print(f"   {after.get('status')} · {len(got)}/{len(steps)} passos · gatilhos={[(t['type'], t.get('active'), t['conditions'][0]['value']) for t in trs]}")
    print(f"   workflow {wid}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
