#!/usr/bin/env python3
"""Builds contract version 4 from version 3 (NEW UPDATE 1, owner approved 2026-11-10, master blueprint section 49 M).

Version 4 adds the milestone events of LynkTrace, LynkGPS and LynkSentry (shipments, hand-overs, zones, assets, rentals,
protection alerts, LynkSentry incidents, location shares, trip plans and a device's last report) and the commands that issue
the device ones. Nothing in an older event changes: version 3 events read as version 4 as they are (upcaster 3 to 4 only raises
the version). A position (latitude, longitude, a map point) is never part of any event: zones, places and trips are referred
to by id, and positions live only in the encrypted, time-limited position store (section 49 H). Money stays integer minor units
with a currency; distances are whole metres and times whole seconds.

    python3 contract/tools/build_v4.py          writes contract/event-payloads.v4.json and contract/command-policy-register.v4.json
    python3 contract/tools/build_v4.py --check  fails when either file is out of date (tests/test_contract_v4.py runs it)
"""
import copy, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
U7, U, TS = {"$ref": "#/$defs/uuid7"}, {"$ref": "#/$defs/uuid"}, {"$ref": "#/$defs/timestamp_utc"}
SHA = {"$ref": "#/$defs/sha256"}
INT0 = {"type": "integer", "minimum": 0}
INT1 = {"type": "integer", "minimum": 1}


def enum(*v):
    return {"enum": list(v)}


def ev(origins, required, props, note):
    return {"origins": origins, "since": "v4", "blueprint": "49 M", "note": note,
            "payload": {"type": "object", "additionalProperties": False, "required": required, "properties": props}}


