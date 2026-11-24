#!/usr/bin/env python3
"""Shared vectors for betting at an agent point (BETTING UPDATE, master blueprint section 86): core/betting.py is the reference
and ts/src/betting.ts must agree on every case. Also writes the register into ts/src/betting.generated.ts so devices carry it.
  python3 tools/betting_vectors.py          writes contract/vectors/betting.v1.json and ts/src/betting.generated.ts
  python3 tools/betting_vectors.py --check  fails when either file is out of date (tests/test_betting.py)"""
import json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from core import betting as B  # noqa: E402

OUT = os.path.join(ROOT, "contract", "vectors", "betting.v1.json")
TS = os.path.join(ROOT, "ts", "src", "betting.generated.ts")

STARTS = [(o, s, a, x) for o in (True, False) for s in (True, False) for a in (True, False) for x in (False, True)]
ODDS = [[1000], [2150], [1850, 2100], [1500, 1750, 3200], [1001, 1001, 1001], [12500, 9999, 4040, 1333]]
STAKES = [0, 1, 99, 100, 250, 1000, 99999, 123457, 5_000_000]
TODAY = 1000
TICKETS = [None, {"known": False}, {"known": True, "paid": True, "result": "won", "payable": 500, "expires": 1050},
           {"known": True, "result": "pending", "payable": 0, "expires": 1050}, {"known": True, "result": "lost", "payable": 0, "expires": 1050},
           {"known": True, "result": "won", "payable": 500, "expires": 999}, {"known": True, "result": "won", "payable": 500, "expires": 1000},
           {"known": True, "result": "void", "payable": 200, "expires": 1050}, {"known": True, "result": "won", "payable": 50_000, "expires": 1050},
           {"known": True, "result": "won", "payable": 9_000, "expires": 1050}, {"known": True, "result": "draw", "payable": 10, "expires": 1050},
           {"known": True, "result": "won", "payable": 20_000, "expires": 1050}]


