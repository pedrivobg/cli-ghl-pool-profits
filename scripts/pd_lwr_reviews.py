#!/usr/bin/env python3
"""Pool Duck Lakewood Ranch: one-time Google review request to current clients ("turtle rock"),
leaving out the people Connie listed (email of 07/10, Ed's clarification of 09/10).

    set -a; . <poolduck.env>; set +a
    ./.venv/bin/python scripts/pd_lwr_reviews.py setup     # exclusion tags, review link, workflow
    ./.venv/bin/python scripts/pd_lwr_reviews.py test      # 2 test contacts: one gets it, the excluded one must not
    ./.venv/bin/python scripts/pd_lwr_reviews.py launch    # SENDS: tags every turtle rock client not excluded

Exclusions: dump/poolduck/lwr-review-exclusions.json (names matched to contacts; client data,
gitignored) → tag "exclude from reviews". The workflow only starts on tag "send review request"
for contacts that do NOT have "exclude from reviews" (trigger filter, same shape as the GHL UI),
and launch() also skips them, so the list is enforced twice.
Messages go straight to the Google review page of "Pool Duck of Lakewood Ranch" (no incentive,
no rating gate: both are against Google's review policy). Names are mostly ALL CAPS in this
account, so the texts do not use {{contact.first_name}}.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import uuid

from _common import ROOT, load_dotenv

from cli_anything.gohighlevel.utils.agency import BACKEND, SERVICES, Agency

LWR = "MosKIX4oux96vchwHZ5W"
EXCLUDE_TAG, LAUNCH_TAG, CLIENT_TAG = "exclude from reviews", "send review request", "turtle rock"
NAME = "Review Request Campaign - Turtle Rock"
FOLDER = "7. Reviews & Referrals"
REVIEW_LINK = "https://search.google.com/local/writereview?placeid=ChIJd2NJBNZuh4cRKlAZHY8HW3Y"
EXCLUSIONS = ROOT / "dump" / "poolduck" / "lwr-review-exclusions.json"

SMS_1 = ("Hi, this is Pool Duck Lakewood Ranch! Thank you for trusting us with your pool. Would you take "
         "30 seconds to leave us a quick Google review? It means a lot to our local team: "
         "{{custom_values.public_review_link}}")
SMS_2 = ("Hi again from Pool Duck Lakewood Ranch! If you haven't had a chance yet, we'd be grateful for a "
         "quick Google review: {{custom_values.public_review_link}} If you already left one, thank you so much!")
EMAIL_SUBJECT = "Quick favor from Pool Duck Lakewood Ranch?"
P = '<p style="margin:0px"><span style="font-size: 13pt; font-family: helvetica">{}</span></p>'
EMAIL_HTML = "".join([
    P.format("Hi,"), "<br>",
    P.format("Thank you for trusting Pool Duck Lakewood Ranch with your pool. Reviews from customers like you "
             "help other families in Lakewood Ranch find a pool service they can count on."), "<br>",
    P.format("Would you take 30 seconds to share your experience on Google?"), "<br>",
    '<p style="margin:0px"><a href="{{custom_values.public_review_link}}" style="display:inline-block;'
    'padding:12px 22px;background:#60b847;color:#ffffff;text-decoration:none;border-radius:6px;'
    'font-family:helvetica;font-size:13pt;font-weight:bold">Leave a Google review</a></p>', "<br>",
    P.format("Thank you!<br>The Pool Duck Lakewood Ranch team"),
])
WAIT = {"type": "time", "startAfter": {"type": "days", "value": 4, "when": "after"}, "name": "Wait 4 days",
        "cat": "", "timePeriodInputMode": "standard", "unitInputMode": "standard", "isHybridAction": True,
        "hybridActionType": "wait", "convertToMultipath": False, "transitions": []}


def steps(wid: str) -> list[dict]:
    chain = [("sms", "SMS - Review Request", {"body": SMS_1, "attachments": []}),
             ("email", "Email - Review Request", {"subject": EMAIL_SUBJECT, "html": EMAIL_HTML, "from_email": "",
                                                  "from_name": "", "attachments": []}),
             ("wait", "Wait 4 days", WAIT),
             ("sms", "SMS - Reminder", {"body": SMS_2, "attachments": []}),
             ("remove_from_workflow", "End", {"type": "remove_from_workflow", "workflow_id": [wid]})]
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


def ensure_tags(a: Agency) -> None:
    have = {t["name"].lower() for t in a.tags(LWR)}
    for tag in (EXCLUDE_TAG, LAUNCH_TAG):
        if tag not in have:
            a.call("POST", BACKEND, f"/workflow/{LWR}/tags/create", body={"tag": tag})


def setup(a: Agency) -> None:
    ensure_tags(a)
    excl = json.loads(EXCLUSIONS.read_text())["exclude"]
    for e in excl:
        a.call("POST", SERVICES, f"/contacts/{e['id']}/tags", body={"tags": [EXCLUDE_TAG]})
    print(f"✓ tag {EXCLUDE_TAG!r} em {len(excl)} contatos")

    cvs = {(c.get("fieldKey") or "").replace(" ", ""): c for c in a.custom_values(LWR)}
    cv = cvs.get("{{custom_values.public_review_link}}")
    if cv and cv.get("value") != REVIEW_LINK:
        a.call("PUT", SERVICES, f"/locations/{LWR}/customValues/{cv['id']}", body={"name": cv["name"], "value": REVIEW_LINK})
    elif not cv:
        a.call("POST", SERVICES, f"/locations/{LWR}/customValues", body={"name": "Public Review Link", "value": REVIEW_LINK})
    print(f"✓ public_review_link = {REVIEW_LINK}")

    parent = {v: k for k, v in a.folders(LWR).items()}.get(FOLDER)
    w = next((w for w in a.workflows(LWR) if w["name"] == NAME), None)
    if w:
        wid, version = w["id"], a.workflow(LWR, w["id"]).get("version", 1)
    else:
        res = a.call("POST", BACKEND, f"/workflow/{LWR}", body={"name": NAME, "parentId": parent, "status": "draft"})
        wid, version = res.get("id") or res.get("_id"), 1
    templates = steps(wid)
    a.call("PUT", BACKEND, f"/workflow/{LWR}/{wid}", body={
        "name": NAME, "version": version, "status": "published", "parentId": parent, "allowMultiple": False,
        "workflowData": {"templates": templates}})
    trig = {"type": "contact_tag", "name": "Contact Tag", "masterType": "highlevel", "schedule_config": {},
            "conditions": [{"operator": "index-of-true", "field": "tagsAdded", "value": LAUNCH_TAG,
                            "title": "Tag Added", "type": "select", "id": "tag-added"},
                           {"field": "contact.tags", "id": "doesnot-have-tag", "title": "Doesn't Have Tag",
                            "type": "select", "operator": "index-of-false", "value": EXCLUDE_TAG}],
            "actions": [{"workflow_id": wid, "type": "add_to_workflow"}], "workflowId": wid, "workflow_id": wid,
            "location_id": LWR, "targetActionId": templates[0]["id"]}
    current = [t for t in a.triggers(LWR, wid) if not t.get("deleted")]
    if current:
        a.call("PUT", BACKEND, f"/workflow/{LWR}/trigger/{current[0]['id']}", body={**trig, "id": current[0]["id"]})
    else:
        res = a.call("POST", BACKEND, f"/workflow/{LWR}/trigger", body=trig)
        a.call("PUT", BACKEND, f"/workflow/{LWR}/trigger/{res['id']}", body={**trig, "id": res["id"]})
    time.sleep(4)
    after = a.workflow(LWR, wid)
    trs = [t for t in a.triggers(LWR, wid) if not t.get("deleted")]
    print(f"✓ {NAME} [{after.get('status')}] {' → '.join(s['type'] for s in after['workflowData']['templates'])}"
          f" · gatilho {[(c.get('title'), c.get('value')) for c in trs[0]['conditions']]} ativo={trs[0].get('active')}")


def messages(a: Agency, cid: str) -> list[tuple]:
    out = []
    for cv in a.call("GET", SERVICES, "/conversations/search", params={"locationId": LWR, "contactId": cid}).get("conversations", []):
        for m in (a.call("GET", SERVICES, f"/conversations/{cv['id']}/messages", params={"limit": 10}).get("messages") or {}).get("messages", []):
            out.append((m.get("messageType") or m.get("type"), m.get("status"), (m.get("body") or m.get("subject") or "")[:60]))
    return out


def test(a: Agency, email: str) -> None:
    made = {}
    for label, mail, tags in (("recebe", email, []), ("excluído", "test.review.excluded@example.com", [EXCLUDE_TAG])):
        c = a.call("POST", SERVICES, "/contacts/", body={"locationId": LWR, "firstName": "TEST - review campaign",
                                                          "lastName": f"({label}, please ignore)", "email": mail, "tags": tags})
        made[label] = (c.get("contact") or c)["id"]
    time.sleep(3)
    for cid in made.values():
        a.call("POST", SERVICES, f"/contacts/{cid}/tags", body={"tags": [LAUNCH_TAG]})
    for _ in range(12):
        time.sleep(10)
        got = {k: messages(a, v) for k, v in made.items()}
        if got["recebe"]:
            break
    time.sleep(20)
    got = {k: messages(a, v) for k, v in made.items()}
    for k, v in got.items():
        print(f"   {k}: {v or 'nenhuma mensagem'}")
    ok = bool(got["recebe"]) and not got["excluído"]
    print(f"{'✓' if ok else '✗ VERIFICAR'} teste: o contato normal recebeu, o excluído não recebeu nada")
    print("   contatos de teste:", made)


def launch(a: Agency) -> None:
    excluded = {e["id"] for e in json.loads(EXCLUSIONS.read_text())["exclude"]}
    contacts, page = [], 1
    while True:
        r = a.call("POST", SERVICES, "/contacts/search", body={"locationId": LWR, "pageLimit": 100, "page": page,
                                                               "filters": [{"field": "tags", "operator": "contains", "value": CLIENT_TAG}]})
        contacts += r.get("contacts", [])
        if len(r.get("contacts", [])) < 100:
            break
        page += 1
    targets = [c for c in contacts if c["id"] not in excluded and EXCLUDE_TAG not in c.get("tags", [])
               and LAUNCH_TAG not in c.get("tags", [])]
    log = ROOT / "backup" / "pool-duck-lakewood-ranch" / f"review-campaign-launch-{time.strftime('%Y%m%d-%H%M%S')}.json"
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text(json.dumps([c["id"] for c in targets]))
    print(f"enviando para {len(targets)} de {len(contacts)} clientes turtle rock (lista em {log.name})")
    for i, c in enumerate(targets, 1):
        a.call("POST", SERVICES, f"/contacts/{c['id']}/tags", body={"tags": [LAUNCH_TAG]})
        if i % 50 == 0:
            print(f"   {i}/{len(targets)}")
    print(f"✓ {len(targets)} contatos marcados com {LAUNCH_TAG!r}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("action", choices=["setup", "test", "launch"])
    parser.add_argument("--test-email", default="pedro@poolprofits.com")
    args = parser.parse_args()
    load_dotenv()
    a = Agency()
    {"setup": lambda: setup(a), "test": lambda: test(a, args.test_email), "launch": lambda: launch(a)}[args.action]()
    return 0


if __name__ == "__main__":
    sys.exit(main())
