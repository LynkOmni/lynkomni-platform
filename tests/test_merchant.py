"""Build section 3: the Business app and the whole of LynkPOS (blueprint 42 C, 42 I, 44 C, 44 I N1 N2 N8 N11, 45 E row 3)."""
import json, os, subprocess, sys, time, unittest, uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from contract.tools.validate_contract import validate_event
from dv.box import LocalRejection, LynkDVBox
from merchant.agent import SandboxPartner, AgentPoint
from merchant.business import Business, HANDHELD_TILES, SETUP_STEPS, TABS
from merchant.delivery import SandboxDeliveryPartner
from merchant.devices import SandboxDrivers, web_rule
from services.flow import REGISTER
from services.platform import Platform

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T0 = 1_800_000_000.0
U = lambda: str(uuid.uuid4())


def device(online=False, practice=False, role="owner", merchant=None):
    return LynkDVBox(merchant or U(), U(), U(), U(), role, online=online, practice=practice)


class DeviceCommands(unittest.TestCase):
    def test_every_new_command_writes_a_valid_contract_event_offline(self):
        x = device(); pid = x.create_product("Rice", 1000); x.receive_stock([(pid, 5000)])
        x.open_shift(2000); sid = x.record_sale([(pid, 2000, 0)]); x.record_payment(sid, "cash", 2000)
        cid, diff = x.count_cash(3900, "spot"); self.assertEqual(diff, -100)
        c = x.record_customer_credit(U(), sid, 1000, "2026-12-01"); self.assertEqual(x.record_credit_payment(c, 400), 600)
        x.redeem_voucher(U(), 200); x.hand_over_pickup(U(), "123456")
        e = U(); x.clock_in(e); x.clock_out(e)
        t = x.open_table("T1", 2); o = x.send_to_kitchen(t, [(pid, 1000, "no salt")]); x.mark_kitchen_item_ready(o, 1)
        ids = x.split_table_bill(t, [[(pid, 1000, 0)], [(pid, 1000, 0)]]); x.record_tip(ids[0], 150); x.close_table(t)
        self.assertEqual(x.close_shift(4400), 0)     # 2000 float + 2000 cash + 400 credit payment
        for evt in x.log: self.assertEqual(validate_event(evt), [], evt["type"])
        self.assertEqual(len(x.pending(0)), len(x.log))
    def test_agent_collection_and_delivery_requests_are_online_only_and_never_queued(self):
        x = device(online=False)
        with self.assertRaises(LocalRejection) as r: x.request_agent_service(U(), "bills", 500, 10)
        self.assertEqual(r.exception.reason, "offline_not_possible")
        with self.assertRaises(LocalRejection): x.request_delivery(U(), 300, partner_id=U())
        x.online = True
        self.assertTrue(x.request_agent_service(U(), "bills", 500, 10))
        self.assertEqual(x.log[-1]["type"], "AgentRequestCreated")
    def test_a_practice_device_never_syncs_and_a_cash_count_never_blocks(self):
        x = device(practice=True); pid = x.create_product("Soap", 500); x.open_shift(0)
        sid = x.record_sale([(pid, 1000, 0)]); x.record_payment(sid, "cash", 500)
        self.assertEqual(x.pending(0), []); self.assertEqual(Business.practice_label(True), "PRACTICE")
        self.assertEqual(x.count_cash(0, "day_end")[1], -500)      # a difference is a fact, not a block
    def test_table_rules(self):
        x = device(); pid = x.create_product("Tea", 300)
        t = x.open_table("A"); o = x.send_to_kitchen(t, [(pid, 1000, None)])
        with self.assertRaises(LocalRejection): x.close_table(t)              # kitchen items still open
        x.mark_kitchen_item_ready(o, 1)
        with self.assertRaises(LocalRejection): x.split_table_bill(t, [[(pid, 1000, 0)]])   # one bill is an ordinary sale
        x.close_table(t)
        with self.assertRaises(LocalRejection): x.record_tip(U(), 10)


