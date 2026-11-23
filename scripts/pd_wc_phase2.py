#!/usr/bin/env python3
"""Pool Duck Wesley Chapel → V9, phase 2 (Pedro, after the 16/11 meeting with Justin and Ed: "start from scratch, do it
the way every Pool Duck location does it"; our flows as the standard, one copy of theirs kept in draft; nothing may fire
to existing contacts; no lead may be lost).

Run with the Pool Duck token:  GHL_AGENCY=poolduck python3 scripts/pd_wc_phase2.py <step> [--apply]

Steps (each prints a plan; --apply writes, with a backup of everything it touches):
  ads      Our copies of their 7 ad / LSA workflows ("<name> (Pool Leads)"): same trigger (line / form / lead form), same
           tags, same Google Ads / Meta conversion steps, but the card goes to Pool Leads → New Lead. Their "Converted Lead"
           conversion is copied onto the 3 Won stages of Pool Leads. Published; the originals go to draft.
  guards   "Doesn't Have Tag: pre-snapshot" on every V9 stage / tag / customer-reply trigger (the 2,675 contacts that existed
           before the migration never get a V9 message, even if a card of theirs is moved).
  publish  V9 set published (Southern model statuses, minus 08 Paid Ads / IVR / per-line tags / Won welcome, which stays with
           their tag-based welcome per Ed 11/11; Missed New Lead SMS stays off because the native missed-call text is on).
           Incoming call flows only on the main line 813-606-0773 (ad lines get their card from the ad copies).
  cards    The 108 cards of "Leads --> Sales Pipeline" into Pool Leads, mapped from the meeting + the PoolBrain report:
           Customer → Won - Weekly, Engaged → In Communication, Didn't Sign Up/Bad Fit → Lost, still Lead but an active
           PoolBrain customer → Current/Recurring Customer, inactive → Lost, unknown → New Lead (the team calls them).
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import re
import sys
import time
import uuid

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(__file__))
from _common import load_dotenv  # noqa: E402

load_dotenv()
from cli_anything.gohighlevel.utils.agency import BACKEND, SERVICES, Agency  # noqa: E402

# Other Pool Duck accounts (23/11): PD_LOC, PD_SLUG, PD_MAIN_LINE, PD_ALERT_EMAIL, PD_SITE_FORMS (comma list), PD_PUBLISH_ALSO
# (comma list of KEEP_DRAFT names to publish too). Defaults = Wesley Chapel.
LOC = os.environ.get("PD_LOC", "uJr8H2qaQM5ffZxeYFqn")
MAIN_LINE = os.environ.get("PD_MAIN_LINE", "+18136060773")
GUARD = "pre-snapshot"
BK = os.path.join(ROOT, "backup", os.environ.get("PD_SLUG", "poolduck-wesley-chapel"), f"phase2-{time.strftime('%Y%m%d-%H%M%S')}")
TRIGGER_DROP = ("id", "_id", "date_added", "date_updated", "deleted", "origin_id", "company_id", "workflowId",
                "workflow_id", "location_id", "actions", "belongs_to", "last_conditions_change_at", "targetActionId")
ADS = ["Google AdWords - Qualified Lead (Call In)", "Google AdWords - Qualified Lead (Form FIll)",
       "Google AdWords - Qualified Lead (Lead Form)", "LSA Call Flow", "Facebook - Qualified Lead (Call In)",
       "Facebook - Qualified Lead (Form FIll)"]
CONVERTED = "Google AdWords - Converted Lead (Form Fill)"
FILTER = {"field": "contact.tags", "id": "doesnot-have-tag", "type": "select", "title": "Doesn't Have Tag",
          "value": GUARD, "operator": "index-of-false"}


def backup(name: str, obj) -> None:
    os.makedirs(BK, exist_ok=True)
    with open(os.path.join(BK, re.sub(r"[^\w.-]+", "_", name) + ".json"), "w") as fh:
        json.dump(obj, fh, indent=1)


def pool_leads(a: Agency) -> dict:
    p = next(p for p in a.pipelines(LOC) if "pool leads" in (p.get("name") or "").lower())
    return {"id": p["id"], "stages": {s["name"]: s["id"] for s in p["stages"]}}


def stage_like(pl: dict, *keys: str) -> str:
    for k in keys:
        for n, i in pl["stages"].items():
            if k.lower() in n.lower():
                return i
    raise SystemExit(f"Pool Leads has no stage like {keys}: {list(pl['stages'])}")


def wf_by_name(a: Agency, name: str) -> dict | None:
    return next((w for w in a.workflows(LOC) if (w.get("name") or "").strip() == name), None)


def put(a: Agency, wid: str, status: str, templates: list[dict], name: str | None = None) -> dict:
    live = a.workflow(LOC, wid)
    body = {k: live[k] for k in live if k not in ("_id", "createdAt", "updatedAt", "__v")}
    body["status"] = status
    body["workflowData"] = {**(live.get("workflowData") or {}), "templates": templates}
    if name:
        body["name"] = name
    a.call("PUT", BACKEND, f"/workflow/{LOC}/{wid}", body=body)
    return a.workflow(LOC, wid)


def copy_workflow(a: Agency, src: dict, new_name: str, fix_steps, fix_trigger, apply: bool) -> str | None:
    """Create new_name as a copy of src (fresh step ids), steps/triggers changed by the two callbacks; published."""
    full = a.workflow(LOC, src["id"])
    trs = [t for t in a.triggers(LOC, src["id"]) if not t.get("deleted")]
    backup(f"src-{src['name']}", {"workflow": full, "triggers": trs})
    tpl = copy.deepcopy(full["workflowData"]["templates"])
    ids = {t["id"]: str(uuid.uuid4()) for t in tpl}
    raw = json.dumps(tpl)
    for o, n in ids.items():
        raw = raw.replace(o, n)
    tpl = fix_steps(json.loads(raw))
    first = next((t["id"] for t in tpl if not t.get("parentKey") and not t.get("parent")), tpl[0]["id"] if tpl else None)
    new_trs = []
    for t in trs:
        r = fix_trigger({k: v for k, v in t.items() if k not in TRIGGER_DROP})
        new_trs += r if isinstance(r, list) else [r]
    print(f"   + '{new_name}': {len(tpl)} steps, triggers {[ (t.get('type'), [str(c.get('value'))[:24] for c in t.get('conditions') or []]) for t in new_trs]}")
    if not apply:
        return None
    if wf_by_name(a, new_name):
        print("     already exists — skipped")
        return wf_by_name(a, new_name)["id"]
    res = a.call("POST", BACKEND, f"/workflow/{LOC}", body={"name": new_name, "parentId": full.get("parentId"), "status": "draft"})
    wid = res.get("id") or res.get("_id")
    put(a, wid, "draft", tpl, new_name)
    for t in new_trs:
        body = {**t, "workflowId": wid, "workflow_id": wid, "location_id": LOC,
                "actions": [{"workflow_id": wid, "type": "add_to_workflow"}], "targetActionId": first}
        r = a.call("POST", BACKEND, f"/workflow/{LOC}/trigger", body=body)
        if r.get("id"):
            a.call("PUT", BACKEND, f"/workflow/{LOC}/trigger/{r['id']}", body={**body, "id": r["id"]})
    got = put(a, wid, "published", a.workflow(LOC, wid)["workflowData"]["templates"])
    act = [t.get("active") for t in a.triggers(LOC, wid) if not t.get("deleted")]
    print(f"     ✓ {wid[:8]} {got['status']} · {len(got['workflowData']['templates'])} steps · triggers active {act}")
    return wid


def step_ads(a: Agency, apply: bool) -> None:
    pl = pool_leads(a)
    new_lead = stage_like(pl, "new lead")
    won = [i for n, i in pl["stages"].items() if "won" in n.lower()]

    def to_pool_leads(tpl):
        for t in tpl:
            if t["type"] == "create_opportunity":
                at = t["attributes"]
                for k in ("pipeline_id", "pipelineId"):
                    if k in at:
                        at[k] = pl["id"]
                for k in ("pipeline_stage_id", "stage_id", "pipelineStageId"):
                    if k in at:
                        at[k] = new_lead
            if t["type"] == "remove_from_workflow":  # pointed at their own flows; ours must not pull leads out of V9
                pass
        return tpl

    done = []
    for name in ADS:
        src = wf_by_name(a, name)
        if not src:
            print(f"   ! '{name}' not found")
            continue
        wid = copy_workflow(a, src, f"{name} (Pool Leads)", to_pool_leads, lambda t: t, apply)
        if apply and wid and src.get("status") == "published":  # right away, so a lead never gets two cards
            put(a, src["id"], "draft", a.workflow(LOC, src["id"])["workflowData"]["templates"])
            print(f"     theirs → draft: {src['name']}")
    src = wf_by_name(a, CONVERTED)
    if src:
        def won_trigger(t):
            out = []
            for stage in won:  # one trigger per Won stage of Pool Leads, guarded
                x = copy.deepcopy(t)
                for c in x.get("conditions") or []:
                    if c.get("field") == "opportunity.pipelineId":
                        c["value"] = pl["id"]
                    if c.get("field") == "opportunity.pipelineStageId":
                        c["value"] = stage
                x["conditions"] = (x.get("conditions") or []) + [dict(FILTER)]
                out.append(x)
            return out
        wid = copy_workflow(a, src, f"{CONVERTED} (Pool Leads Won)", lambda tpl: tpl, won_trigger, apply)
        done.append((src, wid))
    if apply:
        for src, wid in done:
            if wid and src.get("status") == "published":
                full = a.workflow(LOC, src["id"])
                put(a, src["id"], "draft", full["workflowData"]["templates"])
                print(f"   theirs → draft: {src['name']}")


MODEL_DIR = os.path.join(ROOT, "dump", "southern-pool-outdoors")
GUARD_TYPES = ("pipeline_stage_updated", "opportunity_status_changed", "contact_tag", "customer_reply")
# V9 flows that stay OFF in the WC: per-client ads/lines (ours are the "(Pool Leads)" copies), IVR, Won welcome (Ed 11/11:
# their tag-based welcome), Missed New Lead SMS (the native missed-call text is on), appointments/recurring (no calendar).
KEEP_DRAFT = {"AdWords Call In - New Lead", "AdWords Form - New Lead", "Adword Call - Conversion", "Google Ads SMS - New Lead",
              "IVR - Main Line Menu", "Sequential Call Routing", "Facebook Ads Call - Tag", "Website & GBP Call - Tag",
              "Won Stage", "Missed New Lead - Initial SMS Follow-up",
              # until the account has its NPS form/link and Google connected for reviews
              "Review Request", "Review Response - Negative", "Review Response - Positive"}
KEEP_DRAFT -= {x.strip() for x in os.environ.get("PD_PUBLISH_ALSO", "").split(",") if x.strip()}
ALERT_ALL = {"Inbound SMS - Notify Owner"}  # Ed 13/11 + 16/11: every text alerts, customers included


def v9_names() -> dict:
    return {w["name"]: w["status"] for w in json.load(open(os.path.join(MODEL_DIR, "workflows", "_index.json")))}


def has_guard(t: dict) -> bool:
    return any(c.get("field") == "contact.tags" and c.get("value") == GUARD and c.get("operator") == "index-of-false"
               for c in t.get("conditions") or [])


def step_guards(a: Agency, apply: bool) -> None:
    names = v9_names()
    for w in a.workflows(LOC):
        if w["name"] not in names:
            continue
        for t in a.triggers(LOC, w["id"]):
            if t.get("deleted") or t.get("type") not in GUARD_TYPES:
                continue
            if has_guard(t):
                print(f"   = {w['name']} ({t['type']}) already guarded")
                continue
            print(f"   + {w['name']} ({t['type']})")
            if apply:
                backup(f"trigger-{t['id']}", t)
                body = {k: v for k, v in t.items() if k not in ("_id", "date_added", "date_updated", "deleted", "origin_id",
                                                               "company_id", "belongs_to", "last_conditions_change_at")}
                body["conditions"] = (t.get("conditions") or []) + [dict(FILTER)]
                a.call("PUT", BACKEND, f"/workflow/{LOC}/trigger/{t['id']}", body=body)
                after = next(x for x in a.triggers(LOC, w["id"]) if x["id"] == t["id"])
                print(f"     {'✓' if has_guard(after) else '✗ CHECK'}")


def users_ok(tpl: list[dict]) -> list[str]:
    """steps that notify/assign 'user' with nobody selected (GHL refuses to publish them)"""
    bad = []
    for t in tpl:
        at = t.get("attributes") or {}
        for k in ("sms", "email"):
            x = at.get(k) or {}
            if isinstance(x, dict) and x.get("userType") == "user" and not x.get("selectedUser"):
                bad.append(t.get("name"))
        if t["type"] in ("assign_user",) and not (at.get("user_list") or at.get("assigned_to")):
            bad.append(t.get("name"))
    return bad


def step_publish(a: Agency, apply: bool) -> None:
    names = v9_names()
    debbie = next(u["id"] for u in a.users(LOC) if (u.get("email") or "").lower() == os.environ.get("PD_ALERT_EMAIL", "debbie@poolduck.com"))
    for w in sorted(a.workflows(LOC), key=lambda x: x["name"]):
        if w["name"] not in names or names[w["name"]] != "published" or w["name"] in KEEP_DRAFT:
            continue
        full = a.workflow(LOC, w["id"])
        tpl = full["workflowData"]["templates"]
        trs = [t for t in a.triggers(LOC, w["id"]) if not t.get("deleted")]
        unguarded = [] if w["name"] in ALERT_ALL else [t["type"] for t in trs if t.get("type") in GUARD_TYPES and not has_guard(t)]
        nobody = users_ok(tpl)
        print(f"   {'=' if w['status'] == 'published' else '+'} {w['name']}: {len(tpl)} steps · unguarded {unguarded} · "
              f"no user {nobody}")
        if not apply or w["status"] == "published":
            continue
        if unguarded:
            print("     ✗ not published: run 'guards' first")
            continue
        backup(f"wf-{w['name']}", {"workflow": full, "triggers": trs})
        for t in tpl:  # nobody → Debbie (Ed in the 16/11 call: every call/text/alert goes to Debbie for now)
            at = t.get("attributes") or {}
            for k in ("sms", "email"):
                x = at.get(k)
                if isinstance(x, dict) and x.get("userType") == "user" and not x.get("selectedUser"):
                    x["selectedUser"] = [debbie]
            if w["name"] in ALERT_ALL and t["type"] == "internal_notification":
                at.setdefault("sms", {}).update(userType="user", selectedUser=[debbie])
            if t["type"] == "assign_user" and not (at.get("user_list") or at.get("assigned_to")):
                at["user_list"] = [debbie]
            if t["type"] == "task-notification" and not at.get("assignedTo"):
                at["assignedTo"] = debbie
        got = put(a, w["id"], "published", tpl)
        print(f"     ✓ {got['status']} · triggers active {[t.get('active') for t in a.triggers(LOC, w['id']) if not t.get('deleted')]}")


PB_REPORT = os.environ.get("WC_PB_REPORT", "")
# Justin in the 16/11 meeting: new customers won from the ads (the other "Customer" cards were existing customers)
NEW_WINS = ("matos", "oles", "olis", "musser", "douglas bell", "dana moser", "brice", "bryce")


def pb_index() -> dict:
    import openpyxl
    rows = list(openpyxl.load_workbook(PB_REPORT, read_only=True).worksheets[0].iter_rows(values_only=True))
    h = {x: i for i, x in enumerate(rows[0])}
    dig = lambda v: re.sub(r"\D", "", str(v or ""))[-10:]  # noqa: E731
    idx = {}
    for r in rows[1:]:
        st = r[h["Status"]]
        for p in re.split(r"[,;/]", str(r[h["Billing Phone"]] or "")):
            if len(dig(p)) == 10:
                idx["p" + dig(p)] = st
        for e in re.split(r"[,; ]", str(r[h["Billing Email"]] or "")):
            if "@" in e:
                idx["e" + e.strip().lower()] = st
        if r[h["Name"]]:
            idx["n" + str(r[h["Name"]]).strip().lower()] = st
    return idx


def step_cards(a: Agency, apply: bool) -> None:
    if not PB_REPORT:
        sys.exit("set WC_PB_REPORT=<PoolBrain customer report .xlsx>")
    pb = pb_index()
    dig = lambda v: re.sub(r"\D", "", str(v or ""))[-10:]  # noqa: E731
    pl = pool_leads(a)
    S = {k: stage_like(pl, k) for k in ("new lead", "in communication", "won - weekly", "recurring", "lost")}
    old = next(p for p in a.pipelines(LOC) if p["id"] != pl["id"])
    names = {s["id"]: s["name"] for s in old["stages"]}
    ops, page = [], 1
    while True:
        o = a.get(SERVICES, "/opportunities/search", {"location_id": LOC, "pipeline_id": old["id"], "limit": 100, "page": page}).get("opportunities", [])
        ops += o
        if len(o) < 100:
            break
        page += 1
    backup("cards-before", ops)
    plan = {}
    for x in ops:
        c = x.get("contact") or {}
        nm = (c.get("name") or x.get("name") or "").split(" - ")[0].strip().lower()
        st = pb.get("p" + dig(c.get("phone"))) or pb.get("e" + (c.get("email") or "").lower()) or pb.get("n" + nm) or ""
        old_stage = names.get(x.get("pipelineStageId"), "?")
        if any(k in nm for k in NEW_WINS):
            to = "won - weekly"
        elif old_stage == "Customer":
            to = "won - weekly" if x.get("status") == "won" else "recurring"
        elif old_stage in ("Didn't Sign Up", "Bad Fit"):
            to = "lost"
        elif old_stage == "Engaged Lead":
            to = "in communication"
        elif st.startswith("Active"):
            to = "recurring"
        elif st == "Inactive":
            to = "lost"
        else:
            to = "new lead"
        plan.setdefault(to, []).append((x, old_stage, st))
    for to, xs in plan.items():
        print(f"   → {to}: {len(xs)}  e.g. {[ (x.get('name') or '')[:22] for x, _, _ in xs[:6]]}")
    if not apply:
        return
    moved = 0
    for to, xs in plan.items():
        for x, _, _ in xs:
            body = {"pipelineId": pl["id"], "pipelineStageId": S[to]}
            if to == "lost":
                body["status"] = "lost"
            elif to in ("won - weekly",):
                body["status"] = "won"
            a.call("PUT", SERVICES, f"/opportunities/{x['id']}", body=body)
            moved += 1
    print(f"   ✓ moved {moved} cards to Pool Leads (contacts all carry '{GUARD}', so no V9 message fires)")


CALL_FLOWS = ("Answered Incoming Call To Pipeline", "Missed Incoming Call To Pipeline")
SITE_FORMS = [x for x in os.environ.get("PD_SITE_FORMS", "r0tUEDr6n1bIqmv1RDST,cS4QIWtJd3IXOtB4Fuza,oawTezosQbLJGDPJ3P3k,TcPu80nUo9cmZCFuPSsF").split(",") if x]  # website quote forms (both snapshot copies)


def step_calls_forms(a: Agency, apply: bool) -> None:
    """V9 call flows: main line only + skip existing customers / spam / dnd (customers call the main line to pay).
    Website Form Fill: the account's website quote forms."""
    from pp_lead_alerts import guard_nodes
    for name in CALL_FLOWS:
        w = wf_by_name(a, name)
        full = a.workflow(LOC, w["id"])
        tpl = full["workflowData"]["templates"]
        trs = [t for t in a.triggers(LOC, w["id"]) if not t.get("deleted")]
        wrapped = any(t.get("type") == "if_else" for t in tpl)
        print(f"   {name}: {len(tpl)} steps, guard if/else {'already' if wrapped else 'added'}, trigger → main line only")
        if not apply:
            continue
        backup(f"calls-{name}", {"workflow": full, "triggers": trs})
        if not wrapped:
            by = {t["id"]: t for t in tpl}
            chain = [next(t for t in tpl if not t.get("parentKey"))]
            while chain[-1].get("next"):
                chain.append(by[chain[-1]["next"]])
            if len(chain) != len(tpl):
                sys.exit(f"{name}: not a linear chain")
            c, y, n = guard_nodes(None, None, 0, skip=["spam", "dnd", "existing customer"])
            chain = json.loads(json.dumps(chain))
            for i, st in enumerate(chain):
                st.update(order=i, parent=y["id"], parentKey=chain[i - 1]["id"] if i else y["id"])
                st.pop("next", None)
                if i:
                    chain[i - 1]["next"] = st["id"]
            y["next"] = chain[0]["id"]
            tpl = [c, y, n, *chain]
            put(a, w["id"], w["status"], tpl)
        first = tpl[0]["id"]
        for t in trs:
            body = {k: v for k, v in t.items() if k not in ("_id", "date_added", "date_updated", "deleted", "origin_id",
                                                           "company_id", "belongs_to", "last_conditions_change_at")}
            conds = [c for c in body.get("conditions") or [] if c.get("field") != "inbound_number"]
            conds.append({"operator": "contains-any", "field": "inbound_number", "value": [MAIN_LINE],
                          "title": "In phone number", "type": "multiselect", "id": "inbound-twilio-number"})
            body.update(conditions=conds, targetActionId=first, workflowId=w["id"], workflow_id=w["id"], location_id=LOC,
                        actions=[{"workflow_id": w["id"], "type": "add_to_workflow"}])
            a.call("PUT", BACKEND, f"/workflow/{LOC}/trigger/{t['id']}", body=body)
        chk = a.workflow(LOC, w["id"])["workflowData"]["templates"]
        print(f"     ✓ {len(chk)} steps, first = {chk[0]['name']}; triggers {[[c.get('value') for c in t.get('conditions') or []] for t in a.triggers(LOC, w['id'])]}")
    w = wf_by_name(a, "Website Form Fill To Pipeline")
    trs = [t for t in a.triggers(LOC, w["id"]) if not t.get("deleted")]
    print(f"   Website Form Fill To Pipeline: form trigger on {len(SITE_FORMS)} website forms (has {len(trs)} triggers now)")
    if apply and not trs:
        tpl = a.workflow(LOC, w["id"])["workflowData"]["templates"]
        first = next(t["id"] for t in tpl if not t.get("parentKey"))
        body = {"type": "form_submission", "name": "Form Submitted", "masterType": "highlevel", "schedule_config": {},
                "conditions": [{"operator": "is-any-of", "field": "form.id", "value": SITE_FORMS, "title": "Form is",
                                "type": "string"}],
                "workflowId": w["id"], "workflow_id": w["id"], "location_id": LOC, "targetActionId": first,
                "actions": [{"workflow_id": w["id"], "type": "add_to_workflow"}]}
        r = a.call("POST", BACKEND, f"/workflow/{LOC}/trigger", body=body)
        if r.get("id"):
            a.call("PUT", BACKEND, f"/workflow/{LOC}/trigger/{r['id']}", body={**body, "id": r["id"]})
        print(f"     ✓ {[[c.get('value') for c in t.get('conditions') or []] for t in a.triggers(LOC, w['id'])]}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("step", choices=["ads", "guards", "calls_forms", "publish", "cards"])
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    if os.environ.get("GHL_AGENCY", "").lower() != "poolduck":
        sys.exit("run with GHL_AGENCY=poolduck")
    a = Agency()
    {"ads": step_ads, "guards": step_guards, "publish": step_publish, "cards": step_cards, "calls_forms": step_calls_forms}.get(args.step, lambda *_: sys.exit("step not written yet"))(a, args.apply)


if __name__ == "__main__":
    main()
