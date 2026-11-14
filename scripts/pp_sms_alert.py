#!/usr/bin/env python3
"""Every text a contact sends to any line of the account → text to the owner's cell (Ed, 13/11).

Ed (ClickUp DM 13/11): "make sure all clients receive all inbound texts and calls and update the newest snapshot".
Live check on Sparkling Clear (13/11): a text to the Website & GBP line made a card but alerted nobody; texts to the
Adwords and LSA lines did nothing at all. In the standard setup only reactivation replies sent an SMS to the team.

What it creates (new workflow, nothing existing is changed):
  "Inbound SMS - Notify Owner"  trigger Customer Replied, channel SMS, any line, contact without tag spam / dnd /
  zz test → internal SMS to the owner (user = Business Profile representative; fallback: the only user with a phone).
  Re-entry on (every text alerts). Nothing goes to the contact.

    ./.venv/bin/python scripts/pp_sms_alert.py plan --all
    ./.venv/bin/python scripts/pp_sms_alert.py apply --only "Sparkling Clear"
    ./.venv/bin/python scripts/pp_sms_alert.py apply --only "Snapshot Pool Profits" --template   # master: no owner
    ./.venv/bin/python scripts/pp_sms_alert.py testprep --only "Sparkling Clear" --phone +55...    # live test (see docs)
    ./.venv/bin/python scripts/pp_sms_alert.py testcheck --only "Sparkling Clear" --phone +55...   # verify + clean up

Live test (inbound texts can't be simulated by API): testprep tags Pedro's contact "zz test" (so the real workflow skips
him) and creates "ZZ TEST inbound sms" (same trigger, only "zz test" contacts, stand-in tag instead of the SMS). Pedro
texts the Adwords line (no other workflow listens to it); testcheck looks for the stand-in tag and deletes the contact,
its conversation and the ZZ workflow.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import uuid

from _common import ROOT, Agency, load_dotenv, select, slugify
from cli_anything.gohighlevel.utils.agency import BACKEND, SERVICES

NAME = "Inbound SMS - Notify Owner"
TEST_NAME = "ZZ TEST inbound sms"
SKIP_TAGS = ["spam", "dnd", "zz test"]
TEST_MARK = "zz inbound sms ok"
NOT_CLIENT = {"pool profits", "test snapshot", "snapshot pool profits", "pool profits (sales)", "pool profits - sample",
              "damon's pool care - billing only", "master pool service snapshot v1", "nathan taylor's account", "test inc"}
BODY = ("\U0001F4AC New text to {{location.name}}\n\nFrom: {{contact.name}}\nPhone: {{contact.phone}}\n\n"
        "{{message.body}}\n\n{{message.attachments}}\n\nReply in the GHL app (Conversations).")


def stamp() -> str:
    return time.strftime("%Y%m%d-%H%M%S")


def owner(a: Agency, loc: str) -> tuple[dict | None, str]:
    full = a.location(loc)
    rep = (full.get("authorizedRepresentative") or {}).get("email", "").lower()
    users = a.users(loc)
    u = next((u for u in users if rep and (u.get("email") or "").lower() == rep), None)
    if u and u.get("phone"):
        return u, "representante do Business Profile"
    with_phone = [u for u in users if u.get("phone")]
    if len(with_phone) == 1:
        return with_phone[0], "único usuário com telefone"
    return None, f"sem dono claro (rep={'sim' if u else 'não'}, usuários com telefone={len(with_phone)})"


def conditions(test: bool) -> list[dict]:
    out = [{"operator": "==", "field": "message.type", "value": 2, "title": "Reply channel", "type": "select"}]
    if test:
        out.append({"field": "contact.tags", "id": "has-tag", "title": "Has Tag", "type": "select",
                    "operator": "index-of-true", "value": "zz test"})
    else:
        out += [{"field": "contact.tags", "id": "doesnot-have-tag", "title": "Doesn't Have Tag", "type": "select",
                 "operator": "index-of-false", "value": t} for t in SKIP_TAGS]
    return out


def create(a: Agency, loc: str, name: str, step: dict, status: str, test: bool = False) -> str:
    res = a.call("POST", BACKEND, f"/workflow/{loc}", body={"name": name, "status": "draft"})
    wid = res.get("id") or res.get("_id")
    sid = str(uuid.uuid4())
    tpl = [{"id": sid, "order": 0, "name": step.pop("name"), **step}]
    link = {"workflowId": wid, "workflow_id": wid, "location_id": loc,
            "actions": [{"workflow_id": wid, "type": "add_to_workflow"}]}
    trig = {"type": "customer_reply", "name": "Customer Replied", "masterType": "highlevel", "schedule_config": {},
            "conditions": conditions(test), **link, "targetActionId": sid}
    a.call("PUT", BACKEND, f"/workflow/{loc}/{wid}", body={"name": name, "version": 1, "status": "draft",
           "allowMultiple": True, "workflowData": {"templates": tpl}})
    t = a.call("POST", BACKEND, f"/workflow/{loc}/trigger", body=trig)
    a.call("PUT", BACKEND, f"/workflow/{loc}/trigger/{t['id']}", body={**trig, "id": t["id"]})
    if status == "published":
        live = a.workflow(loc, wid)
        a.call("PUT", BACKEND, f"/workflow/{loc}/{wid}", body={"name": name, "version": live.get("version", 2),
               "status": "published", "allowMultiple": True, "workflowData": live["workflowData"]})
    return wid


def alert_step(user_ids: list[str]) -> dict:
    """Master of the snapshot has no users and GHL refuses to publish "user" without one → "all" (every user of the
    account; a new account has the owner only)."""
    who = {"userType": "user", "selectedUser": user_ids} if user_ids else {"userType": "all"}
    return {"name": "Text Owner - Inbound SMS", "type": "internal_notification", "attributes": {"type": "sms", "sms": {
        "body": BODY, **who, "attachments": []}}}


def existing(a: Agency, loc: str, name: str) -> dict | None:
    return next((w for w in a.workflows(loc) if w.get("name") == name), None)


def verify(a: Agency, loc: str, wid: str, want_status: str) -> str:
    time.sleep(6)
    w = a.workflow(loc, wid)
    tr = a.triggers(loc, wid)
    steps = w["workflowData"]["templates"]
    ok = w["status"] == want_status and w.get("allowMultiple") and len(tr) == 1 and tr[0]["type"] == "customer_reply" \
        and len(tr[0].get("conditions") or []) == len(conditions(False)) and steps and steps[0]["type"] == "internal_notification"
    return f"{'ok' if ok else 'DIFERENTE'} (status {w['status']}, re-entry {w.get('allowMultiple')}, gatilho ativo " \
           f"{[t.get('active') for t in tr]}, passo {[s['name'] for s in steps]})"


def run(args) -> int:
    load_dotenv()
    a = Agency()
    locs = select(a.locations(), args.only, args.all, False)
    if args.all:
        inactive = json.loads((ROOT / "config" / "inactive_accounts.json").read_text())["accounts"]  # Frank 13/11
        locs = [l for l in locs if (l.get("name") or "").strip().lower() not in NOT_CLIENT and l["id"] not in inactive]
    bad = 0
    for l in locs:
        loc, nm = l["id"], l.get("name", "").strip()
        if args.cmd in ("testprep", "testcheck"):
            bad |= test(a, loc, nm, args)
            continue
        have = existing(a, loc, NAME)
        if have and args.template and args.cmd == "apply" and have.get("status") != "published":
            wid = have.get("id") or have.get("_id")
            live = a.workflow(loc, wid)
            a.call("PUT", BACKEND, f"/workflow/{loc}/{wid}", body={"name": NAME, "version": live.get("version", 2),
                   "status": "published", "allowMultiple": True, "workflowData": {"templates": [
                       {**live["workflowData"]["templates"][0], "attributes": alert_step([])["attributes"]}]}})
            print(f"~ {nm}: {NAME} → todos os usuários, publicado; releitura {verify(a, loc, wid, 'published')}")
            continue
        if have:
            print(f"= {nm}: já tem \"{NAME}\" ({have.get('status')})")
            continue
        if args.template:
            user, why = None, "master do snapshot: sem usuários → aviso para todos os usuários da conta"
        else:
            user, why = owner(a, loc)
            if not user:
                print(f"! {nm}: {why} → pulei")
                bad = 1
                continue
        print(f"+ {nm}: {NAME} → {user['name'] + ' ' + user['phone'] if user else '(sem usuário)'} [{why}]")
        if args.cmd == "apply":
            d = ROOT / "backup" / slugify(nm)
            d.mkdir(parents=True, exist_ok=True)
            (d / f"sms-alert-before-{stamp()}.json").write_text(json.dumps(
                [{"id": w.get("id"), "name": w.get("name"), "status": w.get("status")} for w in a.workflows(loc)], indent=1))
            status = "draft" if args.template and args.draft_template else "published"
            wid = create(a, loc, NAME, alert_step([user["id"]] if user else []), status)
            print(f"   criado {wid}; releitura {verify(a, loc, wid, status)}")
    return bad


def test(a: Agency, loc: str, nm: str, args) -> int:
    if not args.phone:
        sys.exit("--phone obrigatório")
    found = a.call("GET", SERVICES, "/contacts/", params={"locationId": loc, "query": args.phone[-10:]}).get("contacts", [])
    if args.cmd == "testprep":
        for t in ("zz test", TEST_MARK):
            try:
                a.call("POST", BACKEND, f"/workflow/{loc}/tags/create", body={"tag": t})
            except Exception:
                pass
        if found:
            cid = found[0]["id"]
        else:
            cid = a.call("POST", SERVICES, "/contacts/upsert", body={
                "locationId": loc, "firstName": "ZZ TEST", "lastName": f"inbound {stamp()}", "phone": args.phone})["contact"]["id"]
        a.call("POST", SERVICES, f"/contacts/{cid}/tags", body={"tags": ["zz test"]})
        if not existing(a, loc, TEST_NAME):
            wid = create(a, loc, TEST_NAME, {"name": "Stand-in alert", "type": "add_contact_tag",
                                            "attributes": {"type": "add_contact_tag", "tags": [TEST_MARK]}}, "published", test=True)
            print(f"   {TEST_NAME} {wid} publicado; contato {cid} com tag zz test")
        return 0
    ok = bool(found) and TEST_MARK in (a.call("GET", SERVICES, f"/contacts/{found[0]['id']}")["contact"].get("tags") or [])
    print(f"{'✓' if ok else '✗'} {nm}: texto do {args.phone} {'disparou' if ok else 'NÃO disparou'} o gatilho")
    if ok or args.cleanup:
        for c in found:
            if (c.get("firstName") or "").startswith("ZZ TEST"):  # created by testprep → delete (conversation goes too)
                a.call("DELETE", SERVICES, f"/contacts/{c['id']}")
            else:  # Pedro's contact already existed: only take the test tags off
                a.call("DELETE", SERVICES, f"/contacts/{c['id']}/tags", body={"tags": ["zz test", TEST_MARK]})
        w = existing(a, loc, TEST_NAME)
        if w:
            a.call("DELETE", BACKEND, f"/workflow/{loc}/{w.get('id') or w.get('_id')}")
        print("   contato de teste (ou só as tags) e ZZ TEST apagados")
    return 0 if ok else 1


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("cmd", choices=["plan", "apply", "testprep", "testcheck"])
    p.add_argument("--only", nargs="*")
    p.add_argument("--all", action="store_true")
    p.add_argument("--template", action="store_true", help="snapshot master: no owner user")
    p.add_argument("--draft-template", action="store_true")
    p.add_argument("--phone")
    p.add_argument("--cleanup", action="store_true", help="testcheck: delete the test even if it did not fire")
    return run(p.parse_args())


if __name__ == "__main__":
    sys.exit(main())
