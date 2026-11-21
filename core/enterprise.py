"""The large-organisation set and the Move in tool (OFFICE UPDATE, master blueprint 66.5 and 66.6; section 4 step D4a), read from
catalog/enterprise.v1.json.

Approval flows an organisation builds itself (steps by amount and department, stand-ins, never the preparer), its own roles
(never more than the owner's, preparing and approving kept apart), charges split by department, legal hold and keeping times,
where data is kept, and the Move in check report: amounts read exactly as whole minor units, dates that exist, required fields,
the same reference twice, open items for unknown people, and opening balances that balance. These rules only ever make
LynkOmni do less.

This module is the Python reference; ts/src/enterprise.ts must agree on every case of contract/vectors/enterprise.v1.json
(python3 tools/enterprise_vectors.py after a change)."""
import datetime as _dt
import json, os, re

from core import books as B

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
with open(os.path.join(ROOT, "catalog", "enterprise.v1.json"), encoding="utf-8") as _f:
    ENT = json.load(_f)
TYPES = ("asset", "liability", "equity", "income", "expense")


# ---- approval flows ----------------------------------------------------------------------------------------------------------
def flow_steps(flow, amount, department=None):
    """The steps a document needs: every step whose amount it reaches and whose department (if any) matches, in order."""
    if len(flow) > ENT["approval_flows"]["max_steps"]:
        raise ValueError("too many steps")
    return [s for s in flow if amount >= s.get("from_minor", 0) and (s.get("department") is None or s.get("department") == department)]


def may_approve(steps, approvals, preparer, who, role, main_away=False):
    """Whether this person may approve the next step: never the preparer, never twice, the step's role (or its stand-in's
    role while the approver is away)."""
    n = len(approvals)
    if n >= len(steps):
        return {"ok": False, "why": "no_step_left"}
    if who == preparer:
        return {"ok": False, "why": "preparer"}
    if who in [a["who"] for a in approvals]:
        return {"ok": False, "why": "already_approved"}
    step = steps[n]
    if role == step["role"]:
        return {"ok": True, "why": "step"}
    if main_away and step.get("stand_in") and role == step["stand_in"]:
        return {"ok": True, "why": "stand_in"}
    return {"ok": False, "why": "wrong_role"}


# ---- own roles ---------------------------------------------------------------------------------------------------------------
def role_problems(perms, kept_apart=True):
    """What is wrong with an organisation's own role: a permission the owner does not have, or preparing and approving held
    together in one area while they are kept apart."""
    owner = ENT["roles"]["base"]["owner"]
    out = []
    for area in sorted(perms):
        if area not in ENT["areas"]:
            out.append({"area": area, "problem": "unknown_area"}); continue
        for p in perms[area]:
            if p not in owner.get(area, []):
                out.append({"area": area, "problem": "more_than_owner", "permission": p})
        if kept_apart:
            for a, b in ENT["roles"]["kept_apart"]:
                if a in perms[area] and b in perms[area]:
                    out.append({"area": area, "problem": "kept_apart", "permission": f"{a}+{b}"})
    return out


def can(perms, area, permission):
    return permission in (perms.get(area) or [])


# ---- charges, holds, keeping, region -----------------------------------------------------------------------------------------
def split_charges(total, shares):
    """Charges split by department: {department: basis points} adding up to 10000; the split adds up exactly."""
    keys = sorted(shares)
    if sum(shares[k] for k in keys) != 10000:
        raise ValueError("shares must add up to 10000")
    return dict(zip(keys, B.allocate(total, [shares[k] for k in keys])))


def may_change(held):
    """Nothing under a legal hold is changed or deleted until the hold is lifted."""
    return not held


def may_delete(age_days, policy_days, law_days, held=False):
    """A record may go only after the longer of the policy's and the law's keeping time, and never under a hold."""
    return not held and age_days >= max(policy_days or 0, law_days or 0)


def data_region(choice, pack=None):
    """The country's own rule wins over the organisation's choice."""
    forced = ((((pack or {}).get("office") or {}).get("crm")) or {}).get("data_region")
    return forced or choice


def suspended_by(removed_minute):
    """A person removed in the staff directory loses access within this minute."""
    return removed_minute + ENT["directory"]["suspend_within_minutes"]


# ---- Move in -----------------------------------------------------------------------------------------------------------------
_THOUSANDS = re.compile(r"^-?\d{1,3}(,\d{3})+(\.\d+)?$")


def parse_amount(text, decimals):
    """A written amount as whole minor units, read exactly; None when it is not one ("1,234.50", "1234,5" and "-12" are;
    "1.234" with 2 decimals is 1.234 and so refused for having three decimals; "12abc" is not)."""
    t = str(text if text is not None else "").strip().replace(" ", "").replace(" ", "").replace("_", "")
    if not t:
        return None
    if _THOUSANDS.match(t):
        t = t.replace(",", "")
    elif "," in t and "." not in t and t.count(",") == 1:
        t = t.replace(",", ".")
    if not re.fullmatch(r"-?\d+(\.\d+)?", t):
        return None
    neg = t.startswith("-")
    whole, _, frac = t.lstrip("-").partition(".")
    if len(frac) > decimals:
        return None
    value = int(whole) * 10 ** decimals + int((frac + "0" * decimals)[:decimals] or "0")
    return -value if neg else value


