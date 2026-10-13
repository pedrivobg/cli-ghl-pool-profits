#!/usr/bin/env python3
"""Mirror the model sub-account (Southern Pool + Outdoors) onto a snapshot-based target.

    ./.venv/bin/python scripts/pp_mirror.py --target "Bahama Blue"            # plan only
    ./.venv/bin/python scripts/pp_mirror.py --target "Bahama Blue" --apply    # write
    ./.venv/bin/python scripts/pp_mirror.py --target "The Pool Keepers" --apply --no-publish

Reads dump/ for both sides (run pp_dump.py first) and re-reads the live object
before every write; every object written is first saved to backup/<slug>/.

What it does, in order:
  1. Duplicate snapshot workflows (same name loaded twice): keep the oldest, draft the rest.
  2. Pipeline "Pool Leads": add the model's stages that are missing (No Response,
     No Show, Won by service type), rename "🏆 Won" → "🏆 Won - Weekly Pool Service",
     and order like the model. No stage is ever removed.
  3. Templates used by the mirrored workflows: create the missing ones, update text.
  4. CONTENT workflows: steps and triggers copied from the model, every id remapped
     to the target (pipeline, stages, templates, forms, users, workflows).
     "Incoming Call" / "New Lead - Initial SMS" are renamed to their Missed versions,
     and "Answered Incoming Call To Pipeline" is created.
  5. Website Form Fill To Pipeline: steps copied; its form trigger is left alone —
     which forms feed it depends on the account, so run pp_forms.py afterwards.
  6. Status of every other model workflow mirrored (draft/published), except
     08 Paid Ads, which is left as it is (ads tracking is per client).

Full sequence for an account: pp_dump → pp_mirror --apply → pp_dump →
pp_forms --apply → pp_fix --drop-booking --apply → pp_dump → pp_audit/pp_compare.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from collections import Counter, defaultdict

from _common import PRIORITY, ROOT, load_dotenv, location_dirs
from pp_audit import load

from cli_anything.gohighlevel.utils.agency import BACKEND, SERVICES, Agency, GHLError

BACKUP = ROOT / "backup"

CONTENT = [
    "Answered Incoming Call To Pipeline",
    "Missed Incoming Call To Pipeline",
    "Missed New Lead - Initial SMS Follow-up",
    "SMS Customer Reply to pipeline",
    "No Response Follow-up",
    "No-Show Follow-up",
    "Quote Sent Follow-up",
    "Won Stage",
    "Review Request",
    "Contact Created -> add owner",
]
STEPS_ONLY = ["Website Form Fill To Pipeline"]
ALIASES = {
    "Missed Incoming Call To Pipeline": ["Incoming Call To Pipeline"],
    "Missed New Lead - Initial SMS Follow-up": ["New Lead - Initial SMS Follow-up"],
}
STAGE_ALIASES = {"🏆 Won - Weekly Pool Service": ["🏆 Won"]}
SKIP_STATUS_FOLDERS = ("08 Paid Ads",)
TRIGGER_DROP = ("id", "_id", "date_added", "date_updated", "deleted", "origin_id",
                "company_id", "company_age", "last_conditions_change_at", "belongs_to")


def norm(name: str) -> str:
    return re.sub(r"\s+", " ", (name or "").strip().lower())


class Side:
    """One sub-account as dumped."""

    def __init__(self, d):
        self.dir = d
        self.location = load(d / "location.json", {})
        self.loc = self.location["id"]
        self.name = self.location.get("name")
        self.index = load(d / "workflows" / "_index.json", [])
        self.snippets = load(d / "snippets.json", [])
        self.forms = load(d / "forms.json", [])
        self.pipelines = load(d / "pipelines.json", [])
        self.users = load(d / "users.json", [])
        self.calendars = load(d / "calendars.json", [])
        self.custom_fields = load(d / "custom_fields.json", [])

    def wf(self, wid: str) -> dict:
        return load(self.dir / "workflows" / f"{wid}.json", {})

    def pool_pipeline(self) -> dict:
        for p in self.pipelines:
            if "pool leads" in norm(p.get("name")):
                return p
        return self.pipelines[0] if self.pipelines else {}


class Mirror:
    def __init__(self, agency: Agency | None, model: Side, target: Side, apply: bool, publish: bool):
        self.agency, self.m, self.t = agency, model, target
        self.apply, self.publish = apply, publish
        self.ids: dict[str, str] = {model.loc: target.loc}
        self.log: list[str] = []
        self.problems: list[str] = []
        self.stamp = time.strftime("%Y%m%d-%H%M%S")
        self.bdir = BACKUP / target.dir.name
        # canonical target workflow per name (oldest copy wins)
        groups = defaultdict(list)
        for w in target.index:
            groups[norm(w["name"])].append(w)
        self.dupes = []
        self.t_by_name = {}
        for key, ws in groups.items():
            ws.sort(key=lambda w: target.wf(w["id"]).get("createdAt", ""))
            self.t_by_name[key] = ws[0]
            self.dupes += ws[1:]

    # ── helpers ────────────────────────────────────────────────────────────

    def say(self, msg: str) -> None:
        self.log.append(msg)
        print(msg)

    def backup(self, kind: str, obj_id: str, data) -> None:
        self.bdir.mkdir(parents=True, exist_ok=True)
        (self.bdir / f"{kind}-{obj_id}-{self.stamp}.json").write_text(
            json.dumps(data, ensure_ascii=False, indent=1))

    def target_wf(self, model_name: str) -> dict | None:
        for name in [model_name, *ALIASES.get(model_name, [])]:
            if norm(name) in self.t_by_name:
                return self.t_by_name[norm(name)]
        return None

    def put_workflow(self, wid: str, name: str, status: str, steps: list | None = None) -> dict:
        live = self.agency.workflow(self.t.loc, wid)
        self.backup("workflow", wid, live)
        body = {"name": name, "version": live.get("version", 1), "status": status,
                "parentId": live.get("parentId"),
                "workflowData": {"templates": steps if steps is not None
                                 else (live.get("workflowData") or {}).get("templates") or []}}
        self.agency.call("PUT", BACKEND, f"/workflow/{self.t.loc}/{wid}", body=body)
        after = self.agency.workflow(self.t.loc, wid)
        if after.get("status") != status or after.get("name") != name:
            self.problems.append(f"{name}: depois do PUT ficou status={after.get('status')} nome={after.get('name')}")
        return after

    # ── 1. duplicates ──────────────────────────────────────────────────────

    def dedupe(self) -> None:
        live_dupes = [w for w in self.dupes if w["status"] == "published"]
        if not live_dupes:
            return
        self.say(f"\n[1] {len(live_dupes)} workflows duplicados publicados → draft (mantida a cópia mais antiga)")
        for w in live_dupes:
            self.say(f"    draft: {w['name']} ({w['id'][:8]}, cópia de {self.t.wf(w['id']).get('createdAt', '')[:10]})")
            if self.apply:
                self.put_workflow(w["id"], w["name"], "draft")

    # ── 2. pipeline ────────────────────────────────────────────────────────

    def pipeline(self) -> None:
        mp, tp = self.m.pool_pipeline(), self.t.pool_pipeline()
        if not tp:
            self.problems.append("alvo sem pipeline Pool Leads")
            return
        self.ids[mp["id"]] = tp["id"]
        t_by = {norm(s["name"]): s for s in tp["stages"]}
        keep = ("id", "name", "showInFunnel", "showInPieChart", "color")
        new, used = [], set()
        for ms in mp["stages"]:
            found = None
            for name in [ms["name"], *STAGE_ALIASES.get(ms["name"], [])]:
                if norm(name) in t_by and t_by[norm(name)]["id"] not in used:
                    found = t_by[norm(name)]
                    break
            if found:
                used.add(found["id"])
                stage = {k: found[k] for k in keep if k in found}
                stage["name"] = ms["name"]
            else:
                stage = {k: ms[k] for k in keep if k in ms and k != "id"}
            new.append(stage)
        # stages only the target has stay, right after Recurring Customer
        extras = [{k: s[k] for k in keep if k in s} for s in tp["stages"] if s["id"] not in used]
        if extras:
            at = next((i + 1 for i, s in enumerate(new) if "recurring" in norm(s["name"])), len(new))
            new[at:at] = extras
        for i, s in enumerate(new):
            s["position"] = i
        before = [s["name"] for s in tp["stages"]]
        after = [s["name"] for s in new]
        if before != after:
            self.say("\n[2] Pipeline Pool Leads\n    antes:  " + " | ".join(before) + "\n    depois: " + " | ".join(after))
            if self.apply:
                live = next(p for p in self.agency.pipelines(self.t.loc) if p["id"] == tp["id"])
                self.backup("pipeline", tp["id"], live)
                self.agency.call("PUT", SERVICES, f"/opportunities/pipelines/{tp['id']}",
                                 body={"name": live["name"], "stages": new})
                for _ in range(10):  # GHL reads lag a few seconds behind the write
                    tp = next(p for p in self.agency.pipelines(self.t.loc) if p["id"] == tp["id"])
                    if [s["name"] for s in tp["stages"]] == after:
                        break
                    time.sleep(3)
                self.t.pipelines = [tp if p["id"] == tp["id"] else p for p in self.t.pipelines]
        t_names = {norm(s["name"]): s["id"] for s in tp["stages"]}
        for ms in mp["stages"]:
            if norm(ms["name"]) in t_names:
                self.ids[ms["id"]] = t_names[norm(ms["name"])]
            elif not self.apply:
                self.ids[ms["id"]] = f"<nova etapa {ms['name']}>"
            else:
                self.problems.append(f"etapa '{ms['name']}' não apareceu no alvo")

    # ── id maps ────────────────────────────────────────────────────────────

    def map_assets(self) -> None:
        t_forms = defaultdict(list)
        for f in self.t.forms:
            t_forms[norm(f["name"])].append(f.get("_id") or f.get("id"))
        for f in self.m.forms:
            cands = t_forms.get(norm(f["name"]))
            if cands:
                self.ids[f.get("_id") or f.get("id")] = cands[0]
        t_cal = {norm(c["name"]): c["id"] for c in self.t.calendars}
        for c in self.m.calendars:
            if norm(c["name"]) in t_cal:
                self.ids[c["id"]] = t_cal[norm(c["name"])]
        t_cf = {norm(c.get("fieldKey") or c["name"]): c["id"] for c in self.t.custom_fields}
        for c in self.m.custom_fields:
            key = norm(c.get("fieldKey") or c["name"])
            if key in t_cf:
                self.ids[c["id"]] = t_cf[key]
        # users: the target's main user (most referenced in its workflows, else first admin)
        t_user_ids = [u["id"] for u in self.t.users]
        counts = Counter()
        for w in self.t.index:
            raw = (self.t.dir / "workflows" / f"{w['id']}.json").read_text()
            for uid in t_user_ids:
                counts[uid] += raw.count(uid)
        main = counts.most_common(1)[0][0] if counts and counts.most_common(1)[0][1] else (t_user_ids or [""])[0]
        if len(t_user_ids) > 1:
            names = {u["id"]: u.get("name") for u in self.t.users}
            self.say(f"    usuário principal escolhido: {names.get(main)} (de {len(t_user_ids)} usuários)")
        for u in self.m.users:
            self.ids[u["id"]] = main
        self.main_user = main

    def map_workflows(self) -> None:
        for w in self.m.index:
            tw = self.target_wf(w["name"])
            if tw:
                self.ids[w["id"]] = tw["id"]

    def remap(self, obj):
        raw = json.dumps(obj, ensure_ascii=False)
        for src in sorted(self.ids, key=len, reverse=True):
            if src and self.ids[src]:
                raw = raw.replace(src, self.ids[src])
        return json.loads(raw)

    def leftovers(self, obj) -> list[str]:
        raw = json.dumps(obj, ensure_ascii=False)
        model_ids = {self.m.loc, *(u["id"] for u in self.m.users),
                     *(s["_id"] for s in self.m.snippets),
                     *((f.get("_id") or f.get("id")) for f in self.m.forms),
                     *(c["id"] for c in self.m.calendars), *(c["id"] for c in self.m.custom_fields),
                     *(w["id"] for w in self.m.index)}
        for p in self.m.pipelines:
            model_ids.add(p["id"])
            model_ids |= {s["id"] for s in p["stages"]}
        return sorted(i for i in model_ids if i and i in raw and self.ids.get(i) != i)

    # ── 3. templates ───────────────────────────────────────────────────────

    def templates(self, names: list[str]) -> None:
        m_sn = {s["_id"]: s for s in self.m.snippets}
        t_sn = {norm(s["name"]): s for s in self.t.snippets}
        needed = {}
        for name in names:
            mw = next((w for w in self.m.index if w["name"] == name), None)
            if not mw:
                continue
            for step in (self.m.wf(mw["id"]).get("workflowData") or {}).get("templates") or []:
                ref = (step.get("attributes") or {}).get("template_id")
                if ref in m_sn:
                    needed[ref] = m_sn[ref]
        header = False
        for sid, ms in needed.items():
            ts = t_sn.get(norm(ms["name"]))
            if ts and ts.get("template") == ms.get("template"):
                self.ids[sid] = ts["_id"]
                continue
            if not header:
                self.say("\n[3] Templates")
                header = True
            text = (ms.get("template") or {}).get("body") or ""
            if re.search(r"southern|brett", json.dumps(ms.get("template")), re.I):
                self.problems.append(f"template '{ms['name']}' do modelo tem texto específico da Southern — pulado")
                continue
            if ts:
                self.say(f"    atualiza '{ms['name']}': {re.sub(r'<[^>]+>', ' ', text)[:140]}")
                self.ids[sid] = ts["_id"]
                if self.apply:
                    self.backup("snippet", ts["_id"], ts)
                    self.agency.call("PUT", BACKEND, f"/snippets/{self.t.loc}/{ts['_id']}",
                                     body={"name": ts["name"], "type": ts["type"], "template": ms["template"]})
            else:
                self.say(f"    cria '{ms['name']}'")
                if self.apply:
                    res = self.agency.call("POST", BACKEND, f"/snippets/{self.t.loc}",
                                           body={"name": ms["name"], "type": ms["type"], "template": ms["template"]})
                    self.ids[sid] = (res.get("snippet") or res).get("id") or (res.get("snippet") or res).get("_id")
                else:
                    self.ids[sid] = f"<novo template {ms['name']}>"

    # ── 4/5. workflows ─────────────────────────────────────────────────────

    def ensure_created(self) -> None:
        for name in CONTENT + STEPS_ONLY:
            if self.target_wf(name):
                continue
            mw = next((w for w in self.m.index if w["name"] == name), None)
            if not mw:
                continue
            sibling = next((w for w in self.t.index if w.get("folder") == mw.get("folder")), None) \
                or self.target_wf("Missed Incoming Call To Pipeline") or {}
            parent = self.t.wf(sibling["id"]).get("parentId") if sibling else None
            self.say(f"\n[4] cria workflow '{name}' (pasta {sibling.get('folder', '—')})")
            if self.apply:
                res = self.agency.call("POST", BACKEND, f"/workflow/{self.t.loc}",
                                       body={"name": name, "parentId": parent, "status": "draft"})
                wid = res.get("id") or res.get("_id")
                created = {"id": wid, "name": name, "status": "draft"}
            else:
                created = {"id": f"<novo {name}>", "name": name, "status": "draft"}
            self.t_by_name[norm(name)] = created
            self.ids[mw["id"]] = created["id"]

    def triggers(self, mw: dict, tw: dict, model_wf: dict, first_step: str | None) -> None:
        m_tr = [t for t in model_wf.get("triggers") or [] if not t.get("deleted")]
        t_tr = [] if not self.apply or tw["id"].startswith("<") else \
            [t for t in self.agency.triggers(self.t.loc, tw["id"]) if not t.get("deleted")]
        if not self.apply:
            t_tr = [t for t in self.t.wf(tw["id"]).get("triggers") or [] if not t.get("deleted")] \
                if not tw["id"].startswith("<") else []
        for i, mt in enumerate(m_tr):
            body = self.remap({k: v for k, v in mt.items() if k not in TRIGGER_DROP})
            body.update({"workflowId": tw["id"], "workflow_id": tw["id"], "location_id": self.t.loc,
                         "actions": [{"workflow_id": tw["id"], "type": "add_to_workflow"}]})
            if first_step and not body.get("targetActionId"):
                body["targetActionId"] = first_step
            left = self.leftovers(body)
            if left:
                self.problems.append(f"{mw['name']}: gatilho com ids do modelo sem par no alvo {left}")
                continue
            if not self.apply:
                continue
            if i < len(t_tr):
                self.backup("trigger", t_tr[i]["id"], t_tr[i])
                self.agency.call("PUT", BACKEND, f"/workflow/{self.t.loc}/trigger/{t_tr[i]['id']}",
                                 body={**body, "id": t_tr[i]["id"]})
            else:
                res = self.agency.call("POST", BACKEND, f"/workflow/{self.t.loc}/trigger", body=body)
                if res.get("id"):
                    self.agency.call("PUT", BACKEND, f"/workflow/{self.t.loc}/trigger/{res['id']}",
                                     body={**body, "id": res["id"]})
        for extra in t_tr[len(m_tr):]:
            if self.apply:
                self.backup("trigger", extra["id"], extra)
                self.agency.call("DELETE", BACKEND, f"/workflow/{self.t.loc}/trigger/{extra['id']}")
        self.say(f"      gatilhos: {len(m_tr)} do modelo" +
                 (f", {len(t_tr) - len(m_tr)} sobrando no alvo → removidos (backup salvo)" if len(t_tr) > len(m_tr) else ""))

    def trigger_tags(self) -> None:
        have = {norm(t.get("name")) for t in load(self.t.dir / "tags.json", [])}
        want = set()
        for name in CONTENT:
            mw = next((w for w in self.m.index if w["name"] == name), None)
            for tr in (self.m.wf(mw["id"]).get("triggers") or []) if mw else []:
                for c in tr.get("conditions") or []:
                    if str(c.get("field", "")).lower().startswith("tag"):
                        vals = c["value"] if isinstance(c.get("value"), list) else [c.get("value")]
                        want |= {v for v in vals if isinstance(v, str) and v}
        missing = sorted(t for t in want if norm(t) not in have)
        if missing:
            self.say(f"\n    cria tags usadas em gatilhos: {missing}")
            if self.apply:
                for tag in missing:
                    self.agency.call("POST", BACKEND, f"/workflow/{self.t.loc}/tags/create", body={"tag": tag})

    def content(self) -> None:
        self.trigger_tags()
        self.say("\n[4] Workflows copiados do modelo (passos + gatilhos)")
        for name in CONTENT + STEPS_ONLY:
            mw = next((w for w in self.m.index if w["name"] == name), None)
            tw = self.target_wf(name)
            if not mw or not tw:
                self.problems.append(f"{name}: sem par (modelo={bool(mw)}, alvo={bool(tw)})")
                continue
            model_wf = self.m.wf(mw["id"])
            steps = self.remap((model_wf.get("workflowData") or {}).get("templates") or [])
            left = self.leftovers(steps)
            if left:
                self.problems.append(f"{name}: passos com ids do modelo sem par no alvo {left} — não copiado")
                continue
            status = mw["status"] if (self.publish or mw["status"] == "draft") else tw.get("status", "draft")
            rename = f" (renomeado de '{tw['name']}')" if tw["name"] != name else ""
            self.say(f"    {name}{rename}: {len(steps)} passos, status → {status}")
            if self.apply:
                self.put_workflow(tw["id"], name, status, steps)
            if name in STEPS_ONLY:
                # Which forms feed this workflow depends on the account's own
                # forms and on who else listens to them: scripts/pp_forms.py.
                self.say("      gatilho de forms: mantido — rodar pp_forms.py depois")
            else:
                self.triggers(mw, tw, model_wf, steps[0]["id"] if steps else None)

    # ── 6. status ──────────────────────────────────────────────────────────

    def statuses(self) -> None:
        header = False
        for mw in self.m.index:
            if mw["name"] in CONTENT + STEPS_ONLY:
                continue
            tw = self.target_wf(mw["name"])
            if not tw:
                continue
            if mw.get("folder", "").startswith(SKIP_STATUS_FOLDERS):
                continue
            want = mw["status"]
            if want == "published" and not self.publish:
                continue
            if tw["status"] == want:
                continue
            if not header:
                self.say("\n[6] Status")
                header = True
            self.say(f"    {mw['name']}: {tw['status']} → {want}")
            if self.apply:
                self.put_workflow(tw["id"], tw["name"], want)

    def run(self) -> None:
        print(f"\n===== {self.t.name}  ←  modelo {self.m.name}  ({'APLICANDO' if self.apply else 'plano'})")
        self.dedupe()
        self.pipeline()
        self.map_assets()
        self.ensure_created()
        self.map_workflows()
        self.templates(CONTENT + STEPS_ONLY)
        self.content()
        self.statuses()
        untouched = [w["name"] for w in self.t.index if not any(
            norm(w["name"]) in (norm(n), *map(norm, ALIASES.get(n, []))) for n in [x["name"] for x in self.m.index])]
        if untouched:
            self.say("\n    só no alvo (não mexi): " + ", ".join(sorted(set(untouched))))
        for p in self.problems:
            print(f"  ⚠ {p}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--target", action="append", required=True)
    parser.add_argument("--model", default=PRIORITY["model"])
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--no-publish", action="store_true",
                        help="never publish anything (only content, and drafts where the model is draft)")
    args = parser.parse_args()
    load_dotenv()
    model = Side(location_dirs([args.model])[0])
    agency = Agency() if args.apply else None
    for d in location_dirs(args.target):
        if d == model.dir:
            continue
        Mirror(agency, model, Side(d), args.apply, not args.no_publish).run()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except GHLError as exc:
        print(f"\nERRO GHL: {exc}", file=sys.stderr)
        raise SystemExit(2)
