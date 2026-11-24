#!/usr/bin/env python3
"""Poolheads: Thanksgiving 2026 call routing + text (Frank/Felipe, ClickUp 24/11). Account time zone America/Chicago.

    python3 scripts/ph_thanksgiving.py plan
    python3 scripts/ph_thanksgiving.py on        # insert the holiday branches (GET + backup first)
    python3 scripts/ph_thanksgiving.py notest    # drop only the "ZZ TEST" branches (after the live test)
    python3 scripts/ph_thanksgiving.py off       # remove everything named "TG26" (run on 11/28)

What "on" does (nothing else is touched; existing node ids, stepIndex values and statuses are kept):
- "Business Hours Call Routing" (IVR of all 4 lines): right after "Recording notice" an if/else "TG26 Thanksgiving":
    Thu 11/26 and Fri 11/27 (month == 10 because GHL counts months from 0, tested) → tag "missed call" → holiday voicemail
    Wed 11/25 from 12:00 → tag "missed call" → regular voicemail (before 9:00 the existing "Closed" branch already does it)
    ZZ TEST branch (contact has tag "zz tg test") → same as Thu, so the holiday path can be tested today
    else → the existing "Check Business Hours" chain, unchanged.
- "Missed New Lead - Initial SMS Follow-up" (trigger: tag "missed call"): if/else "TG26 Thanksgiving SMS" first:
    Thu 11/26 / Fri 11/27 / ZZ TEST tag → the holiday text only (no regular missed-call text = no duplicate)
    else → the existing chain (SMS 1 → wait → ...), unchanged.
- "After Hours Message" (incoming texts): the same if/else first, so texts on Thu/Fri get the holiday text (on weekdays
  9-5 the flow normally sends nothing) and no after-hours message on top of it.
Tested 24/11 on the Test Snapshot: date_time / day_month == "24" true, "23" false; month == "10" true in November.
"""
from __future__ import annotations

import copy
import json
import sys
import time
import uuid

from _common import ROOT, load_dotenv

load_dotenv()
from cli_anything.gohighlevel.utils.agency import BACKEND, Agency  # noqa: E402

LOC = "PeUynYCMm8e6PJMy785O"
IVR, MISSED = "4bdf1654-e687-4f8d-9629-5b34c5f82d91", "e58cc40e-910f-4a47-bd2c-99793217f294"
AFTER = "90cc5b1e-fe1c-4939-bcf3-412b4bbcea19"  # "After Hours Message" (customer_reply, texts)
TEST_TAG = "zz tg test"
VM_TEXT = ("Thank you for calling Poolheads! Our office is currently closed for Thanksgiving break. Please leave your name, "
           "phone number, and a brief message, and we'll get back to you when we return. Happy Thanksgiving!")
SMS_TEXT = ("Thank you for contacting Poolheads! Our team is currently away for Thanksgiving break. If you have an urgent "
            "pool concern, please visit our Holiday Pool Care page for assistance: https://www.poolheadscare.com/holidays\n"
            "We'll get back to you as soon as we return. Happy Thanksgiving!")
BDIR = ROOT / "backup" / "poolheads"
NEST = ["inboundWebhookRequest", "sheet", "datetime_formatter", "custom_webhook", "array_functions", "ivr_gather",
        "ivr_connect_call", "custom_code", "ai_agent", "task-notification", "event"]
IS_OPS = ["contact_reply", "inboundWebhookRequest", "custom_webhook", "custom_code", "ai_agent", "contact_detail",
          "array_functions", "appointment", "service_booking", "rental_booking"]


def nid() -> str:
    return str(uuid.uuid4())


def cond(ctype: str, sub: str, op: str, val) -> dict:
    return {"conditionType": ctype, "conditionSubType": sub, "conditionOperator": op, "conditionValue": val,
            "__conditionId": nid(), "ifElseNodeId": "", "__customFieldType__": "standard", "isWait": False,
            "nestedDropdownTypes": NEST, "allowIsOperatorTypes": IS_OPS}


def day(d: str) -> list:
    return [cond("date_time", "month", "==", "10"), cond("date_time", "day_month", "==", d)]


