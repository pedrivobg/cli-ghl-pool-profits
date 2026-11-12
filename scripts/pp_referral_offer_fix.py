#!/usr/bin/env python3
"""Remove the free-month-per-referral offer from the old-snapshot "In Communications" → Nurture Email Day 3 (Ed 11/11).

    python3 scripts/pp_referral_offer_fix.py <rows.json> x [<account name>] [--apply]
rows.json (the 3 still live: config/referral_offer_live.json) = [[type, account, loc, wfId, wfName, status], …] from a scan for "free month" (scratchpad freemonth.py).
Keeps status/version/parent; backup in backup/<slug>/<wfId>-<stamp>.json. Only the text and subject change."""
import sys, json, os, re, time; sys.path.insert(0,'scripts')
from _common import load_dotenv
load_dotenv()
from cli_anything.gohighlevel.utils.agency import Agency, BACKEND, slugify
a=Agency()
OLD1="It's not everyday you here from your pool guy on how he can PAY YOU!"
NEW1="Quick favor to ask!"
OLD2="At {{location.name}} we have one of the most aggressive referral programs in the industry. Every time you refer us a new customer, you get a free month of service. You heard that right... FREE MONTH OF SERVICE."
NEW2="If you have a friend, family member or neighbor who could use help with their pool, we'd love an introduction. Just reply to this email or pass along our number."
SUBJ="Know Someone Who Needs a Pool Pro?"
rows=[r for r in json.load(open(sys.argv[1])) if r[4]=='In Communications']
only=sys.argv[3] if len(sys.argv)>3 else None
apply='--apply' in sys.argv
stamp=time.strftime("%Y%m%d-%H%M%S")
for typ,ln,loc,wid,name,st in rows:
    if only and ln!=only: continue
    wf=a.workflow(loc,wid)
    tpl=wf['workflowData']['templates']
    t=[t for t in tpl if t['name']=='Nurture Email Day 3'][0]; at=t['attributes']
    if OLD2 not in at['html']: print(ln,'já sem'); continue
    at['html']=at['html'].replace(OLD1,NEW1).replace(OLD2,NEW2)
    if at.get('subject')=='How Can You Earn Money With Us?': at['subject']=SUBJ
    if not apply: print('plan',ln,wf['status']); continue
    d=f'backup/{slugify(ln)}'; os.makedirs(d,exist_ok=True)
    json.dump(a.workflow(loc,wid),open(f'{d}/{wid}-{stamp}.json','w'))
    a.call("PUT",BACKEND,f"/workflow/{loc}/{wid}",body={"name":wf['name'],"version":wf.get('version',1),"status":wf['status'],
        "parentId":wf.get('parentId'),"workflowData":{"templates":tpl}})
    time.sleep(2)
    after=a.workflow(loc,wid); h=json.dumps(after)
    ok = 'free month' not in h.lower() and after['status']==wf['status'] and len(after['workflowData']['templates'])==len(tpl)
    print('✓' if ok else '✗ VERIFICAR', ln, after['status'], after.get('version'), flush=True)
