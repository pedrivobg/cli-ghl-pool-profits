#!/usr/bin/env python3
"""Mark ClickUp things as read / clear them from Pedro's Inbox (Pedro 17/11: "está ficando uma bagunça").

The public ClickUp API has NO read-state endpoint. These are the web app's own endpoints on the workspace shard
(frontdoor-prod-us-east-2-2.clickup.com), found in the app's JS and tested live 17/11. They need Pedro's browser session
token, which is a network secret of the Claude Code environment: the proxy injects `Authorization: Bearer …` into every
request to that host, so nothing here holds or prints a token. When it expires every call returns 401 → this script exits
2 and the routine emails Pedro "[Passo seu] ClickUp: renovar o token" (steps in docs/inbox-watch-routine.md).

  python3 scripts/cu_mark_read.py --list                                  # what is unread now (Inbox + chat)
  python3 scripts/cu_mark_read.py --channel 2kyd9h1f-1154                 # DM / group DM / channel (whole view)
  python3 scripts/cu_mark_read.py --thread 80140067278020                 # chat thread or task-comment thread (parent id)
  python3 scripts/cu_mark_read.py --task 86bd3m8cc                        # task comments read + its Inbox bundle read+cleared
  python3 scripts/cu_mark_read.py --clear-activity --older-hours 24       # Inbox: clear assignment/status-only bundles
  (several flags can be combined; each may repeat)

Endpoints (all relative to the shard host):
  POST /inbox/v3/workspaces/{ws}/notifications/bundles/search {pagination:{limit,nextCursor}}  → bundles
  PUT  /inbox/v3/workspaces/{ws}/notifications/bundles/read {bundleSnapshotId}                 → bundle read
  PUT  /inbox/v3/workspaces/{ws}/notifications/bundles/{urlencoded bundle id}/clear {}         → bundle cleared
  PUT  /comment-service/v3/workspaces/{ws}/comments/last_read_at {keys:[{object_id, object_type: view|comment|task}],
       attributes:{date: now ms, override_prior_date: true}}                                   → read up to now
  POST same path {keys}                                                                        → current state
  POST …/comments/last_read_at/search_threads {filters:{limit, root_parent_id, unread: true}}  → unread threads
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

WS = "90141148207"
HOST = "https://frontdoor-prod-us-east-2-2.clickup.com"
INBOX = f"/inbox/v3/workspaces/{WS}/notifications/bundles"
LAST = f"/comment-service/v3/workspaces/{WS}/comments/last_read_at"


class AuthExpired(Exception):
    pass


def call(method: str, path: str, body: dict | None = None):
    data = json.dumps(body if body is not None else {}).encode()
    req = urllib.request.Request(HOST + path, data=data if method != "GET" else None, method=method,
                                 headers={"content-type": "application/json",
                                          # placeholder: the environment's proxy replaces it with Pedro's session token
                                          "authorization": "Bearer proxy-injected"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read().decode() or "{}"
    except urllib.error.HTTPError as e:
        body = e.read() or b""
        if e.code in (401, 403) or (e.code == 400 and b"JWT" in body):
            raise AuthExpired(f"{e.code} on {path}") from None
        raise RuntimeError(f"{e.code} on {path}: {body[:200]!r}") from None
    try:
        return json.loads(raw)
    except ValueError:
        return {}


def bundles() -> list[dict]:
    out, cur = [], None
    for _ in range(20):
        b = {"pagination": {"limit": 50, **({"nextCursor": cur} if cur else {})}}
        d = call("POST", f"{INBOX}/search", b)
        for g in d.get("notificationBundleGroups", []):
            out += g.get("notificationBundles", [])
        cur = d.get("nextCursor")
        if not cur:
            break
    return out


def read_keys(keys: list[dict]) -> list[dict]:
    if not keys:
        return []
    d = call("PUT", LAST, {"keys": keys, "attributes": {"date": int(time.time() * 1000), "override_prior_date": True}})
    return d.get("comments_last_read_at", [])


def state(keys: list[dict]) -> list[dict]:
    return call("POST", LAST, {"keys": keys}).get("comments_last_read_at", []) if keys else []


def clear_bundle(b: dict) -> None:
    call("PUT", f"{INBOX}/read", {"bundleSnapshotId": b["id"]})
    call("PUT", f"{INBOX}/{urllib.parse.quote(b['id'], safe='')}/clear", {})


def when(b: dict) -> float:
    t = ((b.get("previewNotification") or {}).get("historyItem") or {}).get("occurredAt") or ""
    try:
        return time.mktime(time.strptime(t[:19], "%Y-%m-%dT%H:%M:%S")) - time.timezone
    except ValueError:
        return time.time()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--channel", action="append", default=[])
    ap.add_argument("--thread", action="append", default=[])
    ap.add_argument("--task", action="append", default=[])
    ap.add_argument("--clear-activity", action="store_true")
    ap.add_argument("--older-hours", type=float, default=24)
    a = ap.parse_args()
    try:
        if a.list:
            bs = bundles()
            print(f"Inbox: {len(bs)} uncleared bundles")
            for b in bs:
                print(f"   {b.get('unreadCount', 0):3} {b['bundleType']:9} {b['rootEntityResourceName'].split(':', 2)[-1]}"
                      f" {time.strftime('%m-%d %H:%M', time.gmtime(when(b)))}")
            for ch in a.channel:
                th = call("POST", f"{LAST}/search_threads", {"filters": {"limit": 100, "root_parent_id": ch, "unread": True}})
                print(f"   channel {ch}: {len(th) if isinstance(th, list) else '?'} unread threads")
        keys = ([{"object_id": c, "object_type": "view"} for c in a.channel]
                + [{"object_id": t, "object_type": "comment"} for t in a.thread]
                + [{"object_id": t, "object_type": "task"} for t in a.task])
        if keys and not a.list:
            for x in read_keys(keys):
                d = x.get("data") or {}
                print(f"read {x['key']['object_type']:7} {x['key']['object_id']}: unread={d.get('has_unread')}")
            if a.channel:  # threads inside a channel keep their own unread flag: read those too
                for ch in a.channel:
                    th = call("POST", f"{LAST}/search_threads", {"filters": {"limit": 100, "root_parent_id": ch, "unread": True}})
                    tk = [{"object_id": t["parent_id"], "object_type": "comment"} for t in (th if isinstance(th, list) else [])]
                    if tk:
                        read_keys(tk)
                        print(f"read {len(tk)} threads in {ch}")
        if a.task or a.clear_activity:
            cut = time.time() - a.older_hours * 3600
            for b in bundles():
                tid = b["rootEntityResourceName"].split(":")[-1]
                if tid in a.task or (a.clear_activity and b["bundleType"] == "activity" and not b.get("hasMention")
                                     and when(b) < cut):
                    clear_bundle(b)
                    print(f"cleared Inbox {b['bundleType']} {tid}")
    except AuthExpired as e:
        print(f"ClickUp session token expired or missing ({e}). Pedro must paste a new one (docs/inbox-watch-routine.md).")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
