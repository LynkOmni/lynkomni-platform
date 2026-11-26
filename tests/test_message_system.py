"""The message system (CONNECT UPDATE 71.7; catalog/messages.v1.json "system"; section 4 row 71.9 step 4):
smart, role and rota routing, role inboxes, urgent broadcast, replies by text and email, email-in, wording edits, test mode,
good time, results, the fair-use guard and corrections."""
import json, os, re, unittest
from services import messages as M
from services.message_desk import MessageDesk, check_wording, wording_kinds

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SYS = M.SYS
NOON = 1_800_014_400          # 2027-01-15 12:00 UTC: midday in Africa/Douala
NIGHT = NOON + 11 * 3600      # 23:00 UTC
PDF = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"
EXE = b"MZ\x90\x00" + b"\x00" * 60


class Sender(M.SandboxSender):
    def price(self, channel, country):
        return {"minor": 3 if channel == "text" else 9, "currency": "USD", "sample": True}


class Register(unittest.TestCase):
    def test_the_system_block_agrees_with_the_register(self):
        kinds = {k["id"] for k in M.REG["kinds"]}
        for need in (SYS["broadcast"]["kind"], SYS["corrections"]["kind"], "email_in_arrived", "message_wording_test", "fair_use_warning"):
            self.assertIn(need, kinds)
        self.assertEqual(SYS["routing"]["cost_order"][0], "bell")
        self.assertEqual(SYS["routing"]["cost_order"][-1], "call", "a call is always the last step")
        self.assertTrue(set(SYS["routing"]["cost_order"]) == set(M.REG["channels"]))
        self.assertFalse(any("call" in k["channels"] for k in M.REG["kinds"]), "no kind sends a call directly: only routing's last step")
        self.assertEqual(set(SYS["states"]["map"].values()) - {"queued", "sent", "accepted", "confirmed", "failed"}, set())
        events = json.load(open(os.path.join(ROOT, "merchant", "events.v1.json")))["events"]
        for kid in ("urgent_broadcast", "message_correction", "email_in_arrived", "message_wording_test", "fair_use_warning"):
            self.assertIn(M.KINDS[kid]["trigger"], events, kid)

    def test_wording_never_touches_security_safety_or_legal(self):
        for kid in wording_kinds():
            k = M.KINDS[kid]
            self.assertEqual(k["audience"], "customer")
            self.assertNotIn(k["basis"], ("security", "safety", "legal"))
        self.assertIn("receipt", wording_kinds())

    def test_address_patterns_live_in_the_contacts_map(self):
        c = json.load(open(os.path.join(ROOT, "catalog", "contacts.v1.json")))
        ids = {p["id"] for p in c["patterns"]}
        self.assertTrue({"reply", "email_in_bills", "email_in_files", "email_in_cvs"} <= ids)
        src = open(os.path.join(ROOT, "services", "message_desk.py")).read()
        self.assertNotRegex(src, r"[a-z]@(?:in|mail)\.lynkomni\.com", "addresses come from the contacts map")

    def test_the_desk_only_sends_through_the_engine(self):
        src = open(os.path.join(ROOT, "services", "message_desk.py")).read()
        self.assertNotIn(".deliver(", src)
        self.assertNotIn("sender.", src)


