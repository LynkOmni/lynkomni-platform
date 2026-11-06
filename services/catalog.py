"""Sub-core service categories (extra revenue): Booking & Ticketing, and Utility, Payments & Connectivity.
LynkOmni is the distribution layer: providers own inventory and fulfilment, licensed partners handle money and credit.
All providers here are SANDBOX simulators. Every sub-service is OFF per country until its provider and licence exist."""
import time, uuid
from core.regions import country, enabled
from services.suite import ServiceOff

CATEGORIES = {"booking": "Booking & Ticketing", "utility": "Utility, Payments & Connectivity"}
# id: (category, name, provider type, what must exist before it goes live)
SUBS = {
 "flights": ("booking", "Flight Booking", "airline or aggregator", "aggregator agreement, refund and cancellation rules"),
 "bus": ("booking", "Bus & Coach Tickets", "bus operators", "operator agreements, seat inventory feed"),
 "train": ("booking", "Train Tickets", "rail operator", "operator agreement, where rail exists"),
 "hotel": ("booking", "Hotel & Accommodation", "hotel aggregator", "aggregator agreement, cancellation rules"),
 "events": ("booking", "Event Tickets", "organizers or ticketing platform", "organizer agreements, ticket anti-fraud"),
 "cinema": ("booking", "Cinema Tickets", "cinema chains", "chain agreements, seat maps"),
 "ferry": ("booking", "Ferry & Boat Tickets", "water transport operators", "operator agreements"),
 "car_rental": ("booking", "Car Rental", "rental companies", "company agreements, insurance and deposit rules"),
 "local_transport": ("booking", "Local Transport", "taxi and shuttle partners", "partner agreements"),
 "alt_accommodation": ("booking", "Alternative Accommodation", "alternative accommodation platforms or property managers", "platform or property-manager agreements, host verification, cancellation and refund rules"),
 "appointments": ("booking", "Appointment Booking", "participating service providers", "provider onboarding, reminders"),
 "utility_bills": ("utility", "Utility Bills", "utilities or bill aggregator", "utility or aggregator agreement, payment partner"),
 "internet": ("utility", "Internet & Broadband", "ISPs", "ISP agreements, payment partner"),
 "airtime": ("utility", "Mobile Airtime & Credit", "operators or airtime aggregator", "operator or aggregator agreement"),
 "data_bundles": ("utility", "Mobile Data Bundles", "operators or aggregator", "operator or aggregator agreement"),
 "esim": ("utility", "eSIM Purchase", "eSIM aggregator", "aggregator agreement, device compatibility checks"),
 "intl_esim": ("utility", "International eSIM Plans", "eSIM aggregator", "aggregator agreement, travel-plan catalog"),
 "tv_streaming": ("utility", "TV & Streaming Subscriptions", "TV and streaming providers", "provider agreements"),
 "school_fees": ("utility", "School & Education Payments", "schools or education bodies", "school or ministry integration, reconciliation"),
 "insurance_payments": ("utility", "Insurance Payments", "licensed insurers", "licensed insurer agreement, premium-collection rules"),
 "vouchers": ("utility", "Digital Vouchers & Gift Cards", "voucher issuers", "issuer agreements, fraud controls"),
 "merchant_payments": ("utility", "Merchant Payments", "payment providers", "licensed payment provider (service 1)"),
 "credit_services": ("utility", "Credit Services", "licensed lenders", "licensed lender decides; LynkOmni only facilitates"),
 "currency_exchange": ("utility", "Currency Exchange", "licensed FX provider or bureau", "licensed partner, rate and fee transparency, limits, identity checks"),
 "crypto_exchange": ("utility", "Crypto Exchange", "licensed crypto exchange", "country allows it, licensed partner, risk disclosure, consent. Referral only: no trading or custody by LynkOmni"),
}
TERMS_REQUIRED = {"insurance_payments", "credit_services", "currency_exchange", "crypto_exchange"}   # each has its own terms and disclosures, per country
STEPUP_REQUIRED = {"currency_exchange", "crypto_exchange", "credit_services"}                  # extra verification for sensitive actions
REFERRAL_ONLY = {"credit_services", "crypto_exchange"}  # a licensed partner provides these; LynkOmni only refers

class SandboxProvider:
    """Stands in for a real provider. Replace with an adapter that calls the real API."""
    def __init__(s, name="sandbox", fail_fulfil=False, commission_bps=150, cancel_hours=24):
        s.name, s.fail_fulfil, s.commission_bps, s.cancel_hours = name, fail_fulfil, commission_bps, cancel_hours  # bps are PLACEHOLDERS
    def quote(s, sub, currency, fx, params):
        return {"quote_id": uuid.uuid4().hex, "sub": sub, "provider": s.name, "currency": currency,
                "price_minor": fx.convert(500, "USD", currency), "commission_bps": s.commission_bps, "params": params}
    def fulfil(s, quote, order_id):
        return {"ok": False} if s.fail_fulfil else {"ok": True, "item": {"kind": quote["sub"], "code": f"{quote['sub'].upper()}-{order_id[:8]}"}}

