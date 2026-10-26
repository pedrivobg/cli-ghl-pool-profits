#!/usr/bin/env python3
"""Poolheads: their old GHL account's call routing and after-hours reply, rebuilt in our Poolheads sub-account so the
main number (+1 936-314-9255, "Poolheads Main Service") can be ported in (Pedro 21/10; screenshots of the old account).

    ./.venv/bin/python scripts/pp_poolheads_port.py plan
    ./.venv/bin/python scripts/pp_poolheads_port.py apply                    # both workflows as DRAFT (nothing changes)
    ./.venv/bin/python scripts/pp_poolheads_port.py go-live                  # after the port: IVR on every line + publish

Old account → here:
- "Business Hours Call Routing" (IVR on the main line): Mon–Fri 9–5 rings the team (Felipe's app/deskphone and his cell,
  where the line forwarded before; Jorge once he is a user here), not answered → voicemail; outside those hours →
  voicemail. Voicemail plays their own recorded greeting from the old account (22/10). The old flow then texted "Hi this is Poolheads, We are
  sorry we missed your call! …". Here the IVR tags "missed call" instead, and that text (verbatim, config/
  poolheads_wording.json) is SMS 1 of our "Missed New Lead - Initial SMS Follow-up": the caller gets the same first text,
  once, and our follow-up and pipeline card keep working (with an IVR every call is "completed", so the missed-call
  trigger would never fire). The number's "This call will be recorded for quality purposes." plays at the start.
- "After Hours Message": a text from a customer outside Mon–Fri 9–5 gets their after-hours reply (verbatim).
Business hours in the account's time zone (America/Chicago). go-live adds the IVR trigger with every number in the
account (the ported one included) and publishes both; GET + backup before writes.
"""
from __future__ import annotations

import argparse
import json
import sys
import time

from _common import ROOT, load_dotenv
from pp_ivr import IS_OPS, NEST, link, nid

from cli_anything.gohighlevel.utils.agency import BACKEND, SERVICES, Agency

LOC = "PeUynYCMm8e6PJMy785O"  # Poolheads
TEAM = ["PTRbzJWOILyLyoz9aOfK"]  # Felipe Cobo (+ Jorge Arias when he has a user here)
IVR, AFTER = "Business Hours Call Routing", "After Hours Message"
OPEN = ("weekday", "900", "1700")  # Mon–Fri 9:00–17:00, account time zone
RECORDING = "This call will be recorded for quality purposes."
# Their own voicemail greeting from the old account (Frank, 22/10: Poolheads_Voicemail_1.mp3), in this account's media
# library; the text is its transcription (shown in the builder). Used for both voicemail steps (it says "closed or
# helping another customer").
VM_AUDIO = "https://assets.cdn.filesafe.space/PeUynYCMm8e6PJMy785O/media/6ada863ffdcb71bb828255e9.mp3"
VM_TEXT = ("Thank you for calling Poolheads. Sorry we missed your call. We're either closed or helping another customer. "
           "Our hours are 9 a.m. to 5 p.m. If this is an emergency, please turn off your pool equipment. Leave your name "
           "and a brief message and we'll get back to you as soon as possible. Thank you.")
# The main line forwarded to Felipe's cell before the IVR: ring it too, so calls reach him even before the
# LeadConnector app / deskphone are set up on this account.
FELIPE_CELL = "+12818188794"
AFTER_SMS = ("Thanks for contacting Poolheads! Our hours are 9am- 5pm Monday to Friday. If this is an emergency please "
             "turn off the power of your pool or spa equipment. We will reach out as soon as possible!")  # verbatim


def cond(sub: str, op: str, value: str) -> dict:
    return {"conditionType": "date_time", "conditionSubType": sub, "conditionOperator": op, "conditionValue": value,
            "__conditionId": nid(), "ifElseNodeId": "", "__customFieldType__": "standard", "isWait": False,
            "nestedDropdownTypes": NEST, "allowIsOperatorTypes": IS_OPS}


def hours_split(name: str, order: int, parent: str | None = None, parent_key: str | None = None) -> tuple[dict, dict, dict]:
    """if/else 'open' (Mon–Fri 9–5) / None = closed. Returns (condition node, open branch, closed branch)."""
    head, b_open, b_closed = nid(), nid(), nid()
    day, start, end = OPEN
    node = {"id": head, "order": order, "name": name, "type": "if_else", "cat": "conditions", "comments": [],
            "nodeType": "condition-node", "next": [b_open, b_closed],
            "attributes": {"currentRecipeType": "CUSTOM", "operator": "and", "if": True, "conditionName": name,
                           "version": 2, "noneBranchName": "Closed",
                           "branches": [{"id": b_open, "name": "Open (Mon-Fri 9-5)", "operator": "and",
                                         "showErrors": False, "branchNameError": "Branch name cannot be empty!",
                                         "segments": [{"__segmentId": nid(), "operator": "and", "conditions": [
                                             cond("day_week", "==", day), cond("quarter_hour", ">=", start),
                                             cond("quarter_hour", "<", end)]}]}]}}
    if parent:
        node["parent"] = parent
    if parent_key:
        node["parentKey"] = parent_key
    opened = {"id": b_open, "name": "Open (Mon-Fri 9-5)", "type": "if_else", "parent": head, "parentKey": head,
              "cat": "conditions", "comments": [], "nodeType": "branch-yes", "sibling": [b_closed], "order": order + 1,
              "attributes": {"if": False, "conditionName": "Condition", "operator": "and", "branches": []}}
    closed = {"id": b_closed, "name": "Closed", "type": "if_else", "parent": head, "parentKey": head,
              "cat": "conditions", "comments": [], "nodeType": "branch-no", "sibling": [b_open], "order": order + 1,
              "attributes": {"else": True}}
    return node, opened, closed


