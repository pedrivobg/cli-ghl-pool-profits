#!/usr/bin/env python3
"""Data for the standard CRM guide every new client gets before go-live (site/crm-guide/index.html, one JSON per
client: site/crm-guide/data/<slug>.json, schema in site/crm-guide/SCHEMA.md).

    python3 scripts/pp_dump.py --only "Snapshot Pool Profits"      # the V9 model
    python3 scripts/pp_dump.py --only "Corolla Pool and Spa"       # the client
    python3 scripts/pp_crm_guide.py corolla-pool-and-spa [more slugs] [--offline]

What the client will have at go-live = the master "Snapshot Pool Profits" (V9): the workflows published in the
Southern model (minus per-account ones: 08 Paid Ads, Sequential Call Routing), texts from the master with the
CLIENT's own custom values filled in (pp_client_sheet.Sheet: same flow walk, "when" text, merge-field rendering,
SMS templates), contact fields as [First name], links as readable labels. Stages, journey, plain meanings and
questions: config/crm_guide.json.

Client tasks get a status hint from the client's live account: dump (users, location, custom values, forms) plus
read-only calls (phone numbers, form submissions, contact count) and a look at the client's website for a privacy
page. --offline reuses the last answers (dump/<slug>/crm_guide_live.json). Never writes to GHL.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
import urllib.request
from pathlib import Path

from _common import DUMP, ROOT
from pp_client_sheet import LINKS, Sheet
from pp_snapshot_guide import lines

CFG = ROOT / "config" / "crm_guide.json"
OUT = ROOT / "site" / "crm-guide" / "data"
ICONS = {"phone", "form", "chat", "clock", "quote", "calendar", "trophy", "star", "refresh"}
AREAS = {"Phone", "Google", "Website", "Team", "Messages", "Billing", "Other"}
LEGAL_SUFFIX = re.compile(r",?\s+(inc\.?|llc|l\.l\.c\.|corp\.?|co\.|ltd\.?)$", re.I)


def phone_fmt(raw: str) -> str:
    d = re.sub(r"\D", "", raw or "")
    if len(d) == 11 and d.startswith("1"):
        d = d[1:]
    return f"({d[:3]}) {d[3:6]}-{d[6:]}" if len(d) == 10 else (raw or "")


def stage_name(name: str) -> str:
    """'🆕 New Lead' → 'New Lead'."""
    return re.sub(r"^[^A-Za-z0-9]+", "", name or "").strip()


class Guide(Sheet):
    """pp_client_sheet's Sheet writing plain text instead of HTML."""

    def out_text(self, s: str) -> str:
        return s

    def out_link(self, label: str, url: str, field: str) -> str:
        return label

    def out_value(self, val: str, field: str) -> str:
        return val

    def out_missing(self, name: str, field: str) -> str:
        return LINKS[field] if field in LINKS else f"[{name}: not set yet]"  # links: created by me at go-live

    def out_field(self, label: str) -> str:
        return f"[{label}]"

    def out_lines(self, parts: list[str]) -> str:
        return "\n".join(parts).strip()

    def review_text(self, link: str) -> str:
        return ""  # written per channel in CrmGuide.messages()


