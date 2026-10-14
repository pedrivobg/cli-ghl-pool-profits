#!/usr/bin/env python3
"""Pool Duck: localize the Wesley Chapel ad landing pages cloned into Lakewood Ranch.

    set -a; . <poolduck.env>; set +a                        # Pool Duck agency token
    ./.venv/bin/python scripts/pd_lwr_pages.py               # plan: what changes per page
    ./.venv/bin/python scripts/pd_lwr_pages.py --apply

The funnels were cloned with GHL's own "clone to sub-account"
(POST backend /funnels/funnel/clone-funnel-to-locations {funnelId, funnelName, locationIds}),
which keeps design/structure but leaves Wesley Chapel's forms, phones and copy in the pages.
Page bodies live in a JSON file (page.pageDataDownloadUrl) and are saved with
POST backend /funnels/builder/autosave/{pageId} {funnelId, pageData, pageVersion, pageType, ...}
with pageType "live" (otherwise it is only a draft); SEO meta also via
POST backend /funnels/funnel/funnel-page/{pageId} {meta}.
Each page and its data are backed up to backup/pool-duck-lakewood-ranch/ first.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time

import requests

from _common import ROOT, load_dotenv

from cli_anything.gohighlevel.utils.agency import BACKEND, Agency

LWR = "MosKIX4oux96vchwHZ5W"
PAGES = {  # LWR page id → label (Google funnel KVsiYlxVtBTUKYzRVkNt, FB funnel zfqO82ZBuj0LYBcAuel6)
    "YFcLwNp6AYdOUnJeXcWE": "Google landing",
    "MDOxMUPB3e6Mm2njmFRl": "Google thank you",
    "cnsiCLgYk8DdEzZhRhwE": "FB landing",
    "pMOAbr1nACLcVQ5neOUm": "FB thank you",
}
# The clone blanks every form element ({"value": "none"}): forms of another sub-account are not
# copied. Every form element on a page (inline and popup) gets its funnel's LWR form.
GOOGLE_FORM = {"value": "L35gq3SnSDyoda4Kl9D4", "text": "Google AdWords"}
FB_FORM = {"value": "331LWSK5w0JSbZFswx4q", "text": "Facebook Leads"}
PAGE_FORM = {"YFcLwNp6AYdOUnJeXcWE": GOOGLE_FORM, "MDOxMUPB3e6Mm2njmFRl": GOOGLE_FORM,
             "cnsiCLgYk8DdEzZhRhwE": FB_FORM, "pMOAbr1nACLcVQ5neOUm": FB_FORM}
# Wesley Chapel → Lakewood Ranch, applied to the whole page JSON (forms, phones, popups, buttons).
# Phones: LWR has no Google/FB tracking numbers yet, so both pages use the main line for now.
GLOBAL = [
    ("3OeoAxL72ioduhLuXqgh", "L35gq3SnSDyoda4Kl9D4"),   # form "Google AdWords"
    ("CcwYR5GI3dyIuzRdxpzK", "331LWSK5w0JSbZFswx4q"),   # form "Facebook Leads"
    ("+18138157946", "+19415882227"), ("+18136703825", "+19415882227"),
    ("813-815-7946", "941-588-2227"), ("813-670-3825", "941-588-2227"),
    ("(813) 815-7946", "(941) 588-2227"), ("(813) 670-3825", "(941) 588-2227"),
    ("POOL DUCK WESLEY CHAPEL", "POOL DUCK LAKEWOOD RANCH"),
    ("Centrally Located in Zephyrhills, FL", "Centrally Located in Lakewood Ranch, FL"),
    ("COMPANY IN PASCO COUNTY!", "COMPANY IN LAKEWOOD RANCH!"),
    ("Over 15+ years of experience in Pasco County pool service!", "Over 15+ years of pool service experience!"),
    ("in all of Pasco County.", "in all of Lakewood Ranch."),
]
AREAS = {  # "Areas We Serve" bullets, top to bottom
    "bulletList-7JeJmJW8ZM": ("Zephyrhills", "Lakewood Ranch"),
    "bulletList-RoHTy9E2Br": ("Wesley Chapel", "Bradenton"),
    "bulletList-WDwwcnJlDb": ("Crystal Springs", "Sarasota"),
    "bulletList-U8i3qLt4KR": ("Zephyhills North/South/West", "Manatee &amp; Sarasota Counties"),
    "bulletList-iPU9brjhBk": ("33540, 33541, 33542, 33543, 33544, 33545", "34202, 34211, 34212, 34240"),
}
MAP = {"name": "Lakewood Ranch, FL, USA", "placeId": "ChIJd2NJBNZuh4cRKlAZHY8HW3Y",  # "Pool Duck of Lakewood Ranch"
       "lat": 27.4136, "lng": -82.4199,
       "url": "https://assets.cdn.filesafe.space/MosKIX4oux96vchwHZ5W/media/6acfa8253cd85e1fe341017c.jpg"}
# Reviews are Wesley Chapel's (Trustindex widget c5c5…, Dennell M. testimonial): hidden until LWR has its own.
HIDE = {"section-IRCKCP3FSf", "sub-heading-j90srWK2zq", "custom-code-F3z1CXRs2k", "custom-code-iM-oi9v5prY"}
META = {"title": "Pool Cleaning Service & Repair Lakewood Ranch, FL",
        "description": "Pool Duck is Lakewood Ranch's premier pool service with over 30 years of experience. "
                       "Secure your promo rate today!"}
LEFTOVER = re.compile(r"wesley|zephyr|zephyh|pasco|paso county|crystal springs|813[-) .]|\+1813|uJr8H2qaQM5ffZxeYFqn"
                      r"|3OeoAxL72ioduhLuXqgh|CcwYR5GI3dyIuzRdxpzK|trustindex", re.I)


def nodes(data: dict):
    """Every section (its metaData) and every row/column/element, popups included."""
    def walk(node):
        if isinstance(node, dict):
            if "extra" in node and node.get("id"):
                yield node["id"], node
            for key in ("elements", "children"):
                for child in node.get(key) or []:
                    yield from walk(child)
        elif isinstance(node, list):
            for child in node:
                yield from walk(child)
    for s in data.get("sections") or []:
        yield s["id"], s.get("metaData") or {}
        yield from walk(s.get("elements") or [])
    yield from walk(data.get("popups") or [])


def localize(data: dict, form: dict | None = None) -> tuple[dict, list[str]]:
    raw = json.dumps(data, ensure_ascii=False)
    notes = []
    for old, new in GLOBAL:
        n = raw.count(json.dumps(old, ensure_ascii=False)[1:-1])
        if n:
            raw = raw.replace(json.dumps(old, ensure_ascii=False)[1:-1], json.dumps(new, ensure_ascii=False)[1:-1])
            notes.append(f"{n}× {old!r} → {new!r}")
    data = json.loads(raw)
    for nid, node in nodes(data):
        extra = node.get("extra") or {}
        if nid in AREAS:
            old, new = AREAS[nid]
            text = extra["text"]["value"]
            if f"<strong>{old}</strong>" in text:
                extra["text"]["value"] = text.replace(f"<strong>{old}</strong>", f"<strong>{new}</strong>")
                notes.append(f"área {old!r} → {new!r}")
        if form and isinstance(extra.get("formId"), dict) and extra["formId"].get("value") != form["value"]:
            notes.append(f"form {nid}: {extra['formId'].get('text')!r} ({extra['formId'].get('value')}) → {form['text']!r} da LWR")
            extra["formId"] = dict(form)
        if "mapLocation" in extra and extra["mapLocation"].get("value", {}).get("placeId") != MAP["placeId"]:
            extra["mapLocation"]["value"] = dict(MAP)
            notes.append("mapa → Lakewood Ranch (Pool Duck of Lakewood Ranch)")
        if nid in HIDE:
            code = (extra.get("customCode") or {}).get("value") or {}
            if "trustindex" in code.get("rawCustomCode", ""):
                code["rawCustomCode"] = " "  # a hidden element still loads its script
                notes.append(f"widget Trustindex de WC removido de {nid}")
            vis = extra.setdefault("visibility", {"value": {}})["value"]
            if not all(vis.get(k) for k in ("hideDesktop", "hideMobile")):
                vis.update({"hideDesktop": True, "hideMobile": True, **({"hideTablet": True} if "hideTablet" in vis else {})})
                notes.append(f"oculto {nid}")
    return data, notes


def leftovers(data: dict) -> list[str]:
    raw = json.dumps(data, ensure_ascii=False)
    out = []
    for m in LEFTOVER.finditer(raw):
        ctx = raw[max(0, m.start() - 60):m.end() + 30]
        if "filesafe.space/uJr8" in ctx or "%2FuJr8" in ctx or "msgsndr/uJr8" in ctx:
            continue  # images hosted in WC's media library: public brand assets, fine to reuse
        out.append(ctx.replace("\n", " "))
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--only", help="one page id")
    args = parser.parse_args()
    load_dotenv()
    a = Agency()
    bdir = ROOT / "backup" / "pool-duck-lakewood-ranch"
    bdir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    bad = 0
    for pid, label in PAGES.items():
        if args.only and pid != args.only:
            continue
        page = a.get(BACKEND, f"/funnels/page/{pid}")
        assert page["locationId"] == LWR, page["locationId"]
        data = requests.get(page["pageDataDownloadUrl"], timeout=60).json()
        new, notes = localize(json.loads(json.dumps(data)), PAGE_FORM[pid])
        meta = {**(page.get("meta") or {}), **META}
        print(f"== {label} ({pid})")
        for n in notes:
            print("   ", n)
        if meta != page.get("meta"):
            print(f"    meta: {page['meta'].get('title')!r} → {META['title']!r}")
        if not args.apply:
            for l in leftovers(new):
                print("    ainda sobra:", l)
            continue
        (bdir / f"page-{pid}-{stamp}.json").write_text(json.dumps({"page": page, "pageData": data}, ensure_ascii=False))
        # Same body the page builder sends on "Save": without pageType "live" GHL keeps it as a
        # draft (Redis autosave) and the page itself does not change. A live save keeps pageVersion.
        history = page.get("versionHistory") or [{}]
        a.call("POST", BACKEND, f"/funnels/builder/autosave/{pid}",
               body={"funnelId": page["funnelId"], "pageData": new, "pageVersion": page.get("pageVersion") or 1,
                     "pageType": "live", "manualSave": True, "meta": meta,
                     "integrations": history[0].get("integrations") or {}})
        a.call("POST", BACKEND, f"/funnels/funnel/funnel-page/{pid}", body={"meta": meta})
        for _ in range(6):  # GHL reads lag behind writes
            time.sleep(3)
            after = a.get(BACKEND, f"/funnels/page/{pid}")
            saved = requests.get(after["pageDataDownloadUrl"], timeout=60).json()
            if not localize(json.loads(json.dumps(saved)), PAGE_FORM[pid])[1] and after["meta"].get("title") == META["title"]:
                break
        left, redo = leftovers(saved), localize(json.loads(json.dumps(saved)), PAGE_FORM[pid])[1]
        ok = not left and not redo and after["meta"].get("title") == META["title"]
        bad += not ok
        print(f"    {'✓' if ok else '✗ VERIFICAR'} salvo (data {after['pageDataUrl'][-12:]}, title {after['meta'].get('title')!r})")
        for l in left + redo:
            print("      sobra:", l)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
