#!/usr/bin/env python3
"""Pool Duck Wesley Chapel — CRM guide answers (Justin 17/11) that are not plain text (pp_wording does the texts:
config/pool_duck_wc_wording.json).

    GHL_AGENCY=poolduck python3 scripts/pd_wc_guide_extras.py --tos <pdf>            # plan
    GHL_AGENCY=poolduck python3 scripts/pd_wc_guide_extras.py --tos <pdf> --apply
    GHL_AGENCY=poolduck python3 scripts/pd_wc_guide_extras.py --loc m2glhRgphyM7uXh4Rc8u --apply   # other account:
        weekday follow-ups (+ STOP on the native text when it is on); M10 only with --tos (East Orlando 23/11)

1. M10 (Won Stage / Welcome Email): portal URL as a hyperlink + Terms of Service PDF attached (media library upload),
   in the step AND its snippet.
2. "Follow-up texts on weekends? NO": No Response / Quote Sent: "Wait 1 day" gets a Mon–Fri 08:00–17:00 window, and a
   1-minute wait with the same window goes right before each SMS after a reply-timeout (ids of existing steps kept, so
   contacts already waiting stay where they are).
3. "M1 ends with Reply STOP to opt out? YES": also on the native missed-call text (the one live today).
Backup of everything in backup/pool-duck-wesley-chapel/ before writing; re-read after.
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import sys
import time
import uuid
from pathlib import Path

import requests

from _common import ROOT, load_dotenv

load_dotenv()
from cli_anything.gohighlevel.utils.agency import BACKEND, SERVICES, Agency  # noqa: E402

LOC = "uJr8H2qaQM5ffZxeYFqn"
BDIR = ROOT / "backup" / "pool-duck-wesley-chapel"
PORTAL = "https://poolduck.poolbrain.com"
LINK = f'<a href="{PORTAL}" target="_blank" rel="noopener noreferrer">{PORTAL}</a>'
OPT = " Reply STOP to opt out."
WINDOW = {"condition": "when", "days": [1, 2, 3, 4, 5], "start": "08:00", "end": "17:00"}
WCOND = {"field": "", "operator": "", "value": ""}


def upload(a: Agency, path: Path) -> dict:
    data = path.read_bytes()
    up = a.call("POST", SERVICES, "/medias/files/", body={"name": path.name, "contentType": "application/pdf",
                                                          "parentId": "", "altType": "location", "altId": LOC,
                                                          "size": len(data)})
    requests.put(up["url"], data=data, headers={"Content-Type": "application/pdf"}, timeout=60).raise_for_status()
    v = a.call("POST", SERVICES, "/medias/files/verify", body={"altId": LOC, "altType": "location", "id": up["aknId"]})
    url = v.get("url") or (v.get("file") or {}).get("url")
    return {"url": url, "name": path.name, "size": len(data)}


def put_wf(a: Agency, wf: dict, tpl: list) -> None:
    a.call("PUT", BACKEND, f"/workflow/{LOC}/{wf['id']}", body={
        "name": wf["name"], "version": wf.get("version", 1), "status": wf["status"], "parentId": wf.get("parentId"),
        "allowMultiple": wf.get("allowMultiple", True), "workflowData": {"templates": tpl}})


def weekday_waits(tpl: list) -> list[str]:
    """Window on time waits; 1-min windowed wait before every SMS that hangs off a timeout transition."""
    notes, by = [], {t["id"]: t for t in tpl}
    for t in tpl:
        if t["type"] == "wait" and t["attributes"].get("type") == "time" and t["attributes"].get("window") != WINDOW:
            t["attributes"]["window"], t["attributes"]["windowCondition"] = dict(WINDOW), dict(WCOND)
            notes.append(f"window on {t['name']!r}")
    for sms in [t for t in tpl if t["type"] == "sms"]:
        tr = by.get(sms.get("parentKey"))
        if not tr or tr["type"] != "transition" or tr["attributes"].get("type") != "wait_timeout":
            continue
        wid = str(uuid.uuid4())
        w = {"id": wid, "type": "wait", "name": "Weekdays 8-5", "order": sms.get("order", 0), "cat": "",
             "parent": tr["id"], "parentKey": tr["id"], "next": sms["id"],
             "attributes": {"type": "time", "startAfter": {"type": "minutes", "value": 1, "when": "after"},
                            "name": "Weekdays 8-5", "cat": "", "window": dict(WINDOW), "windowCondition": dict(WCOND),
                            "timePeriodInputMode": "standard", "unitInputMode": "standard", "isHybridAction": True,
                            "hybridActionType": "wait", "convertToMultipath": False, "transitions": []}}
        for t in tpl:
            if t.get("parent") == tr["id"]:
                t["order"] = t.get("order", 0) + 1
        tr["next"], sms["parentKey"] = wid, wid
        tpl.insert(tpl.index(sms), w)
        notes.append(f"weekday wait before {sms['name']!r}")
    return notes


def main() -> int:
    global LOC, BDIR
    ap = argparse.ArgumentParser()
    ap.add_argument("--tos", type=Path)
    ap.add_argument("--loc", default=LOC)
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    if args.loc != LOC:
        LOC = args.loc
        BDIR = ROOT / "backup" / f"pool-duck-{LOC}"
    a = Agency()
    stamp = time.strftime("%Y%m%d-%H%M%S")
    BDIR.mkdir(parents=True, exist_ok=True)
    ws = {w["name"]: w for w in a.workflows(LOC)}
    snips = {s["_id"]: s for s in a.snippets(LOC)}
    plan = []

    won = a.workflow(LOC, ws["Won Stage"]["id"])
    step = next(t for t in won["workflowData"]["templates"] if t["name"] == "Welcome Email")
    sn = snips[step["attributes"]["template_id"]]
    need_link = bool(args.tos) and LINK not in (step["attributes"]["html"] or "")
    need_att = bool(args.tos) and not any(x.get("name") == args.tos.name for x in step["attributes"].get("attachments") or [])
    if args.tos:
        plan.append(f"M10: link {'add' if need_link else 'ok'}, ToS attachment {'add' if need_att else 'ok'}")

    fu = {}
    for n in ("No Response Follow-up", "Quote Sent Follow-up"):
        wf = a.workflow(LOC, ws[n]["id"])
        tpl = copy.deepcopy(wf["workflowData"]["templates"])
        notes = weekday_waits(tpl)
        fu[n] = (wf, tpl, notes)
        plan.append(f"{n}: {', '.join(notes) or 'ok'}")

    L = a.call("GET", SERVICES, f"/locations/{LOC}")
    L = L.get("location", L)
    mct = L.get("missedCallText") or ""
    native_on = bool(L.get("enableMissedCallText"))
    plan.append(f"native missed-call text: {'off (skip)' if not native_on else 'add opt-out' if 'STOP' not in mct else 'ok'}")
    print("\n".join(plan))
    if not args.apply:
        return 0

    (BDIR / f"guide-extras-{stamp}.json").write_text(json.dumps({
        "won": won, "snippet": sn, "followups": {n: v[0] for n, v in fu.items()},
        "missedCallText": mct, "enableMissedCallText": L.get("enableMissedCallText")}, ensure_ascii=False))

    if need_link or need_att:
        att = upload(a, args.tos) if need_att else None
        html = step["attributes"]["html"].replace(PORTAL, LINK) if need_link else step["attributes"]["html"]
        atts = (step["attributes"].get("attachments") or []) + ([att] if att else [])
        tpl = copy.deepcopy(won["workflowData"]["templates"])
        s2 = next(t for t in tpl if t["id"] == step["id"])
        s2["attributes"].update({"html": html, "attachments": atts})
        t = dict(sn.get("template") or {})
        t.update({"html": html, "attachments": atts})
        a.call("PUT", BACKEND, f"/snippets/{LOC}/{sn['_id']}", body={"name": sn["name"], "type": sn["type"], "template": t})
        put_wf(a, won, tpl)
        print(f"   M10 applied (ToS: {att['url'] if att else 'already there'})")
    for n, (wf, tpl, notes) in fu.items():
        if notes:
            put_wf(a, wf, tpl)
            print(f"   {n}: applied")
    if native_on and "STOP" not in mct:
        a.call("PUT", SERVICES, f"/locations/{LOC}", body={"missedCallText": mct.rstrip() + OPT})
        print("   native missed-call text: applied")

    time.sleep(15)  # reads lag after writes
    ok = True
    w2 = a.workflow(LOC, won["id"])
    st = next(t for t in w2["workflowData"]["templates"] if t["id"] == step["id"])
    sn2 = next(s for s in a.snippets(LOC) if s["_id"] == sn["_id"])
    for label, h, at in ((("step", st["attributes"]["html"], st["attributes"].get("attachments")),
                          ("snippet", sn2["template"].get("html"), sn2["template"].get("attachments"))) if args.tos else ()):
        good = LINK in (h or "") and any(x.get("name") == args.tos.name for x in at or [])
        ok &= good
        print(f"   {'✓' if good else '✗'} M10 {label}: link + ToS")
    print(f"   Won Stage status {w2['status']} (was {won['status']})")
    for n, (wf, _, _) in fu.items():
        chk = a.workflow(LOC, wf["id"])
        tp = chk["workflowData"]["templates"]
        left = weekday_waits(copy.deepcopy(tp))
        old = {t["id"] for t in wf["workflowData"]["templates"]}
        kept = old <= {t["id"] for t in tp}
        good = not left and kept and chk["status"] == wf["status"] and chk.get("allowMultiple") == wf.get("allowMultiple")
        ok &= good
        print(f"   {'✓' if good else '✗'} {n}: windows in place, old ids kept, status {chk['status']}, "
              f"re-entry {chk.get('allowMultiple')}, steps {len(wf['workflowData']['templates'])} → {len(tp)}")
    L2 = a.call("GET", SERVICES, f"/locations/{LOC}")
    L2 = L2.get("location", L2)
    good = (not native_on or "STOP" in (L2.get("missedCallText") or "")) and L2.get("enableMissedCallText") == L.get("enableMissedCallText")
    ok &= good
    print(f"   {'✓' if good else '✗'} native missed-call text: {L2.get('missedCallText')!r}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
