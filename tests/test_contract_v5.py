"""Contract version 5 (MASTER UPDATE, owner approved 2026-11-10): version 4 plus the LynkVCard card group request (section 61).
A request is made online only; the licensed partner's answer is written by the cloud alone; no event carries a card detail."""
import json, pathlib, subprocess, sys, unittest
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from contract.upcast import upcast, CURRENT

def load(name): return json.loads((ROOT / "contract" / name).read_text())
V4, V5 = load("event-payloads.v4.json"), load("event-payloads.v5.json")
REG = load("command-policy-register.v5.json")
NEW = {"CardRequested", "CardRequestConfirmed", "CardRequestFailed"}
CARD_DETAILS = {"card_number", "pan", "number", "cvv", "cvc", "code", "expiry", "pin", "income", "balance", "salary", "account_number"}


class ContractV5(unittest.TestCase):
    def test_built_from_v4_and_current(self):
        r = subprocess.run([sys.executable, str(ROOT / "contract" / "tools" / "build_v5.py"), "--check"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(CURRENT, 5)

    def test_version_4_events_are_unchanged_and_the_card_events_added(self):
        self.assertEqual(set(V5["events"]) - set(V4["events"]), NEW)
        for name, e in V4["events"].items():
            self.assertEqual(V5["events"][name]["payload"], e["payload"], name)
            self.assertEqual(V5["events"][name]["origins"], e["origins"], name)
        for e in V5["events"].values(): self.assertEqual(e["schema_version"], 5)

    def test_only_the_cloud_writes_the_partners_answer_and_no_card_detail_is_carried(self):
        self.assertEqual(V5["events"]["CardRequested"]["origins"], ["device"])
        for name in ("CardRequestConfirmed", "CardRequestFailed"): self.assertEqual(V5["events"][name]["origins"], ["server"], name)
        for name in NEW: self.assertEqual(set(V5["events"][name]["payload"]["properties"]) & CARD_DETAILS, set(), name)
        self.assertEqual(V5["events"]["CardRequestConfirmed"]["payload"]["properties"]["credit_limit"]["type"], "integer")

    def test_request_card_is_class_c_and_never_offline(self):
        c = next(c for c in REG["commands"] if c["name"] == "RequestCard")
        self.assertEqual((c["class"], c["offline"]["allowed"], c["emits"]), ("C", False, ["CardRequested"]))
        self.assertEqual(REG["session_policy"]["on_expiry"], "cash_selling_continues_rest_waits_for_sign_in")

    def test_upcaster_reads_version_4_unchanged(self):
        v4 = {"type": "ZoneEntered", "schema_version": 4, "payload": {"zone_id": "z1"}}
        up = upcast(v4)
        self.assertEqual((up["schema_version"], up["payload"]), (5, v4["payload"]))
        self.assertEqual(v4["schema_version"], 4)

    def test_validator_passes(self):
        r = subprocess.run([sys.executable, str(ROOT / "contract" / "tools" / "validate_contract.py")], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout[-2000:])


if __name__ == "__main__": unittest.main()
