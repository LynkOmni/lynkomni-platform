"""LynkBooking in the office services (BOOKING UPDATE, master blueprint 64.11; section 4 step E4a), on core/booking.py and the
events of contract version 14. It reads booking events (never another service's storage) and acts through each office service:

- LynkAcc: a payment taken before the visit is held as received in advance (2500) until the customer comes, then earned (4000); a
  payment after check-in is earned at once; a kept cancellation or no-show fee is earned; a refund comes out of what is still held,
  and anything beyond it is a refund expense (6400); LynkOmni's commission is a provider fee (6100) taken from the payout (1010).
- LynkInv: a deposit asked for as an invoice with its pay link; a pass or membership sold as an invoice; a company's bookings for a
  period on one invoice, each booking invoiced once.
- LynkCRM: a confirmed booking goes on the customer's timeline (source "bookings") when the business keeps a record for them.
- LynkStat: the busy-time forecast (always an estimate), the empty-hours report and the no-show rate.
- Commission: worked out with the locked rule only for customers LynkBooking brought; in another currency the fixed amounts come from
  the country pack's booking settings and nothing is recorded while they are unconfirmed.
"""
import time

from core import booking as K
from core.regions import country
from services.billing import BOOKING_COMMISSION
from services.improvements import Table

USES_FIXED = ("appointment", "event", "cinema", "table")
_TS = "%Y-%m-%dT%H:%M:%SZ"


