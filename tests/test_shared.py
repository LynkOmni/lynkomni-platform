"""The parts every service shares (CONNECT UPDATE 71.3; section 4 row 71.9 step 2; catalog/shared.v1.json, core/shared.py,
services/shared.py): one role system, calendar, address book, timeline and audit viewer, recycle bin, consent page, plans and limits,
data dictionary and test copy."""
import json, os, re, subprocess, sys, unittest
os.environ["LYNK_MODE"] = "sandbox"
from core import shared as SH, build_sections as BS
from core.connections import LINKS
from identity import device_access
from services.platform import Platform

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LINES = [{"qty_milli": 1000, "unit_minor": 1000}]
DAY = 86400


class Register(unittest.TestCase):
    def test_every_role_maps_to_a_base_role_with_permissions(self):
        for role in device_access.ROLES:
            self.assertIn(SH.base_role("device", role), SH.SHARED["roles"]["base"], role)
        self.assertEqual(set(SH.SHARED["roles"]["base"]), set(SH.BASE_ROLES))
        self.assertTrue(SH.may("device", "manager", "pos", "approve"))
        self.assertFalse(SH.may("device", "cashier", "acc", "approve"), "a cashier never approves in the books")
        with self.assertRaises(KeyError): SH.base_role("device", "chef")

    def test_calendar_sources_name_real_services_and_sections(self):
        from services.billing import FAMILIES
        for x in SH.SHARED["calendar"]["sources"]:
            self.assertIn(x["service"], FAMILIES, x["id"]); self.assertIn(str(x["build_section"]), [str(n) for n in BS.ORDER], x["id"])

    def test_the_bin_never_takes_what_must_stay(self):
        self.assertTrue(SH.binnable("crm_record")); self.assertFalse(SH.binnable("invoice")); self.assertFalse(SH.binnable("ballot"))
        self.assertFalse(SH.purge_due(0, 29 * DAY)); self.assertTrue(SH.purge_due(0, 30 * DAY))

    def test_the_data_dictionary_is_current_and_holds_no_personal_field(self):
        r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "data_dictionary.py"), "--check"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout)
        d = json.load(open(os.path.join(ROOT, "catalog", "data-dictionary.v1.json"), encoding="utf-8"))
        bad = re.compile(r"^(customer_name|person_name|staff_name|full_name|first_name|last_name|email|phone|phone_number|address|id_number|latitude|longitude|lat|lng)$")
        for e in d["events"]:
            self.assertEqual([f for f in e["fields"] if bad.match(f)], [], e["type"])


class Vectors(unittest.TestCase):
    def test_shared_vectors_are_current(self):
        r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "shared_vectors.py"), "--check"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


