"""The conversation engine (CHAT UPDATE, master blueprint 74; build section 4 step C1): catalog/chat.v1.json read through
core/chat.py and ts/src/chat.ts with shared vectors. Chat is customer-and-business and support only; only the five states;
live signs carry words and are never stored; card numbers and codes are masked before a message is queued; every card comes
from its own service through a link in catalog/connections.v1.json; every tone comes from the design tokens."""
import json, os, subprocess, sys, unittest
from core import build_sections as b, chat as C, connections as K

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOKENS = json.load(open(os.path.join(ROOT, "design", "tokens.v1.json"), encoding="utf-8"))["sounds"]
ORDER = [str(n) for n in b.ORDER]


class Chat(unittest.TestCase):
    def test_vectors_and_the_typescript_register_are_current(self):
        r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "chat_vectors.py"), "--check"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_only_customer_business_storefront_and_support(self):
        self.assertEqual(sorted(C.KINDS), ["customer_business", "storefront", "support"])
        for never in ("personal_chat", "group_chat", "staff_to_staff", "end_to_end_claim", "customer_last_seen", "assistant_as_person", "adverts_in_chat"):
            self.assertIn(never, C.CHAT["never"])
        self.assertIn("never called end-to-end", C.CHAT["rule"].lower())

    def test_the_five_states_and_who_writes_them(self):
        self.assertEqual(list(C.STATES), ["queued", "sent", "accepted", "confirmed", "failed"])
        st = C.CHAT["states"]
        self.assertEqual(sorted(st["device_writes"] + st["cloud_writes"]), sorted(C.STATES))
        self.assertFalse(C.can_move("sent", "confirmed", "device"), "a device never claims the other side saw it")
        self.assertTrue(C.can_move("accepted", "confirmed", "cloud"))
        self.assertEqual(C.shown_state("confirmed", "customer", False), "accepted")
        self.assertEqual(C.shown_state("confirmed", "business", False), "confirmed", "a business's team always shows seen")

    def test_live_signs_always_have_words_and_are_never_stored(self):
        for k, s in C.SIGNS.items():
            self.assertTrue(s["words"].startswith("ch_"), k)
            self.assertIn(s["motion"], ("dots", "wave", "pulse", "progress", "none"), k)
        self.assertTrue(C.CHAT["live_signs"]["needs_online"])
        self.assertIn("never stored", C.CHAT["live_signs"]["rule"])
        self.assertIsNone(C.live_sign("staff_replying", "business"), "'Ama is replying' is for the team only")
        self.assertEqual(C.live_sign("typing", "customer", reduced_motion=True)["motion"], "none")
        self.assertIsNone(C.live_sign("typing", "customer", sender_allows=False))
        self.assertIn("assistant", C.SIGNS["assist_writing"]["from"])

    def test_every_tone_and_vibration_comes_from_the_design_tokens(self):
        for k, e in C.SOUND_EVENTS.items():
            if e["tone"] not in (None, "notification"):
                self.assertIn(e["tone"], TOKENS["tones"], k)
            if e["vibrate"] is not None:
                self.assertIn(e["vibrate"], TOKENS["vibrate"], k)
        self.assertIsNone(C.SOUND_EVENTS["typing"]["tone"])
        pats = [tuple(TOKENS["vibrate"][e["vibrate"]]) for k, e in C.SOUND_EVENTS.items() if e["vibrate"] and k != "counter_new_chat"]
        self.assertEqual(len({p for p in pats}), len(set(e["vibrate"] for k, e in C.SOUND_EVENTS.items() if e["vibrate"] and k != "counter_new_chat")),
                         "each vibration pattern differs, so they can be told apart in a pocket")
        for screen in ("payment", "cash_count", "signature", "ballot", "pin"):
            self.assertIn(screen, C.CHAT["sounds"]["protected_screens"])

    def test_masking_never_lets_a_card_number_or_code_through(self):
        out = C.mask("card 4111 1111 1111 1111, PIN 4821", ["pin"])
        self.assertNotIn("4111 1111", out["text"]); self.assertNotIn("4821", out["text"]); self.assertIn("1111", out["text"])
        self.assertEqual(out["found"], ["card", "code"])
        self.assertEqual(C.mask("I paid 5000 RWF")["text"], "I paid 5000 RWF", "an amount is not a code")

    def test_every_card_comes_from_its_service_through_a_link(self):
        for k, c in C.CARDS.items():
            link = K.LINKS.get(c["link"])
            self.assertIsNotNone(link, f"{k}: link {c['link']} is not in catalog/connections.v1.json")
            self.assertEqual((link["from"], link["to"]), (c["service"], "lynkchat"), k)
            self.assertIn(c["build_section"], ORDER, k)
            self.assertIn(c["offline"], ("opens", "not_offered"), k)
            self.assertLessEqual(ORDER.index(c["build_section"]), ORDER.index(str(link["build_section"])) if c["build_section"] != "3" else 99, k)
        for never in ("ballot", "card_details", "credentials"):
            self.assertIn(never, C.CHAT["cards"]["never"]); self.assertNotIn(never, C.CARDS)
        self.assertEqual(set(C.CHAT["chat_about"]["records"]) - set(C.CARDS), {"customer"})
        self.assertEqual(K.LINKS[C.CHAT["cards"]["panels"]["customer"]["link"]]["from"], "lynkcrm")

    def test_routing_reasons_cover_every_answer(self):
        reasons = set(C.CHAT["routing"]["reasons"])
        vec = json.load(open(os.path.join(ROOT, "contract", "vectors", "chat.v1.json"), encoding="utf-8"))
        for case in vec["route"] + vec["team"]:
            self.assertIn(case["expect"]["reason"], reasons)
        self.assertEqual(C.route_support({"topic": "fraud"}, [])["desk"], "security", "the fast lane goes straight to its desk")
        self.assertEqual(C.route_support({"topic": "orders"}, [])["to"], "assistant", "LynkAssist answers first")

    def test_offline_never_offers_money_or_partner_steps(self):
        for w in ("payment", "provider_booking", "partner_request"):
            self.assertEqual(C.offline(w), "not_offered", w)
        self.assertEqual(C.offline("write"), "queued")
        self.assertFalse(C.card_action("invoice", "pay", online=False))
        self.assertTrue(C.card_action("invoice", "chat_about", online=False))


if __name__ == "__main__":
    unittest.main()
