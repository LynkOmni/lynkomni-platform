"""All nine LynkOmni CORE services as modules over one event log.
Numbers match the locked list: 1 Universal Payment App, 2 Offline-First POS, 3 Automatic Business Accountant,
4 Payment Failure Recovery, 5 Pay-by-Link and QR, 6 Smart Inventory and Reordering, 7 Customer Loyalty,
8 Global Merchant Dashboard, 9 Merchant Growth Engine (intelligence, marketplace, financing, protection)."""
import base64, hashlib, hmac, json, os, time, uuid
from decimal import Decimal
from core.events import EventStore
from core.money import FX
from core.providers import build_providers, fiscal_for
from core.regions import SERVICES, country, enabled, resolve_country

CLIENT_EVENTS = {"sale.recorded", "sale.voided", "stock.received", "expense.recorded", "refund.recorded",
                 "loyalty.earned", "loyalty.redeemed", "credit.sale", "credit.payment", "shift.opened",
                 "shift.closed", "chat.thread.opened", "chat.message", "chat.read", "ad.impression", "ad.click"}  # nothing else from devices

class ServiceOff(Exception):
    pass

class Ctx:
    def __init__(self, store=None, fx=None, providers=None):
        self.store, self.fx, self.providers = store or EventStore(), fx or FX(), providers or {}
    def profile(self, m):
        e = self.store.of(m, "merchant.registered")
        return e[-1]["payload"] if e else {"country": None, "currency": "USD"}
    def gate(self, m, svc):
        if not enabled(self.profile(m)["country"], svc):
            raise ServiceOff(f"{svc} is not enabled for this country yet")
    def prov(self, code):
        if code not in self.providers:
            self.providers[code] = build_providers(country(code)["providers"])  # sandbox simulators
        return self.providers[code]
    def base(self, m, p, key="total_minor"):
        return self.fx.convert(p[key], p.get("currency", self.profile(m)["currency"]), self.profile(m)["currency"])

