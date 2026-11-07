#!/usr/bin/env python3
"""Stay Fresh: move already-quoted leads to 💰 Quote Sent without any automated text (Frank, 06/11).

    ./.venv/bin/python scripts/sf_quote_sent_silent.py plan
    ./.venv/bin/python scripts/sf_quote_sent_silent.py guard     # permanent trigger filter + tag only
    ./.venv/bin/python scripts/sf_quote_sent_silent.py test      # ZZ TEST copy: tagged card skipped, control enters
    ./.venv/bin/python scripts/sf_quote_sent_silent.py apply     # guard + the 6 cards

Frank: Donna Johnson, Cyndy Pellien, Brent Olson, Evan Harrison, Susan Ogg and Sean Mullane were already contacted and
quoted by the team → their cards go to Quote Sent, but they must NOT get the "Quote Sent Follow-up" texts (1 day → SMS 1
→ 2 days → SMS 2 → 2 days → Lost). The only workflow on that stage is "Quote Sent Follow-up" (`plan` scans every
trigger of the account to prove it; "Stage Changed -> Stop Follow-ups" does not listen to Quote Sent).
Guard (permanent, harmless — the same shape as `existing customer` on the Won triggers): the Quote Sent trigger gets
"Doesn't Have Tag: quoted manually". Team usage from now on: add `quoted manually`, then move the card → no follow-up.
apply, per contact: GET + backup of the card → tag → card PUT to Quote Sent → wait → defensive "remove from Quote Sent
Follow-up" (no-op if never entered) → tag removed again (a later re-quote follows the normal flow) → check: card in
Quote Sent, no outbound SMS/e-mail since the start. Sean Mullane already has a card (website form 30/10): moved too.
"""
from __future__ import annotations

import argparse
import calendar
import json
import sys
import time
import uuid

from _common import ROOT, load_dotenv

from cli_anything.gohighlevel.utils.agency import BACKEND, SERVICES, Agency, GHLError

LOC = "DdTE6mF11dqgoI5Cv7XN"
PIPELINE = "5lyzLFECNQGtANjpnKc6"
NEW_LEAD = "00add63d-7bd2-4890-8974-598b7287765c"
QUOTE_SENT = "636f468f-055e-432e-87bc-9b6ba281f084"
QS_FLOW = "9b1b2c75-4445-4a87-8444-f13727c1cf42"  # Quote Sent Follow-up
TAG = "quoted manually"
FILTER = {"field": "contact.tags", "id": "doesnot-have-tag", "type": "select", "title": "Doesn't Have Tag",
          "value": TAG, "operator": "index-of-false"}
DROP = ("_id", "date_added", "date_updated", "deleted", "origin_id", "company_id", "company_age",
        "last_conditions_change_at", "belongs_to")
CONTACTS = {  # Frank's names → contact ids (searched 07/11)
    "Donna Johnson": "NU97RCDRXnipnsIFpBb8", "Cyndy Pellien": "RK07G732Mj3vmn8qhfiQ",
    "Brent Olson": "llBGHsZV2JuvZ8lgt5na", "Evan Harrison": "k5YCQSQ3iRzWejwRBYr2",
    "Susan Ogg": "WtmXw8DoEEskZONQ1zpG", "Sean Mullane": "A74yG2KujpRZnQjUilsG"}
BDIR = ROOT / "backup" / "stay-fresh-pools"
ACTIVITY = {25, 26, 27, 28, 29, 30, 31}  # activity notes in the conversation (28 = "Opportunity updated"), not messages


def stamp() -> str:
    return time.strftime("%Y%m%d-%H%M%S")


def cards(a: Agency, cid: str) -> list[dict]:
    return [o for o in a.call("GET", SERVICES, "/opportunities/search",
                              params={"location_id": LOC, "contact_id": cid, "limit": 50})["opportunities"]
            if o.get("pipelineId") == PIPELINE]