class CloudSide(unittest.TestCase):
    def setUp(self):
        os.environ.pop("LYNK_MODE", None); self.p = Platform(); self.m = U(); self.partner = U()
        self.gw = SandboxPartner(self.partner, float_minor=100_000)
        self.p.agent.add_partner(self.partner, self.gw); self.p.agent.approve_agent(self.m, self.partner)
        self.x = LynkDVBox(self.m, U(), U(), U(), "owner", online=True)
    def ask(self, service="bills", amount=5_000, fee=50, ref="cust-1"):
        rid = self.x.request_agent_service(self.partner, service, amount, fee, ref)
        return rid, self.p.agent.handle_request(self.m, self.x.log[-1], now=T0)
    def test_agent_request_confirmed_by_the_partner_then_cash_may_change_hands(self):
        rid, state = self.ask()
        self.assertEqual(state, "confirmed"); self.assertTrue(AgentPoint.may_hand_over_cash(state))
        types = [e["type"] for e in self.p.c.store.of(self.m, "AgentRequestConfirmed", "CommissionRecorded")]
        self.assertEqual(types, ["AgentRequestConfirmed", "CommissionRecorded"])
        self.assertEqual(self.p.agent.state(rid)["state"], "confirmed"); self.assertEqual(self.gw.float, 95_000)
        self.assertEqual(self.p.agent.commissions(self.m)[0]["commission"], 50)
    def test_every_failure_reason_is_a_cloud_event_and_cash_never_moves_on_sent(self):
        self.assertFalse(AgentPoint.may_hand_over_cash("sent"))
        self.gw.fail_next = "partner_declined"; self.assertEqual(self.ask()[1], "failed")
        self.assertEqual(self.ask(amount=10**9)[1], "failed")                      # limit_exceeded
        self.gw.rejects_identity.add("bad"); self.assertEqual(self.ask(ref="bad")[1], "failed")   # identity_check_failed
        self.assertEqual(self.ask(amount=99_000)[1], "confirmed"); self.assertEqual(self.ask(amount=5_000)[1], "failed")   # insufficient_float
        reasons = [e["payload"]["reason_code"] for e in self.p.c.store.of(self.m, "AgentRequestFailed")]
        self.assertEqual(reasons, ["partner_declined", "limit_exceeded", "identity_check_failed", "insufficient_float"])
    def test_only_approved_agents_and_the_tier_caps_partners(self):
        other = U(); self.p.agent.add_partner(other, SandboxPartner(other))
        rid = self.x.request_agent_service(other, "bills", 100, 1)
        self.assertEqual(self.p.agent.handle_request(self.m, self.x.log[-1], now=T0), "failed")   # not approved
        with self.assertRaises(PermissionError): self.p.agent.approve_agent(self.m, other)       # Free: 1 partner
        self.p.billing.set_plan(self.m, "lynkpos", "plus"); self.p.agent.approve_agent(self.m, other)
    def test_float_is_read_from_the_partner_and_low_float_warns(self):
        for _ in range(3): self.ask(amount=20_000)
        bal = self.p.agent.read_float(self.m, self.partner, now=T0)
        self.assertEqual(bal, 40_000); self.assertEqual(self.p.c.store.of(self.m, "FloatBalanceRead")[-1]["payload"]["balance"], 40_000)
        self.assertFalse(self.p.agent.low_float(self.m, self.partner))
        self.gw.float = 5_000; self.assertTrue(self.p.agent.low_float(self.m, self.partner))
        self.assertIsNotNone(self.p.agent.float_forecast(self.m, self.partner))
        self.assertIn(self.partner, self.p.agent.home(self.m, "2027-01-15")["low_float"])
    def test_statement_match_flags_each_mismatch(self):
        rid1, _ = self.ask(); rid2, _ = self.ask()
        rows = self.gw.statement("2027-01"); rows[0]["commission"] += 7; rows.pop()    # one wrong, one missing
        r = self.p.agent.match_statement(self.m, self.partner, "2027-01", rows=rows, now=T0)
        self.assertEqual(r["matched"], 0); self.assertEqual(len(r["mismatches"]), 2)
        self.assertEqual(len(self.p.c.store.of(self.m, "CommissionMismatchFlagged")), 2)
        self.assertEqual(self.p.c.store.of(self.m, "PartnerStatementMatched")[-1]["payload"]["matched_count"], 0)
    def test_cash_difference_is_flagged_never_blocked(self):
        self.x.open_shift(1000); self.x.count_cash(900, "handover")
        self.assertEqual(self.p.agent.handle_cash_count(self.m, self.x.log[-1], now=T0), -100)
        self.assertEqual(self.p.c.store.of(self.m, "CashDifferenceFlagged")[-1]["payload"]["difference"], -100)
        self.assertEqual(len(self.p.agent.cash_differences(self.m)), 1)
    def test_collection_and_partner_finance_are_recorded_and_lynkomni_holds_nothing(self):
        self.p.agent.record_collection(self.m, self.partner, "loan_repayment", 3000, "XXX" if False else self.x.currency, now=T0)
        self.p.agent.refer(self.m, self.partner, "savings", 500, self.x.currency, now=T0)
        self.assertEqual(self.p.c.store.of(self.m, "CollectionRecorded")[-1]["payload"]["kind"], "loan_repayment")
        self.assertEqual(self.p.c.store.of(self.m, "PartnerReferralRecorded")[-1]["payload"]["product"], "savings")
        with self.assertRaises(ValueError): self.p.agent.refer(self.m, self.partner, "wallet", 1, self.x.currency)


