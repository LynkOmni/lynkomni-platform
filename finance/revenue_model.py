"""Subscription revenue model (blueprint section 14, part E, table 1) and the LynkVCard subscription lines.

Reproduces the blueprint's figures from its stated assumptions, so a price change can be re-run instead of re-typed.
Revenue for a line = subscribers x price x regional price index, summed over Plus, Pro and Max. Everything that is not a
subscription price (payments, commerce, booking, utility, advertising, infrastructure, card interchange and so on) is
carried over from the blueprint as stated, because those lines do not depend on subscription prices.

Scenarios, not forecasts: the adoption shares are assumptions to be replaced with pilot data.
"""
from decimal import Decimal, ROUND_HALF_UP

from services import billing

STAGES = ("stage1", "stage2", "stage3")
# The three stages are sizes, never countries (Step 0, blueprint 42 A): proving ground, regional scale, global scale.
STAGE_NAMES = {"stage1": "proving_ground", "stage2": "regional_scale", "stage3": "global_scale"}
MERCHANTS = {"stage1": 3_000, "stage2": 100_000, "stage3": 2_000_000}
INDEX = {"stage1": Decimal("0.35"), "stage2": Decimal("0.40"), "stage3": Decimal("0.55")}
CONVERSION = {"stage1": Decimal("0.6"), "stage2": Decimal("0.9"), "stage3": Decimal("1.0")}
PAYMENT_SHARE = {"stage1": Decimal("0.10"), "stage2": Decimal("0.25"), "stage3": Decimal("0.30")}   # merchants using payments
CONSUMERS = {"stage1": 15_000, "stage2": 500_000, "stage3": 10_000_000}

# Adoption before the conversion factor, Plus / Pro / Max, in percent. Same in every stage.
SUITE = (8, 3, Decimal("0.5"))                      # of all merchants
PRODUCTS = {                                        # of all merchants (not already on LynkSuite)
    "lynkpos": (8, 3, Decimal("0.5")), "lynkacc": (5, 2, Decimal("0.3")), "lynkstock": (5, 2, Decimal("0.3")),
    "lynkstat": (4, Decimal("1.5"), Decimal("0.2")), "lynkrewards": (3, 1, Decimal("0.2")),
    "lynkgrow": (3, Decimal("1.5"), Decimal("0.3")), "lynkchat": (5, 2, Decimal("0.3")),
    # New on 2026-11-07 (ASSUMPTIONS, no pilot data): LynkAcc keeps LynkLedger's share; LynkInv, LynkCRM and the LynkOps tier below.
    "lynkinv": (4, Decimal("1.5"), Decimal("0.2")), "lynkcrm": (3, 1, Decimal("0.2")), "lynkops": (3, 1, Decimal("0.2")),
}
ADDONS = {                                          # of merchants using payments
    "lynkmpay": (8, 5, 2), "lynkrecover": (10, 5, 1), "lynkcheckout": (15, 6, 2),
}
ASSIST = (4, Decimal("1.5"), Decimal("0.3"))        # LynkAssist, of all merchants
# Consumer memberships, Plus / Pro / Max, of consumers (percent): Travel = LynkBooking, Connect = LynkEssential
TRAVEL = (Decimal("0.8"), Decimal("0.2"), Decimal("0.05"))
CONNECT = (Decimal("1.0"), Decimal("0.3"), Decimal("0.08"))
# LynkVCard subscribers at Stage 3 (Plus / Pro / Max), read back from the blueprint's card table at index 0.55
VCARD_STAGE3 = (28_000, 14_000, 3_000)

ORDER = ["lynksuite", "lynkpos", "lynkacc", "lynkinv", "lynkcrm", "lynkops", "lynkstock", "lynkstat", "lynkrewards", "lynkgrow", "lynkchat",
         "lynkmpay", "lynkrecover", "lynkcheckout", "lynkassist", "travel", "connect"]


