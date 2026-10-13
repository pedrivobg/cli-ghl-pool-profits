#!/usr/bin/env python3
"""Diff each priority sub-account against the model (Southern Pool + Outdoors). Offline.

    ./.venv/bin/python scripts/pp_compare.py                       # model vs config/priority.json
    ./.venv/bin/python scripts/pp_compare.py --target "Bahama Blue"

Workflows are matched by name. For each one it reports what the target must
change to mirror the model: status (draft/published), triggers, message text,
waits, and workflows that exist on only one side. Pipeline stages are compared
by name and order. Business names and custom-value values are neutralised
before comparing text, so "Southern Pool" vs "Bahama Blue" is not a diff.

Writes reports/compare-<target>.md.
"""
from __future__ import annotations

import argparse
import difflib
import json
import re
from pathlib import Path

from _common import PRIORITY, REPORTS, location_dirs, slugify
from pp_audit import TAG_RE, load, snippets_map, steps_of, step_text


def canon(text: str, location: dict, cv_map: dict) -> str:
    text = TAG_RE.sub(" ", text or "")
    for value in sorted({v for v in cv_map.values() if v and len(v) > 3} | {location.get("name", "")},
                        key=len, reverse=True):
        if value:
            text = re.sub(re.escape(value), "{BUSINESS/VALUE}", text, flags=re.I)
    return re.sub(r"\s+", " ", text).strip()


def wf_key(name: str) -> str:
    return slugify(re.sub(r"\(.*?\)|copy|\bv\d+\b", "", name or ""))


class Account:
    def __init__(self, d: Path):
        self.dir = d
        self.location = load(d / "location.json", {})
        self.name = self.location.get("name", d.name)
        self.cv_map = {}
        for cv in load(d / "custom_values.json", []):
            m = re.search(r"custom_values\.([a-zA-Z0-9_]+)", cv.get("fieldKey") or "")
            if m:
                self.cv_map[m.group(1)] = (cv.get("value") or "").strip()
        self.snippets = snippets_map(d)
        self.index = load(d / "workflows" / "_index.json", [])
        self.by_key = {wf_key(w["name"]): w for w in self.index}
        self.ids = {}
        for f in load(d / "forms.json", []):
            self.ids[f.get("id")] = f"form:{f.get('name')}"
        for p in load(d / "pipelines.json", []):
            for s in p.get("stages") or []:
                self.ids[s.get("id")] = f"stage:{s.get('name')}"
        for c in load(d / "calendars.json", []):
            self.ids[c.get("id")] = f"calendar:{c.get('name')}"
        for w in self.index:
            self.ids[w["id"]] = f"workflow:{w['name']}"

    def workflow(self, meta: dict) -> dict:
        return load(self.dir / "workflows" / f"{meta['id']}.json", {})

    def stages(self) -> list[str]:
        out = []
        for p in load(self.dir / "pipelines.json", []):
            out += [f"{p.get('name')} → {s.get('name')}" for s in p.get("stages") or []]
        return out

    def describe_triggers(self, wf: dict) -> list[str]:
        out = []
        for t in wf.get("triggers") or []:
            if t.get("deleted"):
                continue
            blob = json.dumps(t.get("conditions") or [], ensure_ascii=False)
            refs = sorted({self.ids[i] for i in re.findall(r'"([A-Za-z0-9]{15,})"', blob) if i in self.ids})
            tags = sorted(set(re.findall(r'"value":\s*"([^"]{2,40})"', blob)) - set(self.ids))
            state = "" if t.get("active", True) else " [inativo]"
            out.append(f"{t.get('type')}{state} {refs or ''} {tags or ''}".strip())
        return sorted(out)

    def describe_steps(self, wf: dict) -> list[str]:
        out = []
        for s in steps_of(wf):
            stype = s.get("type", "")
            attrs = s.get("attributes") or {}
            if stype == "wait":
                st = attrs.get("startAfter") or {}
                out.append(f"wait {st.get('value')} {st.get('type')}" if st else "wait (condição)")
            elif stype in ("sms", "email", "internal_notification"):
                out.append(f"{stype}: {canon(step_text(s, self.snippets), self.location, self.cv_map)}")
            else:
                out.append(stype)
        return out


def compare(model: Account, target: Account) -> str:
    lines = [f"# {target.name} vs modelo ({model.name})", ""]

    ms, ts = model.stages(), target.stages()
    if ms != ts:
        lines += ["## Pipeline", "", "Modelo:", *[f"- {s}" for s in ms], "", "Alvo:",
                  *[f"- {s}" for s in ts], ""]

    only_model = [model.by_key[k] for k in model.by_key.keys() - target.by_key.keys()]
    only_target = [target.by_key[k] for k in target.by_key.keys() - model.by_key.keys()]
    if only_model:
        lines += ["## Existem só no modelo (criar/copiar no alvo)", ""]
        lines += [f"- {w['name']} ({w['status']})" for w in sorted(only_model, key=lambda w: w["name"])]
        lines.append("")
    if only_target:
        lines += ["## Existem só no alvo", ""]
        lines += [f"- {w['name']} ({w['status']})" for w in sorted(only_target, key=lambda w: w["name"])]
        lines.append("")

    lines += ["## Workflows em comum", ""]
    same = 0
    for key in sorted(model.by_key.keys() & target.by_key.keys(), key=lambda k: model.by_key[k]["name"]):
        mm, tm = model.by_key[key], target.by_key[key]
        mw, tw = model.workflow(mm), target.workflow(tm)
        diffs = []
        if mm["status"] != tm["status"]:
            diffs.append(f"- **status**: alvo `{tm['status']}` → modelo `{mm['status']}`")
        mt, tt = model.describe_triggers(mw), target.describe_triggers(tw)
        if mt != tt:
            diffs.append(f"- **gatilhos**\n  - modelo: {mt}\n  - alvo: {tt}")
        msteps, tsteps = model.describe_steps(mw), target.describe_steps(tw)
        if msteps != tsteps:
            diff = list(difflib.unified_diff(tsteps, msteps, "alvo", "modelo", lineterm="", n=0))
            diffs.append("- **passos** (− alvo, + modelo)\n```diff\n" + "\n".join(diff[2:]) + "\n```")
        if diffs:
            lines += [f"### {mm['name']}", *diffs, ""]
        else:
            same += 1
    lines.append(f"_{same} workflow(s) idênticos ao modelo._")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--model", default=PRIORITY["model"])
    parser.add_argument("--target", action="append")
    args = parser.parse_args()

    model_dirs = location_dirs([args.model])
    if not model_dirs:
        print(f"Modelo '{args.model}' não está em dump/ — rode pp_dump.py --priority.")
        return 1
    model = Account(model_dirs[0])
    REPORTS.mkdir(exist_ok=True)
    for d in location_dirs(args.target or PRIORITY["priority"]):
        if d == model.dir:
            continue
        target = Account(d)
        out = REPORTS / f"compare-{d.name}.md"
        out.write_text(compare(model, target))
        print(f"  {target.name} → {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