def ifelse(name: str, parent_key: str, branches: list[tuple[str, list]], else_name: str):
    """branches: [(name, conditions)] → (nodes, [branch ids], else id)."""
    cid, bids, eid = nid(), [nid() for _ in branches], nid()
    main = {"id": cid, "order": 1, "name": name, "type": "if_else", "cat": "conditions", "comments": [],
            "nodeType": "condition-node", "next": bids + [eid], "parentKey": parent_key,
            "attributes": {"currentRecipeType": "CUSTOM", "operator": "and", "if": True, "conditionName": name,
                           "version": 2, "noneBranchName": else_name,
                           "branches": [{"id": b, "name": n, "operator": "and", "showErrors": False,
                                         "branchNameError": "Branch name cannot be empty!",
                                         "segments": [{"__segmentId": nid(), "operator": "and", "conditions": c}]}
                                        for b, (n, c) in zip(bids, branches)]}}
    nodes = [main]
    for b, (n, _) in zip(bids, branches):
        nodes.append({"id": b, "name": n, "type": "if_else", "parent": cid, "parentKey": cid, "cat": "conditions",
                      "comments": [], "nodeType": "branch-yes", "sibling": [x for x in bids + [eid] if x != b],
                      "order": 2, "attributes": {"if": False, "conditionName": "Condition", "operator": "and",
                                                 "branches": []}})
    nodes.append({"id": eid, "name": else_name, "type": "if_else", "parent": cid, "parentKey": cid, "cat": "conditions",
                  "comments": [], "nodeType": "branch-no", "sibling": bids, "order": 2, "attributes": {"else": True}})
    return nodes, bids, eid


def branches_ivr() -> list:
    return [("TG26 Thu 11/26 closed", day("26")), ("TG26 Fri 11/27 closed", day("27")),
            ("TG26 Wed 11/25 after 12pm", day("25") + [cond("date_time", "quarter_hour", ">=", "1200")]),
            ("TG26 ZZ TEST", [cond("contact_detail", "tags", "index-of-true", [TEST_TAG])])]


def on_ivr(tpl: list) -> list:
    if any((t.get("name") or "").startswith("TG26") for t in tpl):
        raise SystemExit("IVR already has TG26 nodes")
    notice = next(t for t in tpl if t["type"] == "ivr_say" and not t.get("parent"))
    first = next(t for t in tpl if t["id"] == notice["next"])
    reg_vm = next(t for t in tpl if t["type"] == "ivr_collect_voicemail")
    assert reg_vm["attributes"]["sayPlayAttributes"].get("audioUrl"), "regular greeting missing — stop"
    nodes, bids, eid = ifelse("TG26 Thanksgiving (remove 11/28)", notice["id"], branches_ivr(), "TG26 Normal days")
    nodes[0]["name"] = nodes[0]["attributes"]["conditionName"] = "TG26 Thanksgiving (remove 11/28)"
    notice["next"] = nodes[0]["id"]
    first["parent"] = first["parentKey"] = eid
    nodes[-1]["next"] = first["id"]
    used = max(int(t.get("stepIndex") or 0) for t in tpl)
    for i, b in enumerate(bids):
        tag, vm = nid(), nid()
        holiday = not nodes[1 + i]["name"].startswith("TG26 Wed")
        nodes[1 + i]["next"] = tag
        sp = copy.deepcopy(reg_vm["attributes"]["sayPlayAttributes"])
        if holiday:
            sp.update(widgetType="say", message=VM_TEXT)
        attrs = copy.deepcopy(reg_vm["attributes"])
        attrs["sayPlayAttributes"] = sp
        attrs["isSayPlayOn"] = True
        used += 1
        nodes += [{"id": tag, "name": "TG26 Tag missed call", "type": "add_contact_tag", "order": 0, "parent": b,
                   "parentKey": b, "next": vm, "attributes": {"tags": ["missed call"], "type": "add_contact_tag"}},
                  {"id": vm, "name": "TG26 Holiday voicemail" if holiday else "TG26 Voicemail", "order": 1,
                   "type": "ivr_collect_voicemail", "stepIndex": used, "parent": b, "parentKey": tag,
                   "attributes": attrs}]
    return tpl + nodes