def build():
    starts = [{"online": o, "signed": s, "age": a, "excluded": x, "answer": B.may_start(o, s, a, x)} for o, s, a, x in STARTS]
    odds = [{"odds": o, "total": B.total_odds(o)} for o in ODDS]
    wins = [{"stake": s, "odds": o, "max": m, "win": B.possible_win(s, o, m)} for s in STAKES for o in ODDS[:4] for m in (None, 1_000_000)]
    stakes = [{"stake": s, "min": 100, "max": 1_000_000, "left": left, "answer": B.stake_check(s, 100, 1_000_000, left)} for s in STAKES for left in (None, 1000)]
    checks = [{"ticket": tk, "today": TODAY, "shop_max": 20_000, "cash": cash, "answer": B.check_answer(tk, TODAY, 20_000, cash)} for tk in TICKETS for cash in (0, 8_000, 100_000)]
    comm = [{"amount": a, "bps": b, "commission": B.commission(a, b)} for a in STAKES for b in (0, 150, 500, 1234)]
    cash = [{"opening": 10_000, "stakes": [500, 1_000, 250], "payouts": [800], "expected": B.expected_cash(10_000, [500, 1_000, 250], [800])},
            {"opening": 0, "stakes": [], "payouts": [], "expected": 0}]
    flags = [{"scans": sc, "payouts": p, "shop_max": 20_000, "flags": B.flags(sc, p, 20_000)}
             for sc in ({}, {"T1": 2}, {"T2": 3, "T1": 5}) for p in ([], [16_000, 16_000], [16_000, 17_000, 20_000], [15_999, 16_000, 16_001])]
    methods = [{"method": m, "ok": B.stake_method_ok(m)} for m in B.STAKE_METHODS + tuple(B.REG["never_stake_methods"]) + ("card",)]
    ages = [{"pack": a, "age": B.adult_age(a)} for a in (None, 16, 18, 19, 21)]
    refer = [{"step": s, "next": B.refer_next(s)} for s in B.REG["refer_steps"]]
    texts = [{"odds": o, "format": f, "text": B.odds_text(o, f)} for o in (1000, 1001, 1333, 1850, 1909, 2000, 2150, 3200, 12500) for f in B.REG["odds_formats"]]
    slips = [{"allows": al, "kind": k, "starts_in": si, "lead": 30, "stake": st, "slip_cap": 5000, "queued": q, "shop_cap": 20000,
              "answer": B.offline_slip(al, k, si, 30, st, 5000, q, 20000)}
             for al in (True, False) for k in ("sports", "live", "lottery") for si in (10, 30, 120) for st in (1000, 6000) for q in (0, 15000)]
    results = [{"accepted": a, "stake": s, "out": B.slip_result(a, s)} for a in (True, False) for s in (0, 1500)]
    online = [{"action": a, "online": o, "ok": B.may_online_only(a, o)} for a in ("payout", "refer", "cancel") for o in (True, False)]
    cancels = [{"online": o, "allows": al, "started": g, "manager": m, "since": t, "window": 10, "answer": B.cancel_check(o, al, g, m, t, 10)}
               for o in (True, False) for al in (True, False) for g in (False, True) for m in (True, False) for t in (5, 11)]
    two = [{"amount": a, "owner": w, "needed": B.two_person_needed(a, w)} for a in (0, 9999, 10000, 50000) for w in (None, 10000)]
    split = [{"stakes": st, "threshold": 10000, "flag": B.splitting(st, 10000)} for st in ([], [9500, 9900, 9000], [9500, 9900, 8999], [9500, 9900, 9000, 10000], [9999] * 5)]
    settle = [{"stakes": a, "payouts": b, "commission": c, "net": B.settlement(a, b, c)} for a, b, c in ((100000, 60000, 5000), (20000, 90000, 1000), (0, 0, 0))]
    return {"version": 1, "description": "LynkBet: who may start, odds and how they look, possible wins, stakes, ticket checks, commission, cash, flags, stake methods, ages, referral steps, offline slips, online-only actions, cancelling, two-person approval, money-washing warnings and settlement. core/betting.py is the reference; ts/src/betting.ts must agree.",
            "starts": starts, "odds": odds, "wins": wins, "stakes": stakes, "checks": checks, "commission": comm, "cash": cash, "flags": flags,
            "methods": methods, "ages": ages, "refer": refer, "texts": texts, "slips": slips, "results": results, "online": online, "cancels": cancels,
            "two_person": two, "splitting": split, "settlement": settle}


def ts_text():
    keep = {k: B.REG[k] for k in ("request_states", "results", "check_order", "refer_steps", "payout_ways", "stake_methods", "never_stake_methods", "odds_scale", "flags", "expiry_days", "odds_formats", "kinds", "bet_types")}
    keep["flags"] = {k: v for k, v in keep["flags"].items() if k != "note"}
    keep["expiry_days"] = {k: v for k, v in keep["expiry_days"].items() if k != "note"}
    return ("// GENERATED by tools/betting_vectors.py from catalog/betting.v1.json. Do not edit by hand.\n"
            f"export const BETTING = {json.dumps(keep, ensure_ascii=False)} as const;\n")


def main(check=False):
    vec = json.dumps(build(), indent=1, ensure_ascii=False) + "\n"
    ts = ts_text()
    if check:
        bad = [p for p, want in ((OUT, vec), (TS, ts)) if not os.path.isfile(p) or open(p, encoding="utf-8").read() != want]
        if bad:
            print("out of date: " + ", ".join(bad) + " (run python3 tools/betting_vectors.py)"); return 1
        print("betting vectors are current"); return 0
    for p, txt in ((OUT, vec), (TS, ts)):
        with open(p, "w", encoding="utf-8") as f: f.write(txt)
    print(f"wrote {OUT} and {TS}"); return 0


if __name__ == "__main__":
    sys.exit(main("--check" in sys.argv))
