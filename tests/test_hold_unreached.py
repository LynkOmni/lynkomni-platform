"""Held, never texted (owner, 2026-11-26): when no free channel delivered the alert about a payout or contact change, the change
waits until the person opens the alert or confirms on a device they used before; the checkup makes sure a free way reaches them."""
import os, unittest

from identity.account import PAYOUT_WAIT_S
from services import messages as M
from services.platform import Platform
from tests._signup import confirm_contacts

T0, DAY = 1_800_000_000, 86400


class HoldNotText(unittest.TestCase):
    def setUp(self):
        os.environ.pop("LYNK_MODE", None); self.p = Platform(); self.a = self.p.account
        s = self.a.begin_sign_up("grace.k", "en", T0, adult_confirmed=True); self.me = s["person"]
        confirm_contacts(self.a, self.me, T0)
        self.a.finish_sign_up(self.me, "pk-grace", "phone", "pii_p", "pii_e", now=T0)
        self.org = self.p.idp.register_org(self.me, "Mama Shop", country="XX")["internal"]

    def test_a_payout_change_nobody_was_reached_about_waits_until_read(self):
        r = self.a.request_payout_change(self.me, self.org, now=T0)
        sent = M.Notifier().notify("payout_change_requested", self.me, "e1", T0, contacts=("bell", "text"))
        self.assertNotIn("text", sent["channels"]); self.assertFalse(sent["reached"])
        self.assertTrue(self.a.hold_unreached(self.me, "payout_change", r["id"], T0))
        with self.assertRaises(PermissionError, msg="held after its own wait, never applied silently"):
            self.a.apply_payout_change(self.me, r["id"], T0 + PAYOUT_WAIT_S + 1)
        with self.assertRaises(PermissionError): self.a.reached(self.me, r["id"], "known_device", T0, device="stranger")
        self.assertTrue(self.a.reached(self.me, r["id"], "read", T0 + PAYOUT_WAIT_S + 60))
        self.a.apply_payout_change(self.me, r["id"], T0 + PAYOUT_WAIT_S + 61)
        types = [e["type"] for e in self.p.c.store.since(self.me)]
        self.assertIn("ChangeHeldUntilReached", types); self.assertIn("ChangeHoldCleared", types)

    def test_a_known_device_clears_a_held_contact_change(self):
        self.a.ways.signed_in(self.me, "my-phone", "XX", True, T0)
        r = self.a.protect.request_contact_change(self.me, "email", "pii_new", fresh_check=True, now=T0)
        self.a.hold_unreached(self.me, "contact_change", r["change_id"], T0)
        self.assertEqual(self.a.protect.apply_contact_changes(T0 + 30 * DAY), [])
        self.assertTrue(self.a.reached(self.me, r["change_id"], "known_device", T0 + 30 * DAY, device="my-phone"))
        self.assertEqual(self.a.protect.apply_contact_changes(T0 + 30 * DAY + 1), [r["change_id"]])
        with self.assertRaises(ValueError): self.a.hold_unreached(self.me, "recovery", "rid-1", T0)

    def test_the_checkup_asks_for_a_working_way_to_reach_you(self):
        self.assertNotIn("reachable", self.a.ways.checkup(self.me, T0))
        self.a.ways.email_bounced(self.me, T0)
        self.assertIn("reachable", self.a.ways.checkup(self.me, T0), "email bouncing and no app signed in")
        self.assertEqual(self.a.ways.checkup(self.me, T0)[0], "reachable", "it comes first")
        self.a.ways.signed_in(self.me, "my-phone", "XX", True, T0)
        self.assertNotIn("reachable", self.a.ways.checkup(self.me, T0), "the app reaches them for free")
