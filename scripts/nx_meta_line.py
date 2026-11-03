#!/usr/bin/env python3
"""NorTex Pools: the Meta Ads line (469) 535-7838 ("Facebook", bought by Val 03/11, only on the Premium Weekly Pool Cleaning
page = Meta Ads). Same pattern as the Google Ads line (nx_ads_forms.py / nx_ads_line.py) and the ad lines of The Pool
Shack / YardSpring (ps_ads_lines.py / ys_ads_line.py).

    ./.venv/bin/python scripts/nx_meta_line.py plan
    ./.venv/bin/python scripts/nx_meta_line.py test --to pedro@poolprofits.com
    ./.venv/bin/python scripts/nx_meta_line.py apply

Routing: every NorTex line rings through "IVR SPAM Detection" ("press 1" → rings Fareed's user, no answer → voicemail +
tag `missed call`; no forwarding number on any line). apply adds this number to that IVR trigger (backup first), so it
rings exactly like the main line and the Google Ads line. The account's generic "Answered / Missed Incoming Call To
Pipeline" have no number filter (tags `new lead` / `inbound call` [/ `missed call` → the account's missed-call text],
card "Inbound Call", task) and keep running for this line.
On top of that, one workflow per channel (folder of "Meta Ads LP - Weekly"):
  "Meta Ads Call - Weekly"  Call Status, inbound, In Phone Number = the line.
  "Meta Ads SMS - Weekly"   Customer Replied, SMS, In phone number = the line.
  Spam / DND          → nothing.
  In the last 24 h    → nothing (every call / text fires the trigger: one alert per lead per day).
  Current customer    → tags `meta ads - weekly` + `meta ads` + `meta ads - call|sms` + 24 h tag, Service "Weekly Pool
                        Cleaning" (as the Weekly LP flow), text + email to Fareed marked existing customer; no card.
  New lead            → same tags + `new lead`, Service, owner Fareed (if none), text + email + task to Fareed
                        ("NEW META ADS CALL|TEXT - PREMIUM WEEKLY POOL CLEANING"), card in Pool Leads → New Lead (source
                        "Meta Ads Call|SMS - Weekly"). No Google conversion. Calls: the card comes 1 minute after the
                        alerts and the workflow does not allow a second card, so it updates the "Inbound Call" card the
                        generic call flow opens for the same call instead of adding a duplicate.
Every branch with tags: wait 1 day → remove the 24 h tag.
test: temporary copies (alerts by email to --to only, no text to Fareed), API-enrolled contacts for every branch + a
repeat (+ for calls a contact that already has an "Inbound Call" card); checks tags/Service/cards/tasks, deletes all.
"""
from __future__ import annotations

import argparse
import json
import sys
import time

from _common import ROOT, load_dotenv
from ps_ads_forms import P, cond, if_else, outline
from pp_source_tags import refs_ok
from pp_won_stage import DROP

from cli_anything.gohighlevel.utils.agency import BACKEND, SERVICES, Agency

LOC = "k6nDPHktS2PySJoJuwpG"
LINE, SHOW = "+14695357838", "(469) 535-7838"
FAREED, FAREED_EMAIL = "L9rAwvOd8DjsUnw4m5tX", "f.alayoub@nortexpools.com"  # Fareed (only user)
PIPELINE, NEW_LEAD = "6cVcvhrosWlJHPrWLMx5", "cc31ee8a-8a37-4c69-8d28-a771df8b1f41"
SERVICE_FIELD, WEEKLY_SERVICE = "j2bvM8wUG7YDTQe7ARyS", "Weekly Pool Cleaning"  # "Service" (dropdown), as the Weekly LP
IVR, FOLDER_OF = "IVR SPAM Detection", "Meta Ads LP - Weekly"
SPAM, CUSTOMER = ["spam", "dnd"], ["existing customer", "recurring customer", "current customer", "won"]
BASE = ["meta ads - weekly", "meta ads"]
KIND = {"call": {"flow": "Meta Ads Call - Weekly", "tag": "meta ads - call", "recent": "meta ads call 24h",
                 "head": "📞 NEW META ADS CALL - PREMIUM WEEKLY POOL CLEANING", "what": "call", "extra": [],
                 "subject": "📞 New Meta Ads call (Premium Weekly Pool Cleaning)",
                 "todo": "If you didn't talk to them, call back.", "task": "Call back Meta Ads lead"},
        "sms": {"flow": "Meta Ads SMS - Weekly", "tag": "meta ads - sms", "recent": "meta ads sms 24h",
                "head": "📱 NEW META ADS TEXT - PREMIUM WEEKLY POOL CLEANING", "what": "text",
                "extra": [("Message", "{{message.body}}")],
                "subject": "📱 New Meta Ads text (Premium Weekly Pool Cleaning)",
                "todo": "Reply from the CRM so it goes out from the Meta Ads number.", "task": "Reply to Meta Ads text lead"}}