class Cloud(unittest.TestCase):
    def setUp(self):
        os.environ["LYNK_MODE"] = "sandbox"
        self.p = Platform(); self.p.register("m1", "RW"); self.sh = self.p.shared
        for fam in ("lynkinv", "lynkcrm", "lynkacc", "lynkfiles"): self.p.billing.set_plan("m1", fam, "pro")
        self.cust = self.p.crm.create("m1", "u1", "customer", name="Amina", email="amina@example.com")

    def test_one_role_set_once_decides_every_service(self):
        self.sh.set_role("m1", "u2", "accountant", "u1")
        self.assertTrue(self.sh.may("m1", "u2", "acc", "post"))
        self.assertFalse(self.sh.may("m1", "u2", "pos", "approve"))
        with self.assertRaises(PermissionError): self.sh.set_role("m1", "u3", "owner", "u3")
        with self.assertRaises(ValueError): self.sh.set_role("m1", "u3", "cashier", "u1")

    def test_one_calendar_reads_each_service(self):
        inv = self.p.invoicing.issue("m1", self.cust, LINES)
        self.p.invoicing.promise("m1", inv["id"], "2099-01-05")
        b = self.p.books.record_bill("m1", "u1", 5000, due="2099-01-10")["bill"]
        cal = self.sh.calendar("m1", "2000-01-01", "2099-12-31")
        self.assertEqual({(x["source"], x["ref"]) for x in cal} >= {("invoice_due", inv["id"]), ("promise_to_pay", inv["id"]), ("bill_due", b)}, True)
        self.assertEqual(cal, sorted(cal, key=lambda x: (x["date"], x["source"], x["ref"])))

    def test_the_address_book_is_the_crm_with_vault_references_only(self):
        self.p.invoicing.issue("m1", self.cust, LINES)
        book = self.sh.address_book("m1")
        row = next(r for r in book if r["id"] == self.cust)
        self.assertIn("lynkinv", row["used_by"])
        self.assertNotIn("amina", json.dumps(book).lower(), "no name or email in the address book itself")

    def test_timeline_and_audit_viewer(self):
        self.p.crm.consent("m1", self.cust, "email", True)
        tl = self.sh.record_timeline("m1", self.cust)
        self.assertIn("crm.consent", [x["type"] for x in tl])
        self.assertEqual(set(tl[0]), {"at", "type", "device"})
        with self.assertRaises(PermissionError): self.sh.audit("m1", "u9", "staff")
        rows = self.sh.audit("m1", "u1", "owner")
        self.assertTrue(rows)
        self.assertIn("audit.viewed", [e["type"] for e in self.p.c.store.since("m1")], "every look at the audit viewer is recorded")

    def test_recycle_bin_keeps_restores_and_empties(self):
        with self.assertRaises(PermissionError): self.sh.delete("m1", "invoice", "x", "u1")
        bid = self.sh.delete("m1", "crm_record", self.cust, "u1")
        self.assertNotIn(self.cust, [r["id"] for r in self.sh.address_book("m1")])
        self.sh.restore("m1", bid, "u1")
        self.assertIn(self.cust, [r["id"] for r in self.sh.address_book("m1")])
        self.sh.delete("m1", "crm_record", self.cust, "u1")
        self.assertEqual(self.sh.empty("m1", now=self.p.shared.now() + 29 * DAY), [])
        self.assertEqual(self.sh.empty("m1", now=self.p.shared.now() + 31 * DAY), [self.cust])
        self.assertIsNone(self.p.crm.recs[self.cust]["name_ref"], "gone for good: the vault reference is dropped")

    def test_consent_page_and_links_that_need_the_business(self):
        lid = next(k for k, l in LINKS.items() if l["consent"] == "merchant")
        with self.assertRaises(ValueError): self.sh.set_link("m1", next(k for k, l in LINKS.items() if l["consent"] == "none"), True, "u1")
        self.sh.set_link("m1", lid, True, "u1")
        self.p.crm.consent("m1", self.cust, "email", True)
        page = self.sh.consents("m1")
        self.assertTrue(next(x for x in page if x["ref"] == lid)["on"])
        self.assertEqual(next(x for x in page if x["source"] == "contact_channels" and x["ref"] == "email")["count"], 1)
        self.sh.set_link("m1", lid, False, "u1"); self.assertFalse(self.sh.link_on("m1", lid))

    def test_plans_and_limits_come_from_billing(self):
        from services.billing import FEATURES
        self.p.invoicing.issue("m1", self.cust, LINES)
        rows = {r["family"]: r for r in self.sh.plans_and_limits("m1")}
        self.assertEqual(rows["lynkinv"]["tier"], "pro")
        lim = {x["key"]: x for x in rows["lynkinv"]["limits"]}
        if "invoices_per_month" in lim: self.assertEqual(lim["invoices_per_month"]["used"], 1)
        crm = {x["key"]: x for x in rows["lynkcrm"]["limits"]}
        if "customers" in crm: self.assertEqual(crm["customers"]["used"], 1)

    def test_a_test_copy_never_messages_a_customer(self):
        t = self.sh.test_copy("m1")
        self.assertTrue(self.sh.is_test_copy(t)); self.assertFalse(self.sh.is_test_copy("m1"))
        from services.flow import REGISTER
        a = next(x for x in REGISTER.values() if x["customer_message"])
        self.p.flow.handle(a["id"], lambda f, m, p, now: {"sent": 1}); self.p.flow.set_on(t, a["id"])
        self.assertEqual(self.p.flow._run(a, t, {}, trigger_event="x1"), [], "nothing sent from a test copy")


if __name__ == "__main__":
    unittest.main()
