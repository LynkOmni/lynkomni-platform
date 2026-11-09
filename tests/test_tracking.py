"""LynkOmni tracking (owner request 9 November 2026): the register (catalog/tracking.v1.json), the engine (services/tracking.py),
its place in the platform (the event store feeds it; LynkFlow tells customers and owners) and the privacy rules."""
import json, os, re, unittest, uuid

from contract.tools.validate_contract import uuid7
from core import ids
from services import tracking as T

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REG = T.register()
CONTRACT = json.load(open(os.path.join(ROOT, "contract", "event-payloads.v2.json"), encoding="utf-8"))["events"]
IDENTITY = json.load(open(os.path.join(ROOT, "identity", "events.v1.json"), encoding="utf-8"))["events"]
ADDR = json.load(open(os.path.join(ROOT, "catalog", "addresses.v1.json"), encoding="utf-8"))
T0 = 1_794_200_000          # 2026-11-09


def fields_of(event):
    if event in CONTRACT: return set(CONTRACT[event]["payload"]["properties"])
    if event in IDENTITY: return set(IDENTITY[event]["payload"])
    raise KeyError(event)


def address_ok(where):
    host, _, path = where.partition("/")
    pools = {"app.lynkomni.com": ADDR["app_paths"], "account.lynkomni.com": ADDR["account_paths"], "shop.lynkomni.com": ADDR["shop_paths"], "pay.lynkomni.com": ADDR["pay_paths"]}
    return "/" + path in pools.get(host, [])


class Register(unittest.TestCase):
    def test_every_kind_is_complete_and_uses_only_the_five_states(self):
        self.assertEqual(tuple(REG["states"]), T.STATES)
        seen = set()
        for k in REG["kinds"]:
            self.assertNotIn(k["id"], seen); seen.add(k["id"])
            self.assertRegex(k["id"], r"^[a-z_]+$")
            if k["record"]: self.assertIn(k["record"], ids.TYPES, k["id"])            # public ids only from core/ids.py
            self.assertTrue(any(s.get("terminal") for s in k["steps"]), k["id"])
            for s in k["steps"]:
                self.assertIn(s["state"], T.STATES, f"{k['id']}.{s['id']}")
                self.assertIn("customer", s, f"{k['id']}.{s['id']}")

    def test_every_event_a_step_waits_for_exists_and_carries_the_record_key(self):
        for k in REG["kinds"]:
            aliases = {a["event"]: a for a in k.get("aliases", [])}
            alias_fields = {a["from"] for a in k.get("aliases", [])}
            for s in k["steps"]:
                for rule in s["on"]:
                    if "event" not in rule: continue
                    f = fields_of(rule["event"])                                       # a contract or identity event, never an invented one
                    self.assertTrue(k["key"] in f or f & alias_fields, f"{k['id']}: {rule['event']} has no {k['key']}")
                    for field in rule.get("when", {}): self.assertIn(field, f, rule["event"])
            for e in aliases: fields_of(e)
            for e in k.get("eta", []): self.assertIn(e["field"], fields_of(e["event"]))

    def test_children_and_parents_point_at_real_steps(self):
        kinds = {k["id"]: k for k in REG["kinds"]}
        for k in REG["kinds"]:
            if "parent" in k:
                self.assertIn(k["parent"]["kind"], kinds); self.assertIn(k["parent"]["field"], fields_of(k["parent"]["event"]))
            for s in k["steps"]:
                for rule in s["on"]:
                    if "child" in rule:
                        self.assertIn(rule["step"], [x["id"] for x in kinds[rule["child"]]["steps"]])
                        self.assertEqual(kinds[rule["child"]]["parent"]["kind"], k["id"])

    def test_every_viewer_address_is_in_the_address_map(self):
        for k in REG["kinds"]:
            for who, where in k["viewers"].items():
                self.assertIn(who, T.AUDIENCES)
                if ".lynkomni.com/" in where: self.assertTrue(address_ok(where), f"{k['id']}: {where}")

    def test_every_step_word_and_kind_name_is_in_the_tracker_words(self):
        # the tracker's own word pack (web/tracking) travels only with the tracker, so devices that show none stay small
        en = json.load(open(os.path.join(ROOT, "web", "tracking", "strings.en.json"), encoding="utf-8"))
        for k in REG["kinds"] + REG["planned"]:
            self.assertIn(f"trk_k_{k['id']}", en)
        for k in REG["kinds"]:
            for s in k["steps"]: self.assertIn(f"trk_{s['id']}", en, s["id"])

    def test_planned_kinds_name_their_build_section(self):
        for k in REG["planned"]:
            self.assertIn(k["record"], ids.TYPES); self.assertGreater(k["ui_section"], 3)


