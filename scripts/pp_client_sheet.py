#!/usr/bin/env python3
"""Short, client-friendly PDF of the automations (Frank, 06/11: Erik at Ekahi was overwhelmed by the full automation
review, so the client gets a few pages he can answer quickly: "M4 looks good", "change M7 to …").

    GHL_AGENCY=burchtech python3 scripts/pp_dump.py --only "Pool Keepers"          # fresh dump first
    python3 scripts/pp_client_sheet.py the-pool-keepers --agency-dir burchtech
    python3 scripts/pp_client_sheet.py ekahi-solutions-llc                          # dump/<slug> of Pool Profits

Pages: (1) the journey in plain words; (2…) one card per message the customer receives — when it goes out (worked
out from the flow: waits, "if they haven't replied", which kind of customer), the exact text with the account's own
values filled in and contact fields as [First name], and two tick boxes; (last) what goes to the team, what is built
but kept off, the client's own automations already running and 3–6 yes/no questions.

Reads dump/[<agency-dir>/]<slug>/ and config/client_sheet/<slug>.json (which automations go on and in which stage,
the plain-English event that starts each one, branch labels, notes, decisions). Every workflow of the dump must be
listed in the config (automations / off / yours / not_shown) so nothing new slips by unexplained. Offline: never
calls GHL. Writes reports/client-sheet/<slug>.html and .pdf (gitignored).
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

from _common import DUMP, ROOT
from pp_snapshot_guide import CHROMIUM, lines, window_text

OUT = ROOT / "reports" / "client-sheet"
MERGE_RE = re.compile(r"\{\{\s*([^}]+?)\s*\}\}")
MINUTES = {"minute": 1, "minutes": 1, "hour": 60, "hours": 60, "day": 1440, "days": 1440, "week": 10080, "weeks": 10080}
CONTACT = {"first_name": "First name", "name": "Full name", "full_name": "Full name", "last_name": "Last name",
           "phone": "Phone", "phone_raw": "Phone", "email": "Email", "address1": "Address", "full_address": "Address",
           "city": "City", "postal_code": "ZIP", "nps_score": "Rating", "nps_message": "Rating comment"}
LINKS = {"nps_survey_link": "your rating page", "google_review_link": "your Google review page",
         "booking_link": "your booking page", "calendar_link": "your booking page", "privacy_policy": "privacy policy",
         "terms_of_use": "terms of use", "logo_url": "logo"}
MSG_TYPES = {"sms", "email", "review_request", "internal_notification", "task-notification"}


def esc(s) -> str:
    return html.escape(str(s or ""), quote=True)


def mins_text(m: float) -> str:
    m = int(round(m))
    if m < 1:
        return "a few seconds"
    parts = []
    for unit, size in (("day", 1440), ("hour", 60), ("minute", 1)):
        if m >= size:
            n, m = divmod(m, size)
            parts.append(f"{n} {unit}{'' if n == 1 else 's'}")
    return " and ".join(parts[:2])


class Sheet:
    def __init__(self, slug: str, src: Path, cfg: dict):
        self.slug, self.src, self.cfg = slug, src, cfg
        load = lambda name, default=None: json.loads((src / name).read_text()) if (src / name).exists() else default  # noqa: E731
        self.flows = [json.loads(f.read_text()) for f in sorted((src / "workflows").glob("*.json")) if f.name != "_index.json"]
        self.flows = [w for w in self.flows if isinstance(w, dict) and w.get("workflowData")]
        self.by_name = {w["name"]: w for w in self.flows}
        self.snip = {s["_id"]: s for s in load("snippets.json", [])}
        self.load_account(src)
        self.cards: list[dict] = []  # customer messages, numbered
        self.team: list[dict] = []
        self.missing: set[str] = set()

    def load_account(self, src: Path) -> None:
        """Location, users and custom values used to fill the texts (pp_crm_guide.py: the client's account while
        the flows come from the master)."""
        load = lambda name, default=None: json.loads((src / name).read_text()) if (src / name).exists() else default  # noqa: E731
        loc = load("location.json", {})
        self.loc = loc.get("location", loc)
        self.users = {u["id"]: u.get("name") or f"{u.get('firstName', '')} {u.get('lastName', '')}".strip()
                      for u in load("users.json", []) if not u.get("deleted")}
        self.values: dict[str, str] = {"location.name": self.loc.get("name", "")}
        self.cv_names: dict[str, str] = {}
        for c in load("custom_values.json", []):
            m = re.search(r"custom_values\.(\w+)", c.get("fieldKey") or "")
            if m:
                self.cv_names[m.group(1)] = c.get("name") or m.group(1)
                v = str(c.get("value") or "").strip()
                if v and v.lower() not in ("null", "none"):
                    self.values[f"custom_values.{m.group(1)}"] = v

    # ── text ───────────────────────────────────────────────────────────────

    # how each piece is written out (HTML here; pp_crm_guide.py overrides them for plain text)
    def out_text(self, s: str) -> str:
        return esc(s)

    def out_link(self, label: str, url: str, field: str) -> str:
        return f'<a class="lk" href="{esc(url)}">{esc(label)}</a>'

    def out_value(self, val: str, field: str) -> str:
        return f'<span class="v">{esc(val)}</span>'

    def out_missing(self, name: str, field: str) -> str:
        return f'<span class="miss">[{esc(name)}: not set yet]</span>'

    def out_field(self, label: str) -> str:
        return f'<span class="mf">{esc(label)}</span>'

    def out_lines(self, parts: list[str]) -> str:
        return "".join(f"<p>{p}</p>" if p else '<p class="gap"></p>' for p in parts)

    def review_text(self, link: str) -> str:
        target = f'<a class="lk" href="{esc(link)}">your Google review page</a>' if link else "your Google review page"
        return (f"<p>A short request from your Google review tool with a link to {target}.</p>"
                '<p class="gap"></p><p class="dim">Its wording is set once in your review settings; '
                "tell me if you'd like it changed too.</p>")

    def fill(self, text: str) -> str:
        """One line of a message → HTML: business values filled in, contact fields as [chips]."""
        text = re.sub(r"(\{\{\s*custom_values\.\w+\s*\}\})\?\S+", r"\1", text or "")  # tracking query of a link
        out, pos = [], 0
        for m in MERGE_RE.finditer(text):
            out.append(self.out_text(text[pos:m.start()]))
            key, pos = m.group(1), m.end()
            group, _, field = key.partition(".")
            val = self.values.get(key)
            if group in ("custom_values", "location") and val:
                if re.match(r"https?://", val):
                    out.append(self.out_link(LINKS.get(field, "link"), val, field))
                else:
                    out.append(self.out_value(val, field))
            elif group == "custom_values":
                self.missing.add(self.cv_names.get(field, field))
                out.append(self.out_missing(self.cv_names.get(field, field), field))
            elif group == "contact":
                out.append(self.out_field(CONTACT.get(field, field.replace("_", " ").capitalize())))
            elif key.startswith("appointment."):
                out.append(self.out_field("Appointment date & time"))
            elif key.startswith("message."):
                out.append(self.out_field("Their message" if "body" in key else "Attachments"))
            else:
                out.append(self.out_field(field or key))
        out.append(self.out_text(text[pos:]))
        return "".join(out)

    def body(self, raw: str) -> str:
        return self.out_lines([self.fill(ln) if ln else "" for ln in lines(raw)])

    def first_line(self, raw: str, n: int = 75) -> str:
        s = " ".join(x for x in lines(raw) if x)
        if len(s) > n:
            s = re.sub(r"\{\{[^}]*$", "", s[:n].rsplit(" ", 1)[0]).rstrip(" ,.-:") + "…"
        return self.fill(s)

    def sms_body(self, a: dict) -> str:
        s = self.snip.get(a.get("template_id")) or {}
        t = s.get("template") if isinstance(s.get("template"), dict) else {}
        return (t or {}).get("body") or a.get("body") or ""

    def who(self, refs) -> str:
        refs = refs if isinstance(refs, list) else [refs]
        names = [self.users[r].split(" ")[0] for r in refs if r in self.users]
        if names:
            return " and ".join(names)
        if refs and refs[0] == "all":
            return "your whole team"
        return self.cfg.get("owner") or "the lead's owner"  # assign / contact.assigned_user: the contact's owner

    # ── flow → when ────────────────────────────────────────────────────────

    def walk(self, w: dict, info: dict) -> list[tuple[dict, list[dict]]]:
        """Message steps in flow order, each with every path (state) that reaches it."""
        nodes = {n["id"]: n for n in w["workflowData"]["templates"]}
        pointed = {x for n in nodes.values() for x in (n.get("next") if isinstance(n.get("next"), list) else [n.get("next")]) if x}
        roots = [n["id"] for n in sorted(nodes.values(), key=lambda n: n.get("order", 0)) if n["id"] not in pointed
                 and not n.get("parent") and n["type"] not in ("transition",)]
        trig_ids = {t.get("id") for t in w.get("triggers") or []}
        labels = info.get("branch_labels") or {}
        found: dict[str, list[dict]] = {}
        order: list[str] = []
        budget = [400]

        def branch_conds(ifnode: dict, bid: str) -> list[dict]:
            for b in (ifnode.get("attributes") or {}).get("branches") or []:
                if b.get("id") == bid:
                    return [c for s in b.get("segments") or [] for c in s.get("conditions") or []]
            return []

        def go(nid, st):
            while nid and nid in nodes and budget[0] > 0:
                budget[0] -= 1
                n = nodes[nid]
                a, ty, nxt = n.get("attributes") or {}, n["type"], n.get("next")
                if ty == "wait":
                    sa = a.get("startAfter") or {}
                    mins = float(sa.get("value") or 0) * MINUTES.get(sa.get("type") or "days", 1440)
                    if isinstance(nxt, list):
                        for t in (nodes[x] for x in nxt if x in nodes):
                            kind = (t.get("attributes") or {}).get("type")
                            if kind == "wait_reply":
                                go(t.get("next"), {**st, "conds": st["conds"] + ["if they reply"]})
                            elif kind == "wait_condition":
                                go(t.get("next"), {**st, "event": info.get("rating_event", "the condition is met"),
                                                   "delay": 0, "conds": [], "before": None})
                            elif kind == "wait_timeout":
                                cond = "if they haven't replied" if a.get("type") != "condition" else "if they haven't answered"
                                go(t.get("next"), {**st, "delay": st["delay"] + mins, "conds": st["conds"] + [cond]})
                        return
                    before = a.get("appointmentStartAfter") or {}
                    if a.get("type") == "appointment" or before.get("when") == "before":
                        v = int(before.get("value") or 0)
                        span = mins_text(v) if v else n["name"].lower().replace("wait ", "").replace(" before", "")
                        st = {**st, "before": f"{span} before the appointment"}
                    else:
                        st = {**st, "delay": st["delay"] + mins}
                    if window_text(a.get("window")):
                        st = {**st, "window": window_text(a.get("window"))}
                elif ty == "if_else" and isinstance(nxt, list):
                    picked = []
                    for bid in nxt:
                        b = nodes.get(bid)
                        if not b:
                            continue
                        conds = branch_conds(n, bid)
                        trig = [c.get("conditionValue") for c in conds if c.get("conditionType") == "trigger"]
                        if trig and st["trig"] and st["trig"] not in trig:
                            continue  # this path started from another trigger: the branch never matches
                        if (b.get("attributes") or {}).get("else") and st["trig"] and any(
                                st["trig"] in [c.get("conditionValue") for c in branch_conds(n, o)] for o in nxt if o != bid):
                            continue
                        picked.append((b, trig))
                    for b, trig in picked:
                        label = labels.get(b["name"], b["name"].lower())
                        if label is None:
                            continue
                        new = {**st, "conds": st["conds"] + ([label] if label else [])}
                        if trig and not st["trig"]:
                            new["trig"] = trig[0] if trig[0] in trig_ids else None
                        go(b.get("next"), new)
                    return
                elif ty == "goto":
                    nid = a.get("targetNodeId")
                    continue
                elif ty in MSG_TYPES:
                    if nid not in found:
                        order.append(nid)
                    found.setdefault(nid, []).append(dict(st))
                nid = nxt if isinstance(nxt, str) else None

        for r in roots:
            go(r, {"delay": 0, "conds": [], "window": None, "before": None, "trig": None, "event": None})
        return [(nodes[i], found[i]) for i in order]

    def when(self, info: dict, states: list[dict]) -> str:
        out = []
        for st in states:
            ev = st.get("event") or info.get("event") or "it starts"
            if st.get("before"):
                base = st["before"][0].upper() + st["before"][1:]
            elif st["delay"] < 1:
                base = f"Right after {ev}"
            else:
                base = f"{mins_text(st['delay'])} after {ev}"
                base = base[0].upper() + base[1:]
            conds = list(dict.fromkeys(st["conds"]))
            if conds:
                base += ", " + ", ".join(conds)
            if st.get("window") and st["delay"] >= 1:
                win = st["window"].replace("sent ", "").replace("every day, ", "").replace("Mon–Fri, ", "weekdays ")
                base += f" ({win})"
            if base not in out:
                out.append(base)
        return " · or ".join(out)

    # ── collect ────────────────────────────────────────────────────────────

    def collect(self) -> None:
        stages = [s["id"] for s in self.cfg["stages"]] + ["team"]
        autos = sorted(((name, info) for name, info in self.cfg["automations"].items() if name in self.by_name),
                       key=lambda x: stages.index(x[1]["stage"]))
        for name in self.cfg["automations"]:
            if name not in self.by_name:
                print(f"  ! no config/dump match for {name!r}", file=sys.stderr)
        for name, info in autos:
            w = self.by_name[name]
            steps = self.walk(w, info)
            skip = set()
            for i, (n, states) in enumerate(steps):
                if n["id"] in skip:
                    continue
                a, ty = n.get("attributes") or {}, n["type"]
                when = (info.get("when") or {}).get(n["name"]) or self.when(info, states)
                base = {"auto": name, "stage": info["stage"], "group": info.get("group"), "when": when,
                        "note": (info.get("notes") or {}).get(n["name"]), "step": n["name"]}
                if ty == "sms":
                    self.cards.append({**base, "channel": "Text", "html": self.body(self.sms_body(a))})
                elif ty == "email":
                    self.cards.append({**base, "channel": "Email", "subject": self.fill(a.get("subject", "")),
                                       "html": self.body(a.get("html", ""))})
                elif ty == "review_request":
                    chans = {a.get("review_type")}
                    nxt = n.get("next")
                    if isinstance(nxt, str) and any(m["id"] == nxt and m["type"] == "review_request" for m, _ in steps):
                        chans.add("sms" if a.get("review_type") == "email" else "email")
                        skip.add(nxt)
                    link = a.get("overrideReviewLink") or self.values.get("custom_values.google_review_link", "")
                    chan = "Text + email" if len(chans) > 1 else ("Text" if "sms" in chans else "Email")
                    self.cards.append({**base, "channel": chan, "review": True, "html": self.review_text(link)})
                elif ty == "internal_notification":
                    kind = a.get("type")
                    sub = a.get(kind) if isinstance(a.get(kind), dict) else {}
                    who = self.who(sub.get("selectedUser") or sub.get("userType") or "")
                    how = {"sms": "Text", "email": "Email", "notification": "App alert"}.get(kind, "Alert")
                    raw = sub.get("body") or sub.get("html") or sub.get("subject") or ""
                    self.team.append({**base, "how": how, "who": who, "what": self.first_line(raw)})
                elif ty == "task-notification":
                    who = self.who(a.get("assignedTo") or "")
                    self.team.append({**base, "how": "Task", "who": who, "what": self.fill(a.get("title", ""))})
        for i, c in enumerate(self.cards, 1):
            c["code"] = f"M{i}"

    def codes(self, pred) -> str:
        cs = [c["code"] for c in self.cards if pred(c)]
        if not cs:
            return ""
        return cs[0] if len(cs) == 1 else f"{cs[0]}–{cs[-1]}"

    def check(self) -> None:
        listed = set(self.cfg["automations"]) | {o["name"] for o in self.cfg.get("off", [])} | \
            {y["name"] for y in self.cfg.get("yours", [])} | set(self.cfg.get("not_shown", []))
        for w in self.flows:
            if w["name"] not in listed:
                print(f"  ! workflow not in config/client_sheet/{self.slug}.json: {w['name']!r} ({w['status']})",
                      file=sys.stderr)
        for y in self.cfg.get("yours", []):
            w = self.by_name.get(y["name"])
            if y["name"] != "_missed_call_text" and (not w or w["status"] != "published"):
                print(f"  ! listed as running but not published: {y['name']!r}", file=sys.stderr)

    # ── pages ──────────────────────────────────────────────────────────────

    def sub(self, text: str) -> str:
        """{codes:<workflow>} and {codes:stage=<id>} → M ranges."""
        def rep(m):
            key = m.group(1)
            if key.startswith("stage="):
                return self.codes(lambda c: c["stage"] == key[6:]) or "—"
            return self.codes(lambda c: c["auto"] == key) or "—"
        return re.sub(r"\{codes:([^}]+)\}", rep, text)

    def page_journey(self) -> str:
        steps = "".join(
            f'<li><span class="ic">{s["icon"]}</span><div><b>{esc(s["title"])}.</b> {esc(s["text"])}'
            + (f' <span class="refs">{self.codes(lambda c, s=s: c["stage"] == s["codes"])}</span>'
               if s.get("codes") and self.codes(lambda c, s=s: c["stage"] == s["codes"]) else "")
            + "</div></li>" for s in self.cfg["journey"])
        n_c = len(self.cards)
        return f"""
