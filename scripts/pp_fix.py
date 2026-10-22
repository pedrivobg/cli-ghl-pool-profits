#!/usr/bin/env python3
"""Apply the BASIC fixes the audit finds, in published workflows only. No logic changes.

    ./.venv/bin/python scripts/pp_fix.py --only "Southern Pool"            # dry-run: shows the diff
    ./.venv/bin/python scripts/pp_fix.py --only "Southern Pool" --apply    # backs up, writes, re-reads
    ... --drop-booking      treat booking_link as empty (baseline: no calendar link)
    ... --include-drafts    also fix drafts (account about to go live)
    ... --skip "In Communication Stage"   leave a workflow as the model has it (repeatable)

Works from dump/ (run pp_dump.py first, and again after --apply). Fixes:

1. Merge fields split by the email editor's autolink
   ``{{custom_<a href="http://values.booking">values.booking</a>_link}}`` → ``{{custom_values.booking_link}}``
2. Booking/calendar link when ``booking_link`` is EMPTY in the sub-account (the call
   dropped the calendar from the baseline): the sentence becomes "reply / call us",
   and "📞 Or call us:" left without its first option becomes "📞 Call us:".
   With --drop-booking the same happens even when it is filled (the GHL calendar
   widget most clients have there opens an empty page).
3. NPS survey link when ``nps_survey_link`` is EMPTY: ask for the reply instead.
4. Task steps with no assignee → the only user of the account, else the contact's
   assigned user; task due date "{{right_now.hour}}" (born due in 1970) → due now.
   Internal notifications to "user" with nobody selected → the only user.
5. Name of ANOTHER business (other sub-account, e.g. "Clear Pool Solutions Tucson")
   → {{custom_values.friendly_business_name}}.
6. "Create opportunity" pointing at a pipeline/stage that does not exist in the
   account (copied from another location) → Pool Leads → New Lead.

Anything with a booking link that does not match a known sentence is listed as
MANUAL and left untouched. Every object written is first saved to
backup/<slug>/<kind>-<id>-<stamp>.json; scripts/pp_restore.py puts it back.
"""
from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
import time

from _common import ROOT, load_dotenv, location_dirs
from pp_audit import TAG_RE, foreign_names, load, norm

from cli_anything.gohighlevel.utils.agency import BACKEND, Agency, GHLError

BACKUP = ROOT / "backup"

BROKEN_MERGE = re.compile(r"\{\{\s*([a-z_]*)<a [^>]*>([a-z_.]+)</a>([a-z_]*)\s*\}\}", re.I)
BOOKING = r"\{\{\s*custom_values\.booking_link\s*\}\}"
NPS = r"\{\{\s*custom_values\.nps_survey_link\s*\}\}"
PHONE = "{{custom_values.business_phone}}"
PARA = re.compile(r"<p\b[^>]*>(?:(?!</p>).)*?</p>", re.S)
SEP = r"(?:\s|</p>|<p\b[^>]*>|<br\s*/?>|&nbsp;)*"   # the link often sits in the next paragraph

# (pattern over the text of ONE paragraph / SMS, replacement). Order matters.
BOOKING_SENTENCES = [
    (re.compile(r"please book a quick call with us:" + SEP + BOOKING, re.I),
     "just reply to this email or give us a call at " + PHONE + "."),
    (re.compile(r"book a free estimate today:" + SEP + BOOKING, re.I),
     "reply to this email or give us a call for a free estimate."),
    # In Communication Stage (Nurture Email Day 2 / Day 3)
    (re.compile(r"book your free estimate here:" + SEP + BOOKING, re.I),
     "Just reply to this email to book your free estimate."),
    (re.compile(r"book your free estimate today:" + SEP + BOOKING + SEP + r"or call us directly:", re.I),
     "Reply to this email to book your free estimate, or call us directly:"),
    # only at the end of an SMS: the one rule that is not applied across paragraphs
    (re.compile(r"\?\s*" + BOOKING + r"\s*$", re.I),
     "? Just reply here or call us at " + PHONE + "."),
]
# A paragraph that is only the link (optionally "📅 Book here:") is dropped.
BOOKING_ONLY = re.compile(r"^\W*(book here:?)?\W*" + BOOKING + r"\W*$", re.I)
NPS_SENTENCES = [
    (re.compile(r"please take 10 seconds to rate your experience here:\s*" + NPS, re.I),
     "Just reply to this text and let us know."),
]


def plain(html: str) -> str:
    return re.sub(r"\s+", " ", TAG_RE.sub(" ", html or "")).strip()


