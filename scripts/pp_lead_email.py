#!/usr/bin/env python3
"""Lead forms also e-mail the client (Orange Tree: Val, 14/10; BluVantage: Vanessa, 15/10).

    ./.venv/bin/python scripts/pp_lead_email.py test --to pedro@poolprofits.com   # Test Snapshot
    ./.venv/bin/python scripts/pp_lead_email.py test --to pedro@poolprofits.com --loc nptD4SfaNCSR95LjTJsb  # sent by Orange Tree
    ./.venv/bin/python scripts/pp_lead_email.py test --to pedro@poolprofits.com --loc KLFYmoVapqQgX3T0AnLn --only BluVantage
    ./.venv/bin/python scripts/pp_lead_email.py plan --only "Orange Tree"
    ./.venv/bin/python scripts/pp_lead_email.py apply --only "Orange Tree"

Found live: no form and no workflow sent e-mail (forms: emailNotifications false; workflows: SMS only);
the Facebook form's SMS went to the contact owner, which these contacts never have; and the client's
phone (623) 974-5300 answered "Stop" to an alert on 09/03, so no internal SMS reaches it since.
This adds an internal e-mail notification (custom e-mail, same format as Passion's live ones) right
after the existing alert in each lead workflow, and points the Facebook form SMS to the account owner.
Backup of each workflow in backup/<slug>/ first.

BluVantage: Vanessa found Chris Kelleher's form only in the contact's Activity log and asked for the
details by e-mail. One e-mail per address (custom e-mail) with every field of the form (service and
message included), after the NEW LEAD text of the website and Google Ads forms; and the forms' own
"show submission in the Conversations feed" option turned on, so the answers sit in the conversation.

Passion (Frank/Pedro, 17/10): only the Google Ads path (calls/texts to 629-302-2044, Ads landing form)
e-mailed passionpoolcare@gmail.com. Website quote forms → e-mail after the SMS to John, with the pool
answers; and two new workflows for the Website & GBP line (629-247-6255), calls and texts: if/else
skips spam / DND / existing customer, then the e-mail. Re-entry off = one e-mail per new number (the
line also gets customers, and none are tagged in GHL). Same trigger shape as the Ads ones.
"""
from __future__ import annotations

import argparse
import json
import time
import uuid

from _common import ROOT, load_dotenv, location_dirs
from pp_audit import load
from pp_lead_alerts import guard_nodes
from pp_won_stage import DROP

from cli_anything.gohighlevel.utils.agency import BACKEND, SERVICES, Agency

P = '<p style="margin:0px;font-family:verdana,geneva,sans-serif;font-size:16px;">{}</p>'
DETAILS = ["Name: {{contact.name}}", "Phone: {{contact.phone}}", "Email: {{contact.email}}",
           "Address: {{contact.address1}} {{contact.city}} {{contact.postal_code}}", "Source: {{contact.source}}"]
BV_DETAILS = ["Name: {{contact.name}}", "Phone: {{contact.phone}}", "Email: {{contact.email}}",
              "Address: {{contact.address1}}, {{contact.city}}, {{contact.state}} {{contact.postal_code}}"]
