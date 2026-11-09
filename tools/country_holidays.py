#!/usr/bin/env python3
"""Public holidays in every country pack (rule 0.5: a country adds only data, holidays included), never typed by hand.

  python3 tools/country_holidays.py --holidays <path to the holidays package source>   writes the "holidays" field of every pack
  python3 tools/country_holidays.py --check                                            fails when a pack has no "holidays" field

Source: the open-source "holidays" package by the Vacanza team (MIT licence, https://github.com/vacanza/holidays), version
pinned below, which computes each country's public holidays from its laws (moving feasts included). Names are in English
where the package offers it. Dates are for this year and next; re-run at the start of each year. The field stays
"confirmed": false until a person in the country confirms it, and a country the package does not cover gets an empty list
(never a guess). Holidays inform schedules and reports only; they never block a sale.

Also writes the two other rule 0.5 fields that are the same shape everywhere until a person confirms a country:
  invoice_numbering  how printed invoice numbers run (services/invoicing.py): one sequential series per merchant series,
                     numbers reserved for offline use and left unused are voided with a reason, never reused
  legal_text         the legal wording a country requires on invoices and receipts: empty until the country's lawyer sets it
                     (ledger item country_legal_text); nothing legal is printed before then"""
import json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PACKS = os.path.join(ROOT, "contract", "country-packs")
VERSION = "0.84"
YEARS = (2026, 2027)

INVOICE_NUMBERING = {"series_per": "merchant", "sequential": True, "format": "{series}-{number}", "offline_blocks": True,
                     "unused_numbers": "voided_with_reason", "reuse": False, "confirmed": False,
                     "note": "services/invoicing.py rules; a country's tax authority may require more (for example a registered series). Set confirmed when a person checks the country."}
LEGAL_TEXT = {"invoice": None, "receipt": None, "confirmed": False,
              "note": "Set by the country's lawyer (ledger item country_legal_text). Until then nothing is printed as legal wording."}


def _calendar(code, hol):
    try:
        cls = hol.country_holidays(code, years=YEARS[0])
    except NotImplementedError:
        return {"source": None, "confirmed": False, "years": {str(y): {} for y in YEARS}, "note": "Not covered by the source yet; add when a person confirms the country's holidays."}
    lang = next((l for l in ("en_US", "en_GB", "en") if l in (getattr(cls, "supported_languages", ()) or ())), None)
    years = {}
    for y in YEARS:
        h = hol.country_holidays(code, years=y, language=lang) if lang else hol.country_holidays(code, years=y)
        years[str(y)] = {d.isoformat(): name for d, name in sorted(h.items())}
    return {"source": f"holidays {VERSION} (Vacanza team, MIT)", "names_in": "en" if lang else "the country's own language", "confirmed": False, "years": years}


def fields(code, hol):
    return {"holidays": _calendar(code, hol), "invoice_numbering": INVOICE_NUMBERING, "legal_text": LEGAL_TEXT}


def main(argv):
    names = sorted(f for f in os.listdir(PACKS) if f.endswith(".json"))
    if "--check" in argv:
        bad = [n for n in names if not all(k in json.load(open(os.path.join(PACKS, n), encoding="utf-8")) for k in ("holidays", "invoice_numbering", "legal_text"))]
        print("missing rule 0.5 fields: " + ", ".join(bad[:8]) if bad else f"every pack has holidays, invoice numbering and legal text ({len(names)})")
        return 1 if bad else 0
    src = argv[argv.index("--holidays") + 1]
    sys.path.insert(0, src)
    import holidays as hol
    if hol.__version__ != VERSION:
        print(f"holidays {VERSION} is pinned; found {hol.__version__}"); return 1
    for n in names:
        path = os.path.join(PACKS, n)
        with open(path, encoding="utf-8") as f: p = json.load(f)
        code = p["code"]
        p.update(fields(code, hol) if code != "XX" else {"holidays": {"source": None, "confirmed": False, "years": {str(y): {} for y in YEARS}, "note": "The sample country has no holidays."}, "invoice_numbering": INVOICE_NUMBERING, "legal_text": LEGAL_TEXT})
        with open(path, "w", encoding="utf-8") as f: f.write(json.dumps(p, indent=1, ensure_ascii=False) + "\n")
    print(f"wrote holidays, invoice numbering and legal text into {len(names)} packs"); return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
