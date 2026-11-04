#!/usr/bin/env python3
"""Pool Duck Lakewood Ranch: Atif's commercial landing page + thank-you page, live on the LWR domain (Atif/Val, 03/11).

    ./.venv/bin/python scripts/pd_lwr_commercial_page.py export          # Pool Profits token: Atif's pages → dump/poolduck
    set -a; . <poolduck.env>; set +a
    ./.venv/bin/python scripts/pd_lwr_commercial_page.py plan|apply

Atif designed the pages in the "Pool Duck" sub-account of the Pool Profits agency (`VpRdADKTSUn7nIYzxGGn`, funnel
"Google Ads - Commercial Pool Service - Lakewood Ranch" `VHLmTPe8J3SIvYCeOKzV`), with no domain there. The form they
embed ("Google Ads - Commercial" `wjt6wjkZcPzaGlhb8xfs`) and its workflow are in Pool Duck Lakewood Ranch (Pool Duck
agency), and the LWR domain lakewoodranchflorida.poolduck.com is already connected there. Funnels cannot be cloned between
agencies, so the funnel is a clone of the LWR Google ads funnel (same folder) whose 2 pages get Atif's page bodies,
SEO title and paths, the Google Ads tag of the LWR Google funnel, and the Google Ads tracking number (941-541-5942) in
place of the main line (like the other ad pages). The commercial form then redirects to the thank-you page.
URLs: the landing page is served at the funnel path (/commercial-pool-service-lakewood-ranch; its step is "…-page"):
a step PUT changes the step but the live domain keeps routing the old path, and a step path equal to the funnel path
gets a random suffix when the domain is attached. A live page save (autosave pageType "live") refreshes title/body.
Backups of the form and of each page before saving.
`css` (after a new `export`): copies only the page CSS (trackingCode.headerCode) of Atif's pages to the live LWR pages,
keeping the live body (04/11: new commercial hero image, Val/Atif). Backup of each page first.
"""
from __future__ import annotations

import argparse
import json
import sys
import time

import requests

from _common import ROOT, keep_redirect, load_dotenv
from bv_service_forms import latest_form_data
from pd_lwr_pages import ADS_PHONE

from cli_anything.gohighlevel.utils.agency import BACKEND, SERVICES, Agency

SRC_LOC, SRC_FUNNEL = "VpRdADKTSUn7nIYzxGGn", "VHLmTPe8J3SIvYCeOKzV"
LWR, DOMAIN, HOST = "MosKIX4oux96vchwHZ5W", "UXfzEkCNpAe1pmN4SS70", "https://lakewoodranchflorida.poolduck.com"
GOOGLE_FUNNEL = "KVsiYlxVtBTUKYzRVkNt"  # tracking code (Google Ads tag) comes from here
NAME = "Google Ads - Commercial Pool Service - Lakewood Ranch"
FORM = "wjt6wjkZcPzaGlhb8xfs"
SRC = ROOT / "dump" / "poolduck" / "commercial-pages.json"
BDIR = ROOT / "backup" / "pool-duck-lakewood-ranch"


def export() -> int:
    a = Agency()
    f = next(x for x in a.call("GET", SERVICES, "/funnels/funnel/list", params={"locationId": SRC_LOC})["funnels"]
             if x["_id"] == SRC_FUNNEL)
    out = {"funnel": {k: f.get(k) for k in ("name", "url")}, "steps": []}
    for s in sorted(f["steps"], key=lambda s: s["sequence"]):
        p = a.call("GET", BACKEND, f"/funnels/page/{s['pages'][0]}")
        p = p.get("page", p)
        out["steps"].append({"name": s["name"], "url": s["url"], "meta": p.get("meta") or {},
                             "integrations": (p.get("versionHistory") or [{}])[0].get("integrations") or {},
                             "pageData": requests.get(p["pageDataDownloadUrl"], timeout=60).json()})
    SRC.parent.mkdir(parents=True, exist_ok=True)
    SRC.write_text(json.dumps(out, ensure_ascii=False))
    print(f"   {len(out['steps'])} páginas → {SRC}: {[(s['name'], s['url']) for s in out['steps']]}")
    return 0


