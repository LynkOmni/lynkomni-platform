"""LynkAcc's rules (OFFICE UPDATE, master blueprint 66.2; section 4 step D1), read from catalog/books.v1.json.

Bills to pay with their approval steps and three-way matching, expense claims and company-card matching, assets and loans,
spreading over time, repeating and reversing entries, the period lock and year-end close, two people for sensitive entries,
bank matching, several taxes on one line, the four statements, period-end revaluation, stock value, group books and the
tools for each kind of entity. Money is integer minor units; rates are integer basis points or integer fractions; quantities
are integer thousandths. Every split adds up exactly to its whole, rounding half away from zero. The journal itself stays the
event log's projection (core/accounts.py): these functions decide amounts and lines, never a second ledger.

This module is the Python reference; ts/src/books.ts must agree on every case of contract/vectors/books.v1.json
(python3 tools/books_vectors.py after a change)."""
import datetime as _dt
import json, os

from core import accounts as A

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
with open(os.path.join(ROOT, "catalog", "books.v1.json"), encoding="utf-8") as _f:
    BOOKS = json.load(_f)

CASH_BY_METHOD = {"cash": "1000", "bank": "1020", "mobile_money": "1030", "cheque": "1040"}
ADDED_TAXES = ("sales", "import")


# ---- integer arithmetic ----------------------------------------------------------------------------------------------------
def round_div(n, d):
    """n / d rounded half away from zero (d > 0)."""
    if d <= 0:
        raise ValueError("divide by a positive number")
    q = (2 * abs(n) + d) // (2 * d)
    return q if n >= 0 else -q


def split(total, parts):
    """An even split that adds up exactly: the first parts take the remainder."""
    if parts <= 0:
        return []
    base, rem = divmod(abs(total), parts)
    sign = -1 if total < 0 else 1
    return [sign * (base + (1 if i < rem else 0)) for i in range(parts)]


def allocate(total, weights):
    """total shared by weights; the last share takes what rounding left, so the shares add up exactly."""
    w = sum(weights)
    if not weights or w <= 0:
        return []
    out = [round_div(total * x, w) for x in weights[:-1]]
    return out + [total - sum(out)]


# ---- tax ---------------------------------------------------------------------------------------------------------------------
def tax_line(amount, taxes, included=False):
    """Several taxes on one line. taxes: [{"kind": sales|import|withholding|reverse_charge, "rate_bp": int}]. With included,
    amount is the price with the added taxes inside it. Returns the net, each tax, the total charged, the tax held back
    and what the customer pays now; a reverse-charge tax is recorded but not charged."""
    added = [t for t in taxes if t["kind"] in ADDED_TAXES]
    rates = [t["rate_bp"] for t in added]
    if included and sum(rates):
        net = round_div(amount * 10000, 10000 + sum(rates))
        shares = iter(allocate(amount - net, rates))
    else:
        net = amount
        shares = iter([round_div(net * r, 10000) for r in rates])
    out = []
    for t in taxes:
        if t["kind"] in ADDED_TAXES:
            amt, charged = next(shares), True
        else:
            amt, charged = round_div(net * t["rate_bp"], 10000), False
        out.append({"kind": t["kind"], "rate_bp": t["rate_bp"], "amount": amt, "charged": charged})
    total = net + sum(t["amount"] for t in out if t["charged"])
    withheld = sum(t["amount"] for t in out if t["kind"] == "withholding")
    reverse = sum(t["amount"] for t in out if t["kind"] == "reverse_charge")
    return {"net": net, "taxes": out, "total": total, "withheld": withheld, "to_pay": total - withheld, "reverse_charge": reverse}


# ---- bills to pay ------------------------------------------------------------------------------------------------------------
def bill_move(state, action):
    """The next state of a bill, or None when the move is not allowed. 'paid' comes only from the provider's confirmation."""
    return BOOKS["bills"]["moves"].get(state, {}).get(action)


