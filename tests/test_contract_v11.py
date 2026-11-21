"""Contract version 11 (build section 4, step D2b): version 10 plus the LynkAcc, LynkInv and LynkCRM events of OFFICE UPDATE (66). Nothing
older changes; a version 10 event reads as version 11 with only its version raised. No name, bank account, card number, tax
number, address or photo is ever in an event; approvals, confirmed payments, journals, documents, reminders, write-offs and
e-invoice answers come from the cloud alone; a journal must balance and name real accounts."""
import json, pathlib, subprocess, sys, unittest
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from contract.upcast import upcast, CURRENT
from contract.tools.validate_contract import validate_event

def load(name): return json.loads((ROOT / "contract" / name).read_text())
V10, V11 = load("event-payloads.v10.json"), load("event-payloads.v11.json")
REG10, REG11 = load("command-policy-register.v10.json"), load("command-policy-register.v11.json")
NEW = {"BillRecorded", "BillApproved", "BillPaymentConfirmed", "ExpenseClaimSubmitted", "ExpenseClaimApproved", "AssetAdded", "DepreciationPosted",
       "JournalPosted", "LockDateSet", "DocumentIssued", "InvoiceReminderSent", "PromiseToPayRecorded", "InvoiceDisputed", "InvoiceWrittenOff",
       "CreditBalanceChanged", "InstalmentPlanAgreed", "SubscriptionChanged", "EInvoiceStateChanged",
       "CustomerRecordCreated", "CustomerRecordsMerged", "CustomerHandedOver", "CaseOpened", "CaseStateChanged", "ContactConsentChanged",
       "DataRequestReceived", "VisitCheckedIn"}
DEVICE = {"BillRecorded", "ExpenseClaimSubmitted", "PromiseToPayRecorded", "InvoiceDisputed", "CustomerRecordCreated", "CaseOpened",
          "ContactConsentChanged", "VisitCheckedIn"}


class ContractV11(unittest.TestCase):
    def test_built_from_v10_and_current(self):
        r = subprocess.run([sys.executable, str(ROOT / "contract" / "tools" / "build_v11.py"), "--check"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertGreaterEqual(CURRENT, 11)                                  # version 12 (section 4, step E2) reads version 11 unchanged

    def test_only_the_new_events_are_added(self):
        self.assertEqual(set(V11["events"]) - set(V10["events"]), NEW)
        for name, e in V10["events"].items():
            self.assertEqual((V11["events"][name]["payload"], V11["events"][name]["origins"]), (e["payload"], e["origins"]), name)
        self.assertTrue(all(e["schema_version"] == 11 for e in V11["events"].values()))
        self.assertEqual(REG11["commands"][:len(REG10["commands"])], REG10["commands"])

    def test_the_cloud_alone_writes_approvals_payments_journals_and_answers(self):
        emitted = {e for c in REG11["commands"] for e in c["emits"]}
        for name in NEW - DEVICE:
            self.assertEqual(V11["events"][name]["origins"], ["server"], name)
            self.assertNotIn(name, emitted, f"{name} is written by the cloud alone")
        for name in DEVICE:
            self.assertIn("device", V11["events"][name]["origins"], name)
            self.assertIn(name, emitted, f"{name} has its offline device command")

    def test_no_name_account_card_tax_number_address_or_photo(self):
        fields = {f.lower() for n in NEW for f in V11["events"][n]["payload"]["properties"]}
        for word in ("name", "iban", "card", "phone", "address", "photo", "image", "text", "pin", "password", "number", "latitude", "position"):
            self.assertFalse([f for f in fields if word in f.split("_")], f"no field about {word}: {sorted(fields)}")
        self.assertIn("document_sha256", V11["events"]["BillRecorded"]["payload"]["properties"], "a photo stays in the document store")
        self.assertNotIn("email", {f for n in NEW - {"ContactConsentChanged"} for f in V11["events"][n]["payload"]["properties"]}, "no email address")

    def test_a_version_10_event_reads_as_version_11_unchanged(self):
        old = {"type": "MessageStateChanged", "schema_version": 10, "payload": {"message_id": "m1", "state": "confirmed"}}
        up = upcast(old)
        self.assertEqual((up["schema_version"], up["payload"]), (CURRENT, old["payload"]))
        self.assertEqual(old["schema_version"], 10, "the stored event is never rewritten")

    def test_a_journal_must_balance_and_name_real_accounts(self):
        from contract.tools.validate_contract import uuid7, ts, fake_sig, MERCHANT
        ok = {"event_id": uuid7(), "origin": "server", "merchant_id": MERCHANT, "type": "JournalPosted", "schema_version": CURRENT,
              "created_at_server": ts(), "server_cursor": 1, "server_signature": fake_sig(),
              "payload": {"journal_id": uuid7(), "kind": "manual", "currency": "USD", "prepared_by": "accountant", "approved_by": "owner",
                          "lines": [{"account": "6500", "debit": 100, "credit": 0}, {"account": "1510", "debit": 0, "credit": 100}]}}
        self.assertEqual(validate_event(ok), [])
        for bad_lines in ([{"account": "6500", "debit": 100, "credit": 0}, {"account": "1510", "debit": 0, "credit": 99}],
                          [{"account": "9999", "debit": 5, "credit": 0}, {"account": "1000", "debit": 0, "credit": 5}],
                          [{"account": "6500", "debit": 5, "credit": 5}, {"account": "1000", "debit": 0, "credit": 0}]):
            bad = json.loads(json.dumps(ok)); bad["payload"]["lines"] = bad_lines
            self.assertTrue(validate_event(bad), bad_lines)
        bad = json.loads(json.dumps(ok)); bad["payload"]["lines"][0]["debit"] = 1.5
        self.assertTrue(validate_event(bad), "money is whole minor units")


if __name__ == "__main__":
    unittest.main()
