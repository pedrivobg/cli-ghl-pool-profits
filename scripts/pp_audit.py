#!/usr/bin/env python3
"""Audit dumped sub-accounts for basic errors. Offline: reads dump/, never calls GHL.

    ./.venv/bin/python scripts/pp_audit.py                         # every dumped sub-account
    ./.venv/bin/python scripts/pp_audit.py --only "Southern Pool"  # one (repeatable)
    ./.venv/bin/python scripts/pp_audit.py --include-drafts        # drafts too

Only published workflows by default — that is what reaches leads today.

Checks (severity in brackets):
  [ALTA]  name of ANOTHER business (other sub-account, snapshot example, agency) in a message
  [ALTA]  {{custom_values.x}} used in a message but missing or empty in this sub-account
  [ALTA]  internal notification / task / assign step with no user selected
  [ALTA]  trigger or step pointing at a form, stage, calendar or workflow that does not exist
  [ALTA]  if/else or wait condition on a contact field the sub-account does not have (never true)
  [ALTA]  if/else "which trigger fired?" naming a trigger of another workflow (no branch ever matches)
  [ALTA]  SMS/email step with an empty body
  [MÉDIA] two published workflows with the same trigger (double sends, e.g. the Landing Page form)
  [MÉDIA] booking/calendar link sent to leads (the meeting dropped it from the baseline)
  [MÉDIA] step that adds to / goes to a workflow that is draft
  [INFO]  waits, links and the snapshot custom values still empty

Writes reports/audit-<slug>.md per sub-account and reports/audit-summary.md.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

from _common import REPORTS, location_dirs, slugify

CV_RE = re.compile(r"\{\{\s*custom_values\.([a-zA-Z0-9_]+)\s*\}\}")
# The email editor auto-links "values.booking" inside {{custom_values.booking_link}},
# which splits the merge field: the lead gets the raw braces and a dead link.
BROKEN_MERGE_RE = re.compile(r"\{\{\s*[a-z_]*<a[^>]*>|href=\"https?://values\.[a-z_]+\"", re.I)
URL_RE = re.compile(r"https?://[^\s\"'<>)]+")
TAG_RE = re.compile(r"<[^>]+>")

# Names that must never reach a lead of another business: snapshot examples,
# names seen leaking between accounts, and the agency itself.
KNOWN_FOREIGN = ["Crystal Clear Pools", "Clear Pool Solution", "Clear Pool Solutions",
                 "Pool Smart OC", "PoolSmart OC", "Pool Profits"]
GENERIC = {"pool service", "pool services", "pool care", "pool cleaning", "pool and spa",
           "pool & spa", "pools", "test", "demo", "snapshot"}

# Custom values the implementation guide (snapshot V9) asks to fill.
GUIDE_VALUES = ["friendly_business_name", "legal_business_name", "owner_first_name",
                "business_phone", "business_email", "business_address", "service_area",
                "booking_link", "calendar_link", "google_review_link", "weekly_service_price",
                "chemical_only_price", "onetime_clean_price", "green_to_clean_price",
                "logo_url", "client_domain_name", "privacy_policy", "terms_of_use",
                "a2p_verification_number"]
CALENDAR_VALUES = {"booking_link", "calendar_link"}

MESSAGE_TYPES = {"sms", "email", "internal_notification", "gmb", "messenger",
                 "instagram-dm", "review_request", "voicemail"}
USER_STEP_TYPES = {"internal_notification", "task-notification", "assign_user"}
USER_KEYS = ("users", "userIds", "user_ids", "assignedTo", "assigned_to", "userId",
             "user_id", "selectedUsers", "toUsers", "assignTo", "assignedOwners", "user_list", "selectedUser", "to")
TEXT_KEYS = ("body", "html", "message", "subject", "text", "title", "description", "content")


def load(path: Path, default):
    try:
        return json.loads(path.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def norm(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9& ]+", " ", (text or "").lower())).strip()


def strings(node, skip_ids: bool = True):
    """Every string leaf under node (ids and urls of assets skipped)."""
    if isinstance(node, dict):
        for key, value in node.items():
            if skip_ids and (key in ("id", "_id") or key.endswith("Id") or key.endswith("_id")):
                continue
            yield from strings(value, skip_ids)
    elif isinstance(node, list):
        for item in node:
            yield from strings(item, skip_ids)
    elif isinstance(node, str):
        yield node


def id_leaves(node):
    """Every string that sits under an id-like key (to resolve references)."""
    if isinstance(node, dict):
        for key, value in node.items():
            if isinstance(value, str) and (key in ("id", "value") or key.lower().endswith("id")):
                yield key, value
            else:
                yield from id_leaves(value)
    elif isinstance(node, list):
        for item in node:
            yield from id_leaves(item)


# ids of objects the dump does not fetch (documents/contract templates, ad accounts): not checkable here
UNDUMPED_ID_FIELDS = {"documentCreatedByTemplateId", "adAccountId"}


def field_conditions(node):
    """Contact-field ids read by if/else and wait conditions."""
    if isinstance(node, dict):
        if node.get("conditionType") == "contact_detail" and isinstance(node.get("conditionSubType"), str):
            yield node["conditionSubType"]
        for v in node.values():
            yield from field_conditions(v)
    elif isinstance(node, list):
        for v in node:
            yield from field_conditions(v)


def trigger_conditions(node):
    """Trigger ids an if/else compares with the trigger that fired."""
    if isinstance(node, dict):
        if node.get("conditionType") == "trigger" and node.get("conditionValue"):
            yield node["conditionValue"]
        for v in node.values():
            yield from trigger_conditions(v)
    elif isinstance(node, list):
        for v in node:
            yield from trigger_conditions(v)


def trigger_refs(trig: dict) -> tuple[list[str], list[str]]:
    """(referenced ids, referenced tags) of a trigger's conditions."""
    ids, tags = [], []
    for cond in trig.get("conditions") or []:
        field = str(cond.get("field") or "")
        values = cond.get("value")
        values = values if isinstance(values, list) else [values]
        values = [v for v in values if isinstance(v, str) and v]
        if field.lower().startswith("tag"):
            tags += values
        elif field.lower().endswith("id") and field not in UNDUMPED_ID_FIELDS:
            ids += values
    return sorted(ids), sorted(tags)