class ServiceCatalog:
    AGENT_SHARE_BPS = 3000  # share of the commission paid to the merchant who sold it (PLACEHOLDER)
    def __init__(s, c, payments, rights, control=None, provider=None):
        s.c, s.pay, s.rights, s.control, s.provider = c, payments, rights, control, provider or SandboxProvider()
    SPREAD_BPS = 100  # PLACEHOLDER exchange spread
    identity = None   # set by the platform: when present, sensitive services need a valid step-up token
    def accept_terms(s, m, sub, version="v1"):
        s.c.store.append(m, "server", "terms.accepted", {"sub": sub, "version": version, "country": s.c.profile(m)["country"]})
    def _checks(s, m, sub, stepup):
        if sub in TERMS_REQUIRED and not any(e["payload"]["sub"] == sub and e["payload"]["country"] == s.c.profile(m)["country"] for e in s.c.store.of(m, "terms.accepted")):
            raise PermissionError("accept the terms and disclosures for this service in your country first")
        if sub in STEPUP_REQUIRED and s.identity is not None and not s.identity.stepup_valid(stepup, m):
            raise PermissionError("extra verification is required for this action")
    def _gate(s, m, sub):
        if sub in country(s.c.profile(m)["country"]).get("blocked_services", ()):  # legal can block a service per country
            raise ServiceOff(f"{sub} is blocked in this country")
        s.c.gate(m, "svc_" + sub)
    def available(s, code): return [k for k in SUBS if enabled(code, "svc_" + k) and k not in country(code).get("blocked_services", ())]
    def search(s, m, sub, **params):
        s._gate(m, sub)
        return [s.provider.quote(sub, s.c.profile(m)["currency"], s.c.fx, params)]
    def buy(s, m, sub, quote, method, key, agent=None, stepup=None):
        s._gate(m, sub)
        if sub in REFERRAL_ONLY:
            raise ValueError("this service is referral only: a licensed partner provides it")
        s._checks(m, sub, stepup)
        if time.time() > quote.get("expires", float("inf")):
            raise PermissionError("quote expired: request a new rate")
        pay = s.pay.charge(m, quote["price_minor"], method, key)
        if not pay["ok"]:
            s.c.store.append(m, "server", "service.failed", {"order_id": key, "sub": sub, "stage": "payment"})
            return {"ok": False, "stage": "payment", **pay}
        res = s.provider.fulfil(quote, key)
        if not res["ok"]:  # paid but not delivered: the money is owed back
            s.c.store.append(m, "server", "service.refund_due", {"order_id": key, "amount_minor": quote["price_minor"], "reason": "fulfilment failed"})
            return {"ok": False, "stage": "fulfilment", "refund_due": True}
        s.c.store.append(m, "server", "service.fulfilled", {"order_id": key, "sub": sub, "price_minor": quote["price_minor"],
                         "currency": quote["currency"], "item": res["item"], "provider": quote["provider"],
                         "cancel_until": time.time() + s.provider.cancel_hours * 3600})
        fee = quote["price_minor"] * quote["commission_bps"] // 10000
        agent_cut = fee * s.AGENT_SHARE_BPS // 10000 if agent else 0
        if agent_cut:
            s.c.store.append(agent, "server", "commission.earned", {"order_id": key, "amount_minor": agent_cut, "currency": quote["currency"]})
        if s.control:
            s.control.record_revenue(agent or m, "service_commission", fee - agent_cut, quote["currency"], s.c.profile(m)["country"])
        return {"ok": True, "order_id": key, "item": res["item"], "commission_minor": fee}
    def my_items(s, m):  # tickets, eSIM codes and vouchers: cached on the phone so they open offline
        return [e["payload"] for e in s.c.store.of(m, "service.fulfilled")]
    def cancel(s, m, order_id):
        o = next((e["payload"] for e in s.c.store.of(m, "service.fulfilled") if e["payload"]["order_id"] == order_id), None)
        if o is None or any(e["payload"]["order_id"] == order_id for e in s.c.store.of(m, "service.cancelled")):
            raise ValueError("unknown or already cancelled order")
        if time.time() > o["cancel_until"]:
            raise PermissionError("outside the provider's cancellation window")
        s.c.store.append(m, "server", "service.cancelled", {"order_id": order_id})
        s.c.store.append(m, "server", "service.refund_due", {"order_id": order_id, "amount_minor": o["price_minor"], "reason": "cancelled"})
    def apply_credit(s, m, lender, amount_minor, stepup=None):
        s.c.gate(m, "svc_credit_services"); s._checks(m, "credit_services", stepup)
        if not s.rights.has_consent(m, lender):
            raise PermissionError("no merchant consent to share data with this lender")
        s.c.store.append(m, "server", "credit.application", {"lender": lender, "amount_minor": amount_minor})
        return {"status": "submitted_to_lender", "decision": "by the lender"}  # LynkOmni never decides
    def exchange_quote(s, m, to_currency, amount_minor):
        """Indicative quote from a licensed partner: rate, spread and amount received are always shown. Valid 60 seconds."""
        s._gate(m, "currency_exchange")
        cur = s.c.profile(m)["currency"]
        mid = s.c.fx.convert(amount_minor, cur, to_currency)
        return {"quote_id": uuid.uuid4().hex, "sub": "currency_exchange", "provider": s.provider.name, "currency": cur,
                "price_minor": amount_minor, "commission_bps": s.provider.commission_bps, "to_currency": to_currency,
                "receive_minor": mid - mid * s.SPREAD_BPS // 10000, "spread_bps": s.SPREAD_BPS, "expires": time.time() + 60}
    def refer_crypto(s, m, partner, risk_acknowledged=False, stepup=None):
        """Referral to a licensed exchange. LynkOmni does not trade, hold or promise prices."""
        s._gate(m, "crypto_exchange"); s._checks(m, "crypto_exchange", stepup)
        if not risk_acknowledged:
            raise ValueError("the risk disclosure must be acknowledged first")
        if not s.rights.has_consent(m, partner):
            raise PermissionError("no consent to share data with this exchange")
        s.c.store.append(m, "server", "risk.acknowledged", {"service": "crypto_exchange"})
        s.c.store.append(m, "server", "crypto.referral", {"partner": partner})
        return {"status": "referred_to_licensed_exchange", "custody": "none", "trading": "by the exchange"}
