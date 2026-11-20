#!/usr/bin/env python3
"""Pool Palooza (Todd, Basecamp 18/11: "Go ahead with changes #1"): every form lead and booking gets a source tag from
its UTM/gclid. Todd's own flows (TAG Orchestrator / TAG Incoming Calls) stay untouched.

    python3 scripts/pz_source_tag.py plan
    python3 scripts/pz_source_tag.py test      # ZZ TEST copy + ZZ TEST contact (no attribution → "direct"), all deleted
    python3 scripts/pz_source_tag.py apply

"Lead Source - Tag (forms & bookings)": Free Trial / F1 - Mobile / F1 - Desktop submitted, or an appointment on
"Free Onsite Pool Service Quote" (todd-poolpalooza) → not DND → wait 1 min (attribution is saved with the submission)
→ copy the contact's last attribution into 2 fields ("Lead Session Source" = sessionSource + utmSource + utmMedium,
"Lead GCLID" = gclid) → Google Ads (gclid or "Paid Search") → tag adwords; Facebook ("Social", fb, facebook, ig,
instagram) → tag facebook; "Organic" → tag organic; else → tag direct. Tags added, never removed.
"""
from __future__ import annotations

import argparse
import sys
import time

from _common import load_dotenv
from ps_ads_forms import cond, if_else, outline, tags

import pd_lwr_google_leads as lwr
from cli_anything.gohighlevel.utils.agency import BACKEND, SERVICES, Agency

LOC = "AjePy51fOb6BM1Kk2QQX"
lwr.LOC = LOC
FLOW = "Lead Source - Tag (forms & bookings)"
FORMS = ["QccIB4S3uej3a6lVE8jE", "ON3VuxGdv6gwJv8SYpkm", "mV9voBC8l3n8LEPzOO0N"]  # Free Trial, F1 Mobile, F1 Desktop
CALENDAR = "u6pXCj1gTEwlEhsufECP"  # Free Onsite Pool Service Quote (todd-poolpalooza)
SESSION_F, GCLID_F = "Lead Session Source", "Lead GCLID"
TAGS = ["adwords", "facebook", "organic", "direct"]


def fields(cfs: dict) -> tuple[str, str, dict]:
    vals = [(SESSION_F, "{{contact.lastAttributionSource.sessionSource}} {{contact.lastAttributionSource.utmSource}} "
                        "{{contact.lastAttributionSource.utmMedium}}"),
            (GCLID_F, "{{contact.lastAttributionSource.gclid}}")]
    return ("update_contact_field", "Copy UTM / gclid", {
        "type": "update_contact_field", "actionType": "update_field_data",
        "fields": [{"field": cfs[n], "value": v, "title": n, "type": "text", "date": ""} for n, v in vals]})


def wait_min() -> tuple[str, str, dict]:
    return ("wait", "Wait 1 minute", {"type": "time", "startAfter": {"type": "minutes", "value": 1, "when": "after"},
                                      "name": "Wait 1 minute", "cat": "", "isHybridAction": True,
                                      "hybridActionType": "wait", "convertToMultipath": False, "transitions": []})


def build(cfs: dict, wait: bool = True) -> list[dict]:
    s = cfs[SESSION_F]
    route = ("ifelse", "Source", [
        ("Google Ads", [cond(cfs[GCLID_F], "has_value", ""), cond(s, "contains", "Paid Search")], [tags(["adwords"])]),
        ("Facebook", [cond(s, "contains", x) for x in ("Social", "fb", "facebook", "Facebook", "ig", "instagram")],
         [tags(["facebook"])]),
        ("Organic", [cond(s, "contains", "Organic")], [tags(["organic"])]),
    ], "Direct / other", [tags(["direct"])])
    nodes, _ = if_else("Not DND", [("Go", [cond("tags", "index-of-false", ["dnd"])],
                                    [*([wait_min()] if wait else []), fields(cfs), route])], "DND", [])
    return nodes


