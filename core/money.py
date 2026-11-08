"""Money is integer minor units + currency code. Never use floats for money."""
import json, os
from decimal import Decimal, ROUND_HALF_EVEN

# Decimals per currency come from the contract's currency list (contract/currencies.v1.json), the one source shared by every language.
with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "contract", "currencies.v1.json"), encoding="utf-8") as _f:
    CURRENCIES = json.load(_f)["decimals"]
# PLACEHOLDER units per 1 USD. Replace with a live FX provider before real use.
USD_RATES = {"USD": "1", "RWF": "1450", "KES": "129", "UGX": "3700", "TZS": "2600",
             "NGN": "1500", "GHS": "12", "INR": "84", "AED": "3.6725", "EUR": "0.92"}

def to_minor(amount, cur):
    return int((Decimal(str(amount)) * Decimal(10) ** CURRENCIES[cur]).quantize(Decimal(1), ROUND_HALF_EVEN))

def fmt(minor, cur):
    d = CURRENCIES[cur]
    return f"{cur} {Decimal(minor) / Decimal(10) ** d:,.{d}f}"

class FX:
    """Swap `rates` for a live provider; the interface stays the same."""
    def __init__(self, rates=None):
        self.rates = {k: Decimal(v) for k, v in (rates or USD_RATES).items()}
    def convert(self, minor, src, dst):
        if src == dst:
            return minor
        usd = (Decimal(minor) / Decimal(10) ** CURRENCIES[src]) / self.rates[src]
        return to_minor(usd * self.rates[dst], dst)
