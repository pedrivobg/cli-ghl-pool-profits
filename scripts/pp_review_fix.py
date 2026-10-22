#!/usr/bin/env python3
"""Review Request: the "First Request?" check was inverted since the V9 snapshot (found 22/10, Pedro OK'd the fix).
Also (22/10, Ekahi): the rating gate pointing at a field of ANOTHER account, and a Google link of another business.

    ./.venv/bin/python scripts/pp_review_fix.py                 # plan, every sub-account the token opens
    ./.venv/bin/python scripts/pp_review_fix.py --apply
    ./.venv/bin/python scripts/pp_review_fix.py --only "Test Snapshot" --apply

After the wait that follows a Won stage, "First Request?" asked "NPS Score has_value" and its YES branch sends the
rating text. A customer who never rated has an empty score, so they fell into NO and left the workflow: nobody got
the rating text nor the Google review request (tested live on the Test Snapshot: empty → NO, filled → YES). The
intent, by the name, is "no rating yet → ask". Fix: has_value → has_no_value (empty → YES; tested the same way).
In some accounts "Wait for NPS Submission" and "Low NPS Score Detected" read NPS Score by the id of the snapshot's
source account (ZIN3A1XVj7dvVTyCL3qX), a field the account does not have: the wait never sees the rating, so after
7 days everyone (unhappy customers too) gets the review link and the team is never alerted. Fix: that id → the
account's own "NPS Score" field (when every field the workflow reads is NPS Score). And a review link whose placeid
is not the account's own Google place (location.googlePlacesId) → writereview?placeid=<own place>.
Only those values change. Status and every other setting stay as they are; GET + backup before each PUT.
BurchTech (The Pool Keepers drafts): load burchtech.env.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time

from _common import ROOT, load_dotenv, slugify

from cli_anything.gohighlevel.utils.agency import BACKEND, Agency, GHLError

CHECK = "First Request?"
FIELD_ID = re.compile(r"^[A-Za-z0-9]{20}$")
REVIEW = "https://search.google.com/local/writereview?placeid="


def inverted(tpl: list[dict]) -> list[dict]:
    """The "First Request?" conditions still on has_value."""
    out = []
    for st in tpl:
        a = st.get("attributes") or {}
        if st.get("type") != "if_else" or a.get("conditionName") != CHECK:
            continue
        for b in a.get("branches") or []:
            for seg in b.get("segments") or []:
                for c in seg.get("conditions") or []:
                    if c.get("conditionType") == "contact_detail" and c.get("conditionOperator") == "has_value":
                        out.append(c)
    return out


def conditions(o):
    """Every contact-field condition in a step's attributes (if/else branches and wait conditions alike)."""
    if isinstance(o, dict):
        if o.get("conditionType") == "contact_detail":
            yield o
        for v in o.values():
            yield from conditions(v)
    elif isinstance(o, list):
        for v in o:
            yield from conditions(v)


def foreign_fields(tpl: list[dict], fields: dict[str, str]) -> tuple[list[dict], str | None]:
    """Conditions on a field id the account does not have, and the account's NPS Score field to point them to."""
    conds = [c for st in tpl for c in conditions(st.get("attributes") or {})]
    nps = next((i for i, n in fields.items() if n.strip().lower() == "nps score"), None)
    ids = [c for c in conds if FIELD_ID.match(str(c.get("conditionSubType") or ""))]
    own = {fields[c["conditionSubType"]] for c in ids if c["conditionSubType"] in fields}
    bad = [c for c in ids if c["conditionSubType"] not in fields]
    return (bad, nps) if bad and nps and own <= {fields[nps]} else ([], None)


def wrong_links(tpl: list[dict], place: str | None) -> list[dict]:
    """Review-request steps sending a Google link of another place."""
    out = []
    for st in tpl:
        link = (st.get("attributes") or {}).get("overrideReviewLink") or ""
        m = re.search(r"placeid=([\w-]+)", link)
        if st.get("type") == "review_request" and place and m and m.group(1) != place:
            out.append(st["attributes"])
    return out


def read(a: Agency, loc: str, wid: str) -> dict:
    for i in range(3):  # backend reads sometimes 503 for a moment
        try:
            return a.workflow(loc, wid)
        except GHLError as e:
            if e.status < 500 or i == 2:
                raise
            time.sleep(5)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--only", action="append", default=[], help="sub-account name contains this (repeatable)")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    load_dotenv()
    a = Agency()
    stamp = time.strftime("%Y%m%d-%H%M%S")
    locs = [l for l in a.locations() if not args.only or any(o.lower() in l["name"].lower() for o in args.only)]
    fixed = bad = 0
    for loc in sorted(locs, key=lambda l: l["name"].lower()):
        try:
            flows = [w for w in a.workflows(loc["id"]) if "review request" in w["name"].lower()]
        except GHLError as e:
            print(f"   ? {loc['name']}: {e.status}")
            continue
        fields = place = None
        for w in flows:
            live = read(a, loc["id"], w["id"])
            tpl = json.loads(json.dumps(live["workflowData"]["templates"]))
            if fields is None:
                fields = {f["id"]: f["name"] for f in a.custom_fields(loc["id"])}
                place = a.location(loc["id"]).get("googlePlacesId")
            conds = inverted(tpl)
            alien, nps = foreign_fields(tpl, fields)
            links = wrong_links(tpl, place)
            if not (conds or alien or links):
                continue
            what = ([f"{len(conds)} condição(ões) has_value → has_no_value"] if conds else []) + \
                ([f"{len(alien)} condição(ões) no campo {sorted({c['conditionSubType'] for c in alien})} (de outra conta)"
                  f" → NPS Score {nps}"] if alien else []) + \
                ([f"{len(links)} link(s) de review de outro lugar → placeid={place}"] if links else [])
            print(f"   {loc['name']} / {live['name']} [{live['status']}]: " + "; ".join(what))
            if not args.apply:
                continue
            bdir = ROOT / "backup" / slugify(loc["name"])
            bdir.mkdir(parents=True, exist_ok=True)
            (bdir / f"workflow-{w['id']}-{stamp}.json").write_text(json.dumps(live))
            for c in conds:
                c["conditionOperator"] = "has_no_value"
            for c in alien:
                c["conditionSubType"] = nps
            for at in links:
                at["overrideReviewLink"] = REVIEW + place
            a.call("PUT", BACKEND, f"/workflow/{loc['id']}/{w['id']}", body={
                "name": live["name"], "version": live.get("version", 1), "status": live["status"],
                "parentId": live.get("parentId"), "workflowData": {"templates": tpl}})
            time.sleep(2)
            got = read(a, loc["id"], w["id"])
            gt = got["workflowData"]["templates"]
            ok = not inverted(gt) and not foreign_fields(gt, fields)[0] and not wrong_links(gt, place) and \
                got["status"] == live["status"] and \
                len(got["workflowData"]["templates"]) == len(tpl) and got.get("allowMultiple") == live.get("allowMultiple")
            fixed += ok
            bad += not ok
            print(f"      {'✓' if ok else '✗ VERIFICAR'} {got['status']} · re-entry {got.get('allowMultiple')}")
    if args.apply:
        print(f"{fixed} corrigido(s), {bad} a verificar")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
