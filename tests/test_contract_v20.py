"""Contract version 20 (build section 4B step 4): version 19 with the Emulator Panel's events naming the LynkHR, LynkProject and LynkFiles
emulators. No event and no command is added; nothing older changes; a later emulator joins a later version."""
import json, pathlib, subprocess, sys, unittest
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from contract.upcast import CURRENT, upcast
from core import emulators as E


def load(name): return json.loads((ROOT / "contract" / name).read_text())
V19, V20 = load("event-payloads.v19.json"), load("event-payloads.v20.json")
REG19, REG20 = load("command-policy-register.v19.json"), load("command-policy-register.v20.json")
NEW = {"hr.people", "project.site_phone", "files.documents", "files.signing_tablet"}


class ContractV20(unittest.TestCase):
    def test_built_from_v19_and_current(self):
        r = subprocess.run([sys.executable, str(ROOT / "contract" / "tools" / "build_v20.py"), "--check"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertGreaterEqual(CURRENT, 20)

    def test_only_the_emulator_ids_widen(self):
        self.assertEqual(set(V20["events"]), set(V19["events"]))
        self.assertEqual(REG20["commands"], REG19["commands"])
        widened = []
        for name, e in V19["events"].items():
            a, b = e["payload"], V20["events"][name]["payload"]
            self.assertEqual(V20["events"][name]["origins"], e["origins"], name)
            if name in ("ReviewCycleOpened", "ReviewAnswered"):
                self.assertIn("lesson_observation", json.dumps(b), name); continue
            if a != b:
                old, new = a["properties"]["emulator"]["enum"], b["properties"]["emulator"]["enum"]
                self.assertEqual(new[: len(old)], old, name)                 # the old ids stay, in order
                self.assertEqual(set(new) - set(old), NEW, name)
                widened.append(name)
        self.assertIn("EmulatorConnected", widened)
        self.assertEqual(set(V20["events"]["EmulatorConnected"]["payload"]["properties"]["emulator"]["enum"]), set(E.EMULATORS))

    def test_a_version_19_event_reads_as_version_20_unchanged(self):
        ev = {"schema_version": 19, "type": "LeaveRequested", "payload": {"leave_id": "x"}}
        up = upcast(dict(ev))
        self.assertEqual((up["schema_version"], up["payload"]), (CURRENT, ev["payload"]))


if __name__ == "__main__":
    unittest.main()
