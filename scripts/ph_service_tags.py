#!/usr/bin/env python3
"""Poolheads (Vikkar/Frank, Basecamp 24/11 "Website Updates: Leak Detection & Pool Repairs"): the site form's service list
and a tag per service, so leak/repair leads can be told apart from weekly leads.

    python3 scripts/ph_service_tags.py plan
    python3 scripts/ph_service_tags.py test     # ZZ TEST copy of the flow + one ZZ TEST contact per option; all deleted
    python3 scripts/ph_service_tags.py apply

1. Custom field "Service Needed" (6X93EGQHXTJezBox5KqU, used only by the 2 site forms) → the 6 options below.
2. The 2 site forms ("PoolHeads Home Quote" on the home page, "PoolHeads Service Quote v2" on the service pages): same
   options on the field (read from the newest version file, saved with keep_redirect). Backups in backup/poolheads/.
3. Flow "Service Needed - Tag (site forms)": either form submitted → if/else on Service Needed → tag (existing tag names
   kept: leak detection / leak repair / pool repair / weekly service). Tags are only added.
"""
from __future__ import annotations

import json
import sys
import time

import requests

from _common import ROOT, keep_redirect, load_dotenv
from ps_ads_forms import cond, if_else, tags

import pd_lwr_google_leads as lwr
from cli_anything.gohighlevel.utils.agency import BACKEND, SERVICES, Agency

LOC = "PeUynYCMm8e6PJMy785O"
lwr.LOC = LOC
FIELD = "6X93EGQHXTJezBox5KqU"
FORMS = {"E9ZMLZ7YU229zQzjZv88": "PoolHeads Home Quote", "00UuYWT5vZIqwIheNBym": "PoolHeads Service Quote v2"}
FLOW = "Service Needed - Tag (site forms)"
OPTIONS = {  # option → tags
    "Pool Leak Detection": ["leak detection"],
    "Pool Leak Repair": ["leak repair"],
    "Pool Equipment Repair": ["pool repair", "equipment repair"],
    "Pool Equipment Installation": ["equipment installation"],
    "Weekly Pool Service": ["weekly service"],
    "Other": ["other service"],
}
BDIR = ROOT / "backup" / "poolheads"


def latest(a: Agency, fid: str) -> tuple[dict, dict]:
    g = a.call("GET", BACKEND, f"/forms/{fid}")["form"]
    vh = sorted(g.get("versionHistory") or [], key=lambda v: v.get("updatedAt", ""))
    fd = requests.get(vh[-1]["formDataDownloadUrl"], timeout=30).json() if vh else g["formData"]
    return g, fd


def build() -> list[dict]:
    nodes, _ = if_else("Service Needed", [(opt, [cond(FIELD, "==", opt)], [tags(t)]) for opt, t in OPTIONS.items()],
                       "Not set", [])
    return nodes


