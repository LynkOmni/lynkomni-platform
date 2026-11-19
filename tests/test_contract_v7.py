"""Contract version 7 (EMULATOR UPDATE, master blueprint section 70; build section 3A): version 6 plus the Emulator Panel and LynkSurvey's
"You said, we did". The device only asks (answers a connect request, asks to connect again, signs a user in or out, changes its own
tones, reports its health); the cloud alone offers, connects, disconnects, locks, swaps, asks for re-approval and records a screen
view. No event carries a PIN, a position or a name."""
import json, pathlib, subprocess, sys, unittest
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from contract.upcast import upcast, CURRENT
from core import emulators as E

def load(name): return json.loads((ROOT / "contract" / name).read_text())
V6, V7 = load("event-payloads.v6.json"), load("event-payloads.v7.json")
REG = load("command-policy-register.v7.json")
SECRETS = {"pin", "idcn", "id_number", "phone", "phone_number", "lat", "lng", "position", "location", "name", "code", "device_name", "email"}
CLOUD_ONLY = {"EmulatorOffered", "EmulatorConnected", "EmulatorDisconnected", "DeviceMarkedLost", "EmulatorSwapped", "EmulatorReapprovalNeeded",
              "EmulatorAssignedTo", "ScreenViewChanged", "SurveyYouSaidSent", "EmulatorSwapStarted", "DeviceApprovedAgain"}


class ContractV7(unittest.TestCase):
    def test_built_from_v6_and_current(self):
        r = subprocess.run([sys.executable, str(ROOT / "contract" / "tools" / "build_v7.py"), "--check"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(CURRENT, 7)

    def test_version_6_events_are_unchanged(self):
        for name, e in V6["events"].items():
            self.assertEqual((V7["events"][name]["payload"], V7["events"][name]["origins"]), (e["payload"], e["origins"]), name)
        for e in V7["events"].values(): self.assertEqual(e["schema_version"], 7)

    def test_the_device_only_asks_and_nothing_secret(self):
        new = set(V7["events"]) - set(V6["events"])
        self.assertEqual(len(new), 16)
        for name in CLOUD_ONLY: self.assertEqual(V7["events"][name]["origins"], ["server"], name)
        for name in new: self.assertEqual(set(V7["events"][name]["payload"]["properties"]) & SECRETS, set(), name)

    def test_emulator_names_come_from_the_register(self):
        self.assertEqual(V7["events"]["EmulatorConnected"]["payload"]["properties"]["emulator"]["enum"], list(E.EMULATORS))

    def test_answering_needs_the_cloud_and_the_rest_works_offline(self):
        new = {c["name"]: c for c in REG["commands"] if c.get("v7")}
        self.assertEqual(set(new), {"AnswerEmulatorRequest", "AskToConnect", "ChangeEmulatorUser", "ChangeEmulatorSettings", "ReportDeviceHealth"})
        self.assertEqual((new["AnswerEmulatorRequest"]["class"], new["AnswerEmulatorRequest"]["offline"]["allowed"]), ("C", False))
        for n, c in new.items():
            for et in c["emits"]: self.assertIn("device", V7["events"][et]["origins"], (n, et))
            if n != "AnswerEmulatorRequest": self.assertEqual((c["class"], c["offline"]["allowed"]), ("A", True), n)

    def test_upcaster_reads_version_6_unchanged(self):
        v6 = {"type": "TicketIssued", "schema_version": 6, "payload": {"ticket_id": "t1"}}
        self.assertEqual((upcast(v6)["schema_version"], upcast(v6)["payload"]), (7, v6["payload"]))

    def test_validator_passes(self):
        r = subprocess.run([sys.executable, str(ROOT / "contract" / "tools" / "validate_contract.py")], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout[-2000:])


if __name__ == "__main__": unittest.main()
