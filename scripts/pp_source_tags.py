#!/usr/bin/env python3
"""Lead source tags (Val, 19/10): Google Ads tags in Wrigley's, Google Lead Form workflow in Reign /
Damon's / Simple, source tags by line in Sunwave and Passion. Val, 22/10: Google Lead Form workflow also in
Wrigley's, BluVantage, Precision Pools and Pool Duck Wesley Chapel (Pool Duck agency: load poolduck.env).

    ./.venv/bin/python scripts/pp_source_tags.py --only "Wrigley"            # plan
    ./.venv/bin/python scripts/pp_source_tags.py --only "Wrigley" --apply

Per account (ACCOUNTS):
- "copy": new published workflow made from one of the account's own (same steps, new ids) with
  another trigger: a phone line (call status, inbound, number whose name has `line`) or the Google
  Lead Form trigger (ad account = the location's googleAdwordsId; any form of that account). The Add
  Tag step gets `tags`, the card gets `source`, step types in `drop` go away (google_adword: Google
  counts lead-form leads itself; a second conversion would double them), `keep` = only the first N
  steps, and SMS alerts that went to the contact owner go to the account's users (a new lead has no
  owner, so "assign" reaches nobody).
- "add_tags": tags added to the first Add Tag step of existing workflows.
- "notify_users": existing workflows whose SMS alert goes to the contact owner → the account's users
  (Damon's and Simple: 0 of 7 and 1 of 16 Google Ads form leads had an owner).
- "line_tags": new workflow per line (calls and/or texts in, same trigger shape as the live line
  workflows): once per contact, if/else skips `skip` tags (customers, internal, spam), adds the line's
  source tag. Calls through an IVR fire it too (BluVantage's line workflows fire on IVR calls).
Backup of every workflow changed (backup/<slug>/); every tag used is created in the account first.
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

LEAD_FORM = {"from": "AdWords Form - New Lead", "trigger": "google_lead_form",
             "tags": ["new lead", "adwords", "google lead form"], "source": "Google Ads - Lead Form",
             "drop": ["google_adword"]}
ACCOUNTS = {
    "Wrigley": {
        "copy": {
            "AdWords Call In - New Lead": {"from": "Incoming Call To Pipeline", "line": "adwords", "keep": 4,
                                           "tags": ["new lead", "incoming call", "adwords", "adwords call in"],
                                           "source": "AdWords - PPC - Call In"},
            "Google LSA Call In - New Lead": {"from": "Incoming Call To Pipeline", "line": "lsa", "keep": 4,
                                              "tags": ["new lead", "incoming call", "google lsa"],
                                              "source": "Google LSA Call In"},
            "Google Lead Form - New Lead": {**LEAD_FORM, "from": "Adwords Form Fill To Pipeline"},
        },
        "add_tags": {"Adwords Form Fill To Pipeline": ["new lead", "adwords form fill"]},
    },
    "BluVantage": {"copy": {"Google Lead Form - New Lead": LEAD_FORM}},
    "Precision Pools": {"copy": {"Google Lead Form - New Lead": LEAD_FORM}},
    "Pool Duck Wesley Chapel": {"copy": {"Google AdWords - Qualified Lead (Lead Form)": {
        **LEAD_FORM, "from": "Google AdWords - Qualified Lead (Form FIll)",
        "tags": ["new lead", "google adwords", "google lead form"],
        "drop": ["google_adword", "remove_from_workflow"]}}},  # its last step only takes the contact out of itself
    "Reign": {"copy": {"Google Lead Form - New Lead": LEAD_FORM}},
    "Damon": {"copy": {"Google Lead Form - New Lead": LEAD_FORM}, "notify_users": ["AdWords Form - New Lead"]},
    "Simple Pool": {"copy": {"Google Lead Form - New Lead": LEAD_FORM}, "notify_users": ["AdWords Form - New Lead"]},
    "Sunwave": {  # every line goes through an IVR that tags "new lead"/"inbound call" without the line
        "line_tags": {
            "Lead Source - Adwords Call": {"line": "adwords", "kinds": ["call"], "tags": ["adwords", "adwords call in"]},
            "Lead Source - Website & GBP": {"line": "gbp", "kinds": ["call", "sms"], "tags": ["website & gbp"]},
            # texts to the Adwords and Angi's numbers were all spam/vendors (31 of 31 since August): calls only
            "Lead Source - Angi's Leads": {"line": "angi", "kinds": ["call"], "tags": ["angi"]},
            "Lead Source - Trucks & Cards": {"line": "truck", "kinds": ["call", "sms"], "tags": ["trucks & cards"]},
            "Lead Source - Customer Service": {"line": "customer service", "kinds": ["call", "sms"],
                                               "tags": ["customer service line"]},
        },
        "skip": ["quickbooks", "recurring customer", "internal", "outbound (staff)", "spam", "dnd"],
        "folder_of": "Website Form Fill To Pipeline",
        # "website form fill" is the Zapier lead form's tag here (rule → "google ads lead form"): site forms
        # get "website form" until the Zap has its own tag
        "add_tags": {"Website Form Fill To Pipeline": ["website form"],
                     "Service Quote Form Fill To Pipeline": ["website form"],
                     "AdWords Form - New Lead": ["adwords form fill"],
                     "Google Leads Form Fill To Pipeline": ["adwords", "google ads lead form"]},
    },
    "Passion": {  # the Google Ads line already tags itself (AdWords Call In / SMS)
        "line_tags": {"Lead Source - Website & GBP": {"line": "website", "kinds": ["call", "sms"],
                                                      "tags": ["website & gbp"]}},
        "skip": ["spam", "dnd", "existing customer", "internal"],
        "folder_of": "Website Form Fill To Pipeline",
        "add_tags": {"Website Form Fill To Pipeline": ["website form fill"]},
    },
}


def chain_of(tpl: list[dict], first: dict) -> list[dict]:
    by = {s["id"]: s for s in tpl}
    out = [first]
    while isinstance(out[-1].get("next"), str):
        out.append(by[out[-1]["next"]])
    return out


def fresh_ids(tpl: list[dict]) -> list[dict]:
    text = json.dumps(tpl)
    for s in tpl:
        text = text.replace(s["id"], str(uuid.uuid4()))
    return json.loads(text)


def drop_step(tpl: list[dict], sid: str) -> list[dict]:
    """Remove a step from its chain (root or branch); the rest of the chain moves up one."""
    by = {s["id"]: s for s in json.loads(json.dumps(tpl))}
    gone = by.pop(sid)
    nxt = gone.get("next")
    if isinstance(nxt, list):
        raise SystemExit("cannot drop a condition node")
    for s in by.values():
        if s.get("next") == sid:
            if nxt:
                s["next"] = nxt
            else:
                s.pop("next")
    cur = by.get(nxt) if nxt else None
    if cur:
        if gone.get("parentKey"):
            cur["parentKey"] = gone["parentKey"]
        else:
            cur.pop("parentKey", None)
    while cur:
        if isinstance(cur.get("next"), list):
            raise SystemExit("a condition follows the dropped step — not shifting orders blindly")
        cur["order"] -= 1
        cur = by.get(cur.get("next")) if isinstance(cur.get("next"), str) else None
    return list(by.values())


def first_step(tpl: list[dict]) -> dict:
    return next(s for s in tpl if not s.get("parentKey") and not s.get("parent"))


def to_users(step: dict, users: list[str]) -> bool:
    """SMS alert to the contact owner → to the account's users. True if changed."""
    sms = (step.get("attributes") or {}).get("sms") or {}
    if step["type"] != "internal_notification" or sms.get("userType") != "assign":
        return False
    sms.pop("assignedOwners", None)
    sms.update(userType="user", selectedUser=users)
    step.pop("incompleteData", None)
    return True