BDIR = ROOT / "backup" / "nortex-pools"


def build(kind: str, test_to: str | None = None) -> list[dict]:
    k = KIND[kind]
    rows = [("Name", "{{contact.name}}"), ("Phone", "{{contact.phone}}"), *k["extra"], ("Service", WEEKLY_SERVICE),
            ("Line", f"Meta Ads – Premium Weekly Pool Cleaning page {SHOW}")]

    def alerts(customer: bool) -> list:
        head = k["head"] + (" (EXISTING CUSTOMER)" if customer else "")
        email = ("internal_notification", "Email Fareed", {"type": "email", "email": {
            "userType": "custom_email", "to": test_to or FAREED_EMAIL,
            "subject": ("[TEST] " if test_to else "") + k["subject"] + ": {{contact.name}} {{contact.phone}}",
            "html": P.format(head + ":") + "".join(P.format(f"<b>{a}:</b> {b}") for a, b in rows) + P.format(k["todo"])}})
        if test_to:
            return [email]
        sms = ("internal_notification", "Text Fareed", {"type": "sms", "sms": {
            "body": f"{head}\n\n" + "\n".join(f"{a}: {b}" for a, b in rows) + f"\n\n{k['todo']}",
            "userType": "user", "selectedUser": [FAREED], "attachments": []}})
        return [sms, email]

    def wait(value: int, unit: str, name: str) -> tuple:
        return ("wait", name, {"type": "time", "startAfter": {"type": unit, "value": value, "when": "after"}, "name": name,
                               "cat": "", "isHybridAction": True, "hybridActionType": "wait", "convertToMultipath": False,
                               "transitions": []})

    service = ("update_contact_field", "Set Service", {"type": "update_contact_field", "actionType": "update_field_data",
               "fields": [{"field": SERVICE_FIELD, "value": WEEKLY_SERVICE, "title": "Service", "type": "select", "date": ""}]})
    release = [wait(1, "days", "Wait 1 day"),
               ("remove_contact_tag", "Remove 24 h tag", {"type": "remove_contact_tag", "tags": [k["recent"]]})]
    owner = ("assign_user", "Assign to Fareed", {"type": "assign_user", "only_unassigned_contact": True, "traffic_split": "equally",
                                              "user_list": [FAREED], "traffic_weightage": {FAREED: 1}, "total_index": 1,
                                              "traffic_index": [{"id": FAREED, "indexes": [1]}]})
    card = ("create_opportunity", "Card in New Lead", {
        "fields": [], "type": "create_opportunity", "pipeline_id": PIPELINE, "pipeline_stage_id": NEW_LEAD,
        "opportunity_name": "{{contact.name}}", "opportunity_source": k["flow"], "monetary_value": "", "opportunity_status": "open"})
    task = ("task-notification", f"Task: {k['task'].lower()}", {
        "type": "task_notification", "title": f"{k['task']}: {{{{contact.name}}}} {{{{contact.phone}}}}",
        "body": f"<p style=\"margin:0px\">New Meta Ads {k['what']} (Premium Weekly Pool Cleaning page, {SHOW}).</p>"
                f"<p style=\"margin:0px\">{k['todo']} Then move the card down the pipeline.</p>",
        "assignedTo": FAREED, "dueDate": {"duration": 0, "unit": "days"}})
    tags = ("add_contact_tag", "Add Tags", {"type": "add_contact_tag", "tags": [*BASE, k["tag"], "new lead", k["recent"]]})
    if kind == "call":  # after the generic call flow's "Inbound Call" card, which this one then updates (no duplicate)
        lead = [tags, service, owner, *alerts(False), task, wait(1, "minutes", "Wait 1 minute"), card, *release]
    else:
        lead = [tags, service, owner, card, *alerts(False), task, *release]
    customer = [("add_contact_tag", "Add Tags", {"type": "add_contact_tag", "tags": [*BASE, k["tag"], k["recent"]]}),
                service, *alerts(True), *release]
    nodes, _ = if_else(f"Route the {k['what']}", [
        ("Spam / DND", [cond("tags", "index-of-true", [t]) for t in SPAM], []),
        ("In the last 24 h", [cond("tags", "index-of-true", [k["recent"]])], []),
        ("Current customer", [cond("tags", "index-of-true", [t]) for t in CUSTOMER], customer),
    ], "New lead", lead)
    return nodes


