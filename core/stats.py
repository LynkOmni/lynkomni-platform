"""LynkStat's additions (SERVICES UPDATE, master blueprint 67.5; section 4 step D4b), read from catalog/stats.v1.json.

Groups over time (cohorts), "what if" (always labelled an estimate), your own measures from existing figures (a small formula
of figures, whole numbers and + - * / with brackets, never code), seeing only your part, freshness, scheduled exports, goals
for teams and branches, public reports with small groups hidden. Integer arithmetic throughout.

This module is the Python reference; ts/src/stats.ts must agree on every case of contract/vectors/stats.v1.json
(python3 tools/stats_vectors.py after a change)."""
import datetime as _dt
import json, os, re

from core import books as B

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
with open(os.path.join(ROOT, "catalog", "stats.v1.json"), encoding="utf-8") as _f:
    STAT = json.load(_f)


def _mi(month):
    y, m = month.split("-")
    return int(y) * 12 + int(m) - 1


def _mname(i):
    return f"{i // 12:04d}-{i % 12 + 1:02d}"


# ---- groups over time --------------------------------------------------------------------------------------------------------
def cohorts(purchases):
    """purchases: [{"customer", "month": "YYYY-MM"}]. Each first-purchase month with its size and how many came back in each
    following month, up to the latest month in the data (at most the register's months)."""
    first, months = {}, {}
    for p in purchases:
        i = _mi(p["month"])
        first[p["customer"]] = min(first.get(p["customer"], i), i)
        months.setdefault(p["customer"], set()).add(i)
    if not first:
        return []
    last = max(i for s in months.values() for i in s)
    out = []
    for start in sorted(set(first.values())):
        members = [c for c, f in first.items() if f == start]
        span = min(last - start, STAT["cohorts"]["max_months"])
        back = [sum(1 for c in members if start + k in months[c]) for k in range(1, span + 1)]
        out.append({"month": _mname(start), "size": len(members), "back": back})
    return out


# ---- what if -----------------------------------------------------------------------------------------------------------------
def what_if(base, changes, elasticity_bp=None):
    """A likely result, always labelled an estimate. base: {"units", "price_minor", "unit_cost_minor", "staff_minor"};
    changes in basis points: {"price_bp", "cost_bp", "staff_hours_bp"}."""
    e = STAT["what_if"]["default_elasticity_bp"] if elasticity_bp is None else elasticity_bp
    pb, cb, sb = changes.get("price_bp", 0), changes.get("cost_bp", 0), changes.get("staff_hours_bp", 0)
    units = base["units"] + B.round_div(base["units"] * pb * e, 10000 * 10000)
    price = base["price_minor"] + B.round_div(base["price_minor"] * pb, 10000)
    cost = base["unit_cost_minor"] + B.round_div(base["unit_cost_minor"] * cb, 10000)
    staff = base["staff_minor"] + B.round_div(base["staff_minor"] * sb, 10000)
    units = max(units, 0)
    revenue = units * price
    return {"units": units, "revenue": revenue, "profit": revenue - units * cost - staff, "estimate": True}


# ---- your own measures -------------------------------------------------------------------------------------------------------
_TOKEN = re.compile(r"\s*(?:(\d+)|([a-z_]+)|(.))")


def _tokens(expr):
    out = []
    for num, name, op in _TOKEN.findall(expr):
        if num:
            out.append(("n", int(num)))
        elif name:
            out.append(("f", name))
        elif op.strip():
            if op not in "+-*/()":
                raise ValueError(f"not allowed: {op}")
            out.append(("o", op))
    return out


def measure_names(expr):
    """The figures a measure uses; refuses anything that is not a figure, a whole number, + - * / or a bracket, or that does
    not read as one formula."""
    toks = _tokens(expr)
    terms = sum(1 for t in toks if t[0] in ("n", "f"))
    if terms == 0 or terms > STAT["measures"]["max_terms"]:
        raise ValueError("a measure has between 1 and the most terms allowed")
    names = sorted({v for k, v in toks if k == "f"})
    unknown = [n for n in names if n not in STAT["measures"]["figures"]]
    if unknown:
        raise ValueError("unknown figures: " + ", ".join(unknown))
    _run(toks, {})
    return names


def evaluate(expr, figures):
    """A measure's value from the figures, in whole numbers; division rounds half away from zero; dividing by zero gives
    None (nothing is shown rather than a made-up number), and so does a result too large for every device to hold exactly."""
    measure_names(expr)
    return _run(_tokens(expr), figures)


SAFE = 2 ** 53 - 1  # the largest whole number every device holds exactly; a result beyond it shows nothing


def _run(toks, figures):
    pos, zero = [0], [False]

    def peek():
        return toks[pos[0]] if pos[0] < len(toks) else None

    def take():
        t = peek(); pos[0] += 1; return t

    def atom():
        t = take()
        if t is None:
            raise ValueError("the measure ends too soon")
        if t == ("o", "("):
            v = expr_()
            if take() != ("o", ")"):
                raise ValueError("a bracket is not closed")
            return v
        if t == ("o", "-"):
            return -atom()
        if t[0] == "n":
            return t[1]
        if t[0] == "f":
            return figures.get(t[1], 0)
        raise ValueError("unexpected sign")

    def term():
        v = atom()
        while peek() in (("o", "*"), ("o", "/")):
            op, r = take()[1], atom()
            if op == "*":
                v = v * r
            else:
                if r == 0:
                    zero[0], v = True, 0                              # read on, so a broken formula is still refused
                else:
                    v = B.round_div(v if r > 0 else -v, abs(r))
        return v

    def expr_():
        v = term()
        while peek() in (("o", "+"), ("o", "-")):
            op, r = take()[1], term()
            v = v + r if op == "+" else v - r
        return v

    v = expr_()
    if peek() is not None:
        raise ValueError("unexpected end")
    return None if zero[0] or abs(v) > SAFE else v


# ---- scope, freshness, exports, goals, public reports ------------------------------------------------------------------------
def scope(rows, viewer, rules):
    """Only the part a role may see: rules {role: "branch" | "all"}; with "branch", only the viewer's branch, and nothing at
    all when the viewer has no branch."""
    r, b = rules.get(viewer["role"], "all"), viewer.get("branch")
    return [x for x in rows if r == "all" or (b is not None and x.get("branch") == b)]


def freshness(updated_minute, now_minute, kind, expected, present):
    age = now_minute - updated_minute
    return {"age_minutes": age, "stale": age > STAT["freshness"]["max_age_minutes"][kind], "missing": [s for s in expected if s not in present]}


def export_dates(start, every, count):
    if every == "day":
        d = _dt.date.fromisoformat(start)
        return [(d + _dt.timedelta(days=i)).isoformat() for i in range(count)]
    return B.repeat_dates(start, every, count)


def goal(actual, target, elapsed_bp):
    """Progress in basis points of the target, and on track when at least as far along as the period."""
    if target <= 0:
        return {"progress_bp": None, "on_track": None}
    p = B.round_div(actual * 10000, target)
    return {"progress_bp": p, "on_track": p >= elapsed_bp}


def public_table(groups):
    """Totals only; a group below the register's minimum is hidden (value None), never shown."""
    k = STAT["public"]["min_group"]
    return [{"group": g["group"], "n": g["n"] if g["n"] >= k else None, "value": g["value"] if g["n"] >= k else None} for g in groups]
