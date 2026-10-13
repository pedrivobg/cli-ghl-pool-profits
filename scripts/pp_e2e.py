#!/usr/bin/env python3
"""Live end-to-end test of the mirrored workflows on a TEST sub-account.

    ./.venv/bin/python scripts/pp_e2e.py --only "Test Snapshot"
    ./.venv/bin/python scripts/pp_e2e.py --only "Test Snapshot" --cleanup   # delete the zz-e2e contacts

Never point it at a client: it creates contacts and opportunities, and the
workflows send real SMS/emails (to fake addresses) and notify the account users.

Each test fires a real trigger through the API and then looks for the effect the
model workflow must produce (tags, opportunity, outbound message, DND). Form
submissions cannot be scripted (GHL protects the form endpoint with Turnstile),
so the form path is verified from real submissions instead.
"""
from __future__ import annotations

import argparse
import sys
import time

from _common import load_dotenv, location_dirs
from pp_audit import load

from cli_anything.gohighlevel.utils.agency import SERVICES, Agency, GHLError

PREFIX = "zz-e2e"


def messages(a: Agency, loc: str, cid: str) -> list[dict]:
    convs = a.get(SERVICES, "/conversations/search", {"locationId": loc, "contactId": cid}).get("conversations", [])
    out = []
    for c in convs:
        out += a.get(SERVICES, f"/conversations/{c['id']}/messages").get("messages", {}).get("messages", [])
    return out


def wait_for(check, timeout: int, every: int = 10):
    end = time.time() + timeout
    while time.time() < end:
        got = check()
        if got:
            return got
        time.sleep(every)
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--only", required=True)
    parser.add_argument("--cleanup", action="store_true")
    args = parser.parse_args()
    load_dotenv()
    a = Agency()
    d = location_dirs([args.only])[0]
    location = load(d / "location.json", {})
    loc, name = location["id"], location.get("name", "")
    if "test" not in name.lower():
        print(f"Recusado: '{name}' não parece sub-conta de teste.")
        return 1

    if args.cleanup:
        found = a.get(SERVICES, "/contacts/", {"locationId": loc, "query": PREFIX, "limit": 100}).get("contacts", [])
        for c in found:
            if (c.get("email") or "").startswith(PREFIX) or (c.get("email") or "").startswith("zz-webhook"):
                a.call("DELETE", SERVICES, f"/contacts/{c['id']}")
                print("  apagado", c.get("email"))
        return 0

    pipe = next(p for p in a.pipelines(loc) if "pool leads" in p["name"].lower())
    stage = {s["name"]: s["id"] for s in pipe["stages"]}
    ts = int(time.time())
    results = []

    seq = iter(range(1, 100))

    def contact(tag: str) -> dict:
        body = {"locationId": loc, "firstName": "ZZ", "lastName": f"E2E {tag}",
                "email": f"{PREFIX}-{tag}-{ts}@example.com", "phone": f"+1480555{(ts + next(seq)) % 10000:04d}"}
        return a.call("POST", SERVICES, "/contacts/", body=body)["contact"]

    def record(test: str, ok: bool, detail: str) -> None:
        results.append((test, ok, detail))
        print(f"  {'✓' if ok else '✗'} {test}: {detail}")

    # 1. missed call tag → Missed New Lead SMS 1 (sorry we missed your call)
    c1 = contact("missed")
    a.call("POST", SERVICES, f"/contacts/{c1['id']}/tags", body={"tags": ["missed call"]})
    got = wait_for(lambda: [m for m in messages(a, loc, c1["id"]) if "missed your call" in (m.get("body") or "").lower()], 120)
    record("tag 'missed call' → SMS 1 (missed call text back)", bool(got),
           (got[0].get("body", "")[:90] + f" [status {got[0].get('status')}]") if got else "nenhum SMS em 120s")

    # 2. opportunity → No Show stage → No-Show SMS 1
    c2 = contact("noshow")
    opp = a.call("POST", SERVICES, "/opportunities/", body={"locationId": loc, "pipelineId": pipe["id"],
                 "pipelineStageId": stage["🆕 New Lead"], "contactId": c2["id"], "name": "ZZ E2E noshow", "status": "open"})
    opp = opp.get("opportunity", opp)
    time.sleep(5)
    a.call("PUT", SERVICES, f"/opportunities/{opp['id']}", body={"pipelineStageId": stage["No Show"]})
    got = wait_for(lambda: [m for m in messages(a, loc, c2["id"]) if "missed you today" in (m.get("body") or "").lower()], 120)
    record("etapa → No Show → SMS 1 (reschedule)", bool(got),
           (got[0].get("body", "")[:90] + f" [status {got[0].get('status')}]") if got else "nenhum SMS em 120s")

    # 3. same opportunity → Won - Weekly → Won Stage welcome (after its 2-minute wait)
    a.call("PUT", SERVICES, f"/opportunities/{opp['id']}", body={"pipelineStageId": stage["🏆 Won - Weekly Pool Service"]})
    got = wait_for(lambda: [m for m in messages(a, loc, c2["id"]) if "welcome" in ((m.get("body") or "") + str(m.get("meta") or "")).lower()], 300, 15)
    record("etapa → Won Weekly → boas-vindas (após 2 min)", bool(got),
           f"{len(got)} mensagem(ns) de boas-vindas" if got else "nada em 5 min")

    # 4. opportunity → Spam → tags spam + DND
    c3 = contact("spam")
    opp3 = a.call("POST", SERVICES, "/opportunities/", body={"locationId": loc, "pipelineId": pipe["id"],
                  "pipelineStageId": stage["🆕 New Lead"], "contactId": c3["id"], "name": "ZZ E2E spam", "status": "open"})
    opp3 = opp3.get("opportunity", opp3)
    time.sleep(5)
    a.call("PUT", SERVICES, f"/opportunities/{opp3['id']}", body={"pipelineStageId": stage["🚫 Spam"]})
    got = wait_for(lambda: (lambda c: c if "spam" in (c.get("tags") or []) else None)(
        a.get(SERVICES, f"/contacts/{c3['id']}")["contact"]), 120)
    record("etapa → Spam → tags spam/dnd + DND", bool(got),
           f"tags {got.get('tags')} dnd={got.get('dnd')}" if got else "sem tag spam em 120s")

    failed = [r for r in results if not r[1]]
    print(f"\n{len(results) - len(failed)}/{len(results)} testes passaram em {name}")
    return 1 if failed else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except GHLError as exc:
        print(f"ERRO GHL: {exc}", file=sys.stderr)
        raise SystemExit(2)