def phones(data: dict) -> tuple[dict, int]:
    raw, n = json.dumps(data, ensure_ascii=False), 0
    for old, new in ADS_PHONE:
        n += raw.count(old)
        raw = raw.replace(old, new)
    return json.loads(raw), n


def funnel(a: Agency, fid: str | None = None) -> dict | None:
    fs = a.call("GET", SERVICES, "/funnels/funnel/list", params={"locationId": LWR, "limit": 100})["funnels"]
    return next((f for f in fs if (f["_id"] == fid if fid else f["name"] == NAME)), None)


def settings(f: dict, head: str) -> dict:
    return {"locationId": LWR, "funnelId": f["_id"], "funnelName": f["name"], "funnelPath": src_funnel()["url"],
            "domainId": DOMAIN, "faviconUrl": f.get("faviconUrl") or "", "headTrackingCode": head, "bodyTrackingCode": "",
            "allowPaymentModeOption": f.get("orderFormVersion") == 2 and bool(f.get("isLivePaymentMode")),
            "paymentMode": bool(f.get("isLivePaymentMode")), "chatWidgetId": f.get("chatWidgetId") or "",
            "imageOptimization": bool(f.get("imageOptimization")), "isGdprCompliant": bool(f.get("isGdprCompliant")),
            "isOptimisePageLoad": f.get("isOptimisePageLoad", True), "stopAllSplitTestsAndReset": None,
            "requireCreditCard": f.get("requireCreditCard", True), "storeCurrencyFormatting": bool(f.get("storeCurrencyFormatting"))}


def src_funnel() -> dict:
    return json.loads(SRC.read_text())["funnel"]


