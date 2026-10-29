#!/usr/bin/env python3
"""NorTex Google Ads landing pages: form → booking calendar, like the website (Val/client, 29/10).

    ./.venv/bin/python scripts/nx_ads_booking.py plan
    ./.venv/bin/python scripts/nx_ads_booking.py apply

The website form ("New Website Form") redirects to the "Pool Service Appointment" calendar with name, email and phone
already filled (?full_name=&email=&phone=), so the visitor picks a time and confirms right away. The 2 landing page forms
(WEEKLY, REPAIR; scripts/nx_ads_forms.py) redirected to a thank-you page; now they redirect to the same calendar, the
same way. The form submission still fires "Google Ads LP - Weekly/Repair" (tags, card, alert, conversion) before the
booking. Latest form version read before saving (the GET lags); both redirect fields saved (keep_redirect); backup.
Bookings notified no one (the calendar's notifications were deleted; "Appointment Confirmation/Reminders" is draft):
new "Appointment Booked -> Notify Fareed" (Appointment status confirmed — the calendar auto-confirms — any calendar, so
website bookings too): text + email to Fareed with name, phone, email, address and the appointment time.
    ./.venv/bin/python scripts/nx_ads_booking.py test --to pedro@poolprofits.com   # notice copy by email, then deleted
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import uuid

from _common import ROOT, keep_redirect, load_dotenv
from bv_service_forms import latest_form_data

from nx_ads_forms import FAREED, FAREED_EMAIL
from ps_ads_forms import P

from cli_anything.gohighlevel.utils.agency import BACKEND, SERVICES, Agency

LOC = "k6nDPHktS2PySJoJuwpG"
SITE_FORM = "oXWnLdsRNgpoUXUqIQE6"
FORMS = {"lxtvCbfxc4lDxC50Sifc": "GOOGLE ADS – WEEKLY", "L3f9uKoFBk7QmOtl0hkq": "GOOGLE ADS – REPAIR"}
BDIR = ROOT / "backup" / "nortex-pools"
FLOW = "Appointment Booked -> Notify Fareed"
WHEN = "{{appointment.start_time}}"


def notice(to: str | None = None) -> list[dict]:
    rows = [("When", WHEN), ("Name", "{{contact.name}}"), ("Phone", "{{contact.phone}}"), ("Email", "{{contact.email}}"),
            ("Address", "{{contact.address1}}, {{contact.city}} {{contact.postal_code}}")]
    html = P.format("New appointment booked online:") + "".join(P.format(f"<b>{k}:</b> {v}") for k, v in rows)
    email = {"id": str(uuid.uuid4()), "name": "Email Fareed", "type": "internal_notification",
             "attributes": {"type": "email", "email": {"userType": "custom_email", "to": to or FAREED_EMAIL,
                                                       "subject": f"📅 New appointment: {{{{contact.name}}}} – {WHEN}", "html": html}}}
    if to:
        return [{**email, "order": 0}]
    sms = {"id": str(uuid.uuid4()), "order": 0, "name": "Text Fareed", "type": "internal_notification",
           "attributes": {"type": "sms", "sms": {"body": f"📅 NEW APPOINTMENT BOOKED\n\n{WHEN}\n\nName: {{{{contact.name}}}}\n"
                                                         "Phone: {{contact.phone}}\nEmail: {{contact.email}}\n"
                                                         "Address: {{contact.address1}}, {{contact.city}} {{contact.postal_code}}",
                                                 "userType": "user", "selectedUser": [FAREED], "attachments": []}}}
    email.update(order=1, parentKey=sms["id"])
    sms["next"] = email["id"]
    return [sms, email]


def create_flow(a: Agency, name: str, tpl: list[dict], trigger: bool) -> str:
    res = a.call("POST", BACKEND, f"/workflow/{LOC}", body={"name": name, "status": "draft"})
    wid = res.get("id") or res.get("_id")
    body = {"name": name, "version": 1, "status": "draft", "allowMultiple": True, "workflowData": {"templates": tpl}}
    a.call("PUT", BACKEND, f"/workflow/{LOC}/{wid}", body=body)
    if trigger:
        trig = {"type": "appointment", "name": "Appointment Status", "masterType": "highlevel", "schedule_config": {},
                "workflowId": wid, "workflow_id": wid, "location_id": LOC, "targetActionId": tpl[0]["id"],
                "actions": [{"workflow_id": wid, "type": "add_to_workflow"}],
                "conditions": [{"operator": "==", "field": "appointment.eventType", "value": "normal", "title": "Event type", "type": "select"},
                               {"operator": "is-any-of", "field": "contactMode", "value": ["contact"], "type": "input"},
                               {"operator": "==", "field": "appointment.status", "value": "confirmed", "title": "Appointment status is", "type": "select"}]}
        t = a.call("POST", BACKEND, f"/workflow/{LOC}/trigger", body=trig)
        a.call("PUT", BACKEND, f"/workflow/{LOC}/trigger/{t['id']}", body={**trig, "id": t["id"]})
    live = a.workflow(LOC, wid)
    a.call("PUT", BACKEND, f"/workflow/{LOC}/{wid}", body={**body, "status": "published", "version": live.get("version", 1),
                                                         "workflowData": {"templates": live["workflowData"]["templates"]}})
    return wid


def redirect(fd: dict) -> str:
    act = fd["form"]["formAction"]
    return act.get("redirect_url") or act.get("redirectUrl") or ""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("mode", choices=["plan", "test", "apply"])
    parser.add_argument("--to")
    args = parser.parse_args()
    load_dotenv()
    a = Agency()
    if not a.location(LOC)["name"].lower().startswith("nortex"):
        sys.exit("sub-conta errada")
    if args.mode == "test":
        if not args.to:
            parser.error("--to is required in test mode")
        wid = create_flow(a, "ZZ TEST booking notice", notice(args.to), False)
        cid = a.call("POST", SERVICES, "/contacts/", body={"locationId": LOC, "firstName": "ZZ Test", "lastName": "booking",
                                                           "email": args.to.replace("@", f"+nx-book-{int(time.time())}@")})["contact"]["id"]
        time.sleep(3)
        a.call("POST", SERVICES, f"/contacts/{cid}/workflow/{wid}", body={})
        time.sleep(30)
        a.call("DELETE", SERVICES, f"/contacts/{cid}")
        live = a.workflow(LOC, wid)
        a.call("PUT", BACKEND, f"/workflow/{LOC}/{wid}", body={"name": live["name"], "version": live.get("version", 1),
               "status": "draft", "workflowData": {"templates": live["workflowData"]["templates"]}})
        a.call("DELETE", BACKEND, f"/workflow/{LOC}/{wid}")
        print(f"   limpo. Esperado em {args.to}: 1 e-mail '📅 New appointment' (horário vazio: sem agendamento real).")
        return 0
    flows = {w["name"] for w in a.workflows(LOC)}
    print(f"   {FLOW}: {'existe' if FLOW in flows else 'cria'}")
    if args.mode == "apply" and FLOW not in flows:
        wid = create_flow(a, FLOW, notice(), True)
        time.sleep(3)
        trs = [t for t in a.triggers(LOC, wid) if not t.get("deleted")]
        print(f"      {'✓' if a.workflow(LOC, wid)['status'] == 'published' and trs and trs[0].get('active') else '✗ VERIFICAR'} publicado")
    _, site = latest_form_data(a, SITE_FORM)
    target = redirect(site)
    if "/widget/booking/" not in target:
        sys.exit(f"o form do site não redireciona para o calendário: {target}")
    print(f"   site → {target}")
    for fid, name in FORMS.items():
        f, fd = latest_form_data(a, fid)
        now = redirect(fd)
        print(f"   {name}: {now} → {'já' if now == target else 'calendário'}")
        if args.mode != "apply" or now == target:
            continue
        BDIR.mkdir(parents=True, exist_ok=True)
        (BDIR / f"form-{fid}-{time.strftime('%Y%m%d-%H%M%S')}.json").write_text(json.dumps({"form": f, "formData": fd}))
        fd["form"]["formAction"].update(actionType="1", redirectUrl=target, redirect_url=target)
        a.call("POST", BACKEND, f"/forms/{fid}", body={"name": f["name"], "formData": keep_redirect(fd)})
        time.sleep(5)
        _, got = latest_form_data(a, fid)
        act = got["form"]["formAction"]
        ok = act.get("redirect_url") == target and act.get("redirectUrl") == target and str(act.get("actionType")) == "1"
        print(f"      {'✓' if ok else '✗ VERIFICAR'} {act.get('redirect_url')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
