"""Partners of LynkExchange (EXCHANGE UPDATE, owner approved 2026-11-18, master blueprint 65.7 and 65.8).

LynkExchange never holds money and never runs a market: every conversion and transfer goes through a licensed currency or
money-transfer partner per country, behind the ExchangePartner interface. "exchange" stays "Coming to your country soon."
until its partner is signed there (providers/registry.v1.json exchange_currency_partner).

Practice partner (blueprint 65.5, Practice mode): the sandbox answers with a fixed practice rate for each pair, clearly a sample,
and never moves money. It answers "pending" when an order is placed; paid, settled, failed and refunded are written only by the
cloud from the partner's answer. The partner checks identity, sets limits and alone decides a refusal.

Rules every adapter keeps: rates are fractions of whole numbers, never decimals; a payee or a sender is only a vault reference;
the full price (the partner's cost plus LynkOmni's part) is fixed for the quote's countdown and nothing else is added.
"""

# Practice rates: whole to-currency minor units per 100 from-currency minor units, for practice only (never shown as live).
PRACTICE = {("USD", "EUR"): (92, 100), ("EUR", "USD"): (108, 100), ("USD", "RWF"): (1350, 1), ("RWF", "USD"): (1, 1350),
            ("USD", "XAF"): (605, 1), ("XAF", "USD"): (1, 605), ("EUR", "XAF"): (656, 1), ("XAF", "EUR"): (1, 656),
            ("USD", "KES"): (129, 1), ("KES", "USD"): (1, 129), ("USD", "NGN"): (1550, 1), ("NGN", "USD"): (1, 1550)}


class ExchangePartner:
    def quote(self, from_currency, to_currency, amount):
        """{"rate": [num, den], "mid": [num, den], "seconds": how long the price holds}"""
        raise NotImplementedError

    def place(self, order_id, quote, payer_ref, payee_ref):
        raise NotImplementedError


class SandboxExchangePartner(ExchangePartner):
    """SANDBOX: the practice partner. A fixed practice rate a little below a practice mid-market rate; never moves money."""
    def quote(self, from_currency, to_currency, amount):
        pair = (from_currency, to_currency)
        if pair not in PRACTICE:
            return {"ok": False, "reason": "pair_not_in_practice"}
        num, den = PRACTICE[pair]
        return {"ok": True, "rate": [num * 995, den * 1000], "mid": [num, den], "seconds": 30, "practice": True, "status": "sandbox"}

    def place(self, order_id, quote, payer_ref, payee_ref=None):
        for ref in (payer_ref, payee_ref):
            if ref is not None and not (isinstance(ref, str) and ref.startswith("vault:")):
                return {"ok": False, "reason": "people_must_be_vault_references"}
        return {"ok": True, "order_id": order_id, "state": "pending", "practice": True, "status": "sandbox"}
