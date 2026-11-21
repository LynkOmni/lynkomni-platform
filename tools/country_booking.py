#!/usr/bin/env python3
"""LynkBooking's settings in every country pack (BOOKING UPDATE, owner locked 2026-11-18, master blueprint 64; section 4 step E4a).
Rule 0.5: a country adds only data.

  booking.commission_fixed_minor   the fixed commission amounts in this country's currency, in whole minor units: cap (an
                                   appointment's cap), ticket (per paid event ticket) and guest (per seated restaurant guest).
                                   null until confirmed: in a currency other than USD, those commissions are not recorded meanwhile
  booking.tourist_tax              how a stay's tourist or city tax is charged (null: not yet confirmed; nothing is added meanwhile)
  booking.travel_seller_licence    whether selling partner travel needs a licence here (null: not yet confirmed; partner supply
                                   stays "Coming to your country soon." meanwhile)
  booking.deposit_max_bp           the most a deposit may be, as basis points of the total (null: no limit set by law known yet)
  booking.cancel_notice_hours_min  the shortest free-cancelling notice the law requires (null: the business's own rule applies)

Nothing is invented: every value starts unknown and unconfirmed (ledger item booking_country_rules).
  python3 tools/country_booking.py          writes the field into every pack (keeps confirmed values)
  python3 tools/country_booking.py --check  fails when a pack lacks it (tests/test_booking_office.py)"""
import json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PACKS = os.path.join(ROOT, "contract", "country-packs")
DEFAULT = {"commission_fixed_minor": {"cap": None, "ticket": None, "guest": None}, "tourist_tax": None, "travel_seller_licence": None,
           "deposit_max_bp": None, "cancel_notice_hours_min": None, "confirmed": False,
           "note": "Set per country after the lawyer and accountant review (ledger item booking_country_rules); unknown until then."}


def main(argv):
    names = sorted(n for n in os.listdir(PACKS) if n.endswith(".json"))
    if "--check" in argv:
        bad = [n for n in names if "booking" not in json.load(open(os.path.join(PACKS, n), encoding="utf-8"))]
        if bad:
            print(f"{len(bad)} packs lack booking settings (run python3 tools/country_booking.py)"); return 1
        print("every pack has its booking settings"); return 0
    for n in names:
        path = os.path.join(PACKS, n)
        with open(path, encoding="utf-8") as f: p = json.load(f)
        if "booking" not in p:
            p["booking"] = json.loads(json.dumps(DEFAULT))
        with open(path, "w", encoding="utf-8") as f: f.write(json.dumps(p, indent=1, ensure_ascii=False) + "\n")
    print(f"wrote booking settings into {len(names)} packs"); return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
