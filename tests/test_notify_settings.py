"""The Notifications settings page, read sync and the Messages page (MASTER UPDATE, sections 56 and 62; build section 2)."""
import unittest
from services import messages as m
from services.notify_settings import Settings

NOON = 1_800_014_400
H = 3600


class TestSettings(unittest.TestCase):
    def setUp(self):
        self.n = m.Notifier(); self.events = []
        self.s = Settings(self.n, emit=lambda person, t, p, now=None: self.events.append(t))

    def send(self, kid, person="p1", eid="e", **kw):
        return self.n.notify(kid, person, eid, kw.pop("now", NOON), prefs=self.s.prefs(person, kw.pop("at", NOON)), **kw)

    def test_security_and_safety_can_never_be_switched_off(self):
        for area in ("security", "safety"):
            with self.assertRaises(PermissionError):
                self.s.set_channel("p1", area, "push", False)
        with self.assertRaises(PermissionError):
            self.s.mute("p1", "new_sign_in")
        with self.assertRaises(PermissionError):
            self.s.snooze("p1", "recovery_started", 2)
        self.s.pause_all_optional("p1", True)
        self.assertEqual(self.send("new_sign_in")["state"], "shown")
        self.assertEqual(self.send("stock_low", eid="e2")["state"], "suppressed")

    def test_the_grid_mute_snooze_and_do_not_disturb(self):
        self.s.set_channel("p1", "stock", "push", False); self.s.set_channel("p1", "stock", "email", False); self.s.set_channel("p1", "stock", "text", False)
        r = self.send("stock_negative")
        self.assertEqual(r["channels"], ["bell"], "the grid decides the channels")
        self.s.snooze("p1", "stock_low", 2, now=NOON)
        self.assertEqual(self.send("stock_low", eid="e2")["state"], "suppressed")
        self.assertNotEqual(self.send("stock_low", eid="e3", now=NOON + 3 * H, at=NOON + 3 * H)["state"], "suppressed", "a snooze ends by itself")
        self.s.do_not_disturb("p2", NOON + H)
        self.assertEqual(self.send("stock_negative", person="p2", eid="e4")["state"], "bell_only_until_quiet_ends")
        self.assertEqual(self.send("recovery_started", person="p2", eid="e5")["state"], "shown", "critical breaks through")

    def test_each_business_on_or_off_but_security_still_arrives(self):
        self.s.set_business("p1", "b2", False)
        self.assertEqual(self.send("stock_negative", business="b2")["state"], "suppressed")
        self.assertEqual(self.send("stock_negative", eid="e2", business="b1")["state"], "shown")
        self.assertEqual(self.send("new_sign_in", eid="e3", business="b2")["state"], "shown")

    def test_the_lock_screen_is_neutral_unless_the_person_chooses(self):
        r = self.send("stock_negative"); self.assertEqual(self.n.lines[r["nid"]]["lock_screen"], "neutral")
        self.s.set_lock_screen("p1", "stock_negative", "full")
        r = self.send("stock_negative", eid="e2"); self.assertEqual(self.n.lines[r["nid"]]["lock_screen"], "full")
        with self.assertRaises(ValueError):
            self.s.set_lock_screen("p1", "stock_negative", "everything")

    def test_a_deputy_gets_business_notices_within_their_own_role_never_personal_ones(self):
        with self.assertRaises(ValueError):
            self.s.set_deputy("owner1", "m1", "owner", NOON + 3 * 86400, now=NOON)
        self.s.set_deputy("owner1", "m1", "manager", NOON + 3 * 86400, now=NOON)
        r = self.n.notify("staff_request", "owner1", "req1", NOON, prefs=self.s.prefs("owner1", NOON), role="owner")
        self.assertEqual(self.n.lines[r["nid"]]["person"], "m1"); self.assertEqual(self.n.lines[r["nid"]]["role"], "manager")
        r = self.n.notify("new_sign_in", "owner1", "s1", NOON, prefs=self.s.prefs("owner1", NOON), role="owner")
        self.assertEqual(self.n.lines[r["nid"]]["person"], "owner1", "security stays with the owner")
        self.assertEqual(len(self.s.end_deputy("owner1")), 1, "the owner sees what the deputy handled")
        self.assertIn("DeputyNamed", self.events)

    def test_send_me_a_test_and_the_health_check(self):
        self.assertTrue(self.s.send_test("p1", "push")["delivered"])
        n2 = m.Notifier(m.SandboxSender(fail={"push"})); s2 = Settings(n2)
        self.assertFalse(s2.send_test("p1", "push")["delivered"])
        h = Settings.health([{"name": "Grace's phone", "push_allowed": False}, {"name": "Tablet", "push_allowed": True, "push_link_age_days": 45}], {"phone": "pii_1"})
        self.assertEqual([(x["problem"], x["fix"]) for x in h], [("push_off", "open_phone_settings"), ("push_stale", "open_the_app")])
        self.assertEqual(Settings.health([], {})[0]["problem"], "no_contact")

    def test_personal_reminders_arrive_as_a_notice_and_can_be_snoozed_or_cleared(self):
        with self.assertRaises(ValueError):
            self.s.remind("p1", "LOINV-1", NOON - 1, now=NOON)
        rid = self.s.remind("p1", "LOINV-1234-5678-9015", NOON + H, now=NOON)
        self.assertEqual(self.s.due(NOON), [])
        out = self.s.due(NOON + H)
        self.assertEqual(out[0]["state"], "shown")
        self.s.snooze_reminder(rid, NOON + 5 * H)
        self.assertEqual(len(self.s.due(NOON + 5 * H)), 1)
        self.s.clear_reminder(rid)
        self.assertEqual(self.s.due(NOON + 10 * H), [])
        self.assertEqual(self.events.count("ReminderDue"), 2)


class TestSyncAndMessages(unittest.TestCase):
    def test_read_on_one_device_shows_on_every_device(self):
        n = m.Notifier()
        a = n.notify("stock_negative", "p1", "a", NOON); n.notify("stock_conflict", "p1", "b", NOON)
        n.read(a["nid"], now=NOON + 10)
        ch = n.changes("p1", since=NOON + 5)
        self.assertEqual([(c["nid"], c["read"]) for c in ch], [(a["nid"], True)])
        n.mark_all_read("p1", now=NOON + 20)
        self.assertEqual(len(n.changes("p1", since=NOON + 15)), 1, "only what changed is sent")

    def test_the_messages_page_lists_every_outside_message_with_its_sender(self):
        n = m.Notifier()
        n.notify("new_sign_in", "p1", "a", NOON)
        n.notify("stock_negative", "p1", "b", NOON + 1)
        msgs = n.messages("p1")
        self.assertEqual([x["kind"] for x in msgs], ["stock_negative", "new_sign_in"])
        senders = {x["sender"] for x in msgs}
        self.assertTrue(all(s.endswith(".lynkomni.com") for s in senders))
        self.assertTrue(all(x["channel"] in ("push", "email", "text") for x in msgs), "the bell itself is not a sent message")


if __name__ == "__main__":
    unittest.main()
