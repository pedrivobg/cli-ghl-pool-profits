#!/usr/bin/env python3
"""NorTex: the Weekly landing page becomes the Meta Ads page; Meta Conversions API "Lead" and "Schedule" (Val, 03/11).

    ./.venv/bin/python scripts/nx_meta_capi.py plan
    ./.venv/bin/python scripts/nx_meta_capi.py check     # the dataset + token answer at Meta (no event sent)
    ./.venv/bin/python scripts/nx_meta_capi.py apply

Val: Meta Ads → Premium Weekly Pool Cleaning page, Google Ads → Pool Equipment Repairs page. Dataset 2163998117807974;
the access token is in her draft "Forms/Meta Conversion API" (read from there, never printed).
- "Google Ads LP - Weekly" → "Meta Ads LP - Weekly": tags `meta ads - weekly` + `meta ads` (instead of `google ads -
  weekly` + `adwords`), 24 h tag, Landing Page value, card source and alerts say Meta Ads. Its Google Ads conversion step
  becomes the Meta "Lead" event (Conversions API, funnel event, fbclid of the submission), new lead branch, right after
  the card: fires on the submit, booked or not. The form is renamed "META ADS – WEEKLY" (same id, redirect kept).
- "Appointment Booked -> Notify Fareed" (every booking, both calendars): after the alerts and the Google "Appointment
  Booked" upload (gclid only), an if/else "Meta Ads weekly lead?" (tag `meta ads - weekly`) → Meta "Schedule" event.
  So "Schedule" fires only for bookings by Weekly page leads; the Google one only counts ad clicks with a gclid.
- "Google Ads LP - Repair" unchanged (Google Ads, "LP Form Submit").
GET + backup before each PUT.
"""
from __future__ import annotations

import argparse
import json
import sys
import time

import requests

from _common import ROOT, keep_redirect, load_dotenv
from bv_service_forms import latest_form_data
from ps_ads_forms import if_else, outline

from cli_anything.gohighlevel.utils.agency import BACKEND, Agency

LOC = "k6nDPHktS2PySJoJuwpG"
DATASET = "2163998117807974"
VAL_DRAFT = "bf3d368c-5401-476f-bc67-5a2ba60ba989"
WEEKLY = "8d2d0344-d14b-41c8-9e3d-39044bf09cba"
BOOKED = "5dd0dc33-7705-49bb-a31c-9d7b681c8739"
FORM, FORM_NAME = "lxtvCbfxc4lDxC50Sifc", "META ADS – WEEKLY"
FLOW_NAME = "Meta Ads LP - Weekly"
TAG = "meta ads - weekly"
SWAP = [("google ads lp weekly 24h", "meta ads lp weekly 24h"), ("google ads - weekly", TAG), ('"adwords"', '"meta ads"'),
        ("Google Ads landing page", "Meta Ads landing page"), ("Google Ads LP - Premium", "Meta Ads LP - Premium"),
        ("Google Ads LP - Weekly", "Meta Ads LP - Weekly"), ("NEW GOOGLE ADS LEAD", "NEW META ADS LEAD"),
        ("New Google Ads lead", "New Meta Ads lead")]
BDIR = ROOT / "backup" / "nortex-pools"


def token(a: Agency) -> str:
    for s in a.workflow(LOC, VAL_DRAFT)["workflowData"]["templates"]:
        if s["type"] == "facebook_conversion_api" and s["attributes"].get("pixel_id") == DATASET:
            return s["attributes"]["access_token"]
    sys.exit("token não encontrado no draft da Val")


def meta(event: str, tok: str, fbclid: str) -> dict:
    return {"type": "facebook_conversion_api", "event_type": "funnel_event", "event_name": event, "pixel_id": DATASET,
            "access_token": tok, "currency": "USD", "connection_type": "INTEGRATION",
            "customMapping": {"fbClidId": fbclid}, "isCustomMappingEnabled": True}


def weekly(tpl: list[dict], tok: str) -> list[dict]:
    raw = json.dumps(tpl, ensure_ascii=False)
    for old, new in SWAP:
        raw = raw.replace(old, new)
    out = json.loads(raw)
    for s in out:
        if s["type"] == "google_adword":  # same node, so the chain around it stays as it is
            s["type"], s["name"] = "facebook_conversion_api", "Meta Lead event"
            s["attributes"] = meta("Lead", tok, "{{contact.lastAttributionSource.fbclid}}")
    return out


