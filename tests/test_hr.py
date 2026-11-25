"""LynkHR's rules (SIX SERVICES UPDATE, master blueprint 69.3 and 69.12; build section 4B): catalog/hr.v1.json read through core/hr.py
and ts/src/hr.ts with shared vectors. LynkAssist never decides about a person; special details only where the law allows; the
person always sees their own record; nobody approves their own leave or pay; volunteers and contractors are never on payroll."""
import json, os, subprocess, sys, unittest

from core import hr as H

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Hr(unittest.TestCase):
    def test_vectors_and_the_typescript_register_are_current(self):
        r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "hr_vectors.py"), "--check"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_lynkassist_never_decides_about_a_person(self):
        for a in ("hire", "reject", "set_pay", "promote", "discipline", "dismiss", "score_person"):
            self.assertIn(a, H.HR["assist"]["never"])
            self.assertFalse(H.assist_may(a), a)
        self.assertFalse(set(H.HR["assist"]["may"]) & set(H.HR["assist"]["never"]))

    def test_special_details_need_the_country_pack(self):
        for k in H.HR["fields"]["special"]:
            self.assertFalse(H.special_allowed(k, None), k)
            self.assertNotIn(k, H.visible_fields("owner"), "the owner never sees health, family or union details")
            self.assertNotIn(k, H.visible_fields("staff", is_self=True))

    def test_the_person_sees_their_own_record_but_not_case_notes(self):
        own = H.visible_fields("staff", is_self=True)
        for f in ("salary", "bank_ref", "pay_grade"):
            self.assertIn(f, own)
            self.assertNotIn(f, H.visible_fields("staff"))
        self.assertNotIn("case_notes", own)

    def test_nobody_approves_their_own(self):
        self.assertFalse(H.may_approve("u1", "u1"))
        self.assertFalse(H.pay_change_ok("u1", "u2", 300, 200, "u2"), "over budget needs a third person")
        self.assertTrue(H.pay_change_ok("u1", "u2", 300, 200, "u3"))

    def test_only_payroll_workers_reach_lynkacc_and_money_is_whole(self):
        figs = H.payroll_figures([{"id": "v", "kind": "volunteer", "salary": 5}, {"id": "c", "kind": "contractor", "salary": 5},
                                  {"id": "p", "kind": "permanent", "salary": 100, "week_minutes": 2401, "hourly_minor": 1999}])
        self.assertEqual([f["id"] for f in figs], ["p"])
        self.assertTrue(all(isinstance(v, int) for f in figs for v in f.values() if v != f["id"]))

    def test_leave_minimum_is_never_invented(self):
        self.assertIsNone(H.leave_minimum("annual", None))
        self.assertTrue(all(v in (0, None) for v in H.HR["leave"]["default_half_days"].values()))

    def test_anonymous_reviews_show_from_three(self):
        self.assertFalse(H.review_shown("peer", 2))
        self.assertTrue(H.review_shown("peer", 3))

    def test_cases_are_restricted(self):
        self.assertFalse(H.case_may_see("manager"))
        self.assertFalse(H.case_may_see("owner"))
        self.assertTrue(H.case_may_see("owner", named=True))

    def test_every_worker_kind_and_tier_feature_is_sound(self):
        self.assertEqual(set(H.HR["on_payroll"]) - set(H.HR["workers"]), set())
        feats = [f for t in H.HR["tiers"].values() for f in t]
        self.assertEqual(len(feats), len(set(feats)), "each feature belongs to one tier")

    def test_billing_features_agree_with_the_register(self):
        from services import billing
        tiers = ["free", "plus", "pro", "max"]
        for i, t in enumerate(tiers):
            ent = {}
            for d in billing.FEATURES["lynkhr"][: i + 1]:
                ent.update(d)
            for f in (x for tt in H.HR["tiers"].values() for x in tt):
                self.assertEqual(ent.get(f), H.tier_has(t, f), (t, f))


if __name__ == "__main__":
    unittest.main()
