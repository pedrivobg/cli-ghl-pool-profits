#!/usr/bin/env python3
"""Stay Fresh: "Service Needed" on the website form; weekly leads go to Kris, the rest to Mike (Frank, 06/11).

    ./.venv/bin/python scripts/sf_service_routing.py plan
    ./.venv/bin/python scripts/sf_service_routing.py test --to pedro@poolprofits.com
    ./.venv/bin/python scripts/sf_service_routing.py apply
    ./.venv/bin/python scripts/sf_service_routing.py style      # dropdown look = the site's gold-border inputs

- Custom field "Service Needed" (dropdown): Weekly Pool Service, Pool Repairs, Pool Remodeling, New Pool Build, Other.
- "Main Website Form" (the only form the site stayfreshpoolsaz.com uses; 7 of the 9 submissions of 2026, all from the
  site): required dropdown right before "Message". Newest version file read before the POST, keep_redirect, backup.
  The other 4 forms of the trigger (Google Ads LP, Landing Page optin, Service Page, Lead Gen) are not on the site.
- "Website Form Fill To Pipeline": if/else "Service Needed?" before the chain:
    Weekly Pool Service           → owner Kris → card (owner = Kris) → tags → SMS Kris → e-mail Kris → FYI e-mail to
                                    the office inbox (Mike) → task for Kris
    Repairs / Remodel / Build / Other → owner Mike → card (owner = Mike) → tags → SMS Mike → e-mail office inbox → FYI
                                    e-mail to Kris → task for Mike
    No service selected (other forms, tag trigger) → the old chain, same step ids, unchanged (SMS both, e-mail Kris).
  The card takes the contact's owner when it is created (cp_owner, 27/10), so the owner is set first. Re-entry and
  settings kept (Agency.call); triggers pointed at the if/else.
- "Contact Created -> add owner" (Mike for every new contact): only_unassigned_contact → true. A new website contact
  fires that flow and the form flow at the same time; without this, if it ran second it would put Mike back as owner
  of a weekly lead. Every contact that arrives without an owner still gets Mike.
test: ZZ TEST copy of the new flow (tag trigger; no SMS, no tasks, e-mails to --to, both routed branches assign Mike so
Kris gets nothing — a marker tag per branch proves the route), one contact per option + one blank; checks branch,
card in New Lead and card owner; everything deleted.
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
import time
import uuid

from _common import ROOT, keep_redirect, load_dotenv
from bv_service_forms import latest_form_data
from pp_lead_alerts import retarget
from pp_review_fix import read
from pp_source_tags import refs_ok
from pp_won_stage import IS_OPS, NEST

from cli_anything.gohighlevel.utils.agency import BACKEND, SERVICES, Agency, GHLError

LOC = "DdTE6mF11dqgoI5Cv7XN"
FLOW = "Website Form Fill To Pipeline"
OWNER_FLOW = "Contact Created -> add owner"
FORM = "kqNJs6ZFliL5IQQpUYp6"  # Main Website Form
FIELD = "Service Needed"
WEEKLY = "Weekly Pool Service"
OTHERS = ["Pool Repairs", "Pool Remodeling", "New Pool Build", "Other"]
MIKE, KRIS = "RBEED1mFWVMUqGkrZWyi", "0aJXUMBBZuJgPbEnkUWy"
MIKE_EMAIL, KRIS_EMAIL = "stayfreshpoolsoffice@gmail.com", "Kris@stayfreshpools.com"
COND_NAME = "Service Needed?"
BDIR = ROOT / "backup" / "stay-fresh-pools"
P = '<p style="margin:0 0 12px 0;font-family:Arial,Helvetica,sans-serif;font-size:15px;line-height:1.5;">{}</p>'


def nid() -> str:
    return str(uuid.uuid4())


def stamp() -> str:
    return time.strftime("%Y%m%d-%H%M%S")


# ── field + form ──────────────────────────────────────────────────────────

def ensure_field(a: Agency, do: bool) -> dict | None:
    cfs = {c["name"]: c for c in a.custom_fields(LOC)}
    if FIELD in cfs:
        return cfs[FIELD]
    if not do:
        return None
    res = a.call("POST", SERVICES, f"/locations/{LOC}/customFields",
                 body={"name": FIELD, "dataType": "SINGLE_OPTIONS", "options": [WEEKLY, *OTHERS], "placeholder": "",
                       "position": 0, "model": "contact"})
    cf = res.get("customField") or res
    print(f"   ✓ campo {FIELD} ({cf.get('fieldKey')}) {cf.get('picklistOptions')}")
    return cf


def dropdown(cf: dict) -> dict:
    return {"dataType": "SINGLE_OPTIONS", "fieldKey": cf["fieldKey"], "fieldName": FIELD,
            "hiddenFieldQueryKey": cf["fieldKey"].split(".")[-1], "id": cf["id"], "label": FIELD,
            "locationId": LOC, "model": "contact", "name": FIELD, "picklistOptions": [WEEKLY, *OTHERS],
            "placeholder": "Select a service", "position": 0, "required": True, "tag": cf["id"],
            "type": "single_options", "fieldWidthPercentage": 100}


def new_form(fd: dict, cf: dict) -> dict | None:
    fd = copy.deepcopy(fd)
    fields = fd["form"]["fields"]
    if any(x.get("tag") == cf["id"] for x in fields):
        return None
    at = next((i for i, x in enumerate(fields) if x.get("fieldKey") == "contact.message"), None)
    if at is None:
        at = next(i for i, x in enumerate(fields) if x.get("type") in ("terms_and_conditions", "submit"))
    fields.insert(at, dropdown(cf))
    return keep_redirect(fd)


CSS_MARK = "/* ---------- Service Needed dropdown (sf_service_routing.py) ---------- */"
DROPDOWN_CSS = CSS_MARK + """
#_builder-form#_builder-form .multiselect,
#_builder-form#_builder-form .multiselect__tags {
  background-color: transparent !important;
  min-height: 47px !important;
}
#_builder-form#_builder-form .multiselect__tags {
  border: 2px solid #a8771a !important;
  border-radius: 15px !important;
  padding: 12px 40px 0 16px !important;
}
#_builder-form#_builder-form .multiselect input.multiselect__input[type="text"] {
  border: 0 !important;
  border-radius: 0 !important;
  height: 20px !important;
  background: transparent !important;
  box-shadow: none !important;
}
#_builder-form#_builder-form .multiselect__placeholder,
#_builder-form#_builder-form .multiselect__single,
#_builder-form#_builder-form .multiselect__input {
  background: transparent !important;
  color: #ffffff !important;
  font-family: "Poppins", sans-serif !important;
  font-size: 13px !important;
  font-weight: 600 !important;
  margin: 0 !important;
  padding: 0 !important;
}
#_builder-form#_builder-form .multiselect__placeholder {
  opacity: 0.6 !important;
  font-family: "Inter", sans-serif !important;
  font-size: 16px !important;
  font-weight: 400 !important;
}
#_builder-form#_builder-form .multiselect__select {
  height: 47px !important;
}
#_builder-form#_builder-form .multiselect__select::before {
  border-color: #ffffff transparent transparent !important;
}
#_builder-form#_builder-form .multiselect__content-wrapper {
  border: 2px solid #a8771a !important;
  border-radius: 15px !important;
  background: #ffffff !important;
}
#_builder-form#_builder-form .multiselect__option {
  color: #101828 !important;
  font-family: "Poppins", sans-serif !important;
  font-size: 13px !important;
}
#_builder-form#_builder-form .multiselect__option--highlight {
  background: #005f59 !important;
  color: #ffffff !important;
}
"""


def styled(fd: dict) -> dict | None:
    fd = copy.deepcopy(fd)
    css = fd["form"].get("customStyle") or ""
    if DROPDOWN_CSS in css:
        return None
    fd["form"]["customStyle"] = css.split(CSS_MARK)[0].rstrip() + "\n\n" + DROPDOWN_CSS  # replaces an older block
    return keep_redirect(fd)


# ── workflow ──────────────────────────────────────────────────────────────

def cond(cf_id: str, value: str) -> dict:
    return {"conditionType": "contact_detail", "conditionSubType": cf_id, "conditionOperator": "==",
            "conditionValue": value, "__conditionId": nid(), "ifElseNodeId": "", "__customFieldType__": "standard",
            "isWait": False, "nestedDropdownTypes": NEST, "allowIsOperatorTypes": IS_OPS}


def assign(user: str, name: str) -> dict:
    return {"id": nid(), "name": f"Assign to {name}", "type": "assign_user",
            "attributes": {"type": "assign_user", "only_unassigned_contact": False, "total_index": 1,
                           "traffic_split": "equally", "traffic_weightage": {user: 1},
                           "traffic_index": [{"id": user, "indexes": [1]}], "user_list": [user]}}


def routed(old: list[dict], cf: dict, user: str, who: str, to: str, fyi_to: str, fyi_who: str) -> list[dict]:
    """Copies of the old steps (new ids) for one person, plus owner first and an FYI e-mail for the other."""
    by = {s["type"] if s["type"] != "internal_notification" else s["attributes"]["type"]: s for s in old}
    key = "{{" + cf["fieldKey"] + "}}"
    card, tag, sms, mail, task = (copy.deepcopy(by[k]) for k in ("create_opportunity", "add_contact_tag", "sms",
                                                                 "email", "task-notification"))
    sms["name"] = f"New Lead SMS - {who}"
    sms["attributes"]["sms"].update(selectedUser=[user], body=sms["attributes"]["sms"]["body"].replace(
        "\n\nSource: Website Form", f"\nService: {key}\n\nSource: Website Form"))
    service_row = P.format(f"<b>Service:</b> {key}")
    em = mail["attributes"]["email"]
    em.update(to=to, subject=f"🚨 New website lead ({key}): {{{{contact.name}}}} {{{{contact.phone}}}}",
              html=em["html"].replace(P.format("<b>Source:</b> Website Form"),
                                      service_row + P.format("<b>Source:</b> Website Form") +
                                      P.format(f"<b>Assigned to:</b> {who}")))
    mail["name"] = f"New Lead Email - {who}"
    fyi = copy.deepcopy(mail)
    fyi["name"] = f"FYI Email - {fyi_who}"
    fyi["attributes"]["email"].update(
        to=fyi_to, subject=f"FYI: new website lead for {who} ({key}): {{{{contact.name}}}}",
        html=P.format(f"FYI: this website lead was assigned to <b>{who}</b> (no action needed from you).") +
        em["html"])
    task["attributes"]["assignedTo"] = user
    task.pop("incompleteData", None)
    task["name"] = f"Add Task - {who}"
    steps = [assign(user, who), card, tag, sms, mail, fyi, task]
    for s in steps:
        s["id"] = nid()
    return steps


def link(steps: list[dict], parent: str) -> list[dict]:
    for i, s in enumerate(steps):
        s.update(order=i, parent=parent, parentKey=steps[i - 1]["id"] if i else parent)
        s.pop("next", None)
        if i + 1 < len(steps):
            s["next"] = steps[i + 1]["id"]
    return steps


def linear(tpl: list[dict]) -> list[dict]:
    by = {s["id"]: s for s in tpl}
    first = next(s for s in tpl if not s.get("parentKey"))
    out = [first]
    while isinstance(out[-1].get("next"), str):
        out.append(by[out[-1]["next"]])
    if len(out) != len(tpl):
        raise SystemExit("not a linear chain — not rebuilding blindly")
    return json.loads(json.dumps(out))


def build(tpl: list[dict], cf: dict) -> list[dict] | None:
    if any(s.get("name") == COND_NAME for s in tpl):
        return None
    old = linear(tpl)
    head, b_k, b_m, b_n = nid(), nid(), nid(), nid()
    kris = link(routed(old, cf, KRIS, "Kris", KRIS_EMAIL, MIKE_EMAIL, "Mike"), b_k)
    mike = link(routed(old, cf, MIKE, "Mike", MIKE_EMAIL, KRIS_EMAIL, "Kris"), b_m)
    keep = link(old, b_n)  # same ids, same attributes
    names = {b_k: "Weekly Pool Service → Kris", b_m: "Repairs / Remodel / Build / Other → Mike"}
    node = {"id": head, "order": 0, "name": COND_NAME, "type": "if_else", "cat": "conditions",
            "nodeType": "condition-node", "comments": [], "next": [b_k, b_m, b_n],
            "attributes": {"currentRecipeType": "CUSTOM", "operator": "and", "if": True, "conditionName": COND_NAME,
                           "version": 2, "noneBranchName": "No service selected",
                           "branches": [{"id": bid, "name": names[bid], "operator": "and", "showErrors": False,
                                         "branchNameError": "Branch name cannot be empty!",
                                         "segments": [{"__segmentId": nid(), "operator": "or", "conditions": cs}]}
                                        for bid, cs in ((b_k, [cond(cf["id"], WEEKLY)]),
                                                        (b_m, [cond(cf["id"], v) for v in OTHERS]))]}}
    out = [node]
    for bid, name, body in ((b_k, names[b_k], kris), (b_m, names[b_m], mike), (b_n, "No service selected", keep)):
        last = bid == b_n
        out.append({"id": bid, "parent": head, "parentKey": head, "order": 1, "name": name, "type": "if_else",
                    "cat": "conditions", "sibling": [x for x in (b_k, b_m, b_n) if x != bid], "comments": [],
                    "nodeType": "branch-no" if last else "branch-yes", "next": body[0]["id"],
                    "attributes": {"else": True} if last else
                    {"if": False, "conditionName": "Condition", "operator": "and", "branches": []}})
        out += body
    return out


def for_test(tpl: list[dict], to: str, stamp_: int) -> list[dict]:
    """No SMS, no tasks, e-mails to the tester, both routed branches assign Mike, a marker tag per branch."""
    tpl = json.loads(json.dumps(tpl))
    by = {s["id"]: s for s in tpl}
    drop = {s["id"] for s in tpl if s["type"] == "task-notification" or
            (s["type"] == "internal_notification" and s["attributes"].get("type") == "sms")}
    out = []
    for s in tpl:
        if s["id"] in drop:
            continue
        at = s["attributes"]
        if s["type"] == "assign_user":
            at.update(traffic_weightage={MIKE: 1}, traffic_index=[{"id": MIKE, "indexes": [1]}], user_list=[MIKE])
        if at.get("type") == "email":
            at["email"]["to"] = to
            at["email"]["subject"] = f"[TEST {s['name']}] " + at["email"]["subject"]
        if s["type"] == "add_contact_tag":
            branch = by[s["parent"]]["name"] if s.get("parent") in by else "?"
            at["tags"] = at["tags"] + [f"zz route {branch.split(' ')[0].lower()} {stamp_}"]
        out.append(s)
    for s in out:  # re-link each branch without the dropped steps
        for k in ("next", "parentKey"):
            v = s.get(k)
            while isinstance(v, str) and v in drop:
                v = by[v].get(k) if k == "parentKey" else by[v].get("next")
            if v is None:
                s.pop(k, None)
            else:
                s[k] = v
    return out


def create_copy(a: Agency, tpl: list[dict], tag: str, parent: str | None) -> str:
    wid = (lambda r: r.get("id") or r.get("_id"))(a.call("POST", BACKEND, f"/workflow/{LOC}",
                                                          body={"name": "ZZ TEST service routing", "parentId": parent,
                                                                "status": "draft"}))
    body = {"name": "ZZ TEST service routing", "version": 1, "status": "draft", "parentId": parent,
            "allowMultiple": True, "workflowData": {"templates": tpl}}
    a.call("PUT", BACKEND, f"/workflow/{LOC}/{wid}", body=body)
    trig = {"type": "contact_tag", "name": "Contact Tag", "masterType": "highlevel", "schedule_config": {},
            "workflowId": wid, "workflow_id": wid, "location_id": LOC, "targetActionId": tpl[0]["id"],
            "actions": [{"workflow_id": wid, "type": "add_to_workflow"}],
            "conditions": [{"operator": "index-of-true", "type": "select", "value": tag, "field": "tagsAdded",
                            "title": "Tag Added", "id": "tag-added"}]}
    t = a.call("POST", BACKEND, f"/workflow/{LOC}/trigger", body=trig)
    a.call("PUT", BACKEND, f"/workflow/{LOC}/trigger/{t['id']}", body={**trig, "id": t["id"]})
    a.call("PUT", BACKEND, f"/workflow/{LOC}/{wid}", body={**body, "status": "published",
                                                         "version": a.workflow(LOC, wid).get("version", 1)})
    return wid


def drop_flow(a: Agency, wid: str) -> None:
    live = a.workflow(LOC, wid)
    a.call("PUT", BACKEND, f"/workflow/{LOC}/{wid}", body={"name": live["name"], "version": live.get("version", 1),
                                                         "status": "draft", "workflowData": live["workflowData"]})
    a.call("DELETE", BACKEND, f"/workflow/{LOC}/{wid}")


def outline(tpl: list[dict]) -> None:
    by = {s["id"]: s for s in tpl}

    def walk(sid, depth):
        while sid and sid in by:
            s = by[sid]
            if isinstance(s.get("next"), list):
                print("  " * depth + f"◆ {s['name']}")
                for b in s["next"]:
                    print("  " * (depth + 1) + f"▸ {by[b]['name']}")
                    walk(by[b].get("next"), depth + 2)
                return
            at = s["attributes"]
            extra = (at.get("sms") or {}).get("selectedUser") or (at.get("email") or {}).get("to") or \
                at.get("user_list") or at.get("assignedTo") or at.get("tags") or ""
            print("  " * depth + f"- {s['name']} [{s['id'][:8]}] {extra}")
            sid = s.get("next") if isinstance(s.get("next"), str) else None
    walk(tpl[0]["id"], 2)


def test(a: Agency, to: str, cf: dict, live: dict) -> int:
    st = int(time.time())
    tpl = build(live["workflowData"]["templates"], cf)
    if tpl is None:
        sys.exit("já aplicado")
    tpl = for_test(tpl, to, st)
    assert refs_ok(tpl), "ids quebrados na cópia"
    tag = f"zz sf route {st}"
    cases = {"weekly": WEEKLY, "repairs": "Pool Repairs", "remodel": "Pool Remodeling", "build": "New Pool Build",
             "other": "Other", "blank": None}
    want = {"weekly": "weekly", "blank": "no"}
    wid, made = None, {}
    try:
        wid = create_copy(a, tpl, tag, live.get("parentId"))
        time.sleep(8)
        for case, val in cases.items():
            body = {"locationId": LOC, "firstName": "ZZ Test", "lastName": f"route {case}",
                    "email": to.replace("@", f"+sf-route-{case}-{st}@"), "city": "Queen Creek"}
            if val:
                body["customFields"] = [{"id": cf["id"], "field_value": val}]
            made[case] = a.call("POST", SERVICES, "/contacts/", body=body)["contact"]["id"]
        time.sleep(15)  # Contact Created -> add owner runs first (Mike); the copy then routes
        for cid in made.values():
            a.call("POST", SERVICES, f"/contacts/{cid}/tags", body={"tags": [tag]})
        time.sleep(75)
        bad = 0
        for case, cid in made.items():
            c = a.call("GET", SERVICES, f"/contacts/{cid}")["contact"]
            tags = c.get("tags") or []
            route = [t.split(" ")[2] for t in tags if t.startswith("zz route ")]
            opps = a.call("GET", SERVICES, "/opportunities/search",
                          params={"location_id": LOC, "contact_id": cid}).get("opportunities", [])
            exp = want.get(case, "repairs")
            owner_ok = all(o.get("assignedTo") == MIKE for o in opps) if exp != "no" else True
            ok = route == [exp] and len(opps) == 1 and opps[0]["pipelineStageId"].startswith("00add63d") and owner_ok
            bad += not ok
            print(f"   {'✓' if ok else '✗'} {case} ({cases[case]}): ramo {route} · cards {len(opps)} · "
                  f"dono do card {[o.get('assignedTo') == MIKE and 'Mike' or o.get('assignedTo') for o in opps]} · "
                  f"tags {sorted(t for t in tags if not t.startswith('zz'))}")
        print(f"   e-mails esperados em {to}: 5 ramos roteados × (aviso + FYI) = 10, + 1 do blank (Email - Kris do fluxo antigo)")
        return 1 if bad else 0
    finally:
        for cid in made.values():
            for o in a.call("GET", SERVICES, "/opportunities/search",
                            params={"location_id": LOC, "contact_id": cid}).get("opportunities", []):
                a.call("DELETE", SERVICES, f"/opportunities/{o['id']}")
            a.call("DELETE", SERVICES, f"/contacts/{cid}")
        if wid:
            drop_flow(a, wid)
        print("   limpo (cópia, contatos, cards).")


def apply_owner_flow(a: Agency, flows: dict, do: bool) -> bool:
    live = read(a, LOC, flows[OWNER_FLOW])
    tpl = json.loads(json.dumps(live["workflowData"]["templates"]))
    steps = [s for s in tpl if s["type"] == "assign_user"]
    if len(steps) != 1 or len(tpl) != 1:
        print(f"   ✗ {OWNER_FLOW}: esperado 1 passo assign_user — não mexo")
        return False
    if steps[0]["attributes"].get("only_unassigned_contact"):
        print(f"   = {OWNER_FLOW}: já só atribui contato sem dono")
        return True
    print(f"   + {OWNER_FLOW}: only_unassigned_contact false → true")
    if not do:
        return True
    steps[0]["attributes"]["only_unassigned_contact"] = True
    (BDIR / f"workflow-{flows[OWNER_FLOW]}-{stamp()}.json").write_text(json.dumps(live))
    a.call("PUT", BACKEND, f"/workflow/{LOC}/{flows[OWNER_FLOW]}", body={
        "name": live["name"], "version": live.get("version", 1), "status": live["status"],
        "parentId": live.get("parentId"), "workflowData": {"templates": tpl}})
    time.sleep(3)
    got = read(a, LOC, flows[OWNER_FLOW])
    ok = got["status"] == live["status"] and got.get("allowMultiple") == live.get("allowMultiple") and \
        got["workflowData"]["templates"][0]["attributes"].get("only_unassigned_contact") is True and \
        got["workflowData"]["templates"][0]["attributes"].get("user_list") == [MIKE]
    print(f"     {'✓' if ok else '✗ VERIFICAR'} {got['status']} · re-entry {got.get('allowMultiple')}")
    return ok


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("mode", choices=["plan", "test", "apply", "style"])
    parser.add_argument("--to")
    args = parser.parse_args()
    if args.mode == "test" and not args.to:
        parser.error("--to is required in test mode")
    load_dotenv()
    a = Agency()
    if not a.location(LOC)["name"].startswith("Stay Fresh"):
        sys.exit("sub-conta errada")
    BDIR.mkdir(parents=True, exist_ok=True)
    flows = {w["name"]: w["id"] for w in a.workflows(LOC)}
    live = read(a, LOC, flows[FLOW])
    cf = ensure_field(a, args.mode != "plan")
    if args.mode == "plan":
        cf = cf or {"id": "<novo>", "fieldKey": "contact.service_needed", "name": FIELD}
        print(f"== campo {FIELD}: {'existe' if cf['id'] != '<novo>' else 'cria'} · {[WEEKLY, *OTHERS]}")
        form, fd = latest_form_data(a, FORM)
        nf = new_form(fd, cf)
        print(f"== form {form.get('name')}: " + ("já tem o campo" if nf is None else
              " · ".join(x.get("label") or x.get("tag") for x in nf["form"]["fields"])))
        apply_owner_flow(a, flows, False)
        tpl = build(live["workflowData"]["templates"], cf)
        print(f"== {FLOW}: " + ("já feito" if tpl is None else f"{len(tpl)} nós"))
        if tpl:
            outline(tpl)
        return 0
    if args.mode == "test":
        return test(a, args.to, cf, live)
    if args.mode == "style":  # the site's custom CSS styles inputs, not the dropdown component
        form, fd = latest_form_data(a, FORM)
        nf = styled(fd)
        if nf is None:
            print("   = CSS do dropdown já está no form")
            return 0
        (BDIR / f"form-{FORM}-{stamp()}.json").write_text(json.dumps({"form": form, "formData": fd}))
        a.call("POST", BACKEND, f"/forms/{FORM}", body={"name": form["name"], "formData": nf})
        time.sleep(5)
        _, got = latest_form_data(a, FORM)
        ok = DROPDOWN_CSS in (got["form"].get("customStyle") or "") and len(got["form"]["fields"]) == len(fd["form"]["fields"])
        print(f"   {'✓' if ok else '✗ VERIFICAR'} CSS do dropdown gravado")
        return 0 if ok else 1

    bad = 0
    form, fd = latest_form_data(a, FORM)
    nf = new_form(fd, cf)
    if nf is None:
        print(f"   = form {form.get('name')}: já tem {FIELD}")
    else:
        (BDIR / f"form-{FORM}-{stamp()}.json").write_text(json.dumps({"form": form, "formData": fd}))
        a.call("POST", BACKEND, f"/forms/{FORM}", body={"name": form["name"], "formData": nf})
        time.sleep(5)
        _, got = latest_form_data(a, FORM)
        fa = got["form"].get("formAction") or {}
        ok = any(x.get("tag") == cf["id"] and x.get("required") for x in got["form"]["fields"]) and \
            len(got["form"]["fields"]) == len(fd["form"]["fields"]) + 1 and \
            fa.get("actionType") == (fd["form"].get("formAction") or {}).get("actionType")
        bad += not ok
        print(f"   {'✓' if ok else '✗ VERIFICAR'} form {form.get('name')}: + {FIELD} (obrigatório) · ação {fa.get('actionType')}")
    bad += not apply_owner_flow(a, flows, True)
    tpl = build(live["workflowData"]["templates"], cf)
    if tpl is None:
        print(f"   = {FLOW}: já feito")
        return 1 if bad else 0
    (BDIR / f"workflow-{flows[FLOW]}-{stamp()}.json").write_text(json.dumps(live))
    a.call("PUT", BACKEND, f"/workflow/{LOC}/{flows[FLOW]}", body={
        "name": live["name"], "version": live.get("version", 1), "status": live["status"],
        "parentId": live.get("parentId"), "workflowData": {"templates": tpl}})
    time.sleep(3)
    retarget(a, LOC, flows[FLOW], tpl[0]["id"])
    got = read(a, LOC, flows[FLOW])
    t2 = got["workflowData"]["templates"]
    trs = [t for t in a.triggers(LOC, flows[FLOW]) if not t.get("deleted")]
    old_ids = {s["id"] for s in live["workflowData"]["templates"]}
    ok = refs_ok(t2) and len(t2) == len(tpl) and got["status"] == live["status"] and \
        got.get("allowMultiple") == live.get("allowMultiple") and old_ids <= {s["id"] for s in t2} and \
        all(t.get("targetActionId") == tpl[0]["id"] and t.get("active") for t in trs)
    bad += not ok
    print(f"   {'✓' if ok else '✗ VERIFICAR'} {FLOW}: {got['status']} · re-entry {got.get('allowMultiple')} · "
          f"{len(t2)} nós · ids antigos mantidos {old_ids <= {s['id'] for s in t2}} · {len(trs)} gatilhos no if/else")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
