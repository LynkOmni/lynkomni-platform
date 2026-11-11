import os, re, sqlite3, threading, unittest
import pathlib
from core import ids, naming
from core.capability import Capabilities
from core.ids import IdAllocator, fmt, luhn_digit, parse
from services.privacy import PiiVault, assert_no_pii, check_claim

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class TestIds(unittest.TestCase):
    def setUp(self): self.a = IdAllocator(sqlite3.connect(":memory:", check_same_thread=False))
    def test_registry_and_format(self):
        self.assertEqual(len(ids.TYPES), 48); self.assertIn("SRV", ids.TYPES); self.assertIn("ATT", ids.TYPES); self.assertIn("DEV", ids.TYPES); self.assertIn("LST", ids.TYPES); self.assertIn("AST", ids.TYPES); self.assertIn("TRP", ids.TYPES); self.assertIn("SNT", ids.TYPES); self.assertIn("CST", ids.TYPES)
        p11 = "48271936504"; pid = fmt("ID", p11 + luhn_digit(p11)); self.assertEqual(parse(pid), ("ID", p11 + luhn_digit(p11)))
        self.assertTrue(re.match(r"^LOID-\d{4}-\d{4}-\d{4}$", pid))
    def test_rejects_typos_and_unknown_types(self):
        pid = self.a.assign("ORD", "sale-1"); bad = pid[:-1] + str((int(pid[-1]) + 1) % 10)
        with self.assertRaises(ValueError): parse(bad)                          # one wrong digit is caught
        for junk in ("LOZZ-1234-5678-9012", "ID-1234-5678-9012", "LOID-1234-5678", "", None): 
            with self.assertRaises(ValueError): parse(junk)
    def test_idempotent_random_and_unique(self):
        a1, a2 = self.a.assign("RCP", "r1"), self.a.assign("RCP", "r1"); self.assertEqual(a1, a2)
        many = {self.a.assign("TXN", f"t{i}") for i in range(300)}; self.assertEqual(len(many), 300)
        nums = sorted(int("".join(re.findall(r"\d+", p))) for p in many); self.assertFalse(all(b - a == 1 for a, b in zip(nums, nums[1:])))   # not sequential
    def test_concurrent_allocation_is_safe(self):
        out, errs = [], []
        def work(i):
            try: out.append(self.a.assign("ORD", f"o{i % 40}"))             # many threads, 40 distinct records
            except Exception as e: errs.append(e)
        ts = [threading.Thread(target=work, args=(i,)) for i in range(200)]; [t.start() for t in ts]; [t.join() for t in ts]
        self.assertEqual(errs, []); self.assertEqual(len(set(out)), 40)
    def test_leased_blocks_for_offline_and_never_reused(self):
        block = self.a.lease("RCP", "dev-1", 5); self.a.claim(block[0], "receipt-9", "dev-1")
        self.assertEqual(self.a.lookup(block[0])["internal_id"], "receipt-9")
        with self.assertRaises(PermissionError): self.a.claim(block[1], "x", "dev-2")                 # another device cannot use it
        self.assertEqual(self.a.release("dev-1"), 4); self.assertEqual(self.a.lookup(block[1])["status"], "retired")
        with self.assertRaises(PermissionError): self.a.claim(block[1], "x", "dev-1")                 # retired for good
        self.a.retire(block[0]); self.assertEqual(self.a.lookup(block[0])["status"], "retired"); self.assertEqual(self.a.assign("RCP", "receipt-9"), block[0])
    def test_vectors_file_matches(self):
        import json; v = json.loads(pathlib.Path(os.path.join(ROOT, "contract", "vectors", "identifiers.v1.json")).read_text())
        for c in v["valid"]: self.assertEqual(parse(c["id"])[1], c["payload"]); self.assertEqual(luhn_digit(c["payload"][:11]), c["payload"][11])
        for c in v["invalid"]:
            with self.assertRaises(ValueError): parse(c["id"])

