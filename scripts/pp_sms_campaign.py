#!/usr/bin/env python3
"""Stay Fresh — drain & wash SMS campaign to the "active client" list (Frank/Mike, 16/10).

    ./.venv/bin/python scripts/pp_sms_campaign.py setup            # 2 workflows in DRAFT, nothing sent
    ./.venv/bin/python scripts/pp_sms_campaign.py launch --confirm # publish + tag the audience = SENDS
    ./.venv/bin/python scripts/pp_sms_campaign.py check            # after the send: sent tag / replies
    ./.venv/bin/python scripts/pp_sms_campaign.py setup --live     # change the published one (before any send)

Audience: contacts tagged "active client" (106 imported 14/10, 105 with phone, none DND). The campaign
is a tag-triggered workflow, so launch = add CAMPAIGN_TAG to the audience; the SMS goes from the
account's default number and replies land there. A second workflow catches replies from campaign
contacts: tag "drain wash interested" + SMS and e-mail to Mike with the reply.
Text: exactly Mike's copy (Pedro, 16/10: no edits, whatever the length — 8 SMS segments). A2P is
approved (Pedro). setup also rewrites the SMS of the draft if the copy here changes.
Send time (Frank, 16/10: "Client said Monday 9am"): the campaign's first step is a wait with an advance
window (SEND_DAY, SEND_WINDOW, account time zone America/Phoenix), so launch can run any day before —
GHL holds everyone and sends when the window opens; nothing here has to run at 9am. The SMS step then
adds SENT_TAG, and only contacts with SENT_TAG count as replies (no false alerts while they wait).
Drip (Pedro, 17/10: "drip mode, não todos ao mesmo tempo"): a drip step after the wait releases DRIP[0]
contacts every DRIP[1] minutes. Contacts already parked in the wait follow an edit of the published
workflow (tested on Test Snapshot), so setup --live can add it after launch, while nothing went out.
"""
from __future__ import annotations

import argparse
import json
import time
import uuid

from _common import ROOT, load_dotenv, location_dirs
from pp_audit import load
from pp_won_stage import DROP

from cli_anything.gohighlevel.utils.agency import BACKEND, SERVICES, Agency

ACCOUNT = "Stay Fresh"
AUDIENCE = "active client"
CAMPAIGN_TAG = "drain wash campaign"
REPLY_TAG = "drain wash interested"
SENT_TAG = "drain wash sent"
SEND_DAY = 1  # GHL window days: Sunday = 0 → Monday
SEND_WINDOW = ("09:00", "09:30")
DRIP = (10, 5)  # batch size, minutes between batches → 105 contacts from 9:00 to ~9:50
NAME = "Drain & Wash Campaign - Active Clients"
REPLIES = "Drain & Wash Campaign - Replies"
NOTIFY = "Mike Redman"
TEXT = ("Now’s the time to freshen up your pool! 💦 We recommend a drain & wash every 2 years, based on water "
        "and surface conditions, to reduce mineral buildup, improve water chemistry, and support surface and "
        "equipment longevity.\n\nWe use Pool Wash by Plaster Logic instead of muriatic acid—a gentler approach "
        "that helps preserve your pool’s finish.\n\nPlus, there’s no better time to clean that nasty calcium "
        "buildup off your tile!\n\nReply to schedule. Let’s get your pool Stay Fresh!")


def step(name: str, type_: str, attributes: dict) -> dict:
    return {"id": str(uuid.uuid4()), "name": name, "type": type_, "attributes": attributes}


def chain(steps: list[dict]) -> list[dict]:
    for i, s in enumerate(steps):
        s["order"] = i
        if i:
            s["parentKey"] = steps[i - 1]["id"]
            steps[i - 1]["next"] = s["id"]
    return steps