def say(text: str) -> dict:
    return {"loop": 1, "widgetType": "say", "message": text, "type": "ivr_say", "language": "en-US", "voice": "woman"}


def voicemail(index: int) -> dict:
    play = {**say(VM_TEXT), "widgetType": "play", "audioUrl": VM_AUDIO}
    return {"id": nid(), "name": "Record voicemail", "type": "ivr_collect_voicemail", "stepIndex": index,
            "attributes": {"sayPlayAttributes": play, "isSayPlayOn": True, "timeout": 5, "finishOnKey": "",
                           "maxLength": 360, "playBeep": True, "type": "ivr_collect_voicemail"}}


def missed_tag() -> dict:
    return {"id": nid(), "name": "Tag missed call", "type": "add_contact_tag",
            "attributes": {"tags": ["missed call"], "type": "add_contact_tag"}}


def ivr_steps() -> list[dict]:
    intro = {"id": nid(), "order": 0, "name": "Recording notice", "type": "ivr_say", "stepIndex": 1,
             "attributes": say(RECORDING)}
    head, opened, closed = hours_split("Check Business Hours (9am-5pm)", 1, parent_key=intro["id"])
    intro["next"] = head["id"]
    ring = {"id": nid(), "name": "Ring the team", "type": "ivr_connect_call", "stepIndex": 2, "attributes": {
        "timeout": 20, "timeLimit": 3600, "userId": "", "users": TEAM, "detectVoicemail": False, "isSayPlayOn": False,
        "customNumbers": [{"country": "US", "phone": FELIPE_CELL, "displayValue": "(281) 818-8794", "isValid": True}], "record": "record-from-answer", "sayPlayAttributes": say("")}}
    check, not_answered, answered = nid(), nid(), nid()
    answered_q = {"id": check, "name": "Answered?", "type": "if_else", "cat": "conditions", "comments": [],
                  "nodeType": "condition-node", "next": [not_answered, answered],
                  "attributes": {"currentRecipeType": "CUSTOM", "operator": "and", "if": True,
                                 "conditionName": "Condition", "version": 2, "noneBranchName": "Answered",
                                 "branches": [{"id": not_answered, "name": "Not answered", "operator": "and",
                                               "showErrors": False, "branchNameError": "Branch name cannot be empty!",
                                               "segments": [{"__segmentId": nid(), "operator": "and", "conditions": [{
                                                   "conditionType": "ivr_connect_call",
                                                   "conditionSubType": "2.dialCallStatus", "conditionOperator": "!=",
                                                   "conditionValue": "completed", "__conditionId": nid(),
                                                   "ifElseNodeId": "", "__customFieldType__": "standard",
                                                   "isWait": False, "nestedDropdownTypes": NEST,
                                                   "allowIsOperatorTypes": IS_OPS}]}]}]}}
    open_chain = link(opened["id"], [ring, answered_q])
    opened["next"] = ring["id"]
    branches = [{"id": not_answered, "name": "Not answered", "type": "if_else", "parent": check, "parentKey": check,
                 "cat": "conditions", "sibling": [answered], "comments": [], "nodeType": "branch-yes", "order": 2,
                 "attributes": {"if": False, "conditionName": "Condition", "operator": "and", "branches": []}},
                {"id": answered, "name": "Answered", "type": "if_else", "parent": check, "parentKey": check,
                 "cat": "conditions", "sibling": [not_answered], "comments": [], "nodeType": "branch-no", "order": 2,
                 "attributes": {"else": True}}]
    missed = link(not_answered, [missed_tag(), voicemail(3)])
    branches[0]["next"] = missed[0]["id"]
    after = link(closed["id"], [missed_tag(), voicemail(4)])
    closed["next"] = after[0]["id"]
    return [intro, head, opened, closed, *open_chain, *branches, *missed, *after]


def after_steps() -> list[dict]:
    head, opened, closed = hours_split("Outside business hours?", 0)
    sms = {"id": nid(), "name": "Send After Hours Message", "type": "sms", "order": 0, "parent": closed["id"],
           "parentKey": closed["id"], "attributes": {"body": AFTER_SMS, "attachments": []}}
    closed["next"] = sms["id"]
    return [head, opened, closed, sms]


