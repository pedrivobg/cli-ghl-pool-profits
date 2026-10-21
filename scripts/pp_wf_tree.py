#!/usr/bin/env python3
"""Workflows of a dumped sub-account as readable trees: settings, triggers, steps with the SMS/e-mail text. Read-only.

    ./.venv/bin/python scripts/pp_wf_tree.py the-pool-shack                      # every workflow
    ./.venv/bin/python scripts/pp_wf_tree.py the-pool-shack "Quote Sent" "Lost"  # names containing these

Reads dump/<slug>/ (pp_dump.py first). Used to map a client's change requests onto what is live.
"""
import html
import json
import re
import sys

from _common import DUMP

d = DUMP / sys.argv[1]; names = sys.argv[2:]
snip = {s["_id"]: s for s in json.loads((d / "snippets.json").read_text())}
pipes = json.loads((d / "pipelines.json").read_text())
stage = {s["id"]: f"{p['name']}/{s['name']}" for p in pipes for s in p.get("stages", [])}
fields = {c["id"]: c["name"] for c in json.loads((d / "custom_fields.json").read_text())}
idx = json.loads((d / "workflows" / "_index.json").read_text())

def txt(s, n=400):
    s = re.sub(r"<br\s*/?>|</p>", "\n", s or ""); s = html.unescape(re.sub(r"<[^>]+>", "", s))
    s = re.sub(r"\n\s*\n+", "\n", s).strip()
    return s if len(s) <= n else s[:n] + "…"

def cond(c):
    v = c.get("value"); v = stage.get(v, fields.get(v, v)) if isinstance(v, str) else v
    f = c.get("field") or c.get("conditionSubType") or c.get("title")
    return f"{c.get('title') or f} {c.get('operator')} {v}"

def desc(n):
    t, a = n.get("type"), n.get("attributes") or {}
    if t == "sms":
        s = snip.get(a.get("template_id")); body = s["template"].get("body") if s and isinstance(s.get("template"), dict) else (s or {}).get("template")
        return f"SMS «{txt(body if isinstance(body, str) else json.dumps(body), 600)}»" + ("" if s else f" [template {a.get('template_id')} ?] «{txt(a.get('body',''))}»")
    if t == "email":
        return f"EMAIL subj «{a.get('subject')}» «{txt(a.get('html') or a.get('body',''), 300)}»"
    if t == "wait":
        w = a.get("type"); sa = a.get("startAfter") or {}
        extra = f" window={a.get('window')}" if a.get("window") else ""
        if w == "reply": return f"WAIT for reply to {a.get('replyLabel')} up to {sa.get('value')} {sa.get('type')}{extra}"
        if w == "time": return f"WAIT {sa.get('value')} {sa.get('type')}{extra}"
        return f"WAIT {w} {json.dumps({k:a.get(k) for k in ('startAfter','conditions','segments') if a.get(k)},default=str)[:300]}{extra}"
    if t in ("if_else",):
        return "IF/ELSE"
    if t == "transition":
        segs = a.get("segments") or []
        cs = [cond(c) for s in segs for c in s.get("conditions", [])]
        return f"→ branch «{n.get('name')}» {a.get('type','')} " + " AND ".join(cs)
    if t in ("add_contact_tag", "remove_contact_tag"):
        return f"{t} {a.get('tags')}"
    if t == "internal_notification":
        k = a.get("type"); sub = a.get(k) or {}
        return f"NOTIFY {k} to {sub.get('selectedUser') or sub.get('to') or sub.get('userType')} «{txt(sub.get('body') or sub.get('subject') or '', 160)}»"
    if t in ("create_opportunity", "update_opportunity"):
        return f"{t} stage={stage.get(a.get('pipeline_stage_id') or a.get('stageId'), a.get('pipeline_stage_id'))}"
    if t in ("remove_from_workflow", "add_to_workflow", "remove_from_all_workflows"):
        return f"{t} {a.get('workflow_id') or a.get('workflowId') or a}"
    return f"{t} {json.dumps({k: v for k, v in a.items() if k not in ('isHybridAction','hybridActionType','cat','convertToMultipath','transitions','timePeriodInputMode','unitInputMode')}, default=str)[:250]}"

def walk(nodes, nid, ind, seen):
    while nid and nid not in seen:
        seen.add(nid); n = nodes.get(nid)
        if not n: print(ind + f"? {nid}"); return
        print(ind + f"- {n.get('name')}: {desc(n)}")
        nx = n.get("next")
        if isinstance(nx, list):
            for b in nx: walk(nodes, b, ind + "    ", seen)
            return
        nid = nx

for w in idx:
    if names and not any(x.lower() in w["name"].lower() for x in names): continue
    wf = json.loads((d / "workflows" / f"{w['id']}.json").read_text())
    print(f"\n=== {w['name']} [{wf['status']}] re-entry={wf.get('allowMultiple')} stopOnResponse={wf.get('stopOnResponse')} window={wf.get('window')} tz={wf.get('timezone')}")
    for t in wf.get("triggers") or []:
        if t.get("deleted"): continue
        print(f"  TRIGGER {t['type']} «{t.get('name')}» active={t.get('active')} :: " + "; ".join(cond(c) for c in t.get("conditions") or []))
    tpl = wf.get("workflowData", {}).get("templates") or []
    nodes = {n["id"]: n for n in tpl}
    roots = [n["id"] for n in tpl if not n.get("parentKey") and n.get("type") != "transition"]
    seen = set()
    for r in roots: walk(nodes, r, "  ", seen)
