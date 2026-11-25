#!/usr/bin/env python3
"""Passion Pool Care: Atif's ChatGPT Ads landing page (ClickUp 86bc6vqr9, 24/11) → CRM side.

Live state 25/11: go.passionpoolcare.com/pool-care (funnel "Passion Pool Care - ChatGPT Ads") embeds the form
"PPC - ChatGPT Ads Quote" (kN5NIChZuMfrwgWBiqDf) twice, element action = next funnel step (/pool-care-thank-you).
No workflow listened to that form → a lead got no card, no alert.

This creates "ChatGPT Ads Form - New Lead" as a copy of the live "AdWords Form - New Lead" (same folder, same spam
filter, same alerts: SMS to the office +1 615-624-7624 and Brad, e-mail to passionpoolcare@gmail.com and Brad), with
the source changed: text "NEW LEAD FROM CHATGPT ADS", tags new lead / new form fill / chatgpt ads, card in New Lead with
source "ChatGPT Ads - Form Fill". Trigger = that form only. The form also gets redirect_url (keep_redirect).
Nothing touches existing contacts (only new submissions of this form).

    python3 scripts/pc_chatgpt_lp.py plan
    python3 scripts/pc_chatgpt_lp.py test    # ZZ TEST copy, alerts redirected to Pedro, ZZ TEST contact; all deleted
    python3 scripts/pc_chatgpt_lp.py apply
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
import time
import uuid

from _common import ROOT, keep_redirect, load_dotenv
import ps_ads_forms as ps
from sc_ads_launch import latest_form, save_form

from cli_anything.gohighlevel.utils.agency import BACKEND, SERVICES, Agency

LOC = "d03SMzI37dxTBeuoTJ13"
ps.LOC = LOC
BASE = "AdWords Form - New Lead"
NAME = "ChatGPT Ads Form - New Lead"
FORM = "kN5NIChZuMfrwgWBiqDf"
THANKS = "https://go.passionpoolcare.com/pool-care-thank-you"
TAGS = ["new lead", "new form fill", "chatgpt ads"]
SOURCE = "ChatGPT Ads - Form Fill"
BDIR = ROOT / "backup" / "passion-pool-care-lp"
TEST_EMAIL, TEST_PHONE = "pedro@poolprofits.com", "+5537998339401"


def backup(name: str, data) -> None:
    BDIR.mkdir(parents=True, exist_ok=True)
    (BDIR / f"{name}-{int(time.time())}.json").write_text(json.dumps(data, indent=1))


def build(templates: list[dict], test: bool) -> list[dict]:
    tpl = copy.deepcopy(templates)
    ids = {s["id"]: str(uuid.uuid4()) for s in tpl}
    raw = json.dumps(tpl)
    for old, new in ids.items():
        raw = raw.replace(old, new)
    raw = raw.replace("GOOGLE ADWORDS", "CHATGPT ADS").replace("Google AdWords", "ChatGPT Ads").replace(
        "Google Adwords", "ChatGPT Ads")
    tpl = json.loads(raw)
    for s in tpl:
        at = s.get("attributes") or {}
        if s.get("type") == "add_contact_tag" and "adwords" in (at.get("tags") or []):
            at["tags"] = TAGS
        if s.get("type") == "create_opportunity" and "AdWords" in (at.get("opportunity_source") or ""):
            at["opportunity_source"] = SOURCE
        if test and s.get("type") == "internal_notification":
            if at.get("type") == "sms":
                at["sms"]["to"] = TEST_PHONE
            if at.get("type") == "email":
                at["email"]["to"] = TEST_EMAIL
                at["email"]["subject"] = "ZZ TEST " + (at["email"].get("subject") or "")
    return tpl


def publish(a: Agency, wid: str, name: str, folder: str | None) -> None:
    live = a.workflow(LOC, wid)
    a.call("PUT", BACKEND, f"/workflow/{LOC}/{wid}", body={"name": name, "version": live.get("version", 1),
           "status": "published", "parentId": folder, "allowMultiple": True,
           "workflowData": {"templates": live["workflowData"]["templates"]}})
    time.sleep(3)


def test(a: Agency, base: dict, folder: str | None) -> int:
    stamp = int(time.time())
    wid = ps.create_flow(a, f"ZZ TEST {NAME}", folder, build(base["workflowData"]["templates"], True), publish=False)
    publish(a, wid, f"ZZ TEST {NAME}", folder)
    cid = a.call("POST", SERVICES, "/contacts/", body={
        "locationId": LOC, "firstName": "ZZ Test", "lastName": "chatgpt lp", "postalCode": "37064",
        "email": f"pedro+pc-gpt-{stamp}@poolprofits.com"})["contact"]["id"]
    time.sleep(3)
    a.call("POST", SERVICES, f"/contacts/{cid}/workflow/{wid}", body={})
    time.sleep(45)
    tg = set(a.call("GET", SERVICES, f"/contacts/{cid}")["contact"].get("tags") or [])
    opps = a.call("GET", SERVICES, "/opportunities/search", params={"location_id": LOC, "contact_id": cid}).get(
        "opportunities", [])
    want_stage = next(s for s in base["workflowData"]["templates"] if s["name"] == "Create Or Update Opportunity")[
        "attributes"]["pipeline_stage_id"]
    ok_tags = set(TAGS) <= tg and "adwords" not in tg
    ok_card = any(o.get("pipelineStageId") == want_stage and o.get("source") == SOURCE for o in opps)
    print(f"   {'✓' if ok_tags else '✗'} tags {sorted(tg)}")
    print(f"   {'✓' if ok_card else '✗'} card {[(o.get('pipelineStageId'), o.get('source')) for o in opps]}")
    for o in opps:
        a.call("DELETE", SERVICES, f"/opportunities/{o['id']}")
    a.call("DELETE", SERVICES, f"/contacts/{cid}")
    ps.drop_flow(a, wid)
    print("   limpo (card, contato e fluxo ZZ TEST apagados); avisos de teste foram para o Pedro")
    return 0 if ok_tags and ok_card else 1


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("mode", choices=["plan", "test", "apply"])
    args = p.parse_args()
    load_dotenv()
    a = Agency()
    if "passion" not in a.location(LOC)["name"].lower():
        sys.exit("sub-conta errada")
    flows = {w["name"]: w["id"] for w in a.workflows(LOC)}
    base = a.workflow(LOC, flows[BASE])
    folder = base.get("parentId")
    if args.mode != "plan":
        for t in TAGS:
            try:
                a.call("POST", BACKEND, f"/workflow/{LOC}/tags/create", body={"tag": t})
            except Exception:  # noqa: BLE001 — already exists
                pass
    if args.mode == "test":
        return test(a, base, folder)
    form = latest_form(a, FORM)
    fa = form["formData"]["form"].get("formAction") or {}
    print(f"   form {form['name']}: redirect_url {fa.get('redirect_url')!r} → {THANKS}")
    print(f"   {NAME}: {'existe' if NAME in flows else 'cria'} (cópia de {BASE}, tags {TAGS}, fonte {SOURCE})")
    if args.mode == "plan":
        return 0
    backup(f"form-{FORM}", form)
    backup(f"workflow-{flows[BASE]}", base)
    fd = form["formData"]
    fd["form"]["formAction"] = {**fa, "actionType": "1", "redirectUrl": THANKS, "redirect_url": THANKS}
    save_form(a, FORM, form["name"], keep_redirect(fd))
    if NAME in flows:
        return 0
    tpl = build(base["workflowData"]["templates"], False)
    wid = ps.create_flow(a, NAME, folder, tpl, publish=False)
    body = ps.trigger_body(wid, FORM, tpl[0]["id"])
    t = a.call("POST", BACKEND, f"/workflow/{LOC}/trigger", body=body)
    a.call("PUT", BACKEND, f"/workflow/{LOC}/trigger/{t['id']}", body={**body, "id": t["id"]})
    time.sleep(2)
    publish(a, wid, NAME, folder)
    trs = [x for x in a.triggers(LOC, wid) if not x.get("deleted")]
    print(f"   ✓ {NAME} {wid} {a.workflow(LOC, wid).get('status')} · gatilhos "
          f"{[(x.get('type'), x.get('active'), x.get('conditions')) for x in trs]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
