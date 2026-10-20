#!/usr/bin/env python3
"""Put a client's own wording into its automations' SMS and e-mails (one config per client).

    ./.venv/bin/python scripts/pp_wording.py --config config/stay_fresh_wording.json            # plan
    ./.venv/bin/python scripts/pp_wording.py --config config/stay_fresh_wording.json --apply
    ./.venv/bin/python scripts/pp_wording.py --config config/stay_fresh_wording.json --test pedro@poolprofits.com

The config lists, per workflow step (workflow name + step name), the client's text verbatim with its
placeholders ([First Name] …), mapped to merge fields by `placeholders`. SMS: the text lives in the
step's template (attributes.template_id). E-mail: subject + html go into the step AND its template.
In SMS, curly quotes/apostrophes become straight ones (same words; keeps the message in GSM-7 when
nothing else forces Unicode); e-mails keep the text exactly. Blank line = paragraph; line break = <br>.
Backup of every workflow and template in backup/<slug>/ before writing.

--test: nothing is written to the client's account. A throwaway workflow in Test Snapshot e-mails
every e-mail (and one "SMS preview" with all the SMS) to the given inbox, rendered for a contact
named Pedro, with the account's custom values filled in; then the workflow and contact are deleted.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import time
import uuid

from _common import ROOT, load_dotenv, slugify
from pp_lead_email import TEST_LOC

from cli_anything.gohighlevel.utils.agency import BACKEND, SERVICES, Agency

P = '<p class="custom-newline" style="line-height: 1.5;padding-left: 0px!important;margin:0px 0px 16px 0px">{}</p>'
STRAIGHT = str.maketrans({"’": "'", "‘": "'", "“": '"', "”": '"'})


def merge(text: str, placeholders: dict[str, str]) -> str:
    for k, v in placeholders.items():
        text = text.replace(k, v)
    left = re.findall(r"\[[A-Z][A-Za-z ]+\]", text)
    if left:
        raise SystemExit(f"placeholder sem merge field: {left}")
    return text


def to_html(text: str) -> str:
    return "".join(P.format("<br>".join(html.escape(line, quote=False) for line in block.split("\n")))
                   for block in text.split("\n\n"))


def wanted(msg: dict, placeholders: dict[str, str]) -> dict:
    """What the step/template must hold: {'body'} for SMS, {'subject', 'html'} for e-mail."""
    if "subject" in msg:
        return {"subject": merge(msg["subject"], placeholders), "html": to_html(merge(msg["text"], placeholders))}
    return {"body": merge(msg["text"], placeholders).translate(STRAIGHT)}


def locate(cfg: dict, flows: dict[str, dict], snippets: dict[str, dict]) -> list[dict]:
    out = []
    for msg in cfg["messages"]:
        wf = flows.get(msg["workflow"])
        if not wf:
            raise SystemExit(f"workflow não encontrado: {msg['workflow']!r}")
        steps = [s for s in wf["workflowData"]["templates"]
                 if s.get("name") == msg["step"] and s["type"] in ("sms", "email")]
        if len(steps) != 1:
            raise SystemExit(f"{msg['workflow']} / {msg['step']}: {len(steps)} passos com esse nome")
        step = steps[0]
        kind = "email" if "subject" in msg else "sms"
        if step["type"] != kind:
            raise SystemExit(f"{msg['workflow']} / {msg['step']}: passo é {step['type']}, config diz {kind}")
        sn = snippets.get((step.get("attributes") or {}).get("template_id"))
        if kind == "sms" and not sn:
            raise SystemExit(f"{msg['workflow']} / {msg['step']}: SMS sem template — texto ficaria no passo")
        out.append({"msg": msg, "wf": wf, "step": step, "snippet": sn, "new": wanted(msg, cfg["placeholders"])})
    return out


def current(item: dict) -> dict:
    at = item["step"]["attributes"]
    tpl = (item["snippet"] or {}).get("template") or {}
    if "body" in item["new"]:
        return {"template": {"body": tpl.get("body")}}
    return {"step": {"subject": at.get("subject"), "html": at.get("html")},
            "template": {"subject": tpl.get("subject"), "html": tpl.get("html")} if item["snippet"] else None}


def done(item: dict) -> bool:
    cur, new = current(item), item["new"]
    if "body" in new:
        return cur["template"]["body"] == new["body"]
    return cur["step"] == new and (cur["template"] is None or cur["template"] == new)


def read(a: Agency, loc: str) -> tuple[dict[str, dict], dict[str, dict]]:
    flows = {}
    for w in a.workflows(loc):
        flows[w["name"]] = a.workflow(loc, w["id"])
    return flows, {s["_id"]: s for s in a.snippets(loc)}


def plain(h: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", " ", re.sub(r"<br>|</p>", "\n", h or ""))).strip()


def apply(a: Agency, loc: str, items: list[dict], bdir) -> None:
    stamp = time.strftime("%Y%m%d-%H%M%S")
    bdir.mkdir(parents=True, exist_ok=True)
    for sid in {i["snippet"]["_id"] for i in items if i["snippet"]}:
        sn = next(i["snippet"] for i in items if i["snippet"] and i["snippet"]["_id"] == sid)
        (bdir / f"snippet-{sid}-{stamp}.json").write_text(json.dumps(sn, ensure_ascii=False))
    for wid in {i["wf"]["id"] for i in items}:
        wf = next(i["wf"] for i in items if i["wf"]["id"] == wid)
        trs = [t for t in a.triggers(loc, wid) if not t.get("deleted")]
        (bdir / f"workflow-{wid}-{stamp}.json").write_text(json.dumps({"workflow": wf, "triggers": trs},
                                                                      ensure_ascii=False))
    for i in items:
        if not i["snippet"]:
            continue
        sn = i["snippet"]
        tpl = dict(sn.get("template") or {})
        tpl.update(i["new"])
        a.call("PUT", BACKEND, f"/snippets/{loc}/{sn['_id']}", body={"name": sn["name"], "type": sn["type"],
                                                                     "template": tpl})
    for wid in {i["wf"]["id"] for i in items if "html" in i["new"]}:
        live = a.workflow(loc, wid)
        new = {i["step"]["id"]: i["new"] for i in items if i["wf"]["id"] == wid and "html" in i["new"]}
        tpl = json.loads(json.dumps(live["workflowData"]["templates"]))
        for s in tpl:
            if s["id"] in new:
                s["attributes"].update(new[s["id"]])
        a.call("PUT", BACKEND, f"/workflow/{loc}/{wid}", body={
            "name": live["name"], "version": live.get("version", 1), "status": live["status"],
            "parentId": live.get("parentId"), "allowMultiple": live.get("allowMultiple", True),
            "workflowData": {"templates": tpl}})


def run_test(a: Agency, cfg: dict, items: list[dict], to: str) -> int:
    """Throwaway workflow in Test Snapshot: one internal e-mail per client e-mail + one with every SMS."""
    values = {(c.get("fieldKey") or "").replace(" ", ""): c.get("value") or ""  # "{{custom_values.business_phone}}"
              for c in a.custom_values(cfg["location"])}
    fill = lambda s: re.sub(r"\{\{custom_values\.\w+\}\}", lambda m: values.get(m.group(0), m.group(0)), s)  # noqa: E731
    mails = [(f"[TEST {i['msg']['workflow']}] " + fill(i["new"]["subject"]), fill(i["new"]["html"]))
             for i in items if "html" in i["new"]]
    sms = "".join(P.format(f"<strong>{html.escape(i['msg']['workflow'])} — {html.escape(i['msg']['step'])}</strong>"
                           f"<br>{html.escape(fill(i['new']['body']))}") for i in items if "body" in i["new"])
    if sms:
        mails.append(("[TEST] SMS preview — {{contact.first_name}}", sms))
    go, ran_tag = "wording test go", "wording test done"
    try:
        a.call("POST", BACKEND, f"/workflow/{TEST_LOC}/tags/create", body={"tag": go})
    except Exception:  # noqa: BLE001 — already exists
        pass
    res = a.call("POST", BACKEND, f"/workflow/{TEST_LOC}", body={"name": "TMP wording test", "status": "draft"})
    wid = res.get("id") or res.get("_id")
    steps = [{"id": str(uuid.uuid4()), "name": "Add Tag", "type": "add_contact_tag",
              "attributes": {"tags": [ran_tag], "type": "add_contact_tag"}}]
    for subject, body in mails:
        steps.append({"id": str(uuid.uuid4()), "name": "Test Email", "type": "internal_notification",
                      "attributes": {"type": "email", "email": {"isCloned": False, "html": body, "to": to,
                                                                "userType": "custom_email", "subject": subject,
                                                                "attachments": []}}})
    for n, s in enumerate(steps):
        s["order"] = n
        if n:
            s["parentKey"] = steps[n - 1]["id"]
        if n + 1 < len(steps):
            s["next"] = steps[n + 1]["id"]
    cid = None
    try:
        a.call("PUT", BACKEND, f"/workflow/{TEST_LOC}/{wid}", body={
            "name": "TMP wording test", "version": 1, "status": "published", "workflowData": {"templates": steps}})
        trig = {"type": "contact_tag", "name": "Contact Tag", "masterType": "highlevel", "schedule_config": {},
                "conditions": [{"operator": "index-of-true", "field": "tagsAdded", "value": go, "title": "Tag Added",
                                "type": "select", "id": "tag-added"}], "workflowId": wid, "workflow_id": wid,
                "location_id": TEST_LOC, "actions": [{"workflow_id": wid, "type": "add_to_workflow"}],
                "targetActionId": steps[0]["id"]}
        t = a.call("POST", BACKEND, f"/workflow/{TEST_LOC}/trigger", body=trig)
        a.call("PUT", BACKEND, f"/workflow/{TEST_LOC}/trigger/{t['id']}", body={**trig, "id": t["id"]})
        time.sleep(5)
        c = a.call("POST", SERVICES, "/contacts/upsert", body={
            "locationId": TEST_LOC, "firstName": "Pedro", "lastName": "TEST wording", "email": "wording-test@example.com"})
        cid = c["contact"]["id"]
        time.sleep(3)
        a.call("POST", SERVICES, f"/contacts/{cid}/tags", body={"tags": [go]})
        ran = False
        for _ in range(12):
            time.sleep(5)
            if ran_tag in a.call("GET", SERVICES, f"/contacts/{cid}")["contact"].get("tags", []):
                ran = True
                break
        time.sleep(20)  # let the e-mail steps after the tag go out
        print(f"   {'✓' if ran else '✗'} workflow de teste rodou · {len(mails)} e-mail(s) para {to} (conferir a caixa)")
        return 0 if ran else 1
    finally:
        if cid:
            a.call("DELETE", SERVICES, f"/contacts/{cid}")
        try:
            a.call("DELETE", BACKEND, f"/workflow/{TEST_LOC}/{wid}")
        except Exception as e:  # noqa: BLE001
            print(f"   apagar à mão: TMP wording test ({wid}): {e}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", required=True)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--test", metavar="EMAIL", help="send the e-mails + an SMS preview to this inbox (Test Snapshot)")
    args = parser.parse_args()
    load_dotenv()
    cfg = json.loads((ROOT / args.config).read_text())
    loc = cfg["location"]
    a = Agency()
    name = a.location(loc)["name"]
    flows, snippets = read(a, loc)
    items = locate(cfg, flows, snippets)
    todo = [i for i in items if not done(i)]
    print(f"== {name}: {len(items)} mensagens, {len(todo)} a mudar")
    for i in items:
        new = i["new"]
        mark = "=" if i not in todo else "→"
        where = f"{i['msg']['workflow']} / {i['msg']['step']}"
        if "body" in new:
            print(f" {mark} SMS   {where} [{(i['snippet'] or {}).get('name')}] ({len(new['body'])} chars)")
            if i in todo:
                print(f"     antes: {current(i)['template']['body']!r}\n     depois: {new['body']!r}")
        else:
            print(f" {mark} EMAIL {where} [{(i['snippet'] or {}).get('name') or 'sem template'}]")
            if i in todo:
                print(f"     assunto: {i['step']['attributes'].get('subject')!r} → {new['subject']!r}")
                print("     " + plain(new["html"]).replace("\n", "\n     "))
    if args.test:
        return run_test(a, cfg, items, args.test)
    if not args.apply or not todo:
        return 0
    apply(a, loc, todo, ROOT / "backup" / slugify(name))
    for _ in range(10):  # template reads lag ~10-20 s behind the write
        time.sleep(5)
        flows2, snippets2 = read(a, loc)
        after = locate(cfg, flows2, snippets2)
        bad = [i for i in after if not done(i)]
        if not bad:
            break
    for w in {i["wf"]["id"]: i["wf"] for i in items}.values():
        got = flows2[w["name"]]
        same = got["status"] == w["status"] and len(got["workflowData"]["templates"]) == len(w["workflowData"]["templates"])
        if not same:
            bad.append({"msg": {"workflow": w["name"], "step": "(estrutura/status)"}})
    for i in bad:
        print(f"   ✗ VERIFICAR {i['msg']['workflow']} / {i['msg']['step']}")
    print(f"   {'✓' if not bad else '✗'} {len(items) - len(bad)}/{len(items)} conferidas no GHL")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
