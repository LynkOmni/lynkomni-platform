"""LynkAssist's trust layer (ASSIST UPDATE, master blueprint 75; build section 4 step C3a): catalog/assist-trust.v1.json read
through core/assist_trust.py and ts/src/assisttrust.ts with shared vectors. Content is never obeyed; figures are worked out
exactly or not shown; memory never keeps a secret and never mixes; every change has a preview, the owner's limits only lower,
big changes need a second person, the pause switch stops every action; warnings are never shown inside a payment; a release,
a language or a new skill passes its bar or waits."""
import json, os, subprocess, sys, unittest
from core import assist_trust as A
from core import build_sections as b

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class AssistTrust(unittest.TestCase):
    def test_vectors_and_the_typescript_register_are_current(self):
        r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "assist_trust_vectors.py"), "--check"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_it_says_how_sure_it_is_and_never_invents(self):
        self.assertEqual(A.certainty(0), "dont_know")
        self.assertEqual(A.certainty(3, unconfirmed=True), "not_sure", "an unconfirmed country rule is said")
        self.assertEqual(A.certainty(3, estimate=True), "likely")
        self.assertEqual(A.certainty(3, checked=False), "not_sure", "never certain without the second check")
        self.assertEqual(A.certainty(3), "certain")

    def test_figures_are_worked_out_exactly_or_not_shown(self):
        self.assertEqual(A.work([{"minor": 1500, "currency": "USD"}, {"minor": 250, "currency": "USD"}])["total"], 1750)
        for bad in ([{"minor": 10.5, "currency": "USD"}], [{"minor": 1, "currency": "USD"}, {"minor": 1, "currency": "EUR"}], []):
            self.assertFalse(A.work(bad)["ok"], bad)
        self.assertTrue(A.needs_not_adviser("tax")); self.assertFalse(A.needs_not_adviser("orders"))

    def test_text_it_reads_is_never_obeyed(self):
        for src in A.TRUST["content"]["content_sources"]:
            self.assertEqual(A.guard("none", True, "A", source=src)["outcome"], "content_not_instructions", src)
        self.assertEqual(A.guard("none", True, "A", source="person")["outcome"], "run")
        self.assertEqual(A.TRUST["content"]["instruction_sources"], ["person"])

    def test_memory_never_keeps_a_secret_and_never_mixes(self):
        self.assertTrue(A.remember("remember_that", "business", "Our supplier delivers on Tuesdays", "business")["keep"])
        self.assertEqual(A.remember("remember_that", "business", "card 4111 1111 1111 1111", "business")["why"], "never_secrets")
        self.assertEqual(A.remember("remember_that", "person", "x", "business")["why"], "kept_apart")
        self.assertEqual(A.remember("preference", "person", "short answers", "person", memory_on=False)["why"], "memory_off")
        self.assertEqual(A.remember("remember_that", "person", "x", "person", sensitive=["health"])["why"], "sensitive_not_asked")
        items = [{"id": "o", "scope": "business", "role_min": "owner"}, {"id": "c", "scope": "business", "role_min": "cashier"}]
        self.assertEqual(A.recall(items, "business", "cashier"), ["c"], "a staff member's assistant never learns what only the owner may see")
        self.assertIn("never in the event log", A.TRUST["memory"]["rule"])

    def test_every_change_is_previewed_limited_and_big_ones_need_a_second_person(self):
        self.assertEqual(A.guard("confirm", False, "B")["outcome"], "preview")
        self.assertEqual(A.guard("confirm", False, "B", confirmed=True)["outcome"], "run")
        g = A.guard("confirm", False, "B", confirmed=True, items=240, asker="u1")
        self.assertEqual((g["outcome"], g["sample"], g["show_all"]), ("second_approver", 5, False))
        self.assertEqual(A.guard("confirm", False, "B", confirmed=True, items=240, asker="u1", approver="u1", approver_role="owner")["outcome"], "second_approver",
                         "the person asking can never be the second approver")
        self.assertEqual(A.guard("confirm", False, "B", confirmed=True, items=240, asker="u1", approver="u2", approver_role="manager")["outcome"], "run")
        self.assertEqual(A.effective_limit(50, 500), 50, "the owner's limit can only lower the register's")
        self.assertEqual(A.guard("none", True, "A", paused=True)["outcome"], "paused")
        self.assertEqual(A.guard("none", True, "A", practice=True)["outcome"], "practice")
        self.assertEqual(A.guard("hand_over", False, "D", confirmed=True)["outcome"], "register", "the register's own refusals still stand")
        self.assertTrue(A.plan_move("running", "paused")); self.assertFalse(A.plan_move("done", "running"))

    def test_warnings_are_never_inside_a_payment_and_keep_the_pace(self):
        self.assertTrue(A.warning("price_below_cost")["show"])
        self.assertFalse(A.warning("price_below_cost", screen="payment")["show"])
        self.assertFalse(A.warning("price_below_cost", shown_today=2, pace="less")["show"])
        self.assertFalse(A.warning("price_below_cost", fine=True)["show"], "It is fine is respected")
        order = [str(n) for n in b.ORDER]
        for k, c in A.TRUST["warnings"]["checks"].items():
            self.assertIn(c["build_section"], order, k); self.assertTrue(c["words"].startswith("at_"), k)

    def test_quality_gates_block_a_worse_release_a_weak_language_and_an_unproven_skill(self):
        self.assertFalse(A.gate({"wrong": 100}, {"wrong": 250})["pass"])
        self.assertTrue(A.gate({"solved_alone": 7000}, {"solved_alone": 6950})["pass"])
        self.assertFalse(A.language_ready(199, 9000, 0))
        self.assertEqual(A.skill_level(10, 10000, 0), "suggest", "a new skill starts as suggestions only")


if __name__ == "__main__":
    unittest.main()
