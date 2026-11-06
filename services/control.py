"""Company Control Center (internal). Aggregates only: no raw merchant records. Online only.
Management view, not statutory accounts: reconcile monthly to bank and provider statements."""
import datetime as dt
from core.locale import FMT, local_dt

COMPANY = "_company"
ROLE_VIEWS = {"founder": {"revenue", "profit", "acquisition", "reliability", "volume", "alerts"},
              "finance": {"revenue", "profit", "volume"},
              "country_lead": {"revenue", "profit", "acquisition"},   # role string "country_lead:RW"
              "support": {"reliability"}}

class ControlCenter:
    MIN_GROUP = 3  # smaller country groups are hidden to protect merchant privacy
    def __init__(s, c): s.c = c
    def record_revenue(s, merchant, stream, amount_minor, currency, country_code, ts=None):
        s.c.store.append(COMPANY, "server", "revenue.earned", {"merchant": merchant, "stream": stream, "amount_minor": amount_minor,
                         "currency": currency, "country": country_code, "usd_minor": s.c.fx.convert(amount_minor, currency, "USD")}, ts=ts)
    def record_cost(s, category, amount_minor, currency, country_code=None, channel=None, ts=None):
        s.c.store.append(COMPANY, "server", "cost.recorded", {"category": category, "amount_minor": amount_minor, "currency": currency,
                         "country": country_code, "channel": channel, "usd_minor": s.c.fx.convert(amount_minor, currency, "USD")}, ts=ts)
    @staticmethod
    def _period(ts, period, code=None):
        d = local_dt(ts, code) if code else dt.datetime.strptime(ts, FMT)
        return d.strftime("%Y-%m-%d" if period == "day" else "%Y-%m")
    def revenue(s, by="country", period="month", country=None):
        agg = {}
        for e in s.c.store.of(COMPANY, "revenue.earned"):
            p = e["payload"]
            if country and p["country"] != country:
                continue
            r = agg.setdefault((p[by], s._period(e["ts"], period, p["country"] if by == "country" else None)), {"usd": 0, "m": set()})
            r["usd"] += p["usd_minor"]; r["m"].add(p["merchant"])
        rows = []
        for (g, per), r in sorted(agg.items()):
            hidden = by == "country" and len(r["m"]) < s.MIN_GROUP
            rows.append({"group": g, "period": per, "usd_minor": None if hidden else r["usd"], "merchants": len(r["m"]), "suppressed": hidden})
        return rows
    def pnl(s, period="month", country=None):
        rev, cost = {}, {}
        for typ, bucket in (("revenue.earned", rev), ("cost.recorded", cost)):
            for e in s.c.store.of(COMPANY, typ):
                p = e["payload"]
                if country and p.get("country") != country:
                    continue
                k = s._period(e["ts"], period)
                bucket[k] = bucket.get(k, 0) + p["usd_minor"]
        return [{"period": k, "revenue_usd_minor": rev.get(k, 0), "cost_usd_minor": cost.get(k, 0),
                 "profit_usd_minor": rev.get(k, 0) - cost.get(k, 0),
                 "margin_pct": round(100 * (rev.get(k, 0) - cost.get(k, 0)) / rev[k], 1) if rev.get(k) else None}
                for k in sorted(set(rev) | set(cost))]
    def funnel(s, now):
        registered = {e["merchant"] for e in s.c.store.all_of("merchant.registered")}
        sales = [e for e in s.c.store.all_of("sale.recorded") if e["merchant"] in registered]
        cutoff = (dt.datetime.strptime(now, FMT) - dt.timedelta(days=7)).strftime(FMT)
        paid = {e["payload"]["merchant"] for e in s.c.store.of(COMPANY, "revenue.earned") if e["payload"]["stream"].startswith("subscription")}
        return {"registered": len(registered), "activated": len({e["merchant"] for e in sales}),
                "weekly_active": len({e["merchant"] for e in sales if e["ts"] >= cutoff}), "paid": len(paid)}
    def cac(s):
        reg, cost = {}, {}
        for e in s.c.store.all_of("merchant.registered"):
            ch = e["payload"].get("channel")
            if ch:
                reg[ch] = reg.get(ch, 0) + 1
        for e in s.c.store.of(COMPANY, "cost.recorded"):
            ch = e["payload"].get("channel")
            if ch:
                cost[ch] = cost.get(ch, 0) + e["payload"]["usd_minor"]
        return {ch: {"registered": n, "cost_usd_minor": cost.get(ch, 0), "cac_usd_minor": cost.get(ch, 0) // n} for ch, n in reg.items()}
    def volume_vs_revenue(s):
        vol = sum(s.c.fx.convert(e["payload"]["amount_minor"], e["payload"]["currency"], "USD") for e in s.c.store.all_of("payment.settled"))
        fees = sum(e["payload"]["usd_minor"] for e in s.c.store.of(COMPANY, "revenue.earned") if e["payload"]["stream"] == "payment_fee")
        return {"payment_volume_usd_minor": vol, "payment_fee_revenue_usd_minor": fees}  # volume is never revenue
    def reliability(s):
        at = [e["payload"]["ok"] for e in s.c.store.all_of("payment.attempt")]
        return {"payment_attempts": len(at), "payment_success_rate": round(sum(at) / len(at), 3) if at else None}
    def alerts(s):
        out, r = [], s.reliability()
        if r["payment_success_rate"] is not None and r["payment_success_rate"] < 0.9:
            out.append({"alert": "payment_success_low", "value": r["payment_success_rate"]})
        for c in sorted({e["payload"].get("country") for e in s.c.store.of(COMPANY, "revenue.earned", "cost.recorded")} - {None}):
            p = s.pnl("month", c)
            if p and p[-1]["profit_usd_minor"] < 0:
                out.append({"alert": "negative_margin", "country": c, "period": p[-1]["period"]})
        return out
    def view(s, role, name, now=None, **kw):
        """Role-checked, audit-logged entry point. country_lead is limited to its own country."""
        base, _, scope = role.partition(":")
        if name not in ROLE_VIEWS.get(base, set()):
            raise PermissionError(f"{role} cannot view {name}")
        s.c.store.append(COMPANY, role, "audit.logged", {"view": name, "role": role})
        lead = {"country": scope} if base == "country_lead" else {}
        if name == "revenue": return s.revenue(**kw, **lead)
        if name == "profit": return s.pnl(**kw, **lead)
        if name == "acquisition": return {"funnel": s.funnel(now), "cac": s.cac()}
        if name == "reliability": return s.reliability()
        if name == "volume": return s.volume_vs_revenue()
        return s.alerts()