class DeliveriesTablesGroups(unittest.TestCase):
    def setUp(self):
        os.environ.pop("LYNK_MODE", None); self.p = Platform(); self.m = U()
        self.x = LynkDVBox(self.m, U(), U(), U(), "owner", online=True)
    def test_partner_delivery_quotes_booking_steps_and_tracking(self):
        a, b = U(), U(); self.p.deliveries.add_partner(a, SandboxDeliveryPartner(a, price=2000, eta_s=1800)); self.p.deliveries.add_partner(b, SandboxDeliveryPartner(b, price=1500, eta_s=3600))
        self.assertEqual(len(self.p.deliveries.quotes(self.m, {})), 1)                  # Free: one partner, no routing
        self.p.billing.set_plan(self.m, "lynkpos", "pro")
        self.assertEqual(self.p.deliveries.quotes(self.m, {})[0]["partner_id"], b)     # cheapest
        self.assertEqual(self.p.deliveries.quotes(self.m, {}, "fastest")[0]["partner_id"], a)
        did = self.x.request_delivery(U(), 1500, partner_id=b)
        r = self.p.deliveries.handle_request(self.m, self.x.log[-1], now=T0)
        self.assertEqual(r["state"], "accepted"); self.assertTrue(self.p.deliveries.code_matches(did, r["code"])); self.assertFalse(self.p.deliveries.code_matches(did, "000000"))
        self.p.deliveries.partner_step(self.m, did, "picked_up", T0); self.p.deliveries.partner_step(self.m, did, "delivered", T0)
        tr = self.p.deliveries.track(did)
        self.assertEqual((tr["state"], tr["step"], tr["ended"]), ("confirmed", "delivered", True))
        self.assertEqual([s["id"] for s in tr["steps"]], ["requested", "assigned", "on_the_way", "delivered"])
        self.assertEqual([e["type"] for e in self.p.c.store.of(self.m, "DeliveryAccepted", "DeliveryPickedUp", "DeliveryDelivered")], ["DeliveryAccepted", "DeliveryPickedUp", "DeliveryDelivered"])
    def test_own_riders_follow_the_tier_and_record_steps_offline(self):
        with self.assertRaises(PermissionError): self.p.deliveries.add_rider(self.m, "rider-1")    # Free: 0 riders
        self.p.billing.set_plan(self.m, "lynkpos", "plus"); self.p.deliveries.add_rider(self.m, "rider-1")
        did = self.x.request_delivery(U(), 0)
        self.assertEqual(self.p.deliveries.handle_request(self.m, self.x.log[-1], now=T0)["state"], "accepted")
        rider = LynkDVBox(self.m, U(), U(), U(), "cashier"); rider.record_delivery_step(did, "picked_up"); rider.record_delivery_step(did, "delivered", "code")
        for e in rider.log[-2:]: self.assertEqual(validate_event(e), []); self.p.deliveries.note_device_step(self.m, e)
        self.assertEqual(self.p.deliveries.track(did)["step"], "delivered")
    def test_partner_delivery_monthly_limit_on_free(self):
        a = U(); self.p.deliveries.add_partner(a, SandboxDeliveryPartner(a))
        for i in range(21):
            self.x.request_delivery(U(), 1500, partner_id=a); r = self.p.deliveries.handle_request(self.m, self.x.log[-1], now=T0)
        self.assertEqual(r["state"], "failed"); self.assertEqual(r["reason"], "limit_exceeded")
    def test_restaurant_limits_and_kitchen_queue(self):
        r = self.p.restaurant
        self.assertEqual(r.limits(self.m)["tables"], 5); self.assertEqual(r.kitchen_output(self.m), "printed_tickets"); self.assertFalse(r.limits(self.m)["tips"])
        self.assertTrue(r.may_open_table(self.m, 4)); self.assertFalse(r.may_open_table(self.m, 5))
        self.p.billing.set_plan(self.m, "lynkpos", "pro"); self.assertEqual(r.kitchen_output(self.m), "screen"); self.assertTrue(r.limits(self.m)["table_qr_ordering"])
        pid = self.x.create_product("Soup", 900); t = self.x.open_table("T4", 3); o = self.x.send_to_kitchen(t, [(pid, 2000, None)])
        for e in self.x.log: self.p.cloud.device_event(self.m, e)
        self.assertEqual(r.kitchen_queue(self.m), [{"table": "T4", "order_id": o, "line_no": 1}])
        self.assertEqual(r.tip_share_for_lynkomni(1000), 0)
    def test_buy_together_never_pools_and_nobody_pays_when_short(self):
        bt, sup = self.p.buy_together, U()
        with self.assertRaises(PermissionError): bt.open(self.m, sup, 10_000, "USD", T0 + 86400)     # Free cannot start a group
        self.p.billing.set_plan(self.m, "lynkpos", "pro")
        g = bt.open(self.m, sup, 10_000, "USD", T0 + 86400, now=T0)
        o1 = bt.join(U(), g, 4_000, now=T0); o2 = bt.join(U(), g, 3_000, now=T0)
        self.assertEqual(bt.close(g, now=T0 + 86400), "failed"); self.assertFalse(bt.charged(o1))
        g2 = bt.open(self.m, sup, 5_000, "USD", T0 + 86400, now=T0); o3 = bt.join(U(), g2, 5_000, now=T0)
        self.assertEqual(bt.close(g2, now=T0 + 86400), "reached"); self.assertTrue(bt.charged(o3)); self.assertEqual(bt.pooled_by_lynkomni(), 0)
        with self.assertRaises(ValueError): bt.join(U(), g2, 1, now=T0)


