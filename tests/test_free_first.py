"""LynkOmni's own messages and sign-in codes use the free ways first; a text only where it is truly needed (owner, 2026-11-26)."""
import unittest

from core import ways_in as WI
from services import messages as M

NOON = 1_800_000_000 + 12 * 3600


class FreeFirst(unittest.TestCase):
    def test_lynkomnis_own_alert_goes_by_free_channels_only(self):
        n = M.Notifier()
        r = n.notify("new_sign_in", "p1", "e1", NOON)
        self.assertNotIn("text", r["channels"])
        self.assertTrue({"push", "email"} & set(r["channels"]))
        r = n.notify("recovery_started", "p2", "e2", NOON)
        self.assertNotIn("text", r["channels"], "even a critical alert does not text when a free channel delivered it")
        n.used("p3", "text", NOON)
        r = n.notify("new_sign_in", "p3", "e3", NOON + 1)
        self.assertNotIn("text", r["channels"], "having used texts before does not make LynkOmni pay for one")

    def test_lynkomni_never_texts_and_reports_when_nobody_was_reached(self):
        n = M.Notifier()
        r = n.notify("payout_change_requested", "p1", "e1", NOON, contacts=("bell", "text"))
        self.assertNotIn("text", r["channels"])
        self.assertFalse(r["reached"], "a payout change nobody was reached about is held, never texted")
        r = n.notify("payout_change_requested", "p2", "e2", NOON)
        self.assertTrue(r["reached"])
        n = M.Notifier(M.SandboxSender(fail={"push", "email"}))
        r = n.notify("trip_plan_overdue", "t1", "e3", NOON)
        self.assertNotIn("text", r["channels"])

    def test_a_security_alert_repeats_free_until_read(self):
        n = M.Notifier()
        r = n.notify("new_sign_in", "p1", "e1", NOON)
        self.assertIn(("repeated", r["nid"]), n.tick(NOON + M.REPEAT_S))
        n.lines[r["nid"]]["read"] = True
        self.assertNotIn(("repeated", r["nid"]), n.tick(NOON + 3 * M.REPEAT_S))
        self.assertFalse([x for x in n.sender.sent if x[0] in ("text", "call")])

    def test_a_business_message_is_the_business_s_own_choice_and_bill(self):
        n = M.Notifier()
        r = n.notify("protection_alert", "p1", "e1", NOON, business="biz1", contacts=("bell", "text"))
        self.assertIn("text", r["channels"])

    def test_a_text_code_is_offered_only_when_no_free_way_exists(self):
        self.assertNotIn("text_code", WI.sign_in_ways({"email_code", "text_code"}))
        self.assertNotIn("text_code", WI.sign_in_ways({"passkey", "text_code"}))
        self.assertEqual(WI.sign_in_ways({"text_code"}), ["text_code"])
        ff = WI.W["free_first"]
        self.assertEqual(set(ff["text_only_when"]), {"confirm_number", "recovery_email_and_phone"})
        self.assertNotIn("text_code", ff["free_ways"])
