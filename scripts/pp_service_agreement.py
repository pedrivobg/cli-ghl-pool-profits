#!/usr/bin/env python3
"""Pool Service Agreement template (Payments -> Proposals & Estimates -> Templates), Ed 17/11.

Source = Clean Co Pools' "Pool Service Agreement" (Ed wrote it). Changes:
  - company name typed in the text ("Clean Co." / "Clean Co. Pool and Spa Pro's") -> {{location.name}}
  - "made this day" -> "made on {{document.createdDate}}"
  - Customer Information table: Name/Email/Phone/Street/City/State/Zip come from the contact
    ({{contact.name}}, {{contact.email}}, {{contact.phone}}, {{contact.address1}}, {{contact.city}},
    {{contact.state}}, {{contact.postal_code}}); the blank fill-in boxes for those rows are removed.
    "Dog on site?", card info, signature and date stay as fill-in fields for the customer.
  - --example (snapshot copy): the logo is replaced by an "EXAMPLE ONLY" banner, name "Pool Service Agreement (Example)".
Variables render when the document is created for a contact (tested 17/11 on a ZZ TEST template + contact in the
Snapshot: every variable above came out filled in the public link).

API (agency token): GET services /proposals/templates/{id}?locationId; PUT same path with the template body minus
read-only keys (_id, versionHistory, type, meta, tags, version...); POST /proposals/templates {locationId, name,
type: "proposal"} creates an empty one. Test = POST /proposals/templates/send {sendDocument: false} + POST
/proposals/document/send {medium: "link"} -> link.poolprofits.com/documents/v1/<referenceId>.

  python3 scripts/pp_service_agreement.py plan
  python3 scripts/pp_service_agreement.py apply --loc <loc> --tpl <id> [--example] [--name "..."]
"""
from __future__ import annotations

import argparse
import copy
import datetime as dt
import json
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
from cli_anything.gohighlevel.utils.agency import SERVICES, Agency  # noqa: E402

CLEANCO = "GcsMfF3Np8B43qyum1aT"
SOURCE_TPL = "68646ae7e76781c6d061ef32"
READ_ONLY = {"_id", "id", "versionHistory", "traceId", "createdAt", "updatedAt", "__v", "paymentInfo",
             "contentLibraryThumbnail", "deleted", "updatedBy", "docFormPublicLink", "tags", "version",
             "locationId", "type", "meta"}
# row label in the Customer Information table -> variable; fieldIds of the fill-in boxes on those rows
ROWS = [("Name:", "{{contact.name}}", "text_field_2"), ("Email:", "{{contact.email}}", "text_field_4"),
        ("Phone Number:", "{{contact.phone}}", "text_field_5"),
        ("Service Street Address:", "{{contact.address1}}", "text_field_7"),
        ("Service City:", "{{contact.city}}", "text_field_8"), ("Service State:", "{{contact.state}}", "text_field_9"),
        ("Service Zip Code", "{{contact.postal_code}}", "text_field_10")]
BANNER = ('<p style="line-height: 1.4; text-align: center"><span style="font-size: 16px; font-family: Arial; '
          'color: rgb(200, 30, 30)"><strong>EXAMPLE ONLY: update everything written in this agreement to fit your '
          'business before sending it.</strong></span></p><p style="line-height: 1.4; text-align: center"><span '
          'style="font-size: 12px; font-family: Arial; color: rgb(200, 30, 30)">This is not legal advice. Have a '
          'licensed attorney in your state review it before using it with customers. Delete this notice when '
          'done.</span></p>')


def transform(src: dict, example: bool) -> dict:
    d = copy.deepcopy(src)
    page = d["pages"][0]
    drop = {f for _, _, f in ROWS}
    for n in page["children"]:
        opts = n["component"]["options"]
        if n["type"] == "Text":
            t = opts["text"]
            t = t.replace("Clean Co. Pool and Spa Pro's", "{{location.name}}")
            t = t.replace("YOUR NAME Pool and Spa Pro's", "{{location.name}}")
            t = re.sub(r"Clean Co\.?(?=[\s<,'])", "{{location.name}}", t)
            t = t.replace("YOUR NAME", "{{location.name}}")
            t = t.replace("is made this day between", "is made on {{document.createdDate}} between")
            opts["text"] = t
        if n["type"] == "Table" and "Name:" in opts.get("text", ""):
            t = opts["text"]
            for label, var, _ in ROWS:
                pat = re.compile(r"(<p[^>]*>" + re.escape(label) + r"\s*</p></td><td[^>]*><p[^>]*>)(</p>)")
                t, k = pat.subn(lambda m: m.group(1) + var + m.group(2), t, count=1)
                if not k:
                    raise SystemExit(f"row not found: {label}")
            opts["text"] = t
            n["children"] = [c for c in n["children"] if c["component"]["options"].get("fieldId") not in drop]
    d["fillableFields"] = [f for f in d["fillableFields"] if f["fieldId"] not in drop]
    if example:
        img = page["children"][0]
        assert img["type"] == "Image", img["type"]
        text_tpl = next(n for n in page["children"] if n["type"] == "Text")
        banner = copy.deepcopy(text_tpl)
        banner["id"] = img["id"]
        banner["component"]["options"]["text"] = BANNER
        pos = img["responsiveStyles"]["large"]["position"]
        banner["responsiveStyles"]["large"]["position"] = {"top": pos["top"], "left": 48, "bottom": pos["bottom"]}
        banner["responsiveStyles"]["large"]["backgroundColor"] = "#fff4f4"
        page["children"][0] = banner
    return d


def body_for(d: dict, loc: str, name: str, live: dict) -> dict:
    b = {k: v for k, v in d.items() if k not in READ_ONLY}
    b["locationId"] = loc
    b["name"] = name
    b["variables"] = live.get("variables", b.get("variables", []))
    return b


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["plan", "apply"])
    ap.add_argument("--loc")
    ap.add_argument("--tpl")
    ap.add_argument("--name")
    ap.add_argument("--example", action="store_true")
    args = ap.parse_args()
    a = Agency()
    src = a.get(SERVICES, f"/proposals/templates/{SOURCE_TPL}", {"locationId": CLEANCO})
    new = transform(src, args.example)
    if args.cmd == "plan":
        for n in new["pages"][0]["children"]:
            t = re.sub("<[^>]+>", " ", n["component"]["options"].get("text") or "")
            print(n["type"], set(re.findall(r"\{\{[^}]+\}\}", t)), len(n.get("children", [])))
        print("fillable:", [f["fieldId"] for f in new["fillableFields"]])
        return
    live = a.get(SERVICES, f"/proposals/templates/{args.tpl}", {"locationId": args.loc})
    os.makedirs(os.path.join(ROOT, "backup", "proposals"), exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    with open(os.path.join(ROOT, "backup", "proposals", f"{args.loc}-{args.tpl}-{stamp}.json"), "w") as f:
        json.dump(live, f, indent=1)
    name = args.name or live["name"]
    a.call("PUT", SERVICES, f"/proposals/templates/{args.tpl}", body=body_for(new, args.loc, name, live))
    back = a.get(SERVICES, f"/proposals/templates/{args.tpl}", {"locationId": args.loc})
    s = json.dumps(back["pages"])
    print("saved", back["name"], "vars:", sorted(set(re.findall(r"\{\{[^}]+\}\}", s))),
          "fillable:", len(back["fillableFields"]), "example banner:", "EXAMPLE ONLY" in s)


if __name__ == "__main__":
    main()
