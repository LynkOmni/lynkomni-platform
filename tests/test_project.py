"""LynkProject's rules (SIX SERVICES UPDATE, master blueprint 69.4 and 69.12; build section 4B): catalog/project.v1.json read through
core/project.py and ts/src/project.ts with shared vectors. Tasks never wait in a circle; a task is done only when what it waits on
is done; nobody approves their own time; billable time is billed once; a guest sees only their project and never money; field
time and place only for staff on shift who agreed; LynkAssist never changes anything without a person's Confirm."""
import os, subprocess, sys, unittest

from core import project as P

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Project(unittest.TestCase):
    def test_vectors_and_the_typescript_register_are_current(self):
        r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "project_vectors.py"), "--check"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_never_a_circle(self):
        deps = {"a": [], "b": ["a"], "c": ["b"]}
        self.assertFalse(P.wait_ok(deps, "a", "c"))
        self.assertFalse(P.wait_ok(deps, "a", "a"))
        self.assertTrue(P.wait_ok(deps, "c", "a"))

    def test_done_only_when_what_it_waits_on_is_done(self):
        tasks = [{"id": "a", "state": "doing"}, {"id": "b", "state": "doing", "waits_on": ["a"]}]
        self.assertFalse(P.done_ok(tasks[1], tasks))
        tasks[0]["state"] = "done"
        self.assertTrue(P.done_ok(tasks[1], tasks))

    def test_time_is_approved_by_someone_else_and_billed_once(self):
        self.assertFalse(P.time_approve_ok("u1", "u1"))
        b = P.billable([{"id": "x", "minutes": 60, "rate": 100, "approved": True, "billable": True, "billed": True}])
        self.assertEqual(b, {"ids": [], "minutes": 0, "amount": 0})
        self.assertIsInstance(P.billable([{"id": "y", "minutes": 7, "rate": 12345, "approved": True, "billable": True}])["amount"], int)

    def test_guests_never_see_money(self):
        for part in P.PJ["guests"]["never"]:
            self.assertFalse(P.guest_sees(part, ["p1"], "p1"), part)
        self.assertFalse(P.guest_sees("tasks", ["p2"], "p1"))

    def test_field_place_needs_shift_and_consent(self):
        self.assertFalse(P.field_place_ok(True, False))
        self.assertFalse(P.field_place_ok(False, True))

    def test_lynkassist_only_suggests(self):
        for a in P.PJ["assist"]["never"]:
            self.assertFalse(P.assist_may(a), a)

    def test_over_budget_and_overload_are_shown_never_blocked(self):
        self.assertEqual(P.money(100, [150], 0)["over"], 50)
        self.assertEqual(P.workload({"u": 3000})["u"]["over"], 600)

    def test_each_feature_belongs_to_one_tier(self):
        feats = [f for t in P.PJ["tiers"].values() for f in t]
        self.assertEqual(len(feats), len(set(feats)))

    def test_billing_features_agree_with_the_register(self):
        from services import billing
        tiers = ["free", "plus", "pro", "max"]
        for i, t in enumerate(tiers):
            ent = {}
            for d in billing.FEATURES["lynkproject"][: i + 1]:
                ent.update(d)
            for f in (x for tt in P.PJ["tiers"].values() for x in tt):
                self.assertEqual(ent.get(f), P.tier_has(t, f), (t, f))


if __name__ == "__main__":
    unittest.main()
