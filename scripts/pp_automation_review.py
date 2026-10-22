#!/usr/bin/env python3
"""Client-facing review of the automations LIVE in one sub-account (Frank, 22/10: Erik at Ekahi approves what runs
today before anything changes). Same look as pp_snapshot_guide.py, built from the account's own dump.

    ./.venv/bin/python scripts/pp_dump.py --only "Ekahi"            # fresh dump first
    ./.venv/bin/python scripts/pp_automation_review.py ekahi-solutions-llc

Reads dump/<slug>/, config/snapshot_guide.json (phases, defaults) and config/review/<slug>.json (client name, what each
automation does in THIS account, custom flows, timeline scenarios, what we fixed, decisions to approve). Codes: A1…
for the active automations by phase, then the ones that are off; M1… for every message. Business details show the
account's real values (links clickable); contact fields stay as grey chips. On top of the snapshot guide, each
automation says what a reply does and where the contact goes next, and the timelines simulate, from the dump, what
one contact receives day by day. Writes reports/automation-review/<slug>.html and .pdf (gitignored).
"""
from __future__ import annotations

import argparse
import heapq
import json
import re
import subprocess
import sys

import pp_snapshot_guide as sg
from _common import DUMP, ROOT
from pp_snapshot_guide import CFG, CHROMIUM, Guide, chips, esc, plural, window_text

OUT = ROOT / "reports" / "automation-review"
PHASES = [p["id"] for p in CFG["phases"]]
MINUTES = {"minutes": 1, "minute": 1, "hours": 60, "hour": 60, "days": 1440, "day": 1440}
CSS = """
@page { @bottom-left { content: "Pool Profits · Automation review · %s"; } }
.pill.off { background: #f1f5f9; color: #475569; }
.cv { color: #0e7490; font-weight: 600; text-decoration: none; border-bottom: 1px dotted #0891b2; }
a.cv { white-space: nowrap; }
.after { margin: 8pt 0 2pt; display: grid; grid-template-columns: 1.05in 1fr; gap: 3pt 8pt; font-size: 8.6pt;
         background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6pt; padding: 6pt 10pt; break-inside: avoid; }
.after .k { font-size: 7.4pt; text-transform: uppercase; letter-spacing: .06em; font-weight: 700; color: #0e7490;
            padding-top: 1pt; }
table.glance td.st { white-space: nowrap; font-weight: 700; font-size: 7.6pt; }
table.glance td.st.on { color: #065f46; }
table.glance td.st.off { color: #94a3b8; }
table.glance td.tr { color: #475569; font-size: 8pt; }
.tl { margin: 4pt 0 16pt; break-inside: auto; }
.tl h3 { font-size: 11.5pt; margin: 12pt 0 2pt; break-after: avoid; }
.tl .small { break-after: avoid; }
table.time { font-size: 8.3pt; margin-top: 4pt; }
table.time td { padding: 2.5pt 6pt; }
table.time tr { break-inside: avoid; }
table.time td.t { white-space: nowrap; font-weight: 700; color: #0b2540; width: .95in; }
table.time td.a { width: .4in; }
table.time td.w { white-space: nowrap; color: #64748b; width: .75in; font-size: 7.8pt; }
table.time tr.sys td { color: #94a3b8; font-size: 7.8pt; }
table.time tr.sys td.t { color: #94a3b8; font-weight: 600; }
table.time tr.team td.x { color: #475569; }
.fixed { background: #ecfdf5; border: 1px solid #a7f3d0; border-radius: 8pt; padding: 8pt 13pt 6pt; margin: 8pt 0 12pt; }
.fixed h4 { margin: 0 0 3pt; color: #047857; }
.fixed ul { margin: 0; padding-left: 15pt; font-size: 8.7pt; }
.fixed li { margin-bottom: 2pt; }
.dec { border: 1px solid #e2e8f0; border-left: 4px solid #f59e0b; border-radius: 0 8pt 8pt 0; padding: 7pt 12pt;
       margin: 8pt 0; break-inside: avoid; }
.dec h3 { font-size: 10.5pt; margin-bottom: 3pt; }
.dec h3 .dn { color: #b45309; margin-right: 5pt; }
.dec p { font-size: 8.9pt; margin-bottom: 4pt; }
.dec .sg { font-size: 8.9pt; color: #065f46; }
.dec .sg b { color: #047857; }
.flow > .lbl, .starts .lbl { break-after: avoid; }
.offrow td:first-child { font-weight: 800; color: #94a3b8; }
"""


