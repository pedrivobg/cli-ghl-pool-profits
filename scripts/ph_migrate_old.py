#!/usr/bin/env python3
"""Poolheads: bring Felipe's old HighLevel account (other agency) into the new one (Frank/Felipe, 04/11).

    set -a; . <poolheads-old.env>; set +a     # old account token (outside the repo); the new one comes from .env
    ./.venv/bin/python scripts/ph_migrate_old.py inventory
    ./.venv/bin/python scripts/ph_migrate_old.py emails [--apply]
    ./.venv/bin/python scripts/ph_migrate_old.py snippets [--apply]

Two tokens: the old account's (GHL_FIREBASE_REFRESH_TOKEN in the environment, from poolheads-old.env) reads; the new
account's (OLD_ENV unset → .env) writes. Nothing is ever written to the old account.
- emails: the 5 email templates ("Weekly Service Estimate" + folder "Email Confirmation Templates" with 4) → same names and
  folder in the new account, as HTML templates (the builder's drag-and-drop JSON is not downloadable; the HTML is the
  exact rendered email, editable in the code editor). Their images live in the old account's media storage and would
  disappear with it: each is downloaded and uploaded to the new account's media library, and the links swapped.
- snippets: the 9 SMS templates → same names and text (skips names that already exist).
- fields: the 16 contact custom fields (same name, type and options) that the new account does not have.
- forms: the 5 forms (same names, fields, look; custom fields swapped for the new account's).
- workflows: the 11 with steps → drafts named "[Old account] …" (the 2 already ported in October and the 7 empty ones are
  skipped). Every old-account id in them is swapped for the new account's: users (Jorge, Jose and "Main Office Phone" are
  not users here → Felipe), pipeline and stages (by meaning: New/Leads → New Lead, Appointment Scheduled → Scheduled,
  Quoted → Quote Sent, Signed Account → Won Weekly, Backouts/Went w/ Another/Not Interested → Lost), calendars, custom
  fields (ids and merge keys), SMS/email templates and forms (by name). Triggers copied too (inactive while draft).
- calendars: the 5 calendars → same settings (duration, interval, hours, title, description, confirmation), **inactive**,
  Felipe as the team member (the old ones also had Jorge, not a user here yet); their email notifications to the
  contact point at the migrated email templates (same subject).
"""
from __future__ import annotations

import argparse
import json
import mimetypes
import os
import re
import subprocess
import sys
import time

import requests

from _common import ROOT

from cli_anything.gohighlevel.utils.agency import SERVICES, Agency
from cli_anything.gohighlevel.utils.ghl_internal_client import TokenManager

OLD, NEW = "PvPul1DiA2pXShC0xfDD", "PeUynYCMm8e6PJMy785O"
EMAIL_FOLDER = "Email Confirmation Templates"
BDIR = ROOT / "backup" / "poolheads" / "old-account"
MEDIA = re.compile(r"https://(?:assets\.cdn\.filesafe\.space|storage\.googleapis\.com/msgsndr)/" + OLD + r"/media/([0-9a-f]{24})(\.[a-z]+)?")


def new_agency() -> Agency:
    """The new account lives in the Pool Profits agency: its token is in .env, not in the environment."""
    env = {k: v for k, v in os.environ.items() if k not in ("GHL_FIREBASE_REFRESH_TOKEN", "GHL_DUMP_DIR")}
    out = subprocess.run([sys.executable, "-c", "import sys; sys.path.insert(0,'scripts'); from _common import load_dotenv; "
                          "load_dotenv(); import os; print(os.environ['GHL_FIREBASE_REFRESH_TOKEN'])"],
                         capture_output=True, text=True, env=env, cwd=ROOT, check=True).stdout.strip()
    saved = os.environ.get("GHL_FIREBASE_REFRESH_TOKEN")
    os.environ["GHL_FIREBASE_REFRESH_TOKEN"] = out
    try:
        tm = TokenManager()
        tm.get_token()  # the ID token stays in this object (valid ~50 min), whatever the environment says later
        return Agency(tm)
    finally:
        os.environ["GHL_FIREBASE_REFRESH_TOKEN"] = saved or ""


