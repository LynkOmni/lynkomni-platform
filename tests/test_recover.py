"""The Can't sign in? hub and every reset (section 4C point 5, catalog/ways-in.v1.json, identity/recover.py)."""
import json, os, unittest

from core import ways_in as WI
from services.platform import Platform
from tests._signup import confirm_contacts

T0, H = 1_800_000_000, 3600


class Hub(unittest.TestCase):
    def setUp(self):
        os.environ.pop("LYNK_MODE", None); self.p = Platform(); self.a = self.p.account; self.r = self.a.recover

    def person(self, username="grace.k"):
        s = self.a.begin_sign_up(username, "en", T0, adult_confirmed=True)
        confirm_contacts(self.a, s["person"], T0)
        done = self.a.finish_sign_up(s["person"], f"pk-{username}", "phone", f"pii_p_{username}", f"pii_e_{username}", now=T0)
        return s["person"], done

    def test_the_hub_offers_only_the_ways_the_person_has_strongest_first(self):
        p, _ = self.person()
        ways = [w["id"] for w in self.r.ways(p)["ways"]]
        self.assertEqual(ways, ["backup_code", "recovery_code", "email_and_phone", "id_check"])
        self.a.sign_in(p, "account", "old phone", "CM", T0)
        self.a.ways.set_recovery_contacts(p, ["LOID-1", "LOID-2", "LOID-3"], True, T0)
        ways = self.r.ways(p, "lost_phone", new_device="new phone")
        self.assertEqual([w["id"] for w in ways["ways"]][:1], ["other_device"])
        self.assertIn({"id": "recovery_contacts", "wait_h": 24}, ways["ways"])
        self.assertEqual(self.r.ways(p, "someone_else")["first"], ["lock_everything"])
        with self.assertRaises(ValueError):
            self.r.ways(p, "forgot_password")

    def test_never_a_password_question_text_email_or_call_alone(self):
        p, _ = self.person()
        for way in WI.RECOVERY["never"]:
            with self.assertRaises(PermissionError):
                self.r.start(p, way, {}, "new phone", T0)
        with self.assertRaises(PermissionError):                      # both codes together, never one alone
            self.r.start(p, "email_and_phone", {"email_code_ok": True}, "new phone", T0)

    def test_a_backup_code_gets_straight_back_in_then_24_hours_restricted(self):
        p, done = self.person()
        res = self.r.start(p, "backup_code", {"code": done["backup_codes"][0]}, "new phone", T0)
        self.assertEqual((res["state"], res["next"]), ("done", "checkup"))
        self.assertTrue(self.r.restricted(p, "payouts", T0 + 23 * H))
        self.assertFalse(self.r.restricted(p, "payouts", T0 + 24 * H))
        self.assertTrue(self.r.paused(p, "cards", T0 + H))

    def test_email_and_phone_wait_24_hours_and_any_old_device_can_cancel(self):
        p, _ = self.person()
        res = self.r.start(p, "email_and_phone", {"email_code_ok": True, "phone_code_ok": True}, "new phone", T0)
        self.assertEqual(res["state"], "waiting")
        self.assertIn("recovery_started", [n["message"] for n in self.a.contact_notices])
        with self.assertRaises(PermissionError):
            self.r.complete(res["recovery_id"], "self", T0 + 23 * H)
        self.assertTrue(self.r.paused(p, "payouts", T0 + H), "payouts pause while it waits")
        with self.assertRaises(PermissionError):
            self.r.cancel(res["recovery_id"], "stranger", T0 + H)
        self.assertTrue(self.r.cancel(res["recovery_id"], "old_device", T0 + H)["unusual_check"])
        self.assertTrue(self.r.watched(p))
        with self.assertRaises(ValueError):
            self.r.complete(res["recovery_id"], "self", T0 + 25 * H)

    def test_support_and_lynkassist_never_finish_a_recovery(self):
        p, _ = self.person()
        res = self.r.start(p, "email_and_phone", {"email_code_ok": True, "phone_code_ok": True}, "new phone", T0)
        for by in ("support", "assist", "staff"):
            with self.assertRaises(PermissionError):
                self.r.complete(res["recovery_id"], by, T0 + 25 * H)
        self.assertEqual(self.r.complete(res["recovery_id"], "self", T0 + 25 * H)["state"], "done")

    def test_recovery_contacts_must_confirm(self):
        p, _ = self.person()
        self.a.ways.set_recovery_contacts(p, ["LOID-1", "LOID-2", "LOID-3"], True, T0)
        rid = self.r.start(p, "recovery_contacts", {}, "new phone", T0)["recovery_id"]
        with self.assertRaises(PermissionError):
            self.r.contact_confirms(rid, "LOID-9", T0)
        self.r.contact_confirms(rid, "LOID-1", T0)
        with self.assertRaises(PermissionError):
            self.r.complete(rid, "self", T0 + 25 * H)
        self.r.contact_confirms(rid, "LOID-2", T0)
        self.assertEqual(self.r.complete(rid, "self", T0 + 25 * H)["state"], "done")

    def test_the_id_check_waits_72_hours_with_two_different_staff(self):
        p, _ = self.person()
        with self.assertRaises(PermissionError):
            self.r.start(p, "id_check", {"lover": "LOVER-x"}, "new phone", T0)          # the partner has not confirmed
        lover = self.a.request_identity_check(p, "account_recovery", T0)["lover"]
        self.a.partner_identity_answer(lover, True, "sandbox", T0)
        rid = self.r.start(p, "id_check", {"lover": lover}, "new phone", T0)["recovery_id"]
        self.r.staff_approves(rid, "staff-1"); self.r.staff_approves(rid, "staff-1")
        with self.assertRaises(PermissionError):
            self.r.complete(rid, "self", T0 + 73 * H)
        self.r.staff_approves(rid, "staff-2")
        with self.assertRaises(PermissionError):
            self.r.complete(rid, "self", T0 + 71 * H)
        self.assertEqual(self.r.complete(rid, "cloud", T0 + 73 * H)["state"], "done")

    def test_repeated_failures_switch_on_the_strongest_mode(self):
        p, _ = self.person()
        for i in range(5):
            with self.assertRaises(PermissionError):
                self.r.start(p, "recovery_code", {"code": "wrong"}, "new phone", T0 + i)
        self.assertTrue(self.r.strongest(p, T0 + 10))
        self.assertIn("RecoveryAttemptsBlocked", [e["type"] for e in self.p.c.store.since(p)])

    def test_someone_else_locks_everything_first_and_lost_phone_needs_no_sign_in(self):
        p, _ = self.person()
        self.a.sign_in(p, "account", "phone", "CM", T0)
        out = self.r.someone_else(p, True, T0)
        self.assertEqual(out["lock"]["state"], "locked")
        self.assertEqual(out["then"], ["recover", "activity_log", "security_desk"])
        q, _ = self.person("ama.k")
        self.assertEqual(self.r.lost_phone("ama.k", True, T0), self.r.lost_phone("nobody.here", True, T0))
        self.assertTrue(self.a.protect.locked(q))

    def test_no_code_name_or_contact_in_any_recovery_event(self):
        p, done = self.person()
        self.r.start(p, "backup_code", {"code": done["backup_codes"][1]}, "new phone", T0)
        text = json.dumps([e for e in self.p.c.store.since(p) if e["type"].startswith("Recovery")])
        for secret in (done["backup_codes"][1], done["recovery_code"], "pii_p_grace.k", "pii_e_grace.k"):
            self.assertNotIn(secret, text)


