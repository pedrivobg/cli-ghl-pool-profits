#!/usr/bin/env python3
"""A2P 10DLC + LC Phone by API (internal endpoints the GHL Trust Center uses; Firebase agency token).

  pp_a2p.py status [--all | -n "<name>" ...]          what's missing per sub-account (read-only)
  pp_a2p.py campaign -n "<name>" [--apply]           campaign details from the Southern model (dry-run by default)
  pp_a2p.py forward -n "<name>" --to +1XXXXXXXXXX [--number +1...] [--apply]   call forwarding per number
  pp_a2p.py submit -n "<name>" --yes                 SUBMITS the standard (low volume) brand + campaign. Paid,
                                                     goes to the carriers: only after Pedro approves.

Found 10/11 from the Trust Center bundle (appcdn …/revex/phone-integration, module LocationTrustCenterV2):
- Business Profile (A2P fields): GET/PUT services /locations/{loc} — legalBusinessName, businessInformation
  {type, industry, registrationId: "EIN", registrationNumber, regions, businessNotRegistered}, authorizedRepresentative
  {firstName, lastName, email, phoneNumber, title, position}. PUT tested on "test inc" (and restored).
- Campaign details + numbers config: GET/PUT backend /phone-system/twilio-accounts?entityId=&entityType=LOCATION
  (PUT ?locationId=) — campaignDetails {useCase, useCaseDescription, sampleMessages, endUserConsent, optIn*,
  privacyPolicyUrl, termsAndConditionsUrl, checkboxStates…}, forwardingNumbers {number: target}, numberName.
  Forwarding is written with POST …/twilio-accounts?locationId= {number, forwardingNumber} (PUT ignores it).
- Submit: POST backend/isv_service /compliance/{companyId}/standard-registration/{loc}?brandType=standard (no body;
  uses the two above). Status: compliance.standardRegistration in twilio-accounts (brandData.status, campaignStatus),
  GET isv_service /compliance/{companyId}/brands/{loc}, …/campaigns/{loc}.
"""
from __future__ import annotations

import argparse
import copy
import json
import re
import sys
from pathlib import Path

from _common import ROOT, load_dotenv

load_dotenv()
from cli_anything.gohighlevel.utils.agency import Agency, SERVICES, match_location, slugify  # noqa: E402

BACKEND = "https://backend.leadconnectorhq.com"
ISV = "https://backend.leadconnectorhq.com/isv_service"
MODEL_LOC = "SylIOZiJ6YQsZOypUI8Z"  # Southern Pool + Outdoors (campaign VERIFIED, brand APPROVED)
MODEL_LEGAL = "Dragon Ventures LLC"
MODEL_SITE = "https://go.southernpoolandoutdoors.com"


def twilio(a: Agency, loc: str) -> dict:
    return a.get(BACKEND, "/phone-system/twilio-accounts", {"entityId": loc, "entityType": "LOCATION"}) or {}


def backup(slug: str, name: str, data) -> None:
    d = ROOT / "backup" / slug
    d.mkdir(parents=True, exist_ok=True)
    (d / name).write_text(json.dumps(data, indent=1, ensure_ascii=False))


def a2p_site(loc: dict, a: Agency) -> str:
    """Base URL of the site that holds the privacy/terms pages (custom values first, then the A2P funnel domain)."""
    for cv in a.custom_values(loc["id"]):
        if (cv.get("name") or "").strip().lower() in ("privacy policy", "privacy_policy") and cv.get("value"):
            m = re.match(r"(https?://[^/]+(?:/[^/]+)?)/privacy-policy", cv["value"].strip())
            if m:
                return m.group(1)
    return ""


def status_row(a: Agency, loc: dict) -> dict:
    full = a.location(loc["id"])
    bi, ar = full.get("businessInformation") or {}, full.get("authorizedRepresentative") or {}
    tw = twilio(a, loc["id"])
    sr = (tw.get("compliance") or {}).get("standardRegistration") or {}
    nums = list((tw.get("numberName") or {}).keys()) or list((tw.get("forwardingNumbers") or {}).keys())
    fwd = tw.get("forwardingNumbers") or {}
    missing = [k for k, ok in [
        ("legal name", full.get("legalBusinessName")), ("EIN", bi.get("registrationNumber")), ("type", bi.get("type")),
        ("industry", bi.get("industry")), ("rep name", ar.get("firstName") and ar.get("lastName")),
        ("rep email", ar.get("email")), ("rep phone", ar.get("phoneNumber")),
        ("rep title", ar.get("title") not in (None, "", "Other")), ("website", full.get("website"))] if not ok]
    return {
        "name": full.get("name"), "id": loc["id"],
        "numbers": len(nums), "unforwarded": [n for n in nums if not fwd.get(n) and not (tw.get("inboundCallService") or {}).get(n)],
        "profile_missing": missing,
        "campaign_details": bool((tw.get("campaignDetails") or {}).get("useCaseDescription")),
        "brand": (sr.get("brandData") or {}).get("status") or ("submitted" if sr.get("brandSid") else ""),
        "campaign": sr.get("campaignStatus") or "",
        "campaign_errors": sr.get("campaignErrors") or [],
    }


