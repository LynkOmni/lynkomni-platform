"""Sign-up, sign-in, help and notifications on phones with no apps (MASTER UPDATE; build section 3)."""
import json, os, subprocess, sys, unittest
from identity import basic_phone as B
from identity.offline import may_open_account

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
V = json.load(open(os.path.join(ROOT, "contract", "vectors", "basicphone.v1.json"), encoding="utf-8"))


class BasicPhone(unittest.TestCase):
    def test_vectors_are_current(self):
        r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "basicphone_vectors.py"), "--check"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_a_number_alone_never_opens_an_account(self):
        self.assertFalse(may_open_account({"phone"}))
        self.assertTrue(may_open_account({"phone", "device_pin"}))

    def test_no_page_ever_shows_a_pin(self):
        for steps in V["sessions"]:
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
        for steps in V["sessions"]:
            for st in steps:
                self.assertLessEqual(len(render(st["page"], words)), USSD_MAX, st["page"])

    def test_sign_up_asks_age_first_and_never_keeps_the_pin(self):
        s = B.start()
        s, _, _ = B.step(s, "2", {})
        self.assertEqual(s["screen"], "age")
        ctx = {"username_check": lambda u: None, "taken": lambda u: False}
        for t in ("1", "ama.shop", "4826", "4826"):
            s, _, _ = B.step(s, t, ctx)
        s, ends, action = B.step(s, "1", ctx)
        self.assertTrue(ends); self.assertEqual(action["create"]["username"], "ama.shop")
        self.assertIsNone(s["pin"], "the PIN leaves with the request and is not kept in the session")

    def test_text_notification_carries_no_secret(self):
        from services.messages import check_content
        for c in V["texts"]:
            check_content({"text": c["text"]})


if __name__ == "__main__":
    unittest.main()
