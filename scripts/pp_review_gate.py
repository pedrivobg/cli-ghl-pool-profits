#!/usr/bin/env python3
"""Review rating gate in every account (Frank 10/11: "5 stars gets the link, anything below gets a feedback request
and notifies the business owner").

The V9 Review Request already asks for the NPS score (1–5) before the Google link and branches on it:
  "Low NPS Score Detected"  (NPS != 5 AND != 4)  → "Notify Team - Negative Feedback" (SMS to all users)
  "High NPS Score Detected" (else)               → Go To → Email + SMS review request (Google link)
What this script makes every account match:
  1. Low branch = NPS != 5 only (a 4 now gets the feedback path, not the Google link).
  2. First step of the Low branch = SMS to the customer asking what went wrong (template FEEDBACK_NAME, created in
     the account when missing), then the existing team notification.
Read-only by default; --apply backs up the workflow (backup/<slug>/review-request-<date>.json) and PUTs it.

  python3 scripts/pp_review_gate.py                       # report for every client account
  python3 scripts/pp_review_gate.py --only "Test Snapshot" --apply
"""
from __future__ import annotations

import argparse
import copy
import datetime as dt
import json
import os
import sys
import uuid

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
from cli_anything.gohighlevel.utils.agency import BACKEND, Agency, GHLError, match_location, slugify  # noqa: E402
from pp_dashboard import SKIP as DASH_SKIP  # noqa: E402

FEEDBACK_NAME = "NPS - Feedback Request (below 5)"
FEEDBACK_TEXT = ("Hi {{contact.first_name}}, thank you for rating {{custom_values.friendly_business_name}}. We're sorry we "
                 "didn't earn 5 stars this time. What could we have done better? Just reply to this text. The owner "
                 "reads every answer and will reach out to make it right.")
STEP_NAME = "SMS - Ask What Went Wrong"
# Snapshot master and the test account are in; the rest of the non-client accounts are not.
SKIP = (DASH_SKIP - {"Kvdj7o189zlS3caaCNuX", "hmzX5j1dPhOQKX2dH4kf", "OVQ4nVT6Ik0xlcSacRGL"})


def nps_conditions(branch: dict) -> list[dict]:
    return [c for seg in branch.get("segments", []) for c in seg.get("conditions", [])
            if c.get("conditionType") == "contact_detail" and c.get("conditionOperator") == "!="]


def find_gate(templates: list[dict]):
    """(if_else node, low branch dict, low branch node) — the if/else whose branch tests NPS != 5."""
    by_id = {t["id"]: t for t in templates}
    for t in templates:
        if t.get("type") != "if_else":
            continue
        for br in (t.get("attributes") or {}).get("branches") or []:
            if any(str(c.get("conditionValue")) == "5" for c in nps_conditions(br)):
                return t, br, by_id.get(br["id"])
    return None, None, None


def snippet_id(a: Agency, loc: str, apply: bool) -> str | None:
    for s in a.snippets(loc):
        if s.get("name") == FEEDBACK_NAME:
            return s.get("_id") or s.get("id")
    if not apply:
        return None
    res = a.call("POST", BACKEND, f"/snippets/{loc}",
                 body={"name": FEEDBACK_NAME, "type": "sms", "template": {"body": FEEDBACK_TEXT, "attachments": []}})
    r = res.get("snippet") or res
    return r.get("id") or r.get("_id")