def approvers(amount, rules=None):
    """The roles that approve a bill of this amount, in order (the first rule whose limit it is within)."""
    for r in rules or BOOKS["bills"]["approval"]:
        if r["up_to_minor"] is None or amount <= r["up_to_minor"]:
            return list(r["roles"])
    return []


def may_approve(preparer, approver):
    """The person who entered a bill never approves it."""
    return approver is not None and approver != preparer


def match3(po, received, bill, tolerance_bp=0):
    """A bill checked against its purchase order and the goods received: [{"sku", "qty", "price_minor"}] each (qty in
    thousandths). Returns {"ok", "issues": [{"sku", "issue"}]} in the bill's order."""
    def by_sku(lines):
        out = {}
        for ln in lines:
            o = out.setdefault(ln["sku"], {"qty": 0, "price": ln.get("price_minor", 0)})
            o["qty"] += ln["qty"]
        return out
    p, r, b = by_sku(po), by_sku(received), by_sku(bill)
    issues = []
    for sku, ln in b.items():
        if sku not in p:
            issues.append({"sku": sku, "issue": "not_ordered"}); continue
        if sku not in r:
            issues.append({"sku": sku, "issue": "not_received"}); continue
        if ln["qty"] > r[sku]["qty"] or ln["qty"] > p[sku]["qty"]:
            issues.append({"sku": sku, "issue": "qty_over"})
        if ln["price"] * 10000 > p[sku]["price"] * (10000 + tolerance_bp):
            issues.append({"sku": sku, "issue": "price_over"})
    return {"ok": not issues, "issues": issues}


def early_discount(amount, rate_bp, within_days, paid_after_days):
    """What paying early saves: rate_bp of the amount when paid within its days, otherwise nothing."""
    return round_div(amount * rate_bp, 10000) if 0 <= paid_after_days <= within_days else 0


# ---- staff spending ----------------------------------------------------------------------------------------------------------
def mileage(km_thousandths, rate_minor_per_km):
    return round_div(km_thousandths * rate_minor_per_km, 1000)


def allowance(days, rate_minor_per_day):
    return days * rate_minor_per_day


def card_match(spends, receipts, days=None):
    """Company-card spends matched to receipts of the same amount within the days; spends with none are 'missing'.
    spends and receipts: [{"id", "amount", "day"}] (day: a whole day number)."""
    days = BOOKS["expenses"]["card_match_days"] if days is None else days
    used, matched, missing = set(), [], []
    for s in spends:
        best = None
        for i, r in enumerate(receipts):
            if i in used or r["amount"] != s["amount"]:
                continue
            gap = abs(r["day"] - s["day"])
            if gap <= days and (best is None or gap < best[0]):
                best = (gap, i)
        if best is None:
            missing.append(s["id"])
        else:
            used.add(best[1]); matched.append([s["id"], receipts[best[1]]["id"]])
    return {"matched": matched, "missing": missing}


# ---- assets and loans --------------------------------------------------------------------------------------------------------
def depreciation(cost, residual, years, method="straight_line", rate_bp=0):
    """Yearly loss of value; the schedule ends exactly at the residual value."""
    if years <= 0 or residual > cost:
        return []
    if method == "straight_line":
        base = (cost - residual) // years
        out = [base] * years
        out[-1] += (cost - residual) - base * years
        return out
    if method == "reducing_balance":
        book, out = cost, []
        for y in range(years):
            amt = book - residual if y == years - 1 else min(round_div(book * rate_bp, 10000), book - residual)
            out.append(amt); book -= amt
        return out
    raise ValueError("unknown method")


def disposal(cost, so_far, proceeds, method="bank"):
    """Lines for selling or writing off an asset: the cost and the loss so far leave the books; a gain or loss is posted."""
    lines = []
    if proceeds:
        lines.append([CASH_BY_METHOD.get(method, "1020"), proceeds, 0])
    if so_far:
        lines.append(["1510", so_far, 0])
    lines.append(["1500", 0, cost])
    diff = proceeds + so_far - cost
    if diff > 0:
        lines.append(["4200", 0, diff])
    elif diff < 0:
        lines.append(["6900", -diff, 0])
    return lines