def build_copy(live: dict, spec: dict, users: list[str]) -> list[dict]:
    tpl = fresh_ids(live["workflowData"]["templates"])
    for t in spec.get("drop", []):
        for s in [s for s in tpl if s["type"] == t]:
            tpl = drop_step(tpl, s["id"])
    if spec.get("keep"):
        chain = chain_of(tpl, first_step(tpl))
        if len(chain) != len(tpl):
            raise SystemExit("keep only works on a linear workflow")
        tpl = chain[:spec["keep"]]
        tpl[-1].pop("next", None)
    tag = next((s for s in sorted(tpl, key=lambda s: s.get("order", 0)) if s["type"] == "add_contact_tag"), None)
    if not tag:
        raise SystemExit(f"{live['name']}: no Add Tag step to carry the tags")
    tag["attributes"]["tags"] = spec["tags"]
    for s in tpl:
        if s["type"] == "create_opportunity":
            s["attributes"]["opportunity_source"] = spec["source"]
        to_users(s, users)
    return tpl


def line_trigger(kind: str, line: list[str]) -> dict:
    first = {"call": {"field": "message.direction", "operator": "==", "value": "inbound", "title": "Call Direction",
                      "type": "select"},
             "sms": {"field": "message.type", "operator": "==", "value": 2, "title": "Reply channel", "type": "select"}}
    return {"type": {"call": "call_status", "sms": "customer_reply"}[kind],
            "name": {"call": "Call Details", "sms": "Customer Replied"}[kind], "masterType": "highlevel",
            "conditions": [first[kind], {"field": "inbound_number", "operator": "contains-any",
                                         "id": "inbound-twilio-number", "value": line, "title": "In Phone Number",
                                         "type": "multiselect"}]}


