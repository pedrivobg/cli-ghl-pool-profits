#!/usr/bin/env python3
"""Dump sub-accounts of the Pool Profits agency to disk. Read-only.

    ./.venv/bin/python scripts/pp_dump.py --list                 # só lista as sub-contas
    ./.venv/bin/python scripts/pp_dump.py --priority             # modelo + 5 prioritárias
    ./.venv/bin/python scripts/pp_dump.py --only "Bahama Blue"   # uma (repetível)
    ./.venv/bin/python scripts/pp_dump.py --all                  # todas

Output, per sub-account, in dump/<slug>/:
    location.json  custom_values.json  custom_fields.json  tags.json
    pipelines.json forms.json  calendars.json  users.json  snippets.json
    workflows/_index.json          id, name, status, folder
    workflows/<id>.json            full definition + "triggers" list

dump/ holds client data (message bodies, phone numbers) and is gitignored.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor

from _common import DUMP, Agency, load_dotenv, select, slugify

from cli_anything.gohighlevel.utils.agency import GHLError

ASSETS = ("custom_values", "custom_fields", "tags", "pipelines", "forms",
          "calendars", "users", "snippets")


def write(path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False))


def dump_location(agency: Agency, loc: dict, all_names: list[str]) -> dict:
    out = DUMP / slugify(loc.get("name", loc["id"]))
    summary = {"name": loc.get("name"), "id": loc["id"], "errors": []}

    try:
        detail = agency.location(loc["id"])
    except GHLError:
        detail = loc
    write(out / "location.json", {**loc, **detail, "_agency_location_names": all_names})

    for asset in ASSETS:
        try:
            write(out / f"{asset}.json", getattr(agency, asset)(loc["id"]))
        except GHLError as exc:
            summary["errors"].append(f"{asset}: {exc.status}")
            write(out / f"{asset}.json", [])

    try:
        workflows = agency.workflows(loc["id"])
    except GHLError as exc:
        summary["errors"].append(f"workflows: {exc}")
        workflows = []
    folders = agency.folders(loc["id"])

    index = []
    for wf in workflows:
        try:
            full = agency.workflow(loc["id"], wf["id"])
            full["triggers"] = agency.triggers(loc["id"], wf["id"])
        except GHLError as exc:
            summary["errors"].append(f"workflow {wf.get('name')}: {exc.status}")
            continue
        folder = wf.get("folder") or folders.get(full.get("parentId") or "", "")
        full["_folder"] = folder
        write(out / "workflows" / f"{wf['id']}.json", full)
        index.append({"id": wf["id"], "name": full.get("name") or wf.get("name"),
                      "status": full.get("status") or wf.get("status"), "folder": folder})
    write(out / "workflows" / "_index.json", index)

    summary["workflows"] = len(index)
    summary["published"] = sum(1 for w in index if w["status"] == "published")
    summary["dir"] = str(out.relative_to(DUMP.parent))
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--list", action="store_true", help="list sub-accounts and exit")
    parser.add_argument("--only", action="append", help="sub-account name or id (repeatable)")
    parser.add_argument("--priority", action="store_true", help="model + priority list from config/priority.json")
    parser.add_argument("--all", action="store_true", help="every sub-account")
    parser.add_argument("--workers", type=int, default=3, help="sub-accounts dumped in parallel")
    args = parser.parse_args()

    load_dotenv()
    agency = Agency()
    claims = agency.claims()
    print(f"→ token de {claims.get('email') or claims.get('user_id') or '?'} "
          f"(company {agency.company_id() or '?'})")

    locations = sorted(agency.locations(), key=lambda l: (l.get("name") or "").lower())
    print(f"  {len(locations)} sub-contas (via {agency.working_paths.get('locations')})")
    DUMP.mkdir(exist_ok=True)
    write(DUMP / "_locations.json",
          [{"id": l["id"], "name": l.get("name")} for l in locations])

    if args.list:
        for loc in locations:
            print(f"  {loc['id']}  {loc.get('name')}")
        return 0

    chosen = select(locations, args.only, args.all, args.priority)
    if not chosen:
        print("Nada selecionado: use --only, --priority ou --all", file=sys.stderr)
        return 1

    names = [l.get("name") or "" for l in locations]
    started = time.time()
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        results = list(pool.map(lambda l: dump_location(agency, l, names), chosen))

    for r in results:
        flag = f"  ⚠ {len(r['errors'])} erro(s)" if r["errors"] else ""
        print(f"  ✓ {r['name']}: {r.get('workflows', 0)} workflows "
              f"({r.get('published', 0)} published) → {r.get('dir')}{flag}")
        for err in r["errors"][:8]:
            print(f"      - {err}")
    print(f"\n{agency.calls} chamadas em {time.time() - started:.0f}s. "
          f"Caminhos usados: {agency.working_paths}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