def ev(t, at=T0, **p): return {"type": t, "payload": p, "at": at}


class Engine(unittest.TestCase):
    def setUp(self): self.t = T.Tracking()

    def test_a_delivery_moves_only_on_the_events_that_prove_each_step(self):
        d, o = uuid7(), uuid7()
        self.t.apply(ev("DeliveryRequested", delivery_id=d, order_id=o, own_rider=False, price=1500, currency="USD"), "m")
        v = self.t.view("delivery", d, "customer", now=T0)
        self.assertEqual((v["state"], v["step"]), ("sent", "requested"))
        self.assertEqual([s["id"] for s in v["steps"]], ["requested", "assigned", "on_the_way", "delivered"])   # failure is never shown in advance
        self.t.apply(ev("DeliveryAccepted", T0 + 10, delivery_id=d, partner_reference="SBXD-1", eta="2026-11-09T05:00:00Z"), "m")
        self.assertEqual(self.t.state("delivery", d), "accepted")
        self.t.apply(ev("DeliveryFailed", T0 + 20, delivery_id=d, reason_code="timeout"), "m")
        v = self.t.view("delivery", d, "customer", now=T0 + 30)
        self.assertEqual((v["state"], v["step"], v["ended"]), ("failed", "failed", True))
        self.assertEqual([s["id"] for s in v["steps"]], ["requested", "assigned", "failed"])
        self.t.apply(ev("DeliveryDelivered", T0 + 40, delivery_id=d, proof="code"), "m")       # nothing moves after an ending
        self.assertEqual(self.t.state("delivery", d), "failed")

    def test_the_customer_never_sees_ids_addresses_or_positions(self):
        d, o = uuid7(), uuid7()
        for e in (ev("DeliveryRequested", delivery_id=d, order_id=o, own_rider=True, price=0, currency="USD"), ev("DeliveryAccepted", delivery_id=d, partner_reference="own-rider"), ev("DeliveryPickedUp", delivery_id=d)):
            self.t.apply(e, "m")
        self.assertTrue(self.t.set_progress("delivery", d, 0.43, "2026-11-09T05:10:00Z"))
        v = self.t.view("delivery", d, "customer", now=T0)
        self.assertEqual(v["progress"], 0.45)                                      # whole steps of 5%, never a position
        blob = json.dumps(v)
        for banned in (d, o, "own-rider"): self.assertNotIn(banned, blob)
        def keys(x): return set(x) | set().union(*(keys(v) for v in x.values() if isinstance(v, dict))) | set().union(*(keys(i) for v in x.values() if isinstance(v, list) for i in v if isinstance(i, dict)))
        self.assertFalse(keys(v) & {"lat", "lon", "latitude", "longitude", "position", "address", "phone", "name", "rider"})
        self.assertNotIn("record", v)
        m = self.t.view("delivery", d, "merchant", now=T0)
        self.assertEqual(m["record"], d); self.assertEqual(m["parent"], {"kind": "order", "record": o})

    def test_progress_is_only_for_a_trip_on_its_way_and_ends_with_it(self):
        d = uuid7()
        self.t.apply(ev("DeliveryRequested", delivery_id=d, order_id=uuid7(), own_rider=True, price=0, currency="USD"), "m")
        self.assertFalse(self.t.set_progress("delivery", d, 0.5))                  # not picked up yet
        self.t.apply(ev("DeliveryPickedUp", delivery_id=d), "m")
        self.assertTrue(self.t.set_progress("delivery", d, 0.5))
        self.t.apply(ev("DeliveryDelivered", delivery_id=d, proof="photo"), "m")
        self.assertIsNone(self.t.view("delivery", d, "merchant", now=T0)["progress"])
        self.assertFalse(self.t.set_progress("delivery", d, 0.9))
        self.assertFalse(T.Tracking().set_progress("delivery", "unknown", 0.1))

    def test_an_order_is_ready_only_when_every_line_is_ready_and_ends_with_its_delivery(self):
        o, d = uuid7(), uuid7()
        self.t.apply(ev("OrderSentToKitchen", order_id=o, table_id=uuid7(), lines=[{"x": 1}, {"x": 2}, {"x": 3}]), "m")
        self.t.apply(ev("KitchenItemReady", order_id=o, line_no=0), "m"); self.t.apply(ev("KitchenItemReady", order_id=o, line_no=0), "m")
        self.assertEqual(self.t.view("order", o, now=T0)["step"], "preparing")   # the same line twice is still one line
        self.t.apply(ev("KitchenItemReady", order_id=o, line_no=1), "m"); self.t.apply(ev("KitchenItemReady", order_id=o, line_no=2), "m")
        self.assertEqual(self.t.view("order", o, now=T0)["step"], "ready")
        self.assertEqual(self.t.view("order", o, now=T0)["steps"][-1]["id"], "collected")       # no delivery: collected is expected
        self.t.apply(ev("DeliveryRequested", delivery_id=d, order_id=o, own_rider=True, price=0, currency="USD"), "m")
        self.assertEqual([s["id"] for s in self.t.view("order", o, now=T0)["steps"]][-2:], ["out_for_delivery", "delivered"])
        self.t.apply(ev("DeliveryPickedUp", delivery_id=d), "m")
        self.assertEqual(self.t.view("order", o, now=T0)["step"], "out_for_delivery")
        self.t.apply(ev("DeliveryDelivered", delivery_id=d, proof="code"), "m")
        v = self.t.view("order", o, "customer", now=T0)
        self.assertEqual((v["state"], v["step"]), ("confirmed", "delivered"))
        self.assertEqual(v["children"][0]["step"], "delivered")

    def test_a_payment_is_confirmed_only_by_its_provider(self):
        p = uuid7()
        self.t.apply(ev("PaymentRecorded", payment_id=p, sale_id=uuid7(), method="mobile_money", amount=500, status="pending_confirmation", currency="USD"), "m")
        self.assertEqual(self.t.view("payment", p, now=T0)["step"], "waiting_provider")
        self.t.apply(ev("PaymentStatusChanged", payment_id=p, from_status="pending_confirmation", to_status="confirmed", source="provider_callback"), "m")
        self.assertEqual(self.t.state("payment", p), "confirmed")
        q = uuid7()
        self.t.apply(ev("PaymentRecorded", payment_id=q, sale_id=uuid7(), method="cash", amount=500, status="cash_received", currency="USD"), "m")
        self.assertEqual([s["id"] for s in self.t.view("payment", q, now=T0)["steps"]], ["confirmed"])

    def test_aliases_follow_a_record_whose_id_changes(self):
        r, o = uuid7(), uuid7()
        self.t.apply(ev("FinancingRequested", request_id=r, invoice_id=uuid7(), consent_id=uuid7()), "m")
        self.t.apply(ev("FinancingOffered", offer_id=o, request_id=r, lender_id=uuid7(), amount=1, total_cost=1, currency="USD"), "m")
        self.t.apply(ev("FinancingAccepted", offer_id=o), "m"); self.t.apply(ev("FinancingPaidOut", offer_id=o, provider_reference="x"), "m")
        self.assertEqual(self.t.view("financing", r, now=T0)["step"], "paid_out")

    def test_services_with_their_own_state_feed_it(self):
        i = uuid7()
        self.t.feed_state("invoice", i, "issued", T0, "m"); self.t.feed_state("invoice", i, "partially_paid", T0 + 1)
        self.assertEqual(self.t.view("invoice", i, now=T0)["step"], "partly_paid")
        self.assertEqual([s["id"] for s in self.t.view("invoice", i, "customer", now=T0)["steps"]], ["issued", "partly_paid", "paid"])
        with self.assertRaises(ValueError): self.t.feed_state("nothing", i, "issued", T0)

    def test_late_and_active_lists(self):
        d = uuid7()
        self.t.apply(ev("DeliveryRequested", delivery_id=d, order_id=uuid7(), own_rider=False, price=1, currency="USD"), "m1")
        self.t.apply(ev("DeliveryAccepted", delivery_id=d, partner_reference="r", eta="2026-11-09T01:00:00Z"), "m1")
        eta = T.epoch("2026-11-09T01:00:00Z")
        self.assertFalse(self.t.view("delivery", d, now=eta - 1)["late"])
        self.assertEqual([v["record"] for v in self.t.late(eta + 1, "m1")], [d])
        self.assertEqual(self.t.late(eta + 1, "m2"), [])
        self.assertEqual(len(self.t.active("m1")), 1)


