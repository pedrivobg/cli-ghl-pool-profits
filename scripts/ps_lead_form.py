#!/usr/bin/env python3
"""The Pool Shack: Google Ads Lead Form asset → CRM (Val, ClickUp 24/11: Google Lead Ads connected by her).

    python3 scripts/ps_lead_form.py plan
    python3 scripts/ps_lead_form.py test --to pedro@poolprofits.com
    python3 scripts/ps_lead_form.py apply

Workflow "Google Ads Lead Form - New Lead" (folder of "AdWords Form - New Lead"), trigger Google Lead Form Submitted
with no adAccountId filter (the new "Google Lead Ads" app leaves googleAdwordsId empty; Sparkling 19/11). Same routing as
the LP flows (`ps_ads_forms.py`): spam/DND → nothing; already in the last 24 h → nothing; current customer → tags +
alerts marked existing customer, no card; new lead → tags (google ads, lead form, new lead), Landing Page field, card in
Pool Leads → New Lead (source "Google Ads - Lead Form"), text + email to Rob, confirmation text + email to the lead.
No Google Ads conversion step: Google already counts lead form submissions itself (an upload would double count).
test: a ZZ TEST copy (alerts only to --to, no text to Rob), contacts enrolled through the API, checks, deletes all.
"""
from __future__ import annotations

import argparse
import sys
import time

from _common import load_dotenv
from ps_ads_forms import (BDIR, FOLDER_OF, LOC, NUMBER, PAGE_FIELD, create_flow, drop_flow, outline)
import ps_ads_forms as ps
from pp_source_tags import refs_ok

from cli_anything.gohighlevel.utils.agency import BACKEND, SERVICES, Agency

FLOW = "Google Ads Lead Form - New Lead"
P = {"key": "leadform", "tag": "lead form", "label": "LEAD FORM", "page": "Google Ads Lead Form",
     "source": "Google Ads - Lead Form", "value": "",
     "sms": "Hi {{contact.first_name}}, thanks for contacting The Pool Shack! We received your request and will reach "
            "out shortly. Questions? Call or text us at " + NUMBER + ". Reply STOP to opt out.",
     "subject": "We received your request",
     "email": ["Hi {{contact.first_name}},",
               "Thanks for reaching out to The Pool Shack. We received your request and will contact you shortly to go "
               "over your pool and get you a quote.",
               "If you need us sooner, call or text us at " + NUMBER + ".",
               "Thank you,<br>The Pool Shack"]}
RECENT = "google ads lp leadform 24h"


def strip_conversion(tpl: list[dict]) -> list[dict]:
    """Remove the google_adword step from the chain (relinks parentKey/next)."""
    by = {s["id"]: s for s in tpl}
    for s in [x for x in tpl if x["type"] == "google_adword"]:
        prev = by.get(s.get("parentKey"))
        nxt = by.get(s.get("next")) if isinstance(s.get("next"), str) else None
        if prev and prev.get("next") == s["id"]:
            prev["next"] = s.get("next")
        if nxt:
            nxt["parentKey"] = s.get("parentKey")
        tpl.remove(s)
    return tpl


def flow(cfs: dict, test_to: str | None = None) -> list[dict]:
    return strip_conversion(ps.build_flow(P, cfs, test_to))


def trigger(wid: str, first: str) -> dict:
    return {"type": "google_lead_form_submitted", "name": "Google Lead Form Submitted", "masterType": "internal",
            "schedule_config": {}, "conditions": [], "workflowId": wid, "workflow_id": wid, "location_id": LOC,
            "actions": [{"workflow_id": wid, "type": "add_to_workflow"}], "targetActionId": first}


