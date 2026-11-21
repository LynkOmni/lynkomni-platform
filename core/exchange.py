"""LynkExchange's price and book-value rules (EXCHANGE UPDATE, master blueprint 65; section 4 step E4b). The levels and each
tier's part are the locked services/billing.py EXCHANGE_LEVELS and FEATURES lynkexchange, passed in by the caller.

This module is the Python reference; ts/src/exchange.ts must agree on every case of contract/vectors/exchange.v1.json
(python3 tools/exchange_vectors.py after a change). Money is whole minor units and a rate is a fraction of whole numbers
(to-currency minor units per from-currency minor unit), never a decimal.

- part_bps: LynkOmni's part, the lower of the tier's part and the level reached by the last 30 days' volume.
- quote: one full price. The customer pays `amount`; LynkOmni's part is taken first, then the partner's rate converts the rest,
  rounded down so the receiver is never promised more than arrives.
- above_mid_bps: how far the full price is from the mid-market rate, in basis points, so it can be shown beside it.
- cost_out: the book value of foreign money spent, at its average cost.
"""
from core.books import round_div


def level_bps(levels, volume_30d_minor):
    """The level's part for the last 30 days' volume (in USD cents): the last level whose start the volume reached."""
    if volume_30d_minor < 0:
        raise ValueError("a volume is never negative")
    bps = levels[0][1]
    for start, part in levels:
        if volume_30d_minor >= start:
            bps = part
    return bps


def part_bps(tier_bps, levels, volume_30d_minor):
    return min(tier_bps, level_bps(levels, volume_30d_minor))


def quote(amount, rate_num, rate_den, part):
    """{"part": LynkOmni's part in the from currency, "to_amount": what arrives}. amount and the rate are whole numbers."""
    for v in (amount, rate_num, rate_den, part):
        if isinstance(v, bool) or not isinstance(v, int):
            raise ValueError("whole numbers only")
    if amount <= 0 or rate_num <= 0 or rate_den <= 0 or not 0 <= part < 10000:
        raise ValueError("an amount and a rate are more than nothing, and a part is below 100%")
    fee = round_div(amount * part, 10000)
    return {"part": fee, "to_amount": (amount - fee) * rate_num // rate_den}


def above_mid_bps(amount, to_amount, mid_num, mid_den):
    """Basis points between what the mid-market rate would give and what arrives (0 or more), rounded."""
    at_mid = amount * mid_num // mid_den
    if at_mid <= 0:
        raise ValueError("the mid-market rate gives nothing for this amount")
    return max(0, round_div((at_mid - to_amount) * 10000, at_mid))


def cost_out(held, held_cost, spent):
    """The book value of `spent` foreign money out of `held` that cost `held_cost` in the book currency (average cost)."""
    if not 0 < spent <= held:
        raise ValueError("spend more than nothing and at most what is held")
    return held_cost if spent == held else round_div(held_cost * spent, held)
