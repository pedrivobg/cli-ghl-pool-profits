#!/usr/bin/env python3
"""Tags used by workflows that do not exist in the account → create them.

    ./.venv/bin/python scripts/pp_tags_missing.py --only "Stay Fresh"          # plan
    ./.venv/bin/python scripts/pp_tags_missing.py --only "Stay Fresh" --apply

Frank (16/10, Stay Fresh): the builder showed "Referenced Tag does not exist or does not belong to this
location" on Won Stage — the tags added by `pp_won_stage.py` ("won weekly", "won repairs and installs",
"won construction") were put in workflow steps via the API without creating the tag itself. The step
works, but the builder flags it. Looks at every workflow (any status): add/remove tag steps, tag
triggers/filters and if/else tag conditions; compares with the account's tag list (case-insensitive).
"""
from __future__ import annotations

import argparse

from _common import load_dotenv, location_dirs
from pp_audit import load

from cli_anything.gohighlevel.utils.agency import BACKEND, Agency

TAG_FIELDS = {"tagsAdded", "tagsRemoved", "contact.tags", "tags"}


def as_list(v) -> list[str]:
    return [x for x in (v if isinstance(v, list) else [v]) if isinstance(x, str) and x.strip()]


def used_tags(a: Agency, loc: str) -> dict[str, set[str]]:
    """tag → workflows that use it."""
    out: dict[str, set[str]] = {}
    for w in a.workflows(loc):
        name = w["name"]
        live = a.workflow(loc, w["id"])
        for s in (live.get("workflowData") or {}).get("templates") or []:
            at = s.get("attributes") or {}
            if s.get("type") in ("add_contact_tag", "remove_contact_tag"):
                for t in as_list(at.get("tags")):
                    out.setdefault(t.strip().lower(), set()).add(name)
            for b in at.get("branches") or []:
                for seg in b.get("segments") or []:
                    for c in seg.get("conditions") or []:
                        if c.get("conditionSubType") == "tags":
                            for t in as_list(c.get("conditionValue")):
                                out.setdefault(t.strip().lower(), set()).add(name)
        for t in a.triggers(loc, w["id"]):
            if t.get("deleted"):
                continue
            for c in t.get("conditions") or []:
                if c.get("field") in TAG_FIELDS:
                    for v in as_list(c.get("value")):
                        out.setdefault(v.strip().lower(), set()).add(name)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--only", action="append", required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    load_dotenv()
    a = Agency()
    bad = 0
    for d in location_dirs(args.only):
        loc = load(d / "location.json", {})["id"]
        have = {(t.get("name") or "").strip().lower() for t in a.tags(loc)}
        used = used_tags(a, loc)
        missing = {t: ws for t, ws in used.items() if t not in have}
        print(f"== {d.name}: {len(used)} tags usadas, {len(missing)} não existem")
        for t, ws in sorted(missing.items()):
            print(f"   - {t!r}  ({', '.join(sorted(ws))})")
        if not args.apply or not missing:
            continue
        for t in missing:
            try:
                a.call("POST", BACKEND, f"/workflow/{loc}/tags/create", body={"tag": t})
            except Exception as e:  # noqa: BLE001
                print(f"   ✗ {t!r}: {str(e)[:120]}")
        have = {(t.get("name") or "").strip().lower() for t in a.tags(loc)}
        left = [t for t in missing if t not in have]
        bad += bool(left)
        print(f"   {'✓ criadas' if not left else '✗ faltam ' + str(left)}")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
