"""LynkQueue in full (LynkQ; master blueprint section 63; build section 3B): setup and plan limits, added devices and their blocks
of codes, the queue keeper on the device (offline), the fair order, the counter's buttons, Send to, Missed and Put back, the person
on the phone, another device taking over, closing the day, the live view, reports, the public queue page and what is billed.
No event ever carries a phone number or a name."""
import json, os, unittest
from datetime import datetime, timezone

from contract.tools.validate_contract import uuid4, validate_event
from core import queue_tickets as R
from dv.box import LocalRejection, LynkDVBox
from people.keeper import QueueKeeper
from people.queue import DAY, Queue
from services.platform import Platform

T0 = 1_800_000_000.0 - 1_800_000_000.0 % DAY + 9 * 3600        # 09:00 on a fixed day
AT = lambda t: datetime.fromtimestamp(t, tz=timezone.utc)
PHONE = "+237650000111"


class QueueTests(unittest.TestCase):
    def setUp(self):
        os.environ.pop("LYNK_MODE", None)
        self.p = Platform(); self.q = self.p.queue; self.m = uuid4(); self.boss = uuid4(); self.staff = uuid4()
        self.p.billing.set_plan(self.m, "lynkqueue", "plus")
        self.q.add_manager(self.m, self.boss)
        self.place = self.q.add_place(self.m, self.boss, country="CM", now=T0)            # "One place": section GEN with 2 counters
        self.q.add_section(self.m, self.place, "LAB", self.boss, now=T0)
        self.c1, self.c2 = [c["counter_id"] for c in self.q._counters(self.place)]
        self.lab = self.q.add_counter(self.m, self.place, ["LAB"], self.boss, now=T0)
        self.dev = uuid4(); self.box = LynkDVBox(self.m, self.place, self.dev, self.staff, "manager", now=AT(T0))
        self.k = QueueKeeper(self.box, self.q.add_device(self.m, self.place, self.dev, "reception", self.boss, now=T0))
        self._sent = {}

    def sync(self, box=None, now=None):
        box = box or self.box; n = self._sent.get(id(box), 0)
        out = [self.q.ingest(self.m, e, now=now if now is not None else self.box.clock.timestamp()) for e in box.log[n:]]; self._sent[id(box)] = len(box.log); return out
    def events(self, *types): return self.p.c.store.of(self.m, *types)
    def give(self, n, section="GEN", **kw): return [self.k.issue(section, **kw) for _ in range(n)]

    # ---- setting up and the plan
    def test_setup_fills_a_ready_place_and_the_plan_sets_its_size(self):
        self.assertEqual([x["code"] for x in self.q._sections(self.place)], ["GEN", "LAB"])
        with self.assertRaises(PermissionError): self.q.add_section(self.m, self.place, "PHA", uuid4())          # only the manager
        with self.assertRaisesRegex(ValueError, "3 Lynk Alphabet"): self.q.add_section(self.m, self.place, "LOB", self.boss)   # no O in the Lynk Alphabet
        free = uuid4(); self.q.add_manager(free, self.boss); place = self.q.add_place(free, self.boss, setup="just_me", now=T0)
        self.q.add_section(free, place, "LAB", self.boss); self.q.add_section(free, place, "PHA", self.boss)
        with self.assertRaisesRegex(PermissionError, "plan_limit_sections"): self.q.add_section(free, place, "ADM", self.boss)
        with self.assertRaisesRegex(PermissionError, "plan_limit_places"): self.q.add_place(free, self.boss)
        self.q.add_counter(free, place, ["LAB"], self.boss); self.q.add_counter(free, place, ["PHA", "LAB"], self.boss)
        with self.assertRaisesRegex(PermissionError, "plan_limit_counters"): self.q.add_counter(free, place, ["LAB"], self.boss)
        with self.assertRaisesRegex(PermissionError, "plan_no_hardware_without_display"): self.q.add_device(free, place, uuid4(), "printer", self.boss)

    def test_only_an_added_device_works_and_each_has_its_own_codes(self):
        pack = self.k.pack
        self.assertEqual(pack["blocks"]["GEN"], {"first": "222222", "count": R.BLOCK_SIZE}); self.assertEqual(pack["keeper"], self.dev)
        dev2 = uuid4(); pack2 = self.q.add_device(self.m, self.place, dev2, "counter", self.boss, now=T0)
        self.assertEqual(R.index(pack2["blocks"]["GEN"]["first"]), R.BLOCK_SIZE)                          # the next block: never the same code twice
        self.assertEqual(len(self.events("TicketCodesReserved")), 4)
        stranger = LynkDVBox(self.m, self.place, uuid4(), self.staff, "manager", now=AT(T0))
        with self.assertRaisesRegex(LocalRejection, "device_not_added"): QueueKeeper(stranger).issue("GEN")
        fake = QueueKeeper(stranger, pack); fake.issue("GEN")                                              # a copied pack on a device nobody added
        self.assertEqual(self.sync(stranger)[0], {"state": "refused", "reason": "device_not_added"})
        screen = self.q.add_device(self.m, self.place, uuid4(), "screen", self.boss, now=T0)
        self.assertEqual(screen["blocks"], {})                                                             # a screen only follows

    # ---- tickets
    def test_a_ticket_number_is_a_section_and_a_lynk_code_and_is_never_given_twice(self):
        got = self.give(3) + self.give(2, "LAB", via="kiosk")
        self.assertEqual([t["number"] for t in got], ["GEN-222222", "GEN-222223", "GEN-222224", "LAB-222222", "LAB-222223"])
        self.assertEqual([t["place"] for t in got], [1, 2, 3, 1, 2])
        self.assertTrue(all(r["state"] == "accepted" for r in self.sync()))
        evt = dict(self.box.log[0]); evt["event_id"] = uuid4()                                             # the same code sent again as a new ticket
        self.assertEqual(self.q.ingest(self.m, evt, now=T0)["reason"], "code_not_set_aside_for_this_device")
        self.assertEqual(self.q.ingest(self.m, self.box.log[0], now=T0), {"state": "duplicate"})
        for e in self.box.log: self.assertEqual(validate_event(e), [])

    def test_closed_after_the_last_ticket_time_and_may_not_be_served_today(self):
        self.box.advance(hours=7, minutes=31)                                                              # 16:31, closing 17:00, last ticket 30 minutes before
        with self.assertRaisesRegex(LocalRejection, "after_last_ticket_time"): self.k.issue("GEN")
        self.box.advance(hours=1)
        with self.assertRaisesRegex(LocalRejection, "section_closed"): self.k.issue("GEN")
        box = LynkDVBox(self.m, self.place, self.dev, self.staff, "manager", now=AT(T0 + 7 * 3600)); k = QueueKeeper(box, self.k.pack)   # 16:00
        self.assertFalse(k.may_not_be_served("GEN"))
        for _ in range(20): k.issue("GEN")
        self.assertTrue(k.may_not_be_served("GEN"))                                                        # told before the ticket is taken

    def test_one_phone_holds_one_waiting_ticket_per_section(self):
        j = self.q.join(self.m, self.place, "GEN", "link", PHONE, lang="fr", now=T0)
        self.assertEqual(j["state"], "sent")
        t = self.k.issue("GEN", via=j["via"], phone_mark=j["phone_mark"]); self.q.joined(j["join_id"], t["ticket_id"]); self.sync()
        self.assertEqual(self.q.join(self.m, self.place, "GEN", "link", PHONE, now=T0)["reason"], "one_waiting_ticket_per_phone")
        with self.assertRaisesRegex(LocalRejection, "one_waiting_ticket_per_phone"): self.k.issue("GEN", via="smartphone", phone_mark=j["phone_mark"])
        self.assertEqual(self.q.join(self.m, self.place, "LAB", "link", PHONE, now=T0)["state"], "sent")   # another section is fine
        self.assertNotIn(PHONE, json.dumps(self.box.log)); self.assertNotIn(PHONE, json.dumps(self.events()))
        self.assertNotIn(PHONE, j["phone_mark"])

    def test_ways_to_join_follow_the_plan_the_place_and_the_partner(self):
        self.assertEqual(self.q.join(self.m, self.place, "GEN", "whatsapp", PHONE, now=T0), {"state": "coming_soon"})      # the partner is not signed there
        self.assertEqual(self.q.join(self.m, self.place, "GEN", "lynkchat", PHONE, now=T0)["state"], "sent")
        free = uuid4(); self.q.add_manager(free, self.boss); place = self.q.add_place(free, self.boss, setup="just_me", join_from="only_at_the_place", now=T0)
        self.assertEqual(self.q.join(free, place, "GEN", "lynkchat", PHONE, now=T0)["reason"], "plan_no_whatsapp_or_chat")
        self.assertEqual(self.q.join(free, place, "GEN", "basic_phone", PHONE, now=T0)["reason"], "plan_no_basic_phone")
        self.assertEqual(self.q.join(free, place, "GEN", "link", PHONE, now=T0)["reason"], "only_at_the_place")
        self.assertEqual(self.q.join(free, place, "GEN", "link", PHONE, at_the_place=True, now=T0)["state"], "sent")

    # ---- the fair order and the counter
    def test_call_next_follows_the_fair_order_and_staff_never_choose(self):
        a, b, c, d = self.give(4); p = self.k.issue("GEN", priority=True, by=self.staff)
        with self.assertRaisesRegex(LocalRejection, "counter_closed"): self.k.call_next(self.c1)
        self.k.counter_state(self.c1, "open", by=self.staff)
        called = []
        for _ in range(5):
            called.append(self.k.call_next(self.c1)["number"])
            with self.assertRaisesRegex(LocalRejection, "still_serving"): self.k.call_next(self.c1)
            self.k.served(self.c1)
        self.assertEqual(called, [a["number"], b["number"], c["number"], p["number"], d["number"]])       # 1 priority after every 3 others
        with self.assertRaisesRegex(LocalRejection, "no_one_waiting"): self.k.call_next(self.c1)
        self.assertFalse(hasattr(self.k, "call"))                                                          # there is no way to call a chosen ticket
        self.sync(); done = [h for h in self.q.history(self.m) if h["what"] == "served"]
        self.assertEqual(len(done), 5); self.assertEqual({h["by"] for h in done}, {self.staff})         # who served each ticket is kept

    def test_missed_after_three_calls_put_back_after_the_next_three_within_15_minutes(self):
        a = self.give(1)[0]; rest = self.give(5); self.k.counter_state(self.c1, "open")
        self.k.call_next(self.c1)
        with self.assertRaisesRegex(LocalRejection, "call_three_times_first"): self.k.missed(self.c1)
        self.k.call_again(self.c1); self.k.call_again(self.c1)
        with self.assertRaisesRegex(LocalRejection, "called_three_times"): self.k.call_again(self.c1)
        self.k.missed(self.c1)
        self.assertEqual(self.k.check_ticket(a["number"]), {"valid": False, "state": "missed"})
        self.box.advance(minutes=10); self.k.put_back(a["ticket_id"], self.staff)
        self.assertEqual(self.k.order("GEN").index(a["ticket_id"]), 3)                                    # after the next 3 people
        b = self.give(1)[0]
        for _ in range(3): self.k.call_next(self.c1); self.k.served(self.c1)
        self.k.call_next(self.c1); self.k.call_again(self.c1); self.k.call_again(self.c1); self.k.missed(self.c1)
        self.box.advance(minutes=16)
        with self.assertRaisesRegex(LocalRejection, "too_late_to_put_back"): self.k.put_back(a["ticket_id"], self.staff)
        self.sync()
        self.assertEqual([e["type"] for e in self.events("TicketMissed", "TicketPutBack")], ["TicketMissed", "TicketPutBack", "TicketMissed"])

    def test_send_to_keeps_the_same_ticket_and_counts_as_one(self):
        a = self.give(1)[0]; self.give(2, "LAB"); self.k.counter_state(self.c1, "open"); self.k.counter_state(self.lab, "open")
        self.k.call_next(self.c1); self.k.send_to(self.c1, "LAB")
        self.assertEqual(self.k.place(a["ticket_id"]), 1)                                                  # the same arrival time: it came before the two in LAB
        self.assertEqual(self.k.call_next(self.lab)["number"], a["number"])                               # still GEN-222222
        self.k.served(self.lab); self.sync()
        self.assertEqual(self.q.ticket(a["ticket_id"]), {"number": "GEN-222222", "section": "LAB", "state": "served"})
        bill = self.q.billable(self.m, T0 - DAY, T0 + DAY)
        self.assertEqual((bill["places"], bill["tickets"], bill["extra_places"]), (1, 3, 0))

    def test_a_counter_serves_its_sections_in_the_managers_order_and_pause_moves_the_queue_on(self):
        self.q.set_counter_sections(self.m, self.c2, ["LAB", "GEN"], self.boss); self.k.setup(self.q.pack(self.dev, now=T0))
        g = self.give(1)[0]; lab = self.give(1, "LAB")[0]
        self.k.counter_state(self.c2, "open"); self.assertEqual(self.k.call_next(self.c2)["number"], lab["number"])
        self.k.served(self.c2); self.k.counter_state(self.c2, "paused")
        with self.assertRaisesRegex(LocalRejection, "counter_closed"): self.k.call_next(self.c2)          # "Room 3: back soon"
        self.k.counter_state(self.c1, "open"); self.assertEqual(self.k.call_next(self.c1)["number"], g["number"])
        self.sync(); live = self.q.live(self.m, self.place, now=T0)
        self.assertEqual([c["state"] for c in live["counters"]], ["open", "paused", "closed"])

    # ---- the person on the phone
    def test_running_late_once_leave_and_please_come_now(self):
        self.k.counter_state(self.c1, "open"); tickets = self.give(7)
        j = self.q.join(self.m, self.place, "GEN", "link", PHONE, lang="fr", now=T0)
        me = self.k.issue("GEN", via="smartphone", phone_mark=j["phone_mark"]); self.q.joined(j["join_id"], me["ticket_id"]); self.sync()
        self.assertEqual(self.q.ticket(me["ticket_id"])["place"], 8)
        self.assertEqual(self.k.please_come(), [])
        for _ in range(3): self.k.call_next(self.c1); self.k.served(self.c1)
        self.sync(); come = self.k.please_come(); self.assertEqual(come, [me["ticket_id"]]); self.assertEqual(self.k.please_come(), [])
        self.assertEqual(self.q.please_come(self.m, self.place, come, now=T0), come); self.assertEqual(self.q.please_come(self.m, self.place, come, now=T0), [])
        first = tickets[3]["ticket_id"]; self.k.running_late(first)
        self.assertEqual(self.k.place(first), 4)                                                           # back 3 places
        with self.assertRaisesRegex(LocalRejection, "already_used_once"): self.k.running_late(first)
        self.q.leave(self.m, me["ticket_id"], now=T0); self.k.leave(me["ticket_id"], from_cloud=True)     # asked on the internet: the cloud writes it once
        with self.assertRaisesRegex(LocalRejection, "ticket_finished"): self.k.leave(me["ticket_id"])
        self.sync(); self.assertEqual(len(self.events("TicketLeft")), 1); self.assertEqual(self.q.ticket(me["ticket_id"])["state"], "left")

    def test_the_person_is_told_in_their_language_and_the_number_is_forgotten_after_30_days(self):
        j = self.q.join(self.m, self.place, "GEN", "link", PHONE, lang="fr", now=T0)
        me = self.k.issue("GEN", via="smartphone", phone_mark=j["phone_mark"]); self.q.joined(j["join_id"], me["ticket_id"])
        self.k.counter_state(self.c1, "open"); self.k.call_next(self.c1); self.sync()
        told = [l for l in self.p.notifier.lines.values() if l["kind"] == "queue_your_turn"]
        self.assertEqual([(l["lang"], l["record"]) for l in told], [("fr", me["ticket_id"])]); self.assertTrue(told[0]["person"].startswith("pii_")); self.assertNotIn(PHONE, json.dumps(told))
        self.assertEqual(self.q.forget_contacts(now=T0 + 29 * DAY), 0)
        self.assertEqual(self.q.forget_contacts(now=T0 + 31 * DAY), 1)
        self.assertIsNone(self.q.db.execute("select contact_ref from qu_tickets where ticket_id=?", (me["ticket_id"],)).fetchone()[0])

    # ---- offline, taking over, closing
    def test_another_device_takes_over_with_the_same_queue_and_its_own_codes(self):
        a, b = self.give(2); self.k.counter_state(self.c1, "open"); self.k.call_next(self.c1)
        dev2 = uuid4(); box2 = LynkDVBox(self.m, self.place, dev2, self.staff, "manager", now=AT(T0))
        k2 = QueueKeeper(box2, self.q.add_device(self.m, self.place, dev2, "counter", self.boss, now=T0))
        self.assertEqual(k2.take_over_from(self.k), ["GEN", "LAB"])
        self.assertEqual(k2.order("GEN"), [b["ticket_id"]]); k2.served(self.c1)                           # the same queue, the same person being served
        c = k2.issue("GEN"); self.assertEqual(c["number"], "GEN-" + R.code(R.BLOCK_SIZE)); self.assertEqual(c["place"], 2)
        self.sync(); self.sync(box2)
        self.assertEqual(self.q.live(self.m, self.place, now=T0)["keeper"], dev2)
        self.assertEqual([e["payload"]["reason"] for e in self.events("TicketCodesVoided")], ["block_not_used", "block_not_used"])
        self.assertEqual(self.q.pack(self.dev, now=T0)["blocks"], {})                                     # the old keeper's unused codes are closed for good

    def test_days_offline_arrive_in_order_and_a_locked_device_is_refused(self):
        self.give(3); self.k.counter_state(self.c1, "open"); self.k.call_next(self.c1); self.k.served(self.c1)
        self.assertEqual(self.events("TicketIssued"), [])                                                  # nothing reached the cloud yet
        out = self.sync(now=T0 + 2 * DAY)
        self.assertTrue(all(r["state"] == "accepted" for r in out)); self.assertEqual(len(self.events("TicketIssued")), 3)
        self.q.lock_device(self.m, self.dev, self.boss, now=T0)
        self.assertEqual([(e["payload"]["section"], e["payload"]["first"], e["payload"]["reason"]) for e in self.events("TicketCodesVoided")], [("GEN", "222225", "device_locked"), ("LAB", "222222", "device_locked")])
        self.k.issue("GEN"); self.assertEqual(self.sync()[0]["reason"], "device_not_added")
        with self.assertRaisesRegex(PermissionError, "device_locked"): self.q.pack(self.dev)

    def test_closing_marks_tickets_not_served_today(self):
        a, b, c = self.give(3); self.k.counter_state(self.c1, "open"); self.k.call_next(self.c1); self.k.served(self.c1); self.sync()
        left = self.q.close_day(self.m, self.place, now=T0 + 8 * 3600); self.assertEqual(sorted(left), sorted(self.k.close_day()))
        self.assertEqual(len(left), 2); self.assertEqual(len(self.events("TicketNotServedToday")), 2)
        self.assertEqual(self.q.ticket(b["ticket_id"])["state"], "not_served_today")
        rep = self.q.report(self.m, self.place, T0 - DAY, T0 + DAY)
        self.assertEqual(rep["rows"], [{"section": "GEN", "tickets": 3, "served": 1, "missed": 0, "left": 0, "not_served_today": 2, "average_wait_minutes": 0}])
        self.assertEqual(rep["busiest_hour"], 9)

    # ---- the manager and the public
    def test_live_view_suggestion_please_check_and_device_health(self):
        self.give(2); self.sync()
        live = self.q.live(self.m, self.place, now=T0 + 45 * 60); gen = live["sections"][0]
        self.assertEqual((gen["waiting"], gen["longest_wait_minutes"], gen["suggest_open_counter"]), (2, 45, True))     # LynkAssist suggests; the manager decides
        other = uuid4()
        for t in self.give(4): self.k.mark_priority(t["ticket_id"], self.staff)
        self.k.mark_priority(self.give(1)[0]["ticket_id"], other); self.sync()
        self.assertEqual(self.q.please_check(self.m, now=T0), [{"staff": self.staff, "sign": "priority", "times": 4}])   # a flag, never an accusation
        printer = uuid4(); self.q.add_device(self.m, self.place, printer, "printer", self.boss, now=T0); self.q.device_health(self.m, printer, "paper_low", now=T0)
        self.assertEqual([d["health"] for d in self.q.devices(self.m, self.place)], ["ok", "paper_low"])

    def test_the_public_queue_page_shows_numbers_only_when_switched_on(self):
        self.assertIsNone(self.q.public_page(self.place))
        self.q.set_public_page(self.m, self.place, True, self.boss); a = self.give(3)[0]; self.k.counter_state(self.c1, "open"); self.k.call_next(self.c1); self.sync()
        page = self.q.public_page(self.place)
        self.assertEqual(page["sections"][0], {"section": "GEN", "waiting": 2, "about_minutes": 12, "now_serving": [a["number"]]})
        self.assertEqual(set(page["sections"][0]), {"section", "waiting", "about_minutes", "now_serving"})

    def test_reports_and_forecast_follow_the_plan(self):
        self.give(3); self.sync()
        self.assertEqual(len(self.q.report(self.m, self.place, T0 - DAY, T0 + DAY, by="hour")["rows"]), 1)
        self.assertEqual(self.q.forecast(self.m, self.place, AT(T0).weekday())[0], {"section": "GEN", "hour": 9, "tickets": 3})
        self.p.billing.set_plan(self.m, "lynkqueue", "free")
        with self.assertRaisesRegex(PermissionError, "plan_daily_summary_only"): self.q.report(self.m, self.place, T0 - DAY, T0 + DAY, by="counter")
        with self.assertRaisesRegex(PermissionError, "plan_no_busy_forecast"): self.q.forecast(self.m, self.place, 0)

    def test_nobody_is_turned_away_on_the_day_and_only_places_that_gave_tickets_are_billed(self):
        other = self.q.add_place(self.m, self.boss, now=T0)                                               # gave no ticket: not counted
        self.give(2); self.sync()
        bill = self.q.billable(self.m, T0 - DAY, T0 + DAY); self.assertEqual((bill["places"], bill["extra_place_cents"], bill["extra_ticket_cents"]), (1, 0, 0))
        self.q.db.execute("update qu_tickets set issued=issued where 1"); many = [(uuid4(), self.m, self.place, "GEN", "GEN", R.code(5000 + i), "kiosk", T0) for i in range(3100)]
        self.q.db.executemany("insert into qu_tickets values(?,?,?,?,?,?,?,0,'served',?,null,null,null,0,null,null,null,'en',0,0)", many)
        bill = self.q.billable(self.m, T0 - DAY, T0 + DAY); self.assertEqual((bill["extra_tickets"], bill["extra_ticket_cents"]), (102, 200))   # paid tiers: extra tickets just cost more
        self.assertFalse(self.q.pack(self.dev, now=T0 + DAY)["free_limit_reached"])
        self.p.billing.set_plan(self.m, "lynkqueue", "free")
        self.assertFalse(self.q.pack(self.dev, now=T0)["free_limit_reached"])                              # the day the limit is reached keeps working until closing
        pack = self.q.pack(self.dev, now=T0 + DAY); self.assertTrue(pack["free_limit_reached"])
        box = LynkDVBox(self.m, self.place, self.dev, self.staff, "manager", now=AT(T0 + DAY)); k = QueueKeeper(box, pack)
        with self.assertRaisesRegex(LocalRejection, "free_limit_reached"): k.issue("GEN")

    # ---- automations (catalog/automations.v1.json, run by LynkFlow)
    def test_please_come_and_the_long_wait_suggestion_run_once(self):
        self.k.counter_state(self.c1, "open"); self.give(2)
        j = self.q.join(self.m, self.place, "GEN", "link", PHONE, now=T0); me = self.k.issue("GEN", via="smartphone", phone_mark=j["phone_mark"]); self.q.joined(j["join_id"], me["ticket_id"]); self.sync()
        come = self.k.please_come(); f = self.p.flow
        self.assertEqual(f.metric("place_is_5", self.m, {"place_id": self.place, "ticket_ids": come}, me["ticket_id"], now=T0)[0]["told"], 1)
        self.assertEqual(f.metric("place_is_5", self.m, {"place_id": self.place, "ticket_ids": come}, me["ticket_id"], now=T0), [])
        gen = self.q.live(self.m, self.place, now=T0 + 40 * 60)["sections"][0]; self.assertTrue(gen["suggest_open_counter"])
        ran = f.metric("longest_wait_over_30", self.m, {"place_id": self.place, "section": "GEN", "longest_wait_minutes": gen["longest_wait_minutes"]}, f"{self.place}:GEN:9", now=T0 + 40 * 60)
        self.assertEqual((ran[0]["level"], ran[0]["suggested"]), ("inform", "GEN"))                       # only a suggestion: nothing was opened
        self.assertEqual([c["state"] for c in self.q.live(self.m, self.place, now=T0)["counters"]], ["open", "closed", "closed"])

    def test_closing_and_the_forecast_run_by_themselves(self):
        self.give(3); self.sync(); f = self.p.flow
        self.assertEqual(f.tick("closing", [self.m], now=T0 + 3600), [])                                   # still open: nothing is closed early
        self.assertEqual(f.tick("closing", [self.m], now=T0 + DAY + 8 * 3600 + 60)[0]["closed"], 3)
        self.assertEqual(len(self.events("TicketNotServedToday")), 3)
        self.assertEqual(f.tick("daily", [self.m], now=T0 + 6 * DAY)[0]["places"], 1)                      # the same weekday comes tomorrow

    def test_a_counter_follows_its_persons_check_in_and_a_collection_gets_a_ticket(self):
        member = uuid4(); self.q.set_counter_staff(self.m, self.lab, member, self.boss)
        self.assertEqual(self.p.flow.on_event(self.m, {"id": uuid4(), "type": "CheckedIn", "payload": {"member_id": member, "record_id": uuid4()}}, now=T0), [])   # a link is off until switched on
        self.p.flow.set_on(self.m, "attend-opens-queue-counter"); self.p.flow.set_on(self.m, "queue-pickup-collection")
        ran = self.p.flow.on_event(self.m, {"id": uuid4(), "type": "CheckedIn", "payload": {"member_id": member, "record_id": uuid4()}}, now=T0)
        self.assertIn(1, [r.get("counters") for r in ran])
        self.assertEqual(self.k.on_check(member, "in", self.q.counters_of(member)), [self.lab]); self.assertEqual(self.k.counters[self.lab]["state"], "open")
        self.give(1, "LAB"); self.k.call_next(self.lab)
        self.assertEqual(self.k.on_check(member, "out", [self.lab]), [])                                   # never closes in the middle of serving someone
        self.k.served(self.lab); self.assertEqual(self.k.on_check(member, "out", [self.lab]), [self.lab])
        point = uuid4(); self.q.set_pickup_section(self.m, point, self.place, "GEN", self.boss)
        ran = self.p.flow.on_event(self.m, {"id": uuid4(), "type": "ShipmentScanned", "payload": {"shipment_id": uuid4(), "scan_id": uuid4(), "piece": 1, "place_id": point, "step": "at_pickup_point"}}, now=T0)
        self.assertEqual(ran[0]["ready"], "GEN")
        ask = self.q.pending(self.place); self.assertEqual([a["way"] for a in ask], ["collection"])
        t = self.k.issue("GEN", via="api"); self.q.joined(ask[0]["join_id"], t["ticket_id"]); self.assertEqual(self.q.pending(self.place), [])


if __name__ == "__main__":
    unittest.main()
