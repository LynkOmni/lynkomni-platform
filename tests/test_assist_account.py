"""LynkAssist on the account site and a person's cards by group (MASTER UPDATE sections 54 and 61; build section 2)."""
import os, unittest
from identity.account import EVENTS
from services.assist_account import AccountAssist
from services.platform import Platform

T0 = 1_800_000_000.0


class AccountAssistTests(unittest.TestCase):
    def setUp(self):
        os.environ.pop("LYNK_MODE", None); self.p = Platform(); self.a = self.p.account; self.x = AccountAssist(self.a)
        s = self.a.begin_sign_up("grace.k", "en", T0, adult_confirmed=True); self.person = s["person"]
        code = self.a.send_contact_code(self.person, T0); self.a.confirm_contact(self.person, code, T0)
        self.a.finish_sign_up(self.person, "pk-1", "Grace's phone", "pii_1", None, now=T0)
        self.tok = self.a.sign_in(self.person, "account", "Grace's phone", "Kigali", T0)

    def stepup(self):
        code = self.a.auth.begin_stepup(self.person, T0)
        return self.a.auth.complete_stepup(self.person, self.tok, code, T0)

    def test_answers_follow_their_class(self):
        self.assertFalse(self.x.ask(self.person, "sign_in_history", signed_in=False)["answered"])
        self.assertFalse(self.x.ask(self.person, "sign_in_history", signed_in=True)["answered"], "verified answers need a fresh check")
        got = self.x.ask(self.person, "sign_in_history", signed_in=True, stepup_token=self.stepup(), now=T0)
        self.assertTrue(got["answered"]); self.assertEqual(got["facts"][0]["device"], "Grace's phone")
        for secret in ("password", "codes_and_keys", "full_card_number"):
            self.assertFalse(self.x.ask(self.person, secret, signed_in=True, stepup_token=self.stepup(), now=T0)["answered"], secret)

    def test_class_b_needs_confirm_and_can_be_undone(self):
        r = self.x.do(self.person, "change_language", lang="fr", now=T0)
        self.assertEqual(r["needs"], "confirm")
        r = self.x.do(self.person, "change_language", confirmed=True, lang="fr", now=T0)
        self.assertTrue(r["run"])
        self.assertEqual(self.a.db.execute("select lang from acct_people where person=?", (self.person,)).fetchone()[0], "fr")
        self.assertTrue(self.x.undo(self.person, r["entry"], now=T0 + 5))
        self.assertEqual(self.a.db.execute("select lang from acct_people where person=?", (self.person,)).fetchone()[0], "en")
        self.assertFalse(self.x.undo(self.person, r["entry"], now=T0 + 6), "undone once")

    def test_class_c_needs_the_fresh_identity_check_then_confirm(self):
        self.assertEqual(self.x.do(self.person, "lock_everything", confirmed=True, now=T0)["needs"], "fresh_check")
        su = self.stepup()
        self.assertEqual(self.x.do(self.person, "lock_everything", stepup_token=su, now=T0)["needs"], "confirm")
        r = self.x.do(self.person, "lock_everything", confirmed=True, stepup_token=su, now=T0)
        self.assertTrue(r["run"]); self.assertEqual(r["result"]["state"], "locked")
        self.assertTrue(self.a.protect.locked(self.person))

    def test_recovery_and_passkeys_are_only_prepared_never_done(self):
        for act in ("recover_account", "change_passkeys"):
            r = self.x.do(self.person, act, confirmed=True, stepup_token=self.stepup(), now=T0)
            self.assertFalse(r["run"]); self.assertEqual((r["needs"], r["result"]), ("hand_over", "prepared_for_security_center"))
        self.assertEqual(self.x.do(self.person, "send_all_money_to_me", confirmed=True, now=T0)["needs"], "refused")

    def test_everything_lynkassist_did_is_recorded_run_or_not(self):
        self.x.do(self.person, "change_language", lang="sw", now=T0)
        self.x.do(self.person, "change_language", confirmed=True, lang="sw", now=T0)
        h = self.x.everything_done(self.person)
        self.assertEqual([(e["action"], e["ran"]) for e in h], [("change_language", True), ("change_language", False)])
        self.assertEqual([e["type"] for e in self.p.c.store.of(self.person, *EVENTS)].count("AssistActionRecorded"), 2)


class CardsByGroup(unittest.TestCase):
    def test_cards_are_listed_by_group_with_the_last_four_only(self):
        from services.vcard import VCard
        p = Platform(); v = VCard(p)
        v.db.execute("insert into vcards(card,account,internal,token,last4,type,state,lock,expiry,auto_renew,rotation,balance,created,physical,card_group) values('LOVC-1','m1','i1','tok','4242','team','active','{}',0,0,null,0,1,null,'debit')")
        v.db.execute("insert into vcards(card,account,internal,token,last4,type,state,lock,expiry,auto_renew,rotation,balance,created,physical) values('LOVC-2','m1','i2','tok2','1111','supplier','active','{}',0,0,null,0,2,null)")
        g = v.cards_by_group("m1")
        self.assertEqual(sorted(g), ["credit", "debit", "prepaid"])
        self.assertEqual([c["card"] for c in g["prepaid"]], ["LOVC-2"], "older cards are prepaid")
        self.assertEqual(g["debit"][0]["last4"], "4242")
        self.assertNotIn("token", g["debit"][0])


if __name__ == "__main__":
    unittest.main()
