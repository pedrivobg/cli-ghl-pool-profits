#!/usr/bin/env python3
"""Sparkling Clear: point the 2 Google Ads LP forms at Atif's dedicated thank-you pages (ClickUp 86bd4wxp0, 20/11).

    python3 scripts/sc_lp_thanks.py          # plan
    python3 scripts/sc_lp_thanks.py --apply  # GET latest version + backup, then POST with redirectUrl + redirect_url
"""
from __future__ import annotations

import argparse
import json
import time

from _common import keep_redirect, load_dotenv
from sc_ads_launch import BDIR, latest_form, save_form

from cli_anything.gohighlevel.utils.agency import BACKEND, Agency

PAGES = {
    "TlEIfCFRFGkk9x82iGH1": "https://go.sparklingclearpool.com/weekly-pool-service-thank-you",
    "0DHVgn77lriQmJgUjwrI": "https://go.sparklingclearpool.com/pool-repair-thank-you",
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    load_dotenv()
    a = Agency()
    for fid, url in PAGES.items():
        f = latest_form(a, fid)
        fd = f["formData"]
        act = fd["form"].get("formAction") or {}
        print(f"{f['name']}: {act.get('redirectUrl')} → {url}")
        if not args.apply or (act.get("redirectUrl") == url and act.get("redirect_url") == url):
            continue
        BDIR.mkdir(parents=True, exist_ok=True)
        (BDIR / f"form-{fid}-{int(time.time())}.json").write_text(json.dumps(f, indent=1))
        fd["form"]["formAction"] = {**act, "actionType": "1", "redirectUrl": url, "redirect_url": url}
        save_form(a, fid, f["name"], keep_redirect(fd))
        time.sleep(5)
        got = (latest_form(a, fid)["formData"]["form"].get("formAction") or {})
        print(f"   {'✓' if got.get('redirectUrl') == url and got.get('redirect_url') == url else '✗'} {got}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