def install(a: Agency, name: str, with_triggers: bool) -> str:
    tpl = build()
    wid = lwr.create(a, name, None, tpl)
    if with_triggers:
        first = next(s["id"] for s in tpl if not s.get("parentKey") and not s.get("parent"))
        t = {"schedule_config": {}, "workflowId": wid, "workflow_id": wid, "location_id": LOC, "type": "form_submission",
             "name": "Site form submitted", "actions": [{"workflow_id": wid, "type": "add_to_workflow"}],
             "targetActionId": first, "masterType": "highlevel",
             "conditions": [{"operator": "is-any-of", "field": "form.id", "value": list(FORMS), "title": "Form is",
                             "type": "string"}]}
        made = a.call("POST", BACKEND, f"/workflow/{LOC}/trigger", body=t)
        a.call("PUT", BACKEND, f"/workflow/{LOC}/trigger/{made['id']}", body={**t, "id": made["id"]})
    lwr.set_status(a, wid, "published")
    return wid


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else "plan"
    load_dotenv()
    a = Agency()
    BDIR.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    cf = a.call("GET", SERVICES, f"/locations/{LOC}/customFields/{FIELD}")["customField"]
    print("field now:", cf["picklistOptions"])
    if mode != "plan":
        for tg in {t for ts in OPTIONS.values() for t in ts}:
            try:
                a.call("POST", BACKEND, f"/workflow/{LOC}/tags/create", body={"tag": tg})
            except Exception:  # noqa: BLE001 — exists
                pass
    if mode == "test":  # needs the new options on the field: option values are only stored if they exist
        if cf["picklistOptions"] != list(OPTIONS):
            print("run apply-field first (options must exist to store the test values)")
            return 1
        wid = install(a, "ZZ TEST " + FLOW, False)
        bad = 0
        for opt, want in OPTIONS.items():
            c = a.call("POST", SERVICES, "/contacts/", body={
                "locationId": LOC, "firstName": "ZZ TEST", "lastName": "service tag",
                "email": f"zztest.svc.{int(time.time() * 1000)}@example.com",
                "customFields": [{"id": FIELD, "field_value": opt}]})["contact"]
            a.call("POST", SERVICES, f"/contacts/{c['id']}/workflow/{wid}", body={})
            time.sleep(25)
            got = a.call("GET", SERVICES, f"/contacts/{c['id']}")["contact"].get("tags") or []
            ok = all(t in got for t in want) and not (set(got) & ({t for ts in OPTIONS.values() for t in ts} - set(want)))
            bad += not ok
            print(f"   {'ok' if ok else 'FAIL'}  {opt:28} → {got}")
            a.call("DELETE", SERVICES, f"/contacts/{c['id']}")
        a.call("DELETE", BACKEND, f"/workflow/{LOC}/{wid}")
        print("   test copy + contacts deleted")
        return 1 if bad else 0
    if mode in ("apply", "apply-field"):
        (BDIR / f"field-{FIELD}-{stamp}.json").write_text(json.dumps(cf))
        a.call("PUT", SERVICES, f"/locations/{LOC}/customFields/{FIELD}",
               body={"name": cf["name"], "dataType": cf["dataType"], "placeholder": cf.get("placeholder", ""),
                     "position": cf.get("position", 0), "options": list(OPTIONS)})
        time.sleep(3)
        print("field after:", a.call("GET", SERVICES, f"/locations/{LOC}/customFields/{FIELD}")["customField"]["picklistOptions"])
        if mode == "apply-field":
            return 0
    for fid, name in FORMS.items():
        g, fd = latest(a, fid)
        f = next(x for x in fd["form"]["fields"] if x.get("tag") == FIELD)
        print(f"form {name}: {f.get('picklistOptions')} → {list(OPTIONS)}")
        if mode == "apply":
            (BDIR / f"form-{fid}-{stamp}.json").write_text(json.dumps({"form": g, "formData": fd}))
            f["picklistOptions"] = list(OPTIONS)
            f["calculatedOptions"] = [{"calculatedValue": "", "label": o} for o in OPTIONS]  # the widget renders these
            if "options" in f:
                f["options"] = list(OPTIONS)
            a.call("POST", BACKEND, f"/forms/{fid}", body={"name": g.get("name") or name, "formData": keep_redirect(fd)})
            time.sleep(5)
            _, now = latest(a, fid)
            nf = next(x for x in now["form"]["fields"] if x.get("tag") == FIELD)
            print("   calculatedOptions:", [o["label"] for o in nf.get("calculatedOptions") or []])
            act = now["form"].get("formAction") or {}
            print(f"   saved: {nf.get('picklistOptions')} · action {act.get('actionType')} redirect_url={bool(act.get('redirect_url'))}")
    flows = {w["name"]: w["id"] for w in a.workflows(LOC)}
    if mode == "plan":
        print(f"flow {FLOW}: {'exists' if FLOW in flows else 'create'} ({len(build())} nodes)")
        return 0
    if FLOW in flows:
        print(f"flow exists ({flows[FLOW]})")
        return 0
    wid = install(a, FLOW, True)
    trs = [t for t in a.triggers(LOC, wid) if not t.get("deleted")]
    print(f"flow {FLOW} ({wid}): {a.workflow(LOC, wid)['status']} · triggers {[(t['type'], t.get('active')) for t in trs]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
