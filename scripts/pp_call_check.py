#!/usr/bin/env python3
"""Every phone line of every sub-account still rings someone (read-only; after BluVantage 11/11).

On 11/11 the fleet migration rewrote BluVantage's live "Sequential Call Routing" with the generic snapshot copy: the ring
steps lost their users and every call went to voicemail. This check looks at what is LIVE, account by account:

  ERRO  published workflow with an IVR "connect call" step without user and without number (rings nobody)
  ERRO  connect-call step ringing a user that is not in the account (deleted user / another client's)
  ERRO  line whose inbound call service points at a workflow that is missing or in draft
  ERRO  published IVR trigger listening to a number the account doesn't own (another client's line)
  AVISO published call workflow changed on --since day (review what changed)
  AVISO voicemail / greeting text naming another client
  info  line with no IVR and no forwarding (rings the GHL app users only)

    python3 scripts/pp_call_check.py                      # all client accounts (Pool Profits agency)
    python3 scripts/pp_call_check.py --only BluVantage
    GHL_AGENCY=poolduck python3 scripts/pp_call_check.py  # other agency
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(__file__))
from _common import load_dotenv  # noqa: E402

load_dotenv()
from cli_anything.gohighlevel.utils.agency import SERVICES, Agency, match_location  # noqa: E402

SKIP = {"Kvdj7o189zlS3caaCNuX", "ry6sFIgFjqY8XLwTVYEj", "hmzX5j1dPhOQKX2dH4kf", "6lzYFANJTxKkAUA8Z18b",
        "XPTb5f0mJ9i1rEuGcbMx", "9RRhRHphfPCXM1glTaqL"}  # snapshot master/old, Test Snapshot, test inc, sample, billing


def digits(n: str) -> str:
    d = "".join(c for c in str(n) if c.isdigit())
    return d[-10:]


def check(a: Agency, loc: dict, since: str, others: dict[str, str]) -> list[tuple[str, str]]:
    lid, out = loc["id"], []
    users = {u["id"] for u in a.users(lid)}
    try:
        nums = a.call("GET", SERVICES, f"/phone-system/numbers/location/{lid}").get("numbers", [])
    except Exception as exc:  # noqa: BLE001 — 404 = account without a phone system (no numbers)
        nums, _ = [], out.append(("info" if "404" in str(exc) else "AVISO", f"linhas não lidas: {str(exc)[:80]}"))
    own = {digits(n.get("phoneNumber", "")) for n in nums}
    wfs = {w["id"]: w for w in a.workflows(lid)}
    call_wfs = {}
    for wid, w in wfs.items():
        d = a.workflow(lid, wid)
        steps = (d.get("workflowData") or {}).get("templates") or []
        if not any((s.get("type") or "").startswith("ivr_") for s in steps):
            continue
        d["triggers"] = [t for t in a.triggers(lid, wid) if not t.get("deleted")]
        call_wfs[wid] = d
        live = d.get("status") == "published"
        tag = f"'{d['name']}' [{d.get('status')}]"
        for s in steps:
            at = s.get("attributes") or {}
            if s.get("type") == "ivr_connect_call":
                if live and not at.get("users") and not at.get("customNumbers"):
                    out.append(("ERRO", f"{tag}: passo '{s.get('name')}' não toca ninguém (sem usuário/número)"))
                bad = [u for u in at.get("users") or [] if u not in users]
                if bad and live:
                    out.append(("ERRO", f"{tag}: passo '{s.get('name')}' toca usuário que não é da conta {bad}"))
            text = json.dumps(at.get("sayPlayAttributes") or at, ensure_ascii=False).lower()
            for other in others:
                if other in text and other not in loc.get("name", "").lower():
                    out.append(("AVISO", f"{tag}: '{s.get('name')}' fala/toca '{others[other]}' (outro cliente)"))
        if live and (d.get("updatedAt") or "")[:10] == since:
            out.append(("AVISO", f"{tag}: publicado e alterado em {since} ({d.get('updatedAt')}) — conferir"))
        for t in d["triggers"]:
            for c in t.get("conditions") or []:
                if c.get("field") == "inbound_number":
                    foreign = [v for v in c.get("value") or [] if digits(v) not in own]
                    if foreign and live and nums:
                        out.append(("ERRO", f"{tag}: gatilho ouve número que não é da conta {foreign}"))
    for n in nums:
        svc = n.get("inboundCallService") or {}
        line = f"linha {n.get('phoneNumber')} ({n.get('friendlyName') or n.get('name') or ''})".strip()
        target = svc.get("value") or svc.get("id") or svc.get("workflowId")
        if svc.get("type") and "ivr" in str(svc.get("type")).lower() or (svc.get("type") == "workflow"):
            wf = call_wfs.get(target) or (wfs.get(target) and a.workflow(lid, target))
            if not wf:
                out.append(("ERRO", f"{line}: IVR aponta para workflow inexistente ({target})"))
            elif wf.get("status") != "published":
                out.append(("ERRO", f"{line}: IVR '{wf.get('name')}' está em {wf.get('status')}"))
            else:
                out.append(("ok", f"{line}: IVR '{wf.get('name')}'"))
        elif n.get("forwardingNumber"):
            out.append(("ok", f"{line}: encaminha para {n['forwardingNumber']}"))
        else:
            out.append(("info", f"{line}: sem IVR e sem encaminhamento (toca só os usuários no app)"))
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", action="append")
    ap.add_argument("--since", default="2026-11-11", help="day of a fleet run (YYYY-MM-DD)")
    ap.add_argument("--json", help="write the full result here")
    ap.add_argument("--quiet", action="store_true", help="hide ok/info lines")
    args = ap.parse_args()
    a = Agency()
    locs = a.locations()
    targets = [match_location(locs, o) for o in args.only] if args.only else [l for l in locs if l["id"] not in SKIP]
    others = {l["name"].lower().split(" pool")[0].strip(): l["name"] for l in locs
              if len(l["name"].lower().split(" pool")[0].strip()) >= 6 and l["id"] not in SKIP}
    others = {k: v for k, v in others.items() if k not in ("pool profits", "snapshot", "master")}

    def one(loc):
        try:
            return loc, check(a, loc, args.since, others)
        except Exception as exc:  # noqa: BLE001
            return loc, [("AVISO", f"falhou: {str(exc)[:160]}")]

    res = {}
    with ThreadPoolExecutor(6) as ex:
        for loc, rows in ex.map(one, sorted(targets, key=lambda l: l.get("name", ""))):
            res[loc["name"]] = rows
            bad = [r for r in rows if r[0] in ("ERRO", "AVISO")]
            print(f"== {loc['name']}: {sum(r[0] == 'ERRO' for r in rows)} ERRO, {sum(r[0] == 'AVISO' for r in rows)} AVISO",
                  flush=True)
            for lvl, msg in (bad if args.quiet else rows):
                print(f"   {lvl:5} {msg}", flush=True)
    if args.json:
        with open(args.json, "w") as fh:
            json.dump(res, fh, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