def outbound_since(a: Agency, cid: str, since_ms: int) -> list[dict]:
    """Outbound messages (SMS, e-mail, calls…; not the activity notes) created after since_ms."""
    out = []
    for conv in a.call("GET", SERVICES, "/conversations/search",
                       params={"locationId": LOC, "contactId": cid}).get("conversations", []):
        r = a.call("GET", SERVICES, f"/conversations/{conv['id']}/messages", params={"limit": 50}).get("messages", {})
        msgs = r.get("messages", []) if isinstance(r, dict) else r
        for m in msgs:
            when = m.get("dateAdded") or ""
            ms = calendar.timegm(time.strptime(when[:19], "%Y-%m-%dT%H:%M:%S")) * 1000 if when else 0
            if m.get("direction") == "outbound" and ms >= since_ms and m.get("type") not in ACTIVITY \
                    and "ACTIVITY" not in str(m.get("messageType")):
                out.append({"type": m.get("messageType"), "at": when, "body": (m.get("body") or "")[:60]})
    return out


def stage_triggers(a: Agency) -> list[tuple[str, str, dict]]:
    """Every published/draft trigger that could react to a card entering Quote Sent."""
    hits = []
    for w in a.workflows(LOC):
        for t in a.triggers(LOC, w["id"]):
            if t.get("deleted"):
                continue
            kind = t.get("type") or ""
            if not (kind.startswith("pipeline") or kind.startswith("opportunity")):
                continue
            stage = [c.get("value") for c in t.get("conditions") or [] if c.get("field") == "opportunity.pipelineStageId"]
            if not stage or QUOTE_SENT in stage or any(QUOTE_SENT in (v if isinstance(v, list) else []) for v in stage):
                hits.append((w["name"], w.get("status"), t))
    return hits


def guard(a: Agency, do: bool) -> bool:
    ok = True
    if do:
        try:
            a.call("POST", BACKEND, f"/workflow/{LOC}/tags/create", body={"tag": TAG})
        except GHLError as exc:
            if exc.status != 409:
                raise
    for t in a.triggers(LOC, QS_FLOW):
        if t.get("deleted") or t.get("type") != "pipeline_stage_updated":
            continue
        if any(c.get("field") == "contact.tags" and c.get("value") == TAG for c in t["conditions"]):
            print(f"   = Quote Sent Follow-up trigger {t['id']}: filtro '{TAG}' já está lá (ativo={t.get('active')})")
            continue
        print(f"   + Quote Sent Follow-up trigger {t['id']}: + Doesn't Have Tag '{TAG}'")
        if not do:
            continue
        BDIR.mkdir(parents=True, exist_ok=True)
        (BDIR / f"trigger-{t['id']}-{stamp()}.json").write_text(json.dumps(t, ensure_ascii=False, indent=1))
        body = {k: v for k, v in t.items() if k not in DROP}
        body["conditions"] = t["conditions"] + [dict(FILTER)]
        a.call("PUT", BACKEND, f"/workflow/{LOC}/trigger/{t['id']}", body=body)
        time.sleep(2)
        after = next(x for x in a.triggers(LOC, QS_FLOW) if x["id"] == t["id"])
        good = after.get("active") and after.get("targetActionId") == t.get("targetActionId") and \
            [c for c in after["conditions"] if c.get("field") != "contact.tags"] == t["conditions"] and \
            any(c.get("operator") == "index-of-false" and c.get("value") == TAG for c in after["conditions"])
        ok &= bool(good)
        print(f"     {'✓' if good else '✗ VERIFICAR'} filtro gravado · ativo={after.get('active')} · alvo mantido")
    return ok


def plan(a: Agency) -> None:
    stages = {s["id"]: s["name"] for p in a.pipelines(LOC) for s in p["stages"]}
    print("== gatilhos que reagem a card em Quote Sent (ou a qualquer etapa):")
    for name, status, t in stage_triggers(a):
        print(f"   {status:9} {name} · {t['type']} · {[(c.get('title'), c.get('value')) for c in t['conditions']]}")
    print("== cards:")
    for name, cid in CONTACTS.items():
        c = a.call("GET", SERVICES, f"/contacts/{cid}")["contact"]
        cs = cards(a, cid)
        print(f"   {name}: {c.get('firstName')} {c.get('lastName')} · dnd={c.get('dnd')} · "
              f"{[(stages.get(o['pipelineStageId']), o['status'], o.get('source')) for o in cs] or 'SEM CARD'}")
    guard(a, False)


