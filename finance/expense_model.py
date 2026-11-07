"""Expenses and net profit per day, month and year (blueprint section 44 M, owner approved 2026-11-08).
EVERY number here is an ASSUMPTION (staff, salaries, marketing, SMS, tax) except the list prices noted, which were checked on
2026-11-07: Google Cloud Run ($0.000024 per vCPU-second, $0.40 per million requests, L4 GPU $0.0001867 a second), Cloud SQL
(about $197 a month for 4 vCPUs, doubled for high availability), email $0.10 to $1.50 per 1,000, Google Workspace Business
Starter $7 a user a month. A day is a month x 12 / 365. Tax on profit is a blended 25% guess; losses carried forward are not used."""
from decimal import Decimal, ROUND_HALF_UP
from finance import revenue_model as rm

STAFF = {"stage1": 8, "stage2": 200, "stage3": 3000}                      # people
STAFF_COST = {"stage1": 30000, "stage2": 45000, "stage3": 55000}          # USD a person a year, everything included
NEW_MERCHANTS = {"stage1": 208, "stage2": 6667, "stage3": 83333}          # a month
LEGAL = {"stage1": 3000, "stage2": 60000, "stage3": 500000}
SECURITY = {"stage1": 1000, "stage2": 25000, "stage3": 150000}
INSURANCE = {"stage1": 500, "stage2": 10000, "stage3": 80000}
GPUS = {"stage1": 1, "stage2": 4, "stage3": 40}
MESSAGING_REVENUE = {"stage1": 338, "stage2": 16920, "stage3": 376000}    # messaging-credit revenue (section 14 E)
TAX_RATE = Decimal("0.25")
NEW_SERVICE_COST_SHARE = Decimal("0.20")                                  # running costs of the second review's additions
ROWS = ("people", "office_tools", "marketing", "payment_collection", "legal", "hosting", "message_delivery", "sms", "security",
        "ai", "assist_everywhere", "insurance", "email", "translation_gpu", "new_service_costs")


def _r(x):
    return int(Decimal(x).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def expenses(stage):
    """Monthly USD per expense line for one stage (whole dollars)."""
    m, c = Decimal(rm.MERCHANTS[stage]), Decimal(rm.CONSUMERS[stage])
    subs = Decimal(rm.totals()[stage]["subscriptions"])
    rows = {
        "people": Decimal(STAFF[stage] * STAFF_COST[stage]) / 12,
        "office_tools": Decimal(STAFF[stage] * (300 + 50 + 14)),
        "marketing": Decimal(NEW_MERCHANTS[stage] * 20),
        "payment_collection": subs * Decimal("0.035"),
        "legal": Decimal(LEGAL[stage]),
        "hosting": 1500 + m * Decimal("0.12") + c * Decimal("0.01"),
        "message_delivery": Decimal("0.7") * MESSAGING_REVENUE[stage],
        "sms": (m * Decimal("1.5") + c) * Decimal("0.5") * Decimal("0.03"),
        "security": Decimal(SECURITY[stage]),
        "ai": m * Decimal("0.058") * rm.CONVERSION[stage] * Decimal("0.5") + m * Decimal("0.02"),
        "assist_everywhere": m * Decimal("0.03") + c * Decimal("0.005"),   # LynkAssist in support, chat, drafts and summaries (blueprint 45)
        "insurance": Decimal(INSURANCE[stage]),
        "email": (m * 30 + c * 5) / 1000 * Decimal("0.30"),
        "translation_gpu": GPUS[stage] * Decimal("0.0001867") * 3600 * 730,
        "new_service_costs": rm.second_review_uplift(stage) * NEW_SERVICE_COST_SHARE,
    }
    return {k: _r(v) for k, v in rows.items()}


def profit(stage):
    """Revenue, expenses, tax and net profit per day, month and year for one stage."""
    rev = sum(rm.ecosystem(stage).values())
    exp = sum(expenses(stage).values())
    before = rev - exp
    tax = _r(max(before, 0) * TAX_RATE)
    net = before - tax
    day = lambda v: _r(Decimal(v) * 12 / 365)
    return {"revenue": {"day": day(rev), "month": rev, "year": rev * 12},
            "expenses": {"day": day(exp), "month": exp, "year": exp * 12},
            "before_tax": before, "tax": tax,
            "net": {"day": day(net), "month": net, "year": net * 12},
            "margin_pct": (Decimal(net) * 100 / rev).quantize(Decimal("0.1"))}


if __name__ == "__main__":
    for st in rm.STAGES:
        print(st, profit(st))
