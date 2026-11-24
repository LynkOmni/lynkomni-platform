#!/usr/bin/env python3
"""Builds contract version 7 from version 6 (EMULATOR UPDATE, owner accepted 2026-11-18, master blueprint section 70; build section 3A).

Version 7 adds the Emulator Panel. The device may only ask: it answers a connect request (Accept or Deny), asks its manager to
connect it again, signs a user in or out with the staff PIN (checked on the device; the PIN is never in an event), changes its own
tone and vibration settings where allowed, and reports its health. The cloud alone writes that an emulator is offered, connected,
disconnected, locked, swapped or due for re-approval, and that a screen view started or ended. A position, a PIN or a person's name
is never in an event; the place shown is the branch.

It also adds SurveyYouSaidSent (LynkSurvey's "You said, we did", carried over from section 3B): the cloud alone writes that the
organisation's message went to the people who answered, or was shown on the public page for an anonymous survey.

Nothing in an older event changes: version 6 events read as version 7 as they are (upcaster 6 to 7 only raises the version).

    python3 contract/tools/build_v7.py          writes contract/event-payloads.v7.json and contract/command-policy-register.v7.json
    python3 contract/tools/build_v7.py --check  fails when either file is out of date (tests/test_contract_v7.py runs it)
"""
import copy, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(ROOT))
U7, U = {"$ref": "#/$defs/uuid7"}, {"$ref": "#/$defs/uuid"}
INT0 = {"type": "integer", "minimum": 0}
INT1 = {"type": "integer", "minimum": 1}
BOOL = {"type": "boolean"}


def _emulator_ids():
    with open(os.path.join(os.path.dirname(ROOT), "catalog", "emulators.v1.json"), encoding="utf-8") as f:
        return [e["id"] for e in json.load(f)["emulators"] if e.get("contract_since", 7) <= 7]   # a later emulator joins a later version (bet.counter: v17)


EMU = {"enum": _emulator_ids()}


def enum(*v):
    return {"enum": list(v)}


def ev(origins, required, props, note, part="70"):
    return {"origins": origins, "since": "v7", "blueprint": part, "note": note,
            "payload": {"type": "object", "additionalProperties": False, "required": required, "properties": props}}


D, S, DS = ["device"], ["server"], ["device", "server"]
WAYS = ("code", "device_asked", "known_device", "batch", "template", "managed", "face_to_face", "guided_setup")
EVENTS = {
    "EmulatorOffered": ev(S, ["assignment_id", "emulator", "way", "expires_in_minutes"],
        {"assignment_id": U, "emulator": EMU, "way": enum(*WAYS), "expires_in_minutes": INT1, "temporary_until_day": INT0, "device_id": U},
        "Cloud only: a manager offered an emulator to a device (QR code, Lynk Code or link; or one of the other ways). The code itself is never in an event."),
    "EmulatorRequestAnswered": ev(D, ["assignment_id", "device_id", "answer"],
        {"assignment_id": U, "device_id": U, "answer": enum("accept", "deny")},
        "The person at the device tapped Accept or Deny on the connect request."),
    "EmulatorConnected": ev(S, ["assignment_id", "device_id", "emulator"],
        {"assignment_id": U, "device_id": U, "emulator": EMU, "practice": BOOL, "extra_slot": BOOL},
        "Cloud only: the emulator is connected on the device; a staff emulator now counts against the plan unless it is in practice mode."),
    "EmulatorDisconnected": ev(S, ["device_id", "emulator", "reason"],
        {"device_id": U, "emulator": EMU, "reason": enum("manager", "temporary_ended", "lost", "plan", "removed", "swapped", "opening_hours"),
         "unsent": INT0},
        "Cloud only: the emulator is switched off on the device. A safe disconnect first takes the device's unsent records; unsent says how many were still to come."),
    "EmulatorConnectAsked": ev(D, ["device_id", "emulator"], {"device_id": U, "emulator": EMU},
        "A disconnected emulator asked the manager to connect it again (the Connect request button)."),
    "DeviceMarkedLost": ev(S, ["device_id"], {"device_id": U, "found": BOOL},
        "Cloud only: Mark as lost locks every emulator on the device (a wipe stays with the owner alone, identity/device_access.py); found reverses it."),
    "EmulatorSwapStarted": ev(S, ["from_device_id", "to_device_id", "emulator"], {"from_device_id": U, "to_device_id": U, "emulator": EMU},
        "Cloud only: a swap began; the old device finishes its work and sends its unsent records first."),
    "EmulatorSwapped": ev(S, ["from_device_id", "to_device_id", "emulator"], {"from_device_id": U, "to_device_id": U, "emulator": EMU},
        "Cloud only: the emulator moved to another device with its name, settings and printers."),
    "EmulatorReapprovalNeeded": ev(S, ["device_id", "days"], {"device_id": U, "days": INT1},
        "Cloud only: the device was not seen for this many days and must be approved again before it works."),
    "DeviceApprovedAgain": ev(S, ["device_id"], {"device_id": U}, "Cloud only: a manager approved the device again after it was not seen for a while; it works again."),
    "EmulatorUserChanged": ev(D, ["device_id", "emulator", "change"],
        {"device_id": U, "emulator": EMU, "change": enum("signed_in", "signed_out", "switched", "idle_signed_out"), "user_id": U},
        "A staff member signed in or out of an emulator with their staff PIN (checked on the device; the PIN is never in an event)."),
    "EmulatorAssignedTo": ev(S, ["device_id", "emulator", "to"], {"device_id": U, "emulator": EMU, "to": enum("person", "people", "role", "nobody"), "user_id": U},
        "Cloud only: the manager gave the emulator on this device to a person, several people or a role (customer-facing screens: nobody)."),
    "EmulatorSettingsChanged": ev(DS, ["device_id", "tones", "vibration", "volume"],
        {"device_id": U, "tones": BOOL, "vibration": BOOL, "volume": enum("low", "medium", "high"), "pin_same_tone": BOOL, "by": enum("device", "manager")},
        "Key tones, press vibration and volume on a device (the manager's default or the user's own choice where allowed)."),
    "DeviceHealthReported": ev(D, ["device_id", "online", "unsent"],
        {"device_id": U, "online": BOOL, "unsent": INT0, "battery_pct": {"type": "integer", "minimum": 0, "maximum": 100},
         "printer": enum("ready", "paper_low", "out_of_paper", "not_connected"), "morning_check": enum("passed", "failed")},
        "The device's own health for the live view: online, unsent records, battery and printer, and the morning check at opening."),
    "ScreenViewChanged": ev(S, ["device_id", "change", "viewer"],
        {"device_id": U, "change": enum("started", "ended", "refused"), "viewer": enum("manager", "support"), "consent_id": U},
        "Cloud only: someone viewed a device's emulator screen to help, only with the user's consent (support through its time-limited consent record); never during a payment, cash count, signature or PIN."),
    "SurveyYouSaidSent": ev(S, ["survey_id", "told", "public_page"], {"survey_id": U, "told": INT0, "public_page": BOOL},
        "Cloud only: the organisation's \"You said, we did\" message went to the people who answered (told), or was shown on the survey's public page for an anonymous survey.", "63 LynkS"),
}