ACCOUNTS = {
    "Orange Tree": {
        "to": ["orangetreepools@gmail.com", "vanessa.orangetreepools@gmail.com"],  # Vanessa reads her own (16/10)
        "sms_to": ["0ijzATNg4PxprYIhQnhz"],  # Stephen Sherman (both users share the same phone)
        "reorder": True,
        "flows": {  # workflow → (subject, headline, lines)
            "Facebook Form - New Lead": ("🚨 New Facebook lead: {{contact.name}}", "🚨 NEW LEAD FROM FACEBOOK 🚨", DETAILS),
            "Website Form Fill To Pipeline": ("🚨 New website lead: {{contact.name}}", "🚨 NEW LEAD FROM YOUR WEBSITE 🚨",
                                              DETAILS),
            "Incoming Chat To Pipeline": ("💬 New web chat: {{contact.name}}", "💬 NEW WEB CHAT REQUEST 💬",
                                          DETAILS + ["Message: {{message.body}}"]),
            # customer texts (photos included as links): the SMS forward can't carry pictures and the
            # office cell has been on STOP since 09/03, so the e-mail is what reaches them (Vanessa, 16/10)
            "SMS Reply": ("💬 {{contact.name}} texted you", "💬 CUSTOMER TEXT 💬",
                          ["From: {{contact.name}} {{contact.phone}}", "Message: {{message.body}}",
                           "Photos / files: {{message.attachments}}"]),
        },
    },
    "BluVantage": {
        "to": ["vanessa@bluvantagepools.com", "paul@bluvantagepools.com"],
        "flows": {
            "Website Form Fill To Pipeline": (
                "🚨 New website lead: {{contact.name}}", "🚨 NEW LEAD FROM THE WEBSITE FORM 🚨",
                BV_DETAILS + ["Service: {{contact.which_services_are_you_interested_in}}",
                              "Message: {{contact.multi_line_409w}}", "Form: {{contact.source}}"]),
            "AdWords Form - New Lead": (
                "🚨 New Google Ads lead: {{contact.name}}", "🚨 NEW LEAD FROM GOOGLE ADS 🚨",
                BV_DETAILS + ["Form: Google Ads landing page (go.bluvantagepools.com)"]),
        },
        "feed_forms": ["Footer Form - BluVantage", "FORM - GOOGLE ADS"],
    },
    "Southern": {  # Val, 16/10: e-mail on Google Ads forms and calls (Brett is the only user)
        "to": ["brett@southernpoolandoutdoors.com"],
        "flows": {  # a 4th item = insert after the first step of that type (default: the SMS alert)
            "AdWords Form - New Lead": ("🚨 New Google Ads lead: {{contact.name}}", "🚨 NEW LEAD FROM GOOGLE ADS 🚨",
                                        BV_DETAILS + ["Form: GOOGLE ADS - FORM (service.southernpoolandoutdoors.com)"]),
            "AdWords Call In - New Lead": ("📞 New Google Ads call: {{contact.phone}}", "📞 NEW CALL FROM GOOGLE ADS 📞",
                                           ["Caller: {{contact.name}}", "Phone: {{contact.phone}}",
                                            "Line: Google Ads (972-632-3259)"], "create_opportunity"),
            "Website Form Fill To Pipeline": ("🚨 New website lead: {{contact.name}}", "🚨 NEW LEAD FROM A WEBSITE FORM 🚨",
                                              BV_DETAILS + ["Form: {{contact.source}}"]),
        },
        "feed_forms": ["GOOGLE ADS - FORM"],
    },
}
PASSION_LINE = "+16292476255"  # "Website & GBP"


def line_trigger(kind: str, number: str) -> dict:
    """Same shape as Passion's live AdWords Call In / AdWords SMS triggers, for another number."""
    first = {"call_status": {"operator": "==", "field": "message.direction", "value": "inbound",
                             "title": "Call Direction", "type": "select"},
             "customer_reply": {"operator": "==", "field": "message.type", "value": 2, "title": "Reply channel",
                                "type": "select"}}[kind]
    return {"type": kind, "name": {"call_status": "Call Details", "customer_reply": "Customer Replied"}[kind],
            "conditions": [first, {"operator": "contains-any", "field": "inbound_number", "value": [number],
                                   "title": "In Phone Number", "type": "multiselect", "id": "inbound-twilio-number"}]}


ACCOUNTS["Passion"] = {
    "to": ["passionpoolcare@gmail.com"],
    "flows": {
        "Website Form Fill To Pipeline": (
            "🚨 New website lead: {{contact.name}}", "🚨 NEW LEAD FROM YOUR WEBSITE 🚨",
            BV_DETAILS + ["Pool: {{contact.pool_type}}", "About the pool: {{contact.pool_details}}",
                          "Form: {{contact.source}}"]),
    },
    "feed_forms": ["PPC - Home Quote", "PPC - Universal Quote"],
    "new_flows": {  # new workflow → (trigger, subject, headline, lines)
        "Website & GBP Call - Lead Email": (
            line_trigger("call_status", PASSION_LINE), "📞 New call: {{contact.phone}}",
            "📞 NEW CALL ON YOUR WEBSITE & GOOGLE LINE 📞",
            ["Caller: {{contact.name}}", "Phone: {{contact.phone}}", "Line: Website & Google (629-247-6255)",
             "The card is in Opportunities → Pool Leads → New Lead."]),
        "Website & GBP SMS - Lead Email": (
            line_trigger("customer_reply", PASSION_LINE), "💬 New text from {{contact.phone}}",
            "💬 NEW TEXT ON YOUR WEBSITE & GOOGLE LINE 💬",
            ["From: {{contact.name}} {{contact.phone}}", "Message: {{message.body}}",
             "Photos / files: {{message.attachments}}", "Line: Website & Google (629-247-6255)"]),
    },
    "folder": "01 Incoming Lead",
    "skip": ["spam", "dnd", "existing customer"],
}
TEST_LOC = "hmzX5j1dPhOQKX2dH4kf"  # Test Snapshot


