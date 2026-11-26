"""Sign-up, sign-in, the ways to prove it's you and the protections around an account (section 4C point 3, catalog/ways-in.v1.json)."""
import json, os, subprocess, sys, unittest

from core import ways_in as WI
from identity.ways_in import totp
from services.platform import Platform
from tests._signup import confirm_contacts

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T0 = 1_800_000_000
EVENTS = json.load(open(os.path.join(ROOT, "identity", "events.v1.json"), encoding="utf-8"))["events"]


class Register(unittest.TestCase):
    def test_vectors_and_the_typescript_register_are_up_to_date(self):
        r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "waysin_vectors.py"), "--check"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr or r.stdout)

    def test_the_rules_the_owner_agreed(self):
        self.assertEqual(WI.SIGN_UP["steps"], ["country", "username", "age", "legal_name", "email", "email_code", "phone", "phone_code", "passkey", "recovery"])
        self.assertTrue(WI.SIGN_UP["online_only"]); self.assertFalse(WI.SIGN_UP["temporary_offline_account"])
        self.assertEqual(WI.SIGN_UP["needs"], ["email", "phone"])
        self.assertFalse(WI.SIGN_UP["abuse"]["picture_puzzles"])
        self.assertEqual(WI.BASIC["limited"], ["payouts", "cards", "exchange", "storefront_selling"])
        self.assertEqual(WI.W["backup_codes"]["count"], 10); self.assertEqual(WI.W["backup_codes"]["remind_at"], 2)
        self.assertEqual((WI.W["recovery_contacts"]["min"], WI.W["recovery_contacts"]["max"]), (3, 5))
        self.assertEqual(WI.PROTECT["old_devices_days"], 90)
        self.assertEqual(WI.SIGN_IN["codes"]["lifetime_s"], 300)
        for never in ("password", "security_questions", "text_alone", "email_alone", "call_alone", "support_in_chat"):
            self.assertIn(never, WI.RECOVERY["never"])
        self.assertEqual([w["id"] for w in WI.RECOVERY["ways"]], ["other_device", "backup_code", "recovery_code", "recovery_contacts", "email_and_phone", "id_check"])
        self.assertTrue(RESETS_OK)

    def test_no_brand_and_no_outside_company_is_named(self):
        text = open(os.path.join(ROOT, "catalog", "ways-in.v1.json"), encoding="utf-8").read().lower()
        for brand in ("google", "microsoft", "authy", "yubico", "captcha", "okta", "twilio"):
            self.assertNotIn(brand, text)

    def test_every_new_account_event_carries_no_secret(self):
        for name in ("BackupCodesMade", "BackupCodeUsed", "ExtraCheckTurnedOn", "ExtraCheckTurnedOff", "SecurityKeyAdded", "RecoveryContactsSet",
                     "AntiPhishingWordSet", "CountryLockSet", "SignInRefused", "OldDeviceSignedOut", "BasicPhoneLimitsLifted"):
            self.assertIn(name, EVENTS)
            self.assertFalse({"code", "codes", "secret", "word", "name", "phone", "email", "contacts", "country"} & set(EVENTS[name]["payload"]), name)
        self.assertTrue(EVENTS["ProvisionalAccountStarted"].get("retired"))


RESETS_OK = WI.may_reset("staff_pin", "manager", own=True)[1] == "not_own" and WI.may_reset("username", "self") == (False, "never") \
    and WI.may_reset("staff_pin", "manager", online=False) == (True, None) and WI.may_reset("passkey", "self", online=False) == (False, "go_online")


