"""LynkHR's rules (SIX SERVICES UPDATE, master blueprint 69.3, 69.11 and 69.12; build section 4B), read from catalog/hr.v1.json.

Staff records with sensitive fields seen by the fewest roles, every kind of worker, leave counted in half days with balances,
carry-over and clashes, joining and leaving checklists, probation, expiry reminders, reviews with anonymous answers shown only
from 3 up, pay changes with a second person, overtime, cases with restricted access and deadlines, what LynkAssist may and
may never do, and the payroll figures LynkAcc receives. Money is integer minor units; nothing here ever decides about a person.

This module is the Python reference; ts/src/hr.ts must agree on every case of contract/vectors/hr.v1.json
(python3 tools/hr_vectors.py after a change)."""
import calendar, datetime, json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
with open(os.path.join(ROOT, "catalog", "hr.v1.json"), encoding="utf-8") as _f:
    HR = json.load(_f)

_EPOCH = datetime.date(1970, 1, 1).toordinal()


def day(iso):
    """A date as a whole day number (days since 1970-01-01)."""
    return datetime.date.fromisoformat(iso).toordinal() - _EPOCH


def iso(n):
    return datetime.date.fromordinal(n + _EPOCH).isoformat()


def _pack_hr(pack):
    return ((pack or {}).get("office") or {}).get("hr") or {}


def _div_half_up(a, b):
    """a / b rounded half up, for non-negative whole numbers (money is never a float)."""
    return (2 * a + b) // (2 * b)


# ---- records -------------------------------------------------------------------------------------------------------------------
def visible_fields(role, is_self=False):
    """The fields a role sees on a staff record; the person always sees their own record (not case notes)."""
    f = HR["fields"]
    out = list(f["always"])
    for name, roles in f["sensitive"].items():
        if role in roles or (is_self and name in f["self_sees"]):
            out.append(name)
    return out


def special_allowed(kind, pack):
    """Health, family or union details: kept only where the country pack says so; unknown means not kept."""
    if kind not in HR["fields"]["special"]:
        return True
    return _pack_hr(pack).get("special_allowed", {}).get(kind) is True


def on_payroll(worker_kind):
    return worker_kind in HR["on_payroll"]


# ---- leave ---------------------------------------------------------------------------------------------------------------------
def leave_minimum(kind, pack):
    """The country's legal minimum in half days, or None while the pack has not confirmed it (never invented)."""
    v = _pack_hr(pack).get("leave_half_days", {}).get(kind)
    return v if isinstance(v, int) else None


def has_balance(kind):
    return HR["leave"]["default_half_days"].get(kind, 0) is not None


def carry_over(remaining, cap=None):
    cap = HR["leave"]["carry_cap_half_days"] if cap is None else cap
    return max(0, min(remaining, cap))


def leave_balance(entitled, taken, carried=0):
    """What is left this year, in half days: what was carried (already capped) plus this year's entitlement, less what was taken."""
    return carried + entitled - taken


def leave_request_ok(kind, half_days, balance):
    if kind not in HR["leave"]["kinds"] or half_days <= 0:
        return False
    return True if not has_balance(kind) else half_days <= balance


def may_approve(asker, approver):
    """Nobody approves their own leave, claim or pay change."""
    return bool(approver) and asker != approver


def clashes(team_size, away_by_day, days, share_bp=None):
    """The days of a request that would leave more than the team's share away; shown, never refused."""
    share_bp = HR["leave"]["max_away_share_bp"] if share_bp is None else share_bp
    return [d for d in days if (away_by_day.get(d, 0) + 1) * 10000 > share_bp * team_size]


def absence_counts(records):
    """Counts by kind only: never a score, a ranking or a judgment about a person."""
    out = {}
    for r in records:
        out[r["kind"]] = out.get(r["kind"], 0) + 1
    return dict(sorted(out.items()))


