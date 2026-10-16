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

Southern (Val, 16/10): the weekly landing service.southernpoolandoutdoors.com shared "Appointment
Booking Form" with the remodeling landing (redirect to the remodeling thank-you page) and no workflow
listened to it; "AdWords Form - New Lead" was a draft listening to the Optin form.

    ./.venv/bin/python scripts/pp_ads_form.py --only "Southern" --form "GOOGLE ADS - FORM" \
        --create-from "Appointment Booking Form" \
        --redirect https://service.southernpoolandoutdoors.com/ty-page-2934-3692 --country-picker \
        --replace --publish --notify "Brett Relander" --apply

--create-from copies another form's fields/style into a new form named --form; --redirect sends it to
that thank-you page; --country-picker turns on the phone field's country code selector; --replace makes
the trigger listen to --form only (the old form stays with "Website Form Fill To Pipeline", so nothing
enters twice); --publish publishes the workflow. The page itself must then use the new form.
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
    parser.add_argument("--create-from", help="create --form as a copy of this form if it does not exist")
    parser.add_argument("--redirect", help="thank-you page URL for --form")
    parser.add_argument("--country-picker", action="store_true", help="phone field with country code selector")
    parser.add_argument("--replace", action="store_true", help="trigger listens to --form only")
    parser.add_argument("--publish", action="store_true")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    load_dotenv()
    a = Agency()
    d = location_dirs([args.only])[0]
    loc = load(d / "location.json", {})["id"]
    forms = {f["name"]: f.get("_id") or f.get("id") for f in a.forms(loc)}
    users = {u.get("name"): u["id"] for u in a.users(loc)}
    bdir = ROOT / "backup" / d.name
    bdir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    if args.form not in forms:
        if not args.create_from:
            raise SystemExit(f"form {args.form!r} não existe (passe --create-from)")
        print(f"== cria form {args.form!r} como cópia de {args.create_from!r}")
        if not args.apply:
            return 0
        src = a.call("GET", BACKEND, f"/forms/{forms[args.create_from]}")
        src = src.get("form", src)
        res = a.call("POST", BACKEND, "/forms/", body={"name": args.form, "formData": src["formData"], "locationId": loc})
        made = res.get("form") or res.get("data") or res
        forms[args.form] = made.get("_id") or made.get("id")
        time.sleep(3)
    fid = forms[args.form]
    form = a.call("GET", BACKEND, f"/forms/{fid}")
    form = form.get("form", form)
    fd = json.loads(json.dumps(form["formData"]))
    action = fd["form"].get("formAction") or {}
    phone = next((x for x in fd["form"]["fields"] if x.get("tag") == "phone"), {})
    form_changes = []
    if args.redirect and (str(action.get("actionType")) != "1" or action.get("redirectUrl") != args.redirect):
        fd["form"]["formAction"] = {**action, "actionType": 1, "redirectUrl": args.redirect}
        form_changes.append(f"obrigado → {args.redirect}")
    if args.country_picker and phone and not phone.get("enableCountryPicker"):
        phone["enableCountryPicker"] = True
        form_changes.append("telefone com código do país")
    if form_changes:
        print(f"   form {args.form}: {', '.join(form_changes)}")
        if args.apply:
            (bdir / f"form-{fid}-{stamp}.json").write_text(json.dumps(form))
            a.call("POST", BACKEND, f"/forms/{fid}", body={"name": form["name"], "formData": fd})
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
    want = [fid] if args.replace else [*cond["value"], fid] if fid not in cond["value"] else cond["value"]
    add_form = want != cond["value"]
    status = "published" if args.publish else live["status"]
    print(f"   gatilho → {[names.get(v, v) for v in want]}" if add_form else f"   já escuta {args.form}")
    if owner:
        print(f"   SMS interno: dono do contato → {args.notify}" if notify else "   SMS interno vai para o dono do contato (passe --notify)")
    if status != live["status"]:
        print(f"   {live['status']} → {status}")
    if not args.apply or not (add_form or (owner and notify) or status != live["status"]):
        return 0
    (bdir / f"workflow-{wid}-{stamp}.json").write_text(json.dumps({"workflow": live, "triggers": trs}))
    if (owner and notify) or status != live["status"]:
        for s in owner if notify else []:
            sms = s["attributes"]["sms"]
            sms.pop("assignedOwners", None)
            sms.update(userType="user", selectedUser=notify)
            s.pop("incompleteData", None)
        a.call("PUT", BACKEND, f"/workflow/{loc}/{wid}", body={
            "name": live["name"], "version": live.get("version", 1), "status": status,
            "parentId": live.get("parentId"), "allowMultiple": live.get("allowMultiple", False),
            "workflowData": {"templates": tpl}})
    if add_form:
        body = {k: v for k, v in trig.items() if k not in DROP}
        body["conditions"] = [{**c, "value": want} if c is cond else c for c in trig["conditions"]]
        body.update(workflowId=wid, workflow_id=wid, location_id=loc,
                    actions=[{"workflow_id": wid, "type": "add_to_workflow"}])
        a.call("PUT", BACKEND, f"/workflow/{loc}/trigger/{trig['id']}", body=body)
    time.sleep(4)
    after = a.workflow(loc, wid)
    t2 = next(t for t in a.triggers(loc, wid) if t["id"] == trig["id"])
    got = next(c for c in t2["conditions"] if c.get("field") == "form.id")["value"]
    sms_ok = all(s["attributes"]["sms"].get("selectedUser") == notify for s in after["workflowData"]["templates"]
                 if s["id"] in {x["id"] for x in owner}) if notify else True
    f2 = a.call("GET", BACKEND, f"/forms/{fid}")
    f2 = f2.get("form", f2)["formData"]["form"]
    form_ok = (not args.redirect or f2.get("formAction", {}).get("redirectUrl") == args.redirect) and \
        (not args.country_picker or any(x.get("enableCountryPicker") for x in f2["fields"] if x.get("tag") == "phone"))
    ok = sorted(got) == sorted(want) and after["status"] == status and sms_ok and form_ok
    print(f"   {'✓' if ok else '✗ VERIFICAR'} {after['status']} · escuta {[names.get(v, v) for v in got]} · SMS ok={sms_ok}"
          f" · form ok={form_ok} · form id {fid}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
