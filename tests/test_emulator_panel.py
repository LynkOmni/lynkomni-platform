"""The Emulator Panel (EMULATOR UPDATE, master blueprint section 70; build section 3A): the register and its four checks, the rules
(core/emulators.py) and the cloud service (services/emulator_panel.py) with the device side (dv/panel_device.py)."""
import os, unittest
from datetime import datetime, timezone

from contract.tools.validate_contract import uuid4, validate_event
from core import build_sections, emulators as E
from dv.box import LynkDVBox, LocalRejection
from dv.panel_device import PanelDevice
from services import billing
from services.platform import Platform

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T0 = 1_800_000_000
PHONE = {"short_side": 390, "touch": True, "keys": False, "camera": True, "speaker": True, "vibration": True}
TV = {"short_side": 1080, "touch": False, "keys": True, "camera": False, "speaker": True}


class Register(unittest.TestCase):
    def test_every_emulator_states_the_four_checks(self):
        for e in E.REG["emulators"]:
            self.assertEqual(E.four_checks(e), [], e["id"])
        bad = dict(E.EMULATORS["pos.terminal"], checks={"touch": True, "buttons_only": False, "offline": "works", "sides": ["internal"]})
        self.assertEqual(E.four_checks(bad), ["buttons_only"])

    def test_every_built_emulator_is_registered_or_says_why_not(self):
        built = {d for d in os.listdir(os.path.join(ROOT, "web", "emulators")) if os.path.isfile(os.path.join(ROOT, "web", "emulators", d, "app.ts"))}
        on_panel = {e["built_in"] for e in E.REG["emulators"] if e["built_in"]}
        self.assertEqual(built, on_panel | set(E.REG["not_on_the_panel"]))
        self.assertFalse(on_panel & set(E.REG["not_on_the_panel"]))

    def test_names_services_and_sections_are_real(self):
        for e in E.REG["emulators"]:
            self.assertIn(e["service"], billing.FAMILIES, e["id"])
            self.assertTrue(set(e["devices"]) <= set(E.DEVICE_NAMES), e["id"])
            self.assertIn(e["build_section"], build_sections.ORDER, e["id"])
            self.assertEqual(e["planned"], e["built_in"] is None, e["id"])
            if e["customer_facing"]: self.assertEqual((e["counted"], e["user"]), (False, "none"), e["id"])
            if e["shared_with"]: self.assertIn(e["shared_with"], billing.FAMILIES)
            for h in e["hardware"]: self.assertIn(h, E.HARDWARE_WAYS, e["id"])
        services = {e["service"] for e in E.REG["emulators"]}
        self.assertFalse(services & set(E.REG["no_panel_services"]))
        self.assertTrue(services <= set(billing.EMULATOR_FAMILIES))

    def test_every_counted_family_has_its_slots(self):
        for e in E.REG["emulators"]:
            fam = E.counts_for(e["id"])
            if fam: self.assertIn("emulator_slots", billing.FEATURES[fam][0], fam)