def cmd(name, emits, rejections, permission=None, how=None, offline=True, channels=("mobile",)):
    c = {"name": name, "class": "A" if offline else "C", "v7": True, "emits": emits, "permission": permission, "channels": list(channels),
         "offline": {"allowed": True} if offline else {"allowed": False, "behavior": "refuse_with_reason",
                                                         "note": "Assigning needs the cloud once (or the face-to-face offline permission)."},
         "cloud_may_reject": not offline, "cloud_outcomes": ["accepted", "accepted_flagged"] if offline else ["accepted", "rejected_expired", "rejected_plan_limit"],
         "local_rejections": rejections, "ui_states": ["recorded", "pending_sync", "accepted"] if offline else ["sent", "confirmed", "failed"]}
    if how:
        c[how] = True
    return c


COMMANDS = [
    cmd("AnswerEmulatorRequest", ["EmulatorRequestAnswered"], ["code_expired", "code_used", "device_cannot_run"], how="local_only", offline=False),
    cmd("AskToConnect", ["EmulatorConnectAsked"], ["already_connected"], how="local_only"),
    cmd("ChangeEmulatorUser", ["EmulatorUserChanged"], ["pin_not_recognised", "not_assigned_to_this_person"], how="local_only"),
    cmd("ChangeEmulatorSettings", ["EmulatorSettingsChanged"], ["manager_does_not_allow"], how="local_only"),
    cmd("ReportDeviceHealth", ["DeviceHealthReported"], ["device_not_added"], how="local_only"),
]


def load(name):
    with open(os.path.join(ROOT, name), encoding="utf-8") as f:
        return json.load(f)


def build():
    v6 = load("event-payloads.v6.json")
    v7 = copy.deepcopy(v6)
    v7["$id"] = "lynkomni/event-payloads.v7"
    v7["description"] = ("Contract version 7 (EMULATOR UPDATE, build section 3A): version 6 plus the Emulator Panel, where the device only asks and "
                         "the cloud alone connects, disconnects, locks and swaps, and LynkSurvey's \"You said, we did\" message. No PIN, position "
                         "or name is ever part of an event. Upcaster 6 to 7 in contract/upcasters.v1.json only raises the version.")
    for e in v7["events"].values():
        e["schema_version"] = 7
    for name, e in EVENTS.items():
        if name in v7["events"]:
            raise SystemExit(f"{name} already exists in version 6")
        e = copy.deepcopy(e)
        e["payload"]["properties"]["side"] = {"$ref": "#/$defs/side"}
        v7["events"][name] = {"schema_version": 7, **e}
    reg = copy.deepcopy(load("command-policy-register.v6.json"))
    reg["$id"] = "lynkomni/command-policy-register.v7"
    reg["description"] = ("Command register version 7 (EMULATOR UPDATE, build section 3A): version 6's commands unchanged plus the device's own "
                          "Emulator Panel commands. Answering a connect request needs the cloud; asking to connect, changing the user, the tone "
                          "settings and the health report work offline. Connecting, disconnecting, locking and swapping are written by the cloud alone.")
    names = {c["name"] for c in reg["commands"]}
    for c in COMMANDS:
        if c["name"] in names:
            raise SystemExit(f"command {c['name']} already exists")
        reg["commands"].append(copy.deepcopy(c))
    return {"event-payloads.v7.json": v7, "command-policy-register.v7.json": reg}


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
        print("out of date: " + ", ".join(stale) + " (run python3 contract/tools/build_v7.py)")
        return 1
    print("contract v7 is current" if check else "wrote contract v7")
    return 0


if __name__ == "__main__":
    sys.exit(main("--check" in sys.argv))
