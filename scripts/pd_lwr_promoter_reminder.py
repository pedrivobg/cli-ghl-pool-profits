#!/usr/bin/env python3
"""Pool Duck Lakewood Ranch: one friendly Google-review reminder to the customers who rated us 4–5 in the review
campaign (Val, 21/10), sent Monday from 10 AM ET together with the reminder to the ones who didn't answer.

    set -a; . <poolduck.env>; set +a
    ./.venv/bin/python scripts/pd_lwr_promoter_reminder.py plan
    ./.venv/bin/python scripts/pd_lwr_promoter_reminder.py apply     # workflow + tags the current promoters (no send yet)
    ./.venv/bin/python scripts/pd_lwr_promoter_reminder.py check     # after Monday: who got it

Workflow "Review Reminder - Promoters (Turtle Rock)": tag REMINDER_TAG (and not "exclude from reviews") → waits for
the Monday window (10:00–16:00, account time zone) → drip like the campaign → SMS (the reminder text the client
approved for the campaign: "If you already left one, thank you so much!") + e-mail → tag SENT_TAG. Re-entry off: one
reminder per person. Only the promoters tagged at apply time get it (the 28 of 21/10); anyone who scores later already
gets the Google link right away. Editing the workflow before Monday still applies to the people waiting in it.
"""
from __future__ import annotations

import argparse
import sys
import time
import uuid

from _common import load_dotenv
from pd_lwr_nps_gate import TAGS
from pd_lwr_reviews import DRIP, DRIP_STEP, EXCLUDE_TAG, FOLDER, LWR, P, SEND_WINDOW, SMS_2

from cli_anything.gohighlevel.utils.agency import BACKEND, SERVICES, Agency

NAME = "Review Reminder - Promoters (Turtle Rock)"
REMINDER_TAG, SENT_TAG = "review reminder - promoters", "review reminder - promoters sent"
MONDAY = {"type": "time", "startAfter": {"type": "minutes", "value": 1, "when": "after"}, "name": "Wait for Monday 10 AM",
          "cat": "", "isHybridAction": True, "hybridActionType": "wait", "convertToMultipath": False, "transitions": [],
          "window": {"condition": "when", "days": [1], "start": SEND_WINDOW[0], "end": SEND_WINDOW[1]},
          "windowCondition": {"field": "", "operator": "", "value": ""}}
EMAIL_SUBJECT = "A quick reminder from Pool Duck Lakewood Ranch"
LINK = "{{custom_values.public_review_link}}"
EMAIL_HTML = "".join([
    P.format("Hi,"), "<br>",
    P.format("Thank you again for the great rating! If you haven't had a chance yet, we'd be grateful if you could "
             "share it on Google. It takes 30 seconds and helps other families in Lakewood Ranch find us."), "<br>",
    f'<p style="margin:0px"><a href="{LINK}" style="display:inline-block;padding:12px 22px;background:#60b847;'
    'color:#ffffff;text-decoration:none;border-radius:6px;font-family:helvetica;font-size:13pt;font-weight:bold">'
    'Leave a Google review</a></p>', "<br>",
    P.format("If you already left one, thank you so much!<br>The Pool Duck Lakewood Ranch team"),
])


def steps() -> list[dict]:
    chain = [("wait", "Wait for Monday 10 AM", MONDAY),
             ("drip", f"Drip Mode - {DRIP[0]} every {DRIP[1]} min", DRIP_STEP),
             ("sms", "SMS - Google review reminder", {"body": SMS_2, "attachments": []}),
             ("email", "Email - Google review reminder", {"subject": EMAIL_SUBJECT, "html": EMAIL_HTML,
                                                          "from_email": "", "from_name": "", "attachments": []}),
             ("add_contact_tag", f"Add Tag {SENT_TAG}", {"tags": [SENT_TAG], "type": "add_contact_tag"})]
    ids = [str(uuid.uuid4()) for _ in chain]
    out = []
    for i, (kind, name, attrs) in enumerate(chain):
        s = {"id": ids[i], "order": i, "name": name, "type": kind, "attributes": attrs}
        if i:
            s["parentKey"] = ids[i - 1]
        if i + 1 < len(chain):
            s["next"] = ids[i + 1]
        out.append(s)
    return out


