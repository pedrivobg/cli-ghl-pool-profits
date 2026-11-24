#!/usr/bin/env python3
"""Clear Pool Tucson: Thanksgiving voicemail 24-27/11 (Frank, 24/11). IVR SPAM Detection → "Record voicemail" step.

    python3 scripts/cp_holiday_vm.py on      # spoken holiday greeting (say), Derek's MP3 kept in the step
    python3 scripts/cp_holiday_vm.py off     # back to Derek's recording (play) — run 28/11
Rings Derek first exactly as before (only the voicemail greeting changes). GET + backup before the PUT.
"""
from __future__ import annotations

import json
import sys
import time

from _common import ROOT, load_dotenv

load_dotenv()
from cli_anything.gohighlevel.utils.agency import BACKEND, Agency  # noqa: E402

LOC, WID = "ghUi89uCpNyNunNpbtAt", "02f4e11a-6900-45f2-a91c-e9a3ded98fdc"
TEXT = ("Thank you for calling Clear Pool Solutions Tucson! In observance of the Thanksgiving holiday, our office will be "
        "closed this week to allow our team to enjoy some extra time with their families. We appreciate your "
        "understanding and wish you and your family a wonderful Thanksgiving! Please leave your name, number, and a "
        "brief message, and we'll get back to you when we return.")
BDIR = ROOT / "backup" / "clear-pool-solutions-tucson"


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    if mode not in ("on", "off"):
        print(__doc__)
        return 1
    a = Agency()
    live = a.workflow(LOC, WID)
    BDIR.mkdir(parents=True, exist_ok=True)
    (BDIR / f"workflow-{WID}-{time.strftime('%Y%m%d-%H%M%S')}.json").write_text(json.dumps(live))
    tpl = live["workflowData"]["templates"]
    vm = [t for t in tpl if t["type"] == "ivr_collect_voicemail"]
    assert len(vm) == 1, "expected one voicemail step"
    sp = vm[0]["attributes"]["sayPlayAttributes"]
    assert sp.get("audioUrl"), "Derek's recording missing — do not touch"
    if mode == "on":
        sp.update(widgetType="say", message=TEXT)
    else:
        sp.update(widgetType="play", message="Please record your message after the beep.")
    vm[0]["attributes"]["isSayPlayOn"] = True
    a.call("PUT", BACKEND, f"/workflow/{LOC}/{WID}", body={"name": live["name"], "version": live.get("version", 1),
                                                         "status": live["status"], "parentId": live.get("parentId"),
                                                         "workflowData": {"templates": tpl}})
    time.sleep(5)
    now = a.workflow(LOC, WID)
    v = [t for t in now["workflowData"]["templates"] if t["type"] == "ivr_collect_voicemail"][0]["attributes"]
    print(now["status"], "| widget:", v["sayPlayAttributes"]["widgetType"], "| msg:", v["sayPlayAttributes"]["message"][:60],
          "| mp3 kept:", bool(v["sayPlayAttributes"].get("audioUrl")))
    other = [(t["type"], t["attributes"].get("timeout")) for t in now["workflowData"]["templates"] if t["type"] == "ivr_connect_call"]
    print("connect call:", other, "| steps:", len(now["workflowData"]["templates"]), "(antes", len(tpl), ")")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
