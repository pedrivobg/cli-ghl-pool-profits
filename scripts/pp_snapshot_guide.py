#!/usr/bin/env python3
"""Client-facing PDF of the snapshot: funnels, sales pipeline, automations and every message (Ed, 22/10: Jeremy at
SwimReady wants to study the system and suggest changes before it goes into his account).

    ./.venv/bin/python scripts/pp_snapshot_guide.py --for "SwimReady Pool Service"
    ... --shots      # first refresh funnels.json from the API and re-take the page screenshots (headless Chromium)

Reads dump/snapshot-pool-profits (pp_dump.py --only "Snapshot Pool Profits") and config/snapshot_guide.json (codes A1…,
phases, the plain-English purpose of each automation, stage/form/custom-value notes, funnels to show). Message texts
come from the snapshot as they are; merge fields show as chips. Every customer or team message gets a code (M1…), so
the client can ask for changes by code. Writes reports/snapshot-guide/<slug>.html and .pdf (gitignored).
"""
from __future__ import annotations

import argparse
import html
import json
import re
import subprocess
import sys
import time
from pathlib import Path

from _common import DUMP, ROOT, load_dotenv, slugify

CHROMIUM = "/opt/pw-browsers/chromium"
MASTER = DUMP / "snapshot-pool-profits"
OUT = ROOT / "reports" / "snapshot-guide"
SHOTS = OUT / "shots"
CFG = json.loads((ROOT / "config" / "snapshot_guide.json").read_text())

MERGE = {
    "contact.first_name": "First Name", "contact.name": "Name", "contact.phone": "Phone", "contact.phone_raw": "Phone",
    "contact.email": "Email", "contact.city": "City", "contact.address1": "Address", "contact.postal_code": "ZIP",
    "contact.state": "State", "contact.nps_score": "Rating", "contact.nps_message": "Rating Comment",
    "custom_values.friendly_business_name": "Business Name", "location.name": "Business Name",
    "custom_values.business_phone": "Business Phone", "custom_values.a2p_verification_number": "Texting Number",
    "custom_values.owner_first_name": "Owner First Name", "custom_values.nps_survey_link": "Rating Link",
    "custom_values.google_review_link": "Google Review Link", "appointment.start_date_time": "Appointment Date & Time",
    "message.body": "Their Message", "message.attachments": "Attachments", "user.name": "Team Member",
}
MERGE_RE = re.compile(r"\{\{\s*([^}]+?)\s*\}\}")
DAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
RECIPIENT = {"assign": "the assigned team member", "all": "all team members", "user": "selected team members",
             "contact.assigned_user": "the assigned team member"}


def esc(s: str) -> str:
    return html.escape(s or "", quote=False)


def chips(text: str) -> str:
    """Plain text → HTML with merge fields as chips (the rating link drops its tracking query)."""
    text = re.sub(r"(\{\{\s*custom_values\.nps_survey_link\s*\}\})\?\S+", r"\1", text or "")
    out, pos = [], 0
    for m in MERGE_RE.finditer(text):
        out.append(esc(text[pos:m.start()]))
        key = m.group(1)
        label = MERGE.get(key) or key.split(".")[-1].replace("_", " ").title()
        out.append(f'<span class="mf">{esc(label)}</span>')
        pos = m.end()
    out.append(esc(text[pos:]))
    return "".join(out)


def lines(raw: str) -> list[str]:
    s = re.sub(r"(?i)<br\s*/?>", "\n", raw or "")
    s = re.sub(r"(?i)</(p|div|li|h[1-6]|tr)>", "\n", s)
    s = re.sub(r"(?i)<li[^>]*>", "• ", s)
    s = html.unescape(re.sub(r"<[^>]+>", "", s)).replace("\xa0", " ")
    out: list[str] = []
    for ln in (re.sub(r"[ \t]+", " ", x).strip() for x in s.split("\n")):
        if ln or (out and out[-1]):
            out.append(ln)
    while out and not out[-1]:
        out.pop()
    return out


def para(raw: str) -> str:
    return "".join(f"<p>{chips(ln)}</p>" if ln else '<p class="gap"></p>' for ln in lines(raw))


def plural(n, unit: str) -> str:
    n = int(n) if float(n).is_integer() else n
    unit = unit.rstrip("s")
    return f"{n} {unit}{'' if n == 1 else 's'}"


def window_text(win: dict | None) -> str:
    if not win or not win.get("days"):
        return ""
    days = sorted(win["days"])
    span = "every day" if len(days) == 7 else "Mon–Fri" if days == [1, 2, 3, 4, 5] else ", ".join(DAYS[d] for d in days)
    fmt = lambda t: time.strftime("%-I%p", time.strptime(t, "%H:%M")).lower()  # noqa: E731
    return f"sent {span}, {fmt(win['start'])}–{fmt(win['end'])}"


