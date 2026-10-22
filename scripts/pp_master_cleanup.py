#!/usr/bin/env python3
"""Snapshot master ("Snapshot Pool Profits"): take out what belongs to other clients (Pedro OK'd, 22/10).

    ./.venv/bin/python scripts/pp_master_cleanup.py            # plan
    ./.venv/bin/python scripts/pp_master_cleanup.py --apply

- Sequential Call Routing (draft) was BluVantage's IVR: steps "Ring Fred"/"Ring Paul" with BluVantage users, their
  recorded voicemail ("you've reached BluVantage…") and a trigger on 6 BluVantage numbers. It becomes generic: "Ring
  team member 1/2" without users (a loaded snapshot blanks unknown users anyway), a spoken voicemail with the
  account's friendly business name, and no trigger (the account's own lines are added when the IVR is set up).
- AdWords Call In - New Lead (draft): its trigger listened to a Tucson number (Clear Pool Solutions): trigger removed;
  the account's Google Ads line goes in when its ads start.
- Funnels: the 3 "Simple Pool Care" copies and "Weekly Pool Service — LP Teste" are deleted (pages backed up first).
  The two "Pool Maintenance Service Website Version 1" are NOT duplicates (one has a quote form in the header): kept.
- "Pool Maintenance Snapshot" → Schedule page: "The Pool Care Pros" logo → {{custom_values.logo_url}}, like the
  funnel's first page.
Then Pedro clicks Refresh on the snapshot.
"""
from __future__ import annotations

import argparse
import base64
import json
import sys
import time

import requests

from _common import ROOT, load_dotenv

from cli_anything.gohighlevel.utils.agency import BACKEND, SERVICES, Agency

LOC = "Kvdj7o189zlS3caaCNuX"
IVR, ADS_CALL = "Sequential Call Routing", "AdWords Call In - New Lead"
FOREIGN_FUNNELS = {"9amYfIseZNT5fAZkqv2h": "Maintenance - Simple Pool Care",
                   "sl8THaFvlXefHXqlSAJI": "Repairs & Equipaments - Simple Pool Care",
                   "0oqurU0lpdo38tWtqGr7": "Weekly - Simple Pool Care",
                   "zOk7gw1gunwKOxvzpRdE": "Weekly Pool Service — LP Teste"}
SCHEDULE_PAGE = "2Il3lNMSzwvi9e8J6UM8"
FOREIGN_LOGO = "07dfe3cb-6067-46a4-b4db-ef04d582375e"  # The Pool Care Pros
LOGO = "{{custom_values.logo_url}}"
VOICEMAIL = ("Thank you for calling {{custom_values.friendly_business_name}}. We're either helping another customer or "
             "out in the field. Please leave your name, phone number, address, and a quick note about what you need, "
             "and we'll get back to you as soon as we can.")
BDIR = ROOT / "backup" / "snapshot-pool-profits"


def user_id(a: Agency) -> str:
    payload = a.tokens.get_token().split(".")[1]
    return json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))["user_id"]


def generic_ivr(tpl: list[dict]) -> list[str]:
    done, n = [], 0
    for st in tpl:
        a = st.get("attributes") or {}
        for who, member in (("Fred", "team member 1"), ("Paul", "team member 2")):  # "Did Fred Answer?"
            if st["type"] == "if_else" and who in (a.get("conditionName") or ""):
                done.append(f"condição '{a['conditionName']}' → sem o nome")
                a["conditionName"] = a["conditionName"].replace(who, member)
        if st["type"] == "ivr_connect_call":
            n += 1
            if a.get("users") or not st["name"].startswith("Ring team member"):
                done.append(f"'{st['name']}' → 'Ring team member {n}' sem usuário")
                st["name"], a["users"] = f"Ring team member {n}", []
        if st["type"] == "ivr_collect_voicemail":
            sp = a.get("sayPlayAttributes") or {}
            if sp.get("audioUrl") or sp.get("message") != VOICEMAIL:
                done.append("caixa postal → texto genérico (sem a gravação da BluVantage)")
                sp.pop("audioUrl", None)
                sp.update(widgetType="say", message=VOICEMAIL)
    return done


