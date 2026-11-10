"""Open APIs for every service (NEW UPDATE 1, owner approved 2026-11-10, master blueprint section 50): one register,
catalog/apis.v1.json, covers every billing family; usage prices live only in services/billing.py; nothing forbidden is ever an API."""
import json, os, sys, unittest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from services import billing  # noqa: E402
from core.build_sections import ORDER  # noqa: E402

R = json.load(open(os.path.join(ROOT, "catalog", "apis.v1.json"), encoding="utf-8"))
ADDR = json.load(open(os.path.join(ROOT, "catalog", "addresses.v1.json"), encoding="utf-8"))


class Apis(unittest.TestCase):
    def test_every_billing_family_has_exactly_one_api(self):
        fams = [a["family"] for a in R["apis"] if a["family"] != "platform"]
        self.assertEqual(sorted(fams), sorted(billing.FAMILIES))

    def test_ids_unique_sections_known_usage_priced_in_billing(self):
        ids = [a["id"] for a in R["apis"]]
        self.assertEqual(len(ids), len(set(ids)))
        for a in R["apis"]:
            self.assertIn(a["build_section"], ORDER, a["id"])
            u = a["usage"]
            self.assertTrue(u in billing.API_PRICES or u in R["usage_kinds"], a["id"])
            if a["family"] in ("lynkops", "lynksuite"): self.assertEqual(u, "as_members", a["id"])
            if a["family"] in ("lynkmpay", "lynkrecover", "lynkcheckout"): self.assertEqual(u, "existing_tier_fees", a["id"])   # money services add no fee
        for k in R["usage_kinds"]["tracking_and_maps"].split(", "):
            self.assertIn(k, billing.API_PRICES)

    def test_own_account_access_follows_the_plan(self):
        self.assertEqual(billing.API_OWN_ACCOUNT, {"pro": ("read", "webhooks"), "max": ("read", "write", "webhooks")})

    def test_nothing_forbidden_is_ever_an_api(self):
        for must in ("change credentials", "complete account recovery", "give out a card number", "give out a customer's position",
                     "sell data", "file with a tax authority", "send personal or group chat"):
            self.assertIn(must, R["never"])
        banned = ("credential", "recovery.complete", "card_number", "pan", "position", "location.raw", "tax.file", "personal_chat")
        for a in R["apis"]:
            for s in a["scopes"]:
                self.assertFalse(any(b in s for b in banned), f"{a['id']}: {s}")

    def test_hosts_exist(self):
        hosts = {h["host"] for h in ADDR["hosts"]}
        for h in R["hosts"].values(): self.assertIn(h, hosts)


if __name__ == "__main__": unittest.main()
