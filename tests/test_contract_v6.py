"""Contract version 6 (NEW UPDATE 4, owner locked 2026-11-11, master blueprint section 63): version 5 plus the events of LynkAttend,
LynkQueue and LynkSurvey. Check-ins, tickets and device answers are device facts; PINs, the partner's answers and the check of an
answer are cloud only; no event carries a PIN, IDCN, ID number, face or finger pattern, phone number, position or anonymous identity."""
import json, pathlib, subprocess, sys, unittest
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from contract.upcast import upcast, CURRENT

def load(name): return json.loads((ROOT / "contract" / name).read_text())
V5, V6 = load("event-payloads.v5.json"), load("event-payloads.v6.json")
REG = load("command-policy-register.v6.json")
SECRETS = {"pin", "idcn", "id_number", "template", "face", "finger", "phone", "phone_number", "lat", "lng", "position", "respondent", "respondent_id", "name"}
CLOUD_ONLY = {"AttendancePinCreated", "AttendancePinSent", "AttendancePinShown", "AttendancePinRecreated", "AttendanceRequestRaised", "AttendanceDetailsDeleted",
              "TicketNotServedToday", "TicketCodesReserved", "SurveyAnswerReceived", "SurveyAnswerChecked", "SurveyAnswerDeleted", "SurveyOptOut",
              "SurveyRewardRequested", "SurveyRewardAnswered", "PanelMembership", "SurveyResultsVerified"}


class ContractV6(unittest.TestCase):
    def test_built_from_v5_and_current(self):
        r = subprocess.run([sys.executable, str(ROOT / "contract" / "tools" / "build_v6.py"), "--check"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(CURRENT, 6)

    def test_version_5_events_are_unchanged(self):
        for name, e in V5["events"].items():
            self.assertEqual(V6["events"][name]["payload"], e["payload"], name)
            self.assertEqual(V6["events"][name]["origins"], e["origins"], name)
        for e in V6["events"].values(): self.assertEqual(e["schema_version"], 6)

    def test_cloud_only_and_nothing_secret(self):
        new = set(V6["events"]) - set(V5["events"])
        self.assertGreaterEqual(len(new), 45)
        for name in CLOUD_ONLY: self.assertEqual(V6["events"][name]["origins"], ["server"], name)
        for name in new:
            props = set(V6["events"][name]["payload"]["properties"])
            self.assertEqual(props & SECRETS, set(), name)
            self.assertTrue(V6["events"][name]["blueprint"].startswith("63 "), name)

    def test_ticket_codes_use_the_lynk_alphabet(self):
        p = V6["events"]["TicketIssued"]["payload"]["properties"]
        self.assertEqual(p["code"]["pattern"], "^[2-9A-HJ-NP-Z]{6}$")
        self.assertEqual(p["section"]["pattern"], "^[2-9A-HJ-NP-Z]{3}$")

    def test_new_commands_are_class_a_and_work_offline(self):
        for c in REG["commands"]:
            if c.get("v6"):
                self.assertEqual((c["class"], c["offline"]["allowed"], c["cloud_may_reject"]), ("A", True, False), c["name"])
                for et in c["emits"]: self.assertIn("device", V6["events"][et]["origins"], (c["name"], et))

    def test_upcaster_reads_version_5_unchanged(self):
        v5 = {"type": "CardRequested", "schema_version": 5, "payload": {"request_id": "r1"}}
        up = upcast(v5)
        self.assertEqual((up["schema_version"], up["payload"]), (6, v5["payload"]))

    def test_validator_passes(self):
        r = subprocess.run([sys.executable, str(ROOT / "contract" / "tools" / "validate_contract.py")], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout[-2000:])


if __name__ == "__main__": unittest.main()