<section class="p1">
  <div class="brand">POOL PROFITS</div>
  <h1>{esc(self.cfg['title'])}</h1>
  <p class="sub">Prepared for <b>{esc(self.cfg['client'])}</b> · {time.strftime('%B %-d, %Y')}</p>
  <h2>How your leads and customers are handled</h2>
  <ol class="journey">{steps}</ol>
  <p class="tip">💡 {esc(self.cfg.get('journey_tip', ''))}</p>
  <div class="yrs"><h3>Already running (your own, they stay exactly as they are)</h3><ul class="yours">{self.yours()}</ul></div>
  <div class="how">
    <h3>How to reply (5 minutes)</h3>
    <p>The next pages show the <b>{n_c} messages</b> your customers can receive, numbered <b>M1</b>–<b>M{n_c}</b>, with
    the exact words. For each one tick <span class="box"></span> <b>Looks good</b> or write what to change. Then answer
    the questions on the last page. A quick text works too: <i>“All good except M4: say ‘this week’ instead of
    ‘today’.”</i></p>
    <p class="legend"><span class="mf">First name</span> = filled in for each customer &nbsp;·&nbsp;
    <span class="v">{esc(self.values.get('custom_values.business_phone') or self.values.get('location.name'))}</span> = your details, already in the system</p>
  </div>
