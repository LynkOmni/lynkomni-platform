"""One global chart of accounts and the journal as a projection of the event log (Step 0, blueprint 42 A)."""
import json, pathlib, sys, unittest
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from core import accounts, regions
from services.platform import Platform

def item(sku, qty, price): return {"sku": sku, "qty": qty, "price_minor": price}


class Chart(unittest.TestCase):
    def test_one_global_chart_with_balanced_postings(self):
        self.assertTrue(all(a["type"] in accounts.TYPES for a in accounts.ACCOUNTS.values()))
        for t, rule in accounts.POSTINGS.items():
            lines = accounts.post(t, {"method": "cash"}, 1000)
            self.assertEqual(sum(d for _, d, _ in lines), sum(c for _, _, c in lines), t)
            self.assertTrue(all(a in accounts.ACCOUNTS for a, _, _ in lines), t)
        self.assertEqual(accounts.post("product.created", {}, 1000), [])            # not a money fact: posts nothing
        self.assertEqual(accounts.post("sale.recorded", {"method": "mobile_money"}, 500), [("1010", 500, 0), ("4000", 0, 500)])
        self.assertEqual(accounts.post("sale.voided", {"method": "mobile_money"}, 500), [("1010", 0, 500), ("4000", 500, 0)])
        self.assertEqual(accounts.post("cash_difference.flagged", {}, -200), [("1000", 200, 0), ("6200", 0, 200)])   # a surplus mirrors a shortfall

    def test_country_pack_mapping_changes_labels_only(self):
        plain = accounts.local_chart(None)
        self.assertEqual(plain["4000"]["name"], "Sales"); self.assertEqual(plain["4000"]["code"], "4000")
        mapped = accounts.local_chart({"chart_of_accounts": {"4000": {"code": "701", "name": "Ventes de marchandises"}}})
        self.assertEqual((mapped["4000"]["code"], mapped["4000"]["name"], mapped["4000"]["global_code"]), ("701", "Ventes de marchandises", "4000"))
        self.assertEqual(mapped["1000"], plain["1000"])
        for code, pack in regions.COUNTRIES.items():                              # a pack mapping may only name global codes
            for g in (pack.get("chart_of_accounts") or {}):
                self.assertIn(g, accounts.ACCOUNTS, code)

    def test_journal_is_a_projection_that_agrees_with_the_summary(self):
        p = Platform(); p.register("m1", "XX")
        p.inventory.receive("m1", "d", "x", 10, 100)
        p.pos.record_sale("m1", "d", [item("x", 4, 150)]); p.pos.expense("m1", "d", 50, "rent")
        j = p.accountant.journal("m1")
        self.assertTrue(accounts.balanced(j)); self.assertEqual(len(j), 4)        # stock in, sale, its cost of goods, the expense
        self.assertEqual(accounts.profit(j), p.accountant.summary("m1")["profit_minor"])  # 600 - 400 - 50
        tb = p.accountant.trial_balance("m1")
        self.assertEqual(tb["1200"]["balance_minor"], 600)                        # 10 x 100 in, 4 x 100 sold
        self.assertEqual(tb["4000"]["balance_minor"], 600); self.assertEqual(tb["1000"]["balance_minor"], 550)
        self.assertEqual(tb["2000"]["balance_minor"], 1000)
        # a journal exists at Free: tiers decide which reports are shown, never what is recorded
        self.assertTrue(j)

    def test_chart_file_is_shared_with_the_contract(self):
        c = json.loads((ROOT / "contract" / "chart-of-accounts.v1.json").read_text())
        self.assertEqual(c["$id"], "lynkomni/chart-of-accounts.v1"); self.assertIn("4100", c["accounts"])   # commission income from the cloud only


if __name__ == "__main__": unittest.main()
