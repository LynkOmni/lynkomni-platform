"""N8 Delivery and pickup (blueprint 44 I). From any order the merchant taps Deliver and picks a delivery partner's price and
time, or their own staff rider. Proof of delivery is a code or a photo of the parcel, never of a person. LynkOmni never employs
riders. The partner's price is shown before booking and paid to the partner through the licensed provider; the partner pays
LynkOmni about $0.10 a delivery (billing SERVICE_FEES delivery_share_cents). Partners are SANDBOX adapters behind
DeliveryPartner (provider ledger: delivery_partners). Pickup uses the same codes as the LynkPOS collection point."""
import hashlib, secrets, time

from contract.tools.validate_contract import uuid7
from services import billing

STATES = ("sent", "accepted", "picked_up", "delivered", "failed")
def _now(n): return time.time() if n is None else n


class DeliveryPartner:
    def quote(self, order): raise NotImplementedError      # {"price": minor, "eta_s": seconds}
    def book(self, delivery): raise NotImplementedError     # {"ok": True, "reference": str, "eta": "…Z"} or {"ok": False, "reason": code}


class SandboxDeliveryPartner(DeliveryPartner):
    """SANDBOX: a flat price and a fixed time; `fail_next` makes the next booking fail."""
    def __init__(self, partner_id, price=1500, eta_s=2700):
        self.id, self.price, self.eta_s, self.fail_next = partner_id, price, eta_s, None
    def quote(self, order): return {"price": self.price, "eta_s": self.eta_s}
    def book(self, delivery):
        if self.fail_next: r, self.fail_next = self.fail_next, None; return {"ok": False, "reason": r}
        return {"ok": True, "reference": "SBXD-" + hashlib.sha256(delivery["delivery_id"].encode()).hexdigest()[:10].upper(), "eta_s": self.eta_s}