def trigger(kind: str, wid: str, first: str) -> dict:
    if kind == "call":
        name, typ, conds = "Call Status", "call_status", [
            {"field": "message.direction", "operator": "==", "value": "inbound", "title": "Call Direction", "type": "select"},
            {"field": "inbound_number", "operator": "contains-any", "id": "inbound-twilio-number", "value": [LINE],
             "title": "In Phone Number", "type": "multiselect"}]
    else:
        name, typ, conds = "Customer Replied", "customer_reply", [
            {"operator": "==", "field": "message.type", "value": 2, "title": "Reply channel", "type": "select"},
            {"operator": "contains-any", "field": "inbound_number", "value": [LINE], "title": "In phone number",
             "type": "multiselect", "id": "inbound-twilio-number"}]
    return {"type": typ, "name": name, "masterType": "highlevel", "schedule_config": {}, "conditions": conds,
            "workflowId": wid, "workflow_id": wid, "location_id": LOC,
            "actions": [{"workflow_id": wid, "type": "add_to_workflow"}], "targetActionId": first}


def create(a: Agency, name: str, parent: str | None, tpl: list[dict]) -> str:
    res = a.call("POST", BACKEND, f"/workflow/{LOC}", body={"name": name, "parentId": parent, "status": "draft"})
    wid = res.get("id") or res.get("_id")
    a.call("PUT", BACKEND, f"/workflow/{LOC}/{wid}", body={"name": name, "version": 1, "status": "draft", "parentId": parent,
                                                         "allowMultiple": True, "allowMultipleOpportunity": False,
                                                         "workflowData": {"templates": tpl}})
    return wid


def set_status(a: Agency, wid: str, status: str) -> dict:
    live = a.workflow(LOC, wid)
    a.call("PUT", BACKEND, f"/workflow/{LOC}/{wid}", body={"name": live["name"], "version": live.get("version", 1), "status": status,
           "parentId": live.get("parentId"), "workflowData": {"templates": live["workflowData"]["templates"]}})
    time.sleep(3)
    return a.workflow(LOC, wid)


def state(a: Agency, cid: str) -> tuple[dict, list, list]:
    c = a.call("GET", SERVICES, f"/contacts/{cid}")["contact"]
    opps = a.call("GET", SERVICES, "/opportunities/search", params={"location_id": LOC, "contact_id": cid}).get("opportunities", [])
    tasks = a.call("GET", SERVICES, f"/contacts/{cid}/tasks").get("tasks", [])
    return c, opps, tasks


def service_of(c: dict) -> str | None:
    return next((f.get("value") for f in c.get("customFields") or [] if f.get("id") == SERVICE_FIELD), None)


