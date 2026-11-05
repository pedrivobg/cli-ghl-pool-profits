#!/usr/bin/env python3
"""Ekahi Solutions: Hawaiian greetings + no booking links in the automations (Frank, e-mail 05/11/2026).

    ./.venv/bin/python scripts/ek_wording.py            # plan (read-only)
    ./.venv/bin/python scripts/ek_wording.py --apply    # backup + write + re-read
    ./.venv/bin/python scripts/ek_wording.py --test pedro@poolprofits.com   # preview e-mail via Test Snapshot

Surgical edits (formatting of the e-mails is kept):
- SMS templates: greeting "Hi {{" -> "Aloha {{", "Hey {{" -> "Howzit {{".
- Booking links -> call / text / reply: Reactivation SMS 2, Upsell SMS 2, Reactivation e-mails 1-3
  (template html AND the copy in the workflow step).
- E-mail steps whose html still has the booking link while their template was already rewritten to
  "call or reply" (Nurture Day 2/3, Lost Stage 1/2): the step gets the template's html.
Backup of every snippet and workflow touched in backup/ekahi-solutions-llc/ before writing.
"""
from __future__ import annotations

import argparse
import json
import re
import time

from _common import ROOT, load_dotenv

from cli_anything.gohighlevel.utils.agency import BACKEND, Agency

LOC = "qtSUhAbLtnENh56h17a3"
SLUG = "ekahi-solutions-llc"
PH = "{{custom_values.business_phone}}"
PSTYLE = '<p class="custom-newline" style="line-height: 1.5;padding-left: 0px!important;">{}</p>'

GREET = [(re.compile(r"^Hi \{\{"), "Aloha {{"), (re.compile(r"^Hey \{\{"), "Howzit {{")]

SMS_EDITS = {  # template name -> (old, new) after the greeting swap
    "Reactivation - SMS 2": ("Interested in getting your pool back in top shape? {{custom_values.booking_link}}",
                             f"Interested in getting your pool back in top shape? Just reply here or call/text us at {PH}."),
    "Upsell Opportunity - SMS 2": ("Interested? {{custom_values.booking_link}}",
                                   f"Interested? Just reply here or call/text us at {PH}."),
}
EMAIL_EDITS = {  # template name -> list of (old html, new html)
    "Reactivation - Email 1 - We Miss You": [
        (PSTYLE.format("📅 Book here: {{custom_values.booking_link}}"), PSTYLE.format(f"📞 Call or text us: {PH}")),
        (PSTYLE.format(f"📞 Or call us: {PH}"), PSTYLE.format("💬 Or just reply to this email.")),
    ],
    "Reactivation - Email 2 - How's Your Pool": [
        (PSTYLE.format("Give us a shot, book a free estimate today:") + PSTYLE.format("{{custom_values.booking_link}}"),
         PSTYLE.format(f"Give us a shot! Call or text us at {PH}, or just reply to this email for a free estimate.")),
    ],
    "Reactivation - Email 3 - Last Note": [
        (PSTYLE.format("{{custom_values.booking_link}}"),
         PSTYLE.format(f"Just call or text us at {PH}, or reply to this email anytime.")),
    ],
}