class Deliveries:
    def __init__(s, cloud, platform):
        s.cloud, s.p, s.db, s.partners = cloud, platform, platform.c.store.db, {}
        s.db.executescript("""
        create table if not exists dl(delivery_id text primary key, merchant text, order_id text, partner text, own_rider int, price int, currency text, state text, reference text, code_hash text, month text, created real);
        create table if not exists dl_riders(merchant text, rider text, primary key(merchant, rider));""")
    def add_partner(s, partner_id, gateway): s.partners[partner_id] = gateway
    def _ent(s, merchant):
        b = billing.Billing(s.p.c)
        pos, co = b.entitlement(merchant, "lynkpos"), b.entitlement(merchant, "lynkcheckout")
        def higher(k):   # the higher of LynkPOS or LynkCheckout (None = unlimited)
            a, c = pos.get(k), co.get(k)
            return None if a is None or c is None else max(a, c)
        return {"partner_deliveries_per_month": higher("partner_deliveries_per_month"), "own_riders": higher("own_riders"), "delivery_routing": bool(pos.get("delivery_routing") or co.get("delivery_routing"))}
    # ---- own riders (per tier)
    def add_rider(s, merchant, rider):
        limit = s._ent(merchant)["own_riders"]
        have = s.db.execute("select count(*) from dl_riders where merchant=?", (merchant,)).fetchone()[0]
        if limit is not None and have >= limit: raise PermissionError("rider_limit_for_tier")
        s.db.execute("insert or ignore into dl_riders(merchant, rider) values(?,?)", (merchant, rider))
    def riders(s, merchant): return [r[0] for r in s.db.execute("select rider from dl_riders where merchant=?", (merchant,))]
    # ---- quotes: several partners, cheapest or fastest, on Pro and Max (per outlet on Max)
    def quotes(s, merchant, order, prefer="cheapest"):
        qs = [{"partner_id": pid, **gw.quote(order)} for pid, gw in s.partners.items()]
        if not s._ent(merchant)["delivery_routing"]: return qs[:1]
        return sorted(qs, key=lambda q: q["price"] if prefer == "cheapest" else q["eta_s"])
    # ---- the request (the device's DeliveryRequested, online only) and the partner's answer
    def handle_request(s, merchant, evt, now=None):
        p, now = evt["payload"], _now(now); did = p["delivery_id"]; month = time.strftime("%Y-%m", time.gmtime(now))
        code = f"{secrets.randbelow(10**6):06d}"            # the customer's pickup or delivery code; only its hash is kept
        s.db.execute("insert or ignore into dl(delivery_id, merchant, order_id, partner, own_rider, price, currency, state, code_hash, month, created) values(?,?,?,?,?,?,?,'sent',?,?,?)",
                     (did, merchant, p["order_id"], p.get("partner_id"), int(p["own_rider"]), p["price"], p["currency"], hashlib.sha256(code.encode()).hexdigest(), month, now))
        def fail(reason):
            s.db.execute("update dl set state='failed' where delivery_id=?", (did,))
            s.cloud.event(merchant, "DeliveryFailed", {"delivery_id": did, "reason_code": reason}, now=now, causes=[evt["event_id"]])
            return {"state": "failed", "reason": reason}
        if p["own_rider"]:
            if not s.riders(merchant): return fail("other")
            s.db.execute("update dl set state='accepted', reference='own-rider' where delivery_id=?", (did,))
            s.cloud.event(merchant, "DeliveryAccepted", {"delivery_id": did, "partner_reference": "own-rider"}, now=now, causes=[evt["event_id"]])
            return {"state": "accepted", "code": code}
        used = s.db.execute("select count(*) from dl where merchant=? and own_rider=0 and month=? and state!='failed' and delivery_id!=?", (merchant, month, did)).fetchone()[0]
        limit = s._ent(merchant)["partner_deliveries_per_month"]
        if limit is not None and used >= limit: return fail("limit_exceeded")
        gw = s.partners.get(p.get("partner_id"))
        if gw is None: return fail("partner_declined")
        ans = gw.book({"delivery_id": did, "order_id": p["order_id"], "price": p["price"]})
        if not ans.get("ok"): return fail(ans.get("reason", "provider_error"))
        eta = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now + ans.get("eta_s", 0)))
        s.db.execute("update dl set state='accepted', reference=? where delivery_id=?", (ans["reference"], did))
        s.cloud.event(merchant, "DeliveryAccepted", {"delivery_id": did, "partner_reference": ans["reference"], "eta": eta}, now=now, causes=[evt["event_id"]])
        return {"state": "accepted", "code": code, "eta": eta}
    # ---- steps: a partner reports them; own riders record them on the staff device (DeliveryPickedUp / DeliveryDelivered from the device)
    def partner_step(s, merchant, delivery_id, step, now=None):
        if step == "picked_up":
            s.db.execute("update dl set state='picked_up' where delivery_id=?", (delivery_id,))
            s.cloud.event(merchant, "DeliveryPickedUp", {"delivery_id": delivery_id}, now=now)
        elif step == "delivered":
            s.db.execute("update dl set state='delivered' where delivery_id=?", (delivery_id,))
            s.cloud.event(merchant, "DeliveryDelivered", {"delivery_id": delivery_id, "proof": "code"}, now=now)
        else: raise ValueError("unknown step")
    def note_device_step(s, merchant, evt):
        st = {"DeliveryPickedUp": "picked_up", "DeliveryDelivered": "delivered"}[evt["type"]]
        s.db.execute("update dl set state=? where delivery_id=?", (st, evt["payload"]["delivery_id"]))
    def code_matches(s, delivery_id, code):
        r = s.db.execute("select code_hash from dl where delivery_id=?", (delivery_id,)).fetchone()
        return bool(r) and r[0] == hashlib.sha256(code.encode()).hexdigest()
    # ---- what the customer sees (shop.lynkomni.com/track/(LODLV-), no account needed) and what LynkOmni earns
    def track(s, delivery_id):
        r = s.db.execute("select state, reference, own_rider from dl where delivery_id=?", (delivery_id,)).fetchone()
        return {"state": r[0], "own_rider": bool(r[2])} if r else None
    @staticmethod
    def lynkomni_share_cents(partner_deliveries): return partner_deliveries * billing.SERVICE_FEES["delivery_share_cents"]   # paid by the partner, an assumption until contracts
