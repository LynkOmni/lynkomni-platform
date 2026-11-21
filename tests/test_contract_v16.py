"""Contract version 16 (build section 4, step F, row 67.17): version 15 plus the office side of gift cards, store credit, deposits,
matching and payment costs (SERVICES UPDATE 67.2 and 67.8). Nothing older changes; the four device events are class A (offline, never
rejected); the provider's facts are cloud only and carry its reference; a card's code or PIN, a customer's name or contact and a bank
account are never in an event."""
import json, pathlib, subprocess, sys, unittest
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from contract.upcast import upcast, CURRENT
from contract.tools.validate_contract import validate_event, uuid7, ts, fake_sig, MERCHANT, Device

def load(name): return json.loads((ROOT / "contract" / name).read_text())
V15, V16 = load("event-payloads.v15.json"), load("event-payloads.v16.json")
REG15, REG16 = load("command-policy-register.v15.json"), load("command-policy-register.v16.json")
DEVICE = {"GiftCardSold", "DepositTaken", "DepositSettled"}
NEW = DEVICE | {"StoreCreditIssued", "DepositRefunded", "StoredValueConflictFlagged", "PaymentSettled", "PaymentMatched", "PaymentMatchUndone",
                "ProviderPayoutScheduled", "ProviderPayoutArrived"}


class ContractV16(unittest.TestCase):
    def test_built_from_v15_and_current(self):
        r = subprocess.run([sys.executable, str(ROOT / "contract" / "tools" / "build_v16.py"), "--check"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertGreaterEqual(CURRENT, 16)

    def test_only_new_events_and_who_may_write_them(self):
        self.assertEqual(set(V16["events"]) - set(V15["events"]), NEW)
        for name, e in V15["events"].items():
            self.assertEqual((V16["events"][name]["payload"], V16["events"][name]["origins"]), (e["payload"], e["origins"]), name)
        for name in NEW - DEVICE - {"StoreCreditIssued"}:
            self.assertEqual(V16["events"][name]["origins"], ["server"], name)
        for name in DEVICE:
            self.assertEqual(V16["events"][name]["origins"], ["device"], name)
        self.assertEqual(V16["events"]["StoreCreditIssued"]["origins"], ["device", "server"])
        added = [c for c in REG16["commands"] if c not in REG15["commands"]]
        self.assertEqual(sorted(e for c in added for e in c["emits"]), sorted(DEVICE | {"StoreCreditIssued"}))
        self.assertTrue(all(c["class"] == "A" and c["offline"]["allowed"] and not c["cloud_may_reject"] for c in added), "never blocked")
        for name in ("DepositRefunded", "PaymentSettled", "ProviderPayoutArrived"):
            self.assertIn("provider_reference", V16["events"][name]["payload"]["required"], name)
        self.assertNotIn("credit", V16["events"]["GiftCardSold"]["payload"]["properties"]["method"]["enum"], "a gift card is never sold on credit")

    def test_no_code_pin_name_contact_or_bank_account(self):
        fields = {f.lower() for n in NEW for f in V16["events"][n]["payload"]["properties"]}
        for word in ("code", "pin", "name", "phone", "email", "iban", "bank", "account", "address"):
            self.assertFalse([f for f in fields if word in f.split("_")], word)

    def test_a_version_15_event_reads_as_version_16_unchanged(self):
        old = {"type": "ExchangeOrderPaid", "schema_version": 15, "payload": {"order_id": uuid7(), "provider_reference": "P-1"}}
        self.assertEqual(upcast(old)["schema_version"], CURRENT)

    def test_a_device_sells_a_gift_card_and_a_settlement_validates(self):
        sold = Device().emit("GiftCardSold", {"card_id": uuid7(), "amount": 5000, "currency": "RWF", "method": "cash", "top_up": False})
        self.assertEqual(validate_event(sold), [], validate_event(sold))
        ok = {"event_id": uuid7(), "origin": "server", "merchant_id": MERCHANT, "type": "PaymentSettled", "schema_version": 16,
              "created_at_server": ts(), "server_cursor": 1, "server_signature": fake_sig(),
              "payload": {"provider_reference": "P-1", "amount": 1500, "currency": "RWF", "provider_fee": 30, "lynkomni_part": 8, "settled_on": "2026-11-21"}}
        self.assertEqual(validate_event(ok), [], validate_event(ok))
        for k, v in (("provider_fee", 30.5), ("card_code", "1234"), ("settled_on", "21/11/2026")):
            bad = json.loads(json.dumps(ok)); bad["payload"][k] = v
            self.assertTrue(validate_event(bad), k)
        forged = Device().emit("PaymentSettled", ok["payload"])
        self.assertTrue(validate_event(forged), "a device can never write the provider's settlement")


if __name__ == "__main__":
    unittest.main()