def loan_schedule(principal, annual_bp, months):
    """Equal monthly payments; each month's interest on the balance; the last payment clears it exactly."""
    if months <= 0:
        return []
    rows, bal = [], principal
    if annual_bp == 0:
        for m, part in enumerate(split(principal, months), 1):
            bal -= part
            rows.append({"month": m, "payment": part, "interest": 0, "principal": part, "balance": bal})
        return rows
    a, b = annual_bp, 120000
    g = (b + a) ** months
    payment = round_div(principal * a * g, b * (g - b ** months))
    for m in range(1, months + 1):
        interest = round_div(bal * a, b)
        princ = bal if m == months else payment - interest
        bal -= princ
        rows.append({"month": m, "payment": princ + interest, "interest": interest, "principal": princ, "balance": bal})
    return rows


def loan_lines(row, method="bank"):
    lines = [["2600", row["principal"], 0]]
    if row["interest"]:
        lines.append(["6600", row["interest"], 0])
    lines.append([CASH_BY_METHOD.get(method, "1020"), 0, row["payment"]])
    return lines


# ---- dates, repeating and reversing ------------------------------------------------------------------------------------------
def _date(s):
    return _dt.date.fromisoformat(s)


def _days_in_month(y, m):
    return (_dt.date(y + (m == 12), m % 12 + 1, 1) - _dt.date(y, m, 1)).days


def repeat_dates(start, every, count):
    """The dates of a repeating entry; a month-end start stays at each month's end."""
    d = _date(start)
    if every == "week":
        return [(d + _dt.timedelta(days=7 * i)).isoformat() for i in range(count)]
    step = {"month": 1, "quarter": 3, "year": 12}[every]
    end = d.day == _days_in_month(d.year, d.month)
    out = []
    for i in range(count):
        mm = d.month - 1 + step * i
        y, m = d.year + mm // 12, mm % 12 + 1
        last = _days_in_month(y, m)
        out.append(_dt.date(y, m, last if end else min(d.day, last)).isoformat())
    return out


def reversal_date(date):
    return (_date(date) + _dt.timedelta(days=1)).isoformat()


def reverse(lines):
    return [[a, cr, dr] for a, dr, cr in lines]


def may_post(date, lock_date=None):
    """Nothing posts on or before the lock date."""
    return lock_date is None or date > lock_date


def two_person(kind, preparer, approver):
    if kind not in BOOKS["two_person"]["kinds"]:
        return {"needed": False, "ok": True}
    return {"needed": True, "ok": approver is not None and approver != preparer}


def close_missing(done):
    return [c for c in BOOKS["closing"]["checklist"] if c not in done]


def year_end_lines(tb):
    """Closing lines that move the year's income and expenses into profit kept from earlier years."""
    lines, profit = [], 0
    for acct in sorted(tb):
        bal, t = tb[acct], A.ACCOUNTS[acct]["type"]
        if not bal or t not in ("income", "expense"):
            continue
        if t == "income":
            lines.append([acct, bal, 0] if bal > 0 else [acct, 0, -bal]); profit += bal
        else:
            lines.append([acct, 0, bal] if bal > 0 else [acct, -bal, 0]); profit -= bal
    keep = BOOKS["closing"]["year_end_account"]
    if profit > 0:
        lines.append([keep, 0, profit])
    elif profit < 0:
        lines.append([keep, -profit, 0])
    return lines


# ---- banks -------------------------------------------------------------------------------------------------------------------
def bank_match(lines, items, days=None):
    """Statement lines matched to book items of the same amount within the days: a matching reference first, then the
    nearest date, then the order. lines and items: [{"id", "amount", "day", "ref"}]."""
    days = BOOKS["bank"]["match_days"] if days is None else days
    used, matched, unmatched = set(), [], []
    for ln in lines:
        best = None
        for i, it in enumerate(items):
            if i in used or it["amount"] != ln["amount"]:
                continue
            gap = abs(it["day"] - ln["day"])
            if gap > days:
                continue
            ref = bool(it.get("ref")) and it["ref"] in (ln.get("ref") or "")
            key = (0 if ref else 1, gap, i)
            if best is None or key < best:
                best = key
        if best is None:
            unmatched.append(ln["id"])
        else:
            used.add(best[2]); matched.append([ln["id"], items[best[2]]["id"]])
    return {"matched": matched, "unmatched": unmatched}


