import os, unittest
from core.ids import IdAllocator
from identity.auth import Identity
from identity.platform import IdentityPlatform, OFFLINE_DAYS
from services.platform import Platform, ServiceOff

class T(unittest.TestCase):
    def setUp(self):
        os.environ.pop("LYNK_MODE", None); self.p = Platform(); self.i = self.p.idp
        self.owner = self.i.register_person()["internal"]; self.org = self.i.register_org(self.owner, "Mama Shop", country="RW")["internal"]
        self.staff = self.i.register_person()["internal"]
    def tearDown(self): os.environ.pop("LYNK_MODE", None)

    def test_ids_are_permanent_and_separate(self):
        a, b = self.i.register_person(), self.i.register_org(self.owner, "X")
        self.assertTrue(a["lynkid"].startswith("LOID-") and b["lynkoid"].startswith("LOOID-"))
        self.i.close_person(a["internal"]); self.assertEqual(self.p.ids.lookup(a["lynkid"])["status"], "assigned")           # closed, never reissued
        self.assertTrue(self.i.add_branch(self.org, "Kigali").startswith("LOBRN-"))

    def test_default_deny_and_last_owner_protection(self):
        self.assertFalse(self.i.can(self.staff, self.org, "sale.record"))                                                  # not a member: no access
        self.i.add_member(self.owner, self.org, self.staff, "cashier")
        self.assertTrue(self.i.can(self.staff, self.org, "sale.record")); self.assertFalse(self.i.can(self.staff, self.org, "sale.void"))
        with self.assertRaises(PermissionError): self.i.add_member(self.staff, self.org, self.owner, "owner")             # a cashier cannot add anyone
        with self.assertRaises(PermissionError): self.i.remove_member(self.owner, self.org, self.owner)                    # last owner
        with self.assertRaises(PermissionError): self.i.change_role(self.owner, self.org, self.owner, "manager")
        with self.assertRaises(PermissionError): self.i.transfer_ownership(self.org, self.owner, self.staff)               # needs step-up and acceptance
        self.i.transfer_ownership(self.org, self.owner, self.staff, True, True); self.assertEqual(self.i.role_of(self.staff, self.org), "owner")
        other = self.i.register_org(self.i.register_person()["internal"], "Other")["internal"]; self.assertFalse(self.i.can(self.staff, other, "sale.record"))   # tenant isolation

    def test_pin_lockout_limited_sessions_and_offline_windows(self):
        self.i.enroll_pin(self.owner, "482913")
        with self.assertRaises(ValueError): self.i.enroll_pin(self.owner, "111111")
        t = self.i.sign_in_pin(self.owner, "482913", "device", now=1000); self.assertEqual(self.i.session(t, now=1001)["assurance"], "full")
        u = self.i.sign_in_pin(self.owner, "482913", "ussd", now=1000); self.assertEqual(self.i.session(u, now=1001)["assurance"], "limited")
        self.assertTrue(self.i.require(t, "transfer_ownership", 1001)); 
        with self.assertRaises(PermissionError): self.i.require(u, "transfer_ownership", 1001)                              # feature-phone sessions cannot do high-risk actions
        self.assertIsNone(self.i.session(t[:-2] + "zz", now=1001)); self.assertIsNone(self.i.session(t, now=1000 + 13 * 3600))
        self.i.revoke_sessions(self.owner, now=2000); self.assertIsNone(self.i.session(t, now=2001))
        for k in range(5):
            with self.assertRaises(PermissionError): self.i.sign_in_pin(self.owner, "000000", now=5000 + k)
        with self.assertRaises(PermissionError): self.i.sign_in_pin(self.owner, "482913", now=5010)                         # locked even with the right PIN
        self.assertEqual(OFFLINE_DAYS, {"owner": 7, "manager": 7, "cashier": 14}); self.assertTrue(self.i.offline_unlock_allowed("cashier", 14)); self.assertFalse(self.i.offline_unlock_allowed("owner", 8))

    def test_verification_is_gated_honest_and_narrow(self):
        with self.assertRaises(ServiceOff): self.i.open_case("org", self.org, "registration", "RW")                          # not active in the pilot
        os.environ["LYNK_MODE"] = "sandbox"; c = self.i.open_case("org", self.org, "registration", "RW", opener="agent1")
        self.i.submit_evidence(c, "registry_lookup", "official_registry", False, ["h1"])                                      # the source was down
        self.assertEqual(self.i.decide(c, "rev1", "verified"), "additional_evidence_required")                              # never a success
        with self.assertRaises(PermissionError): self.i.decide(c, "agent1", "rejected")                                       # reviewers cannot decide their own cases
        c2 = self.i.attest_partner("person", self.owner, "identity", "RW", "PartnerBank", "verified", expires=10 ** 12)
        self.assertTrue(self.i.is_verified(self.owner, "identity", "RW")); self.assertFalse(self.i.is_verified(self.owner, "identity", "KE"))   # not universal
        view = self.i.status_view(self.owner); self.assertEqual(set(view[0]), {"claim", "status", "expires"})                # support sees status only
        with self.assertRaises(ValueError): self.i._move(c2, "pending")                                                      # illegal transition

    def test_customer_references_and_support_grants(self):
        cust = self.i.register_person()["internal"]; m2 = self.i.register_org(self.owner, "Shop 2")["internal"]
        r1, r1b, r2 = self.i.customer_ref(self.org, cust), self.i.customer_ref(self.org, cust), self.i.customer_ref(m2, cust)
        self.assertEqual(r1, r1b); self.assertNotEqual(r1, r2); self.assertTrue(r1.startswith("LOCST-"))                    # merchants cannot link one customer across shops
        g = self.i.grant_support_access(cust, "diagnostics", 1, now=1000); self.assertTrue(g.startswith("LOCNS-"))
        self.assertTrue(self.i.support_access_ok(cust, "diagnostics", now=1500)); self.assertFalse(self.i.support_access_ok(cust, "diagnostics", now=1000 + 3601))
        self.i.revoke_grant(g); self.assertFalse(self.i.support_access_ok(cust, "diagnostics", now=1500))

    def test_site_sessions_stepup_and_layered_recovery(self):
        a = Identity(self.p.c); a.register("p1", "+250700000001", "a@x.org"); code = a.add_merchant_role("p1", "m1", backup_contact="bk1")
        a.enroll_device("p1", "m1", "dev-old", "owner", now=0); tok = a.sign_in("p1", "account", now=10)
        self.assertEqual(a.validate_session(tok, "account", now=11), "p1"); self.assertIsNone(a.validate_session(tok, "exchange", now=11))   # one site only
        with self.assertRaises(PermissionError): a.start_code_recovery("p1", "wrong", True, "dev-new", "dev-old", now=100)                     # SMS alone is never enough
        rid = a.start_code_recovery("p1", code, True, "dev-new", "dev-old", now=100)
        with self.assertRaises(PermissionError): a.complete_recovery(rid, now=100 + 3600)                                                      # 24-hour wait
        a.complete_recovery(rid, now=100 + 24 * 3600 + 1); self.assertFalse(a.device_can("dev-new", "export_data", now=200 + 24 * 3600))     # restricted for 24 hours
        self.assertTrue(a.device_can("dev-new", "export_data", now=100 + 49 * 3600)); self.assertFalse(a.device_can("dev-old", "sale", now=100 + 49 * 3600))   # lost device revoked
        with self.assertRaises(PermissionError): a.staff_recover()
        r2 = a.start_assisted("p1", "dev-new2", True, True, now=0)
        a.staff_approve(r2, "s1")
        with self.assertRaises(PermissionError): a.complete_recovery(r2, now=72 * 3600 + 1)                                                    # needs two different staff

if __name__ == "__main__":
    unittest.main()