def triggers(wid: str, first: str) -> list[dict]:
    base = {"schedule_config": {}, "workflowId": wid, "workflow_id": wid, "location_id": LOC,
            "actions": [{"workflow_id": wid, "type": "add_to_workflow"}], "targetActionId": first, "masterType": "highlevel"}
    return [{**base, "type": "form_submission", "name": "Form Submitted (Free Trial / F1)", "conditions": [
                {"operator": "is-any-of", "field": "form.id", "value": FORMS, "title": "Form is", "type": "string"}]},
            {**base, "type": "appointment", "name": "Booked: Free Onsite Pool Service Quote", "conditions": [
                {"field": "appointment.eventType", "title": "Event Type", "type": "select", "value": "normal", "operator": "=="},
                {"field": "appointment.status", "title": "Appointment status is", "type": "select", "value": "confirmed",
                 "operator": "=="},
                {"field": "calendar.id", "title": "In calendar", "type": "select", "value": CALENDAR, "operator": "=="}]}]


def custom_fields(a: Agency, create: bool) -> dict:
    have = {f["name"]: f["id"] for f in a.call("GET", SERVICES, f"/locations/{LOC}/customFields").get("customFields", [])}
    for n in (SESSION_F, GCLID_F):
        if n not in have and create:
            r = a.call("POST", SERVICES, f"/locations/{LOC}/customFields",
                       body={"name": n, "dataType": "TEXT", "placeholder": "", "position": 0, "model": "contact"})
            have[n] = (r.get("customField") or r)["id"]
            print(f"   ✓ field {n}")
    return {n: have.get(n, f"<{n}>") for n in (SESSION_F, GCLID_F)}


def first_id(tpl: list[dict]) -> str:
    return next(s["id"] for s in tpl if not s.get("parentKey") and not s.get("parent"))


def install(a: Agency, name: str, tpl: list[dict], with_triggers: bool) -> str:
    wid = lwr.create(a, name, None, tpl)
    if with_triggers:
        for t in triggers(wid, first_id(tpl)):
            made = a.call("POST", BACKEND, f"/workflow/{LOC}/trigger", body=t)
            a.call("PUT", BACKEND, f"/workflow/{LOC}/trigger/{made['id']}", body={**t, "id": made["id"]})
    lwr.set_status(a, wid, "published")
    return wid


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mode", choices=["plan", "test", "apply"])
    args = ap.parse_args()
    load_dotenv()
    a = Agency()
    flows = {w["name"]: w["id"] for w in a.workflows(LOC)}
    cfs = custom_fields(a, args.mode != "plan")
    if args.mode != "plan":
        for t in TAGS:
            try:
                a.call("POST", BACKEND, f"/workflow/{LOC}/tags/create", body={"tag": t})
            except Exception:  # noqa: BLE001 — already exists
                pass
    if args.mode == "plan":
        print(f"   {FLOW}: {'existe' if FLOW in flows else 'cria'}\n{outline(build(cfs))}")
        return 0
    if args.mode == "test":
        wid = install(a, "ZZ TEST " + FLOW, build(cfs, wait=False), False)
        c = a.call("POST", SERVICES, "/contacts/", body={"locationId": LOC, "firstName": "ZZ TEST", "lastName": "source tag",
                                                       "email": f"zztest.source.{int(time.time())}@example.com"})["contact"]
        a.call("POST", SERVICES, f"/contacts/{c['id']}/workflow/{wid}", body={})
        time.sleep(40)
        got = a.call("GET", SERVICES, f"/contacts/{c['id']}")["contact"]
        vals = {f["id"]: f.get("value") for f in got.get("customFields", [])}
        print("   tags:", got.get("tags"), "| session:", repr(vals.get(cfs[SESSION_F])), "| gclid:", repr(vals.get(cfs[GCLID_F])))
        ok = "direct" in (got.get("tags") or [])
        a.call("DELETE", SERVICES, f"/contacts/{c['id']}")
        a.call("DELETE", BACKEND, f"/workflow/{LOC}/{wid}")
        print("   ✓ test ok (deleted)" if ok else "   ✗ test FAILED (deleted)")
        return 0 if ok else 1
    if FLOW in flows:
        print(f"   {FLOW}: já existe ({flows[FLOW]})")
        return 0
    wid = install(a, FLOW, build(cfs), True)
    got = a.workflow(LOC, wid)
    trs = [t for t in a.triggers(LOC, wid) if not t.get("deleted")]
    print(f"   {FLOW} ({wid}): {got['status']} · gatilhos {[(t['type'], t.get('active')) for t in trs]}")
    return 0 if got["status"] == "published" and len(trs) == 2 and all(t.get("active") for t in trs) else 1


if __name__ == "__main__":
    sys.exit(main())