class Fixer:
    def __init__(self, cv: dict[str, str], foreign: list[str] | None = None,
                 pipelines: list[dict] | None = None, users: list[dict] | None = None):
        self.cv = cv
        # with a single user there is no doubt who a notification/task is for
        self.only_user = users[0]["id"] if users and len(users) == 1 else None
        self.manual: list[str] = []
        self.pipelines = pipelines or []
        self.pool_leads = next((p for p in self.pipelines if "pool leads" in norm(p.get("name"))), None)
        self.new_lead_stage = next((s["id"] for s in (self.pool_leads or {}).get("stages", [])
                                    if "new lead" in norm(s["name"])), None)
        self.foreign = [re.compile(r"(?<![A-Za-z0-9])" + r"\s+".join(map(re.escape, n.split())) + r"(?![A-Za-z0-9])", re.I)
                        for n in (foreign or []) if norm(n) != "pool profits"]

    def text(self, value: str, where: str, is_html: bool) -> str:
        value = BROKEN_MERGE.sub(lambda m: "{{" + m.group(1) + m.group(2) + m.group(3) + "}}", value)
        for rx in self.foreign:
            value = rx.sub("{{custom_values.friendly_business_name}}", value)
        if not self.cv.get("booking_link") and re.search(BOOKING, value, re.I):
            value = self._booking(value, where, is_html)
        if not re.search(BOOKING, value, re.I):
            # "📅 Book here: … 📞 Or call us: …" once the booking line is gone
            value = re.sub(r"(📞\s*)Or call us:", r"\1Call us:", value)
        if not self.cv.get("nps_survey_link") and re.search(NPS, value, re.I):
            for rx, rep in NPS_SENTENCES:
                value = rx.sub(rep, value)
            if re.search(NPS, value, re.I):
                self.manual.append(f"{where}: link de NPS vazio numa frase não prevista")
        return value

    def _booking(self, value: str, where: str, is_html: bool) -> str:
        def fix_piece(piece: str) -> str | None:
            text = plain(piece) if is_html else piece
            if BOOKING_ONLY.match(text):
                return None
            for rx, rep in BOOKING_SENTENCES:
                if rx.search(piece):
                    return rx.sub(rep, piece)
            return piece

        for rx, rep in BOOKING_SENTENCES[:-1]:
            value = rx.sub(rep, value)
        if is_html:
            def para(m: re.Match) -> str:
                if not re.search(BOOKING, m.group(0), re.I):
                    return m.group(0)
                fixed = fix_piece(m.group(0))
                return "" if fixed is None else fixed
            value = PARA.sub(para, value)
        else:
            fixed = fix_piece(value)
            value = "" if fixed is None else fixed
        if re.search(BOOKING, value, re.I):
            self.manual.append(f"{where}: booking_link vazio numa frase não prevista")
        return value

    def step(self, step: dict, where: str) -> dict:
        step = json.loads(json.dumps(step))
        attrs = step.get("attributes") or {}
        for key in ("html", "body", "subject"):
            if isinstance(attrs.get(key), str):
                attrs[key] = self.text(attrs[key], where, key == "html")
        for sub in ("sms", "email", "notification"):
            if isinstance(attrs.get(sub), dict):
                for key in ("html", "body", "subject"):
                    if isinstance(attrs[sub].get(key), str):
                        attrs[sub][key] = self.text(attrs[sub][key], where, key == "html")
        if step.get("type") == "task-notification" and attrs.get("assignedTo") == "":
            attrs["assignedTo"] = self.only_user or "contact.assigned_user"
        if step.get("type") == "task-notification" and isinstance(attrs.get("dueDate"), str) \
                and "{{" in attrs["dueDate"]:
            # "{{right_now.hour}}" does not resolve: the task is born due in 1970
            attrs["dueDate"] = {"duration": 0, "unit": "days"}
            (attrs.get("__customInputs__") or {}).pop("dueDate", None)
        if step.get("type") == "internal_notification" and self.only_user:
            for sub in ("sms", "email", "notification"):
                block = attrs.get(sub)
                if isinstance(block, dict) and block.get("userType") == "user" and not block.get("selectedUser"):
                    block["selectedUser"] = [self.only_user]
        if step.get("type") == "create_opportunity" and self.pool_leads:
            stage_ids = {s["id"] for s in self.pool_leads["stages"]}
            known = {p["id"] for p in self.pipelines}
            pid, sid = attrs.get("pipeline_id"), attrs.get("pipeline_stage_id")
            if pid and pid not in known:
                attrs["pipeline_id"] = self.pool_leads["id"]
                pid = self.pool_leads["id"]
            if pid == self.pool_leads["id"] and sid and sid not in stage_ids:
                # every snapshot copy of these steps creates the lead in New Lead
                attrs["pipeline_stage_id"] = self.new_lead_stage
        return step

    def snippet(self, snippet: dict, where: str) -> dict:
        snippet = json.loads(json.dumps(snippet))
        tpl = snippet.get("template") or {}
        for key in ("html", "body", "subject"):
            if isinstance(tpl.get(key), str):
                tpl[key] = self.text(tpl[key], where, key == "html" or "<p" in tpl[key])
        return snippet


