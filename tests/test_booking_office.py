"""LynkBooking in the office services (BOOKING UPDATE, master blueprint 64.11; section 4 step E4a): core/booking.py and ts/src/booking.ts
with shared vectors, the country settings and services/booking_office.py on the events of contract version 14.

Money taken before the visit is held until the customer comes; refunds come out of what is held first; commission is only on
customers LynkBooking brought and posts as a provider fee; a deposit, a pass and a company's bookings become invoices without
adding tax twice, each booking invoiced once; a confirmed booking reaches the customer's LynkCRM timeline; the forecast is an
estimate; every country pack carries its booking settings, unknown until confirmed."""
import json, os, subprocess, sys, unittest

from core import booking as K
from services.billing import BOOKING_COMMISSION as R

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLACE = "8b1f6c2e-1111-4222-8333-944455556666"


class Rules(unittest.TestCase):
    def test_vectors_country_settings_and_the_typescript_rule_are_current(self):
        for tool in ("booking_vectors.py", "country_booking.py"):
            r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", tool), "--check"], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_commission_follows_the_locked_rule(self):
        self.assertEqual(K.commission(R, "stay", "own_link", 100000), 0, "nothing on the business's own customers")
        self.assertEqual(K.commission(R, "stay", "lynkbooking", 100000), 8000)
        self.assertEqual(K.commission(R, "appointment", "lynkbooking", 20000, first_visit=True), 500, "5% capped at $5")
        self.assertEqual(K.commission(R, "appointment", "lynkbooking", 20000), 0, "only a new customer's first visit")
        self.assertEqual(K.commission(R, "event", "lynkbooking", 10000, paid_tickets=4), 300)
        self.assertEqual(K.commission(R, "event", "lynkbooking", 0, paid_tickets=4), 0, "free events are free")
        self.assertEqual(K.commission(R, "table", "lynkbooking", 0, guests=6), 150)
        self.assertIsNone(K.commission(R, "stay", "partner", 100000), "partner supply rates stay placeholders")


