"""The large-organisation set and Move in (OFFICE UPDATE, master blueprint 66.5 and 66.6; section 4 step D4a): catalog/enterprise.v1.json
read through core/enterprise.py and ts/src/enterprise.ts with shared vectors, and the cloud services in services/enterprise.py.
Own flows and roles only ever do less; the preparer never approves; nothing under a legal hold changes; a removed person loses
access within minutes; nothing moves in while its check report shows an error; leaving is a full download."""
import os, subprocess, sys, unittest
os.environ["LYNK_MODE"] = "sandbox"

from core import enterprise as E

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Rules(unittest.TestCase):
    def test_vectors_and_the_typescript_register_are_current(self):
        r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "enterprise_vectors.py"), "--check"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_own_roles_never_exceed_the_owner_and_keep_preparing_and_approving_apart(self):
        self.assertEqual(E.role_problems({"inv": ["view", "prepare"]}), [])
        self.assertIn("kept_apart", [p["problem"] for p in E.role_problems({"acc": ["prepare", "approve"]})])
        self.assertIn("more_than_owner", [p["problem"] for p in E.role_problems({"crm": ["post"]})])
        for name, perms in E.ENT["roles"]["base"].items():
            if name != "owner":
                self.assertEqual([p for p in E.role_problems(perms, kept_apart=False) if p["problem"] == "more_than_owner"], [], name)
        self.assertEqual(E.ENT["roles"]["base"]["auditor"]["acc"], ["view", "export"], "the auditor only reads")

    def test_amounts_are_read_exactly_or_refused(self):
        self.assertEqual(E.parse_amount("1,234.50", 2), 123450)
        self.assertIsNone(E.parse_amount("12.345", 2), "more decimals than the currency has")
        self.assertIsNone(E.parse_amount("1e5", 2))
        self.assertIsNone(E.parse_date("2026-02-29"))