def show(label: str, before: str, after: str) -> None:
    a, b = plain(before).split(". "), plain(after).split(". ")
    diff = [l for l in difflib.unified_diff(a, b, lineterm="", n=0) if l[:1] in "+-" and l[:3] not in ("---", "+++")]
    print(f"   · {label}")
    for line in diff[:12]:
        print(f"       {line[:220]}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--only", action="append", required=True)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--drop-booking", action="store_true",
                        help="remove the booking link from messages even when booking_link is filled")
    parser.add_argument("--include-drafts", action="store_true",
                        help="also fix draft workflows (accounts about to go live)")
    parser.add_argument("--skip", action="append", default=[],
                        help="leave this workflow (and its templates) as it is (repeatable)")
    args = parser.parse_args()
    load_dotenv()
    agency = Agency() if args.apply else None

    for d in location_dirs(args.only):
        location = load(d / "location.json", {})
        loc = location["id"]
        cv = {}
        for item in load(d / "custom_values.json", []):
            m = re.search(r"custom_values\.([a-zA-Z0-9_]+)", item.get("fieldKey") or "")
            if m:
                cv[m.group(1)] = (item.get("value") or "").strip()
        if args.drop_booking:
            cv["booking_link"] = ""
        all_dirs = location_dirs()
        others = {}
        for other in all_dirs:
            if other != d:
                for item in load(other / "custom_values.json", []):
                    if "friendly_business_name" in (item.get("fieldKey") or "") and item.get("value"):
                        others[other.name] = item["value"]
        fixer = Fixer(cv, foreign_names(location, others), load(d / "pipelines.json", []),
                      load(d / "users.json", []))
        snippets = {s["_id"]: s for s in load(d / "snippets.json", [])}
        index = load(d / "workflows" / "_index.json", [])
        print(f"\n== {location.get('name')} ({'APLICANDO' if args.apply else 'dry-run'})")

        snippet_ids: set[str] = set()
        wf_changes = []
        for meta in index:
            if meta["status"] != "published" and not args.include_drafts or meta["name"] in args.skip:
                continue
            wf = load(d / "workflows" / f"{meta['id']}.json", {})
            steps = (wf.get("workflowData") or {}).get("templates") or []
            new_steps, changed = [], []
            for s in steps:
                ref = (s.get("attributes") or {}).get("template_id")
                if ref in snippets:
                    snippet_ids.add(ref)
                ns = fixer.step(s, f"{meta['name']} / {s.get('name')}")
                if ns != s:
                    changed.append((s, ns))
                new_steps.append(ns)
            if changed:
                wf_changes.append((meta, wf, new_steps, changed))

        sn_changes = []
        for sid in sorted(snippet_ids):
            old = snippets[sid]
            new = fixer.snippet(old, f"template '{old.get('name')}'")
            if new != old:
                sn_changes.append((old, new))

        for meta, wf, _, changed in wf_changes:
            print(f"  workflow: {meta['name']}")
            for old, new in changed:
                show(old.get("name", ""), json.dumps(old.get("attributes"), ensure_ascii=False),
                     json.dumps(new.get("attributes"), ensure_ascii=False))
        for old, new in sn_changes:
            print(f"  template: {old.get('name')}")
            show("texto", json.dumps(old.get("template"), ensure_ascii=False),
                 json.dumps(new.get("template"), ensure_ascii=False))
        for m in fixer.manual:
            print(f"  ⚠ MANUAL: {m}")
        if not (wf_changes or sn_changes):
            print("  nada a corrigir")
        if not args.apply:
            continue

        bdir = BACKUP / d.name
        bdir.mkdir(parents=True, exist_ok=True)
        stamp = time.strftime("%Y%m%d-%H%M%S")
        for old, new in sn_changes:
            live = next((s for s in agency.snippets(loc) if s.get("_id") == old["_id"]), None)
            if live is None:
                print(f"  ✗ template sumiu: {old.get('name')}", file=sys.stderr)
                continue
            (bdir / f"snippet-{old['_id']}-{stamp}.json").write_text(json.dumps(live, ensure_ascii=False, indent=1))
            agency.call("PUT", BACKEND, f"/snippets/{loc}/{old['_id']}",
                        body={"name": live["name"], "type": live["type"],
                              "template": fixer.snippet(live, live["name"])["template"]})
            print(f"  ✓ template {old.get('name')}")
        for meta, _, _, _ in wf_changes:
            live = agency.workflow(loc, meta["id"])
            (bdir / f"workflow-{meta['id']}-{stamp}.json").write_text(json.dumps(live, ensure_ascii=False, indent=1))
            steps = [fixer.step(s, meta["name"]) for s in (live.get("workflowData") or {}).get("templates") or []]
            body = {"name": live["name"], "version": live.get("version", 1),
                    "status": live.get("status") or "draft", "parentId": live.get("parentId"),
                    "workflowData": {"templates": steps}}
            try:
                agency.call("PUT", BACKEND, f"/workflow/{loc}/{meta['id']}", body=body)
            except GHLError as exc:
                print(f"  ✗ workflow {meta['name']}: GHL recusou — {exc.body[:220]}")
                continue
            after = agency.workflow(loc, meta["id"])
            ok = after.get("status") == live.get("status") and \
                len((after.get("workflowData") or {}).get("templates") or []) == len(steps)
            print(f"  {'✓' if ok else '✗ VERIFICAR'} workflow {meta['name']} "
                  f"(status {after.get('status')}, {len(steps)} passos)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
