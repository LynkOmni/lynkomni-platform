"""Agent point mode (blueprint 42 C and 42 I; owner rules in CLAUDE.md). The device asks (AgentRequestCreated, online only);
the cloud alone writes the partner's answer. The cash belongs to the agent, the electronic float sits in the agent's own
account at the licensed partner, the partner checks identity, sets limits, confirms each transaction and pays the agent's
commission; LynkOmni bills the partner for its share and never pools, holds or settles money. Cash changes hands only after
the partner confirms. Partners are SANDBOX adapters behind PartnerGateway (provider ledger: agent_partner_gateways,
collection_partners, partner_finance_referrals)."""
import hashlib, time

from contract.tools.validate_contract import uuid7
from services import billing

SERVICES = ("cash_withdrawal", "cash_deposit", "money_transfer", "airtime_data", "bills", "tickets", "government_payment", "remittance")
COLLECTION_KINDS = ("loan_repayment", "insurance_premium", "voucher", "pickup")
FINANCE_PRODUCTS = ("savings", "loan", "pay_later", "insurance")
STATES = ("sent", "confirmed", "failed")        # what the agent sees; "queued" never happens here (never offline)
LOW_FLOAT_RATIO = 0.2                            # S2: warn when the float is under a fifth of the day's usual need
def _now(n): return time.time() if n is None else n


class PartnerGateway:
    """Interface to a bank, mobile-money network, aggregator, government gateway, remittance firm, lender or insurer in the
    Partner Hub. The partner decides everything that moves money."""
    def limits(self, service): raise NotImplementedError              # {"per_transaction": minor, "per_day": minor}
    def identity_check(self, service, customer_reference): raise NotImplementedError   # True when the partner accepts the customer
    def send(self, request): raise NotImplementedError                 # {"ok": bool, "reference": str, "commission": minor} or {"ok": False, "reason": code}
    def float_balance(self, agent_account): raise NotImplementedError  # minor units in the agent's own account at the partner
    def statement(self, period): raise NotImplementedError             # [{"request_id", "commission"}] as the partner reports it


class SandboxPartner(PartnerGateway):
    """SANDBOX partner: fixed limits, a float it keeps itself, a commission of 1% and a statement that repeats what it confirmed.
    `fail_next` makes the next request fail with a reason code, so tests cover every state."""
    def __init__(self, partner_id, float_minor=500_000, per_transaction=200_000, per_day=2_000_000, commission_bps=100):
        self.id, self.float, self.per_tx, self.per_day, self.bps = partner_id, float_minor, per_transaction, per_day, commission_bps
        self.confirmed, self.fail_next, self.rejects_identity = {}, None, set()
    def limits(self, service): return {"per_transaction": self.per_tx, "per_day": self.per_day}
    def identity_check(self, service, customer_reference): return customer_reference not in self.rejects_identity
    def send(self, request):
        if self.fail_next: reason, self.fail_next = self.fail_next, None; return {"ok": False, "reason": reason}
        if request["service"] in ("cash_withdrawal", "money_transfer", "remittance", "bills", "airtime_data", "tickets", "government_payment") and request["amount"] > self.float:
            return {"ok": False, "reason": "insufficient_float"}
        if request["service"] == "cash_deposit": self.float += request["amount"]
        else: self.float -= request["amount"]
        commission = request["amount"] * self.bps // 10_000
        ref = "SBX-" + hashlib.sha256(request["request_id"].encode()).hexdigest()[:12].upper()
        self.confirmed[request["request_id"]] = {"reference": ref, "commission": commission, "amount": request["amount"]}
        return {"ok": True, "reference": ref, "commission": commission}
    def float_balance(self, agent_account): return self.float
    def statement(self, period): return [{"request_id": k, "commission": v["commission"]} for k, v in self.confirmed.items()]


