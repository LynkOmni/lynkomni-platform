"""Phone and email fields (section 4C point 1, owner 2026-11-25): every country pack carries its numbering rules, the Python
reference and the TypeScript port agree (contract/vectors/phone.v1.json), and every phone or email field is the shared part."""
import glob, json, os, re, subprocess, sys, unittest
from core import phone as P
from tests._signup import confirm_contacts

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Phone(unittest.TestCase):
    def test_every_pack_has_its_rules_and_the_vectors_are_fresh(self):
        for tool in ("tools/country_phone.py", "tools/phone_vectors.py"):
            r = subprocess.run([sys.executable, os.path.join(ROOT, tool), "--check"], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_a_country_says_how_long_its_numbers_are_and_never_how_they_start(self):
        r = P.rules("XX")                                     # the sample pack: labelled sample rules, never a real country
        self.assertEqual(P.check(r, "5")["state"], "typing")   # owner 2026-11-25: new networks can start numbers with any digit
        self.assertNotIn("first", P.check(r, "5"))
        self.assertEqual(P.check(r, "512345678")["state"], "ok")
        self.assertEqual(P.check(r, "612")["state"], "typing")
        self.assertEqual(P.check(r, "612", submit=True)["state"], "short")
        self.assertEqual(P.check(r, "612345678")["state"], "ok")
        self.assertEqual(P.check(r, "6123456789")["state"], "long")
        self.assertEqual(P.accept(r, "6123456789"), "612345678")   # never more digits than the country's numbers have
        self.assertEqual(P.groups(r, "612345678"), "612 345 678")
        self.assertEqual(P.sample(r), "612 345 678")
        self.assertEqual(P.international(r, "612345678"), "+999612345678")

    def test_no_pack_carries_a_start_rule(self):
        for f in glob.glob(os.path.join(ROOT, "contract", "country-packs", "*.json")):
            ph = json.load(open(f, encoding="utf-8"))["phone"]
            if ph: self.assertFalse({"first", "starts"} & (set(ph["mobile"]) | set(ph["any"])), f)

    def test_a_shared_dialling_code_picks_its_main_country_and_prefixes_are_cleaned(self):
        self.assertEqual(P.read_pasted("+1 212 555 0100", "XX")[0], "US")
        self.assertEqual(P.clean(P.rules("RU"), "88123456789"), "8123456789")
        self.assertEqual(P.clean(P.rules("RU"), "8123456789"), "8123456789")

    def test_the_trunk_prefix_and_any_script_digits_are_cleaned(self):
        r = P.rules("XX")
        self.assertEqual(P.clean(r, "0612 345 678"), "612345678")
        self.assertEqual(P.clean(r, "٦١٢"), "612")

    def test_a_territory_without_a_plan_gets_the_general_rules(self):
        packs = [os.path.basename(p)[:-5] for p in glob.glob(os.path.join(ROOT, "contract", "country-packs", "*.json"))]
        none = [c for c in packs if json.load(open(os.path.join(ROOT, "contract", "country-packs", f"{c}.json"), encoding="utf-8"))["phone"] is None]
        for c in none:
            self.assertEqual(P.check(P.rules(c), "1234")["state"], "ok", c)
        self.assertLess(len(none), 10)

    def test_email(self):
        self.assertEqual(P.check_email("x@gmial.com")["suggest"], "x@gmail.com")
        self.assertEqual(P.check_email("x@y")["state"], "format")
        self.assertEqual(P.check_email("x@mailinator.com")["state"], "ok")
        self.assertEqual(P.check_email("x@mailinator.com", deep=True)["state"], "throwaway")

    def test_every_phone_and_email_field_is_the_shared_part(self):
        """No screen draws its own phone or email input: the shared part (ts/src/fields.ts) draws them all."""
        files = glob.glob(os.path.join(ROOT, "web", "emulators", "*", "app.ts")) + [f for f in glob.glob(os.path.join(ROOT, "ts", "src", "*.ts")) if not f.endswith(("fields.ts", "emailfield.ts", ".generated.ts"))]
        bad = []
        for f in files:
            for m in re.finditer(r"<input[^>]*>", open(f, encoding="utf-8").read()):
                tag = m.group(0)
                if re.search(r'inputmode="tel"|type="tel"|inputmode="email"|type="email"', tag): bad.append(f"{os.path.relpath(f, ROOT)}: {tag[:80]}")
        self.assertEqual(bad, [])


if __name__ == "__main__":
    unittest.main()


class Contacts(unittest.TestCase):
    """Codes, one contact per account and numbers that change hands (section 4C point 1)."""
    T0 = 1_800_000_000

    def setUp(self):
        from services.platform import Platform
        os.environ.pop("LYNK_MODE", None); self.p = Platform(); self.a = self.p.account

    def person(self, name, phone, email):
        s = self.a.begin_sign_up(name, "en", self.T0, adult_confirmed=True); who = s["person"]
        confirm_contacts(self.a, who, self.T0)
        self.a.finish_sign_up(who, "pk", "phone", phone, email, now=self.T0); return who

    def test_codes_last_five_minutes_and_resending_waits(self):
        from identity.account import CodeWait
        s = self.a.begin_sign_up("ama.k", "en", self.T0, adult_confirmed=True); who = s["person"]
        first = self.a.send_contact_code(who, self.T0)
        with self.assertRaises(CodeWait) as w: self.a.send_contact_code(who, self.T0 + 10)
        self.assertEqual(w.exception.seconds, 20)
        with self.assertRaises(PermissionError): self.a.confirm_contact(who, first, self.T0 + 301)       # lasts 5 minutes
        t = self.T0 + 30
        for gap in (0, 60, 120, 300):
            t += gap; self.a.send_contact_code(who, t)
        with self.assertRaises(CodeWait): self.a.send_contact_code(who, t + 3000)                        # 5 in an hour at most
        self.assertEqual(P.resend_wait([], self.T0), 0)

    def test_one_personal_account_per_contact(self):
        self.person("ama.k", "pii_phone_1", "pii_mail_1")
        s = self.a.begin_sign_up("kofi.m", "en", self.T0, adult_confirmed=True); who = s["person"]
        confirm_contacts(self.a, who, self.T0)
        with self.assertRaises(PermissionError): self.a.finish_sign_up(who, "pk", "phone", "pii_phone_1", "pii_mail_2", now=self.T0)

    def test_a_number_given_to_someone_else_leaves_the_account_and_numbers_are_confirmed_yearly(self):
        who = self.person("ama.k", "pii_phone_1", "pii_mail_1")
        self.assertEqual(self.a.number_reassigned("pii_phone_1", self.T0)["told_by"], "email")
        self.assertIsNone(self.a.auth.db.execute("select phone from identities where person=?", (who,)).fetchone()[0])
        self.assertEqual(self.a.contact_notices[-1]["message"], "number_removed_reassigned")
        self.assertIsNone(self.a.number_reassigned("pii_phone_1", self.T0))
        other = self.person("kofi.m", "pii_phone_2", "pii_mail_2")
        self.assertEqual(self.a.numbers_to_confirm(self.T0), [])                                          # starts the year
        self.assertEqual(self.a.numbers_to_confirm(self.T0 + 366 * 86400), [other])
        self.a.confirm_number(other, self.T0 + 366 * 86400)
        self.assertEqual(self.a.numbers_to_confirm(self.T0 + 367 * 86400), [])