def steps_of(workflow: dict) -> list[dict]:
    return (workflow.get("workflowData") or {}).get("templates") or []


def step_text(step: dict, snippets: dict) -> str:
    attrs = step.get("attributes") or {}
    parts = [s for k in TEXT_KEYS for s in strings(attrs.get(k))] if attrs else []
    if not parts:
        parts = list(strings(attrs))
    for key in ("template_id", "templateId", "snippetId", "snippet_id"):
        ref = attrs.get(key)
        if ref and ref in snippets:
            parts.append(snippets[ref])
    return "\n".join(parts)


def snippets_map(loc_dir: Path) -> dict[str, str]:
    """Template id → plain text, so steps that point at a template are checked too."""
    out = {}
    for sn in load(loc_dir / "snippets.json", []):
        tpl = sn.get("template") if isinstance(sn.get("template"), dict) else sn
        body = " ".join(str(tpl.get(k) or "") for k in ("subject", "body", "html", "text"))
        out[sn.get("id") or sn.get("_id")] = TAG_RE.sub(" ", body)
    return out


def has_user(step: dict) -> bool:
    attrs = step.get("attributes") or {}

    def scan(node) -> bool:
        if isinstance(node, dict):
            for key, value in node.items():
                if key in USER_KEYS and value not in (None, "", [], {}):
                    return True
                if key in ("userType", "user_type", "sendTo") and value in (
                        "all", "account", "admins", "all_users", "assign"):
                    return True
                if scan(value):
                    return True
        elif isinstance(node, list):
            return any(scan(i) for i in node)
        return False

    return scan(attrs)


def foreign_names(location: dict, others_cv: dict[str, str]) -> list[str]:
    own = norm(location.get("name", ""))
    own_words = set(own.split())
    names = set(location.get("_agency_location_names") or []) | set(KNOWN_FOREIGN)
    names |= set(others_cv.values())
    out = []
    for name in names:
        n = norm(name)
        if not n or n == own or n in GENERIC or len(n) < 8:
            continue
        if n in own or set(n.split()) <= own_words:
            continue
        out.append(name)
    return sorted(out, key=len, reverse=True)


