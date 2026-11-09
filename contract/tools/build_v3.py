#!/usr/bin/env python3
"""Builds contract version 3 from version 2 (BIZZ & DEVICE, owner approved 2026-11-09).

Version 3 adds one optional payload field to every event: `side`, either "internal" (the workspace: a person, company or
organisation using a service for its own affairs) or "external" (the Storefront: offering to others and earning). A missing
side means "internal", so every event written before version 3 keeps its meaning. Nothing else changes: no field is removed or
renamed, money stays integer minor units with a currency, and version 2 stays published as it was.

    python3 contract/tools/build_v3.py          writes contract/event-payloads.v3.json (commands are unchanged: the v2 register stays current)
    python3 contract/tools/build_v3.py --check  fails when either file is out of date (tests/test_contract_v3.py runs it)
"""
import copy, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SIDES = ["internal", "external"]
SIDE = {"type": "string", "enum": SIDES,
        "description": "Which side of the service the event belongs to: internal (the workspace) or external (the Storefront). Missing means internal."}


def load(name):
    with open(os.path.join(ROOT, name), encoding="utf-8") as f:
        return json.load(f)


def build():
    v2 = load("event-payloads.v2.json")
    v3 = copy.deepcopy(v2)
    v3["$id"] = "lynkomni/event-payloads.v3"
    v3["description"] = ("Contract version 3 (BIZZ & DEVICE, 2026-11-09): version 2 plus an optional `side` on every payload "
                         "(internal or external; missing means internal). Upcaster 2 to 3 in contract/upcasters.v1.json.")
    v3["$defs"]["side"] = SIDE
    for name, ev in v3["events"].items():
        ev["schema_version"] = 3
        props = ev["payload"].setdefault("properties", {})
        if "side" in props:
            raise SystemExit(f"{name} already has a side field")
        props["side"] = {"$ref": "#/$defs/side"}
    return {"event-payloads.v3.json": v3}


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
        print("out of date: " + ", ".join(stale) + " (run python3 contract/tools/build_v3.py)")
        return 1
    print("contract v3 is current" if check else "wrote contract v3")
    return 0


if __name__ == "__main__":
    sys.exit(main("--check" in sys.argv))