class CrmGuide:
    def __init__(self, slug: str, cfg: dict, offline: bool):
        self.slug, self.cfg, self.offline = slug, cfg, offline
        self.model_dir, self.client_dir = DUMP / cfg["model_slug"], DUMP / slug
        if not (self.client_dir / "location.json").exists():
            sys.exit(f"dump/{slug} não encontrado (rode pp_dump.py --only ...)")
        self.flags: list[str] = []
        published = self.published_set()
        sheet_cfg = {"stages": cfg["stages"], "automations": {}}
        for name in published:
            if name not in cfg["automations"]:
                self.flags.append(f"workflow publicado do modelo fora do config/crm_guide.json: {name!r}")
        sheet_cfg["automations"] = {n: i for n, i in cfg["automations"].items() if n in published}
        for n in cfg["automations"]:
            if n not in published:
                self.flags.append(f"config cita {n!r}, que não está no conjunto publicado do modelo")
        self.sheet = Guide(slug, self.model_dir, sheet_cfg)
        self.sheet.load_account(self.client_dir)  # texts: the client's own values
        self.loc = self.sheet.loc
        self.v = self.sheet.values
        rep = self.loc.get("authorizedRepresentative") or {}
        own = self.v.get("custom_values.owner_first_name", "")
        rep_first = (rep.get("firstName") or "").strip()
        user = next((u for u in self.load("users.json", []) if (u.get("email") or "").lower() == (rep.get("email") or "").lower()), None)
        # alerts go to the representative's user; "Josh" (owner_first_name) for "Joshua" is the same person
        self.owner = (user or {}).get("firstName") or (own if own and rep_first.lower().startswith(own.lower()) else rep_first or own) or "you"
        self.sheet.cfg["owner"] = self.owner
        self.business = self.v.get("custom_values.friendly_business_name") or self.loc.get("name", "")
        self.published = published

    def load(self, name: str, default=None, d: Path | None = None):
        p = (d or self.client_dir) / name
        return json.loads(p.read_text()) if p.exists() else default

    # ── model ──────────────────────────────────────────────────────────────

    def published_set(self) -> list[str]:
        """Master workflows that are published in the Southern model, minus the per-account ones."""
        model = self.load("workflows/_index.json", [], self.model_dir)
        south = {w["name"]: w["status"] for w in self.load("workflows/_index.json", [], DUMP / self.cfg["southern_slug"])}
        if not south:
            self.flags.append("dump da Southern ausente: usando o status do master")
        out = []
        for w in model:
            status = south.get(w["name"], w["status"]) if south else w["status"]
            if status != "published" or w["name"] in self.cfg["skip_names"] or \
                    (w.get("folder") or "").startswith(tuple(self.cfg["skip_folders"])):
                continue
            out.append(w["name"])
        return out

    # ── live (read-only) ───────────────────────────────────────────────────

    def live(self) -> dict:
        cache = self.client_dir / "crm_guide_live.json"
        if self.offline:
            return json.loads(cache.read_text()) if cache.exists() else {}
        from _common import load_dotenv, Agency
        from cli_anything.gohighlevel.utils.agency import SERVICES
        load_dotenv()
        a, loc = Agency(), self.loc["id"]
        out: dict = {"at": dt.datetime.now().isoformat(timespec="seconds")}
        try:
            out["numbers"] = [{k: n.get(k) for k in ("phoneNumber", "friendlyName", "forwardingNumber",
                                                      "linkedRingAllUsers", "isDefaultNumber", "inboundCallService")}
                              for n in a.call("GET", SERVICES, f"/phone-system/numbers/location/{loc}").get("numbers", [])]
        except Exception as e:  # noqa: BLE001
            self.flags.append(f"números de telefone: {e}")
        try:
            end = dt.date.today() + dt.timedelta(days=1)
            r = a.call("GET", SERVICES, "/forms/submissions", params={
                "locationId": loc, "startAt": str(end - dt.timedelta(days=90)), "endAt": str(end), "limit": 100})
            out["submissions"] = [s.get("formId") for s in r.get("submissions") or []]
        except Exception as e:  # noqa: BLE001
            self.flags.append(f"submissões de form: {e}")
        try:
            out["contacts"] = (a.call("GET", SERVICES, "/contacts/", params={"locationId": loc, "limit": 1})
                               .get("meta") or {}).get("total")
        except Exception as e:  # noqa: BLE001
            self.flags.append(f"contatos: {e}")
        out["privacy"] = self.privacy_page()
        cache.write_text(json.dumps(out, indent=1))
        return out

    def privacy_page(self) -> dict:
        """Look for a privacy page on the client's site (A2P): its URL and whether it has the SMS sentence."""
        site = (self.v.get("custom_values.privacy_policy") or "").strip()
        base = (self.loc.get("website") or self.v.get("custom_values.client_domain_name") or "").rstrip("/")
        cands = [site] if site.startswith("http") else []
        if base.startswith("http"):
            cands += [f"{base}/privacy-policy", f"{base}/privacy"]
        for url in cands:
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=20) as r:
                    page = r.read(3_000_000).decode("utf-8", "ignore")
            except Exception:  # noqa: BLE001
                continue
            title = re.search(r"<title[^>]*>([^<]*)", page, re.I)
            if title and "privacy" in title.group(1).lower():
                text = page.lower()
                return {"url": url, "sms": "third part" in text and ("mobile" in text or "text messag" in text or "sms" in text)}
        return {}

    # ── content ────────────────────────────────────────────────────────────

    def messages(self) -> tuple[list[dict], list[dict]]:
        s = self.sheet
        s.collect()
        cards: list[dict] = []
        for c in s.cards:
            when = c["when"].replace(" · or ", "; or ")
            if c.get("review"):
                chans = ["email", "sms"] if "email" in c["channel"].lower() and "text" in c["channel"].lower() else \
                    ["sms" if c["channel"] == "Text" else "email"]
                for ch in chans:
                    cards.append({"stage": c["stage"], "auto": c["auto"], "step": c["step"], "channel": ch, "when": when,
                                  "text": f"A short {'text' if ch == 'sms' else 'email'} from Google's review tool asking "
                                          f"them to review {self.business}, with a link to your Google review page.",
                                  "editable": False})
                continue
            m = {"stage": c["stage"], "auto": c["auto"], "step": c["step"], "when": when,
                 "channel": "email" if c["channel"] == "Email" else "sms", "text": c["html"], "editable": True}
            if m["channel"] == "email":
                m["subject"] = c.get("subject", "")
            cards.append(m)
        for i, c in enumerate(cards, 1):
            c["code"] = f"M{i}"
        self.cards = cards
        team, merged = [], []
        tw, tn = self.cfg.get("team_what", {}), self.cfg.get("team_when", {})
        for t in s.team:
            key = f"{t['auto']}/{t['step']}"
            what = tw.get(key) or re.sub(r"\s+", " ", t["what"]).strip()
            when = tn.get(key) or t["when"].replace(" · or ", "; or ")
            prev = merged[-1] if merged else None
            if prev and prev["_auto"] == t["auto"] and prev["when"] == when:
                prev["what"] += f"; plus {what[0].lower()}{what[1:]}"
                continue
            merged.append({"_auto": t["auto"], "when": when, "what": what, "who": self.owner})
        first = [t for t in merged if self.cfg["automations"][t["_auto"]]["stage"] == "team"]  # new leads before reviews
        team = [{k: v for k, v in t.items() if not k.startswith("_")} for t in first + [t for t in merged if t not in first]]
        return cards, team

    def raw_values_used(self) -> dict[str, list[str]]:
        """custom value → codes, from the raw texts (also inside html attributes, e.g. a logo)."""
        used: dict[str, list[str]] = {}
        steps = {}
        for w in self.sheet.flows:
            for n in w["workflowData"]["templates"]:
                steps[(w["name"], n["name"])] = n
        for c in self.cards:
            n = steps.get((c["auto"], c["step"])) or {}
            a = n.get("attributes") or {}
            raw = json.dumps(a) + (self.sheet.sms_body(a) if n.get("type") == "sms" else "")
            for k in re.findall(r"custom_values\.(\w+)", raw):
                used.setdefault(k, [])
                if c["code"] not in used[k]:
                    used[k].append(c["code"])
        return used

    def sub(self, text: str) -> str:
        def codes(stage: str) -> str:
            cs = [c["code"] for c in self.cards if c["stage"] == stage]
            return "" if not cs else cs[0] if len(cs) == 1 else f"{cs[0]}–{cs[-1]}"

        def step(key: str, field: str) -> str:
            auto, _, name = key.partition("/")
            c = next((c for c in self.cards if c["auto"] == auto and c["step"] == name), None)
            if not c:
                return "—"
            return c[field] if field == "code" else c[field][0].lower() + c[field][1:]

        text = text.replace("{business}", self.business).replace("{owner}", self.owner)
        text = re.sub(r"\{codes:([^}]+)\}", lambda m: codes(m.group(1)) or "—", text)
        text = re.sub(r"\{code:([^}]+)\}", lambda m: step(m.group(1), "code"), text)
        return re.sub(r"\{when:([^}]+)\}", lambda m: step(m.group(1), "when"), text)

    def pipeline(self) -> list[dict]:
        pipes = self.load("pipelines.json", [], self.model_dir)
        pipe = next((p for p in pipes if p["name"] == "Pool Leads"), None)
        if not pipe:
            self.flags.append("pipeline Pool Leads não encontrado no modelo")
            return []
        moved = set()
        for w in self.sheet.flows:
            if w["name"] not in self.published:
                continue
            own = {c.get("value") for t in w.get("triggers") or [] for c in t.get("conditions") or []
                   if c.get("field") == "opportunity.pipelineStageId"}
            for n in w["workflowData"]["templates"]:
                sid = (n.get("attributes") or {}).get("pipeline_stage_id")
                if n["type"] == "create_opportunity" and sid and sid not in own:
                    moved.add(sid)
        out = []
        for st in pipe["stages"]:
            nm = stage_name(st["name"])
            plain = self.cfg["pipeline_plain"].get(nm)
            if not plain:
                self.flags.append(f"etapa sem texto em pipeline_plain: {nm!r}")
            out.append({"id": self.cfg["pipeline_ids"].get(nm) or re.sub(r"[^a-z0-9]+", "-", nm.lower()).strip("-"),
                        "name": nm, "plain": plain or "", "auto": st["id"] in moved})
        return out

    def stages(self) -> list[dict]:
        out = []
        for s in self.cfg["stages"]:
            msgs = [{k: c[k] for k in ("code", "channel", "when", "subject", "text", "editable") if k in c}
                    for c in self.cards if c["stage"] == s["id"]]
            if msgs:
                out.append({"id": s["id"], "title": s["title"], "trigger_plain": s["trigger_plain"], "messages": msgs})
        return out

    def tasks(self, live: dict, used: dict[str, list[str]]) -> list[dict]:
        v, loc = self.v, self.loc
        nums = live.get("numbers") or []
        line = next((n for n in nums if n.get("isDefaultNumber")), nums[0] if nums else None)
        line_txt = phone_fmt(line["phoneNumber"]) if line else ""
        users = [u for u in self.load("users.json", []) if not u.get("deleted")]
        tasks: list[dict] = []

        def add(tid, area, title, why, steps, status):
            assert area in AREAS and status in ("todo", "done", "na"), (tid, area, status)
            tasks.append({"id": tid, "area": area, "title": title, "why": why, "steps": steps, "status_hint": status})

        # Phone
        if line:
            add("t-line", "Phone", f"Save your new business line: {line_txt}",
                "Every text your customers get comes from this number, and their replies come back to it.",
                [f"Save {line_txt} in your phone as “{self.business} – Leads”.",
                 "Use it when you text or call leads from the LeadConnector app, so the whole conversation stays in one place.",
                 "Keep your current number as it is: calls to it are not affected."], "done")
        else:
            add("t-line", "Phone", "Get your business line",
                "Texts to your customers need a business line inside the system.",
                ["Tell me the area code you'd like for the new number.",
                 "I'll buy it and send it to you to save in your phone."], "todo")
        rings = bool(line and (line.get("forwardingNumber") or line.get("linkedRingAllUsers") or line.get("inboundCallService")))
        add("t-ring", "Phone", f"Pick the phone that rings when someone calls {line_txt or 'your business line'}",
            "Missed calls get a text right away, but the best result is still picking up.",
            ["Tell me the cell number(s) that should ring: yours, the office, or a team member.",
             "If more than one: should they ring at the same time, or one after the other?",
             "I'll set it up and test it from here before go-live."], "done" if rings else "todo")
        rep = loc.get("authorizedRepresentative") or {}
        bi = loc.get("businessInformation") or {}
        ein = re.sub(r"\D", "", bi.get("registrationNumber") or "")
        addr = v.get("custom_values.business_address") or ", ".join(
            x for x in (loc.get("address"), loc.get("city"), loc.get("state"), loc.get("postalCode")) if x)
        legal = loc.get("legalBusinessName") or v.get("custom_values.legal_business_name") or ""
        a2p_ok = bool(legal and len(ein) == 9 and addr and rep.get("email"))
        add("t-a2p", "Phone", "Confirm your business details for texting approval",
            "Phone carriers only approve business texting when these match your IRS records exactly.",
            [f"Check: {legal or '[legal name missing]'} · EIN ending in {ein[-4:] if ein else '[missing]'} · {addr or '[address missing]'}.",
             f"Contact person: {(rep.get('firstName', '') + ' ' + rep.get('lastName', '')).strip() or '[missing]'}"
             f"{', ' + rep['email'] if rep.get('email') else ''}.",
             "If anything differs from your IRS letter (CP 575 or 147C), send me the right version."],
            "done" if a2p_ok else "todo")
        # Website
        priv = live.get("privacy") or {}
        sentence = ("“No mobile information will be shared with third parties or affiliates for marketing or promotional "
                    "purposes. Text messaging opt-in data and consent will not be shared with any third parties.”")
        if priv.get("url") and priv.get("sms"):
            add("t-privacy", "Website", "Privacy policy page on your website",
                "Phone carriers check it before approving your texts.",
                [f"I found it at {priv['url']} and it already covers text messages.",
                 "Keep it linked in your website footer, and tell me if the address changes."], "done")
        elif priv.get("url"):
            add("t-privacy", "Website", "Add one sentence to your privacy policy",
                "Phone carriers check it before approving your texts.",
                [f"Open your privacy page ({priv['url']}).", f"Add this sentence: {sentence}",
                 "Tell me when it's live and I'll check it."], "todo")
        else:
            add("t-privacy", "Website", "Add a privacy policy page to your website",
                "Phone carriers check it before approving your texts.",
                ["Add a page called “Privacy Policy”, linked in your website footer.",
                 f"Include this sentence: {sentence}",
                 "Send me the link (or tell me who manages your website and I'll help them)."], "todo")
        forms = self.load("forms.json", [])
        skip = re.compile(r"onboarding|nps|post-visit|booking|claim discount|optin", re.I)
        site_forms = [f["name"] for f in forms if not skip.search(f.get("name", ""))]
        main = next((n for n in site_forms if re.search(r"contact", n, re.I) and not n.startswith("Service Page")),
                    site_forms[0] if site_forms else "your quote form")
        ids = {f.get("_id") or f.get("id") for f in forms if f.get("name") in site_forms}
        got = [s for s in live.get("submissions") or [] if s in ids]
        add("t-forms", "Website", f"Put the “{main}” form on your website",
            "Then every website lead lands on your lead board and you get a text alert right away.",
            ["Tell me who manages your website (or send me a login).",
             "Tell me which pages have a contact or quote form today.",
             f"I'll place the “{main}” form there and send a test lead myself before go-live."],
            "done" if got else "todo")
        # Google
        place = loc.get("googlePlacesId") or (loc.get("social") or {}).get("googlePlacesId")
        add("t-google", "Google", "Connect your Google Business Profile",
            "Your Google reviews and messages then show up in the app, next to your texts.",
            ["Log in at app.poolprofits.com (see the Team task).",
             "Go to Settings → Integrations → Google and click Connect.",
             f"Sign in with the Google account that manages your Business Profile, allow everything and pick {self.business}."],
            "done" if place or loc.get("gmbBusinessScopeExist") else "todo")
        link = v.get("custom_values.google_review_link", "")
        if link.startswith("http"):
            add("t-review-link", "Google", "Check your Google review link",
                "Happy customers get this link in the review request.",
                [f"Open {link} on your phone.", f"Make sure it opens the review box for {self.business}.",
                 "If it opens another business (or nothing), tell me."], "done")
        else:
            add("t-review-link", "Google", "Send me your Google review link",
                "Happy customers get this link in the review request.",
                ["Search your business on Google, open your profile and tap “Ask for reviews” (or “Share review form”).",
                 "Copy the link and send it to me."], "todo")
        # Team
        add("t-team", "Team", "Log in to the app (you and your team)",
            "You'll see every lead, text and call in one place, and get alerts on your phone.",
            ["Send me the name, email and cell number of everyone who should use it.",
             "Go to app.poolprofits.com, click “Forgot password” and enter your email to set your password.",
             "Install the “LeadConnector” app on your phone (App Store or Google Play), log in with the same email and allow notifications."],
            "done" if users else "todo")
        # Messages
        n = len(self.cards)
        add("t-messages", "Messages", f"Read every message (M1–M{n}) and mark it OK or change it",
            "These are the exact words your customers will get, with your details filled in.",
            ["Go through each message on this page.", "Mark “OK”, or write the change you want.",
             "I'll update them and test each one before go-live."], "todo")
        if LEGAL_SUFFIX.search(self.business):
            short = LEGAL_SUFFIX.sub("", self.business).strip()
            add("t-name", "Messages", f"Confirm the name your customers see: “{self.business}”",
                "It appears in most texts and emails; customers usually know you by your short name.",
                [f"Tell me if the texts should say “{short}” instead.", "I'll update every message at once."], "todo")
        cv_names = self.sheet.cv_names
        client_missing = []
        for k, codes in sorted(used.items()):
            val = v.get(f"custom_values.{k}", "")
            is_link = k in LINKS or k.endswith(("_link", "_url"))
            if val.startswith("http") if is_link else bool(val):
                continue
            if k in ("nps_survey_link",):
                continue  # created by me at onboarding (pp_nps): flagged in build()
            if k == "google_review_link":
                continue  # covered by t-review-link
            if k == "logo_url":
                self.flags.append(f"logo_url inválido ({val[:30]!r}) usado em {', '.join(codes)}")
                client_missing.append(("your logo (image file)", codes))
                continue
            client_missing.append((cv_names.get(k, k), codes))
        if client_missing:
            add("t-values", "Messages", "Send me the details missing from your messages",
                "Some messages use them; without them the text would go out incomplete.",
                [f"{name} (used in {', '.join(codes)})." for name, codes in client_missing] +
                ["Send them to me and I'll fill them in."], "todo")
        # Other
        add("t-hours", "Other", "Tell me your business hours",
            "Welcome texts and some emails wait for business hours, and your team alerts follow them.",
            ["Send me your office hours for each day (and the days you're closed).",
             "Tell me if you take calls on weekends."], "todo")
        add("t-booking", "Other", "Booking: customers reply or call (no booking link)",
            "Most pool companies book in their own software, so the texts ask customers to reply or call.",
            [f"Customers book by replying to a text or calling {line_txt or 'your business line'}.",
             "If you'd like an online booking link in the texts, tell me which software you book in and I'll check it first."],
            "na")
        contacts = live.get("contacts") or 0
        add("t-import", "Other", "Send me your current customer list",
            "So your current customers never get new-lead texts when they call or text you.",
            ["Export your customers from your pool software (Skimmer, Pool Brain, QuickBooks…) as a spreadsheet: name, phone, email, address.",
             "Send it to me by email.", "I'll import them as customers before go-live."],
            "done" if contacts >= 20 else "todo")
        return tasks

    def build(self) -> dict:
        cards, team = self.messages()
        used = self.raw_values_used()
        live = self.live()
        journey = []
        for j in self.cfg["journey"]:
            assert j["icon"] in ICONS, j
            journey.append({"id": j["id"], "icon": j["icon"], "title": self.sub(j["title"]),
                            "text": self.sub(j["text"]), "stage": j["stage"]})
        loc = self.loc
        city = ", ".join(x for x in (loc.get("city"), loc.get("state")) if x)
        data = {
            "version": 1,
            "generated_at": dt.date.today().isoformat(),
            "client": {"slug": self.slug, "name": self.business, "owner_first": self.owner,
                       "business_phone": phone_fmt(self.v.get("custom_values.business_phone") or loc.get("phone", "")),
                       "city": city, "location_id": loc["id"]},
            "prepared_by": self.cfg["prepared_by"],
            "meeting_note": self.sub(self.cfg["meeting_note"]),
            "journey": journey,
            "pipeline": self.pipeline(),
            "stages": self.stages(),
            "team_alerts": team,
            "client_tasks": self.tasks(live, used),
            "decisions": [{"id": d["id"], "question": self.sub(d["question"]), "suggestion": self.sub(d["suggestion"])}
                          for d in self.cfg["decisions"]],
        }
        for k, codes in sorted(used.items()):
            if not self.v.get(f"custom_values.{k}"):
                ours = " — criado no onboarding (pp_nps)" if k == "nps_survey_link" else ""
                self.flags.append(f"custom value vazio usado: {k} ({', '.join(codes)}){ours}")
        return data


