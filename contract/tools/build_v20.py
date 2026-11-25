#!/usr/bin/env python3
"""Builds contract version 20 from version 19 (build section 4B step 4, 2026-11-25): the Emulator Panel learns the emulators of LynkHR,
LynkProject and LynkFiles (catalog/emulators.v1.json entries with contract_since 20: hr.people, project.site_phone, files.documents and
the LynkFiles signing tablet files.signing_tablet).

Version 20 adds no event and no command. It widens the review kinds of ReviewCycleOpened and ReviewAnswered with a school's
lesson_observation (SCHOOL UPDATE 80.15), and the list of emulator ids that the Emulator Panel's events may name
(EmulatorOffered, EmulatorConnected, EmulatorDisconnected, EmulatorConnectAsked, EmulatorSwapStarted, EmulatorSwapped,
EmulatorUserChanged, EmulatorAssignedTo). Nothing older changes: a version 19 event reads as version 20 as it is (upcaster 19 to 20
only raises the version). A later emulator joins a later version, never a published one.

    python3 contract/tools/build_v20.py          writes contract/event-payloads.v20.json and contract/command-policy-register.v20.json
    python3 contract/tools/build_v20.py --check  fails when either file is out of date (tests/test_contract_v20.py runs it)
"""
import copy, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VERSION = 20


def load(name):
    with open(os.path.join(ROOT, name), encoding="utf-8") as f:
        return json.load(f)


def emulators():
    """The emulator ids of version 20: every emulator of the register published by version 20 (a later one joins a later version)."""
    with open(os.path.join(os.path.dirname(ROOT), "catalog", "emulators.v1.json"), encoding="utf-8") as f:
        return [e["id"] for e in json.load(f)["emulators"] if e.get("contract_since", 7) <= VERSION]


def build():
    v20 = copy.deepcopy(load("event-payloads.v19.json"))
    v20["$id"] = "lynkomni/event-payloads.v20"
    v20["description"] = ("Contract version 20 (build section 4B): version 19 with the Emulator Panel's events naming the LynkHR, LynkProject and "
                          "LynkFiles emulators too (the LynkFiles signing tablet among them) and a school's lesson observation as a review kind. Upcaster 19 to 20 in contract/upcasters.v1.json only raises the version.")
    ids = emulators()
    with open(os.path.join(os.path.dirname(ROOT), "catalog", "hr.v1.json"), encoding="utf-8") as f:
        review_kinds = json.load(f)["reviews"]["kinds"]          # a school's lesson observation (SCHOOL UPDATE 80.15) joins version 20
    for e in v20["events"].values():
        e["schema_version"] = VERSION
        prop = e["payload"].get("properties", {}).get("emulator")
        if isinstance(prop, dict) and "enum" in prop:
            old = prop["enum"]
            prop["enum"] = old + [i for i in ids if i not in old]
    for name in ("ReviewCycleOpened", "ReviewAnswered"):
        props = v20["events"][name]["payload"]["properties"]
        target = props["kinds"]["items"] if "kinds" in props else props["kind"]
        target["enum"] = target["enum"] + [k for k in review_kinds if k not in target["enum"]]
    reg = copy.deepcopy(load("command-policy-register.v19.json"))
    reg["$id"] = "lynkomni/command-policy-register.v20"
    reg["description"] = "Command register version 20 (build section 4B): version 19's commands, unchanged; version 20 only widens the emulator ids."
    return {"event-payloads.v20.json": v20, "command-policy-register.v20.json": reg}


def main(check=False):
    stale = []
    for name, data in build().items():
        text = json.dumps(data, indent=1, ensure_ascii=False) + "\n"
        path = os.path.join(ROOT, name)
        if check:
            if not os.path.isfile(path) or open(path, encoding="utf-8").read() != text:
                stale.append(name)
        else:
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)
    if stale:
        print("out of date: " + ", ".join(stale) + " (run python3 contract/tools/build_v20.py)")
        return 1
    print("contract v20 is current" if check else "wrote contract v20")
    return 0


if __name__ == "__main__":
    sys.exit(main("--check" in sys.argv))
