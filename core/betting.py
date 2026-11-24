"""Betting at an agent point (BETTING UPDATE, owner 2026-11-24, master blueprint section 86).

A shop of a licensed betting operator uses LynkPOS's betting counter to take bets, print the operator's tickets, check tickets and
pay winnings. LynkOmni is only the tool: the operator's own system takes the bet, sets the odds, decides every result and every
amount, and the cloud alone writes its answer. The register is catalog/betting.v1.json; this module is the reference,
ts/src/betting.ts the port, and contract/vectors/betting.v1.json (python3 tools/betting_vectors.py) proves they agree.

Rules kept here:
- A bet is sent online at once; offline only as a queued slip where the operator switched slips on (never live, within its limits),
  and a refused slip returns the full stake. Payouts, referrals and cancelling are online only. It starts only where a licensed
  operator is signed and the customer is of age.
- Money is whole minor units of the shop's currency; odds are whole thousandths (2.150 is 2150); nothing is a float.
- A ticket check answers in a fixed order (register check_order), and only the operator's payable amount is ever paid.
- Cash is handed over only after the operator has locked the payout (state confirmed), so a ticket is never paid twice.
- Above the shop's payout limit a win is referred to the operator's head office; flags are Please check, never an accusation.
"""
import json, os
from math import gcd

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
with open(os.path.join(_ROOT, "catalog", "betting.v1.json"), encoding="utf-8") as _f:
    REG = json.load(_f)

STATES = tuple(REG["request_states"])
RESULTS = tuple(REG["results"])
CHECK_ORDER = tuple(REG["check_order"])
STAKE_METHODS = tuple(REG["stake_methods"])
SCALE = REG["odds_scale"]
FLAGS = REG["flags"]
ADULT_AGE = 18


def _whole(n, what):
    if isinstance(n, bool) or not isinstance(n, int):
        raise TypeError(f"{what} must be a whole number")
    return n


def may_start(online, operator_signed, age_confirmed, self_excluded=False):
    """Whether a bet may start: the first reason it may not, or "ok". Offline nothing starts and nothing is queued."""
    if not online:
        return "offline"
    if not operator_signed:
        return "coming_soon"
    if not age_confirmed:
        return "age"
    if self_excluded:
        return "self_excluded"
    return "ok"


def adult_age(pack_age=None):
    """18, or the country pack's higher age of majority (never lower)."""
    return max(ADULT_AGE, pack_age or 0)


def stake_method_ok(method):
    """Stakes are paid in cash or by mobile money; never on credit, the credit book, a credit card or pay later."""
    return method in STAKE_METHODS


def total_odds(odds):
    """The combined odds of a ticket in thousandths, rounded down at each step (the operator's own figure wins when it answers)."""
    total = SCALE
    for o in odds:
        _whole(o, "odds")
        if o < SCALE:
            raise ValueError("odds below 1.000")
        total = total * o // SCALE
    return total


def possible_win(stake, odds, max_win=None):
    """What the ticket could pay: the stake times the combined odds, rounded down, capped by the operator's largest win."""
    _whole(stake, "stake")
    win = stake * total_odds(odds) // SCALE
    return min(win, max_win) if max_win is not None else win


def stake_check(stake, min_stake, max_stake, personal_left=None):
    """A stake within the operator's limits and the customer's own limit, or the first reason it is not."""
    _whole(stake, "stake")
    if stake < min_stake:
        return "below_min"
    if stake > max_stake:
        return "above_max"
    if personal_left is not None and stake > personal_left:
        return "personal_limit"
    return "ok"


def check_answer(ticket, today, shop_max, cash_in_drawer):
    """What the counter says after a scan. `ticket` is the operator's answer: known, result, paid, payable, expires (a day number)."""
    if not ticket or not ticket.get("known"):
        return "not_valid"
    if ticket.get("paid"):
        return "already_paid"
    result = ticket.get("result")
    if result not in RESULTS:
        return "not_valid"
    if result == "pending":
        return "pending"
    if result == "lost":
        return "lost"
    if today > ticket.get("expires", today):
        return "expired"
    payable = _whole(ticket.get("payable", 0), "payable")
    if payable > shop_max:
        return "refer"
    if payable > cash_in_drawer:
        return "short_of_cash"
    return "pay"


def may_hand_over_cash(lock_state):
    """Cash leaves the drawer only once the operator has confirmed the payout lock."""
    return lock_state == "confirmed"


