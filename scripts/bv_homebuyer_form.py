#!/usr/bin/env python3
"""BluVantage: Homebuyer Postcard campaign (Val, ClickUp 86bck0f6j, 06/11). QR code on the postcard → Atif's landing page
go.bluvantagepools.com/new-homeowner-welcome---landing-page → thank-you /new-homeowner-welcome---thank-you.

    ./.venv/bin/python scripts/bv_homebuyer_form.py plan
    ./.venv/bin/python scripts/bv_homebuyer_form.py test --to pedro@poolprofits.com
    ./.venv/bin/python scripts/bv_homebuyer_form.py apply            # form + workflow + page

Form "Homebuyer Postcard Campaign": built from the NEWEST version of Atif's "BluVantage — New Homeowner Welcome" (his
look, "Claim My Offer" button, our SMS consent): First Name, Last Name, Property Address (one field, Google
autocomplete, as on the NorTex LPs), Email, Phone (US country picker), consent, button. After submit → the thank-you
page (redirectUrl + redirect_url; a created form drops redirect_url, so it is saved again with keep_redirect, retrying
the 404 a new form gives for a few minutes).
Workflow "Homebuyer Postcard Campaign - New Lead": copy of "AdWords Form - Heater & Equipment Repair" (the LP pattern)
without the Google Ads conversion (postcard, not an ad) nor the Service Requested field; guard = the account's
spam / dnd / current customer if/else; tags `new lead` + `printed marketing materials` (the postcard source, as the
printed-materials phone line) + `homebuyer postcard campaign`; card 💧 Pool Leads 💧 → New Lead with source
"Homebuyer Postcard Campaign"; text to the 5 team users + e-mail to Vanessa and Paul; the same reply text to the lead.
Trigger: Form Submitted = the new form or Atif's (in case the page goes back to it).
Page: the form element of the landing page points to the new form (backup first, saved live).
test: a ZZ TEST copy (Contact Tag trigger, e-mail only to --to, no texts) with 3 contacts: lead → tags + card;
spam → nothing; current customer → nothing. Everything deleted afterwards. A real submit (Turnstile) is by hand.
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
import time
import uuid

import requests

from _common import ROOT, keep_redirect, load_dotenv
from bv_service_forms import diverted, first_id, latest_form_data, put_flow
from nx_ads_form_style import ADDRESS, ADDRESS_CFG
from pd_lwr_pages import nodes
from pp_source_tags import drop_step, fresh_ids, refs_ok

from cli_anything.gohighlevel.utils.agency import BACKEND, SERVICES, Agency

LOC = "KLFYmoVapqQgX3T0AnLn"
ATIF_FORM = "mLGnkBqG0Zbrgjl4p41w"  # BluVantage — New Homeowner Welcome (Atif, 05/11)
FORM_NAME = "Homebuyer Postcard Campaign"
FLOW_NAME = "Homebuyer Postcard Campaign - New Lead"
BASE_FLOW = "AdWords Form - Heater & Equipment Repair"
PAGE = "BCsQYJZVHKONhfE4LXFj"  # New Homeowner Welcome - Landing Page
LANDING = "https://go.bluvantagepools.com/new-homeowner-welcome---landing-page"
THANKS_URL = "https://go.bluvantagepools.com/new-homeowner-welcome---thank-you"
SOURCE = "Homebuyer Postcard Campaign"
TAGS = ["new lead", "printed marketing materials", "homebuyer postcard campaign"]
GUARD = ["spam", "dnd", "current customer"]  # "Not spam / not a customer?" of the call flows
TEST_TAG = "zz test homebuyer postcard"
BDIR = ROOT / "backup" / "bluvantage-pool-service"
P = '<p style="margin:0px;font-family:verdana,geneva,sans-serif;font-size:16px;">'


def build_form(atif: dict) -> dict:
    fd = copy.deepcopy(atif)
    f = fd["form"]
    by = {x["tag"]: x for x in f["fields"]}
    first, last, email, phone, consent, button = (copy.deepcopy(by[k]) for k in (
        "first_name", "last_name", "email", "phone", "terms_and_conditions", "button"))
    first["required"] = True
    phone.update(required=True, enableCountryPicker=True)
    email["required"] = True
    f["address"] = copy.deepcopy(ADDRESS_CFG)
    f["fields"] = [first, last, copy.deepcopy(ADDRESS), email, phone, consent, button]
    f["formAction"] = {**(f.get("formAction") or {}), "actionType": "1", "redirectUrl": THANKS_URL, "redirect_url": THANKS_URL}
    f["showSubmissionInConversationsFeed"] = True
    fd["emailNotifications"] = False  # alerts go by the workflow, as on the other BluVantage forms
    return fd


def guard(node: dict) -> None:
    """The if/else of the base flow checks only `current customer`: one condition per tag, as the call flows."""
    seg = node["attributes"]["branches"][0]["segments"][0]
    proto = next(c for c in seg["conditions"] if c["conditionValue"] == ["current customer"])
    seg["conditions"] = [{**copy.deepcopy(proto), "conditionValue": [t], "__conditionId": str(uuid.uuid4())} for t in GUARD]
    seg["operator"] = "and"


def build_flow(src: list[dict]) -> list[dict]:
    tpl = fresh_ids(src)
    for sid in [s["id"] for s in tpl if s["type"] in ("google_adword", "update_contact_field")]:
        tpl = drop_step(tpl, sid)
    for st in tpl:
        a = st.get("attributes") or {}
        if st["type"] == "if_else" and a.get("branches"):
            guard(st)
        elif st["type"] == "add_contact_tag":
            a["tags"] = list(TAGS)
        elif st["type"] == "create_opportunity":
            a["opportunity_source"] = SOURCE
        elif st["type"] == "internal_notification" and a.get("type") == "sms":
            a["sms"]["body"] = ("🚨 NEW LEAD FROM HOMEBUYER POSTCARD 🚨\n\nCampaign: Homebuyer Postcard (New Homeowner Welcome)"
                                "\n\nName: {{contact.name}}\n\nPhone: {{contact.phone}}\n\nEmail: {{contact.email}}"
                                "\n\nAddress: {{contact.address1}}, {{contact.city}}, {{contact.state}} {{contact.postal_code}}")
        elif st["type"] == "internal_notification" and a.get("type") == "email":
            e = a["email"]
            e["subject"] = "🚨 New Homebuyer Postcard lead: {{contact.name}}"
            e["html"] = (f"{P}<strong>🚨 NEW LEAD FROM HOMEBUYER POSTCARD 🚨</strong></p><br/>"
                         f"{P}Name: {{{{contact.name}}}}</p>{P}Phone: {{{{contact.phone}}}}</p>{P}Email: {{{{contact.email}}}}</p>"
                         f"{P}Address: {{{{contact.address1}}}}, {{{{contact.city}}}}, {{{{contact.state}}}} "
                         f"{{{{contact.postal_code}}}}</p>{P}Campaign: Homebuyer Postcard (QR code)</p>"
                         f"{P}Form: {FORM_NAME} ({LANDING.split('//')[1]})</p>")
    return tpl


def add_trigger(a: Agency, wid: str, tpl: list[dict], body: dict) -> dict:
    trig = {**body, "schedule_config": {}, "workflowId": wid, "workflow_id": wid, "location_id": LOC,
            "actions": [{"workflow_id": wid, "type": "add_to_workflow"}], "targetActionId": first_id(tpl)}
    t = a.call("POST", BACKEND, f"/workflow/{LOC}/trigger", body=trig)
    a.call("PUT", BACKEND, f"/workflow/{LOC}/trigger/{t['id']}", body={**trig, "id": t["id"]})
    return t


def form_trigger(form_ids: list[str]) -> dict:
    return {"type": "form_submission", "name": "Form Submitted", "masterType": "highlevel",
            "conditions": [{"operator": "is-any-of", "field": "form.id", "value": form_ids, "title": "Form is", "type": "string"}]}


def publish(a: Agency, wid: str, name: str, allow: bool) -> dict:
    live = a.workflow(LOC, wid)
    a.call("PUT", BACKEND, f"/workflow/{LOC}/{wid}", body={
        "name": name, "version": live.get("version", 1), "status": "published", "parentId": live.get("parentId"),
        "allowMultiple": allow, "workflowData": {"templates": live["workflowData"]["templates"]}})
    time.sleep(4)
    return a.workflow(LOC, wid)


def drop_flow(a: Agency, wid: str) -> None:
    live = a.workflow(LOC, wid)
    a.call("PUT", BACKEND, f"/workflow/{LOC}/{wid}", body={"name": live["name"], "version": live.get("version", 1),
           "status": "draft", "workflowData": {"templates": live["workflowData"]["templates"]}})
    a.call("DELETE", BACKEND, f"/workflow/{LOC}/{wid}")


def save_form(a: Agency, fid: str, fd: dict) -> None:
    """A form just created answers 404 to POST for a few minutes (GET works)."""
    for i in range(20):
        try:
            a.call("POST", BACKEND, f"/forms/{fid}", body={"name": FORM_NAME, "formData": keep_redirect(copy.deepcopy(fd))})
            return
        except Exception as e:  # noqa: BLE001
            if "404" not in str(e) or i == 19:
                raise
            time.sleep(20)


def form_ok(a: Agency, fid: str) -> list[str]:
    _, got = latest_form_data(a, fid)
    f = got["form"]
    act = f.get("formAction") or {}
    tags = [x["tag"] for x in f["fields"]]
    bad = []
    if act.get("redirect_url") != THANKS_URL or str(act.get("actionType")) != "1":
        bad.append(f"redirect {act}")
    if tags != ["first_name", "last_name", "group_address", "email", "phone", "terms_and_conditions", "button"]:
        bad.append(f"campos {tags}")
    if not (f.get("address") or {}).get("autoCompleteEnabled"):
        bad.append("sem autocomplete")
    if not next(x for x in f["fields"] if x["tag"] == "phone").get("enableCountryPicker"):
        bad.append("sem country picker")
    widget = requests.get(f"https://link.poolprofits.com/widget/form/{fid}", timeout=30).text
    if THANKS_URL not in widget.replace("\\u002F", "/"):
        bad.append("widget sem a URL de obrigado")
    return bad


def page_swap(data: dict, fid: str) -> list[str]:
    notes = []
    for nid, node in nodes(data):
        ex = node.get("extra") or {}
        if isinstance(ex.get("formId"), dict) and ex["formId"].get("value") != fid:
            notes.append(f"{nid}: {ex['formId'].get('text')!r} ({ex['formId'].get('value')}) → {FORM_NAME!r} ({fid})")
            ex["formId"] = {"value": fid, "text": FORM_NAME}
    return notes


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("mode", choices=["plan", "apply", "test"])
    parser.add_argument("--to", help="test: inbox that gets the lead e-mail")
    parser.add_argument("--no-page", action="store_true", help="apply: leave the landing page as it is")
    args = parser.parse_args()
    if args.mode == "test" and not args.to:
        parser.error("--to is required in test mode")
    load_dotenv()
    a = Agency()
    if a.location(LOC)["name"] != "BluVantage Pool Service":
        sys.exit("sub-conta errada")
    BDIR.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    forms = {f["name"]: f.get("_id") or f.get("id") for f in a.forms(LOC)}
    flows = {w["name"]: w["id"] for w in a.workflows(LOC)}
    src = a.workflow(LOC, flows[BASE_FLOW])
    _, atif = latest_form_data(a, ATIF_FORM)
    fd = build_form(atif)
    tpl = build_flow(src["workflowData"]["templates"])
    assert refs_ok(tpl)

    if args.mode == "plan":
        print(f"form {FORM_NAME}: {'existe ' + forms[FORM_NAME] if FORM_NAME in forms else 'cria'} (base: Atif {ATIF_FORM})")
        print("   campos:", " · ".join(f"{x['label']}{'*' if x.get('required') else ''}" for x in fd["form"]["fields"]))
        print("   depois do envio →", fd["form"]["formAction"]["redirect_url"])
        print(f"{FLOW_NAME}: {'existe' if FLOW_NAME in flows else 'cria'} · tags {TAGS} · origem {SOURCE!r}")
        print("   passos:", " → ".join(st["name"] for st in sorted(tpl, key=lambda x: (bool(x.get('parent')), x.get('order', 0)))
                                      if not str(st.get("nodeType", "")).startswith("branch")))
        page = a.get(BACKEND, f"/funnels/page/{PAGE}")
        data = requests.get(page["pageDataDownloadUrl"], timeout=60).json()
        print(f"página {page['name']}:", page_swap(data, forms.get(FORM_NAME, "<novo>")) or "já usa o form novo")
        return 0

    for t in {*TAGS, *GUARD}:
        try:
            a.call("POST", BACKEND, f"/workflow/{LOC}/tags/create", body={"tag": t})
        except Exception:  # noqa: BLE001 — already exists
            pass

    if args.mode == "test":
        stamp_i = int(time.time())
        ttpl = diverted(tpl, args.to)
        wid = put_flow(a, f"ZZ TEST {FLOW_NAME}", src.get("parentId"), True, ttpl, "draft")
        made, bad = [], 0
        try:
            add_trigger(a, wid, ttpl, {"type": "contact_tag", "name": "Contact Tag", "masterType": "highlevel",
                                       "conditions": [{"id": "tag-added", "title": "Tag Added", "operator": "index-of-true",
                                                       "field": "tagsAdded", "type": "select", "value": TEST_TAG}]})
            got = publish(a, wid, f"ZZ TEST {FLOW_NAME}", True)
            print(f"   ZZ TEST: {got['status']} · {len(got['workflowData']['templates'])} passos")
            cases = [("lead", []), ("spam", ["spam"]), ("customer", ["current customer"])]
            for case, pre in cases:
                c = a.call("POST", SERVICES, "/contacts/", body={
                    "locationId": LOC, "firstName": "ZZ Test", "lastName": f"Homebuyer {case}", "tags": pre,
                    "email": f"zz-e2e-bv-hb-{stamp_i}-{case}@example.com", "address1": "123 Test St",
                    "city": "Atlanta", "state": "GA", "postalCode": "30301"})["contact"]
                made.append(c["id"])
            time.sleep(4)
            for cid in made:
                a.call("POST", SERVICES, f"/contacts/{cid}/tags", body={"tags": [TEST_TAG]})
            time.sleep(30)
            for (case, pre), cid in zip(cases, made):
                for _ in range(9):
                    c = a.call("GET", SERVICES, f"/contacts/{cid}")["contact"]
                    opps = a.call("GET", SERVICES, "/opportunities/search",
                                  params={"location_id": LOC, "contact_id": cid}).get("opportunities", [])
                    if case != "lead" or (set(TAGS) <= set(c.get("tags", [])) and opps):
                        break
                    time.sleep(10)
                if case == "lead":
                    ok = set(TAGS) <= set(c.get("tags", [])) and any(
                        o.get("source") == SOURCE and o.get("pipelineStageId") == "8b339928-e2b2-4877-945c-e126cf38a620"
                        for o in opps)
                else:
                    ok = not (set(TAGS) & set(c.get("tags", []))) and not opps
                bad += not ok
                print(f"   {'✓' if ok else '✗'} {case}: tags {sorted(c.get('tags', []))} · "
                      f"cards {[(o.get('source'), o.get('pipelineStageId', '')[:8]) for o in opps]}")
                for o in opps:
                    a.call("DELETE", SERVICES, f"/opportunities/{o['id']}")
        finally:
            for cid in made:
                a.call("DELETE", SERVICES, f"/contacts/{cid}")
            drop_flow(a, wid)
            tags = a.call("GET", SERVICES, f"/locations/{LOC}/tags").get("tags", [])
            for t in tags:
                if t["name"] == TEST_TAG:
                    a.call("DELETE", SERVICES, f"/locations/{LOC}/tags/{t['id']}")
            print(f"   limpo (contatos, cards, workflow, tag de teste); e-mail de teste em {args.to}")
        return 1 if bad else 0

    # apply
    bad = 0
    if FORM_NAME in forms:
        fid = forms[FORM_NAME]
        cur, cur_fd = latest_form_data(a, fid)
        (BDIR / f"form-{fid}-{stamp}.json").write_text(json.dumps({"form": cur, "formData": cur_fd}))
        print(f"   form {FORM_NAME}: já existe ({fid}), regravado")
    else:
        res = a.call("POST", BACKEND, "/forms/", body={"name": FORM_NAME, "locationId": LOC, "formData": keep_redirect(copy.deepcopy(fd))})
        fid = (res.get("form") or res).get("_id") or (res.get("form") or res).get("id")
        print(f"   ✓ form {FORM_NAME}: {fid}")
    save_form(a, fid, fd)  # a created form loses redirect_url
    for _ in range(6):
        time.sleep(8)
        problems = form_ok(a, fid)
        if not problems:
            break
    bad += bool(problems)
    print(f"   {'✓' if not problems else '✗ VERIFICAR'} form {fid}: {problems or 'campos, autocomplete, country picker, redirect (widget)'}")

    if FLOW_NAME in flows:
        print(f"   {FLOW_NAME}: já existe ({flows[FLOW_NAME]})")
    else:
        wid = put_flow(a, FLOW_NAME, src.get("parentId"), src.get("allowMultiple", True), tpl, "draft")
        add_trigger(a, wid, tpl, form_trigger([fid, ATIF_FORM]))
        got = publish(a, wid, FLOW_NAME, src.get("allowMultiple", True))
        trs = [x for x in a.triggers(LOC, wid) if not x.get("deleted")]
        ok = got["status"] == "published" and len(got["workflowData"]["templates"]) == len(tpl) and \
            refs_ok(got["workflowData"]["templates"]) and len(trs) == 1 and trs[0].get("active") and \
            trs[0]["conditions"][0]["value"] == [fid, ATIF_FORM]
        bad += not ok
        print(f"   {'✓' if ok else '✗ VERIFICAR'} {FLOW_NAME} ({wid}): {got['status']} · {len(tpl)} passos · "
              f"forms {trs[0]['conditions'][0]['value'] if trs else None} · re-entry {got.get('allowMultiple')}")

    if not args.no_page:
        page = a.get(BACKEND, f"/funnels/page/{PAGE}")
        assert page["locationId"] == LOC
        data = requests.get(page["pageDataDownloadUrl"], timeout=60).json()
        new = json.loads(json.dumps(data))
        notes = page_swap(new, fid)
        if not notes:
            print("   página: já usa o form novo")
        else:
            (BDIR / f"page-{PAGE}-{stamp}.json").write_text(json.dumps({"page": page, "pageData": data}, ensure_ascii=False))
            for n in notes:
                print("   página", n)
            history = page.get("versionHistory") or [{}]
            a.call("POST", BACKEND, f"/funnels/builder/autosave/{PAGE}",
                   body={"funnelId": page["funnelId"], "pageData": new, "pageVersion": page.get("pageVersion") or 1,
                         "pageType": "live", "manualSave": True, "meta": page.get("meta") or {},
                         "integrations": history[0].get("integrations") or {}})
            for _ in range(8):
                time.sleep(5)
                after = a.get(BACKEND, f"/funnels/page/{PAGE}")
                saved = requests.get(after["pageDataDownloadUrl"], timeout=60).json()
                if not page_swap(json.loads(json.dumps(saved)), fid):
                    break
            left = page_swap(json.loads(json.dumps(saved)), fid)
            bad += bool(left)
            print(f"   {'✓' if not left else '✗ VERIFICAR'} página salva (live): {left or 'form ' + fid}")
        html = requests.get(LANDING, timeout=60)
        print(f"   {LANDING}: {html.status_code} · form novo no HTML: {fid in html.text} · do Atif: {ATIF_FORM in html.text}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
