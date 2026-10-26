#!/usr/bin/env python3
"""NorTex: calls that hang up during the IVR (or never press 1) count as missed calls (Val, 27/10).

    ./.venv/bin/python scripts/nx_ivr_missed.py plan
    ./.venv/bin/python scripts/nx_ivr_missed.py test --to pedro@poolprofits.com
    ./.venv/bin/python scripts/nx_ivr_missed.py apply

The line rings through "IVR SPAM Detection" ("press 1"). With an IVR every call ends as "completed", so the
"Missed Incoming Call To Pipeline" trigger (busy/no-answer/…) never fires, and a caller who hangs up during the message
never reaches "Connect call" (where the missed-call tag lived): no tag, no text. Live 20-26/10: 5 calls of 5-13 s, all
handled as answered calls.
- IVR: "NOT SPAM" (pressed 1) → tag `ivr pressed 1` before ringing; the missed branch after Connect call removes
  `missed call` before adding it, so a repeat caller fires the text again (the trigger is "tag added").
- "Answered Incoming Call To Pipeline" (fires for every IVR call): if/else "Pressed 1 in the IVR?":
    Pressed 1 → remove `ivr pressed 1`, then the steps it had.
    Hung up / no key → remove + add `missed call` (→ "Missed New Lead - Initial SMS Follow-up"), then the steps of
                       "Missed Incoming Call To Pipeline" (tags, card in New Lead, task after 1 h).
test: a temporary copy of the new answered-call flow, 2 contacts (with/without the tag, no phone: no SMS goes out);
checks tags/cards; then deletes everything.
GET + backup before each PUT.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import uuid

from _common import ROOT, load_dotenv
from pp_lead_alerts import guard_nodes, retarget
from pp_review_fix import read
from pp_source_tags import fresh_ids, refs_ok

from cli_anything.gohighlevel.utils.agency import BACKEND, SERVICES, Agency

LOC = "k6nDPHktS2PySJoJuwpG"
TAG, MISSED = "ivr pressed 1", "missed call"
IVR, ANSWERED, MISSED_FLOW = "IVR SPAM Detection", "Answered Incoming Call To Pipeline", "Missed Incoming Call To Pipeline"
SMS_FLOW = "Missed New Lead - Initial SMS Follow-up"
NAME = "Pressed 1 in the IVR?"
BDIR = ROOT / "backup" / "nortex-pools"


def step(kind: str, name: str, tags: list[str]) -> dict:
    return {"id": str(uuid.uuid4()), "order": 0, "name": name, "type": kind, "attributes": {"type": kind, "tags": tags}}


def chain_of(tpl: list[dict]) -> list[dict]:
    by = {s["id"]: s for s in tpl}
    out = [next(s for s in tpl if not s.get("parentKey"))]
    while isinstance(out[-1].get("next"), str) and out[-1]["next"] in by:
        out.append(by[out[-1]["next"]])
    if len(out) != len(tpl):
        raise SystemExit("esperava uma cadeia linear")
    return json.loads(json.dumps(out))


def hang(branch: dict, steps: list[dict]) -> list[dict]:
    for i, s in enumerate(steps):
        s.update(order=i, parent=branch["id"], parentKey=steps[i - 1]["id"] if i else branch["id"])
        s["next"] = steps[i + 1]["id"] if i + 1 < len(steps) else None
        if s["next"] is None:
            s.pop("next")
    branch["next"] = steps[0]["id"]
    return steps


def answered(tpl: list[dict], missed_tpl: list[dict]) -> list[dict] | None:
    """The answered-call chain under "Pressed 1"; the missed-call chain under "Hung up / no key"."""
    if any(s["type"] == "if_else" for s in tpl):
        return None
    c, hung, pressed = guard_nodes(None, None, 0, skip=[TAG])
    c["name"] = c["attributes"]["conditionName"] = NAME
    hung["name"] = c["attributes"]["branches"][0]["name"] = "Hung up / no key"
    pressed["name"] = c["attributes"]["noneBranchName"] = "Pressed 1"
    yes = hang(hung, [step("remove_contact_tag", f"Remove Tag {MISSED}", [MISSED]), *chain_of(fresh_ids(missed_tpl))])
    no = hang(pressed, [step("remove_contact_tag", f"Remove Tag {TAG}", [TAG]), *chain_of(tpl)])
    return [c, hung, pressed, *yes, *no]


def ivr(tpl: list[dict]) -> list[dict] | None:
    out = json.loads(json.dumps(tpl))
    if any(TAG in json.dumps(s.get("attributes")) for s in out):
        return None
    ok = next(s for s in out if s["type"] == "transition" and s["name"] == "NOT SPAM")
    connect = next(s for s in out if s["id"] == ok["next"])
    add = {**step("add_contact_tag", f"Tag {TAG}", [TAG]), "parent": ok["id"], "parentKey": ok["id"], "next": connect["id"]}
    ok["next"] = add["id"]
    connect.update(parentKey=add["id"], order=1)
    new = [add]
    tag = next(s for s in out if s["type"] == "add_contact_tag" and MISSED in s["attributes"].get("tags", []))
    rem = {**step("remove_contact_tag", f"Remove Tag {MISSED}", [MISSED]), "parent": tag["parent"],
           "parentKey": tag["parentKey"], "next": tag["id"]}
    prev = next(s for s in out if s["id"] == tag["parentKey"])
    prev["next"] = rem["id"]
    tag["parentKey"] = rem["id"]
    new.append(rem)
    return [*out, *new]


def put(a: Agency, wid: str, live: dict, tpl: list[dict]) -> dict:
    BDIR.mkdir(parents=True, exist_ok=True)
    (BDIR / f"workflow-{wid}-{time.strftime('%Y%m%d-%H%M%S')}.json").write_text(json.dumps(live))
    a.call("PUT", BACKEND, f"/workflow/{LOC}/{wid}", body={"name": live["name"], "version": live.get("version", 1),
                                                         "status": live["status"], "parentId": live.get("parentId"),
                                                         "workflowData": {"templates": tpl}})
    time.sleep(2)
    return read(a, LOC, wid)


def test(a: Agency, flows: dict, tpl: list[dict], to: str) -> int:
    res = a.call("POST", BACKEND, f"/workflow/{LOC}", body={"name": "ZZ TEST IVR missed", "status": "draft"})
    wid = res.get("id") or res.get("_id")
    tpl = fresh_ids(tpl)
    body = {"name": "ZZ TEST IVR missed", "version": 1, "status": "draft", "allowMultiple": True,
            "workflowData": {"templates": tpl}}
    a.call("PUT", BACKEND, f"/workflow/{LOC}/{wid}", body=body)
    live = a.workflow(LOC, wid)
    a.call("PUT", BACKEND, f"/workflow/{LOC}/{wid}", body={**body, "status": "published", "version": live.get("version", 1),
                                                         "workflowData": {"templates": live["workflowData"]["templates"]}})
    ts, made, bad = int(time.time()), {}, 0
    for case, tags in (("hung", [MISSED]), ("pressed", [TAG])):  # "hung" already has the tag: a repeat caller
        made[case] = a.call("POST", SERVICES, "/contacts/", body={
            "locationId": LOC, "firstName": "ZZ Test", "lastName": f"ivr {case}", "tags": tags,
            "email": to.replace("@", f"+nx-ivr-{case}-{ts}@")})["contact"]["id"]
    time.sleep(3)
    for cid in made.values():
        a.call("POST", SERVICES, f"/contacts/{cid}/workflow/{wid}", body={})
    time.sleep(40)
    for case, cid in made.items():
        c = a.call("GET", SERVICES, f"/contacts/{cid}")["contact"]
        tags = set(c.get("tags") or [])
        opps = a.call("GET", SERVICES, "/opportunities/search", params={"location_id": LOC, "contact_id": cid}).get("opportunities", [])
        if case == "hung":
            ok = {MISSED, "new lead", "inbound call"} <= tags and len(opps) == 1
        else:
            ok = TAG not in tags and MISSED not in tags and {"new lead", "inbound call"} <= tags and len(opps) == 1
        bad += not ok
        print(f"   {'✓' if ok else '✗'} {case}: tags {sorted(tags)} · cards {[o.get('source') for o in opps]}")
        for o in opps:
            a.call("DELETE", SERVICES, f"/opportunities/{o['id']}")
        a.call("DELETE", SERVICES, f"/contacts/{cid}")
    live = a.workflow(LOC, wid)
    a.call("PUT", BACKEND, f"/workflow/{LOC}/{wid}", body={"name": live["name"], "version": live.get("version", 1),
           "status": "draft", "workflowData": {"templates": live["workflowData"]["templates"]}})
    a.call("DELETE", BACKEND, f"/workflow/{LOC}/{wid}")
    print("   limpo.")
    return 1 if bad else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("mode", choices=["plan", "test", "apply"])
    parser.add_argument("--to")
    args = parser.parse_args()
    load_dotenv()
    a = Agency()
    if not a.location(LOC)["name"].lower().startswith("nortex"):
        sys.exit("sub-conta errada")
    flows = {w["name"]: w["id"] for w in a.workflows(LOC)}
    for t in (TAG,):
        if args.mode != "plan":
            try:
                a.call("POST", BACKEND, f"/workflow/{LOC}/tags/create", body={"tag": t})
            except Exception:  # noqa: BLE001 — already exists
                pass
    live_ivr = read(a, LOC, flows[IVR])
    new_ivr = ivr(live_ivr["workflowData"]["templates"])
    live_ans = read(a, LOC, flows[ANSWERED])
    missed = read(a, LOC, flows[MISSED_FLOW])["workflowData"]["templates"]
    new_ans = answered(live_ans["workflowData"]["templates"], missed)
    print(f"   {IVR}: {'tecla 1 → tag; perdida → tira e põe missed call' if new_ivr else 'já feito'}")
    print(f"   {ANSWERED}: {'condição ' + NAME + f' ({len(new_ans)} passos)' if new_ans else 'já tem if/else'}")
    if new_ans:
        for s in new_ans:
            print(f"      {s.get('name')} [{s['type']}]{' ← ' + str(s.get('parent'))[:8] if s.get('parent') else ''}")
    if args.mode == "test":
        if not args.to:
            parser.error("--to is required in test mode")
        return test(a, flows, new_ans, args.to)
    if args.mode == "apply":
        if new_ivr:
            got = put(a, flows[IVR], live_ivr, new_ivr)
            print(f"      {'✓' if refs_ok(got['workflowData']['templates']) and got['status'] == live_ivr['status'] else '✗'} IVR {got['status']}")
        if new_ans:
            got = put(a, flows[ANSWERED], live_ans, new_ans)
            retarget(a, LOC, flows[ANSWERED], new_ans[0]["id"])
            trs = [t for t in a.triggers(LOC, flows[ANSWERED]) if not t.get("deleted")]
            ok = refs_ok(got["workflowData"]["templates"]) and got["status"] == live_ans["status"] and \
                all(t.get("targetActionId") == new_ans[0]["id"] for t in trs)
            print(f"      {'✓' if ok else '✗ VERIFICAR'} {ANSWERED} {got['status']} · re-entry {got.get('allowMultiple')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
