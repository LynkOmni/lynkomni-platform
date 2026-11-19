#!/usr/bin/env python3
"""Builds contract version 8 from version 7 (owner decision 2026-11-19: WhatsApp is removed from the whole LynkOmni ecosystem).

Version 8 drops "whatsapp" as a way to receive the LynkAttend PIN, as a way to agree to face or finger ("code_whatsapp"), as a way to
join a LynkQueue queue and as a way to answer a LynkSurvey survey. LynkChat, text messages, email, the link or QR code, the basic phone
and the voice call stay. Nothing else changes: no event is added or removed, and every other field is as in version 7.

Upcaster 7 to 8 (contract/upcasters.v1.json) reads an older event that still names WhatsApp as LynkChat ("code_whatsapp" as
"code_lynkchat"). Only sandbox and test events can hold it: LynkOmni had no live users when WhatsApp was removed. The stored event is
never rewritten.

    python3 contract/tools/build_v8.py          writes contract/event-payloads.v8.json and contract/command-policy-register.v8.json
    python3 contract/tools/build_v8.py --check  fails when either file is out of date (tests/test_contract_v8.py runs it)
"""
import copy, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# (event, field) -> the values version 8 removes
REMOVED = {
    ("AttendanceConsentRecorded", "method"): ("code_whatsapp",),
    ("AttendancePinSent", "channel"): ("whatsapp",),
    ("TicketIssued", "via"): ("whatsapp",),
    ("SurveyAnswered", "way"): ("whatsapp",),
    ("SurveyAnswerReceived", "way"): ("whatsapp",),
}


def load(name):
    with open(os.path.join(ROOT, name), encoding="utf-8") as f:
        return json.load(f)


def build():
    v7 = load("event-payloads.v7.json")
    v8 = copy.deepcopy(v7)
    v8["$id"] = "lynkomni/event-payloads.v8"
    v8["description"] = ("Contract version 8 (owner decision 2026-11-19): version 7 without WhatsApp. LynkAttend PINs and agreement codes, "
                         "joining a LynkQueue queue and answering a LynkSurvey survey no longer name WhatsApp; LynkChat, text, email, the link "
                         "or QR code, the basic phone and the voice call stay. Upcaster 7 to 8 in contract/upcasters.v1.json reads an older "
                         "WhatsApp value as LynkChat.")
    for e in v8["events"].values():
        e["schema_version"] = 8
    for (name, field), gone in REMOVED.items():
        prop = v8["events"][name]["payload"]["properties"][field]
        missing = [g for g in gone if g not in prop["enum"]]
        if missing:
            raise SystemExit(f"{name}.{field} has no {missing} in version 7")
        prop["enum"] = [x for x in prop["enum"] if x not in gone]
    reg = copy.deepcopy(load("command-policy-register.v7.json"))
    reg["$id"] = "lynkomni/command-policy-register.v8"
    reg["description"] = "Command register version 8 (2026-11-19): version 7's commands unchanged; only the event values naming WhatsApp were removed."
    return {"event-payloads.v8.json": v8, "command-policy-register.v8.json": reg}


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
        print("out of date: " + ", ".join(stale) + " (run python3 contract/tools/build_v8.py)")
        return 1
    print("contract v8 is current" if check else "wrote contract v8")
    return 0


if __name__ == "__main__":
    sys.exit(main("--check" in sys.argv))
