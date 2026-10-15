#!/usr/bin/env python3
"""Point "AdWords Form - New Lead" at the form actually used on the Google Ads landing page.

    ./.venv/bin/python scripts/pp_ads_form.py --only "Sunwave" --form "Google ADS - FORM" \\
        --notify "Davey Connolly" --notify "David Connolly"            # plan
    ... --apply

Sunwave (Val, 15/10, launch day): the landing go.sunwavepoolpros.com/sunwave-weekly now uses
"Google ADS - FORM", but the workflow that tags (new lead / new form fill / adwords), creates the card,
sends the Google Ads conversion and the auto-reply still listened to the snapshot's "Landing Page -
Optin Form" (never submitted). The form is added to the trigger (old one kept), and the internal SMS
that went to the contact owner (empty on form leads) goes to --notify users. Backup first.
"""
from __future__ import annotations

import argparse
import json
import time

from _common import ROOT, load_dotenv, location_dirs
from pp_audit import load
from pp_won_stage import DROP

from cli_anything.gohighlevel.utils.agency import BACKEND, Agency

WORKFLOW = "AdWords Form - New Lead"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--only", required=True)
    parser.add_argument("--form", required=True, help="form name on the landing page")
    parser.add_argument("--notify", action="append", default=[], help="user name for the internal SMS")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    load_dotenv()
    a = Agency()
    d = location_dirs([args.only])[0]
    loc = load(d / "location.json", {})["id"]
    forms = {f["name"]: f.get("_id") or f.get("id") for f in a.forms(loc)}
    users = {u.get("name"): u["id"] for u in a.users(loc)}
    fid = forms[args.form]
    notify = [users[n] for n in args.notify]
    wid = next(w["id"] for w in a.workflows(loc) if w["name"] == WORKFLOW)
    live = a.workflow(loc, wid)
    trs = [t for t in a.triggers(loc, wid) if not t.get("deleted")]
    trig = next(t for t in trs if t["type"] == "form_submission")
    cond = next(c for c in trig["conditions"] if c.get("field") == "form.id")
    names = {v: k for k, v in forms.items()}
    print(f"== {d.name}: {WORKFLOW} [{live['status']}] escuta {[names.get(v, v) for v in cond['value']]}")
    tpl = json.loads(json.dumps(live["workflowData"]["templates"]))
    owner = [s for s in tpl if s["type"] == "internal_notification" and s["attributes"].get("type") == "sms"
             and s["attributes"]["sms"].get("userType") == "assign"]
    add_form = fid not in cond["value"]
    print(f"   + form {args.form} ({fid})" if add_form else f"   já escuta {args.form}")
    if owner:
        print(f"   SMS interno: dono do contato → {args.notify}" if notify else "   SMS interno vai para o dono do contato (passe --notify)")
    if not args.apply or not (add_form or (owner and notify)):
        return 0
    bdir = ROOT / "backup" / d.name
    bdir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    (bdir / f"workflow-{wid}-{stamp}.json").write_text(json.dumps({"workflow": live, "triggers": trs}))
    if owner and notify:
        for s in owner:
            sms = s["attributes"]["sms"]
            sms.pop("assignedOwners", None)
            sms.update(userType="user", selectedUser=notify)
            s.pop("incompleteData", None)
        a.call("PUT", BACKEND, f"/workflow/{loc}/{wid}", body={
            "name": live["name"], "version": live.get("version", 1), "status": live["status"],
            "parentId": live.get("parentId"), "allowMultiple": live.get("allowMultiple", False),
            "workflowData": {"templates": tpl}})
    if add_form:
        body = {k: v for k, v in trig.items() if k not in DROP}
        body["conditions"] = [{**c, "value": [*c["value"], fid]} if c is cond else c for c in trig["conditions"]]
        body.update(workflowId=wid, workflow_id=wid, location_id=loc,
                    actions=[{"workflow_id": wid, "type": "add_to_workflow"}])
        a.call("PUT", BACKEND, f"/workflow/{loc}/trigger/{trig['id']}", body=body)
    time.sleep(4)
    after = a.workflow(loc, wid)
    t2 = next(t for t in a.triggers(loc, wid) if t["id"] == trig["id"])
    got = next(c for c in t2["conditions"] if c.get("field") == "form.id")["value"]
    sms_ok = all(s["attributes"]["sms"].get("selectedUser") == notify for s in after["workflowData"]["templates"]
                 if s["id"] in {x["id"] for x in owner}) if notify else True
    ok = fid in got and after["status"] == live["status"] and sms_ok
    print(f"   {'✓' if ok else '✗ VERIFICAR'} {after['status']} · escuta {[names.get(v, v) for v in got]} · SMS ok={sms_ok}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
