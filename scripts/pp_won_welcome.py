#!/usr/bin/env python3
"""Won Stage: welcome e-mail → wait 2 min → SMS also for repairs and construction (CRM guide decision 5).

    python3 scripts/pp_won_welcome.py --only "Aqua Clear Pool Services, Inc."            # plan
    python3 scripts/pp_won_welcome.py --only "Aqua Clear Pool Services, Inc." --apply

Texts = the ones Pedro approved for Corolla (10/11) and Aqua Clear (11/11); merge fields only, so any account works.
After "Mark won (Repairs / Installs)" / "Mark won (Construction)" (branch must end there): e-mail (html in the step AND in
the snippet), wait 2 min inside 08–18 every day (same as Corolla), SMS (snippet). Snippets reused by name if present.
--apply: backup/<slug>/won-stage-<stamp>.json, PUT, re-read (only the new steps + the Mark won `next` differ).
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
from cli_anything.gohighlevel.utils.agency import BACKEND, Agency, match_location, slugify  # noqa: E402

P = '<p class="custom-newline" style="line-height: 1.5;padding-left: 0px!important;">{}</p>'
SUBJECT = "Thank you for choosing {{custom_values.friendly_business_name}}!"
SIGN = ["{{custom_values.owner_first_name}}", "{{custom_values.friendly_business_name}}"]
CONTACT = ["📞 {{custom_values.business_phone}}", "📧 {{custom_values.business_email}}"]

KINDS = {
    "repair": {
        "branch": "Mark won (Repairs / Installs)", "label": "Repair",
        "email": ["{{contact.first_name}},", "<br>",
                  "Thank you for choosing {{custom_values.friendly_business_name}} for your pool repair! "
                  "We're glad you trusted us with your pool.", "<br>",
                  "If you have any questions about your job, don't hesitate to reach out.", *CONTACT, "<br>",
                  "Looking forward to taking care of your pool!", "<br>", *SIGN],
        "sms": "Hi {{contact.first_name}}! Thank you for choosing {{custom_values.friendly_business_name}} for your "
               "pool repair! 🏊 We're glad to have you on board. Questions about your job? Call us at "
               "{{custom_values.a2p_verification_number}}",
    },
    "construction": {
        "branch": "Mark won (Construction)", "label": "Construction",
        "email": ["{{contact.first_name}},", "<br>",
                  "Thank you for choosing {{custom_values.friendly_business_name}} for your pool project! "
                  "We're excited to get started and glad you trusted us with it.", "<br>",
                  "We'll be in touch soon with the next steps. If you have any questions in the meantime, "
                  "don't hesitate to reach out.", *CONTACT, "<br>",
                  "Looking forward to building something great together!", "<br>", *SIGN],
        "sms": "Hi {{contact.first_name}}! Thank you for choosing {{custom_values.friendly_business_name}} for your "
               "pool project! 🏊 We're excited to get started. Questions along the way? Call us at "
               "{{custom_values.a2p_verification_number}}",
    },
}


def snippet(a: Agency, lid: str, name: str, kind: str, content: str, existing: dict) -> str:
    if name in existing:
        return existing[name]
    tpl = {"html": content, "attachments": []} if kind == "email" else {"body": content, "attachments": []}
    res = a.call("POST", BACKEND, f"/snippets/{lid}", body={"name": name, "type": kind, "template": tpl})
    r = res.get("snippet") or res
    return r.get("id") or r.get("_id")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", required=True)
    ap.add_argument("--kinds", default="repair,construction")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    a = Agency()
    loc = match_location(a.locations(), args.only)
    if not loc:
        sys.exit(f"no account {args.only!r}")
    lid, name = loc["id"], loc["name"]
    w = [x for x in a.workflows(lid) if (x.get("name") or "").strip() == "Won Stage"]
    if len(w) != 1:
        sys.exit(f"{name}: {len(w)} 'Won Stage' workflows")
    wf = a.workflow(lid, w[0]["id"])
    new = copy.deepcopy(wf)
    tpl = new["workflowData"]["templates"]
    by_name = {t.get("name"): t for t in tpl}
    existing = {s.get("name"): s.get("_id") or s.get("id") for s in a.snippets(lid)}
    todo = []
    for k in args.kinds.split(","):
        spec = KINDS[k]
        mark = by_name.get(spec["branch"])
        if not mark:
            print(f"   {k}: no step {spec['branch']!r} — skipped")
            continue
        if mark.get("next"):
            nxt = next((t.get("name") for t in tpl if t["id"] == mark["next"]), mark["next"])
            print(f"   {k}: {spec['branch']!r} already continues ({nxt}) — skipped")
            continue
        todo.append((k, spec, mark))
        print(f"   {k}: add e-mail → wait 2 min (08–18) → SMS after {spec['branch']!r}")
    if not args.apply or not todo:
        print(f"== {name}: {len(todo)} branch(es) to add{'' if args.apply else ' (plan)'}")
        return
    folder = os.path.join(ROOT, "backup", slugify(name))
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, f"won-stage-{dt.datetime.now():%Y%m%d-%H%M}.json")
    with open(path, "w") as fh:
        json.dump(wf, fh, indent=1)
    for k, spec, mark in todo:
        html = "".join(P.format(x) for x in spec["email"])
        eid = snippet(a, lid, f"Won Stage - {spec['label']} Welcome Email", "email", html, existing)
        sid = snippet(a, lid, f"Won Stage - {spec['label']} Welcome SMS", "sms", spec["sms"], existing)
        e, wt, s = (str(uuid.uuid4()) for _ in range(3))
        order = (mark.get("order") or 1) + 1
        steps = [
            {"id": e, "order": order, "name": f"{spec['label']} Welcome Email", "type": "email",
             "parent": mark["id"], "parentKey": mark["id"], "next": wt,
             "attributes": {"html": html, "subject": SUBJECT, "fieldDefaults": {}, "htmlDefaults": {},
                            "conditions": [], "preHeader": "", "template_id": eid, "templatesource": "snippet",
                            "from_email": "", "from_name": "", "templateCreationMode": "existing",
                            "attachments": []}},
            {"id": wt, "order": order + 1, "name": "Wait 2 minutes", "type": "wait", "cat": "",
             "parent": e, "parentKey": e, "next": s,
             "attributes": {"type": "time", "startAfter": {"type": "minutes", "value": 2, "when": "after"},
                            "name": "Wait 2 minutes", "cat": "",
                            "window": {"condition": "when", "days": [0, 1, 2, 3, 4, 5, 6],
                                       "start": "08:00", "end": "18:00"},
                            "windowCondition": {"field": "", "operator": "", "value": ""},
                            "isHybridAction": True, "hybridActionType": "wait", "convertToMultipath": False,
                            "transitions": [], "timePeriodInputMode": "standard", "unitInputMode": "standard"}},
            {"id": s, "order": order + 2, "name": f"{spec['label']} Welcome SMS", "type": "sms",
             "parent": wt, "parentKey": wt, "attributes": {"template_id": sid, "attachments": []}},
        ]
        mark["next"] = e
        i = tpl.index(mark) + 1
        tpl[i:i] = steps
    body = {k: new[k] for k in new if k not in ("_id", "createdAt", "updatedAt", "__v")}
    a.call("PUT", BACKEND, f"/workflow/{lid}/{wf['id']}", body=body)
    chk = a.workflow(lid, wf["id"])
    t2 = {t.get("name"): t for t in chk["workflowData"]["templates"]}
    for k, spec, _ in todo:
        m = t2.get(spec["branch"]) or {}
        chain = []
        cur = m
        while cur.get("next") and len(chain) < 5:
            cur = next((t for t in chk["workflowData"]["templates"] if t["id"] == cur["next"]), {})
            chain.append(cur.get("name"))
        print(f"   {k}: {spec['branch']} → {' → '.join(map(str, chain))}")
    print(f"== {name}: APPLIED, status {chk.get('status')}, re-entry {chk.get('allowMultiple')}, "
          f"steps {len(wf['workflowData']['templates'])} → {len(chk['workflowData']['templates'])}; backup {path}")


if __name__ == "__main__":
    main()