class BookingOffice:
    def __init__(s, p, now=time.time):
        s.p, s.now = p, now
        s.bk = Table(p.c.store.db, "booking_office")
        p.c.store.observers.append(s._observe)

    # ---- the books -------------------------------------------------------------------------------------------------------------
    def _rec(s, m, bid):
        return s.bk.get(f"{m}|{bid}") or s.bk.put(f"{m}|{bid}", {"held": 0, "earned": 0, "checked_in": False}) or s.bk.get(f"{m}|{bid}")

    def _post(s, m, lines):
        lines = [l for l in lines if l[1] or l[2]]
        if lines:
            s.p.books._post_journal(m, "booking", lines, "lynkbooking")

    def _observe(s, m, type_, payload, at):
        if not type_.startswith("Booking"):
            return
        bid = payload.get("booking_id")
        r = s._rec(m, bid)
        if type_ == "BookingConfirmed":
            r.update({"kind": payload["kind"], "source": payload["source"], "total": payload["total"], "currency": payload["currency"],
                      "starts_at": payload["starts_at"], "guests": payload["guests"], "first_visit": bool(payload.get("first_visit")),
                      "company": bool(payload.get("company")), "customer": payload.get("customer_id"), "place": payload["place_id"], "confirmed": True})
            if payload.get("customer_id") and s.p.crm.recs.get(payload["customer_id"]):
                s.p.crm.add_activity(m, payload["customer_id"], "bookings", at, bid)
        elif type_ == "BookingPaid":
            a = payload["amount"]
            if r["checked_in"]:
                s._post(m, [("1010", a, 0), ("4000", 0, a)]); r["earned"] = r["earned"] + a
            else:
                s._post(m, [("1010", a, 0), ("2500", 0, a)]); r["held"] = r["held"] + a
        elif type_ == "BookingCheckedIn":
            s._post(m, [("2500", r["held"], 0), ("4000", 0, r["held"])])
            r.update({"earned": r["earned"] + r["held"], "held": 0, "checked_in": True})
        elif type_ in ("BookingCancelled", "BookingNoShow"):
            fee = min(payload["fee"], r["held"])
            s._post(m, [("2500", fee, 0), ("4000", 0, fee)])
            r.update({"earned": r["earned"] + fee, "held": r["held"] - fee, "ended": "cancelled" if type_ == "BookingCancelled" else "no_show"})
        elif type_ == "BookingRefunded":
            a = payload["amount"]
            from_held = min(a, r["held"])
            s._post(m, [("2500", from_held, 0), ("6400", a - from_held, 0), ("1010", 0, a)])
            r["held"] = r["held"] - from_held
        elif type_ == "BookingCommissionRecorded":
            s._post(m, [("6100", payload["amount"], 0), ("1010", 0, payload["amount"])])
            r["commission"] = payload["amount"]

    # ---- commission --------------------------------------------------------------------------------------------------------------
    def record_commission(s, m, bid, paid_tickets=0):
        """Cloud only: LynkOmni's commission on a booking LynkBooking brought, written once."""
        r = s._rec(m, bid)
        if not r.get("confirmed"):
            raise ValueError("no confirmed booking")
        if "commission" in r:
            return r["commission"]
        fixed = None
        if r["currency"] != "USD" and r["kind"] in USES_FIXED and r["source"] == "lynkbooking":
            fixed = ((country(s.p.c.profile(m)["country"]).get("booking") or {}).get("commission_fixed_minor") or {})
            if not all(isinstance(fixed.get(k), int) for k in ("cap", "ticket", "guest")):
                return None                                # waits for the country's fixed amounts to be confirmed
        amount = K.commission(BOOKING_COMMISSION, r["kind"], r["source"], r["total"], r["first_visit"], r["guests"], paid_tickets, fixed)
        if amount:
            s.p.c.store.append(m, "server", "BookingCommissionRecorded", {"booking_id": bid, "amount": amount, "currency": r["currency"]})
        else:
            r["commission"] = amount
        return amount

    # ---- invoices ------------------------------------------------------------------------------------------------------------------
    def deposit_invoice(s, m, bid, customer, amount_minor, label="Deposit"):
        r = s._rec(m, bid)
        if r.get("deposit_invoice"):
            raise ValueError("this booking already has its deposit invoice")
        if not 0 < amount_minor <= r.get("total", 0):
            raise ValueError("a deposit is more than nothing and at most the booking's total")
        inv = s.p.invoicing.issue(m, customer, [{"name": label, "qty_milli": 1000, "unit_minor": amount_minor}], due_days=0, included=True)
        r["deposit_invoice"] = inv["id"]
        from providers import availability
        pay = availability("paylinks", s.p.c.profile(m)["country"])
        link = s.p.invoicing.pay_link(m, inv["id"]) if pay["state"] == "available" else None    # otherwise "Coming to your country soon."
        return {"invoice": inv, "pay_link": link, "pay": pay}

    def pass_invoice(s, m, customer, name, price_minor, uses):
        if not isinstance(uses, int) or uses < 1:
            raise ValueError("a pass covers at least one visit")
        return s.p.invoicing.issue(m, customer, [{"name": f"{name} ({uses})", "qty_milli": 1000, "unit_minor": price_minor}], included=True)

    def company_invoice(s, m, customer, company_record, start, end):
        """One invoice for a company's bookings in the period (starts_at from start up to end); each booking only once."""
        rows = [(k.split("|", 1)[1], r) for k, r in s.bk.items() if k.startswith(m + "|") and r.get("company") and r.get("customer") == company_record
                and start <= r["starts_at"] < end and not r.get("invoiced") and not r.get("ended") == "cancelled"]
        if not rows:
            return None
        lines = [{"name": f"Booking {r['starts_at'][:16].replace('T', ' ')}", "qty_milli": 1000, "unit_minor": r["total"]} for _, r in sorted(rows, key=lambda x: x[1]["starts_at"])]
        inv = s.p.invoicing.issue(m, customer, lines, included=True)          # booking prices already hold the tax
        for bid, r in rows:
            r["invoiced"] = inv["id"]
        return inv

    # ---- figures for LynkStat ------------------------------------------------------------------------------------------------------
    def _mine(s, m, place=None):
        return [r for k, r in s.bk.items() if k.startswith(m + "|") and r.get("confirmed") and (place is None or r["place"] == place)]

    def busy_forecast(s, m, weeks, place=None):
        rows = []
        for r in s._mine(m, place):
            t = time.strptime(r["starts_at"], _TS)
            rows.append({"weekday": t.tm_wday, "hour": t.tm_hour})
        return K.busy_forecast(rows, weeks)

    def empty_hours(s, m, capacity, place=None):
        booked = {}
        for r in s._mine(m, place):
            if r.get("ended") == "cancelled":
                continue
            t = time.strptime(r["starts_at"], _TS)
            k = f"{t.tm_wday}-{t.tm_hour}"
            booked[k] = booked.get(k, 0) + 1
        return K.empty_hours(capacity, booked)

    def no_show_rate(s, m, place=None):
        rows = s._mine(m, place)
        return K.no_show_rate(len(rows), sum(1 for r in rows if r.get("ended") == "no_show"))
