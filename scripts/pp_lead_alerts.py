#!/usr/bin/env python3
"""BluVantage (Vanessa/Paul, 07-12/10): "NEW LEAD" texts only for real leads, and website leads routed.

    ./.venv/bin/python scripts/pp_lead_alerts.py test                     # Test Snapshot dry run of the guard
    ./.venv/bin/python scripts/pp_lead_alerts.py plan --only "BluVantage"
    ./.venv/bin/python scripts/pp_lead_alerts.py apply --only "BluVantage"

What was wrong (live data 06-14/10):
- "Incoming Call To Pipeline" and "SMS To Pipeline" got a "🚨 NEW LEAD🚨" text to 5 users on 06/10 with no
  filter: contacts already marked spam (tags spam/dnd, set by "DND Contact") and current customers got
  the text too. With the IVR every call ends "completed", so every call enters.
- The website form ("Footer Form - BluVantage", in the footer of every page) only had an empty draft
  listening to it: contact created, no card, no text.
- "AdWords Form - New Lead" texted the contact owner, and form contacts have no owner: nobody got it.

What this does (backup of every workflow/trigger first):
- GUARDED workflows: an if/else at the start ("Not spam / not a customer") wraps the whole chain, so
  spam/dnd/current customers make no tag, card, task or text; a second identical check right before the
  NEW LEAD text, which goes out 1 h after the call, so marking the card SPAM in that hour skips the text.
- FORM_ROUTE: a "Form Submitted" trigger for the website form on "Website Form Fill To Pipeline".
- OWNER_FIX: the Google Ads form text goes to the same users as the other NEW LEAD texts.
Branch conditions are contact tags (index-of-false), not trigger filters, so they work for any trigger.
"""
from __future__ import annotations

import argparse
import json
import time
import uuid

from _common import ROOT, load_dotenv, location_dirs
from pp_audit import load
from pp_won_stage import DROP, IS_OPS, NEST

from cli_anything.gohighlevel.utils.agency import BACKEND, SERVICES, Agency

SKIP = ["spam", "dnd", "current customer"]
GUARDED = ["Incoming Call To Pipeline", "SMS To Pipeline"]
FORM_ROUTE = {"Website Form Fill To Pipeline": "Footer Form - BluVantage"}
OWNER_FIX = ["AdWords Form - New Lead"]
GUARD_NAME = "Not spam / not a customer?"
TEST_LOC = "hmzX5j1dPhOQKX2dH4kf"  # Test Snapshot


def nid() -> str:
    return str(uuid.uuid4())


def is_alert(s: dict) -> bool:
    return s["type"] == "internal_notification" and "NEW LEAD" in ((s["attributes"].get("sms") or {}).get("body") or "")


def guard_nodes(prev: str | None, branch: str | None, order: int) -> tuple[dict, dict, dict]:
    """if/else: contact has none of SKIP → "Lead" branch; otherwise the empty None branch."""
    cond, yes, none = nid(), nid(), nid()
    conditions = [{"conditionType": "contact_detail", "conditionSubType": "tags", "conditionOperator": "index-of-false",
                   "conditionValue": [tag], "__conditionId": nid(), "ifElseNodeId": "",
                   "__customFieldType__": "standard", "isWait": False, "nestedDropdownTypes": NEST,
                   "allowIsOperatorTypes": IS_OPS} for tag in SKIP]
    c = {"id": cond, "order": order, "name": GUARD_NAME, "type": "if_else", "cat": "conditions",
         "nodeType": "condition-node", "comments": [], "next": [yes, none],
         "attributes": {"currentRecipeType": "CUSTOM", "operator": "and", "if": True, "conditionName": GUARD_NAME,
                        "version": 2, "noneBranchName": "Spam / customer",
                        "branches": [{"id": yes, "name": "Lead", "operator": "and", "showErrors": False,
                                      "branchNameError": "Branch name cannot be empty!",
                                      "segments": [{"__segmentId": nid(), "operator": "and",
                                                    "conditions": conditions}]}]}}
    if prev:
        c["parentKey"] = prev
    if branch:
        c["parent"] = branch
    y = {"id": yes, "parent": cond, "parentKey": cond, "order": order + 1, "name": "Lead", "type": "if_else",
         "cat": "conditions", "sibling": [none], "comments": [], "nodeType": "branch-yes",
         "attributes": {"if": False, "conditionName": "Condition", "operator": "and", "branches": []}}
    n = {"id": none, "parent": cond, "parentKey": cond, "order": order + 1, "name": "Spam / customer",
         "type": "if_else", "cat": "conditions", "sibling": [yes], "comments": [], "nodeType": "branch-no",
         "attributes": {"else": True}}
    return c, y, n