def test(a: Agency, folder: str | None, to: str) -> int:
    bad = 0
    for kind, k in KIND.items():
        wid = create(a, f"ZZ TEST nx meta {kind}", folder, build(kind, to))
        set_status(a, wid, "published")
        ts, made = int(time.time()), {}
        cases = [("new", []), ("customer", ["existing customer"]), ("spam", ["spam"])]
        if kind == "call":
            cases.insert(1, ("new+card", []))
        try:
            for case, tg in cases:
                made[case] = a.call("POST", SERVICES, "/contacts/", body={
                    "locationId": LOC, "firstName": "ZZ Test", "lastName": f"meta {kind} {case}", "tags": tg,
                    "email": to.replace("@", f"+nx-meta-{kind}-{case.replace('+', '-')}-{ts}@")})["contact"]["id"]
            if "new+card" in made:  # what "Answered Incoming Call To Pipeline" opens for the same call
                a.call("POST", SERVICES, "/opportunities/", body={
                    "locationId": LOC, "pipelineId": PIPELINE, "pipelineStageId": NEW_LEAD, "contactId": made["new+card"],
                    "name": "ZZ Test meta call new+card", "status": "open", "source": "Inbound Call"})
            time.sleep(3)
            for cid in made.values():
                a.call("POST", SERVICES, f"/contacts/{cid}/workflow/{wid}", body={})
            time.sleep(30)
            a.call("POST", SERVICES, f"/contacts/{made['new']}/workflow/{wid}", body={})  # a second call / text
            full = {*BASE, k["tag"], "new lead", k["recent"]}
            want = {"new": (full, 1, 1, WEEKLY_SERVICE), "new+card": (full, 1, 1, WEEKLY_SERVICE),
                    "customer": ({*BASE, k["tag"], k["recent"]}, 0, 0, WEEKLY_SERVICE), "spam": (set(), 0, 0, None)}
            deadline = time.time() + (240 if kind == "call" else 60)
            while True:
                time.sleep(20)
                rows = {case: state(a, cid) for case, cid in made.items()}
                oks = {}
                for case, (c, opps, tasks) in rows.items():
                    exp, ncard, ntask, svc = want[case]
                    tg = set(c.get("tags", []))
                    oks[case] = exp <= tg and len(opps) == ncard and len(tasks) == ntask and service_of(c) == svc and \
                        (case != "spam" or not (tg & {k["tag"], *BASE})) and \
                        all(o.get("source") == k["flow"] for o in opps)
                if all(oks.values()) or time.time() > deadline:
                    break
            for case, (c, opps, tasks) in rows.items():
                bad += not oks[case]
                print(f"   {'✓' if oks[case] else '✗'} {kind} {case}: tags {sorted(c.get('tags', []))} · Service {service_of(c)} · "
                      f"cards {[(o.get('source'), o.get('pipelineStageId') == NEW_LEAD) for o in opps]} · tarefas {len(tasks)}")
        finally:
            for cid in made.values():
                for o in a.call("GET", SERVICES, "/opportunities/search", params={"location_id": LOC, "contact_id": cid}).get("opportunities", []):
                    a.call("DELETE", SERVICES, f"/opportunities/{o['id']}")
                for t in a.call("GET", SERVICES, f"/contacts/{cid}/tasks").get("tasks", []):
                    try:
                        a.call("DELETE", SERVICES, f"/contacts/{cid}/tasks/{t['id']}")
                    except Exception as e:  # noqa: BLE001 — the contact delete takes its tasks too
                        print(f"   (tarefa {t['id']}: {e})")
                a.call("DELETE", SERVICES, f"/contacts/{cid}")
            set_status(a, wid, "draft")
            a.call("DELETE", BACKEND, f"/workflow/{LOC}/{wid}")
    print(f"   limpo. Esperado em {to}: 5 e-mails [TEST] (ligação: novo 1 apesar de 2 entradas, novo+card 1, cliente 1; "
          "SMS: novo 1, cliente 1), nenhum do spam.")
    return 1 if bad else 0


