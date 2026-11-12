"""LynkAttend, LynkQueue and LynkSurvey rules (NEW UPDATE 4, owner locked 2026-11-11, master blueprint section 63): the owner's
examples, the never-twice rules and the shared vectors the TypeScript ports are checked against."""
import os, subprocess, sys, unittest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from core import attendance as A, queue_tickets as Q, surveys as S  # noqa: E402


class Attendance(unittest.TestCase):
    def test_the_owners_idcn_examples(self):
        for full, want in (("123456789", "456789"), ("A6F87399", "687399"), ("2456HYOE99", "245699"), ("R4279", "427900")):
            self.assertEqual(A.idcn(full), want, full)
        self.assertIsNone(A.idcn("DYY87HIO"))           # 2 digits: fewer than 4, so another ID document is registered

    def test_pins_are_never_easy_never_twice_and_groups_warn_at_90(self):
        for p in ("111111", "123456", "654321", "121212", "123123"): self.assertTrue(A.is_easy_pin(p), p)
        self.assertFalse(A.is_easy_pin("482915"))
        draws = iter([111111, 482915, 482915, 908172])
        taken = {"482915"}
        self.assertEqual(A.new_pin(lambda: next(draws), taken), "908172")   # easy and taken PINs are passed over
        self.assertTrue(A.pin_group_warning(A.PIN_GROUP_SIZE * 9 // 10 + 1))
        self.assertEqual(A.EASY_PIN_COUNT, sum(1 for n in range(10 ** 6) if A.is_easy_pin(f"{n:06d}")))

    def test_the_door_runs_the_set_in_order_and_marks_every_backup(self):
        self.assertEqual(A.means_of("face_finger_idcn"), ["face", "finger", "idcn"])
        out = A.door("face_idcn", ["fail", "fail", "fail", "ok"])
        self.assertEqual((out["result"], out["means"], out["backup_from"]), ("in", "idcn", "face_failed"))
        self.assertEqual(A.door("idcn", ["fail"] * 5)["result"], "pin_blocked")
        self.assertEqual(A.door("face_finger_idcn", ["ok"], broken=("face",))["backup_from"], "face_not_working")
        self.assertNotIn("ben", A.checker_choices(["ama", "ben"], "ben"))
        self.assertEqual(A.checker_flags(False), ["checker_not_checked_in"])
        self.assertEqual(A.sets_allowed(False, False), ["idcn"])


class Queue(unittest.TestCase):
    def test_one_billion_codes_from_the_lynk_alphabet_never_twice(self):
        self.assertEqual(Q.CAPACITY, 1_073_741_824)
        self.assertEqual((Q.code(0), Q.code(Q.CAPACITY - 1)), ("222222", "ZZZZZZ"))
        for bad in "O0I1": self.assertNotIn(bad, Q.ALPHABET)
        self.assertEqual(Q.ticket_number("LAB", "A2K9P2"), "LAB-A2K9P2")
        self.assertIsNone(Q.next_code("ZZZZZZ"))         # the section then gets a new section code
        self.assertFalse(Q.rude(Q.next_code("FUCKZZ")))

    def test_staff_never_choose_and_the_order_is_fair(self):
        w = [{"id": "a", "seq": 1}, {"id": "b", "seq": 2, "priority": True}, {"id": "c", "seq": 3}]
        self.assertEqual(Q.pick_next(w, 0, 500), "a")
        self.assertEqual(Q.pick_next(w, 3, 500), "b")
        self.assertEqual(Q.put_back(["a", "b", "c", "d", "e"], "a", 100, 110), ["b", "c", "d", "a", "e"])
        self.assertIsNone(Q.put_back(["a", "b"], "a", 100, 120))


class Survey(unittest.TestCase):
    def test_sample_size_margin_and_the_group_of_five(self):
        self.assertEqual(S.sample_size(5), 385)
        self.assertEqual(S.margin(54, 600), 40)           # 54% (±4.0%)
        self.assertFalse(S.can_show(4)); self.assertTrue(S.can_show(5))
        self.assertEqual(S.may_answer("open", True), "already_answered")
        self.assertEqual(S.real_answer_flags(5, 5, False, 1, False), ["too_fast"])


class CountryPacks(unittest.TestCase):
    def test_every_pack_carries_the_people_settings_and_false_removes_a_means(self):
        r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "country_people.py"), "--check"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(A.sets_for_country({"people": {"attendance": {"face_allowed": None, "finger_allowed": False}}}), ["face_idcn", "idcn"])
        self.assertEqual(A.sets_for_country({}), list(A.SETS))


class Vectors(unittest.TestCase):
    def test_vectors_are_current(self):
        r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "people_vectors.py"), "--check"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


if __name__ == "__main__": unittest.main()