def me(a: Agency) -> str:
    from pp_master_cleanup import user_id
    return user_id(a)


def old_emails(old: Agency) -> list[dict]:
    out = []
    for parent, folder in ((None, None), *[(b["id"], b["name"]) for b in
                                          old.call("GET", SERVICES, "/emails/builder", params={"locationId": OLD, "limit": 100})["builders"]
                                          if b.get("templateType") == "folder"]):
        params = {"locationId": OLD, "limit": 100, **({"parentId": parent} if parent else {})}
        for b in old.call("GET", SERVICES, "/emails/builder", params=params)["builders"]:
            if b.get("templateType") == "folder" or (parent is None and b.get("parentId")):
                continue
            m = old.call("GET", SERVICES, f"/emails/builder/{OLD}/{b['id']}")
            out.append({"id": b["id"], "name": b["name"].strip(), "folder": folder, "html": old.session.get(m["downloadUrl"], timeout=30).text})
    return out


def rehost(new: Agency, ids: set[tuple[str, str]], cache: dict) -> dict:
    """old media id → public URL in the new account's media library."""
    for mid, ext in ids:
        if mid in cache:
            continue
        data = None
        for url in (f"https://assets.cdn.filesafe.space/{OLD}/media/{mid}{ext}", f"https://storage.googleapis.com/msgsndr/{OLD}/media/{mid}{ext}",
                    f"https://storage.googleapis.com/msgsndr/{OLD}/media/{mid}"):
            r = requests.get(url, timeout=30)
            if r.ok and r.content:
                data, ctype = r.content, r.headers.get("content-type", "").split(";")[0] or mimetypes.guess_type(url)[0] or "image/png"
                break
        if data is None:
            print(f"   ✗ imagem {mid}: não baixou")
            continue
        ext2 = ext or mimetypes.guess_extension(ctype) or ".png"
        up = new.call("POST", SERVICES, "/medias/files/", body={"name": f"poolheads-old-{mid}{ext2}", "contentType": ctype, "parentId": "",
                                                                 "altType": "location", "altId": NEW, "size": len(data)})
        requests.put(up["url"], data=data, headers={"Content-Type": ctype}, timeout=60).raise_for_status()
        v = new.call("POST", SERVICES, "/medias/files/verify", body={"altId": NEW, "altType": "location", "id": up["aknId"]})
        cache[mid] = v.get("url") or v.get("file", {}).get("url")
        print(f"   ✓ imagem {mid}{ext} → {cache[mid]}")
    return cache