def parse_date(text, fmt="iso"):
    """A date written iso (2026-01-31), day first (31/01/2026) or month first (01/31/2026), as ISO; None when it does not exist."""
    t = str(text if text is not None else "").strip()
    try:
        if fmt == "iso":
            m = re.fullmatch(r"(\d{4})-(\d{1,2})-(\d{1,2})", t)
            y, mo, d = (int(m.group(1)), int(m.group(2)), int(m.group(3))) if m else (0, 0, 0)
        else:
            m = re.fullmatch(r"(\d{1,2})[/.\-](\d{1,2})[/.\-](\d{4})", t)
            if not m:
                return None
            a, b, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
            d, mo = (a, b) if fmt == "day_first" else (b, a)
        return _dt.date(y, mo, d).isoformat()
    except (ValueError, AttributeError):
        return None


def check(kind, header, rows, decimals=2, date_format="iso", known=None, accounts=None):
    """The check report for one Move in file: rows are lists in the header's order. Returns {"ok", "count", "errors",
    "totals"}; an error names its row (1 is the first row after the header), column and issue."""
    spec = ENT["move_in"]["kinds"][kind]
    errors, totals, seen = [], {}, set()
    missing = [c for c in spec["required"] if c not in header]
    for c in missing:
        errors.append({"row": 0, "column": c, "issue": "missing_column"})
    if missing:
        return {"ok": False, "count": len(rows), "errors": errors, "totals": totals}
    if len(rows) > ENT["move_in"]["max_rows"]:
        return {"ok": False, "count": len(rows), "errors": [{"row": 0, "column": "", "issue": "too_many_rows"}], "totals": totals}
    idx = {c: i for i, c in enumerate(header)}
    get = lambda r, c: (r[idx[c]] if c in idx and idx[c] < len(r) else "")
    debit = credit = amount = 0
    ref_col = {"chart": "code", "customers": "ref", "suppliers": "ref", "open_invoices": "number", "open_bills": "ref", "voters": "ref"}.get(kind)
    for n, r in enumerate(rows, 1):
        for c in spec["required"]:
            if str(get(r, c)).strip() == "":
                errors.append({"row": n, "column": c, "issue": "required_empty"})
        if ref_col:
            ref = str(get(r, ref_col)).strip()
            if ref and ref in seen:
                errors.append({"row": n, "column": ref_col, "issue": "duplicate_ref"})
            seen.add(ref)
        if kind == "voters" and str(get(r, "weight")).strip() and not re.fullmatch(r"[1-9][0-9]{0,8}", str(get(r, "weight")).strip()):
            errors.append({"row": n, "column": "weight", "issue": "bad_weight"})
        if kind == "chart" and str(get(r, "type")).strip() and get(r, "type") not in TYPES:
            errors.append({"row": n, "column": "type", "issue": "unknown_type"})
        if kind == "opening_balances":
            acct = str(get(r, "account")).strip()
            if acct and accounts is not None and acct not in accounts:
                errors.append({"row": n, "column": "account", "issue": "unknown_account"})
            d = parse_amount(get(r, "debit"), decimals) if str(get(r, "debit")).strip() else 0
            c = parse_amount(get(r, "credit"), decimals) if str(get(r, "credit")).strip() else 0
            if d is None or c is None or d < 0 or c < 0:
                errors.append({"row": n, "column": "debit" if d is None or (d or 0) < 0 else "credit", "issue": "bad_amount"})
            elif bool(d) == bool(c):
                errors.append({"row": n, "column": "debit", "issue": "one_side_only"})
            else:
                debit += d; credit += c
        for c in ("issued_on", "due_on", "received_on"):
            if c in idx and str(get(r, c)).strip() and parse_date(get(r, c), date_format) is None:
                errors.append({"row": n, "column": c, "issue": "bad_date"})
        if kind in ("open_invoices", "open_bills"):
            a = parse_amount(get(r, "amount"), decimals)
            if a is None or a <= 0:
                if str(get(r, "amount")).strip():
                    errors.append({"row": n, "column": "amount", "issue": "bad_amount"})
            else:
                amount += a
            who_col, who_kind = ("customer_ref", "customers") if kind == "open_invoices" else ("supplier_ref", "suppliers")
            who = str(get(r, who_col)).strip()
            if who and known is not None and who not in known.get(who_kind, []):
                errors.append({"row": n, "column": who_col, "issue": "unknown_ref"})
    if kind == "opening_balances":
        totals = {"debit": debit, "credit": credit}
        if debit != credit:
            errors.append({"row": 0, "column": "", "issue": "not_balanced"})
    if kind in ("open_invoices", "open_bills"):
        totals = {"amount": amount}
    return {"ok": not errors, "count": len(rows), "errors": errors, "totals": totals}