def cmd_status(a: Agency, locs: list[dict]) -> None:
    for loc in locs:
        try:
            r = status_row(a, loc)
        except Exception as e:  # noqa: BLE001
            print(f"- {loc.get('name')}: ERROR {str(e)[:120]}")
            continue
        state = (f"brand {r['brand'] or '—'}, campaign {r['campaign'] or '—'}" if r["brand"] or r["campaign"] else "not submitted")
        print(f"- {r['name']}: {state} | numbers {r['numbers']}"
              + (f" (no forwarding number: {', '.join(r['unforwarded'])})" if r["unforwarded"] else "")
              + f" | campaign details {'ok' if r['campaign_details'] else 'MISSING'}"
              + (f" | profile missing: {', '.join(r['profile_missing'])}" if r["profile_missing"] else " | profile ok")
              + (f" | ERRORS {r['campaign_errors']}" if r["campaign_errors"] else ""))


def build_campaign(a: Agency, full: dict, site: str) -> dict:
    model = copy.deepcopy(twilio(a, MODEL_LOC).get("campaignDetails") or {})
    legal = full.get("legalBusinessName") or full.get("name")
    for k in ("chatWidgets", "optInValidationId"):
        model.pop(k, None)
    txt = json.dumps(model, ensure_ascii=False).replace(MODEL_LEGAL, legal).replace(MODEL_SITE, site)
    txt = txt.replace("..", ".").replace(".:", ":")  # legal names ending in "inc." / "LLC."
    model = json.loads(txt)
    model["privacyPolicyUrl"] = f"{site}/privacy-policy"
    model["termsAndConditionsUrl"] = f"{site}/terms-of-use"
    model["optInImageUrl"] = f"{site}/contact-us"
    return model


def pick(a: Agency, names: list[str]) -> list[dict]:
    locs = a.locations()
    out = []
    for n in names:
        m = match_location(locs, n)
        if not m:
            sys.exit(f"sub-account not found: {n}")
        out.append(m)
    return out


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("cmd", choices=["status", "campaign", "forward", "submit"])
    p.add_argument("-n", "--name", action="append", default=[])
    p.add_argument("--all", action="store_true")
    p.add_argument("--apply", action="store_true")
    p.add_argument("--yes", action="store_true")
    p.add_argument("--to", help="forward target, E.164")
    p.add_argument("--number", help="only this GHL number")
    p.add_argument("--site", help="base URL for privacy/terms (default: from custom values)")
    args = p.parse_args()
    a = Agency()

    if args.cmd == "status":
        locs = a.locations() if args.all else pick(a, args.name)
        return cmd_status(a, sorted(locs, key=lambda x: x.get("name") or ""))

    (loc,) = pick(a, args.name[:1] or sys.exit("-n <name> required"))
    full, slug = a.location(loc["id"]), slugify(loc.get("name") or loc["id"])
    tw = twilio(a, loc["id"])

    if args.cmd == "campaign":
        site = args.site or a2p_site(loc, a)
        if not site:
            sys.exit("no privacy_policy custom value; pass --site https://go.<domain>/pools")
        new = build_campaign(a, full, site)
        print(json.dumps(new, indent=1, ensure_ascii=False))
        if args.apply:
            backup(slug, "twilio-accounts.json", tw)
            a.call("PUT", BACKEND, f"/phone-system/twilio-accounts?locationId={loc['id']}", body={"campaignDetails": new})
            got = twilio(a, loc["id"]).get("campaignDetails") or {}
            print("saved" if got.get("useCaseDescription") == new["useCaseDescription"] else "NOT saved (re-read differs)")
    elif args.cmd == "forward":
        if not args.to or not re.fullmatch(r"\+1\d{10}", args.to):
            sys.exit("--to +1XXXXXXXXXX required")
        fwd = dict(tw.get("forwardingNumbers") or {})
        targets = [args.number] if args.number else list((tw.get("numberName") or fwd).keys())
        for n in targets:
            print(f"{n}: {fwd.get(n) or '(none)'} -> {args.to}")
            fwd[n] = args.to
        if args.apply:
            backup(slug, "twilio-accounts.json", tw)
            for n in targets:  # what the number settings screen sends (one POST per number)
                a.call("POST", BACKEND, f"/phone-system/twilio-accounts?locationId={loc['id']}",
                       body={"number": n, "forwardingNumber": args.to})
            got = twilio(a, loc["id"]).get("forwardingNumbers") or {}
            print("saved" if all(got.get(n) == args.to for n in targets) else f"NOT saved: {got}")
    elif args.cmd == "submit":
        r = status_row(a, loc)
        if r["profile_missing"] or not r["campaign_details"]:
            sys.exit(f"not ready: profile missing {r['profile_missing']}, campaign details {r['campaign_details']}")
        if r["brand"] or r["campaign"]:
            sys.exit(f"already submitted: brand {r['brand']}, campaign {r['campaign']}")
        if not args.yes:
            sys.exit("paid submission to the carriers: run again with --yes (only after Pedro approves)")
        backup(slug, "twilio-accounts-before-submit.json", tw)
        out = a.call("POST", ISV, f"/compliance/{full['companyId']}/standard-registration/{loc['id']}?brandType=standard")
        print(json.dumps(out, indent=1)[:2000])


if __name__ == "__main__":
    main()