def emails(old: Agency, new: Agency, apply: bool) -> None:
    tpls = old_emails(old)
    BDIR.mkdir(parents=True, exist_ok=True)
    (BDIR / "email-templates.json").write_text(json.dumps(tpls))
    have = {b["name"].strip(): b for b in new.call("GET", SERVICES, "/emails/builder", params={"locationId": NEW, "limit": 100})["builders"]}
    ids = {(m.group(1), m.group(2) or "") for t in tpls for m in MEDIA.finditer(t["html"])}
    print(f"   {len(tpls)} templates · {len({i for i, _ in ids})} imagens da conta antiga · pasta '{EMAIL_FOLDER}': "
          f"{'existe' if EMAIL_FOLDER in have else 'cria'}")
    for t in tpls:
        print(f"   {'= já existe' if t['name'] in have else '+'} {t['name']}" + (f"  (pasta {t['folder']})" if t["folder"] else ""))
    if not apply:
        return
    cache_f = BDIR / "media-map.json"
    cache = json.loads(cache_f.read_text()) if cache_f.exists() else {}
    cache = rehost(new, ids, cache)
    cache_f.write_text(json.dumps(cache))
    folder_id = (have.get(EMAIL_FOLDER) or {}).get("id")
    if not folder_id:
        folder_id = new.call("POST", SERVICES, "/emails/builder", body={"locationId": NEW, "type": "folder", "title": EMAIL_FOLDER,
                                                                         "name": EMAIL_FOLDER})["id"]
    who = me(new)
    for t in tpls:
        if t["name"] in have:
            continue
        html = MEDIA.sub(lambda m: cache.get(m.group(1), m.group(0)), t["html"])
        body = {"locationId": NEW, "type": "html", "title": t["name"], "name": t["name"], "builderVersion": "2",
                **({"parentId": folder_id} if t["folder"] else {})}
        tid = new.call("POST", SERVICES, "/emails/builder", body=body)["id"]
        new.call("POST", SERVICES, "/emails/builder/data", body={"locationId": NEW, "templateId": tid, "updatedBy": who,
                                                                  "html": html, "editorType": "html"})
        got = new.session.get(new.call("GET", SERVICES, f"/emails/builder/{NEW}/{tid}")["downloadUrl"], timeout=30).text
        left = MEDIA.findall(got)
        print(f"   {'✓' if len(got) > 1000 and not left else '✗ VERIFICAR'} {t['name']}: {len(got)} chars, imagens antigas restantes {len(left)}")


def snippets(old: Agency, new: Agency, apply: bool) -> None:
    src = old.call("GET", SERVICES, f"/locations/{OLD}/templates", params={"limit": 200})["templates"]
    BDIR.mkdir(parents=True, exist_ok=True)
    (BDIR / "sms-templates.json").write_text(json.dumps(src))
    have = {t["name"].strip() for t in new.call("GET", SERVICES, f"/locations/{NEW}/templates", params={"limit": 200})["templates"]}
    for t in src:
        name = t["name"].strip()
        print(f"   {'= já existe' if name in have else '+'} [{t['type']}] {name}: {t['template'].get('body', '')[:70]!r}")
        if apply and name not in have:
            new.call("POST", SERVICES, f"/locations/{NEW}/templates", body={"name": name, "type": t["type"], "template": t["template"]})
    if apply:
        time.sleep(15)
        have = {t["name"].strip() for t in new.call("GET", SERVICES, f"/locations/{NEW}/templates", params={"limit": 200})["templates"]}
        miss = [t["name"] for t in src if t["name"].strip() not in have]
        print(f"   {'✓' if not miss else '✗ faltam ' + str(miss)} {len(src)} templates de SMS")


FIELD_TYPES = {"MULTIPLE_OPTIONS", "SINGLE_OPTIONS", "CHECKBOX", "RADIO"}


def fields(old: Agency, new: Agency, apply: bool) -> None:
    have = {c["name"].strip().lower() for c in new.custom_fields(NEW)}
    for c in old.custom_fields(OLD):
        name = c["name"].strip()
        print(f"   {'= já existe' if name.lower() in have else '+'} {name} ({c.get('dataType')})")
        if apply and name.lower() not in have:
            body = {"name": name, "dataType": c["dataType"], "model": "contact", "placeholder": c.get("placeholder") or "", "position": 0}
            if c["dataType"] in FIELD_TYPES:
                body["options"] = c.get("picklistOptions") or []
            new.call("POST", SERVICES, f"/locations/{NEW}/customFields", body=body)
    if apply:
        left = [c["name"] for c in old.custom_fields(OLD) if c["name"].strip().lower() not in {x["name"].strip().lower() for x in new.custom_fields(NEW)}]
        print(f"   {'✓' if not left else '✗ faltam ' + str(left)} campos")


CAL_DROP = {"id", "locationId", "groupId", "teamMembers", "formId", "providerId", "createdBy", "dateAdded", "dateUpdated",
            "lastUpdatedBy", "version", "isSystemGenerated", "linkedCalendars", "stripe", "pixelId", "deleted", "isActive",
            "widgetSlug", "order", "lookBusyConfig", "reserveService", "codeBlock", "notes"}