def _r(x):
    return int(Decimal(x).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def prices(overrides=None):
    """Plus / Pro / Max USD prices per family from services/billing.py (or from `overrides`, for the old prices)."""
    p = {k: tuple(Decimal(str(x)) for x in v[3][1:]) for k, v in billing.FAMILIES.items()}
    p["travel"], p["connect"] = p["lynkbooking"], p["lynkessential"]
    p.update({k: tuple(Decimal(str(x)) for x in v) for k, v in (overrides or {}).items()})
    return p


def subscribers(stage):
    """Subscribers per family and tier, before the regional index. Fractions are kept (the blueprint does the same)."""
    m, conv, pay = Decimal(MERCHANTS[stage]), CONVERSION[stage], MERCHANTS[stage] * PAYMENT_SHARE[stage]
    pct = Decimal("0.01")
    out = {"lynksuite": tuple(m * Decimal(s) * pct * conv for s in SUITE)}
    for k, shares in PRODUCTS.items():
        out[k] = tuple(m * Decimal(s) * pct * conv for s in shares)
    for k, shares in ADDONS.items():
        out[k] = tuple(pay * Decimal(s) * pct * conv for s in shares)
    out["lynkassist"] = tuple(m * Decimal(s) * pct * conv for s in ASSIST)
    c = Decimal(CONSUMERS[stage])
    out["travel"] = tuple(c * s * pct * conv for s in TRAVEL)
    out["connect"] = tuple(c * s * pct * conv for s in CONNECT)
    return out


def line(family, stage, price_table):
    subs = subscribers(stage)[family]
    return _r(sum(n * p for n, p in zip(subs, price_table[family])) * INDEX[stage])


def messaging(stage):
    """About $1 per Chat subscriber (LynkSuite and LynkChat together), not scaled by the index."""
    s = subscribers(stage)
    return _r(sum(s["lynksuite"]) + sum(s["lynkchat"]))


def table(price_table=None):
    pt = price_table or prices()
    rows = {f: {st: line(f, st, pt) for st in STAGES} for f in ORDER}
    rows["messaging"] = {st: messaging(st) for st in STAGES}
    rows["subtotal"] = {st: sum(r[st] for r in rows.values()) for st in STAGES}
    return rows


def vcard_subscriptions(price_table=None):
    """LynkVCard Plus, Pro and Max subscription lines at Stage 3 (index 0.55) and their sum."""
    pt = price_table or prices()
    lines = [_r(n * p * INDEX["stage3"]) for n, p in zip(VCARD_STAGE3, pt["lynkvcard"])]
    return lines + [sum(lines)]


# ---- Totals ---------------------------------------------------------------------------------------------------
# The blueprint's totals before the 2026-11-06 price update (Stage 1, 2, 3). Only subscription prices changed, so the
# new totals are these plus the change in the subscription lines and in the LynkVCard subscription lines.
OLD_PRICES = {
    "lynksuite": (12, 35, 89), "lynkpos": (3, 10, 25), "lynkacc": (2, 6, 15), "lynkstock": (2, 6, 15),
    "lynkinv": (0, 0, 0), "lynkcrm": (0, 0, 0), "lynkops": (0, 0, 0),             # not in the original blueprint table: their whole line is new
    "lynkrewards": (2, 6, 15), "lynkstat": (2, 5, 12), "lynkgrow": (3, 9, 25), "lynkchat": (3, 8, 20),
    "lynkmpay": (4, 12, 30), "lynkrecover": (2, 5, 10), "lynkcheckout": (2, 5, 12), "lynkassist": (5, 12, 29),
    "lynkvcard": (3, 9, 25),
}
OLD_SUBTOTAL = {"stage1": 4_146, "stage2": 250_211, "stage3": 7_664_363}      # table 1 subtotal as printed
OLD_GRAND = {"stage1": 8_322, "stage2": 820_206, "stage3": 30_561_663}        # grand total per month as printed
OTHER_GROUPS = {                                                               # per month, not affected by subscription prices
    "payments": {"stage1": 1_270, "stage2": 121_000, "stage3": 3_993_000},
    "commerce": {"stage1": 1_654, "stage2": 189_720, "stage3": 6_918_000},
    "booking": {"stage1": 303, "stage2": 76_855, "stage3": 4_212_000},
    "utility": {"stage1": 301, "stage2": 76_342, "stage3": 4_198_800},
    "advertising": {"stage1": 512, "stage2": 76_111, "stage3": 2_639_312},
    "infrastructure": {"stage1": 135, "stage2": 16_300, "stage3": 269_000},
}
VCARD_OLD = {"stage1": OLD_GRAND["stage1"] - 4_146 - sum(g["stage1"] for g in OTHER_GROUPS.values()),
             "stage2": OLD_GRAND["stage2"] - OLD_SUBTOTAL["stage2"] - sum(g["stage2"] for g in OTHER_GROUPS.values()),
             "stage3": 667_188}


def _exact_subscription_total(stage, price_table):
    s = subscribers(stage)
    total = sum(sum(n * p for n, p in zip(s[f], price_table[f])) for f in ORDER) * INDEX[stage]
    return total + sum(s["lynksuite"]) + sum(s["lynkchat"])


def subscription_change(stage):
    """Change in the monthly subscription lines (table 1) from the old prices to the current ones."""
    return _exact_subscription_total(stage, prices()) - _exact_subscription_total(stage, prices(OLD_PRICES))


def vcard_change(stage):
    """LynkVCard subscription lines are itemised for Stage 3 only; Stages 1 and 2 keep their old value (the difference
    would be under $1,600 a month at Stage 2 and nothing at Stage 1)."""
    if stage != "stage3":
        return Decimal(0)
    new, old = vcard_subscriptions()[-1], vcard_subscriptions(prices({"lynkvcard": OLD_PRICES["lynkvcard"]}))[-1]
    return Decimal(new - old)


def totals():
    """New per-month subtotal of table 1, LynkVCard group and grand total, per stage."""
    out = {}
    for st in STAGES:
        sub = _r(OLD_SUBTOTAL[st] + subscription_change(st))
        vc = _r(VCARD_OLD[st] + vcard_change(st))
        out[st] = {"subscriptions": sub, "vcard": vc,
                   "grand": _r(OLD_GRAND[st] + subscription_change(st) + vcard_change(st))}
    return out


# ---- Year-by-year path (blueprint part G) -----------------------------------------------------------------------
import math

OLD_YEAR_END = {3: 117_900, 5: 4_530_000, 6: 13_505_000}      # monthly run-rate at year end, the blueprint's "about" figures
YEAR_MERCHANTS = {1: 500, 2: 3_000, 3: 20_000, 4: 100_000, 5: 400_000, 6: 1_000_000, 7: 2_000_000}


def _uplift(merchants, grand):
    """Relative change of the monthly total between old and new prices, interpolated between the stages along the
    logarithm of the merchant count (the same smooth movement the blueprint assumes between stages)."""
    r = {st: Decimal(grand[st]) / Decimal(OLD_GRAND[st]) for st in STAGES}
    points = [(MERCHANTS[st], r[st]) for st in STAGES]
    for (m0, r0), (m1, r1) in zip(points, points[1:]):
        if m0 <= merchants <= m1:
            w = Decimal(str((math.log(merchants) - math.log(m0)) / (math.log(m1) - math.log(m0))))
            return r0 + (r1 - r0) * w
    raise ValueError("merchant count outside the modelled range")


def _round_to(x, step):
    return int((Decimal(x) / step).quantize(Decimal("1"), rounding=ROUND_HALF_UP) * step)


def path():
    """Monthly revenue at each year end and revenue in the year, for years 1 to 7. Years 3, 5 and 6 are 'about'
    (the blueprint's own interpolated figures scaled by the change in the totals)."""
    grand = {st: totals()[st]["grand"] for st in STAGES}
    end = {1: Decimal(grand["stage1"]) * YEAR_MERCHANTS[1] / MERCHANTS["stage1"], 2: Decimal(grand["stage1"]),
           4: Decimal(grand["stage2"]), 7: Decimal(grand["stage3"])}
    steps = {3: 100, 5: 10_000, 6: 5_000}
    for y, old in OLD_YEAR_END.items():
        end[y] = Decimal(_round_to(Decimal(old) * _uplift(YEAR_MERCHANTS[y], grand), steps[y]))
    out, prev = {}, Decimal(0)
    for y in range(1, 8):
        in_year = (prev + end[y]) / 2 * 12
        out[y] = {"merchants": YEAR_MERCHANTS[y], "end": _r(end[y]), "year": _r(in_year) if y in (1, 2, 4, 7) else _round_to(in_year, 1000)}
        prev = end[y]
    return out


def summary():
    """Everything the blueprint prints from part E that moved with the prices."""
    t, p = totals(), path()
    g = {st: t[st]["grand"] for st in STAGES}
    groups = {}
    for st in STAGES:
        parts = {"subscriptions": t[st]["subscriptions"], "payments": OTHER_GROUPS["payments"][st],
                 "commerce": OTHER_GROUPS["commerce"][st], "booking": OTHER_GROUPS["booking"][st],
                 "utility": OTHER_GROUPS["utility"][st], "advertising": OTHER_GROUPS["advertising"][st],
                 "infrastructure": OTHER_GROUPS["infrastructure"][st], "vcard": t[st]["vcard"]}
        groups[st] = {k: round(100 * v / g[st]) for k, v in parts.items()}
    return {
        "monthly": g, "yearly": {st: g[st] * 12 for st in STAGES},
        "per_merchant": {st: round(Decimal(g[st]) / MERCHANTS[st], 2) for st in STAGES},
        "range": {st: (_r(Decimal(g[st]) / 2), _r(Decimal(g[st]) * Decimal("1.5"))) for st in STAGES},
        "groups": groups, "path": p, "cumulative": sum(v["year"] for v in p.values()),
    }


# ---- Whole-ecosystem total (review part 11, agreed 2026-11-07) -------------------------------------------------
# Streams the blueprint agreed but the model above did not count, plus the costs and discounts that go with them.
# EVERY rate below is an ASSUMPTION, labelled as such in the blueprint, until partner contracts or pilot data replace it.
ECO_ASSUMPTIONS = {
    "improvements_global": 24_825,                         # section 28 lines a month at global scale, scaled by merchants
    "agent_share": {"stage1": Decimal("0.05"), "stage2": Decimal("0.10"), "stage3": Decimal("0.15")},   # merchants running agent points
    "agent_services_per_day": 10, "agent_share_per_service": Decimal("0.02"),   # cash in and out, transfers, remittances,
                                                                                 # government, collections; airtime and bills are already in utilities
    "referral_rate": Decimal("0.005"), "referral_fee": 8,  # merchants a month referring one accepted partner product
    "ops_paid_share": Decimal("0.042"), "ops_new_monthly": Decimal("0.03"), "ops_setup_take": Decimal("0.30"), "ops_setup_fee": 99,
    "hardware_rate": Decimal("0.002"), "hardware_margin": 15,
    "yearly_share": Decimal("0.30"),                       # payers on yearly billing at 10 months' price
    "partner_cost_share": Decimal("0.03"),                 # accountant share (2%) plus refer-and-earn credits (1%) of subscriptions
    # Second review (2026-11-08), ASSUMPTIONS:
    "exchange_users": Decimal("0.01"), "exchange_volume": 200, "exchange_share": Decimal("0.005"),   # currency exchange through a licensed partner
    "new_services_global": 4_710_000,                      # the 14 new services N1 to N14 at global scale (blueprint 44 H), scaled by merchants
    "stat_new_monthly": Decimal("0.03"), "stat_setup_take": Decimal("0.30"), "stat_setup_fee": 99,   # LynkStat Setup (LynkOps Setup includes it)
}
ECO_ROWS = ("current_model", "improvements", "agent_commissions", "partner_referrals", "ops_setup", "hardware", "exchange_currency", "new_services",
            "stat_setup", "yearly_billing", "partner_costs")
V2_PRICES = {"lynkstat": (3, 7, 17), "lynkops": (12, 29, 79)}     # LynkDash and three-service LynkOps before price lock version 3


def ecosystem(stage):
    """Monthly USD per stream for one stage (whole dollars); the sum is the whole-ecosystem total."""
    a, m, t = ECO_ASSUMPTIONS, MERCHANTS[stage], totals()[stage]
    subs = Decimal(t["subscriptions"])
    rows = {
        "current_model": Decimal(t["grand"]),
        "improvements": Decimal(a["improvements_global"]) * m / MERCHANTS["stage3"],
        "agent_commissions": m * a["agent_share"][stage] * a["agent_services_per_day"] * 30 * a["agent_share_per_service"],
        "partner_referrals": m * a["referral_rate"] * a["referral_fee"],
        "ops_setup": m * a["ops_paid_share"] * CONVERSION[stage] * a["ops_new_monthly"] * a["ops_setup_take"] * a["ops_setup_fee"],
        "hardware": m * a["hardware_rate"] * a["hardware_margin"],
        "exchange_currency": CONSUMERS[stage] * a["exchange_users"] * a["exchange_volume"] * a["exchange_share"],
        "new_services": Decimal(a["new_services_global"]) * m / MERCHANTS["stage3"],
        "stat_setup": sum(subscribers(stage)["lynkstat"]) * a["stat_new_monthly"] * a["stat_setup_take"] * a["stat_setup_fee"],
        "yearly_billing": -subs * a["yearly_share"] * 2 / 12,
        "partner_costs": -subs * a["partner_cost_share"],
    }
    return {k: _r(v) for k, v in rows.items()}


def second_review_uplift(stage):
    """Monthly revenue the second review added (2026-11-08): LynkStat and LynkOps at price lock version 3, LynkStat Setup and the new services."""
    old, new = prices(V2_PRICES), prices()
    lift = sum(line(f, stage, new) - line(f, stage, old) for f in V2_PRICES)
    rows = ecosystem(stage)
    return lift + rows["stat_setup"] + rows["new_services"]


def ecosystem_totals():
    """Per stage: the total a day, a month and a year (a day = a month x 12 / 365), and per merchant a month."""
    out = {}
    for st in STAGES:
        month = sum(ecosystem(st).values())
        out[st] = {"day": _r(Decimal(month) * 12 / 365), "month": month, "year": month * 12,
                   "per_merchant": (Decimal(month) / MERCHANTS[st]).quantize(Decimal("0.01"))}
    return out


def ecosystem_path():
    """Years 1 to 7: the section 14 G path scaled by each stage's whole-ecosystem total (log-interpolated like _uplift)."""
    base, eco = path(), ecosystem_totals()
    ratio = [(MERCHANTS[st], Decimal(eco[st]["month"]) / Decimal(totals()[st]["grand"])) for st in STAGES]
    def up(n):
        if n <= ratio[0][0]: return ratio[0][1]
        for (m0, r0), (m1, r1) in zip(ratio, ratio[1:]):
            if m0 <= n <= m1:
                w = Decimal(str((math.log(n) - math.log(m0)) / (math.log(m1) - math.log(m0))))
                return r0 + (r1 - r0) * w
        raise ValueError("merchant count outside the modelled range")
    out, prev = {}, Decimal(0)
    for y in range(1, 8):
        end = Decimal(base[y]["end"]) * up(base[y]["merchants"])
        out[y] = {"merchants": base[y]["merchants"], "end_month": _r(end), "end_day": _r(end * 12 / 365), "year": _r((prev + end) / 2 * 12)}
        prev = end
    return out