</section>"""

    def card(self, c: dict) -> str:
        subj = f'<div class="subj">Subject: {c["subject"]}</div>' if c.get("subject") else ""
        note = f'<div class="note">⚠ {esc(c["note"])}</div>' if c.get("note") else ""
        kind = "email" if c["channel"] == "Email" else "sms"
        return f"""
<div class="card {kind}">
  <div class="ch"><span class="code">{c['code']}</span><span class="chan {kind}">{esc(c['channel'])}</span>
  <span class="when">{esc(c['when'])}</span></div>
  <div class="msg {kind}">{subj}{c['html']}</div>{note}
  <div class="ticks"><span><span class="box"></span> Looks good</span><span class="chg"><span class="box"></span> Change:</span><span class="line"></span></div>
</div>"""

    def page_messages(self) -> str:
        out = []
        for s in self.cfg["stages"]:
            cards = [c for c in self.cards if c["stage"] == s["id"]]
            if not cards:
                continue
            body, group, run = [], None, []
            for c in cards:
                if c.get("group") and c["group"] != group:
                    body.append(f'<div class="cards">{"".join(run)}</div>' if run else "")
                    run = []
                    body.append(f'<h3 class="grp">{esc(c["group"])}</h3>')
                group = c.get("group")
                run.append(self.card(c))
            body.append(f'<div class="cards">{"".join(run)}</div>')
            extra = []
            for name, info in self.cfg["automations"].items():
                if info.get("stage") == s["id"] and info.get("after_last") and any(c["auto"] == name for c in cards):
                    extra.append(f'<p class="after">↳ {esc(info["after_last"])}</p>')
            out.append(f'<section class="stage"><h2><span class="rng">{self.codes(lambda c, s=s: c["stage"] == s["id"])}'
                       f'</span>{esc(s["title"])}</h2>{"".join(body)}{"".join(extra)}</section>')
        return "".join(out)

    def page_last(self) -> str:
        merged: list[dict] = []  # same moment, same person: "Text + task to Nathan"
        for t in self.team:
            prev = merged[-1] if merged else None
            if prev and prev["when"] == t["when"] and prev["who"] == t["who"] and prev["auto"] == t["auto"]:
                prev["how"] += f" + {t['how'].lower()}"
                if t["how"] == "Task":
                    prev["what"] += f'<br><span class="dim">Task: {t["what"]}</span>'
                continue
            merged.append(dict(t))
        team = "".join(f'<tr><td class="w">{esc(t["when"])}</td><td class="h">{esc(t["how"])} to {esc(t["who"])}</td>'
                       f'<td>{t["what"]}</td></tr>' for t in merged)
        off, seen = [], set()
        for o in self.cfg.get("off", []):
            g = o.get("group")
            if g and g in seen:
                continue
            seen.add(g)
            if o.get("what"):
                off.append(f'<li><span class="box"></span> <b>{esc(o["what"])}</b> <span class="dim">— {esc(o["why"])}</span></li>')
        return self._last(team, off)

    def yours(self) -> str:
        yours = []
        for y in self.cfg.get("yours", []):
            if y["name"] == "_missed_call_text":
                if self.loc.get("enableMissedCallText") and self.loc.get("missedCallText"):
                    txt = self.loc["missedCallText"]
                    short = " ".join(lines(txt))
                    short = short if len(short) <= 120 else short[:120].rsplit(" ", 1)[0].rstrip(",.—-") + "…"
                    yours.append(f'<li class="wide">{esc(y["what"])}: <span class="q">“{esc(short)}”</span></li>')
                continue
            if (self.by_name.get(y["name"]) or {}).get("status") == "published":
                yours.append(f'<li>{esc(y["what"])}</li>')
        return "".join(yours)

    def _last(self, team: str, off: list[str]) -> str:
        dec = "".join(
            f'<li><div class="dq">{esc(self.sub(d["q"]))}</div><div class="dw">{esc(self.sub(d["why"]))}'
            + (f' <span class="sug">My suggestion: {esc(d["default"])}.</span>' if d.get("default") else "")
            + '</div><div class="yn"><span><span class="box"></span> Yes</span><span><span class="box"></span> No</span>'
            '<span class="line"></span></div></li>' for d in self.cfg.get("decisions", []))
        return f"""
