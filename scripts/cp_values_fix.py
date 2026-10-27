#!/usr/bin/env python3
"""Clear Pool Solutions Tucson: card values by outcome; abandoned cards deleted (Derek via Pedro, 27/10).

    ./.venv/bin/python scripts/cp_values_fix.py plan
    ./.venv/bin/python scripts/cp_values_fix.py test --to pedro@poolprofits.com
    ./.venv/bin/python scripts/cp_values_fix.py apply      # workflows
    ./.venv/bin/python scripts/cp_values_fix.py cards      # existing cards

Values: open $2,160 (a weekly customer's average) · 🎉 Won Customer (weekly) $2,160 · Won Customer – One Time Repair $150 ·
Lost $0 (card stays) · Spam / Out of Scope (abandoned) → card deleted (the contact stays, tagged).
- Intake "Create Or Update Opportunity" steps: value 2160.
- "Won Customer" / "Repair Customer Won" / "Lost Lead": + "Create Or Update Opportunity" in the same stage with the value
  and status (the "Update opportunity" step can't set a value — 4 field variants tested, none changed it).
- "DND Contact" (Spam) and "Out of Scope - Close": "Update opportunity: abandoned" → "Remove Opportunity" (the card that
  fired the workflow; the step that used to delete Won cards in "Current Customer").
test: one contact's card through New Lead → Won → One Time Repair → Lost → Spam (value at each step, deleted at the end).
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
import time
import uuid

from _common import ROOT, load_dotenv
from pp_review_fix import read
from pp_source_tags import refs_ok

from cli_anything.gohighlevel.utils.agency import BACKEND, SERVICES, Agency

LOC = "ghUi89uCpNyNunNpbtAt"
PIPELINE = "3efxD12t1FgWeOkp11yA"
WEEKLY, REPAIR = 2160, 150
VALUES = {"🚨 New Lead": WEEKLY, "In Communications": WEEKLY, "Booked Inspection": WEEKLY,
          "🎉 Won Customer": WEEKLY, "Won Customer – One Time Repair": REPAIR, "Lost Customer": 0}
SETTERS = {"Won Customer": ("🎉 Won Customer", "won", WEEKLY),
           "Repair Customer Won": ("Won Customer – One Time Repair", "won", REPAIR),
           "Lost Lead": ("Lost Customer", "lost", 0)}
REMOVERS = ["DND Contact", "Out of Scope - Close"]
DROP = {"SPAM", "Out of Scope"}
BDIR = ROOT / "backup" / "clear-pool-solutions-tucson"


def card_step(stage_id: str, status: str, value: int) -> dict:
    return {"id": str(uuid.uuid4()), "order": 0, "name": f"Card value ${value:,}", "type": "create_opportunity",
            "attributes": {"fields": [], "type": "create_opportunity", "pipeline_id": PIPELINE, "pipeline_stage_id": stage_id,
                           "opportunity_name": "{{contact.name}}", "opportunity_source": "", "monetary_value": f"{value}.00",
                           "opportunity_status": status}}


def prepend(tpl: list[dict], step: dict) -> list[dict]:
    out = json.loads(json.dumps(tpl))
    root = next(s for s in out if not s.get("parentKey"))
    step["next"] = root["id"]
    root["parentKey"] = step["id"]
    for s in out:
        s["order"] = s.get("order", 0) + 1
    return [step, *out]


def remover(tpl: list[dict]) -> list[dict] | None:
    out = json.loads(json.dumps(tpl))
    upd = next((s for s in out if s["type"] == "internal_update_opportunity"), None)
    if not upd:
        return None
    upd.update(name="Remove Opportunity", type="remove_opportunity", attributes={
        "type": "remove_opportunity", "opportunity_to_be_found": "previous"})
    upd.pop("workflowsActionType", None)
    return out


def put(a: Agency, wid: str, live: dict, tpl: list[dict]) -> dict:
    BDIR.mkdir(parents=True, exist_ok=True)
    (BDIR / f"workflow-{wid}-{time.strftime('%Y%m%d-%H%M%S')}.json").write_text(json.dumps(live))
    a.call("PUT", BACKEND, f"/workflow/{LOC}/{wid}", body={"name": live["name"], "version": live.get("version", 1),
                                                         "status": live["status"], "parentId": live.get("parentId"),
                                                         "workflowData": {"templates": tpl}})
    time.sleep(2)
    return read(a, LOC, wid)


def opps(a: Agency) -> list[dict]:
    out, page = [], 1
    while True:
        o = a.call("GET", SERVICES, "/opportunities/search", params={"location_id": LOC, "pipeline_id": PIPELINE,
                                                                     "limit": 100, "page": page}).get("opportunities", [])
        out += o
        if len(o) < 100:
            return out
        page += 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("mode", choices=["plan", "test", "apply", "cards"])
    parser.add_argument("--to")
    args = parser.parse_args()
    load_dotenv()
    a = Agency()
    if not a.location(LOC)["name"].startswith("Clear Pool Solutions"):
        sys.exit("sub-conta errada")
    flows = {w["name"]: w["id"] for w in a.workflows(LOC)}
    stages = {s["name"]: s["id"] for s in next(p for p in a.pipelines(LOC) if p["id"] == PIPELINE)["stages"]}
    names = {v: k for k, v in stages.items()}
    if args.mode in ("plan", "apply"):
        for name, (stage, status, value) in SETTERS.items():
            live = read(a, LOC, flows[name])
            done = any(s.get("name", "").startswith("Card value") for s in live["workflowData"]["templates"])
            print(f"   {name}: {'já feito' if done else f'+ card {status} ${value:,}'}")
            if not done and args.mode == "apply":
                got = put(a, flows[name], live, prepend(live["workflowData"]["templates"], card_step(stages[stage], status, value)))
                print(f"      {'✓' if refs_ok(got['workflowData']['templates']) and got['status'] == live['status'] else '✗'} {got['status']}")
        for name in REMOVERS:
            live = read(a, LOC, flows[name])
            tpl = remover(live["workflowData"]["templates"])
            print(f"   {name}: {'status abandoned → apaga o card' if tpl else 'já feito'}")
            if tpl and args.mode == "apply":
                got = put(a, flows[name], live, tpl)
                print(f"      {'✓' if refs_ok(got['workflowData']['templates']) and got['status'] == live['status'] else '✗'} {got['status']}")
        for name, wid in flows.items():
            if name in SETTERS:
                continue
            live = read(a, LOC, wid)
            tpl = json.loads(json.dumps(live["workflowData"]["templates"]))
            hit = [s for s in tpl if s["type"] == "create_opportunity" and s["attributes"].get("opportunity_status") == "open"
                   and str(s["attributes"].get("monetary_value")) not in (str(WEEKLY), f"{WEEKLY}.00")]
            if hit:
                for s in hit:
                    s["attributes"]["monetary_value"] = f"{WEEKLY}.00"
                print(f"   {name}: card novo ${WEEKLY:,} ({len(hit)})")
                if args.mode == "apply":
                    got = put(a, wid, live, tpl)
                    print(f"      {'✓' if refs_ok(got['workflowData']['templates']) and got['status'] == live['status'] else '✗'} {got['status']}")
    if args.mode == "test":
        cid = a.call("POST", SERVICES, "/contacts/", body={"locationId": LOC, "firstName": "ZZ Test", "lastName": "values",
                                                           "email": args.to.replace("@", f"+cp-values-{int(time.time())}@")})["contact"]["id"]
        time.sleep(3)
        oid = (lambda o: (o.get("opportunity") or o)["id"])(a.call("POST", SERVICES, "/opportunities/", body={
            "locationId": LOC, "pipelineId": PIPELINE, "contactId": cid, "pipelineStageId": stages["🚨 New Lead"],
            "name": "ZZ Test values", "status": "open", "monetaryValue": 150}))
        bad = 0
        for stage, want in (("🎉 Won Customer", ("won", WEEKLY)), ("Won Customer – One Time Repair", ("won", REPAIR)),
                            ("Lost Customer", ("lost", 0)), ("SPAM", None)):
            a.call("PUT", SERVICES, f"/opportunities/{oid}", body={"pipelineId": PIPELINE, "pipelineStageId": stages[stage], "status": "open"})
            time.sleep(30)
            try:
                o = a.call("GET", SERVICES, f"/opportunities/{oid}").get("opportunity", {})
                got = (o.get("status"), o.get("monetaryValue"))
            except Exception:  # noqa: BLE001 — deleted
                got = None
            ok = got == want
            bad += not ok
            print(f"   {'✓' if ok else '✗'} {stage}: {got if got else 'card apagado'}")
        try:
            a.call("DELETE", SERVICES, f"/opportunities/{oid}")
        except Exception:  # noqa: BLE001
            pass
        a.call("DELETE", SERVICES, f"/contacts/{cid}")
        print("   limpo (o e-mail de boas-vindas do teste foi para o --to).")
        return 1 if bad else 0
    cur = opps(a)
    drop = [o for o in cur if names.get(o["pipelineStageId"]) in DROP]
    fix = [o for o in cur if names.get(o["pipelineStageId"]) in VALUES and o.get("monetaryValue") != VALUES[names[o["pipelineStageId"]]]]
    print(f"   cards: apagar {len(drop)} (spam/fora da área) · valor a acertar {len(fix)} "
          f"{collections.Counter((names[o['pipelineStageId']], o.get('monetaryValue')) for o in fix)}")
    if args.mode == "cards":
        BDIR.mkdir(parents=True, exist_ok=True)
        (BDIR / f"opportunities-before-values-{time.strftime('%Y%m%d-%H%M%S')}.json").write_text(json.dumps(cur))
        for o in fix:
            a.call("PUT", SERVICES, f"/opportunities/{o['id']}", body={"monetaryValue": VALUES[names[o["pipelineStageId"]]]})
        for o in drop:
            a.call("DELETE", SERVICES, f"/opportunities/{o['id']}")
        time.sleep(5)
        print(f"   agora: {collections.Counter((names.get(o['pipelineStageId']), o['status'], o.get('monetaryValue')) for o in opps(a))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