class Guide:
    def __init__(self, client: str):
        self.client = client
        self.flows = [w for f in sorted((MASTER / "workflows").glob("*.json")) if f.name != "_index.json"
                      for w in [json.loads(f.read_text())] if isinstance(w, dict) and w.get("workflowData")]
        self.by_name = {w["name"]: w for w in self.flows}
        self.code = {w["id"]: CFG["automations"][w["name"]]["code"] for w in self.flows if w["name"] in CFG["automations"]}
        missing = [w["name"] for w in self.flows if w["name"] not in CFG["automations"]]
        if missing:
            sys.exit(f"sem descrição em config/snapshot_guide.json: {missing}")
        self.snip = {s["_id"]: s for s in json.loads((MASTER / "snippets.json").read_text())}
        self.pipe = json.loads((MASTER / "pipelines.json").read_text())[0]
        self.stage = {s["id"]: s["name"] for s in self.pipe["stages"]}
        self.forms = {f["_id"]: f["name"] for f in json.loads((MASTER / "forms.json").read_text())}
        cals = json.loads((MASTER / "calendars.json").read_text())
        self.cals = {c["id"]: c for c in (cals if isinstance(cals, list) else cals.get("calendars", []))}
        self.cvs = json.loads((MASTER / "custom_values.json").read_text())
        self.cfields = json.loads((MASTER / "custom_fields.json").read_text())
        self.tags = json.loads((MASTER / "tags.json").read_text())
        self.funnels = json.loads((MASTER / "funnels.json").read_text())["funnels"]
        self.messages: list[dict] = []  # index of M codes
        self.node_code: dict[str, str] = {}  # step id → M code ("waits for a reply to M7")
        self.cur: dict = {}

    # ── triggers ───────────────────────────────────────────────────────────

    def trigger_text(self, t: dict) -> str:
        ty, conds = t["type"], t.get("conditions") or []
        val = lambda field: [c.get("value") for c in conds if c.get("field") == field]  # noqa: E731
        skip = " (skipped for contacts tagged “existing customer”)" if any(
            c.get("operator") == "index-of-false" and c.get("value") == "existing customer" for c in conds) else ""
        if ty == "form_submission":
            ids = [v for c in conds for v in (c["value"] if isinstance(c["value"], list) else [c["value"]])]
            return "A lead submits one of these forms: " + ", ".join(f"“{self.forms.get(i, i)}”" for i in ids)
        if ty == "call_status":
            if any(c.get("field") == "inbound_number" for c in conds):
                return "A call comes in on your Google Ads tracking number"
            st = [v for c in conds if "status" in (c.get("field") or "").lower() or c.get("title") == "Call status"
                  for v in (c["value"] if isinstance(c["value"], list) else [c["value"]])]
            return ("An inbound call to your business line is answered" if st == ["completed"] else
                    "An inbound call is missed (no answer, busy, voicemail or hung up)")
        if ty == "contact_tag":
            tag = (val("tagsAdded") or [c.get("value") for c in conds])[0]
            return f"The tag “{tag}” is added to a contact"
        if ty == "pipeline_stage_updated":
            st = self.stage.get((val("opportunity.pipelineStageId") or [""])[0], "?")
            return f"A card moves to the “{st}” stage{skip}"
        if ty == "appointment":
            cal = next((self.cals[c["value"]]["name"] for c in conds
                        if isinstance(c.get("value"), str) and c["value"] in self.cals), "your")
            return f"An appointment is booked and confirmed on the “{cal}” calendar"
        if ty == "contact_created":
            return "A new contact is added (call, text, form or import)"
        if ty == "reputation_review_received":
            c = conds[0]
            return f"A new Google review comes in with {'3 stars or less' if '<' in c['operator'] else '4 or 5 stars'}"
        if ty == "customer_reply":
            return "A contact tagged “reactivation” replies by text"
        if ty == "ivr_incoming_call":
            return "A call comes in on your main business line"
        return t.get("name") or ty

    # ── steps ──────────────────────────────────────────────────────────────

    def new_msg(self, to: str, channel: str, subject: str, first: str) -> str:
        code = f"M{len(self.messages) + 1}"
        if len(first) > 80:  # whole words, never half a merge field
            first = re.sub(r"\{\{[^}]*$", "", first[:80].rsplit(" ", 1)[0]).rstrip(" ,.-") + "…"
        self.messages.append({"code": code, "to": to, "channel": channel, "auto": self.cur["code"],
                              "title": self.cur["title"], "subject": subject, "first": first})
        return code

    def message(self, n: dict) -> str:
        before = len(self.messages)
        out = self._message(n)
        if len(self.messages) > before:
            self.node_code[n["id"]] = self.messages[-1]["code"]
        return out

    def _message(self, n: dict) -> str:
        a, ty = n.get("attributes") or {}, n["type"]
        if ty == "sms":
            s = self.snip.get(a.get("template_id"))
            body = (s["template"].get("body") if s and isinstance(s.get("template"), dict) else None) or a.get("body", "")
            code = self.new_msg("Customer", "Text", "", " ".join(lines(body)))
            return (f'<div class="msg sms"><div class="mh"><span class="mcode">{code}</span>Text message to the customer'
                    f'</div><div class="bubble">{para(body)}</div></div>')
        if ty == "email":
            subj = a.get("subject", "")
            code = self.new_msg("Customer", "Email", subj, " ".join(lines(a.get("html", ""))))
            return (f'<div class="msg email"><div class="mh"><span class="mcode">{code}</span>Email to the customer</div>'
                    f'<div class="paper"><div class="subj">Subject: {chips(subj)}</div>{para(a.get("html", ""))}</div></div>')
        if ty == "internal_notification":
            kind = a.get("type")
            sub = a.get(kind) if isinstance(a.get(kind), dict) else {}
            who = RECIPIENT.get(sub.get("userType"), "your team")
            label = {"sms": f"Text alert to {who}", "email": f"Email alert to {who}",
                     "notification": f"App notification to {who}"}.get(kind, f"Alert to {who}")
            body = sub.get("body") or sub.get("html") or ""
            title = sub.get("title") or sub.get("subject") or ""
            code = self.new_msg("Team", {"sms": "Text", "email": "Email", "notification": "App"}.get(kind, "Alert"), title,
                                " ".join(lines(body)))
            head = f'<div class="subj">{chips(title)}</div>' if title else ""
            return (f'<div class="msg team"><div class="mh"><span class="mcode">{code}</span>{esc(label)}</div>'
                    f'<div class="note">{head}{para(body)}</div></div>')
        if ty == "task-notification":
            who = RECIPIENT.get(a.get("assignedTo"), "the assigned team member")
            code = self.new_msg("Team", "Task", a.get("title", ""), " ".join(lines(a.get("body", ""))))
            return (f'<div class="msg team task"><div class="mh"><span class="mcode">{code}</span>Task for {esc(who)} '
                    f'(due right away)</div><div class="note"><div class="subj">{chips(a.get("title", ""))}</div>'
                    f'{para(a.get("body", ""))}</div></div>')
        if ty == "review_request":
            channel = "Text" if a.get("review_type") == "sms" else "Email"
            code = self.new_msg("Customer", channel, "Google review request", "Review request with your Google link")
            return (f'<div class="msg review"><div class="mh"><span class="mcode">{code}</span>Google review request '
                    f'by {channel.lower()}</div><div class="note"><p>Sent through the Reputation tool with your '
                    f'<span class="mf">Google Review Link</span>. The wording is set once in Reputation settings and can '
                    f'be customized.</p></div></div>')
        return ""

    def action(self, n: dict) -> str | None:
        a, ty = n.get("attributes") or {}, n["type"]
        if ty == "add_contact_tag":
            return "Tag: " + ", ".join(f"“{t}”" for t in a.get("tags", []))
        if ty == "remove_contact_tag":
            return "Remove tag: " + ", ".join(f"“{t}”" for t in a.get("tags", []))
        if ty == "create_opportunity":
            st = self.stage.get(a.get("pipeline_stage_id"), "?")
            return f"Card → {st}" + (" (marked won)" if a.get("opportunity_status") == "won" else "")
        if ty == "update_contact_field":
            return "; ".join(f"Set {f.get('title')} = {f.get('value')}" for f in a.get("fields", []))
        if ty == "assign_user":
            return "Assign the contact to your team member"
        if ty == "dnd_contact":
            return "Turn on Do Not Disturb (no more texts or emails)"
        if ty == "remove_from_workflow":
            codes = [self.code.get(w, "?") for w in a.get("workflow_id", [])]
            return "Stop " + ", ".join(codes) + " (appointment reminders)"
        if ty == "google_adword":
            return "Report a conversion to Google Ads"
        return None

    def wait_text(self, n: dict) -> str:
        a = n.get("attributes") or {}
        sa = a.get("startAfter") or {}
        if a.get("type") == "appointment" or (not sa and "before" in n["name"].lower()):
            return n["name"].replace("Wait ", "Wait until ") + " the appointment" if "before" in n["name"] else \
                "Wait until 1 hour before the appointment"
        base = f"Wait {plural(sa.get('value', 0), sa.get('type', 'day'))}" if sa else n["name"]
        win = window_text(a.get("window"))
        return base + (f" ({win})" if win else "")

    # ── flows ──────────────────────────────────────────────────────────────

    def walk(self, nodes: dict, nid: str | None) -> list:
        items = []
        while nid and nid in nodes:
            n = nodes[nid]
            nxt = n.get("next")
            if n["type"] == "wait" and isinstance(nxt, list):
                trans = [nodes[x] for x in nxt if x in nodes]
                reply = next((t for t in trans if t["attributes"].get("type") in ("wait_reply", "wait_condition")), None)
                timeout = next((t for t in trans if t["attributes"].get("type") == "wait_timeout"), None)
                items.append(("fork", n, self.walk(nodes, reply.get("next")) if reply else []))
                nid = timeout.get("next") if timeout else None
                continue
            if n["type"] == "if_else" and isinstance(nxt, list):
                branches = [(nodes[b]["name"], self.walk(nodes, nodes[b].get("next"))) for b in nxt if b in nodes]
                items.append(("branch", n, branches))
                break
            items.append(("step", n))
            nid = nxt if isinstance(nxt, str) else None
        return items

    def render(self, items: list, labels: dict | None = None) -> str:
        out, acts = [], []

        def flush():
            if acts:
                out.append('<div class="acts">' + "".join(f'<span class="act">{chips(x)}</span>' for x in acts) + "</div>")
                acts.clear()

        for it in items:
            kind, n = it[0], it[1]
            if kind == "step":
                act = self.action(n)
                if act:
                    acts.append(act)
                    continue
                flush()
                if n["type"] == "wait":
                    out.append(f'<div class="wait"><span>⏱ {esc(self.wait_text(n))}</span></div>')
                elif n["type"] == "goto":
                    out.append('<div class="wait"><span>↪ Continues with the step above</span></div>')
                else:
                    out.append(self.message(n))
            elif kind == "fork":
                flush()
                a = n.get("attributes") or {}
                sa = a.get("startAfter") or {}
                about = ", ".join(self.node_code.get(r, lbl) for r, lbl in zip(a.get("reply") or [], a.get("replyLabel") or [])) \
                    or "the last message"
                out.append(f'<div class="wait"><span>⏱ Waits up to {plural(sa.get("value", 0), sa.get("type", "day"))} '
                           f'for a reply to {esc(about)}</span></div>')
                out.append(f'<div class="fork"><div class="fork-side"><b>If they reply:</b>{self.render(it[2])}</div>'
                           f'<div class="fork-main">No reply: continue ↓</div></div>')
            elif kind == "branch":
                flush()
                real = [(name, sub) for name, sub in it[2] if sub]
                for name, sub in real:
                    label = (labels or {}).get(name, name)
                    out.append(f'<div class="path"><div class="path-label">If {esc(label)}</div>{self.render(sub)}</div>')
        flush()
        return "".join(out)

    def custom_flow(self, w: dict, spec: list) -> str:
        nodes = {n["name"]: n for n in w["workflowData"]["templates"]}
        out = []
        for it in spec:
            k = it["kind"]
            if k == "wait":
                out.append(f'<div class="wait"><span>⏱ {esc(it["text"])}</span></div>')
            elif k == "action":
                out.append(f'<div class="acts"><span class="act">{esc(it["text"])}</span></div>')
            elif k == "step":
                out.append(self.message(nodes[it["name"]]))
            elif k == "paths":
                for p in it["paths"]:
                    out.append(f'<div class="path"><div class="path-label">If {esc(p["label"])}</div>'
                               f'{self.custom_flow(w, p["items"])}</div>')
        return "".join(out)

    def automation(self, w: dict) -> str:
        c = CFG["automations"][w["name"]]
        self.cur = c
        if w["status"] == "published":
            pill = '<span class="pill on">ON at launch</span>'
        elif c.get("status_note"):
            pill = f'<span class="pill soon">{esc(c["status_note"])}</span>'
        else:
            pill = '<span class="pill opt">OPTIONAL · off until you ask</span>'
        trig = [c["trigger_note"]] if c.get("trigger_note") else \
            list(dict.fromkeys(self.trigger_text(t) for t in w.get("triggers") or [] if not t.get("deleted")))
        if c.get("flow"):
            flow = self.custom_flow(w, c["flow"])
        else:
            nodes = {n["id"]: n for n in w["workflowData"]["templates"]}
            pointed = {x for n in nodes.values() for x in (n.get("next") if isinstance(n.get("next"), list)
                                                           else [n.get("next")]) if x}
            root = next(n["id"] for n in sorted(nodes.values(), key=lambda n: n.get("order", 0)) if n["id"] not in pointed)
            flow = self.render(self.walk(nodes, root), c.get("branch_labels"))
        folder = (w.get("_folder") or "").split(" ", 1)[-1]
        return f"""
<section class="auto" id="{c['code']}">
  <div class="auto-head"><span class="code">{c['code']}</span><h3>{esc(c['title'])}</h3>{pill}</div>
  <div class="meta">In the CRM: “{esc(w['name'])}” · folder “{esc(folder)}”</div>
  <p class="purpose">{esc(c['purpose'])}</p>
  <div class="starts"><span class="lbl">Starts when</span><ul>{''.join(f'<li>{esc(t)}</li>' for t in trig)}</ul></div>
  <div class="flow"><div class="lbl">What happens</div>{flow}</div>
</section>"""

    # ── pages ──────────────────────────────────────────────────────────────

    def ordered(self) -> list[dict]:
        key = lambda w: int(CFG["automations"][w["name"]]["code"][1:])  # noqa: E731
        return sorted(self.flows, key=key)

    def cover(self) -> str:
        return f"""
<section class="cover">
  <svg class="waves" viewBox="0 0 800 300" preserveAspectRatio="none" aria-hidden="true">
    <path d="M0 180 C150 120 250 240 400 190 C550 140 650 230 800 170 L800 300 L0 300 Z" fill="rgba(255,255,255,.06)"/>
    <path d="M0 220 C170 170 260 280 420 230 C580 180 660 270 800 220 L800 300 L0 300 Z" fill="rgba(255,255,255,.08)"/>
    <path d="M0 260 C160 230 300 300 460 265 C600 235 700 290 800 260 L800 300 L0 300 Z" fill="rgba(255,255,255,.10)"/>
  </svg>
  <div class="brand">POOL PROFITS</div>
  <div class="cover-body">
    <div class="kicker">CRM system overview</div>
    <h1>{esc(CFG['title'])}</h1>
    <p class="sub">{esc(CFG['subtitle'])}</p>
    <div class="prep">Prepared for <b>{esc(self.client)}</b><br>{time.strftime('%B %Y')}</div>
  </div>
</section>"""

    def glance(self) -> str:
        on = sum(1 for w in self.flows if w["status"] == "published" or CFG["automations"][w["name"]].get("status_note"))
        fun = [f for f in CFG["funnels"]]
        pages = sum(len(next((x for x in self.funnels if x["name"].strip() == f["name"]), {}).get("steps") or [])
                    for f in fun)
        cust = sum(1 for m in self.messages if m["to"] == "Customer")
        team = len(self.messages) - cust
        stats = [(len(self.flows), "automations", f"{on} on at launch · {len(self.flows) - on} optional"),
                 (cust, "customer messages", "texts, emails and review requests"),
                 (team, "team alerts & tasks", "so leads never go cold"),
                 (len(self.pipe["stages"]), "pipeline stages", "from New Lead to Recurring Customer"),
                 (len(fun), "funnels & websites", f"{pages} ready-made pages"),
                 (len(self.forms), "forms", f"+ {len(self.cals)} booking calendars")]
        rows = "".join(
            f'<tr><td class="c">{CFG["automations"][w["name"]]["code"]}</td><td>{esc(CFG["automations"][w["name"]]["title"])}</td>'
            f'<td>{esc(next(p["title"] for p in CFG["phases"] if p["id"] == CFG["automations"][w["name"]]["phase"]))}</td>'
            f'<td>{"ON" if w["status"] == "published" else "ON*" if CFG["automations"][w["name"]].get("status_note") else "Optional"}</td></tr>'
            for w in self.ordered())
        return f"""
<section class="page">
  <h2>At a glance</h2>
  <p class="lead">This is the complete system we set up in your CRM: the pages that capture leads, the pipeline your team
  works every day, and the automations that follow up, welcome, ask for reviews and win customers back. Everything below
  is pulled straight from the system, including the exact wording of every message.</p>
  <div class="stats">{''.join(f'<div class="stat"><div class="n">{n}</div><div class="t">{esc(t)}</div><div class="s">{esc(s)}</div></div>' for n, t, s in stats)}</div>
  <div class="howto">
    <h4>How to suggest changes</h4>
    <p>Every automation has a code (<b>A1</b>–<b>A{len(self.flows)}</b>) and every message has one too (<b>M1</b>–<b>M{len(self.messages)}</b>).
    Just reference the code, for example:</p>
    <ul><li>“<b>M12</b>: make it more casual and mention our 5-star rating”</li>
    <li>“<b>A6</b>: wait 2 days before the first text instead of 1”</li>
    <li>“Turn on <b>A17</b>, and send it every month”</li></ul>
    <p>Grey chips like <span class="mf">First Name</span> or <span class="mf">Business Name</span> are filled in automatically for each
    customer. Messages read as plain text here; we'll set your logo, colors and links.</p>
  </div>
  <h4 class="idx-h">All automations</h4>
  <table class="idx"><thead><tr><th></th><th>Automation</th><th>Part of the journey</th><th>Status</th></tr></thead><tbody>{rows}</tbody></table>
  <p class="foot">ON = active from day one. ON* = turned on once your Google review link is connected. Optional = built
  and ready; we switch it on when you want it.</p>
</section>"""

    def journey(self) -> str:
        def box(x, y, w, h, title, sub, codes, cls="b"):
            sub_html = "".join(f'<tspan x="{x + 12}" dy="15">{esc(s)}</tspan>' for s in sub)
            code = f'<text x="{x + w - 10}" y="{y + 20}" class="cd" text-anchor="end">{esc(codes)}</text>' if codes else ""
            return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" class="{cls}"/>'
                    f'<text x="{x + 12}" y="{y + 21}" class="bt">{esc(title)}</text>{code}'
                    f'<text x="{x + 12}" y="{y + 25}" class="bs">{sub_html}</text>')

        def arrow(x1, y1, x2, y2):
            return f'<path d="M{x1} {y1} L{x2} {y2}" class="ar" marker-end="url(#ah)"/>'

        g = []
        c1, c2, c3, c4 = 20, 266, 522, 770
        g.append(f'<text x="{c1}" y="30" class="ch">1 · Leads come in</text><text x="{c2}" y="30" class="ch">2 · Work the lead</text>'
                 f'<text x="{c3}" y="30" class="ch">3 · Win the job</text><text x="{c4}" y="30" class="ch">4 · After the sale</text>')
        for i, (t, s, c) in enumerate([("Website & landing pages", ["Quote and contact forms"], "A1"),
                                       ("Calls answered", ["Card + call-review task"], "A2"),
                                       ("Calls missed", ["Instant text back"], "A3 A4"),
                                       ("Google Ads", ["Calls and ad forms (optional)"], "A25 A26"),
                                       ("Win-back replies", ["Old leads texting back"], "A22")]):
            y = 48 + i * 72
            g.append(box(c1, y, 210, 60, t, s, c, "b src"))
            g.append(arrow(c1 + 212, y + 30, c2 - 4, 79))
        g.append(box(c2, 48, 220, 62, "🆕 New Lead", ["Team alerted, owner assigned"], "A5", "b stage"))
        g.append(arrow(c2 + 110, 112, c2 + 110, 133))
        for i, (t, s, c) in enumerate([("No Response", ["3 texts over a week"], "A6"),
                                       ("💬 In Communication", ["You're talking (A7 opt.)"], ""),
                                       ("📅 Scheduled", ["Confirm + remind (opt.)"], "A8"),
                                       ("💰 Quote Sent", ["2 follow-up texts"], "A10"),
                                       ("No Show", ["Reschedule texts"], "A9")]):
            g.append(box(c2, 136 + i * 56, 220, 48, t, s, c, "b stage sm"))
        g.append(arrow(c2 + 222, 262, c3 - 4, 150))
        g.append(arrow(c2 + 222, 330, c3 - 4, 440))
        for i, t in enumerate(["🏆 Weekly service", "🏆 Repair / install", "🏆 Construction"]):
            g.append(box(c3, 48 + i * 64, 210, 56, t, ["Welcome email + text" if i == 0 else "Tagged and marked won"],
                         "A11", "b won"))
        g.append(arrow(c3 + 105, 234, c3 + 105, 255))
        g.append(box(c3, 258, 210, 60, "🔄 Recurring Customer", ["Tagged; reminders can start"], "A12", "b won"))
        g.append(f'<text x="{c3}" y="356" class="ch">Exits</text>')
        for i, (t, s, c) in enumerate([("❄ Not Qualified", ["Nothing is sent"], ""),
                                       ("❌ Lost", ["Feedback + 90-day check-in"], "A23"),
                                       ("🚫 Spam", ["Do Not Disturb turned on"], "A24")]):
            g.append(box(c3, 366 + i * 56, 210, 48, t, s, c, "b exit"))
        y = 48
        for t, s, c, h in [("Rating → Google review", ["Happy: review link", "Unhappy: team first"], "A14", 76),
                           ("Review replies", ["Thank-you / apology + task"], "A15 A16", 60),
                           ("Reminders & upsell", ["Monthly, filter, upsell (opt.)"], "A17–A19", 60),
                           ("Win-back campaigns", ["3 texts + 3 emails"], "A20 A21", 60)]:
            g.append(box(c4, y, 210, h, t, s, c, "b after"))
            y += h + 12
        g.append(arrow(c3 + 212, 76, c4 - 4, 86))
        g.append(arrow(c3 + 212, 288, c4 - 4, 238))
        g.append(f'<path d="M{c4 + 105} 344 C {c4 + 105} 625, {c1 + 105} 625, {c1 + 105} 400" class="ar dash" '
                 f'marker-end="url(#ah)"/><text x="500" y="588" class="bs" text-anchor="middle">Replies to win-back '
                 f'campaigns come back in as New Leads (A22)</text>')
        svg = (f'<svg viewBox="0 0 1000 600" class="journey" role="img" aria-label="Customer journey">'
               f'<defs><marker id="ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">'
               f'<path d="M0 0 L10 5 L0 10 z" class="ah"/></marker></defs>{"".join(g)}</svg>')
        return f"""
<section class="page land">
  <h2>The customer journey</h2>
  <p class="lead">How a lead moves through the system, from the first call or form to a loyal, reviewing customer. The
  codes point to the automations described later in this guide.</p>
  {svg}
</section>"""

    def pipeline(self) -> str:
        runs, arrives = {}, {}
        for w in self.flows:
            code = self.code[w["id"]]
            for t in w.get("triggers") or []:
                for c in t.get("conditions") or []:
                    if c.get("field") == "opportunity.pipelineStageId":
                        runs.setdefault(c["value"], set()).add(code)
            for n in w["workflowData"]["templates"]:
                if n["type"] == "create_opportunity":
                    arrives.setdefault((n.get("attributes") or {}).get("pipeline_stage_id"), set()).add(code)
        num = lambda s: int(s[1:])  # noqa: E731
        fmt = lambda s: " ".join(f'<span class="cc">{c}</span>' for c in sorted(s, key=num)) or "—"  # noqa: E731
        rows = "".join(
            f'<tr><td class="st"><span class="dot"></span>{esc(s["name"])}</td><td>{esc(CFG["stages"].get(s["name"], ""))}</td>'
            f'<td>{fmt(runs.get(s["id"], set()))}</td><td>{fmt(arrives.get(s["id"], set()))}</td></tr>'
            for s in self.pipe["stages"])
        return f"""
<section class="page">
  <h2>Sales pipeline: “{esc(self.pipe['name'])}”</h2>
  <p class="lead">One card per opportunity. Your team drags cards between stages, and some automations move them for you
  (a reply moves a card to In Communication, silence moves it to Lost). Moving a card into a stage is also what starts
  the follow-ups, so the pipeline <i>is</i> the control panel.</p>
  <table class="pipe"><thead><tr><th>Stage</th><th>What it means</th><th>Starts</th><th>Cards arrive from</th></tr></thead>
  <tbody>{rows}</tbody></table>
  <p class="foot">“Starts” = automations that run when a card enters the stage. “Cards arrive from” = automations that put
  a card there on their own.</p>
</section>"""

    def funnel_pages(self) -> str:
        cards = []
        for f in CFG["funnels"]:
            live = next((x for x in self.funnels if x["name"].strip() == f["name"]), None)
            if not live:
                continue
            steps = sorted(live.get("steps") or [], key=lambda s: s.get("sequence", 0))
            legal = [s for s in steps if re.search(r"privacy|terms|term of use", s["name"], re.I)]
            main = [s for s in steps if s not in legal]
            flow = " → ".join(f'<span class="pg">{esc(s["name"].strip())}</span>' for s in main)
            if legal:
                flow += f' <span class="legal">+ {len(legal)} legal pages</span>'
            kind = "Website" if live.get("type") == "website" else "Funnel"
            img = SHOTS / f"{f['shot']}.jpg"
            img = img if img.exists() else SHOTS / f"{f['shot']}.png"
            shot = f'<img src="shots/{img.name}" alt="">' if img.exists() else '<div class="noshot"></div>'
            cards.append(f'<div class="fcard"><div class="shot">{shot}</div><div class="ftext"><div class="kind">{kind} · '
                         f'{len(steps)} pages</div><h3>{esc(f["label"])}</h3><p>{esc(f["about"])}</p>'
                         f'<div class="pflow">{flow}</div></div></div>')
        return f"""
<section class="page">
  <h2>Funnels and websites</h2>
  <p class="lead">Ready-made pages that capture leads straight into the pipeline. The screenshots show the template with
  sample details (“We Clean Pool”, placeholder phone and photos); in your account they show your name, logo, phone,
  prices and service area.</p>
  <div class="fgrid">{''.join(cards)}</div>
</section>"""

    def setup_pages(self) -> str:
        forms = "".join(f'<tr><td>{esc(n)}</td><td>{esc(CFG["forms"].get(n, ""))}</td></tr>' for n in sorted(
            self.forms.values(), key=lambda n: list(CFG["forms"]).index(n) if n in CFG["forms"] else 99))
        cals = "".join(f'<tr><td>{esc(c["name"])}</td><td>{c.get("slotDuration")} minutes · your team’s availability; '
                       f'booking link set in your custom values</td></tr>' for c in self.cals.values())
        cv = "".join(f'<tr><td>{esc(v["name"])}</td><td>{esc(CFG["custom_values"].get(v["name"], ""))}</td></tr>'
                     for v in sorted(self.cvs, key=lambda v: list(CFG["custom_values"]).index(v["name"])
                                     if v["name"] in CFG["custom_values"] else 99))
        cf = ", ".join(esc(c["name"]) for c in self.cfields)
        tags = " ".join(f"<span class=\"tg\">{esc(t['name'])}</span>" for t in sorted(self.tags, key=lambda t: t["name"]))
        return f"""
<section class="page">
  <h2>Forms, calendars and your details</h2>
  <h4>Forms</h4>
  <table class="kv"><tbody>{forms}</tbody></table>
  <h4>Booking calendars</h4>
  <table class="kv"><tbody>{cals}</tbody></table>
  <h4>Your business details (custom values)</h4>
  <p class="small">Set once, used everywhere: pages, messages and emails pick these up automatically. We fill them in for
  {esc(self.client)} during setup.</p>
  <table class="kv cv"><tbody>{cv}</tbody></table>
  <h4>Extra contact fields</h4>
  <p class="small">{cf}.</p>
  <h4>Tags used by the automations</h4>
  <p class="tags">{tags}</p>
</section>"""

    def phase_pages(self) -> str:
        out = []
        for i, p in enumerate(CFG["phases"], 1):
            flows = [w for w in self.ordered() if CFG["automations"][w["name"]]["phase"] == p["id"]]
            lst = "".join(f'<li><b>{CFG["automations"][w["name"]]["code"]}</b> {esc(CFG["automations"][w["name"]]["title"])}</li>'
                          for w in flows)
            out.append(f'<section class="phase"><div class="phase-head"><div class="pn">{i}</div><div><h2>{esc(p["title"])}</h2>'
                       f'<p>{esc(p["intro"])}</p><ul class="plist">{lst}</ul></div></div>')
            out.extend(self.automation(w) for w in flows)
            out.append("</section>")
        return "".join(out)

    def index_page(self) -> str:
        rows = "".join(f'<tr><td class="c">{m["code"]}</td><td>{m["to"]}</td><td>{m["channel"]}</td><td>{m["auto"]}</td>'
                       f'<td>{chips(m["subject"] or m["first"])}</td></tr>' for m in self.messages)
        return f"""
<section class="page">
  <h2>Message index</h2>
  <p class="lead">Every message in the system, in the order it appears in this guide.</p>
  <table class="idx msgs"><thead><tr><th></th><th>To</th><th>How</th><th>In</th><th>Subject or first words</th></tr></thead>
  <tbody>{rows}</tbody></table>
</section>"""

    def next_steps(self) -> str:
        steps = [("Read through and mark it up", "Note anything you'd like changed: wording (M codes), timing, or which "
                  "automations are on (A codes). A list or a marked-up PDF both work."),
                 ("Send your notes to Ed", "We review them with you and confirm what changes before anything is touched."),
                 ("We set it up in your account", "Your business name, phone numbers, Google review link, logo, prices "
                  "and service area go into the system, together with your changes."),
                 ("We test before go-live", "Every automation is tested end to end on our side first, so nothing reaches a "
                  "customer until it's right.")]
        items = "".join(f'<div class="ns"><div class="nn">{i}</div><div><h3>{esc(t)}</h3><p>{esc(d)}</p></div></div>'
                        for i, (t, d) in enumerate(steps, 1))
        return f'<section class="page"><h2>Next steps</h2><div class="nsteps">{items}</div></section>'

    def build(self) -> str:
        phases = self.phase_pages()  # numbers the messages
        body = (self.cover() + self.glance() + self.journey() + self.pipeline() + self.funnel_pages()
                + phases + self.setup_pages() + self.index_page() + self.next_steps())
        css = (ROOT / "scripts" / "snapshot_guide.css").read_text()
        return (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><title>{esc(CFG["title"])}</title>'
                f'<link href="https://fonts.googleapis.com/css2?family=Noto+Color+Emoji&display=swap" rel="stylesheet">'
                f'<style>{css}</style></head><body>{body}</body></html>')