def css() -> int:
    a = Agency()
    if a.location(LWR)["name"] != "Pool Duck Lakewood Ranch":
        sys.exit("sub-conta errada (token da Pool Duck?)")
    src, f = json.loads(SRC.read_text()), funnel(a)
    BDIR.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    for s, new in zip(sorted(f["steps"], key=lambda s: s["sequence"]), src["steps"]):
        pid = s["pages"][0]
        page = a.get(BACKEND, f"/funnels/page/{pid}")
        page = page.get("page", page)
        live = requests.get(page["pageDataDownloadUrl"], timeout=60).json()
        want = phones(new["pageData"])[0].get("trackingCode", {}).get("headerCode")
        if live.get("trackingCode", {}).get("headerCode") == want:
            print(f"   = {new['name']}: CSS igual")
            continue
        (BDIR / f"page-{pid}-{stamp}.json").write_text(json.dumps({"page": page, "pageData": live}))
        live.setdefault("trackingCode", {})["headerCode"] = want
        a.call("POST", BACKEND, f"/funnels/builder/autosave/{pid}",
               body={"funnelId": f["_id"], "pageData": live, "pageVersion": page.get("pageVersion") or 1, "pageType": "live",
                     "manualSave": True, "meta": page.get("meta") or {},
                     "integrations": (page.get("versionHistory") or [{}])[0].get("integrations") or {}})
        print(f"   ✓ {new['name']}: CSS do Atif copiado (backup {stamp})")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("mode", choices=["export", "plan", "apply", "css"])
    args = parser.parse_args()
    load_dotenv()
    if args.mode == "export":
        return export()
    if args.mode == "css":
        return css()
    a = Agency()
    if a.location(LWR)["name"] != "Pool Duck Lakewood Ranch":
        sys.exit("sub-conta errada (token da Pool Duck?)")
    src = json.loads(SRC.read_text())
    f = funnel(a)
    if not f:
        if args.mode == "plan":
            print(f"   funil {NAME}: cria (clone de {GOOGLE_FUNNEL})")
            return 0
        a.call("POST", BACKEND, "/funnels/funnel/clone-funnel-to-locations",
               body={"funnelId": GOOGLE_FUNNEL, "funnelName": NAME, "locationIds": [LWR]})
        for _ in range(12):
            time.sleep(5)
            if (f := funnel(a)) and f.get("steps"):
                break
    steps = sorted(f["steps"], key=lambda s: s["sequence"])
    head = funnel(a, GOOGLE_FUNNEL).get("trackingCodeHead") or ""
    thanks = HOST + src["steps"][1]["url"]
    print(f"   funil {f['_id']}: {f.get('url')} → {src['funnel']['url']} · domínio {f.get('domainId') or '-'} → {DOMAIN} · "
          f"tag Google Ads {'AW-' + head.split('AW-')[1][:11] if 'AW-' in head else '—'}")
    for s, new in zip(steps, src["steps"]):
        print(f"   passo {s['name']!r} {s['url']} → {new['name']!r} {new['url']} · página {s['pages'][0]}")
    _, fd = latest_form_data(a, FORM)
    act = fd["form"]["formAction"]
    print(f"   form {FORM}: ação {act.get('actionType')} {act.get('redirect_url') or ''} → redireciona para {thanks}")
    if args.mode == "plan":
        return 0
    BDIR.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    (BDIR / f"funnel-{f['_id']}-{stamp}.json").write_text(json.dumps(f))
    for i, (s, new) in enumerate(zip(steps, src["steps"])):
        cur = a.call("GET", BACKEND, f"/funnels/funnel/{f['_id']}/step/{s['id']}")["data"]
        url = new["url"] + ("-page" if i == 0 else "")  # the funnel path (= Atif's landing path) serves step 1
        a.call("PUT", BACKEND, f"/funnels/funnel/step/{f['_id']}",
               body={**cur, "sequence": str(cur["sequence"]), "stepId": s["id"], "name": new["name"], "url": url,
                     "locationId": LWR, "funnelId": f["_id"]})
        pid = s["pages"][0]
        page = a.get(BACKEND, f"/funnels/page/{pid}")
        (BDIR / f"page-{pid}-{stamp}.json").write_text(json.dumps(page))
        data, n = phones(new["pageData"])
        meta = {**(page.get("meta") or {}), **{k: v for k, v in new["meta"].items() if v}}
        a.call("POST", BACKEND, f"/funnels/builder/autosave/{pid}",
               body={"funnelId": f["_id"], "pageData": data, "pageVersion": page.get("pageVersion") or 1, "pageType": "live",
                     "manualSave": True, "meta": meta, "integrations": new["integrations"]})
        a.call("POST", BACKEND, f"/funnels/funnel/funnel-page/{pid}", body={"meta": meta, "name": new["name"]})
        print(f"   ✓ página {new['name']}: corpo do Atif ({n} telefone(s) → 941-541-5942), título {meta.get('title')!r}")
    a.call("POST", BACKEND, "/funnels/funnel/update-settings", body=settings(f, head))
    (BDIR / f"form-{FORM}-{stamp}.json").write_text(json.dumps(fd))
    fd["form"]["formAction"] = {**act, "actionType": "1", "redirectUrl": thanks, "redirect_url": thanks}
    a.call("POST", BACKEND, f"/forms/{FORM}", body={"name": "Google Ads - Commercial", "formData": keep_redirect(fd)})
    time.sleep(8)
    f = funnel(a, f["_id"])
    print(f"   funil: {f.get('url')} · domínio {f.get('domainId')} · passos {[(s['name'], s['url']) for s in f['steps']]} · "
          f"tag {'ok' if head and f.get('trackingCodeHead') == head else '✗'}")
    print(f"   form: {latest_form_data(a, FORM)[1]['form']['formAction'].get('redirect_url')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