class Inventory:  # 6
    def __init__(s, c): s.c = c
    def receive(s, m, device, sku, qty, cost_minor):
        s.c.store.append(m, device, "stock.received", {"sku": sku, "qty": qty, "cost_minor": cost_minor})
    def levels(s, m):
        lv = {}
        for e in s.c.store.of(m, "stock.received", "sale.recorded", "sale.voided"):
            p = e["payload"]
            if e["type"] == "stock.received":
                lv[p["sku"]] = lv.get(p["sku"], 0) + p["qty"]
            else:
                sign = 1 if e["type"] == "sale.voided" else -1
                for i in p["items"]:
                    lv[i["sku"]] = lv.get(i["sku"], 0) + sign * i["qty"]
        return lv
    def negative(s, m):  # oversold while offline: flagged for the owner, never blocked
        return {k: v for k, v in s.levels(m).items() if v < 0}
    def low(s, m, threshold=5):
        return {k: v for k, v in s.levels(m).items() if v <= threshold}
    def avg_cost(s, m):
        q, t = {}, {}
        for e in s.c.store.of(m, "stock.received"):
            p = e["payload"]
            q[p["sku"]] = q.get(p["sku"], 0) + p["qty"]
            t[p["sku"]] = t.get(p["sku"], 0) + p["qty"] * p["cost_minor"]
        return {k: t[k] // q[k] for k in q if q[k]}

class POS:  # 2
    def __init__(s, c): s.c = c
    def record_sale(s, m, device, items, method="cash", customer=None, id_=None):
        s.c.gate(m, "pos")
        pr = s.c.profile(m)
        total = sum(i["qty"] * i["price_minor"] for i in items)
        p = {"items": items, "total_minor": total, "currency": pr["currency"], "method": method, "customer": customer}
        id_ = id_ or uuid.uuid4().hex
        s.c.store.append(m, device, "sale.recorded", p, id_)
        return {"sale_id": id_, "total_minor": total, "receipt": fiscal_for(country(pr["country"])["fiscal"]).issue(p)}
    def expense(s, m, device, amount_minor, category):
        s.c.store.append(m, device, "expense.recorded", {"amount_minor": amount_minor, "category": category, "currency": s.c.profile(m)["currency"]})

class Accountant:  # 3
    def __init__(s, c): s.c = c
    def journal(s, m):
        """The double-entry journal: a projection of the event log on the one global chart of accounts (core/accounts.py),
        in the base currency, at every tier. Cost of goods sold is posted per sale at the average cost, so the journal's
        profit is the same number as summary()."""
        from core import accounts
        types = tuple(accounts.POSTINGS)
        entries = accounts.journal(s.c.store.of(m, *types), lambda p, f: s.c.base(m, p, f))
        cost = Inventory(s.c).avg_cost(m)
        for e in s.c.store.of(m, "sale.recorded", "sale.voided"):
            cogs = sum(i["qty"] * cost.get(i["sku"], 0) for i in e["payload"]["items"])
            if cogs:
                dr, cr = ("5000", "1200") if e["type"] == "sale.recorded" else ("1200", "5000")
                entries.append({"event_id": e["id"], "type": e["type"] + ".cogs", "ts": e["ts"], "lines": [(dr, cogs, 0), (cr, 0, cogs)]})
        entries.sort(key=lambda x: (x["ts"] or "", x["event_id"]))
        return entries
    def trial_balance(s, m):
        from core import accounts
        pack = country(s.c.profile(m)["country"])
        names = accounts.local_chart(pack)
        tb = accounts.trial_balance(s.journal(m))
        return {code: {"name": names[code]["name"], "local_code": names[code]["code"], "type": names[code]["type"], "balance_minor": v} for code, v in sorted(tb.items())}
    def summary(s, m):
        base, cost = s.c.profile(m)["currency"], Inventory(s.c).avg_cost(m)
        r = rf = ex = fee = cogs = 0
        for e in s.c.store.of(m, "sale.recorded", "sale.voided", "refund.recorded", "expense.recorded", "payment.settled"):
            p, t = e["payload"], e["type"]
            if t == "sale.recorded":
                r += s.c.base(m, p)
                cogs += sum(i["qty"] * cost.get(i["sku"], 0) for i in p["items"])
            elif t == "sale.voided":
                r -= s.c.base(m, p)
                cogs -= sum(i["qty"] * cost.get(i["sku"], 0) for i in p["items"])
            elif t == "refund.recorded":
                rf += s.c.base(m, p, "amount_minor")
            elif t == "expense.recorded":
                ex += s.c.base(m, p, "amount_minor")
            else:
                fee += s.c.base(m, p, "fee_minor")
        return dict(currency=base, revenue_minor=r, refunds_minor=rf, cogs_minor=cogs, expenses_minor=ex,
                    fees_minor=fee, profit_minor=r - rf - cogs - ex - fee)

class Payments:  # 1 Universal Payment App + 4 Failure Recovery (providers are sandbox simulators)
    def __init__(s, c): s.c = c
    def charge(s, m, amount_minor, method, key):
        s.c.gate(m, "payments")
        pr = s.c.profile(m)
        recover = enabled(pr["country"], "recovery")
        routes = [x for x in s.c.prov(pr["country"]) if method in x.methods]
        for r in (routes if recover else routes[:1]):
            for attempt in range(1, 3 if recover else 2):
                res = r.charge(amount_minor, pr["currency"], method, key)  # same key: safe to retry
                s.c.store.append(m, "server", "payment.attempt", {"provider": r.name, "attempt": attempt, "ok": res["ok"]})
                if res["ok"]:
                    s.c.store.append(m, "server", "payment.settled", {"provider": r.name, "amount_minor": amount_minor,
                                     "currency": pr["currency"], "fee_minor": res["fee_minor"], "ref": res["ref"]})
                    return {"ok": True, "provider": r.name, "ref": res["ref"]}
        alts = sorted({x for p in s.c.prov(pr["country"]) for x in p.methods} - {method})
        s.c.store.append(m, "server", "payment.failed", {"amount_minor": amount_minor, "method": method})
        return {"ok": False, "suggest_methods": alts}

class PayLinks:  # 5 (QR image rendering is the client's job; this builds the signed payload)
    SECRET = os.environ.get("LYNK_SECRET", "dev-only-change-me")
    def __init__(s, c): s.c = c
    def _sig(s, body): return hmac.new(s.SECRET.encode(), body.encode(), hashlib.sha256).hexdigest()[:24]
    def create(s, m, amount_minor, ref, ttl=86400):
        s.c.gate(m, "paylinks")
        body = f"{m}|{amount_minor}|{s.c.profile(m)['currency']}|{ref}|{int(time.time()) + ttl}"
        tok = base64.urlsafe_b64encode(body.encode()).decode() + "." + s._sig(body)
        return {"url": f"https://pay.lynkomni.example/{tok}", "qr_payload": f"lynk://pay?t={tok}"}
    def verify(s, token):
        try:
            b, sig = token.rsplit(".", 1)
            body = base64.urlsafe_b64decode(b.encode()).decode()
            m, amt, cur, ref, exp = body.split("|")
        except Exception:
            return None
        if not hmac.compare_digest(sig, s._sig(body)) or int(exp) < time.time():
            return None
        return {"merchant": m, "amount_minor": int(amt), "currency": cur, "ref": ref}

class Loyalty:  # 7
    def __init__(s, c): s.c = c
    def earn(s, m, customer, total_minor, points_per_major=1):
        s.c.gate(m, "loyalty")
        from core.money import CURRENCIES
        pts = total_minor // 10 ** CURRENCIES[s.c.profile(m)["currency"]] * points_per_major
        s.c.store.append(m, "server", "loyalty.earned", {"customer": customer, "points": pts})
        return pts
    def balance(s, m, customer):
        return sum(e["payload"]["points"] * (1 if e["type"] == "loyalty.earned" else -1)
                   for e in s.c.store.of(m, "loyalty.earned", "loyalty.redeemed") if e["payload"]["customer"] == customer)
    def redeem(s, m, customer, points):
        if s.balance(m, customer) < points:
            return False
        s.c.store.append(m, "server", "loyalty.redeemed", {"customer": customer, "points": points})
        return True
    def refer(s, m, referrer, bonus=50):
        s.c.store.append(m, "server", "loyalty.earned", {"customer": referrer, "points": bonus})

class Marketplace:  # 9b Supplier Marketplace + 6 reordering. Suppliers are a catalog adapter.
    def __init__(s, c, inv): s.c, s.inv, s.suppliers = c, inv, {}
    def register_supplier(s, name, prices): s.suppliers[name] = prices
    def compare(s, sku): return sorted((p[sku], n) for n, p in s.suppliers.items() if sku in p)
    def reorder(s, m, target=20, threshold=5):
        out = []
        for sku, have in s.inv.low(m, threshold).items():
            q = s.compare(sku)
            out.append({"sku": sku, "order_qty": max(target - have, 0), "best": q[0] if q else None, "quotes": q})
        return out

class Growth:  # 9a intelligence, 9c financing (consent-based), 9d protection (referral)
    def __init__(s, c, inv, acct): s.c, s.inv, s.acct = c, inv, acct
    def intelligence(s, m):
        cost, sold, leaks = s.inv.avg_cost(m), set(), []
        for e in s.c.store.of(m, "sale.recorded"):
            for i in e["payload"]["items"]:
                sold.add(i["sku"])
                if i["sku"] in cost and i["price_minor"] < cost[i["sku"]]:
                    leaks.append(i["sku"])
        a = s.acct.summary(m)
        return {"profit_leaks": sorted(set(leaks)),
                "slow_stock": sorted(k for k, v in s.inv.levels(m).items() if v > 0 and k not in sold),
                "cashflow_warning": a["expenses_minor"] + a["cogs_minor"] > a["revenue_minor"]}
    def grant_consent(s, m, lender): DataRights(s.c).grant(m, lender)
    def share_with_lender(s, m, lender):
        s.c.gate(m, "financing")
        if not DataRights(s.c).has_consent(m, lender):
            raise PermissionError("no merchant consent for this lender")
        a = s.acct.summary(m)
        s.c.store.append(m, "server", "financing.shared", {"lender": lender})
        return {k: a[k] for k in ("currency", "revenue_minor", "profit_minor")}  # summary only, never raw records
    def protection_referral(s, m, provider):
        s.c.gate(m, "protection")
        s.c.store.append(m, "server", "protection.referred", {"provider": provider})
        return {"status": "referred"}

class Dashboard:  # 8
    def __init__(s, c, inv, acct, growth): s.c, s.inv, s.acct, s.g = c, inv, acct, growth
    def view(s, m, display=None):
        pr, a = s.c.profile(m), s.acct.summary(m)
        cur = display or pr["currency"]
        cv = lambda x: s.c.fx.convert(x, pr["currency"], cur)
        t = Decimal(country(pr["country"])["tax_rate"])
        return {"currency": cur, "revenue_minor": cv(a["revenue_minor"]), "profit_minor": cv(a["profit_minor"]),
                "expenses_minor": cv(a["expenses_minor"]), "low_stock": s.inv.low(m), "negative_stock": s.inv.negative(m),
                "tax_estimate_minor": cv(int(Decimal(a["revenue_minor"]) * t / (1 + t))),  # estimate, not a filing
                "insights": s.g.intelligence(m)}

class DataRights:  # data rights and trust: consent log, revoke, export
    def __init__(s, c): s.c = c
    def grant(s, m, party): s.c.store.append(m, "server", "consent.granted", {"lender": party, "party": party})
    def revoke(s, m, party): s.c.store.append(m, "server", "consent.revoked", {"party": party})
    def has_consent(s, m, party):
        ok = False
        for e in s.c.store.of(m, "consent.granted", "consent.revoked"):
            if e["payload"]["party"] == party:
                ok = e["type"] == "consent.granted"
        return ok
    def log(s, m):
        return [(e["type"], e["payload"]["party"], e["ts"]) for e in s.c.store.of(m, "consent.granted", "consent.revoked")]
    def export(s, m):  # the merchant's own data, portable at any time
        return s.c.store.since(m, 0)

class Platform:
    def __init__(s, path=":memory:", fx=None, providers=None):
        s.c = Ctx(EventStore(path), fx, providers)
        s.inventory, s.pos, s.accountant = Inventory(s.c), POS(s.c), Accountant(s.c)
        s.payments, s.paylinks, s.loyalty = Payments(s.c), PayLinks(s.c), Loyalty(s.c)
        s.marketplace = Marketplace(s.c, s.inventory)
        s.growth = Growth(s.c, s.inventory, s.accountant)
        s.dashboard = Dashboard(s.c, s.inventory, s.accountant, s.growth)
    def register(s, m, country_code=None, lat=None, lon=None, channel=None):
        code = resolve_country(lat, lon, country_code)
        cfg = country(code)
        s.c.store.append(m, "server", "merchant.registered", {"country": code, "currency": cfg["currency"], "channel": channel})
        return {"country": code, "currency": cfg["currency"], "locale": cfg["locale"], "languages": cfg["languages"],
                "providers": cfg["providers"], "flags": {k: enabled(code, k) for k in SERVICES}}
    PRIORITY = {"sale.recorded": 0, "sale.voided": 0, "refund.recorded": 0, "expense.recorded": 1, "stock.received": 1,
                "credit.sale": 1, "credit.payment": 1, "shift.opened": 1, "shift.closed": 1, "loyalty.earned": 2,
                "loyalty.redeemed": 2, "chat.thread.opened": 3, "chat.message": 3, "chat.read": 4,
                "ad.impression": 5, "ad.click": 5}
    def sync(s, m, device, events, cursor=0, budget_bytes=None):
        """Priority sync: money events first, chat later. A byte budget (data saver) defers the rest."""
        acc = dup = rej = used = 0
        deferred = []
        for e in sorted(events, key=lambda e: s.PRIORITY.get(e["type"], 9)):  # stable: order kept within a priority
            size = len(json.dumps(e))
            if budget_bytes is not None and used + size > budget_bytes:
                deferred.append(e["id"]); continue
            used += size
            if e["type"] not in CLIENT_EVENTS:
                rej += 1
            elif s.c.store.append(m, device, e["type"], e["payload"], e["id"], e.get("ts")):
                acc += 1
            else:
                dup += 1
        rows = s.c.store.since(m, cursor)
        return {"accepted": acc, "duplicates": dup, "rejected": rej, "deferred": deferred,
                "cursor": rows[-1]["seq"] if rows else cursor,
                "events": [e for e in rows if e["device"] != device], "negative_stock": s.inventory.negative(m)}
