#!/usr/bin/env python3
"""Builds contract version 18 from version 17 (TRACKING UPDATE, owner 2026-11-19, master blueprint section 72.3; built in section 4,
row 72.9: the tracking engine upgrade, catalog/tracking.v1.json engine).

Version 18 adds one event: TrackingStepMarked, a business's own extra step on a tracked item (a quality check, a second count) marked
on a device, offline too. An extra step is defined by the business (at most five per kind), never changes the five-state chip, never
decides an ending and is shown to customers only when the business says so. It carries the kind, the record, the extra step's id and
who saw it through (a staff member's internal id, never a name).

What is never in an event: a customer's name, contact or address, a position, the business's own wording of the step (that stays in
its settings; the event carries only the step's id).

Nothing older changes: version 17 events read as version 18 as they are (upcaster 17 to 18 only raises the version).

    python3 contract/tools/build_v18.py          writes contract/event-payloads.v18.json and contract/command-policy-register.v18.json
    python3 contract/tools/build_v18.py --check  fails when either file is out of date (tests/test_contract_v18.py runs it)
"""
import copy, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UU = {"$ref": "#/$defs/uuid"}


def _kinds():
    """The tracking kinds version 18 was published with (2026-11-24). Later kinds join a later version (build_v19.py and on)."""
    return ["delivery", "order", "payment", "agent_request", "group_order", "lease", "registration", "recovery", "data_request", "payout_change", "payout", "repair", "invoice", "quote", "standing_payment", "collection", "financing", "tax_return", "queue_ticket", "attendance_correction", "survey_reward", "emulator_request", "device_swap", "device_reapproval", "vote", "signature_request", "exchange_order", "bill_to_pay", "expense_claim", "message_delivery", "provider_payout", "bet_slip", "bet_referral"]


EVENTS = {
    "TrackingStepMarked": {"origins": ["device"], "since": "v18", "blueprint": "72 TRACKING UPDATE",
        "note": "A business's own extra step on a tracked item, marked on a device (offline too). Never changes the five-state chip or an ending; unknown steps are ignored by the engine.",
        "payload": {"type": "object", "additionalProperties": False, "required": ["kind", "record", "extra_step"],
                    "properties": {"kind": {"enum": _kinds()}, "record": {"type": "string", "minLength": 1, "maxLength": 64},
                                   "extra_step": {"type": "string", "pattern": "^[a-z][a-z0-9_]{1,30}$"}, "staff_id": UU}}}}
COMMANDS = [{"name": "MarkTrackingStep", "class": "A", "v18": True, "emits": ["TrackingStepMarked"], "permission": None,
             "channels": ["mobile", "web"], "local_only": True, "local_rejections": ["unknown_extra_step", "item_ended"],
             "offline": {"allowed": True}, "cloud_may_reject": False, "cloud_outcomes": ["accepted"],
             "ui_states": ["recorded", "pending_sync", "accepted"]}]


def load(name):
    with open(os.path.join(ROOT, name), encoding="utf-8") as f:
        return json.load(f)


def build():
    v18 = copy.deepcopy(load("event-payloads.v17.json"))
    v18["$id"] = "lynkomni/event-payloads.v18"
    v18["description"] = ("Contract version 18 (TRACKING UPDATE, master blueprint section 72, built in section 4): version 17 plus TrackingStepMarked, "
                          "a business's own extra step on a tracked item. Upcaster 17 to 18 in contract/upcasters.v1.json only raises the version.")
    for e in v18["events"].values():
        e["schema_version"] = 18
    for name, e in EVENTS.items():
        if name in v18["events"]:
            raise SystemExit(f"{name} already exists in version 17")
        e = copy.deepcopy(e)
        e["payload"]["properties"]["side"] = {"$ref": "#/$defs/side"}
        v18["events"][name] = {"schema_version": 18, **e}
    reg = copy.deepcopy(load("command-policy-register.v17.json"))
    reg["$id"] = "lynkomni/command-policy-register.v18"
    reg["description"] = ("Command register version 18 (TRACKING UPDATE, master blueprint section 72): version 17's commands plus marking a business's own "
                          "extra step on a tracked item (class A: recorded on the device, offline too).")
    names = {c["name"] for c in reg["commands"]}
    for c in COMMANDS:
        if c["name"] in names:
            raise SystemExit(f"command {c['name']} already exists")
        reg["commands"].append(copy.deepcopy(c))
    return {"event-payloads.v18.json": v18, "command-policy-register.v18.json": reg}


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
        print("out of date: " + ", ".join(stale) + " (run python3 contract/tools/build_v18.py)")
        return 1
    print("contract v18 is current" if check else "wrote contract v18")
    return 0


if __name__ == "__main__":
    sys.exit(main("--check" in sys.argv))
