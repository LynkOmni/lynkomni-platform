"""LynkAssist's skills in LynkHR, LynkProject and LynkFiles (build section 4B, ASSIST UPDATE 75.9): every skill is in the register and
built; drafts and suggestions never send, sign, share, enrol or change anything without the person's Confirm; it never decides about
a person."""
import os, unittest
os.environ["LYNK_MODE"] = "sandbox"
from services import assist_register as AR

PDF = b"%PDF-1.7\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF"


class WorkSkills(unittest.TestCase):
    def setUp(self):
        os.environ["LYNK_MODE"] = "sandbox"
        from services.platform import Platform
        from services.assist_work import WorkAssist
        self.p = Platform(); self.p.register("m1", "RW")
        for fam in ("lynkhr", "lynkproject", "lynkfiles"):
            self.p.billing.set_plan("m1", fam, "pro")
        self.a = WorkAssist(self.p, "m1", "u0", "u0")

    def test_every_skill_is_registered_built_and_in_its_area(self):
        from services.assist_work import WORK_ACTIONS
        for a in WORK_ACTIONS:
            self.assertIn(a, AR.ACTIONS, a)
            self.assertEqual(AR.ACTIONS[a]["status"], "built", a)
            self.assertIn(AR.ACTIONS[a]["area"], ("work", "projects", "files"), a)
        for never in ("hire", "dismiss", "set_pay", "score_person", "approve_time", "send_invoice"):
            self.assertNotIn(never, AR.ACTIONS, "deciding about a person is never a LynkAssist action")

    def test_drafts_need_confirm_and_never_send(self):
        self.assertEqual(self.a.do("d1", "u0", "owner", "hr_draft_letter", kind="offer")["state"], "not_done", "a draft needs Confirm")
        r = self.a.do("d1", "u0", "owner", "hr_draft_letter", confirmed=True, kind="offer")["result"]
        self.assertEqual((r["label"], r["sent"]), ("draft", False))
        t = self.a.do("d1", "u0", "owner", "hr_suggest_training", confirmed=True, from_role=["food safety"])["result"]
        self.assertEqual((t["enrolled"], t["who_decides"]), (False, "manager"))
        self.assertEqual(self.a.do("d1", "u0", "staff", "hr_suggest_training", confirmed=True)["state"], "not_done", "staff may not use it")

    def test_answers_come_only_from_the_handbook(self):
        r = self.a.do("d1", "u0", "staff", "hr_answer_from_handbook", question="How many sick days", handbook=["Sick days need a note after two days."])["result"]
        self.assertTrue(r["found"])
        self.assertFalse(self.a.do("d1", "u0", "staff", "hr_answer_from_handbook", question="pension rules", handbook=["Sick days need a note."])["result"]["found"])

    def test_project_and_file_skills(self):
        pid = self.p.projects.create("m1", "u0", "Fair")
        r = self.a.do("d1", "u0", "owner", "pj_actions_from_minutes", confirmed=True, project=pid, actions=[{"title": "Book hall", "owner": "u2"}])["result"]
        self.assertEqual(len(r["tasks"]), 1)
        self.assertEqual(self.a.do("d1", "u0", "owner", "pj_status_report", project=pid)["result"]["tasks"], 1)
        s = self.a.do("d1", "u0", "owner", "pj_suggest_date", confirmed=True, project=pid)["result"]
        self.assertEqual((s["label"], s["changed"]), ("suggestion", False))
        self.assertEqual(self.a.do("d1", "u0", "staff", "files_key_dates", text="Starts 2026-12-01, renews 2027-12-01.")["result"]["dates"], ["2026-12-01", "2027-12-01"])
        f = self.a.do("d1", "u0", "staff", "files_file_scan", confirmed=True, record_kind="staff", record_id="s1", data=PDF)["result"]
        self.assertTrue(f["document"])


if __name__ == "__main__":
    unittest.main()
