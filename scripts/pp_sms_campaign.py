#!/usr/bin/env python3
"""Stay Fresh — drain & wash SMS campaign to the "active client" list (Frank/Mike, 16/10).

    ./.venv/bin/python scripts/pp_sms_campaign.py setup            # 2 workflows in DRAFT, nothing sent
    ./.venv/bin/python scripts/pp_sms_campaign.py launch --confirm # publish + tag the audience = SENDS
    ./.venv/bin/python scripts/pp_sms_campaign.py check            # after the send: sent tag / replies

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


def campaign_steps(sms: dict) -> list[dict]:
    """wait for the window → SMS → SENT_TAG (keeps the SMS step's id)."""
    return chain([wait_window(), {k: v for k, v in sms.items() if k not in ("order", "next", "parentKey")},
                  step("Add Tag sent", "add_contact_tag", {"tags": [SENT_TAG], "type": "add_contact_tag"})])


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
        else:  # keep the draft equal to TEXT + wait window + sent tag
            wid = flows[NAME]["id"]
            live = a.workflow(loc, wid)
            tpl = json.loads(json.dumps(live["workflowData"]["templates"]))
            sms = next(s for s in tpl if s["type"] == "sms")
            want = campaign_steps({**sms, "attributes": {**sms["attributes"], "body": text}})
            if tpl[0]["type"] == "wait":  # already wrapped: keep its step ids
                want = tpl
                want[[s["id"] for s in tpl].index(sms["id"])]["attributes"]["body"] = text
            if want != live["workflowData"]["templates"]:
                if live["status"] != "draft":
                    raise SystemExit(f"{NAME} já está {live['status']} — não mexo numa campanha no ar")
                backup(d.name, a, loc, wid, live)
                a.call("PUT", BACKEND, f"/workflow/{loc}/{wid}", body={
                    "name": live["name"], "version": live.get("version", 1), "status": "draft",
                    "parentId": live.get("parentId"), "allowMultiple": False, "workflowData": {"templates": want}})
                for t in a.triggers(loc, wid):
                    if not t.get("deleted") and t.get("targetActionId") != want[0]["id"]:
                        put_trigger(a, loc, wid, t, targetActionId=want[0]["id"])
                time.sleep(3)
                got = a.workflow(loc, wid)["workflowData"]["templates"]
                ok = [s["type"] for s in got] == ["wait", "sms", "add_contact_tag"] and got[1]["attributes"]["body"] == text
                print(f"   {'✓' if ok else '✗ VERIFICAR'} {NAME}: espera {SEND_WINDOW} dia {SEND_DAY} → SMS → '{SENT_TAG}'")
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
    first = a.workflow(loc, flows[NAME]["id"])["workflowData"]["templates"][0]
    if first["type"] != "wait" or first["attributes"].get("window", {}).get("days") != [SEND_DAY]:
        raise SystemExit(f"{NAME} não começa com a espera de {SEND_WINDOW} — rode setup antes (senão envia na hora)")
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
