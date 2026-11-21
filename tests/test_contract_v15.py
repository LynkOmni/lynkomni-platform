"""Contract version 15 (build section 4, step E4b): version 14 plus LynkExchange's order steps and the proof of exchange (EXCHANGE
UPDATE 65). Nothing older changes; every new event is cloud only (nothing about an exchange is queued offline); a payee's name,
bank account or contact, an identity document or a safety word is never in an event; money facts carry the partner's reference."""
import json, pathlib, subprocess, sys, unittest
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from contract.upcast import upcast, CURRENT
from contract.tools.validate_contract import validate_event, uuid7, ts, fake_sig, MERCHANT

def load(name): return json.loads((ROOT / "contract" / name).read_text())
V14, V15 = load("event-payloads.v14.json"), load("event-payloads.v15.json")
REG14, REG15 = load("command-policy-register.v14.json"), load("command-policy-register.v15.json")
NEW = {"ExchangeOrderPlaced", "ExchangeOrderPaid", "ExchangeOrderFailed", "ExchangeRefunded", "ExchangeProofIssued"}


class ContractV15(unittest.TestCase):
    def test_built_from_v14_and_current(self):
        r = subprocess.run([sys.executable, str(ROOT / "contract" / "tools" / "build_v15.py"), "--check"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertGreaterEqual(CURRENT, 15)

    def test_only_the_new_events_are_added_and_all_are_cloud_only(self):
        self.assertEqual(set(V15["events"]) - set(V14["events"]), NEW)
        for name, e in V14["events"].items():
            if name == "CustomerRecordCreated":
                k14, k15 = e["payload"]["properties"]["kind"]["enum"], V15["events"][name]["payload"]["properties"]["kind"]["enum"]
                self.assertEqual(sorted(set(k15) - set(k14)), ["payee"], "version 15 only adds the payee kind")
                continue
            self.assertEqual((V15["events"][name]["payload"], V15["events"][name]["origins"]), (e["payload"], e["origins"]), name)
        self.assertEqual(REG15["commands"], REG14["commands"], "no device command: nothing about an exchange is queued offline")
        for name in NEW | {"ExchangeSettled"}:
            self.assertEqual(V15["events"][name]["origins"], ["server"], name)
        for name in ("ExchangeOrderPaid", "ExchangeRefunded", "ExchangeSettled"):
            self.assertIn("provider_reference", V15["events"][name]["payload"]["required"], name)

    def test_no_payee_bank_account_identity_or_safety_word(self):
        fields = {f.lower() for n in NEW for f in V15["events"][n]["payload"]["properties"]}
        for word in ("name", "iban", "account", "bank", "phone", "email", "identity", "document", "word", "code", "address"):
            self.assertFalse([f for f in fields if word in f.split("_") and f not in ("document_id", "code_sha256")], word)

    def test_a_version_14_event_reads_as_version_15_unchanged(self):
        old = {"type": "BookingCheckedIn", "schema_version": 14, "payload": {"booking_id": uuid7()}}
        self.assertEqual(upcast(old)["schema_version"], CURRENT)

    def test_an_order_validates_and_a_decimal_rate_part_is_refused(self):
        ok = {"event_id": uuid7(), "origin": "server", "merchant_id": MERCHANT, "type": "ExchangeOrderPlaced", "schema_version": 15,
              "created_at_server": ts(), "server_cursor": 1, "server_signature": fake_sig(),
              "payload": {"order_id": uuid7(), "kind": "convert", "amount": 100000, "currency": "USD", "to_currency": "EUR", "part_bps": 50, "practice": True}}
        self.assertEqual(validate_event(ok), [], validate_event(ok))
        for k, v in (("part_bps", 0.5), ("iban", "DE00"), ("kind", "margin")):
            bad = json.loads(json.dumps(ok)); bad["payload"][k] = v
            self.assertTrue(validate_event(bad), k)


if __name__ == "__main__":
    unittest.main()
