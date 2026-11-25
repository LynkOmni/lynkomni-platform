"""LynkHR, LynkProject and LynkFiles' flows in the cloud (build section 4B step 2, SIX SERVICES UPDATE 69.3, 69.4, 69.7 and 69.12):
the services follow their rules, every event fits contract version 19, and no event carries a name, contact or anybody's words."""
import json, os, unittest
os.environ["LYNK_MODE"] = "sandbox"
from services.platform import Platform

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
V19 = json.load(open(os.path.join(ROOT, "contract", "event-payloads.v19.json"), encoding="utf-8"))["events"]
NEW = set(V19) - set(json.load(open(os.path.join(ROOT, "contract", "event-payloads.v18.json"), encoding="utf-8"))["events"])
PDF = b"%PDF-1.7\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF"


class PeopleProjects(unittest.TestCase):
    def setUp(self):
        os.environ["LYNK_MODE"] = "sandbox"
        self.p = Platform(); self.p.register("m1", "RW")

    def plans(self, tier):
        for fam in ("lynkhr", "lynkproject", "lynkfiles", "lynkinv", "lynkacc", "lynkcrm"):
            self.p.billing.set_plan("m1", fam, tier)

    def test_free_has_its_limits_and_paid_features_wait_for_their_plan(self):
        for i in range(5):
            self.p.hr.add("m1", "owner", "casual", "2026-11-01", f"Person {i}")
        with self.assertRaises(PermissionError):
            self.p.hr.add("m1", "owner", "casual", "2026-11-01", "Sixth")
        with self.assertRaises(PermissionError):
            self.p.hr.open_cycle("m1", ["self"], "2026-12-01", "hr1")
        pid = self.p.projects.create("m1", "owner", "Launch")
        with self.assertRaises(PermissionError):
            self.p.projects.log_time("m1", pid, "u1", 30)

    def test_staff_records_and_special_details(self):
        self.plans("pro")
        sid = self.p.hr.add("m1", "owner", "permanent", "2026-01-31", "Grace", salary=200000)
        self.assertNotIn("salary", self.p.hr.record("m1", sid, "staff"))
        self.assertIn("salary", self.p.hr.record("m1", sid, "staff", is_self=True), "the person always sees their own record")
        with self.assertRaises(PermissionError):
            self.p.hr.set_special("m1", sid, "health", True, "hr1")                       # only where the country's pack allows it
        self.assertEqual(self.p.hr._staff("m1", sid)["probation_end"], "2026-04-30")

    def test_leave_pay_cases_and_lynkassist(self):
        self.plans("pro")
        a = self.p.hr.add("m1", "owner", "permanent", "2026-01-01", "Ana")
        b = self.p.hr.add("m1", "owner", "permanent", "2026-01-01", "Ben")
        self.p.hr.set_entitlement("m1", a, "annual", 10)
        with self.assertRaises(ValueError):
            self.p.hr.request_leave("m1", a, "annual", 12, "2026-12-01", "2026-12-06")
        q = self.p.hr.request_leave("m1", a, "annual", 4, "2026-12-01", "2026-12-02", team=[a, b])
        with self.assertRaises(PermissionError):
            self.p.hr.answer_leave("m1", q["request"], a, "approved")
        self.p.hr.answer_leave("m1", q["request"], "manager1", "approved")
        self.p.hr.set_entitlement("m1", b, "annual", 10)
        self.assertEqual(self.p.hr.request_leave("m1", b, "annual", 2, "2026-12-02", "2026-12-02", team=[a, b])["clashes"], ["2026-12-02"],
                         "a clash is shown, never a refusal")
        c = self.p.hr.propose_pay("m1", "hr1", a, "pay_review", 30000)
        with self.assertRaises(PermissionError):
            self.p.hr.approve_pay("m1", c, "hr1", budget=100000)
        with self.assertRaises(PermissionError):
            self.p.hr.approve_pay("m1", c, "owner", budget=10000)                       # over the budget needs a third person
        self.p.hr.approve_pay("m1", c, "owner", budget=10000, second="director1")
        case = self.p.hr.open_case("m1", "grievance", a)
        with self.assertRaises(PermissionError):
            self.p.hr.case("m1", case, "manager")
        self.assertEqual(self.p.hr.case("m1", case, "hr")["step"], "opened")
        self.p.hr.open_case("m1", "concern", anonymous=True)
        for act in ("hire", "dismiss", "score_person", "set_pay"):
            with self.assertRaises(PermissionError):
                self.p.hr.assist("m1", act)

    def test_leaving_waits_for_its_musts(self):
        self.plans("plus")
        sid = self.p.hr.add("m1", "owner", "permanent", "2025-01-01", "Eric")
        with self.assertRaises(PermissionError):
            self.p.hr.step_done("m1", sid, "leaving", "final_pay_figures", "hr1")
        with self.assertRaises(PermissionError):
            self.p.hr.leave_org("m1", sid, "2026-12-31", "hr1")
        for step in ("notice_recorded", "equipment_back", "access_closed", "final_pay_figures"):
            self.p.hr.step_done("m1", sid, "leaving", step, "hr1")
        self.p.hr.leave_org("m1", sid, "2026-12-31", "hr1")

    def test_guests_and_change_requests(self):
        self.plans("pro")
        pid = self.p.projects.create("m1", "owner", "Audit", budget=100)
        self.p.projects.add_task("m1", pid, "owner", "Collect files")
        self.p.projects.invite_guest("m1", pid, "client1")
        self.assertEqual(len(self.p.projects.guest_view("m1", "client1", pid, "tasks")), 1)
        with self.assertRaises(PermissionError):
            self.p.projects.guest_view("m1", "client1", pid, "budget")
        r = self.p.projects.raise_change("m1", pid, "u1", cost_change=5000)
        with self.assertRaises(PermissionError):
            self.p.projects.decide_change("m1", r, "u1", "accepted")
        self.p.projects.decide_change("m1", r, "owner", "accepted")

    def test_events_fit_the_contract_and_carry_nothing_personal(self):
        self.plans("pro")
        sid = self.p.hr.add("m1", "owner", "permanent", "2026-01-01", "Zawadi Uwimana", salary=150000)
        self.p.hr.add("m1", "owner", "permanent", "2026-01-01", "Second person", salary=90000)   # the period's total is never one person's pay
        self.p.hr.set_entitlement("m1", sid, "annual", 10)
        q = self.p.hr.request_leave("m1", sid, "annual", 2, "2026-12-01", "2026-12-01")
        self.p.hr.answer_leave("m1", q["request"], "manager1", "approved")
        cyc = self.p.hr.open_cycle("m1", ["self", "peer"], "2026-12-15", "hr1")
        self.p.hr.answer_review("m1", cyc, sid, "peer", "a" * 64)
        self.p.hr.sign_off("m1", cyc, sid, "manager1")
        self.p.hr.open_case("m1", "grievance", sid)
        self.p.hr.payroll("m1", "2026-11", "hr1")
        pid = self.p.projects.create("m1", "owner", "Secret product launch", method="agile")
        t = self.p.projects.add_task("m1", pid, "owner", "Write the confidential plan", due=20500, owner="u1")
        self.p.projects.move("m1", t, "doing", "u1")
        self.p.projects.milestone("m1", pid, "beta", 20510, reached=True)
        self.p.projects.log_time("m1", pid, "u1", 45, rate=10000)
        doc = self.p.files.store("m1", "owner", "staff", sid, "contract", PDF)
        self.p.files.start_route("m1", doc, "owner", ["manager1"])
        self.p.files.request_document("m1", "hr1", "id_document", "2026-12-01")
        seen = set()
        for e in self.p.c.store.since("m1"):
            if e["type"] not in NEW:
                continue
            seen.add(e["type"])
            spec = V19[e["type"]]["payload"]
            self.assertTrue(set(spec["required"]) <= set(e["payload"]) <= set(spec["properties"]), (e["type"], e["payload"]))
            text = json.dumps(e["payload"])
            for secret in ("Zawadi", "Uwimana", "Secret", "confidential", "150000"):
                self.assertNotIn(secret, text, e["type"])
        self.assertGreaterEqual(len(seen), 15)

    def test_staff_projects_and_tasks_move_in_with_a_check_report(self):
        from core import enterprise as E
        r = E.check("staff", ["ref", "name", "worker_kind", "start_on", "salary"], [["S1", "A", "permanent", "2026-01-05", "1200.50"], ["S2", "B", "casual", "2026-13-01", "x"]])
        self.assertEqual({(e["row"], e["issue"]) for e in r["errors"]}, {(2, "bad_date"), (2, "bad_amount")})
        r = E.check("tasks", ["ref", "project_ref", "title"], [["T1", "P9", "Paint"]], known={"projects": {"P1"}})
        self.assertEqual(r["errors"], [{"row": 1, "column": "project_ref", "issue": "unknown_ref"}])


if __name__ == "__main__":
    unittest.main()
