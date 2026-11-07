#!/usr/bin/env python3
"""Ekahi Solutions: pause the Monthly Service Reminder + "First 90 Days" sequence in DRAFT (Frank, e-mail 06/11/2026).

    ./.venv/bin/python scripts/ek_90day.py pause            # Monthly Service Reminder -> draft (backup + re-read)
    ./.venv/bin/python scripts/ek_90day.py build            # plan (read-only): texts + steps
    ./.venv/bin/python scripts/ek_90day.py build --apply    # templates (snippets) + DRAFT workflow + Won trigger
    ./.venv/bin/python scripts/ek_90day.py test             # ZZ TEST copy: minute waits, tags instead of SMS/e-mail

Sequence (trigger = Pool Leads / Won, the same stage as Won Stage, Post-Appointment and Review Request):
    +1 h          Day 1 SMS   service details (gate code, pets, best way to reach)   [Won Stage welcome SMS stays]
    day 7         SMS         how was the first visit                                [replaces the 1 h Post-Appointment SMS]
    (day 14       NPS / review request: Review Request workflow, unchanged)
    day 30        SMS         island pool tip (rain / sun / trade winds)
    day 75        e-mail      filter cleaning heads-up (text of the draft "Filter Clean Reminder")
    every 90 days SMS         seasonal check-in (Go To loop)
Before every message: guard if/else "Still a client?" (no tag lost lead / spam / dnd / one-time customer). Waits hold
until Mon-Fri 9:00-17:00 (account time zone, Pacific/Honolulu). Re-entry off (moving the card to Won again does not
restart the sequence). Idempotent: templates matched by name, workflow by name.
"""
from __future__ import annotations

import argparse
import json
import time
import uuid

from _common import ROOT, load_dotenv
from pp_won_stage import IS_OPS, NEST

from cli_anything.gohighlevel.utils.agency import BACKEND, SERVICES, Agency

LOC = "qtSUhAbLtnENh56h17a3"
SLUG = "ekahi-solutions-llc"
MONTHLY = "Monthly Service Reminder"
WON_STAGE = "Won Stage"
FILTER = "Filter Clean Reminder"
NAME = "First 90 Days - New Client Sequence"
MARK = "first 90 days"
SKIP = ["lost lead", "spam", "dnd", "one-time customer"]
WINDOW = {"condition": "when", "days": [1, 2, 3, 4, 5], "start": "09:00", "end": "17:00"}
PH = "{{custom_values.business_phone}}"
FN = "{{contact.first_name}}"
BIZ = "{{custom_values.friendly_business_name}}"

SMS = {  # template name -> body
    "90 Days - Day 1 - Service Details":
        f"Aloha {FN}, Erik here from {BIZ}! A few quick things so your first visit goes smooth: "
        "Any gate code or lockbox? Any pets we should know about? Best way to reach you, text or call? "
        "Just reply here. Mahalo!",
    "90 Days - Day 7 - First Visit Check-in":
        f"Howzit {FN}! How was your first visit? Anything we should know about your pool or equipment? "
        f"Just reply here or call/text {PH}. - Erik, {BIZ}",
    "90 Days - Day 30 - Island Pool Tip":
        f"Aloha {FN}! Quick tip from Erik: heavy rain dilutes your chemicals and strong sun burns off chlorine, "
        "so if the water looks off after a storm or a hot week, let me know. When the trade winds kick up, "
        "keeping the skimmer basket clear helps a lot. Reply anytime! Reply STOP to opt out.",
    "90 Days - Quarterly Seasonal Check-in":
        f"Howzit {FN}! Seasonal check-in from Erik at {BIZ}: anything new with your pool? More swimming, "
        f"guests coming, equipment making noise? Just reply or call/text {PH}. Mahalo! Reply STOP to opt out.",
}
EMAIL_NAME = "90 Days - Day 75 - Filter Clean Heads-up"
EMAIL_SUBJECT = "Your filter cleaning is coming up soon"