class Rules(unittest.TestCase):
    def test_only_connected_staff_emulators_count_and_a_shared_till_counts_once(self):
        conns = [{"device": "a", "emulator": "pos.terminal", "connected": True}, {"device": "a", "emulator": "rewards.till", "connected": True},
                 {"device": "a", "emulator": "pay.till", "connected": True}, {"device": "b", "emulator": "pos.customer_display", "connected": True},
                 {"device": "c", "emulator": "pos.merchant_phone", "connected": True, "practice": True}, {"device": "d", "emulator": "pos.rider_phone", "connected": False}]
        self.assertEqual(E.in_use("lynkpos", conns), 1)
        self.assertEqual(E.may_connect(1, "lynkpos", conns, {"device": "e", "emulator": "pos.counter_tablet"}), (False, "plan_limit"))
        self.assertEqual(E.may_connect(1, "lynkpos", conns, {"device": "e", "emulator": "pos.counter_tablet"}, extra=1), (True, None))
        self.assertEqual(E.may_connect(1, "lynkpos", conns, {"device": "e", "emulator": "pos.customer_display"}), (True, None))   # free and unlimited
        self.assertEqual(E.may_connect(1, "lynkpos", conns, {"device": "e", "emulator": "pos.terminal", "practice": True}), (True, None))
        self.assertEqual(E.may_connect("own_units", "lynkqueue", conns, {"device": "e", "emulator": "queue.counter"}), (True, None))
        self.assertEqual(E.slots("lynkpos", "plus"), 2); self.assertIsNone(E.slots("lynkstock", "max")); self.assertEqual(E.extra_slot_cents("lynkpos"), 800); self.assertIsNone(E.extra_slot_cents("lynkattend"))

    def test_codes_work_once_and_expire(self):
        self.assertTrue(E.code_valid(T0, T0 + 599)); self.assertFalse(E.code_valid(T0, T0 + 601)); self.assertFalse(E.code_valid(T0, T0 + 5, used=True))
        self.assertRegex(E.new_code(12345), r"^[2-9A-HJ-NP-Z]{6}$")

    def test_the_check_before_assigning_refuses_only_what_cannot_run(self):
        self.assertEqual(E.can_run("queue.board", dict(PHONE))["refused"], "screen_too_small")
        self.assertEqual(E.can_run("stock.scanner", dict(PHONE, camera=False))["missing"], [{"need": "camera_or_scanner", "way": "connect_a_scanner"}])
        self.assertTrue(E.can_run("stock.scanner", dict(PHONE, camera=False, hardware=["scanner"]))["ok"])
        self.assertEqual(E.can_run("pos.terminal", {"short_side": 400})["refused"], "no_way_to_use")
        self.assertEqual(E.can_run("queue.board", dict(TV, speaker=False))["missing"], [{"need": "speaker", "way": "use_a_device_with_sound"}])

    def test_hardware_says_the_way_that_works(self):
        self.assertEqual(E.connect_ways("receipt_printer", "ios"), ["network", "device_print"])
        self.assertEqual(E.hardware_advice("fingerprint_reader", "ios"), {"ways": [], "fallback": "through_another_device"})
        self.assertEqual(E.connect_ways("scale", "android")[0], "usb")

    def test_tones_follow_the_manager_the_user_and_quiet_times(self):
        mgr = {"tones": True, "vibration": True, "volume": "medium", "user_may_change": True}
        self.assertEqual(E.tones(mgr, {"volume": "low"})["volume"], "low")
        self.assertEqual(E.tones(dict(mgr, user_may_change=False), {"tones": False})["tones"], True)
        self.assertEqual(E.tones(mgr, {"tones": False}, customer_facing=True)["tones"], True)          # a kiosk follows the manager
        self.assertFalse(E.tones(mgr, quiet_hours=True)["tones"]); self.assertFalse(E.tones(mgr, vibrates=False)["vibration"])
        self.assertEqual(E.tones(dict(mgr, pin_same_tone=True))["pin_tones"], "same")

    def test_the_delivery_menu_shows_only_what_works_now(self):
        ways = E.delivery_ways({"nearby": True}, online=False, printer_ready=True, customer_known=True, contact_given=True)
        self.assertEqual([(w["way"], w["state"]) for w in ways], [("print", "now"), ("qr", "now"), ("account", "queued"), ("lynkchat", "queued"),
                                                                  ("message", "queued"), ("nearby", "now"), ("file", "now")])
        self.assertEqual([w["way"] for w in E.delivery_ways({}, True, False, False, False)], ["qr", "file"])

    def test_fit_never_stretches_and_fills_the_spare_space(self):
        f = E.fit(1920, 1080, 390, 844)
        self.assertEqual((f["scale_pct"], f["artwork"]), (128, "sides"))
        self.assertEqual(E.fit(390, 844, 390, 844)["artwork"], "none")
        self.assertEqual(E.fit(200, 400, 390, 844)["scale_pct"], 75)                          # never below what keeps the text whole

    def test_states_are_the_five_and_downgrade_waits(self):
        self.assertTrue(all(E.request_state(s) in E.STATES for s in ("made_offline", "offered", "accepted", "connected", "denied", "expired")))
        conns = [{"device": d, "emulator": "pos.counter_tablet", "connected": True} for d in "abc"]
        self.assertEqual(E.downgrade(1, "lynkpos", conns), {"to_disconnect": 2, "grace_days": E.DOWNGRADE_GRACE_DAYS})

    def test_shared_vectors_and_the_typescript_register_are_current(self):
        import subprocess, sys
        r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "emulators_vectors.py"), "--check"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


