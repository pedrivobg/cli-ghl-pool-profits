#!/usr/bin/env python3
"""Orange Tree (Val, 14/10): every lead form also e-mails the client.

    ./.venv/bin/python scripts/pp_lead_email.py test --to pedro@poolprofits.com   # Test Snapshot
    ./.venv/bin/python scripts/pp_lead_email.py test --to pedro@poolprofits.com --loc nptD4SfaNCSR95LjTJsb  # sent by Orange Tree
    ./.venv/bin/python scripts/pp_lead_email.py plan
    ./.venv/bin/python scripts/pp_lead_email.py apply

Found live: no form and no workflow sent e-mail (forms: emailNotifications false; workflows: SMS only);
the Facebook form's SMS went to the contact owner, which these contacts never have; and the client's
phone (623) 974-5300 answered "Stop" to an alert on 09/03, so no internal SMS reaches it since.
This adds an internal e-mail notification (custom e-mail, same format as Passion's live ones) right
after the existing alert in each lead workflow, and points the Facebook form SMS to the account owner.
Backup of each workflow in backup/<slug>/ first.
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

ACCOUNT = "Orange Tree"
TO = "orangetreepools@gmail.com"
SMS_TO = ["0ijzATNg4PxprYIhQnhz"]  # Stephen Sherman (both users share the same phone)
P = '<p style="margin:0px;font-family:verdana,geneva,sans-serif;font-size:16px;">{}</p>'
DETAILS = ["Name: {{contact.name}}", "Phone: {{contact.phone}}", "Email: {{contact.email}}",
           "Address: {{contact.address1}} {{contact.city}} {{contact.postal_code}}", "Source: {{contact.source}}"]
FLOWS = {  # workflow → (subject, headline, extra lines)
    "Facebook Form - New Lead": ("🚨 New Facebook lead: {{contact.name}}", "🚨 NEW LEAD FROM FACEBOOK 🚨", []),
    "Website Form Fill To Pipeline": ("🚨 New website lead: {{contact.name}}", "🚨 NEW LEAD FROM YOUR WEBSITE 🚨", []),
    "Incoming Chat To Pipeline": ("💬 New web chat: {{contact.name}}", "💬 NEW WEB CHAT REQUEST 💬",
                                  ["Message: {{message.body}}"]),
}
TEST_LOC = "hmzX5j1dPhOQKX2dH4kf"  # Test Snapshot


def email_step(subject: str, headline: str, extra: list[str], to: str) -> dict:
    html = P.format(f"<strong>{headline}</strong>") + "<br/>" + "".join(P.format(x) for x in DETAILS + extra)
    return {"id": str(uuid.uuid4()), "name": "New Lead Email", "type": "internal_notification",
            "attributes": {"type": "email", "email": {"isCloned": False, "html": html, "to": to,
                                                       "userType": "custom_email", "subject": subject,
                                                       "attachments": []}}}


def insert_after(templates: list[dict], after_id: str, step: dict) -> list[dict]:
    """Linear chain only: step goes between after_id and its next."""
    out = json.loads(json.dumps(templates))
    if any(s["type"] == "if_else" for s in out):
        raise SystemExit("workflow has branches — not inserting blindly")
    by_id = {s["id"]: s for s in out}
    prev = by_id[after_id]
    step = dict(step, parentKey=prev["id"], order=prev["order"] + 1)
    if prev.get("next"):
        step["next"] = prev["next"]
        by_id[prev["next"]]["parentKey"] = step["id"]
    prev["next"] = step["id"]
    for s in out:
        if s["order"] > prev["order"]:
            s["order"] += 1
    return out + [step]


def alert_of(templates: list[dict]) -> dict:
    return next(s for s in templates if s["type"] == "internal_notification" and s["attributes"].get("type") == "sms")


def put(a: Agency, loc: str, wid: str, live: dict, templates: list[dict]) -> None:
    a.call("PUT", BACKEND, f"/workflow/{loc}/{wid}", body={
        "name": live["name"], "version": live.get("version", 1), "status": live["status"],
        "parentId": live.get("parentId"), "allowMultiple": live.get("allowMultiple", False),
        "workflowData": {"templates": templates}})


def apply(a: Agency, do: bool) -> int:
    d = location_dirs([ACCOUNT])[0]
    loc = load(d / "location.json", {})["id"]
    flows = {w["name"]: w["id"] for w in a.workflows(loc)}
    stamp = time.strftime("%Y%m%d-%H%M%S")
    bdir = ROOT / "backup" / d.name
    bdir.mkdir(parents=True, exist_ok=True)
    bad = 0
    for name, (subject, headline, extra) in FLOWS.items():
        wid = flows[name]
        live = a.workflow(loc, wid)
        tpl = live["workflowData"]["templates"]
        if any(s["attributes"].get("type") == "email" and s["attributes"]["email"].get("to") == TO
               for s in tpl if s["type"] == "internal_notification"):
            print(f"   {name}: já manda e-mail para {TO}")
            continue
        alert = alert_of(tpl)
        new = insert_after(tpl, alert["id"], email_step(subject, headline, extra, TO))
        fix_sms = alert["attributes"]["sms"].get("userType") == "assign"
        if fix_sms:
            sms = next(s for s in new if s["id"] == alert["id"])
            sms["attributes"]["sms"].pop("assignedOwners", None)
            sms["attributes"]["sms"].update(userType="user", selectedUser=SMS_TO)
            sms.pop("incompleteData", None)
        print(f"   {name} [{live['status']}]: + e-mail para {TO} depois de '{alert['name']}'"
              + (" · SMS: dono do contato → Stephen" if fix_sms else ""))
        if not do:
            continue
        trs = [t for t in a.triggers(loc, wid) if not t.get("deleted")]
        (bdir / f"workflow-{wid}-{stamp}.json").write_text(json.dumps({"workflow": live, "triggers": trs}))
        put(a, loc, wid, live, new)
        time.sleep(4)
        after = a.workflow(loc, wid)
        got = [s for s in after["workflowData"]["templates"] if s["type"] == "internal_notification"
               and s["attributes"].get("type") == "email"]
        ok = len(got) == 1 and got[0]["attributes"]["email"]["to"] == TO and after["status"] == live["status"] \
            and len(after["workflowData"]["templates"]) == len(tpl) + 1
        bad += not ok
        print(f"      {'✓' if ok else '✗ VERIFICAR'} {after['status']} · {len(after['workflowData']['templates'])} passos")
    for name in FLOWS:  # notifications after the card, so tags/card land in ~2 s (Val, 14/10)
        wid = flows[name]
        live = a.workflow(loc, wid)
        tpl = live["workflowData"]["templates"]
        new = notify_after_card(tpl)
        if [s["id"] for s in chain_of(new)] == [s["id"] for s in chain_of(tpl)]:
            continue
        print(f"   {name}: {' → '.join(s['name'] for s in chain_of(new))}")
        if not do:
            continue
        trs = [t for t in a.triggers(loc, wid) if not t.get("deleted")]
        (bdir / f"workflow-{wid}-{stamp}-order.json").write_text(json.dumps({"workflow": live, "triggers": trs}))
        put(a, loc, wid, live, new)
        for t in trs:
            body = {k: v for k, v in t.items() if k not in DROP}
            body.update(workflowId=wid, workflow_id=wid, location_id=loc, targetActionId=chain_of(new)[0]["id"],
                        actions=[{"workflow_id": wid, "type": "add_to_workflow"}])
            a.call("PUT", BACKEND, f"/workflow/{loc}/trigger/{t['id']}", body=body)
        time.sleep(4)
        after = a.workflow(loc, wid)["workflowData"]["templates"]
        ok = [s["id"] for s in chain_of(after)] == [s["id"] for s in chain_of(new)] and len(chain_of(after)) == len(after)
        bad += not ok
        print(f"      {'✓' if ok else '✗ VERIFICAR'} ordem nova")
    return bad


def chain_of(templates: list[dict]) -> list[dict]:
    by_id = {s["id"]: s for s in templates}
    chain = [next(s for s in templates if not s.get("parentKey"))]
    while chain[-1].get("next"):
        chain.append(by_id[chain[-1]["next"]])
    return chain


def notify_after_card(templates: list[dict]) -> list[dict]:
    """Move internal notifications that run before 'Create Or Update Opportunity' to right after it."""
    chain = json.loads(json.dumps(chain_of(templates)))
    if len(chain) != len(templates) or any(s["type"] == "if_else" for s in chain):
        return templates
    card = next((i for i, s in enumerate(chain) if s["type"] == "create_opportunity"), None)
    early = [s for s in chain[:card or 0] if s["type"] == "internal_notification"]
    if not early:
        return templates
    rest = [s for s in chain if s not in early]
    at = rest.index(next(s for s in rest if s["type"] == "create_opportunity")) + 1
    chain = rest[:at] + early + rest[at:]
    for i, s in enumerate(chain):
        s["order"] = i
        s.pop("parentKey", None)
        s.pop("next", None)
        if i:
            s["parentKey"] = chain[i - 1]["id"]
            chain[i - 1]["next"] = s["id"]
    return chain


def run_test(a: Agency, to: str, loc: str = TEST_LOC) -> int:
    """Throwaway workflow in Test Snapshot: tag → SMS-less alert chain → e-mail to `to`."""
    go = "lead email test go"
    try:
        a.call("POST", BACKEND, f"/workflow/{loc}/tags/create", body={"tag": go})
    except Exception:
        pass
    res = a.call("POST", BACKEND, f"/workflow/{loc}", body={"name": "TMP lead email test", "status": "draft"})
    wid = res.get("id") or res.get("_id")
    tag = {"id": str(uuid.uuid4()), "order": 0, "name": "Add Tag", "type": "add_contact_tag",
           "attributes": {"tags": ["lead email test done"], "type": "add_contact_tag"}}
    tpl = insert_after([tag], tag["id"], email_step(*FLOWS["Facebook Form - New Lead"], to))
    a.call("PUT", BACKEND, f"/workflow/{loc}/{wid}", body={"name": "TMP lead email test", "version": 1,
                                                           "status": "published", "workflowData": {"templates": tpl}})
    trig = {"type": "contact_tag", "name": "Contact Tag", "masterType": "highlevel", "schedule_config": {},
            "conditions": [{"operator": "index-of-true", "field": "tagsAdded", "value": go, "title": "Tag Added",
                            "type": "select", "id": "tag-added"}], "workflowId": wid, "workflow_id": wid,
            "location_id": loc, "actions": [{"workflow_id": wid, "type": "add_to_workflow"}],
            "targetActionId": tpl[0]["id"]}
    t = a.call("POST", BACKEND, f"/workflow/{loc}/trigger", body=trig)
    a.call("PUT", BACKEND, f"/workflow/{loc}/trigger/{t['id']}", body={**trig, "id": t["id"]})
    time.sleep(5)
    c = a.call("POST", SERVICES, "/contacts/upsert", body={
        "locationId": loc, "firstName": "TEST lead email", "lastName": "Pool Profits", "email": "lead-email-test@example.com",
        "address1": "123 Test St", "city": "Phoenix", "postalCode": "85001", "source": "FORM - FB ADS"})
    cid = c["contact"]["id"]
    time.sleep(3)
    a.call("POST", SERVICES, f"/contacts/{cid}/tags", body={"tags": [go]})
    time.sleep(30)
    tags = a.call("GET", SERVICES, f"/contacts/{cid}")["contact"].get("tags", [])
    ran = "lead email test done" in tags
    print(f"   {'✓' if ran else '✗'} workflow rodou · e-mail de teste enviado para {to} (conferir a caixa)")
    a.call("DELETE", SERVICES, f"/contacts/{cid}")
    try:
        a.call("DELETE", BACKEND, f"/workflow/{loc}/{wid}")
    except Exception as e:
        print(f"   apagar à mão: TMP lead email test ({wid}): {e}")
    return 0 if ran else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("mode", choices=["test", "plan", "apply"])
    parser.add_argument("--to", help="test: inbox that gets the sample e-mail")
    parser.add_argument("--loc", default=TEST_LOC, help="test: location that sends it (default Test Snapshot)")
    args = parser.parse_args()
    load_dotenv()
    a = Agency()
    if args.mode == "test":
        if not args.to:
            parser.error("--to is required for test")
        return run_test(a, args.to, args.loc)
    return 1 if apply(a, args.mode == "apply") else 0


if __name__ == "__main__":
    raise SystemExit(main())