class Review(Guide):
    def __init__(self, slug: str):
        self.slug = slug
        self.src = DUMP / slug
        self.acc = json.loads((ROOT / "config" / "review" / f"{slug}.json").read_text())
        super().__init__(self.acc["client"], self.src)
        self.loc = json.loads((self.src / "location.json").read_text())
        sg.FILL.clear()
        sg.FILL.update(self.values())
        self.msg_ref: dict[tuple[str, str], str] = {}  # (workflow, step) → M code
        self.raw: dict[str, str] = {}  # M code → raw text (for {N:…})

    # ── setup ──────────────────────────────────────────────────────────────

    def info(self, w: dict) -> dict:
        return {**CFG["automations"].get(w["name"], {}), **self.acc["automations"].get(w["name"], {})}

    def number(self) -> dict[str, str]:
        missing = [w["name"] for w in self.flows if not {"phase", "title"} <= set(self.info(w)) or
                   not (self.info(w).get("purpose") or self.info(w).get("off_note"))]
        if missing:
            sys.exit(f"sem descrição em config/review/{self.slug}.json: {missing}")

        def key(w):
            c = self.info(w)
            like = re.match(r"A(\d+)(\w*)", c.get("like") or c.get("code") or "A99")
            return (w["status"] != "published", PHASES.index(c["phase"]), int(like.group(1)), like.group(2), w["name"])
        self.order = sorted(self.flows, key=key)
        return {w["id"]: f"A{i}" for i, w in enumerate(self.order, 1)}

    def values(self) -> dict[str, str]:
        out = {}
        for c in self.cvs:
            m = re.search(r"custom_values\.(\w+)", c.get("fieldKey") or "")
            if m and (c.get("value") or "").strip() and str(c["value"]).lower() not in ("null", "none"):
                out[f"custom_values.{m.group(1)}"] = c["value"].strip()
        out["location.name"] = self.loc.get("name", "")
        return out

    def who(self, ref) -> str:
        name = super().who(ref)
        if name in sg.RECIPIENT.values() and len(self.users) == 1:
            return f"{self.owner()} (the contact's owner)"
        return name

    def active(self) -> list[dict]:
        return [w for w in self.order if w["status"] == "published"]

    # ── messages ───────────────────────────────────────────────────────────

    def message(self, n: dict) -> str:
        before = len(self.messages)
        out = super().message(n)
        if len(self.messages) > before:
            code = self.messages[-1]["code"]
            self.msg_ref[(self.cur["name"], n["name"])] = code
            a = n.get("attributes") or {}
            s = self.snip.get(a.get("template_id")) or {}
            body = (s.get("template") or {}).get("body") if isinstance(s.get("template"), dict) else None
            self.raw[code] = json.dumps(a) + (body or "")
        return out

    def _message(self, n: dict) -> str:
        a = n.get("attributes") or {}
        if n["type"] != "review_request":
            return super()._message(n)
        channel = "Text" if a.get("review_type") == "sms" else "Email"
        link = a.get("overrideReviewLink") or sg.FILL.get("custom_values.google_review_link", "")
        code = self.new_msg("Customer", channel, "Google review request", "Review request with your Google link")
        target = f'<a class="cv" href="{esc(link)}">your Google review page</a>' if link else "your Google review page"
        return (f'<div class="msg review"><div class="mh"><span class="mcode">{code}</span>Google review request by '
                f'{channel.lower()}</div><div class="note"><p>Sent through the Reputation tool with a link to {target}. '
                f'The wording is the one set in Settings → Reputation; we can customize it there.</p></div></div>')

    # ── per automation ─────────────────────────────────────────────────────

    def nodes(self, w: dict) -> dict[str, dict]:
        return {n["id"]: n for n in w["workflowData"]["templates"]}

    def root(self, w: dict) -> str | None:
        nodes = self.nodes(w)
        pointed = {x for n in nodes.values() for x in (n.get("next") if isinstance(n.get("next"), list)
                                                       else [n.get("next")]) if x}
        return next((n["id"] for n in sorted(nodes.values(), key=lambda n: n.get("order", 0)) if n["id"] not in pointed),
                    None)

    def starts(self, kind: str, value: str, exclude: dict | None = None) -> list[dict]:
        """Active automations a new tag or a card moving to a stage sets off."""
        out = []
        for w in self.active():
            for t in w.get("triggers") or []:
                if t.get("deleted") or t.get("active") is False or w is exclude:
                    continue
                conds = t.get("conditions") or []
                vals = [v for c in conds for v in (c.get("value") if isinstance(c.get("value"), list) else [c.get("value")])]
                if kind == "tag" and t["type"] == "contact_tag" and value in vals and not any(
                        c.get("operator") == "index-of-false" and c.get("value") == value for c in conds):
                    out.append(w)
                elif kind == "stage" and t["type"] == "pipeline_stage_updated" and any(
                        c.get("field") == "opportunity.pipelineStageId" and c.get("value") == value for c in conds):
                    out.append(w)
        return list({id(w): w for w in out}.values())

    def trigger_stages(self, w: dict) -> set[str]:
        return {c.get("value") for t in w.get("triggers") or [] for c in t.get("conditions") or []
                if c.get("field") == "opportunity.pipelineStageId"}

    def handoffs(self, w: dict) -> list[str]:
        """Where the card goes and which automations this one sets off, from every path of the flow."""
        out, seen = [], set()
        for n in sorted(w["workflowData"]["templates"], key=lambda n: n.get("order", 0)):
            a = n.get("attributes") or {}
            if n["type"] == "create_opportunity":
                sid = a.get("pipeline_stage_id")
                if sid in self.trigger_stages(w) or ("stage", sid) in seen:
                    continue
                seen.add(("stage", sid))
                nxt = self.starts("stage", sid, exclude=w)
                out.append(f"Card → {self.stage.get(sid, '?')}" + (f" (starts {self.codes(nxt)})" if nxt else ""))
            elif n["type"] == "add_contact_tag":
                for tag in a.get("tags") or []:
                    nxt = self.starts("tag", tag, exclude=w)
                    if nxt and ("tag", tag) not in seen:
                        seen.add(("tag", tag))
                        out.append(f"Tag “{tag}” (starts {self.codes(nxt)})")
            elif n["type"] == "dnd_contact":
                out.append("Do Not Disturb on")
        return out

    def codes(self, flows: list[dict]) -> str:
        return ", ".join(f"{self.code[w['id']]} {self.info(w)['title']}" for w in flows)

    def has_fork(self, items: list) -> bool:
        return any(it[0] == "fork" or (it[0] == "branch" and any(self.has_fork(sub) for _, sub in it[2])) for it in items)

    def reply_note(self, w: dict, info: dict, sent: int, items: list) -> str | None:
        if info.get("reply_note"):
            return info["reply_note"]
        if w.get("stopOnResponse"):
            return "Any reply stops this automation."
        if self.has_fork(items):
            return ("A reply ends this automation at that point (the texts after it are not sent) and does what the "
                    "green boxes above show. Replies land in your Conversations inbox.")
        if sent > 1:
            return "A reply does not stop it: the remaining messages still go out. Replies land in your Conversations inbox."
        if sent == 1:
            return "Replies land in your Conversations inbox; nothing else changes."
        return None

    def automation(self, w: dict) -> str:
        c = self.info(w)
        code = self.code[w["id"]]
        self.cur = {**c, "code": code, "name": w["name"]}
        before = len(self.messages)
        items = []
        if c.get("flow"):
            flow = self.custom_flow(w, c["flow"])
        else:
            items = self.walk(self.nodes(w), self.root(w))
            flow = self.render(items, c.get("branch_labels"))
        sent = sum(1 for m in self.messages[before:] if m["to"] == "Customer")
        trig = [c["trigger_note"]] if c.get("trigger_note") else \
            list(dict.fromkeys(self.trigger_text(t) for t in w.get("triggers") or [] if not t.get("deleted")))
        rows = []
        note = self.reply_note(w, c, sent, items)
        if note:
            rows.append(("If they reply", esc(note)))
        nxt = self.handoffs(w)
        rows.append(("Then", " · ".join(esc(x) for x in nxt) if nxt else "Nothing else: the automation ends after its "
                     "last step."))
        after = "".join(f'<div class="k">{k}</div><div>{v}</div>' for k, v in rows)
        folder = (w.get("_folder") or "").split(" ", 1)[-1]
        return f"""
<section class="auto" id="{code}">
  <div class="auto-head"><span class="code">{code}</span><h3>{esc(c['title'])}</h3><span class="pill on">ACTIVE</span></div>
  <div class="meta">In the CRM: “{esc(w['name'])}” · folder “{esc(folder)}”</div>
  <p class="purpose">{esc(c['purpose'])}</p>
  <div class="starts"><span class="lbl">Starts when</span><ul>{''.join(f'<li>{esc(t)}</li>' for t in trig)}</ul></div>
  <div class="flow"><div class="lbl">What happens</div>{flow}</div>
  <div class="after">{after}</div>
</section>"""

    # ── timelines ──────────────────────────────────────────────────────────

    @staticmethod
    def when(t: float) -> str:
        if t < 0.01:
            return "Right away"
        if t < 1:
            return f"+{round(t * 60)} sec"
        if t < 60:
            return f"+{t:g} min"
        if t < 1440:
            return f"+{plural(round(t / 60, 1), 'hour')}"
        return f"Day {round(t / 1440)}"

    def simulate(self, sc: dict) -> list[dict]:
        """What one contact who never replies receives: every active automation the scenario sets off, step by step in
        time order (reply waits run to their timeout; if/else takes its first branch; each automation runs once)."""
        heap, seq, ran, tags, out = [], 0, set(), set(), []
        now = {"stage": None}

        def launch(w, t):
            nonlocal seq
            if w["id"] in ran:
                return
            ran.add(w["id"])
            seq += 1
            heapq.heappush(heap, (t, seq, w["id"], self.root(w), ""))

        flows = {w["id"]: w for w in self.active()}
        for name in sc.get("workflows") or []:
            launch(self.by_name[name], 0)
        if sc.get("stage"):
            sid = now["stage"] = next(i for i, n in self.stage.items() if n == sc["stage"])
            for w in self.starts("stage", sid):
                launch(w, 0)
        for x in sc.get("extra") or []:
            out.append({"t": x["t"], "a": "", "m": "", "kind": "cust", "text": x["text"], "w": ""})
        while heap:
            t, _, wid, nid, win = heapq.heappop(heap)
            w = flows[wid]
            nodes = self.nodes(w)
            n = nodes.get(nid)
            if not n:
                continue
            a, ty, nxt = n.get("attributes") or {}, n["type"], n.get("next")
            code = self.code[wid]

            def go(target, t2=t, note=win):
                nonlocal seq
                if isinstance(target, str) and target in nodes:
                    seq += 1
                    heapq.heappush(heap, (t2, seq, wid, target, note))

            if ty == "wait":
                sa = a.get("startAfter") or {}
                dur = float(sa.get("value") or 0) * MINUTES.get(sa.get("type", "minutes"), 1)
                if isinstance(nxt, list):
                    timeout = next((nodes[x] for x in nxt if x in nodes and
                                    (nodes[x].get("attributes") or {}).get("type") == "wait_timeout"), None)
                    go(timeout and timeout.get("next"), t + dur)
                elif a.get("type") == "time":
                    go(nxt, t + dur, window_text(a.get("window")).replace("sent ", ""))
                continue  # appointment waits: no appointment in these scenarios
            if ty == "if_else" and isinstance(nxt, list):
                go(next((nodes[b].get("next") for b in nxt if b in nodes and nodes[b].get("next")), None))
                continue
            if ty in ("if_else", "transition"):
                go(nxt)
                continue
            if ty == "goto":
                continue
            mcode = self.node_code.get(nid, "")
            msg = next((m for m in self.messages if m["code"] == mcode), None)
            if msg:
                out.append({"t": t, "a": code, "m": mcode, "kind": "cust" if msg["to"] == "Customer" else "team",
                            "text": f"{msg['channel']} to {'the customer' if msg['to'] == 'Customer' else self.owner()}: "
                                    + (msg["subject"] or msg["first"]), "w": win})
            elif ty == "create_opportunity" and a.get("pipeline_stage_id") != now["stage"]:
                sid = now["stage"] = a.get("pipeline_stage_id")
                started = [x for x in self.starts("stage", sid) if x["id"] not in ran]
                out.append({"t": t, "a": code, "m": "", "kind": "sys", "w": "",
                            "text": f"Card moves to {self.stage.get(sid, '?')}" +
                                    (f": starts {', '.join(self.code[x['id']] for x in started)}" if started else "")})
                for x in started:
                    launch(x, t)
            elif ty in ("add_contact_tag", "remove_contact_tag"):
                for tag in a.get("tags") or []:
                    if ty == "remove_contact_tag":
                        tags.discard(tag)
                        continue
                    if tag in tags:
                        continue
                    tags.add(tag)
                    started = [x for x in self.starts("tag", tag) if x["id"] not in ran]
                    if started:
                        out.append({"t": t, "a": code, "m": "", "kind": "sys", "w": "",
                                    "text": f"Tagged “{tag}”: starts {', '.join(self.code[x['id']] for x in started)}"})
                    for x in started:
                        launch(x, t)
            elif ty == "dnd_contact":
                out.append({"t": t, "a": code, "m": "", "kind": "sys", "text": "Do Not Disturb turned on", "w": ""})
            elif ty == "google_adword":
                out.append({"t": t, "a": code, "m": "", "kind": "sys", "text": "Reported to Google Ads", "w": ""})
            go(nxt if isinstance(nxt, str) else None)
        return sorted(out, key=lambda e: e["t"])

    def owner(self) -> str:
        return next(iter(self.users.values())) if len(self.users) == 1 else "your team"

    def timelines(self) -> str:
        blocks = []
        for sc in self.acc.get("scenarios") or []:
            ev = self.simulate(sc)
            cust = sum(1 for e in ev if e["kind"] == "cust" and e["m"])
            rows = []
            for e in ev:
                auto = f'<span class="cc">{e["a"]}</span>' if e["a"] else ""
                mcode = f'<b>{e["m"]}</b> ' if e["m"] else ""
                rows.append(f'<tr class="{e["kind"]}"><td class="t">{self.when(e["t"])}</td><td class="a">{auto}</td>'
                            f'<td class="x">{mcode}{chips(e["text"])}</td><td class="w">{esc(e["w"])}</td></tr>')
            days = round(max((e["t"] for e in ev), default=0) / 1440)
            blocks.append(f'<div class="tl"><h3>{esc(sc["title"])}</h3><p class="small">{esc(sc["intro"])} '
                          f'{cust} automated messages to them over {days} days.</p>'
                          f'<table class="time"><tbody>{"".join(rows)}</tbody></table></div>')
        return f"""
<section class="page">
  <h2>What one contact receives</h2>
  <p class="lead">Built from the live automations: everything that goes out, in order, when someone never replies.
  A reply at any point ends the sequence that sent the last text (see each automation). Grey lines are the system moving
  the card or tagging the contact, which is what starts the next automation.</p>
  {''.join(blocks)}
</section>"""

    # ── review pages ───────────────────────────────────────────────────────

    def refs(self, text: str) -> str:
        """{A:workflow} {M:workflow/step} {N:custom value key} → codes, in already-escaped text."""
        def a(m):
            w = self.by_name.get(m.group(1))
            return f'<b>{self.code[w["id"]]}</b> ({esc(self.info(w)["title"])})' if w else esc(m.group(1))

        def msg(m):
            wf, step = m.group(1).rsplit("/", 1)
            return f"<b>{self.msg_ref.get((wf, step), '?')}</b>"

        def n(m):
            return str(sum(1 for raw in self.raw.values() if f"custom_values.{m.group(1)}" in raw))
        text = re.sub(r"\{A:([^}]+)\}", a, esc(text))
        text = re.sub(r"\{M:([^}]+)\}", msg, text)
        return re.sub(r"\{N:([^}]+)\}", n, text)

    def cover(self) -> str:
        return super().cover().replace("CRM system overview", "Automation review").replace(
            esc(CFG["title"]), esc(self.acc["title"])).replace(esc(CFG["subtitle"]), esc(self.acc["subtitle"]))

    def glance(self) -> str:
        act = self.active()
        cust = sum(1 for m in self.messages if m["to"] == "Customer")
        stats = [(len(act), "active automations", f"+ {len(self.flows) - len(act)} built but off"),
                 (cust, "customer messages", "texts, emails and review requests"),
                 (len(self.messages) - cust, "alerts & tasks", f"for {self.owner()}"),
                 (len(self.pipe["stages"]), "pipeline stages", f"“{self.pipe['name']}”")]
        rows = []
        for w in self.order:
            c, on = self.info(w), w["status"] == "published"
            trig = "; ".join(dict.fromkeys(self.trigger_text(t) for t in w.get("triggers") or [] if not t.get("deleted")))
            rows.append(f'<tr><td class="c">{self.code[w["id"]]}</td><td>{esc(c["title"])}</td><td class="tr">'
                        f'{esc(c.get("trigger_note") or trig)}</td><td class="st {"on" if on else "off"}">'
                        f'{"ACTIVE" if on else "OFF"}</td></tr>')
        return f"""
<section class="page">
  <h2>At a glance</h2>
  <p class="lead">Everything that runs automatically in your CRM today, pulled straight from the system: what starts each
  automation, the timing, the exact wording (your own, like the Aloha welcome text, as it is), what happens when someone
  replies, and where the contact goes next.</p>
  <div class="stats" style="grid-template-columns: repeat(4, 1fr)">{''.join(f'<div class="stat"><div class="n">{n}</div><div class="t">{esc(t)}</div><div class="s">{esc(s)}</div></div>' for n, t, s in stats)}</div>
  <div class="howto">
    <h4>How to approve or ask for changes</h4>
    <p>Every automation has a code (<b>A1</b>–<b>A{len(self.flows)}</b>) and every message has one too
    (<b>M1</b>–<b>M{len(self.messages)}</b>). Reference the code, for example “<b>M3</b>: say Mahalo at the end” or
    “<b>A6</b>: wait 2 days before the first text”. Grey chips like <span class="mf">First Name</span> are filled in for
    each customer; <span class="cv">teal text</span> is your business detail as it is set today.</p>
  </div>
  <h4 class="idx-h">All automations</h4>
  <table class="idx glance"><thead><tr><th></th><th>Automation</th><th>Starts when</th><th>Status</th></tr></thead>
  <tbody>{''.join(rows)}</tbody></table>
</section>"""

    def decisions(self) -> str:
        fixed = "".join(f"<li>{esc(x)}</li>" for x in self.acc.get("fixed") or [])
        decs = "".join(
            f'<div class="dec"><h3><span class="dn">D{i}</span>{esc(d["title"])}</h3><p>{self.refs(d["text"])}</p>'
            f'<div class="sg"><b>Our suggestion:</b> {self.refs(d["suggest"])}</div></div>'
            for i, d in enumerate(self.acc.get("decisions") or [], 1))
        return f"""
<section class="page">
  <h2>Things to decide</h2>
  <p class="lead">While reviewing we found a few places where the automations don't do what you'd expect. Nothing here
  changes until you say so: answer each one with a yes, a no, or your own idea (D1, D2…).</p>
  {decs}
  <div class="fixed"><h4>Already fixed (basic errors, nothing changed in how things work)</h4><ul>{fixed}</ul></div>
</section>"""

    def pipeline(self) -> str:
        saved, flows = CFG["stages"], self.flows
        CFG["stages"], self.flows = {**saved, **self.acc.get("stages", {})}, self.active()  # what runs today only
        try:
            out = super().pipeline()
        finally:
            CFG["stages"], self.flows = saved, flows
        return out.replace("(a reply moves a card to In Communication, silence moves it to Lost)",
                           "(a reply moves a card to In Communication, unanswered follow-ups move it to Lost)")

    def phase_pages(self) -> str:
        out = []
        for i, p in enumerate([p for p in CFG["phases"] if any(self.info(w)["phase"] == p["id"] for w in self.active())], 1):
            p = {**p, **self.acc.get("phases", {}).get(p["id"], {})}
            flows = [w for w in self.active() if self.info(w)["phase"] == p["id"]]
            lst = "".join(f'<li><b>{self.code[w["id"]]}</b> {esc(self.info(w)["title"])}</li>' for w in flows)
            out.append(f'<section class="phase"><div class="phase-head"><div class="pn">{i}</div><div><h2>{esc(p["title"])}</h2>'
                       f'<p>{esc(p["intro"])}</p><ul class="plist">{lst}</ul></div></div>')
            out.extend(self.automation(w) for w in flows)
            out.append("</section>")
        return "".join(out)

    def off_page(self) -> str:
        rows = "".join(f'<tr class="offrow"><td>{self.code[w["id"]]}</td><td><b>{esc(self.info(w)["title"])}</b><br>'
                       f'<span class="small">In the CRM: “{esc(w["name"])}”</span></td><td>{esc(self.info(w)["off_note"])}'
                       f'</td></tr>' for w in self.order if w["status"] != "published")
        return f"""
<section class="page">
  <h2>Built but off</h2>
  <p class="lead">These are in your CRM but switched off, so they send nothing. Tell us if you want any of them on.</p>
  <table class="idx"><thead><tr><th></th><th>Automation</th><th>Why it's off</th></tr></thead><tbody>{rows}</tbody></table>
</section>"""

    def next_steps(self) -> str:
        steps = [("Read through and mark it up", "Approve what's right as it is, and note anything you'd like changed by "
                  "its code: wording (M codes) or timing and on/off (A codes)."),
                 ("Answer the decisions", "A yes, a no or your own idea for D1–D" + str(len(self.acc.get("decisions") or []))
                  + " is enough."),
                 (f"Send your notes to {self.acc.get('notes_to', 'us')}", "We confirm with you exactly what changes "
                  "before anything is touched."),
                 ("We make the changes and test them", "Every change is tested end to end on our side first, so nothing "
                  "reaches a customer until it's right.")]
        items = "".join(f'<div class="ns"><div class="nn">{i}</div><div><h3>{esc(t)}</h3><p>{esc(d)}</p></div></div>'
                        for i, (t, d) in enumerate(steps, 1))
        return f'<section class="page"><h2>Next steps</h2><div class="nsteps">{items}</div></section>'

    def build(self) -> str:
        phases = self.phase_pages()  # numbers the messages
        body = (self.cover() + self.glance() + self.timelines() + self.decisions() + self.pipeline() + phases
                + self.off_page() + self.index_page() + self.next_steps())
        css = (ROOT / "scripts" / "snapshot_guide.css").read_text() + CSS % self.acc["client"].replace('"', "")
        return (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><title>{esc(self.acc["title"])}</title>'
                f'<link href="https://fonts.googleapis.com/css2?family=Noto+Color+Emoji&display=swap" rel="stylesheet">'
                f'<style>{css}</style></head><body>{body}</body></html>')


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("slug", help="dump/<slug> (pp_dump.py first); needs config/review/<slug>.json")
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    r = Review(args.slug)
    page = OUT / f"{args.slug}.html"
    page.write_text(r.build())
    pdf = OUT / f"Pool Profits Automation Review - {r.acc['client']}.pdf"
    subprocess.run([CHROMIUM, "--headless=new", "--no-sandbox", "--disable-gpu", "--no-pdf-header-footer",
                    "--virtual-time-budget=15000", f"--print-to-pdf={pdf}", page.as_uri()], capture_output=True, timeout=180)
    act = len(r.active())
    print(f"{act} ativas + {len(r.flows) - act} off, {len(r.messages)} mensagens → {pdf} ({pdf.stat().st_size // 1024} KB)")
    for sc in r.acc.get("scenarios") or []:
        ev = r.simulate(sc)
        print(f"  {sc['title']}: " + " | ".join(f"{r.when(e['t'])} {e['m'] or e['text'][:30]}" for e in ev))
    return 0


if __name__ == "__main__":
    sys.exit(main())