def guard(templates: list[dict], alert=is_alert) -> list[dict]:
    """Wrap a linear chain in the guard and re-check right before its last step (the alert)."""
    if any(s["type"] == "if_else" for s in templates):
        raise SystemExit("workflow already has if/else — not rebuilding blindly")
    by_id = {s["id"]: s for s in templates}
    first = next(s for s in templates if not s.get("parentKey"))
    chain = [first]
    while chain[-1].get("next"):
        chain.append(by_id[chain[-1]["next"]])
    if len(chain) != len(templates) or not alert(chain[-1]):
        raise SystemExit("expected a linear chain ending in the NEW LEAD text")
    chain = json.loads(json.dumps(chain))
    *body, last = chain
    ca, ya, na = guard_nodes(None, None, 0)
    for i, s in enumerate(body):
        s.update(order=i, parent=ya["id"], parentKey=body[i - 1]["id"] if i else ya["id"])
        s.pop("next", None)
        if i:
            body[i - 1]["next"] = s["id"]
    ya["next"] = body[0]["id"]
    cb, yb, nb = guard_nodes(body[-1]["id"], ya["id"], len(body))
    body[-1]["next"] = cb["id"]
    last.update(order=0, parent=yb["id"], parentKey=yb["id"])
    last.pop("next", None)
    yb["next"] = last["id"]
    return [ca, ya, na, *body, cb, yb, nb, last]


def put_workflow(a: Agency, loc: str, wid: str, live: dict, templates: list[dict]) -> None:
    a.call("PUT", BACKEND, f"/workflow/{loc}/{wid}", body={
        "name": live["name"], "version": live.get("version", 1), "status": live["status"],
        "parentId": live.get("parentId"), "allowMultiple": live.get("allowMultiple", False),
        "workflowData": {"templates": templates}})


def link(loc: str, wid: str) -> dict:
    return {"workflowId": wid, "workflow_id": wid, "location_id": loc,
            "actions": [{"workflow_id": wid, "type": "add_to_workflow"}]}


def retarget(a: Agency, loc: str, wid: str, first: str) -> None:
    for t in [x for x in a.triggers(loc, wid) if not x.get("deleted")]:
        body = {k: v for k, v in t.items() if k not in DROP}
        body.update(link(loc, wid))
        body["targetActionId"] = first
        a.call("PUT", BACKEND, f"/workflow/{loc}/trigger/{t['id']}", body=body)


def check(templates: list[dict]) -> bool:
    """Both guards present, the alert only under the inner one, every next/parent id resolvable."""
    ids = {s["id"] for s in templates}
    conds = [s for s in templates if s.get("name") == GUARD_NAME and s.get("nodeType") == "condition-node"]
    alert = [s for s in templates if is_alert(s)]
    refs = [r for s in templates for r in ([s.get("next")] if isinstance(s.get("next"), str) else s.get("next") or [])]
    refs += [s[k] for s in templates for k in ("parent", "parentKey") if s.get(k)]
    return len(conds) == 2 and len(alert) == 1 and alert[0].get("parentKey") in {c["next"][0] for c in conds} \
        and all(r in ids for r in refs)