def first_id(tpl: list[dict]) -> str:
    return next(s["id"] for s in tpl if not s.get("parentKey") and not s.get("parent"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mode", choices=["plan", "test", "apply"])
    ap.add_argument("--to")
    args = ap.parse_args()
    if args.mode == "test" and not args.to:
        ap.error("--to is required in test mode")
    load_dotenv()
    a = Agency()
    if a.location(LOC)["name"] != "The Pool Shack":
        sys.exit("sub-conta errada")
    BDIR.mkdir(parents=True, exist_ok=True)
    flows = {w["name"]: w["id"] for w in a.workflows(LOC)}
    folder = a.workflow(LOC, flows[FOLDER_OF]).get("parentId")
    cfs = {c["name"]: c for c in a.custom_fields(LOC)}
    for t in ("google ads", "lead form", "new lead", RECENT):
        try:
            a.call("POST", BACKEND, f"/workflow/{LOC}/tags/create", body={"tag": t})
        except Exception:  # noqa: BLE001 — already exists
            pass

    if args.mode == "plan":
        print(f"== {FLOW}: {'existe' if FLOW in flows else 'cria'}\n{outline(flow(cfs))}")
        return 0

    if args.mode == "test":
        stamp, bad = int(time.time()), 0
        wid = create_flow(a, f"ZZ TEST {FLOW}", folder, flow(cfs, args.to), True)
        made = {}
        for case, extra in [("new", {}), ("customer", {"tags": ["existing customer"]}), ("spam", {"tags": ["spam"]})]:
            body = {"locationId": LOC, "firstName": "ZZ Test", "lastName": f"leadform {case}",
                    "email": args.to.replace("@", f"+ps-lf-{case}-{stamp}@"), "postalCode": "85251", **extra}
            made[case] = a.call("POST", SERVICES, "/contacts/", body=body)["contact"]["id"]
        time.sleep(3)
        for cid in made.values():
            a.call("POST", SERVICES, f"/contacts/{cid}/workflow/{wid}", body={})
        time.sleep(40)
        a.call("POST", SERVICES, f"/contacts/{made['new']}/workflow/{wid}", body={})  # second submit within 24 h
        time.sleep(40)
        want = {"new": ({"google ads", "lead form", "new lead", RECENT}, 1), "customer": ({"google ads", "lead form"}, 0),
                "spam": (set(), 0)}
        for case, cid in made.items():
            c = a.call("GET", SERVICES, f"/contacts/{cid}")["contact"]
            tg = c.get("tags", [])
            page = next((f.get("value") for f in c.get("customFields", []) if f.get("id") == cfs[PAGE_FIELD]["id"]), None)
            opps = a.call("GET", SERVICES, "/opportunities/search",
                          params={"location_id": LOC, "contact_id": cid}).get("opportunities", [])
            exp_tags, exp_cards = want[case]
            ok = exp_tags <= set(tg) and len(opps) == exp_cards and all(o.get("source") == P["source"] for o in opps) and \
                (case == "spam" and "google ads" not in tg or case != "spam" and page == P["page"])
            bad += not ok
            print(f"   {'✓' if ok else '✗'} {case}: tags {sorted(tg)} · page {page!r} · cards {[o.get('source') for o in opps]}")
        sent = []
        for cv in a.call("GET", SERVICES, "/conversations/search", params={"locationId": LOC, "contactId": made["new"]}).get("conversations", []):
            ms = a.call("GET", SERVICES, f"/conversations/{cv['id']}/messages").get("messages", {})
            ms = ms.get("messages", []) if isinstance(ms, dict) else ms
            sent += [m for m in ms if m.get("direction") == "outbound" and m.get("messageType") == "TYPE_EMAIL"]
        ok = len(sent) == 1
        print(f"   {'✓' if ok else '?'} repeat: {len(sent)} e-mail(s) na conversa (o e-mail pode não aparecer na conversa:"
              f" conferir na caixa {args.to} 1 alerta só para 'Leadform New')")
        for cid in made.values():
            for o in a.call("GET", SERVICES, "/opportunities/search", params={"location_id": LOC, "contact_id": cid}).get("opportunities", []):
                a.call("DELETE", SERVICES, f"/opportunities/{o['id']}")
            a.call("DELETE", SERVICES, f"/contacts/{cid}")
        drop_flow(a, wid)
        print(f"   limpo (contatos, cards, fluxo ZZ TEST). Alertas de teste em {args.to}.")
        return 1 if bad else 0

    if FLOW in flows:
        print(f"   {FLOW}: já existe ({flows[FLOW]})")
        return 0
    tpl = flow(cfs)
    wid = create_flow(a, FLOW, folder, tpl, False)
    trig = trigger(wid, first_id(tpl))
    t = a.call("POST", BACKEND, f"/workflow/{LOC}/trigger", body=trig)
    a.call("PUT", BACKEND, f"/workflow/{LOC}/trigger/{t['id']}", body={**trig, "id": t["id"]})
    live = a.workflow(LOC, wid)
    a.call("PUT", BACKEND, f"/workflow/{LOC}/{wid}", body={
        "name": FLOW, "version": live.get("version", 1), "status": "published", "parentId": folder,
        "allowMultiple": True, "workflowData": {"templates": live["workflowData"]["templates"]}})
    time.sleep(4)
    got = a.workflow(LOC, wid)
    trs = [x for x in a.triggers(LOC, wid) if not x.get("deleted")]
    ok = got["status"] == "published" and len(got["workflowData"]["templates"]) == len(tpl) and \
        refs_ok(got["workflowData"]["templates"]) and len(trs) == 1 and trs[0].get("active") and \
        trs[0]["type"] == "google_lead_form_submitted" and got.get("allowMultiple")
    print(f"   {'✓' if ok else '✗ VERIFICAR'} {FLOW} ({wid}): {got['status']} · {len(tpl)} passos · "
          f"gatilho {[x['type'] for x in trs]} ativo {[x.get('active') for x in trs]}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
