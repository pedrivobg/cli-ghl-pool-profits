"""GoHighLevel internal API client for workflow creation.

Uses Firebase JWT auth against backend.leadconnectorhq.com.
Adapted from ghl-superspeed-v3-main/lib/engine.py (2026-03-25).

EXPERIMENTAL: Gated behind --experimental flag in CLI.
"""
from __future__ import annotations

import hashlib
import json
import os
import ssl
import sys
import time
import urllib.error
import urllib.request
from typing import Any, Optional

BASE_URL = "https://backend.leadconnectorhq.com"
FIREBASE_API_KEY = "AIzaSyB_w3vXmsI7WeQtrIOkjR6xTRVN5uOieiE"
CTX = ssl.create_default_context()

CHROME_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

# Keys to strip from GET responses before PUT (avoids validation errors)
STRIP_KEYS = frozenset([
    "_id", "id", "__v", "createdAt", "updatedAt", "companyId", "locationId",
    "companyAge", "creationSource", "originType", "deleted",
    "isTriggerBucketMigrated", "permissionMeta",
])


class TokenManager:
    """Firebase refresh token management with auto-refresh.

    Token sources (in priority order):
    1. Cached token (if < 50 minutes old)
    2. Firebase refresh token (from GHL_FIREBASE_REFRESH_TOKEN env var)
    3. Direct Firebase token (from GHL_FIREBASE_TOKEN env var)
    """

    def __init__(self):
        self._token: Optional[str] = None
        self._token_time: float = 0

    # Google rate-limits token exchanges per minute, and every script run used to do
    # one; the ID token is shared between runs through this gitignored file — one per
    # refresh token, so two agencies never pick up each other's token.
    @property
    def CACHE(self) -> str:
        key = hashlib.sha256(os.environ.get("GHL_FIREBASE_REFRESH_TOKEN", "").strip().encode()).hexdigest()[:12]
        return os.path.join(os.path.dirname(__file__), "..", "..", "..", f".token-cache-{key}.json")

    def _read_cache(self) -> None:
        try:
            with open(self.CACHE) as fh:
                cached = json.load(fh)
            if time.time() - cached["time"] < 3000:
                self._token, self._token_time = cached["token"], cached["time"]
        except (OSError, ValueError, KeyError):
            pass

    def _write_cache(self) -> None:
        try:
            fd = os.open(self.CACHE, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            with os.fdopen(fd, "w") as fh:
                json.dump({"token": self._token, "time": self._token_time}, fh)
        except OSError:
            pass

    def get_token(self) -> str:
        """Get a valid Firebase JWT token."""
        # 1. Check if current token is still fresh (< 50 min), here or in the cache file
        if not self._token:
            self._read_cache()
        if self._token and (time.time() - self._token_time) < 3000:
            return self._token

        # 2. Try Firebase refresh token
        refresh_token = os.environ.get("GHL_FIREBASE_REFRESH_TOKEN", "").strip()
        if refresh_token:
            token = None
            for wait in (0, 20, 40):  # quota is per minute: wait it out
                time.sleep(wait)
                token = self._refresh_firebase(refresh_token)
                if token:
                    break
            if token:
                self._token = token
                self._token_time = time.time()
                self._write_cache()
                return token
            print(
                "Error: Firebase refresh token is set but token refresh failed.\n"
                "The refresh token may be revoked or expired.\n"
                "Get a new one with the DevTools snippet in docs/get-firebase-token.md.",
                file=sys.stderr,
            )
            sys.exit(1)

        # 3. Try direct Firebase token from env
        token = os.environ.get("GHL_FIREBASE_TOKEN", "").strip()
        if token:
            self._token = token
            self._token_time = time.time()
            return token

        print(
            "Error: No Firebase token available for internal API.\n"
            "Set GHL_FIREBASE_REFRESH_TOKEN (preferred) or GHL_FIREBASE_TOKEN.\n"
            "Get the refresh token with the DevTools snippet in docs/get-firebase-token.md.",
            file=sys.stderr,
        )
        sys.exit(1)

    def force_refresh(self) -> str:
        """Force token refresh (called on 401)."""
        self._token = None
        self._token_time = 0
        try:
            os.remove(self.CACHE)  # the cached token is the one that was just refused
        except OSError:
            pass
        return self.get_token()

    def _refresh_firebase(self, refresh_token: str) -> Optional[str]:
        """Exchange Firebase refresh token for a fresh ID token."""
        try:
            body = f"grant_type=refresh_token&refresh_token={refresh_token}"
            req = urllib.request.Request(
                f"https://securetoken.googleapis.com/v1/token?key={FIREBASE_API_KEY}",
                data=body.encode(),
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                method="POST",
            )
            with urllib.request.urlopen(req, context=CTX, timeout=10) as r:
                data = json.loads(r.read())
                return data.get("id_token", "")
        except Exception:
            return None


class InternalGHLClient:
    """GHL internal API client (backend.leadconnectorhq.com).

    Uses Firebase JWT auth with token-id header (NOT Authorization: Bearer).
    """

    def __init__(self, token_mgr: TokenManager, location_id: str):
        self.token_mgr = token_mgr
        self.location_id = location_id
        self._call_count = 0

    @property
    def call_count(self) -> int:
        return self._call_count

    def request(self, method: str, path: str, body: dict[str, Any] | None = None) -> Optional[dict]:
        """Make an API request with auto-retry on 401."""
        token = self.token_mgr.get_token()
        result = self._do_request(method, path, body, token)

        # Retry on auth failure
        if result is None:
            token = self.token_mgr.force_refresh()
            result = self._do_request(method, path, body, token)

        return result

    def _do_request(
        self, method: str, path: str, body: dict | None, token: str
    ) -> Optional[dict]:
        self._call_count += 1
        safe_token = token.encode("ascii", "ignore").decode("ascii").strip()
        headers = {
            "token-id": safe_token,
            "channel": "APP",
            "source": "WEB_USER",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": CHROME_UA,
        }
        url = f"{BASE_URL}{path}"
        data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body else None
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, context=CTX, timeout=30) as resp:
                text = resp.read().decode()
                return json.loads(text) if text else {}
        except urllib.error.HTTPError as e:
            if e.code in (401, 403):
                return None  # Signal retry
            error_body = e.read().decode() if e.fp else ""
            return {"_error": True, "code": e.code, "message": error_body[:200]}
        except Exception as ex:
            return {"_error": True, "message": str(ex)}

    def create_location_tag(self, tag: str) -> bool:
        """Create a tag at location level (required before using in triggers)."""
        result = self.request(
            "POST", f"/workflow/{self.location_id}/tags/create", {"tag": tag}
        )
        return bool(result and not result.get("_error"))