# ---- statements --------------------------------------------------------------------------------------------------------------
def _group_sum(tb, group):
    total = 0
    for acct, bal in tb.items():
        a = A.ACCOUNTS[acct]
        if a["group"] == group:
            total += -bal if a.get("contra") else bal
    return total


def statements(tb):
    """Profit and loss and the balance sheet from a trial balance ({account: balance on its normal side})."""
    income, other = _group_sum(tb, "income"), _group_sum(tb, "other_income")
    cos, exp = _group_sum(tb, "cost_of_sales"), _group_sum(tb, "expense")
    profit = income + other - cos - exp
    cash, cur, noncur = _group_sum(tb, "cash"), _group_sum(tb, "current_asset"), _group_sum(tb, "non_current_asset")
    lc, ln, eq = _group_sum(tb, "current_liability"), _group_sum(tb, "non_current_liability"), _group_sum(tb, "equity")
    assets, liabilities = cash + cur + noncur, lc + ln
    return {"income": income, "other_income": other, "cost_of_sales": cos, "gross": income - cos, "expenses": exp, "profit": profit,
            "cash": cash, "current_assets": cur, "non_current_assets": noncur, "assets": assets,
            "current_liabilities": lc, "non_current_liabilities": ln, "liabilities": liabilities,
            "equity": eq, "equity_with_profit": eq + profit, "balanced": assets == liabilities + eq + profit}


def cash_flow(entries):
    """Money in and out of the cash accounts, grouped by what the other side of each entry was."""
    groups = BOOKS["statements"]["cash_flow_groups"]
    out = {"operating": 0, "investing": 0, "financing": 0}
    for e in entries:
        move = sum(dr - cr for acct, dr, cr in e["lines"] if A.ACCOUNTS[acct]["group"] == "cash")
        if not move:
            continue
        others = {A.ACCOUNTS[acct]["group"] for acct, _, _ in e["lines"] if A.ACCOUNTS[acct]["group"] != "cash"}
        kind = "operating"
        for k in ("investing", "financing"):
            if others & set(groups[k]):
                kind = k
                break
        out[kind] += move
    out["net"] = out["operating"] + out["investing"] + out["financing"]
    return out


def equity_changes(opening, entries):
    """Opening equity, the profit, money put in or taken out by the owners, and closing equity."""
    tb = A.trial_balance(entries)
    st = statements(tb)
    contributions = st["equity"]
    return {"opening": opening, "profit": st["profit"], "contributions": contributions, "closing": opening + st["profit"] + contributions}


# ---- currencies and stock ----------------------------------------------------------------------------------------------------
def revalue(items, num, den):
    """Open items in another currency revalued at the rate num/den (base minor units per foreign minor unit).
    items: [{"id", "foreign_minor", "booked_minor", "side": owed_to_us|we_owe}]. The gain or loss is shown apart."""
    rec = pay = 0
    out = []
    for it in items:
        new = round_div(it["foreign_minor"] * num, den)
        diff = new - it["booked_minor"]
        gain = diff if it["side"] == "owed_to_us" else -diff
        if it["side"] == "owed_to_us":
            rec += diff
        else:
            pay += diff
        out.append({"id": it["id"], "new_minor": new, "gain": gain})
    lines = []
    if rec:
        lines.append(["1100", rec, 0] if rec > 0 else ["1100", 0, -rec])
    if pay:
        lines.append(["2000", 0, pay] if pay > 0 else ["2000", -pay, 0])
    g = rec - pay
    if g > 0:
        lines.append(["4400", 0, g])
    elif g < 0:
        lines.append(["6700", -g, 0])
    return {"items": out, "gain": g, "lines": lines}