class Routing(unittest.TestCase):
    def test_the_channel_a_person_uses_comes_first_then_the_cheapest(self):
        n = M.Notifier()
        r = n.notify("attend_flag_for_manager", "p1", "e1", NOON)
        self.assertEqual(r["channels"][1], "push", "the cheapest that works first")
        n.used("p2", "email", NOON - 3600)
        r = n.notify("attend_flag_for_manager", "p2", "e2", NOON)
        self.assertEqual(r["channels"][1], "email", "the channel this person actually uses first")
        n.used("p3", "email", NOON - 40 * 86400)
        self.assertEqual(n.notify("attend_flag_for_manager", "p3", "e3", NOON)["channels"][1], "push", "an old habit is forgotten")

    def test_not_delivered_steps_to_the_next_channel(self):
        n = M.Notifier(M.SandboxSender(fail={"push"}))
        r = n.notify("attend_flag_for_manager", "p1", "e1", NOON)
        self.assertIn("email", r["channels"])
        self.assertEqual(n.lines[r["nid"]]["state"], "confirmed")

    def test_a_call_is_the_last_step_only_for_an_unacknowledged_critical_alert(self):
        n = M.Notifier()
        own = n.notify("recovery_started", "p9", "e9", NOON)
        self.assertNotIn("text", own["channels"], "LynkOmni's own alert goes by the free channels")
        self.assertFalse([x for x in n.tick(NOON + SYS["routing"]["call_after_s"]) if x[0] == "called"], "LynkOmni never calls for its own messages")
        n = M.Notifier()
        r = n.notify("protection_alert", "p1", "e1", NOON, business="biz1")
        self.assertNotIn("call", r["channels"])
        self.assertFalse([x for x in n.tick(NOON + 60) if x[0] == "called"])
        out = n.tick(NOON + SYS["routing"]["call_after_s"])
        self.assertIn(("called", r["nid"]), out)
        self.assertIn(("call", "p1", "protection_alert", "en"), n.sender.sent)
        self.assertFalse([x for x in n.tick(NOON + 2 * SYS["routing"]["call_after_s"]) if x[0] == "called"], "called once")
        r2 = n.notify("stock_conflict", "p2", "e2", NOON)
        n.tick(NOON + 3600)
        self.assertNotIn("call", n.lines[r2["nid"]]["channels"], "never a call for anything but critical")
        r3 = n.notify("protection_alert", "p3", "e3", NOON, business="biz1", contacts=("bell", "push", "email"))
        n.tick(NOON + 3600)
        self.assertNotIn("call", n.lines[r3["nid"]]["channels"], "no phone, no call")

    def test_cost_is_shown_before_texts_are_spent(self):
        n = M.Notifier(Sender())
        prev = n.cost_preview([["text"], ["push"], ["text"]], "RW")
        self.assertEqual(prev["text"]["count"], 2)
        self.assertTrue(prev["text"]["price"]["sample"], "sandbox prices are labelled samples")
        self.assertNotIn("push", prev)

    def test_a_role_message_goes_to_whoever_holds_it_now(self):
        n = M.Notifier()
        holders = {"manager": ["ana", "ben"], "owner": ["olu"]}
        got = n.notify_role("stock_conflict", "m1", "manager", holders, "e1", NOON, in_now={"ben"})
        self.assertEqual(got["people"], ["ben"], "the manager on shift, not the one off duty")
        got = n.notify_role("stock_conflict", "m1", "manager", holders, "e2", NOON, in_now=set())
        self.assertEqual(got["people"], ["ana", "ben"], "nobody in: every holder")
        got = n.notify_role("stock_conflict", "m1", "stock_staff", holders, "e3", NOON, in_now=set())
        self.assertEqual((got["role"], got["people"]), ("manager", ["ana", "ben"]), "no holder: the next role up")

    def test_the_on_call_rota_climbs_and_done_clears_every_step(self):
        n = M.Notifier()
        with self.assertRaises(ValueError):
            n.set_rota("night", ["a", "a"])
        n.set_rota("night", ["a", "b"], step_after_s=600, owner="olu")
        r = n.notify_rota("device_copy_suspended", "night", "e1", NOON, business="m1")
        out = n.tick(NOON + 600)
        self.assertIn(("climbed", r["nid"], "b"), out)
        out = n.tick(NOON + 1200)
        self.assertTrue(any(x[0] == "climbed" and x[2] == "olu" for x in out), "from the last person to the owner")
        b_line = next(l for l in n.lines.values() if l["person"] == "b")
        n.act(b_line["nid"], "b")
        self.assertTrue(all(l["done_by"] == "b" for l in n.lines.values() if "e1" in l["events"]), "Done by clears every step")

    def test_a_role_inbox_is_handled_once(self):
        n = M.Notifier()
        r = n.notify_inbox("stock_conflict", "m1", "front_desk", {"front_desk": ["a", "b"]}, "e1", NOON, in_now={"a", "b"})
        self.assertEqual(len(n.inbox("m1", "front_desk")), 1)
        self.assertEqual(n.claim(r["nid"], "a"), {"state": "yours"})
        self.assertEqual(n.claim(r["nid"], "b"), {"state": "taken", "by": "a"})
        a_line = next(l for l in n.lines.values() if l["person"] == "a")
        n.act(a_line["nid"], "a")
        self.assertEqual(n.inbox("m1", "front_desk"), [], "done for everyone")
        self.assertFalse([x for x in n.tick(NOON + 86400) if x[1] == r["nid"]], "the shared line never repeats or escalates itself")


