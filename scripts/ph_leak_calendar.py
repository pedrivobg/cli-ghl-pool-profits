#!/usr/bin/env python3
"""Poolheads: client notifications of the "Pool & Spa Leak Detection" calendar (Frank/Felipe, 13/11).

    ./.venv/bin/python scripts/ph_leak_calendar.py plan
    ./.venv/bin/python scripts/ph_leak_calendar.py test --email pedro@poolprofits.com   # ZZ TEST calendar copy, deleted after
    ./.venv/bin/python scripts/ph_leak_calendar.py apply

The old account (other agency) only had: confirmation e-mail to the client (template "Leak Detection Email Scheduled OG",
already migrated; Felipe edited the new copy 05/11) + in-app alerts, and the confirmation SMS came from the workflow
"Scheduled Appointment Text Message". Felipe set booked/confirmation e-mail + SMS in the new account on 05/11, but both SMS
greet with {{user.first_name}} (= Felipe's name, not the client's). Frank asked (13/11) for confirmation, cancellation,
reschedule (e-mail + SMS) and a reminder SMS 1 day before; no follow-up after the appointment.

What this does on the calendar: the 2 client SMS → {{contact.first_name}} and date + time; adds cancellation e-mail + SMS,
reschedule e-mail (same template as the confirmation, new subject) + SMS, reminder SMS 1 day before. Everything else
(Felipe's e-mails, in-app alerts, disabled team copies) stays. Backup of the notifications in backup/poolheads/ first.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import time

from _common import ROOT, load_dotenv

from cli_anything.gohighlevel.utils.agency import SERVICES, Agency

LOC, CAL = "PeUynYCMm8e6PJMy785O", "txO3WUqGPfheh6dvB3mi"
TEMPLATE = "6ae90bce606e5ecb91cdd669"  # Leak Detection Email Scheduled OG (Felipe's copy)
SIGN = "Poolheads Team\nReply STOP to unsubscribe."
WHEN = "{{appointment.only_start_date}} at {{appointment.only_start_time}}"
SMS = {
    "booked": "Hi {{contact.first_name}},\n\nYour Pool & Spa Leak Detection appointment for " + WHEN + " has been scheduled! "
              "Please check your email for additional information about your upcoming service.\n\nThank you for choosing us, " + SIGN,
    "confirmation": "Hi {{contact.first_name}},\n\nYour Pool & Spa Leak Detection appointment for " + WHEN + " has been scheduled! "
                    "Please check your email for additional information about your upcoming service.\n\nThank you for choosing us, " + SIGN,
    "reschedule": "Hi {{contact.first_name}},\n\nYour Pool & Spa Leak Detection appointment has been rescheduled to " + WHEN +
                   ". Please check your email for the details.\n\nQuestions? Call or text us at (936) 314-9255.\n" + SIGN,
    "cancellation": "Hi {{contact.first_name}},\n\nYour Pool & Spa Leak Detection appointment for " + WHEN + " has been canceled. "
                    "If you'd like to book a new time, just reply here or call us at (936) 314-9255.\n" + SIGN,
    "reminder": "Hi {{contact.first_name}}, this is a reminder of your Pool & Spa Leak Detection appointment tomorrow, " + WHEN +
                ". Please make sure the pool is clean, filled to its proper level and the equipment is working. "
                "Need to reschedule? Call or text us at (936) 314-9255.\n" + SIGN,
}
P = '<p style="margin:0px; line-height: 1.5;"><span style="font-size: 14px; font-family: verdana; color: rgb(0, 0, 1)">{}</span></p><br/>'
FOOT = ('<p style="margin:0px; line-height: 1.5;"><strong><span style="font-family: verdana">Poolheads Team</span></strong>'
        '<span style="font-size: 13px; font-family: verdana"><br>Phone: (936) 314-9255 &nbsp;Email: info@poolheadscare.com</span></p>')
CANCEL_HTML = "".join(P.format(x) for x in [
    "Dear {{contact.name}},",
    "<strong>Your Pool &amp; Spa Leak Detection appointment for {{appointment.start_time}} ({{appointment.timezone}}) has been canceled.</strong>",
    "If you'd like to book a new time, just reply to this email or call or text us at (936) 314-9255.",
    "Sincerely,"]) + FOOT
EMAIL = {
    "reschedule": {"subject": "Your Pool & Spa Leak Detection Appointment has been Rescheduled", "templateId": TEMPLATE, "body": ""},
    "cancellation": {"subject": "Your Pool & Spa Leak Detection Appointment has been Canceled", "templateId": "", "body": CANCEL_HTML},
}
REMINDER = [{"timeOffset": 1, "unit": "days"}]


def notifs(a: Agency, cal: str) -> list[dict]:
    return [n for n in a.call("GET", SERVICES, f"/calendars/{cal}/notifications") if not n.get("deleted")]


def find(ns, channel, ntype, receiver="contact"):
    return [n for n in ns if n["channel"] == channel and n["notificationType"] == ntype and n.get("receiverType") == receiver]


def plan(ns: list[dict], from_addr: dict) -> tuple[list[tuple[str, dict]], list[dict]]:
    """(updates [(id, body)], creates [body])"""
    upd, new = [], []
    for t in ("booked", "confirmation"):
        for n in find(ns, "sms", t):
            if n.get("body") != SMS[t]:
                upd.append((n["_id"], {"body": SMS[t]}))
    for t in ("reschedule", "cancellation", "reminder"):
        if not find(ns, "sms", t):
            b = {"channel": "sms", "notificationType": t, "receiverType": "contact", "isActive": True, "body": SMS[t],
                 "templateId": "", "subject": "", "selectedUsers": [], "additionalPhoneNumbers": []}
            if t == "reminder":
                b["beforeTime"] = REMINDER
            new.append(b)
    for t in ("reschedule", "cancellation"):
        if not find(ns, "email", t):
            new.append({"channel": "email", "notificationType": t, "receiverType": "contact", "isActive": True,
                        "additionalEmailIds": [], "selectedUsers": [], **from_addr, **EMAIL[t]})
    return upd, new


def apply_plan(a: Agency, cal: str, upd, new) -> None:
    for nid, body in upd:
        a.call("PUT", SERVICES, f"/calendars/{cal}/notifications/{nid}", body=body)
    if new:
        a.call("POST", SERVICES, f"/calendars/{cal}/notifications", body=new)


def show(upd, new) -> None:
    for nid, body in upd:
        print(f"  ~ {nid}: {body['body'][:90]!r}…")
    for b in new:
        print(f"  + {b['channel']} {b['notificationType']} {b.get('beforeTime', '')} {b.get('subject') or b.get('body', '')[:80]!r}")


def check(ns) -> list[str]:
    errs = []
    if any("user.first_name" in (n.get("body") or "") for n in ns if n.get("receiverType") == "contact" and n["isActive"]):
        errs.append("user.first_name")
    for t in ("confirmation", "reschedule", "cancellation", "reminder"):
        s = find(ns, "sms", t)
        if not s or any("user.first_name" in (n.get("body") or "") for n in s) or not any(n["isActive"] for n in s):
            errs.append(f"sms {t}")
    for t in ("confirmation", "reschedule", "cancellation"):
        if not any(n["isActive"] for n in find(ns, "email", t)):
            errs.append(f"email {t}")
    r = find(ns, "sms", "reminder")
    if r and r[0].get("beforeTime") != REMINDER:
        errs.append(f"reminder beforeTime {r[0].get('beforeTime')}")
    return errs


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["plan", "test", "apply"])
    ap.add_argument("--email", default="pedro+zztest@poolprofits.com")
    ap.add_argument("--keep", action="store_true", help="test: do not delete the test calendar/contact")
    args = ap.parse_args()
    load_dotenv()
    a = Agency()
    ns = notifs(a, CAL)
    conf = find(ns, "email", "confirmation")[0]
    from_addr = {"fromAddress": conf.get("fromAddress", ""), "fromName": conf.get("fromName", "")}
    upd, new = plan(ns, from_addr)
    if args.cmd == "plan":
        show(upd, new)
        return 0
    if args.cmd == "apply":
        bdir = ROOT / "backup" / "poolheads"
        bdir.mkdir(parents=True, exist_ok=True)
        (bdir / f"calendar-{CAL}-notifications-{time.strftime('%Y%m%d-%H%M%S')}.json").write_text(json.dumps(ns, indent=1))
        show(upd, new)
        apply_plan(a, CAL, upd, new)
        time.sleep(3)
        errs = check(notifs(a, CAL))
        print("  ✓ conferido" if not errs else f"  ✗ {errs}")
        return 1 if errs else 0
    return test(a, ns, from_addr, args)


def test(a: Agency, ns, from_addr, args) -> int:
    """ZZ TEST copy of the calendar with the same client notifications (no in-app/team ones), booked for a ZZ TEST contact
    with only the given e-mail and a fictional 936-555-01xx phone: reminder (~6 min), reschedule, cancel. Deleted afterwards."""
    src = a.call("GET", SERVICES, f"/calendars/{CAL}")["calendar"]
    from ph_migrate_old import CAL_DROP
    body = {k: v for k, v in src.items() if k not in CAL_DROP}
    body.update(locationId=LOC, name="ZZ TEST Leak Detection", isActive=True, teamMembers=src["teamMembers"])
    for _ in range(40):
        try:
            res = a.call("POST", SERVICES, "/calendars/", body=body)
            break
        except Exception as e:  # noqa: BLE001
            import re
            bad = re.findall(r"property (\w+) should not exist", str(e))
            if not bad:
                raise
            for k in bad:
                body.pop(k, None)
    cal = (res.get("calendar") or res)["id"]
    print(f"  calendário ZZ TEST {cal}")
    contact = None
    try:
        for n in notifs(a, cal):  # whatever the API created by default → off
            a.call("PUT", SERVICES, f"/calendars/{cal}/notifications/{n['_id']}", body={"isActive": False})
        copy = [{k: n[k] for k in ("channel", "notificationType", "receiverType", "isActive", "templateId", "subject", "body",
                                   "beforeTime", "fromAddress", "fromName") if k in n}
                for n in ns if n.get("receiverType") == "contact" and n["isActive"]]
        a.call("POST", SERVICES, f"/calendars/{cal}/notifications", body=copy)
        upd, new = plan(notifs(a, cal), from_addr)
        apply_plan(a, cal, upd, new)
        time.sleep(3)
        errs = check(notifs(a, cal))
        print(f"  notificações: {'✓' if not errs else errs}")
        c = a.call("POST", SERVICES, "/contacts/", body={"locationId": LOC, "firstName": "Pedro", "lastName": "ZZ TEST",
                                                        "email": args.email, "phone": "+19365550199"})
        contact = (c.get("contact") or c)["id"]
        start = dt.datetime.now(dt.timezone.utc).replace(second=0, microsecond=0) + dt.timedelta(days=1, minutes=4)
        ap = a.call("POST", SERVICES, "/calendars/events/appointments", body={
            "calendarId": cal, "locationId": LOC, "contactId": contact, "startTime": start.isoformat(),
            "endTime": (start + dt.timedelta(minutes=30)).isoformat(), "title": "ZZ TEST Leak Detection",
            "appointmentStatus": "confirmed", "ignoreFreeSlotValidation": True, "toNotify": True,
            "assignedUserId": src["teamMembers"][0]["userId"]})
        aid = (ap.get("appointment") or ap)["id"]
        print(f"  agendado {aid} para {start} (confirmação agora; lembrete em ~4 min)")
        time.sleep(330)
        later = start + dt.timedelta(days=1)
        a.call("PUT", SERVICES, f"/calendars/events/appointments/{aid}", body={
            "startTime": later.isoformat(), "endTime": (later + dt.timedelta(minutes=30)).isoformat(),
            "ignoreFreeSlotValidation": True, "toNotify": True,
            "calendarId": cal, "assignedUserId": src["teamMembers"][0]["userId"]})
        print(f"  remarcado para {later}")
        time.sleep(90)
        a.call("PUT", SERVICES, f"/calendars/events/appointments/{aid}", body={"appointmentStatus": "cancelled", "toNotify": True,
            "calendarId": cal, "assignedUserId": src["teamMembers"][0]["userId"]})
        print("  cancelado")
        time.sleep(90)
    finally:
        if contact:
            conv = a.call("GET", SERVICES, "/conversations/search", params={"locationId": LOC, "contactId": contact})
            for cv in conv.get("conversations", []):
                msgs = a.call("GET", SERVICES, f"/conversations/{cv['id']}/messages")
                msgs = (msgs.get("messages") or {}).get("messages", msgs.get("messages")) if isinstance(msgs, dict) else msgs
                for m in sorted(msgs or [], key=lambda m: m.get("dateAdded", "")):
                    print(f"   [{m.get('messageType')}] {m.get('status')} {m.get('dateAdded')} | "
                          f"{(m.get('body') or (m.get('meta') or {}).get('email', {}).get('subject') or '')[:160]!r}")
        if not args.keep:
            if contact:
                a.call("DELETE", SERVICES, f"/contacts/{contact}")
            a.call("DELETE", SERVICES, f"/calendars/{cal}")
            print("  ZZ TEST apagados (calendário, contato e agendamento)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
