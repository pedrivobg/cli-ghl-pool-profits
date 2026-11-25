#!/usr/bin/env python3
"""Passion Pool Care: calls to the ChatGPT Ads line → card + alerts + OpenAI Conversions API (Val, ClickUp 86bc6vqr9, 25/11).

Live 25/11: +1 629-290-1180 ("OpenAI" line, forwards to 615-624-7624) only hit the generic Answered/Missed Incoming
Call To Pipeline flows: card, no alert, no source. This creates two workflows (nothing existing is changed):

1. "ChatGPT Ads Call In - New Lead" = copy of the live "AdWords Call In - New Lead" (SMS to the office +1 615-624-7624
   and Brad, e-mail to passionpoolcare@gmail.com and Brad, card in New Lead) with text "NEW LEAD FROM CHATGPT ADS",
   tags new lead / chatgpt ads / chatgpt ads call in, source "ChatGPT Ads - Call In". Trigger: inbound call to the line.
2. "ChatGPT Ads Call - OpenAI Conversion": trigger = ANSWERED (completed) inbound call to the line → if not spam / dnd /
   current customer → custom_webhook to n8n "Passion - OpenAI CAPI (ChatGPT Ads calls)" (MaPiK7MgXDfmSHiu), which hashes
   the phone (1 + 10 digits) / e-mail / contact id and posts lead_created, action_source phone_call, to pixel
   2vWucauJLhgQD55Sc9CKnL. The API key lives only in n8n. Event id = contact + minute (a retry never counts twice).

    python3 scripts/pc_chatgpt_call.py plan
    python3 scripts/pc_chatgpt_call.py test    # ZZ TEST copies: alerts → Pedro, webhook with validate_only; all deleted
    python3 scripts/pc_chatgpt_call.py apply
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
import time
import uuid

from _common import ROOT, load_dotenv
import ps_ads_forms as ps
from pp_lead_alerts import guard_nodes

from cli_anything.gohighlevel.utils.agency import BACKEND, SERVICES, Agency

LOC = "d03SMzI37dxTBeuoTJ13"
ps.LOC = LOC
LINE = "+16292901180"
BASE = "AdWords Call In - New Lead"
NAME = "ChatGPT Ads Call In - New Lead"
CAPI = "ChatGPT Ads Call - OpenAI Conversion"
TAGS = ["new lead", "chatgpt ads", "chatgpt ads call in"]
SOURCE = "ChatGPT Ads - Call In"
HOOK = "https://n8n.valenteai.cloud/webhook/oai-capi-passion-9d41e7b2c6"
SKIP = ["spam", "dnd", "current customer"]
BDIR = ROOT / "backup" / "passion-pool-care-lp"
TEST_EMAIL, TEST_PHONE = "pedro@poolprofits.com", "+5537998339401"


def nid() -> str:
    return str(uuid.uuid4())


def build_alerts(templates: list[dict], test: bool) -> list[dict]:
    raw = json.dumps(copy.deepcopy(templates))
    for old in {s["id"] for s in templates}:
        raw = raw.replace(old, nid())
    raw = raw.replace("GOOGLE ADWORDS", "CHATGPT ADS").replace("Google AdWords", "ChatGPT Ads").replace(
        "Google Adwords", "ChatGPT Ads")
    tpl = json.loads(raw)
    for s in tpl:
        at = s.get("attributes") or {}
        if s.get("type") == "add_contact_tag":
            at["tags"] = TAGS
        if s.get("type") == "create_opportunity":
            at["opportunity_source"] = SOURCE
        if test and s.get("type") == "internal_notification":
            if at.get("type") == "sms":
                at["sms"]["to"] = TEST_PHONE
            if at.get("type") == "email":
                at["email"]["to"] = TEST_EMAIL
                at["email"]["subject"] = "ZZ TEST " + (at["email"].get("subject") or "")
    return tpl


def build_capi(test: bool) -> list[dict]:
    c, yes, none = guard_nodes(None, None, 0, SKIP)
    body = {"contact_id": "{{contact.id}}", "phone_raw": "{{contact.phone_raw}}", "phone": "{{contact.phone}}",
            "email": "{{contact.email}}", "source": "Passion ChatGPT Ads call", "validate_only": "true" if test else "false"}
    hook = {"id": nid(), "order": 2, "name": "OpenAI CAPI - lead_created (phone_call)", "type": "custom_webhook",
            "parent": yes["id"], "parentKey": yes["id"],
            "attributes": {"event": "CUSTOM", "method": "POST", "url": HOOK,
                           "body": {"contentType": "application/json", "rawData": json.dumps(body, indent=1),
                                    "keyValueData": []},
                           "headers": [], "parameters": [], "authorization": {"type": "NONE", "data": None},
                           "saveResponse": False}}
    yes["next"] = hook["id"]
    return [c, yes, none, hook]


def call_trigger(wid: str, first: str, answered_only: bool) -> dict:
    cond = [{"operator": "==", "field": "message.direction", "value": "inbound", "title": "Call Direction", "type": "select"},
            {"operator": "contains-any", "field": "inbound_number", "value": [LINE], "title": "In Phone Number",
             "type": "multiselect", "id": "inbound-twilio-number"}]
    if answered_only:
        cond.append({"operator": "contains-any", "field": "call_status", "value": ["completed"], "title": "Call status",
                     "type": "multiselect"})
    return {"type": "call_status", "name": "Call Details", "masterType": "highlevel", "schedule_config": {},
            "conditions": cond, "workflowId": wid, "workflow_id": wid, "location_id": LOC,
            "actions": [{"workflow_id": wid, "type": "add_to_workflow"}], "targetActionId": first}


def publish(a: Agency, wid: str, name: str, folder: str | None) -> None:
    live = a.workflow(LOC, wid)
    a.call("PUT", BACKEND, f"/workflow/{LOC}/{wid}", body={"name": name, "version": live.get("version", 1),
           "status": "published", "parentId": folder, "allowMultiple": True,
           "workflowData": {"templates": live["workflowData"]["templates"]}})
    time.sleep(3)


def test(a: Agency, base: dict, folder: str | None) -> int:
    stamp = int(time.time())
    w1 = ps.create_flow(a, f"ZZ TEST {NAME}", folder, build_alerts(base["workflowData"]["templates"], True), False)
    w2 = ps.create_flow(a, f"ZZ TEST {CAPI}", folder, build_capi(True), False)
    for w, n in ((w1, NAME), (w2, CAPI)):
        publish(a, w, f"ZZ TEST {n}", folder)
    cid = a.call("POST", SERVICES, "/contacts/", body={
        "locationId": LOC, "firstName": "ZZ Test", "lastName": "chatgpt call", "phone": "+16155550142",
        "email": f"pedro+pc-gptcall-{stamp}@poolprofits.com"})["contact"]["id"]
    time.sleep(3)
    for w in (w1, w2):
        a.call("POST", SERVICES, f"/contacts/{cid}/workflow/{w}", body={})
    time.sleep(45)
    tg = set(a.call("GET", SERVICES, f"/contacts/{cid}")["contact"].get("tags") or [])
    opps = a.call("GET", SERVICES, "/opportunities/search", params={"location_id": LOC, "contact_id": cid}).get(
        "opportunities", [])
    ok_tags = set(TAGS) <= tg and "adwords" not in tg
    ok_card = any(o.get("source") == SOURCE for o in opps)
    print(f"   {'✓' if ok_tags else '✗'} tags {sorted(tg)}")
    print(f"   {'✓' if ok_card else '✗'} card {[(o.get('pipelineStageId'), o.get('source')) for o in opps]}")
    print(f"   contato {cid}: conferir a execução do n8n MaPiK7MgXDfmSHiu (validate_only) antes de apagar")
    for o in opps:
        a.call("DELETE", SERVICES, f"/opportunities/{o['id']}")
    a.call("DELETE", SERVICES, f"/contacts/{cid}")
    ps.drop_flow(a, w1)
    ps.drop_flow(a, w2)
    print("   limpo (card, contato e 2 fluxos ZZ TEST apagados); avisos de teste foram para o Pedro")
    return 0 if ok_tags and ok_card else 1


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("mode", choices=["plan", "test", "apply"])
    args = p.parse_args()
    load_dotenv()
    a = Agency()
    if "passion" not in a.location(LOC)["name"].lower():
        sys.exit("sub-conta errada")
    flows = {w["name"]: w["id"] for w in a.workflows(LOC)}
    base = a.workflow(LOC, flows[BASE])
    folder = base.get("parentId")
    print(f"   {NAME}: {'existe' if NAME in flows else 'cria'} · {CAPI}: {'existe' if CAPI in flows else 'cria'}")
    if args.mode == "plan":
        return 0
    for t in TAGS:
        try:
            a.call("POST", BACKEND, f"/workflow/{LOC}/tags/create", body={"tag": t})
        except Exception:  # noqa: BLE001 — already exists
            pass
    if args.mode == "test":
        return test(a, base, folder)
    BDIR.mkdir(parents=True, exist_ok=True)
    (BDIR / f"workflow-{flows[BASE]}-{int(time.time())}.json").write_text(json.dumps(base, indent=1))
    for name, tpl, answered in ((NAME, build_alerts(base["workflowData"]["templates"], False), False),
                                (CAPI, build_capi(False), True)):
        if name in flows:
            continue
        wid = ps.create_flow(a, name, folder, tpl, publish=False)
        body = call_trigger(wid, tpl[0]["id"], answered)
        t = a.call("POST", BACKEND, f"/workflow/{LOC}/trigger", body=body)
        a.call("PUT", BACKEND, f"/workflow/{LOC}/trigger/{t['id']}", body={**body, "id": t["id"]})
        time.sleep(2)
        publish(a, wid, name, folder)
        trs = [x for x in a.triggers(LOC, wid) if not x.get("deleted")]
        print(f"   ✓ {name} {wid} {a.workflow(LOC, wid).get('status')} · gatilhos "
              f"{[(x.get('type'), x.get('active'), x.get('conditions')) for x in trs]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
