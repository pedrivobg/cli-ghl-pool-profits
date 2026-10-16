#!/usr/bin/env python3
"""Tag rule: when a contact gets tag A, also add tag B (published workflow) + backfill.

    ./.venv/bin/python scripts/pp_tag_rule.py --only "Sunwave" --when "website form fill" \\
        --add "google ads lead form" --name "Google Ads Lead Form - Tag"          # plan
    ... --apply [--skip-email spiderparker@icanmarvel.com]

Sunwave (Val, 16/10): Google Ads lead-form leads come in through Zapier with source and tag
"website form fill" (attribution medium "zapier"; nothing else in the account uses that tag). Val
wants a tag that says where they came from. The workflow adds it to every new one; --apply also adds
it to the contacts that already have tag A (except --skip-email, e.g. a test contact). The cleaner fix
is in the Zap itself (tag/source), which lives in Zapier, not in GHL.
"""
from __future__ import annotations

import argparse
import time
import uuid

from _common import load_dotenv, location_dirs
from pp_audit import load

from cli_anything.gohighlevel.utils.agency import BACKEND, SERVICES, Agency


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--only", required=True)
    parser.add_argument("--when", required=True, help="tag that triggers")
    parser.add_argument("--add", required=True, help="tag to add")
    parser.add_argument("--name", required=True, help="workflow name")
    parser.add_argument("--skip-email", action="append", default=[])
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    load_dotenv()
    a = Agency()
    d = location_dirs([args.only])[0]
    loc = load(d / "location.json", {})["id"]
    have = a.call("POST", SERVICES, "/contacts/search", body={
        "locationId": loc, "pageLimit": 100,
        "filters": [{"field": "tags", "operator": "contains", "value": args.when}]}).get("contacts", [])
    todo = [c for c in have if args.add not in (c.get("tags") or []) and (c.get("email") or "") not in args.skip_email]
    exists = any(w["name"] == args.name for w in a.workflows(loc))
    print(f"== {d.name}: workflow '{args.name}' {'já existe' if exists else 'novo'}: tag '{args.when}' → + '{args.add}'")
    print(f"   backfill: {len(todo)} contato(s) com '{args.when}' sem '{args.add}'")
    if not args.apply:
        return 0
    try:
        a.call("POST", BACKEND, f"/workflow/{loc}/tags/create", body={"tag": args.add})
    except Exception:
        pass  # already exists
    if not exists:
        res = a.call("POST", BACKEND, f"/workflow/{loc}", body={"name": args.name, "status": "draft"})
        wid = res.get("id") or res.get("_id")
        step = {"id": str(uuid.uuid4()), "order": 0, "name": f"Add Tag {args.add}", "type": "add_contact_tag",
                "attributes": {"tags": [args.add], "type": "add_contact_tag"}}
        a.call("PUT", BACKEND, f"/workflow/{loc}/{wid}", body={
            "name": args.name, "version": 1, "status": "published", "allowMultiple": False,
            "workflowData": {"templates": [step]}})
        trig = {"type": "contact_tag", "name": "Contact Tag", "masterType": "highlevel", "schedule_config": {},
                "conditions": [{"operator": "index-of-true", "field": "tagsAdded", "value": args.when,
                                "title": "Tag Added", "type": "select", "id": "tag-added"}],
                "actions": [{"workflow_id": wid, "type": "add_to_workflow"}], "workflowId": wid, "workflow_id": wid,
                "location_id": loc, "targetActionId": step["id"]}
        t = a.call("POST", BACKEND, f"/workflow/{loc}/trigger", body=trig)
        a.call("PUT", BACKEND, f"/workflow/{loc}/trigger/{t['id']}", body={**trig, "id": t["id"]})
        time.sleep(4)
        after = a.workflow(loc, wid)
        trs = [x for x in a.triggers(loc, wid) if not x.get("deleted")]
        print(f"   {'✓' if after.get('status') == 'published' and len(trs) == 1 else '✗ VERIFICAR'} workflow {after.get('status')}")
    for c in todo:
        a.call("POST", SERVICES, f"/contacts/{c['id']}/tags", body={"tags": [args.add]})
    time.sleep(3)
    ok = sum(args.add in (a.call("GET", SERVICES, f"/contacts/{c['id']}")["contact"].get("tags") or []) for c in todo)
    print(f"   {'✓' if ok == len(todo) else '✗ VERIFICAR'} backfill {ok}/{len(todo)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
