#!/usr/bin/env python3
"""Let the team move an already-serviced customer to Won without the Won automations.

    ./.venv/bin/python scripts/pp_skip_tag.py --only "Southern Pool"            # plan
    ./.venv/bin/python scripts/pp_skip_tag.py --only "Southern Pool" --apply

Adds the trigger filter "Doesn't Have Tag: existing customer" (same shape the GHL UI
saves) to every Won-stage trigger of the workflows below, and creates the tag.
To use it: add the tag "existing customer" to the contact, THEN move the card to Won.
The card moves normally; welcome email/SMS, review request and the Ads conversion
do not fire for that contact. Trigger backups go to backup/<slug>/.
"""
from __future__ import annotations

import argparse
import json
import time

from _common import ROOT, load_dotenv, location_dirs
from pp_audit import load

from cli_anything.gohighlevel.utils.agency import BACKEND, Agency, GHLError

TAG = "existing customer"
WORKFLOWS = ("Won Stage", "Review Request", "Adword Call - Conversion", "Post-Appointment Follow-up")
FILTER = {"field": "contact.tags", "id": "doesnot-have-tag", "type": "select",
          "title": "Doesn't Have Tag", "value": TAG, "operator": "index-of-false"}
DROP = ("_id", "date_added", "date_updated", "deleted", "origin_id", "company_id",
        "company_age", "last_conditions_change_at", "belongs_to")


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
        print(f"== {load(d / 'location.json', {}).get('name')}")
        won = {s["id"]: s["name"] for p in a.pipelines(loc) for s in p["stages"] if "won" in s["name"].lower()}
        bdir = ROOT / "backup" / d.name
        bdir.mkdir(parents=True, exist_ok=True)
        if args.apply:
            try:
                a.call("POST", BACKEND, f"/workflow/{loc}/tags/create", body={"tag": TAG})
            except GHLError as exc:
                if exc.status != 409:  # 409 = the tag already exists
                    raise
        for w in a.workflows(loc):
            if w["name"] not in WORKFLOWS:
                continue
            for t in a.triggers(loc, w["id"]):
                if t.get("deleted") or t.get("type") != "pipeline_stage_updated":
                    continue
                stage = next((c["value"] for c in t["conditions"] if c.get("field") == "opportunity.pipelineStageId"), None)
                if stage not in won:
                    continue
                if any(c.get("field") == "contact.tags" and c.get("value") == TAG for c in t["conditions"]):
                    print(f"   = {w['name']} [{w.get('status')}] ← {won[stage]}: já tem o filtro")
                    continue
                print(f"   + {w['name']} [{w.get('status')}] ← {won[stage]}")
                if not args.apply:
                    continue
                (bdir / f"trigger-{t['id']}-{time.strftime('%Y%m%d-%H%M%S')}.json").write_text(
                    json.dumps(t, ensure_ascii=False, indent=1))
                body = {k: v for k, v in t.items() if k not in DROP}
                body["conditions"] = t["conditions"] + [dict(FILTER)]
                a.call("PUT", BACKEND, f"/workflow/{loc}/trigger/{t['id']}", body=body)
                after = next(x for x in a.triggers(loc, w["id"]) if x["id"] == t["id"])
                ok = any(c.get("operator") == "index-of-false" and c.get("value") == TAG for c in after["conditions"])
                print(f"     {'✓' if ok else '✗ VERIFICAR'} filtro gravado, ativo={after.get('active')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
