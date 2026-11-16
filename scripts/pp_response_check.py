#!/usr/bin/env python3
"""Which clients are not answering their leads / not using the CRM (Ed, call 16/11: "make a short list of accounts where
nobody's responding, who's not logging in and doing anything this past week"). Read-only.

Per active client account (config/inactive_accounts.json and non-client accounts skipped), last --days days:
  waiting   conversations whose last message came FROM the contact (SMS/call/email/chat; not reviews, not spam/dnd)
  human     conversations with a message typed by a person on the team (lastManualMessageDate in the window)
  leads     opportunities created in the window, and how many are still in the first pipeline stage
Flags: 2+ texts whose last message is the contact's (calls left out: with the IVR every call ends "completed") →
"texts unanswered"; 3+ new leads and none moved out of the first stage → "no card moved" (Ed: Reign never moves cards,
so Google Ads gets no won/lost signal).

  python3 scripts/pp_response_check.py --days 7 [--json reports/response-check.json]
"""
from __future__ import annotations

import argparse
import json
import time

from _common import ROOT, Agency, load_dotenv
from cli_anything.gohighlevel.utils.agency import SERVICES

NOT_CLIENT = {"pool profits", "test snapshot", "snapshot pool profits", "pool profits (sales)", "pool profits - sample",
              "damon's pool care - billing only", "master pool service snapshot v1", "nathan taylor's account", "test inc"}
SKIP = {"spam", "dnd", "zz test", "spam contact"}
# calls are left out: with the IVR every call ends "completed", answered or not, so a call can't tell us if someone replied
CALLS = {"TYPE_CALL", "TYPE_IVR_CALL", "TYPE_VOICEMAIL"}
DONE = ("stop", "thank", "thanks", "ok", "okay", "perfect", "great", "sounds good", "will do", "👍")


def account(a: Agency, loc: str, days: int) -> dict:
    since = (time.time() - days * 86400) * 1000
    waiting, human, convs = [], 0, 0
    r = a.get(SERVICES, "/conversations/search", {"locationId": loc, "limit": 100, "sort": "desc", "sortBy": "last_message_date"})
    for c in r.get("conversations", []):
        if (c.get("lastMessageDate") or 0) < since:
            break
        if SKIP & {t.lower() for t in (c.get("tags") or [])} or c.get("lastMessageType") == "TYPE_REVIEW":
            continue
        convs += 1
        if (c.get("lastManualMessageDate") or 0) >= since:
            human += 1
        if c.get("lastMessageDirection") == "inbound" and c.get("contactId") and c.get("lastMessageType") not in CALLS:
            body = (c.get("lastMessageBody") or "").strip().lower()
            if not body or body.startswith(DONE) and len(body) < 40:
                continue
            waiting.append(f"{c.get('fullName') or c.get('phone') or '?'} ({time.strftime('%m/%d', time.gmtime(c['lastMessageDate'] / 1000))})")
    leads, first = 0, 0
    try:
        pipes = a.pipelines(loc)
        firsts = {p["stages"][0]["id"] for p in pipes if p.get("stages")}
        o = a.get(SERVICES, "/opportunities/search", {"location_id": loc, "limit": 100, "order": "added_desc"})
        for op in o.get("opportunities", []):
            added = op.get("createdAt") or ""
            t = time.mktime(time.strptime(added[:19], "%Y-%m-%dT%H:%M:%S")) * 1000 if added else 0
            if t < since:
                continue
            leads += 1
            first += op.get("pipelineStageId") in firsts
    except Exception:  # noqa: BLE001
        pass
    flags = []
    if len(waiting) >= 2:
        flags.append("texts unanswered")
    if leads >= 3 and first == leads:
        flags.append("no card moved")
    flag = " + ".join(flags)
    return {"convs": convs, "human": human, "waiting": waiting, "leads": leads, "leads_first_stage": first, "flag": flag}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--json")
    args = ap.parse_args()
    load_dotenv()
    a = Agency()
    inactive = json.loads((ROOT / "config" / "inactive_accounts.json").read_text())["accounts"]
    res = {}
    for l in sorted(a.locations(), key=lambda x: x.get("name", "")):
        nm = (l.get("name") or "").strip()
        if nm.lower() in NOT_CLIENT or l["id"] in inactive:
            continue
        try:
            r = account(a, l["id"], args.days)
        except Exception as e:  # noqa: BLE001
            print(f"{nm[:32]:32} ERROR {str(e)[:80]}")
            continue
        res[nm] = r
        print(f"{nm[:32]:32} {r['flag']:34} leads {r['leads']:3} (still New {r['leads_first_stage']:3}) · convs {r['convs']:3} · "
              f"texts waiting {len(r['waiting'])}: {', '.join(r['waiting'][:4])}")
    if args.json:
        json.dump(res, open(args.json, "w"), indent=1, ensure_ascii=False)


if __name__ == "__main__":
    main()
