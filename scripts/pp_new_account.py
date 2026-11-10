#!/usr/bin/env python3
"""New sub-account, end to end, without the private key / n8n form (Pedro 10/11: "only the DNS is left").

  pp_new_account.py -n "<name>"            plan (read-only): what is missing and what would be done
  pp_new_account.py -n "<name>" --apply    do every step that is ready
  pp_new_account.py --scan [--apply]       every sub-account created in the last 30 days
  add --submit to also send the A2P brand + campaign when everything is ready (paid, goes to the carriers)

Steps (each one only when its input exists; safe to re-run, nothing filled by hand is overwritten):
 0. Standard dashboard (pp_dashboard.py: "Pool Profits Dashboard" from the snapshot master, set as default).
 1. Onboarding survey (efErcbOr4GAKXzZ28J4S, sub-account "Pool Profits") matched by e-mail / business name
    → custom values + time zone (pp_onboarding_fill.py --apply --timezone).
 2. Business Profile for A2P from the survey: legal name, EIN, entity type, representative (title CEO,
    industry CONSUMER, region USA_AND_CANADA) — only empty fields.
 3. Phone: LC Phone number + call forwarding to the business phone. Buying the FIRST number of a sub-account
    needs GHL's identity check (Persona ID + selfie, kyc-verification status "completed") — a person does it once
    in Settings → Phone Numbers; after that numbers can be bought here (local area code of the business phone).
 4. A2P site: the "New A2P Verification" website with its domain (Frank connects the domain; the client points the
    DNS: CNAME go → sites.ludicrous.cloud). When /privacy-policy and /terms-of-use load → custom values
    privacy_policy / terms_of_use + campaign details (pp_a2p.py campaign).
 5. --submit: A2P standard registration when profile, campaign, number and live site are all there.
The rest of the onboarding sequence (pp_mirror → pp_forms → pp_nps → pp_fix …) stays in docs/new-account-review.md.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
import sys
import time

import requests

from _common import ROOT, load_dotenv, slugify

load_dotenv()
from cli_anything.gohighlevel.utils.agency import SERVICES, Agency, match_location  # noqa: E402
import pp_a2p  # noqa: E402
import pp_dashboard  # noqa: E402

ONBOARDING_LOC = "wohRifObKPEykgu17LJu"
F_BUSINESS, F_LEGAL, F_TYPE, F_EIN, F_REP = ("UUc0Lc3Bps8PZm8g5Y1I", "Er4JquP5hSCM8Jna1VOj", "1KzpDbDTP0oZ2Jvw72gZ",
                                             "fz90PpR2jFrHOTuF67nN", "ZJgSwbkWQIMnN8Hx3T9G")
BACKEND = pp_a2p.BACKEND
LINES = ["Website & GBP", "Google Ads", "Facebook Ads"]  # SOP: three numbers per client (main first)


def e164(v: str) -> str:
    d = re.sub(r"\D", "", v or "")
    return f"+1{d[-10:]}" if len(d) >= 10 else ""


def entity_type(answer: str, legal: str) -> str:
    t = f"{answer} {legal}".lower()
    if re.search(r"\b(inc|corp|corporation|s ?corp|c ?corp)\b", t):
        return "Corporation"
    if "partnership" in t:
        return "Partnership"
    if re.search(r"\bllc\b|limited liability", t):
        return "Limited Liability Corporation"
    return ""


def rep_from(text: str, fallback_name: str) -> dict:
    lines = [x.strip() for x in (text or "").splitlines() if x.strip()]
    email = next((x for x in lines if "@" in x), "")
    phone = next((e164(x) for x in lines if len(re.sub(r"\D", "", x)) >= 10), "")
    name = next((x for x in lines if "@" not in x and len(re.sub(r"\D", "", x)) < 7), fallback_name or "")
    first, _, last = name.partition(" ")
    return {"firstName": first, "lastName": last.strip(), "email": email, "phoneNumber": phone}


def find_submission(a: Agency, loc: dict) -> dict | None:
    subs = a.get(SERVICES, "/surveys/submissions", {"locationId": ONBOARDING_LOC, "limit": 100}).get("submissions", [])
    email = (loc.get("email") or "").lower()
    name = re.sub(r"\W+", "", (loc.get("name") or "").lower())
    for s in subs:  # newest first
        o = s.get("others") or {}
        if email and email == (o.get("email") or s.get("email") or "").lower():
            return s
        if name and name == re.sub(r"\W+", "", (o.get(F_BUSINESS) or "").lower()):
            return s
    return None


def a2p_site(a: Agency, loc_id: str) -> tuple[str, str]:
    """(base url of the A2P website, domain) — '' when no domain is attached yet."""
    domains = {d["id"]: d["url"] for d in a.get(SERVICES, "/funnels/domain/", {"locationId": loc_id}).get("domains", [])
               if not d.get("deleted")}
    for f in a.get(SERVICES, "/funnels/funnel/list", {"locationId": loc_id}).get("funnels", []):
        if "a2p" in (f.get("name") or "").lower() and f.get("domainId") in domains:
            dom = domains[f["domainId"]]
            return f"https://{dom.lower()}", dom  # pages answer at the root (Southern), not under the website path /pools
    return "", next(iter(domains.values()), "")


def live(url: str) -> bool:
    try:
        return requests.get(url, timeout=20, allow_redirects=True).status_code == 200
    except requests.RequestException:
        return False


def process(a: Agency, loc: dict, apply: bool, submit: bool) -> list[str]:
    lid, out = loc["id"], []
    full = a.location(lid)
    say = out.append
    say(f"== {full['name']} ({lid})")

    # 0. standard dashboard (copy of the snapshot master's "Pool Profits Dashboard" as the default)
    try:
        say(f"   Dashboard: {pp_dashboard.run(a, full | {'id': lid}, apply)}")
    except Exception as e:  # noqa: BLE001
        say(f"   Dashboard: ERROR {str(e)[:200]}")

    # 1. survey → custom values + time zone
    sub = find_submission(a, full)
    o = (sub or {}).get("others") or {}
    cvs0 = {c["name"]: (c.get("value") or "").strip() for c in a.custom_values(lid)}
    fresh = full.get("timezone") == "America/Sao_Paulo" or cvs0.get("Friendly Business Name", "").lower() in ("", "none", "null")
    if sub and not fresh:
        say("   survey: account already set up — custom values left as they are")
    elif not sub:
        say("   survey: NOT FOUND (client didn't answer, or different e-mail/name) — custom values/profile by hand")
    else:
        cmd = [sys.executable, str(ROOT / "scripts" / "pp_onboarding_fill.py"), "--submission", sub["id"], "--loc", lid,
               "--timezone"] + (["--apply"] if apply else [])
        r = subprocess.run(cmd, capture_output=True, text=True)
        changed = [x.strip() for x in r.stdout.splitlines() if "→" in x]
        say(f"   survey {sub['createdAt'][:10]}: {len(changed)} custom value/time zone change(s)"
            + (" applied" if apply and changed else "") + ("" if r.returncode == 0 else f" ERROR {r.stderr[-200:]}"))

    # 2. Business Profile (A2P) from the survey — only empty fields
    if sub:
        bi = dict(full.get("businessInformation") or {})
        ar = dict(full.get("authorizedRepresentative") or {})
        body, legal = {}, (o.get(F_LEGAL) or "").strip()
        if legal and not full.get("legalBusinessName"):
            body["legalBusinessName"] = legal
        want_bi = {"registrationNumber": (o.get(F_EIN) or "").strip(), "registrationId": "EIN",
                   "type": entity_type(o.get(F_TYPE) or "", legal), "industry": "CONSUMER",
                   "regions": ["USA_AND_CANADA"], "businessNotRegistered": False}
        if any(bi.get(k) in (None, "", []) and v not in ("", None) for k, v in want_bi.items()):
            body["businessInformation"] = {**want_bi, **{k: v for k, v in bi.items() if v not in ("", None, [])}}
        rep = rep_from(o.get(F_REP) or "", o.get("full_name") or "")
        want_ar = {**rep, "title": "CEO", "position": "CEO"}
        if any(not ar.get(k) or ar.get(k) == "Other" for k in want_ar if want_ar[k]):
            body["authorizedRepresentative"] = {**want_ar, **{k: v for k, v in ar.items() if v and v != "Other"}}
        if body:
            say(f"   business profile: fill {', '.join(body)}" + (" ✓" if apply else ""))
            if apply:
                pp_a2p.backup(slugify(full["name"]), "location-before-profile.json", full)
                a.call("PUT", SERVICES, f"/locations/{lid}", body=body)
        else:
            say("   business profile: ok")

    # 3. phone: three numbers (SOP) named by line + forwarding to the business phone
    try:
        tw = pp_a2p.twilio(a, lid)
    except Exception:  # noqa: BLE001
        tw = None
    target = e164(full.get("phone") or "") or e164((o or {}).get("phone") or "")
    nums: list[str] = []
    main = ""
    if tw is None:
        say("   phone: LC Phone NOT active (Pedro: Settings → Phone Numbers → activate)")
    else:
        names = dict(tw.get("numberName") or {})
        nums = list(names.keys())
        kyc = a.get(BACKEND, "/phone-system/kyc-verification/status", {"entityId": lid, "entity": "LOCATION"})
        if not nums and kyc.get("status") != "completed":
            say("   phone: no number; first purchase needs GHL identity check (Persona) — Pedro buys the FIRST one once "
                f"in Settings → Phone Numbers (area code {target[2:5] or '?'}); I buy the other two")
        elif len(nums) < len(LINES):
            avail = a.get(BACKEND, f"/phone-system/numbers/location/{lid}/available",
                          {"countryCode": "US", "firstPart": target[2:5], "smsEnabled": "true", "voiceEnabled": "true",
                           "mmsEnabled": "true", "numberTypes": "local"})
            city = (full.get("city") or "").lower()
            pool = sorted(avail.get("numbers", []), key=lambda n: (n.get("locality") or "").lower() != city)
            need = len(LINES) - len(nums)
            picks = pool[:need]
            if not picks:
                say(f"   phone: no {target[2:5]} numbers available")
            for pick in picks:
                if apply:
                    a.call("POST", BACKEND, f"/phone-system/numbers/location/{lid}/purchase", body={
                        "addressSid": "", "bundleSid": "", "countryCode": "US", "numberType": "local",
                        "phoneNumber": pick["phoneNumber"], "stripeAccountId": "", "locality": pick.get("locality", ""),
                        "region": pick.get("region", ""), "paymentIntentId": "", "paymentMethodId": "",
                        "fingerprintId": avail.get("fingerprintId"), "skipLocationKYC": False})
                    nums.append(pick["phoneNumber"])
                say(f"   phone: {'bought' if apply else 'would buy'} {pick['phoneNumber']} ({pick.get('locality')})")
            if apply and picks:
                time.sleep(5)
                tw = pp_a2p.twilio(a, lid)
                names = dict(tw.get("numberName") or {})
        # line names: Website & GBP (main, the A2P verification number) / Google Ads / Facebook Ads
        free = [l for l in LINES if l not in names.values()]
        for n in nums:
            if not (names.get(n) or "").strip() and free:
                line = free.pop(0)
                say(f"   phone: name {n} → {line}" + (" ✓" if apply else ""))
                if apply:
                    a.call("POST", BACKEND, f"/phone-system/twilio-accounts?locationId={lid}", body={"number": n, "friendlyName": line})
                    names[n] = line
        fwd = tw.get("forwardingNumbers") or {}
        try:
            ring = {n["phoneNumber"] for n in a.get(BACKEND, f"/phone-system/numbers/location/{lid}").get("numbers", [])
                    if n.get("linkedRingAllUsers")}
        except Exception:  # noqa: BLE001  (404 when the sub-account has no number yet)
            ring = set()
        todo = [n for n in nums if not fwd.get(n) and not (tw.get("inboundCallService") or {}).get(n) and n not in ring]
        if todo and target:
            say(f"   forwarding {', '.join(todo)} → {target}" + (" ✓" if apply else ""))
            if apply:
                for n in todo:
                    a.call("POST", BACKEND, f"/phone-system/twilio-accounts?locationId={lid}",
                           body={"number": n, "forwardingNumber": target})
        elif nums:
            say(f"   phone: {len(nums)} number(s), forwarding ok")
        main = next((n for n, l in names.items() if l == LINES[0]), nums[0] if nums else "")

    # 4. SOP custom values (Fase 1) + A2P site (Fase 2) + campaign (Fases 4–6)
    cvs = {c["name"].lower(): c for c in a.custom_values(lid)}
    def setcv(name: str, value: str) -> None:
        c = cvs.get(name.lower())
        if apply:
            if c:
                a.call("PUT", SERVICES, f"/locations/{lid}/customValues/{c['id']}", body={"name": c["name"], "value": value})
            else:
                a.call("POST", SERVICES, f"/locations/{lid}/customValues", body={"name": name, "value": value})
    cv = lambda n: ((cvs.get(n.lower()) or {}).get("value") or "").strip()  # noqa: E731
    a2p_num = re.sub(r"\D", "", cv("A2P Verification Number"))[-10:]
    if main and a2p_num not in {n[-10:] for n in nums}:  # empty or provisional (business phone): use the main GHL number
        say(f"   custom value A2P Verification Number → {main} (main number)" + (" ✓" if apply else ""))
        setcv("A2P Verification Number", f"({main[2:5]}) {main[5:8]}-{main[8:]}")
    biz_logo = (full.get("business") or {}).get("logoUrl") or full.get("logoUrl") or ""
    if not cv("Logo URL").startswith("http") and biz_logo.startswith("http") and live(biz_logo):
        say("   custom value Logo URL ← Business Profile logo" + (" ✓" if apply else ""))
        setcv("Logo URL", biz_logo)
        if apply:
            cvs["logo url"] = {**(cvs.get("logo url") or {}), "value": biz_logo}
    cv_missing = [n for n in ("Business Address", "Business Email", "Friendly Business Name", "Legal Business Name", "Logo URL")
                  if not cv(n) or cv(n).lower() in ("none", "null")]
    if cv("Logo URL").startswith("http") and not live(cv("Logo URL")):
        cv_missing.append("Logo URL (doesn't open publicly)")
    if cv_missing:
        say(f"   custom values missing (SOP): {', '.join(cv_missing)}")
    site, dom = a2p_site(a, lid)
    site_live = bool(site) and all(live(f"{site}/{p}") for p in ("privacy-policy", "terms-of-use", "contact-us"))
    review: dict = {}
    if not site:
        say(f"   A2P site: no domain on the A2P website yet ({dom or 'no domain at all'}) — Frank connects go.<domain>, "
            "client points CNAME go → sites.ludicrous.cloud")
    elif not site_live:
        say(f"   A2P site: {site} not loading yet (DNS/SSL pending)")
    else:
        for name, path in (("Privacy Policy", "privacy-policy"), ("Terms of Use", "terms-of-use")):
            if cv(name) != f"{site}/{path}":
                say(f"   custom value {name} → {site}/{path}" + (" ✓" if apply else ""))
                setcv(name, f"{site}/{path}")
        if (full.get("website") or "").rstrip("/").lower() != site:
            say(f"   brand website → {site} (as Southern)" + (" ✓" if apply else ""))
            if apply:
                a.call("PUT", SERVICES, f"/locations/{lid}", body={"website": site, "business": {**(full.get("business") or {}), "website": site}})
        if tw is not None:
            cur = tw.get("campaignDetails") or {}
            want = pp_a2p.build_campaign(a, a.location(lid), site)
            stale = {k for k in ("useCaseDescription", "privacyPolicyUrl", "termsAndConditionsUrl", "optInImageUrl", "endUserConsent")
                     if cur.get(k) != want[k]} or cur.get("sampleMessages") != want["sampleMessages"]
            if stale and not (tw.get("compliance") or {}).get("standardRegistration", {}).get("brandSid"):
                say("   A2P campaign details: SOP texts + links" + (" ✓" if apply else ""))
                if apply:
                    pp_a2p.backup(slugify(full["name"]), "twilio-accounts.json", tw)
                    a.call("PUT", BACKEND, f"/phone-system/twilio-accounts?locationId={lid}", body={"campaignDetails": want})

    # 5. status / AI compliance review / submit
    if tw is not None:
        st = pp_a2p.status_row(a, {"id": lid, "name": full["name"]})
        ready = site_live and st["numbers"] and not st["profile_missing"] and st["campaign_details"] and not cv_missing
        if st["brand"] or st["campaign"]:
            say(f"   A2P: brand {st['brand'] or '—'}, campaign {st['campaign'] or '—'}")
        elif ready and submit and apply:
            review = pp_a2p.compliance_review(a, lid, site)
            if not review.get("isCompliant"):
                bad = [c.get("label") for c in review.get("checks", []) if not c.get("passed")] + review.get("errors", [])
                say(f"   A2P: AI compliance review FAILED ({review.get('passedChecks')}/{review.get('totalChecks')}): {bad} — not submitted")
            else:
                tw = pp_a2p.twilio(a, lid)
                cd = {**(tw.get("campaignDetails") or {}), "optInValidationId": review.get("optInValidationId", "")}
                a.call("PUT", BACKEND, f"/phone-system/twilio-accounts?locationId={lid}", body={"campaignDetails": cd})
                pp_a2p.backup(slugify(full["name"]), "twilio-accounts-before-submit.json", pp_a2p.twilio(a, lid))
                r = a.call("POST", pp_a2p.ISV, f"/compliance/{full['companyId']}/standard-registration/{lid}?brandType=standard")
                say(f"   A2P: AI review {review.get('passedChecks')}/{review.get('totalChecks')} ✓ → SUBMITTED {json.dumps(r)[:200]}")
        else:
            missing = [x for x, ok in (("live site", site_live), ("number", st["numbers"]),
                                       ("profile " + ",".join(st["profile_missing"]), not st["profile_missing"]),
                                       ("custom values " + ",".join(cv_missing), not cv_missing),
                                       ("campaign details", st["campaign_details"])) if not ok]
            say("   A2P: " + ("READY to submit" if ready else "waiting on " + "; ".join(missing)))
    return out


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("-n", "--name", action="append", default=[])
    p.add_argument("--scan", action="store_true", help="sub-accounts created in the last 30 days")
    p.add_argument("--apply", action="store_true")
    p.add_argument("--submit", action="store_true")
    args = p.parse_args()
    a = Agency()
    locs = a.locations()
    if args.scan:
        since = (dt.datetime.now(dt.timezone.utc).replace(tzinfo=None) - dt.timedelta(days=30)).isoformat()
        todo = [l for l in locs if (l.get("dateAdded") or "") >= since]
    else:
        todo = [match_location(locs, n) or sys.exit(f"not found: {n}") for n in args.name]
    for loc in sorted(todo, key=lambda l: l.get("dateAdded") or ""):
        try:
            print("\n".join(process(a, loc, args.apply, args.submit)))
        except Exception as e:  # noqa: BLE001
            print(f"== {loc.get('name')}: ERROR {str(e)[:300]}")


if __name__ == "__main__":
    main()
