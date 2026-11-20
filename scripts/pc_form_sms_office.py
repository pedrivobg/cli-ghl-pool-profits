#!/usr/bin/env python3
"""Passion Pool Care (John, Basecamp 20/11): website form leads only reached the e-mail.

Live state 20/11: "Website Form Fill To Pipeline" and "Website Webhook Lead To Pipeline" text the NEW LEAD alert to the
user John Dixon (+1 623-764-2078), and that number replied STOP on 18/11 ("DnD enabled by user"), so nothing goes out.
The Google Ads alerts already go to the office phone (+1 615-624-7624, custom_sms) and are delivered.

This points the "New Lead SMS" step of both workflows to the office phone (custom_sms, same as the AdWords flows).
Text, status, re-entry and everything else unchanged. Backup in backup/passion-pool-care-lp/.

    python3 scripts/pc_form_sms_office.py            # plan
    python3 scripts/pc_form_sms_office.py --apply
"""
from __future__ import annotations

import argparse
import json
import time

from _common import ROOT, load_dotenv

LOC = "d03SMzI37dxTBeuoTJ13"
OFFICE = "+1 615-624-7624"
WFS = ["1a2ae47d-ca34-44a0-b7da-3c5c446c85f1",   # Website Form Fill To Pipeline
       "313cdeaf-4acc-4f36-91a5-7f5213a17e23"]   # Website Webhook Lead To Pipeline


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    load_dotenv()
    from cli_anything.gohighlevel.utils.agency import Agency, BACKEND
    a = Agency()
    bad = 0
    for wid in WFS:
        live = a.workflow(LOC, wid)
        steps = live["workflowData"]["templates"]
        hits = [s for s in steps if s.get("type") == "internal_notification"
                and (s.get("attributes") or {}).get("type") == "sms"
                and s["attributes"]["sms"].get("to") != OFFICE]
        print(f"{live['name']} ({live['status']}): {len(hits)} SMS para trocar")
        if not hits or not args.apply:
            continue
        d = ROOT / "backup" / "passion-pool-care-lp"
        d.mkdir(parents=True, exist_ok=True)
        (d / f"{wid}-office-sms-{time.strftime('%Y%m%d-%H%M%S')}.json").write_text(json.dumps(live, indent=1))
        for s in hits:
            sms = s["attributes"]["sms"]
            sms.pop("selectedUser", None)
            sms["userType"] = "custom_sms"
            sms["to"] = OFFICE
        a.call("PUT", BACKEND, f"/workflow/{LOC}/{wid}", body={
            "name": live["name"], "version": live.get("version", 2), "status": live["status"],
            "allowMultiple": live.get("allowMultiple", True), "workflowData": {"templates": steps}})
        time.sleep(4)
        after = a.workflow(LOC, wid)
        ok = all(s["attributes"]["sms"].get("to") == OFFICE for s in after["workflowData"]["templates"]
                 if s.get("type") == "internal_notification" and s["attributes"].get("type") == "sms")
        ok = ok and after["status"] == live["status"] and after.get("allowMultiple") == live.get("allowMultiple")
        print(f"   {'ok' if ok else 'DIFERENTE'} (status {after['status']}, re-entry {after.get('allowMultiple')})")
        bad += not ok
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
