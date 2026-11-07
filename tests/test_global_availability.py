"""Global availability rule (owner approved 2026-11-06): every service is designed for the world and shown everywhere;
partner-free services work in every country; regulated ones say "Coming to your country soon." with Notify me until signed."""
import os, unittest
import providers
from core.regions import SERVICES
from services.waitlist import Waitlist

CORE = ("pos", "accountant", "invoicing", "crm", "inventory", "dashboard", "intelligence", "chat")


class GlobalAvailability(unittest.TestCase):
    def setUp(s):
        s.mode = os.environ.pop("LYNK_MODE", None)

    def tearDown(s):
        if s.mode is not None:
            os.environ["LYNK_MODE"] = s.mode

    def test_core_services_work_in_every_country_including_ones_without_a_pack(self):
        for c in ("RW", "KE", "US", "FR", "BR", "JP", "ZZ", ""):
            for svc in CORE:
                self.assertEqual(providers.availability(svc, c)["state"], "available", f"{svc} in {c}")

    def test_every_service_is_shown_everywhere_never_hidden_or_broken(self):
        for c in ("RW", "FR", "ZZ"):
            for svc in SERVICES:
                a = providers.availability(svc, c)
                self.assertIn(a["state"], ("available", "coming_soon"))
                if a["state"] == "coming_soon":
                    self.assertEqual(a["message"], "Coming to your country soon.")
                    self.assertTrue(a["notify_me"])
                    self.assertTrue(a["visual"])

    def test_no_user_facing_text_says_not_available(self):
        import json
        for i in providers.registry()["items"]:
            self.assertNotIn("not available", i["when_off"]["message"].lower(), i["id"])

    def test_notify_me_needs_consent_and_a_vault_reference(self):
        w = Waitlist()
        with self.assertRaises(PermissionError):
            w.join("vcard", "FR", "pii_abc", consent=False)
        with self.assertRaises(ValueError):
            w.join("vcard", "FR", "+33 6 12 34 56 78", consent=True)
        self.assertTrue(w.join("vcard", "FR", "pii_abc", consent=True)["joined"])
        self.assertFalse(w.join("pos", "FR", "pii_abc", consent=True)["joined"])   # already available
        self.assertEqual(w.due(), [])                                              # not signed yet: nobody told
        self.assertTrue(w.leave("vcard", "FR", "pii_abc"))

    def test_people_are_told_once_when_the_service_arrives(self):
        w = Waitlist()
        w.join("payments", "RW", "pii_x", consent=True)
        os.environ["LYNK_MODE"] = "sandbox"   # stands in for the partner being signed
        try:
            self.assertEqual(len(w.due()), 1)
            self.assertEqual(w.due(), [])
        finally:
            os.environ.pop("LYNK_MODE")


if __name__ == "__main__":
    unittest.main()