class Panel(unittest.TestCase):
    def setUp(self):
        os.environ.pop("LYNK_MODE", None)
        self.p = Platform(); self.e = self.p.panel; self.m = uuid4(); self.boss = uuid4(); self.branch = uuid4()
        self.e.add_role(self.m, self.boss, "owner")
        self.phone = self.e.add_device(self.m, self.branch, "Counter 2", "LynkMobile", "android", PHONE, now=T0)
        self.tv = self.e.add_device(self.m, self.branch, "Waiting room", "LynkDScreen", "tv", TV, now=T0)
    def box(self, device, online=True):
        return LynkDVBox(self.m, self.branch, device, uuid4(), "manager", now=datetime.fromtimestamp(T0, timezone.utc), online=online)
    def give(self, emulator, device, now=T0, **kw):
        o = self.e.offer(self.m, emulator, self.boss, now=now, **kw)
        look = self.e.lookup(o["code"], now=now + 30)
        b = self.box(device); PanelDevice(b).answer(look["assignment_id"], True)
        return o, self.e.ingest(self.m, b.log[-1], now=now + 40)
    def events(self, *types): return self.p.c.store.of(self.m, *types)

    def test_a_code_works_once_and_the_device_accepts_or_denies(self):
        o, r = self.give("pos.merchant_phone", self.phone)
        self.assertEqual((o["state"], r["state"]), ("sent", "confirmed"))
        self.assertEqual(self.e.lookup(o["code"], now=T0 + 50)["reason"], "code_expired_or_used")
        o2 = self.e.offer(self.m, "queue.board", self.boss, now=T0)
        self.assertEqual(self.e.lookup(o2["code"], now=T0 + 3600)["reason"], "code_expired_or_used")
        o3 = self.e.offer(self.m, "queue.board", self.boss, now=T0); b = self.box(self.tv)
        PanelDevice(b).answer(self.e.lookup(o3["code"], now=T0)["assignment_id"], False)
        self.assertEqual(self.e.ingest(self.m, b.log[-1], now=T0 + 5)["reason"], "denied")
        with self.assertRaisesRegex(LocalRejection, "offline_not_possible"): PanelDevice(self.box(self.tv, online=False)).answer(o3["assignment_id"], True)
        for e in b.log: self.assertEqual(validate_event(e), [])
        self.assertEqual([e["type"] for e in self.events("EmulatorOffered", "EmulatorConnected")].count("EmulatorConnected"), 1)

    def test_only_the_owner_and_chosen_roles_assign_and_a_branch_manager_sees_their_branch(self):
        staff, other = uuid4(), uuid4()
        self.e.add_role(self.m, staff, "staff", by=self.boss)
        with self.assertRaisesRegex(PermissionError, "only_the_owner"): self.e.offer(self.m, "pos.terminal", staff)
        self.e.add_role(self.m, other, "manager", branch=uuid4(), by=self.boss)
        with self.assertRaisesRegex(PermissionError, "other_branch"): self.e.connect(self.m, [self.phone], "pos.merchant_phone", other)
        self.assertEqual(self.e.live(self.m, other), [])

    def test_the_plan_counts_staff_emulators_and_offers_an_extra_slot(self):
        self.give("pos.merchant_phone", self.phone)                                            # LynkPOS Free: 1 device
        tab = self.e.add_device(self.m, self.branch, "Till 2", "LynkTab", "android", dict(PHONE, short_side=800), now=T0)
        self.assertEqual(self.give("pos.counter_tablet", tab)[1], {"state": "failed", "reason": "plan_limit", "family": "lynkpos"})
        self.assertEqual(self.give("queue.board", self.tv)[1]["state"], "confirmed")           # customer-facing: free
        with self.assertRaisesRegex(PermissionError, "paid_tiers"): self.e.buy_extra_slot(self.m, "lynkpos", self.boss)
        self.p.billing.set_plan(self.m, "lynkpos", "plus"); self.p.billing.set_plan(self.m, "lynkpos", "plus")
        self.assertEqual(self.give("pos.counter_tablet", tab)[1]["state"], "confirmed")
        u = self.e.usage(self.m, self.boss)
        self.assertEqual((u["lynkpos"]["in_use"], u["lynkpos"]["limit"], u["free_screens"]), (2, 2, 1))
        self.assertEqual(self.e.buy_extra_slot(self.m, "lynkpos", self.boss), {"extra": 1, "monthly_cents": 800, "cheaper_tier": None})
        self.assertEqual(self.e.buy_extra_slot(self.m, "lynkpos", self.boss, n=2)["cheaper_tier"], "pro")        # Plus with 3 extras costs more than Pro

    def test_safe_disconnect_waits_for_an_offline_device_and_shows_the_message(self):
        self.give("pos.merchant_phone", self.phone)
        b = self.box(self.phone); PanelDevice(b).health(False, 7); self.e.ingest(self.m, b.log[-1], now=T0 + 60)
        self.assertEqual(self.e.disconnect(self.m, [self.phone], self.boss, now=T0 + 70)[0], {"state": "sent", "device_id": self.phone, "emulator": "pos.merchant_phone", "unsent": 7})
        self.assertEqual(next(x for x in self.e.live(self.m, self.boss) if x["device_id"] == self.phone)["emulators"][0]["state"], "disconnect_sent")
        PanelDevice(b).health(True, 0); self.e.ingest(self.m, b.log[-1], now=T0 + 90)
        self.assertEqual(self.e.device_view(self.phone, "pos.merchant_phone"), {"screen": "disconnected", "ask": True})
        PanelDevice(b).ask_to_connect("pos.merchant_phone"); self.e.ingest(self.m, b.log[-1], now=T0 + 95)
        self.assertIn("emulator_connect_asked", [l["kind"] for l in self.p.notifier.lines.values() if l["person"] == self.boss])
        self.assertEqual([e["payload"]["unsent"] for e in self.events("EmulatorDisconnected")], [0])

    def test_lost_swap_reapproval_and_temporary(self):
        self.give("pos.merchant_phone", self.phone, temporary_until_day=T0 // 86400)
        self.e.mark_lost(self.m, self.phone, self.boss)
        self.assertEqual(self.e.device_view(self.phone, "pos.merchant_phone"), {"screen": "locked_lost"})
        self.e.mark_lost(self.m, self.phone, self.boss, found=True)
        spare = self.e.add_device(self.m, self.branch, "Spare", "LynkMobile", "android", PHONE, now=T0)
        self.e.set_tones(self.m, self.phone, self.boss, volume="low")
        self.assertEqual(self.e.swap(self.m, self.phone, spare, "pos.merchant_phone", self.boss, now=T0 + 10)["state"], "confirmed")
        self.assertEqual(self.e.tones_for(spare, "pos.merchant_phone")["volume"], "low")
        self.assertEqual(self.e.daily(now=T0 + 86400 * 2)["ended"], 0)                          # the swap ended the temporary one already
        self.assertEqual(self.e.daily(now=T0 + 86400 * 31)["reapproval"], 3)
        self.assertEqual(self.give("queue.board", self.tv, now=T0 + 86400 * 31)[1]["reason"], "reapproval_needed")
        self.e.approve_again(self.m, self.tv, self.boss, now=T0 + 86400 * 31)
        self.assertEqual(self.give("queue.board", self.tv, now=T0 + 86400 * 31 + 60)[1]["state"], "confirmed")
        self.assertEqual(len(self.events("EmulatorSwapStarted", "EmulatorSwapped", "DeviceMarkedLost", "EmulatorReapprovalNeeded", "DeviceApprovedAgain")), 8)

    def test_users_history_and_screen_view_with_consent(self):
        self.give("pos.merchant_phone", self.phone); ama = uuid4()
        self.e.assign_to(self.m, self.phone, "pos.merchant_phone", self.boss, to="person", user_id=ama)
        with self.assertRaisesRegex(PermissionError, "customer_facing"): self.e.assign_to(self.m, self.tv, "queue.board", self.boss, to="role")
        b = self.box(self.phone); PanelDevice(b).user("pos.merchant_phone", "signed_in", ama); self.e.ingest(self.m, b.log[-1], now=T0 + 100)
        self.assertEqual(self.e.history(self.m, user_id=ama)[0]["device"], "Counter 2")
        self.assertEqual(self.e.view_screen(self.m, self.phone, self.boss, now=T0 + 110)["reason"], "no_consent")
        self.e.set_busy(self.phone, "payment")
        self.assertEqual(self.e.view_screen(self.m, self.phone, self.boss, consent_id=uuid4(), now=T0 + 120)["reason"], "busy")
        self.e.set_busy(self.phone, None)
        self.assertEqual(self.e.view_screen(self.m, self.phone, self.boss, consent_id=uuid4(), now=T0 + 130)["state"], "confirmed")
        self.assertIn("emulator_screen_view", [l["kind"] for l in self.p.notifier.lines.values() if l["person"] == ama])
        PanelDevice(b).user("pos.merchant_phone", "signed_out"); self.e.ingest(self.m, b.log[-1], now=T0 + 200)
        self.assertEqual(self.e.history(self.m, self.boss)[0]["until"], T0 + 200)

    def test_health_alerts_guided_setup_and_planned_emulators(self):
        self.give("pos.merchant_phone", self.phone)
        b = self.box(self.phone); PanelDevice(b).health(True, 0, battery_pct=9, printer="out_of_paper"); self.e.ingest(self.m, b.log[-1], now=T0 + 10)
        self.assertIn("emulator_device_alert", [l["kind"] for l in self.p.notifier.lines.values() if l["person"] == self.boss])
        setup = self.e.guided_setup(self.m, "lynkqueue", self.boss, now=T0)
        self.assertEqual([x["emulator"] for x in setup], ["queue.kiosk", "queue.reception", "queue.counter", "queue.counter_screen", "queue.board"])
        with self.assertRaisesRegex(PermissionError, "later_section"): self.e.offer(self.m, "booking.front_desk", self.boss)
        with self.assertRaisesRegex(PermissionError, "not_on_this_side"): self.e.offer(self.m, "pos.rider_phone", self.boss, side="external")
        self.assertEqual(self.e.carry_on(uuid4(), self.phone, self.tv), {"state": "confirmed"})

    def test_a_downgrade_waits_three_days_then_lynkflow_disconnects_the_newest(self):
        self.p.billing.set_plan(self.m, "lynkpos", "plus")
        self.give("pos.merchant_phone", self.phone)
        tab = self.e.add_device(self.m, self.branch, "Till 2", "LynkTab", "android", dict(PHONE, short_side=800), now=T0)
        self.give("pos.counter_tablet", tab, now=T0 + 100)
        self.p.billing.set_plan(self.m, "lynkpos", "free")
        self.assertEqual(self.e.after_downgrade(self.m, "lynkpos", now=T0 + 200), {"to_disconnect": 1, "grace_days": E.DOWNGRADE_GRACE_DAYS})
        self.assertEqual(self.p.flow.tick("daily", [self.m], now=T0 + 86400), [])                 # still in the grace
        ran = self.p.flow.tick("daily", [self.m], now=T0 + 86400 * (E.DOWNGRADE_GRACE_DAYS + 1))
        self.assertEqual((ran[0]["automation"], ran[0]["over_plan"]), ("emulator-daily", 1))
        gone = self.events("EmulatorDisconnected")
        self.assertEqual([(x["payload"]["device_id"], x["payload"]["reason"]) for x in gone], [(tab, "plan")])
        self.assertIn("emulator-daily", [h["automation"] for h in self.p.flow.history(self.m)])

    def test_a_day_pass_adds_a_device_for_the_day_on_any_tier(self):
        self.give("pos.merchant_phone", self.phone)                                            # LynkPOS Free: 1 device
        tab = self.e.add_device(self.m, self.branch, "Till 2", "LynkTab", "android", dict(PHONE, short_side=800), now=T0)
        self.assertEqual(self.give("pos.counter_tablet", tab)[1]["reason"], "plan_limit")
        self.assertEqual(self.e.buy_day_pass(self.m, "lynkpos", self.boss, now=T0), {"devices": 1, "until_day": int(T0 // 86400), "cents": E.day_pass_cents()})
        self.assertEqual(self.give("pos.counter_tablet", tab, now=T0 + 60)[1]["state"], "confirmed")
        with self.assertRaises(ValueError): self.e.buy_day_pass(self.m, "lynkpos", self.boss, days=E.day_pass_max_days() + 1, now=T0)
        self.assertEqual(E.cheaper_tier("lynkpos", "plus", 3), "pro")
        self.assertIsNone(E.cheaper_tier("lynkpos", "plus", 1))

    def test_alerts_and_connect_requests_run_on_lynkflow_and_can_be_switched_off(self):
        self.give("pos.merchant_phone", self.phone)
        self.p.flow.set_off(self.m, "emulator-device-alert")
        b = self.box(self.phone); PanelDevice(b).health(True, 0, printer="out_of_paper"); self.e.ingest(self.m, b.log[-1], now=T0 + 10)
        self.assertNotIn("emulator_device_alert", [l["kind"] for l in self.p.notifier.lines.values()])
        self.p.flow.set_off(self.m, "emulator-device-alert", off=False)
        PanelDevice(b).health(True, 0, printer="paper_low"); self.e.ingest(self.m, b.log[-1], now=T0 + 20)
        self.assertIn("emulator-device-alert", [h["automation"] for h in self.p.flow.history(self.m)])


if __name__ == "__main__":
    unittest.main()