def plain(h: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", h or "")).strip()


def plan(a: Agency):
    snips = {s["_id"]: s for s in a.snippets(LOC)}
    new_tpl: dict[str, dict] = {}
    for sid, s in snips.items():
        tpl = dict(s.get("template") or {})
        name = s["name"].strip()
        if s["type"] == "sms":
            body = tpl.get("body") or ""
            nb = body
            for rx, rep in GREET:
                nb = rx.sub(rep, nb)
            if name in SMS_EDITS:
                old, new = SMS_EDITS[name]
                assert old in nb or new in nb, f"{name}: trecho não encontrado"
                nb = nb.replace(old, new)
            if nb != body:
                new_tpl[sid] = {**tpl, "body": nb}
        elif name in EMAIL_EDITS:
            h = tpl.get("html") or ""
            for old, new in EMAIL_EDITS[name]:
                assert old in h or new in h, f"{name}: trecho não encontrado"
                h = h.replace(old, new)
            if h != tpl.get("html"):
                new_tpl[sid] = {**tpl, "html": h}
    steps: dict[str, dict[str, str]] = {}  # wid -> {step id: new html}
    flows = {}
    for w in a.workflows(LOC):
        wf = a.workflow(LOC, w["id"])
        for st in wf["workflowData"]["templates"]:
            at = st.get("attributes") or {}
            if st.get("type") != "email" or "booking_link" not in (at.get("html") or ""):
                continue
            sid = at.get("template_id")
            target = (new_tpl.get(sid) or (snips.get(sid) or {}).get("template") or {}).get("html") or ""
            if not target or "booking_link" in target:
                raise SystemExit(f"{wf['name']} / {st['name']}: template ainda com link — revisar à mão")
            steps.setdefault(w["id"], {})[st["id"]] = target
            flows[w["id"]] = wf
    return snips, new_tpl, flows, steps


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--test", metavar="INBOX")
    args = ap.parse_args()
    load_dotenv()
    a = Agency()
    snips, new_tpl, flows, steps = plan(a)
    for sid, t in new_tpl.items():
        s = snips[sid]
        print(f"[{s['type']}] {s['name'].strip()}\n   - {plain(s['template'].get('body') or s['template'].get('html'))[:260]}"
              f"\n   + {plain(t.get('body') or t.get('html'))[:260]}")
    for wid, m in steps.items():
        for stid in m:
            st = next(x for x in flows[wid]["workflowData"]["templates"] if x["id"] == stid)
            print(f"[step] {flows[wid]['name']} / {st['name']}: html do passo = html do template (sem booking link)")
    if args.test:
        from pp_wording import run_test
        # current texts (after --apply new_tpl is empty): every SMS template + the e-mails edited here
        cur = {sid: {**(s.get("template") or {}), **new_tpl.get(sid, {})} for sid, s in snips.items()
               if s["type"] == "sms" or s["name"].strip() in EMAIL_EDITS}
        items = [{"msg": {"workflow": snips[sid]["name"].strip(), "step": snips[sid]["type"]},
                  "new": {"subject": t.get("subject") or snips[sid]["name"], "html": t["html"]}
                  if t.get("html") else {"body": t.get("body") or ""}} for sid, t in cur.items()]
        return run_test(a, {"location": LOC}, items, args.test)
    if not args.apply:
        print("\n(plano; --apply para gravar)")
        return 0
    stamp = time.strftime("%Y%m%d-%H%M%S")
    bdir = ROOT / "backup" / SLUG
    bdir.mkdir(parents=True, exist_ok=True)
    for sid in new_tpl:
        (bdir / f"snippet-{sid}-{stamp}.json").write_text(json.dumps(snips[sid], ensure_ascii=False))
    for wid, wf in flows.items():
        trs = [t for t in a.triggers(LOC, wid) if not t.get("deleted")]
        (bdir / f"workflow-{wid}-{stamp}.json").write_text(json.dumps({"workflow": wf, "triggers": trs},
                                                                      ensure_ascii=False))
    for sid, t in new_tpl.items():
        s = snips[sid]
        a.call("PUT", BACKEND, f"/snippets/{LOC}/{sid}", body={"name": s["name"], "type": s["type"], "template": t})
    for wid, m in steps.items():
        live = a.workflow(LOC, wid)
        tpl = json.loads(json.dumps(live["workflowData"]["templates"]))
        for st in tpl:
            if st["id"] in m:
                st["attributes"]["html"] = m[st["id"]]
        a.call("PUT", BACKEND, f"/workflow/{LOC}/{wid}", body={
            "name": live["name"], "version": live.get("version", 1), "status": live["status"],
            "parentId": live.get("parentId"), "allowMultiple": live.get("allowMultiple", True),
            "workflowData": {"templates": tpl}})
    bad = 0
    for _ in range(8):  # snippet reads lag ~10-20 s
        time.sleep(5)
        cur = {s["_id"]: s for s in a.snippets(LOC)}
        bad = sum((cur[sid].get("template") or {}).get(k) != t.get(k) for sid, t in new_tpl.items()
                  for k in ("body", "html") if k in t)
        if not bad:
            break
    for wid, m in steps.items():
        live = a.workflow(LOC, wid)
        got = {st["id"]: st["attributes"].get("html") for st in live["workflowData"]["templates"]}
        bad += sum(got.get(k) != v for k, v in m.items())
        print(f"   {live['name']}: status {live['status']}, allowMultiple {live.get('allowMultiple')}")
    print(f"{'✓' if not bad else '✗'} {len(new_tpl)} templates, {sum(len(m) for m in steps.values())} passos "
          f"(diferenças na releitura: {bad})")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
