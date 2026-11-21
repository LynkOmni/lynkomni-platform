"""The six services' partners (SIX SERVICES UPDATE, master blueprint 69.13; section 4 row 69.14): each has its interface, a sandbox
and a ledger entry, stays off until signed, takes people only as vault references, asks for consent before any check and never
claims a result, a listing, a payment or a cover."""
import json, os, unittest

from services import six_partners as S

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class SixPartners(unittest.TestCase):
    def test_every_partner_is_in_the_ledger_and_off_until_signed(self):
        from providers import availability
        ledger = json.load(open(os.path.join(ROOT, "providers", "registry.v1.json"), encoding="utf-8"))
        mine = [i for i in ledger["items"] if i["interface"].startswith("services.six_partners:")]
        self.assertEqual(len(mine), 11)
        for i in mine:
            self.assertEqual(i["status"], "sandbox", i["id"])
            self.assertEqual(availability(i["used_by"][0], "RW")["message"], "Coming to your country soon.", i["id"])

    def test_checks_need_consent_and_vault_references(self):
        self.assertFalse(S.SandboxBackgroundCheck().check("c1", "vault:p", ["references"], None)["ok"])
        self.assertFalse(S.SandboxBackgroundCheck().check("c1", "Ana Uwase", ["references"], "consent-1")["ok"])
        self.assertEqual(S.SandboxBackgroundCheck().check("c1", "vault:p", ["references"], "consent-1")["state"], "pending")
        self.assertFalse(S.SandboxTenantScreening().screen("s1", "vault:p", None)["ok"])

    def test_no_sandbox_claims_a_result_or_holds_money(self):
        self.assertFalse(S.SandboxNotary().notarise("n1", "a" * 64, ["vault:p"])["notarised"])
        self.assertFalse(S.SandboxDepositProtection().protect("d1", 50000, "RWF", "vault:t")["protected"])
        self.assertFalse(S.SandboxRentInsurance().quote("q1", "u1", 30000, "RWF")["covered"])
        with self.assertRaises(ValueError):
            S.SandboxDepositProtection().protect("d1", 500.5, "RWF", "vault:t")
        self.assertEqual(S.SandboxJobListings().publish("j1", ["site-a"])["sites"], {"site-a": "pending"})


if __name__ == "__main__":
    unittest.main()
