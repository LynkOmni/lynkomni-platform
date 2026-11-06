import unittest
from services.platform import Platform

class T(unittest.TestCase):
    def setUp(self): self.p = Platform(); self.n = self.p.newsletter
    def test_double_opt_in_and_honest_states(self):
        r = self.n.subscribe("Amina@Example.com", "fr", "RW", {"product", "merchant"}, True, now=1000)
        self.assertEqual(r["status"], "check_your_email"); self.assertEqual(self.n.state("amina@example.com"), "pending")      # not subscribed until confirmed
        self.assertEqual(self.n.confirm(r["mail"]["confirm_token"], now=1100)["status"], "subscribed"); self.assertEqual(self.n.state("amina@example.com"), "confirmed")
        with self.assertRaises(PermissionError): self.n.confirm(r["mail"]["confirm_token"], now=1200)                         # single use
    def test_consent_validation_honeypot_and_no_enumeration(self):
        with self.assertRaises(ValueError): self.n.subscribe("a@b.co", "en", "RW", set(), False)                                # no consent, no subscription
        with self.assertRaises(ValueError): self.n.subscribe("not-an-email", "en", "RW", set(), True)
        with self.assertRaises(ValueError): self.n.subscribe("a@b.co", "en", "RW", {"spam"}, True)
        self.assertEqual(self.n.subscribe("bot@b.co", "en", "RW", set(), True, honeypot="x"), {"status": "check_your_email"}); self.assertIsNone(self.n.state("bot@b.co"))
        first = self.n.subscribe("c@d.co", "en", "RW", set(), True, now=1000); self.n.confirm(first["mail"]["confirm_token"], now=1001)
        again = self.n.subscribe("c@d.co", "en", "RW", set(), True, now=9000); self.assertEqual(again, {"status": "check_your_email"})   # same answer for a known address
        self.assertEqual(self.n.subscribe("c@d.co", "en", "RW", set(), True, now=9010), {"status": "check_your_email"})
    def test_one_click_unsubscribe_and_deletion(self):
        r = self.n.subscribe("e@f.co", "en", "KE", {"company"}, True, now=1000); self.n.confirm(r["mail"]["confirm_token"], now=1001)
        t = self.n.unsubscribe_token("e@f.co", now=1002); self.assertEqual(self.n.unsubscribe(t, now=2000)["status"], "unsubscribed"); self.assertEqual(self.n.state("e@f.co"), "unsubscribed")
        self.assertEqual(self.n.unsubscribe(t, now=3000)["status"], "unsubscribed")                                                   # the link keeps working
        self.n.delete("e@f.co"); self.assertIsNone(self.n.state("e@f.co"))
if __name__ == "__main__":
    unittest.main()
