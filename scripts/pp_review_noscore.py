#!/usr/bin/env python3
"""No rating = no Google review link (Ed 13/11, DM: "Yes make that change for Southern and all other sub accounts and
snapshot. No score should mean no link gets sent out.").

The V9 Review Request asks for the NPS score, then waits up to 7 days ("Wait for NPS Submission", multi-path wait).
Before: the wait's TIMEOUT path (no score in 7 days) sent the Email + SMS review request (Google link).
After: the timeout path ends there (no link). A score still follows the gate (5 → Google link; 1-4 → feedback SMS +
team alert) — only the no-score path changes.

Read-only by default; --apply backs up each workflow (backup/<slug>/review-noscore-<id8>-<date>.json), PUTs it (status
kept) and re-reads it to confirm the timeout path has no review_request step left.

  python3 scripts/pp_review_noscore.py                              # plan, every client account
  python3 scripts/pp_review_noscore.py --only "Snapshot Pool Profits" --apply
  python3 scripts/pp_review_noscore.py --apply                      # every client account + snapshot master
"""
from __future__ import annotations

import argparse
import copy
import datetime as dt
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
from cli_anything.gohighlevel.utils.agency import BACKEND, Agency, GHLError, match_location, slugify  # noqa: E402
from pp_review_gate import SKIP  # noqa: E402  (snapshot master + test account in, other non-client accounts out)


def timeout_chain(tpl: list[dict]) -> list[tuple[dict, list[dict]]]:
    """[(timeout transition, steps after it)] for every multi-path wait in the workflow."""
    by_id = {t["id"]: t for t in tpl}
    out = []
    for t in tpl:
        if t.get("type") == "transition" and (t.get("attributes") or {}).get("type") == "wait_timeout":
            chain, cur = [], by_id.get(t.get("next")) if isinstance(t.get("next"), str) else None
            while cur:
                chain.append(cur)
                cur = by_id.get(cur.get("next")) if isinstance(cur.get("next"), str) else None
            out.append((t, chain))
    return out


def plan(a: Agency, loc: dict, apply: bool) -> str:
    lid, name = loc["id"], loc.get("name", "")
    wfs = [w for w in a.workflows(lid) if (w.get("name") or "").strip().lower() == "review request"]
    if not wfs:
        return "no 'Review Request'"
    notes = []
    for w in wfs:
        wf = a.workflow(lid, w["id"])
        tpl = (wf.get("workflowData") or {}).get("templates") or []
        hits = [(t, ch) for t, ch in timeout_chain(tpl) if any(s.get("type") == "review_request" for s in ch)]
        if not hits:
            notes.append(f"{w.get('status')}: ok (no link on timeout)")
            continue
        steps = [s for _, ch in hits for s in ch]
        if any(s.get("type") in ("if_else", "wait", "transition", "goto") for s in steps):
            notes.append(f"{w.get('status')}: timeout path has branches ({[s.get('type') for s in steps]}) — SKIPPED, check by hand")
            continue
        desc = ", ".join(s.get("name") or s.get("type") for s in steps)
        if not apply:
            notes.append(f"{w.get('status')}: would remove from timeout: {desc}")
            continue
        folder = os.path.join(ROOT, "backup", slugify(name))
        os.makedirs(folder, exist_ok=True)
        with open(os.path.join(folder, f"review-noscore-{w['id'][:8]}-{dt.date.today():%Y%m%d}.json"), "w") as fh:
            json.dump(wf, fh, indent=1)
        new = copy.deepcopy(wf)
        ntpl = new["workflowData"]["templates"]
        nby = {t["id"]: t for t in ntpl}
        sids = {s["id"] for s in steps}
        # The 5-star branch reaches the link steps with a Go To into the timeout path (V9). Move the steps into the
        # 5-star branch in place of that Go To, so the 5-star path keeps its link and only the timeout path loses it.
        gotos = [t for t in ntpl if t.get("type") == "goto" and (t.get("attributes") or {}).get("targetNodeId") in sids]
        if len({h["id"] for h, _ in hits}) != 1 or len(gotos) > 1:
            notes.append(f"{w.get('status')}: {len(hits)} timeout paths / {len(gotos)} Go To into them — SKIPPED, check by hand")
            continue
        hit, chain = hits[0]
        nby[hit["id"]].pop("next", None)
        if gotos:
            g = nby[gotos[0]["id"]]
            if g["attributes"]["targetNodeId"] != chain[0]["id"]:
                notes.append(f"{w.get('status')}: Go To points mid-chain — SKIPPED, check by hand")
                continue
            for t in ntpl:
                if t.get("next") == g["id"]:
                    t["next"] = chain[0]["id"]
            prev_key, order = g.get("parentKey"), g.get("order", 0)
            for s in chain:
                n = nby[s["id"]]
                n["parent"], n["parentKey"], n["order"] = g.get("parent"), prev_key, order
                prev_key, order = n["id"], order + 1
            if g.get("next"):
                nby[chain[-1]["id"]]["next"] = g["next"]
            else:
                nby[chain[-1]["id"]].pop("next", None)
            ntpl.remove(g)
        else:
            new["workflowData"]["templates"] = ntpl = [t for t in ntpl if t["id"] not in sids]
        body = {k: new[k] for k in new if k not in ("_id", "createdAt", "updatedAt", "__v")}
        a.call("PUT", BACKEND, f"/workflow/{lid}/{w['id']}", body=body)
        chk = a.workflow(lid, w["id"])
        left = [s for _, ch in timeout_chain(chk["workflowData"]["templates"]) for s in ch if s.get("type") == "review_request"]
        ctpl = chk["workflowData"]["templates"]
        cby = {t["id"]: t for t in ctpl}
        five = []  # link steps reachable from the branch that holds the old Go To (5-star path)
        if gotos:
            cur = cby.get(cby.get(gotos[0].get("parent"), {}).get("next"))
            while cur:
                five.append(cur.get("type"))
                cur = cby.get(cur.get("next")) if isinstance(cur.get("next"), str) else None
        ok = not left and (not gotos or five.count("review_request") == len(chain))
        notes.append(f"{w.get('status')}→{chk.get('status')}: timeout path now ends; {desc} "
                     f"{'moved into the 5-star branch' if gotos else 'removed'} — {'OK' if ok else 'CHECK'} "
                     f"(5-star path: {five or '-'})")
    return " | ".join(notes)