def apply_account(a: Agency, d, do: bool) -> int:
    loc = load(d / "location.json", {})["id"]
    name = load(d / "location.json", {}).get("name")
    flows = {w["name"]: w for w in a.workflows(loc)}
    forms = {f["name"]: f.get("_id") or f.get("id") for f in a.forms(loc)}
    stamp = time.strftime("%Y%m%d-%H%M%S")
    bdir = ROOT / "backup" / d.name
    bdir.mkdir(parents=True, exist_ok=True)
    bad = 0
    print(f"== {name}")

    def backup(wid: str, live: dict) -> None:
        trs = [t for t in a.triggers(loc, wid) if not t.get("deleted")]
        (bdir / f"workflow-{wid}-{stamp}.json").write_text(json.dumps({"workflow": live, "triggers": trs}))

    users = []
    for wname in GUARDED:
        wid = flows[wname]["id"]
        live = a.workflow(loc, wid)
        tpl = live["workflowData"]["templates"]
        users = users or next(s for s in tpl if is_alert(s))["attributes"]["sms"]["selectedUser"]
        if any(s.get("name") == GUARD_NAME for s in tpl):
            print(f"   {wname}: já filtrado")
            continue
        new = guard(tpl)
        print(f"   {wname} [{live['status']}]: {' → '.join(s['type'] for s in tpl)}  ⇒  guard + re-check antes do alerta")
        if not do:
            continue
        backup(wid, live)
        put_workflow(a, loc, wid, live, new)
        retarget(a, loc, wid, new[0]["id"])
        time.sleep(4)
        after = a.workflow(loc, wid)
        ok = check(after["workflowData"]["templates"]) and after["status"] == live["status"]
        bad += not ok
        print(f"      {'✓' if ok else '✗ VERIFICAR'} {after['status']} · {len(after['workflowData']['templates'])} passos")

    for wname, fname in FORM_ROUTE.items():
        wid, fid = flows[wname]["id"], forms[fname]
        trs = [t for t in a.triggers(loc, wid) if not t.get("deleted")]
        if any(fid in (c.get("value") or []) for t in trs for c in t["conditions"]):
            print(f"   {wname}: já escuta {fname}")
            continue
        print(f"   {wname}: + gatilho Form Submitted = {fname} ({fid})")
        if not do:
            continue
        live = a.workflow(loc, wid)
        backup(wid, live)
        body = {"type": "form_submission", "name": "Form Submitted", "masterType": "highlevel", "schedule_config": {},
                "conditions": [{"operator": "is-any-of", "field": "form.id", "value": [fid], "title": "Form is",
                                "type": "string"}], **link(loc, wid),
                "targetActionId": live["workflowData"]["templates"][0]["id"]}
        res = a.call("POST", BACKEND, f"/workflow/{loc}/trigger", body=body)
        a.call("PUT", BACKEND, f"/workflow/{loc}/trigger/{res['id']}", body={**body, "id": res["id"]})
        time.sleep(3)
        ok = any(fid in (c.get("value") or []) for t in a.triggers(loc, wid) if not t.get("deleted") for c in t["conditions"])
        bad += not ok
        print(f"      {'✓' if ok else '✗ VERIFICAR'} gatilho {res['id']}")

    for wname in OWNER_FIX:
        wid = flows[wname]["id"]
        live = a.workflow(loc, wid)
        tpl = json.loads(json.dumps(live["workflowData"]["templates"]))
        steps = [s for s in tpl if s["type"] == "internal_notification" and s["attributes"].get("type") == "sms"
                 and s["attributes"]["sms"].get("userType") == "assign"]
        if not steps:
            print(f"   {wname}: alerta já tem destinatário")
            continue
        print(f"   {wname}: alerta 'contact owner' (vazio) → {len(users)} usuários dos outros NEW LEAD")
        if not do:
            continue
        backup(wid, live)
        for s in steps:
            sms = s["attributes"]["sms"]
            sms.pop("assignedOwners", None)
            sms.update(userType="user", selectedUser=users)
            s.pop("incompleteData", None)
        put_workflow(a, loc, wid, live, tpl)
        time.sleep(4)
        after = a.workflow(loc, wid)
        got = [s["attributes"]["sms"].get("selectedUser") for s in after["workflowData"]["templates"]
               if s["id"] in {x["id"] for x in steps}]
        ok = all(g == users for g in got) and after["status"] == live["status"]
        bad += not ok
        print(f"      {'✓' if ok else '✗ VERIFICAR'} {after['status']}")
    return bad


