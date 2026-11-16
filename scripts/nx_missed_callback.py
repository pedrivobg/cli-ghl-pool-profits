#!/usr/bin/env python3
"""NorTex: a caller who hangs up during the IVR and calls right back (answered) gets no missed-call follow-ups (Fareed via
Frank, Pedro approved 16/11).

    ./.venv/bin/python scripts/nx_missed_callback.py plan
    ./.venv/bin/python scripts/nx_missed_callback.py test
    ./.venv/bin/python scripts/nx_missed_callback.py apply

Pedro 16/11: "the first text goes out right away; the follow-ups wait and check whether the person called back".
- "Missed New Lead - Initial SMS Follow-up": SMS 1 stays immediate. On the 30-min timeout, before SMS 2 + tag `follow-up`
  (= "No Response Follow-up"), if/else "Still a missed call?": no `missed call` tag any more (a later call was answered) →
  stop; otherwise as before.
- "IVR SPAM Detection", answered branch (dialCallStatus = completed, after Connect call; no ivr_* step touched): remove tags
  `missed call` + `follow-up` and remove the contact from the SMS flow and from "No Response Follow-up".
Not done (would double SMS 1): removing `ivr pressed 1` in the unanswered branch — "Answered Incoming Call To Pipeline"
would then take its "Hung up" branch and add `missed call` again.
test: ZZ TEST copies (30 min → 1 min), contacts without phone, then everything deleted. GET + backup before each PUT.
"""
from __future__ import annotations

import argparse
import json
import sys
import time

from _common import load_dotenv
from nx_ivr_missed import BDIR, LOC, hang, put, step
from pp_lead_alerts import guard_nodes
from pp_review_fix import read
from pp_source_tags import fresh_ids

from cli_anything.gohighlevel.utils.agency import BACKEND, SERVICES, Agency

IVR, SMS_FLOW, NO_RESP = "IVR SPAM Detection", "Missed New Lead - Initial SMS Follow-up", "No Response Follow-up"
MISSED, FOLLOW = "missed call", "follow-up"
GUARD = "Still a missed call?"


def sms_flow(tpl: list[dict]) -> list[dict] | None:
    out = json.loads(json.dumps(tpl))
    if any(s.get("name") == GUARD for s in out):
        return None
    by = {s["id"]: s for s in out}
    timeout = next(s for s in out if s["type"] == "transition" and s.get("attributes", {}).get("type") == "wait_timeout")
    first = by[timeout["next"]]
    if first["type"] != "sms":
        raise SystemExit("timeout branch não começa no SMS 2")
    c, answered, still = guard_nodes(timeout["id"], timeout["id"], first.get("order", 0), skip=[MISSED])
    c["name"] = c["attributes"]["conditionName"] = GUARD
    answered["name"] = c["attributes"]["branches"][0]["name"] = "Called back, answered"
    still["name"] = c["attributes"]["noneBranchName"] = "Still missed"
    timeout["next"] = c["id"]
    still["next"] = first["id"]
    for s in out:
        if s.get("parent") == timeout["id"] and s["id"] != c["id"]:
            s["parent"] = still["id"]
    first["parentKey"] = still["id"]
    return [*out, c, answered, still]


def answered_steps(wids: list[str]) -> list[dict]:
    return [step("remove_contact_tag", "Remove Tags missed call / follow-up", [MISSED, FOLLOW]),
            {**step("remove_from_workflow", "Stop missed-call follow-ups", []),
             "attributes": {"type": "remove_from_workflow", "workflow_id": wids}}]


def ivr_flow(tpl: list[dict], wids: list[str]) -> list[dict] | None:
    out = json.loads(json.dumps(tpl))
    if any(s["type"] == "remove_from_workflow" for s in out):
        return None
    cond = next(s for s in out if s["type"] == "if_else" and "dialCallStatus" in json.dumps(s.get("attributes")))
    yes = cond["attributes"]["branches"][0]["id"]
    done = next(s for s in out if s.get("parent") == cond["id"] and s["id"] != yes)  # the "else" = completed branch
    if done.get("next"):
        raise SystemExit("ramo atendido já tem passos")
    return [*out, *hang(done, answered_steps(wids))]


