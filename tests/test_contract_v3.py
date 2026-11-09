"""Contract version 3 (BIZZ & DEVICE, 2026-11-09): version 2 plus an optional side on every payload, internal (the
workspace) or external (the Storefront). A missing side means internal; version 2 stays published and readable."""
import json, pathlib, subprocess, sys, unittest
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from contract.upcast import upcast, CURRENT

def load(name): return json.loads((ROOT / "contract" / name).read_text())
V2, V3 = load("event-payloads.v2.json"), load("event-payloads.v3.json")


class ContractV3(unittest.TestCase):
    def test_built_from_v2_and_current(self):
        r = subprocess.run([sys.executable, str(ROOT / "contract" / "tools" / "build_v3.py"), "--check"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_same_events_each_with_an_optional_side(self):
        self.assertEqual(set(V3["events"]), set(V2["events"]))
        self.assertEqual(V3["$defs"]["side"]["enum"], ["internal", "external"])
        for name, ev in V3["events"].items():
            self.assertEqual(ev["schema_version"], 3, name)
            self.assertEqual(ev["payload"]["properties"]["side"], {"$ref": "#/$defs/side"}, name)
            self.assertNotIn("side", ev["payload"].get("required", []), name)        # missing means internal
            v2 = dict(V2["events"][name]["payload"]); v3 = dict(ev["payload"])
            p2, p3 = dict(v2.get("properties", {})), dict(v3.get("properties", {})); p3.pop("side")
            self.assertEqual(p2, p3, f"{name}: version 3 may only add the side")
            self.assertEqual(v2.get("required"), v3.get("required"), name)

    def test_upcaster_reads_version_2_as_the_workspace_side(self):
        self.assertEqual(CURRENT, 3)
        v2 = {"type": "SaleRecorded", "schema_version": 2, "payload": {"currency": "XXX", "total": 5}}
        up = upcast(v2)
        self.assertEqual((up["schema_version"], up["payload"]["side"], up["payload"]["total"]), (3, "internal", 5))
        self.assertNotIn("side", v2["payload"])                                      # the stored event is never rewritten
        ext = {"type": "SaleRecorded", "schema_version": 3, "payload": {"side": "external"}}
        self.assertIs(upcast(ext), ext)

    def test_validator_passes(self):
        r = subprocess.run([sys.executable, str(ROOT / "contract" / "tools" / "validate_contract.py")], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout[-2000:])


if __name__ == "__main__": unittest.main()