# (label, wait, kind, template name) — wait = (unit, value) after the previous message
PLAN = [
    ("Day 1 - Service Details", ("hours", 1), "sms", "90 Days - Day 1 - Service Details"),
    ("Day 7 - First Visit Check-in", ("days", 6), "sms", "90 Days - Day 7 - First Visit Check-in"),
    ("Day 30 - Island Pool Tip", ("days", 23), "sms", "90 Days - Day 30 - Island Pool Tip"),
    ("Day 75 - Filter Clean Heads-up", ("days", 45), "email", EMAIL_NAME),
    ("Quarterly Seasonal Check-in", ("days", 90), "sms", "90 Days - Quarterly Seasonal Check-in"),
]
LOOP = "Quarterly Seasonal Check-in"


def nid() -> str:
    return str(uuid.uuid4())


def flows(a: Agency) -> dict[str, dict]:
    return {w["name"]: w for w in a.workflows(LOC)}


def backup(a: Agency, wid: str, tag: str) -> None:
    bdir = ROOT / "backup" / SLUG
    bdir.mkdir(parents=True, exist_ok=True)
    wf = a.workflow(LOC, wid)
    trs = [t for t in a.triggers(LOC, wid) if not t.get("deleted")]
    (bdir / f"workflow-{wid}-{tag}-{time.strftime('%Y%m%d-%H%M%S')}.json").write_text(
        json.dumps({"workflow": wf, "triggers": trs}, ensure_ascii=False))


# ── pause ────────────────────────────────────────────────────────────────

def pause(a: Agency) -> int:
    w = flows(a)[MONTHLY]
    live = a.workflow(LOC, w["id"])
    print(f"{MONTHLY} ({w['id']}): status {live['status']}, re-entry {live.get('allowMultiple')}")
    if live["status"] == "draft":
        print("   já está em draft")
        return 0
    backup(a, w["id"], "before-pause")
    a.call("PUT", BACKEND, f"/workflow/{LOC}/{w['id']}", body={
        "name": live["name"], "version": live.get("version", 1), "status": "draft", "parentId": live.get("parentId"),
        "allowMultiple": live.get("allowMultiple", True), "workflowData": live["workflowData"]})
    time.sleep(3)
    now = a.workflow(LOC, w["id"])
    trs = [t for t in a.triggers(LOC, w["id"]) if not t.get("deleted")]
    same = now["workflowData"]["templates"] == live["workflowData"]["templates"]
    print(f"   agora: status {now['status']}, re-entry {now.get('allowMultiple')}, passos iguais {same}, "
          f"gatilhos ativos {[t.get('active') for t in trs]}")
    return 0 if now["status"] == "draft" and same else 1


# ── build ────────────────────────────────────────────────────────────────

def wait(label: str, unit: str, value: int, window: dict | None) -> dict:
    at = {"type": "time", "startAfter": {"type": unit, "value": value, "when": "after"}, "name": label, "cat": "",
          "windowCondition": {"field": "", "operator": "", "value": ""}, "isHybridAction": True,
          "hybridActionType": "wait", "convertToMultipath": False, "transitions": [],
          "timePeriodInputMode": "standard", "unitInputMode": "standard"}
    if window:
        at["window"] = window
    return {"id": nid(), "type": "wait", "name": label, "attributes": at, "cat": ""}


def guard() -> tuple[dict, dict, dict]:
    cond, yes, none = nid(), nid(), nid()
    name = "Still a client?"
    conditions = [{"conditionType": "contact_detail", "conditionSubType": "tags", "conditionOperator": "index-of-false",
                   "conditionValue": [tag], "__conditionId": nid(), "ifElseNodeId": "",
                   "__customFieldType__": "standard", "isWait": False, "nestedDropdownTypes": NEST,
                   "allowIsOperatorTypes": IS_OPS} for tag in SKIP]
    c = {"id": cond, "name": name, "type": "if_else", "cat": "conditions", "nodeType": "condition-node",
         "comments": [], "next": [yes, none],
         "attributes": {"currentRecipeType": "CUSTOM", "operator": "and", "if": True, "conditionName": name,
                        "version": 2, "noneBranchName": "Lost / spam / DND",
                        "branches": [{"id": yes, "name": "Client", "operator": "and", "showErrors": False,
                                      "branchNameError": "Branch name cannot be empty!",
                                      "segments": [{"__segmentId": nid(), "operator": "and",
                                                    "conditions": conditions}]}]}}
    y = {"id": yes, "parent": cond, "parentKey": cond, "order": 0, "name": "Client", "type": "if_else",
         "cat": "conditions", "sibling": [none], "comments": [], "nodeType": "branch-yes",
         "attributes": {"if": False, "conditionName": "Condition", "operator": "and", "branches": []}}
    n = {"id": none, "parent": cond, "parentKey": cond, "order": 0, "name": "Lost / spam / DND", "type": "if_else",
         "cat": "conditions", "sibling": [yes], "comments": [], "nodeType": "branch-no", "attributes": {"else": True}}
    return c, y, n


