"""Agency-wide access to every Pool Profits sub-account with one Firebase token.

The FF setup used one Private Integration Token per location. Pool Profits has
many sub-accounts, so everything here runs on the agency user's Firebase
session instead (GHL_FIREBASE_REFRESH_TOKEN): the same identity the GHL web
app uses, which can open every sub-account the user can open in the UI.

Both hosts accept the Firebase JWT in a ``token-id`` header:

- ``services.leadconnectorhq.com``  public-API paths (needs a ``Version`` header)
- ``backend.leadconnectorhq.com``   internal paths (workflow definitions, triggers,
                                   snippets) — the only place workflows can be written

Several reads have more than one known path. ``first_ok`` tries them in order
and remembers which one answered, so a path GHL retires costs one failed call,
not a broken run. Nothing in this module writes to GHL.
"""
from __future__ import annotations

import base64
import json
import re
import time
from typing import Any, Callable, Iterable, Optional

import requests

from cli_anything.gohighlevel.utils.ghl_internal_client import CHROME_UA, TokenManager

SERVICES = "https://services.leadconnectorhq.com"
BACKEND = "https://backend.leadconnectorhq.com"
API_VERSION = "2021-07-28"

# Workflow settings the PUT resets to the default when the body leaves them out (seen 20/10: every
# script that re-saved a workflow turned "allow re-entry" off and dropped its send window).
WORKFLOW_PUT = re.compile(r"^/workflow/([^/]+)/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})$")
WORKFLOW_SETTINGS = ("allowMultiple", "allowMultipleOpportunity", "stopOnResponse", "removeContactFromLastStep",
                     "autoMarkAsRead", "timezone", "window", "eventStartDate", "senderAddress")


class GHLError(RuntimeError):
    def __init__(self, status: int, url: str, body: str):
        super().__init__(f"{status} {url}: {body[:300]}")
        self.status = status
        self.url = url
        self.body = body


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (name or "").lower()).strip("-") or "unnamed"


def _rows(data: Any, *keys: str) -> list:
    """Pull the list out of a GHL response, whatever key it hides under."""
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in keys + ("rows", "data", "items", "results"):
            value = data.get(key)
            if isinstance(value, list):
                return value
    return []