def line_flow(skip: list[str], tags: list[str]) -> list[dict]:
    """if/else (none of `skip`) → Add Tag in the "Lead" branch."""
    cond, yes, none = guard_nodes(None, None, 0, skip=skip)
    tag = {"id": str(uuid.uuid4()), "order": 0, "name": "Add Tag " + " / ".join(tags), "type": "add_contact_tag",
           "parent": yes["id"], "parentKey": yes["id"], "attributes": {"tags": tags, "type": "add_contact_tag"}}
    yes["next"] = tag["id"]
    return [cond, yes, none, tag]


def trigger_for(spec: dict, loc_obj: dict, numbers: list[dict]) -> dict:
    if spec.get("trigger") == "google_lead_form":
        acct = loc_obj.get("googleAdwordsId")
        if not acct:
            raise SystemExit("location has no googleAdwordsId (Google Ads account not connected)")
        return {"type": "google_lead_form_submitted", "name": "Google Lead Form Submitted", "masterType": "internal",
                "workflowsTriggerType": "INTERNAL",
                "conditions": [{"operator": "==", "field": "adAccountId", "value": acct, "title": "Ad Account Is",
                                "type": "select", "id": "adAccountId"}]}
    line = [n["phoneNumber"] for n in numbers if spec["line"] in (n.get("friendlyName") or "").lower()]
    if len(line) != 1:
        raise SystemExit(f"line '{spec['line']}': {line or 'nenhuma'}")
    return {"type": "call_status", "name": "Call Details", "masterType": "highlevel",
            "conditions": [{"field": "message.direction", "operator": "==", "value": "inbound",
                            "title": "Call Direction", "type": "select"},
                           {"field": "inbound_number", "operator": "contains-any", "id": "inbound-twilio-number",
                            "value": line, "title": "In Phone Number", "type": "multiselect"}]}


def refs_ok(tpl: list[dict]) -> bool:
    ids = {s["id"] for s in tpl}
    refs = [r for s in tpl for r in ([s.get("next")] if isinstance(s.get("next"), str) else s.get("next") or [])]
    refs += [s[k] for s in tpl for k in ("parent", "parentKey") if s.get(k)]
    return all(r in ids for r in refs)