class Account(unittest.TestCase):
    def setUp(self):
        os.environ.pop("LYNK_MODE", None); self.p = Platform(); self.a = self.p.account; self.w = self.a.ways

    def test_under_age_is_final_until_the_partner_id_check_clears_it(self):
        from services.age_partners import SandboxAgeIdCheck
        self.a.age_refused(device="d-kid", network="n-home", now=T0)
        for later in (T0 + 3600, T0 + 30 * 86400):
            with self.assertRaises(PermissionError, msg="no retry by retyping and no wait that ends by itself"):
                self.a.begin_sign_up("kid.try", "en", later, adult_confirmed=True, device="d-kid", network="n-other")
        self.assertTrue(self.a.age_blocked(network="n-home"))
        self.assertEqual(self.a.age_id_check_request("CM", device="d-kid", now=T0)["state"], "coming_soon", "off until a partner is signed")
        r = self.a.age_id_check_request("CM", device="d-kid", network="n-home", now=T0, partner=SandboxAgeIdCheck())
        self.assertEqual(r["state"], "sent")
        self.assertTrue(r["lover"].startswith("LOVER-"))
        self.assertEqual(self.a.partner_age_answer(r["lover"], False, now=T0 + 60), "failed")
        self.assertTrue(self.a.age_blocked(device="d-kid"), "not adult leaves the block")
        r = self.a.age_id_check_request("CM", device="d-kid", network="n-home", now=T0, partner=SandboxAgeIdCheck())
        self.assertEqual(self.a.partner_age_answer(r["lover"], True, now=T0 + 120), "confirmed")
        self.assertFalse(self.a.age_blocked(device="d-kid", network="n-home"))
        self.a.begin_sign_up("adult.now", "en", T0 + 200, adult_confirmed=True, device="d-kid", network="n-home")
        with self.assertRaises(ValueError):
            self.a.partner_age_answer(r["lover"], True, now=T0 + 300)
        rows = self.a.db.execute("select * from acct_age_blocks").fetchall() + self.a.db.execute("select * from acct_age_idchecks").fetchall()
        self.assertFalse(any("19" in str(c) and "-" in str(c) for row in rows for c in row if isinstance(c, str) and not c.startswith(("LOVER", "["))), "no date is kept")

    def sign_up(self, username="grace.k", device="d1", network="n1"):
        s = self.a.begin_sign_up(username, "en", T0, adult_confirmed=True, country="CM", device=device, network=network)
        confirm_contacts(self.a, s["person"], T0)
        done = self.a.finish_sign_up(s["person"], f"pk-{username}", "phone", f"pii_p_{username}", f"pii_e_{username}", now=T0)
        return s["person"], done

    def test_sign_up_is_online_only_with_limits_per_device_and_network(self):
        with self.assertRaises(ConnectionError):
            self.a.begin_sign_up("no.net", "en", T0, adult_confirmed=True, online=False)
        for i in range(3):
            self.a.begin_sign_up(f"from.d{i}", "en", T0 + i, adult_confirmed=True, device="same", network=f"n{i}")
        with self.assertRaises(PermissionError):
            self.a.begin_sign_up("from.d3", "en", T0 + 10, adult_confirmed=True, device="same", network="n9")
        self.a.begin_sign_up("an.hour.later", "en", T0 + 3700, adult_confirmed=True, device="same", network="n9")

    def test_legal_name_comes_before_finishing_and_lives_only_in_the_vault(self):
        s = self.a.begin_sign_up("no.legal", "en", T0, adult_confirmed=True)
        with self.assertRaises(ValueError):
            self.a.set_legal_name(s["person"], "R2D2", "pii_x")
        for kind in ("email", "phone"):
            self.a.confirm_contact(s["person"], self.a.send_contact_code(s["person"], T0, kind=kind), T0, kind=kind)
        with self.assertRaises(PermissionError):
            self.a.finish_sign_up(s["person"], "pk", "phone", "pii_p", "pii_e", now=T0)
        person, _ = self.sign_up()
        self.assertNotIn("Grace Uwase", json.dumps(self.p.c.store.since(person)))

    def test_ten_backup_codes_shown_once_each_used_once(self):
        person, done = self.sign_up()
        codes = done["backup_codes"]
        self.assertEqual(len(codes), 10); self.assertEqual(len(set(codes)), 10)
        self.assertNotIn(codes[0], json.dumps(self.p.c.store.since(person)))
        r = self.w.use_backup_code(person, codes[0].lower(), T0)
        self.assertEqual((r["ok"], r["left"]), (True, 9))
        self.assertFalse(self.w.use_backup_code(person, codes[0], T0)["ok"], "each code works once")
        for c in codes[1:8]:
            self.w.use_backup_code(person, c, T0)
        self.assertEqual(self.w.use_backup_code(person, codes[8], T0)["note"], "make_new")
        self.assertIn("backup_code_used", [n["message"] for n in self.a.contact_notices])
        fresh = self.w.make_backup_codes(person, T0)
        self.assertFalse(self.w.use_backup_code(person, codes[9], T0)["ok"], "making new codes ends the old set")
        self.assertTrue(self.w.use_backup_code(person, fresh[0], T0)["ok"])

    def test_authenticator_app_by_the_open_standard(self):
        person, _ = self.sign_up()
        self.assertEqual(totp("GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ", 59, 8), "94287082")       # RFC 6238 test value
        sec = self.w.add_authenticator(person, T0)["secret"]
        with self.assertRaises(PermissionError):
            self.w.confirm_authenticator(person, "000000", T0)
        self.w.confirm_authenticator(person, totp(sec, T0), T0)
        self.assertIn("authenticator", self.w.extras(person))
        self.assertFalse(self.w.check_authenticator(person, totp(sec, T0), T0)["ok"], "a code works once")
        self.assertTrue(self.w.check_authenticator(person, totp(sec, T0 + 30), T0 + 30)["ok"])
        self.assertNotIn(sec, json.dumps(self.p.c.store.since(person)))

    def test_wrong_extra_codes_make_the_person_wait(self):
        person, _ = self.sign_up()
        self.w.add_authenticator(person, T0)
        for i in range(5):
            self.w.check_authenticator(person, "123456", T0 + i)
        self.assertIn("wait_s", self.w.check_authenticator(person, "123456", T0 + 6))

    def test_qr_sign_in_needs_the_signed_in_phone_and_ends_in_two_minutes(self):
        person, _ = self.sign_up()
        q = self.w.qr_start("laptop", T0)
        with self.assertRaises(PermissionError):
            self.w.qr_approve(person, q["token"], session_ok=False, now=T0)
        self.assertIsNone(self.w.qr_finish(q["token"], "laptop", T0))
        self.w.qr_approve(person, q["token"], session_ok=True, now=T0 + 10)
        self.assertIsNone(self.w.qr_finish(q["token"], "other", T0 + 11), "only on the device that showed it")
        self.assertEqual(self.w.qr_finish(q["token"], "laptop", T0 + 11), person)
        self.assertIsNone(self.w.qr_finish(q["token"], "laptop", T0 + 12), "once")
        late = self.w.qr_start("laptop", T0)
        with self.assertRaises(PermissionError):
            self.w.qr_approve(person, late["token"], True, T0 + 121)

    def test_recovery_contacts_word_and_country_lock_need_a_fresh_check(self):
        person, _ = self.sign_up()
        with self.assertRaises(PermissionError):
            self.w.set_recovery_contacts(person, ["LOID-1", "LOID-2", "LOID-3"], fresh_check=False)
        with self.assertRaises(ValueError):
            self.w.set_recovery_contacts(person, ["LOID-1", "LOID-2"], fresh_check=True)
        self.w.set_recovery_contacts(person, ["LOID-1", "LOID-2", "LOID-3"], True, T0)
        self.w.set_word(person, "sunflower", True, T0)
        self.assertEqual(self.w.word_for_message(person), "sunflower")
        self.assertNotIn("sunflower", json.dumps(self.p.c.store.since(person)))
        self.w.set_country_lock(person, ["CM"], True, T0)
        self.assertEqual(self.w.check_sign_in(person, "d9", "FR", T0)["why"], "country_lock")
        self.assertTrue(self.w.check_sign_in(person, "d9", "CM", T0)["ok"])

    def test_unusual_sign_ins_ask_an_extra_check_and_old_devices_go(self):
        person, _ = self.sign_up()
        self.w.signed_in(person, "phone", "CM", True, T0)
        self.assertFalse(self.w.check_sign_in(person, "phone", "CM", T0 + 60)["extra_check"])
        c = self.w.check_sign_in(person, "laptop", "FR", T0 + 3600)
        self.assertEqual((c["unusual"], c["extra_check"]), (["new_country", "impossible_journey"], True))
        self.assertEqual(self.w.signed_in(person, "kiosk", "CM", False, T0)["hours"], 12)
        self.assertEqual(self.w.sign_out_old_devices(T0 + 90 * 86400), [(person, "phone"), (person, "kiosk")])

    def test_basic_phone_accounts_are_limited_until_an_email_is_added(self):
        person, _ = self.sign_up()
        self.w.mark_basic_phone(person)
        self.assertFalse(self.w.allows(person, "payouts")); self.assertTrue(self.w.allows(person, "cash_sale"))
        self.w.email_added(person, T0)
        self.assertTrue(self.w.allows(person, "payouts"))

    def test_organisation_rules_only_on_max_and_enterprise(self):
        with self.assertRaises(PermissionError):
            self.w.set_org_rules("org1", "pro", {"own_devices_only": True})
        with self.assertRaises(ValueError):
            self.w.set_org_rules("org1", "max", {"staff_session_hours": 48})
        self.w.set_org_rules("org1", "enterprise", {"security_keys_for_admins": True, "staff_session_hours": 8})
        self.assertEqual(self.w.org_rules("org1")["staff_session_hours"], 8)

    def test_checkup_lists_what_is_missing(self):
        person, _ = self.sign_up()
        self.assertEqual(self.w.checkup(person, T0), ["second_way", "recovery_contacts", "anti_phishing_word"])
        self.assertTrue(any(a["type"] == "BackupCodesMade" or a["type"] == "PasskeyEnrolled" for a in self.w.activity(person, T0)))


if __name__ == "__main__":
    unittest.main()
