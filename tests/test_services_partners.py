"""SERVICES UPDATE partners (master blueprint 67.18; section 4 row 67.17): each has its interface, a sandbox and a ledger entry,
stays off until signed, takes people only as vault references, never uses WhatsApp, and never claims a delivery, a listing, a loan,
a payment or stocked goods."""
import json, os, unittest

from services import services_partners as S

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class ServicesPartners(unittest.TestCase):
    def test_every_partner_is_in_the_ledger_and_off_until_signed(self):
        from providers import availability
        ledger = json.load(open(os.path.join(ROOT, "providers", "registry.v1.json"), encoding="utf-8"))
        mine = [i for i in ledger["items"] if i["interface"].startswith("services.services_partners:")]
        self.assertEqual(len(mine), 8)
        for i in mine:
            self.assertEqual(i["status"], "sandbox", i["id"])
            self.assertEqual(availability(i["used_by"][0], "RW")["message"], "Coming to your country soon.", i["id"])
        kinds = {i["id"] for i in ledger["items"]}
        self.assertTrue({"delivery_partners", "vcard_wallet_tokens"} <= kinds, "delivery firms and phone wallets already have theirs")

    def test_no_whatsapp_and_people_only_as_vault_references(self):
        self.assertEqual(S.SandboxChatChannel().send("m1", "WhatsApp", "vault:c", "a" * 64), {"ok": False, "reason": "channel_not_used"})
        self.assertFalse(S.SandboxChatChannel().send("m1", "page", "+250788000000", "a" * 64)["ok"])
        with self.assertRaises(ValueError):
            S.SandboxChatChannel().send("m1", "page", "vault:c", "Hello")
        self.assertFalse(S.SandboxCallPartner().call("c1", "vault:c", False)["connected"])

    def test_no_sandbox_claims_a_loan_payment_listing_or_stock(self):
        self.assertFalse(S.SandboxPayInParts().apply("a1", 50000, "RWF", "vault:c", None)["ok"], "consent first")
        self.assertFalse(S.SandboxPayInParts().apply("a1", 50000, "RWF", "vault:c", "consent-1")["approved"])
        with self.assertRaises(ValueError):
            S.SandboxPayInParts().apply("a1", 500.5, "RWF", "vault:c", "consent-1")
        self.assertFalse(S.SandboxTransportBiller().pay("p1", "toll", "vault:a", 1000, "RWF")["paid"])
        self.assertIsNone(S.SandboxGovernmentFee().pay("p2", "FEE-1", 5000, "RWF", "vault:p")["receipt"])
        self.assertEqual(S.SandboxOutsideWarehouse().stock_report("w1")["lines"], [])
        self.assertEqual(S.SandboxListingConnector().sync("l1", ["maps"])["sites"], {"maps": "pending"})
        self.assertFalse(S.SandboxShopPluginListing().submit("pl1", "store-a")["listed"])


if __name__ == "__main__":
    unittest.main()
