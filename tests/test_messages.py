"""The message and notification register and its engine (MASTER UPDATE, master blueprint sections 56 and 62)."""
import json, os, unittest
from core import build_sections
from services import messages as m

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REG = m.REG
CONTACTS = json.load(open(os.path.join(ROOT, "catalog", "contacts.v1.json"), encoding="utf-8"))
SHOW = json.load(open(os.path.join(ROOT, "web", "showcase", "showcase.v1.json"), encoding="utf-8"))
LOCKED = {s["n"] for s in SHOW["sections"] if s.get("status") == "locked"}
EVENTS = set(json.load(open(os.path.join(ROOT, "identity", "events.v1.json"), encoding="utf-8"))["events"])
EVENTS |= set(json.load(open(os.path.join(ROOT, "merchant", "events.v1.json"), encoding="utf-8"))["events"])
_c = json.load(open(os.path.join(ROOT, "contract", "event-payloads.v4.json"), encoding="utf-8"))
EVENTS |= set(_c.get("events") or _c)
NOON = 1_800_014_400          # 2027-01-15 12:00 UTC: midday in Africa/Douala
NIGHT = NOON + 11 * 3600      # 23:00 UTC: night in Africa/Douala


class TestRegister(unittest.TestCase):
    def test_every_kind_is_complete(self):
        ids = [k["id"] for k in REG["kinds"]]
        self.assertEqual(len(ids), len(set(ids)))
        senders = {s["address"] for s in CONTACTS["senders"]}
        for k in REG["kinds"]:
            self.assertIn(k["basis"], REG["bases"], k["id"])
            self.assertIn(k["priority"], REG["priorities"], k["id"])
            self.assertIn(k["group"], REG["groups"], k["id"])
            self.assertIn(k["lock_screen"], REG["lock_screen"], k["id"])
            self.assertTrue(set(k["channels"]) <= set(REG["channels"]) and k["channels"], k["id"])
            self.assertIn(k["sender"], senders, f"{k['id']}: every sender is in the contacts map")
            self.assertIn(k["build_section"], build_sections.ORDER, k["id"])

    def test_triggers_of_built_sections_are_real_events(self):
        for k in REG["kinds"]:
            if k["build_section"] in LOCKED:
                self.assertIn(k["trigger"], EVENTS, f"{k['id']}: {k['trigger']}")

    def test_security_and_safety_can_never_be_turned_off(self):
        for k in REG["kinds"]:
            if k["basis"] in ("security", "safety"):
                self.assertFalse(k["can_turn_off"], k["id"])
            if k["priority"] == "critical":
                self.assertFalse(k["can_turn_off"], k["id"])
                self.assertGreaterEqual(len(k["channels"]), 3, k["id"])

    def test_no_advertising_no_open_tracking_and_marketing_needs_opt_in(self):
        self.assertFalse(REG["advertising"])
        self.assertFalse(REG["track_opens"])
        self.assertEqual(REG["history_days"], 90)
        for k in REG["kinds"]:
            if k["area"] == "marketing":
                self.assertEqual(k["basis"], "opt_in", k["id"])
                self.assertNotIn("push", k["channels"], k["id"])
            if k["basis"] == "opt_in":
                self.assertEqual(k["priority"], "low", k["id"])

    def test_lock_screens_are_private_by_default(self):
        self.assertTrue(all(k["lock_screen"] == "neutral" for k in REG["kinds"]))