def felipe(new: Agency) -> str:
    return next(u["id"] for u in new.call("GET", SERVICES, "/users/", params={"locationId": NEW})["users"] if u.get("name") == "Felipe Cobo")


def email_ids(new: Agency) -> dict:
    out = {}
    for b in new.call("GET", SERVICES, "/emails/builder", params={"locationId": NEW, "limit": 100})["builders"]:
        out[b["name"].strip()] = b["id"]
        if b.get("templateType") == "folder":
            for k in new.call("GET", SERVICES, "/emails/builder", params={"locationId": NEW, "limit": 100, "parentId": b["id"]})["builders"]:
                out[k["name"].strip()] = k["id"]
    return out


def calendars(old: Agency, new: Agency, apply: bool) -> None:
    src = old.call("GET", SERVICES, "/calendars/", params={"locationId": OLD})["calendars"]
    BDIR.mkdir(parents=True, exist_ok=True)
    (BDIR / "calendars.json").write_text(json.dumps(src))
    have = {c["name"].strip() for c in new.call("GET", SERVICES, "/calendars/", params={"locationId": NEW})["calendars"]}
    old_names = {t["id"]: t["name"].strip() for t in json.loads((BDIR / "email-templates.json").read_text())}
    tpl_new = email_ids(new)
    fid = felipe(new)
    for c in src:
        name = c["name"].strip()
        notif = [n for n in old.call("GET", SERVICES, f"/calendars/{c['id']}/notifications")
                 if not n.get("deleted") and n.get("isActive") and n.get("channel") == "email" and n.get("receiverType") == "contact"]
        mapped = [(n, tpl_new.get(old_names.get(n.get("templateId"), ""))) for n in notif]
        print(f"   {'= já existe' if name in have else '+'} {name}: {c.get('slotDuration')} min · e-mail ao cliente "
              f"{[(old_names.get(n.get('templateId')), bool(t)) for n, t in mapped]}")
        if not apply or name in have:
            continue
        body = {k: v for k, v in c.items() if k not in CAL_DROP}
        tm = (c.get("teamMembers") or [{}])[0]
        body.update(locationId=NEW, name=name, isActive=False,
                    teamMembers=[{**tm, "userId": fid, "isPrimary": True, "selected": True}])
        for _ in range(40):  # the create endpoint rejects some read-only fields one at a time
            try:
                res = new.call("POST", SERVICES, "/calendars/", body=body)
                break
            except Exception as e:  # noqa: BLE001
                bad = re.findall(r"property (\w+) should not exist", str(e))
                if not bad:
                    raise
                for k in bad:
                    body.pop(k, None)
        cid = (res.get("calendar") or res)["id"]
        for n, tid in mapped:
            if not tid:
                continue
            new.call("POST", SERVICES, f"/calendars/{cid}/notifications", body=[{
                "channel": "email", "notificationType": n["notificationType"], "receiverType": "contact", "isActive": True,
                "templateId": tid, "subject": n.get("subject") or "", "body": n.get("body") or "",
                "additionalEmailIds": [], "selectedUsers": []}])
        got = new.call("GET", SERVICES, f"/calendars/{cid}")["calendar"]
        ns = [x for x in new.call("GET", SERVICES, f"/calendars/{cid}/notifications") if not x.get("deleted")]
        ok = got["isActive"] is False and got["slotDuration"] == c["slotDuration"] and \
            all(any(x.get("templateId") == t for x in ns) for _, t in mapped if t)
        print(f"      {'✓' if ok else '✗ VERIFICAR'} {cid} · inativo · e-mails {[x.get('templateId') for x in ns if x.get('channel') == 'email']}")