def booked(tpl: list[dict], tok: str) -> list[dict]:
    if any(s["type"] == "facebook_conversion_api" for s in tpl):
        return tpl
    out = json.loads(json.dumps(tpl))
    last = next(s for s in out if not s.get("next") and not s.get("parent"))
    # the booking widget's own visit has no fbclid: use the first visit's (the landing page)
    nodes, head = if_else("Meta Ads weekly lead?", [
        ("Weekly page lead", [{"conditionType": "contact_detail", "conditionSubType": "tags", "conditionOperator": "index-of-true",
                               "conditionValue": [TAG], **{k: v for k, v in cond_extra().items()}}],
         [("facebook_conversion_api", "Meta Schedule event", meta("Schedule", tok, "{{contact.attributionSource.fbclid}}"))]),
    ], "Other bookings", [], parent_key=last["id"], order=last.get("order", len(out) - 1) + 1)
    last["next"] = head
    return [*out, *nodes]


def cond_extra() -> dict:
    from ps_ads_forms import cond
    c = cond("tags", "index-of-true", [TAG])
    return {k: v for k, v in c.items() if k not in ("conditionType", "conditionSubType", "conditionOperator", "conditionValue")}


def put(a: Agency, wid: str, tpl: list[dict], name: str | None = None) -> dict:
    live = a.workflow(LOC, wid)
    BDIR.mkdir(parents=True, exist_ok=True)
    (BDIR / f"workflow-{wid}-{time.strftime('%Y%m%d-%H%M%S')}.json").write_text(json.dumps(live))
    a.call("PUT", BACKEND, f"/workflow/{LOC}/{wid}", body={"name": name or live["name"], "version": live.get("version", 1),
           "status": live["status"], "parentId": live.get("parentId"), "workflowData": {"templates": tpl}})
    time.sleep(3)
    return a.workflow(LOC, wid)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("mode", choices=["plan", "check", "apply"])
    args = parser.parse_args()
    load_dotenv()
    a = Agency()
    if not a.location(LOC)["name"].lower().startswith("nortex"):
        sys.exit("sub-conta errada")
    tok = token(a)
    if args.mode == "check":
        r = requests.get(f"https://graph.facebook.com/v21.0/{DATASET}", params={"fields": "id,name", "access_token": tok}, timeout=30)
        print(f"   dataset {DATASET}: HTTP {r.status_code} · {r.json().get('name') or r.json().get('error', {}).get('message')}")
        return 0 if r.ok else 1
    for t in (TAG, "meta ads", "meta ads lp weekly 24h"):
        if args.mode == "apply":
            try:
                a.call("POST", BACKEND, f"/workflow/{LOC}/tags/create", body={"tag": t})
            except Exception:  # noqa: BLE001 — already exists
                pass
    w, b = a.workflow(LOC, WEEKLY), a.workflow(LOC, BOOKED)
    nw, nb = weekly(w["workflowData"]["templates"], tok), booked(b["workflowData"]["templates"], tok)
    print(f"   {w['name']} → {FLOW_NAME}: {[s['type'] for s in nw].count('facebook_conversion_api')} evento Meta, "
          f"{[s['type'] for s in nw].count('google_adword')} Google")
    print(outline(nb))
    if args.mode == "plan":
        return 0
    got = put(a, WEEKLY, nw, FLOW_NAME)
    types = [s["type"] for s in got["workflowData"]["templates"]]
    ok = got["name"] == FLOW_NAME and got["status"] == "published" and "facebook_conversion_api" in types and "google_adword" not in types \
        and "google ads - weekly" not in json.dumps(got["workflowData"])
    print(f"   {'✓' if ok else '✗ VERIFICAR'} {got['name']}: {got['status']}")
    got = put(a, BOOKED, nb)
    ok = got["status"] == "published" and [s["type"] for s in got["workflowData"]["templates"]].count("facebook_conversion_api") == 1
    print(f"   {'✓' if ok else '✗ VERIFICAR'} {got['name']}: {got['status']} · {len(got['workflowData']['templates'])} passos")
    f, fd = latest_form_data(a, FORM)
    if f["name"] != FORM_NAME:
        (BDIR / f"form-{FORM}-{time.strftime('%Y%m%d-%H%M%S')}.json").write_text(json.dumps({"form": f, "formData": fd}))
        a.call("POST", BACKEND, f"/forms/{FORM}", body={"name": FORM_NAME, "formData": keep_redirect(fd)})
        time.sleep(5)
        f2, fd2 = latest_form_data(a, FORM)
        print(f"   form: {f2['name']} · redirect {fd2['form']['formAction'].get('redirect_url')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