def ivr_line(a: Agency, flows: dict, apply: bool) -> None:
    t = next(x for x in a.triggers(LOC, flows[IVR]) if not x.get("deleted"))
    c = next(x for x in t["conditions"] if x.get("field") == "inbound_number")
    print(f"   {IVR}: gatilho {c['value']} → {SHOW} {'já está' if LINE in c['value'] else 'entra'}")
    if apply and LINE not in c["value"]:
        BDIR.mkdir(parents=True, exist_ok=True)
        (BDIR / f"trigger-{t['id']}-{time.strftime('%Y%m%d-%H%M%S')}.json").write_text(json.dumps(t))
        c["value"] = [*c["value"], LINE]
        body = {k: v for k, v in t.items() if k not in DROP}
        body.update({"workflowId": flows[IVR], "workflow_id": flows[IVR], "location_id": LOC})
        a.call("PUT", BACKEND, f"/workflow/{LOC}/trigger/{t['id']}", body=body)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("mode", choices=["plan", "test", "apply"])
    parser.add_argument("--to")
    args = parser.parse_args()
    if args.mode == "test" and not args.to:
        parser.error("--to is required in test mode")
    load_dotenv()
    a = Agency()
    if not a.location(LOC)["name"].lower().startswith("nortex"):
        sys.exit("sub-conta errada")
    nums = {n["phoneNumber"]: n for n in a.call("GET", SERVICES, f"/phone-system/numbers/location/{LOC}")["numbers"]}
    if LINE not in nums:
        sys.exit(f"{SHOW} não está na conta")
    for p, n in nums.items():
        print(f"   {p} {n.get('friendlyName')!r}: encaminha {n.get('forwardingNumber') or '—'} · "
              f"{(n.get('inboundCallService') or {}).get('type') or 'sem IVR'}")
    flows = {w["name"]: w["id"] for w in a.workflows(LOC)}
    folder = a.workflow(LOC, flows[FOLDER_OF]).get("parentId")
    ivr_line(a, flows, False)
    if args.mode == "plan":
        for kind, k in KIND.items():
            print(f"   {k['flow']}: {'existe' if k['flow'] in flows else 'cria'}")
            print(outline(build(kind)))
        return 0
    for k in KIND.values():
        for t in (*BASE, k["tag"], k["recent"], "new lead"):
            try:
                a.call("POST", BACKEND, f"/workflow/{LOC}/tags/create", body={"tag": t})
            except Exception:  # noqa: BLE001 — already exists
                pass
    if args.mode == "test":
        return test(a, folder, args.to)
    ivr_line(a, flows, True)
    for kind, k in KIND.items():
        if k["flow"] in flows:
            print(f"   {k['flow']}: já existe")
            continue
        tpl = build(kind)
        wid = create(a, k["flow"], folder, tpl)
        t = trigger(kind, wid, tpl[0]["id"])
        r = a.call("POST", BACKEND, f"/workflow/{LOC}/trigger", body=t)
        a.call("PUT", BACKEND, f"/workflow/{LOC}/trigger/{r['id']}", body={**t, "id": r["id"]})
        got = set_status(a, wid, "published")
        trs = [x for x in a.triggers(LOC, wid) if not x.get("deleted")]
        on = [v for x in trs for c in x.get("conditions") or [] if c.get("field") == "inbound_number" for v in c.get("value") or []]
        ok = got["status"] == "published" and refs_ok(got["workflowData"]["templates"]) and len(trs) == 1 and \
            trs[0].get("active") and on == [LINE] and got.get("allowMultiple") and not got.get("allowMultipleOpportunity")
        print(f"   {'✓' if ok else '✗ VERIFICAR'} {k['flow']} [{wid}]: {got['status']} · gatilho {trs[0]['type'] if trs else '—'} {on}")
    time.sleep(5)
    n = next(x for x in a.call("GET", SERVICES, f"/phone-system/numbers/location/{LOC}")["numbers"] if x["phoneNumber"] == LINE)
    t = next(x for x in a.triggers(LOC, flows[IVR]) if not x.get("deleted"))
    print(f"   conferido {SHOW}: inboundCallService {n.get('inboundCallService')} · IVR ativo {t.get('active')} "
          f"{next(c['value'] for c in t['conditions'] if c.get('field') == 'inbound_number')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