def wait_window() -> dict:
    return step("Wait until Monday 9am", "wait", {
        "type": "time", "startAfter": {"type": "minutes", "value": 1, "when": "after"}, "name": "Wait until Monday 9am",
        "cat": "", "isHybridAction": True, "hybridActionType": "wait", "convertToMultipath": False, "transitions": [],
        "window": {"condition": "when", "days": [SEND_DAY], "start": SEND_WINDOW[0], "end": SEND_WINDOW[1]},
        "windowCondition": {"field": "", "operator": "", "value": ""}})


def drip_step() -> dict:
    return step(f"Drip Mode - {DRIP[0]} every {DRIP[1]} min", "drip", {
        "batchSize": DRIP[0], "interval": {"timeUnit": "minutes", "value": DRIP[1]}, "type": "drip"})


def campaign_steps(sms: dict, have: list[dict] | None = None) -> list[dict]:
    """wait for the window → drip → SMS → SENT_TAG; steps already in `have` keep their ids."""
    ids = {s["type"]: s["id"] for s in have or []}
    out = []
    for s in (wait_window(), drip_step(), sms,
              step("Add Tag sent", "add_contact_tag", {"tags": [SENT_TAG], "type": "add_contact_tag"})):
        s = {k: v for k, v in s.items() if k not in ("order", "next", "parentKey")}
        out.append({**s, "id": ids.get(s["type"], s["id"])})
    return chain(out)


def shape(tpl: list[dict]) -> list[tuple]:
    """What setup compares (GHL adds fields of its own to saved steps)."""
    keys = ("window", "batchSize", "interval", "body", "tags")
    return [(s["type"], s["id"], s.get("next"), json.dumps({k: (s.get("attributes") or {}).get(k) for k in keys},
                                                         sort_keys=True)) for s in tpl]


def reply_conditions(tag: str) -> list[dict]:
    return [{"operator": "==", "field": "message.type", "value": 2, "title": "Reply channel", "type": "select"},
            {"operator": "index-of-true", "field": "contact.tags", "value": tag, "title": "Has tag",
             "type": "select", "id": "has-tag"}]


def put_trigger(a: Agency, loc: str, wid: str, t: dict, **changes) -> None:
    body = {k: v for k, v in t.items() if k not in DROP}
    body.update(workflowId=wid, workflow_id=wid, location_id=loc,
                actions=[{"workflow_id": wid, "type": "add_to_workflow"}], **changes)
    a.call("PUT", BACKEND, f"/workflow/{loc}/trigger/{t['id']}", body=body)


def backup(slug: str, a: Agency, loc: str, wid: str, live: dict) -> None:
    d = ROOT / "backup" / slug
    d.mkdir(parents=True, exist_ok=True)
    trs = [t for t in a.triggers(loc, wid) if not t.get("deleted")]
    (d / f"workflow-{wid}-{time.strftime('%Y%m%d-%H%M%S')}.json").write_text(
        json.dumps({"workflow": live, "triggers": trs}, ensure_ascii=False))


def make(a: Agency, loc: str, name: str, parent: str | None, steps: list[dict], trigger: dict) -> str:
    res = a.call("POST", BACKEND, f"/workflow/{loc}", body={"name": name, "parentId": parent, "status": "draft"})
    wid = res.get("id") or res.get("_id")
    a.call("PUT", BACKEND, f"/workflow/{loc}/{wid}", body={
        "name": name, "version": 1, "status": "draft", "parentId": parent, "allowMultiple": False,
        "workflowData": {"templates": steps}})
    trig = {**trigger, "masterType": "highlevel", "schedule_config": {}, "workflowId": wid, "workflow_id": wid,
            "location_id": loc, "actions": [{"workflow_id": wid, "type": "add_to_workflow"}],
            "targetActionId": steps[0]["id"]}
    t = a.call("POST", BACKEND, f"/workflow/{loc}/trigger", body=trig)
    a.call("PUT", BACKEND, f"/workflow/{loc}/trigger/{t['id']}", body={**trig, "id": t["id"]})
    return wid