class Desk(unittest.TestCase):
    def setUp(self):
        from services.platform import Platform
        self.p = Platform(); self.p.register("m1", "RW")
        self.n = M.Notifier(Sender())
        self.d = MessageDesk(self.p, self.n)

    def events(self, t):
        return [e for e in self.p.c.store.since("m1", 0) if e["type"] == t] if hasattr(self.p.c.store, "since") else []

    def test_urgent_broadcast(self):
        with self.assertRaises(PermissionError):
            self.d.broadcast("m1", "c1", "cashier", "staff", ["a"], "Closed today", NOON)
        with self.assertRaises(ValueError):
            self.d.broadcast("m1", "o", "owner", "staff", ["a"], "PIN 4719 for the door", NOON)
        r = self.d.broadcast("m1", "o", "owner", "staff", ["a", "b"], "Closed today after the flood", NOON,
                             contacts={"a": ("bell", "text"), "b": ("bell", "push")})
        self.assertEqual(r["state"], "confirm_cost", "texts are shown before they are spent")
        self.assertEqual(r["preview"]["text"]["count"], 1)
        r = self.d.broadcast("m1", "o", "owner", "staff", ["a", "b"], "Closed today after the flood", NOON,
                             contacts={"a": ("bell", "text"), "b": ("bell", "push")}, cost_seen=True)
        self.assertEqual(r["count"], 2)
        self.assertEqual(self.d.seen("m1", r["broadcast_id"])["seen"], [])
        self.n.open_bell("a")
        s = self.d.seen("m1", r["broadcast_id"])
        self.assertEqual((s["seen"], s["not_seen"]), (["a"], ["b"]), "seen only from the app's read state")
        self.assertFalse(M.REG["track_opens"])
        for e in self.events("UrgentBroadcastSent"):
            self.assertNotIn("flood", json.dumps(e), "the words are never in an event")
        for _ in range(SYS["broadcast"]["per_day"] - 1):
            self.d.broadcast("m1", "o", "owner", "staff", ["a"], "Again", NOON, cost_seen=True)
        self.assertEqual(self.d.broadcast("m1", "o", "owner", "staff", ["a"], "Again", NOON, cost_seen=True)["state"], "refused")

    def test_reply_by_text_yes_and_stop(self):
        booked = []
        self.d.on_yes["booking_reminder"] = lambda person, business, record: booked.append(record) or "confirmed"
        self.n.notify("booking_reminder", "cust", "e1", NOON, business="m1", record="LOBKG-1")
        r = self.d.reply_text("cust", "m1", " yes ", NOON + 60)
        self.assertEqual((r["state"], booked), ("confirmed", ["LOBKG-1"]))
        self.assertEqual(self.d.reply_text("cust", "m1", "YES", NOON + 90)["state"], "nothing_to_confirm", "confirmed once")
        self.n.notify("assist_needs_confirm", "cust", "e9", NOON, business="m1")
        self.assertEqual(self.d.reply_text("cust", "m1", "YES", NOON + 99)["state"], "nothing_to_confirm",
                         "YES never confirms LynkAssist or money")
        self.assertEqual(self.d.reply_text("cust", "m1", "maybe", NOON)["state"], "help")
        self.assertEqual(self.d.reply_text("cust", "m1", "STOP", NOON + 120)["state"], "stopped")
        r = self.n.notify("merchant_offer", "cust", "e2", NOON + 200, business="m1", consent=True)
        self.assertEqual(r, {"state": "refused", "reason": "stopped"})
        self.assertEqual(self.n.notify("merchant_offer", "cust", "e3", NOON + 200, business="m2", consent=True).get("state") in ("in_summary", "shown"), True,
                         "STOP ends only that business's messages")
        self.assertEqual(self.n.notify("receipt", "cust", "e4", NOON + 200, business="m1").get("state"), "shown", "transaction messages keep coming")

    def test_reply_by_email_lands_in_the_record(self):
        addr = self.d.reply_address("m1", "LOINV-1234-5678-9012", NOON)
        self.assertTrue(addr.startswith("reply+") and addr.endswith("@mail.lynkomni.com"))
        tok = addr.split("+", 1)[1].split("@")[0]
        self.assertNotIn(tok, json.dumps(list(self.d.tokens)), "the token is kept only as a digest")
        r = self.d.reply_email(tok, "Can I pay next week?", NOON + 60)
        self.assertEqual(r["lands_in"], "invoice_thread")
        self.assertEqual(self.d.thread("m1", "LOINV-1234-5678-9012")[0]["text"], "Can I pay next week?")
        self.assertEqual(self.d.reply_email("nope", "x", NOON)["state"], "refused")
        self.assertEqual(self.d.reply_email(tok, "late", NOON + 91 * 86400)["state"], "refused", "reply addresses end")
        addr = self.d.reply_address("m1", "LOCASE-1111-2222-3333", NOON)
        self.assertEqual(self.d.reply_email(addr.split("+", 1)[1].split("@")[0], "hi", NOON)["lands_in"], "case")

    def test_email_in(self):
        self.assertEqual(self.d.email_in_address("shop.one", "bills"), "shop.one+bills@in.lynkomni.com")
        r = self.d.email_in("m1", "bills", "stranger@example.org", [PDF], NOON)
        self.assertEqual(r["state"], "held", "an unknown sender is held for the owner")
        self.d.allow_sender("m1", "Supplier@Example.org")
        r = self.d.email_in("m1", "bills", "supplier@example.org", [PDF, EXE], NOON)
        self.assertEqual((r["state"], len(r["documents"]), r["refused"]), ("draft", 1, ["blocked"]), "programs are refused")
        self.assertEqual(self.d.drafts["m1"][r["draft"]]["state"], "draft", "a draft until a person completes it")
        bill = self.d.complete_draft("m1", r["draft"], "acc1", 12_500)
        self.assertEqual(bill["state"], "draft", "the bill still needs approving in LynkAcc")
        with self.assertRaises(ValueError):
            self.d.complete_draft("m1", r["draft"], "acc1", 12_500)
        self.assertEqual(self.d.email_in("m1", "files", "supplier@example.org", [PDF], NOON)["state"], "filed")
        self.assertEqual(self.d.email_in("m1", "cvs", "supplier@example.org", [PDF], NOON)["state"], "planned", "CVs wait for LynkJobs (8B)")
        self.assertEqual(self.d.email_in("m1", "bills", "supplier@example.org", [EXE], NOON)["state"], "refused")

    def test_wording_edits_and_test_mode(self):
        for bad, why in (("x" * 400, "too_long"), ("Thanks!", "missing_placeholder"), ("{business}: {secret}", "unknown_placeholder"),
                         ("{business} see https://example.com", "not_allowed"), ("{business} PIN 4719", "not_allowed")):
            if why:
                self.assertEqual(check_wording(bad), why, bad)
        with self.assertRaises(PermissionError):
            self.d.edit_wording("m1", "c", "cashier", "receipt", "Thanks from {business}", NOON)
        with self.assertRaises(ValueError):
            self.d.edit_wording("m1", "o", "owner", "new_sign_in", "Hi from {business}", NOON)
        r = self.d.edit_wording("m1", "o", "owner", "receipt", "Thank you for shopping at {business}", NOON, languages=["en", "fr", "ar"])
        self.assertEqual(r["state"], "testing")
        self.assertTrue(all("{business}" in t for t in r["preview"].values()), "placeholders come back unchanged in every language")
        sent = self.d.send_customer("m1", "receipt", "cust", "s1", NOON)
        self.assertTrue(sent["test"], "test mode: only the owner gets it")
        self.assertFalse([l for l in self.n.lines.values() if l["person"] == "cust"])
        with self.assertRaises(PermissionError):
            self.d.approve_wording("m1", "receipt", "mgr", "manager")
        self.d.approve_wording("m1", "receipt", "o", "owner")
        self.assertEqual(self.d.send_customer("m1", "receipt", "cust", "s2", NOON)["state"], "shown")
        self.assertEqual(self.d.words_for("m1", "receipt", "fr"), r["preview"]["fr"])

    def test_optional_messages_wait_for_a_good_local_time(self):
        r = self.d.send_customer("m1", "merchant_offer", "cust", "o1", NIGHT, country="CM", consent=True)
        self.assertEqual(r["state"], "scheduled")
        from core.locale import local_dt
        import time as _t
        self.assertEqual(local_dt(_t.strftime(M.FMT, _t.gmtime(r["at"])), "CM").hour, SYS["good_time"]["send_at"])
        self.assertEqual(self.d.due(NIGHT + 60), [])
        self.assertEqual(len(self.d.due(r["at"])), 1)
        self.assertNotEqual(self.d.send_customer("m1", "receipt", "cust", "o2", NIGHT, country="CM").get("state"), "scheduled",
                            "transaction messages are never held for a good time")

    def test_results_are_totals_from_five(self):
        for i in range(4):
            self.n.notify("receipt", f"c{i}", f"r{i}", NOON, business="m1")
        self.assertIsNone(self.d.results("m1")["receipt"]["sent"], "below 5 nothing is shown")
        self.n.notify("receipt", "c9", "r9", NOON, business="m1")
        res = self.d.results("m1")["receipt"]
        self.assertEqual(res["sent"], 5)
        self.assertNotIn("c1", json.dumps(res), "nothing per person")

    def test_fair_use_slows_and_warns_once(self):
        f = SYS["fair_use"]
        for i in range(f["min_sample"]):
            self.n.notify("merchant_offer", f"c{i}", f"x{i}", NOON, business="m1", consent=True)
        for i in range(f["min_sample"] * f["stop_rate_bp"] // 10000 + 1):
            self.d.reply_text(f"c{i}", "m1", "STOP", NOON)
        warns = [l for l in self.n.lines.values() if l["kind"] == "fair_use_warning"]
        self.assertEqual(len(warns), 1, "warned once a day")
        self.assertEqual(self.d._fair_use("m1", NOON), "stops")
        for i in range(f["slowed_per_hour"]):
            self.d.send_customer("m1", "merchant_offer", f"n{i}", f"y{i}", NOON, consent=True)
        self.assertEqual(self.d.send_customer("m1", "merchant_offer", "late", "z", NOON, consent=True)["state"], "slowed")
        self.assertNotEqual(self.d.send_customer("m1", "receipt", "late", "z2", NOON).get("state"), "slowed", "receipts are never slowed")

    def test_a_linked_correction_on_the_record(self):
        r = self.n.notify("receipt", "cust", "e1", NOON, business="m1", record="LOSAL-1")
        with self.assertRaises(PermissionError):
            self.d.correct("m2", "o", r["nid"], "Sorry", NOON)
        c = self.d.correct("m1", "o", r["nid"], "Sorry, the total was 4,500", NOON + 60)
        self.assertEqual(c["state"], "sent")
        self.assertEqual(self.d.correct("m1", "o", r["nid"], "again", NOON)["state"], "refused", "one correction per message")
        rec = self.n.on_record("m1", "LOSAL-1")
        self.assertEqual([x["kind"] for x in rec], ["receipt", "message_correction"])
        self.assertEqual(rec[0]["corrected_by"], c["nid"])
        self.assertEqual(rec[1]["corrects"], r["nid"])
        self.assertTrue(all(x["state"] in ("queued", "sent", "accepted", "confirmed", "failed") for x in rec), "five states only")

    def test_the_country_decides_the_text_sender_name(self):
        self.assertEqual(MessageDesk.sender_name("Shop One", "RW"), "LynkOmni", "unconfirmed: LynkOmni's registered name")

    def test_the_platform_knows_who_is_on_shift(self):
        self.assertTrue(callable(self.p.message_desk.on_shift))
        self.assertEqual(self.p.message_desk.on_shift("m1"), set())


if __name__ == "__main__":
    unittest.main()
