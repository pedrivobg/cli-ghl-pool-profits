#!/usr/bin/env python3
"""Make every lead form reach the pipeline exactly once.

    ./.venv/bin/python scripts/pp_forms.py --only "Southern Pool"            # plan
    ./.venv/bin/python scripts/pp_forms.py --only "Southern Pool" --apply

Rule: a lead form (Main Website Form, Landing Page, Service Page - Contact,
Lead Gen) that no published workflow listens to is added to the form trigger
of "Website Form Fill To Pipeline" (created if the workflow has none). A form
some other published workflow already listens to (e.g. Landing Page in a
published AdWords Form workflow) is left alone, so nothing enters twice.

Works live (no dump needed); the trigger is backed up before it changes.
"""
from __future__ import annotations

import argparse
import json
import time

from _common import ROOT, load_dotenv, location_dirs
from pp_audit import load

from cli_anything.gohighlevel.utils.agency import BACKEND, Agency

LEAD_FORM_HINTS = ("main website form", "website form", "landing page", "service page - contact",
                   "lead gen", "contact form", "contact us", " lp", "google ads",
                   "quote")  # Passion's site forms "PPC - Home Quote" / "PPC - Universal Quote" (15/10)
NOT_LEADS = ("nps", "post-visit", "onboarding", "appointment booking")
WORKFLOW = "Website Form Fill To Pipeline"
DROP = ("id", "_id", "date_added", "date_updated", "deleted", "origin_id", "company_id",
        "company_age", "last_conditions_change_at", "belongs_to")


def is_lead_form(name: str) -> bool:
    n = name.lower()
    return any(h in n for h in LEAD_FORM_HINTS) and not any(x in n for x in NOT_LEADS)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--only", action="append", required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    load_dotenv()
    a = Agency()
    for d in location_dirs(args.only):
        loc = load(d / "location.json", {})["id"]
        name = load(d / "location.json", {}).get("name")
        forms = {f.get("_id") or f.get("id"): f["name"] for f in a.forms(loc)}
        wfs = a.workflows(loc)
        target = sorted([w for w in wfs if w["name"] == WORKFLOW],
                        key=lambda w: (w.get("status") != "published", w.get("createdAt", "")))
        if not target:
            print(f"== {name}: sem '{WORKFLOW}'")
            continue
        target = target[0]
        listeners: dict[str, list[str]] = {}
        own_trigger = None
        for w in wfs:
            for t in a.triggers(loc, w["id"]):
                if t.get("deleted") or t.get("type") != "form_submission":
                    continue
                if w["id"] == target["id"]:
                    own_trigger = t
                    continue
                if w.get("status") != "published":
                    continue
                for c in t.get("conditions") or []:
                    for v in c["value"] if isinstance(c.get("value"), list) else [c.get("value")]:
                        listeners.setdefault(v, []).append(w["name"])
        current = []
        if own_trigger:
            for c in own_trigger.get("conditions") or []:
                if c.get("field") == "form.id":
                    current += c["value"] if isinstance(c["value"], list) else [c["value"]]
        want = [f for f in current if f in forms and f not in listeners]
        want += [f for f, n in forms.items() if is_lead_form(n) and f not in listeners and f not in want]
        print(f"== {name}  ({target['status']})")
        for f, n in sorted(forms.items(), key=lambda x: x[1]):
            who = listeners.get(f)
            mark = "→ Website Form Fill" if f in want else (f"já em: {', '.join(who)}" if who else "não é lead / ninguém")
            print(f"   {n[:38]:38} {f[:6]}  {mark}")
        if sorted(want) == sorted(current):
            print("   nada a mudar")
            continue
        if not args.apply:
            continue
        live = a.workflow(loc, target["id"])
        first = ((live.get("workflowData") or {}).get("templates") or [{}])[0].get("id")
        cond = [{"operator": "is-any-of", "field": "form.id", "value": want, "title": "Form is", "type": "string"}]
        bdir = ROOT / "backup" / d.name
        bdir.mkdir(parents=True, exist_ok=True)
        if own_trigger:
            (bdir / f"trigger-{own_trigger['id']}-{time.strftime('%Y%m%d-%H%M%S')}.json").write_text(
                json.dumps(own_trigger, ensure_ascii=False, indent=1))
            body = {k: v for k, v in own_trigger.items() if k not in DROP}
            body.update({"id": own_trigger["id"], "conditions": cond})
            a.call("PUT", BACKEND, f"/workflow/{loc}/trigger/{own_trigger['id']}", body=body)
        else:
            body = {"type": "form_submission", "masterType": "highlevel", "name": "Form Submitted",
                    "schedule_config": {}, "workflowId": target["id"], "workflow_id": target["id"],
                    "location_id": loc, "active": True, "targetActionId": first, "conditions": cond,
                    "actions": [{"workflow_id": target["id"], "type": "add_to_workflow"}]}
            res = a.call("POST", BACKEND, f"/workflow/{loc}/trigger", body=body)
            if res.get("id"):
                a.call("PUT", BACKEND, f"/workflow/{loc}/trigger/{res['id']}", body={**body, "id": res["id"]})
        time.sleep(2)
        after = [t for t in a.triggers(loc, target["id"]) if t.get("type") == "form_submission"]
        got = [v for t in after for c in t["conditions"] for v in (c["value"] if isinstance(c["value"], list) else [c["value"]])]
        print(f"   {'✓' if sorted(got) == sorted(want) else '✗ VERIFICAR'} gatilho agora: {[forms.get(g, g) for g in got]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
