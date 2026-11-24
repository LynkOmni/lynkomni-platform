"""The tracking engine upgrade (TRACKING UPDATE, master blueprint section 72.3 and 72.4, built in section 4 row 72.9): flows never break
items on their way, a step shows within two seconds, every kind's promise and scan rules point at real steps and device events, and the
owner is told once per item and reason about what needs a person. The behaviour itself is in the shared vectors
(contract/vectors/tracking.v1.json, the scenarios named TRACKING UPDATE)."""
import json, os, time, unittest, uuid
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import sys; sys.path.insert(0, ROOT)
from services import tracking as T
from contract.tools.validate_contract import REGISTRY, uuid7

REG = json.load(open(os.path.join(ROOT, "catalog", "tracking.v1.json"), encoding="utf-8"))
LOCK = json.load(open(os.path.join(ROOT, "contract", "vectors", "tracking-steps.lock.json"), encoding="utf-8"))["kinds"]
T0 = 1_794_200_000
DEVICE = {n for n, e in REGISTRY["events"].items() if "device" in e["origins"]}


class Flows(unittest.TestCase):
    def test_no_step_is_ever_removed_or_renamed_and_new_ones_are_locked_in(self):
        now = {k["id"]: [s["id"] for s in k["steps"]] for k in REG["kinds"]}
        for kind, steps in LOCK.items():
            self.assertIn(kind, now, f"{kind}: a tracking kind was removed while items may be on their way")
            self.assertEqual([s for s in steps if s not in now[kind]], [], f"{kind}: a step was removed or renamed")
        for kind, steps in now.items():
            self.assertEqual([s for s in steps if s not in LOCK.get(kind, [])], [], f"{kind}: add the new steps to contract/vectors/tracking-steps.lock.json")

    def test_promises_scans_checks_and_partner_maps_point_at_real_steps_and_device_events(self):
        for k in REG["kinds"]:
            ids = {s["id"] for s in k["steps"]}
            for st, minutes in k.get("promise", {}).items():
                self.assertIn(st, ids, k["id"]); self.assertGreater(minutes, 0, k["id"])
            for st, rule in k.get("scan", {}).items():
                self.assertIn(st, ids, k["id"])
                self.assertIn(rule["event"], DEVICE, f"{k['id']}.{st}: a scan only ever writes an event a device may write")
                self.assertTrue(any(r.get("event") == rule["event"] for s in k["steps"] if s["id"] == st for r in s["on"]), f"{k['id']}.{st}")
            for st, checks in k.get("checks", {}).items():
                self.assertIn(st, ids, k["id"])
                for c in checks: self.assertIn(c.removeprefix("after:"), ids, k["id"])
            for st in k.get("waits_on_customer", []): self.assertIn(st, ids, k["id"])
            for partner, m in k.get("partner_status", {}).items():
                for code, event in m.items():
                    self.assertIn(event, REGISTRY["events"], f"{k['id']} {partner} {code}")
                    self.assertIn("server", REGISTRY["events"][event]["origins"], f"{event}: the cloud writes what a partner reports")

    def test_extra_steps_are_limited_and_never_borrow_a_registered_id(self):
        t = T.Tracking()
        with self.assertRaises(ValueError): t.set_extra_steps("m", "order", [{"id": f"step_{i}", "label": "x"} for i in range(6)])
        with self.assertRaises(ValueError): t.set_extra_steps("m", "order", [{"id": "ready", "label": "x"}])
        with self.assertRaises(ValueError): t.set_extra_steps("m", "order", [{"id": "Bad-Id", "label": "x"}])


class TwoSeconds(unittest.TestCase):
    def test_a_busy_day_is_applied_and_drawn_well_inside_two_seconds(self):
        t, n = T.Tracking(), 4000
        events = []
        for i in range(n):
            d, o = f"d{i}", f"o{i}"
            events += [{"type": "DeliveryRequested", "payload": {"delivery_id": d, "order_id": o, "own_rider": True, "price": 0, "currency": "USD"}, "at": T0 + i},
                       {"type": "DeliveryPickedUp", "payload": {"delivery_id": d}, "at": T0 + i + 60}]
        start = time.perf_counter()
        for e in events: t.apply(e, "m")
        t.tower("m", T0 + 3600); t.exceptions("m", T0 + 3600)
        took_ms = (time.perf_counter() - start) * 1000
        self.assertLess(took_ms, REG["engine"]["two_second_ms"], f"{len(events)} events took {took_ms:.0f} ms")


class RaisedOnce(unittest.TestCase):
    def setUp(self):
        os.environ.pop("LYNK_MODE", None)
        from services.platform import Platform
        self.p = Platform(); self.m = str(uuid.uuid4())
        self.p.business.create(self.m, "Shop", "shop", "XX", "USD", now=T0)

    def test_what_needs_a_person_is_raised_once_per_item_and_reason_and_never_for_practice(self):
        tr = self.p.tracking.t
        tr.apply({"type": "OrderSentToKitchen", "payload": {"order_id": "o1", "table_id": uuid7(), "lines": [{"line_no": 0}]}, "at": T0}, self.m)
        tr.apply({"type": "OrderSentToKitchen", "payload": {"order_id": "o2", "table_id": uuid7(), "lines": [{"line_no": 0}], "practice": True}, "at": T0}, self.m)
        for minute in (9, 25, 26):
            self.p.flow.tick("minutely", [self.m], now=T0 + minute * 60)
        got = [(e["payload"]["ref"], e["payload"]["detail"]["why"]) for e in self.p.c.store.of(self.m, "AlertSent") if e["payload"]["kind"] == "tracking_exception"]
        self.assertEqual(got, [("o1", "at_risk"), ("o1", "stuck")])


if __name__ == "__main__":
    unittest.main()