class AgentPoint:
    def __init__(s, cloud, platform):
        s.cloud, s.p, s.db = cloud, platform, platform.c.store.db
        s.partners, s.approved = {}, {}     # partner_id -> gateway; merchant -> set(partner_id) the partner approved as its agent
        s.db.executescript("""
        create table if not exists ag_requests(request_id text primary key, merchant text, partner text, service text, amount int, fee int, commission int, currency text, state text, reference text, day text, created real);
        create table if not exists ag_float(merchant text, partner text, balance int, read_at real, primary key(merchant, partner));
        create table if not exists ag_cash(merchant text, count_id text primary key, difference int, kind text, at real);""")
    # ---- partners and approval (only approved agents; per-tier partner count)
    def add_partner(s, partner_id, gateway): s.partners[partner_id] = gateway
    def approve_agent(s, merchant, partner_id):
        """The partner approved this business as its agent. The tier caps how many partners an agent point can hold."""
        limit = billing.Billing(s.p.c).entitlement(merchant, "lynkpos").get("agent_partners")
        have = s.approved.setdefault(merchant, set())
        if partner_id not in have and limit is not None and len(have) >= limit: raise PermissionError("partner_limit_for_tier")
        have.add(partner_id)
    def outlets_allowed(s, merchant):
        return billing.Billing(s.p.c).entitlement(merchant, "lynkpos").get("outlets")   # None = unlimited (S9: each outlet's float stays at the partner)
    # ---- limits shown before each request (partner's and the country pack's)
    def limits(s, merchant, partner_id, service, country=None):
        from core import regions
        pl = s.partners[partner_id].limits(service)
        pack = regions.country(country).get("agent_limits", {}).get(service, {})
        return {"per_transaction": min(x for x in (pl["per_transaction"], pack.get("per_transaction")) if x is not None),
                "per_day": min(x for x in (pl["per_day"], pack.get("per_day")) if x is not None)}
    def used_today(s, merchant, partner_id, day):
        r = s.db.execute("select coalesce(sum(amount),0) from ag_requests where merchant=? and partner=? and day=? and state='confirmed'", (merchant, partner_id, day)).fetchone()
        return r[0]
    # ---- the request flow: the device's AgentRequestCreated arrives, the cloud answers
    def handle_request(s, merchant, evt, now=None, country=None):
        """evt: the device's AgentRequestCreated (already accepted by cc/box.py). Writes AgentRequestConfirmed + CommissionRecorded,
        or AgentRequestFailed. Returns the state the agent sees. Cash may change hands only on 'confirmed'."""
        p = evt["payload"]; rid, partner_id, service = p["request_id"], p["partner_id"], p["service"]
        now = _now(now); day = time.strftime("%Y-%m-%d", time.gmtime(now))
        s.db.execute("insert or ignore into ag_requests(request_id, merchant, partner, service, amount, fee, commission, currency, state, day, created) values(?,?,?,?,?,?,0,?,'sent',?,?)",
                     (rid, merchant, partner_id, service, p["amount"], p["fee"], p["currency"], day, now))
        def fail(reason):
            s.db.execute("update ag_requests set state='failed' where request_id=?", (rid,))
            s.cloud.event(merchant, "AgentRequestFailed", {"request_id": rid, "reason_code": reason}, now=now, causes=[evt["event_id"]])
            return "failed"
        gw = s.partners.get(partner_id)
        if gw is None or partner_id not in s.approved.get(merchant, set()): return fail("partner_declined")   # only approved agents
        lim = s.limits(merchant, partner_id, service, country)
        if p["amount"] > lim["per_transaction"] or s.used_today(merchant, partner_id, day) + p["amount"] > lim["per_day"]: return fail("limit_exceeded")
        if not gw.identity_check(service, p.get("customer_reference")): return fail("identity_check_failed")   # the partner checks identity; only its reference is kept
        ans = gw.send({"request_id": rid, "service": service, "amount": p["amount"], "fee": p["fee"], "currency": p["currency"], "customer_reference": p.get("customer_reference")})
        if not ans.get("ok"): return fail(ans.get("reason", "provider_error"))
        s.db.execute("update ag_requests set state='confirmed', reference=?, commission=? where request_id=?", (ans["reference"], ans["commission"], rid))
        s.cloud.event(merchant, "AgentRequestConfirmed", {"request_id": rid, "partner_reference": ans["reference"], "amount": p["amount"], "fee": p["fee"], "commission": ans["commission"], "currency": p["currency"]}, now=now, causes=[evt["event_id"]])
        s.cloud.event(merchant, "CommissionRecorded", {"commission_id": uuid7(), "request_id": rid, "partner_id": partner_id, "amount": ans["commission"], "currency": p["currency"], "period": day}, now=now)
        return "confirmed"
    def state(s, request_id):
        r = s.db.execute("select state, reference from ag_requests where request_id=?", (request_id,)).fetchone()
        return {"state": r[0], "partner_reference": r[1]} if r else None
    @staticmethod
    def may_hand_over_cash(state): return state == "confirmed"     # never on "sent"
    # ---- float (read from the partner, never held) and the low-float warning (S2)
    def read_float(s, merchant, partner_id, now=None):
        bal, now = s.partners[partner_id].float_balance(merchant), _now(now)
        s.db.execute("insert or replace into ag_float(merchant, partner, balance, read_at) values(?,?,?,?)", (merchant, partner_id, bal, now))
        cur = s.db.execute("select currency from ag_requests where merchant=? and partner=? limit 1", (merchant, partner_id)).fetchone()
        from contract.tools.validate_contract import SAMPLE_CURRENCY
        s.cloud.event(merchant, "FloatBalanceRead", {"partner_id": partner_id, "balance": bal, "currency": cur[0] if cur else SAMPLE_CURRENCY, "read_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now))}, now=now)
        return bal
    def usual_daily_need(s, merchant, partner_id, days=7):
        r = s.db.execute("select coalesce(sum(amount),0), count(distinct day) from ag_requests where merchant=? and partner=? and state='confirmed' and service!='cash_deposit'", (merchant, partner_id)).fetchone()
        return r[0] // max(r[1], 1)
    def low_float(s, merchant, partner_id, balance=None):
        bal = s.partners[partner_id].float_balance(merchant) if balance is None else balance
        need = s.usual_daily_need(merchant, partner_id)
        return need > 0 and bal < need * LOW_FLOAT_RATIO
    def float_forecast(s, merchant, partner_id):
        """Days of float left at the usual pace (an estimate, labelled so on screen)."""
        need, bal = s.usual_daily_need(merchant, partner_id), s.partners[partner_id].float_balance(merchant)
        return None if need == 0 else bal / need
    # ---- cash checks (day start, day end, handover): a difference is flagged for the owner and never blocks
    def handle_cash_count(s, merchant, evt, now=None):
        p = evt["payload"]; diff = p["counted_cash"] - p["expected_cash"]
        s.db.execute("insert or ignore into ag_cash(merchant, count_id, difference, kind, at) values(?,?,?,?,?)", (merchant, p["count_id"], diff, p["kind"], _now(now)))
        if diff != 0:
            s.cloud.event(merchant, "CashDifferenceFlagged", {"count_id": p["count_id"], "difference": diff, "currency": p["currency"]}, now=now, causes=[evt["event_id"]])
        return diff
    def cash_differences(s, merchant): return [{"count_id": r[0], "difference": r[1], "kind": r[2]} for r in s.db.execute("select count_id, difference, kind from ag_cash where merchant=? and difference!=0 order by at", (merchant,))]
    # ---- commissions and the partner statement check (S12)
    def commissions(s, merchant, partner_id=None, period=None):
        q, a = "select partner, day, sum(commission), count(*) from ag_requests where merchant=? and state='confirmed'", [merchant]
        if partner_id: q += " and partner=?"; a.append(partner_id)
        if period: q += " and day like ?"; a.append(period + "%")
        return [{"partner_id": r[0], "day": r[1], "commission": r[2], "count": r[3]} for r in s.db.execute(q + " group by partner, day order by day", a)]
    def match_statement(s, merchant, partner_id, period, rows=None, now=None):
        """Match what the partner reports against what the cloud recorded. Every mismatch is its own flag for the owner."""
        rows = s.partners[partner_id].statement(period) if rows is None else rows
        sid, matched, total, mismatches = uuid7(), 0, 0, []
        ours = {r[0]: r[1] for r in s.db.execute("select request_id, commission from ag_requests where merchant=? and partner=? and state='confirmed' and day like ?", (merchant, partner_id, period + "%"))}
        cur = s.db.execute("select currency from ag_requests where merchant=? and partner=? limit 1", (merchant, partner_id)).fetchone()
        from contract.tools.validate_contract import SAMPLE_CURRENCY
        currency = cur[0] if cur else SAMPLE_CURRENCY
        for r in rows:
            exp = ours.get(r["request_id"])
            if exp == r["commission"]: matched += 1; total += r["commission"]
            else:
                mismatches.append(r["request_id"])
                pl = {"mismatch_id": uuid7(), "statement_id": sid, "expected": exp or 0, "reported": r["commission"], "currency": currency}
                if exp is not None: pl["request_id"] = r["request_id"]
                s.cloud.event(merchant, "CommissionMismatchFlagged", pl, now=now)
        for rid in set(ours) - {r["request_id"] for r in rows}:   # we recorded it, the partner did not report it
            mismatches.append(rid)
            s.cloud.event(merchant, "CommissionMismatchFlagged", {"mismatch_id": uuid7(), "statement_id": sid, "request_id": rid, "expected": ours[rid], "reported": 0, "currency": currency}, now=now)
        s.cloud.event(merchant, "PartnerStatementMatched", {"statement_id": sid, "partner_id": partner_id, "period": period, "matched_count": matched, "total": total, "currency": currency}, now=now)
        return {"statement_id": sid, "matched": matched, "total": total, "mismatches": mismatches}
    # ---- collection point and partner finance (referrals): the partner holds the money and decides
    def record_collection(s, merchant, partner_id, kind, amount, currency, request_id=None, now=None):
        if kind not in COLLECTION_KINDS: raise ValueError("unknown collection kind")
        cid = uuid7()
        s.cloud.event(merchant, "CollectionRecorded", {"collection_id": cid, "request_id": request_id or uuid7(), "partner_id": partner_id, "kind": kind, "amount": amount, "currency": currency}, now=now)
        return cid
    def refer(s, merchant, partner_id, product, fee, currency, now=None):
        """A customer was referred to a licensed partner's savings, loan, pay-later or insurance product; the partner decides and pays the fee."""
        if product not in FINANCE_PRODUCTS: raise ValueError("unknown partner finance product")
        rid = uuid7()
        s.cloud.event(merchant, "PartnerReferralRecorded", {"referral_id": rid, "partner_id": partner_id, "product": product, "fee": fee, "currency": currency}, now=now)
        return rid
    # ---- home screen numbers (read live from the partner; never a LynkOmni balance)
    def home(s, merchant, day):
        floats = {pid: s.partners[pid].float_balance(merchant) for pid in s.approved.get(merchant, set()) if pid in s.partners}
        today = s.db.execute("select count(*), coalesce(sum(commission),0) from ag_requests where merchant=? and day=? and state='confirmed'", (merchant, day)).fetchone()
        return {"float_per_partner": floats, "today_count": today[0], "today_commission": today[1], "low_float": [pid for pid, b in floats.items() if s.low_float(merchant, pid, b)], "services": list(SERVICES)}