class Office(unittest.TestCase):
    def setUp(self):
        from services.platform import Platform
        self.p = Platform(); self.p.register("m1", "US"); self.b = self.p.booking_office

    def ev(self, type_, **payload):
        self.p.c.store.append("m1", "server", type_, payload)

    def confirm(self, bid, total, source="lynkbooking", kind="stay", starts="2026-12-07T09:00:00Z", **kw):
        self.ev("BookingConfirmed", booking_id=bid, kind=kind, place_id=PLACE, starts_at=starts, minutes=60, guests=kw.pop("guests", 1),
                source=source, total=total, currency="USD", **kw)

    def balances(self):
        tb = {}
        for e in self.p.c.store.of("m1", "journal.posted"):
            for acct, dr, cr in e["payload"]["lines"]:
                tb[acct] = tb.get(acct, 0) + dr - cr
        return {k: v for k, v in tb.items() if v}

    def test_money_is_held_until_the_customer_comes(self):
        self.confirm("b1", 30000)
        self.ev("BookingPaid", booking_id="b1", part="deposit", amount=10000, currency="USD", provider_reference="p1")
        self.assertEqual(self.balances(), {"1010": 10000, "2500": -10000})
        self.ev("BookingCheckedIn", booking_id="b1")
        self.ev("BookingPaid", booking_id="b1", part="balance", amount=20000, currency="USD", provider_reference="p2")
        self.assertEqual(self.balances(), {"1010": 30000, "4000": -30000})

    def test_fees_refunds_and_commission(self):
        self.confirm("b2", 30000)
        self.ev("BookingPaid", booking_id="b2", part="full", amount=30000, currency="USD", provider_reference="p3")
        self.ev("BookingCancelled", booking_id="b2", by="customer", fee=5000, currency="USD")
        self.ev("BookingRefunded", booking_id="b2", amount=25000, currency="USD", provider_reference="p4")
        self.assertEqual(self.balances(), {"1010": 5000, "4000": -5000})
        self.assertEqual(self.b.record_commission("m1", "b2"), 2400)
        self.assertEqual(self.b.record_commission("m1", "b2"), 2400, "written once")
        self.assertEqual(self.balances(), {"1010": 2600, "4000": -5000, "6100": 2400})
        self.confirm("b3", 30000, source="returning")
        self.assertEqual(self.b.record_commission("m1", "b3"), 0)
        self.assertEqual(len(self.p.c.store.of("m1", "BookingCommissionRecorded")), 1)

    def test_a_refund_beyond_what_is_held_is_a_refund_expense(self):
        self.confirm("b4", 8000)
        self.ev("BookingPaid", booking_id="b4", part="full", amount=8000, currency="USD", provider_reference="p5")
        self.ev("BookingCheckedIn", booking_id="b4")
        self.ev("BookingRefunded", booking_id="b4", amount=3000, currency="USD", provider_reference="p6")
        self.assertEqual(self.balances(), {"1010": 5000, "4000": -8000, "6400": 3000})

    def test_invoices_for_deposits_passes_and_company_bookings(self):
        self.confirm("b5", 12000)
        got = self.b.deposit_invoice("m1", "b5", "cust-1", 3000)
        self.assertEqual(got["invoice"]["total_minor"], 3000, "the price already holds the tax")
        self.assertIsNone(got["pay_link"]); self.assertEqual(got["pay"]["message"], "Coming to your country soon.")
        with self.assertRaises(ValueError):
            self.b.deposit_invoice("m1", "b5", "cust-1", 3000)
        self.assertEqual(self.b.pass_invoice("m1", "cust-2", "Ten classes", 9000, 10)["total_minor"], 9000)
        for i, day in enumerate(("2026-12-01", "2026-12-15", "2027-01-02")):
            self.confirm(f"c{i}", 5000, source="own_link", starts=f"{day}T10:00:00Z", company=True, customer_id="corp")
        inv = self.b.company_invoice("m1", "corp-billing", "corp", "2026-12-01", "2027-01-01")
        self.assertEqual(inv["total_minor"], 10000)
        self.assertIsNone(self.b.company_invoice("m1", "corp-billing", "corp", "2026-12-01", "2027-01-01"), "each booking only once")

    def test_a_confirmed_booking_reaches_the_customers_timeline(self):
        rid = self.p.crm.create("m1", "owner", "customer", name="Amina")
        self.confirm("b6", 4000, customer_id=rid)
        self.assertIn("b6", [i["id"] for i in self.p.crm.recs[rid]["timeline"] if i["source"] == "bookings"])

    def test_the_figures_for_lynkstat(self):
        for i, (day, hour) in enumerate((("07", "09"), ("14", "09"), ("08", "10"))):
            self.confirm(f"f{i}", 1000, starts=f"2026-12-{day}T{hour}:00:00Z")
        self.ev("BookingNoShow", booking_id="f2", fee=0, currency="USD")
        f = self.b.busy_forecast("m1", 2)
        self.assertTrue(f["estimate"])
        self.assertEqual(f["slots"], [[0, 9, 1], [1, 10, 1]])
        self.assertEqual(self.b.empty_hours("m1", {"0-9": 3, "1-10": 1}), [["0-9", 1]])
        self.assertEqual(self.b.no_show_rate("m1"), 3333)

    def test_another_currency_waits_for_its_fixed_amounts(self):
        from services.platform import Platform
        p = Platform(); p.register("m2", "RW")
        p.c.store.append("m2", "server", "BookingConfirmed", {"booking_id": "t1", "kind": "table", "place_id": PLACE, "starts_at": "2026-12-07T19:00:00Z",
                                                                "minutes": 90, "guests": 4, "source": "lynkbooking", "total": 40000, "currency": "RWF"})
        self.assertIsNone(p.booking_office.record_commission("m2", "t1"))
        self.assertEqual(p.c.store.of("m2", "BookingCommissionRecorded"), [])


if __name__ == "__main__":
    unittest.main()
