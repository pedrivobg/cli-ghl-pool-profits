#!/usr/bin/env python3
"""Move old cards in a pipeline without firing the stage automations (Frank 12/11: Reign call on 16/11).

How the team uses it: add the tag "pipeline cleanup" to the contacts whose cards will be moved, move the cards,
then remove the tag. While the contact has the tag, no stage workflow starts for it (no follow-up texts/e-mails,
no Won welcome, no review request, no Google Ads conversion, no Lost message).

What this does (backup of every trigger first): on every PUBLISHED workflow, each trigger of type
pipeline_stage_updated / opportunity_status_changed gets the filter "Doesn't Have Tag: pipeline cleanup" (same shape the
GHL UI saves, proven in pp_skip_tag); KEEP (DND / Current Customer / Spam) stay as they are. Nothing else changes; contacts without the tag behave exactly as before.

    python3 scripts/pp_cleanup_tag.py --only "Reign"            # plan
    python3 scripts/pp_cleanup_tag.py --only "Reign" --apply
    python3 scripts/pp_cleanup_tag.py --only "Reign" --test     # ZZ TEST contact (e-mail only, example.com) with the
                                                                # tag, card moved through every stage; checks nothing ran
"""
from __future__ import annotations

import argparse
import json
import time

from _common import ROOT, load_dotenv, location_dirs
from pp_audit import load

from cli_anything.gohighlevel.utils.agency import BACKEND, SERVICES, Agency, GHLError

TAG = "pipeline cleanup"
TYPES = ("pipeline_stage_updated", "opportunity_status_changed")
# workflows that only protect/tidy (DND on Spam, tag + remove card on Current Customer) keep running during a cleanup
KEEP = ("DND Contact", "Current Customer", "Spam Contact")
FILTER = {"field": "contact.tags", "id": "doesnot-have-tag", "type": "select",
          "title": "Doesn't Have Tag", "value": TAG, "operator": "index-of-false"}
DROP = ("_id", "date_added", "date_updated", "deleted", "origin_id", "company_id",
        "company_age", "last_conditions_change_at", "belongs_to")


def has_filter(t: dict) -> bool:
    return any(c.get("field") == "contact.tags" and c.get("value") == TAG and c.get("operator") == "index-of-false"
               for c in t.get("conditions") or [])


def apply(a: Agency, d, do: bool) -> list[str]:
    loc = load(d / "location.json", {})["id"]
    print(f"== {load(d / 'location.json', {}).get('name')}")
    bdir = ROOT / "backup" / d.name
    bdir.mkdir(parents=True, exist_ok=True)
    if do:
        try:
            a.call("POST", BACKEND, f"/workflow/{loc}/tags/create", body={"tag": TAG})
        except GHLError as exc:
            if exc.status not in (400, 409):
                raise
    names = []
    for w in a.workflows(loc):
        if w.get("status") != "published" or w["name"] in KEEP:
            continue
        for t in a.triggers(loc, w["id"]):
            if t.get("deleted") or t.get("type") not in TYPES:
                continue
            names.append(w["name"])
            if has_filter(t):
                print(f"   = {w['name']} ({t['type']}): já tem o filtro")
                continue
            print(f"   + {w['name']} ({t['type']})")
            if not do:
                continue
            (bdir / f"trigger-{t['id']}-{time.strftime('%Y%m%d-%H%M%S')}.json").write_text(json.dumps(t, ensure_ascii=False))
            body = {k: v for k, v in t.items() if k not in DROP}
            body["conditions"] = (t.get("conditions") or []) + [dict(FILTER)]
            a.call("PUT", BACKEND, f"/workflow/{loc}/trigger/{t['id']}", body=body)
            after = next(x for x in a.triggers(loc, w["id"]) if x["id"] == t["id"])
            print(f"     {'✓' if has_filter(after) else '✗ VERIFICAR'} filtro gravado, ativo={after.get('active')}")
    return sorted(set(names))


def test(a: Agency, d) -> int:
    loc = load(d / "location.json", {})["id"]
    pipes = a.pipelines(loc)
    pipe = next(p for p in pipes if "pool leads" in p["name"].lower()) if any("pool leads" in p["name"].lower() for p in pipes) else pipes[0]
    c = a.call("POST", SERVICES, "/contacts/", body={"locationId": loc, "firstName": "ZZ Test", "lastName": "Pipeline Cleanup",
               "email": f"zz.cleanup.{int(time.time())}@example.com", "tags": [TAG]})["contact"]
    cid, oid, bad = c["id"], None, 0
    try:
        time.sleep(3)
        stages = pipe["stages"]
        o = a.call("POST", SERVICES, "/opportunities/", body={"locationId": loc, "pipelineId": pipe["id"], "contactId": cid,
                   "name": "ZZ Test Pipeline Cleanup", "status": "open", "pipelineStageId": stages[0]["id"]})
        oid = (o.get("opportunity") or o).get("id")
        for s in [x for x in stages[1:] if not any(k in x['name'].lower() for k in ('spam', 'current customer'))]:
            a.call("PUT", SERVICES, f"/opportunities/{oid}", body={"pipelineStageId": s["id"], "pipelineId": pipe["id"]})
            print(f"   card → {s['name']}")
            time.sleep(4)
        a.call("PUT", SERVICES, f"/opportunities/{oid}", body={"status": "won"})
        a.call("PUT", SERVICES, f"/opportunities/{oid}", body={"status": "lost"})
        print("   esperando 90 s para os fluxos (se algum rodasse)…")
        time.sleep(90)
        ct = a.get(SERVICES, f"/contacts/{cid}")["contact"]
        tags = sorted(ct.get("tags") or [])
        msgs = []
        for conv in a.get(SERVICES, "/conversations/search", {"locationId": loc, "contactId": cid}).get("conversations", []):
            m = a.get(SERVICES, f"/conversations/{conv['id']}/messages", {"limit": 20}).get("messages", {})
            msgs += [x for x in (m.get("messages") if isinstance(m, dict) else m) or [] if x.get("direction") == "outbound"]
        tasks = a.get(SERVICES, f"/contacts/{cid}/tasks").get("tasks", [])
        ok = tags == [TAG] and not msgs and not tasks
        bad += not ok
        print(f"   {'✓' if ok else '✗'} tags {tags} · mensagens enviadas {len(msgs)} · tarefas {len(tasks)}")
        for x in msgs[:5]:
            print("     enviado:", x.get("messageType"), (x.get("body") or x.get("subject") or "")[:80])
    finally:
        if oid:
            a.call("DELETE", SERVICES, f"/opportunities/{oid}")
        a.call("DELETE", SERVICES, f"/contacts/{cid}")
        print("   contato e card de teste apagados")
    return 1 if bad else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", action="append", required=True)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--test", action="store_true")
    args = ap.parse_args()
    load_dotenv()
    a = Agency()
    rc = 0
    for d in location_dirs(args.only):
        if args.test:
            rc |= test(a, d)
        else:
            print("   fluxos:", apply(a, d, args.apply))
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
