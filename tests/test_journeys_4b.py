"""The cross-service journeys of build section 4B run end to end on the real platform (CONNECT UPDATE 71.2, SIX SERVICES UPDATE 69):
hire to work (hr-files, attend-hr, hr-acc, academy-hr), document to record (files-crm, files-acc) and meeting to action
(files-project, project-inv, with project-acc)."""
import os, unittest
os.environ["LYNK_MODE"] = "sandbox"
from core import accounts as AC
from services.platform import Platform

PDF = b"%PDF-1.7\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF"


class Journeys4B(unittest.TestCase):
    def setUp(self):
        os.environ["LYNK_MODE"] = "sandbox"
        self.p = Platform(); self.p.register("m1", "RW")
        for fam in ("lynkhr", "lynkproject", "lynkfiles", "lynkinv", "lynkcrm", "lynkacc"):
            self.p.billing.set_plan("m1", fam, "pro")

    def tb(self):
        e = self.p.accountant.journal("m1")
        self.assertTrue(AC.balanced(e), "the books balance at every step")
        return AC.trial_balance(e)

    def test_hire_to_work(self):
        hr = self.p.hr
        sid = hr.add("m1", "owner", "permanent", "2026-11-02", "Aline", salary=300000)
        self.assertTrue(sid.startswith("LOSTF-"))
        doc = self.p.files.store("m1", "owner", "staff", sid, "contract", PDF)
        rid, (tok,) = self.p.files.request_signatures("m1", doc, "owner", ["Aline, aline@example.org"])
        self.p.files.sign(tok, self.p.files.open("m1", doc, "owner")["sha256"])
        self.assertEqual(self.p.files.state(rid), "completed", "hr-files: the contract is signed and kept in the staff file")
        hr.step_done("m1", sid, "joining", "contract_signed", "owner")
        with self.assertRaises(PermissionError):
            hr.from_attendance("m1", sid, "sick", 2, "2026-11-10")                     # attend-hr is off until the business switches it on
        self.p.shared.set_link("m1", "attend-hr", True, "owner")
        hr.set_entitlement("m1", sid, "sick", 20)
        q = hr.from_attendance("m1", sid, "sick", 2, "2026-11-10")
        self.assertEqual(hr.answer_leave("m1", q["request"], "manager1", "approved"), "approved", "attend-hr: an absence becomes leave")
        self.assertEqual(hr.balance("m1", sid, "sick"), 18)
        hr.course_completed("m1", sid, "course:food-safety", person_agreed=True)
        self.assertIn("course:food-safety", hr.record("m1", sid, "manager")["skills"], "academy-hr: training joins the skills record")
        run = hr.payroll("m1", "2026-11", "hr1")
        self.assertEqual((run["gross"], run["draft"]["state"]), (300000, "awaiting_approval"), "hr-acc: payroll is a draft a second person posts")
        with self.assertRaises(PermissionError):
            self.p.books.approve_journal("m1", run["draft"]["pending"], "hr1")
        self.p.books.approve_journal("m1", run["draft"]["pending"], "owner")
        tb = self.tb()
        self.assertEqual((tb["6300"], tb["2400"]), (300000, 300000), "wages and wages owed (each on its own side)")

    def test_document_to_record(self):
        cust = self.p.crm.create("m1", "u1", "customer", name="Amina")
        doc = self.p.files.store("m1", "owner", "customer", cust, "contract", PDF)
        rid, (tok,) = self.p.files.request_signatures("m1", doc, "owner", ["Amina, amina@example.org"])
        self.p.files.sign(tok, self.p.files.open("m1", doc, "owner")["sha256"])
        self.assertEqual(self.p.files.state(rid), "completed", "files-crm: the signed document is filed on the customer's record")
        route = self.p.files.start_route("m1", doc, "owner", ["manager1", "director1"])
        with self.assertRaises(PermissionError):
            self.p.files.answer_route("m1", route, "director1", "approved")               # each step is answered by its named approver, in order
        self.p.files.answer_route("m1", route, "manager1", "approved")
        self.assertEqual(self.p.files.answer_route("m1", route, "director1", "approved"), "approved")
        bill = self.p.files.store("m1", "owner", "bill", "b-1", "bill", PDF)
        self.assertTrue(bill)
        self.p.books.record_bill("m1", "owner", 45000, source="photo")
        self.assertEqual(self.tb()["2000"], 45000, "files-acc: a filed bill becomes a bill to pay, owed to the supplier")
        req = self.p.files.request_document("m1", "hr1", "certificate", "2026-12-01")
        with self.assertRaises(PermissionError):
            self.p.files.answer_request("m1", req, "hr1", result="checked")
        self.p.files.answer_request("m1", req, "staff1", PDF)
        self.assertEqual(self.p.files.answer_request("m1", req, "hr1", result="checked"), "checked")

    def test_meeting_to_action(self):
        pj = self.p.projects
        cust = self.p.crm.create("m1", "u1", "customer", name="Client")
        pid = pj.create("m1", "owner", "Shop refit", template="shop_refit", budget=500000)
        tasks = pj.actions_from_minutes("m1", pid, "owner", [{"title": "Order shelves", "owner": "u2"}, {"title": "Paint wall", "owner": "u3"}])
        self.assertTrue(all(t.startswith("LOTSK-") for t in tasks), "files-project: minutes become tasks for named people")
        pj.wait_on("m1", tasks[1], tasks[0])
        with self.assertRaises(ValueError):
            pj.wait_on("m1", tasks[0], tasks[1])                                         # never in a circle
        pj.move("m1", tasks[1], "doing", "u3")
        with self.assertRaises(PermissionError):
            pj.move("m1", tasks[1], "done", "u3")                                        # it waits on the shelves
        pj.log_time("m1", pid, "u2", 90, rate=15000, task=tasks[0])
        with self.assertRaises(PermissionError):
            pj.answer_sheet("m1", "u2", "u2")
        pj.answer_sheet("m1", "u2", "manager1")
        billed = pj.bill_time("m1", pid, cust)
        self.assertEqual((billed["minutes"], billed["amount"]), (90, 22500))
        self.assertIsNone(pj.bill_time("m1", pid, cust), "project-inv: time is billed once")
        self.assertEqual(self.tb()["1100"], self.p.invoicing.outstanding(billed["invoice"]), "the invoice, with its tax, is owed by the customer")
        pj.add_cost("m1", pid, "owner", 120000)
        self.assertEqual(pj.money("m1", pid), {"spent": 120000, "left": 380000, "over": 0, "profit": -97500}, "project-acc: costs count against the budget")


if __name__ == "__main__":
    unittest.main()
