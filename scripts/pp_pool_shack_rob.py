#!/usr/bin/env python3
"""The Pool Shack: Rob's changes to the lead and new-customer automations (Basecamp "Automation Snapshots",
19/10; Frank 20/10). Structure here, texts in config/pool_shack_wording.json (scripts/pp_wording.py).

    ./.venv/bin/python scripts/pp_pool_shack_rob.py --only "Test Snapshot"              # plan
    ./.venv/bin/python scripts/pp_pool_shack_rob.py --only "Test Snapshot" --apply      # test account first
    ./.venv/bin/python scripts/pp_pool_shack_rob.py --only "The Pool Shack" --apply
    ./.venv/bin/python scripts/pp_wording.py --config config/pool_shack_wording.json --apply

- Missed New Lead SMS: waits for a reply for 1 day (was 30 min), then business hours → SMS 2 ("next business day").
- Quote Sent: no automatic move to Lost at the end (big projects take time to decide); SMS 1 and 2 in business hours.
- No Response: SMS 1, 2 and 3 in business hours.
- Won Stage: the Repairs / Installs and Construction branches get their own welcome e-mail + SMS (the weekly branch
  keeps its own). Texts from the wording config.
- "Stop Follow-ups" (new, published, 02 Lead Nurturing): a reply on any channel, or the card moving to In
  Communication, Quote Sent, No Response, a Won stage, Recurring Customer or Lost, takes the contact out of the
  sequences that no longer apply (Missed New Lead SMS, No Response, Quote Sent, Lost Stage). One if/else branch
  per trigger: Quote Sent keeps Quote Sent, No Response keeps No Response, Lost keeps Lost; everything else stops
  all four (after 1 minute, so a reply still runs the sequence's own "replied" branch first).
Business hours = Mon–Fri 09:00–17:00 in the account's time zone (the window Lost/Won/In Communication already use).
Idempotent (steps it adds have fixed names); GET + backup before every write. --extra-target <workflow name>: also
remove from that workflow in the "stop all" branch (used only by the test on Test Snapshot).
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
import time
import uuid

from _common import ROOT, load_dotenv, slugify
from pp_ivr import IS_OPS, NEST
from pp_wording import wanted

from cli_anything.gohighlevel.utils.agency import BACKEND, SERVICES, Agency, match_location

MISSED, QUOTE, NORESP, LOST, WON = ("Missed New Lead - Initial SMS Follow-up", "Quote Sent Follow-up",
                                    "No Response Follow-up", "Lost Stage", "Won Stage")
STOP = "Stop Follow-ups"
HOURS_NAME = "Business hours (Mon-Fri 9-5)"
WINDOW = {"window": {"condition": "when", "days": [1, 2, 3, 4, 5], "start": "09:00", "end": "17:00"},
          "windowCondition": {"field": "", "operator": "", "value": ""}}
WORDING = ROOT / "config" / "pool_shack_wording.json"
WON_BRANCHES = {"Repairs / Installs": "Repairs / Installs", "Construction": "Construction / Remodeling"}
STOP_STAGES = {  # stage name (as in the snapshot's "Pool Leads") → what entering it stops
    "💬 In Communication": "all", "💰 Quote Sent": "quote", "No Response - Follow Up": "noresp",
    "🏆 Won - Weekly Pool Service": "all", "🏆 Won - One Time Repair or Install": "all",
    "🏆 Won - Pool Construction or Remodeling": "all", "🔄 Recurring Customer": "all", "❌ Lost": "lost"}
KEEP = {"quote": QUOTE, "noresp": NORESP, "lost": LOST}  # the sequence each stage starts is not stopped


def nid() -> str:
    return str(uuid.uuid4())


def by_name(tpl: list[dict], name: str) -> dict:
    found = [s for s in tpl if s.get("name") == name]
    if len(found) != 1:
        raise SystemExit(f"passo {name!r}: {len(found)} encontrados")
    return found[0]


def hours_wait() -> dict:
    return {"id": nid(), "type": "wait", "name": HOURS_NAME, "cat": "",
            "attributes": {"type": "time", "startAfter": {"type": "minutes", "value": 1, "when": "after"},
                           "name": HOURS_NAME, "cat": "", "isHybridAction": True, "hybridActionType": "wait",
                           "convertToMultipath": False, "transitions": [], **copy.deepcopy(WINDOW)}}


def insert_before(tpl: list[dict], target: dict, node: dict) -> bool:
    """Put `node` right before `target` in its chain. False if a business-hours wait is already there."""
    pk = target.get("parentKey")
    prev = next((s for s in tpl if s["id"] == pk), None)
    if prev and prev.get("name") == node["name"]:
        return False
    node["order"] = target.get("order", 0)
    if pk:
        node["parentKey"] = pk
    if target.get("parent"):
        node["parent"] = target["parent"]
    node["next"] = target["id"]
    if prev is not None:
        if isinstance(prev.get("next"), list):
            raise SystemExit(f"{target['name']}: anterior é multi-path")
        prev["next"] = node["id"]
    target["parentKey"] = node["id"]
    s, n = target, target.get("order", 0) + 1
    while s is not None:  # renumber the rest of the chain
        s["order"] = n
        nxt = s.get("next")
        s = next((x for x in tpl if x["id"] == nxt), None) if isinstance(nxt, str) else None
        n += 1
    tpl.insert(tpl.index(target), node)
    return True


def windowed(step: dict) -> bool:
    if step["attributes"].get("window") == WINDOW["window"]:
        return False
    step["attributes"].update(copy.deepcopy(WINDOW))
    return True


def chain_end(tpl: list[dict], start: dict) -> dict:
    s = start
    while isinstance(s.get("next"), str):
        s = next(x for x in tpl if x["id"] == s["next"])
    return s


# ── per workflow ─────────────────────────────────────────────────────────

def missed(tpl: list[dict]) -> list[str]:
    done = []
    wait = next(s for s in tpl if s["type"] == "wait" and s["attributes"].get("type") == "reply")
    if wait["attributes"]["startAfter"] != {"type": "days", "value": 1, "when": "after"}:
        wait["attributes"]["startAfter"] = {"type": "days", "value": 1, "when": "after"}
        wait["attributes"]["name"] = "Wait 1 day"
        done.append("espera por resposta 30 min → 1 dia")
    if insert_before(tpl, by_name(tpl, "SMS 2"), hours_wait()):
        done.append("SMS 2 em horário comercial")
    return done


def quote(tpl: list[dict]) -> list[str]:
    done = []
    first = next(s for s in tpl if not s.get("parentKey"))
    if first["type"] == "wait" and windowed(first):
        done.append("SMS 1 em horário comercial")
    if insert_before(tpl, by_name(tpl, "SMS 2"), hours_wait()):
        done.append("SMS 2 em horário comercial")
    lost = [s for s in tpl if s["name"] in ("Add Tag lost lead", "Move to Lost")]
    if lost:
        parent = lost[0]["parent"]
        for s in lost:
            tpl.remove(s)
        branch = next(s for s in tpl if s["id"] == parent)
        branch.pop("next", None)
        done.append("sem ir para Lost sozinho no fim")
    return done


def noresp(tpl: list[dict]) -> list[str]:
    done = []
    first = next(s for s in tpl if not s.get("parentKey"))
    if first["type"] == "wait" and windowed(first):
        done.append("SMS 1 em horário comercial")
    for name in ("SMS 2", "SMS 3"):
        if insert_before(tpl, by_name(tpl, name), hours_wait()):
            done.append(f"{name} em horário comercial")
    return done


def won(tpl: list[dict], texts: dict[str, dict]) -> list[str]:
    done = []
    weekly_email = by_name(tpl, "Welcome Email")
    for branch, label in WON_BRANCHES.items():
        if any(s["name"] == f"Welcome Email - {label}" for s in tpl):
            continue
        head = next(s for s in tpl if s.get("name") == branch and s.get("nodeType") == "branch-yes")
        end = chain_end(tpl, next(s for s in tpl if s["id"] == head["next"]))
        email = {"id": nid(), "type": "email", "name": f"Welcome Email - {label}",
                 "attributes": {k: copy.deepcopy(v) for k, v in weekly_email["attributes"].items()
                                if k not in ("template_id", "templatesource", "templateCreationMode", "trackingOptions",
                                             "createdAt", "updatedAt")}}
        email["attributes"].update(texts[f"Welcome Email - {label}"])
        wait = {"id": nid(), "type": "wait", "name": "Wait 2 minutes", "cat": "",
                "attributes": {"type": "time", "startAfter": {"type": "minutes", "value": 2, "when": "after"},
                               "name": "Wait 2 minutes", "cat": "", "isHybridAction": True, "hybridActionType": "wait",
                               "convertToMultipath": False, "transitions": [], **copy.deepcopy(WINDOW)}}
        sms = {"id": nid(), "type": "sms", "name": f"Welcome SMS - {label}",
               "attributes": {"body": texts[f"Welcome SMS - {label}"]["body"], "attachments": []}}
        prev, order = end, end.get("order", 0) + 1
        for node in (email, wait, sms):
            node.update({"order": order, "parentKey": prev["id"], "parent": head["id"]})
            prev["next"] = node["id"]
            prev, order = node, order + 1
        tpl.extend([email, wait, sms])
        done.append(f"boas-vindas (e-mail + SMS) no ramo {branch}")
    return done


def stop_flow(ids: dict[str, str], extra: str | None) -> tuple[list[dict], dict[str, str]]:
    """Steps of "Stop Follow-ups" with placeholders TRIGGER:<kind> for the if/else, filled after the triggers exist."""
    every = [ids[MISSED], ids[NORESP], ids[QUOTE], ids[LOST]] + ([ids[extra]] if extra else [])
    remove = lambda wids, name: {"id": nid(), "type": "remove_from_workflow", "name": name,  # noqa: E731
                                 "attributes": {"type": "remove_from_workflow", "workflow_id": wids}}
    cond, branches, steps = nid(), [], []
    plan = {kind: [w for w in every[:4] if w != ids[keep]] for kind, keep in KEEP.items()}
    for kind, label in (("quote", "Quote Sent"), ("noresp", "No Response"), ("lost", "Lost")):
        bid = nid()
        branches.append({"id": bid, "name": label, "operator": "and", "showErrors": False,
                         "branchNameError": "Branch name cannot be empty!",
                         "segments": [{"__segmentId": nid(), "operator": "and", "conditions": [{
                             "conditionType": "trigger", "conditionSubType": "trigger", "conditionOperator": "==",
                             "conditionValue": f"TRIGGER:{kind}", "__conditionId": nid(), "ifElseNodeId": "",
                             "__customFieldType__": "standard", "isWait": False, "nestedDropdownTypes": NEST,
                             "allowIsOperatorTypes": IS_OPS}]}]})
        r = remove(plan[kind], f"Stop the other follow-ups ({label})")
        r.update({"order": 0, "parent": bid, "parentKey": bid})
        steps.append(({"id": bid, "name": label, "type": "if_else", "parent": cond, "parentKey": cond,
                       "cat": "conditions", "comments": [], "nodeType": "branch-yes", "next": r["id"], "order": 1,
                       "attributes": {"if": False, "conditionName": "Condition", "operator": "and", "branches": []}}, r))
    none_id, wait, rall = nid(), {"id": nid(), "type": "wait", "name": "Wait 1 minute", "cat": "", "attributes": {
        "type": "time", "startAfter": {"type": "minutes", "value": 1, "when": "after"}, "name": "Wait 1 minute",
        "cat": "", "isHybridAction": True, "hybridActionType": "wait", "convertToMultipath": False,
        "transitions": []}}, remove(every, "Stop all follow-ups")
    wait.update({"order": 0, "parent": none_id, "parentKey": none_id, "next": rall["id"]})
    rall.update({"order": 1, "parent": none_id, "parentKey": wait["id"]})
    head = {"id": cond, "order": 0, "name": "Which trigger?", "type": "if_else", "cat": "conditions",
            "comments": [], "nodeType": "condition-node", "next": [b["id"] for b in branches] + [none_id],
            "attributes": {"currentRecipeType": "CUSTOM", "operator": "and", "if": True, "conditionName": "Condition",
                           "version": 2, "noneBranchName": "Reply, In Communication, Won, Recurring",
                           "branches": branches}}
    tpl = [head]
    for branch, r in steps:
        tpl += [branch, r]
    tpl += [{"id": none_id, "name": "Reply, In Communication, Won, Recurring", "type": "if_else", "parent": cond,
             "parentKey": cond, "cat": "conditions", "comments": [], "nodeType": "branch-no", "order": 1,
             "next": wait["id"], "attributes": {"else": True}}, wait, rall]
    for b, (branch, _) in zip(branches, steps):
        branch["sibling"] = [x["id"] for x in branches if x is not b] + [none_id]
    return tpl, {"head": cond}


def put(a: Agency, loc: str, live: dict, tpl: list[dict], status: str | None = None) -> None:
    a.call("PUT", BACKEND, f"/workflow/{loc}/{live['id']}", body={
        "name": live["name"], "version": live.get("version", 1), "status": status or live["status"],
        "parentId": live.get("parentId"), "workflowData": {"templates": tpl}})


def ensure_stop(a: Agency, loc: str, flows: dict[str, dict], extra: str | None, apply: bool, bdir) -> str:
    pipes = a.call("GET", SERVICES, "/opportunities/pipelines",
                   params={"locationId": loc})["pipelines"]
    pipe = next(p for p in pipes if p["name"] == "Pool Leads")
    stage = {s["name"]: s["id"] for s in pipe["stages"]}
    missing = [n for n in STOP_STAGES if n not in stage]
    if missing:
        raise SystemExit(f"etapas faltando em Pool Leads: {missing}")
    ids = {name: flows[name]["id"] for name in (MISSED, QUOTE, NORESP, LOST) + ((extra,) if extra else ())}
    tpl, _ = stop_flow(ids, extra)
    if not apply:
        return "plano"
    folders = {v: k for k, v in a.folders(loc).items()}
    parent = folders.get("02 Lead Nurturing")
    if STOP in flows:
        wid = flows[STOP]["id"]
        old = a.workflow(loc, wid)
        trs = [t for t in a.triggers(loc, wid) if not t.get("deleted")]
        (bdir / f"workflow-{wid}-{time.strftime('%Y%m%d-%H%M%S')}.json").write_text(
            json.dumps({"workflow": old, "triggers": trs}))
        for t in trs:  # rebuilt from scratch: the if/else must point at these trigger ids
            a.call("DELETE", BACKEND, f"/workflow/{loc}/trigger/{t['id']}")
    else:
        res = a.call("POST", BACKEND, f"/workflow/{loc}", body={"name": STOP, "parentId": parent, "status": "draft"})
        wid = res.get("id") or res.get("_id")
    base = {"masterType": "highlevel", "schedule_config": {}, "workflowId": wid, "workflow_id": wid,
            "location_id": loc, "actions": [{"workflow_id": wid, "type": "add_to_workflow"}],
            "targetActionId": tpl[0]["id"]}
    trig_ids: dict[str, str] = {}

    def make(body: dict) -> str:
        t = a.call("POST", BACKEND, f"/workflow/{loc}/trigger", body={**base, **body})
        a.call("PUT", BACKEND, f"/workflow/{loc}/trigger/{t['id']}", body={**base, **body, "id": t["id"]})
        return t["id"]

    make({"type": "customer_reply", "name": "Customer Replied", "conditions": []})
    for name, kind in STOP_STAGES.items():
        tid = make({"type": "pipeline_stage_updated", "name": f"Stage: {name}", "conditions": [
            {"operator": "==", "field": "opportunity.pipelineId", "value": pipe["id"], "title": "In pipeline",
             "type": "select"},
            {"operator": "==", "field": "opportunity.pipelineStageId", "value": stage[name], "title": "Pipeline stage",
             "type": "select"}]})
        if kind != "all":
            trig_ids[kind] = tid
    raw = json.dumps(tpl)
    for kind, tid in trig_ids.items():
        raw = raw.replace(f"TRIGGER:{kind}", tid)
    live = a.workflow(loc, wid)
    a.call("PUT", BACKEND, f"/workflow/{loc}/{wid}", body={
        "name": STOP, "version": live.get("version", 1), "status": "published", "parentId": parent,
        "allowMultiple": True, "workflowData": {"templates": json.loads(raw)}})
    return wid


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--only", required=True)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--extra-target", help="test only: also stopped by the 'stop all' branch")
    args = parser.parse_args()
    load_dotenv()
    a = Agency()
    loc = match_location(a.locations(), args.only)
    cfg = json.loads(WORDING.read_text())
    texts = {m["step"]: wanted(m, cfg["placeholders"]) for m in cfg["messages"] if m["workflow"] == WON}
    flows = {w["name"]: w for w in a.workflows(loc["id"])}
    bdir = ROOT / "backup" / slugify(loc["name"])
    bdir.mkdir(parents=True, exist_ok=True)
    print(f"== {loc['name']}")
    for name, fn in ((MISSED, missed), (QUOTE, quote), (NORESP, noresp), (WON, lambda t: won(t, texts))):
        live = a.workflow(loc["id"], flows[name]["id"])
        tpl = copy.deepcopy(live["workflowData"]["templates"])
        done = fn(tpl)
        print(f"   {name}: {', '.join(done) or 'já está'}")
        if done and args.apply:
            (bdir / f"workflow-{live['id']}-{time.strftime('%Y%m%d-%H%M%S')}.json").write_text(json.dumps(live))
            put(a, loc["id"], live, tpl)
            time.sleep(2)
            after = a.workflow(loc["id"], live["id"])
            got = after["workflowData"]["templates"]
            ok = len(got) == len(tpl) and after["status"] == live["status"]
            print(f"      {'✓' if ok else '✗'} {len(got)} passos · {after['status']}")
    wid = ensure_stop(a, loc["id"], flows, args.extra_target, args.apply, bdir)
    if args.apply:
        time.sleep(3)
        after = a.workflow(loc["id"], wid)
        trs = [t for t in a.triggers(loc["id"], wid) if not t.get("deleted")]
        print(f"   {STOP}: {after['status']} · {len(after['workflowData']['templates'])} passos · "
              f"{len(trs)} gatilhos ({sum(bool(t.get('active')) for t in trs)} ativos) · {wid}")
    else:
        print(f"   {STOP}: {'atualizar' if STOP in flows else 'criar'} (1 resposta + {len(STOP_STAGES)} etapas)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