def take_shots() -> None:
    load_dotenv()
    from cli_anything.gohighlevel.utils.agency import SERVICES, Agency
    a = Agency()
    loc = json.loads((MASTER / "location.json").read_text())["id"]
    (MASTER / "funnels.json").write_text(json.dumps(a.call("GET", SERVICES, f"/funnels/funnel/list?locationId={loc}")))
    SHOTS.mkdir(parents=True, exist_ok=True)
    for f in CFG["funnels"]:
        png = SHOTS / f"{f['shot']}.png"
        subprocess.run([CHROMIUM, "--headless=new", "--no-sandbox", "--disable-gpu", "--hide-scrollbars",
                        "--window-size=1280,1700", "--virtual-time-budget=20000", f"--screenshot={png}",
                        f"https://app.gohighlevel.com/v2/preview/{f['shot']}"], capture_output=True, timeout=120)
        print(f"  {f['label']}: {png.stat().st_size // 1024} KB")


def thumbs() -> None:
    try:
        from PIL import Image
    except ImportError:
        return  # PNGs are used as they are
    for png in SHOTS.glob("*.png"):
        jpg = png.with_suffix(".jpg")
        if not jpg.exists() or jpg.stat().st_mtime < png.stat().st_mtime:
            im = Image.open(png).convert("RGB")
            im.crop((0, 0, im.width, min(im.height, 1200))).resize((900, int(900 * min(im.height, 1200) / im.width))).save(
                jpg, quality=82)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--for", dest="client", required=True, help="client name on the cover")
    parser.add_argument("--shots", action="store_true", help="refresh funnels.json and the page screenshots first")
    args = parser.parse_args()
    if args.shots:
        take_shots()
    thumbs()
    OUT.mkdir(parents=True, exist_ok=True)
    g = Guide(args.client)
    page = OUT / f"{slugify(args.client)}.html"
    page.write_text(g.build())
    pdf = OUT / f"Pool Profits CRM Overview - {args.client}.pdf"
    subprocess.run([CHROMIUM, "--headless=new", "--no-sandbox", "--disable-gpu", "--no-pdf-header-footer",
                    "--virtual-time-budget=15000", f"--print-to-pdf={pdf}", page.as_uri()], capture_output=True, timeout=180)
    print(f"{len(g.flows)} automações, {len(g.messages)} mensagens → {pdf} ({pdf.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