def create_copy(a: Agency, parent: str | None, mark: str, zz: str) -> tuple[str, str]:
    """ZZ TEST copy: Quote Sent trigger with the same guard + 'has zz tag' (only test contacts), one tag step."""
    first = str(uuid.uuid4())
    tpl = [{"id": first, "order": 0, "name": "Mark entered", "type": "add_contact_tag",
            "attributes": {"type": "add_contact_tag", "tags": [mark]}}]
    wid = (lambda r: r.get("id") or r.get("_id"))(a.call("POST", BACKEND, f"/workflow/{LOC}",
                                                          body={"name": "ZZ TEST quote sent guard", "parentId": parent,
                                                                "status": "draft"}))
    body = {"name": "ZZ TEST quote sent guard", "version": 1, "status": "draft", "parentId": parent,
            "allowMultiple": False, "workflowData": {"templates": tpl}}
    a.call("PUT", BACKEND, f"/workflow/{LOC}/{wid}", body=body)
    real = next(t for t in a.triggers(LOC, QS_FLOW) if not t.get("deleted") and t.get("type") == "pipeline_stage_updated")
    trig = {"type": "pipeline_stage_updated", "name": "Pipeline Stage Changed", "masterType": "highlevel",
            "schedule_config": {}, "workflowId": wid, "workflow_id": wid, "location_id": LOC, "targetActionId": first,
            "actions": [{"workflow_id": wid, "type": "add_to_workflow"}],
            "conditions": real["conditions"] + [{"field": "contact.tags", "id": "has-tag", "type": "select",
                                                 "title": "Has Tag", "value": zz, "operator": "index-of-true"}]}
    if not any(c.get("value") == TAG for c in trig["conditions"]):
        raise SystemExit("rodar `guard` antes do teste: o teste usa as condições do gatilho real")
    t = a.call("POST", BACKEND, f"/workflow/{LOC}/trigger", body=trig)
    a.call("PUT", BACKEND, f"/workflow/{LOC}/trigger/{t['id']}", body={**trig, "id": t["id"]})
    a.call("PUT", BACKEND, f"/workflow/{LOC}/{wid}", body={**body, "status": "published",
                                                         "version": a.workflow(LOC, wid).get("version", 1)})
    return wid, first


def drop_flow(a: Agency, wid: str) -> None:
    live = a.workflow(LOC, wid)
    a.call("PUT", BACKEND, f"/workflow/{LOC}/{wid}", body={"name": live["name"], "version": live.get("version", 1),
                                                         "status": "draft", "workflowData": live["workflowData"]})
    a.call("DELETE", BACKEND, f"/workflow/{LOC}/{wid}")


def leave_qs(a: Agency, cid: str) -> str:
    try:
        a.call("DELETE", SERVICES, f"/contacts/{cid}/workflow/{QS_FLOW}")
        return "ok"
    except GHLError as exc:
        return f"{exc.status}"