def on_missed(tpl: list) -> list:
    if any((t.get("name") or "").startswith("TG26") for t in tpl):
        raise SystemExit("workflow already has TG26 nodes")
    first = next(t for t in tpl if not t.get("parent") and not t.get("parentKey"))
    br = [("TG26 Thu 11/26", day("26")), ("TG26 Fri 11/27", day("27")),
          ("TG26 ZZ TEST", [cond("contact_detail", "tags", "index-of-true", [TEST_TAG])])]
    nodes, bids, eid = ifelse("TG26 Thanksgiving SMS (remove 11/28)", "", br, "TG26 Normal days")
    nodes[0].pop("parentKey")
    nodes[0]["order"] = 0
    first["parent"] = first["parentKey"] = eid
    nodes[-1]["next"] = first["id"]
    for i, b in enumerate(bids):
        s = nid()
        nodes[1 + i]["next"] = s
        nodes.append({"id": s, "name": "TG26 Holiday SMS", "type": "sms", "order": 0, "parent": b, "parentKey": b,
                      "attributes": {"body": SMS_TEXT, "attachments": []}})
    return nodes + tpl


def off(tpl: list, only_test: bool = False) -> list:
    """Remove every TG26 node (or only the ZZ TEST branch) and reconnect the original chain."""
    by = {t["id"]: t for t in tpl}
    main = next((t for t in tpl if (t.get("name") or "").startswith("TG26 Thanksgiving")), None)
    if not main:
        return tpl
    if only_test:
        test = next((by[b] for b in main["next"] if by[b]["name"] == "TG26 ZZ TEST"), None)
        if not test:
            return tpl
        drop, n = {test["id"]}, test.get("next")
        while n:
            drop.add(n)
            n = by[n].get("next")
        main["next"] = [x for x in main["next"] if x != test["id"]]
        main["attributes"]["branches"] = [b for b in main["attributes"]["branches"] if b["id"] != test["id"]]
        for b in main["next"]:
            by[b]["sibling"] = [x for x in by[b].get("sibling", []) if x != test["id"]]
        return [t for t in tpl if t["id"] not in drop]
    else_node = next(by[b] for b in main["next"] if by[b]["attributes"].get("else"))
    original = by[else_node["next"]]
    original.pop("parent", None)
    if main.get("parentKey"):
        by[main["parentKey"]]["next"] = original["id"]
        original["parentKey"] = main["parentKey"]
    else:
        original.pop("parentKey", None)
    return [t for t in tpl if not (t.get("name") or "").startswith("TG26")]


def save(a: Agency, wid: str, live: dict, tpl: list) -> None:
    a.call("PUT", BACKEND, f"/workflow/{LOC}/{wid}", body={"name": live["name"], "version": live.get("version", 1),
                                                         "status": live["status"], "parentId": live.get("parentId"),
                                                         "workflowData": {"templates": tpl}})


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else "plan"
    only = {x for x in sys.argv[2:] if x}  # optional workflow ids
    a = Agency()
    BDIR.mkdir(parents=True, exist_ok=True)
    for wid, fn in ((IVR, on_ivr), (MISSED, on_missed), (AFTER, on_missed)):
        if only and wid not in only:
            continue
        live = a.workflow(LOC, wid)
        tpl = copy.deepcopy(live["workflowData"]["templates"])
        if mode == "plan":
            new = fn(copy.deepcopy(tpl))
            print(live["name"], live["status"], len(tpl), "→", len(new), "nodes")
            for t in new:
                if (t.get("name") or "").startswith("TG26"):
                    print("   +", t["type"], t["name"])
            continue
        (BDIR / f"workflow-{wid}-{time.strftime('%Y%m%d-%H%M%S')}.json").write_text(json.dumps(live))
        new = fn(tpl) if mode == "on" else off(tpl, only_test=(mode == "notest"))
        save(a, wid, live, new)
        time.sleep(5)
        now = a.workflow(LOC, wid)
        names = [t.get("name") for t in now["workflowData"]["templates"]]
        print(now["name"], now["status"], len(names), "nodes; TG26:", sum(1 for n in names if (n or "").startswith("TG26")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