class OnThePlatform(unittest.TestCase):
    def setUp(self):
        os.environ.pop("LYNK_MODE", None)
        from services.platform import Platform
        self.p = Platform(); self.m = str(uuid.uuid4())
        self.p.business.create(self.m, "Shop", "shop", "XX", "USD", now=T0)

    def deliver(self):
        from merchant.delivery import SandboxDeliveryPartner
        a = str(uuid.uuid4()); self.p.deliveries.add_partner(a, SandboxDeliveryPartner(a, eta_s=600))
        d, o = uuid7(), uuid7()
        evt = {"event_id": uuid7(), "type": "DeliveryRequested", "payload": {"delivery_id": d, "order_id": o, "partner_id": a, "own_rider": False, "price": 1500, "currency": "USD"}}
        return d, o, evt

    def test_the_log_feeds_tracking_and_every_step_is_a_signal(self):
        d, o, evt = self.deliver()
        self.p.deliveries.handle_request(self.m, evt, now=T0)
        steps = [e["payload"]["step"] for e in self.p.c.store.of(self.m, "TrackingStepReached")]
        self.assertEqual(steps, ["requested", "assigned"])
        self.p.deliveries.partner_step(self.m, d, "picked_up", T0 + 60)
        self.assertEqual(self.p.deliveries.track(d)["step"], "on_the_way")
        self.assertEqual(self.p.tracking.view("order", o)["step"], "out_for_delivery")

    def test_customer_messages_go_only_to_a_customer_who_chose_a_way_and_wait_for_quiet_hours(self):
        d, o, evt = self.deliver()
        self.p.deliveries.handle_request(self.m, evt, now=T0)
        self.assertEqual(self.p.c.store.of(self.m, "TrackingUpdateSent"), [])          # nobody asked yet
        self.p.tracking.subscribe(self.m, "delivery", d, "sms", "fr", now=T0)
        night = T.epoch("2026-11-09T23:30:00Z")                                          # the sample country keeps UTC
        self.p.deliveries.partner_step(self.m, d, "picked_up", night)                    # on the way: the customer must act now
        self.p.deliveries.partner_step(self.m, d, "delivered", night + 60)
        sent = [e["payload"] for e in self.p.c.store.of(self.m, "TrackingUpdateSent")]
        self.assertEqual([(s["step"], s["lang"], s["channel"]) for s in sent], [("on_the_way", "fr", "sms"), ("delivered", "fr", "sms")])
        self.assertIsNone(sent[0]["held_until"]); self.assertEqual(sent[1]["held_until"], T.epoch("2026-11-10T07:00:00Z"))
        self.assertIsNone(T.PlatformTracking.quiet_until(T.epoch("2026-11-09T12:00:00Z")))
        self.assertEqual(T.PlatformTracking.quiet_until(T.epoch("2026-11-09T05:00:00Z")), T.epoch("2026-11-09T07:00:00Z"))
        with self.assertRaises(ValueError): self.p.tracking.subscribe(self.m, "delivery", d, "pigeon")

    def test_the_owner_is_told_once_when_a_promise_is_missed(self):
        d, o, evt = self.deliver()
        self.p.deliveries.handle_request(self.m, evt, now=T0)
        self.p.flow.tick("minutely", [self.m], now=T0 + 300)
        self.assertEqual([e for e in self.p.c.store.of(self.m, "AlertSent") if e["payload"]["kind"] == "tracking_late"], [])
        self.p.flow.tick("minutely", [self.m], now=T0 + 700); self.p.flow.tick("minutely", [self.m], now=T0 + 800)
        late = [e["payload"] for e in self.p.c.store.of(self.m, "AlertSent") if e["payload"]["kind"] == "tracking_late"]
        self.assertEqual([x["ref"] for x in late], [d])

    def test_the_public_tracking_page_finds_the_record_by_its_public_id_only(self):
        d, o, evt = self.deliver()
        self.p.deliveries.handle_request(self.m, evt, now=T0)
        pid = self.p.tracking.view("delivery", d, "customer")["public_id"]
        self.assertRegex(pid, r"^LODLV-\d{4}-\d{4}-\d{4}$")
        page = self.p.tracking.by_public_id(pid)
        self.assertEqual(page["step"], "assigned"); self.assertNotIn(d, json.dumps(page))
        self.assertIsNone(self.p.tracking.by_public_id("LODLV-0000-0000-0000"))

    def test_identity_records_are_tracked_for_the_person(self):
        self.p.c.store.append("person-1", "server", "DataRequestOpened", {"lynkid": "x", "request_id": "r1", "due_at": "2026-12-09T00:00:00Z"}, ts="2026-11-09T00:00:00Z")
        v = self.p.tracking.view("data_request", "r1", "person")
        self.assertEqual((v["step"], v["eta"]), ("preparing", "2026-12-09T00:00:00Z"))


class Vectors(unittest.TestCase):
    def test_shared_vectors_are_current(self):
        import subprocess, sys
        r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "tracking_vectors.py"), "--check"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()