class Services(unittest.TestCase):
    def setUp(self):
        os.environ["LYNK_MODE"] = "sandbox"
        from services.platform import Platform
        self.p = Platform(); self.p.register("m1", "RW"); self.o, self.mi = self.p.enterprise, self.p.move_in

    def test_the_set_needs_max_and_an_agreement(self):
        with self.assertRaises(PermissionError):
            self.o.set_flow("m1", "bill", [{"role": "manager"}])
        self.p.billing.set_plan("m1", "lynkacc", "max")
        with self.assertRaises(PermissionError):
            self.o.set_flow("m1", "bill", [{"role": "manager"}])
        self.o.set_agreement("m1", True, "staff-1")
        self.assertEqual(self.o.set_flow("m1", "bill", [{"role": "manager"}, {"role": "finance", "from_minor": 100000}]), 2)
        self.assertEqual([s["role"] for s in self.o.steps_for("m1", "bill", 150000)], ["manager", "finance"])
        with self.assertRaises(ValueError):
            self.o.define_role("m1", "clerk", {"acc": ["prepare", "approve"]})

    def test_removed_staff_lose_access_and_holds_freeze_records(self):
        self.p.billing.set_plan("m1", "lynkacc", "max"); self.o.set_agreement("m1", True, "staff-1")
        self.o.directory.push({"change": "add", "user": "u7", "role": "staff", "minute": 0})
        self.o.sync_staff("m1")
        self.assertTrue(self.o.has_access("m1", "u7", 10))
        self.o.directory.push({"change": "remove", "user": "u7", "minute": 100})
        self.o.sync_staff("m1")
        self.assertTrue(self.o.has_access("m1", "u7", 110)); self.assertFalse(self.o.has_access("m1", "u7", 115))
        self.o.hold("m1", "LOINV-X", True, "dispute")
        self.assertFalse(self.o.may_delete("m1", "LOINV-X", 9999, 10, 10))
        audit = self.o.audit_export("m1")
        self.assertTrue(audit.startswith("id,at,type,device"))
        self.assertIn("enterprise.agreement", audit, "the export carries every event, not an empty list")
        self.assertTrue(self.o.is_test_copy(self.o.test_copy("m1")))

    def test_nothing_moves_in_with_an_error_and_contacts_go_to_the_vault(self):
        bad = self.mi.apply("m1", "customers", ["ref", "name"], [["C1", ""]], "u1")
        self.assertEqual(bad["applied"], 0); self.assertFalse(bad["report"]["ok"])
        ok = self.mi.apply("m1", "customers", ["ref", "name", "email"], [["C1", "Amina", "a@shop.rw"], ["C2", "Jean", ""]], "u1")
        self.assertEqual(ok["applied"], 2)
        events = self.p.c.store.since("m1")
        self.assertTrue(events, "the check reads real events")
        self.assertNotIn("a@shop.rw", str(events))
        rep = self.mi.check("m1", "open_invoices", ["number", "customer_ref", "issued_on", "amount"], [["A-1", "C1", "2026-01-31", "250"], ["A-2", "C9", "2026-01-31", "5"]])
        self.assertEqual([e["issue"] for e in rep["errors"]], ["unknown_ref"], "an open invoice for someone not moved in")

    def test_opening_balances_need_two_people_and_leaving_is_a_full_download(self):
        self.p.billing.set_plan("m1", "lynkacc", "plus")
        r = self.mi.apply("m1", "opening_balances", ["account", "debit", "credit"], [["1020", "500", ""], ["3000", "", "500"]], "u1")
        self.assertEqual(r["pending"]["state"], "awaiting_approval")
        self.p.books.approve_journal("m1", r["pending"]["pending"], "u2")
        out = self.mi.leave("m1")
        self.assertIn("journal.csv", out); self.assertTrue(any(row[2] == "1020" for row in out["journal.csv"][1:]))

    def test_every_service_has_its_flows_and_each_needs_its_own_max(self):
        flows = E.ENT["approval_flows"]
        self.assertTrue(all(d in flows["document_family"] for d in flows["documents"]), "every document names its service")
        self.p.billing.set_plan("m1", "lynkacc", "max"); self.o.set_agreement("m1", True, "staff-1")
        with self.assertRaises(PermissionError):
            self.o.set_flow("m1", "stock_adjustment", [{"role": "manager"}])      # LynkStock is not on Max
        self.p.billing.set_plan("m1", "lynkstock", "max")
        self.assertEqual(self.o.set_flow("m1", "stock_adjustment", [{"role": "manager"}]), 1)

    def test_every_service_moves_in(self):
        self.p.billing.set_plan("m1", "lynkexchange", "plus")
        r = self.mi.apply("m1", "products", ["ref", "name", "price"], [["P1", "Tea", "2500"], ["P2", "Rice", "10000"]], "u1")
        self.assertEqual(r["applied"], 2); self.assertTrue(r["on_devices"])
        self.assertEqual(self.mi.catalog_pack("m1")["products"][0]["price"], 2500, "a price is whole minor units")
        self.assertEqual(self.mi.check("m1", "products", ["ref", "name", "price"], [["P3", "Tea", "2.50"]])["errors"][0]["issue"], "bad_amount", "francs have no cents")
        bad = self.mi.check("m1", "stock_levels", ["product_ref", "quantity"], [["P9", "3"], ["P1", "2.5"]])
        self.assertEqual(sorted(e["issue"] for e in bad["errors"]), ["bad_number", "unknown_ref"])
        self.assertEqual(self.mi.apply("m1", "stock_levels", ["product_ref", "quantity"], [["P1", "12"]], "u1")["applied"], 1)
        self.assertEqual(self.mi.apply("m1", "members", ["ref", "name", "email"], [["M1", "Ines", "i@club.rw"]], "u1", entity_kind="association")["applied"], 1)
        self.mi.apply("m1", "points", ["member_ref", "points"], [["M1", "40"]], "u1")
        earned = self.p.c.store.of("m1", "loyalty.earned")[-1]["payload"]
        self.assertTrue(earned["customer"].startswith("LO"), "points follow the member's LynkCRM record")
        self.assertNotIn("i@club.rw", str(self.p.c.store.since("m1")))
        self.assertEqual(self.mi.apply("m1", "payees", ["ref", "name", "bank_details"], [["Y1", "Supplier Ltd", "IBAN-X"]], "u1")["applied"], 1)
        self.assertNotIn("IBAN-X", str(self.p.c.store.since("m1")))
        self.assertEqual(self.mi.apply("m1", "bookings", ["ref", "starts_on", "total"], [["B1", "2026-12-01", "15000"]], "u1")["applied"], 1)


if __name__ == "__main__":
    unittest.main()
