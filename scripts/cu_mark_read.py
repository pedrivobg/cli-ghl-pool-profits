#!/usr/bin/env python3
"""Mark ClickUp things as read / clear them from Pedro's Inbox (Pedro 17/11: "está ficando uma bagunça").

The public ClickUp API has NO read-state endpoint. These are the web app's own endpoints on the workspace shard
(frontdoor-prod-us-east-2-2.clickup.com), found in the app's JS and tested live 17/11. They need Pedro's browser session
token, which is a network secret of the Claude Code environment: the proxy injects `Authorization: Bearer …` into every
request to that host, so nothing here holds or prints a token. When it expires every call returns 401 → this script exits
2 and the routine emails Pedro "[Passo seu] ClickUp: renovar o token" (steps in docs/inbox-watch-routine.md).

  python3 scripts/cu_mark_read.py --sweep [--dry]                         # read/clear everything already answered
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
import re
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


PEDRO = 106228366
COMMENTS = f"/comment-service/v3/workspaces/{WS}/comments"
# same idea as the n8n triage: a short thanks/ok with no question and no request is not something to answer
ACK = re.compile(r"^\s*(?:@?[\w .]{0,25}[,!:]?\s*)?(thanks?( you)?|thank u|ty|tysm+|thx|perfect|great|awesome|amazing+|beautiful|"
                 r"cool|nice|love it|got it|ok(ay)?|k|sounds (good|great|perfect)|will do|noted|on it|yes please|yep|yup|"
                 r"no worries|copy that|good morning|morning|hi|hello|hey|mahalo)\b[^?]{0,90}$", re.I)
REQUEST = re.compile(r"\b(help|need|can you|could you|please|fix|check|why|how|what|when|where|which|should)\b", re.I)


def latest(kind: str, oid: str, n: int = 10) -> list[dict]:
    path = {"view": "view", "comment": "comment", "task": "task"}[kind]
    cs = call("GET", f"{COMMENTS}/{path}/{urllib.parse.quote(oid, safe='')}?limit={n}").get("comments", [])
    return sorted(cs, key=lambda c: int(c.get("date") or 0), reverse=True)


def handled(cs: list[dict]) -> tuple[bool, str]:
    """True when Pedro wrote last, or the last message is a bare thanks/ok after a message from Pedro."""
    if not cs:
        return True, "no messages"
    last = cs[0]
    txt = re.sub(r"\s+", " ", last.get("text_content") or "").strip()
    if int(last.get("userid") or 0) == PEDRO:
        return True, "Pedro replied last"
    tagged = {int((p.get("user") or {}).get("id") or 0) for p in (last.get("comment") or []) if p.get("type") == "tag"}
    if tagged and PEDRO not in tagged:
        return True, f"addressed to someone else ({len(tagged)} tagged, not Pedro)"
    # everything since Pedro's last message: if nobody tagged/named Pedro and someone else was tagged, it's their talk
    since = []
    for c in cs:
        if int(c.get("userid") or 0) == PEDRO:
            break
        since.append(c)
    tags = [{int((p.get("user") or {}).get("id") or 0) for p in (c.get("comment") or []) if p.get("type") == "tag"}
            for c in since]
    named = any(PEDRO in t or re.search(r"\bpedro\b", c.get("text_content") or "", re.I) for t, c in zip(tags, since))
    if not named and any(t for t in tags):
        return True, "conversation between others since Pedro's last message"
    pedro_before = any(int(c.get("userid") or 0) == PEDRO for c in cs[1:])
    if pedro_before and len(txt) <= 160 and "?" not in txt and ACK.match(re.sub(r"@\S+( \S+)?", "", txt).strip()) \
            and not REQUEST.search(txt):
        return True, "thanks/ok after Pedro"
    return False, f"last from user {last.get('userid')}: {txt[:80]!r}"


def unread_parents() -> list[dict]:
    since = int((time.time() - 14 * 86400) * 1000)
    out, cur = [], None
    for _ in range(20):
        q = f"?next_cursor={urllib.parse.quote(cur)}" if cur else ""
        d = call("GET", f"{LAST}/delta/{since}{q}")
        out += [x.get("data") or x for x in d.get("comments_last_read_at", [])]
        cur = d.get("next_cursor")
        if not cur:
            break
    seen, res = set(), []
    for x in out:
        k = (x.get("parent_type"), x.get("parent_id"))
        if x.get("has_unread") and k not in seen:
            seen.add(k)
            res.append(x)
    return res


def sweep(dry: bool) -> int:
    """Mark read everything already answered; leave (and list) what still needs a reply."""
    left = 0
    for x in unread_parents():
        kind, oid = x.get("parent_type"), x.get("parent_id")
        if kind not in ("view", "comment", "task"):
            continue
        ok, why = handled(latest(kind, oid))
        print(f"{'read ' if ok else 'LEFT '} {kind:7} {oid}: {why}")
        if ok and not dry:
            read_keys([{"object_id": oid, "object_type": kind}])
        left += not ok
    for b in bundles():
        root = b["rootEntityResourceName"].split(":")
        kind, oid = root[1], root[-1]
        if b["bundleType"] == "activity" and not b.get("hasMention"):
            ok, why = True, "activity (status/assignee), no mention"
        elif kind == "task":
            ok, why = handled(latest("task", oid))
        elif kind == "chat-view":
            ok, why = handled(latest("view", oid))
        else:
            ok, why = False, f"unknown bundle {kind}"
        print(f"{'clear' if ok else 'LEFT '} Inbox {b['bundleType']:8} {oid}: {why}")
        if ok and not dry:
            clear_bundle(b)
        left += not ok
    return left


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--channel", action="append", default=[])
    ap.add_argument("--thread", action="append", default=[])
    ap.add_argument("--task", action="append", default=[])
    ap.add_argument("--clear-activity", action="store_true")
    ap.add_argument("--older-hours", type=float, default=24)
    ap.add_argument("--sweep", action="store_true", help="mark read everything already answered (Pedro wrote last)")
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    try:
        if a.sweep:
            left = sweep(a.dry)
            print(f"{left} still need a reply")
            return 0
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
        if a.task or a.channel or a.clear_activity:
            cut = time.time() - a.older_hours * 3600
            for b in bundles():
                tid = b["rootEntityResourceName"].split(":")[-1]
                if tid in a.task or tid in a.channel or (a.clear_activity and b["bundleType"] == "activity" and not b.get("hasMention")
                                     and when(b) < cut):
                    clear_bundle(b)
                    print(f"cleared Inbox {b['bundleType']} {tid}")
    except AuthExpired as e:
        print(f"ClickUp session token expired or missing ({e}). Pedro must paste a new one (docs/inbox-watch-routine.md).")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