def audience(a: Agency, loc: str) -> list[dict]:
    out, page = [], 1
    while True:
        r = a.call("POST", SERVICES, "/contacts/search", body={
            "locationId": loc, "pageLimit": 100, "page": page,
            "filters": [{"field": "tags", "operator": "contains", "value": AUDIENCE}]})
        out += r.get("contacts", [])
        if len(r.get("contacts", [])) < 100:
            return out
        page += 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("mode", choices=["setup", "launch", "check"])
    parser.add_argument("--confirm", action="store_true", help="launch: really send")
    parser.add_argument("--live", action="store_true", help="setup: allow changing the published campaign "
                                                            "while nothing was sent")
    args = parser.parse_args()
    load_dotenv()
    a = Agency()
    d = location_dirs([ACCOUNT])[0]
    loc = load(d / "location.json", {})["id"]
    flows = {w["name"]: w for w in a.workflows(loc)}
    users = {u.get("name"): u for u in a.users(loc)}
    text = TEXT
    everyone = audience(a, loc)
    people = [c for c in everyone if c.get("phone") and not c.get("dnd")]
    print(f"== {d.name}: público '{AUDIENCE}' com telefone e sem DND: {len(people)}")
    if args.mode == "check":
        for tag in (CAMPAIGN_TAG, SENT_TAG, REPLY_TAG):
            print(f"   {tag!r}: {sum(tag in (c.get('tags') or []) for c in everyone)}")
        for name in (NAME, REPLIES):
            print(f"   {name}: {a.workflow(loc, flows[name]['id'])['status']}")
        return 0
    if args.mode == "setup":
        for tag in (CAMPAIGN_TAG, REPLY_TAG, SENT_TAG):
            try:
                a.call("POST", BACKEND, f"/workflow/{loc}/tags/create", body={"tag": tag})
            except Exception:
                pass  # already exists
        parent = a.workflow(loc, flows["Reactivation Campaign - SMS"]["id"]).get("parentId") \
            if "Reactivation Campaign - SMS" in flows else None
        mike = users[NOTIFY]
        if NAME not in flows:
            wid = make(a, loc, NAME, parent, campaign_steps(step("Drain & Wash SMS", "sms", {"body": text, "attachments": []})),
                       {"type": "contact_tag", "name": "Contact Tag", "conditions": [
                           {"operator": "index-of-true", "field": "tagsAdded", "value": CAMPAIGN_TAG,
                            "title": "Tag added", "type": "select", "id": "tag-added"}]})
            print(f"   ✓ {NAME} (draft) {wid}")
        else:  # keep the workflow equal to TEXT + wait window + drip + sent tag
            wid = flows[NAME]["id"]
            live = a.workflow(loc, wid)
            tpl = json.loads(json.dumps(live["workflowData"]["templates"]))
            sms = next(s for s in tpl if s["type"] == "sms")
            have = {s["type"]: s for s in tpl}
            want = campaign_steps({**sms, "attributes": {**sms["attributes"], "body": text}}, tpl)
            for s in want:  # keep what GHL added to steps that stay (configuredAt, …)
                if s["type"] in have and s["type"] != "sms":
                    s["attributes"] = {**have[s["type"]]["attributes"], **s["attributes"]}
            if shape(want) != shape(tpl):
                sent = sum(SENT_TAG in (c.get("tags") or []) for c in everyone)
                if live["status"] != "draft" and not (args.live and sent == 0):
                    raise SystemExit(f"{NAME} já está {live['status']} ({sent} enviados) — só com --live e antes "
                                     "de qualquer envio")
                backup(d.name, a, loc, wid, live)
                a.call("PUT", BACKEND, f"/workflow/{loc}/{wid}", body={
                    "name": live["name"], "version": live.get("version", 1), "status": live["status"],
                    "parentId": live.get("parentId"), "allowMultiple": False, "workflowData": {"templates": want}})
                for t in a.triggers(loc, wid):
                    if not t.get("deleted") and t.get("targetActionId") != want[0]["id"]:
                        put_trigger(a, loc, wid, t, targetActionId=want[0]["id"])
                time.sleep(3)
                got = a.workflow(loc, wid)
                ok = shape(got["workflowData"]["templates"]) == shape(want) and got["status"] == live["status"]
                print(f"   {'✓' if ok else '✗ VERIFICAR'} {NAME} ({got['status']}): espera {SEND_WINDOW} dia {SEND_DAY}"
                      f" → drip {DRIP[0]} a cada {DRIP[1]} min → SMS → '{SENT_TAG}'")
        if REPLIES in flows:  # replies only count after the SMS went out
            wid = flows[REPLIES]["id"]
            for t in [t for t in a.triggers(loc, wid) if not t.get("deleted")]:
                if any(c.get("id") == "has-tag" and c.get("value") != SENT_TAG for c in t.get("conditions") or []):
                    live = a.workflow(loc, wid)
                    if live["status"] != "draft":
                        raise SystemExit(f"{REPLIES} já está {live['status']} — não mexo no gatilho")
                    backup(d.name, a, loc, wid, live)
                    put_trigger(a, loc, wid, t, conditions=reply_conditions(SENT_TAG))
                    print(f"   ✓ {REPLIES}: gatilho só para quem tem '{SENT_TAG}'")
        else:
            body = "💦 Drain & wash reply from {{contact.name}} {{contact.phone}}:\n\n{{message.body}}"
            steps = chain([
                step("Add Tag interested", "add_contact_tag", {"tags": [REPLY_TAG], "type": "add_contact_tag"}),
                step("SMS to Mike", "internal_notification", {"type": "sms", "sms": {
                    "body": body, "userType": "user", "selectedUser": [mike["id"]], "attachments": []}}),
                step("Email to Mike", "internal_notification", {"type": "email", "email": {
                    "isCloned": False, "userType": "custom_email", "to": mike["email"], "attachments": [],
                    "subject": "Drain & wash reply: {{contact.name}}",
                    "html": "<p>{{contact.name}} ({{contact.phone}}) replied to the drain &amp; wash text:</p>"
                            "<p>{{message.body}}</p>"}})])
            wid = make(a, loc, REPLIES, parent, steps, {"type": "customer_reply", "name": "Customer Replied",
                                                        "conditions": reply_conditions(SENT_TAG)})
            print(f"   ✓ {REPLIES} (draft) {wid}")
        print(f"   texto ({len(text)} caracteres):\n{text}")
        return 0
    if not args.confirm:
        raise SystemExit("launch envia SMS para o público — rode com --confirm só depois do OK")
    first, second = a.workflow(loc, flows[NAME]["id"])["workflowData"]["templates"][:2]
    if first["type"] != "wait" or first["attributes"].get("window", {}).get("days") != [SEND_DAY] \
            or second["type"] != "drip":
        raise SystemExit(f"{NAME} não começa com espera {SEND_WINDOW} + drip — rode setup antes (senão envia na hora)")
    for name in (REPLIES, NAME):  # replies first, so no answer is missed
        live = a.workflow(loc, flows[name]["id"])
        a.call("PUT", BACKEND, f"/workflow/{loc}/{flows[name]['id']}", body={
            "name": live["name"], "version": live.get("version", 1), "status": "published",
            "parentId": live.get("parentId"), "allowMultiple": False, "workflowData": live["workflowData"]})
    time.sleep(5)
    for c in people:
        a.call("POST", SERVICES, f"/contacts/{c['id']}/tags", body={"tags": [CAMPAIGN_TAG]})
    print(f"   ✓ publicado e tag '{CAMPAIGN_TAG}' em {len(people)} contatos — o SMS sai no dia {SEND_DAY} "
          f"(0 = domingo) entre {SEND_WINDOW[0]} e {SEND_WINDOW[1]}, fuso da conta")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
