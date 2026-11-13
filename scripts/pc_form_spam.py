#!/usr/bin/env python3
"""Passion Pool Care: spam filter on the website/ads forms (Frank 12/11, John: "a lot of spam leads").

Live data 13/10–12/11: the sales pitches all came with a non-US phone (+92 / +91: "complimentary cleaning bid",
"seorankings", "Wikipedia page") or SEO/marketing words in the "Pool Details" message.

What it does (backup first): at the start of "Website Form Fill To Pipeline" and "AdWords Form - New Lead" an
if/else "Spam form fill?" (any of):
  - phone contains +2 … +9 (phones are E.164, so that is any country code other than +1)
  - Pool Details contains one of KEYWORDS
  → Spam branch: tag `spam` + `form spam filter`, card in 🚫 Spam ("Spam Contact" then adds dnd/spam + DND). Nothing
    else: no NEW LEAD text/email to John, no task, no follow-up. Nothing is deleted.
  → otherwise the original chain, unchanged.

    python3 scripts/pc_form_spam.py plan
    python3 scripts/pc_form_spam.py test     # ZZ TEST copy with a tag trigger, tags only, test contacts; all deleted after
    python3 scripts/pc_form_spam.py apply
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import uuid

sys.path.insert(0, os.path.dirname(__file__))
from _common import ROOT, load_dotenv  # noqa: E402

load_dotenv()
from cli_anything.gohighlevel.utils.agency import BACKEND, SERVICES, Agency  # noqa: E402
from pp_won_stage import DROP, IS_OPS, NEST  # noqa: E402

LOC = "d03SMzI37dxTBeuoTJ13"
FLOWS = ["Website Form Fill To Pipeline", "AdWords Form - New Lead"]
DETAILS = "vgf18SsSqNjwgfNakmPk"  # contact field "Pool Details" (the form's message box)
PIPE, SPAM_STAGE = "upBpvcGQ9jo004msxkLJ", "8108db77"
KEYWORDS = ["SEO", "seo", "Seo", "Wikipedia", "wikipedia", "backlink", "Backlink", "ranking", "Ranking",
            "marketing", "Marketing", "Business Development", "business development"]
NAME = "Spam form fill?"
TEST_TAG = "zz spam test"


def nid() -> str:
    return str(uuid.uuid4())


def cond(sub: str, value: str) -> dict:
    return {"conditionType": "contact_detail", "conditionSubType": sub, "conditionOperator": "contain",
            "conditionValue": value, "__conditionId": nid(), "ifElseNodeId": "", "__customFieldType__": "standard",
            "isWait": False, "nestedDropdownTypes": NEST, "allowIsOperatorTypes": IS_OPS}


def spam_stage(a: Agency) -> str:
    p = next(p for p in a.pipelines(LOC) if p["id"] == PIPE)
    return next(s["id"] for s in p["stages"] if s["id"].startswith(SPAM_STAGE))


def tag_step(tags: list[str], parent: str, order: int) -> dict:
    return {"id": nid(), "order": order, "name": "Tag spam" if "spam" in tags else f"Tag {tags[0]}", "type": "add_contact_tag",
            "parent": parent, "parentKey": parent, "attributes": {"tags": tags}}


def build(chain: list[dict], spam_steps: list[dict]) -> list[dict]:
    """[guard, Spam branch → spam_steps, Lead branch → chain]."""
    c, yes, no = nid(), nid(), nid()
    conds = [cond("phone", f"+{d}") for d in range(2, 10)] + [cond(DETAILS, k) for k in KEYWORDS]
    guard = {"id": c, "order": 0, "name": NAME, "type": "if_else", "cat": "conditions", "nodeType": "condition-node",
             "comments": [], "next": [yes, no],
             "attributes": {"currentRecipeType": "CUSTOM", "operator": "or", "if": True, "conditionName": NAME,
                            "version": 2, "noneBranchName": "Lead",
                            "branches": [{"id": yes, "name": "Spam", "operator": "or", "showErrors": False,
                                          "branchNameError": "Branch name cannot be empty!",
                                          "segments": [{"__segmentId": nid(), "operator": "or", "conditions": conds}]}]}}
    y = {"id": yes, "parent": c, "parentKey": c, "order": 1, "name": "Spam", "type": "if_else", "cat": "conditions",
         "sibling": [no], "comments": [], "nodeType": "branch-yes",
         "attributes": {"if": False, "conditionName": "Condition", "operator": "or", "branches": []}}
    n = {"id": no, "parent": c, "parentKey": c, "order": 1, "name": "Lead", "type": "if_else", "cat": "conditions",
         "sibling": [yes], "comments": [], "nodeType": "branch-no", "attributes": {"else": True}}

    def hang(steps: list[dict], branch: dict) -> list[dict]:
        steps = json.loads(json.dumps(steps))
        for i, s in enumerate(steps):
            s.update(order=i, parent=branch["id"], parentKey=steps[i - 1]["id"] if i else branch["id"])
            s.pop("next", None)
            if i:
                steps[i - 1]["next"] = s["id"]
        if steps:
            branch["next"] = steps[0]["id"]
        return steps

    return [guard, y, n, *hang(spam_steps, y), *hang(chain, n)]


def linear(templates: list[dict]) -> list[dict]:
    by_id = {s["id"]: s for s in templates}
    first = next(s for s in templates if not s.get("parentKey"))
    chain = [first]
    while chain[-1].get("next"):
        chain.append(by_id[chain[-1]["next"]])
    if len(chain) != len(templates) or any(s["type"] == "if_else" for s in templates):
        raise SystemExit("workflow is not a plain linear chain — not rebuilding blindly")
    return chain


def spam_actions(stage: str) -> list[dict]:
    return [{"id": nid(), "name": "Tag spam", "type": "add_contact_tag", "attributes": {"tags": ["spam", "form spam filter"]}},
            {"id": nid(), "name": "Card in Spam", "type": "create_opportunity",
             "attributes": {"fields": [], "type": "create_opportunity", "pipeline_id": PIPE, "pipeline_stage_id": stage,
                            "opportunity_name": "{{contact.name}}", "opportunity_source": "Website Form (spam filter)",
                            "opportunity_status": "open"}}]


def put(a: Agency, wid: str, live: dict, templates: list[dict], status: str | None = None) -> None:
    a.call("PUT", BACKEND, f"/workflow/{LOC}/{wid}", body={
        "name": live["name"], "version": live.get("version", 1), "status": status or live["status"],
        "parentId": live.get("parentId"), "workflowData": {"templates": templates}})


def retarget(a: Agency, wid: str, first: str) -> None:
    for t in [x for x in a.triggers(LOC, wid) if not x.get("deleted")]:
        body = {k: v for k, v in t.items() if k not in DROP}
        body.update({"workflowId": wid, "workflow_id": wid, "location_id": LOC, "targetActionId": first,
                     "actions": [{"workflow_id": wid, "type": "add_to_workflow"}]})
        a.call("PUT", BACKEND, f"/workflow/{LOC}/trigger/{t['id']}", body=body)


def tags_of(a: Agency, cid: str) -> list[str]:
    return a.get(SERVICES, f"/contacts/{cid}").get("contact", {}).get("tags") or []


def test(a: Agency) -> int:
    name = "ZZ TEST Spam form filter"
    tpl = build([{"id": nid(), "name": "Tag lead", "type": "add_contact_tag", "attributes": {"tags": ["zz-lead"]}}],
                [{"id": nid(), "name": "Tag spam", "type": "add_contact_tag", "attributes": {"tags": ["zz-spam"]}}])
    cases = [("ZZ Test Foreign", "+925550100001", "I can offer a complimentary cleaning bid", "zz-spam"),
             ("ZZ Test SEO", "+16155550101", "We can boost your Google ranking with SEO", "zz-spam"),
             ("ZZ Test lower", "+16155550102", "cheap seo and backlink services", "zz-spam"),
             ("ZZ Test Real", "+16155550103", "Need my pool closed for the season & reopened in Spring", "zz-lead"),
             ("ZZ Test Empty", "+16155550104", "", "zz-lead")]
    wid, cids, bad = None, [], 0
    try:
        res = a.call("POST", BACKEND, f"/workflow/{LOC}", body={"name": name, "status": "draft"})
        wid = res.get("id") or res.get("_id")
        live = a.workflow(LOC, wid)
        put(a, wid, live, tpl, "draft")
        live = a.workflow(LOC, wid)
        put(a, wid, live, live["workflowData"]["templates"], "published")
        body = {"type": "contact_tag", "name": "Tag Added", "active": True, "workflowId": wid, "workflow_id": wid,
                "location_id": LOC, "targetActionId": tpl[0]["id"], "actions": [{"workflow_id": wid, "type": "add_to_workflow"}],
                "masterType": "highlevel",
                "conditions": [{"operator": "index-of-true", "field": "tagsAdded", "value": TEST_TAG, "title": "Tag Added",
                                "type": "select", "id": "tag-added"}]}
        try:
            a.call("POST", BACKEND, f"/workflow/{LOC}/tags/create", body={"tag": TEST_TAG})
        except Exception:  # noqa: BLE001
            pass
        r = a.call("POST", BACKEND, f"/workflow/{LOC}/trigger", body=body)
        a.call("PUT", BACKEND, f"/workflow/{LOC}/trigger/{r['id']}", body={**body, "id": r["id"]})
        time.sleep(5)
        for nm, phone, details, _ in cases:
            c = a.call("POST", SERVICES, "/contacts/", body={"locationId": LOC, "firstName": nm, "phone": phone,
                       "email": f"{nm.lower().replace(' ', '.')}@example.com",
                       "customFields": [{"id": DETAILS, "field_value": details}] if details else []})["contact"]
            cids.append(c["id"])
        time.sleep(3)
        for cid in cids:
            a.call("POST", SERVICES, f"/contacts/{cid}/tags", body={"tags": [TEST_TAG]})
        deadline = time.time() + 240
        got = {}
        while time.time() < deadline and len(got) < len(cids):
            time.sleep(15)
            for (nm, *_), cid in zip(cases, cids):
                t = tags_of(a, cid)
                if "zz-spam" in t or "zz-lead" in t:
                    got[nm] = "zz-spam" if "zz-spam" in t else "zz-lead"
        for nm, phone, details, want in cases:
            ok = got.get(nm) == want
            bad += not ok
            print(f"   {'✓' if ok else '✗'} {nm} ({phone}, {details[:30]!r}) → {got.get(nm, 'nada')} (esperado {want})")
    finally:
        for cid in cids:
            a.call("DELETE", SERVICES, f"/contacts/{cid}")
        if wid:
            live = a.workflow(LOC, wid)
            put(a, wid, live, live["workflowData"]["templates"], "draft")
            a.call("DELETE", BACKEND, f"/workflow/{LOC}/{wid}")
        for t in a.tags(LOC):
            if t["name"] in (TEST_TAG, "zz-spam", "zz-lead"):
                a.call("DELETE", SERVICES, f"/locations/{LOC}/tags/{t['id']}")
        print("   limpo (contatos, tags e workflow de teste apagados)")
    return 1 if bad else 0


def apply(a: Agency, do: bool) -> int:
    stage = spam_stage(a)
    flows = {w["name"]: w for w in a.workflows(LOC)}
    bdir = os.path.join(ROOT, "backup", "passion-pool-care-lp")
    os.makedirs(bdir, exist_ok=True)
    bad = 0
    for tag in ("spam", "form spam filter"):
        if do:
            try:
                a.call("POST", BACKEND, f"/workflow/{LOC}/tags/create", body={"tag": tag})
            except Exception:  # noqa: BLE001
                pass
    for name in FLOWS:
        wid = flows[name]["id"]
        live = a.workflow(LOC, wid)
        tpl = live["workflowData"]["templates"]
        if any(s.get("name") == NAME for s in tpl):
            print(f"   {name}: já tem o filtro")
            continue
        chain = linear(tpl)
        new = build(chain, spam_actions(stage))
        print(f"   {name} [{live['status']}]: {' → '.join(s['type'] for s in chain)}  ⇒  filtro + mesma cadeia no ramo Lead")
        if not do:
            continue
        json.dump({"workflow": live, "triggers": a.triggers(LOC, wid)},
                  open(os.path.join(bdir, f"workflow-{wid}-{time.strftime('%Y%m%d-%H%M%S')}.json"), "w"))
        put(a, wid, live, new)
        retarget(a, wid, new[0]["id"])
        time.sleep(4)
        after = a.workflow(LOC, wid)
        st = after["workflowData"]["templates"]
        ok = after["status"] == live["status"] and st[0].get("name") == NAME and len(st) == len(new) \
            and all(t.get("targetActionId") == new[0]["id"] for t in a.triggers(LOC, wid) if not t.get("deleted"))
        bad += not ok
        print(f"     {'✓' if ok else '✗ VERIFICAR'} {after['status']} · {len(st)} passos · gatilhos no filtro")
    return 1 if bad else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mode", choices=["plan", "test", "apply"])
    args = ap.parse_args()
    a = Agency()
    if args.mode == "test":
        return test(a)
    return apply(a, args.mode == "apply")


if __name__ == "__main__":
    raise SystemExit(main())
