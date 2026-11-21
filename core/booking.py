"""LynkBooking's money and figures for the office services (BOOKING UPDATE, owner locked 2026-11-18, master blueprint 64; section 4
step E4a). The commission rule is the locked services/billing.py BOOKING_COMMISSION, passed in by the caller.

This module is the Python reference; ts/src/booking.ts must agree on every case of contract/vectors/booking.v1.json
(python3 tools/booking_vectors.py after a change). Money is whole minor units; every split rounds half away from zero.

- commission: only on customers LynkBooking brought. Nothing on the business's own link, QR code, front desk or returning
  customers; appointments only on a new customer's first visit, capped; events a share plus a fixed amount per paid ticket and
  nothing on free events; tables a fixed amount per seated guest. Partner supply has no rate yet (None, a placeholder).
- busy_forecast: the average bookings for each weekday and hour over the weeks given, always labelled an estimate.
- empty_hours: the hours with room left, from what each hour can take and what was booked.
- no_show_rate: the share of confirmed bookings nobody came to, in basis points.
"""
from core.books import round_div

KINDS = ("appointment", "stay", "tour", "event", "cinema", "transport", "transfer", "rental", "space", "thing", "table", "class")
SOURCES = ("lynkbooking", "own_link", "qr", "front_desk", "returning", "partner")
OWN = ("own_link", "qr", "front_desk", "returning")
_RATE = {"stay": "stay_bps", "tour": "tour_bps", "transport": "transport_bps", "transfer": "transport_bps", "rental": "rental_and_space_bps",
         "space": "rental_and_space_bps", "thing": "rental_and_space_bps", "class": "class_bps"}


def commission(rules, kind, source, amount_minor, first_visit=False, guests=0, paid_tickets=0, fixed=None):
    """LynkOmni's commission on one booking, in minor units, or None where no rate exists yet (partner supply).
    fixed: the fixed amounts in this currency's minor units ({"cap", "ticket", "guest"}); by default the locked USD cents."""
    if kind not in KINDS or source not in SOURCES:
        raise ValueError("unknown booking kind or source")
    if isinstance(amount_minor, bool) or not isinstance(amount_minor, int) or amount_minor < 0:
        raise ValueError("an amount is whole minor units")
    if source in OWN:
        return round_div(amount_minor * rules["own_customers_bps"], 10000)          # 0% on the business's own customers
    if source == "partner":
        return None
    f = {"cap": rules["appointment_first_visit_cap_cents"], "ticket": rules["event_ticket_cents"], "guest": rules["table_guest_cents"], **(fixed or {})}
    if kind == "appointment":
        return min(round_div(amount_minor * rules["appointment_first_visit_bps"], 10000), f["cap"]) if first_visit else 0
    if kind in ("event", "cinema"):
        return 0 if amount_minor == 0 else round_div(amount_minor * rules["event_bps"], 10000) + paid_tickets * f["ticket"]
    if kind == "table":
        return guests * f["guest"]
    return round_div(amount_minor * rules[_RATE[kind]], 10000)


def busy_forecast(bookings, weeks):
    """bookings: [{"weekday": 0..6, "hour": 0..23}] over `weeks` weeks. Returns {"estimate": True, "slots": [[weekday, hour, average]]}
    for every slot that had a booking, sorted by weekday then hour; averages are whole bookings, rounded."""
    if not isinstance(weeks, int) or weeks < 1:
        raise ValueError("at least one week")
    count = {}
    for b in bookings:
        if not (0 <= b["weekday"] <= 6 and 0 <= b["hour"] <= 23):
            raise ValueError("a weekday is 0 to 6 and an hour 0 to 23")
        k = (b["weekday"], b["hour"])
        count[k] = count.get(k, 0) + 1
    return {"estimate": True, "slots": [[w, h, round_div(n, weeks)] for (w, h), n in sorted(count.items())]}


def empty_hours(capacity, booked):
    """capacity and booked: {"weekday-hour": number}. The hours with room left, with how much, sorted by the room left (most first)."""
    out = []
    for slot, cap in capacity.items():
        left = cap - booked.get(slot, 0)
        if left > 0:
            out.append([slot, left])
    return sorted(out, key=lambda x: (-x[1], x[0]))


def no_show_rate(confirmed, no_shows):
    """Basis points of confirmed bookings nobody came to; None when there were none."""
    if confirmed <= 0:
        return None
    if not 0 <= no_shows <= confirmed:
        raise ValueError("no-shows are between zero and the confirmed bookings")
    return round_div(no_shows * 10000, confirmed)