class DevicesAndBusiness(unittest.TestCase):
    def setUp(self):
        os.environ.pop("LYNK_MODE", None); self.p = Platform(); self.m = U()
    def test_the_web_rule(self):
        for a in ("sell", "cash_drawer", "shift", "cash_count", "agent_service"): self.assertEqual(web_rule(a, False), "registered_device"); self.assertEqual(web_rule(a, True), "ok")
        self.assertEqual(web_rule("settings_change", False), "step_up"); self.assertEqual(web_rule("accounting", False), "ok")
    def test_registered_devices_follow_the_tier_and_report_health(self):
        d, key = self.p.devices, "A" * 87
        d.enrol(self.m, U(), "Till 1", "phone", "android", U(), key, now=T0)
        with self.assertRaises(PermissionError): d.enrol(self.m, U(), "Till 2", "tablet", "android", U(), key, now=T0)   # Free: 1 device
        self.p.billing.set_plan(self.m, "lynkpos", "plus"); dev2 = U(); d.enrol(self.m, dev2, "Till 2", "handheld", "android", U(), key, now=T0)
        self.assertEqual(d.may(self.m, dev2, "sell"), "ok"); d.revoke(self.m, dev2, U(), "staff_left", now=T0); self.assertEqual(d.may(self.m, dev2, "sell"), "registered_device")
        d.heartbeat(self.m, d.list(self.m)[0]["device_id"], "1.0", 9, 100, now=T0)
        self.assertEqual(d.health(self.m, "1.1", now=T0)[0]["issues"], ["old_app", "low_battery", "low_storage"])
        self.assertEqual([e["type"] for e in self.p.c.store.of(self.m, "DeviceEnrolled", "DeviceRevoked")], ["DeviceEnrolled", "DeviceEnrolled", "DeviceRevoked"])
    def test_sandbox_drivers_behind_one_interface(self):
        drv = SandboxDrivers(); drv.print(["a", "b"]); drv.open_drawer(); drv.show(["Total 5"]); r = drv.card_tap(500, "USD")
        self.assertEqual((len(drv.printed), drv.drawer_opens, len(drv.shown)), (1, 1, 1)); self.assertTrue(r["sent"]); self.assertNotIn("confirmed", r)
        phone = SandboxDrivers(parts=())
        with self.assertRaises(RuntimeError): phone.print([])          # a phone alone has no printer; selling still works
    def test_tabs_by_business_type_setup_and_username(self):
        b = self.p.business; b.create(self.m, "Mama's Kitchen", "shop", "XX", "USD", now=T0)
        self.assertEqual(b.tabs(self.m), ("home", "sell", "stock", "chats", "business"))
        for t, tabs in TABS.items(): self.assertEqual(len(tabs), 5); self.assertEqual(tabs[0], "home"); self.assertEqual(tabs[-2:], ("chats", "business"))
        self.assertEqual(len(HANDHELD_TILES), 12)
        for st in SETUP_STEPS: left = b.complete_setup_step(self.m, st)
        self.assertEqual(left, []); self.assertTrue(b.ready_to_sell(self.m))
        self.assertEqual(b.take_username(self.m, "Mamas.Kitchen", now=T0), "mamas.kitchen"); self.assertEqual(b.shop_page(self.m), "shop.lynkomni.com/mamas.kitchen")
        with self.assertRaises(ValueError): b.take_username(U(), "admin")
        self.assertEqual(self.p.c.store.of(self.m, "BusinessCreated")[0]["payload"]["business_type"], "shop")
    def test_second_currency_is_a_labelled_estimate_and_receipts_follow_the_tier(self):
        b = self.p.business
        self.assertIsNone(b.second_currency(1000, "USD", "USD"))
        s = b.second_currency(1000, "USD", "EUR"); self.assertTrue(s["estimate"]); self.assertEqual(s["sale_currency"], "USD")
        self.assertEqual(b.receipt_channels(self.m), ("print", "qr")); self.p.billing.set_plan(self.m, "lynkpos", "plus"); self.assertIn("message", b.receipt_channels(self.m))
        self.assertFalse(b.may_show_confirmed("pending_confirmation")); self.assertTrue(b.may_show_confirmed("confirmed"))
    def test_sell_by_voice_fills_the_basket_for_the_cashier_to_confirm(self):
        prods = [{"id": "p1", "name": "Rice"}, {"id": "p2", "name": "Soap"}]
        self.assertEqual(Business.parse_voice("two bags of rice, one soap", prods), [("p1", 2000), ("p2", 1000)])
        self.assertEqual(Business.parse_voice("3 soap and rice", prods), [("p2", 3000), ("p1", 1000)])
    def test_day_close_counts_only_confirmed_money_as_received(self):
        x = LynkDVBox(self.m, U(), U(), U(), "owner"); pid = x.create_product("Rice", 1000)
        s1 = x.record_sale([(pid, 1000, 0)]); x.record_payment(s1, "cash", 1000)
        s2 = x.record_sale([(pid, 2000, 0)]); x.record_payment(s2, "mobile_money", 2000)
        for e in x.log: self.p.cloud.device_event(self.m, e)
        day = time.strftime("%Y-%m-%d", time.gmtime())
        d = self.p.business.day_close(self.m, day)
        self.assertEqual((d["sales"], d["cash_expected"], d["waiting"], d["confirmed"]), (2, 1000, 2000, 0))
    def test_services_are_off_until_a_partner_is_signed_but_pos_never_waits(self):
        import providers
        for sv in ("agent", "collection", "delivery"): self.assertEqual(providers.availability(sv, "XX")["state"], "coming_soon")
        self.assertEqual(providers.availability("pos", "XX")["state"], "available")