def message(label: str, kind: str, tname: str, ids: dict, email_tpl: dict, test: bool) -> dict:
    if test:  # copy: a tag per message, nothing goes out
        tag = "zz90 " + label.split(" - ")[0].lower()
        return {"id": nid(), "type": "add_contact_tag", "name": f"TEST {label}",
                "attributes": {"tags": [tag], "type": "add_contact_tag"}}
    if kind == "sms":
        return {"id": nid(), "type": "sms", "name": f"SMS - {label}",
                "attributes": {"template_id": ids[tname], "attachments": []}}
    at = json.loads(json.dumps(email_tpl))
    sid = nid()
    at.update(html=email_html(), subject=EMAIL_SUBJECT, template_id=ids[tname], templatesource="snippet",
              templateCreationMode="existing")
    if isinstance(at.get("trackingOptions"), dict):
        at["trackingOptions"]["sourceId"] = sid
    return {"id": sid, "type": "email", "name": f"Email - {label}", "attributes": at}


def email_html() -> str:
    p = '<p class="custom-newline" style="line-height: 1.5;padding-left: 0px!important;margin:0px">{}</p>'
    lines = [f"Aloha {FN},",
             f"It's been about 75 days since you started your service with {BIZ}, which means your filter cleaning "
             "is coming up soon!",
             "We'll be keeping an eye on it during our next few visits and will get you scheduled when the cleaning "
             "is due.",
             "As always, if you have any questions or concerns about your pool, just reply to this email or call/text "
             f"us at {PH}.",
             "Mahalo,", "{{custom_values.owner_first_name}}", BIZ, PH]
    return "".join(p.format(x) for x in lines)


def build_steps(ids: dict, email_tpl: dict, test: bool = False) -> list[dict]:
    """Marker tag, then per message: wait -> guard -> (Client branch) message -> next wait …; loop on the last."""
    out: list[dict] = []
    scope = {"parent": None, "prev": None, "order": 0}  # where the next node goes

    def put(node: dict) -> dict:
        node["order"] = scope["order"]
        if scope["parent"]:
            node["parent"] = scope["parent"]
        node["parentKey"] = scope["prev"] or scope["parent"]
        if not node["parentKey"]:
            node.pop("parentKey")
        prev = next((x for x in out if x["id"] == scope["prev"]), None)
        if prev is not None:
            prev["next"] = node["id"]
        elif scope["parent"]:
            next(x for x in out if x["id"] == scope["parent"])["next"] = node["id"]
        out.append(node)
        scope.update(prev=node["id"], order=scope["order"] + 1)
        return node

    put({"id": nid(), "type": "add_contact_tag", "name": f"Add Tag {MARK}",
         "attributes": {"tags": [MARK], "type": "add_contact_tag"}})
    loop_wait = None
    for label, (unit, value), kind, tname in PLAN:
        if test:
            unit, value = "minutes", 1
        w = put(wait(f"Wait {value} {unit.rstrip('s') if value == 1 else unit}" + (" (quarterly loop)" if label == LOOP else ""), unit, value,
                     None if test else WINDOW))
        if label == LOOP:
            loop_wait = w
        c, y, n = guard()
        put(c)
        y["order"] = n["order"] = c["order"] + 1
        out.extend([y, n])
        scope.update(parent=y["id"], prev=None, order=0)
        put(message(label, kind, tname, ids, email_tpl, test))
    put({"id": nid(), "type": "goto", "name": "Go To quarterly wait",
         "attributes": {"targetNodeId": loop_wait["id"], "type": "goto"}})
    out[-1].pop("next", None)
    return out