class Agency:
    """Read-only client for every sub-account the token's user can open."""

    def __init__(self, tokens: Optional[TokenManager] = None, sleep: float = 0.15):
        self.tokens = tokens or TokenManager()
        self.sleep = sleep
        self.session = requests.Session()
        self.working_paths: dict[str, str] = {}
        self.calls = 0

    # ── transport ─────────────────────────────────────────────────────────

    def call(self, method: str, host: str, path: str,
             params: dict | None = None, body: dict | None = None,
             version: str = API_VERSION, _retried: bool = False) -> Any:
        url = f"{host}{path}"
        match = WORKFLOW_PUT.match(path) if method == "PUT" and host == BACKEND and body else None
        if match and not _retried:
            body = self._keep_settings(match.group(1), match.group(2), body)
        headers = {
            "token-id": self.tokens.get_token(),
            "channel": "APP",
            "source": "WEB_USER",
            "Version": version,
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": CHROME_UA,
        }
        self.calls += 1
        resp = self.session.request(method, url, headers=headers, params=params,
                                    json=body, timeout=40)
        if resp.status_code == 401 and not _retried:
            self.tokens.force_refresh()
            return self.call(method, host, path, params, body, version, _retried=True)
        if resp.status_code == 429 and not _retried:
            time.sleep(5)
            return self.call(method, host, path, params, body, version, _retried=True)
        if resp.status_code >= 400:
            raise GHLError(resp.status_code, url, resp.text)
        if self.sleep:
            time.sleep(self.sleep)
        if not resp.text:
            return {}
        try:
            return resp.json()
        except ValueError:
            return {"_text": resp.text[:500]}

    def get(self, host: str, path: str, params: dict | None = None) -> Any:
        return self.call("GET", host, path, params=params)

    def _keep_settings(self, loc: str, wf_id: str, body: dict) -> dict:
        """Settings the caller did not send keep their live value instead of falling to the default."""
        missing = [k for k in WORKFLOW_SETTINGS if k not in body]
        if not missing:
            return body
        try:
            live = self.workflow(loc, wf_id)
        except GHLError:
            return body
        return {**body, **{k: live[k] for k in missing if live.get(k) is not None}}

    def first_ok(self, kind: str, attempts: Iterable[tuple[str, Callable[[], Any]]]) -> Any:
        """Run the attempts in order; return the first that answers 2xx.

        The label of the winner is remembered in ``working_paths[kind]`` and
        tried first next time.
        """
        attempts = list(attempts)
        known = self.working_paths.get(kind)
        if known:
            attempts.sort(key=lambda a: a[0] != known)
        errors = []
        for label, fn in attempts:
            try:
                result = fn()
            except GHLError as exc:
                errors.append(f"{label}: {exc.status}")
                continue
            self.working_paths[kind] = label
            return result
        raise GHLError(0, kind, "all paths failed — " + "; ".join(errors))

    # ── identity ──────────────────────────────────────────────────────────

    def claims(self) -> dict:
        """Decoded payload of the Firebase JWT (who the token belongs to)."""
        payload = self.tokens.get_token().split(".")[1]
        payload += "=" * (-len(payload) % 4)
        return json.loads(base64.urlsafe_b64decode(payload))

    def company_id(self) -> str:
        claims = self.claims()
        for key in ("company_id", "companyId", "company"):
            if claims.get(key):
                return str(claims[key])
        nested = claims.get("claims") or {}
        return str(nested.get("company_id") or nested.get("companyId") or "")

    # ── sub-accounts ──────────────────────────────────────────────────────

    def locations(self) -> list[dict]:
        """Every sub-account of the agency, as {id, name, ...} dicts."""
        company = self.company_id()

        def paged(host: str) -> Callable[[], list]:
            def run() -> list:
                out, skip = [], 0
                while True:
                    data = self.get(host, "/locations/search",
                                    {"companyId": company, "limit": 100, "skip": skip})
                    page = _rows(data, "locations")
                    out.extend(page)
                    if len(page) < 100:
                        return out
                    skip += 100
            return run

        def from_claims() -> list:
            ids = self.claims().get("locations") or []
            if not ids:
                raise GHLError(0, "claims", "no locations in token")
            return [self.location(i) for i in ids]

        found = self.first_ok("locations", [
            ("services:/locations/search", paged(SERVICES)),
            ("backend:/locations/search", paged(BACKEND)),
            ("claims.locations", from_claims),
        ])
        return [{"id": l.get("id") or l.get("_id"), **l} for l in found]

    def location(self, loc: str) -> dict:
        data = self.get(SERVICES, f"/locations/{loc}")
        return data.get("location", data)

    # ── workflows ─────────────────────────────────────────────────────────

    def workflows(self, loc: str) -> list[dict]:
        """Flat list of workflows (id, name, status, parentId when known)."""

        def public() -> list:
            return _rows(self.get(SERVICES, "/workflows/", {"locationId": loc}), "workflows")

        def internal() -> list:
            out: list = []

            def walk(parent: str, folder: str) -> None:
                offset = 0
                while True:
                    page = _rows(self.get(BACKEND, f"/workflow/{loc}/list",
                                          {"parentId": parent, "limit": 100, "offset": offset}),
                                 "workflows")
                    for row in page:
                        if row.get("type") == "directory":
                            walk(row.get("_id") or row.get("id"), row.get("name", ""))
                        else:
                            out.append({**row, "folder": folder})
                    if len(page) < 100:
                        return
                    offset += 100

            walk("", "")
            return out

        rows = self.first_ok("workflows", [
            ("services:/workflows/", public),
            ("backend:/workflow/{loc}/list", internal),
        ])
        return [{"id": w.get("id") or w.get("_id"), **w} for w in rows]

    def workflow(self, loc: str, wf_id: str) -> dict:
        return self.get(BACKEND, f"/workflow/{loc}/{wf_id}")

    def triggers(self, loc: str, wf_id: str) -> list[dict]:
        return _rows(self.get(BACKEND, f"/workflow/{loc}/trigger", {"workflowId": wf_id}),
                     "triggers")

    def folders(self, loc: str) -> dict[str, str]:
        """Folder id → name. Empty when GHL does not expose the listing."""
        try:
            page = _rows(self.get(BACKEND, f"/workflow/{loc}/list",
                                  {"parentId": "", "limit": 100, "offset": 0}), "workflows")
        except GHLError:
            return {}
        return {(r.get("_id") or r.get("id")): r.get("name", "")
                for r in page if r.get("type") == "directory"}

    # ── location assets ───────────────────────────────────────────────────

    def custom_values(self, loc: str) -> list[dict]:
        return _rows(self.get(SERVICES, f"/locations/{loc}/customValues"), "customValues")

    def custom_fields(self, loc: str) -> list[dict]:
        return _rows(self.get(SERVICES, f"/locations/{loc}/customFields"), "customFields")

    def tags(self, loc: str) -> list[dict]:
        return _rows(self.get(SERVICES, f"/locations/{loc}/tags"), "tags")

    def pipelines(self, loc: str) -> list[dict]:
        return _rows(self.get(SERVICES, "/opportunities/pipelines", {"locationId": loc}),
                     "pipelines")

    def forms(self, loc: str) -> list[dict]:
        out, skip = [], 0
        while True:
            page = _rows(self.get(SERVICES, "/forms/",
                                  {"locationId": loc, "limit": 50, "skip": skip}), "forms")
            out.extend(page)
            if len(page) < 50:
                return out
            skip += 50

    def calendars(self, loc: str) -> list[dict]:
        return _rows(self.get(SERVICES, "/calendars/", {"locationId": loc}), "calendars")

    def users(self, loc: str) -> list[dict]:
        return _rows(self.get(SERVICES, "/users/", {"locationId": loc}), "users")

    def snippets(self, loc: str) -> list[dict]:
        """SMS and email templates (Marketing → Snippets/Templates)."""
        out: list = []
        for kind in ("sms", "email"):
            try:
                out.extend(_rows(self.get(BACKEND, f"/snippets/{loc}",
                                          {"limit": 500, "type": kind}), "snippets"))
            except GHLError:
                continue
        return out


def match_location(locations: list[dict], wanted: str) -> Optional[dict]:
    """Find a sub-account by id, exact name, or loose name match."""
    for loc in locations:
        if loc.get("id") == wanted:
            return loc
    norm = slugify(wanted)
    exact = [l for l in locations if slugify(l.get("name", "")) == norm]
    if exact:
        return exact[0]
    loose = [l for l in locations if norm in slugify(l.get("name", ""))
             or slugify(l.get("name", "")) in norm]
    return loose[0] if len(loose) == 1 else None
