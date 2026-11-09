#!/usr/bin/env python3
"""Publish the interactive CRM guide on the n8n page host (public link, no claude.ai sharing step).

  scripts/pp_crm_guide_publish.py <slug> [<slug>...]   # client page(s): site/crm-guide/data/<slug>.json
  scripts/pp_crm_guide_publish.py --template           # page layout (site/crm-guide/index.html + logo)

n8n workflow "CRM Guide (client pages + answers)" (SlfpWZmKH1d62hB9) serves
  https://n8n.valenteai.cloud/webhook/crm-guide?c=<key>
and saves the client's answers in the n8n data table "CRM Guide Answers" (tju295LzOR6tfp8J); "Send to Pedro" emails
pedro@ (cc Frank). Each client's key (= the link) lives in config/crm_guide_links.json and never changes on republish.
Admin key: env CRM_GUIDE_ADMIN_KEY (also inside the workflow's "Check admin key" node). Never commit it.
"""
import base64, json, os, secrets, sys, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site" / "crm-guide"
LINKS = ROOT / "config" / "crm_guide_links.json"
HOST = "https://n8n.valenteai.cloud/webhook"


def admin_key():
    k = os.environ.get("CRM_GUIDE_ADMIN_KEY", "")
    if not k:
        sys.exit("CRM_GUIDE_ADMIN_KEY not set (value is in the n8n workflow node 'Check admin key')")
    return k


def post(body):
    req = urllib.request.Request(f"{HOST}/crm-guide-admin", data=json.dumps(body).encode(), method="POST",
                                 headers={"Content-Type": "application/json", "x-admin-key": admin_key()})
    with urllib.request.urlopen(req, timeout=60) as r:
        out = json.load(r)
    if not out.get("ok"):
        sys.exit(f"publish refused: {out}")
    return out


def template_html():
    page = (SITE / "index.html").read_text()
    logo = base64.b64encode((SITE / "logo.png").read_bytes()).decode()
    page = page.replace('src="logo.png"', f'src="data:image/png;base64,{logo}"')
    assert "/*CRM_BOOT*/" in page and "<title>CRM Launch Guide</title>" in page
    return ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
            '<meta name="robots" content="noindex"></head><body>' + page + "</body></html>")


def main(args):
    links = json.loads(LINKS.read_text()) if LINKS.exists() else {}
    if args == ["--template"]:
        post({"key": "_template", "slug": "_template", "name": "template", "data": template_html()})
        print("template published")
        return
    if not args:
        sys.exit(__doc__)
    for slug in args:
        data = json.loads((SITE / "data" / f"{slug}.json").read_text())
        ent = links.get(slug) or {"key": f"{slug.split('-')[0]}-{secrets.token_hex(4)}"}
        ent["name"] = data["client"]["name"]
        post({"key": ent["key"], "slug": slug, "name": ent["name"], "data": json.dumps(data, ensure_ascii=False)})
        ent["url"] = f"{HOST}/crm-guide?c={ent['key']}"
        links[slug] = ent
        print(f"{slug}: {ent['url']}")
    LINKS.write_text(json.dumps(links, indent=2, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main(sys.argv[1:])
