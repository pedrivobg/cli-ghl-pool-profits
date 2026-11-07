#!/usr/bin/env python3
"""Pool Duck Franchising: SMS when a card moves in Franchise Development (Lee Majidimehr, e-mail, nov/2026).

    GHL_AGENCY=poolduck ./.venv/bin/python scripts/pd_franchise_stage_sms.py plan
    GHL_AGENCY=poolduck ./.venv/bin/python scripts/pd_franchise_stage_sms.py test    # ZZ TEST copies, tags instead of SMS
    GHL_AGENCY=poolduck ./.venv/bin/python scripts/pd_franchise_stage_sms.py apply   # 6 workflows, published

Texts: config/pd_franchise_stage_sms.json (Lee's wording). Sender: the account's default number, Lee's 813-710-4144
(the SMS step has no "from", like the Tampa Show follow-up).
- 4 sequences, each started by the card entering its stage (pipeline_stage_updated, Franchise Development):
  📞 Intro Call Booked → Intro Call Nurture (SMS 24 h later); 👻 Missed Intro Call → 3 SMS (20 min, +24 h, +2 days);
  🖥️ Webinar → Webinar Nurture (SMS 24 h later); 👻 Missed Webinar → 3 SMS (20 min, +24 h, +2 days).
  Every wait also holds the text until 9 AM–8 PM Eastern (a lead moved at night is not texted at night).
- Leaving the stage ends the sequence: each sequence starts by removing the contact from the other three, and
  "Stage SMS Stop (Left Stage)" (card enters any other stage of the pipeline, or turns won/lost/abandoned) removes
  from all four.
- The two "Missed" sequences also stop on a reply (native "Stop on response"; a STOP reply is a reply too, and GHL
  never texts a DND contact) and on any appointment booked ("Missed Follow-up Stop (Booked)", any calendar).
- Re-entry on everywhere: a lead who misses a second call (moved back into the stage) gets the sequence again. No
  overlap: moving out of the stage always ends the running copy first.
test: copies named "ZZ TEST …", every trigger filtered by a test tag (a real card moved meanwhile does not enter),
1–2 min waits, "add tag" in place of each SMS, test contacts without phone; everything deleted at the end.
Tested 07/11: a card created straight in a stage fires pipeline_stage_updated too (no opportunity_created trigger:
it would enroll twice). A reply cannot be simulated (inbound message API refuses the Firebase token).
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import uuid

from _common import ROOT, load_dotenv

from cli_anything.gohighlevel.utils.agency import BACKEND, SERVICES, Agency, GHLError

CFG = json.loads((ROOT / "config" / "pd_franchise_stage_sms.json").read_text())
LOC, PIPELINE = CFG["location"], CFG["pipeline"]
FOLDER = "f766e194-6a51-4e79-a52e-e657a6400205"  # Franchise Drip Campaigns (Tampa Show flows)
BOOKED_STOP = "Franchise Dev - Missed Follow-up Stop (Booked)"
LEFT_STOP = "Franchise Dev - Stage SMS Stop (Left Stage)"
WINDOW = ("09:00", "20:00")
EVERY_DAY = [0, 1, 2, 3, 4, 5, 6]
TEST_TAG = "zz test franchise stage sms"
BDIR = ROOT / "backup" / "pool-duck-franchising"


FULL: dict[str, str] = {}  # stage id → name as in the pipeline


def stages(a: Agency) -> dict[str, str]:
    """Stage name without the emoji → id."""
    p = next(p for p in a.pipelines(LOC) if p["id"] == PIPELINE)
    FULL.update({s["id"]: s["name"] for s in p["stages"]})
    return {s["name"].split(" ", 1)[-1].strip() if not s["name"][0].isalnum() else s["name"].strip(): s["id"] for s in p["stages"]}


def sms_text(text: str) -> str:
    for k, v in CFG["links"].items():
        text = text.replace("{" + k + "}", v)  # not .format: {{merge}}
    return text


def wait(name: str, after: list, window: bool) -> dict:
    a = {"type": "time", "startAfter": {"type": after[0], "value": after[1], "when": "after"}, "name": name, "cat": "",
         "isHybridAction": True, "hybridActionType": "wait", "convertToMultipath": False, "transitions": []}
    if window:
        a["window"] = {"condition": "when", "days": EVERY_DAY, "start": WINDOW[0], "end": WINDOW[1]}
        a["windowCondition"] = {"field": "", "operator": "", "value": ""}
    return a


def chain(items: list[tuple[str, str, dict]]) -> list[dict]:
    ids = [str(uuid.uuid4()) for _ in items]
    out = []
    for i, (kind, name, attrs) in enumerate(items):
        s = {"id": ids[i], "order": i, "name": name, "type": kind, "attributes": attrs}
        if i:
            s["parentKey"] = ids[i - 1]
        if i + 1 < len(items):
            s["next"] = ids[i + 1]
        out.append(s)
    return out


def test_tag(seq: dict, n: int) -> str:
    return f"zz pdfs {seq['key']} {n}"


def seq_steps(seq: dict, others: dict[str, str], test: bool) -> list[dict]:
    items = [("remove_from_workflow", "Stop the other stage sequences",
              {"type": "remove_from_workflow", "workflow_id": list(others.values())})]
    for n, m in enumerate(seq["messages"], 1):
        if test:
            items.append(("wait", f"Wait ({m['label']})", wait(m["label"], ["minutes", 1 if n == 1 else 2], False)))
            items.append(("add_contact_tag", f"SMS {n} (test tag)", {"type": "add_contact_tag", "tags": [test_tag(seq, n)]}))
        else:
            items.append(("wait", f"Wait {m['label']} (9 AM-8 PM ET)", wait(m["label"], m["after"], True)))
            items.append(("sms", f"SMS {n} - {m['label']}", {"body": sms_text(m["text"]), "attachments": []}))
    return chain(items)


def stop_steps(wids: list[str], name: str) -> list[dict]:
    return chain([("remove_from_workflow", name, {"type": "remove_from_workflow", "workflow_id": wids})])


def tag_cond() -> dict:
    return {"field": "contact.tags", "id": "has-tag", "title": "Has Tag", "type": "select", "operator": "index-of-true",
            "value": TEST_TAG}


def stage_trigger(sid: str, name: str, kind: str = "pipeline_stage_updated") -> dict:
    return {"type": kind, "name": name, "conditions": [
        {"operator": "==", "field": "opportunity.pipelineId", "value": PIPELINE, "title": "In pipeline", "type": "select"},
        {"operator": "==", "field": "opportunity.pipelineStageId", "value": sid, "title": "Pipeline stage", "type": "select"}]}


def status_trigger(status: str) -> dict:
    return {"type": "opportunity_status_changed", "name": f"Status: {status}", "conditions": [
        {"operator": "==", "field": "opportunity.pipelineId", "value": PIPELINE, "title": "In pipeline", "type": "select"},
        {"operator": "==", "field": "opportunity.status", "value": status, "title": "Moved to status", "type": "select",
         "id": "moved-to-status"}]}


def booked_trigger(status: str) -> dict:
    return {"type": "appointment", "name": f"Appointment {status} (any calendar)", "conditions": [
        {"operator": "==", "field": "appointment.eventType", "value": "normal", "title": "Event type", "type": "select"},
        {"operator": "is-any-of", "field": "contactMode", "value": ["contact"], "type": "input"},
        {"operator": "==", "field": "appointment.status", "value": status, "title": "Appointment status is", "type": "select"}]}


def add_trigger(a: Agency, wid: str, first: str, body: dict, test: bool) -> None:
    body = json.loads(json.dumps(body))
    if test:
        body["conditions"].append(tag_cond())
    trig = {"masterType": "highlevel", "schedule_config": {}, "workflowId": wid, "workflow_id": wid, "location_id": LOC,
            "actions": [{"workflow_id": wid, "type": "add_to_workflow"}], "targetActionId": first, **body}
    t = a.call("POST", BACKEND, f"/workflow/{LOC}/trigger", body=trig)
    a.call("PUT", BACKEND, f"/workflow/{LOC}/trigger/{t['id']}", body={**trig, "id": t["id"]})


def create(a: Agency, name: str) -> str:
    res = a.call("POST", BACKEND, f"/workflow/{LOC}", body={"name": name, "parentId": FOLDER, "status": "draft"})
    return res.get("id") or res.get("_id")


def fill(a: Agency, wid: str, name: str, tpl: list[dict], stop_on_reply: bool) -> None:
    live = a.workflow(LOC, wid)
    a.call("PUT", BACKEND, f"/workflow/{LOC}/{wid}", body={
        "name": name, "version": live.get("version", 1), "status": "draft", "parentId": FOLDER, "allowMultiple": True,
        "stopOnResponse": stop_on_reply, "workflowData": {"templates": tpl}})


def publish(a: Agency, wid: str) -> dict:
    live = a.workflow(LOC, wid)
    a.call("PUT", BACKEND, f"/workflow/{LOC}/{wid}", body={
        "name": live["name"], "version": live.get("version", 1), "status": "published", "parentId": live.get("parentId"),
        "workflowData": {"templates": live["workflowData"]["templates"]}})
    time.sleep(3)
    return a.workflow(LOC, wid)


def drop(a: Agency, wid: str) -> None:
    try:
        live = a.workflow(LOC, wid)
        a.call("PUT", BACKEND, f"/workflow/{LOC}/{wid}", body={"name": live["name"], "version": live.get("version", 1),
                                                             "status": "draft", "workflowData": {"templates": live["workflowData"]["templates"]}})
    except GHLError:
        pass
    a.call("DELETE", BACKEND, f"/workflow/{LOC}/{wid}")


def build(a: Agency, st: dict[str, str], test: bool) -> dict[str, str]:
    """All six workflows (draft), triggers included. Returns name → id."""
    pre = "ZZ TEST " if test else ""
    seqs = CFG["sequences"]
    ids = {s["key"]: create(a, pre + s["name"]) for s in seqs}
    for s in seqs:
        tpl = seq_steps(s, {k: v for k, v in ids.items() if k != s["key"]}, test)
        fill(a, ids[s["key"]], pre + s["name"], tpl, s["stop_on_reply"])
        add_trigger(a, ids[s["key"]], tpl[0]["id"], stage_trigger(st[s["stage"]], f"Card enters {s['stage']}"), test)
    out = {pre + s["name"]: ids[s["key"]] for s in seqs}
    missed = [ids[s["key"]] for s in seqs if s["stop_on_reply"]]
    b = create(a, pre + BOOKED_STOP)
    tpl = stop_steps(missed, "Stop the Missed Intro Call / Missed Webinar texts")
    fill(a, b, pre + BOOKED_STOP, tpl, False)
    for status in ("confirmed", "new"):
        add_trigger(a, b, tpl[0]["id"], booked_trigger(status), test)
    out[pre + BOOKED_STOP] = b
    left = create(a, pre + LEFT_STOP)
    tpl = stop_steps(list(ids.values()), "Stop the 4 stage sequences")
    fill(a, left, pre + LEFT_STOP, tpl, False)
    own = {st[s["stage"]] for s in seqs}
    for sid in FULL:
        if sid not in own:
            add_trigger(a, left, tpl[0]["id"], stage_trigger(sid, f"Card enters {FULL[sid]}"), test)
    for status in ("won", "lost", "abandoned"):
        add_trigger(a, left, tpl[0]["id"], status_trigger(status), test)
    out[pre + LEFT_STOP] = left
    return out


def tags(a: Agency, cid: str) -> set[str]:
    return set(a.call("GET", SERVICES, f"/contacts/{cid}")["contact"].get("tags") or [])


def test(a: Agency, st: dict[str, str]) -> int:
    seq = {s["key"]: s for s in CFG["sequences"]}
    made, wids, stamp = {}, {}, int(time.time())
    T = lambda k, n: test_tag(seq[k], n)  # noqa: E731
    try:
        wids = build(a, st, True)
        for name in [n for n in wids if "Stop" in n] + [n for n in wids if "Stop" not in n]:
            got = publish(a, wids[name])
            print(f"   {name}: {got['status']} · re-entry {got.get('allowMultiple')} · stop on response {got.get('stopOnResponse')}")
        booked_copy = wids["ZZ TEST " + BOOKED_STOP]
        time.sleep(5)
        start = {"A": "New Lead", "B": "Webinar", "C": "Intro Call Booked", "D": "Intro Call Booked", "E": "Webinar",
                 "F": "Webinar", "G": "Intro Call Booked"}
        for case, stage in start.items():
            cid = a.call("POST", SERVICES, "/contacts/", body={
                "locationId": LOC, "firstName": "ZZ Test", "lastName": f"stage sms {case}", "tags": [TEST_TAG],
                "email": f"pedro+pdfs-{case.lower()}-{stamp}@poolprofits.com"})["contact"]["id"]
            o = a.call("POST", SERVICES, "/opportunities/", body={"locationId": LOC, "pipelineId": PIPELINE, "contactId": cid,
                                                                  "pipelineStageId": st[stage], "name": f"ZZ Test stage sms {case}",
                                                                  "status": "open"})
            made[case] = (cid, (o.get("opportunity") or o)["id"])
        time.sleep(10)
        move = lambda case, stage: a.call("PUT", SERVICES, f"/opportunities/{made[case][1]}",  # noqa: E731
                                          body={"pipelineId": PIPELINE, "pipelineStageId": st[stage]})
        move("A", "Intro Call Booked")
        for c in "CDG":
            move(c, "Missed Intro Call")
        for c in "EF":
            move(c, "Missed Webinar")
        t0 = time.time()
        # after SMS 1 (tag 1): D books (stop flow), E → Unit Economics, F → Intro Call Booked, G → abandoned
        act = {"D": ("missed-intro", lambda: a.call("POST", SERVICES, f"/contacts/{made['D'][0]}/workflow/{booked_copy}", body={})),
               "E": ("missed-webinar", lambda: move("E", "Unit Economics")),
               "F": ("missed-webinar", lambda: move("F", "Intro Call Booked")),
               "G": ("missed-intro", lambda: a.call("PUT", SERVICES, f"/opportunities/{made['G'][1]}", body={"status": "abandoned"}))}
        done = set()
        while len(done) < len(act) and time.time() - t0 < 200:
            time.sleep(8)
            for case, (k, fn) in act.items():
                if case not in done and T(k, 1) in tags(a, made[case][0]):
                    fn()
                    done.add(case)
                    print(f"   {case}: SMS 1 at {int(time.time() - t0)} s → stop action")
        missing = set(act) - done
        while time.time() - t0 < 420 and not {T("missed-intro", 3)} <= tags(a, made["C"][0]):
            time.sleep(15)
        time.sleep(30)
        want = {"A": {T("intro", 1)}, "B": {T("webinar", 1)},
                "C": {T("missed-intro", 1), T("missed-intro", 2), T("missed-intro", 3)},
                "D": {T("missed-intro", 1)}, "E": {T("missed-webinar", 1)}, "F": {T("missed-webinar", 1), T("intro", 1)},
                "G": {T("missed-intro", 1)}}
        about = {"A": "New Lead → Intro Call Booked", "B": "card created straight in Webinar (no move)",
                 "C": "Missed Intro Call, full sequence", "D": "Missed Intro Call, booked after SMS 1",
                 "E": "Missed Webinar, moved to Unit Economics after SMS 1", "F": "Missed Webinar, moved to Intro Call Booked after SMS 1",
                 "G": "Missed Intro Call, card abandoned after SMS 1"}
        bad = 0
        for case, (cid, _) in made.items():
            got = {t for t in tags(a, cid) if t.startswith("zz pdfs")}
            ok = got == want[case] and case not in missing
            bad += not ok and case != "B"
            print(f"   {'✓' if ok else ('?' if case == 'B' else '✗')} {case} {about[case]}: {sorted(got)}")
        # re-entry: C out of the stage and back in → SMS 1 again
        cid = made["C"][0]
        a.call("DELETE", SERVICES, f"/contacts/{cid}/tags", body={"tags": sorted(want["C"])})
        move("C", "Unit Economics")
        time.sleep(15)
        move("C", "Missed Intro Call")
        t1 = time.time()
        while time.time() - t1 < 180 and T("missed-intro", 1) not in tags(a, cid):
            time.sleep(10)
        ok = T("missed-intro", 1) in tags(a, cid)
        bad += not ok
        print(f"   {'✓' if ok else '✗'} C re-entry (moved out and back into Missed Intro Call): SMS 1 again = {ok}")
        return 1 if bad else 0
    finally:
        for cid, oid in made.values():
            for call in (f"/opportunities/{oid}", f"/contacts/{cid}"):
                try:
                    a.call("DELETE", SERVICES, call)
                except GHLError:
                    pass
        for wid in wids.values():
            drop(a, wid)
        for t in a.call("GET", SERVICES, f"/locations/{LOC}/tags").get("tags", []):
            if t["name"].startswith("zz pdfs") or t["name"] == TEST_TAG:
                a.call("DELETE", SERVICES, f"/locations/{LOC}/tags/{t['id']}")
        print("   limpo (contatos, cards, workflows ZZ TEST, tags de teste)")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("mode", choices=["plan", "test", "apply"])
    args = parser.parse_args()
    load_dotenv()
    a = Agency()
    if a.location(LOC)["name"] != "Pool Duck Franchising, LLC":
        sys.exit("token/sub-conta errados (GHL_AGENCY=poolduck)")
    st = stages(a)
    missing = [s["stage"] for s in CFG["sequences"] if s["stage"] not in st]
    if missing:
        sys.exit(f"etapas não encontradas em Franchise Development: {missing}")
    flows = {w["name"]: w["id"] for w in a.workflows(LOC)}
    names = [s["name"] for s in CFG["sequences"]] + [BOOKED_STOP, LEFT_STOP]

    if args.mode == "plan":
        for s in CFG["sequences"]:
            print(f"== {s['name']} ← card enters {s['stage']} ({st[s['stage']]}) · stop on reply {s['stop_on_reply']}"
                  f" · {'existe' if s['name'] in flows else 'novo'}")
            for st_ in seq_steps(s, {"x": "x"}, False)[1:]:
                at = st_["attributes"]
                print(f"   [{st_['type']}] {st_['name']}" + (f": {at['body']}" if st_["type"] == "sms" else ""))
        print(f"== {BOOKED_STOP}: appointment confirmed/new (any calendar) → out of the 2 Missed sequences")
        print(f"== {LEFT_STOP}: card enters any of the other {len(st) - 4} stages, or won/lost/abandoned → out of all 4")
        return 0

    if args.mode == "test":
        return test(a, st)

    if set(names) & set(flows):
        sys.exit(f"já existem: {sorted(set(names) & set(flows))} (conferir antes de recriar)")
    ids = build(a, st, False)
    BDIR.mkdir(parents=True, exist_ok=True)
    for name in [BOOKED_STOP, LEFT_STOP] + [s["name"] for s in CFG["sequences"]]:  # exits first
        got = publish(a, ids[name])
        trs = [t for t in a.triggers(LOC, ids[name]) if not t.get("deleted")]
        (BDIR / f"workflow-{ids[name]}-created-{time.strftime('%Y%m%d-%H%M%S')}.json").write_text(json.dumps({**got, "triggers": trs}))
        ok = got["status"] == "published" and trs and all(t.get("active") for t in trs) and got.get("allowMultiple")
        print(f"   {'✓' if ok else '✗ VERIFICAR'} {name} ({ids[name]}): {got['status']} · re-entry {got.get('allowMultiple')}"
              f" · stop on response {got.get('stopOnResponse')} · {len(got['workflowData']['templates'])} passos"
              f" · {len(trs)} gatilhos ativos={sum(bool(t.get('active')) for t in trs)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
