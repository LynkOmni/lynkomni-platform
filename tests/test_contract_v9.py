"""Contract version 9 (build section 4, step A2): version 8 plus the events of the section 4 links in catalog/connections.v1.json.
Nothing older changes; a version 8 event reads as version 9 with only its version raised."""
import json, pathlib, subprocess, sys, unittest
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from contract.upcast import upcast, CURRENT
from contract.tools.validate_contract import validate_event

def load(name): return json.loads((ROOT / "contract" / name).read_text())
V8, V9 = load("event-payloads.v8.json"), load("event-payloads.v9.json")
REG8, REG9 = load("command-policy-register.v8.json"), load("command-policy-register.v9.json")
NEW = {"InvoiceIssued", "CreditNoteIssued", "PeriodClosed", "DealStageChanged", "ConversationCardSent", "AdEarningsRecorded",
       "DocumentFiled", "VoteRollImported", "ExchangeSettled"}


class ContractV9(unittest.TestCase):
    def test_built_from_v8_and_current(self):
        r = subprocess.run([sys.executable, str(ROOT / "contract" / "tools" / "build_v9.py"), "--check"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertGreaterEqual(CURRENT, 9)                                   # version 10 (section 4, step C1) reads version 9 unchanged

    def test_only_the_new_events_are_added(self):
        self.assertEqual(set(V9["events"]) - set(V8["events"]), NEW)
        for name, e in V8["events"].items():
            self.assertEqual((V9["events"][name]["payload"], V9["events"][name]["origins"]), (e["payload"], e["origins"]), name)
        self.assertTrue(all(e["schema_version"] == 9 for e in V9["events"].values()))
        self.assertEqual(REG9["commands"][:len(REG8["commands"])], REG8["commands"])

    def test_the_cloud_alone_issues_closes_settles_and_imports(self):
        for name in NEW - {"DealStageChanged", "DocumentFiled"}:
            self.assertEqual(V9["events"][name]["origins"], ["server"], name)
        for name in ("DealStageChanged", "DocumentFiled"):
            self.assertIn("device", V9["events"][name]["origins"])
        emitted = {e for c in REG9["commands"] for e in c["emits"]}
        self.assertIn("DealStageChanged", emitted); self.assertIn("DocumentFiled", emitted)
        for name in NEW - {"DealStageChanged", "DocumentFiled"}:
            self.assertNotIn(name, emitted, f"{name} is written by the cloud alone, never by a device command")

    def test_no_secret_or_personal_field_and_money_is_integer_minor_units(self):
        text = json.dumps({n: V9["events"][n] for n in NEW}).lower()
        for word in ("pin", "card_number", "phone", "position", "latitude", "password", '"name"'):
            self.assertNotIn(word, text, word)
        for n in NEW:
            for field, spec in V9["events"][n]["payload"]["properties"].items():
                if spec.get("$ref") == "#/$defs/money":
                    cur = field.replace("amount", "currency") if "amount" in field else "currency"
                    self.assertIn(cur, V9["events"][n]["payload"]["properties"], f"{n}.{field} carries its currency")

    def test_a_version_8_event_reads_as_version_9_unchanged(self):
        old = {"type": "SaleRecorded", "schema_version": 8, "payload": {"sale_id": "s1", "total": 5}}
        up = upcast(old)
        self.assertEqual((up["schema_version"], up["payload"]), (CURRENT, old["payload"]))
        self.assertEqual(old["schema_version"], 8, "the stored event is never rewritten")

    def test_a_new_event_validates(self):
        from contract.tools.validate_contract import uuid7, ts, fake_sig, MERCHANT
        ok = {"event_id": uuid7(), "origin": "server", "merchant_id": MERCHANT, "type": "InvoiceIssued", "schema_version": 9,
              "created_at_server": ts(), "server_cursor": 1, "server_signature": fake_sig(),
              "payload": {"invoice_id": uuid7(), "total": 150000, "currency": "USD", "issued_on": "2026-11-19"}}
        self.assertEqual(validate_event(ok), [])
        bad = json.loads(json.dumps(ok)); bad["payload"]["total"] = 1500.5
        self.assertTrue(validate_event(bad), "money is never a float")

if __name__ == "__main__":
    unittest.main()
