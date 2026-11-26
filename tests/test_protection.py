"""Account protections (MASTER UPDATE, master blueprint sections 55 and 59; build section 2)."""
import os, unittest
from identity.account import EVENTS
from identity import protection as P
from services.platform import Platform
from tests._signup import confirm_contacts

T0 = 1_800_000_000.0
DAY = P.DAY


class Protections(unittest.TestCase):
    def setUp(self):
        os.environ.pop("LYNK_MODE", None); self.p = Platform(); self.a = self.p.account; self.x = self.a.protect
        s = self.a.begin_sign_up("grace.k", "en", T0, adult_confirmed=True); self.person = s["person"]
        confirm_contacts(self.a, self.person, T0)
        self.done = self.a.finish_sign_up(self.person, "pk-1", "Grace's phone", "pii_1", "pii_2", backup_contact="bk-1", now=T0)

    def types(self):
        return [e["type"] for e in self.p.c.store.of(self.person, *EVENTS)]

    def test_two_ways_in_needs_a_second_way_and_the_recovery_code_typed_back(self):
        self.assertFalse(self.x.two_ways(self.person)["done"])
        self.assertFalse(self.x.confirm_recovery_code(self.person, "wrong-code"))
        self.assertTrue(self.x.confirm_recovery_code(self.person, self.done["recovery_code"]))
        self.x.add_second_way(self.person, "passkey", T0)
        self.assertTrue(self.x.two_ways(self.person)["done"])
        with self.assertRaises(ValueError):
            self.x.add_second_way(self.person, "sms")

    def test_a_new_device_holds_the_sensitive_acts_for_the_cool_off(self):
        self.a.sign_in(self.person, "account", "Grace's phone", "Kigali", T0)
        self.a.sign_in(self.person, "account", "Unknown laptop", "Kigali", T0 + 10)
        self.assertIn("CoolOffStarted", self.types())
        for act in P.HELD_ACTS:
            self.assertEqual(self.x.may(self.person, act, T0 + 60)["why"], "cool_off", act)
        self.assertTrue(self.x.may(self.person, "data_export", T0 + 10 + P.COOL_OFF_S + 1)["ok"])
        self.assertIn("SensitiveActHeld", self.types())

    def test_a_contact_change_is_slow_and_the_old_contact_can_cancel(self):
        self.assertEqual(self.x.request_contact_change(self.person, "email", "pii_new", fresh_check=False, now=T0)["state"], "needs_fresh_check")
        r = self.x.request_contact_change(self.person, "email", "pii_new", fresh_check=True, now=T0)
        self.assertEqual(r["state"], "waiting"); self.assertTrue(r["old_contact_told"])
        self.assertEqual(self.x.apply_contact_changes(T0 + DAY), [], "never at once")
        self.assertTrue(self.x.cancel_contact_change(self.person, r["change_id"], "old_contact", T0 + DAY))
        self.assertEqual(self.x.apply_contact_changes(T0 + 10 * DAY), [])
        r2 = self.x.request_contact_change(self.person, "phone", "pii_new2", fresh_check=True, now=T0 + 11 * DAY)
        self.assertEqual(self.x.apply_contact_changes(T0 + 11 * DAY + P.CONTACT_WAIT_S), [r2["change_id"]])
        self.assertIn("ContactChanged", self.types())
        self.assertEqual(self.x.request_contact_change(self.person, "email", "pii_x", True, T0 + 11 * DAY + P.CONTACT_WAIT_S + 60)["state"], "held", "a new contact starts a cool-off")
        with self.assertRaises(ValueError):
            self.x.cancel_contact_change(self.person, r2["change_id"], "staff")

    def test_advanced_protection_needs_two_passkeys_and_turns_off_code_sign_in(self):
        self.assertEqual(self.x.turn_on_advanced(self.person, True, T0)["state"], "needs_second_passkey")
        self.a.enroll_passkey(self.person, "pk-2", "Grace's key", T0)
        self.assertEqual(self.x.turn_on_advanced(self.person, False, T0)["state"], "needs_fresh_check")
        self.assertEqual(self.x.turn_on_advanced(self.person, True, T0)["state"], "on")
        self.assertFalse(self.x.code_sign_in_allowed(self.person))
        r = self.x.request_contact_change(self.person, "email", "pii_new", True, T0)
        self.assertEqual(r["ready_at"] - T0, P.ADVANCED_CONTACT_WAIT_S)

    def test_lock_everything_is_quick_keeps_safety_shares_running_and_unlocking_needs_a_check(self):
        self.a.sign_in(self.person, "account", "Grace's phone", "Kigali", T0)
        self.x.db.execute("insert into prot_cards values('c1',?, 'active')", (self.person,))
        self.x.db.execute("insert into prot_api values('k1',?, 'active')", (self.person,)); self.x.db.commit()
        share = self.a.safe.share(self.person, "LOID-1111-2222-3335", "live", 2, T0)
        self.assertEqual(self.x.lock_everything(self.person, "person", verified=False, now=T0)["state"], "needs_fresh_check")
        r = self.x.lock_everything(self.person, "person", verified=True, now=T0 + 5)
        self.assertEqual((r["state"], r["cards_freeze_sent"], r["keys_paused"]), ("locked", 1, 1))
        self.assertEqual(self.x.db.execute("select state from prot_cards where card_id='c1'").fetchone()[0], "freeze_sent", "never shown frozen before the issuer confirms")
        self.assertEqual(len(r["safety_shares_running"]), 1); self.assertTrue(r["ask_about_shares"])
        self.assertEqual(len(self.a.safe.shares(self.person, T0 + 6)), 1, "Arrive Safe keeps running")
        self.assertEqual(self.a.sessions(self.person), [])
        self.assertEqual(self.x.may(self.person, "payout_change", T0 + 10)["why"], "locked")
        self.assertEqual(self.x.unlock(self.person, verified=False, now=T0 + 20)["state"], "needs_fresh_check")
        self.assertEqual(self.x.unlock(self.person, verified=True, now=T0 + 20)["state"], "unlocked")
        self.assertTrue(share)

    def test_this_was_not_me_locks_and_rolls_back_the_suspicious_session(self):
        self.x.record_change(self.person, "abcd1234", "language", "restore_setting", T0)
        self.x.record_change(self.person, "abcd1234", "sent_message", None, T0)
        self.x.record_change(self.person, "zzzz9999", "theme", "restore_setting", T0)
        r = self.x.not_me(self.person, "abcd1234", T0 + 1)
        self.assertEqual(r["state"], "locked")
        self.assertEqual(r["rolled_back"], [{"what": "language", "undo": "restore_setting"}])
        self.assertEqual(r["could_not_undo"], ["sent_message"])
        self.assertIn("NotMeReported", self.types())

    def test_the_successor_stays_off_until_a_lawyer_confirms_the_country(self):
        self.assertEqual(self.x.name_successor(self.person, "LOID-1111-2222-3335", 90, "RW", True, T0)["state"], "coming_soon")

    def test_the_successor_waits_the_owner_is_told_and_the_partner_decides(self):
        self.x.successor_available = lambda country: True                  # a country whose rule a lawyer confirmed (none yet)
        with self.assertRaises(ValueError):
            self.x.name_successor(self.person, "LOID-1111-2222-3335", 5, "XX", True, T0)
        self.assertEqual(self.x.name_successor(self.person, "LOID-1111-2222-3335", 90, "XX", True, T0)["state"], "named")
        self.x.seen(self.person, T0)
        self.assertEqual(self.x.successor_request(self.person, "LOID-1111-2222-3335", T0 + 10 * DAY)["state"], "refused")
        self.assertEqual(self.x.successor_request(self.person, "LOID-9999-9999-9999", T0 + 100 * DAY)["state"], "refused")
        r = self.x.successor_request(self.person, "LOID-1111-2222-3335", T0 + 100 * DAY)
        self.assertEqual(r["state"], "waiting"); self.assertTrue(r["owner_told"])
        self.assertEqual(self.x.successor_partner_answer(self.person, "LOVER-1", True, T0 + 101 * DAY)["state"], "waiting")
        self.x.seen(self.person, T0 + 105 * DAY)                            # the owner signs in: the request stops
        self.assertIn("SuccessorRequestStopped", self.types())
        r = self.x.successor_request(self.person, "LOID-1111-2222-3335", T0 + 200 * DAY)
        self.assertEqual(self.x.successor_partner_answer(self.person, "LOVER-1", False, r["ready_at"] + 1)["state"], "refused")
        r = self.x.successor_request(self.person, "LOID-1111-2222-3335", T0 + 300 * DAY)
        self.assertEqual(self.x.successor_partner_answer(self.person, "LOVER-2", True, r["ready_at"] + 1)["state"], "granted")

    def test_the_terms_agreed_are_recorded_and_a_new_version_asks_again(self):
        self.assertEqual(self.x.terms_to_accept(self.person), [], "sign-up records the versions accepted")
        self.assertIn("TermsAccepted", self.types())
        with self.assertRaises(ValueError):
            self.x.accept_terms(self.person, "2020-01-01", P.TERMS["privacy"], T0)
        self.x.accept_terms(self.person, P.TERMS["terms"], P.TERMS["privacy"], T0)
        self.assertEqual(self.x.terms_to_accept(self.person), [])
        old = dict(P.TERMS); P.TERMS["terms"] = "2027-01-01"
        try:
            self.assertEqual(self.x.terms_to_accept(self.person), ["terms"])
        finally:
            P.TERMS.update(old)

    def test_staff_see_data_only_through_a_live_consent_and_every_look_is_shown(self):
        with self.assertRaises(PermissionError):
            self.x.record_staff_view(self.person, "LOCNS-x", "support", "support", T0)
        c = self.a.grant_consent(self.person, "support", "support", "case LOCASE-1", 1, T0)
        self.x.record_staff_view(self.person, c, "support", "support", T0 + 60)
        self.assertEqual(len(self.x.staff_views(self.person)), 1)
        with self.assertRaises(PermissionError):
            self.x.record_staff_view(self.person, c, "support", "support", T0 + 2 * DAY)

    def test_the_security_check_up_has_a_fix_for_each_finding(self):
        ids = [f["id"] for f in self.x.checkup(self.person, T0)]
        self.assertEqual(ids[:2], ["add_second_way", "confirm_recovery_code"])
        self.x.add_second_way(self.person, "passkey", T0); self.x.confirm_recovery_code(self.person, self.done["recovery_code"])
        self.assertEqual(self.x.checkup(self.person, T0), [])
        self.assertTrue(all(f.get("fix") for f in self.x.checkup(self.person, T0)))

    def test_no_event_carries_a_contact_or_a_code(self):
        self.x.request_contact_change(self.person, "email", "pii_new", True, T0)
        for e in self.p.c.store.of(self.person, *EVENTS):
            self.assertFalse(any(k in e["payload"] for k in ("email", "phone", "code", "new_ref", "recovery_code")), e["type"])


