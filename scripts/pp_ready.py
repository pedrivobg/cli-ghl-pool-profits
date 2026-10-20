#!/usr/bin/env python3
"""Is a sub-account ready to go live? Offline double-check of a dumped account against the model.

    ./.venv/bin/python scripts/pp_ready.py --only Poolheads --only "Rosebrook pools"

Complements pp_audit (message content) and pp_compare (diff to the model) with what a new client
needs before the first lead (Pedro, 20/10):
  - the Business Profile representative is a user of the account (same name, e-mail, phone);
  - every internal notification / task / assignment step has a user, and only users of THIS account;
  - no id of another dumped account (user, pipeline, stage, form, field, template, calendar,
    workflow) left in a workflow — the GHL accepts some of them and the step silently does nothing;
  - every published workflow has an active trigger; same published set and settings as the model
    (allow re-entry, stop on response…), apart from what is per account (08 Paid Ads, IVR, line tags);
  - pipeline "Pool Leads" with the model's stages in the model's order;
  - Google review links = the account's own place (or empty with Review Request in draft);
  - time zone set (not the onboarding's America/Sao_Paulo), native missed-call text off;
  - no custom value holding the literal "null" / "None".
Exit code 1 if anything is wrong (ERRO); AVISO lines are for a human to look at.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from _common import PRIORITY, load_dotenv, location_dirs
from pp_audit import load

PER_ACCOUNT = ("08 Paid Ads",)  # folders whose status depends on the client
PER_ACCOUNT_NAMES = {"IVR - Main Line Menu", "Facebook Ads Call - Tag", "Website & GBP Call - Tag",
                     "Sequential Call Routing"}
SETTINGS = ("allowMultiple", "allowMultipleOpportunity", "stopOnResponse", "removeContactFromLastStep",
            "autoMarkAsRead")
ID_RE = re.compile(r'"([A-Za-z0-9]{20}|[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})"')


def workflows(d: Path) -> list[dict]:
    return [load(d / "workflows" / f"{w['id']}.json", {}) | {"_meta": w}
            for w in load(d / "workflows" / "_index.json", [])]


def assets(d: Path) -> dict[str, str]:
    """id → kind for everything a workflow can point at."""
    out = {u["id"]: "usuário" for u in load(d / "users.json", [])}
    for p in load(d / "pipelines.json", []):
        out[p["id"]] = "pipeline"
        out.update({s["id"]: "etapa" for s in p.get("stages") or []})
    out.update({(f.get("id") or f.get("_id")): "form" for f in load(d / "forms.json", [])})
    out.update({f["id"]: "campo" for f in load(d / "custom_fields.json", [])})
    out.update({s["_id"]: "template" for s in load(d / "snippets.json", [])})
    out.update({c["id"]: "calendário" for c in load(d / "calendars.json", [])})
    out.update({w["id"]: "workflow" for w in load(d / "workflows" / "_index.json", [])})
    return out


def user_refs(step: dict) -> list[tuple[str, list]]:
    """(what, user ids) for every step that must reach a person."""
    at = step.get("attributes") or {}
    t = step.get("type")
    if t == "internal_notification":
        sub = at.get(at.get("type")) or {}
        if sub.get("userType") == "user":
            return [("notificação", sub.get("selectedUser") or [])]
        return []
    if t in ("task-notification", "task_notification"):
        return [("tarefa", [at["assignedTo"]] if at.get("assignedTo") else [])] if "assignedTo" in at else []
    if t == "assign_user":
        return [("atribuição", at.get("user_list") or at.get("userList") or at.get("users") or [])]
    return []


def check(d: Path, model: Path, foreign: dict[str, tuple[str, str]], place_ok: set[str]) -> int:
    loc = load(d / "location.json", {})
    users = {u["id"]: u for u in load(d / "users.json", [])}
    own = assets(d)
    errs, warns = [], []
    err, warn = errs.append, warns.append

    rep = loc.get("authorizedRepresentative") or {}
    rep_user = next((u for u in users.values() if (u.get("email") or "").lower() == (rep.get("email") or "").lower()), None)
    if not rep.get("email"):
        warn("Business Profile sem representante autorizado")
    elif not rep_user:
        err(f"representante {rep.get('firstName')} {rep.get('lastName')} <{rep.get('email')}> não é usuário da conta")
    else:
        if (rep_user.get("firstName"), rep_user.get("lastName"), rep_user.get("phone")) != \
                (rep.get("firstName"), rep.get("lastName"), rep.get("phoneNumber")):
            warn(f"usuário {rep_user.get('name')} difere do representante (nome/telefone)")
    if loc.get("timezone") in (None, "", "America/Sao_Paulo"):
        err(f"fuso da conta: {loc.get('timezone')}")
    if loc.get("enableMissedCallText"):
        err("missed-call text nativo ligado (duplica o SMS do workflow)")
    for cv in load(d / "custom_values.json", []):
        if str(cv.get("value") or "").strip().lower() in ("null", "none"):
            err(f"custom value {cv['name']} = {cv['value']!r}")

    m_flows = {w["name"]: w for w in workflows(model)}
    t_flows = workflows(d)
    for w in t_flows:
        name, status = w["name"], w["status"]
        raw = json.dumps(w.get("workflowData"))
        for ref in set(ID_RE.findall(raw)):
            if ref not in own and ref in foreign:
                (err if status == "published" else warn)(f"{name} [{status}]: {foreign[ref][1]} de {foreign[ref][0]} ({ref})")
        for step in (w.get("workflowData") or {}).get("templates") or []:
            for what, ids in user_refs(step):
                if not ids and what != "tarefa":
                    err(f"{name} [{status}] / {step.get('name')}: {what} sem usuário")
                for uid in ids:
                    if uid not in users and uid != "contact.assigned_user":  # = the contact's owner
                        err(f"{name} [{status}] / {step.get('name')}: {what} para usuário que não é da conta ({uid})")
            link = (step.get("attributes") or {}).get("overrideReviewLink")
            if link is not None and status == "published":
                place = re.search(r"placeid=([\w-]+)", link)
                if not place or place.group(1) not in place_ok:
                    err(f"{name} / {step.get('name')}: link de review {link or '(vazio)'!r} não é o Google da conta")
        trs = [t for t in w.get("triggers") or [] if not t.get("deleted")]
        if status == "published" and not any(t.get("active") for t in trs):
            err(f"{name}: publicado sem gatilho ativo")
        mw = m_flows.get(name)
        if not mw or w["_meta"].get("folder", "").startswith(PER_ACCOUNT) or name in PER_ACCOUNT_NAMES:
            continue
        if status != mw["status"]:
            (warn if name == "Review Request" else err)(f"{name}: {status} (modelo {mw['status']})")
        for k in SETTINGS:
            if w.get(k) != mw.get(k):
                warn(f"{name}: {k} = {w.get(k)!r} (modelo {mw.get(k)!r})")
        if status == "published" and len([t for t in trs if t.get("active")]) != \
                len([t for t in mw.get("triggers") or [] if not t.get("deleted") and t.get("active")]):
            warn(f"{name}: {len(trs)} gatilho(s), modelo tem outro número")
    for name, mw in m_flows.items():
        if mw["status"] == "published" and name not in {w["name"] for w in t_flows} and \
                not mw["_meta"].get("folder", "").startswith(PER_ACCOUNT) and name not in PER_ACCOUNT_NAMES:
            err(f"falta o workflow do modelo: {name}")

    stages = lambda p: [s["name"] for s in next((x for x in load(p / "pipelines.json", [])
                                                if x["name"] == "Pool Leads"), {}).get("stages") or []]
    if stages(d) != stages(model):
        err(f"etapas da Pool Leads diferentes do modelo: {stages(d)}")

    print(f"== {loc.get('name')} ({loc.get('id')}): {len(errs)} ERRO, {len(warns)} AVISO"
          f" · usuário {rep_user.get('name') if rep_user else '—'} · fuso {loc.get('timezone')}")
    for e in errs:
        print(f"   ERRO  {e}")
    for w in warns:
        print(f"   AVISO {w}")
    return len(errs)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--only", action="append", required=True)
    parser.add_argument("--model", default=PRIORITY["model"])
    parser.add_argument("--place", action="append", default=[], metavar="SLUG=PLACEID",
                        help="Google place of an account whose profile has none (from its review link)")
    args = parser.parse_args()
    load_dotenv()
    model = location_dirs([args.model])[0]
    foreign: dict[str, tuple[str, str]] = {}
    for other in location_dirs():
        for ref, kind in assets(other).items():
            foreign.setdefault(ref, (other.name, kind))
    extra = dict(p.split("=", 1) for p in args.place)
    bad = 0
    for d in location_dirs(args.only):
        if d == model:
            continue
        own_place = load(d / "location.json", {}).get("googlePlacesId")
        bad += check(d, model, foreign, {p for p in (own_place, extra.get(d.name)) if p})
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