<section class="last first">
  <h2>What goes to your team</h2>
  <table class="team"><tbody>{team}</tbody></table>
  <h2>Built, but kept off for now <span class="hint">tick to turn on</span></h2>
  <ul class="off">{''.join(off)}</ul>
</section>
<section class="last">
  <h2>Questions for you</h2>
  <ol class="dec">{dec}</ol>
  <div class="end">Nothing changes until you reply. Send your ticks and answers to {esc(self.cfg.get('contact_person', 'me'))}
  (a photo of the pages or a short text is perfect). I test every change before it goes live.</div>
</section>"""

    def build(self) -> str:
        self.collect()
        self.check()
        body = self.page_journey() + self.page_messages() + self.page_last()
        return (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><title>{esc(self.cfg["client"])} · '
                f'automations</title><style>{CSS.replace("__CLIENT__", esc(self.cfg["client"]))}</style></head><body>{body}</body></html>')


CSS = """
@page { size: Letter; margin: .5in .55in .55in; @bottom-left { content: "__CLIENT__ · your automations"; font: 8pt Inter, sans-serif; color: #94a3b8; }
        @bottom-right { content: counter(page) " / " counter(pages); font: 8pt Inter, sans-serif; color: #94a3b8; } }
* { box-sizing: border-box; }
body { font-family: Inter, "DejaVu Sans", sans-serif, "Noto Color Emoji"; color: #0f172a; font-size: 11pt; line-height: 1.4;
       margin: 0; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
h1 { font-size: 23pt; line-height: 1.15; margin: 4pt 0 4pt; color: #0b2540; letter-spacing: -.01em; }
h2 { font-size: 15pt; color: #0b2540; margin: 0 0 10pt; break-after: avoid; }
h3 { font-size: 12pt; margin: 0 0 4pt; color: #0b2540; }
p { margin: 0; }
.brand { font-size: 8.5pt; letter-spacing: .2em; font-weight: 800; color: #0891b2; }
.sub { color: #475569; margin-bottom: 8pt; }
.p1 { break-after: page; }
.journey { list-style: none; padding: 0; margin: 0 0 12pt; counter-reset: j; }
.journey li { display: flex; gap: 12pt; align-items: flex-start; padding: 3.5pt 0; border-bottom: 1px solid #e2e8f0; }
.journey li:last-child { border-bottom: 0; }
.journey .ic { font-size: 17pt; width: 26pt; text-align: center; line-height: 1.1; font-family: "Noto Color Emoji"; }
.journey b { color: #0b2540; }
.refs { display: inline-block; font-size: 8.5pt; font-weight: 700; color: #0e7490; background: #ecfeff; border-radius: 8pt;
        padding: 0 6pt; margin-left: 3pt; white-space: nowrap; }
.tip { background: #f8fafc; border-radius: 8pt; padding: 6pt 12pt; color: #334155; font-size: 10.2pt; margin-bottom: 10pt; }
.how { border: 1.5px solid #0891b2; border-radius: 10pt; padding: 9pt 13pt; }
.how p { font-size: 10.4pt; margin-bottom: 4pt; }
.legend { color: #475569; font-size: 9.5pt !important; margin: 4pt 0 0 !important; }
.mf { background: #e2e8f0; color: #334155; border-radius: 4pt; padding: 0 4pt; font-size: .92em; white-space: nowrap; }
.mf::before { content: "["; color: #94a3b8; } .mf::after { content: "]"; color: #94a3b8; }
.v { color: #0e7490; font-weight: 600; }
.lk { color: #0e7490; font-weight: 600; text-decoration: underline; }
.miss { background: #fee2e2; color: #b91c1c; border-radius: 4pt; padding: 0 4pt; font-size: .92em; }
.box { display: inline-block; width: 11pt; height: 11pt; border: 1.5px solid #64748b; border-radius: 2.5pt; vertical-align: -1.5pt; }
.stage { break-before: page; }
.stage + .stage { break-before: auto; margin-top: 10pt; }
.stage h2 { border-bottom: 2px solid #0891b2; padding-bottom: 3pt; margin-bottom: 7pt; }
.rng { float: right; font-size: 10pt; color: #0891b2; font-weight: 700; padding-top: 4pt; }
.grp { margin: 4pt 0 6pt; font-size: 11pt; color: #475569; break-after: avoid; }
.cards { display: flex; flex-wrap: wrap; justify-content: space-between; }
.cards .card { width: calc(50% - 5pt); }
.card { border: 1px solid #cbd5e1; border-radius: 10pt; padding: 8pt 10pt 7pt; margin: 0 0 7pt; break-inside: avoid; display: flex; flex-direction: column; }
.card .msg { flex: 1; }
.ch { display: flex; align-items: baseline; gap: 6pt; margin-bottom: 5pt; flex-wrap: wrap; }
.code { font-weight: 800; font-size: 13pt; color: #0b2540; min-width: 28pt; }
.chan { font-size: 8pt; font-weight: 700; text-transform: uppercase; letter-spacing: .06em; border-radius: 6pt; padding: 1pt 6pt;
        white-space: nowrap; }
.chan.sms { background: #dcfce7; color: #166534; }
.chan.email { background: #e0e7ff; color: #3730a3; }
.when { font-weight: 600; color: #0f172a; font-size: 9.6pt; line-height: 1.3; flex-basis: 100%; }
.msg { font-size: 10pt; line-height: 1.33; border-radius: 9pt; padding: 6pt 9pt; }
.msg.sms { background: #f0fdf4; border: 1px solid #bbf7d0; }
.msg.email { background: #f8fafc; border: 1px solid #e2e8f0; font-size: 9pt; line-height: 1.28; }
.msg p.gap { height: 3pt; }
.subj { font-weight: 700; margin-bottom: 5pt; padding-bottom: 4pt; border-bottom: 1px solid #e2e8f0; }
.dim { color: #64748b; font-size: .92em; }
.note { margin-top: 6pt; font-size: 9.6pt; color: #92400e; background: #fffbeb; border-radius: 6pt; padding: 4pt 8pt; }
.ticks, .yn { display: flex; gap: 12pt; align-items: center; margin-top: 6pt; font-size: 9.8pt; color: #334155; }
.ticks .line, .yn .line { flex: 1; border-bottom: 1px solid #94a3b8; height: 12pt; }
.after { color: #475569; font-size: 10pt; margin: -3pt 0 6pt 6pt; }
.last { break-before: page; }
.last.first { break-before: auto; margin-top: 6pt; }
.last h2 { margin-top: 12pt; } .last h2:first-child { margin-top: 0; }
.small { color: #475569; font-size: 10pt; margin: -6pt 0 8pt; }
.yours, .off { margin: 0 0 6pt; padding-left: 16pt; font-size: 10.5pt; }
.yours li, .off li { margin-bottom: 2.5pt; }
.off { list-style: none; padding-left: 0; }
.hint { font-size: 9.5pt; font-weight: 500; color: #64748b; margin-left: 6pt; }
.q { color: #334155; font-style: italic; }
.yrs { margin: 0 0 10pt; } .yrs h3 { font-size: 10.5pt; } .yrs .yours { font-size: 9.4pt; columns: 2; column-gap: 18pt; padding-left: 12pt; } .yrs li.wide { column-span: all; } .yrs li { margin-bottom: 1.5pt; }
table.team { width: 100%; border-collapse: collapse; font-size: 9.6pt; }
table.team td { border-bottom: 1px solid #e2e8f0; padding: 3pt 5pt; vertical-align: top; }
table.team td.w { width: 2.25in; color: #475569; }
table.team td.h { width: 1.35in; font-weight: 600; white-space: nowrap; }
.dec { padding-left: 18pt; margin: 0; }
.dec li { margin-bottom: 9pt; break-inside: avoid; }
.dq { font-weight: 700; color: #0b2540; font-size: 11.5pt; }
.dw { color: #475569; font-size: 10.2pt; margin-top: 2pt; }
.sug { color: #047857; font-weight: 600; }
.end { margin-top: 10pt; background: #ecfeff; border-radius: 10pt; padding: 11pt 14pt; color: #0b2540; font-size: 10.8pt; }
"""


def source(slug: str, agency_dir: str | None) -> Path:
    if agency_dir:
        return ROOT / "dump" / agency_dir / slug
    if (DUMP / slug / "location.json").exists():
        return DUMP / slug
    hits = sorted((ROOT / "dump").glob(f"*/{slug}/location.json"))
    if len(hits) == 1:
        return hits[0].parent
    sys.exit(f"dump de {slug!r} não encontrado (use --agency-dir)")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("slug")
    parser.add_argument("--agency-dir", help="dump/<agency-dir>/<slug> (e.g. burchtech, poolduck)")
    parser.add_argument("--config", help="default: config/client_sheet/<slug>.json")
    parser.add_argument("--out", help="extra copy of the PDF (e.g. a scratchpad path)")
    args = parser.parse_args()
    src = source(args.slug, args.agency_dir)
    cfg = json.loads(Path(args.config or ROOT / "config" / "client_sheet" / f"{args.slug}.json").read_text())
    sheet = Sheet(args.slug, src, cfg)
    OUT.mkdir(parents=True, exist_ok=True)
    page, pdf = OUT / f"{args.slug}.html", OUT / f"{args.slug}.pdf"
    page.write_text(sheet.build())
    subprocess.run([CHROMIUM, "--headless=new", "--no-sandbox", "--disable-gpu", "--no-pdf-header-footer",
                    "--virtual-time-budget=10000", f"--print-to-pdf={pdf}", page.as_uri()], capture_output=True, timeout=180)
    pages = "?"
    try:
        from pypdf import PdfReader
        pages = len(PdfReader(str(pdf)).pages)
    except Exception:  # noqa: BLE001
        pass
    if args.out:
        Path(args.out).write_bytes(pdf.read_bytes())
    if sheet.missing:
        print(f"  ! custom values vazios usados em mensagens: {sorted(sheet.missing)}", file=sys.stderr)
    print(f"{len(sheet.cards)} mensagens ao cliente, {len(sheet.team)} avisos à equipe, {pages} páginas → {pdf}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