def commission(amount, bps):
    """The operator's commission in basis points, rounded down (the operator's statement wins)."""
    return _whole(amount, "amount") * _whole(bps, "bps") // 10_000


def expected_cash(opening, stakes_cash, payouts_cash):
    """What the drawer should hold at the end of a shift; a difference is a fact for the owner, never a block."""
    return opening + sum(stakes_cash) - sum(payouts_cash)


def flags(scans, payouts, shop_max):
    """Please check flags: a ticket scanned again and again, or many payouts close to the shop's limit in one shift."""
    out = [f"repeat_scans:{code}" for code, n in sorted(scans.items()) if n >= FLAGS["repeat_scans"]]
    big = [p for p in payouts if p * 10_000 >= shop_max * FLAGS["big_payout_share_bps"]]
    if len(big) >= FLAGS["big_payouts"]:
        out.append("many_big_payouts")
    return out


def refer_next(step):
    """The next step of a head-office referral, or None when it is paid."""
    steps = REG["refer_steps"]
    i = steps.index(step)
    return steps[i + 1] if i + 1 < len(steps) else None


def odds_text(milli, fmt="decimal"):
    """How the operator's odds look to a person (display only; the bet never changes): decimal 2.15, fractional 23/20, American
    +115 or -118, Hong Kong 1.15. Whole-number arithmetic, rounded down."""
    _whole(milli, "odds")
    if milli < SCALE:
        raise ValueError("odds below 1.000")
    win = milli - SCALE
    if fmt == "decimal":
        return f"{milli // SCALE}.{milli % SCALE:03d}"[:-1]
    if fmt == "hong_kong":
        return f"{win // SCALE}.{win % SCALE:03d}"[:-1]
    if fmt == "fractional":
        g = gcd(win, SCALE) or 1
        return f"{win // g}/{SCALE // g}"
    if fmt == "american":
        if win == 0:
            return "0"
        return f"+{win // 10}" if milli >= 2 * SCALE else f"-{-(-100 * SCALE // win)}"
    raise ValueError(f"unknown format {fmt}")


def offline_slip(operator_allows, kind, starts_in_minutes, min_lead_minutes, stake, slip_cap, queued_total, shop_cap):
    """Whether a queued slip may be taken offline, or the first reason it may not. A slip is never a ticket until the operator accepts."""
    if not operator_allows:
        return "operator_off"
    if kind == "live":
        return "live"
    if kind != "lottery" and starts_in_minutes < min_lead_minutes:
        return "starts_soon"
    if stake > slip_cap:
        return "slip_cap"
    if queued_total + stake > shop_cap:
        return "shop_cap"
    return "ok"


def slip_result(accepted, stake):
    """What happens to a queued slip when the operator answers: a ticket, or the whole stake back."""
    return {"ticket": True, "refund": 0} if accepted else {"ticket": False, "refund": _whole(stake, "stake")}


def may_online_only(action, online):
    """Paying a winning ticket, referring a big win and cancelling never happen offline."""
    if action not in ("payout", "refer", "cancel"):
        raise ValueError(f"unknown action {action}")
    return online


def cancel_check(online, operator_allows, game_started, manager_approved, minutes_since, window_minutes):
    """Whether a bet may be cancelled, or the first reason it may not."""
    if not online:
        return "offline"
    if not operator_allows:
        return "operator_off"
    if game_started:
        return "game_started"
    if minutes_since > window_minutes:
        return "too_late"
    if not manager_approved:
        return "manager_needed"
    return "ok"


def two_person_needed(amount, owner_amount):
    """A payout at or above the owner's amount needs a second staff member (never the same person)."""
    return owner_amount is not None and amount >= owner_amount


def splitting(stakes, report_threshold):
    """Stakes kept just under a reporting amount (90% to 100% of it): a money-washing warning for the operator when there are enough."""
    band = report_threshold * FLAGS["split_band_bps"] // 10_000
    near = [s for s in stakes if band <= s < report_threshold]
    return len(near) >= FLAGS["stake_splitting"]


def settlement(stakes, payouts, commission_):
    """One period with an operator: stakes held for it minus payouts minus the shop's commission. Positive: the shop owes the
    operator; negative: the operator owes the shop."""
    return _whole(stakes, "stakes") - _whole(payouts, "payouts") - _whole(commission_, "commission")
