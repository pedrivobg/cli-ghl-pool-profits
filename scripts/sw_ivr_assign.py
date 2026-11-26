#!/usr/bin/env python3
"""Sunwave (weekly audit 19/11 #2, fixed 26/11): "Marketing - IVR" → "Assign to user" had an empty user list, so call
leads got no owner and their tasks (assigned to contact.assigned_user) had nobody. → David Connolly (he gets every
new-lead alert in the other lead flows). Only that step changes; IVR steps untouched. Backup in backup/sunwave-pool-pros/.

    python3 scripts/sw_ivr_assign.py [--apply]
"""
import argparse
import json
import os
import time

from _common import ROOT, Agency, load_dotenv
from pp_lead_alerts import put_workflow

LOC, WID, DAVID = "GeeXTPcJXAoVUAmzLxfT", "e66c40c0-63bb-4568-913e-db7610edaf38", "aBXyonAu6hC7r04MyJ1p"

ap = argparse.ArgumentParser()
ap.add_argument("--apply", action="store_true")
args = ap.parse_args()
load_dotenv()
a = Agency()
live = a.workflow(LOC, WID)
t = json.loads(json.dumps(live["workflowData"]["templates"]))
s = next(x for x in t if x["type"] == "assign_user")
print("before:", s["attributes"].get("user_list"))
s["attributes"].update(user_list=[DAVID], total_index=1, traffic_split="equally", traffic_weightage={DAVID: 1},
                       traffic_index=[{"id": DAVID, "indexes": [1]}], only_unassigned_contact=False)
s["attributes"].pop("customUserList", None)
if args.apply:
    d = os.path.join(ROOT, "backup", "sunwave-pool-pros")
    os.makedirs(d, exist_ok=True)
    json.dump(live, open(os.path.join(d, f"{WID}-{time.strftime('%Y%m%d-%H%M%S')}.json"), "w"))
    put_workflow(a, LOC, WID, live, t)
    time.sleep(4)
    now = a.workflow(LOC, WID)
    s2 = next(x for x in now["workflowData"]["templates"] if x["type"] == "assign_user")
    same_ivr = [x for x in now["workflowData"]["templates"] if x["type"].startswith("ivr")] == \
               [x for x in live["workflowData"]["templates"] if x["type"].startswith("ivr")]
    print("after:", now["status"], s2["attributes"].get("user_list"), "| ivr steps unchanged:", same_ivr)
