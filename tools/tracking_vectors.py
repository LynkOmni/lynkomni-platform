#!/usr/bin/env python3
"""Shared vectors for LynkOmni tracking: the Python reference (services/tracking.py) replays each scenario and records what every
audience sees; the TypeScript port (ts/src/tracking.ts) must see exactly the same. Also writes the register into
ts/src/tracking.generated.ts so the apps carry it offline. Run after changing catalog/tracking.v1.json or either engine:
  python3 tools/tracking_vectors.py          writes contract/vectors/tracking.v1.json and ts/src/tracking.generated.ts
  python3 tools/tracking_vectors.py --check  fails when either file is out of date (tests/test_tracking.py)"""
import json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from services import tracking as T  # noqa: E402

OUT = os.path.join(ROOT, "contract", "vectors", "tracking.v1.json")
TS = os.path.join(ROOT, "ts", "src", "tracking.generated.ts")
T0 = 1_794_200_000
U = lambda n: f"01900000-0000-7000-8000-{n:012d}"


def e(t, at, **p): return {"op": "event", "event": {"type": t, "payload": p, "at": at}, "owner": "m1"}
def look(kind, record, audience, now): return {"op": "view", "kind": kind, "record": record, "audience": audience, "now": now}


SCENARIOS = [
    {"name": "partner delivery from request to door, with progress and a missed promise", "steps": [
        e("DeliveryRequested", T0, delivery_id=U(1), order_id=U(2), own_rider=False, price=1500, currency="USD"),
        look("delivery", U(1), "customer", T0),
        e("DeliveryAccepted", T0 + 60, delivery_id=U(1), partner_reference="SBXD-1", eta="2026-11-09T05:00:00Z"),
        e("DeliveryPickedUp", T0 + 120, delivery_id=U(1)),
        {"op": "progress", "kind": "delivery", "record": U(1), "share": 0.425, "eta": None},
        look("delivery", U(1), "customer", T.epoch("2026-11-09T05:00:01Z")),
        look("order", U(2), "merchant", T0 + 130),
        e("DeliveryDelivered", T0 + 180, delivery_id=U(1), proof="code"),
        {"op": "progress", "kind": "delivery", "record": U(1), "share": 0.9, "eta": None},
        look("delivery", U(1), "merchant", T0 + 200),
        look("order", U(2), "customer", T0 + 200)]},
    {"name": "failed delivery shows the failure and nothing after it", "steps": [
        e("DeliveryRequested", T0, delivery_id=U(3), order_id=U(4), own_rider=True, price=0, currency="USD"),
        e("DeliveryFailed", T0 + 5, delivery_id=U(3), reason_code="timeout"),
        e("DeliveryDelivered", T0 + 9, delivery_id=U(3), proof="code"),
        look("delivery", U(3), "customer", T0 + 10)]},
    {"name": "table order: ready only when every line is ready, then collected", "steps": [
        e("OrderSentToKitchen", T0, order_id=U(5), table_id=U(6), lines=[{"product_id": U(7)}, {"product_id": U(8)}]),
        e("KitchenItemReady", T0 + 1, order_id=U(5), line_no=0),
        e("KitchenItemReady", T0 + 2, order_id=U(5), line_no=0),
        look("order", U(5), "customer", T0 + 3),
        e("KitchenItemReady", T0 + 4, order_id=U(5), line_no=1),
        look("order", U(5), "customer", T0 + 5),
        e("PickupHandedOver", T0 + 6, pickup_id=U(9), order_id=U(5), code_hash="0" * 64),
        look("order", U(5), "merchant", T0 + 7)]},
    {"name": "payments wait for the provider; cash is confirmed at once", "steps": [
        e("PaymentRecorded", T0, payment_id=U(10), sale_id=U(11), method="mobile_money", amount=500, status="pending_confirmation", currency="USD"),
        look("payment", U(10), "customer", T0),
        e("PaymentStatusChanged", T0 + 1, payment_id=U(10), from_status="pending_confirmation", to_status="failed", source="provider_callback"),
        look("payment", U(10), "merchant", T0 + 2),
        e("PaymentRecorded", T0, payment_id=U(12), sale_id=U(13), method="cash", amount=500, status="cash_received", currency="USD"),
        look("payment", U(12), "customer", T0)]},
    {"name": "financing follows its offer id", "steps": [
        e("FinancingRequested", T0, request_id=U(14), invoice_id=U(15), consent_id=U(16)),
        e("FinancingOffered", T0 + 1, offer_id=U(17), request_id=U(14), lender_id=U(18), amount=1000, total_cost=1050, currency="USD"),
        e("FinancingAccepted", T0 + 2, offer_id=U(17)),
        look("financing", U(14), "merchant", T0 + 3)]},
    {"name": "an invoice fed by its own service state", "steps": [
        {"op": "state", "kind": "invoice", "record": U(19), "state": "issued", "at": T0},
        {"op": "state", "kind": "invoice", "record": U(19), "state": "viewed", "at": T0 + 1},
        look("invoice", U(19), "customer", T0 + 2),
        look("invoice", U(19), "merchant", T0 + 2)]},
    {"name": "repair steps appear as they are reached", "steps": [
        e("RepairTicketOpened", T0, ticket_id=U(20), customer_id=U(21)),
        e("RepairStatusChanged", T0 + 1, ticket_id=U(20), to_status="waiting_parts"),
        look("repair", U(20), "customer", T0 + 2)]},
    {"name": "account recovery waiting period, then cancelled", "steps": [
        e("RecoveryStarted", T0, lynkid="LOID-1", path="code", recovery_id=U(22), ready_at="2026-11-10T00:00:00Z"),
        look("recovery", U(22), "person", T0),
        e("RecoveryCancelled", T0 + 1, lynkid="LOID-1", recovery_id=U(22), by="person"),
        look("recovery", U(22), "person", T0 + 2)]},
]


