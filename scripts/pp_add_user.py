#!/usr/bin/env python3
"""Add a user to a sub-account with the same role and permissions as one of its users.

    ./.venv/bin/python scripts/pp_add_user.py --loc KEJlwJ9kRS8u9QM5kv1X --like brian@blissfulwaterspoolcare.com \\
        --first Jason --last Kirk --email jasonkirk@att.net --phone +12108483438            # plan
    ... --apply

POST services /users/ {companyId, firstName, lastName, email, phone, type: "account", role, locationIds,
permissions}: no scopes (422; GHL builds them from the permissions), no password: the first login is through
"Forgot password" at app.poolprofits.com. The new user stays isActive=false until that first login.
"""
from __future__ import annotations

import argparse
import sys

from _common import load_dotenv

from cli_anything.gohighlevel.utils.agency import SERVICES, Agency


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--loc", required=True)
    parser.add_argument("--like", required=True, help="e-mail or id of the user whose role/permissions are copied")
    parser.add_argument("--first", required=True)
    parser.add_argument("--last", required=True)
    parser.add_argument("--email", required=True)
    parser.add_argument("--phone", default="")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    load_dotenv()
    a = Agency()
    loc = a.location(args.loc)
    users = a.users(args.loc)
    if any((u.get("email") or "").lower() == args.email.lower() for u in users):
        print(f"{args.email} já é usuário de {loc['name']}")
        return 0
    like = next((u for u in users if args.like in (u["id"], (u.get("email") or "").lower())), None)
    if not like:
        sys.exit(f"{args.like} não é usuário de {loc['name']}")
    model = a.call("GET", SERVICES, f"/users/{like['id']}")
    roles = model.get("roles") or {}
    print(f"== {loc['name']}: + {args.first} {args.last} <{args.email}> {args.phone} · papel {roles.get('type')}/"
          f"{roles.get('role')} e permissões de {model.get('name')}")
    if not args.apply:
        return 0
    body = {"companyId": loc["companyId"], "firstName": args.first, "lastName": args.last, "email": args.email,
            "phone": args.phone, "type": roles.get("type", "account"), "role": roles.get("role", "user"),
            "locationIds": [args.loc], "permissions": model.get("permissions") or {}}
    res = a.call("POST", SERVICES, "/users/", body=body)
    new = res.get("user") or res
    got = a.call("GET", SERVICES, f"/users/{new['id']}")
    ok = (got.get("roles") or {}).get("role") == roles.get("role") and got.get("permissions") == model.get("permissions") \
        and args.loc in ((got.get("roles") or {}).get("locationIds") or [])
    print(f"   {'✓' if ok else '✗ VERIFICAR'} {new['id']} · {got.get('name')} · {got.get('email')} · {got.get('phone')}"
          f" · papel {(got.get('roles') or {}).get('role')}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