def test(a: Agency) -> int:
    st = int(time.time())
    zz, mark = f"zz sf qs {st}", f"zz sf qs entered {st}"
    parent = a.workflow(LOC, QS_FLOW).get("parentId")
    wid, made = None, {}
    try:
        wid, _ = create_copy(a, parent, mark, zz)
        time.sleep(8)
        for case in ("quoted", "control"):  # e-mail only (no phone): nothing can text anyone
            made[case] = a.call("POST", SERVICES, "/contacts/", body={
                "locationId": LOC, "firstName": "ZZ Test", "lastName": f"quote sent {case}",
                "email": f"pedro+sf-qs-{case}-{st}@poolprofits.com",
                "tags": [zz] + ([TAG] if case == "quoted" else [])})["contact"]["id"]
        time.sleep(5)
        opp = {}
        for case, cid in made.items():
            opp[case] = a.call("POST", SERVICES, "/opportunities/", body={
                "locationId": LOC, "pipelineId": PIPELINE, "pipelineStageId": NEW_LEAD, "contactId": cid,
                "name": f"ZZ Test quote sent {case}", "status": "open"})["opportunity"]["id"]
        time.sleep(10)
        for case in made:
            a.call("PUT", SERVICES, f"/opportunities/{opp[case]}", body={"pipelineStageId": QUOTE_SENT})
        time.sleep(60)
        bad = 0
        for case, cid in made.items():
            tags = set(a.call("GET", SERVICES, f"/contacts/{cid}")["contact"].get("tags") or [])
            o = a.call("GET", SERVICES, f"/opportunities/{opp[case]}")["opportunity"]
            entered = mark in tags
            ok = o["pipelineStageId"] == QUOTE_SENT and entered == (case == "control")
            bad += not ok
            print(f"   {'✓' if ok else '✗'} {case}: card em Quote Sent={o['pipelineStageId'] == QUOTE_SENT} · "
                  f"entrou no fluxo de Quote Sent (cópia)={entered}")
        return 1 if bad else 0
    finally:
        for cid in made.values():
            leave_qs(a, cid)  # the control also entered the real Quote Sent Follow-up (1-day wait): out now
            for o in cards(a, cid):
                a.call("DELETE", SERVICES, f"/opportunities/{o['id']}")
            a.call("DELETE", SERVICES, f"/contacts/{cid}")
        if wid:
            drop_flow(a, wid)
        print("   limpo (cópia, 2 contatos, 2 cards).")


def apply(a: Agency) -> int:
    if not guard(a, True):
        return 1
    since = int(time.time() * 1000)
    BDIR.mkdir(parents=True, exist_ok=True)
    moved = {}
    for name, cid in CONTACTS.items():
        cs = [o for o in cards(a, cid) if o["status"] == "open"]
        if len(cs) != 1:
            print(f"   ✗ {name}: {len(cs)} cards abertos — pulado (revisar à mão)")
            continue
        o = cs[0]
        if o["pipelineStageId"] == QUOTE_SENT:
            print(f"   = {name}: já em Quote Sent")
            continue
        (BDIR / f"opportunity-{o['id']}-{stamp()}.json").write_text(json.dumps(o, ensure_ascii=False, indent=1))
        a.call("POST", SERVICES, f"/contacts/{cid}/tags", body={"tags": [TAG]})
        moved[name] = (cid, o["id"])
    time.sleep(10)
    for name, (cid, oid) in moved.items():
        a.call("PUT", SERVICES, f"/opportunities/{oid}", body={"pipelineStageId": QUOTE_SENT})
        print(f"   → {name}: card {oid} → Quote Sent")
    time.sleep(90)
    bad = 0
    for name, (cid, oid) in moved.items():
        left = leave_qs(a, cid)
        o = a.call("GET", SERVICES, f"/opportunities/{oid}")["opportunity"]
        a.call("DELETE", SERVICES, f"/contacts/{cid}/tags", body={"tags": [TAG]})
        sent = outbound_since(a, cid, since)
        ok = o["pipelineStageId"] == QUOTE_SENT and o["status"] == "open" and not sent
        bad += not ok
        print(f"   {'✓' if ok else '✗'} {name}: Quote Sent={o['pipelineStageId'] == QUOTE_SENT} · status {o['status']} · "
              f"saídas desde o início: {sent or 'nenhuma'} · remove-from-workflow {left}")
    return 1 if bad else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("mode", choices=["plan", "guard", "test", "apply", "check"])
    parser.add_argument("--since", type=int, help="check: epoch ms of the apply")
    args = parser.parse_args()
    load_dotenv()
    a = Agency()
    if not a.location(LOC)["name"].startswith("Stay Fresh"):
        sys.exit("sub-conta errada")
    if args.mode == "plan":
        plan(a)
        return 0
    if args.mode == "guard":
        return 0 if guard(a, True) else 1
    if args.mode == "test":
        return test(a)
    if args.mode == "check":  # re-check later: no texts/e-mails went out, cards still in Quote Sent
        for name, cid in CONTACTS.items():
            print(f"   {name}: {[o['pipelineStageId'] == QUOTE_SENT for o in cards(a, cid)]} · "
                  f"saídas: {outbound_since(a, cid, args.since or 0) or 'nenhuma'}")
        return 0
    return apply(a)


if __name__ == "__main__":
    sys.exit(main())
