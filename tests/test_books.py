"""LynkAcc's rules (OFFICE UPDATE, master blueprint 66.2; section 4 step D1): catalog/books.v1.json read through core/books.py and
ts/src/books.ts with shared vectors, on chart of accounts version 2. Every split adds up exactly; nothing is paid before the
provider confirms; the person who enters a bill never approves it; nothing posts on a locked date; the balance sheet always
balances; group books remove what entities owe each other; the tier table of 66.7 is in billing."""
import json, os, subprocess, sys, unittest

from core import accounts as AC
from core import books as B

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Books(unittest.TestCase):
    def test_vectors_and_the_typescript_register_are_current(self):
        r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "books_vectors.py"), "--check"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_chart_version_2_keeps_every_version_1_code_and_posting(self):
        v1 = json.load(open(os.path.join(ROOT, "contract", "chart-of-accounts.v1.json"), encoding="utf-8"))
        for code, a in v1["accounts"].items():
            self.assertEqual((AC.ACCOUNTS[code]["name"], AC.ACCOUNTS[code]["type"]), (a["name"], a["type"]), code)
        for k, rule in v1["postings"].items():
            self.assertEqual(AC.POSTINGS.get(k, rule) if k == "description" else AC.POSTINGS[k], rule, k)
        groups = {"cash", "current_asset", "non_current_asset", "current_liability", "non_current_liability", "equity", "income", "other_income", "cost_of_sales", "expense"}
        for code, a in AC.ACCOUNTS.items():
            self.assertIn(a["group"], groups, code)
        for k in AC.POSTINGS:
            for line in AC.post(k, {"method": "cash", "account": "6000", "lines": [["6000", 5, 0], ["1000", 0, 5]]}, 1000):
                self.assertIn(line[0], AC.ACCOUNTS, k)

    def test_a_journal_from_a_payload_must_balance_and_name_real_accounts(self):
        self.assertEqual(AC.post("journal.posted", {"lines": [["6500", 100, 0], ["1510", 0, 100]]}, 0), [("6500", 100, 0), ("1510", 0, 100)])
        for bad in ([["6500", 100, 0], ["1510", 0, 99]], [["9999", 1, 0], ["1000", 0, 1]], [["6500", 1.5, 0], ["1510", 0, 1.5]], [["6500", 5, 5]], []):
            self.assertEqual(AC.post("journal.posted", {"lines": bad}, 0), [], bad)
        self.assertEqual(AC.post("bill.recorded", {"account": "1510"}, 300), [("6000", 300, 0), ("2000", 0, 300)], "a contra account is never chosen")
        self.assertEqual(AC.post("bill.recorded", {"account": "1500"}, 300), [("1500", 300, 0), ("2000", 0, 300)])

    def test_every_split_adds_up_and_taxes_add_up(self):
        for t, p in ((101, 3), (-101, 4), (7, 7)):
            self.assertEqual(sum(B.split(t, p)), t)
        r = B.tax_line(118000, [{"kind": "sales", "rate_bp": 1800}], included=True)
        self.assertEqual((r["net"], r["total"]), (100000, 118000))
        r = B.tax_line(100000, [{"kind": "sales", "rate_bp": 1800}, {"kind": "withholding", "rate_bp": 300}])
        self.assertEqual((r["total"], r["withheld"], r["to_pay"]), (118000, 3000, 115000))
        r = B.tax_line(100000, [{"kind": "reverse_charge", "rate_bp": 1800}])
        self.assertEqual((r["total"], r["reverse_charge"]), (100000, 18000), "the buyer accounts for it; nothing is charged")

    def test_bills_are_paid_only_through_confirmation_and_never_approved_by_their_preparer(self):
        self.assertEqual(B.BOOKS["bills"]["paid_only_when"], "provider_confirms")
        self.assertIsNone(B.bill_move("draft", "pay_all"), "a bill is approved before it is paid")
        self.assertIsNone(B.bill_move("paid", "void"))
        self.assertFalse(B.may_approve("u1", "u1"))
        self.assertEqual(B.approvers(50001), ["manager", "owner"])
        self.assertFalse(B.match3([{"sku": "A", "qty": 1, "price_minor": 5}], [], [{"sku": "A", "qty": 1, "price_minor": 5}])["ok"], "nothing received")

    def test_schedules_end_exactly(self):
        rows = B.loan_schedule(99999, 2450, 36)
        self.assertEqual(rows[-1]["balance"], 0); self.assertEqual(sum(r["principal"] for r in rows), 99999)
        for m, bp in (("straight_line", 0), ("reducing_balance", 4000)):
            self.assertEqual(sum(B.depreciation(100001, 1000, 3, m, bp)), 99001, m)
        self.assertEqual(B.repeat_dates("2026-01-31", "month", 3), ["2026-01-31", "2026-02-28", "2026-03-31"], "a month-end stays at the month's end")

    def test_closing_two_people_and_the_lock_date(self):
        self.assertFalse(B.may_post("2026-03-31", "2026-03-31"))
        self.assertEqual(B.two_person("write_off", "u1", "u1"), {"needed": True, "ok": False})
        tb = {"4000": 1000, "6000": 400, "1000": 600}
        lines = B.year_end_lines(tb)
        self.assertIn(["3100", 0, 600], lines)
        self.assertEqual(sum(d for _, d, _ in lines), sum(c for _, _, c in lines))

    def test_the_statements_balance_and_group_books_remove_what_entities_owe_each_other(self):
        v = json.load(open(os.path.join(ROOT, "contract", "vectors", "books.v1.json"), encoding="utf-8"))
        self.assertTrue(v["statements"]["balanced"])
        self.assertEqual(v["cash_flow"]["net"], v["statements"]["cash"])
        g = B.consolidate([{"id": "a", "tb": {"1600": 100, "1020": 100, "3000": 200}, "num": 1, "den": 1},
                           {"id": "b", "tb": {"2700": 100, "1020": 100}, "num": 1, "den": 1}])
        self.assertNotIn("1600", g["tb"]); self.assertNotIn("2700", g["tb"]); self.assertEqual(g["difference"], 0)
        for lines in (B.revalue([{"id": "x", "foreign_minor": 100, "booked_minor": 130, "side": "owed_to_us"}], 127, 100)["lines"],
                      B.disposal(600000, 240000, 300000), B.loan_lines(B.loan_schedule(500000, 1200, 12)[0])):
            self.assertEqual(sum(d for _, d, _ in lines), sum(c for _, _, c in lines))
            self.assertEqual(AC.post("journal.posted", {"lines": lines}, 0), [tuple(l) for l in lines], "worked-out lines post as a journal")

    def test_a_sale_beyond_the_stock_is_never_blocked(self):
        r = B.stock_cost([{"kind": "in", "qty": 1000, "unit_cost_minor": 100}, {"kind": "out", "qty": 3000}])
        self.assertEqual((r["cogs"], r["short"]), (100, 2000))

    def test_the_tier_table_of_66_7_is_in_billing(self):
        from services import billing
        F = billing.FEATURES["lynkacc"]
        for k in ("withholding_tax", "legal_keeping", "offline", "import_records", "change_history", "bills_to_pay"):
            self.assertTrue(F[0][k], f"{k} is on every tier, Free included")
        self.assertTrue(F[1]["approval_steps"] and F[2]["assets"] and F[3]["group_books"])
        for kind in json.load(open(os.path.join(ROOT, "catalog", "workspaces.v1.json"), encoding="utf-8"))["entities"].values():
            for k in kind["kinds"]:
                self.assertTrue(B.entity_tools(k), f"{k} has its tools")


if __name__ == "__main__":
    unittest.main()