if __name__ == "__main__":
    unittest.main()


class SignUpWays(unittest.TestCase):
    """MASTER UPDATE 55 and section 4C point 3: email and phone both, no clue for strangers, nothing made offline."""
    def setUp(self):
        os.environ.pop("LYNK_MODE", None); self.p = Platform(); self.a = self.p.account

    def make(self, username, phone, email):
        s = self.a.begin_sign_up(username, "en", T0, adult_confirmed=True)
        confirm_contacts(self.a, s["person"], T0)
        self.a.finish_sign_up(s["person"], f"pk-{username}", "phone", phone, email, now=T0)
        return s["person"]

    def test_email_and_phone_are_both_needed(self):
        """Section 4C point 3: sign-up needs both, each confirmed with its own code (it was either one before)."""
        self.make("both.ways", "pii_p1", "pii_e1")
        for phone, email in (("pii_p2", None), (None, "pii_e2"), (None, None)):
            s = self.a.begin_sign_up(f"one.{len(str(phone))}{len(str(email))}", "en", T0, adult_confirmed=True)
            confirm_contacts(self.a, s["person"], T0)
            with self.assertRaises(ValueError):
                self.a.finish_sign_up(s["person"], "pk-x", "phone", phone, email, now=T0)
        s = self.a.begin_sign_up("half.done", "en", T0, adult_confirmed=True)
        self.a.set_legal_name(s["person"], "Half Done", "pii_l")
        self.a.confirm_contact(s["person"], self.a.send_contact_code(s["person"], T0, kind="email"), T0, kind="email")
        with self.assertRaises(PermissionError):                                       # the phone is not confirmed yet
            self.a.finish_sign_up(s["person"], "pk-y", "phone", "pii_p3", "pii_e3", now=T0)

    def test_the_answer_never_reveals_whether_a_contact_has_an_account(self):
        self.make("grace.k", "pii_p1", "pii_e1")
        known = self.a.start_with_contact("phone", "pii_p1")
        unknown = self.a.start_with_contact("phone", "pii_p2")
        self.assertEqual(known, unknown)
        self.assertEqual([n["message"] for n in self.a.contact_notices], ["someone_tried_your_contact", "sign_up_code"])

    def test_no_account_is_made_offline_any_more(self):
        """Section 4C point 3: the temporary offline account is removed; sign-up is online only and keeps what was typed."""
        import identity.offline as o
        self.assertFalse(hasattr(o, "ProvisionalAccount") or hasattr(self.a, "attach_provisional"))
        with self.assertRaises(ConnectionError):
            self.a.begin_sign_up("no.network", "en", T0, adult_confirmed=True, online=False)