ROLES = ("sender", "rider", "agency", "carrier", "pickup_point", "receiver")
EVENTS = {
    "ShipmentCreated": ev(["device", "server"], ["shipment_id", "carrier", "pieces"],
                          {"shipment_id": U7, "order_id": U, "carrier": enum("own_rider", "partner_carrier", "agency"), "partner_id": U, "pieces": INT1},
                          "A shipment exists (LOSHP-): one or more pieces sent by the business's own rider, a partner carrier or an agency."),
    "ShipmentScanned": ev(["device"], ["shipment_id", "scan_id", "piece", "step"],
                          {"shipment_id": U, "scan_id": U7, "piece": INT1, "place_id": U,
                           "step": enum("picked_up", "at_hub", "on_the_way", "out_for_delivery", "at_pickup_point")},
                          "A piece was scanned at a step; the place is a registered hub or pickup point, never a position."),
    "ShipmentHandedOver": ev(["device"], ["shipment_id", "handover_id", "from_role", "to_role", "method", "seal"],
                             {"shipment_id": U, "handover_id": U7, "from_role": enum(*ROLES[:-1]), "to_role": enum(*ROLES[1:]),
                              "method": enum("code", "photo", "signature", "collect_pass", "pin"), "seal": SHA},
                             "Custody passed from one party to the next; seal is the hash of the sealed hand-over batch (services/sealing.py), so the Proof Chain can be checked by QR."),
    "ShipmentExceptionRaised": ev(["device", "server"], ["shipment_id", "exception", "next_step"],
                                  {"shipment_id": U, "exception": enum("address_problem", "nobody_home", "refused", "damaged", "customs_hold", "weather", "payment_not_confirmed"),
                                   "next_step": enum("new_address", "new_time", "pickup_point", "return_to_sender", "documents", "wait", "retry_payment")},
                                  "Something went wrong, always with the next step the receiver or sender is offered."),
    "DeliveryAttempted": ev(["device"], ["shipment_id", "attempt", "outcome"],
                            {"shipment_id": U, "attempt": INT1, "outcome": enum("missed", "refused", "address_problem")},
                            "A delivery attempt that did not end in a hand-over."),
    "DeliveryRescheduled": ev(["server"], ["shipment_id", "choice"],
                              {"shipment_id": U, "choice": enum("new_time", "pickup_point", "redirect"), "window_start": TS, "window_end": TS, "place_id": U},
                              "The receiver chose a new time, a pickup point or a new place (through the cloud, from the tracking page, USSD or text)."),
    "ZoneEntered": ev(["device", "server"], ["zone_id", "subject_kind", "subject_id"],
                      {"zone_id": U, "subject_kind": enum("asset", "trip", "rider"), "subject_id": U},
                      "A tracked subject entered a zone; worked out on the device or the cloud, never sent as a position."),
    "ZoneLeft": ev(["device", "server"], ["zone_id", "subject_kind", "subject_id"],
                   {"zone_id": U, "subject_kind": enum("asset", "trip", "rider"), "subject_id": U}, "A tracked subject left a zone."),
    "AssetRegistered": ev(["device", "server"], ["asset_id", "kind", "tracker"],
                          {"asset_id": U7, "kind": enum("car", "motorbike", "truck", "van", "bus", "container", "cargo", "equipment", "other"),
                           "tracker": enum("phone", "connected_car", "tracker", "tag", "seal")},
                          "A vehicle or asset is protected (LOAST-). Hardware is only on demand; the phone is the default tracker."),
    "AssetTripStarted": ev(["device", "server"], ["trip_id", "asset_id"], {"trip_id": U7, "asset_id": U}, "A trip of an asset began (LOTRP-)."),
    "AssetTripEnded": ev(["device", "server"], ["trip_id", "asset_id", "distance_m", "duration_s"],
                         {"trip_id": U, "asset_id": U, "distance_m": INT0, "duration_s": INT0}, "A trip of an asset ended: whole metres and seconds."),
    "RentalStarted": ev(["device"], ["rental_id", "asset_id", "renter_told", "photos", "odometer_m"],
                        {"rental_id": U7, "asset_id": U, "renter_told": {"const": True}, "photos": INT0, "odometer_m": INT0},
                        "A rental began after the renter was told the vehicle is tracked during the rental; hand-over photos are sealed."),
    "RentalEnded": ev(["device"], ["rental_id", "photos", "odometer_m"], {"rental_id": U, "photos": INT0, "odometer_m": INT0},
                      "A rental ended; tracking for the renter stops here."),
    "ProtectionAlertRaised": ev(["device", "server"], ["alert_id", "subject_id", "alert", "level"],
                                {"alert_id": U7, "subject_id": U,
                                 "alert": enum("moved_without_owner", "towed", "after_hours", "curfew", "zone_breach", "tamper", "jamming", "power_cut",
                                               "crash", "sos", "gone_silent", "seal_broken", "door_opened", "temperature", "shock", "unplanned_stop", "unknown_tracker"),
                                 "level": enum("notice", "warning", "urgent")},
                                "A LynkSentry alert (never the platform's AlertRaised). LynkSentry never contacts police by itself."),
    "ProtectionAlertCleared": ev(["device", "server"], ["alert_id", "by"], {"alert_id": U, "by": enum("owner", "trusted_contact", "system")},
                                 "An alert was cleared, for example \"Yes, it is me\"."),
    "SentryIncidentOpened": ev(["device", "server"], ["incident_id", "kind"],
                               {"incident_id": U7, "alert_id": U, "kind": enum("theft", "tamper", "crash", "sos", "custody")},
                               "An incident room opened (LOSNT-); it goes to the safety desk. Never the platform status incident (INC)."),
    "SentryIncidentClosed": ev(["device", "server"], ["incident_id", "outcome"],
                               {"incident_id": U, "outcome": enum("found", "resolved", "false_alarm", "handed_to_police")}, "An incident was closed by its owner."),
    "LocationShareStarted": ev(["device"], ["share_id", "consent_id", "scope", "ends_at"],
                               {"share_id": U7, "consent_id": U, "scope": enum("live", "trips", "zones"), "ends_at": TS},
                               "A person started sharing with people they chose, under a consent record with an end time."),
    "LocationShareEnded": ev(["device", "server"], ["share_id", "reason"], {"share_id": U, "reason": enum("stopped", "expired", "trip_ended")},
                             "A share ended; nothing more is shared from here."),
    "TripPlanSet": ev(["device"], ["plan_id", "due_at", "contacts"], {"plan_id": U7, "due_at": TS, "contacts": INT1},
                      "A trip plan with a check-in deadline; the cloud watches it, so it works even if the phone dies."),
    "TripPlanCheckedIn": ev(["device"], ["plan_id"], {"plan_id": U}, "The person checked in on time."),
    "TripPlanOverdue": ev(["server"], ["plan_id"], {"plan_id": U}, "The deadline passed with no check-in; trusted contacts are told (cloud only)."),
    "DeviceLastReport": ev(["device"], ["device_id", "reason", "battery_pct"],
                           {"device_id": U, "reason": enum("battery", "switched_off", "out_of_coverage", "suspected_jamming"),
                            "battery_pct": {"type": "integer", "minimum": 0, "maximum": 100}, "subject_id": U},
                           "A device's last sealed report before it went quiet, with the reason, so owners know why."),
}