class Automations(unittest.TestCase):
    def setUp(self):
        os.environ.pop("LYNK_MODE", None); self.p = Platform(); self.m = U(); self.f = self.p.flow
        self.p.business.create(self.m, "Shop", "shop", "XX", "USD", now=T0)
    def ran(self, aid): return [h for h in self.f.history(self.m) if h["automation"] == aid]
    def test_all_twenty_two_are_registered_with_the_levels_of_the_register(self):
        ids = [a["id"] for a in REGISTER.values() if a["build_section"] == 3]
        self.assertEqual(len(ids), 23)                     # twenty, plus order-updates, tracking-late-watch and driver-update-reminder (9 November 2026)
        for aid in ids: self.assertIn(aid, self.f.handlers); self.assertTrue(REGISTER[aid].get("implemented_by", "").startswith("merchant/automations.py"))
        self.assertEqual(REGISTER["negative-stock-flag"]["trigger"], "event:NegativeStockFlagged")      # a contract event, not an invented one
    def test_driver_update_reminder_tells_once_with_the_deadline(self):
        self.p.cloud.signal(self.m, "DriverUpdateAvailable", {"version": "1.2.0", "level": "required", "devices": [U()]}, now=T0)
        self.p.cloud.signal(self.m, "DriverUpdateAvailable", {"version": "1.2.0", "level": "required", "devices": [U()]}, now=T0 + 60)
        runs = [r for r in self.ran("driver-update-reminder") if r.get("result")]
        alerts = [e for e in self.p.c.store.of(self.m, "AlertSent") if e["payload"]["kind"] == "driver_update"]
        self.assertEqual(len(alerts), 1); self.assertEqual(alerts[0]["payload"]["detail"]["due_at"], T0 + 3 * 86400)
    def test_drafts_and_alerts_from_events(self):
        self.assertEqual(len(self.ran("setup-autofill")), 1)                                  # BusinessCreated in setUp
        self.p.cloud.signal(self.m, "StockBelowThreshold", {"product_id": U(), "level_milli": 1000, "reorder_at_milli": 2000}, now=T0)
        self.assertEqual(len(self.ran("low-stock-reorder")), 1)
        self.p.cloud.event(self.m, "NegativeStockFlagged", {"product_id": "01900000-0000-7000-8000-000000000001", "projected_milli": -1000, "as_of_cursor": 1}, now=T0)
        self.assertEqual(self.ran("negative-stock-flag")[0]["level"], "inform")
        x = LynkDVBox(self.m, U(), U(), U(), "owner"); x.open_shift(1000); x.count_cash(900)
        self.p.cloud.device_event(self.m, x.log[-1], now=T0); self.assertEqual(self.ran("cash-difference-flag")[0]["did"]["difference"], -100)
        pid = x.create_product("Tea", 100); sid = x.record_sale([(pid, 1000, 0)]); self.p.cloud.device_event(self.m, x.log[-2], now=T0)
        self.assertEqual(self.ran("receipt-delivery")[0]["did"]["channel"], "qr")                 # Free: print and QR only
        t = x.open_table("T1"); x.send_to_kitchen(t, [(pid, 1000, None)]); self.p.cloud.device_event(self.m, x.log[-1], now=T0)
        self.assertEqual(self.ran("kitchen-routing")[0]["did"]["station"], "printed_tickets")
        self.p.cloud.signal(self.m, "MessageReceived", {"thread_id": "th1", "message_id": "m1", "lang": "fr"}, now=T0)
        self.assertEqual(len(self.ran("chat-suggested-replies")), 1); self.assertEqual(self.ran("chat-routing")[0]["did"]["to"], "orders")
        self.p.cloud.signal(self.m, "DeviceIdle", {"device_id": "d1", "idle_s": 30}, now=T0, by="d1"); self.assertEqual(self.ran("staff-pin-lock"), [])
        self.p.cloud.signal(self.m, "DeviceIdle", {"device_id": "d1", "idle_s": 200}, now=T0, by="d1"); self.assertEqual(len(self.ran("staff-pin-lock")), 1)
        self.p.cloud.signal(self.m, "ConnectionRestored", {"device_id": "d1", "pending": {"media": 2, "sales": 3}}, now=T0, by="d1")
        self.assertEqual(self.ran("sync-retry")[0]["did"]["sent"], ["sales", "media"])
    def test_schedules_and_user_asks(self):
        self.f.tick("closing_time", [self.m], now=T0); self.assertEqual(self.ran("day-close-prepare")[0]["did"]["summary"], "day_close")
        self.f.tick("closing_time", [self.m], now=T0 + 60); self.assertEqual(len(self.ran("day-close-prepare")), 1)      # once a day
        self.f.user_action(self.m, "summarise", {"thread_id": "th1"}, now=T0); self.assertEqual(len(self.ran("chat-summary")), 1)
        self.f.user_action(self.m, "photo", {"photo_ref": "ph1"}, now=T0); self.assertEqual(self.ran("product-from-photo")[0]["level"], "draft")
        self.p.devices.enrol(self.m, U(), "Till", "phone", "android", U(), "A" * 87, now=T0); self.p.devices.heartbeat(self.m, self.p.devices.list(self.m)[0]["device_id"], "0.9", 50, 1000, now=T0)
        self.f.tick("daily", [self.m], now=T0); self.assertEqual(self.ran("device-health")[0]["did"]["devices"], 1)
    def test_agent_and_delivery_automations(self):
        partner = U(); gw = SandboxPartner(partner, float_minor=50_000); self.p.agent.add_partner(partner, gw); self.p.agent.approve_agent(self.m, partner)
        x = LynkDVBox(self.m, U(), U(), U(), "owner", online=True)
        for _ in range(3): x.request_agent_service(partner, "bills", 10_000, 100); self.p.agent.handle_request(self.m, x.log[-1], now=T0)
        gw.float = 1_000; self.p.agent.read_float(self.m, partner, now=T0)
        self.assertEqual(self.ran("low-float-warning")[0]["did"]["alert"], "low_float")
        self.p.cloud.signal(self.m, "PartnerStatementReceived", {"partner_id": partner, "period": "2027-01", "rows": gw.statement("2027-01")}, now=T0)
        self.assertEqual(self.ran("commission-match")[0]["did"]["mismatches"], 0)
        a = U(); self.p.deliveries.add_partner(a, SandboxDeliveryPartner(a))
        self.p.cloud.signal(self.m, "OrderReadyForDelivery", {"order_id": U(), "lynkoid": self.m}, now=T0)
        self.assertEqual(self.ran("delivery-auto-request")[0]["level"], "auto_undo")
    def test_off_switch_and_history_why(self):
        self.f.set_off(self.m, "chat-routing")
        self.p.cloud.signal(self.m, "MessageReceived", {"thread_id": "t", "message_id": "m", "lang": "en"}, now=T0)
        self.assertEqual(self.ran("chat-routing"), []); self.assertTrue(all(h["why"] for h in self.f.history(self.m)))
    def test_shared_vectors_are_current(self):
        self.assertEqual(subprocess.run([sys.executable, os.path.join(ROOT, "tools", "pos_vectors.py"), "--check"], capture_output=True, text=True).returncode, 0, "run python3 tools/pos_vectors.py")


if __name__ == "__main__":
    unittest.main()
