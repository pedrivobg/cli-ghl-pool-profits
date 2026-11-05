"""Shared bits for the Pool Profits scripts: .env loading and sub-account selection."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from cli_anything.gohighlevel.utils.agency import Agency, match_location, slugify  # noqa: E402,F401

# Another agency's dumps go elsewhere (e.g. GHL_DUMP_DIR=dump/poolduck) so the Pool Profits
# scripts, which scan every folder in dump/, never pick them up.
_AGENCY = os.environ.get("GHL_AGENCY", "").strip().lower()
# GHL_AGENCY must pick the dump dir here, at import: scripts do `from _common import DUMP` before load_dotenv runs
# (05/11: a GHL_AGENCY=poolduck dump landed in dump/ and mixed with the Pool Profits sub-accounts).
DUMP = Path(os.environ.get("GHL_DUMP_DIR") or (ROOT / "dump" / _AGENCY if _AGENCY else ROOT / "dump")).resolve()
REPORTS = ROOT / "reports"
PRIORITY = json.loads((ROOT / "config" / "priority.json").read_text())


AGENCY_TOKENS = {"poolduck": "POOLDUCK_FIREBASE_REFRESH_TOKEN", "burchtech": "BURCHTECH_FIREBASE_REFRESH_TOKEN",
                 "poolheads_old": "POOLHEADS_OLD_FIREBASE_REFRESH_TOKEN"}


def load_dotenv() -> None:
    """`.env` first; then, with GHL_AGENCY=poolduck|burchtech|poolheads_old, use that agency's token from the
    environment variables (set in the cloud environment, never in the repo) and its own dump dir."""
    path = ROOT / ".env"
    if path.exists():
        for line in path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, val = line.partition("=")
                os.environ.setdefault(key.strip(), val.strip())
    agency = os.environ.get("GHL_AGENCY", "").strip().lower()
    if agency:
        var = AGENCY_TOKENS.get(agency)
        if not var or not os.environ.get(var):
            sys.exit(f"GHL_AGENCY={agency}: variável {var or '?'} não está no ambiente")
        os.environ["GHL_FIREBASE_REFRESH_TOKEN"] = os.environ[var]
        os.environ["GHL_DUMP_DIR"] = str(ROOT / "dump" / agency)


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
    wanted = [slugify(n) for n in names]
    return [d for d in dirs if any(w == d.name or w in d.name or d.name in w for w in wanted)]


def keep_redirect(fd: dict) -> dict:
    """Before saving a form: the widget redirects with formAction.redirect_url, but the form GET returns only
    redirectUrl, so a GET → POST round trip used to drop the redirect (BluVantage 15/10, Southern 16/10). Sets both."""
    act = (fd.get("form") or {}).get("formAction") or {}
    url = act.get("redirect_url") or act.get("redirectUrl")
    if str(act.get("actionType")) == "1" and url:
        act.update(redirectUrl=url, redirect_url=url)
    return fd
