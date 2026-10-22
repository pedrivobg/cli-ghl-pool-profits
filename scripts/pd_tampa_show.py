#!/usr/bin/env python3
"""Pool Duck Franchising: follow-up for the Tampa Franchise Show 2026 leads (Lee Majidimehr, via Jonathan, 22/10).

    set -a; . <poolduck.env>; set +a                         # Pool Duck agency token
    ./.venv/bin/python scripts/pd_tampa_show.py plan
    ./.venv/bin/python scripts/pd_tampa_show.py test --to pedro@poolprofits.com   # temporary copies, 1-min waits
    ... test --to pedro@poolprofits.com --stop-only         # only: booking after e-mail 1 stops the rest
    ./.venv/bin/python scripts/pd_tampa_show.py apply        # both workflows, published
    ./.venv/bin/python scripts/pd_tampa_show.py enroll       # put the contacts already tagged into the follow-up

Texts: config/pd_tampa_show.json (Lee's document, verbatim). Cadence from the document: Day 1 email + SMS 1, Day 2
email + SMS 2, Day 4, Day 5, Day 7 (Days 3 and 6 skipped).
- "Tampa Show 2026 - Follow-up": starts when the tag "tampa show 2026" is added (the 74 show leads imported 21/10
  carry it already: `enroll` puts them in through the API). Day 1 goes out right away between 9 AM and 8 PM ET,
  otherwise at 9 AM. Each later day goes out 9:30–11 AM ET: a 12 h (next day) or 36 h (skip a day) wait whose window
  holds it until the morning. Emails from lee@poolduck.com with Lee's signature; booking buttons prefill the e-mail
  and phone on the calendar.
- "Tampa Show 2026 - Intro Call Booked": an intro call booked (confirmed) on "Tampa Email Blast" (the document's link),
  "Pool Duck: Franchise Introductory Call" or "Pool Duck Franchise Discovery Call", by a contact with the show tag →
  out of the follow-up and an "Intro call" card in Franchise Development → 📞 Intro Call Booked (create or update;
  never moves a card back).
- "Tampa Show 2026 - Other Call Booked": Webinar, Territory Review, FDD Review or Meet the Executive Team booked by a
  show lead → only out of the follow-up (no card: those calls have their own stages).
enroll skips contacts in DND, with an intro call already booked, or already in a later stage of that pipeline.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import uuid

from _common import ROOT, load_dotenv

from cli_anything.gohighlevel.utils.agency import BACKEND, SERVICES, Agency, GHLError

CFG = json.loads((ROOT / "config" / "pd_tampa_show.json").read_text())
LOC, TAG = CFG["location"], CFG["tag"]
FOLLOW, BOOKED, OTHER = ("Tampa Show 2026 - Follow-up", "Tampa Show 2026 - Intro Call Booked",
                         "Tampa Show 2026 - Other Call Booked")
FOLDER = "f766e194-6a51-4e79-a52e-e657a6400205"  # Franchise Drip Campaigns (with the 2025 Tampa drip)
PIPELINE, STAGE = "ZQaQOztZ37hkLheoQJCO", "66d6fc1b-4df6-48fc-bae7-ca7b7c5b6efe"  # Franchise Development → Intro Call Booked
INTRO_CALENDARS = {"kgVdIKDXQQI8AQd2BUWx": "Tampa Email Blast", "PRroY8c7Av9mrgx8Ss2G": "Pool Duck: Franchise Introductory Call",
                   "rrsXrlUdnSE3Dqbc2oI3": "Pool Duck Franchise Discovery Call"}
# a later-stage call booked straight away (2 of the 74 had a webinar already): only out of the follow-up, no card
OTHER_CALENDARS = {"Xn2hvP5Cs3O6U2BW1zsn": "Pool Duck: Webinar Presentation", "mGXZpVzGUYLEdlwQHuL7": "Pool Duck - Territory Review",
                   "19x0xKbEEzgbr6JTqPea": "Pool Duck: FDD Review", "GZfxvovHjAjfAWJQwmBK": "Pool Duck: Meet The Executive Team",
                   "nAJCbMGT3PscojBAnkOd": "Pool Duck - Meet The Executive Team"}
EVERY_DAY = [0, 1, 2, 3, 4, 5, 6]
DAY1_WINDOW, MORNING = ("09:00", "20:00"), ("09:30", "11:00")
P = '<p style="margin:0 0 14px 0;font-family:verdana,geneva,sans-serif;font-size:15px;line-height:1.6;color:#000;">{}</p>'
LI = '<li style="margin:0 0 8px 0;font-family:verdana,geneva,sans-serif;font-size:15px;line-height:1.6;color:#000;">{}</li>'
BOOKING_PREFILL = CFG["booking"] + "?email={{contact.email}}&phone={{contact.phone_raw}}"


def inline(text: str) -> str:
    text = re.sub(r"\[([^\]]+)\]\((booking|video)\)", lambda m: (
        f'<a href="{BOOKING_PREFILL if m.group(2) == "booking" else CFG["video"]}" '
        f'style="color:#0b6fd6;text-decoration:underline;font-weight:bold;">{m.group(1)}</a>'), text)
    return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)


def email_html(day: dict) -> str:
    out = []
    for block in day["body"]:
        if isinstance(block, list):
            out.append('<ul style="margin:0 0 14px 0;padding-left:22px;">' + "".join(LI.format(inline(b)) for b in block) + "</ul>")
        else:
            out.append(P.format(inline(block)))
    out.append(P.format("<br>".join(CFG["signature"])))
    return "".join(out)


def sms_text(day: dict) -> str:
    return day["sms"].replace("{booking}", CFG["booking"]).replace("{video}", CFG["video"])  # not .format: {{merge}}


def wait(name: str, after: tuple[str, int], window: tuple[str, str] | None) -> dict:
    a = {"type": "time", "startAfter": {"type": after[0], "value": after[1], "when": "after"}, "name": name, "cat": "",
         "isHybridAction": True, "hybridActionType": "wait", "convertToMultipath": False, "transitions": []}
    if window:
        a["window"] = {"condition": "when", "days": EVERY_DAY, "start": window[0], "end": window[1]}
        a["windowCondition"] = {"field": "", "operator": "", "value": ""}
    return a


def chain(items: list[tuple[str, str, dict]]) -> list[dict]:
    ids = [str(uuid.uuid4()) for _ in items]
    out = []
    for i, (kind, name, attrs) in enumerate(items):
        s = {"id": ids[i], "order": i, "name": name, "type": kind, "attributes": attrs}
        if i:
            s["parentKey"] = ids[i - 1]
        if i + 1 < len(items):
            s["next"] = ids[i + 1]
        out.append(s)
    return out


def follow_steps(test_to: str | None = None) -> list[dict]:
    gaps = {1: ("Day 1 - send window (9 AM-8 PM ET)", ("minutes", 1), DAY1_WINDOW),
            2: ("Wait until Day 2 morning", ("hours", 12), MORNING), 4: ("Wait until Day 4 morning", ("hours", 36), MORNING),
            5: ("Wait until Day 5 morning", ("hours", 12), MORNING), 7: ("Wait until Day 7 morning", ("hours", 36), MORNING)}
    items = []
    for n, day in enumerate(CFG["days"], 1):
        name, after, window = gaps[day["day"]]
        items.append(("wait", name, wait(name, ("minutes", 1), None) if test_to else wait(name, after, window)))
        subject = ("[TEST] " if test_to else "") + day["subject"]
        items.append(("email", f"Email {n} (Day {day['day']})", {
            "subject": subject, "html": email_html(day), "from_email": CFG["from_email"], "from_name": CFG["from_name"],
            "attachments": []}))
        items.append(("sms", f"SMS {n} (Day {day['day']})", {"body": sms_text(day), "attachments": []}))
    return chain(items)


def booked_steps(follow_id: str, card: bool = True) -> list[dict]:
    head, yes, no = (str(uuid.uuid4()) for _ in range(3))
    cond = {"conditionType": "contact_detail", "conditionSubType": "tags", "conditionOperator": "index-of-true",
            "conditionValue": TAG, "__conditionId": str(uuid.uuid4()), "ifElseNodeId": "",
            "__customFieldType__": "standard", "isWait": False}
    rest = chain([
        ("remove_from_workflow", f"Stop {FOLLOW}", {"type": "remove_from_workflow", "workflow_id": [follow_id]}),
        ("create_opportunity", "Intro call card", {
            "fields": [], "type": "create_opportunity", "pipeline_id": PIPELINE, "pipeline_stage_id": STAGE,
            "opportunity_name": "{{contact.name}} - Intro call", "opportunity_source": "Tampa Show 2026",
            "monetary_value": "", "opportunity_status": "open"})][:2 if card else 1])
    rest[0]["parentKey"] = yes
    for s in rest:
        s["parent"] = yes
    return [
        {"id": head, "order": 0, "name": "Tampa show lead?", "type": "if_else", "cat": "conditions", "nodeType": "condition-node",
         "next": [yes, no], "attributes": {"currentRecipeType": "CUSTOM", "operator": "and", "if": True,
                                           "conditionName": "Tampa show lead?", "version": 2, "noneBranchName": "No",
                                           "branches": [{"id": yes, "name": "Yes", "operator": "and", "showErrors": False,
                                                         "segments": [{"__segmentId": str(uuid.uuid4()), "operator": "and",
                                                                       "conditions": [cond]}]}]}},
        {"id": yes, "parent": head, "parentKey": head, "order": 1, "name": "Yes", "type": "if_else", "cat": "conditions",
         "nodeType": "branch-yes", "sibling": [no], "next": rest[0]["id"],
         "attributes": {"if": False, "conditionName": "Condition", "operator": "and", "branches": []}},
        {"id": no, "parent": head, "parentKey": head, "order": 1, "name": "No", "type": "if_else", "cat": "conditions",
         "nodeType": "branch-no", "sibling": [yes], "attributes": {"else": True}},
        *rest]


def trigger(a: Agency, wid: str, first: str, body: dict) -> None:
    trig = {"masterType": "highlevel", "schedule_config": {}, "workflowId": wid, "workflow_id": wid, "location_id": LOC,
            "actions": [{"workflow_id": wid, "type": "add_to_workflow"}], "targetActionId": first, **body}
    t = a.call("POST", BACKEND, f"/workflow/{LOC}/trigger", body=trig)
    a.call("PUT", BACKEND, f"/workflow/{LOC}/trigger/{t['id']}", body={**trig, "id": t["id"]})


def tag_trigger() -> dict:
    return {"type": "contact_tag", "name": "Contact Tag", "conditions": [
        {"operator": "index-of-true", "field": "tagsAdded", "value": TAG, "title": "Tag Added", "type": "select", "id": "tag-added"}]}


def booking_trigger(cal: str) -> dict:
    return {"type": "appointment", "name": f"Booked - {INTRO_CALENDARS.get(cal) or OTHER_CALENDARS[cal]}", "conditions": [
        {"operator": "==", "field": "appointment.eventType", "value": "normal", "title": "Event type", "type": "select"},
        {"operator": "is-any-of", "field": "contactMode", "value": ["contact"], "type": "input"},
        {"operator": "==", "field": "appointment.status", "value": "confirmed", "title": "Appointment status is", "type": "select"},
        {"operator": "==", "field": "calendar.id", "value": cal, "title": "In calendar", "type": "select"}]}


def create(a: Agency, name: str, tpl: list[dict]) -> str:
    res = a.call("POST", BACKEND, f"/workflow/{LOC}", body={"name": name, "parentId": FOLDER, "status": "draft"})
    wid = res.get("id") or res.get("_id")
    a.call("PUT", BACKEND, f"/workflow/{LOC}/{wid}", body={"name": name, "version": 1, "status": "draft", "parentId": FOLDER,
                                                         "allowMultiple": False, "workflowData": {"templates": tpl}})
    return wid


def publish(a: Agency, wid: str) -> dict:
    live = a.workflow(LOC, wid)
    a.call("PUT", BACKEND, f"/workflow/{LOC}/{wid}", body={
        "name": live["name"], "version": live.get("version", 1), "status": "published", "parentId": live.get("parentId"),
        "workflowData": {"templates": live["workflowData"]["templates"]}})
    time.sleep(3)
    return a.workflow(LOC, wid)


def drop(a: Agency, wid: str) -> None:
    live = a.workflow(LOC, wid)
    a.call("PUT", BACKEND, f"/workflow/{LOC}/{wid}", body={"name": live["name"], "version": live.get("version", 1),
                                                         "status": "draft", "workflowData": {"templates": live["workflowData"]["templates"]}})
    a.call("DELETE", BACKEND, f"/workflow/{LOC}/{wid}")


def messages(a: Agency, cid: str) -> list[dict]:
    conv = a.call("GET", SERVICES, "/conversations/search", params={"locationId": LOC, "contactId": cid}).get("conversations", [])
    out = []
    for c in conv:
        ms = a.call("GET", SERVICES, f"/conversations/{c['id']}/messages").get("messages", {})
        out += ms.get("messages", ms) if isinstance(ms, dict) else ms
    return out


def tagged(a: Agency) -> list[dict]:
    out, page = [], 1
    while True:
        r = a.call("POST", SERVICES, "/contacts/search", body={"locationId": LOC, "pageLimit": 100, "page": page,
                                                               "filters": [{"field": "tags", "operator": "eq", "value": TAG}]})
        out += r.get("contacts", [])
        if not r.get("contacts") or len(out) >= r.get("total", 0):
            return out
        page += 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("mode", choices=["plan", "test", "apply", "enroll"])
    parser.add_argument("--to", help="test: inbox for the 5 test e-mails")
    parser.add_argument("--stop-only", action="store_true", help="test: only the booking-stops-the-sequence check")
    args = parser.parse_args()
    load_dotenv()
    a = Agency()
    if a.location(LOC)["name"] != "Pool Duck Franchising, LLC":
        sys.exit("token/sub-conta errados (carregar poolduck.env)")
    flows = {w["name"]: w["id"] for w in a.workflows(LOC)}

    if args.mode == "plan":
        for s in follow_steps():
            at = s["attributes"]
            what = at.get("subject") or at.get("body", "")[:70].replace("\n", " ") if s["type"] != "wait" else \
                f"{at['startAfter']['value']} {at['startAfter']['type']} · janela {at.get('window', {}).get('start')}–{at.get('window', {}).get('end')}"
            print(f"   [{s['type']}] {s['name']}: {what}")
        print(f"   {BOOKED}: gatilhos {list(INTRO_CALENDARS.values())} → tag '{TAG}'? → sai do follow-up + card Intro call")
        print(f"   {OTHER}: gatilhos {list(OTHER_CALENDARS.values())} → tag '{TAG}'? → sai do follow-up")
        return 0

    if args.mode == "test":
        if not args.to:
            parser.error("--to is required in test mode")
        f_id = create(a, f"ZZ TEST {FOLLOW}", follow_steps(args.to))
        b_id = create(a, f"ZZ TEST {BOOKED}", booked_steps(f_id))
        publish(a, f_id), publish(a, b_id)
        user, domain = args.to.split("@")
        made = []
        try:
            emails = lambda cid: [m for m in messages(a, cid) if m.get("messageType") == "TYPE_EMAIL" or m.get("type") == 3]  # noqa: E731
            if not args.stop_only:
                full = a.call("POST", SERVICES, "/contacts/", body={"locationId": LOC, "firstName": "Pedro",
                                                                    "lastName": "TEST full sequence", "email": args.to})["contact"]
                made.append(full)
                a.call("POST", SERVICES, f"/contacts/{full['id']}/workflow/{f_id}", body={})
            # a real inbox (example.com gets no e-mail): books after e-mail 1, must get nothing more
            stop = a.call("POST", SERVICES, "/contacts/", body={"locationId": LOC, "firstName": "Pedro", "lastName": "TEST booked",
                                                                "email": f"{user}+stop@{domain}", "tags": [TAG]})["contact"]
            made.append(stop)
            a.call("POST", SERVICES, f"/contacts/{stop['id']}/workflow/{f_id}", body={})
            for _ in range(24):
                time.sleep(15)
                if emails(stop["id"]):
                    break
            before = len(emails(stop["id"]))
            a.call("POST", SERVICES, f"/contacts/{stop['id']}/workflow/{b_id}", body={})
            for _ in range(24):  # long enough for the 4 remaining 1-min waits
                time.sleep(30)
                if not args.stop_only and len(emails(full["id"])) >= 5:
                    break
            if args.stop_only:
                time.sleep(120)
            after = len(emails(stop["id"]))
            opps = a.call("GET", SERVICES, "/opportunities/search", params={"location_id": LOC, "contact_id": stop["id"]}).get("opportunities", [])
            if not args.stop_only:
                print(f"   sequência completa: {len(emails(full['id']))} e-mail(s) para {args.to}")
            print(f"   agendou depois do e-mail {before}: {after} e-mail(s) no total · cards "
                  f"{[(o.get('name'), o.get('pipelineStageId') == STAGE, o.get('source')) for o in opps]}")
            ok = before >= 1 and after == before and any(o.get("pipelineStageId") == STAGE for o in opps)
            print("   ✓ ok: parou no agendamento" if ok else "   ✗ VERIFICAR")
        finally:
            for c in made:
                for o in a.call("GET", SERVICES, "/opportunities/search", params={"location_id": LOC, "contact_id": c["id"]}).get("opportunities", []):
                    a.call("DELETE", SERVICES, f"/opportunities/{o['id']}")
                a.call("DELETE", SERVICES, f"/contacts/{c['id']}")
            drop(a, b_id), drop(a, f_id)
            print("   limpo")
        return 0

    if args.mode == "apply":
        if {FOLLOW, BOOKED, OTHER} & set(flows):
            sys.exit("já existem: conferir antes de recriar")
        tpl = follow_steps()
        f_id = create(a, FOLLOW, tpl)
        trigger(a, f_id, tpl[0]["id"], tag_trigger())
        btpl = booked_steps(f_id)
        b_id = create(a, BOOKED, btpl)
        for cal in INTRO_CALENDARS:
            trigger(a, b_id, btpl[0]["id"], booking_trigger(cal))
        otpl = booked_steps(f_id, card=False)
        o_id = create(a, OTHER, otpl)
        for cal in OTHER_CALENDARS:
            trigger(a, o_id, otpl[0]["id"], booking_trigger(cal))
        for wid in (b_id, o_id, f_id):  # the exits first, so nobody is in the follow-up without them
            got = publish(a, wid)
            trs = [(t["type"], t.get("active")) for t in a.triggers(LOC, wid) if not t.get("deleted")]
            print(f"   ✓ {got['name']}: {got['status']} · {len(got['workflowData']['templates'])} passos · gatilhos {trs}")
        return 0

    # enroll
    f_id = flows[FOLLOW]
    if {"published"} != {a.workflow(LOC, flows[n])["status"] for n in (FOLLOW, BOOKED, OTHER)}:
        sys.exit("os três workflows têm que estar publicados")
    later = {s["id"] for p in a.pipelines(LOC) if p["id"] == PIPELINE for s in p["stages"][4:]}  # from Intro Call Booked on
    people, skipped = tagged(a), []
    for c in people:
        if c.get("dnd"):
            skipped.append((c.get("contactName"), "DND"))
            continue
        try:  # the contact search lags: a contact deleted minutes ago (test) can still come back
            opps = a.call("GET", SERVICES, "/opportunities/search", params={"location_id": LOC, "contact_id": c["id"]}).get("opportunities", [])
            appts = a.call("GET", SERVICES, f"/contacts/{c['id']}/appointments").get("events", [])
        except GHLError as e:
            skipped.append((c.get("contactName"), f"não existe mais ({e.status})"))
            continue
        if any(o.get("pipelineStageId") in later for o in opps) or \
                any(e.get("calendarId") in INTRO_CALENDARS or e.get("calendarId") in OTHER_CALENDARS for e in appts):
            skipped.append((c.get("contactName"), "já agendou / etapa adiante"))
            continue
        a.call("POST", SERVICES, f"/contacts/{c['id']}/workflow/{f_id}", body={})
    print(f"   {len(people) - len(skipped)} de {len(people)} postos no follow-up; pulados: {skipped or 'nenhum'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