def email_step(subject: str, headline: str, lines: list[str], to: str) -> dict:
    html = P.format(f"<strong>{headline}</strong>") + "<br/>" + "".join(P.format(x) for x in lines)
    return {"id": str(uuid.uuid4()), "name": "New Lead Email", "type": "internal_notification",
            "attributes": {"type": "email", "email": {"isCloned": False, "html": html, "to": to,
                                                       "userType": "custom_email", "subject": subject,
                                                       "attachments": []}}}


def insert_after(templates: list[dict], after_id: str, step: dict) -> list[dict]:
    """Step goes between after_id and its next, in the same chain (root or inside a branch)."""
    out = json.loads(json.dumps(templates))
    by_id = {s["id"]: s for s in out}
    prev = by_id[after_id]
    if isinstance(prev.get("next"), list):
        raise SystemExit("cannot insert after a condition node")
    step = dict(step, parentKey=prev["id"], order=prev["order"] + 1)
    if prev.get("parent"):
        step["parent"] = prev["parent"]
    if prev.get("next"):
        step["next"] = prev["next"]
        by_id[prev["next"]]["parentKey"] = step["id"]
    prev["next"] = step["id"]
    chain, nxt = [], step.get("next")
    while isinstance(nxt, str):  # shift the orders of what follows in this chain
        chain.append(by_id[nxt])
        nxt = by_id[nxt].get("next")
    if any(isinstance(s.get("next"), list) for s in chain):
        raise SystemExit("a condition follows the insertion point — not shifting orders blindly")
    for s in chain:
        s["order"] += 1
    return out + [step]


def alert_of(templates: list[dict]) -> dict:
    return next(s for s in templates if s["type"] == "internal_notification" and s["attributes"].get("type") == "sms")


def put(a: Agency, loc: str, wid: str, live: dict, templates: list[dict]) -> None:
    a.call("PUT", BACKEND, f"/workflow/{loc}/{wid}", body={
        "name": live["name"], "version": live.get("version", 1), "status": live["status"],
        "parentId": live.get("parentId"), "allowMultiple": live.get("allowMultiple", False),
        "workflowData": {"templates": templates}})


