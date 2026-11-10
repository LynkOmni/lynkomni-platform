"""Contract version 4 (NEW UPDATE 1, owner approved 2026-11-10): version 3 plus the milestone events of LynkTrace, LynkGPS and
LynkSentry and the class A commands that issue the device ones. No event ever carries a position; version 3 reads unchanged."""
import json, pathlib, subprocess, sys, unittest
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from contract.upcast import upcast, CURRENT

def load(name): return json.loads((ROOT / "contract" / name).read_text())
V3, V4 = load("event-payloads.v3.json"), load("event-payloads.v4.json")
REG = load("command-policy-register.v4.json")
NEW = {"ShipmentCreated", "ShipmentScanned", "ShipmentHandedOver", "ShipmentExceptionRaised", "DeliveryAttempted", "DeliveryRescheduled",
       "ZoneEntered", "ZoneLeft", "AssetRegistered", "AssetTripStarted", "AssetTripEnded", "RentalStarted", "RentalEnded",
       "ProtectionAlertRaised", "ProtectionAlertCleared", "SentryIncidentOpened", "SentryIncidentClosed", "LocationShareStarted",
       "LocationShareEnded", "TripPlanSet", "TripPlanCheckedIn", "TripPlanOverdue", "DeviceLastReport"}
POSITION = {"lat", "lng", "lon", "latitude", "longitude", "position", "location", "coordinates", "point", "geo"}


class ContractV4(unittest.TestCase):
    def test_built_from_v3_and_current(self):
        r = subprocess.run([sys.executable, str(ROOT / "contract" / "tools" / "build_v4.py"), "--check"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_version_3_events_are_unchanged_and_the_new_ones_added(self):
        self.assertEqual(set(V4["events"]) - set(V3["events"]), NEW)
        for name, e in V3["events"].items():
            self.assertEqual(V4["events"][name]["payload"], e["payload"], name)
            self.assertEqual(V4["events"][name]["origins"], e["origins"], name)
        for e in V4["events"].values(): self.assertEqual(e["schema_version"], 4)

    def test_no_event_carries_a_position(self):
        for name, e in V4["events"].items():
            self.assertEqual(set(e["payload"]["properties"]) & POSITION, set(), name)

    def test_cloud_only_and_device_facts(self):
        for name in ("DeliveryRescheduled", "TripPlanOverdue"): self.assertEqual(V4["events"][name]["origins"], ["server"], name)
        self.assertNotIn("AlertRaised", NEW)                         # the platform's alert stays its own; LynkSentry has ProtectionAlertRaised
        emitted = {et for c in REG["commands"] for et in c["emits"]}
        for name in NEW:
            if "device" in V4["events"][name]["origins"]: self.assertIn(name, emitted, name)
        for c in REG["commands"]:
            if c.get("v4"):
                self.assertEqual((c["class"], c["offline"]["allowed"], c["cloud_may_reject"]), ("A", True, False), c["name"])

    def test_upcaster_reads_version_3_unchanged(self):
        self.assertGreaterEqual(CURRENT, 4)                          # version 5 (MASTER UPDATE) reads version 4 unchanged too
        v3 = {"type": "SaleRecorded", "schema_version": 3, "payload": {"currency": "XXX", "total": 5, "side": "external"}}
        up = upcast(v3)
        self.assertEqual((up["schema_version"], up["payload"]), (CURRENT, v3["payload"]))
        self.assertEqual(v3["schema_version"], 3)                    # the stored event is never rewritten

    def test_validator_passes(self):
        r = subprocess.run([sys.executable, str(ROOT / "contract" / "tools" / "validate_contract.py")], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout[-2000:])


if __name__ == "__main__": unittest.main()
