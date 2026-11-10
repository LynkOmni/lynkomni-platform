"""LynkVCard card groups (MASTER UPDATE, master blueprint section 61): prepaid, debit and credit on the four faces."""
import json, os, unittest
from services import billing
from services import card_groups as cg

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
V5 = json.load(open(os.path.join(ROOT, "contract", "event-payloads.v5.json"), encoding="utf-8"))["events"]


class TestCardGroups(unittest.TestCase):
    def test_the_sample_number_can_never_be_a_real_card(self):
        self.assertFalse(cg.luhn_ok(cg.SAMPLE["number"]), "it fails the check digit every real card number passes")
        self.assertFalse(cg.looks_like_a_network_number(cg.SAMPLE["number"]))
        self.assertTrue(cg.luhn_ok("4111 1111 1111 1111"), "the check itself works")
        self.assertEqual((cg.SAMPLE["expiry"], cg.SAMPLE["holder"], cg.SAMPLE["code"]), ("MM/YY", "CARD HOLDER", "000"))

    def test_names_are_locked_and_never_new_products(self):
        self.assertEqual(cg.NAMES, {"prepaid": "LynkPrima", "debit": "LynkDyna", "credit": "LynkCrest"})
        self.assertEqual(cg.plan_name("debit", "core"), "LynkDyna Pro")
        self.assertEqual(cg.plan_name("credit", "edge"), "LynkCrest Free")
        for n in ("lynkprima", "lynkdyna", "lynkcrest"):
            self.assertNotIn(n, billing.FAMILIES, "one LynkVCard plan covers all three groups")
        self.assertEqual(billing.FAMILIES["lynkvcard"][3], (0, 4, 12, 30), "plan prices unchanged")

    def test_tiers_by_group(self):
        self.assertFalse(cg.allowed("credit", "edge", "charge")["ok"])
        self.assertTrue(cg.allowed("credit", "edge", "secured")["ok"])
        self.assertTrue(cg.allowed("credit", "hub", "charge")["ok"])
        self.assertFalse(cg.allowed("credit", "hub", "credit")["ok"])
        self.assertTrue(cg.allowed("credit", "core", "credit")["ok"])
        self.assertFalse(cg.allowed("debit", "edge", physical=True)["ok"], "EDGE stays virtual")
        self.assertEqual(cg.allowed("debit", "hub", physical=True)["physical_fee"], "issuer")
        self.assertIsNone(cg.allowed("prepaid", "omni", physical=True)["physical_fee"], "included on OMNI")
        for f in billing.FEATURES["lynkvcard"]:
            self.assertEqual(tuple(f["card_groups"]), cg.GROUPS)

    def test_a_request_is_online_only_and_the_card_exists_only_when_the_partner_answers(self):
        with self.assertRaises(PermissionError):
            cg.request("prepaid", "edge", "virtual", "self", online=False, partner_ready=True, request_id="r1")
        self.assertEqual(cg.request("debit", "hub", "virtual", "self", True, False, "r1")["state"], "coming_soon")
        r = cg.request("credit", "core", "virtual", "self", True, True, "r2", credit_kind="secured")
        name, payload = r["event"]
        self.assertEqual(name, "CardRequested")
        self.assertTrue(set(payload) <= set(V5["CardRequested"]["payload"]["properties"]))
        self.assertEqual(V5["CardRequested"]["origins"], ["device"])
        for answer in ("CardRequestConfirmed", "CardRequestFailed"):
            self.assertEqual(V5[answer]["origins"], ["server"], "only the cloud records the partner's answer")

    def test_the_lender_alone_decides_and_no_event_carries_card_details_or_income(self):
        lender = cg.SandboxLender()
        self.assertEqual(lender.decide("secured", True, True)["reason"], "deposit_not_received")
        ok = lender.decide("credit", True, True, asked_limit=20_000)
        name, p = cg.partner_answer("r3", "credit", ok, card_id="c1", credit_limit=ok["limit"], currency="XAF")
        self.assertEqual((name, p["partner_kind"], p["credit_limit"]), ("CardRequestConfirmed", "lender", 20_000))
        with self.assertRaises(ValueError):
            cg.partner_answer("r4", "credit", ok, card_id="c2", credit_limit=200.5, currency="XAF")
        self.assertEqual(cg.partner_answer("r5", "debit", cg.SandboxAccountPartner().open_card(False))[1]["reason"], "identity_not_confirmed")
        banned = {"card_number", "pan", "number", "cvv", "cvc", "code", "expiry", "income", "balance", "salary"}
        for name in ("CardRequested", "CardRequestConfirmed", "CardRequestFailed"):
            self.assertFalse(banned & set(V5[name]["payload"]["properties"]), name)

    def test_each_group_asks_only_what_it_needs(self):
        self.assertNotIn("income", cg.FORM["prepaid"] + cg.FORM["debit"])
        self.assertIn("credit_check_consent", cg.FORM["credit"])
        self.assertNotIn("card_number", sum(cg.FORM.values(), ()))


if __name__ == "__main__":
    unittest.main()