def stock_cost(moves, method="fifo"):
    """Cost of goods sold and the stock left, by FIFO or average cost. moves in order: {"kind": "in", "qty", "unit_cost_minor",
    "extra_minor"} (shipping and duty added to the batch) or {"kind": "out", "qty"}. A sale beyond the stock is never
    blocked: what is missing is reported as 'short'."""
    batches, total_q, total_v, cogs, outs, short = [], 0, 0, 0, [], 0
    for mv in moves:
        if mv["kind"] == "in":
            v = round_div(mv["qty"] * mv["unit_cost_minor"], 1000) + mv.get("extra_minor", 0)
            batches.append([mv["qty"], v]); total_q += mv["qty"]; total_v += v
            continue
        want, cost = mv["qty"], 0
        if method == "average":
            take = min(want, total_q)
            part = total_v if take == total_q else round_div(total_v * take, total_q) if total_q else 0
            total_q -= take; total_v -= part; cost = part
            short += want - take
        else:
            while want and batches:
                q, v = batches[0]
                take = min(want, q)
                part = v if take == q else round_div(v * take, q)
                cost += part; want -= take
                if take == q:
                    batches.pop(0)
                else:
                    batches[0] = [q - take, v - part]
            short += want
            total_q = sum(b[0] for b in batches); total_v = sum(b[1] for b in batches)
        cogs += cost; outs.append(cost)
    return {"cogs": cogs, "outs": outs, "qty": total_q, "value": total_v, "short": short}


# ---- groups ------------------------------------------------------------------------------------------------------------------
def consolidate(entities, intercompany_sales=0):
    """Group books: each entity's trial balance translated at its rate (num/den), added together; what they owe each other
    (1600 against 2700) and their sales to each other removed; the share owned by others shown.
    entities: [{"id", "tb", "num", "den", "share_bp"}]."""
    combined, others = {}, 0
    for en in entities:
        t = {a: round_div(b * en["num"], en["den"]) for a, b in en["tb"].items()}
        for a, b in t.items():
            combined[a] = combined.get(a, 0) + b
        if en.get("share_bp", 10000) < 10000:
            st = statements(t)
            others += round_div(st["equity_with_profit"] * (10000 - en["share_bp"]), 10000)
    a, b = BOOKS["group"]["intercompany_accounts"]
    difference = combined.get(a, 0) - combined.get(b, 0)
    combined.pop(a, None); combined.pop(b, None)
    if intercompany_sales:
        combined["4000"] = combined.get("4000", 0) - intercompany_sales
        combined["5000"] = combined.get("5000", 0) - intercompany_sales
    return {"tb": {k: v for k, v in sorted(combined.items()) if v}, "difference": difference, "others_share": others}


def mirror(invoice):
    """A sale between group entities: one side's invoice becomes the other side's bill."""
    return {"supplier": invoice["from"], "entity": invoice["to"], "ref": invoice["number"], "lines": invoice["lines"],
            "total_minor": invoice["total_minor"], "currency": invoice["currency"], "source": "group_mirror", "state": "awaiting_approval"}


# ---- splitting the books and kinds of entity ---------------------------------------------------------------------------------
def dims_ok(dims):
    return all(k in BOOKS["dimensions"]["kinds"] for k in dims)


def fund_spend_ok(fund, purpose):
    """A restricted fund may be spent only for its purpose."""
    return not fund.get("restricted") or fund.get("purpose") == purpose


def available(budget, committed, spent):
    """A public body's budget line: what is left after money promised and money spent."""
    return budget - committed - spent


def budget_vs_actual(budgets, actuals):
    out = []
    for k in sorted(set(budgets) | set(actuals)):
        b, a = budgets.get(k, 0), actuals.get(k, 0)
        out.append({"key": k, "budget": b, "actual": a, "diff": a - b, "used_bp": round_div(a * 10000, b) if b > 0 else None})
    return out


def entity_tools(kind):
    return list(BOOKS["entity_tools"].get(kind, []))