H = {"offset_min": 60, "days": {str(d): [[480, 1020]] for d in range(5)}}      # Monday to Friday 08:00 to 17:00, one hour east of UTC
def ev(t, at, eid=None, owner="m1", **p):
    x = {"op": "event", "event": {"type": t, "payload": p, "at": at}, "owner": owner}
    if eid: x["event"]["id"] = eid
    return x

SCENARIOS += [
    {"name": "TRACKING UPDATE: a late offline event lands in its true place, a repeated event counts once, two endings clash", "steps": [
        ev("DeliveryRequested", T0, "e1", delivery_id=U(40), order_id=U(41), own_rider=True, price=0, currency="USD"),
        ev("DeliveryAccepted", T0 + 600, "e2", delivery_id=U(40), partner_reference="SBXD-9", eta="2026-11-09T05:00:00Z"),
        ev("DeliveryDelivered", T0 + 3000, "e3", delivery_id=U(40), proof="code"),
        ev("DeliveryPickedUp", T0 + 1200, "e4", delivery_id=U(40)),
        ev("DeliveryPickedUp", T0 + 1200, "e4", delivery_id=U(40)),
        ev("DeliveryFailed", T0 + 3100, "e5", delivery_id=U(40), reason_code="timeout"),
        look("delivery", U(40), "merchant", T0 + 4000),
        look("delivery", U(40), "customer", T0 + 4000),
        {"op": "exceptions", "owner": "m1", "now": T0 + 4000}]},
    {"name": "TRACKING UPDATE: promises, at risk, late, stuck and the control tower; practice stays out", "steps": [
        ev("DeliveryRequested", T0, None, delivery_id=U(42), order_id=U(43), own_rider=True, price=0, currency="USD"),
        {"op": "risk", "kind": "delivery", "record": U(42), "now": T0 + 11 * 60},
        {"op": "risk", "kind": "delivery", "record": U(42), "now": T0 + 12 * 60},
        {"op": "risk", "kind": "delivery", "record": U(42), "now": T0 + 15 * 60},
        ev("DeliveryRequested", T0 + 60, None, delivery_id=U(44), order_id=U(45), own_rider=True, price=0, currency="USD"),
        ev("DeliveryRequested", T0 + 120, None, delivery_id=U(46), order_id=U(47), own_rider=True, price=0, currency="USD", practice=True),
        ev("OrderSentToKitchen", T0 + 30, None, order_id=U(48), table_id=U(49), lines=[{"line_no": 0}]),
        {"op": "tower", "owner": "m1", "now": T0 + 13 * 60},
        {"op": "tower", "owner": "m1", "now": T0 + 13 * 60, "kind": "delivery"},
        {"op": "exceptions", "owner": "m1", "now": T0 + 31 * 60},
        look("delivery", U(46), "merchant", T0 + 13 * 60)]},
    {"name": "TRACKING UPDATE: working-time promises count only opening hours", "steps": [
        {"op": "working", "start": T0, "end": T0 + 3 * 86400, "hours": H},
        {"op": "working", "start": T0, "end": T0 + 3600},
        {"op": "working", "start": T0 + 3600, "end": T0, "hours": H},
        {"op": "state", "kind": "bill_to_pay", "record": U(50), "state": "draft", "at": T0},
        {"op": "risk", "kind": "bill_to_pay", "record": U(50), "now": T0 + 5 * 86400, "hours": H},
        {"op": "risk", "kind": "bill_to_pay", "record": U(50), "now": T0 + 5 * 86400}]},
    {"name": "TRACKING UPDATE: scanning moves a step only with its proof and after its checks; partner statuses map to events", "steps": [
        ev("DeliveryRequested", T0, None, delivery_id=U(51), order_id=U(52), own_rider=True, price=0, currency="USD"),
        {"op": "scan", "kind": "delivery", "record": U(51), "step": "delivered", "proof": "code"},
        {"op": "scan", "kind": "delivery", "record": U(51), "step": "on_the_way", "client": ["DeliveryPickedUp", "DeliveryDelivered"]},
        ev("DeliveryPickedUp", T0 + 60, None, delivery_id=U(51)),
        {"op": "scan", "kind": "delivery", "record": U(51), "step": "delivered"},
        {"op": "scan", "kind": "delivery", "record": U(51), "step": "delivered", "proof": "signature"},
        {"op": "scan", "kind": "delivery", "record": U(51), "step": "assigned"},
        {"op": "scan", "kind": "delivery", "record": U(51), "step": "on_the_way", "client": ["DeliveryDelivered"]},
        {"op": "partner", "kind": "delivery", "partner": "delivery_partner", "code": "picked_up"},
        {"op": "partner", "kind": "delivery", "partner": "delivery_partner", "code": "lost_in_space"}]},
    {"name": "TRACKING UPDATE: a business's own extra steps show to it, never change the chip; capacity; keeping time", "steps": [
        {"op": "extra_defs", "owner": "m1", "kind": "order", "steps": [{"id": "quality_check", "label": "Quality check"}, {"id": "bagged", "label": "Bagged", "customer": True}]},
        ev("OrderSentToKitchen", T0, None, order_id=U(53), table_id=U(54), lines=[{"line_no": 0}]),
        ev("TrackingStepMarked", T0 + 50, None, kind="order", record=U(53), extra_step="bagged"),
        ev("TrackingStepMarked", T0 + 40, None, kind="order", record=U(53), extra_step="quality_check"),
        ev("TrackingStepMarked", T0 + 60, None, kind="order", record=U(53), extra_step="unknown_step"),
        look("order", U(53), "merchant", T0 + 100),
        look("order", U(53), "customer", T0 + 100),
        {"op": "promise", "base": 10, "load": 7, "capacity": 3, "per_round": 5},
        {"op": "promise", "base": 10, "load": 0, "capacity": 2, "per_round": 5},
        ev("DeliveryRequested", T0, None, delivery_id=U(55), order_id=U(56), own_rider=True, price=0, currency="USD"),
        ev("DeliveryDelivered", T0 + 100, None, delivery_id=U(55), proof="code"),
        {"op": "prune", "now": T0 + 100 + 180 * 86400},
        {"op": "prune", "now": T0 + 101 + 180 * 86400}]},
]

