#!/usr/bin/env python3
"""Pool Duck Lakewood Ranch: the review campaign with our review gate (NPS first) — Pedro, 20/10.

    set -a; . <poolduck.env>; set +a
    ./.venv/bin/python scripts/pd_lwr_nps_gate.py setup   # NPS fields + NPS Form + nps_survey_link + tags
    ./.venv/bin/python scripts/pd_lwr_nps_gate.py test    # the gate on 3 test contacts (score 5, score 2, no answer)
    ./.venv/bin/python scripts/pd_lwr_nps_gate.py apply   # "Review Request Campaign - Turtle Rock" gets the gate

Same gate as every Pool Profits account (Southern's "Review Request", config/nps_gate_steps.json):
NPS request with the link in custom value nps_survey_link (pre-filled with e-mail and phone) → wait for
contact.nps_score → 4–5: Google review (SMS + e-mail); 0–3: team alert (Kenton + Pool Duck Service), no
review link; no answer in WAIT_DAYS: Google review, as Southern's timeout. The NPS Form is the Pool
Profits one (config/nps_form.json) pointed at LWR's own fields. The campaign's first step (weekday
window, where the 271 contacts are parked) keeps its id so they follow the new version.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import uuid

from _common import ROOT, load_dotenv
from pd_lwr_reviews import (DRIP, DRIP_STEP, EMAIL_HTML, EMAIL_SUBJECT, EXCLUDE_TAG, LWR, NAME, SEND_DAYS,
                            SEND_WINDOW)
from pd_lwr_workflows import ALERT_USERS

from cli_anything.gohighlevel.utils.agency import BACKEND, SERVICES, Agency

FIELDS = {"contact.nps_score": ("NPS Score", "TEXT"), "contact.nps_message": ("NPS Message", "LARGE_TEXT")}
FORM_HOST = "https://api.leadconnectorhq.com/widget/form/"  # works for any agency (Pool Duck has no link domain)
WAIT_DAYS = 6  # Tuesday's batches → the next Monday, same hours: spaced and never on a weekend
TAGS = {"high": "review gate - promoter", "low": "review gate - low score", "none": "review gate - no answer"}
NPS_LINK = "{{custom_values.nps_survey_link}}?email={{contact.email}}&phone={{contact.phone_raw}}"
NPS_SMS = ("Hi, this is Pool Duck Lakewood Ranch! Thank you for trusting us with your pool. How are we doing? "
           f"Please take 10 seconds to rate your experience here: {NPS_LINK} We really appreciate your feedback.")
P = '<p style="margin:0px"><span style="font-size: 13pt; font-family: helvetica">{}</span></p>'
NPS_EMAIL_SUBJECT = "How are we doing? (10 seconds)"
NPS_EMAIL_HTML = "".join([
    P.format("Hi,"), "<br>",
    P.format("Thank you for trusting Pool Duck Lakewood Ranch with your pool. How are we doing?"), "<br>",
    f'<p style="margin:0px"><a href="{NPS_LINK}" style="display:inline-block;padding:12px 22px;background:#60b847;'
    'color:#ffffff;text-decoration:none;border-radius:6px;font-family:helvetica;font-size:13pt;font-weight:bold">'
    'Rate your experience</a></p>', "<br>",
    P.format("It takes 10 seconds. Thank you!<br>The Pool Duck Lakewood Ranch team"),
])
HIGH_SMS = ("Thank you so much for the great rating! Would you share it on Google? It takes 30 seconds and helps "
            "other families in Lakewood Ranch find us: {{custom_values.public_review_link}}")
NONE_SMS = ("Hi again from Pool Duck Lakewood Ranch! If you have a moment, we'd be grateful for a quick Google "
            "review: {{custom_values.public_review_link}} Thank you!")
LOW_ALERT = ("⚠️ Negative customer feedback received (review campaign).\n\nCustomer: {{contact.name}}\n"
             "Phone: {{contact.phone}}\nNPS Score: {{contact.nps_score}}\nNPS Message: {{contact.nps_message}}\n\n"
             "Please contact the customer to resolve the issue.")
GATE = json.loads((ROOT / "config" / "nps_gate_steps.json").read_text())


def nid() -> str:
    return str(uuid.uuid4())


def node(type_: str, name: str, attrs: dict, **links) -> dict:
    return {"id": links.pop("id", None) or nid(), "type": type_, "name": name, "attributes": attrs, **links}


def chain(nodes: list[dict], parent: str | None, first_parent_key: str | None, start_order: int = 0) -> list[dict]:
    """Link nodes one after another inside `parent` (None = root)."""
    for i, n in enumerate(nodes):
        n["order"] = start_order + i
        if parent:
            n["parent"] = parent
        pk = nodes[i - 1]["id"] if i else first_parent_key
        if pk:
            n["parentKey"] = pk
        if i:
            nodes[i - 1]["next"] = n["id"]
    return nodes


def gate(score_field: str, after: dict, order: int, wait: dict, test: bool = False) -> list[dict]:
    """wait for the score → if low / else high; timeout branch. `after` = the step before the wait."""
    attrs = json.loads(json.dumps(GATE["wait_condition"]).replace("__NPS_SCORE__", score_field))
    attrs["startAfter"] = wait
    t_ok, t_out = nid(), nid()
    unit = f"{wait['value']} {wait['type']}"
    attrs["transitions"] = [
        {"id": t_ok, "name": "wait", "condition": "primary", "conditionType": "user-defined", "isPrimaryBranch": True,
         "description": "", "attributes": {"type": "wait_condition", "description": "What will happen when specified conditions are met"}},
        {"id": t_out, "name": "timeout", "condition": "timeout", "conditionType": "user-defined", "isPrimaryBranch": False,
         "description": "", "attributes": {"type": "wait_timeout", "description": f"What will happen after {unit}"}}]
    w = node("wait", "Wait for NPS answer", attrs, order=order, parentKey=after["id"], next=[t_ok, t_out],
             cat="multi-path")  # GHL rejects transitions under a wait that is not multi-path at node level
    after["next"] = w["id"]
    tr_ok = node("transition", "wait", {"type": "wait_condition", "description": "What will happen when specified conditions are met"},
                 id=t_ok, parent=w["id"], parentKey=w["id"], order=order + 1, cat="transition")
    tr_out = node("transition", "timeout", {"type": "wait_timeout", "description": f"What will happen after {unit}"},
                  id=t_out, parent=w["id"], parentKey=w["id"], order=order + 1, cat="transition")
    low, high = nid(), nid()
    cond_attrs = json.loads(json.dumps(GATE["if_low"]).replace("__NPS_SCORE__", score_field))
    cond_attrs["branches"][0]["id"] = low
    cond = node("if_else", "yes", cond_attrs, parent=t_ok, parentKey=t_ok, order=0, cat="conditions",
                nodeType="condition-node", next=[low, high], comments=[])
    tr_ok["next"] = cond["id"]
    b_low = node("if_else", "Low NPS Score Detected", {"if": False, "conditionName": "Condition", "operator": "and",
                 "branches": []}, id=low, parent=cond["id"], parentKey=cond["id"], order=1, cat="conditions",
                 nodeType="branch-yes", sibling=[high], comments=[])
    b_high = node("if_else", "High NPS Score Detected", {"else": True}, id=high, parent=cond["id"], parentKey=cond["id"],
                  order=1, cat="conditions", nodeType="branch-no", sibling=[low], comments=[])

    def tag(which: str) -> dict:
        return node("add_contact_tag", f"Add Tag {TAGS[which]}", {"tags": [TAGS[which]], "type": "add_contact_tag"})

    low_steps = [tag("low")] + ([] if test else [node("internal_notification", "Notify Team - Negative Feedback", {
        "type": "sms", "sms": {"body": LOW_ALERT, "userType": "user", "selectedUser": ALERT_USERS, "attachments": []}})])
    high_steps = [tag("high")] + ([] if test else [
        node("sms", "SMS - Google review", {"body": HIGH_SMS, "attachments": []}),
        node("email", "Email - Google review", {"subject": EMAIL_SUBJECT, "html": EMAIL_HTML, "from_email": "",
                                                "from_name": "", "attachments": []})])
    window = {"type": "time", "startAfter": {"type": "minutes", "value": 1, "when": "after"}, "name": "Wait for send window",
              "cat": "", "isHybridAction": True, "hybridActionType": "wait", "convertToMultipath": False, "transitions": [],
              "window": {"condition": "when", "days": SEND_DAYS, "start": SEND_WINDOW[0], "end": SEND_WINDOW[1]},
              "windowCondition": {"field": "", "operator": "", "value": ""}}
    none_steps = ([] if test else [node("wait", "Wait for send window", window)]) + [tag("none")] + ([] if test else [
        node("sms", "SMS - Google review reminder", {"body": NONE_SMS, "attachments": []}),
        node("email", "Email - Google review", {"subject": EMAIL_SUBJECT, "html": EMAIL_HTML, "from_email": "",
                                                "from_name": "", "attachments": []})])
    b_low["next"], b_high["next"], tr_out["next"] = low_steps[0]["id"], high_steps[0]["id"], none_steps[0]["id"]
    return [w, tr_ok, tr_out, cond, b_low, b_high, *chain(low_steps, low, low), *chain(high_steps, high, high),
            *chain(none_steps, t_out, t_out)]


def refs_ok(tpl: list[dict]) -> bool:
    ids = {s["id"] for s in tpl}
    refs = [r for s in tpl for r in ([s.get("next")] if isinstance(s.get("next"), str) else s.get("next") or [])]
    refs += [s[k] for s in tpl for k in ("parent", "parentKey") if s.get(k)]
    return all(r in ids for r in refs)


def fields(a: Agency) -> dict[str, str]:
    cfs = {c.get("fieldKey"): c["id"] for c in a.custom_fields(LWR)}
    for key, (name, dtype) in FIELDS.items():
        if key not in cfs:
            made = a.call("POST", SERVICES, f"/locations/{LWR}/customFields", body={"name": name, "dataType": dtype, "model": "contact"})
            cfs[key] = (made.get("customField") or made)["id"]
            print(f"✓ campo {name} criado")
    return cfs


def setup(a: Agency) -> None:
    cfs = fields(a)
    have = [f for f in a.forms(LWR) if f["name"].strip().lower() == "nps form"]
    if have:
        fid = have[0].get("_id") or have[0].get("id")
    else:
        fd = json.loads((ROOT / "config" / "nps_form.json").read_text().replace("__LOCATION__", LWR))
        for fl in fd["form"]["fields"]:
            if fl.get("fieldKey") in FIELDS:
                fl["tag"] = cfs[fl["fieldKey"]]
            if fl.get("tag") in ("first_name", "last_name"):
                fl["required"] = False
        res = a.call("POST", BACKEND, "/forms/", body={"name": "NPS Form", "formData": fd, "locationId": LWR})
        made = res.get("form") or res.get("data") or res
        fid = made.get("_id") or made.get("id")
        print(f"✓ NPS Form criado {fid}")
    link = FORM_HOST + fid
    cvs = {c["name"]: c for c in a.custom_values(LWR)}
    cv = cvs.get("NPS Survey Link")
    if not cv:
        a.call("POST", SERVICES, f"/locations/{LWR}/customValues", body={"name": "NPS Survey Link", "value": link})
    elif cv.get("value") != link:
        a.call("PUT", SERVICES, f"/locations/{LWR}/customValues/{cv['id']}", body={"name": cv["name"], "value": link})
    print(f"✓ nps_survey_link = {link}")
    have_tags = {t["name"].lower() for t in a.tags(LWR)}
    for t in TAGS.values():
        if t not in have_tags:
            a.call("POST", BACKEND, f"/workflow/{LWR}/tags/create", body={"tag": t})


def score_field(a: Agency) -> str:
    return {c.get("fieldKey"): c["id"] for c in a.custom_fields(LWR)}["contact.nps_score"]


def put(a: Agency, wid: str, name: str, status: str, parent: str | None, tpl: list[dict]) -> dict:
    live = a.workflow(LWR, wid)
    a.call("PUT", BACKEND, f"/workflow/{LWR}/{wid}", body={
        "name": name, "version": live.get("version", 1), "status": status, "parentId": parent,
        "allowMultiple": False, "workflowData": {"templates": tpl}})
    time.sleep(4)
    return a.workflow(LWR, wid)


def test(a: Agency) -> int:
    """Gate alone (no window, no messages, 3-minute timeout) on 3 contacts: 5 → promoter, 2 → low, none → no answer."""
    field = score_field(a)
    go = "nps gate test"
    try:
        a.call("POST", BACKEND, f"/workflow/{LWR}/tags/create", body={"tag": go})
    except Exception:  # noqa: BLE001
        pass
    start = node("add_contact_tag", "Start", {"tags": ["nps gate test started"], "type": "add_contact_tag"}, order=0)
    tpl = [start, *gate(field, start, 1, {"type": "minutes", "value": 3, "when": "after"}, test=True)]
    name = "ZZ NPS gate test (Pedro) - delete"
    wid = (lambda r: r.get("id") or r.get("_id"))(a.call("POST", BACKEND, f"/workflow/{LWR}", body={"name": name, "status": "draft"}))
    a.call("PUT", BACKEND, f"/workflow/{LWR}/{wid}", body={"name": name, "version": 1, "status": "draft",
                                                           "allowMultiple": False, "workflowData": {"templates": tpl}})
    trig = {"type": "contact_tag", "name": "Contact Tag", "masterType": "highlevel", "schedule_config": {},
            "conditions": [{"operator": "index-of-true", "field": "tagsAdded", "value": go, "title": "Tag added",
                            "type": "select", "id": "tag-added"}], "workflowId": wid, "workflow_id": wid,
            "location_id": LWR, "actions": [{"workflow_id": wid, "type": "add_to_workflow"}], "targetActionId": start["id"]}
    t = a.call("POST", BACKEND, f"/workflow/{LWR}/trigger", body=trig)
    a.call("PUT", BACKEND, f"/workflow/{LWR}/trigger/{t['id']}", body={**trig, "id": t["id"]})
    got = put(a, wid, name, "published", None, tpl)
    print(f"workflow de teste {got['status']} · {len(got['workflowData']['templates'])} passos · refs ok {refs_ok(got['workflowData']['templates'])}")
    cs = {}
    for label in ("score 5", "score 2", "sem resposta"):
        c = a.call("POST", SERVICES, "/contacts/", body={"locationId": LWR, "firstName": "TEST", "lastName": f"NPS gate {label} (delete)",
                                                          "email": f"nps-gate-{uuid.uuid4().hex[:6]}@example.com",
                                                          "tags": [EXCLUDE_TAG]})["contact"]
        cs[label] = c["id"]
    time.sleep(3)
    for cid in cs.values():
        a.call("POST", SERVICES, f"/contacts/{cid}/tags", body={"tags": [go]})
    time.sleep(40)
    for label, score in (("score 5", "5"), ("score 2", "2")):
        a.call("PUT", SERVICES, f"/contacts/{cs[label]}", body={"customFields": [{"id": field, "field_value": score}]})
    want = {"score 5": TAGS["high"], "score 2": TAGS["low"], "sem resposta": TAGS["none"]}
    got_tags = {}
    for _ in range(30):
        time.sleep(15)
        got_tags = {k: a.call("GET", SERVICES, f"/contacts/{v}")["contact"].get("tags") or [] for k, v in cs.items()}
        if all(want[k] in got_tags[k] for k in cs):
            break
    ok = all(want[k] in got_tags[k] and not (set(TAGS.values()) - {want[k]}) & set(got_tags[k]) for k in cs)
    for k in cs:
        print(f"   {k}: {[t for t in got_tags[k] if t.startswith('review gate')]} (esperado {want[k]!r})")
    print(f"{'✓' if ok else '✗ VERIFICAR'} gate")
    for cid in cs.values():
        a.call("DELETE", SERVICES, f"/contacts/{cid}")
    a.call("DELETE", BACKEND, f"/workflow/{LWR}/{wid}")
    return 0 if ok else 1


def apply(a: Agency) -> int:
    field = score_field(a)
    w = next(w for w in a.workflows(LWR) if w["name"] == NAME)
    live = a.workflow(LWR, w["id"])
    old = live["workflowData"]["templates"]
    first = next(s for s in old if s.get("order") == 0 and s["type"] == "wait")  # contacts are parked here
    bdir = ROOT / "backup" / "pool-duck-lakewood-ranch"
    bdir.mkdir(parents=True, exist_ok=True)
    trs = [t for t in a.triggers(LWR, w["id"]) if not t.get("deleted")]
    (bdir / f"workflow-{w['id']}-{time.strftime('%Y%m%d-%H%M%S')}.json").write_text(json.dumps({"workflow": live, "triggers": trs}))
    root = chain([{k: v for k, v in first.items() if k not in ("next", "parentKey", "parent")},
                  node("drip", f"Drip Mode - {DRIP[0]} every {DRIP[1]} min", DRIP_STEP),
                  node("sms", "SMS - NPS request", {"body": NPS_SMS, "attachments": []}),
                  node("email", "Email - NPS request", {"subject": NPS_EMAIL_SUBJECT, "html": NPS_EMAIL_HTML,
                                                        "from_email": "", "from_name": "", "attachments": []})], None, None)
    tpl = [*root, *gate(field, root[-1], len(root), {"type": "days", "value": WAIT_DAYS, "when": "after"})]
    if not refs_ok(tpl):
        raise SystemExit("referência quebrada — não salvo")
    got = put(a, w["id"], NAME, live["status"], live.get("parentId"), tpl)
    t2 = got["workflowData"]["templates"]
    ok = got["status"] == live["status"] and len(t2) == len(tpl) and refs_ok(t2) and \
        any(s["id"] == first["id"] and s.get("order") == 0 for s in t2)
    print(f"{'✓' if ok else '✗ VERIFICAR'} {NAME} [{got['status']}] · {len(t2)} passos · 1º passo mantido ({first['id'][:8]})")
    return 0 if ok else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("action", choices=["setup", "test", "apply"])
    args = parser.parse_args()
    load_dotenv()
    a = Agency()
    if args.action == "setup":
        setup(a)
        return 0
    return test(a) if args.action == "test" else apply(a)


if __name__ == "__main__":
    sys.exit(main())
