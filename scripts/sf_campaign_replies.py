#!/usr/bin/env python3
"""Stay Fresh: SMS campaign replies become New Leads, Kris gets the alerts (Val, 04/11).

    ./.venv/bin/python scripts/sf_campaign_replies.py plan
    ./.venv/bin/python scripts/sf_campaign_replies.py test --to pedro@poolprofits.com
    ./.venv/bin/python scripts/sf_campaign_replies.py apply

Val: "when a contact responds to an SMS campaign, their status should update to New Lead and a new opportunity should be
created"; "Mike is receiving notifications, is Kris?". Live state before (04/11):
- "Drain & Wash Campaign - Replies" (reply from a `drain wash sent` contact): tag + SMS/e-mail to Mike only. No card,
  no `new lead` → the 11 replies of 19/10 never reached the pipeline.
- "SMS Customer Reply to pipeline" (reply from a `reactivation` contact): card in New Lead + `new lead` ✓, but the
  alert went only to the contact owner (Mike, by "Contact Created -> add owner"), no e-mail, and the reactivation
  SMS/e-mail sequences kept going after the reply (texts 2 and 3 days later to someone already talking to us).
Fix (same step ids where the step exists, trigger targets unchanged, re-entry/settings kept by Agency.call):
- Drain & Wash Replies: + "Create or update opportunity" (New Lead, source "SMS Reply - Drain & Wash") + tag `new lead`;
  SMS to Mike and Kris; + "Email to Kris".
- SMS Customer Reply to pipeline: + "Stop reactivation sequence" (remove from Reactivation Campaign - SMS / - Email);
  SMS to Mike and Kris; + "Email to Mike" / "Email to Kris".
test: copies (ZZ TEST, tag triggers instead of "Customer Replied", which cannot be simulated) with the SMS/app alerts
dropped and the e-mails sent to --to; a ZZ TEST "reactivation" copy (wait 3 min → tag) checks the stop; all deleted.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import uuid

from _common import ROOT, load_dotenv
from pp_lead_alerts import retarget
from pp_review_fix import read
from pp_source_tags import fresh_ids, refs_ok

from cli_anything.gohighlevel.utils.agency import BACKEND, SERVICES, Agency

LOC = "DdTE6mF11dqgoI5Cv7XN"
PIPELINE = "5lyzLFECNQGtANjpnKc6"
NEW_LEAD = "00add63d-7bd2-4890-8974-598b7287765c"
MIKE, KRIS = "RBEED1mFWVMUqGkrZWyi", "0aJXUMBBZuJgPbEnkUWy"
MIKE_EMAIL, KRIS_EMAIL = "stayfreshpoolsoffice@gmail.com", "Kris@stayfreshpools.com"
DW, REPLY = "Drain & Wash Campaign - Replies", "SMS Customer Reply to pipeline"
REACT = ["Reactivation Campaign - SMS", "Reactivation Campaign - Email"]
BDIR = ROOT / "backup" / "stay-fresh-pools"
P = '<p style="margin:0 0 12px 0;font-family:Arial,Helvetica,sans-serif;font-size:15px;line-height:1.5;">'


def step(name: str, attrs: dict) -> dict:
    return {"id": str(uuid.uuid4()), "name": name, "type": attrs["type"] if attrs["type"] not in ("sms", "email") else
            "internal_notification", "attributes": attrs}


def opp(source: str) -> dict:
    return step("Create or update opportunity", {
        "type": "create_opportunity", "fields": [], "pipeline_id": PIPELINE, "pipeline_stage_id": NEW_LEAD,
        "opportunity_name": "{{contact.name}}", "monetary_value": "{{custom_values.weekly_service_price}}",
        "opportunity_status": "open", "opportunity_source": source})


def email(name: str, to: str, subject: str, intro: str) -> dict:
    html = (f"{P}{intro}</p>{P}<b>Name:</b> {{{{contact.name}}}}</p>{P}<b>Phone:</b> {{{{contact.phone}}}}</p>"
            f"{P}<b>Email:</b> {{{{contact.email}}}}</p>{P}<b>Reply:</b> {{{{message.body}}}}</p>"
            f"{P}The contact is now a New Lead in the Pool Leads pipeline.</p>")
    return step(name, {"type": "email", "email": {"isCloned": False, "userType": "custom_email", "to": to,
                                                  "attachments": [], "subject": subject, "html": html}})


def chain(steps: list[dict]) -> list[dict]:
    out = []
    for i, s in enumerate(steps):
        s = {k: v for k, v in s.items() if k not in ("next", "parentKey", "parent")}
        s["order"] = i
        if i:
            s["parentKey"] = steps[i - 1]["id"]
        if i < len(steps) - 1:
            s["next"] = steps[i + 1]["id"]
        out.append(s)
    return out


def to_both(s: dict) -> dict:
    s = json.loads(json.dumps(s))
    s["attributes"]["sms"].update({"userType": "user", "selectedUser": [MIKE, KRIS]})
    s["name"] = "SMS to Mike & Kris"
    return s


def new_dw(tpl: list[dict]) -> list[dict] | None:
    if any(s["type"] == "create_opportunity" for s in tpl):
        return None
    by = {s["name"]: s for s in tpl}
    mike = by["Email to Mike"]
    kris = json.loads(json.dumps(mike))
    kris.update(id=str(uuid.uuid4()), name="Email to Kris")
    kris["attributes"]["email"]["to"] = KRIS_EMAIL
    return chain([by["Add Tag interested"], opp("SMS Reply - Drain & Wash"),
                  step("Add Tag new lead", {"type": "add_contact_tag", "tags": ["new lead"]}),
                  to_both(by["SMS to Mike"]), mike, kris])


def new_reply(tpl: list[dict], react_ids: list[str]) -> list[dict] | None:
    if any(s["type"] == "remove_from_workflow" for s in tpl):
        return None
    by = {s["name"]: s for s in tpl}
    subj, intro = "💬 Reactivation reply: {{contact.name}} {{contact.phone}}", "{{contact.name}} replied to the reactivation text."
    return chain([by["Create or update opportunity"], by["Remove Tag Reactivation"],
                  step("Stop reactivation sequence", {"type": "remove_from_workflow", "workflow_id": react_ids}),
                  by["Add Tag new lead"], to_both(by["SMS Notification"]), by["App Notification"],
                  email("Email to Mike", MIKE_EMAIL, subj, intro), email("Email to Kris", KRIS_EMAIL, subj, intro)])


def put(a: Agency, wid: str, live: dict, tpl: list[dict]) -> dict:
    BDIR.mkdir(parents=True, exist_ok=True)
    (BDIR / f"workflow-{wid}-{time.strftime('%Y%m%d-%H%M%S')}.json").write_text(json.dumps(live))
    a.call("PUT", BACKEND, f"/workflow/{LOC}/{wid}", body={"name": live["name"], "version": live.get("version", 1),
                                                         "status": live["status"], "parentId": live.get("parentId"),
                                                         "workflowData": {"templates": tpl}})
    time.sleep(3)
    return read(a, LOC, wid)


def show(tpl: list[dict]) -> None:
    for s in tpl:
        at = s["attributes"]
        extra = at.get("tags") or at.get("workflow_id") or at.get("opportunity_source") or \
            (at.get("sms") or {}).get("selectedUser") or (at.get("email") or {}).get("to") or ""
        print(f"      - {s['name']} [{s['type']}] {extra}")


def create_copy(a: Agency, name: str, tpl: list[dict], tag: str, parent: str | None) -> str:
    wid = (lambda r: r.get("id") or r.get("_id"))(a.call("POST", BACKEND, f"/workflow/{LOC}",
                                                          body={"name": name, "parentId": parent, "status": "draft"}))
    body = {"name": name, "version": 1, "status": "draft", "parentId": parent, "allowMultiple": True,
            "workflowData": {"templates": tpl}}
    a.call("PUT", BACKEND, f"/workflow/{LOC}/{wid}", body=body)
    trig = {"type": "contact_tag", "name": "Contact Tag", "masterType": "highlevel", "schedule_config": {},
            "workflowId": wid, "workflow_id": wid, "location_id": LOC, "targetActionId": tpl[0]["id"],
            "actions": [{"workflow_id": wid, "type": "add_to_workflow"}],
            "conditions": [{"operator": "index-of-true", "type": "select", "value": tag, "field": "tagsAdded",
                            "title": "Tag Added", "id": "tag-added"}]}
    t = a.call("POST", BACKEND, f"/workflow/{LOC}/trigger", body=trig)
    a.call("PUT", BACKEND, f"/workflow/{LOC}/trigger/{t['id']}", body={**trig, "id": t["id"]})
    a.call("PUT", BACKEND, f"/workflow/{LOC}/{wid}", body={**body, "status": "published",
                                                         "version": a.workflow(LOC, wid).get("version", 1)})
    return wid


def drop_flow(a: Agency, wid: str) -> None:
    live = a.workflow(LOC, wid)
    a.call("PUT", BACKEND, f"/workflow/{LOC}/{wid}", body={"name": live["name"], "version": live.get("version", 1),
                                                         "status": "draft", "workflowData": live["workflowData"]})
    a.call("DELETE", BACKEND, f"/workflow/{LOC}/{wid}")


def for_test(tpl: list[dict], to: str, stop_ids: list[str]) -> list[dict]:
    keep = []
    for s in json.loads(json.dumps(tpl)):
        at = s["attributes"]
        if at.get("type") in ("sms", "notification"):
            continue  # alerts to Mike/Kris phones and app: never from a test
        if at.get("type") == "email":
            at["email"]["to"] = to
            at["email"]["subject"] = f"[TEST {s['name']}] " + at["email"]["subject"]
        if s["type"] == "remove_from_workflow":
            at["workflow_id"] = stop_ids
        keep.append(s)
    return chain(fresh_ids(keep))


def test(a: Agency, flows: dict, to: str) -> int:
    stamp = int(time.time())
    parent = read(a, LOC, flows[REPLY]).get("parentId")
    react_ids = [flows[n] for n in REACT]
    dw = new_dw(read(a, LOC, flows[DW])["workflowData"]["templates"])
    rp = new_reply(read(a, LOC, flows[REPLY])["workflowData"]["templates"], react_ids)
    if not dw or not rp:
        sys.exit("já aplicado: testar com a versão no ar não é o caso deste script")
    wids, made = [], {}
    tags = {"seq": f"zz sf seq {stamp}", "reply": f"zz sf reply {stamp}", "dw": f"zz sf dw {stamp}"}
    still = f"zz sf still in sequence {stamp}"
    try:
        seq = create_copy(a, "ZZ TEST reactivation copy", chain([
            {"id": str(uuid.uuid4()), "name": "Wait 3 min", "type": "wait",
             "attributes": {"type": "time", "startAfter": {"type": "minutes", "value": 3, "when": "after"}}},
            {"id": str(uuid.uuid4()), "name": "Still in", "type": "add_contact_tag",
             "attributes": {"type": "add_contact_tag", "tags": [still]}}]), tags["seq"], parent)
        wids.append(seq)
        wids.append(create_copy(a, "ZZ TEST reactivation reply copy", for_test(rp, to, [seq]), tags["reply"], parent))
        wids.append(create_copy(a, "ZZ TEST drain wash reply copy", for_test(dw, to, []), tags["dw"], parent))
        time.sleep(8)
        for case in ("replied", "control", "dw"):
            made[case] = a.call("POST", SERVICES, "/contacts/", body={
                "locationId": LOC, "firstName": "ZZ Test", "lastName": f"campaign {case}",
                "email": to.replace("@", f"+sf-{case}-{stamp}@")})["contact"]["id"]
        time.sleep(5)
        for case in ("replied", "control"):
            a.call("POST", SERVICES, f"/contacts/{made[case]}/tags", body={"tags": [tags["seq"]]})
        time.sleep(30)
        a.call("POST", SERVICES, f"/contacts/{made['replied']}/tags", body={"tags": [tags["reply"]]})
        a.call("POST", SERVICES, f"/contacts/{made['dw']}/tags", body={"tags": [tags["dw"]]})
        time.sleep(300)
        opps = a.call("GET", SERVICES, "/opportunities/search", params={"location_id": LOC, "limit": 100})["opportunities"]
        bad = 0
        want = {"replied": ("SMS Reply - Reactivation", {"new lead"}, False),
                "control": (None, set(), True), "dw": ("SMS Reply - Drain & Wash", {"new lead"}, False)}
        for case, cid in made.items():
            tg = set(a.call("GET", SERVICES, f"/contacts/{cid}")["contact"].get("tags") or [])
            mine = [o for o in opps if o["contactId"] == cid]
            src, need, in_seq = want[case]
            ok = (len(mine) == 1 and mine[0]["pipelineStageId"] == NEW_LEAD and mine[0].get("source") == src
                  if src else not mine) and need <= tg and ((still in tg) == in_seq)
            bad += not ok
            print(f"   {'✓' if ok else '✗'} {case}: cards {[(o['pipelineStageId'] == NEW_LEAD, o.get('source')) for o in mine]}"
                  f" · tags {sorted(t for t in tg if not t.startswith('zz sf'))} · ficou na sequência: {still in tg}")
        print(f"   e-mails: 2 [TEST Email to …] reactivation + 2 drain & wash em {to}")
        return 1 if bad else 0
    finally:
        opps = a.call("GET", SERVICES, "/opportunities/search", params={"location_id": LOC, "limit": 100})["opportunities"]
        for o in opps:
            if o["contactId"] in made.values():
                a.call("DELETE", SERVICES, f"/opportunities/{o['id']}")
        for cid in made.values():
            a.call("DELETE", SERVICES, f"/contacts/{cid}")
        for wid in wids:
            drop_flow(a, wid)
        print("   limpo.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("mode", choices=["plan", "test", "apply"])
    parser.add_argument("--to")
    args = parser.parse_args()
    load_dotenv()
    a = Agency()
    if not a.location(LOC)["name"].startswith("Stay Fresh"):
        sys.exit("sub-conta errada")
    flows = {w["name"]: w["id"] for w in a.workflows(LOC)}
    if args.mode == "test":
        if not args.to:
            parser.error("--to is required in test mode")
        return test(a, flows, args.to)
    bad = 0
    for name, build in ((DW, new_dw), (REPLY, lambda t: new_reply(t, [flows[n] for n in REACT]))):
        live = read(a, LOC, flows[name])
        tpl = build(live["workflowData"]["templates"])
        print(f"   {name}: {'já feito' if tpl is None else 'novo encadeamento:'}")
        if tpl is None:
            continue
        show(tpl)
        if args.mode == "apply":
            got = put(a, flows[name], live, tpl)
            retarget(a, LOC, flows[name], tpl[0]["id"])
            trs = [t for t in a.triggers(LOC, flows[name]) if not t.get("deleted")]
            t2 = got["workflowData"]["templates"]
            ok = refs_ok(t2) and len(t2) == len(tpl) and got["status"] == live["status"] and \
                got.get("allowMultiple") == live.get("allowMultiple") and \
                all(t.get("targetActionId") == tpl[0]["id"] and t.get("active") for t in trs)
            bad += not ok
            print(f"      {'✓' if ok else '✗ VERIFICAR'} {got['status']} · re-entry {got.get('allowMultiple')} · {len(t2)} passos")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