class BasicPhonePin(unittest.TestCase):
    def test_account_pin_reset_by_menu_waits_a_day_at_a_shop_at_once(self):
        os.environ.pop("LYNK_MODE", None); p = Platform(); a = p.account
        s = a.begin_sign_up("menu.person", "en", T0, adult_confirmed=True); person = s["person"]
        r = a.recover.basic_pin_reset(person, "self", True, T0)
        self.assertEqual(r["new_pin_from"], T0 + 24 * H)
        with self.assertRaises(PermissionError):
            a.recover.complete(r["recovery_id"], "self", T0 + H)
        self.assertEqual(a.recover.complete(r["recovery_id"], "self", T0 + 24 * H)["next"], "new_pin")
        self.assertEqual(a.recover.basic_pin_reset(person, "agent_point", True, T0)["new_pin_from"], T0)
        with self.assertRaises(PermissionError):
            a.recover.basic_pin_reset(person, "cashier", True, T0)


class Resets(unittest.TestCase):
    def test_every_reset_has_its_rule(self):
        self.assertEqual(WI.may_reset("staff_pin", "owner", online=False), (True, None))
        self.assertEqual(WI.may_reset("staff_pin", "manager", own=True), (False, "not_own"))
        self.assertEqual(WI.may_reset("staff_pin", "cashier"), (False, "not_allowed"))
        self.assertEqual(WI.may_reset("card_pin", "self"), (False, "not_allowed"))
        self.assertEqual(WI.may_reset("card_pin", "card_issuer"), (True, None))
        self.assertEqual(WI.may_reset("username", "self"), (False, "never"))
        self.assertEqual(WI.may_reset("account_pin", "agent_point"), (True, None))
        self.assertEqual(WI.may_reset("organisation_admin", "another_admin"), (True, None))
        self.assertTrue(WI.RESETS["organisation_admin"]["never_one_person"])
        self.assertEqual(WI.RESETS["business_owner"]["until_law"], "coming_soon")


if __name__ == "__main__":
    unittest.main()
