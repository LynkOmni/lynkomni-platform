"""Betting at an agent point (BETTING UPDATE, owner 2026-11-24, master blueprint section 86): LynkOmni is only the shop's tool,
the operator decides, betting is online only and never on credit, a ticket is paid once and only after the operator's lock,
the service stays off until a licensed operator is signed, betting is never advertised, and Python and TypeScript agree."""
import json, os, subprocess, sys, unittest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from core import betting as B
from core import regions

REG = B.REG


class Rules(unittest.TestCase):
    def test_vectors_and_the_typescript_register_are_current(self):
        r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "betting_vectors.py"), "--check"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_offline_only_a_queued_slip_and_never_a_payout(self):
        self.assertEqual(B.may_start(False, True, True), "offline")
        self.assertEqual(B.offline_slip(False, "sports", 120, 30, 100, 500, 0, 2000), "operator_off")
        self.assertEqual(B.offline_slip(True, "live", 120, 30, 100, 500, 0, 2000), "live")
        self.assertEqual(B.offline_slip(True, "sports", 120, 30, 100, 500, 0, 2000), "ok")
        self.assertEqual(B.slip_result(False, 700), {"ticket": False, "refund": 700})        # a refused slip returns the whole stake
        for action in ("payout", "refer", "cancel"):
            self.assertFalse(B.may_online_only(action, False), action)
        self.assertIn("paying a winning ticket (the operator must lock it first)", REG["online_and_offline"]["never_offline"])

    def test_both_sides_and_odds_formats(self):
        self.assertEqual(set(REG["sides"]), {"internal", "external", "operator"})
        self.assertEqual(B.odds_text(2150, "fractional"), "23/20")
        self.assertEqual(B.odds_text(1850, "american"), "-118")
        self.assertEqual(B.settlement(100, 60, 5), 35)

    def test_off_until_a_licensed_operator_is_signed(self):
        self.assertIn("betting", regions.SERVICES)
        self.assertFalse(regions.DEFAULT_FLAGS["betting"])
        self.assertEqual(B.may_start(True, False, True), "coming_soon")
        ledger = json.load(open(os.path.join(ROOT, "providers", "registry.v1.json"), encoding="utf-8"))
        item = next(i for i in ledger["items"] if "betting" in i["used_by"])
        self.assertEqual(item["when_off"]["message"], "Coming to your country soon.")

    def test_age_and_safer_betting(self):
        self.assertEqual(B.may_start(True, True, False), "age")
        self.assertEqual(B.may_start(True, True, True, True), "self_excluded")
        self.assertEqual(B.adult_age(16), 18); self.assertEqual(B.adult_age(21), 21)

    def test_never_on_credit(self):
        for m in REG["never_stake_methods"]:
            self.assertFalse(B.stake_method_ok(m), m)
        self.assertTrue(B.stake_method_ok("cash"))

    def test_money_and_odds_are_whole_numbers(self):
        with self.assertRaises(TypeError):
            B.possible_win(10.5, [2000])
        with self.assertRaises(TypeError):
            B.total_odds([2.15])
        self.assertEqual(B.possible_win(1000, [2150, 1850]), 3977)

    def test_ticket_is_paid_once_and_only_the_operators_amount(self):
        paid = {"known": True, "paid": True, "result": "won", "payable": 500, "expires": 10}
        self.assertEqual(B.check_answer(paid, 1, 1000, 1000), "already_paid")
        self.assertFalse(B.may_hand_over_cash("sent"))
        self.assertTrue(B.may_hand_over_cash("confirmed"))
        self.assertEqual(B.check_answer({"known": True, "result": "won", "payable": 5000, "expires": 10}, 1, 1000, 9000), "refer")

    def test_big_payouts_and_cancelling_need_another_persons_own_pin(self):
        self.assertEqual(B.cancel_check(True, True, False, False, 1, 5), "manager_needed")
        self.assertEqual(B.cancel_check(True, True, False, True, 1, 5), "ok")
        self.assertEqual(B.cancel_check(False, True, False, True, 1, 5), "offline")
        self.assertTrue(B.two_person_needed(500, 500)); self.assertFalse(B.two_person_needed(499, 500)); self.assertFalse(B.two_person_needed(10 ** 9, None))
        src = open(os.path.join(ROOT, "web", "emulators", "bet-counter", "app.ts"), encoding="utf-8").read()
        self.assertIn("never the person serving", src)        # the counter uses the device's manager_approves rule (identity/device_access.py)

    def test_check_order_names_every_answer(self):
        self.assertEqual(set(REG["check_order"]), set(REG["check_answers"]))

    def test_betting_is_never_advertised(self):
        ads = json.load(open(os.path.join(ROOT, "catalog", "ads.v1.json"), encoding="utf-8"))
        self.assertIn("gambling", ads["categories"]["blocked"])
        self.assertIn("agent_point", ads["never"])        # no ad of any kind on the betting counter

    def test_no_country_currency_or_operator_in_the_rules(self):
        src = open(os.path.join(ROOT, "core", "betting.py"), encoding="utf-8").read() + open(os.path.join(ROOT, "ts", "src", "betting.ts"), encoding="utf-8").read()
        for word in ("USD", "XAF", "FCFA", "EUR", "Cameroon", "Nigeria", "Kenya"):
            self.assertNotIn(word, src)

    def test_the_counter_is_registered(self):
        em = json.load(open(os.path.join(ROOT, "catalog", "emulators.v1.json"), encoding="utf-8"))
        e = next(x for x in em["emulators"] if x["id"] == "bet.counter")
        self.assertEqual(e["built_in"], "bet-counter")
        self.assertIn("LynkPOS", e["devices"])
        self.assertEqual(e["checks"]["offline"], "partner_parts_online_only")


if __name__ == "__main__":
    unittest.main()