def create(a: Agency, loc: str, name: str, parent: str | None, allow: bool, tpl: list[dict], triggers: list[dict]) -> bool:
    res = a.call("POST", BACKEND, f"/workflow/{loc}", body={"name": name, "parentId": parent, "status": "draft"})
    wid = res.get("id") or res.get("_id")
    body = {"name": name, "version": 1, "status": "draft", "parentId": parent, "allowMultiple": allow,
            "workflowData": {"templates": tpl}}
    a.call("PUT", BACKEND, f"/workflow/{loc}/{wid}", body=body)
    for trigger in triggers:
        trig = {**trigger, "schedule_config": {}, "workflowId": wid, "workflow_id": wid, "location_id": loc,
                "actions": [{"workflow_id": wid, "type": "add_to_workflow"}], "targetActionId": first_step(tpl)["id"]}
        t = a.call("POST", BACKEND, f"/workflow/{loc}/trigger", body=trig)
        a.call("PUT", BACKEND, f"/workflow/{loc}/trigger/{t['id']}", body={**trig, "id": t["id"]})
    a.call("PUT", BACKEND, f"/workflow/{loc}/{wid}", body={**body, "version": a.workflow(loc, wid).get("version", 1),
                                                           "status": "published"})
    time.sleep(4)
    got = a.workflow(loc, wid)
    t2 = got["workflowData"]["templates"]
    trs = [t for t in a.triggers(loc, wid) if not t.get("deleted")]
    ok = got["status"] == "published" and len(t2) == len(tpl) and refs_ok(t2) and \
        sorted(t["type"] for t in trs) == sorted(t["type"] for t in triggers) and \
        all(any(c in t["conditions"] for t in trs) for tr in triggers for c in tr["conditions"])
    print(f"      {'✓' if ok else '✗ VERIFICAR'} {got['status']} · {len(t2)} passos · gatilhos {[t['type'] for t in trs]}")
    return ok


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--only", action="append", required=True, help="account (key of ACCOUNTS)")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    load_dotenv()
    a = Agency()
    bad = 0
    stamp = time.strftime("%Y%m%d-%H%M%S")
    for key in args.only:
        cfg = ACCOUNTS[key]
        d = location_dirs([key])[0]
        loc_obj = load(d / "location.json", {})
        loc = loc_obj["id"]
        bdir = ROOT / "backup" / d.name
        bdir.mkdir(parents=True, exist_ok=True)
        flows = {w["name"]: w["id"] for w in a.workflows(loc)}
        users = [u["id"] for u in a.users(loc)]
        numbers = a.call("GET", SERVICES, f"/phone-system/numbers/location/{loc}").get("numbers", [])
        print(f"== {d.name}")

        def backup(wid: str, live: dict) -> None:
            trs = [t for t in a.triggers(loc, wid) if not t.get("deleted")]
            (bdir / f"workflow-{wid}-{stamp}.json").write_text(json.dumps({"workflow": live, "triggers": trs}))

        def put(wid: str, live: dict, tpl: list[dict]) -> bool:
            backup(wid, live)
            a.call("PUT", BACKEND, f"/workflow/{loc}/{wid}", body={
                "name": live["name"], "version": live.get("version", 1), "status": live["status"],
                "parentId": live.get("parentId"), "allowMultiple": live.get("allowMultiple", False),
                "workflowData": {"templates": tpl}})
            time.sleep(4)
            got = a.workflow(loc, wid)
            return got["status"] == live["status"] and len(got["workflowData"]["templates"]) == len(tpl) and \
                refs_ok(got["workflowData"]["templates"])

        tags = {t for spec in [*cfg.get("copy", {}).values(), *cfg.get("line_tags", {}).values()] for t in spec["tags"]} | \
            {t for ts in cfg.get("add_tags", {}).values() for t in ts} | set(cfg.get("skip", []))
        if args.apply:
            for t in sorted(tags):
                try:
                    a.call("POST", BACKEND, f"/workflow/{loc}/tags/create", body={"tag": t})
                except Exception:  # noqa: BLE001 — already exists
                    pass
        for name, spec in cfg.get("copy", {}).items():
            if name in flows:
                print(f"   {name}: já existe")
                continue
            src = a.workflow(loc, flows[spec["from"]])
            tpl = build_copy(src, spec, users)
            trig = trigger_for(spec, loc_obj, numbers)
            steps = " → ".join(s["name"] for s in sorted(tpl, key=lambda s: (bool(s.get("parent")), s.get("order", 0)))
                               if not s.get("nodeType", "").startswith("branch"))
            print(f"   + {name} (cópia de '{spec['from']}'): {trig['type']} {[c['value'] for c in trig['conditions']][-1]}"
                  f"\n      {steps}\n      tags {spec['tags']} · card '{spec['source']}'")
            if args.apply:
                bad += not create(a, loc, name, src.get("parentId"), src.get("allowMultiple", True), tpl, [trig])
        for name, spec in cfg.get("line_tags", {}).items():
            if name in flows:
                print(f"   {name}: já existe")
                continue
            line = [n["phoneNumber"] for n in numbers if spec["line"] in (n.get("friendlyName") or "").lower()]
            if len(line) != 1:
                raise SystemExit(f"{name}: linha '{spec['line']}' → {line or 'nenhuma'}")
            print(f"   + {name}: {'/'.join(spec['kinds'])} em {line} → pula {cfg['skip']} → tag {spec['tags']} "
                  "(1 vez por contato)")
            if args.apply:
                parent = a.workflow(loc, flows[cfg["folder_of"]]).get("parentId")
                bad += not create(a, loc, name, parent, False, line_flow(cfg["skip"], spec["tags"]),
                                  [line_trigger(k, line) for k in spec["kinds"]])
        for name, extra in cfg.get("add_tags", {}).items():
            live = a.workflow(loc, flows[name])
            tpl = json.loads(json.dumps(live["workflowData"]["templates"]))
            tag = min((s for s in tpl if s["type"] == "add_contact_tag"), key=lambda s: s.get("order", 0))
            new = [t for t in extra if t not in tag["attributes"]["tags"]]
            if not new:
                print(f"   {name}: já tem {extra}")
                continue
            print(f"   {name}: tags {tag['attributes']['tags']} + {new}")
            if args.apply:
                tag["attributes"]["tags"] = tag["attributes"]["tags"] + new
                ok = put(flows[name], live, tpl)
                got = next(s for s in a.workflow(loc, flows[name])["workflowData"]["templates"] if s["id"] == tag["id"])
                ok = ok and set(extra) <= set(got["attributes"]["tags"])
                bad += not ok
                print(f"      {'✓' if ok else '✗ VERIFICAR'}")
        for name in cfg.get("notify_users", []):
            live = a.workflow(loc, flows[name])
            tpl = json.loads(json.dumps(live["workflowData"]["templates"]))
            changed = [s["name"] for s in tpl if to_users(s, users)]
            if not changed:
                print(f"   {name}: alerta já vai para usuário")
                continue
            print(f"   {name}: {changed} dono do contato → {len(users)} usuário(s) da conta")
            if args.apply:
                ok = put(flows[name], live, tpl)
                bad += not ok
                print(f"      {'✓' if ok else '✗ VERIFICAR'}")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