def apply(a: Agency, account: str, do: bool) -> int:
    cfg = ACCOUNTS[account]
    d = location_dirs([account])[0]
    loc = load(d / "location.json", {})["id"]
    flows = {w["name"]: w["id"] for w in a.workflows(loc)}
    stamp = time.strftime("%Y%m%d-%H%M%S")
    bdir = ROOT / "backup" / d.name
    bdir.mkdir(parents=True, exist_ok=True)
    bad = 0
    print(f"== {d.name}")
    for name, (subject, headline, lines, *anchor) in cfg["flows"].items():
        wid = flows[name]
        live = a.workflow(loc, wid)
        tpl = live["workflowData"]["templates"]
        have = {s["attributes"]["email"].get("to") for s in tpl
                if s["type"] == "internal_notification" and s["attributes"].get("type") == "email"}
        missing = [to for to in cfg["to"] if to not in have]
        if not missing:
            print(f"   {name}: já manda e-mail para {cfg['to']}")
            continue
        alert = next(s for s in tpl if s["type"] == anchor[0]) if anchor else alert_of(tpl)
        new, after_id = tpl, alert["id"]
        for to in missing:
            step = email_step(subject, headline, lines, to)
            step["name"] = f"New Lead Email ({to.split('@')[0]})" if len(cfg["to"]) > 1 else "New Lead Email"
            new = insert_after(new, after_id, step)
            after_id = step["id"]
        fix_sms = cfg.get("sms_to") and alert["type"] == "internal_notification" and \
            alert["attributes"]["sms"].get("userType") == "assign"
        if fix_sms:
            sms = next(s for s in new if s["id"] == alert["id"])
            sms["attributes"]["sms"].pop("assignedOwners", None)
            sms["attributes"]["sms"].update(userType="user", selectedUser=cfg["sms_to"])
            sms.pop("incompleteData", None)
        print(f"   {name} [{live['status']}]: + e-mail para {missing} depois de '{alert['name']}'"
              + (" · SMS: dono do contato → usuário" if fix_sms else ""))
        if not do:
            continue
        trs = [t for t in a.triggers(loc, wid) if not t.get("deleted")]
        (bdir / f"workflow-{wid}-{stamp}.json").write_text(json.dumps({"workflow": live, "triggers": trs}))
        put(a, loc, wid, live, new)
        time.sleep(4)
        after = a.workflow(loc, wid)
        t2 = after["workflowData"]["templates"]
        got = {s["attributes"]["email"].get("to") for s in t2
               if s["type"] == "internal_notification" and s["attributes"].get("type") == "email"}
        ids = {s["id"] for s in t2}
        ok = set(cfg["to"]) <= got and after["status"] == live["status"] and len(t2) == len(tpl) + len(missing) \
            and all(r in ids for s in t2 for r in [s.get("parentKey"), s.get("parent")] if r)
        bad += not ok
        print(f"      {'✓' if ok else '✗ VERIFICAR'} {after['status']} · {len(t2)} passos")
    for name in cfg["flows"] if cfg.get("reorder") else []:  # notifications after the card (Val, 14/10)
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
    forms = {f["name"]: f.get("_id") or f.get("id") for f in a.forms(loc)} if cfg.get("feed_forms") else {}
    for fname in cfg.get("feed_forms", []):  # the form's own "show submission in Conversations" option
        fid = forms[fname]
        f = a.call("GET", BACKEND, f"/forms/{fid}")
        f = f.get("form", f)
        if f["formData"]["form"].get("showSubmissionInConversationsFeed"):
            print(f"   form {fname}: já mostra a submissão na conversa")
            continue
        print(f"   form {fname}: mostrar a submissão na conversa")
        if not do:
            continue
        (bdir / f"form-{fid}-{stamp}.json").write_text(json.dumps(f))
        fd = json.loads(json.dumps(f["formData"]))
        fd["form"]["showSubmissionInConversationsFeed"] = True
        a.call("POST", BACKEND, f"/forms/{fid}", body={"name": f["name"], "formData": fd})
        time.sleep(3)
        g = a.call("GET", BACKEND, f"/forms/{fid}")
        g = g.get("form", g)
        ok = g["formData"]["form"].get("showSubmissionInConversationsFeed") is True and \
            len(g["formData"]["form"]["fields"]) == len(f["formData"]["form"]["fields"])
        bad += not ok
        print(f"      {'✓' if ok else '✗ VERIFICAR'}")
    return bad + create_flows(a, cfg, loc, flows, do)


def guarded_emails(cfg: dict, subject: str, headline: str, lines: list[str]) -> list[dict]:
    """if/else (none of cfg["skip"]) → one e-mail per address in the "Lead" branch."""
    cond, yes, none = guard_nodes(None, None, 0, skip=cfg["skip"])
    out, prev = [cond, yes, none], yes
    for i, to in enumerate(cfg["to"]):
        e = email_step(subject, headline, lines, to)
        e.update(order=i, parent=yes["id"], parentKey=prev["id"])
        prev["next"] = e["id"]
        out.append(e)
        prev = e
    return out


