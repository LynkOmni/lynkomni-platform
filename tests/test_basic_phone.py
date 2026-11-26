"""Sign-up, sign-in, help and notifications on phones with no apps (MASTER UPDATE; build section 3)."""
import json, os, subprocess, sys, unittest
from identity import basic_phone as B
from identity.offline import may_open_account

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
V = json.load(open(os.path.join(ROOT, "contract", "vectors", "basicphone.v1.json"), encoding="utf-8"))
SESSIONS = [x if isinstance(x, list) else x["steps"] for x in V["sessions"]]


class BasicPhone(unittest.TestCase):
    def test_vectors_are_current(self):
        r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "basicphone_vectors.py"), "--check"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_a_number_alone_never_opens_an_account(self):
        self.assertFalse(may_open_account({"phone"}))
        self.assertTrue(may_open_account({"phone", "device_pin"}))

    def test_no_page_ever_shows_a_pin(self):
        for steps in SESSIONS:
            for st in steps:
                text = json.dumps(st["page"])
                self.assertNotIn(V["pin"], text)
                self.assertNotIn("4826", text)
                if V["ctx"]["recovery"] in text:
                    self.assertEqual(st["screen"], "created", "the recovery code shows once, right after sign-up")

    def test_pages_fit_a_ussd_screen_in_english(self):
        en = json.load(open(os.path.join(ROOT, "web", "emulators", "button-phone", "strings.en.json"), encoding="utf-8"))
        shell = json.load(open(os.path.join(ROOT, "web", "shell", "strings.en.json"), encoding="utf-8"))
        pos = json.load(open(os.path.join(ROOT, "web", "pos", "strings.en.json"), encoding="utf-8"))
        words = {**shell, **pos, **en}
        from core.channels import render, USSD_MAX
        for steps in SESSIONS:
            for st in steps:
                self.assertLessEqual(len(render(st["page"], words)), USSD_MAX, st["page"])

    def test_sign_up_asks_age_first_and_never_keeps_the_pin(self):
        s = B.start()
        s, _, _ = B.step(s, "2", {})
        self.assertEqual(s["screen"], "age")
        ctx = {"age": 18, "today": (2026, 11, 26), "username_check": lambda u: None, "taken": lambda u: False}
        for t in ("1990", "5", "14", "1", "ama.shop", "4826", "4826"):
            s, _, _ = B.step(s, t, ctx)
        s, ends, action = B.step(s, "1", ctx)
        self.assertTrue(ends); self.assertEqual(action["create"]["username"], "ama.shop")
        self.assertIsNone(s["pin"], "the PIN leaves with the request and is not kept in the session")

    def test_the_neutral_age_gate_never_says_the_age_or_keeps_the_date(self):
        ctx = {"age": 21, "today": (2026, 11, 26)}
        s = B.step(B.start(), "2", ctx)[0]
        for t in ("2006", "1", "1"):
            s, _, _ = B.step(s, t, ctx)
            self.assertNotIn('"age": 21', json.dumps(B.page(s, ctx)), "the age needed is never shown")
        self.assertEqual(s["screen"], "age_confirm", "Is this right? once before the check")
        s, ends, action = B.step(s, "1", ctx)
        self.assertEqual((s["screen"], ends, action), ("too_young", True, {"age_refused": True}))
        self.assertIsNone(s["birth"], "the date is forgotten at once")
        self.assertNotIn("21", json.dumps(B.page(s, ctx)))
        again, ends, _ = B.step(B.start(), "2", dict(ctx, age_blocked=True))
        self.assertEqual((again["screen"], ends), ("too_young", True), "no retry from the same number until an ID check clears it")

    def test_reset_my_pin_by_menu_asks_the_cloud_and_never_resets_at_once(self):
        s = B.start()
        s, _, _ = B.step(s, "3", {})
        s, _, _ = B.step(s, "3", {})
        self.assertEqual(s["screen"], "pin_reset")
        menu, ends, action = B.step(s, "1", {})
        self.assertTrue(ends); self.assertEqual(action, {"pin_reset": "menu"})
        self.assertEqual(menu["screen"], "pin_reset_sent")
        shop, ends, action = B.step(s, "2", {})
        self.assertTrue(ends); self.assertIsNone(action, "at a shop the ID check happens there, not by menu")
        self.assertEqual(shop["screen"], "pin_reset_shop")

    def test_text_notification_carries_no_secret(self):
        from services.messages import check_content
        for c in V["texts"]:
            check_content({"text": c["text"]})


if __name__ == "__main__":
    unittest.main()
