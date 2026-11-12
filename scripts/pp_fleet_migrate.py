#!/usr/bin/env python3
"""Old accounts → current model, keeping what is live (Pedro 11/11).

Rules: a snapshot workflow the account has is updated in place and keeps its draft/published status; one it doesn't
have is created as draft; the account's own workflows (not in the snapshot) are never touched or deleted; a snapshot
workflow the account changed into its own thing (IVR, own steps/triggers) is left alone and listed as "específico";
template texts the client changed stay. No duplicate clean-up, no status changes, no new published workflow
(pp_line_tag is not run), native missed-call text untouched.

Per account (each step logged to reports/fleet-migrate/<slug>.log):
  pp_dump → pp_nps --apply → pp_dump → pp_mirror --keep-status --apply → pp_dump → pp_forms --apply → pp_fix --apply
  (published only) → pp_tags_missing --apply → pp_skip_tag --apply → pp_review_fix --apply → pp_master_cleanup --loc
  --apply → pp_review_gate --apply → pp_dump → pp_audit → pp_ready → pp_fleet_check

  python3 scripts/pp_fleet_migrate.py --only "<name>"            # plan: pp_mirror --keep-status (read-only)
  python3 scripts/pp_fleet_migrate.py --only "<name>" --apply
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PY = sys.executable
S = os.path.join(ROOT, "scripts")


def run(log, *cmd: str, timeout: int = 900) -> str:
    log.write(f"\n$ {' '.join(cmd)}\n")
    r = subprocess.run([PY, *cmd], cwd=ROOT, capture_output=True, text=True, timeout=timeout)
    out = r.stdout + (f"\n[stderr]\n{r.stderr[-3000:]}" if r.returncode else "")
    log.write(out)
    log.flush()
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", action="append", required=True)
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    sys.path.insert(0, ROOT)
    from cli_anything.gohighlevel.utils.agency import Agency, match_location
    a = Agency()
    locs = a.locations()
    os.makedirs(os.path.join(ROOT, "reports", "fleet-migrate"), exist_ok=True)
    for want in args.only:
        loc = match_location(locs, want)
        if not loc:
            print(f"{want}: not found / ambiguous")
            continue
        name, lid = loc["name"], loc["id"]
        slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
        with open(os.path.join(ROOT, "reports", "fleet-migrate", f"{slug}.log"), "a") as log:
            run(log, f"{S}/pp_dump.py", "--only", name)
            if not args.apply:
                out = run(log, f"{S}/pp_mirror.py", "--target", name, "--keep-status")
                print(f"===== {name}\n" + "\n".join(l for l in out.splitlines()
                                                      if re.match(r"\s*(\[|    \S|  [⚠◆]|== )", l)))
                continue
            run(log, f"{S}/pp_nps.py", "--only", name, "--apply")
            run(log, f"{S}/pp_dump.py", "--only", name)
            mirror = run(log, f"{S}/pp_mirror.py", "--target", name, "--keep-status", "--apply")
            run(log, f"{S}/pp_dump.py", "--only", name)
            for cmd in (["pp_forms.py", "--only", name, "--apply"], ["pp_fix.py", "--only", name, "--apply"],
                        ["pp_tags_missing.py", "--only", name, "--apply"], ["pp_skip_tag.py", "--only", name, "--apply"],
                        ["pp_review_fix.py", "--only", name, "--apply"], ["pp_master_cleanup.py", "--loc", lid, "--apply"],
                        ["pp_review_gate.py", "--only", name, "--apply"]):
                run(log, f"{S}/{cmd[0]}", *cmd[1:])
            run(log, f"{S}/pp_dump.py", "--only", name)
            audit = run(log, f"{S}/pp_audit.py", "--only", name)
            ready = run(log, f"{S}/pp_ready.py", "--only", name)
            fleet = run(log, f"{S}/pp_fleet_check.py", "--only", name)
            calls = run(log, f"{S}/pp_call_check.py", "--only", name, "--quiet")  # BluVantage 11/11: every line still rings
            if " ERRO " in calls or "ERRO  " in calls:
                print(f"!!! {name}: pp_call_check com ERRO — conferir as ligações antes de seguir:\n{calls}", flush=True)
            alta = re.search(r"ALTA (\d+)", audit)
            erro = re.search(r"(\d+) ERRO", ready)
            spec = [l.strip() for l in mirror.splitlines() if "◆" in l or "⚠" in l]
            print(json.dumps({"account": name, "alta": alta and int(alta.group(1)), "erro": erro and int(erro.group(1)),
                              "fleet": fleet.strip().splitlines()[-1][:300] if fleet.strip() else "",
                              "notes": spec}, ensure_ascii=False))


if __name__ == "__main__":
    main()