def create_flows(a: Agency, cfg: dict, loc: str, flows: dict, do: bool) -> int:
    """New published workflows (trigger → guard → e-mails); existing ones are left alone."""
    bad = 0
    folders = {v: k for k, v in a.folders(loc).items()} if cfg.get("new_flows") else {}
    for name, (trigger, subject, headline, lines) in cfg.get("new_flows", {}).items():
        if name in flows:
            print(f"   {name}: já existe")
            continue
        tpl = guarded_emails(cfg, subject, headline, lines)
        print(f"   + {name} ({trigger['type']} {trigger['conditions'][-1]['value']}): pula {cfg['skip']} → "
              f"e-mail para {cfg['to']} · 1 vez por contato")
        if not do:
            continue
        parent = folders.get(cfg.get("folder"))
        res = a.call("POST", BACKEND, f"/workflow/{loc}", body={"name": name, "parentId": parent, "status": "draft"})
        wid = res.get("id") or res.get("_id")
        body = {"name": name, "version": 1, "status": "draft", "parentId": parent, "allowMultiple": False,
                "workflowData": {"templates": tpl}}
        a.call("PUT", BACKEND, f"/workflow/{loc}/{wid}", body=body)
        trig = {**trigger, "masterType": "highlevel", "schedule_config": {}, "workflowId": wid, "workflow_id": wid,
                "location_id": loc, "actions": [{"workflow_id": wid, "type": "add_to_workflow"}],
                "targetActionId": tpl[0]["id"]}
        t = a.call("POST", BACKEND, f"/workflow/{loc}/trigger", body=trig)
        a.call("PUT", BACKEND, f"/workflow/{loc}/trigger/{t['id']}", body={**trig, "id": t["id"]})
        live = a.workflow(loc, wid)
        a.call("PUT", BACKEND, f"/workflow/{loc}/{wid}", body={**body, "version": live.get("version", 1),
                                                               "status": "published"})
        time.sleep(4)
        got = a.workflow(loc, wid)
        t2 = got["workflowData"]["templates"]
        ids = {s["id"] for s in t2}
        refs = [r for s in t2 for r in ([s.get("next")] if isinstance(s.get("next"), str) else s.get("next") or [])]
        refs += [s[k] for s in t2 for k in ("parent", "parentKey") if s.get(k)]
        trs = [x for x in a.triggers(loc, wid) if not x.get("deleted")]
        ok = got["status"] == "published" and len(t2) == len(tpl) and all(r in ids for r in refs) \
            and len(trs) == 1 and trs[0]["conditions"][-1]["value"] == trigger["conditions"][-1]["value"]
        bad += not ok
        print(f"      {'✓' if ok else '✗ VERIFICAR'} {got['status']} · {len(t2)} passos · gatilho {trs[0]['type'] if trs else '—'}")
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


TEST_FIELDS = {"BluVantage": [{"id": "9RVlQh3HgUqdwXG4OBEh", "field_value": "Pool Inspection"},
                              {"id": "vrNW6tfIBG082HVZ7nPe", "field_value": "TEST message from the website form."}]}


def run_test(a: Agency, to: str, loc: str = TEST_LOC, account: str = "Orange Tree", flow: str | None = None) -> int:
    """Throwaway workflow (Test Snapshot by default): tag → the account's lead e-mail (first, or `flow`) → `to`."""
    go = "lead email test go"
    try:
        a.call("POST", BACKEND, f"/workflow/{loc}/tags/create", body={"tag": go})
    except Exception:
        pass
    res = a.call("POST", BACKEND, f"/workflow/{loc}", body={"name": "TMP lead email test", "status": "draft"})
    wid = res.get("id") or res.get("_id")
    tag = {"id": str(uuid.uuid4()), "order": 0, "name": "Add Tag", "type": "add_contact_tag",
           "attributes": {"tags": ["lead email test done"], "type": "add_contact_tag"}}
    every = {**ACCOUNTS[account]["flows"], **{k: v[1:] for k, v in ACCOUNTS[account].get("new_flows", {}).items()}}
    tpl = insert_after([tag], tag["id"], email_step(*(every[flow] if flow else next(iter(every.values())))[:3], to))
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
        "address1": "123 Test St", "city": "Phoenix", "state": "AZ", "postalCode": "85001", "source": "TEST form",
        "customFields": TEST_FIELDS.get(account, [])})
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
    parser.add_argument("--only", choices=list(ACCOUNTS), help="plan/apply: account")
    parser.add_argument("--flow", help="test: which of the account's e-mails (workflow name)")
    args = parser.parse_args()
    load_dotenv()
    a = Agency()
    if args.mode == "test":
        if not args.to:
            parser.error("--to is required for test")
        return run_test(a, args.to, args.loc, args.only or "Orange Tree", args.flow)
    if not args.only:
        parser.error("--only is required for plan/apply")
    return 1 if apply(a, args.only, args.mode == "apply") else 0


if __name__ == "__main__":
    raise SystemExit(main())