def run(scn):
    t, out = T.Tracking(), []
    for s in scn["steps"]:
        if s["op"] == "event": t.apply(s["event"], s["owner"])
        elif s["op"] == "progress": out.append({"progress_ok": t.set_progress(s["kind"], s["record"], s["share"], s["eta"])})
        elif s["op"] == "state": t.feed_state(s["kind"], s["record"], s["state"], s["at"])
        elif s["op"] == "extra_defs": t.set_extra_steps(s["owner"], s["kind"], s["steps"])
        elif s["op"] == "risk": out.append({"risk": t.risk(s["kind"], s["record"], s["now"], s.get("hours"))})
        elif s["op"] == "exceptions": out.append({"exceptions": t.exceptions(s["owner"], s["now"], s.get("hours"))})
        elif s["op"] == "tower": out.append({"tower": t.tower(s["owner"], s["now"], s.get("kind"), s.get("step"), s.get("hours"))})
        elif s["op"] == "scan": out.append({"scan": t.scan(s["kind"], s["record"], s["step"], s.get("proof"), set(s["client"]) if "client" in s else None)})
        elif s["op"] == "partner": out.append({"partner": t.partner_event(s["kind"], s["partner"], s["code"])})
        elif s["op"] == "promise": out.append({"promise": T.promise_minutes(s["base"], s["load"], s["capacity"], s["per_round"])})
        elif s["op"] == "working": out.append({"working": T.working_minutes(s["start"], s["end"], s.get("hours"))})
        elif s["op"] == "prune": out.append({"pruned": t.prune(s["now"]), "left": sorted(f"{k}|{r}" for k, r in t.recs)})
        else: out.append({"view": t.view(s["kind"], s["record"], s["audience"], s["now"])})
    return out


