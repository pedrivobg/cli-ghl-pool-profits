#!/usr/bin/env python3
"""Pool Duck: Lakewood Ranch lead workflows for the ad landing pages, mirrored from Wesley Chapel.

    set -a; . <poolduck.env>; set +a                        # Pool Duck agency token
    ./.venv/bin/python scripts/pd_lwr_workflows.py           # plan
    ./.venv/bin/python scripts/pd_lwr_workflows.py --apply

Copies the four WC workflows of folder "Google Ads (AdWords + LSA)" that handle the landing
pages (form fill + call in, Google + Facebook) into folder "Ad Landing Pages" of LWR:
- LWR form, pipeline/stage and alert recipients (Kenton Dashiell + Pool Duck Service);
- tags get "lakewood ranch" (location) on top of WC's source + contact method tags;
- messages name Pool Duck Lakewood Ranch;
- "Add to Google Ads" / "Meta Conversion API" are left out until LWR sends its own ad accounts;
- the call workflows stay draft without trigger until LWR has its Google/Facebook numbers; with a number
  in CALL_NUMBERS they get WC's trigger (Call Status: inbound, In phone number) and are published.

    ./.venv/bin/python scripts/pd_lwr_workflows.py --only "Google AdWords - Qualified Lead (Call In)" --apply
Step and trigger shapes are WC's own, so the GHL UI shows them as usual.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import uuid

from _common import ROOT, load_dotenv

from cli_anything.gohighlevel.utils.agency import BACKEND, Agency

LWR = "MosKIX4oux96vchwHZ5W"
FOLDER = "Ad Landing Pages"
PIPELINE, LEAD_STAGE = "bBmO8YBJXxiKgEJEN3Ol", "f6512503-5228-4e2e-a9e1-c1dd7e8f232e"
ALERT_USERS = ["Fpwm492Y2wyKFa0xJgVC", "DZkEc4SNZd1bAeBiT2LG"]  # Kenton Dashiell, Pool Duck Service
CALL_NUMBERS = {"Google AdWords - Qualified Lead (Call In)": "+19415415942"}  # bought by Val 19/10; FB: none yet
TAGS = ["new lead", "google adwords", "fb leads", "form fill", "call in", "lakewood ranch"]
ALERT = ("New Lead from {src} for Pool Duck Lakewood Ranch\n\nName: {{{{contact.name}}}}\nEmail: {{{{contact.email}}}}\n"
         "Phone: {{{{contact.phone}}}}\nCity: {{{{contact.city}}}}\nZip: {{{{contact.postal_code}}}}")
LEAD_SMS = ("Hi {{contact.first_name}}, this is Pool Duck in Lakewood Ranch. Got your request for pool service. "
            "We will call you in the next few minutes from this number. If now is bad, reply with a better time, "
            "and we will work around you.")
WAIT = {"type": "time", "startAfter": {"type": "minutes", "value": 0.2, "when": "after"}, "name": "Wait", "cat": "",
        "timePeriodInputMode": "standard", "unitInputMode": "standard", "isHybridAction": True,
        "hybridActionType": "wait", "convertToMultipath": False, "transitions": []}


def alert(src: str) -> dict:
    return {"type": "sms", "sms": {"body": ALERT.format(src=src), "selectedUser": ALERT_USERS, "userType": "user",
                                   "attachments": []}}


def opp(name: str, source: str) -> dict:
    return {"fields": [], "type": "create_opportunity", "pipeline_id": PIPELINE, "pipeline_stage_id": LEAD_STAGE,
            "opportunity_name": name, "opportunity_source": source, "monetary_value": "150.00",
            "opportunity_status": "open"}


# name → (status, form id for the trigger or None, steps as (type, step name, attributes))
WORKFLOWS = {
    "Google AdWords - Qualified Lead (Form Fill)": ("published", "L35gq3SnSDyoda4Kl9D4", [
        ("internal_notification", "Internal Notification", alert("AdWords")),
        ("add_contact_tag", "Add Tag", {"tags": ["new lead", "google adwords", "form fill", "lakewood ranch"]}),
        ("create_opportunity", "Create or update opportunity", opp("{{contact.name}}", "Google AdWords - Form Fill")),
    ]),
    "Facebook - Qualified Lead (Form Fill)": ("published", "331LWSK5w0JSbZFswx4q", [
        ("internal_notification", "Internal Notification", alert("Facebook")),
        ("add_contact_tag", "Add Tag", {"tags": ["new lead", "form fill", "fb leads", "lakewood ranch"]}),
        ("create_opportunity", "Create or update opportunity", opp("{{contact.name}}", "Facebook - Form Fill")),
        ("wait", "Wait", WAIT),
        ("sms", "SMS", {"body": LEAD_SMS, "attachments": []}),
    ]),
    "Google AdWords - Qualified Lead (Call In)": ("draft", None, [
        ("create_opportunity", "Create or update opportunity",
         opp("{{contact.name}} - {{contact.phone}}", "Google Adwords Call In")),
        ("add_contact_tag", "Add Tag", {"tags": ["google adwords", "new lead", "call in", "lakewood ranch"]}),
    ]),
    "Facebook - Qualified Lead (Call In)": ("draft", None, [
        ("add_contact_tag", "Add Tag", {"tags": ["new lead", "call in", "fb leads", "lakewood ranch"]}),
        ("create_opportunity", "Create or update opportunity",
         opp("{{contact.name}} - {{contact.phone}}", "FacebookCall In")),
    ]),
}


def chain(wid: str, steps: list) -> list[dict]:
    """Linear workflow: each step points to the next; WC ends every one with 'remove from this workflow'."""
    steps = steps + [("remove_from_workflow", "Remove from Workflow",
                      {"type": "remove_from_workflow", "workflow_id": [wid]})]
    ids = [str(uuid.uuid4()) for _ in steps]
    out = []
    for i, (kind, name, attrs) in enumerate(steps):
        s = {"id": ids[i], "order": i, "name": name, "type": kind, "attributes": json.loads(json.dumps(attrs))}
        if i:
            s["parentKey"] = ids[i - 1]
        if i + 1 < len(steps):
            s["next"] = ids[i + 1]
        out.append(s)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--only", action="append", help="workflow name (default: all four)")
    args = parser.parse_args()
    load_dotenv()
    a = Agency()
    bdir = ROOT / "backup" / "pool-duck-lakewood-ranch"
    bdir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")

    have_tags = {t["name"].lower() for t in a.tags(LWR)}
    for tag in TAGS:
        if tag not in have_tags:
            print(f"+ tag {tag!r}")
            if args.apply:
                a.call("POST", BACKEND, f"/workflow/{LWR}/tags/create", body={"tag": tag})

    folders = {v: k for k, v in a.folders(LWR).items()}
    parent = folders.get(FOLDER)
    if not parent:
        print(f"+ pasta de workflows {FOLDER!r}")
        if args.apply:
            res = a.call("POST", BACKEND, f"/workflow/{LWR}", body={"name": FOLDER, "type": "directory"})
            parent = res.get("id") or res.get("_id")

    existing = {w["name"]: w for w in a.workflows(LWR)}
    bad = 0
    for name, (status, form, steps) in WORKFLOWS.items():
        if args.only and name not in args.only:
            continue
        number = CALL_NUMBERS.get(name)
        status = "published" if number else status
        w = existing.get(name)
        print(f"{'=' if w else '+'} {name} [{status}]" + (f" ← form {form}" if form else f" ← ligação em {number}"
                                                          if number else " (sem gatilho: falta o número)"))
        if not args.apply:
            continue
        if w:
            live = a.workflow(LWR, w["id"])
            (bdir / f"workflow-{w['id']}-{stamp}.json").write_text(json.dumps(live, ensure_ascii=False))
            wid, version = w["id"], live.get("version", 1)
        else:
            res = a.call("POST", BACKEND, f"/workflow/{LWR}", body={"name": name, "parentId": parent, "status": "draft"})
            wid, version = res.get("id") or res.get("_id"), 1
        templates = chain(wid, steps)
        a.call("PUT", BACKEND, f"/workflow/{LWR}/{wid}", body={
            "name": name, "version": version, "status": status, "parentId": parent, "allowMultiple": True,
            "workflowData": {"templates": templates}})
        if form or number:
            conditions = [{"operator": "is-any-of", "field": "form.id", "value": [form], "title": "Form is",
                           "type": "string"}] if form else [  # WC's call trigger shape
                {"operator": "==", "field": "message.direction", "value": "inbound", "title": "Call direction",
                 "type": "select"},
                {"operator": "contains-any", "field": "inbound_number", "value": [number], "title": "In phone number",
                 "type": "multiselect", "id": "inbound-twilio-number"}]
            trig = {"type": "form_submission" if form else "call_status",
                    "name": "Form Submitted" if form else "Call Details", "masterType": "highlevel",
                    "conditions": conditions,
                    "actions": [{"workflow_id": wid, "type": "add_to_workflow"}], "schedule_config": {},
                    "workflowId": wid, "workflow_id": wid, "location_id": LWR, "targetActionId": templates[0]["id"]}
            current = [t for t in a.triggers(LWR, wid) if not t.get("deleted")]
            if current:
                (bdir / f"trigger-{current[0]['id']}-{stamp}.json").write_text(json.dumps(current[0]))
                a.call("PUT", BACKEND, f"/workflow/{LWR}/trigger/{current[0]['id']}", body={**trig, "id": current[0]["id"]})
            else:
                res = a.call("POST", BACKEND, f"/workflow/{LWR}/trigger", body=trig)
                if res.get("id"):
                    a.call("PUT", BACKEND, f"/workflow/{LWR}/trigger/{res['id']}", body={**trig, "id": res["id"]})
        # PUT returns before reads catch up
        for _ in range(5):
            time.sleep(3)
            after = a.workflow(LWR, wid)
            trs = [t for t in a.triggers(LWR, wid) if not t.get("deleted")]
            got = (after.get("workflowData") or {}).get("templates") or []
            ok = (after.get("status") == status and [s["type"] for s in got] == [s["type"] for s in templates]
                  and after.get("parentId") == parent
                  and (not (form or number) or (len(trs) == 1 and trs[0]["conditions"][-1]["value"] == [form or number]
                                                and trs[0].get("active") == (status == "published"))))
            if ok:
                break
        bad += not ok
        print(f"   {'✓' if ok else '✗ VERIFICAR'} {after.get('status')} · {' → '.join(s['type'] for s in got)}"
              f" · allowMultiple={after.get('allowMultiple')} · gatilhos={[(t['type'], t.get('active')) for t in trs]}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
