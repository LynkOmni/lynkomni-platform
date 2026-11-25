#!/usr/bin/env python3
"""Shared vectors for LynkHR's rules (SIX SERVICES UPDATE, master blueprint 69.3): core/hr.py is the reference and ts/src/hr.ts must
agree on every case. Also writes the register into ts/src/hr.generated.ts.
  python3 tools/hr_vectors.py          writes contract/vectors/hr.v1.json and ts/src/hr.generated.ts
  python3 tools/hr_vectors.py --check  fails when either file is out of date (tests/test_hr.py)"""
import json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from core import hr as H  # noqa: E402

OUT = os.path.join(ROOT, "contract", "vectors", "hr.v1.json")
TS = os.path.join(ROOT, "ts", "src", "hr.generated.ts")
ROLES = ("owner", "hr", "payroll", "manager", "staff", "investigator")
PACKS = {"none": None, "known": {"office": {"hr": {"special_allowed": {"health": True, "union": False}, "leave_half_days": {"annual": 42, "sick": 20},
                                                  "overtime_weekly_minutes": 2700, "overtime_multiplier_bp": 20000}}}}


def build():
    staff = [{"id": "s1", "kind": "permanent", "salary": 450000, "allowances": [20000, 15000], "week_minutes": 2700, "hourly_minor": 2600, "commission": 12345},
             {"id": "s2", "kind": "volunteer", "salary": 0}, {"id": "s3", "kind": "casual", "week_minutes": 2401, "hourly_minor": 1999, "advance_repaid": 5000},
             {"id": "s4", "kind": "contractor", "salary": 900000}, {"id": "s5", "kind": "household_staff", "salary": 80000}]
    away = {"2026-12-01": 1, "2026-12-02": 2, "2026-12-03": 0}
    days = ["2026-12-01", "2026-12-02", "2026-12-03", "2026-12-04"]
    return {"version": 1, "description": "LynkHR's rules (SIX SERVICES UPDATE 69.3). core/hr.py is the reference; ts/src/hr.ts must agree.",
            "packs": PACKS,
            "fields": [{"role": r, "self": s, "expect": H.visible_fields(r, s)} for r in ROLES for s in (False, True)],
            "special": [{"k": k, "p": p, "expect": H.special_allowed(k, PACKS[p])} for k in ("health", "union", "family", "skills") for p in PACKS],
            "payroll_kinds": {k: H.on_payroll(k) for k in H.HR["workers"]},
            "minimum": [{"k": k, "p": p, "expect": H.leave_minimum(k, PACKS[p])} for k in ("annual", "sick", "study") for p in PACKS],
            "carry": [{"r": r, "cap": c, "expect": H.carry_over(r, c)} for r in (-4, 0, 7, 25) for c in (None, 4)],
            "balance": [{"e": e, "t": t, "c": c, "expect": H.leave_balance(e, t, c)} for e, t, c in ((42, 10, 6), (20, 25, 0), (0, 0, 0))],
            "request": [{"k": k, "h": h, "b": b, "expect": H.leave_request_ok(k, h, b)} for k in ("annual", "unpaid", "public_holiday", "holiday") for h in (0, 1, 10) for b in (0, 10)],
            "approve": [{"a": a, "b": b, "expect": H.may_approve(a, b)} for a, b in (("u1", "u2"), ("u1", "u1"), ("u1", ""), ("u1", None))],
            "away": away, "days": days,
            "clashes": [{"n": n, "share": s, "expect": H.clashes(n, away, days, s)} for n in (2, 4, 10) for s in (None, 2500)],
            "absence": {"in": [{"kind": "sick"}, {"kind": "annual"}, {"kind": "sick"}, {"kind": "unpaid"}],
                        "expect": H.absence_counts([{"kind": "sick"}, {"kind": "annual"}, {"kind": "sick"}, {"kind": "unpaid"}])},
            "checklists": [{"k": k, "d": d, "expect": H.checklist(k, d)} for k in ("joining", "leaving") for d in ([], ["contract_signed", "documents", "notice_recorded", "equipment_back"],
                                                                                                                [i["id"] for i in H.HR["checklists"][k]])],
            "final_pay": [{"d": d, "expect": H.final_pay_ready(d)} for d in ([], ["notice_recorded", "equipment_back"], ["notice_recorded", "equipment_back", "access_closed"])],
            "probation": [{"s": s, "m": m, "expect": H.probation_end(s, m)} for s in ("2026-01-31", "2026-11-30", "2024-02-29", "2026-05-15") for m in (None, 1, 6, 12)],
            "expiry": [{"e": e, "t": "2026-11-25", "expect": H.expiry_stage(e, "2026-11-25")} for e in ("2026-11-24", "2026-11-25", "2026-11-30", "2026-12-02", "2026-12-25", "2027-01-24", "2027-01-25", "2027-06-01")],
            "reviews": [{"k": k, "n": n, "expect": H.review_shown(k, n)} for k in ("self", "manager", "peer", "upward", "secret") for n in (0, 1, 2, 3)],
            "pay": [{"p": p, "a": a, "i": i, "b": b, "s": s, "expect": H.pay_change_ok(p, a, i, b, s)}
                    for p, a in (("u1", "u2"), ("u1", "u1")) for i, b in ((100, 200), (300, 200)) for s in (None, "u1", "u2", "u3")],
            "overtime": [{"w": w, "h": h, "p": p, "min": H.overtime_minutes(w, PACKS[p]), "pay": H.overtime_pay(H.overtime_minutes(w, PACKS[p]), h, PACKS[p])}
                         for w in (0, 2400, 2401, 2700, 3000) for h in (1999, 2600) for p in PACKS],
            "staff": staff, "payroll": [{"p": p, "expect": H.payroll_figures(staff, PACKS[p])} for p in PACKS],
            "headcount": [{"pos": pos, "b": b, "expect": H.headcount(pos, b)} for pos in ([], [{"yearly_cost": 6000000}, {"yearly_cost": 4500000}]) for b in (0, 10000000, 11000000)],
            "case_see": [{"r": r, "n": n, "expect": H.case_may_see(r, n)} for r in ROLES for n in (False, True)],
            "case_steps": [{"s": s, "deadline": H.case_deadline(s, 20000), "next": H.case_next(s)} for s in H.HR["cases"]["steps"] + ["unknown"]],
            "assist": {a: H.assist_may(a) for a in H.HR["assist"]["may"] + H.HR["assist"]["never"] + ["fly"]},
            "tiers": [{"t": t, "f": f, "expect": H.tier_has(t, f)} for t in ("free", "plus", "pro", "max", "x") for f in ("records", "leave_rules", "reviews", "succession", "nothing")],
            "dates": [{"iso": d, "day": H.day(d), "back": H.iso(H.day(d))} for d in ("1970-01-01", "2026-11-25", "2024-02-29", "2099-12-31")]}


def ts_source():
    return ("// GENERATED by tools/hr_vectors.py from catalog/hr.v1.json. Do not edit by hand.\n"
            "import type { HrRegister } from \"./hr.js\";\n"
            f"export const HR = {json.dumps(H.HR, ensure_ascii=False, separators=(',', ':'))} as unknown as HrRegister;\n")


def main():
    vec = json.dumps(build(), ensure_ascii=False, separators=(",", ":")) + "\n"
    ts = ts_source()
    if "--check" in sys.argv:
        stale = [p for p, want in ((OUT, vec), (TS, ts)) if not os.path.exists(p) or open(p, encoding="utf-8").read() != want]
        if stale:
            print("out of date:", ", ".join(os.path.relpath(p, ROOT) for p in stale), "- run python3 tools/hr_vectors.py")
            sys.exit(1)
        return
    for p, text in ((OUT, vec), (TS, ts)):
        with open(p, "w", encoding="utf-8") as f:
            f.write(text)
    print("wrote", os.path.relpath(OUT, ROOT), "and", os.path.relpath(TS, ROOT))


if __name__ == "__main__":
    main()
