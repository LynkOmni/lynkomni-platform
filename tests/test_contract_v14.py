"""Contract version 14 (build section 4, step E4a): version 13 plus LynkBooking's facts for the office services (BOOKING UPDATE 64).
Nothing older changes; a version 13 event reads as version 14 with only its version raised. A customer's name or contact, a ticket's
code or an address is never in an event. Only checking in and cancelling at the front desk may come from a device."""
import json, pathlib, subprocess, sys, unittest
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from contract.upcast import upcast, CURRENT
from contract.tools.validate_contract import validate_event, uuid7, ts, fake_sig, MERCHANT

def load(name): return json.loads((ROOT / "contract" / name).read_text())
V13, V14 = load("event-payloads.v13.json"), load("event-payloads.v14.json")
REG13, REG14 = load("command-policy-register.v13.json"), load("command-policy-register.v14.json")
NEW = {"BookingConfirmed", "BookingPaid", "BookingCheckedIn", "BookingCancelled", "BookingNoShow", "BookingRefunded", "BookingCommissionRecorded"}
DEVICE = {"BookingCheckedIn", "BookingCancelled"}


class ContractV14(unittest.TestCase):
    def test_built_from_v13_and_current(self):
        r = subprocess.run([sys.executable, str(ROOT / "contract" / "tools" / "build_v14.py"), "--check"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertGreaterEqual(CURRENT, 14)                                  # version 15 (section 4, step E4b) reads version 14 unchanged

    def test_only_the_new_events_are_added(self):
        self.assertEqual(set(V14["events"]) - set(V13["events"]), NEW)
        for name, e in V13["events"].items():
            self.assertEqual((V14["events"][name]["payload"], V14["events"][name]["origins"]), (e["payload"], e["origins"]), name)
        self.assertTrue(all(e["schema_version"] == 14 for e in V14["events"].values()))
        self.assertEqual(REG14["commands"][:len(REG13["commands"])], REG13["commands"])

    def test_the_cloud_alone_writes_confirmations_payments_no_shows_refunds_and_commission(self):
        emitted = {e for c in REG14["commands"] for e in c["emits"]}
        for name in NEW - DEVICE:
            self.assertEqual(V14["events"][name]["origins"], ["server"], name)
            self.assertNotIn(name, emitted)
        for name in DEVICE:
            self.assertIn("device", V14["events"][name]["origins"]); self.assertIn(name, emitted)
        for name in ("BookingPaid", "BookingRefunded"):
            self.assertIn("provider_reference", V14["events"][name]["payload"]["required"], "only the provider confirms money")

    def test_no_name_contact_code_or_address(self):
        fields = {f.lower() for n in NEW for f in V14["events"][n]["payload"]["properties"]}
        for word in ("name", "email", "phone", "address", "code", "ticket", "position", "latitude"):
            self.assertFalse([f for f in fields if word in f.split("_")], word)

    def test_a_version_13_event_reads_as_version_14_unchanged(self):
        old = {"type": "LegalHoldChanged", "schema_version": 13, "payload": {"document_id": uuid7(), "on": True}}
        self.assertEqual(upcast(old)["schema_version"], CURRENT)

    def test_a_paid_booking_validates_and_a_float_amount_is_refused(self):
        ok = {"event_id": uuid7(), "origin": "server", "merchant_id": MERCHANT, "type": "BookingPaid", "schema_version": CURRENT,
              "created_at_server": ts(), "server_cursor": 1, "server_signature": fake_sig(),
              "payload": {"booking_id": uuid7(), "part": "deposit", "amount": 2000, "currency": "USD", "provider_reference": "prov-123"}}
        self.assertEqual(validate_event(ok), [], validate_event(ok))
        bad = json.loads(json.dumps(ok)); bad["payload"]["amount"] = 20.5
        self.assertTrue(validate_event(bad))
        bad = json.loads(json.dumps(ok)); bad["payload"]["customer_name"] = "Ana"
        self.assertTrue(validate_event(bad))


if __name__ == "__main__":
    unittest.main()
