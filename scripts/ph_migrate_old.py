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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("what", choices=["inventory", "emails", "snippets"])
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
    else:
        print(f"   workflows {len(old.workflows(OLD))} · forms {len(old.forms(OLD))} · campos {len(old.custom_fields(OLD))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