def cmd(name, emits, permission=None, flags=None, rejections=("permission_denied", "session_expired", "device_locked")):
    c = {"name": name, "class": "A", "v1": False, "v4": True, "emits": emits, "permission": permission, "channels": ["mobile"],
         "offline": {"allowed": True}, "cloud_may_reject": False, "cloud_outcomes": ["accepted", "accepted_flagged", "quarantined_identity_or_integrity_only"],
         "local_rejections": list(rejections), "ui_states": ["recorded", "pending_sync", "accepted"]}
    c.update(flags or {})
    return c


AUTO = {"local_only": True}          # written by the device itself (zones, trips, alerts, last report); no person presses anything
PERSON = {"any_authenticated": True}  # a person's own action on their own account (sharing, trip plans, incidents)
COMMANDS = [
    cmd("CreateShipment", ["ShipmentCreated"], "sale.record"),
    cmd("RecordShipmentStep", ["ShipmentScanned", "ShipmentHandedOver", "DeliveryAttempted", "ShipmentExceptionRaised"], "sale.record",
        rejections=("code_mismatch", "shipment_not_found_local", "permission_denied", "session_expired", "device_locked")),
    cmd("RecordZoneEvent", ["ZoneEntered", "ZoneLeft"], None, AUTO, ("zone_not_found_local",)),
    cmd("RegisterAsset", ["AssetRegistered"], "settings.change"),
    cmd("RecordAssetTrip", ["AssetTripStarted", "AssetTripEnded"], None, AUTO, ("asset_not_found_local",)),
    cmd("RecordRental", ["RentalStarted", "RentalEnded"], "sale.record",
        rejections=("renter_not_told", "asset_not_found_local", "permission_denied", "session_expired", "device_locked")),
    cmd("RaiseProtectionAlert", ["ProtectionAlertRaised"], None, AUTO, ("subject_not_found_local",)),
    cmd("ClearProtectionAlert", ["ProtectionAlertCleared"], None, PERSON, ("alert_not_found_local", "session_expired")),
    cmd("RecordSentryIncident", ["SentryIncidentOpened", "SentryIncidentClosed"], None, PERSON, ("session_expired", "device_locked")),
    cmd("ShareLocation", ["LocationShareStarted", "LocationShareEnded"], None, PERSON, ("consent_missing", "session_expired")),
    cmd("SetTripPlan", ["TripPlanSet", "TripPlanCheckedIn"], None, PERSON, ("no_trusted_contact", "session_expired")),
    cmd("SendLastReport", ["DeviceLastReport"], None, AUTO, ("already_sent",)),
]


def load(name):
    with open(os.path.join(ROOT, name), encoding="utf-8") as f:
        return json.load(f)


def build():
    v3 = load("event-payloads.v3.json")
    v4 = copy.deepcopy(v3)
    v4["$id"] = "lynkomni/event-payloads.v4"
    v4["description"] = ("Contract version 4 (NEW UPDATE 1, 2026-11-10): version 3 plus the milestone events of LynkTrace, LynkGPS and LynkSentry. "
                         "No position is ever part of an event. Upcaster 3 to 4 in contract/upcasters.v1.json only raises the version.")
    for name, e in v4["events"].items():
        e["schema_version"] = 4
    for name, e in EVENTS.items():
        if name in v4["events"]:
            raise SystemExit(f"{name} already exists in version 3")
        e = copy.deepcopy(e)
        e["payload"]["properties"]["side"] = {"$ref": "#/$defs/side"}
        v4["events"][name] = {"schema_version": 4, **e}
    reg = copy.deepcopy(load("command-policy-register.v2.json"))
    reg["$id"] = "lynkomni/command-policy-register.v4"
    reg["description"] = ("Command register version 4 (NEW UPDATE 1, 2026-11-10): version 2's commands unchanged plus the commands that issue the "
                          "device events of LynkTrace, LynkGPS and LynkSentry (all class A: they work offline and the cloud never refuses them).")
    names = {c["name"] for c in reg["commands"]}
    for c in COMMANDS:
        if c["name"] in names:
            raise SystemExit(f"command {c['name']} already exists")
        reg["commands"].append(c)
    return {"event-payloads.v4.json": v4, "command-policy-register.v4.json": reg}


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
        print("out of date: " + ", ".join(stale) + " (run python3 contract/tools/build_v4.py)")
        return 1
    print("contract v4 is current" if check else "wrote contract v4")
    return 0


if __name__ == "__main__":
    sys.exit(main("--check" in sys.argv))