class TestEngine(unittest.TestCase):
    def setUp(self):
        self.n = m.Notifier()

    def test_nothing_outside_the_register_is_sent(self):
        with self.assertRaises(KeyError):
            self.n.notify("buy_now_banner", "p1", "e1", NOON)
        for bad in ({"pin": "4719"}, {"code": "123456"}, {"note": "card 4111 1111 1111 1111"}, {"lat": 4.05},
                    {"link": "http://example.com/login"}):
            with self.assertRaises(ValueError):
                m.Notifier().notify("stock_low", "p1", "e1", NOON, facts=bad)
        self.assertTrue(m.check_content({"currency_code": "XAF", "shipping_fee": 500, "link": "https://app.lynkomni.com/stock"}))

    def test_one_notification_per_event_per_person(self):
        r = self.n.notify("new_sign_in", "p1", "e1", NOON, country="CM")
        self.assertEqual(r["state"], "shown")
        self.assertEqual(self.n.notify("new_sign_in", "p1", "e1", NOON + 5, country="CM")["state"], "duplicate")
        self.assertEqual(len(self.n.sender.sent), 1, "one outside channel is enough for a high notice")

    def test_opt_in_and_muting(self):
        self.assertEqual(self.n.notify("merchant_offer", "c1", "e1", NOON)["state"], "refused")
        self.assertEqual(self.n.notify("merchant_offer", "c1", "e2", NOON, consent=True)["state"], "shown")
        self.assertEqual(self.n.notify("stock_low", "p1", "e3", NOON, prefs={"muted": {"stock_low"}})["state"], "suppressed")
        self.assertEqual(self.n.notify("new_sign_in", "p1", "e4", NOON, prefs={"muted": {"new_sign_in"}, "paused_optional": True})["state"],
                         "shown", "security cannot be muted")

    def test_bursts_fold_and_records_update_in_place(self):
        for i in range(12):
            self.n.notify("stock_low", "p1", f"s{i}", NOON + i * 60)
        lines = self.n.bell("p1")["new"]
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]["count"], 12)
        for i, step in enumerate(("confirmed", "on_the_way", "delivered")):
            self.n.notify("order_step", "c1", f"o{i}", NOON + i, record="LOORD-1", facts={"step": step})
        lines = self.n.bell("c1")["new"]
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]["facts"]["step"], "delivered")

    def test_count_seen_read_and_low_priority(self):
        self.n.notify("stock_negative", "p1", "a", NOON)
        self.n.notify("driver_update", "p1", "b", NOON)
        self.n.notify("sync_retried", "p1", "c", NOON)
        self.assertEqual(self.n.count("p1"), 1, "low priority never raises the count")
        self.n.open_bell("p1")
        self.assertEqual(self.n.count("p1"), 0)
        nid = self.n.bell("p1")["earlier"][0]["nid"]
        self.n.read(nid)
        self.n.read(nid, read=False)
        self.assertFalse(self.n.lines[nid]["read"])
        self.n.mark_all_read("p1")
        self.assertEqual(self.n.bell("p1", unread_only=True), {"new": [], "earlier": []})

    def test_quiet_hours_and_do_not_disturb_but_critical_breaks_through(self):
        r = self.n.notify("stock_negative", "p1", "a", NIGHT, country="CM")
        self.assertEqual(r["state"], "bell_only_until_quiet_ends")
        r = self.n.notify("stock_negative", "p2", "b", NOON, country="CM", prefs={"dnd_until": NOON + 3600})
        self.assertEqual(r["state"], "bell_only_until_quiet_ends")
        r = self.n.notify("trip_plan_overdue", "t1", "c", NIGHT, country="CM", prefs={"dnd_until": NIGHT + 3600})
        self.assertEqual(r["state"], "shown")
        self.assertEqual(set(r["channels"]), {"bell", "push", "email", "text"}, "critical uses every channel")

    def test_critical_repeats_until_acknowledged_and_high_escalates(self):
        r = self.n.notify("recovery_started", "p1", "a", NOON)
        events = self.n.tick(NOON + m.REPEAT_S)
        self.assertIn(("repeated", r["nid"]), events)
        self.n.acknowledge(r["nid"])
        self.assertEqual([e for e in self.n.tick(NOON + 2 * m.REPEAT_S) if e[1] == r["nid"]], [])
        s = self.n.notify("sale_failed", "cashier1", "b", NOON, role="cashier")
        out = self.n.tick(NOON + 600, escalate_after={"cashier": 600})
        self.assertIn(("escalated", s["nid"], "manager"), out)

    def test_done_by_clears_for_everyone(self):
        a = self.n.notify("staff_request", "owner1", "req1", NOON, role="owner")
        b = self.n.notify("staff_request", "manager1", "req1", NOON, role="manager")
        self.n.act(a["nid"], by="Grace")
        self.assertEqual(self.n.lines[b["nid"]]["done_by"], "Grace")

    def test_daily_cap_and_summaries(self):
        for i in range(m.REG["daily_cap"] + 3):
            self.n.notify("device_health", "p1", f"h{i}", NOON + i, record=f"dev{i}")
        for i in range(m.REG["daily_cap"] + 3):
            self.n.notify("stock_conflict", "p1", f"c{i}", NOON + i, record=f"x{i}")
        self.assertEqual(self.n.notify("owner_summary", "p1", "d1", NOON, consent=True)["state"], "in_summary")
        caps = [self.n.notify("assist_needs_confirm", "p9", f"z{i}", NOON + i)["state"] for i in range(m.REG["daily_cap"] + 2)]
        self.assertEqual(caps[-1], "in_summary", "normal priority is capped per day")

    def test_fallback_to_the_next_channel(self):
        n = m.Notifier(m.SandboxSender(fail={"push"}))
        r = n.notify("new_sign_in", "p1", "e1", NOON)
        self.assertIn("email", r["channels"])
        r = n.notify("new_sign_in", "p2", "e2", NOON, contacts=("bell", "push", "text"))
        self.assertIn("text", r["channels"], "phone-first people without email still receive it")

    def test_offline_backlog_is_folded_on_reconnect(self):
        for i, step in enumerate(("confirmed", "packed", "on_the_way")):
            self.n.notify("order_step", "c1", f"o{i}", NOON + i, record="LOORD-1", facts={"step": step}, online=False)
        self.n.notify("stock_negative", "c1", "s1", NOON, online=False)
        got = self.n.reconnect("c1")
        self.assertEqual(len(got), 2)
        self.assertEqual([l["facts"].get("step") for l in got if l["kind"] == "order_step"], ["on_the_way"])

    def test_business_filter_never_hides_security(self):
        self.n.notify("stock_negative", "p1", "a", NOON, business="b1")
        self.n.notify("stock_negative", "p1", "b", NOON, business="b2")
        self.n.notify("new_sign_in", "p1", "c", NOON)
        kinds = [l["kind"] for l in self.n.bell("p1", business="b1")["new"]]
        self.assertEqual(sorted(kinds), ["new_sign_in", "stock_negative"])

    def test_why_am_i_seeing_this(self):
        r = self.n.notify("new_sign_in", "p1", "a", NOON)
        self.assertEqual(self.n.why(r["nid"])["event"], "SessionStarted")
        self.assertIn("cannot be turned off", self.n.why(r["nid"])["because"])


if __name__ == "__main__":
    unittest.main()