def audit_location(loc_dir: Path, include_drafts: bool, all_dirs: list[Path]) -> dict:
    location = load(loc_dir / "location.json", {})
    cvs = load(loc_dir / "custom_values.json", [])
    cv_map: dict[str, str] = {}
    for cv in cvs:
        m = CV_RE.search(cv.get("fieldKey") or "")
        key = m.group(1) if m else slugify(cv.get("name", "")).replace("-", "_")
        value = (cv.get("value") or "").strip()
        cv_map[key] = "" if value.lower() in ("null", "none") else value  # the onboarding automation writes these

    # friendly names of the OTHER dumped sub-accounts are foreign here too
    others_cv = {}
    for other in all_dirs:
        if other == loc_dir:
            continue
        for cv in load(other / "custom_values.json", []):
            if "friendly_business_name" in (cv.get("fieldKey") or "") and cv.get("value"):
                others_cv[other.name] = cv["value"]
    foreign = foreign_names(location, others_cv)
    # Google places of the OTHER dumped sub-accounts (a review link copied from the model)
    other_places = {load(o / "location.json", {}).get("googlePlacesId"): o.name for o in all_dirs if o != loc_dir}
    other_places.pop(None, None)
    other_places.pop("", None)
    foreign_res = [(n, re.compile(r"(?<![a-z0-9])" + re.escape(norm(n)) + r"(?![a-z0-9])"))
                   for n in foreign]

    snippets = snippets_map(loc_dir)

    forms = {f.get("id") or f.get("_id"): f.get("name", "") for f in load(loc_dir / "forms.json", [])}
    stages, pipelines = {}, {}
    for p in load(loc_dir / "pipelines.json", []):
        pipelines[p.get("id")] = p.get("name", "")
        for s in p.get("stages") or []:
            stages[s.get("id")] = f"{p.get('name')} → {s.get('name')}"
    calendars = {c.get("id"): c.get("name", "") for c in load(loc_dir / "calendars.json", [])}
    location_tags = {str(t.get("name", "")).lower() for t in load(loc_dir / "tags.json", [])}
    fields = {f.get("id") for f in load(loc_dir / "custom_fields.json", [])}
    index = load(loc_dir / "workflows" / "_index.json", [])
    wf_by_id = {w["id"]: w for w in index}
    known_ids = {**forms, **stages, **pipelines, **calendars,
                 **{k: v["name"] for k, v in wf_by_id.items()}}

    findings: list[dict] = []
    waits: list[str] = []
    links: dict[str, set] = defaultdict(set)
    trigger_keys: dict[str, list[str]] = defaultdict(list)

    def add(sev, wf, step, msg):
        findings.append({"sev": sev, "workflow": wf, "step": step, "msg": msg})

    for meta in index:
        if meta["status"] != "published" and not include_drafts:
            continue
        wf = load(loc_dir / "workflows" / f"{meta['id']}.json", {})
        wname = f"{meta['name']}" + ("" if meta["status"] == "published" else " (draft)")

        for trig in wf.get("triggers") or []:
            if trig.get("deleted"):
                continue
            refs, trig_tags = trigger_refs(trig)
            label = trig.get("name") or trig.get("type")
            ttype = trig.get("type", "?")
            if trig.get("active") is False:
                add("INFO", wname, label, "trigger inativo")
            named = [known_ids.get(r, f"⚠ id inexistente {r}") for r in refs]
            for r in refs:
                if r not in known_ids:
                    add("ALTA", wname, label, f"trigger aponta para id que não existe nesta sub-conta: {r}")
            for t in trig_tags:
                if t.lower() not in location_tags:
                    add("MÉDIA", wname, label, f"trigger usa a tag '{t}', que não existe na sub-conta "
                                               "(nada vai disparar)")
            for n in named:
                if "landing page" in n.lower() and not re.search(r"ads|adword|facebook", meta["name"] + meta.get("folder", ""), re.I):
                    add("MÉDIA", wname, label, f"trigger no form '{n}' (form das campanhas de Ads) "
                                               "num workflow que não é de Ads")
            if meta["status"] == "published" and trig.get("active", True):
                extra = [json.dumps(c.get("value"), ensure_ascii=False) for c in trig.get("conditions") or []
                         if not str(c.get("field", "")).lower().endswith("id") and "tag" not in str(c.get("field", "")).lower()]
                own = [trig.get("id", "")] if ttype == "inbound_webhook" else []  # each webhook has its own URL
                trigger_keys[f"{ttype} | " + ", ".join(named + trig_tags + extra + own)].append(meta["name"])

        own_triggers = {t.get("id") for t in wf.get("triggers") or [] if not t.get("deleted")}
        for step in steps_of(wf):
            stype = step.get("type", "")
            sname = step.get("name") or stype
            attrs = step.get("attributes") or {}
            text = step_text(step, snippets)
            plain = norm(TAG_RE.sub(" ", text))

            raw = json.dumps(attrs, ensure_ascii=False).replace('\\"', '"')
            if BROKEN_MERGE_RE.search(raw):
                add("ALTA", wname, sname, "merge field quebrado pelo autolink do editor "
                                          "(ex.: {{custom_<a href=http://values.booking>…) — lead recebe as chaves cruas")
            if stype in MESSAGE_TYPES or stype in ("sms", "email"):
                for name, rx in foreign_res:
                    if stype == "internal_notification" and norm(name) == "pool profits":
                        continue  # the agency's name in a note to the owner is fine
                    if rx.search(plain):
                        add("ALTA", wname, sname, f"menciona outro negócio: “{name}”")
                for key in sorted(set(CV_RE.findall(text))):
                    if key not in cv_map:
                        add("ALTA", wname, sname, f"usa {{{{custom_values.{key}}}}} que NÃO existe nesta sub-conta")
                    elif not cv_map[key]:
                        add("ALTA", wname, sname, f"usa {{{{custom_values.{key}}}}} que está VAZIO → mensagem sai quebrada")
                    elif key in CALENDAR_VALUES:
                        add("MÉDIA", wname, sname, f"envia link de calendário ({key} = {cv_map[key][:60]}) — "
                                                  "confirmar se o cliente usa o calendário do GHL")
                for url in URL_RE.findall(text):
                    if not re.match(r"https?://values\.", url):
                        links[url].add(meta["name"])
                if stype in ("sms", "email") and not text.strip():
                    add("ALTA", wname, sname, "mensagem sem corpo")

            if step.get("incompleteData"):
                add("MÉDIA", wname, sname, "GHL marca este passo como incompleto — abrir no builder e conferir")
            if stype in USER_STEP_TYPES and not has_user(step):
                add("ALTA", wname, sname, "nenhum usuário selecionado (notificação/tarefa não chega a ninguém)")

            if stype == "wait":
                start = attrs.get("startAfter") or {}
                if start:
                    waits.append(f"{meta['name']} → {sname}: {start.get('value')} {start.get('type')}")

            if stype in ("add_to_workflow", "remove_from_workflow", "goto"):
                for _, ref in id_leaves(attrs):
                    if ref in wf_by_id and wf_by_id[ref]["status"] != "published" and stype == "add_to_workflow":
                        add("MÉDIA", wname, sname, f"adiciona ao workflow '{wf_by_id[ref]['name']}' que está em draft")

            for ref in trigger_conditions(attrs):
                if own_triggers and ref not in own_triggers:  # copied from another workflow (pp_trigger_ref_fix.py)
                    add("ALTA", wname, sname, f"if/else por gatilho aponta para gatilho de outro workflow ({ref}) — "
                                              "nenhum ramo bate")

            for sub in field_conditions(attrs):
                if fields and re.fullmatch(r"[A-Za-z0-9]{20}", sub) and sub not in fields:  # e.g. the snapshot source's NPS Score (pp_review_fix.py)
                    add("ALTA", wname, sname, f"condição em campo que não existe nesta sub-conta ({sub}) — nunca é verdadeira")

            for key, ref in id_leaves(attrs):
                if key.lower() in ("pipelinestageid", "stageid", "pipeline_stage_id") and ref and ref not in stages:
                    add("ALTA", wname, sname, f"move para etapa de pipeline inexistente ({ref})")
                if key.lower() in ("calendarid", "calendar_id") and ref and ref not in calendars:
                    add("ALTA", wname, sname, f"usa calendário inexistente ({ref})")

            own_place = location.get("googlePlacesId")
            for place in re.findall(r"placeid=([\w-]+)", json.dumps(attrs)):
                if own_place and place != own_place:
                    add("ALTA", wname, sname, f"link de review do Google aponta para OUTRO negócio (placeid={place}, "
                                              f"o desta conta é {own_place})")
                elif not own_place and place in other_places:
                    add("ALTA", wname, sname, f"link de review do Google é o de {other_places[place]} (placeid={place})")

    for key, names in trigger_keys.items():
        if len(names) > 1:
            add("INFO" if key.startswith("contact_tag | ") else "MÉDIA", " + ".join(sorted(names)), key,
                "mesmo gatilho em mais de um workflow publicado — confirmar que não gera envio em dobro")

    empty_cvs = [k for k in GUIDE_VALUES if not cv_map.get(k)]
    order = {"ALTA": 0, "MÉDIA": 1, "INFO": 2}
    findings.sort(key=lambda f: (order[f["sev"]], f["workflow"], f["step"]))
    return {"location": location, "dir": loc_dir.name, "index": index, "findings": findings,
            "waits": waits, "links": {u: sorted(v) for u, v in links.items()},
            "empty_cvs": empty_cvs, "cv_map": cv_map, "foreign_checked": len(foreign)}