def make(a: Agency, name: str, tpl: list[dict]) -> str:
    res = a.call("POST", BACKEND, f"/workflow/{LOC}", body={"name": name, "status": "draft"})
    wid = res.get("id") or res.get("_id")
    body = {"name": name, "version": 1, "status": "draft", "allowMultiple": True, "workflowData": {"templates": tpl}}
    a.call("PUT", BACKEND, f"/workflow/{LOC}/{wid}", body=body)
    live = a.workflow(LOC, wid)
    a.call("PUT", BACKEND, f"/workflow/{LOC}/{wid}", body={**body, "status": "published", "version": live.get("version", 1),
                                                         "workflowData": {"templates": live["workflowData"]["templates"]}})
    return wid


def drop(a: Agency, wid: str) -> None:
    live = a.workflow(LOC, wid)
    a.call("PUT", BACKEND, f"/workflow/{LOC}/{wid}", body={"name": live["name"], "version": live.get("version", 1),
           "status": "draft", "workflowData": {"templates": live["workflowData"]["templates"]}})
    a.call("DELETE", BACKEND, f"/workflow/{LOC}/{wid}")


def test(a: Agency, new_sms: list[dict]) -> int:
    tpl = fresh_ids(new_sms)
    for s in tpl:
        if s["type"] == "wait":
            s["attributes"]["startAfter"] = {"type": "minutes", "value": 1, "when": "after"}
    sms_id = make(a, "ZZ TEST missed SMS guard", tpl)
    stop_tpl = answered_steps([sms_id])
    for i, s in enumerate(stop_tpl):
        s["order"] = i
        if i:
            s["parentKey"] = stop_tpl[i - 1]["id"]
        if i + 1 < len(stop_tpl):
            s["next"] = stop_tpl[i + 1]["id"]
    stop_id = make(a, "ZZ TEST answered stop", stop_tpl)
    ts, made, bad = int(time.time()), {}, 0
    for case in ("still", "untagged", "answered"):
        made[case] = a.call("POST", SERVICES, "/contacts/", body={
            "locationId": LOC, "firstName": "ZZ Test", "lastName": f"callback {case}", "tags": [MISSED],
            "email": f"pedro+nx-cb-{case}-{ts}@poolprofits.com"})["contact"]["id"]
    time.sleep(3)
    for cid in made.values():
        a.call("POST", SERVICES, f"/contacts/{cid}/workflow/{sms_id}", body={})
    time.sleep(15)
    a.call("DELETE", SERVICES, f"/contacts/{made['untagged']}/tags", body={"tags": [MISSED]})
    a.call("POST", SERVICES, f"/contacts/{made['answered']}/workflow/{stop_id}", body={})
    time.sleep(150)
    for case, cid in made.items():
        tags = set(a.call("GET", SERVICES, f"/contacts/{cid}")["contact"].get("tags") or [])
        ok = (FOLLOW in tags) if case == "still" else (FOLLOW not in tags and MISSED not in tags)
        bad += not ok
        print(f"   {'✓' if ok else '✗'} {case}: tags {sorted(tags)}")
        a.call("DELETE", SERVICES, f"/contacts/{cid}")
    drop(a, sms_id)
    drop(a, stop_id)
    print("   limpo (contatos e 2 workflows ZZ TEST apagados).")
    return 1 if bad else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("mode", choices=["plan", "test", "apply"])
    args = parser.parse_args()
    load_dotenv()
    a = Agency()
    if not a.location(LOC)["name"].lower().startswith("nortex"):
        sys.exit("sub-conta errada")
    flows = {w["name"]: w["id"] for w in a.workflows(LOC)}
    live_sms, live_ivr = read(a, LOC, flows[SMS_FLOW]), read(a, LOC, flows[IVR])
    new_sms = sms_flow(live_sms["workflowData"]["templates"])
    new_ivr = ivr_flow(live_ivr["workflowData"]["templates"], [flows[SMS_FLOW], flows[NO_RESP]])
    print(f"   {SMS_FLOW}: {'if/else ' + GUARD + ' antes do SMS 2' if new_sms else 'já feito'}")
    print(f"   {IVR}: {'ramo atendido → tira tags + tira das 2 sequências' if new_ivr else 'já feito'}")
    if args.mode == "plan":
        return 0
    if args.mode == "test":
        return test(a, new_sms or live_sms["workflowData"]["templates"])
    BDIR.mkdir(parents=True, exist_ok=True)
    for wid, live, new in ((flows[SMS_FLOW], live_sms, new_sms), (flows[IVR], live_ivr, new_ivr)):
        if not new:
            continue
        after = put(a, wid, live, new)
        types = [s["type"] for s in after["workflowData"]["templates"]]
        print(f"   ✓ {live['name']}: {after['status']}, {len(types)} passos, ivr_* {sum(t.startswith('ivr_') for t in types)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
