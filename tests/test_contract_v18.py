"""Contract version 18 (TRACKING UPDATE, master blueprint section 72, built in section 4 row 72.9): version 17 plus TrackingStepMarked, a
business's own extra step on a tracked item. Nothing older changes; the event may come from a device, offline too; it carries ids only."""
import json, pathlib, subprocess, sys, unittest
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from contract.upcast import CURRENT, upcast


def load(name): return json.loads((ROOT / "contract" / name).read_text())
V17, V18 = load("event-payloads.v17.json"), load("event-payloads.v18.json")
REG17, REG18 = load("command-policy-register.v17.json"), load("command-policy-register.v18.json")


class ContractV18(unittest.TestCase):
    def test_built_from_v17_and_current(self):
        r = subprocess.run([sys.executable, str(ROOT / "contract" / "tools" / "build_v18.py"), "--check"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertGreaterEqual(CURRENT, 18)

    def test_only_the_extra_step_event_is_new_and_nothing_older_changes(self):
        self.assertEqual(set(V18["events"]) - set(V17["events"]), {"TrackingStepMarked"})
        for name, e in V17["events"].items():
            self.assertEqual((V18["events"][name]["payload"], V18["events"][name]["origins"]), (e["payload"], e["origins"]), name)
        e = V18["events"]["TrackingStepMarked"]
        self.assertEqual(e["origins"], ["device"])
        self.assertEqual(set(e["payload"]["properties"]), {"kind", "record", "extra_step", "staff_id", "side"})   # ids only: no words, no person
        kinds = {k["id"] for k in json.loads((ROOT / "catalog" / "tracking.v1.json").read_text())["kinds"]}
        self.assertEqual(set(e["payload"]["properties"]["kind"]["enum"]), kinds)

    def test_marking_an_extra_step_works_offline(self):
        added = [c for c in REG18["commands"] if c not in REG17["commands"]]
        self.assertEqual([(c["name"], c["class"], c["offline"]["allowed"], c["emits"]) for c in added], [("MarkTrackingStep", "A", True, ["TrackingStepMarked"])])

    def test_a_version_17_event_reads_as_version_18_unchanged(self):
        ev = {"schema_version": 17, "type": "DeliveryPickedUp", "payload": {"delivery_id": "x"}}
        up = upcast(dict(ev))
        self.assertEqual((up["schema_version"], up["payload"]), (18, ev["payload"]))


if __name__ == "__main__":
    unittest.main()