def validate(d: dict) -> list[str]:
    """Shape per site/crm-guide/SCHEMA.md."""
    errs = []
    req = {"version": int, "generated_at": str, "client": dict, "prepared_by": str, "meeting_note": str,
           "journey": list, "pipeline": list, "stages": list, "team_alerts": list, "client_tasks": list, "decisions": list}
    for k, t in req.items():
        if not isinstance(d.get(k), t):
            errs.append(f"{k}: falta ou tipo errado")
    for k in ("slug", "name", "owner_first", "business_phone", "city", "location_id"):
        if not d.get("client", {}).get(k):
            errs.append(f"client.{k} vazio")
    if not 6 <= len(d.get("journey", [])) <= 8:
        errs.append("journey: precisa de 6–8 passos")
    for j in d.get("journey", []):
        if set(j) != {"id", "icon", "title", "text", "stage"} or j["icon"] not in ICONS:
            errs.append(f"journey {j.get('id')}: chaves/ícone")
    for p in d.get("pipeline", []):
        if set(p) != {"id", "name", "plain", "auto"} or not isinstance(p["auto"], bool) or not p["plain"]:
            errs.append(f"pipeline {p.get('name')}: chaves")
    if not 6 <= len(d.get("stages", [])) <= 9:
        errs.append("stages: precisa de 6–9")
    codes = []
    for s in d.get("stages", []):
        if not {"id", "title", "trigger_plain", "messages"} <= set(s) or not s["messages"]:
            errs.append(f"stage {s.get('id')}: chaves")
        for m in s.get("messages", []):
            codes.append(m.get("code"))
            if m.get("channel") not in ("sms", "email") or not m.get("when") or not m.get("text") \
                    or not isinstance(m.get("editable"), bool) or (m["channel"] == "email" and not m.get("subject") and m["editable"]):
                errs.append(f"mensagem {m.get('code')}: campos")
            if re.search(r"\{\{|<[a-z/][^>]*>", m.get("text", "") + m.get("subject", "")):
                errs.append(f"mensagem {m.get('code')}: merge field ou HTML sobrando")
    if codes != [f"M{i}" for i in range(1, len(codes) + 1)]:
        errs.append(f"códigos fora de ordem: {codes}")
    for t in d.get("team_alerts", []):
        if set(t) != {"when", "what", "who"} or not all(t.values()):
            errs.append(f"team_alert: {t}")
    for t in d.get("client_tasks", []):
        if set(t) != {"id", "area", "title", "why", "steps", "status_hint"} or t["area"] not in AREAS \
                or t["status_hint"] not in ("todo", "done", "na") or not 2 <= len(t["steps"]) <= 5:
            errs.append(f"task {t.get('id')}: campos")
    if not 3 <= len(d.get("decisions", [])) <= 5:
        errs.append("decisions: precisa de 3–5")
    for x in d.get("decisions", []):
        if set(x) != {"id", "question", "suggestion"} or "—" in x["question"]:
            errs.append(f"decision {x.get('id')}: campos/código")
    ids = [t["id"] for t in d.get("client_tasks", [])] + [x["id"] for x in d.get("decisions", [])]
    if len(ids) != len(set(ids)):
        errs.append("ids repetidos")
    return errs


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("slugs", nargs="+")
    ap.add_argument("--offline", action="store_true", help="no GHL/website calls: reuse dump/<slug>/crm_guide_live.json")
    args = ap.parse_args()
    cfg = json.loads(CFG.read_text())
    OUT.mkdir(parents=True, exist_ok=True)
    bad = 0
    for slug in args.slugs:
        g = CrmGuide(slug, cfg, args.offline)
        data = g.build()
        text = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
        errs = validate(json.loads(text))
        out = OUT / f"{slug}.json"
        out.write_text(text)
        msgs = [m for s in data["stages"] for m in s["messages"]]
        st = {k: sum(t["status_hint"] == k for t in data["client_tasks"]) for k in ("done", "todo", "na")}
        print(f"\n{data['client']['name']} → {out.relative_to(ROOT)}")
        print(f"  {len(msgs)} mensagens ({sum(m['channel'] == 'sms' for m in msgs)} SMS, "
              f"{sum(m['channel'] == 'email' for m in msgs)} e-mail) em {len(data['stages'])} etapas · "
              f"{len(data['team_alerts'])} avisos à equipe ({g.owner}) · {len(data['pipeline'])} colunas · "
              f"{len(data['journey'])} passos · {len(data['client_tasks'])} tarefas {st} · {len(data['decisions'])} perguntas")
        print("  tarefas: " + ", ".join(f"{t['id']}={t['status_hint']}" for t in data["client_tasks"]))
        for f in g.flags:
            print(f"  ! {f}")
        for e in errs:
            print(f"  ERRO {e}")
        bad += bool(errs)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
