#!/usr/bin/env python3
"""Stay Fresh — drain & wash SMS campaign to the "active client" list (Frank/Mike, 16/10).

    ./.venv/bin/python scripts/pp_sms_campaign.py setup            # 2 workflows in DRAFT, nothing sent
    ./.venv/bin/python scripts/pp_sms_campaign.py setup --plain    # same, GSM-only text (4 segments, not 8)
    ./.venv/bin/python scripts/pp_sms_campaign.py launch --confirm # publish + tag the audience = SENDS

Audience: contacts tagged "active client" (106 imported 14/10, 105 with phone, none DND). The campaign
is a tag-triggered workflow, so launch = add CAMPAIGN_TAG to the audience; the SMS goes from the
account's default number and replies land there. A second workflow catches replies from campaign
contacts: tag "drain wash interested" + SMS and e-mail to Mike with the reply.
Before launch: A2P 10DLC approved for Stay Fresh (Settings → Phone System → Trust Center), final OK on
the copy, and a send time (business hours, Arizona).
"""
from __future__ import annotations

import argparse
import json
import time
import uuid

from _common import load_dotenv, location_dirs
from pp_audit import load

from cli_anything.gohighlevel.utils.agency import BACKEND, SERVICES, Agency

ACCOUNT = "Stay Fresh"
AUDIENCE = "active client"
CAMPAIGN_TAG = "drain wash campaign"
REPLY_TAG = "drain wash interested"
NAME = "Drain & Wash Campaign - Active Clients"
REPLIES = "Drain & Wash Campaign - Replies"
NOTIFY = "Mike Redman"
TEXT = ("Now’s the time to freshen up your pool! 💦 We recommend a drain & wash every 2 years, based on water "
        "and surface conditions, to reduce mineral buildup, improve water chemistry, and support surface and "
        "equipment longevity.\n\nWe use Pool Wash by Plaster Logic instead of muriatic acid—a gentler approach "
        "that helps preserve your pool’s finish.\n\nPlus, there’s no better time to clean that nasty calcium "
        "buildup off your tile!\n\nReply to schedule. Let’s get your pool Stay Fresh!\n\nReply STOP to opt out.")


def plain(text: str) -> str:
    """Same copy in the GSM alphabet: 4 SMS segments instead of 8 (emoji/curly quotes/dash force Unicode)."""
    return text.replace("’", "'").replace("—", " - ").replace(" 💦", "")


def step(name: str, type_: str, attributes: dict) -> dict:
    return {"id": str(uuid.uuid4()), "name": name, "type": type_, "attributes": attributes}


def chain(steps: list[dict]) -> list[dict]:
    for i, s in enumerate(steps):
        s["order"] = i
        if i:
            s["parentKey"] = steps[i - 1]["id"]
            steps[i - 1]["next"] = s["id"]
    return steps


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
    parser.add_argument("mode", choices=["setup", "launch"])
    parser.add_argument("--plain", action="store_true", help="GSM-only text")
    parser.add_argument("--confirm", action="store_true", help="launch: really send")
    args = parser.parse_args()
    load_dotenv()
    a = Agency()
    d = location_dirs([ACCOUNT])[0]
    loc = load(d / "location.json", {})["id"]
    flows = {w["name"]: w for w in a.workflows(loc)}
    users = {u.get("name"): u for u in a.users(loc)}
    text = plain(TEXT) if args.plain else TEXT
    people = [c for c in audience(a, loc) if c.get("phone") and not c.get("dnd")]
    print(f"== {d.name}: público '{AUDIENCE}' com telefone e sem DND: {len(people)}")
    if args.mode == "setup":
        for tag in (CAMPAIGN_TAG, REPLY_TAG):
            try:
                a.call("POST", BACKEND, f"/workflow/{loc}/tags/create", body={"tag": tag})
            except Exception:
                pass  # already exists
        parent = a.workflow(loc, flows["Reactivation Campaign - SMS"]["id"]).get("parentId") \
            if "Reactivation Campaign - SMS" in flows else None
        mike = users[NOTIFY]
        if NAME not in flows:
            wid = make(a, loc, NAME, parent, chain([step("Drain & Wash SMS", "sms", {"body": text, "attachments": []})]),
                       {"type": "contact_tag", "name": "Contact Tag", "conditions": [
                           {"operator": "index-of-true", "field": "tagsAdded", "value": CAMPAIGN_TAG,
                            "title": "Tag added", "type": "select", "id": "tag-added"}]})
            print(f"   ✓ {NAME} (draft) {wid}")
        if REPLIES not in flows:
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
            wid = make(a, loc, REPLIES, parent, steps, {"type": "customer_reply", "name": "Customer Replied", "conditions": [
                {"operator": "==", "field": "message.type", "value": 2, "title": "Reply channel", "type": "select"},
                {"operator": "index-of-true", "field": "contact.tags", "value": CAMPAIGN_TAG, "title": "Has tag",
                 "type": "select", "id": "has-tag"}]})
            print(f"   ✓ {REPLIES} (draft) {wid}")
        print(f"   texto ({len(text)} caracteres):\n{text}")
        return 0
    if not args.confirm:
        raise SystemExit("launch envia SMS para o público — rode com --confirm só depois do OK")
    for name in (REPLIES, NAME):  # replies first, so no answer is missed
        live = a.workflow(loc, flows[name]["id"])
        a.call("PUT", BACKEND, f"/workflow/{loc}/{flows[name]['id']}", body={
            "name": live["name"], "version": live.get("version", 1), "status": "published",
            "parentId": live.get("parentId"), "allowMultiple": False, "workflowData": live["workflowData"]})
    time.sleep(5)
    for c in people:
        a.call("POST", SERVICES, f"/contacts/{c['id']}/tags", body={"tags": [CAMPAIGN_TAG]})
    print(f"   ✓ publicado e tag '{CAMPAIGN_TAG}' em {len(people)} contatos")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
