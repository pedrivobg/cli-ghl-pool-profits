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


def twilio(a: Agency, loc: str) -> dict:
    return a.get(BACKEND, "/phone-system/twilio-accounts", {"entityId": loc, "entityType": "LOCATION"}) or {}


def backup(slug: str, name: str, data) -> None:
    d = ROOT / "backup" / slug
    d.mkdir(parents=True, exist_ok=True)
    (d / name).write_text(json.dumps(data, indent=1, ensure_ascii=False))


def a2p_site(loc: dict, a: Agency) -> str:
    """Base URL of the A2P site = https://go.<domain> (root). The "New A2P Verification" website has the path /pools,
    but on its own domain the pages answer at the root (Southern: /privacy-policy 200, /pools/privacy-policy 404)."""
    for cv in a.custom_values(loc["id"]):
        if (cv.get("name") or "").strip().lower() in ("privacy policy", "privacy_policy") and cv.get("value"):
            m = re.match(r"(https?://[^/]+)/", cv["value"].strip())
            if m:
                return m.group(1).lower()
    return ""


# Approved texts (SOP "Submissão A2P 10DLC", Pedro 10/11): copy exactly, only the legal name and links change.
SOP_USE_CASE = ("{legal} uses SMS messaging to send transactional messages related to customers account, orders, or services "
                "requested. These messages may include appointment reminders, order confirmations, and account notifications, "
                "among others. Also to send marketing and promotional messages, including special offers, discounts, new product "
                "updates, among others. Message frequency may vary. Message & Data rates may apply. The customer can reply HELP "
                "for help or STOP to opt-out.")
SOP_SAMPLE_1 = ("Hello Caleb, this is {legal}. We're excited to share a new promotion available for a limited time. "
                "Reply STOP to unsubscribe. Msg & data rates may apply.")
SOP_SAMPLE_2 = ("Hey Kevin, this is {legal}: This is a reminder of your upcoming appointment on 12th July at 5:00pm. "
                "Reply STOP to opt out.")
SOP_CONSENT = ("End users provide consent via the {legal} company's website {site}, where the opt-in form is available on the "
               "main page. Or upon clicking the 'Contact Us' button, they are redirected to an opt-in form where they submit "
               "their information and explicitly agree to receive SMS communications, including marketing and transactional "
               "messages, by checking the consent box. Both the consent check boxes are optional to select. Please refer to "
               "{site} to view the customer's business, as this is the most up-to-date website for their business.")
SOP_OPTIN_MSG = ("You have successfully opted in to receive notification and promotional SMS from {legal}. Message frequency "
                 "varies. Msg & data rates may apply. Reply STOP to opt out. Reply HELP for help.")


def compliance_review(a: Agency, loc_id: str, site: str) -> dict:
    """GHL's AI compliance review ("Review Application"): checks the opt-in form, privacy policy and terms pages.
    Returns the final event: {isCompliant, passedChecks, totalChecks, checks[], errors[], optInValidationId}."""
    from cli_anything.gohighlevel.utils.agency import CHROME_UA
    h = {"token-id": a.tokens.get_token(), "channel": "APP", "source": "WEB_USER", "Version": "2021-07-28",
         "Accept": "text/event-stream", "User-Agent": CHROME_UA}
    r = a.session.get(f"{BACKEND}/phone-system/regulatory-compliance/opt-in-form/validate", headers=h, stream=True, timeout=240,
                      params={"locationId": loc_id, "optInFormUrl": f"{site}/contact-us", "optInMethod": "website"})
    r.raise_for_status()
    last = {}
    for line in r.iter_lines(decode_unicode=True):
        if line and line.startswith("data:"):
            try:
                last = json.loads(line[5:])
            except ValueError:
                continue
            if last.get("responseType") == "final":
                break
    return last


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


def build_campaign(a: Agency, full: dict, site: str, validation_id: str = "") -> dict:
    """Campaign details exactly as the SOP: Low Volume Standard, manual setup, opt-in by website, approved texts."""
    legal = (full.get("legalBusinessName") or full.get("name") or "").strip()
    fix = lambda t: t.replace("..", ".")  # noqa: E731  legal names ending in "inc." / "LLC."
    out = {
        "ageGated": False, "registrationFlowType": "selfserve", "useCase": "LOW_VOLUME",
        "useCaseDescription": fix(SOP_USE_CASE.format(legal=legal)),
        "sampleMessages": [fix(SOP_SAMPLE_1.format(legal=legal)), fix(SOP_SAMPLE_2.format(legal=legal))],
        "messageIncludesEmbeddedLink": True, "messageIncludesPhoneNumbers": True, "directLending": False,
        "endUserConsent": fix(SOP_CONSENT.format(legal=legal, site=site)),
        "optInKeywords": "START, SUBSCRIBE",
        "optInMessage": fix(SOP_OPTIN_MSG.format(legal=legal)),
        "privacyPolicyUrl": f"{site}/privacy-policy", "termsAndConditionsUrl": f"{site}/terms-of-use",
        "optInMethod": "website", "optInImageUrl": f"{site}/contact-us",
        "checkboxStates": {k: True for k in ("optInMethodMentioned", "websiteLiveNoErrors", "businessWebsiteLinkProvided",
                                             "optInFormCompliant", "tosPrivacyPolicyAdded", "tosCorrect",
                                             "businessInfoOnWebsite", "noAffiliateMention", "dbaNamesDisplayed")},
    }
    if validation_id:
        out["optInValidationId"] = validation_id
    return out


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
            sys.exit("no privacy_policy custom value; pass --site https://go.<domain>")
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