STAGES = {"New [Google Lead]": "🆕 New Lead", "New [Google Repairs}": "🆕 New Lead", "New [Facebook Lead]": "🆕 New Lead",
          "Leads": "🆕 New Lead", "Appointment Scheduled": "📅 Scheduled", "Quoted": "💰 Quote Sent",
          "Signed Account": "🏆 Won - Weekly Pool Service", "Backouts": "❌ Lost", "Went w/ Another Company": "❌ Lost",
          "Not Interested / DNC or Not Service Area": "❌ Lost"}
SKIP_FLOWS = {"After Hours Message", "Business Hours Call Routing"}  # ported in October (pp_poolheads_port.py), live


def id_map(old: Agency, new: Agency) -> dict[str, str]:
    m = {OLD: NEW}
    fid = felipe(new)
    for u in old.call("GET", SERVICES, "/users/", params={"locationId": OLD})["users"]:
        m[u["id"]] = fid
    nps = {p["name"]: p for p in new.pipelines(NEW)}
    newp = nps["Pool Leads"]
    nst = {st["name"]: st["id"] for st in newp["stages"]}
    for p in old.pipelines(OLD):
        m[p["id"]] = newp["id"]
        for st in p["stages"]:
            m[st["id"]] = nst[STAGES[st["name"]]]
    ncal = {c["name"].strip(): c["id"] for c in new.call("GET", SERVICES, "/calendars/", params={"locationId": NEW})["calendars"]}
    for c in old.call("GET", SERVICES, "/calendars/", params={"locationId": OLD})["calendars"]:
        if c["name"].strip() in ncal:
            m[c["id"]] = ncal[c["name"].strip()]
    ncf = {c["name"].strip().lower(): c for c in new.custom_fields(NEW)}
    for c in old.custom_fields(OLD):
        n = ncf.get(c["name"].strip().lower())
        if n:
            m[c["id"]] = n["id"]
            m["{{" + c["fieldKey"] + "}}"] = "{{" + n["fieldKey"] + "}}"
    nsms = {t["name"].strip(): t["id"] for t in new.call("GET", SERVICES, f"/locations/{NEW}/templates", params={"limit": 200})["templates"]}
    for t in old.call("GET", SERVICES, f"/locations/{OLD}/templates", params={"limit": 200})["templates"]:
        if t["name"].strip() in nsms:
            m[t["id"]] = nsms[t["name"].strip()]
    nem = email_ids(new)
    for t in json.loads((BDIR / "email-templates.json").read_text()):
        if t["name"] in nem:
            m[t["id"]] = nem[t["name"]]
    nforms = {f["name"]: f.get("_id") or f.get("id") for f in new.forms(NEW)}
    for f in old.forms(OLD):
        if f["name"] in nforms:
            m[f.get("_id") or f.get("id")] = nforms[f["name"]]
    return m


def swap(obj, m: dict[str, str]):
    text = json.dumps(obj)
    for k in sorted(m, key=len, reverse=True):
        text = text.replace(k, m[k])
    return json.loads(text)


def forms(old: Agency, new: Agency, apply: bool) -> None:
    from bv_service_forms import latest_form_data
    from _common import keep_redirect
    have = {f["name"] for f in new.forms(NEW)}
    m = id_map(old, new)
    for f in old.forms(OLD):
        fid = f.get("_id") or f.get("id")
        print(f"   {'= já existe' if f['name'] in have else '+'} {f['name']}")
        if not apply or f["name"] in have:
            continue
        _, fd = latest_form_data(old, fid)
        fd = swap(fd, m)
        res = new.call("POST", SERVICES.replace("services", "backend"), "/forms/", body={"name": f["name"], "locationId": NEW, "formData": keep_redirect(fd)})
        nid = (res.get("form") or res).get("_id") or (res.get("form") or res).get("id")
        print(f"      ✓ {nid}")


def create_flow(new: Agency, name: str, tpl: list[dict], settings: dict) -> str:
    backend = SERVICES.replace("services", "backend")
    res = new.call("POST", backend, f"/workflow/{NEW}", body={"name": name, "status": "draft"})
    wid = res.get("id") or res.get("_id")
    new.call("PUT", backend, f"/workflow/{NEW}/{wid}", body={"name": name, "version": 1, "status": "draft",
                                                            "workflowData": {"templates": tpl}, **settings})
    return wid


