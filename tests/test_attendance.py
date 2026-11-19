"""LynkAttend in full (LynkA; master blueprint section 63; build section 3B): registration, PINs, the door on the device (offline),
records, flags, hand check-in, missed check-out, the clock guard, warning signs, visitors, the fire list, the person's own page,
deletion requests and disputes. No event ever carries a PIN, an IDCN, an ID number, a name or a contact."""
import json, os, unittest
from datetime import datetime, timedelta, timezone

from contract.tools.validate_contract import uuid4, validate_event
from core import attendance as R
from dv.box import LocalRejection, LynkDVBox
from people.attendance import DAY, REQUEST_REMINDER_DAYS, Attendance
from people.door import Door
from services.platform import Platform

T0 = 1_800_000_000.0 - 1_800_000_000.0 % DAY + 8 * 3600        # 08:00 on a fixed day
AT = lambda t: datetime.fromtimestamp(t, tz=timezone.utc)
SECRETS = ("482915", "300442", "A6F87399", "687399", "grace@example.org", "Grace N.")


class AttendanceTests(unittest.TestCase):
    def setUp(self):
        os.environ.pop("LYNK_MODE", None)
        self.p = Platform(); self.a = self.p.attendance; self.m = uuid4(); self.boss = uuid4()
        self.p.billing.set_plan(self.m, "lynkattend", "plus")
        self.a.add_manager(self.m, self.boss, "boss@example.org", now=T0)
        self.place = self.a.add_place(self.m, self.boss, shift_end_min=17 * 60, now=T0)
        self.dev = uuid4(); self.a.add_door_device(self.m, self.place, self.dev, self.boss, now=T0)
        self.box = LynkDVBox(self.m, self.place, self.dev, uuid4(), "manager", now=AT(T0))

    def person(self, id_number, set_name="idcn", name="Grace N.", contact="grace@example.org", **kw):
        member = self.a.register(self.m, self.place, self.boss, id_number, "work", set_name, contact, name, now=T0, **kw)
        self.a.agree(member, "email_link", now=T0); self.a.confirm(self.m, member, self.boss, now=T0); self.a.create_pin(self.m, member, self.boss, now=T0)
        return member, self.a.show_pin(self.m, member, self.boss, now=T0)
    def door(self, **kw): return Door(self.box, self.a.door_pack(self.dev), **kw)
    def sync(self, now=None):
        out = [self.a.ingest(self.m, e, now=now) for e in self.box.log[getattr(self, "_sent", 0):]]; self._sent = len(self.box.log); return out
    def events(self, *types): return self.p.c.store.of(self.m, *types)

    # ---- registration and PINs
    def test_registration_needs_a_manager_an_id_document_and_the_persons_agreement(self):
        with self.assertRaises(PermissionError): self.a.register(self.m, self.place, uuid4(), "A6F87399", "work", "idcn", "x@example.org", "X")
        with self.assertRaisesRegex(ValueError, "id_document_too_few_digits"): self.a.register(self.m, self.place, self.boss, "DYY87HIO", "work", "idcn", "x@example.org", "X")
        member = self.a.register(self.m, self.place, self.boss, "A6F87399", "official", "face_idcn", "grace@example.org", "Grace N.", now=T0)
        with self.assertRaisesRegex(ValueError, "the_person_has_not_agreed"): self.a.confirm(self.m, member, self.boss)
        with self.assertRaisesRegex(ValueError, "id_number_does_not_match"): self.a.agree(member, "full_id_number", "687399")     # the full ID number, not the IDCN
        self.assertEqual(self.a.agree(member, "full_id_number", "A6F87399", now=T0), ["face", "no_sharing"])
        self.assertEqual(self.a.needs_enrolment(member), ["face"])
        with self.assertRaisesRegex(ValueError, "confirm_first"): self.a.create_pin(self.m, member, self.boss)
        self.a.confirm(self.m, member, self.boss, now=T0); self.a.create_pin(self.m, member, self.boss, now=T0)
        self.assertEqual(self.a.my_details(member)["idcn"], "687399")
        self.assertEqual([e["type"] for e in self.events("AttendancePersonRegistered", "AttendanceConsentRecorded", "AttendancePinCreated")],
                         ["AttendancePersonRegistered", "AttendanceConsentRecorded", "AttendancePinCreated"])

    def test_pins_are_created_by_lynkomni_never_easy_never_twice_and_a_blocked_pin_is_dead(self):
        pins = set()
        for i in range(30):
            _, pin = self.person(f"ID{100000 + i}")
            self.assertRegex(pin, r"^\d{6}$"); self.assertFalse(R.is_easy_pin(pin)); self.assertNotIn(pin, pins); pins.add(pin)
        member, pin = self.person("R4279")
        with self.assertRaisesRegex(ValueError, "only_a_blocked_pin"): self.a.recreate_pin(self.m, member, self.boss)
        self.a.block_pin(self.m, member, self.boss, now=T0); self.a.recreate_pin(self.m, member, self.boss, now=T0)
        new = self.a.show_pin(self.m, member, self.boss, now=T0)
        self.assertNotEqual(new, pin); self.assertEqual(self.a.pin_group(self.place)["used"], 32)          # the dead PIN stays used for ever
        self.assertEqual(len(self.events("AttendancePinShown")), 32, "every Show is recorded")
        self.assertIn("pin_shown", [h["what"] for h in self.a.history(self.m)])

    def test_the_pin_and_idcn_go_only_to_the_persons_own_contact(self):
        member, _ = self.person("A6F87399")
        self.assertEqual(self.a.send_pin(self.m, member, "email", self.boss, now=T0), {"state": "sent", "channel": "email"})
        self.assertEqual(self.a.send_pin(self.m, member, "text", self.boss, now=T0), {"state": "coming_soon"}, "text waits for the messaging partner")
        self.assertEqual([e["payload"]["channel"] for e in self.events("AttendancePinSent")], ["email"])
        self.assertEqual([l["kind"] for l in self.p.notifier.lines.values() if l["person"] == member], ["attend_pin_sent"])

    def test_free_covers_fifteen_people_one_branch_and_two_door_devices(self):
        m = uuid4(); self.a.add_manager(m, self.boss, "boss@example.org"); place = self.a.add_place(m, self.boss)
        with self.assertRaisesRegex(PermissionError, "branch_limit"): self.a.add_place(m, self.boss)
        for i in range(15): self.a.register(m, place, self.boss, f"ID{2000 + i}", "work", "idcn", "", f"P{i}")
        with self.assertRaisesRegex(PermissionError, "people_limit_for_tier"): self.a.register(m, place, self.boss, "ID9999", "work", "idcn", "", "P")
        self.a.add_door_device(m, place, uuid4(), self.boss); self.a.add_door_device(m, place, uuid4(), self.boss)
        with self.assertRaisesRegex(PermissionError, "door_device_limit"): self.a.add_door_device(m, place, uuid4(), self.boss)

    # ---- the door
    def test_the_door_pack_holds_only_locked_check_values(self):
        member, pin = self.person("A6F87399")
        pack = json.dumps(self.a.door_pack(self.dev))
        for secret in (pin, "687399", "A6F87399", "Grace", "grace@"): self.assertNotIn(secret, pack)
        with self.assertRaises(PermissionError): self.a.door_pack(uuid4())
        with self.assertRaisesRegex(LocalRejection, "device_not_registered"): Door(self.box).who(pin)

    def test_pin_first_then_idcn_with_a_checker_who_is_not_the_person(self):
        grace, gpin = self.person("A6F87399"); eric, epin = self.person("R4279", name="Eric")
        self.a.set_checkers(self.m, self.place, [grace, eric], self.boss, now=T0)
        d = self.door()
        self.assertEqual(d.check(gpin, "in")["result"], "waiting")
        with self.assertRaisesRegex(ValueError, "select_a_checker"): d.check(gpin, "in", ["687399"])
        with self.assertRaisesRegex(ValueError, "not_a_checker"): d.check(gpin, "in", ["687399"], checker=grace)
        r = d.check(gpin, "in", ["687399"], checker=eric)
        self.assertEqual((r["result"], r["means"], r["flags"]), ("in", "idcn", ["checker_not_checked_in"]))       # still checked in, and flagged
        with self.assertRaisesRegex(LocalRejection, "already_checked_in"): d.check(gpin, "in", ["687399"], checker=eric)
        self.assertEqual(d.check(epin, "in", ["427900"], checker=grace)["flags"], [], "Grace is inside now")
        self.box.advance(hours=9, minutes=6)
        out = d.check(gpin, "out", ["687399"], checker=eric)
        self.assertEqual(out["minutes"], 546)
        with self.assertRaisesRegex(LocalRejection, "not_checked_in"): d.check(gpin, "out", ["687399"], checker=eric)
        for e in self.box.log: self.assertEqual(validate_event(e), [])
        self.assertEqual([x["state"] for x in self.sync(now=T0 + 10 * 3600)], ["accepted"] * 3)
        live = {x["member_id"]: x for x in self.a.live(self.m, now=T0 + 10 * 3600)["people"]}
        self.assertEqual((live[grace]["state"], live[eric]["state"], live[eric]["checker_id"]), ("left", "inside", grace))
        self.assertEqual(self.a.hours(self.m, grace, int(T0 // DAY), int(T0 // DAY)), 546)

    def test_face_or_finger_fails_three_times_and_the_backup_is_marked(self):
        grace, gpin = self.person("A6F87399", "face_finger_idcn"); eric, _ = self.person("R4279", name="Eric")
        self.a.set_checkers(self.m, self.place, [eric], self.boss)
        d = self.door()
        r = d.check(gpin, "in", ["fail", "fail", "fail", "ok"])
        self.assertEqual((r["result"], r["means"], r["backup_from"]), ("in", "finger", "face_failed"))
        d.check(gpin, "out", ["ok"])
        no_readers = self.door(readers=())                                  # a device with no camera or reader goes straight to IDCN
        r = no_readers.check(gpin, "in", ["687399"], checker=eric)
        self.assertEqual((r["means"], r["backup_from"]), ("idcn", "face_not_working"))

    def test_face_and_finger_patterns_never_leave_the_door_device(self):
        """Security control attend-biometrics-on-device-only: the reader on the door device compares the face or finger itself and
        tells the door only whether it matched; the door pack from the cloud holds no pattern, and no event carries one."""
        grace, gpin = self.person("A6F87399", "face_finger_idcn")
        pack = self.a.door_pack(self.dev)
        self.assertFalse({"face", "finger", "template", "pattern"} & {k for p in pack["people"] for k in p}, "no pattern in the door pack")
        self.door().check(gpin, "in", ["ok"])
        self.sync(now=T0 + 3600)
        every = json.load(open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "contract", "event-payloads.v6.json"), encoding="utf-8"))["events"]
        cloud = self.p.c.store.of(self.m, *every); self.assertTrue(cloud)
        for e in self.box.log + cloud:
            self.assertFalse({"template", "pattern", "image", "face_data", "finger_data"} & set(e["payload"]), e["type"])
        for e in self.box.log: self.assertEqual(validate_event(e), [])

    def test_five_wrong_idcns_block_the_pin_and_five_unknown_pins_pause_the_device(self):
        grace, gpin = self.person("A6F87399"); eric, _ = self.person("R4279", name="Eric")
        self.a.set_checkers(self.m, self.place, [eric], self.boss)
        d = self.door()
        self.assertEqual(d.check(gpin, "in", ["000001"] * 5, checker=eric)["result"], "pin_blocked")
        with self.assertRaisesRegex(LocalRejection, "pin_blocked"): d.who(gpin)
        self.sync(now=T0)
        self.assertEqual(self.a.my_details(grace)["pin_state"], "blocked")
        self.assertEqual(self.events("AttendancePinBlocked")[0]["payload"]["reason"], "idcn_wrong_5_times")
        self.assertIn("attend_pin_blocked", [l["kind"] for l in self.p.notifier.lines.values() if l["person"] == self.boss])
        for _ in range(5):
            with self.assertRaisesRegex(LocalRejection, "pin_not_recognised"): d.who("999990")
        with self.assertRaisesRegex(LocalRejection, "device_paused"): d.who("999990")
        self.box.advance(seconds=R.PIN_PAUSE_SECONDS + 1)
        with self.assertRaisesRegex(LocalRejection, "pin_not_recognised"): d.who("999990")

    def test_hand_check_in_needs_a_reason_and_another_manager(self):
        grace, _ = self.person("A6F87399"); d = self.door()
        with self.assertRaisesRegex(LocalRejection, "own_record"): d.by_hand(grace, grace, "all_means_failed")
        with self.assertRaisesRegex(LocalRejection, "reason_missing"): d.by_hand(grace, self.boss, "")
        r = d.by_hand(grace, self.boss, "all_means_failed")
        self.assertEqual(r["flags"], ["by_hand"]); self.sync(now=T0)
        self.assertEqual(self.a.live(self.m, now=T0)["people"][0]["means"], "hand")
        self.assertIn("attend_flag_for_manager", [l["kind"] for l in self.p.notifier.lines.values()])

    def test_only_added_devices_count_and_a_locked_device_is_refused(self):
        grace, gpin = self.person("A6F87399", "face_idcn"); d = self.door()
        d.check(gpin, "in", ["ok"])
        other = LynkDVBox(self.m, self.place, uuid4(), uuid4(), "manager", now=AT(T0)); other._emit("CheckedIn", dict(self.box.log[-1]["payload"], device_id=other.d))
        self.assertEqual(self.a.ingest(self.m, other.log[-1])["reason"], "device_not_registered")
        self.a.lock_device(self.m, self.dev, self.boss)
        self.assertEqual(self.sync()[0]["reason"], "device_not_registered")
        self.assertEqual(self.a.live(self.m, now=T0)["inside"], 0)

    # ---- after the door
    def test_was_this_you_not_me_and_the_persons_off_switch(self):
        grace, gpin = self.person("A6F87399", "face_idcn"); d = self.door()
        rec = d.check(gpin, "in", ["ok"])["record_id"]; self.sync(now=T0)
        mine = [l for l in self.p.notifier.lines.values() if l["person"] == grace and l["kind"] == "attend_was_this_you"]
        self.assertEqual(len(mine), 1)
        self.a.not_me(grace, rec, now=T0)
        self.assertEqual(self.events("CheckInFlagged")[0]["payload"], {"record_id": rec, "flag": "not_me"})
        self.assertEqual(self.a.live(self.m, now=T0)["people"][0]["flags"], ["not_me"])
        self.a.set_was_this_you(grace, False); d.check(gpin, "out", ["ok"]); self.sync(now=T0)
        self.assertEqual(len([l for l in self.p.notifier.lines.values() if l["person"] == grace and l["kind"] == "attend_was_this_you" and l["count"] == 1]), 1)

    def test_missed_check_out_is_marked_and_fixed_only_by_the_manager_with_a_reason(self):
        grace, gpin = self.person("A6F87399", "face_idcn"); d = self.door()
        rec = d.check(gpin, "in", ["ok"])["record_id"]; self.sync(now=T0)
        self.assertEqual(self.a.mark_no_check_out(self.m, now=T0 + 10 * 3600), [], "the shift ends at 17:00; marked 2 hours later")
        self.assertEqual(self.p.flow.tick("shift_end_plus_2h", [self.m], now=T0 + 11 * 3600 + 60)[0]["marked"], 1)
        with self.assertRaisesRegex(ValueError, "reason_missing"): self.a.correct(self.m, rec, self.boss, "", out_at=T0 + 9 * 3600)
        self.a.correct(self.m, rec, self.boss, "missed_check_out", out_at=T0 + 9 * 3600, now=T0 + 12 * 3600)
        row = self.p.c.store.db.execute("select minutes, history from at_records where record_id=?", (rec,)).fetchone()
        self.assertEqual(row[0], 540); self.assertEqual(json.loads(row[1])[0]["out_at"], None, "the old line is kept")
        boss_member, bpin = self.person("B5550001", "face_idcn", name="Boss")
        self.p.c.store.db.execute("update at_members set member_id=? where member_id=?", (self.boss, boss_member))
        self.p.c.store.db.execute("insert into at_records values(?,?,?,?,?,?,null,'face',null,null,'[]',null,'[]')", ("r-own", self.m, self.boss, self.place, self.dev, T0))
        with self.assertRaisesRegex(PermissionError, "own_record"): self.a.correct(self.m, "r-own", self.boss, "other", out_at=T0 + 60)

    def test_a_wrong_device_clock_marks_its_records(self):
        grace, gpin = self.person("A6F87399", "face_idcn"); d = self.door()
        self.assertEqual(self.a.clock_check(self.m, self.dev, T0 + 30, now=T0), [])
        rec = d.check(gpin, "in", ["ok"])["record_id"]; self.sync(now=T0)
        self.assertEqual(self.a.clock_check(self.m, self.dev, T0 + 3 * 3600, now=T0 + 3600), [rec])
        self.assertIn("device_clock_wrong", self.a.live(self.m, now=T0)["people"][0]["flags"])

    def test_warning_signs_are_only_flags(self):
        grace, gpin = self.person("A6F87399"); eric, epin = self.person("R4279", name="Eric")
        self.a.set_checkers(self.m, self.place, [eric, grace], self.boss)
        d = self.door()
        for day in range(3):
            d.check(gpin, "in", ["687399"], checker=eric); self.box.advance(seconds=20)          # Eric is never in when Grace names him
            d.check(epin, "in", ["427900"], checker=grace); self.box.advance(hours=8)
            d.check(gpin, "out", ["687399"], checker=eric); d.check(epin, "out", ["427900"], checker=grace); self.box.advance(hours=16, seconds=-20)
        self.sync(now=T0 + 3 * DAY)
        found = self.p.flow.tick("hourly", [self.m], now=T0 + 3 * DAY)
        signs = {x[1] for x in self.a.warning_signs(self.m, now=T0 + 3 * DAY)} | {r[0] for r in self.p.c.store.db.execute("select sign from at_signs")}
        self.assertEqual(found[0]["please_check"], 2); self.assertEqual(signs, {"same_pair", "checker_often_absent"})
        self.assertEqual({e["payload"]["flag"] for e in self.events("CheckInFlagged")}, {"warning_sign"})
        self.a.set_leave(self.m, grace, int((T0 + 5 * DAY) // DAY), int((T0 + 6 * DAY) // DAY), self.boss)
        self.box.advance(days=2); d.check(gpin, "in", ["687399"], checker=eric); self.sync(now=T0 + 5 * DAY)
        self.assertIn(("on_leave",), self.p.c.store.db.execute("select sign from at_signs where member=?", (grace,)).fetchall())

    # ---- visitors and the fire list
    def test_a_visitor_without_an_id_document_waits_for_the_managers_yes(self):
        grace, gpin = self.person("A6F87399", "face_idcn"); d = self.door(); d.check(gpin, "in", ["ok"])
        v1 = d.visitor_in(grace, "official"); v2 = d.visitor_in(grace, "none")
        self.assertEqual((v1["state"], v2["state"]), ("inside", "waiting_for_manager"))
        self.sync(now=T0); self.a.visitor_details(self.m, v1["visitor_id"], "Visitor One", "P1234567")
        self.assertEqual(len(self.a.inside(self.m)["visitors"]), 1)
        self.a.decide_visitor(self.m, v2["visitor_id"], "allow", self.boss, now=T0)
        self.assertEqual(len(self.a.inside(self.m)["visitors"]), 2)
        self.assertEqual(d.fire_list(self.boss), {"staff": [grace], "visitors": [v1["visitor_id"]]})
        self.assertEqual(self.a.purge_visitors(now=T0 + 31 * DAY), 1, "a visitor's ID number is deleted after 30 days")
        self.assertIsNone(self.p.c.store.db.execute("select id_ref from at_visitors where visitor_id=?", (v1["visitor_id"],)).fetchone()[0])

    # ---- the person's control
    def test_delete_my_details_reminders_and_automatic_deletion_after_thirty_days(self):
        grace, gpin = self.person("A6F87399", "face_idcn"); d = self.door()
        d.check(gpin, "in", ["ok"]); self.box.advance(hours=8); d.check(gpin, "out", ["ok"]); self.sync(now=T0 + 8 * 3600)
        rid = self.a.request(grace, "delete_my_details", now=T0)
        got = []
        for day in (6, 7, 14, 25, 29):
            got += [x[1] for x in self.a.requests_tick(now=T0 + day * DAY)["reminded"]]
        self.assertEqual(tuple(got), REQUEST_REMINDER_DAYS)
        self.assertEqual(self.p.flow.tick("daily", [self.m], now=T0 + 30 * DAY)[0]["deleted"], 1)
        with self.assertRaises(KeyError): self.a.my_details(grace)
        self.assertEqual(self.p.vault.delete_subject(grace), 0, "nothing personal is left in the vault")
        self.assertEqual(self.events("AttendanceDetailsDeleted")[0]["payload"], {"member_id": grace, "by": "thirty_days_passed"})
        self.assertEqual(self.a.pin_group(self.place)["used"], 1, "the deleted PIN is never given again")
        with self.assertRaisesRegex(LocalRejection, "pin_not_recognised"): self.door().who(gpin)

    def test_no_event_and_no_notice_carries_a_secret(self):
        grace, gpin = self.person("A6F87399"); eric, _ = self.person("R4279", name="Eric")
        self.a.set_checkers(self.m, self.place, [eric], self.boss); self.a.send_pin(self.m, grace, "email", self.boss, now=T0)
        d = self.door(); d.check(gpin, "in", ["687399"], checker=eric); self.sync(now=T0); self.a.request(grace, "dispute", now=T0)
        blob = json.dumps([e["payload"] for e in self.p.c.store.of(self.m)]) + json.dumps([l["facts"] for l in self.p.notifier.lines.values()])
        for secret in (gpin, "687399", "A6F87399", "grace@example.org", "Grace N."): self.assertNotIn(secret, blob)

    def test_only_people_who_checked_in_are_billed(self):
        people = [self.person(f"ID{3000 + i}", "face_idcn", name=f"P{i}") for i in range(52)]
        d = self.door()
        for _, pin in people[:51]: d.check(pin, "in", ["ok"])
        self.sync(now=T0)
        self.assertEqual(self.a.billable(self.m, T0 - DAY, T0 + DAY), {"people": 51, "included": 50, "extra_people": 1, "extra_cents": 150})


if __name__ == "__main__": unittest.main()
