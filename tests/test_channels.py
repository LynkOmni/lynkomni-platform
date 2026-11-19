"""Text, USSD and voice channels (BIZZ & DEVICE 48.17, interface phone.text): one engine, every page fits a USSD screen, a sale
needs the PIN, the commands are numbers so they work in every language, and the TypeScript port agrees with the vectors."""
import json, os, subprocess, sys, unittest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from core import channels as C, interfaces as I

EN = json.load(open(os.path.join(ROOT, "web", "pos", "strings.en.json"), encoding="utf-8"))
CTX = {"products": [["Cooking oil 1 L", "12,500", "2"], ["Sugar 1 kg", "1,400", "6"], ["Rice 1 kg", "1,500", "24"], ["Bread", "1,000", "12"], ["Soap", "500", "18"]],
       "today": [14, "42,000"], "receipt": "BP-14", "pin_ok": lambda t: t == "1234"}


class Channels(unittest.TestCase):
    def test_vectors_current(self):
        r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "channels_vectors.py"), "--check"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_every_page_fits_one_ussd_screen(self):
        for scr in C.SCREENS:
            st = {"screen": scr, "prod": 0, "qty": 999}
            text = C.render(C.page(st, CTX), EN)
            self.assertLessEqual(len(text), C.USSD_MAX, f"{scr}: {len(text)} characters")

    def test_a_sale_needs_the_pin_and_a_wrong_pin_records_nothing(self):
        st = C.start()
        for x in ("1", "3", "2"): st, ends, action = C.step(st, x, CTX); self.assertIsNone(action)
        _, ends, action = C.step(st, "0000", CTX); self.assertIsNone(action); self.assertFalse(ends)
        _, ends, action = C.step(st, "1234", CTX); self.assertEqual(action, {"sale": 2, "qty_milli": 2000}); self.assertTrue(ends)

    def test_commands_are_numbers_and_no_partner_request_is_offered(self):
        self.assertEqual(C.parse_sms("1 3 2 1234")["command"], "sell"); self.assertIsNone(C.parse_sms("SELL 3 2 1234"))
        self.assertNotIn("agent", C.MENU)
        self.assertIn("ch_help", EN); self.assertIn("1", EN["ch_help"])

    def test_answering_a_survey_by_basic_phone_is_numbers_only_and_every_page_fits(self):
        ctx = {"org": "Buea Regional Hospital", "minutes": 2, "anonymous": True, "questions": [{"id": "visit", "type": "rating", "text": "How was your visit today?"},
               {"id": "why", "type": "long", "text": "What should we do better?"}, {"id": "wait", "type": "choice", "text": "How long did you wait?", "choices": ["Under 5 min", "5 to 15 min", "Over 15 min"]}]}
        st = C.survey_start(); intro = C.render(C.survey_page(st, ctx), EN)
        self.assertIn("2", intro); self.assertLessEqual(len(intro), C.USSD_MAX)                    # "2 questions": a written question is not asked here
        st, ends, action = C.survey_step(st, "1", ctx)
        for page in (C.survey_page(st, ctx),): self.assertLessEqual(len(C.render(page, EN)), C.USSD_MAX)
        self.assertEqual(C.survey_step(st, "9", ctx)[0], st)                                   # a reply that does not fit is asked again
        st, ends, action = C.survey_step(st, "4", ctx); self.assertLessEqual(len(C.render(C.survey_page(st, ctx), EN)), C.USSD_MAX)
        st, ends, action = C.survey_step(st, "3", ctx)
        self.assertEqual((ends, action), (True, {"answers": [{"q": "visit", "number": 4}, {"q": "wait", "choice": "Over 15 min"}]}))
        self.assertEqual(C.survey_step(C.survey_start(), "0", ctx)[1:], (True, None))

    def test_joining_a_queue_by_basic_phone_is_numbers_only_and_every_page_fits(self):
        ctx = {"place": "Buea Regional Hospital", "sections": [["Laboratory", 12, 25, True], ["Pharmacy", 3, 8, True], ["Accounts", 0, 4, False]], "ticket": None}
        st = C.queue_start(); self.assertLessEqual(len(C.render(C.queue_page(st, ctx), EN)), C.USSD_MAX)
        self.assertEqual(C.queue_step(st, "3", ctx)[2], None)                                   # a closed section gives no ticket
        st, ends, action = C.queue_step(st, "1", ctx); self.assertEqual((ends, action), (False, {"join": 0}))
        ctx["ticket"] = {"number": "LAB-A2K9P2", "place": 13, "minutes": 27, "state": "waiting", "late_used": False}
        text = C.render(C.queue_page(st, ctx), EN); self.assertIn("LAB-A2K9P2", text); self.assertLessEqual(len(text), C.USSD_MAX)
        self.assertEqual(C.queue_step(st, "1", ctx)[2], {"running_late": True})
        ctx["ticket"]["late_used"] = True; self.assertIsNone(C.queue_step(st, "1", ctx)[2]); self.assertNotIn("ch_q_late", [k for k, _ in C.queue_page(st, ctx)])   # once per ticket
        st2, ends, action = C.queue_step(st, "2", ctx); self.assertEqual((ends, action), (True, {"leave": True}))
        ctx["ticket"].update(state="called", counter="Room 3"); self.assertIn("Room 3", C.render(C.queue_page(C.queue_start(True), ctx), EN))
        self.assertEqual(C.parse_queue_sms("2", 3), {"command": "join", "section": 1}); self.assertEqual(C.parse_queue_sms("8", 3), {"command": "running_late"})
        self.assertEqual(C.parse_queue_sms("9", 3), {"command": "leave"}); self.assertIsNone(C.parse_queue_sms("JOIN", 3)); self.assertIsNone(C.parse_queue_sms("5", 3))
        self.assertNotRegex(json.dumps(C.queue_page(st, ctx)), "name\\\": \\\"[A-Z][a-z]+ [A-Z]")   # a ticket number, never a person's name

    def test_the_basic_phone_uses_this_channel(self):
        self.assertEqual(I.DEVICES["basic-phone"]["non_touch"], "phone.text")
        self.assertEqual(I.choose({"registered": {"device": "basic-phone", "version": "non_touch"}})["interface"], "phone.text")


if __name__ == "__main__":
    unittest.main()
