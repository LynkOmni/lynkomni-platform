"""LynkInv's rules (OFFICE UPDATE, master blueprint 66.3; section 4 step D2a): catalog/invoices.v1.json read through
core/invoices.py and ts/src/invoices.ts with shared vectors, the office settings in every country pack, the e-invoice network
behind its interface, and the 66.7 tier table. An issued invoice never changes; late fees only where the law allows; a
buyer-issued invoice only where the country allows it; amounts add up exactly; 'tax invoice' only when confirmed."""
import json, os, subprocess, sys, unittest

from core import books as B
from core import invoices as I
from core import ids as IDS

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Invoices(unittest.TestCase):
    def test_vectors_and_the_typescript_register_are_current(self):
        for tool in ("invoices_vectors.py", "books_vectors.py", "country_office.py"):
            r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", tool), "--check"], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, tool + r.stdout + r.stderr)

    def test_every_document_has_a_registered_identifier(self):
        for kind, d in I.INV["documents"].items():
            self.assertIn(d["id"], IDS.TYPES, f"{kind}: its public id comes from core/ids.py, never a new format")
            self.assertTrue(d["word"].startswith("iv_"), kind)
            for f in d["from"]:
                self.assertIn(f, I.INV["documents"], kind)

    def test_an_issued_invoice_never_changes_and_its_states_only_move_forward(self):
        for final in ("paid", "written_off", "credited", "void"):
            self.assertEqual(I.INV["moves"][final], {}, final)
        self.assertIsNone(I.inv_move("issued", "submit"))
        self.assertIsNone(I.inv_move("paid", "void"), "a paid invoice is corrected with a credit note, never voided")

    def test_buyer_issued_invoices_and_late_fees_only_where_the_law_allows(self):
        unknown = {"office": {"late_fees": {"allowed": None}, "buyer_issued_invoices": None}}
        yes = {"office": {"late_fees": {"allowed": True, "max_rate_bp_year": 1200, "fixed_fee_minor": 0}, "buyer_issued_invoices": True}}
        self.assertFalse(I.may_make(None, "buyer_issued", unknown)); self.assertTrue(I.may_make(None, "buyer_issued", yes))
        self.assertEqual(I.late_fee(100000, 30, unknown)["fee"], 0, "unknown: nothing is charged")
        self.assertEqual(I.late_fee(100000, 365, yes, owner_rate_bp=600)["fee"], 6000, "the owner may only lower the rate")
        self.assertEqual(I.label_word({"flags": {}}), "iv_doc_invoice")

    def test_amounts_add_up_exactly(self):
        self.assertEqual(sum(x["amount"] for x in I.instalments(101, 4, "2026-01-31")), 101)
        self.assertEqual(sum(I.stages(333, [3000, 4000, 3000])), 333)
        r = I.apply_payment(5000, [{"id": "a", "outstanding": 1000, "due": "2026-03-10"}, {"id": "b", "outstanding": 2500, "due": "2026-01-01"}])
        self.assertEqual([u["id"] for u in r["used"]], ["b", "a"], "the oldest first")
        self.assertEqual(r["credit_balance"], 1500, "an overpayment becomes a credit balance, never income")
        t = I.totals([{"qty": 1000, "unit_minor": 118000}], [{"kind": "sales", "rate_bp": 1800}], included=True)
        self.assertEqual((t["net"], t["total"]), (100000, 118000))

    def test_reminders_pause_for_a_promise_and_a_dispute(self):
        self.assertIsNone(I.reminder_due("2026-03-10", "2026-03-24", [], promise="2026-03-30"))
        self.assertIsNone(I.reminder_due("2026-03-10", "2026-03-24", [], disputed=True))
        self.assertEqual(I.reminder_due("2026-03-10", "2026-03-24", ["friendly"]), "firm")

    def test_every_pack_has_office_settings_that_start_unknown(self):
        for n in sorted(os.listdir(os.path.join(ROOT, "contract", "country-packs"))):
            if not n.endswith(".json"):
                continue
            o = json.load(open(os.path.join(ROOT, "contract", "country-packs", n), encoding="utf-8"))["office"]
            if not o.get("confirmed"):
                self.assertIsNot(o["late_fees"]["allowed"], True, f"{n}: late fees are never allowed before a lawyer confirms")

    def test_the_e_invoice_network_only_moves_forward_and_only_it_confirms(self):
        from services.einvoice import SandboxEInvoiceNetwork, next_state
        net = SandboxEInvoiceNetwork(needs_tax_number=True)
        bad = net.submit({"lines": [{"total": 100}], "total_minor": 100})
        self.assertEqual(bad["state"], "failed")
        ok = net.submit({"lines": [{"total": 100}, {"total": 18}], "total_minor": 118, "seller_tax_number": "T1"})
        state = next_state("queued", ok)
        state = next_state(state, net.poll(ok["ref"])); self.assertEqual(state, "accepted")
        state = next_state(state, net.poll(ok["ref"])); self.assertEqual(state, "confirmed")
        self.assertEqual(next_state("confirmed", {"state": "sent"}), "confirmed")
        led = json.load(open(os.path.join(ROOT, "providers", "registry.v1.json"), encoding="utf-8"))
        self.assertTrue(any(i["id"] == "e_invoice_network" and i["status"] == "sandbox" for i in led["items"]))

    def test_rates_are_read_exactly_and_invoicing_uses_integers(self):
        self.assertEqual(B.rate_bp("0.18"), 1800); self.assertEqual(B.rate_bp("7.5%"), 750)
        with self.assertRaises(ValueError):
            B.rate_bp("0.00001")
        for f in ("services/invoicing.py", "services/suite.py"):
            self.assertNotIn("Decimal", open(os.path.join(ROOT, f), encoding="utf-8").read(), f)

    def test_the_tier_table_of_66_7_is_in_billing(self):
        from services import billing
        F = billing.FEATURES["lynkinv"]
        for k in ("e_invoices", "withholding_tax", "legal_keeping", "offline", "import_records", "change_history"):
            self.assertTrue(F[0][k], f"{k} is on every tier, Free included")
        self.assertTrue(F[1]["stepped_reminders"] and F[2]["approval_before_sending"] and F[3]["usage_billing"])


if __name__ == "__main__":
    unittest.main()