def build():
    return {"version": 1, "description": "Tracking scenarios and what each audience sees (services/tracking.py is the reference; ts/src/tracking.ts must agree).",
            "scenarios": [{"name": s["name"], "steps": s["steps"], "expect": run(s)} for s in SCENARIOS]}


def ts_text():
    """Only what the engine reads travels to the apps (version, states, kinds without their prose), one kind per line: the
    register's descriptions, rules and planned list stay in catalog/tracking.v1.json, so every app file stays small."""
    reg = T.register()
    kinds = [{k: v for k, v in kind.items() if k != "description"} for kind in reg["kinds"]]
    body = ",\n  ".join(json.dumps(k, ensure_ascii=False, separators=(",", ":")) for k in kinds)
    engine = json.dumps({k: v for k, v in reg.get("engine", {}).items() if isinstance(v, int)}, separators=(",", ":"))   # the numbers only
    return ("// GENERATED by tools/tracking_vectors.py from catalog/tracking.v1.json. Do not edit by hand.\n"
            "import type { Register } from \"./tracking.js\";\n"
            f"export const REGISTER: Register = {{\"version\":{reg['version']},\"states\":{json.dumps(reg['states'])},\"engine\":{engine},\"kinds\":[\n  {body}\n]}};\n")


def main(argv):
    vec = json.dumps(build(), indent=1, ensure_ascii=False) + "\n"
    ts = ts_text()
    if "--check" in argv:
        bad = [p for p, want in ((OUT, vec), (TS, ts)) if not os.path.isfile(p) or open(p, encoding="utf-8").read() != want]
        print("out of date: " + ", ".join(bad) if bad else "tracking vectors and register are current")
        return 1 if bad else 0
    for p, txt in ((OUT, vec), (TS, ts)):
        with open(p, "w", encoding="utf-8") as f: f.write(txt)
    print(f"wrote {OUT} and {TS}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