def snippet_ids(a: Agency, apply: bool) -> dict:
    snips = {s["name"].strip(): s for s in a.snippets(LOC)}
    want = {n: ("sms", {"body": b, "attachments": []}) for n, b in SMS.items()}
    want[EMAIL_NAME] = ("email", {"subject": EMAIL_SUBJECT, "html": email_html(), "attachments": []})
    ids = {}
    for name, (typ, tpl) in want.items():
        s = snips.get(name)
        if s and all((s.get("template") or {}).get(k) == v for k, v in tpl.items() if k != "attachments"):
            ids[name] = s["_id"]
            continue
        print(f"   {'atualiza' if s else 'cria'} template [{typ}] {name}")
        if not apply:
            ids[name] = f"<{name}>"
            continue
        if s:
            (ROOT / "backup" / SLUG).mkdir(parents=True, exist_ok=True)
            (ROOT / "backup" / SLUG / f"snippet-{s['_id']}-{time.strftime('%Y%m%d-%H%M%S')}.json").write_text(
                json.dumps(s, ensure_ascii=False))
            a.call("PUT", BACKEND, f"/snippets/{LOC}/{s['_id']}", body={"name": name, "type": typ, "template": tpl})
            ids[name] = s["_id"]
        else:
            res = a.call("POST", BACKEND, f"/snippets/{LOC}", body={"name": name, "type": typ, "template": tpl})
            r = res.get("snippet") or res
            ids[name] = r.get("id") or r.get("_id")
    return ids


def email_attrs(a: Agency, fl: dict) -> dict:
    wf = a.workflow(LOC, fl[FILTER]["id"])
    st = next(s for s in wf["workflowData"]["templates"] if s["type"] == "email")
    return st["attributes"]


def won_trigger(a: Agency, fl: dict) -> dict:
    t = next(t for t in a.triggers(LOC, fl[WON_STAGE]["id"]) if not t.get("deleted")
             and t["type"] == "pipeline_stage_updated")
    return {"type": t["type"], "name": "Client moved to Won", "masterType": t.get("masterType", "highlevel"),
            "schedule_config": {}, "conditions": json.loads(json.dumps(t["conditions"]))}


def build(a: Agency, apply: bool) -> int:
    for n, b in SMS.items():
        print(f"[sms {len(b)} chars] {n}\n   {b}")
    fl = flows(a)
    ids = snippet_ids(a, apply)
    steps = build_steps(ids, email_attrs(a, fl))
    for s in steps:
        print(f"   {'  ' if s.get('parent') else ''}- {s['name']} ({s['type']})")
    if not apply:
        print("\n(plano; --apply para gravar em DRAFT)")
        return 0
    for tag in [MARK, *SKIP]:
        try:
            a.call("POST", BACKEND, f"/workflow/{LOC}/tags/create", body={"tag": tag})
        except Exception:  # noqa: BLE001 — already exists
            pass
    parent = a.workflow(LOC, fl[WON_STAGE]["id"]).get("parentId")
    if NAME in fl:
        wid = fl[NAME]["id"]
        backup(a, wid, "before-rebuild")
        if a.workflow(LOC, wid)["status"] != "draft":
            raise SystemExit(f"{NAME} já está publicado — não regravo")
    else:
        res = a.call("POST", BACKEND, f"/workflow/{LOC}", body={"name": NAME, "parentId": parent, "status": "draft"})
        wid = res.get("id") or res.get("_id")
    live = a.workflow(LOC, wid)
    a.call("PUT", BACKEND, f"/workflow/{LOC}/{wid}", body={
        "name": NAME, "version": live.get("version", 1), "status": "draft", "parentId": parent,
        "allowMultiple": False, "workflowData": {"templates": steps}})
    trig = {**won_trigger(a, fl), "workflowId": wid, "workflow_id": wid, "location_id": LOC,
            "actions": [{"workflow_id": wid, "type": "add_to_workflow"}], "targetActionId": steps[0]["id"]}
    old = [t for t in a.triggers(LOC, wid) if not t.get("deleted")]
    if old:
        a.call("PUT", BACKEND, f"/workflow/{LOC}/trigger/{old[0]['id']}", body={**trig, "id": old[0]["id"]})
    else:
        t = a.call("POST", BACKEND, f"/workflow/{LOC}/trigger", body=trig)
        a.call("PUT", BACKEND, f"/workflow/{LOC}/trigger/{t['id']}", body={**trig, "id": t["id"]})
    time.sleep(3)
    now = a.workflow(LOC, wid)
    trs = [t for t in a.triggers(LOC, wid) if not t.get("deleted")]
    n = len(now["workflowData"]["templates"])
    print(f"✓ {NAME} ({wid}): status {now['status']}, re-entry {now.get('allowMultiple')}, {n} nós, "
          f"gatilhos {[(t['type'], t.get('active')) for t in trs]}")
    return 0 if now["status"] == "draft" and n == len(steps) and trs else 1