class TestCapabilities(unittest.TestCase):
    def setUp(self): self.c = Capabilities(sqlite3.connect(":memory:"))
    def test_narrow_expiring_single_use(self):
        t = self.c.issue("pay_link", "LOINV-0000-0000-0000", "pay", ttl=60, now=1000)
        with self.assertRaises(PermissionError): self.c.verify(t, "pay_link", "read", now=1001)            # wrong action: never read access
        with self.assertRaises(PermissionError): self.c.verify(t, "ticket_entry", "pay", now=1001)
        self.assertEqual(self.c.verify(t, "pay_link", "pay", now=1001)["action"], "pay")
        with self.assertRaises(PermissionError): self.c.verify(t, "pay_link", "pay", now=1002)             # single use
        with self.assertRaises(PermissionError): self.c.verify(self.c.issue("pay_link", "x", "pay", ttl=10, now=1000), "pay_link", "pay", now=2000)
        with self.assertRaises(PermissionError): self.c.verify(t[:-2] + "zz", "pay_link", "pay", now=1001)
    def test_ticket_codes_rotate(self):
        code = self.c.ticket_code("LOTKT-1111-1111-1118", now=100)
        self.assertNotEqual(code, self.c.ticket_code("LOTKT-1111-1111-1118", now=100 + 60))              # a screenshot goes stale
        with self.assertRaises(PermissionError): self.c.redeem_ticket(code, now=100 + 120)
        self.assertEqual(self.c.redeem_ticket(code, now=105), "LOTKT-1111-1111-1118")
        with self.assertRaises(PermissionError): self.c.redeem_ticket(code, now=106)                      # one entry per ticket

class TestPrivacyAndNames(unittest.TestCase):
    def test_vault_deletion_keeps_events_intact(self):
        v = PiiVault(sqlite3.connect(":memory:")); payload = v.scrub("cust-1", {"customer_name": "Amina", "phone": "+250788000000", "total": 100})
        self.assertTrue(payload["customer_name"].startswith("pii_")); self.assertEqual(payload["total"], 100)
        self.assertEqual(v.get(payload["customer_name"]), "Amina"); self.assertEqual(v.delete_subject("cust-1"), 2); self.assertIsNone(v.get(payload["customer_name"]))
    def test_device_events_carry_no_personal_data(self):
        from dv.box import LynkDVBox; from contract.tools.validate_contract import uuid4
        d = LynkDVBox(uuid4(), uuid4(), uuid4(), uuid4(), "owner"); p = d.create_product("Juice", 1500); d.receive_stock([(p, 1000)]); d.record_sale([(p, 500, 0)])
        for e in d.log: assert_no_pii(e)
        with self.assertRaises(ValueError): assert_no_pii({"payload": {"customer_note": "call me"}})
        with self.assertRaises(ValueError): assert_no_pii({"payload": {"x": "reach me on +250 788 000 000"}})
    def test_no_false_encryption_claims(self):
        with self.assertRaises(ValueError): check_claim("business_chat", "Your messages are end-to-end encrypted")
        self.assertIn("encrypted", check_claim("business_chat", "Messages are encrypted in transit and at rest"))
    def test_names_corrected_everywhere(self):
        self.assertEqual(naming.SERVICES["doc"][2], "doc.lynkomni.com"); self.assertEqual(naming.SERVICES["support"][2], "lynkomni.com/support")
        self.assertEqual(naming.SERVICES["ai"][1], "LynkAssist"); self.assertIsNone(naming.SERVICES["flow"][2])
        self.assertEqual(naming.ALIASES["LynkOmni Assistant"], naming.ALIASES["LynkOmni AI"])
        bad = []
        for base, _, files in os.walk(ROOT):
            if "__pycache__" in base or os.sep + "vectors" in base: continue
            for f in files:
                if not f.endswith((".py", ".md", ".json", ".ts", ".sql", ".yml", ".rs", ".kt", ".swift")) or f in ("naming.py", "test_foundations.py", "ci.yml", "footer.test.ts"): continue
                with open(os.path.join(base, f), encoding="utf-8") as fh: text = fh.read()
                bad += [(f, b) for b in naming.BANNED if b in text]
        self.assertEqual(bad, [])

if __name__ == "__main__":
    unittest.main()


class TestPiiCheckIgnoresRecordIds(unittest.TestCase):
    def test_an_all_digit_uuid_part_is_not_a_phone_number(self):
        from services.privacy import contains_pii
        self.assertFalse(contains_pii("0190a1b2-c3d4-7e5f-8a9b-123456789012"))
        self.assertTrue(contains_pii("call me on +250 788 123 456"))
        self.assertTrue(contains_pii("0788123456"))
