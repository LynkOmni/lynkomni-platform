"""LynkOmni never pays an outside bill for anyone; it pays only its own mandatory bills (owner, 2026-11-26)."""
import unittest

import providers
from providers.check import payer_problems
from finance import expense_model as X


class WhoPays(unittest.TestCase):
    def test_every_partner_names_who_pays_and_lynkomni_only_its_own_running_costs(self):
        reg = providers.registry()
        self.assertEqual(payer_problems(reg), [])
        own = {i["id"] for i in reg["items"] if i["who_pays"] == "lynkomni_own"}
        self.assertLessEqual(own, {"edge_cdn", "mesh_relay", "logo_storage", "content_store", "fx_rates", "geo_lookup", "sms_otp"})
        for i in reg["items"]:
            if i["kind"] in ("mobile_money", "bank_rail", "card_acquiring", "qr_rail", "identity", "checks", "voice", "post", "logistics", "biller"):
                self.assertNotEqual(i["who_pays"], "lynkomni_own", i["id"])

    def test_a_partner_bill_put_on_lynkomni_is_refused(self):
        reg = providers.registry()
        bad = {**reg, "items": [{**i, "who_pays": "lynkomni_own"} if i["id"] == "people_messaging" else i for i in reg["items"]]}
        self.assertTrue(any("people_messaging" in p for p in payer_problems(bad)))
        none = {**reg, "items": [{k: v for k, v in i.items() if k != "who_pays"} if i["id"] == "phone_owner_networks" else i for i in reg["items"]]}
        self.assertTrue(any("phone_owner_networks" in p for p in payer_problems(none)))

    def test_every_expense_line_is_lynkomnis_own_bill_or_passed_through(self):
        self.assertEqual(set(X.PAYER), set(X.ROWS))
        self.assertLessEqual(set(X.PAYER.values()), {X.OWN, X.PASSED})
        self.assertNotIn("phone_owner_checks", X.ROWS, "a check is paid by the partner or the one who asks, never by LynkOmni")
        for stage in ("stage1", "stage2", "stage3"):
            self.assertLessEqual(X.expenses(stage)["message_delivery"], X.MESSAGING_REVENUE[stage], "passed-through costs are covered by what businesses pay")