def folder(a: Agency, name: str) -> str | None:
    return {v: k for k, v in a.folders(LOC).items()}.get(name)


def upsert(a: Agency, name: str, tpl: list[dict], parent: str | None) -> str:
    existing = next((w for w in a.workflows(LOC) if w["name"] == name), None)
    bdir = ROOT / "backup" / "poolheads"
    bdir.mkdir(parents=True, exist_ok=True)
    if existing:
        live = a.workflow(LOC, existing["id"])
        if live["status"] == "published":
            sys.exit(f"{name!r} já está publicado: não reconstruir por cima")
        (bdir / f"workflow-{existing['id']}-{time.strftime('%Y%m%d-%H%M%S')}.json").write_text(json.dumps(live))
        wid, version = existing["id"], live.get("version", 1)
    else:
        res = a.call("POST", BACKEND, f"/workflow/{LOC}", body={"name": name, "parentId": parent, "status": "draft"})
        wid, version = res.get("id") or res.get("_id"), 1
    a.call("PUT", BACKEND, f"/workflow/{LOC}/{wid}", body={
        "name": name, "version": version, "status": "draft", "parentId": parent, "allowMultiple": True,
        "workflowData": {"templates": tpl}})
    return wid


def trigger(a: Agency, wid: str, body: dict, first: str) -> None:
    base = {"masterType": "highlevel", "schedule_config": {}, "workflowId": wid, "workflow_id": wid,
            "location_id": LOC, "actions": [{"workflow_id": wid, "type": "add_to_workflow"}], "targetActionId": first}
    current = [t for t in a.triggers(LOC, wid) if not t.get("deleted")]
    if current:
        a.call("PUT", BACKEND, f"/workflow/{LOC}/trigger/{current[0]['id']}", body={**base, **body, "id": current[0]["id"]})
    else:
        t = a.call("POST", BACKEND, f"/workflow/{LOC}/trigger", body={**base, **body})
        a.call("PUT", BACKEND, f"/workflow/{LOC}/trigger/{t['id']}", body={**base, **body, "id": t["id"]})


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("mode", choices=["plan", "apply", "go-live"])
    args = parser.parse_args()
    load_dotenv()
    a = Agency()
    if a.location(LOC)["name"] != "Poolheads":
        sys.exit("sub-conta errada")
    if args.mode == "plan":
        for name, tpl in ((IVR, ivr_steps()), (AFTER, after_steps())):
            print(f"== {name}: " + " · ".join(f"[{s['type']}] {s['name']}" for s in tpl))
        return 0
    if args.mode == "apply":
        tpl = after_steps()
        wid = upsert(a, AFTER, tpl, folder(a, "01 Incoming Lead"))
        trigger(a, wid, {"type": "customer_reply", "name": "Customer Replied", "conditions": [
            {"operator": "==", "field": "message.type", "value": 2, "title": "Reply channel", "type": "select"}]},
            tpl[0]["id"])
        ivr = upsert(a, IVR, ivr_steps(), folder(a, "09 System"))
        time.sleep(3)
        for name, w in ((AFTER, wid), (IVR, ivr)):
            got = a.workflow(LOC, w)
            trs = [t["type"] for t in a.triggers(LOC, w) if not t.get("deleted")]
            print(f"   ✓ {name}: {got['status']} · {len(got['workflowData']['templates'])} passos · gatilhos {trs} · {w}")
        return 0
    numbers = [n["phoneNumber"] for n in a.call("GET", SERVICES, f"/phone-system/numbers/location/{LOC}")["numbers"]]
    if "+19363149255" not in numbers:
        sys.exit(f"o 936-314-9255 ainda não está nesta conta (linhas: {numbers}): esperar a portabilidade")
    flows = {w["name"]: w["id"] for w in a.workflows(LOC)}
    ivr = a.workflow(LOC, flows[IVR])
    trigger(a, ivr["id"], {"type": "ivr_incoming_call", "name": "Start IVR Trigger", "conditions": [
        {"operator": "contains-any", "field": "inbound_number", "value": numbers, "title": "In phone number",
         "type": "multiselect", "id": "inbound-twilio-number"}]}, ivr["workflowData"]["templates"][0]["id"])
    for name in (IVR, AFTER):
        live = a.workflow(LOC, flows[name])
        a.call("PUT", BACKEND, f"/workflow/{LOC}/{live['id']}", body={
            "name": name, "version": live.get("version", 1), "status": "published", "parentId": live.get("parentId"),
            "workflowData": {"templates": live["workflowData"]["templates"]}})
    time.sleep(4)
    for name in (IVR, AFTER):
        trs = [(t["type"], t.get("active")) for t in a.triggers(LOC, flows[name]) if not t.get("deleted")]
        print(f"   {name}: {a.workflow(LOC, flows[name])['status']} · {trs}")
    nums = a.call("GET", SERVICES, f"/phone-system/numbers/location/{LOC}")["numbers"]
    print("   linhas:", [(n["phoneNumber"], n.get("inboundCallService")) for n in nums])
    return 0


if __name__ == "__main__":
    sys.exit(main())
