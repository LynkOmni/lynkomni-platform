#!/usr/bin/env python3
"""LynkAcc and LynkInv settings in every country pack (OFFICE UPDATE, owner 2026-11-18, master blueprint 66; section 4 step D2a).
Rule 0.5: a country adds only data. Nothing is invented: every value starts unknown and unconfirmed until a local lawyer and
accountant confirm it (ledger item office_country_rules). While a value is unknown the safe default in catalog/invoices.v1.json
and catalog/books.v1.json applies:

  office.late_fees.allowed            whether late fees or interest may be charged (unknown: never charged)
  office.late_fees.max_rate_bp_year   the most interest the law allows per year, in basis points
  office.late_fees.fixed_fee_minor    a fixed fee the law allows per late invoice
  office.e_invoice.required           whether invoices must be sent in a set digital format or through the tax office
  office.e_invoice.format             that format's name (a code constant, never translated)
  office.keep_years                   how long invoices and books are kept (unknown: 10 years)
  office.mileage_rate_minor           the allowed rate per kilometre in the pack's currency (unknown: the owner sets it)
  office.daily_allowance_minor        the allowed daily allowance (unknown: the owner sets it)
  office.stock_methods                the stock costing methods allowed (unknown: FIFO and average)
  office.depreciation_methods         the loss-of-value methods allowed (unknown: straight line and reducing balance)
  office.buyer_issued_invoices        whether a buyer may issue the invoice for the seller (unknown: no)
  office.reverse_charge               whether the buyer accounts for the tax on some supplies (unknown: no)
  office.crm.request_days             days to answer a person's data request (unknown: 30)
  office.crm.data_region              where customer records must be stored (unknown: the account's region)
  office.crm.keep_years               how long customer records are kept after the relationship ends (unknown: as short as the law allows)
  office.crm.sensitive_allowed        whether health, children or citizens records are allowed (unknown: no, except a school's students
                                      and a public body's cases)

  python3 tools/country_office.py          writes the field into every pack (keeps confirmed values)
  python3 tools/country_office.py --check  fails when a pack lacks it (tests/test_invoices.py)"""
import json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PACKS = os.path.join(ROOT, "contract", "country-packs")
DEFAULT = {"late_fees": {"allowed": None, "max_rate_bp_year": None, "fixed_fee_minor": None},
           "e_invoice": {"required": None, "format": None},
           "keep_years": None, "mileage_rate_minor": None, "daily_allowance_minor": None,
           "stock_methods": None, "depreciation_methods": None, "buyer_issued_invoices": None, "reverse_charge": None,
           "crm": {"request_days": None, "data_region": None, "keep_years": None, "sensitive_allowed": {"health": None, "children": None, "citizens": None}},
           "confirmed": False,
           "note": "Set per country after the lawyer and accountant review (ledger item office_country_rules); unknown until then, and the safe default applies."}


def _fill(have, default):
    """Adds any setting the pack does not have yet; a value already set (confirmed or not) is never replaced."""
    for k, v in default.items():
        if k not in have:
            have[k] = json.loads(json.dumps(v))
        elif isinstance(v, dict) and isinstance(have[k], dict):
            _fill(have[k], v)
    return have


def main(argv):
    names = sorted(n for n in os.listdir(PACKS) if n.endswith(".json"))
    if "--check" in argv:
        bad = [n for n in names if json.load(open(os.path.join(PACKS, n), encoding="utf-8")).get("office") != _fill(json.loads(json.dumps(json.load(open(os.path.join(PACKS, n), encoding="utf-8")).get("office") or {})), DEFAULT)]
        if bad:
            print(f"{len(bad)} packs lack office settings (run python3 tools/country_office.py)"); return 1
        print("every pack has its office settings"); return 0
    for n in names:
        path = os.path.join(PACKS, n)
        with open(path, encoding="utf-8") as f:
            p = json.load(f)
        p["office"] = _fill(p.get("office") or {}, DEFAULT)
        with open(path, "w", encoding="utf-8") as f:
            f.write(json.dumps(p, indent=1, ensure_ascii=False) + "\n")
    print(f"wrote office settings into {len(names)} packs"); return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
