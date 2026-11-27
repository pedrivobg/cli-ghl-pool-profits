#!/usr/bin/env python3
"""The Pool Keepers (BurchTech, live client account): lead cards + text to Nathan for calls and texts (Pedro 27/11: "A").

Nathan 25/11: card + internal alert for new calls, forms and texts; every automated follow-up to the contact stays off.
Skimmer watches "Customer Pipeline > New Lead" only, our cards go to "Pool Leads > New Lead" → no Skimmer customer.
There is no "Skimmer customer" marker in the CRM, so a current customer who calls also gets a card (Nathan drags it to
Lost). From now on the Skimmer notes mark them: a note that only Skimmer writes for customers (CustomerAdded,
"changed to Active", WorkOrder*, InvoicePaid, RouteAssignmentUpdated) → tag "existing customer", and the lead flows skip it.

  Answered Incoming Call To Pipeline / Missed Incoming Call To Pipeline (draft snapshot copies) → guard (no spam /
    spam likely / dnd / existing customer) → tags, card (unchanged) → SMS to Nathan. The old "wait 1 h + task" goes.
  "Inbound SMS - New Lead" (new): Customer Replied, SMS → same guard + no "new lead" (already a card) → tags, card, SMS to
    Nathan. Re-entry off (first text of a contact only).
  "Skimmer Note - Existing Customer" (new): Note Added → copy {{note.body}} to "Skimmer Last Note" → if it has one of
    the markers → tag "existing customer".
Nothing sends anything to the contact. GET + backup before every write.

    GHL_AGENCY=burchtech python3 scripts/pk_lead_flows.py           # plan
    GHL_AGENCY=burchtech python3 scripts/pk_lead_flows.py --apply   # write + publish
    GHL_AGENCY=burchtech python3 scripts/pk_lead_flows.py --test    # ZZ TEST contacts (phone only), deleted after
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import uuid

from _common import ROOT, load_dotenv
from pp_lead_alerts import guard_nodes
from ps_ads_forms import chain, cond, if_else, tags

from cli_anything.gohighlevel.utils.agency import BACKEND, SERVICES, Agency

LOC = "KjLd769fprQ2EaBI9Cro"
NATHAN = "8eLpUBJkMq5GTZy264Cu"
PIPE, STAGE = "WwhrLIXFLCFruCbgHZEW", "7e5d809f-3009-4632-a4cf-66415f760038"
CALLS = {"bc095a96-9358-47c5-841d-2ac28241cb6c": "answered", "4f8f3872-dfa9-48c5-9274-5fa26b9ef7b8": "missed"}
SMS_NAME, NOTE_NAME = "Inbound SMS - New Lead", "Skimmer Note - Existing Customer"
CUSTOMER = "existing customer"
SKIP = ["spam", "spam likely", "dnd", CUSTOMER]
FIELD = "Skimmer Last Note"
MARKERS = ["CustomerAdded", "changed to Active", "WorkOrderFinished", "WorkOrderScheduled", "InvoicePaid",
           "RouteAssignmentUpdated"]
BDIR = ROOT / "backup" / "the-pool-keepers"
STAND_IN = "zz alert ok"
HEAD = {"answered": "📞 NEW CALL (answered)", "missed": "📞 MISSED CALL", "sms": "💬 NEW TEXT"}


def nid() -> str:
    return str(uuid.uuid4())


def alert(kind: str) -> tuple[str, str, dict]:
    extra = "\n\n{{message.body}}" if kind == "sms" else ""
    body = (f"{HEAD[kind]} - The Pool Keepers\n\nName: {{{{contact.name}}}}\nPhone: {{{{contact.phone}}}}{extra}\n\n"
            "Card added to Pool Leads > New Lead. If it's a current customer, move it to Lost.")
    return ("internal_notification", "Text Nathan", {"type": "sms", "sms": {
        "body": body, "userType": "user", "selectedUser": [NATHAN], "attachments": []}})


def opp(source: str) -> tuple[str, str, dict]:
    return ("create_opportunity", "Create New Lead", {
        "fields": [], "type": "create_opportunity", "pipeline_id": PIPE, "pipeline_stage_id": STAGE,
        "opportunity_name": "{{contact.name}}", "opportunity_source": source,
        "monetary_value": "{{custom_values.weekly_service_price}}", "opportunity_status": "open"})


def guarded(items: list, skip: list[str]) -> list[dict]:
    c, y, n = guard_nodes(None, None, 0, skip)
    c["name"] = c["attributes"]["conditionName"] = "New lead? (not spam / not a customer)"
    body = chain(items, parent=y["id"])
    y["next"] = body[0]["id"]
    return [c, y, n, *body]


def call_steps(live: dict, kind: str) -> list[dict]:
    tpl = live["workflowData"]["templates"]
    tag = next(s for s in tpl if s["type"] == "add_contact_tag")["attributes"]["tags"]
    return guarded([tags(tag), opp("Inbound Call"), alert(kind)], SKIP)


def sms_steps() -> list[dict]:
    return guarded([tags(["new lead", "inbound sms"]), opp("Inbound SMS"), alert("sms")], SKIP + ["new lead"])


def note_steps(field_id: str) -> list[dict]:
    copy_ = ("update_contact_field", "Copy note text", {
        "type": "update_contact_field", "actionType": "update_field_data",
        "fields": [{"field": field_id, "value": "{{note.body}}", "title": FIELD, "type": "text", "date": ""}]})
    first = chain([copy_])
    nodes, head = if_else("Skimmer customer note?", [("Customer", [cond(field_id, "contains", m) for m in MARKERS],
                                                       [tags([CUSTOMER])])], "Other note", [],
                          parent_key=first[0]["id"], order=1)
    first[0]["next"] = head
    return [*first, *nodes]


def backup(name: str, data) -> None:
    BDIR.mkdir(parents=True, exist_ok=True)
    (BDIR / f"{name}-{time.strftime('%Y%m%d-%H%M%S')}.json").write_text(json.dumps(data))


def put(a: Agency, wid: str, name: str, version: int, steps: list[dict], allow: bool | None = None) -> None:
    body = {"name": name, "version": version, "status": "published", "workflowData": {"templates": steps}}
    if allow is not None:
        body["allowMultiple"] = allow
    a.call("PUT", BACKEND, f"/workflow/{LOC}/{wid}", body=body)


def new_flow(a: Agency, name: str, trig: dict, steps: list[dict], allow: bool) -> str:
    res = a.call("POST", BACKEND, f"/workflow/{LOC}", body={"name": name, "status": "draft"})
    wid = res.get("id") or res.get("_id")
    a.call("PUT", BACKEND, f"/workflow/{LOC}/{wid}", body={"name": name, "version": 1, "status": "draft",
           "allowMultiple": allow, "workflowData": {"templates": steps}})
    link = {"workflowId": wid, "workflow_id": wid, "location_id": LOC, "targetActionId": steps[0]["id"],
            "actions": [{"workflow_id": wid, "type": "add_to_workflow"}]}
    t = a.call("POST", BACKEND, f"/workflow/{LOC}/trigger", body={**trig, **link})
    a.call("PUT", BACKEND, f"/workflow/{LOC}/trigger/{t['id']}", body={**trig, **link, "id": t["id"]})
    live = a.workflow(LOC, wid)
    put(a, wid, name, live.get("version", 2), live["workflowData"]["templates"], allow)
    return wid


def field_id(a: Agency, write: bool) -> str | None:
    cfs = a.get(SERVICES, f"/locations/{LOC}/customFields").get("customFields", [])
    f = next((c for c in cfs if c.get("name") == FIELD), None)
    if f or not write:
        return f and f["id"]
    made = a.call("POST", SERVICES, f"/locations/{LOC}/customFields", body={"name": FIELD, "dataType": "TEXT",
                                                                            "model": "contact"})
    return (made.get("customField") or made)["id"]


def apply(a: Agency) -> None:
    flows = {w["name"]: w["id"] for w in a.workflows(LOC)}
    for t in [CUSTOMER, "inbound sms"]:
        try:
            a.call("POST", BACKEND, f"/workflow/{LOC}/tags/create", body={"tag": t})
        except Exception as e:  # 409 = already exists
            if "409" not in str(e):
                raise
    for wid, kind in CALLS.items():
        live = a.workflow(LOC, wid)
        backup(f"workflow-{wid}", {"workflow": live, "triggers": a.triggers(LOC, wid)})
        put(a, wid, live["name"], live.get("version", 1), call_steps(live, kind))
    if SMS_NAME not in flows:
        flows[SMS_NAME] = new_flow(a, SMS_NAME, {
            "type": "customer_reply", "name": "Customer Replied", "masterType": "highlevel", "schedule_config": {},
            "conditions": [{"operator": "==", "field": "message.type", "value": 2, "title": "Reply channel",
                            "type": "select"}]}, sms_steps(), False)
    if NOTE_NAME not in flows:
        fid = field_id(a, True)
        flows[NOTE_NAME] = new_flow(a, NOTE_NAME, {"type": "note_add", "name": "Note Added", "masterType": "highlevel",
                                                   "schedule_config": {}, "conditions": []}, note_steps(fid), True)
    time.sleep(5)
    for wid in [*CALLS, flows[SMS_NAME], flows[NOTE_NAME]]:
        w = a.workflow(LOC, wid)
        print(w["name"], w["status"], "re-entry", w.get("allowMultiple"), [s["name"] for s in w["workflowData"]["templates"]],
              [(t["type"], t.get("active")) for t in a.triggers(LOC, wid)])


def wait_for(fn, tries: int = 12, pause: int = 5):
    for _ in range(tries):
        time.sleep(pause)
        got = fn()
        if got:
            return got
    return None


def test(a: Agency) -> int:
    flows = {w["name"]: w["id"] for w in a.workflows(LOC)}
    fid = field_id(a, False)
    bad = 0
    made, zz_flows = [], []
    try:
        def contact(last: str, phone: str, tag_list: list[str] | None = None) -> str:
            c = a.call("POST", SERVICES, "/contacts/", body={"locationId": LOC, "firstName": "ZZ TEST", "lastName": last,
                                                             "phone": phone, **({"tags": tag_list} if tag_list else {})})
            cid = (c.get("contact") or c)["id"]
            made.append(cid)
            return cid

        def opps(cid: str):
            return a.get(SERVICES, "/opportunities/search", {"location_id": LOC, "contact_id": cid}).get("opportunities")

        # ZZ copy of the call chain: the SMS to Nathan is swapped for a stand-in tag (nothing reaches the client)
        zz_items = [tags(["new lead", "inbound call", "missed call"]), opp("Inbound Call"), tags([STAND_IN])]
        zz = new_flow(a, "ZZ TEST pk lead flow", {"type": "contact_tag", "name": "Contact Tag", "masterType": "highlevel",
                      "schedule_config": {}, "conditions": [{"operator": "index-of-true", "field": "tagsAdded",
                      "value": "zz never", "title": "Tag Added", "type": "select", "id": "tag-added"}]},
                      guarded(zz_items, SKIP), True)
        zz_flows.append(zz)
        time.sleep(5)
        lead = contact("Call Lead", "+15055550161")
        a.call("POST", SERVICES, f"/contacts/{lead}/workflow/{zz}", body={})
        o = wait_for(lambda: opps(lead))
        time.sleep(5)
        ct = a.get(SERVICES, f"/contacts/{lead}")["contact"]
        ok = bool(o) and o[0]["pipelineStageId"] == STAGE and STAND_IN in ct.get("tags", [])
        bad += not ok
        print("lead:", "ok" if ok else "FALHOU", o and o[0].get("source"), ct.get("tags"))
        cust = contact("Call Customer", "+15055550162", [CUSTOMER])
        a.call("POST", SERVICES, f"/contacts/{cust}/workflow/{zz}", body={})
        time.sleep(25)
        o2 = opps(cust)
        t2 = a.get(SERVICES, f"/contacts/{cust}")["contact"].get("tags", [])
        bad += bool(o2) or STAND_IN in t2
        print("existing customer:", "ok, sem card/aviso" if not o2 and STAND_IN not in t2 else "FALHOU", t2)
        note = contact("Skimmer Note", "+15055550163")
        a.call("POST", SERVICES, f"/contacts/{note}/notes", body={"body": "ZZ TEST - Other note, no marker"})
        time.sleep(30)
        t1 = a.get(SERVICES, f"/contacts/{note}")["contact"].get("tags", [])
        a.call("POST", SERVICES, f"/contacts/{note}/notes",
               body={"body": "CustomerStatusChanged ZZ TEST status changed to Active. Logged by: System"})
        got = wait_for(lambda: CUSTOMER in a.get(SERVICES, f"/contacts/{note}")["contact"].get("tags", []))
        cv = [c for c in a.get(SERVICES, f"/contacts/{note}")["contact"].get("customFields", []) if c.get("id") == fid]
        ok = CUSTOMER not in t1 and bool(got)
        bad += not ok
        print("note flow:", "ok" if ok else "FALHOU", "(sem marcador → sem tag; Active → tag)", cv)
        print("SMS flow: publicado", flows.get(SMS_NAME), "(SMS de entrada não dá para simular pela API)")
        msgs = a.get(SERVICES, "/conversations/search", {"locationId": LOC, "sort": "desc", "sortBy": "last_message_date",
                                                          "limit": 5}).get("conversations", [])
        print("últimas conversas:", [(c.get("phone") or c.get("contactName"), (c.get("lastMessageBody") or "")[:60])
                                     for c in msgs])
    finally:
        for cid in made:
            for o in opps(cid) or []:
                a.call("DELETE", SERVICES, f"/opportunities/{o['id']}")
            a.call("DELETE", SERVICES, f"/contacts/{cid}")
        for wid in zz_flows:
            a.call("DELETE", BACKEND, f"/workflow/{LOC}/{wid}")
        print("teste apagado:", len(made), "contatos,", len(zz_flows), "fluxo ZZ")
    return 1 if bad else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--test", action="store_true")
    args = ap.parse_args()
    load_dotenv()
    a = Agency()
    if a.location(LOC)["name"] != "The Pool Keepers":
        sys.exit("token errado (GHL_AGENCY=burchtech)")
    if args.apply:
        apply(a)
    elif args.test:
        return test(a)
    else:
        for wid, kind in CALLS.items():
            live = a.workflow(LOC, wid)
            print(live["name"], live["status"], "→", [s["name"] for s in call_steps(live, kind)])
        print(SMS_NAME, "→", [s["name"] for s in sms_steps()])
        print(NOTE_NAME, "→", [s["name"] for s in note_steps("FIELD")], "campo", field_id(a, False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