def workflows(old: Agency, new: Agency, apply: bool) -> None:
    backend = SERVICES.replace("services", "backend")
    m = id_map(old, new)
    have = {w["name"] for w in new.workflows(NEW)}
    BDIR.mkdir(parents=True, exist_ok=True)
    for w in sorted(old.workflows(OLD), key=lambda w: w["name"]):
        full = old.workflow(OLD, w["id"])
        tpl = full["workflowData"]["templates"]
        trs = [t for t in old.triggers(OLD, w["id"]) if not t.get("deleted")]
        name = f"[Old account] {w['name']}"
        why = "já portado em outubro" if w["name"] in SKIP_FLOWS else ("vazio" if not tpl else "")
        (BDIR / f"workflow-{w['id']}.json").write_text(json.dumps({"workflow": full, "triggers": trs}))
        print(f"   {'·' if why else ('=' if name in have else '+')} {w['name']} [{w['status']}] {why or f'{len(tpl)} passos, {len(trs)} gatilhos'}")
        if why or not apply or name in have:
            continue
        settings = {k: full[k] for k in ("allowMultiple", "allowMultipleOpportunity", "stopOnResponse", "timezone", "window",
                                          "removeContactFromLastStep", "autoMarkAsRead") if k in full}
        new_tpl = swap(tpl, m)
        try:
            wid = create_flow(new, name, new_tpl, settings)
        except Exception as e:  # noqa: BLE001
            print(f"      ✗ {str(e)[:300]}")
            continue
        for t in trs:
            body = {k: v for k, v in swap(t, m).items() if k not in ("id", "date_added", "date_updated", "_id", "active", "origin_id")}
            body.update(workflowId=wid, workflow_id=wid, location_id=NEW, actions=[{"workflow_id": wid, "type": "add_to_workflow"}])
            try:
                r = new.call("POST", backend, f"/workflow/{NEW}/trigger", body=body)
                new.call("PUT", backend, f"/workflow/{NEW}/trigger/{r['id']}", body={**body, "id": r["id"]})
            except Exception as e:  # noqa: BLE001
                print(f"      ✗ gatilho {t['type']}: {str(e)[:200]}")
        got = new.workflow(NEW, wid)
        left = [k for k in m if k != OLD and k in json.dumps(got["workflowData"]["templates"])]
        n_tr = len([t for t in new.triggers(NEW, wid) if not t.get("deleted")])
        print(f"      {'✓' if got['status'] == 'draft' and len(got['workflowData']['templates']) == len(tpl) and not left else '✗ VERIFICAR'}"
              f" draft · {len(got['workflowData']['templates'])} passos · {n_tr}/{len(trs)} gatilhos · ids antigos restantes {len(left)}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("what", choices=["inventory", "emails", "snippets", "fields", "calendars", "forms", "workflows"])
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    old = Agency()
    if old.location(OLD)["name"].strip() != "Poolheads Pool Service & Repair":
        sys.exit("token da conta antiga não carregado (poolheads-old.env)")
    new = new_agency()
    if new.location(NEW)["name"] != "Poolheads":
        sys.exit("conta nova errada")
    if args.what == "emails":
        emails(old, new, args.apply)
    elif args.what == "snippets":
        snippets(old, new, args.apply)
    elif args.what == "fields":
        fields(old, new, args.apply)
    elif args.what == "calendars":
        calendars(old, new, args.apply)
    elif args.what == "forms":
        forms(old, new, args.apply)
    elif args.what == "workflows":
        workflows(old, new, args.apply)
    else:
        print(f"   workflows {len(old.workflows(OLD))} · forms {len(old.forms(OLD))} · campos {len(old.custom_fields(OLD))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
