"""LynkAssist across services (CONNECT UPDATE 71.6; section 4 row 71.9 step 3): a question across services, a plan of several
steps, the morning brief, saved questions and the usage meter (services/assist_connect.py, catalog/assist.v1.json)."""
import os, time, unittest
os.environ["LYNK_MODE"] = "sandbox"
from services import assist_register as AR
from services.assist_connect import ConnectAssist, QUESTION_ACTIONS, KINDS, GOALS

LINES = [{"qty_milli": 1000, "unit_minor": 1000}]
def item(sku, qty, price): return {"sku": sku, "qty": qty, "price_minor": price}


class Connect(unittest.TestCase):
    def setUp(self):
        os.environ["LYNK_MODE"] = "sandbox"
        from services.platform import Platform
        self.p = Platform(); self.p.register("m1", "RW")
        for fam in ("lynkinv", "lynkcrm", "lynkacc"): self.p.billing.set_plan("m1", fam, "pro")
        self.cust = self.p.crm.create("m1", "u1", "customer", name="Amina")
        self.a = ConnectAssist(self.p, "m1", "u0", "u0")

    def test_every_skill_is_registered_and_built(self):
        for a in ("ask_across", "assist_plan", "morning_brief", "save_question", "assist_usage"):
            self.assertEqual(AR.ACTIONS[a]["status"], "built", a)
        for a in QUESTION_ACTIONS: self.assertIn(a, AR.ACTIONS, a)

    def test_a_question_across_services_names_each_source_and_hides_what_the_role_may_not_see(self):
        self.p.inventory.receive("m1", "d1", "rice", 10, 400)
        self.p.pos.record_sale("m1", "d1", [item("rice", 2, 1000)], method="cash")
        self.p.invoicing.issue("m1", self.cust, LINES)
        r = self.a.do("d1", "u0", "owner", "ask_across", kind="week")["result"]
        self.assertEqual((r["parts"]["sales"]["total_minor"], r["parts"]["sales"]["source"]), (2000, "lynkpos"))
        self.assertEqual(r["parts"]["owed"]["count"], 1); self.assertEqual(r["hidden"], [])
        acc = self.a.do("d1", "u5", "accountant", "ask_across", kind="week")["result"]
        self.assertIn("sales", acc["hidden"], "an accountant's role does not see the till")
        self.assertNotIn("sales", acc["parts"])
        with self.assertRaises(ValueError): self.a._run("ask_across", {"kind": "everything"})

    def test_a_plan_is_a_draft_whose_steps_each_need_their_own_confirm(self):
        inv = self.p.invoicing.issue("m1", self.cust, LINES)
        self.p.invoicing.inv[inv["id"]]["due_at"] = time.time() - 86400
        r = self.a.do("d1", "u0", "owner", "assist_plan", confirmed=True, goal="chase_overdue")
        self.assertEqual(r["state"], "done")
        self.assertEqual((r["result"]["state"], r["result"]["acted"]), ("draft", False))
        self.assertTrue(r["result"]["steps"]) ; self.assertTrue(all(s["confirm"] for s in r["result"]["steps"]))
        self.assertEqual(self.a.do("d1", "u0", "owner", "assist_plan", goal="month_end")["state"], "not_done", "a plan starts only after Confirm")

    def test_the_morning_brief_goes_only_to_who_asked_and_never_says_nothing(self):
        self.assertIsNone(self.a.run_morning_brief("u0", "owner", opted_in=False))
        self.assertIsNone(self.a.run_morning_brief("u0", "owner", opted_in=True), "nothing to say: nothing sent")
        self.p.inventory.receive("m1", "d1", "rice", 10, 400)
        self.p.pos.record_sale("m1", "d1", [item("rice", 1, 1000)], method="cash")
        b = self.a.run_morning_brief("u0", "owner", opted_in=True)
        self.assertEqual(b["parts"]["sales"]["count"], 1)

    def test_saved_questions_and_the_usage_meter(self):
        self.p.billing.set_plan("m1", "lynkassist", "free")
        limit = self.a.question_limit()
        self.assertEqual(self.a.do("d1", "u0", "owner", "save_question", kind="owed", every="daily")["result"]["saved"], "q1")
        self.assertEqual(self.a.run_saved_questions("u0", "owner", weekday=3), ["q1"])
        self.assertEqual(self.a.run_saved_questions("u9", "owner", weekday=3), [], "only the person who saved it")
        for _ in range(limit): self.a.do("d1", "u0", "owner", "ask_across", kind="owed")
        u = self.a.do("d1", "u0", "owner", "assist_usage")["result"]
        self.assertEqual((u["used"], u["limit"], u["left"]), (limit, limit, 0))
        self.assertTrue(self.a.do("d1", "u0", "owner", "ask_across", kind="owed")["result"]["over_limit"])
        self.p.billing.set_plan("m1", "lynkassist", "max")
        self.assertIsNone(self.a.do("d1", "u0", "owner", "assist_usage")["result"]["limit"], "Max: no limit")


class Register(unittest.TestCase):
    def test_kinds_and_goals_are_small_and_fixed(self):
        self.assertEqual(sorted(KINDS), ["due_soon", "owed", "week"]); self.assertEqual(GOALS, ("chase_overdue", "month_end"))


if __name__ == "__main__":
    unittest.main()
