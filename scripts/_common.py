"""Shared bits for the Pool Profits scripts: .env loading and sub-account selection."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from cli_anything.gohighlevel.utils.agency import Agency, match_location, slugify  # noqa: E402,F401

DUMP = ROOT / "dump"
REPORTS = ROOT / "reports"
PRIORITY = json.loads((ROOT / "config" / "priority.json").read_text())


def load_dotenv() -> None:
    path = ROOT / ".env"
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, val = line.partition("=")
            os.environ.setdefault(key.strip(), val.strip())


def select(locations: list[dict], names: list[str] | None, use_all: bool,
           use_priority: bool) -> list[dict]:
    """Resolve --only / --priority / --all into a list of sub-accounts."""
    if use_all:
        return locations
    wanted = list(names or [])
    if use_priority:
        wanted = [PRIORITY["model"], *PRIORITY["priority"], *wanted]
    picked, missing = [], []
    for name in wanted:
        loc = match_location(locations, name)
        (picked.append(loc) if loc else missing.append(name))
    for name in missing:
        print(f"  ! sub-conta não encontrada (ou ambígua): {name}", file=sys.stderr)
    seen, out = set(), []
    for loc in picked:
        if loc["id"] not in seen:
            seen.add(loc["id"])
            out.append(loc)
    return out


def location_dirs(names: list[str] | None = None) -> list[Path]:
    """Dumped sub-account folders, optionally filtered by name."""
    dirs = sorted(p for p in DUMP.iterdir() if (p / "location.json").exists()) if DUMP.exists() else []
    if not names:
        return dirs
    wanted = {slugify(n) for n in names}
    return [d for d in dirs if d.name in wanted
            or slugify(json.loads((d / "location.json").read_text()).get("name", "")) in wanted]
