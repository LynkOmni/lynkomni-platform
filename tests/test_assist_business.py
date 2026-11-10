"""LynkAssist in the Business app and on devices (MASTER UPDATE section 54; build section 3): the selling, shift, cash, stock
and device actions, offline layer 2 with queued and sealed actions, the owner's controls, standing permissions and Ask the owner."""
import unittest
from services import assist_register as AR
from services.assist_business import BusinessAssist, Books, QUEUE_EXPIRES_S, offline_of
from services.messages import Notifier
from services.sealing import generate_keypair, unseal

T0 = 1_800_000_000


class Business(unittest.TestCase):
    def setUp(self):
        self.ev = []
        self.n = Notifier()
        self.priv, pub = generate_keypair()
        b = Books(); b.prices["rice"] = 1500; b.stock["rice"] = 24000; b.sales["s1"] = "paid"; b.holds["h1"] = "rice"; b.devices["d2"] = "enrolled"
        self.x = BusinessAssist("biz-1", "owner-1", books=b, emit=lambda t, p: self.ev.append(t), notifier=self.n, cloud_public=pub)

    def test_every_action_says_what_it_does_offline(self):
        for a in AR.REG["actions"]:
            self.assertIn(a.get("offline"), ("device", "queue", "cloud_check", "never"), a["id"])
            if a["class"] == "D":
                self.assertEqual(a["offline"], "never", a["id"])
            if a["class"] == "C":
                self.assertEqual(a["offline"], "cloud_check", a["id"])

    def test_class_b_needs_confirm_and_can_be_undone(self):
        r = self.x.do("d1", "mgr-1", "manager", "correct_price", product="rice", price_minor=1400, now=T0)
        self.assertEqual(r["needs"], "confirm")
        r = self.x.do("d1", "mgr-1", "manager", "correct_price", confirmed=True, product="rice", price_minor=1400, now=T0)
        self.assertEqual(r["state"], "done"); self.assertEqual(self.x.books.prices["rice"], 1400)
        self.assertTrue(self.x.undo(r["entry"], now=T0 + 5)); self.assertEqual(self.x.books.prices["rice"], 1500)

    def test_offline_device_fixes_run_and_cloud_actions_queue_sealed(self):
        r = self.x.do("d1", "c1", "cashier", "recount_cash", online=False, now=T0)
        self.assertEqual(r["state"], "done", "a device-only fix is done at once")
        r = self.x.do("d1", "mgr-1", "manager", "correct_stock_quantity", confirmed=True, online=False, product="rice", qty_milli=20000, now=T0)
        self.assertEqual(r["state"], "queued", "never shown as done before the cloud carries it out")
        self.assertEqual(self.x.books.stock["rice"], 24000)
        self.assertIn(b"correct_stock_quantity", unseal(self.x.queue[0]["sealed"], self.priv), "sealed for the cloud only")
        self.assertEqual(self.x.settle("d1", now=T0 + 60), [("correct_stock_quantity", "done")])
        self.assertEqual(self.x.books.stock["rice"], 20000)
        self.assertEqual(self.n.bell("mgr-1", now=T0)["new"][0]["kind"], "assist_fix_done", "the person is told")

    def test_queued_actions_expire_or_ask_on_a_conflict(self):
        self.x.do("d1", "mgr-1", "manager", "correct_price", confirmed=True, online=False, product="rice", price_minor=1300, now=T0)
        self.x.do("d1", "mgr-1", "manager", "release_stale_hold", confirmed=True, online=False, hold="h1", now=T0)
        out = self.x.settle("d1", now=T0 + 10, changed_since={"rice"})
        self.assertEqual(out, [("correct_price", "conflict"), ("release_stale_hold", "done")])
        self.x.do("d1", "mgr-1", "manager", "correct_price", confirmed=True, online=False, product="rice", price_minor=1300, now=T0)
        self.assertEqual(self.x.settle("d1", now=T0 + QUEUE_EXPIRES_S + 1), [("correct_price", "expired")])

    def test_offline_never_offers_partner_work_and_identity_checks_wait(self):
        self.assertEqual(self.x.decide("refund_payment", "owner", confirmed=True, online=False)["needs"], "prepare_for_later")
        self.assertEqual(self.x.decide("wipe_lost_device", "owner", confirmed=True, fresh_check=True, online=False)["needs"], "wait_for_network")
        self.assertEqual(self.x.decide("refund_payment", "owner", confirmed=True)["needs"], "hand_over")

    def test_owner_controls_switches_and_standing_permissions(self):
        with self.assertRaises(PermissionError):
            self.x.switch("manager", "stock", False, "mgr-1")
        self.x.switch("owner", "stock", False, "owner-1")
        self.assertEqual(self.x.decide("correct_price", "manager", confirmed=True)["needs"], "refused")
        self.x.switch("owner", "stock", True, "owner-1")
        with self.assertRaises(ValueError):
            self.x.set_standing("owner", "wipe_lost_device", True)
        self.x.set_standing("owner", "correct_price", True, per_day=2, by="owner-1")
        self.assertTrue(self.x.decide("correct_price", "manager")["run"], "runs without asking within the owner's limits")
        self.x.done_today["correct_price"] = 2
        self.assertEqual(self.x.decide("correct_price", "manager")["needs"], "confirm", "past the owner's limit it asks again")
        self.assertIn("StandingPermissionSet", self.ev)

    def test_ask_the_owner_one_tap(self):
        self.x.ask_owner_first("owner", "void_sale_within_rules")
        r = self.x.do("d1", "mgr-1", "manager", "void_sale_within_rules", confirmed=True, sale="s1", now=T0)
        self.assertEqual(r["state"], "asked_owner")
        rid = self.x.history[0]["request"]
        line = self.n.bell("owner-1", now=T0)["new"][0]
        self.assertEqual((line["kind"], [a for a in AR.REG["actions"] if a["id"] == "void_sale_within_rules"][0]["class"]), ("staff_request", "B"))
        with self.assertRaises(PermissionError):
            self.x.owner_answer(rid, "approve", "mgr-1", "manager")
        self.x.owner_answer(rid, "approve", "owner-1", "owner", args={"sale": "s1"}, now=T0 + 30)
        self.assertEqual(self.x.books.sales["s1"], "voided")
        self.assertEqual(self.x.owner_answer(rid, "deny", "owner-1", "owner"), "approve", "answered once")
        self.assertEqual([e for e in self.ev if e.startswith("Owner")], ["OwnerAsked", "OwnerAnswered"])

    def test_everything_lynkassist_did_includes_what_did_not_run(self):
        self.x.do("d1", "c1", "cashier", "correct_price", confirmed=True, product="rice", price_minor=1)
        self.x.do("d1", "c1", "cashier", "reprint_receipt")
        h = self.x.everything_done()
        self.assertEqual([(e["action"], e["state"]) for e in h], [("reprint_receipt", "done"), ("correct_price", "not_done")])
        self.assertNotIn("undo", h[0])


if __name__ == "__main__":
    unittest.main()
