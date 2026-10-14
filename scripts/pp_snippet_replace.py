#!/usr/bin/env python3
"""Replace a piece of text in a message template (snippet) across sub-accounts.

    ./.venv/bin/python scripts/pp_snippet_replace.py --name "Review Response - Positive SMS" \\
        --old " Don't forget, every referral earns you a free month of service!" --new "" \\
        --loc SylIOZiJ6YQsZOypUI8Z --loc ...            # plan
    ... --apply

SMS steps in workflows send the template's text (attributes.template_id), so fixing the
template fixes every workflow that uses it. Every copy with that name in each account is
changed; each is backed up to backup/<slug>/snippet-<id>-<stamp>.json first.
"""
from __future__ import annotations

import argparse
import json
import time

from _common import ROOT, load_dotenv, slugify

from cli_anything.gohighlevel.utils.agency import BACKEND, Agency


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--name", required=True)
    parser.add_argument("--old", required=True)
    parser.add_argument("--new", default="")
    parser.add_argument("--loc", action="append", required=True, help="location id (repeatable)")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    load_dotenv()
    a = Agency()
    names = {l["id"]: l["name"] for l in a.locations()}
    stamp = time.strftime("%Y%m%d-%H%M%S")
    bad = 0
    for loc in args.loc:
        slug = slugify(names.get(loc, loc))
        hits = [s for s in a.snippets(loc) if s["name"].strip() == args.name]
        if not hits:
            print(f"{names.get(loc, loc)}: sem template {args.name!r}")
            continue
        for sn in hits:
            tpl = dict(sn.get("template") or {})
            body = tpl.get("body") or ""
            if args.old not in body:
                print(f"{names.get(loc, loc)} {sn['_id']}: já sem o trecho")
                continue
            tpl["body"] = body.replace(args.old, args.new)
            print(f"{names.get(loc, loc)} {sn['_id']}: {tpl['body']!r}")
            if not args.apply:
                continue
            bdir = ROOT / "backup" / slug
            bdir.mkdir(parents=True, exist_ok=True)
            (bdir / f"snippet-{sn['_id']}-{stamp}.json").write_text(json.dumps(sn, ensure_ascii=False))
            a.call("PUT", BACKEND, f"/snippets/{loc}/{sn['_id']}",
                   body={"name": sn["name"], "type": sn["type"], "template": tpl})
            for _ in range(6):  # snippet reads lag ~10-20 s behind the write
                time.sleep(4)
                after = next((s for s in a.snippets(loc) if s["_id"] == sn["_id"]), {})
                ok = (after.get("template") or {}).get("body") == tpl["body"]
                if ok:
                    break
            bad += not ok
            print(f"   {'✓' if ok else '✗ VERIFICAR'}")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