def render(result: dict) -> str:
    loc = result["location"]
    index = result["index"]
    pub = [w for w in index if w["status"] == "published"]
    lines = [f"# Auditoria — {loc.get('name')}", "",
             f"`{loc.get('id')}` · {len(index)} workflows, {len(pub)} publicados · "
             f"{result['foreign_checked']} nomes de outros negócios verificados", ""]
    counts = defaultdict(int)
    for f in result["findings"]:
        counts[f["sev"]] += 1
    lines += [f"**ALTA {counts['ALTA']} · MÉDIA {counts['MÉDIA']} · INFO {counts['INFO']}**", ""]

    if result["findings"]:
        lines += ["## Achados", "", "| Sev | Workflow | Passo | Problema |", "|---|---|---|---|"]
        for f in result["findings"]:
            cells = [f["sev"], f["workflow"], f["step"], f["msg"]]
            lines.append("| " + " | ".join(str(c).replace("|", "/").replace("\n", " ") for c in cells) + " |")
        lines.append("")
    if result["empty_cvs"]:
        lines += ["## Custom values do snapshot ainda vazios", "",
                  ", ".join(f"`{k}`" for k in result["empty_cvs"]), ""]
    lines += ["## Workflows publicados", ""]
    for w in sorted(pub, key=lambda w: (w.get("folder") or "", w["name"])):
        lines.append(f"- {w.get('folder') or '—'} / {w['name']}")
    if result["waits"]:
        lines += ["", "## Esperas (publicados)", ""] + [f"- {w}" for w in result["waits"]]
    if result["links"]:
        lines += ["", "## Links enviados", ""]
        lines += [f"- {u} — {', '.join(v)}" for u, v in sorted(result["links"].items())]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--only", action="append", help="sub-account name (repeatable)")
    parser.add_argument("--include-drafts", action="store_true")
    args = parser.parse_args()

    all_dirs = location_dirs()
    dirs = location_dirs(args.only)
    if not dirs:
        print("Nenhuma sub-conta em dump/ — rode scripts/pp_dump.py antes.")
        return 1
    REPORTS.mkdir(exist_ok=True)
    summary = ["# Auditoria — resumo", "", "| Sub-conta | Publicados | ALTA | MÉDIA | Relatório |",
               "|---|---|---|---|---|"]
    for d in dirs:
        result = audit_location(d, args.include_drafts, all_dirs)
        out = REPORTS / f"audit-{d.name}.md"
        out.write_text(render(result))
        sev = defaultdict(int)
        for f in result["findings"]:
            sev[f["sev"]] += 1
        pub = sum(1 for w in result["index"] if w["status"] == "published")
        summary.append(f"| {result['location'].get('name')} | {pub} | {sev['ALTA']} | {sev['MÉDIA']} | {out.name} |")
        print(f"  {result['location'].get('name')}: ALTA {sev['ALTA']}, MÉDIA {sev['MÉDIA']} → {out}")
    (REPORTS / "audit-summary.md").write_text("\n".join(summary) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
