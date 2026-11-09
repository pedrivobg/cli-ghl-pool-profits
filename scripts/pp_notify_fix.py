#!/usr/bin/env python3
"""Missing lead alerts on the accounts activated last week (Val, 09/11: "check the new clients… just in case any
notification is missing"). Map of who gets what: scripts/pp_notify_map.py.

    ./.venv/bin/python scripts/pp_notify_fix.py ys  [--apply | --test]
    GHL_AGENCY=poolduck ./.venv/bin/python scripts/pp_notify_fix.py lwr [--apply | --test]

ys  (YardSpring): "Website Form Fill To Pipeline" only made a card + a task → add "New Lead SMS" to Joe after the tag
    (same step as NorTex / Pool Shack). "Sequential Call Routing" (a BluVantage copy: rings Fred/Paul of BluVantage,
    BluVantage numbers and voicemail) → draft, as in the model.
lwr (Pool Duck Lakewood Ranch): "Google AdWords - Qualified Lead (Call In)" (calls to the Google Ads line, which has no
    forwarding/IVR) made a card + tags and told nobody → add "Text Kenton + Service" after the tag.
--test: throwaway "ZZ TEST" copy of the new chain in the same account, tag trigger, the alert replaced by a stand-in tag
    (nobody gets a text), the card/task steps also
    replaced by a stand-in tag (no stage workflows fire); one ZZ TEST contact (example.com e-mail, no phone); checks the chain, then deletes everything.
Backup of every workflow before a PUT: backup/<slug>/<id>-<stamp>.json.
"""
from __future__ import annotations

import copy
import json
import sys
import time
import uuid

from _common import ROOT, Agency, load_dotenv
from cli_anything.gohighlevel.utils.agency import BACKEND, SERVICES

ACC = {
    "ys": {"loc": "FpRTQZR56xwp1Wg5NQCq", "slug": "yardspring-pools", "wf": "4e4a1be8-13d6-49db-9099-1b1217afc7d6",
           "after": "51471bda-e7c1-4282-815b-93212461fd89", "name": "New Lead SMS", "users": ["vBIKogeCqW1ZuXXNpCSt"],
           "body": "\U0001F6A8 NEW LEAD - Website Form\n\nName: {{contact.name}}\nPhone: {{contact.phone}}\n"
                   "Email: {{contact.email}}\nCity: {{contact.city}}\n\nSource: Website Form",
           "draft": ["d5ae7371-a82f-4339-a923-393550a33eec"]},
    "lwr": {"loc": "MosKIX4oux96vchwHZ5W", "slug": "pool-duck-lakewood-ranch", "wf": "591aa80b-9d73-401b-bc45-e13eb60635c2",
            "after": "63f19f3b-e111-4443-881b-1df5951e0c6a", "name": "Text Kenton + Service",
            "users": ["Fpwm492Y2wyKFa0xJgVC", "DZkEc4SNZd1bAeBiT2LG"],
            "body": "NEW GOOGLE ADS CALL for Pool Duck Lakewood Ranch\n\nName: {{contact.name}}\nPhone: {{contact.phone}}\n\n"
                    "This line doesn't ring anyone yet. Call them back from the Google Ads line (941) 541-5942 in the "
                    "GHL app.",
            "draft": []},
}


def stamp() -> str:
    return time.strftime("%Y%m%d-%H%M%S")


def backup(cfg, wid, live, tag):
    d = ROOT / "backup" / cfg["slug"]
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{wid}-{tag}-{stamp()}.json").write_text(json.dumps(live, indent=1))


def put(a, loc, wid, live, templates, status=None):
    a.call("PUT", BACKEND, f"/workflow/{loc}/{wid}", body={
        "name": live["name"], "version": live.get("version", 1), "status": status or live["status"],
        "parentId": live.get("parentId"), "allowMultiple": live.get("allowMultiple", False),
        "workflowData": {"templates": templates}})


def with_alert(templates, cfg, step=None):
    """Insert the alert right after cfg['after'] (linear chain); step overrides the node (test stand-in)."""
    out = copy.deepcopy(templates)
    if any(s.get("name") == cfg["name"] and s.get("type") == "internal_notification" for s in out):
        return None  # already there
    prev = next(s for s in out if s["id"] == cfg["after"])
    nid = str(uuid.uuid4())
    node = step or {"type": "internal_notification", "attributes": {"type": "sms", "sms": {
        "body": cfg["body"], "selectedUser": cfg["users"], "userType": "user", "attachments": []}}}
    node = {"id": nid, "order": prev["order"] + 1, "name": cfg["name"], **node, "parentKey": prev["id"]}
    if prev.get("parent"):
        node["parent"] = prev["parent"]
    if prev.get("next"):
        node["next"] = prev["next"]
        nxt = next(s for s in out if s["id"] == prev["next"])
        nxt["parentKey"] = nid
    prev["next"] = nid
    for s in out:
        if s is not node and s.get("order", 0) > prev["order"] and s.get("parent") == prev.get("parent"):
            s["order"] += 1
    out.insert(out.index(prev) + 1, node)
    return out