def tagged(a: Agency, tag: str) -> list[dict]:
    out, page = [], 1
    while True:
        r = a.call("POST", SERVICES, "/contacts/search", body={"locationId": LWR, "pageLimit": 100, "page": page,
                                                               "filters": [{"field": "tags", "operator": "eq", "value": tag}]})
        out += r.get("contacts", [])
        if not r.get("contacts") or len(out) >= r.get("total", 0):
            return out
        page += 1


def apply(a: Agency) -> int:
    have = {t["name"].lower() for t in a.tags(LWR)}
    for t in (REMINDER_TAG, SENT_TAG):
        if t not in have:
            a.call("POST", BACKEND, f"/workflow/{LWR}/tags/create", body={"tag": t})
    parent = {v: k for k, v in a.folders(LWR).items()}.get(FOLDER)
    w = next((w for w in a.workflows(LWR) if w["name"] == NAME), None)
    if w:
        sys.exit(f"{NAME!r} já existe ({w['id']}): conferir antes de refazer")
    res = a.call("POST", BACKEND, f"/workflow/{LWR}", body={"name": NAME, "parentId": parent, "status": "draft"})
    wid = res.get("id") or res.get("_id")
    tpl = steps()
    a.call("PUT", BACKEND, f"/workflow/{LWR}/{wid}", body={
        "name": NAME, "version": 1, "status": "published", "parentId": parent, "allowMultiple": False,
        "workflowData": {"templates": tpl}})
    trig = {"type": "contact_tag", "name": "Contact Tag", "masterType": "highlevel", "schedule_config": {},
            "conditions": [{"operator": "index-of-true", "field": "tagsAdded", "value": REMINDER_TAG,
                            "title": "Tag Added", "type": "select", "id": "tag-added"},
                           {"field": "contact.tags", "id": "doesnot-have-tag", "title": "Doesn't Have Tag",
                            "type": "select", "operator": "index-of-false", "value": EXCLUDE_TAG}],
            "actions": [{"workflow_id": wid, "type": "add_to_workflow"}], "workflowId": wid, "workflow_id": wid,
            "location_id": LWR, "targetActionId": tpl[0]["id"]}
    res = a.call("POST", BACKEND, f"/workflow/{LWR}/trigger", body=trig)
    a.call("PUT", BACKEND, f"/workflow/{LWR}/trigger/{res['id']}", body={**trig, "id": res["id"]})
    time.sleep(5)
    after = a.workflow(LWR, wid)
    trs = [t for t in a.triggers(LWR, wid) if not t.get("deleted")]
    ok = after["status"] == "published" and len(after["workflowData"]["templates"]) == len(tpl) and \
        trs and all(t.get("active") for t in trs)
    print(f"   {'✓' if ok else '✗'} {NAME}: {after['status']} · {len(tpl)} passos · gatilho ativo={[t.get('active') for t in trs]}")
    if not ok:
        return 1
    promoters = [c for c in tagged(a, TAGS["high"]) if EXCLUDE_TAG not in (c.get("tags") or [])]
    for c in promoters:
        a.call("POST", SERVICES, f"/contacts/{c['id']}/tags", body={"tags": [REMINDER_TAG]})
    print(f"   ✓ {len(promoters)} promotores marcados com {REMINDER_TAG!r} (esperam a janela de segunda 10:00)")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("mode", choices=["plan", "apply", "check"])
    args = parser.parse_args()
    load_dotenv()
    a = Agency()
    if a.location(LWR).get("name") != "Pool Duck Lakewood Ranch":
        sys.exit("token não é o da Pool Duck (carregar poolduck.env)")
    if args.mode == "plan":
        promoters = [c for c in tagged(a, TAGS["high"]) if EXCLUDE_TAG not in (c.get("tags") or [])]
        print(f"== {NAME}: {len(promoters)} promotores · segunda {SEND_WINDOW[0]}–{SEND_WINDOW[1]} · drip {DRIP}")
        print(f"   SMS: {SMS_2}\n   E-mail: {EMAIL_SUBJECT}")
        return 0
    if args.mode == "apply":
        return apply(a)
    sent, waiting = tagged(a, SENT_TAG), tagged(a, REMINDER_TAG)
    print(f"   marcados {len(waiting)} · enviados {len(sent)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
