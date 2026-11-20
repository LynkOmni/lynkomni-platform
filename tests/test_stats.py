"""LynkStat's additions (SERVICES UPDATE, master blueprint 67.5; section 4 step D4b): catalog/stats.v1.json read through core/stats.py
and ts/src/stats.ts with shared vectors, and the cloud service in services/stats.py. An estimate is always labelled; a measure
is a formula of figures, never code, and shows nothing rather than a made-up number; a branch manager sees only their branch;
small groups are never published."""
import os, subprocess, sys, unittest
os.environ["LYNK_MODE"] = "sandbox"

from core import stats as S

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Rules(unittest.TestCase):
    def test_vectors_and_the_typescript_register_are_current(self):
        r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "stats_vectors.py"), "--check"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_a_measure_is_a_formula_of_figures_never_code(self):
        for bad in ("__import__('os')", "sales; drop", "sales ** 2", "profit", "sales.real"):
            with self.assertRaises(ValueError, msg=bad):
                S.measure_names(bad)
        self.assertIsNone(S.evaluate("sales / orders", {"sales": 5, "orders": 0}), "dividing by zero shows nothing")
        self.assertIsNone(S.evaluate("sales * sales * sales", {"sales": 10 ** 7}), "too large for every device shows nothing")
        self.assertEqual(S.evaluate("(sales - refunds) / orders", {"sales": 1000, "refunds": 1, "orders": 2}), 500)

    def test_estimates_are_labelled_and_small_groups_hidden(self):
        r = S.what_if({"units": 100, "price_minor": 1000, "unit_cost_minor": 600, "staff_minor": 0}, {"price_bp": 1000})
        self.assertEqual((r["units"], r["estimate"]), (90, True))
        self.assertEqual([g["value"] for g in S.public_table([{"group": "a", "n": 4, "value": 9}, {"group": "b", "n": 5, "value": 9}])], [None, 9])
        self.assertEqual(S.scope([{"branch": None}], {"role": "m"}, {"m": "branch"}), [], "a branch role with no branch sees nothing")


class Service(unittest.TestCase):
    def setUp(self):
        os.environ["LYNK_MODE"] = "sandbox"
        from services.platform import Platform
        self.p = Platform(); self.p.register("m1", "RW"); self.a = self.p.stats

    def test_tiers_open_the_additions_in_order(self):
        self.assertIsNotNone(self.a.add_note("m1", "2026-03-01", "New road opened"))
        with self.assertRaises(PermissionError):
            self.a.cohorts("m1")
        self.p.billing.set_plan("m1", "lynkstat", "plus")
        self.assertEqual(self.a.cohorts("m1"), [])
        with self.assertRaises(PermissionError):
            self.a.define_measure("m1", "margin", "sales - cost_of_sales")
        self.p.billing.set_plan("m1", "lynkstat", "pro")
        self.a.define_measure("m1", "margin", "sales - cost_of_sales")
        self.assertIsInstance(self.a.measure("m1", "margin"), int)
        with self.assertRaises(ValueError):
            self.a.define_measure("m1", "bad", "open('x')")
        with self.assertRaises(PermissionError):
            self.a.schedule_export("m1", "week", "csv", "2026-01-05", "warehouse")
        self.p.billing.set_plan("m1", "lynkstat", "max")
        x = self.a.schedule_export("m1", "week", "csv", "2026-01-05", "warehouse")
        self.assertEqual(self.a.next_exports(x), ["2026-01-05", "2026-01-12", "2026-01-19"])

    def test_figures_come_from_the_records_and_cohorts_from_invoices(self):
        self.p.billing.set_plan("m1", "lynkstat", "plus"); self.p.billing.set_plan("m1", "lynkinv", "plus")
        self.p.invoicing.issue("m1", "C1", [{"name": "Work", "qty_milli": 1000, "unit_minor": 5000}], month="2026-01")
        self.p.invoicing.issue("m1", "C1", [{"name": "Work", "qty_milli": 1000, "unit_minor": 5000}], month="2026-02")
        f = self.a.figures("m1")
        self.assertEqual((f["orders"], f["invoices_open"]), (2, 2))
        self.assertTrue(all(isinstance(v, int) for v in f.values()))
        self.assertEqual(self.a.cohorts("m1"), [{"month": "2026-01", "size": 1, "back": [1]}])

    def test_scope_freshness_goals_and_public_reports(self):
        self.p.billing.set_plan("m1", "lynkstat", "pro")
        self.a.set_scope("m1", "branch_manager", "branch")
        rows = [{"branch": "kigali"}, {"branch": "huye"}]
        self.assertEqual(self.a.visible("m1", rows, {"role": "branch_manager", "branch": "huye"}), [{"branch": "huye"}])
        self.assertEqual(self.a.export_rows("m1", {"role": "branch_manager"})["figures"], {})
        self.a.reported("m1", "till-1", 100)
        fr = self.a.freshness("m1", "live", ["till-1", "till-2"], 103)
        self.assertEqual((fr["stale"], fr["missing"]), (False, ["till-2"]))
        self.a.set_goal("m1", "team-a", "sales", 1000)
        self.assertEqual(self.a.goal("m1", "team-a", "sales", 400, 5000), {"progress_bp": 4000, "on_track": False})
        self.assertIsNone(self.a.public_report("m1", [{"group": "x", "n": 2, "value": 1}])[0]["value"])


if __name__ == "__main__":
    unittest.main()