def plan(a: Agency, loc: dict, apply: bool) -> str:
    lid, name = loc["id"], loc.get("name", "")
    wfs = [w for w in a.workflows(lid) if (w.get("name") or "").strip().lower() == "review request"]
    if not wfs:
        return "NO 'Review Request' workflow"
    notes = []
    for w in wfs:
        wf = a.workflow(lid, w["id"])
        tpl = (wf.get("workflowData") or {}).get("templates") or []
        gate, low, low_node = find_gate(tpl)
        if not gate:
            notes.append(f"{w.get('status')}: NO NPS gate")
            continue
        conds = nps_conditions(low)
        field = conds[0].get("conditionSubType")
        extra = [c for c in conds if str(c.get("conditionValue")) != "5"]
        by_id = {t["id"]: t for t in tpl}
        first = by_id.get((low_node or {}).get("next")) if low_node else None
        chain, cur = [], first
        while cur:
            chain.append(cur)
            cur = by_id.get(cur.get("next")) if isinstance(cur.get("next"), str) else None
        has_ask = any(s.get("type") == "sms" and s.get("name") == STEP_NAME for s in chain)
        has_notify = any(s.get("type") == "internal_notification" for s in chain)
        todo = []
        if extra:
            todo.append(f"drop NPS != {','.join(str(c.get('conditionValue')) for c in extra)}")
        if not has_ask:
            todo.append("add feedback SMS")
        state = f"{w.get('status')}: field {field}, notify {'yes' if has_notify else 'NO'}"
        if not todo:
            notes.append(state + " — ok")
            continue
        if not apply:
            notes.append(state + " — would " + "; ".join(todo))
            continue
        if not low_node:
            notes.append(state + " — low branch node missing, skipped")
            continue
        sid = snippet_id(a, lid, True)
        folder = os.path.join(ROOT, "backup", slugify(name))
        os.makedirs(folder, exist_ok=True)
        with open(os.path.join(folder, f"review-request-{w['id'][:8]}-{dt.date.today():%Y%m%d}.json"), "w") as fh:
            json.dump(wf, fh, indent=1)
        new = copy.deepcopy(wf)
        ntpl = new["workflowData"]["templates"]
        nby = {t["id"]: t for t in ntpl}
        ngate = nby[gate["id"]]
        for br in ngate["attributes"]["branches"]:
            if br["id"] == low["id"]:
                for seg in br.get("segments", []):
                    seg["conditions"] = [c for c in seg.get("conditions", [])
                                         if not (c.get("conditionType") == "contact_detail"
                                                 and c.get("conditionOperator") == "!="
                                                 and str(c.get("conditionValue")) != "5")]
        if not has_ask:
            bnode = nby[low["id"]]
            old_first = bnode.get("next")
            step_id = str(uuid.uuid4())
            step = {"id": step_id, "order": 0, "name": STEP_NAME, "type": "sms",
                    "attributes": {"template_id": sid, "attachments": []},
                    "parent": low["id"], "parentKey": low["id"]}
            if old_first:
                step["next"] = old_first
                nby[old_first]["parentKey"] = step_id
                k, cur = 1, nby[old_first]
                while cur:
                    cur["order"] = k
                    k += 1
                    cur = nby.get(cur.get("next")) if isinstance(cur.get("next"), str) else None
            bnode["next"] = step_id
            ntpl.insert(ntpl.index(bnode) + 1, step)
        body = {k: new[k] for k in new if k not in ("_id", "createdAt", "updatedAt", "__v")}
        a.call("PUT", BACKEND, f"/workflow/{lid}/{w['id']}", body=body)
        # verify
        chk = a.workflow(lid, w["id"])
        g2, l2, ln2 = find_gate(chk["workflowData"]["templates"])
        b2 = {t["id"]: t for t in chk["workflowData"]["templates"]}
        ok_cond = [str(c.get("conditionValue")) for c in nps_conditions(l2)] == ["5"]
        ok_ask = b2.get(ln2.get("next"), {}).get("name") == STEP_NAME
        notes.append(state + f" — APPLIED (only !=5: {ok_cond}, feedback SMS first: {ok_ask}, status {chk.get('status')})")
    return " | ".join(notes)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", action="append")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    a = Agency()
    locs = a.locations()
    if args.only:
        targets = [match_location(locs, o) or sys.exit(f"not found: {o}") for o in args.only]
    else:
        targets = [l for l in locs if l["id"] not in SKIP]
    for loc in sorted(targets, key=lambda l: l.get("name", "")):
        try:
            res = plan(a, loc, args.apply)
        except GHLError as exc:
            res = f"ERROR {exc}"
        print(f"{loc.get('name', '')[:34]:34} {res}")


if __name__ == "__main__":
    main()