# ── test ─────────────────────────────────────────────────────────────────

def tags_of(a: Agency, cid: str) -> set:
    return set(a.call("GET", SERVICES, f"/contacts/{cid}")["contact"].get("tags") or [])


def until(a: Agency, cid: str, pred, secs: int = 240) -> set:
    t0 = time.time()
    while True:
        tg = tags_of(a, cid)
        if pred(tg) or time.time() - t0 > secs:
            return tg
        time.sleep(10)


def test(a: Agency) -> int:
    fl = flows(a)
    steps = build_steps({}, email_attrs(a, fl), test=True)
    name = f"ZZ TEST {NAME}"
    wid = cid = None
    labels = ["zz90 " + p[0].split(" - ")[0].lower() for p in PLAN]
    tq = labels[-1]
    bad = 0
    try:
        res = a.call("POST", BACKEND, f"/workflow/{LOC}", body={"name": name, "status": "draft"})
        wid = res.get("id") or res.get("_id")
        body = {"name": name, "version": 1, "status": "draft", "allowMultiple": False,
                "workflowData": {"templates": steps}}
        a.call("PUT", BACKEND, f"/workflow/{LOC}/{wid}", body=body)
        live = a.workflow(LOC, wid)
        a.call("PUT", BACKEND, f"/workflow/{LOC}/{wid}", body={**body, "status": "published",
               "version": live.get("version", 1), "workflowData": {"templates": live["workflowData"]["templates"]}})
        cid = a.call("POST", SERVICES, "/contacts/", body={
            "locationId": LOC, "firstName": "ZZ Test", "lastName": "90 days",
            "email": f"zz90-{int(time.time())}@example.com"})["contact"]["id"]
        time.sleep(3)
        a.call("POST", SERVICES, f"/contacts/{cid}/workflow/{wid}", body={})
        t0 = time.time()
        tg = until(a, cid, lambda t: tq in t, 600)
        got = [x for x in labels if x in tg]
        ok = got == labels and MARK in tg
        bad += not ok
        print(f"   {'✓' if ok else '✗'} caminho completo em {int(time.time() - t0)} s: {got}")
        # loop: take the quarterly tag off, it must come back on the next pass
        a.call("DELETE", SERVICES, f"/contacts/{cid}/tags", body={"tags": [tq]})
        tg = until(a, cid, lambda t: tq in t, 240)
        ok = tq in tg
        bad += not ok
        print(f"   {'✓' if ok else '✗'} Go To: check-in trimestral voltou na volta seguinte")
        # guard: tag "lost lead" -> next pass stops before the message
        a.call("POST", SERVICES, f"/contacts/{cid}/tags", body={"tags": ["lost lead"]})
        time.sleep(5)
        a.call("DELETE", SERVICES, f"/contacts/{cid}/tags", body={"tags": [tq]})
        tg = until(a, cid, lambda t: tq in t, 180)
        ok = tq not in tg
        bad += not ok
        print(f"   {'✓' if ok else '✗'} guarda: com 'lost lead' a mensagem não sai (tags {sorted(tg)})")
    finally:
        if cid:
            a.call("DELETE", SERVICES, f"/contacts/{cid}")
        if wid:
            live = a.workflow(LOC, wid)
            a.call("PUT", BACKEND, f"/workflow/{LOC}/{wid}", body={"name": name, "version": live.get("version", 1),
                   "status": "draft", "workflowData": {"templates": live["workflowData"]["templates"]}})
            a.call("DELETE", BACKEND, f"/workflow/{LOC}/{wid}")
        print(f"   limpo (contato e {name} apagados)")
    return 1 if bad else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["pause", "build", "test"])
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    load_dotenv()
    a = Agency()
    return {"pause": lambda: pause(a), "build": lambda: build(a, args.apply), "test": lambda: test(a)}[args.cmd]()


if __name__ == "__main__":
    raise SystemExit(main())