# ---- joining and leaving -------------------------------------------------------------------------------------------------------
def checklist(kind, done):
    items = HR["checklists"][kind]
    return {"done": sum(1 for i in items if i["id"] in done), "total": len(items),
            "musts_left": [i["id"] for i in items if i["must"] and i["id"] not in done]}


def final_pay_ready(done):
    return all(x in done for x in ("notice_recorded", "equipment_back", "access_closed"))


def probation_end(start, months=None):
    months = HR["probation_months_default"] if months is None else months
    d = datetime.date.fromisoformat(start)
    m = d.month - 1 + months
    y, m = d.year + m // 12, m % 12 + 1
    return datetime.date(y, m, min(d.day, calendar.monthrange(y, m)[1])).isoformat()


def expiry_stage(expiry, today):
    """'expired' after the date; otherwise the reminder step due today or before (60, 30, 7, 0 days), else None."""
    left = day(expiry) - day(today)
    if left < 0:
        return "expired"
    steps = [s for s in HR["expiry"]["remind_days_before"] if left <= s]
    return min(steps) if steps else None


# ---- reviews and pay -----------------------------------------------------------------------------------------------------------
def review_shown(kind, answers):
    if kind not in HR["reviews"]["kinds"]:
        return False
    return answers >= HR["reviews"]["min_answers"] if kind in HR["reviews"]["anonymous"] else answers > 0


def pay_change_ok(proposer, approver, increase_total, budget, second_approver=None):
    """A different person approves; over the budget a third, different person must approve too."""
    if not may_approve(proposer, approver):
        return False
    if increase_total <= budget:
        return True
    return bool(second_approver) and second_approver not in (proposer, approver)


def overtime_minutes(week_minutes, pack=None):
    t = _pack_hr(pack).get("overtime_weekly_minutes", HR["pay"]["overtime"]["weekly_minutes_threshold"])
    return max(0, week_minutes - t)


def overtime_pay(minutes, hourly_minor, pack=None):
    bp = _pack_hr(pack).get("overtime_multiplier_bp", HR["pay"]["overtime"]["multiplier_bp"])
    return _div_half_up(minutes * hourly_minor * bp, 60 * 10000)


def payroll_figures(staff, pack=None):
    """The figures LynkAcc's payroll receives for one period, per person on payroll: salary, allowances, overtime and commission,
    less advances repaid. Volunteers and contractors are never on payroll. LynkHR never pays anyone."""
    out = []
    for s in staff:
        if not on_payroll(s["kind"]):
            continue
        ot = overtime_pay(overtime_minutes(s.get("week_minutes", 0), pack), s.get("hourly_minor", 0), pack)
        gross = s.get("salary", 0) + sum(s.get("allowances", [])) + ot + s.get("commission", 0)
        out.append({"id": s["id"], "gross": gross, "overtime": ot, "deductions": s.get("advance_repaid", 0)})
    return out


def headcount(positions, budget):
    total = sum(p["yearly_cost"] for p in positions)
    return {"total": total, "over": max(0, total - budget)}


# ---- cases ---------------------------------------------------------------------------------------------------------------------
def case_may_see(role, named=False):
    return role in HR["cases"]["see"] or (role == "owner" and named)


def case_deadline(step, started):
    """The day a step is due (day numbers); the last step has no deadline."""
    d = HR["cases"]["days_per_step"].get(step)
    return None if d is None else started + d


def case_next(step):
    s = HR["cases"]["steps"]
    return s[s.index(step) + 1] if step in s and s.index(step) + 1 < len(s) else None


# ---- LynkAssist and tiers ------------------------------------------------------------------------------------------------------
def assist_may(action):
    """LynkAssist drafts and explains; it never decides about a person."""
    return action in HR["assist"]["may"] and action not in HR["assist"]["never"]


def tier_has(tier, feature):
    order = ["free", "plus", "pro", "max"]
    if tier not in order:
        return False
    return any(feature in HR["tiers"][t] for t in order[: order.index(tier) + 1])