def run_test(a: Agency) -> int:
    """Same guard on a throwaway workflow in Test Snapshot; tags stand in for the alert text."""
    loc = TEST_LOC
    go, mark_a, mark_alert = "guard test go", "guard test a", "guard test alert"
    for tag in (go, mark_a, mark_alert, *SKIP):
        try:
            a.call("POST", BACKEND, f"/workflow/{loc}/tags/create", body={"tag": tag})
        except Exception:
            pass  # already exists
    res = a.call("POST", BACKEND, f"/workflow/{loc}", body={"name": "TMP guard test", "status": "draft"})
    wid = res.get("id") or res.get("_id")
    s1, s2, s3 = nid(), nid(), nid()
    chain = [{"id": s1, "order": 0, "name": "Add Tag", "type": "add_contact_tag", "next": s2,
              "attributes": {"tags": [mark_a], "type": "add_contact_tag"}},
             {"id": s2, "order": 1, "name": "Wait", "type": "wait", "cat": "", "next": s3, "parentKey": s1,
              "attributes": {"type": "time", "startAfter": {"type": "minutes", "value": 1, "when": "after"},
                             "name": "Wait", "cat": "", "isHybridAction": True, "hybridActionType": "wait",
                             "convertToMultipath": False, "transitions": []}},
             {"id": s3, "order": 2, "name": "Alert stand-in", "type": "add_contact_tag", "parentKey": s2,
              "attributes": {"tags": [mark_alert], "type": "add_contact_tag"}}]
    tpl = guard(chain, alert=lambda s: s["id"] == s3)
    a.call("PUT", BACKEND, f"/workflow/{loc}/{wid}", body={"name": "TMP guard test", "version": 1,
                                                           "status": "published", "workflowData": {"templates": tpl}})
    trig = {"type": "contact_tag", "name": "Contact Tag", "masterType": "highlevel", "schedule_config": {},
            "conditions": [{"operator": "index-of-true", "field": "tagsAdded", "value": go, "title": "Tag Added",
                            "type": "select", "id": "tag-added"}], **link(loc, wid), "targetActionId": tpl[0]["id"]}
    t = a.call("POST", BACKEND, f"/workflow/{loc}/trigger", body=trig)
    a.call("PUT", BACKEND, f"/workflow/{loc}/trigger/{t['id']}", body={**trig, "id": t["id"]})
    time.sleep(5)
    # lead → a + alert; spam → nothing; customer → nothing; lead marked spam during the wait → a, no alert
    cases = {"lead": ([], True, True), "spam": (["spam"], False, False),
             "customer": (["current customer"], False, False), "late spam": ([], True, False)}
    made = {}
    for key, (tags, _, _) in cases.items():
        c = a.call("POST", SERVICES, "/contacts/upsert", body={
            "locationId": loc, "firstName": "TEST guard", "lastName": key, "tags": tags,
            "email": f"guard-{key.replace(' ', '-')}@example.com"})
        made[key] = c["contact"]["id"]
    time.sleep(3)
    for cid in made.values():
        a.call("POST", SERVICES, f"/contacts/{cid}/tags", body={"tags": [go]})
    time.sleep(20)
    a.call("POST", SERVICES, f"/contacts/{made['late spam']}/tags", body={"tags": ["spam"]})

    def tags_of(key: str) -> list:
        return a.call("GET", SERVICES, f"/contacts/{made[key]}")["contact"].get("tags", [])

    for _ in range(16):  # the 1-minute wait runs on GHL's scheduler: give it up to 4 min
        time.sleep(15)
        if mark_alert in tags_of("lead"):
            break
    time.sleep(15)
    bad = 0
    for key, (_, want_a, want_alert) in cases.items():
        tags = tags_of(key)
        ok = (mark_a in tags) == want_a and (mark_alert in tags) == want_alert
        bad += not ok
        print(f"   {'✓' if ok else '✗'} {key}: a={mark_a in tags} alert={mark_alert in tags}")
    for cid in made.values():
        a.call("DELETE", SERVICES, f"/contacts/{cid}")
    try:
        a.call("DELETE", BACKEND, f"/workflow/{loc}/{wid}")
    except Exception as e:  # leave it as draft for manual deletion
        print(f"   apagar à mão: workflow TMP guard test ({wid}): {e}")
    return bad


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("mode", choices=["test", "plan", "apply"])
    parser.add_argument("--only", action="append")
    args = parser.parse_args()
    load_dotenv()
    a = Agency()
    if args.mode == "test":
        return 1 if run_test(a) else 0
    if not args.only:
        parser.error("--only is required for plan/apply")
    return 1 if sum(apply_account(a, d, args.mode == "apply") for d in location_dirs(args.only)) else 0


if __name__ == "__main__":
    raise SystemExit(main())