def apply(a, cfg, do):
    loc, wid = cfg["loc"], cfg["wf"]
    live = a.workflow(loc, wid)
    tpl = with_alert(live["workflowData"]["templates"], cfg)
    print(f"[{live['name']}] {live['status']}: " + ("alerta já existe" if tpl is None else
          " → ".join(s["name"] for s in tpl)))
    if do and tpl is not None:
        backup(cfg, wid, live, "before-alert")
        put(a, loc, wid, live, tpl)
        time.sleep(8)
        after = a.workflow(loc, wid)
        ok = [s["name"] for s in after["workflowData"]["templates"]] == [s["name"] for s in tpl] and \
            after["status"] == live["status"] and after.get("allowMultiple") == live.get("allowMultiple")
        print(f"   gravado; releitura {'ok' if ok else 'DIFERENTE'} (status {after['status']}, re-entry "
              f"{after.get('allowMultiple')}); gatilhos ativos: {[t.get('active') for t in a.triggers(loc, wid)]}")
    for d in cfg["draft"]:
        w = a.workflow(loc, d)
        print(f"[{w['name']}] {w['status']} → draft")
        if do and w["status"] != "draft":
            backup(cfg, d, w, "before-draft")
            put(a, loc, d, w, w["workflowData"]["templates"], status="draft")
            time.sleep(5)
            print(f"   releitura: {a.workflow(loc, d)['status']}")


def test(a, cfg):
    loc = cfg["loc"]
    live = a.workflow(loc, cfg["wf"])
    go, mark = "zz notify test go", "zz notify test alert"
    for t in (go, mark):
        try:
            a.call("POST", BACKEND, f"/workflow/{loc}/tags/create", body={"tag": t})
        except Exception:
            pass
    tpl = with_alert(live["workflowData"]["templates"], cfg,
                     step={"type": "add_contact_tag", "attributes": {"type": "add_contact_tag", "tags": [mark]}})
    # new ids so nothing collides with the live workflow; drop the self "remove from workflow" step's target
    ids = {s["id"]: str(uuid.uuid4()) for s in tpl}
    raw = json.dumps(tpl)
    for o, n in ids.items():
        raw = raw.replace(o, n)
    tpl = json.loads(raw)
    res = a.call("POST", BACKEND, f"/workflow/{loc}", body={"name": "ZZ TEST notify alert", "status": "draft"})
    wid = res.get("id") or res.get("_id")
    for s in tpl:
        if s["type"] == "remove_from_workflow":
            s["attributes"]["workflow_id"] = [wid]
        if s["type"] in ("task-notification", "create_opportunity"):  # no task / card (stage workflows) in the test
            s["type"], s["attributes"] = "add_contact_tag", {"type": "add_contact_tag", "tags": [mark + " step"]}
    cid = None
    try:
        a.call("PUT", BACKEND, f"/workflow/{loc}/{wid}", body={"name": "ZZ TEST notify alert", "version": 1,
               "status": "published", "allowMultiple": True, "workflowData": {"templates": tpl}})
        link = {"workflowId": wid, "workflow_id": wid, "location_id": loc,
                "actions": [{"workflow_id": wid, "type": "add_to_workflow"}]}
        trig = {"type": "contact_tag", "name": "Contact Tag", "masterType": "highlevel", "schedule_config": {},
                "conditions": [{"operator": "index-of-true", "field": "tagsAdded", "value": go, "title": "Tag Added",
                                "type": "select", "id": "tag-added"}], **link, "targetActionId": tpl[0]["id"]}
        t = a.call("POST", BACKEND, f"/workflow/{loc}/trigger", body=trig)
        a.call("PUT", BACKEND, f"/workflow/{loc}/trigger/{t['id']}", body={**trig, "id": t["id"]})
        time.sleep(8)
        c = a.call("POST", SERVICES, "/contacts/upsert", body={"locationId": loc, "firstName": "ZZ TEST",
                                                                 "lastName": f"notify {stamp()}",
                                                                 "email": f"zz-notify-{stamp()}@example.com"})
        cid = c["contact"]["id"]
        time.sleep(3)
        a.call("POST", SERVICES, f"/contacts/{cid}/tags", body={"tags": [go]})
        want = {mark, mark + " step"} | set(next(s for s in live["workflowData"]["templates"] if s["id"] == cfg["after"])
                            ["attributes"]["tags"])
        for _ in range(12):
            time.sleep(10)
            tags = set(a.call("GET", SERVICES, f"/contacts/{cid}")["contact"].get("tags", []))
            if want <= tags:
                break
        opps = a.call("GET", SERVICES, "/opportunities/search", params={"location_id": loc, "contact_id": cid})
        print(f"   tags: {sorted(tags)}")
        print(f"   {'✓' if want <= tags else '✗'} alerta (stand-in) depois das tags · cards: "
              f"{[(o.get('name'), o.get('pipelineStageId')) for o in opps.get('opportunities', [])]}")
        return 0 if want <= tags else 1
    finally:
        if cid:
            for o in a.call("GET", SERVICES, "/opportunities/search",
                            params={"location_id": loc, "contact_id": cid}).get("opportunities", []):
                a.call("DELETE", SERVICES, f"/opportunities/{o['id']}")
            a.call("DELETE", SERVICES, f"/contacts/{cid}")
        a.call("DELETE", BACKEND, f"/workflow/{loc}/{wid}")
        print("   contato, card e cópia ZZ TEST apagados")


def main():
    load_dotenv()
    cfg = ACC[sys.argv[1]]
    a = Agency()
    if "--test" in sys.argv:
        return test(a, cfg)
    apply(a, cfg, "--apply" in sys.argv)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