def logo_nodes(o):
    if isinstance(o, dict):
        url = ((o.get("imageProperties") or {}).get("value") or {}).get("url")
        if isinstance(url, str) and FOREIGN_LOGO in url:
            yield o["imageProperties"]["value"]
        for v in o.values():
            yield from logo_nodes(v)
    elif isinstance(o, list):
        for v in o:
            yield from logo_nodes(v)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    load_dotenv()
    a = Agency()
    if a.location(LOC)["name"] != "Snapshot Pool Profits":
        sys.exit("sub-conta errada")
    BDIR.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    flows = {w["name"]: w["id"] for w in a.workflows(LOC)}

    # 1-2. workflows
    for name in (IVR, ADS_CALL):
        live = a.workflow(LOC, flows[name])
        trs = [t for t in a.triggers(LOC, live["id"]) if not t.get("deleted")]
        tpl = json.loads(json.dumps(live["workflowData"]["templates"]))
        changes = generic_ivr(tpl) if name == IVR else []
        print(f"== {name} [{live['status']}]")
        for c in changes:
            print("   ", c)
        for t in trs:
            nums = [v for c in t.get("conditions") or [] if c.get("field") == "inbound_number" for v in c.get("value") or []]
            print(f"    tira o gatilho {t['type']} ({', '.join(nums) or 'sem número'})")
        if not args.apply:
            continue
        (BDIR / f"workflow-{live['id']}-{stamp}.json").write_text(json.dumps({"workflow": live, "triggers": trs}))
        if changes:
            a.call("PUT", BACKEND, f"/workflow/{LOC}/{live['id']}", body={
                "name": live["name"], "version": live.get("version", 1), "status": live["status"],
                "parentId": live.get("parentId"), "workflowData": {"templates": tpl}})
        for t in trs:
            a.call("DELETE", BACKEND, f"/workflow/{LOC}/trigger/{t['id']}")
        time.sleep(3)
        got = a.workflow(LOC, live["id"])
        left = [t for t in a.triggers(LOC, live["id"]) if not t.get("deleted")]
        ok = got["status"] == live["status"] and not left and (not changes or not generic_ivr(
            json.loads(json.dumps(got["workflowData"]["templates"]))))
        print(f"    {'✓' if ok else '✗ VERIFICAR'} {got['status']} · gatilhos {len(left)}")

    # 3. funnels
    funnels = {f["_id"]: f for f in a.call("GET", SERVICES, f"/funnels/funnel/list?locationId={LOC}")["funnels"]}
    for fid, fname in FOREIGN_FUNNELS.items():
        f = funnels.get(fid)
        if not f:
            print(f"== funil {fname}: já não existe")
            continue
        assert f["name"].strip() == fname, f["name"]
        print(f"== funil {fname}: apaga ({len(f.get('steps') or [])} passos)")
        if not args.apply:
            continue
        pages = {}
        for st in f.get("steps") or []:
            for pid in st.get("pages") or []:
                page = a.get(BACKEND, f"/funnels/page/{pid}")
                pages[pid] = {"page": page, "pageData": requests.get(page["pageDataDownloadUrl"], timeout=60).json()
                              if page.get("pageDataDownloadUrl") else None}
        (BDIR / f"funnel-{fid}-{stamp}.json").write_text(json.dumps({"funnel": f, "pages": pages}, ensure_ascii=False))
        a.call("POST", SERVICES, "/funnels/funnel/delete", body={"funnelId": fid, "locationId": LOC, "userId": user_id(a)})
    if args.apply:
        time.sleep(3)
        left = {f["_id"] for f in a.call("GET", SERVICES, f"/funnels/funnel/list?locationId={LOC}")["funnels"]}
        print(f"    {'✓' if not left & set(FOREIGN_FUNNELS) else '✗ VERIFICAR'} funis restantes: {len(left)}")

    # 4. logo on the Schedule page
    page = a.get(BACKEND, f"/funnels/page/{SCHEDULE_PAGE}")
    data = requests.get(page["pageDataDownloadUrl"], timeout=60).json()
    new = json.loads(json.dumps(data))
    hits = list(logo_nodes(new))
    print(f"== página Schedule: {len(hits)} logo(s) da Pool Care Pros → {LOGO}")
    if args.apply and hits:
        (BDIR / f"page-{SCHEDULE_PAGE}-{stamp}.json").write_text(json.dumps({"page": page, "pageData": data}, ensure_ascii=False))
        for h in hits:
            h["url"] = LOGO
        history = page.get("versionHistory") or [{}]
        a.call("POST", BACKEND, f"/funnels/builder/autosave/{SCHEDULE_PAGE}",
               body={"funnelId": page["funnelId"], "pageData": new, "pageVersion": page.get("pageVersion") or 1,
                     "pageType": "live", "manualSave": True, "meta": page.get("meta") or {},
                     "integrations": history[0].get("integrations") or {}})
        for _ in range(6):  # page reads lag behind writes
            time.sleep(3)
            after = a.get(BACKEND, f"/funnels/page/{SCHEDULE_PAGE}")
            saved = requests.get(after["pageDataDownloadUrl"], timeout=60).json()
            if not list(logo_nodes(saved)):
                break
        print(f"    {'✓' if not list(logo_nodes(saved)) and LOGO in json.dumps(saved) else '✗ VERIFICAR'} salvo")
    return 0


if __name__ == "__main__":
    sys.exit(main())