def subtree(tpl: list[dict], root_id: str) -> list[dict]:
    kids, out, todo = {}, [], [root_id]
    for t in tpl:
        kids.setdefault(t.get("parent"), []).append(t)
    by_id = {t["id"]: t for t in tpl}
    while todo:
        cur = todo.pop()
        node = by_id[cur]
        out.append(node)
        nxt = node.get("next")
        for n in (nxt if isinstance(nxt, list) else [nxt] if nxt else []):
            if n in by_id and by_id[n] not in out:
                todo.append(n)
    return out


def test(a: Agency, loc: dict) -> int:
    """ZZ TEST copy of the account's (already changed) Review Request score wait, messages swapped for tags, 3-minute
    timeout: contacts with score 5 / 2 / none. Expected: 5 → the moved link steps run (tags zz link …), 2 → feedback
    path (zz sms …), none → nothing after the wait. Deleted afterwards."""
    import time
    import uuid
    from cli_anything.gohighlevel.utils.agency import SERVICES
    lid = loc["id"]
    w = next(w for w in a.workflows(lid) if (w.get("name") or "").strip().lower() == "review request")
    tpl = copy.deepcopy(a.workflow(lid, w["id"])["workflowData"]["templates"])
    wait = next(t for t in tpl if t.get("type") == "wait" and (t.get("cat") == "multi-path" or (t.get("attributes") or {}).get("cat") == "multi-path"))
    field = next(c["conditionSubType"] for br in wait["attributes"]["condition"]["branches"] for sg in br["segments"] for c in sg["conditions"])
    sub = subtree(tpl, wait["id"])
    ids = {t["id"]: str(uuid.uuid4()) for t in sub}
    raw = json.dumps(sub)
    for o, n in ids.items():
        raw = raw.replace(o, n)
    sub = json.loads(raw)
    n = 0
    for t in sub:
        if t.get("type") in ("sms", "email", "review_request", "internal_notification", "goto"):
            n += 1
            tag = f"zz {'link' if t['type'] == 'review_request' else t['type']} {n}"
            if t["type"] == "goto":
                tag = "zz goto still there"
            t.update({"type": "add_contact_tag", "name": tag, "attributes": {"tags": [tag], "type": "add_contact_tag"}})
    start = {"id": str(uuid.uuid4()), "type": "add_contact_tag", "name": "Start", "order": 0,
             "attributes": {"tags": ["zz noscore started"], "type": "add_contact_tag"}, "next": ids[wait["id"]]}
    w2 = next(t for t in sub if t["id"] == ids[wait["id"]])
    w2.pop("parent", None)
    w2["parentKey"] = start["id"]
    w2["attributes"]["startAfter"] = {"type": "minutes", "value": 3, "when": "after"}
    tpl2 = [start, *sub]
    go = "zz noscore test"
    try:
        a.call("POST", BACKEND, f"/workflow/{lid}/tags/create", body={"tag": go})
    except GHLError:
        pass
    name = "ZZ TEST no-score gate (Pedro) - delete"
    r = a.call("POST", BACKEND, f"/workflow/{lid}", body={"name": name, "status": "draft"})
    wid = r.get("id") or r.get("_id")
    cs = {}
    try:
        a.call("PUT", BACKEND, f"/workflow/{lid}/{wid}", body={"name": name, "version": 1, "status": "draft",
                                                               "allowMultiple": False, "workflowData": {"templates": tpl2}})
        trig = {"type": "contact_tag", "name": "Contact Tag", "masterType": "highlevel", "schedule_config": {},
                "conditions": [{"operator": "index-of-true", "field": "tagsAdded", "value": go, "title": "Tag added",
                                "type": "select", "id": "tag-added"}], "workflowId": wid, "workflow_id": wid,
                "location_id": lid, "actions": [{"workflow_id": wid, "type": "add_to_workflow"}], "targetActionId": start["id"]}
        t = a.call("POST", BACKEND, f"/workflow/{lid}/trigger", body=trig)
        a.call("PUT", BACKEND, f"/workflow/{lid}/trigger/{t['id']}", body={**trig, "id": t["id"]})
        live = a.workflow(lid, wid)
        a.call("PUT", BACKEND, f"/workflow/{lid}/{wid}", body={"name": name, "version": live.get("version", 1),
               "status": "published", "allowMultiple": False, "workflowData": {"templates": tpl2}})
        time.sleep(5)
        for label in ("score 5", "score 2", "no score"):
            c = a.call("POST", SERVICES, "/contacts/", body={"locationId": lid, "firstName": "ZZ TEST", "lastName": f"noscore {label}",
                       "email": f"zz-noscore-{uuid.uuid4().hex[:6]}@example.com"})["contact"]
            cs[label] = c["id"]
        time.sleep(3)
        for cid in cs.values():
            a.call("POST", SERVICES, f"/contacts/{cid}/tags", body={"tags": [go]})
        time.sleep(45)
        for label, score in (("score 5", "5"), ("score 2", "2")):
            a.call("PUT", SERVICES, f"/contacts/{cs[label]}", body={"customFields": [{"id": field, "field_value": score}]})
        got = {}
        for _ in range(24):
            time.sleep(15)
            got = {k: sorted(x for x in a.call("GET", SERVICES, f"/contacts/{v}")["contact"].get("tags") or [] if x.startswith("zz ") and x not in (go, "zz noscore started")) for k, v in cs.items()}
            if got["score 5"] and got["score 2"] and _ >= 13:  # past the 3-minute timeout
                break
        ok = (sum(x.startswith("zz link") for x in got["score 5"]) == 2 and not any(x.startswith("zz link") for x in got["score 2"])
              and got["no score"] == [] and not any("goto" in x for v in got.values() for x in v))
        for k, v in got.items():
            print(f"   {k}: {v}")
        print(f"{'OK' if ok else 'CHECK'}: 5 → link steps, 2 → feedback, no score → nothing")
        return 0 if ok else 1
    finally:
        for cid in cs.values():
            a.call("DELETE", SERVICES, f"/contacts/{cid}")
        a.call("DELETE", BACKEND, f"/workflow/{lid}/{wid}")
        print("   ZZ TEST contacts + workflow deleted")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", action="append")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--test", action="store_true", help="ZZ TEST copy of the score wait in --only account")
    args = ap.parse_args()
    a = Agency()
    locs = a.locations()
    if args.only:
        targets = [match_location(locs, o) or sys.exit(f"not found: {o}") for o in args.only]
    else:
        targets = [l for l in locs if l["id"] not in SKIP]
    if args.test:
        raise SystemExit(test(a, targets[0]))
    for loc in sorted(targets, key=lambda l: l.get("name", "")):
        try:
            res = plan(a, loc, args.apply)
        except GHLError as exc:
            res = f"ERROR {exc}"
        print(f"{loc.get('name', '')[:34]:34} {res}")


if __name__ == "__main__":
    main()
