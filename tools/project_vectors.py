#!/usr/bin/env python3
"""Shared vectors for LynkProject's rules (SIX SERVICES UPDATE, master blueprint 69.4): core/project.py is the reference and
ts/src/project.ts must agree on every case. Also writes the register into ts/src/project.generated.ts.
  python3 tools/project_vectors.py          writes contract/vectors/project.v1.json and ts/src/project.generated.ts
  python3 tools/project_vectors.py --check  fails when either file is out of date (tests/test_project.py)"""
import json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from core import project as P  # noqa: E402

OUT = os.path.join(ROOT, "contract", "vectors", "project.v1.json")
TS = os.path.join(ROOT, "ts", "src", "project.generated.ts")


def build():
    T = 20417  # 2025-11-25 as a day number
    tasks = [{"id": "a", "state": "done", "days": 3, "due": T - 2, "owner": "u1"},
             {"id": "b", "state": "doing", "days": 5, "waits_on": ["a"], "due": T - 1, "owner": "u1"},
             {"id": "c", "state": "todo", "days": 2, "waits_on": ["b"], "due": T + 3, "owner": "u1"},
             {"id": "d", "state": "todo", "days": 4, "waits_on": ["a"], "due": T + 20, "owner": "u2"},
             {"id": "e", "state": "waiting", "days": 1, "waits_on": ["c", "d"], "due": T + 6, "owner": "u1"},
             {"id": "f", "state": "cancelled", "days": 9, "due": T - 5, "owner": "u1"},
             {"id": "g", "state": "todo", "days": 1, "owner": "u1"},
             {"id": "h", "state": "todo", "days": 2, "waits_on": ["d"], "due": T + 21, "owner": "u2"},
             {"id": "i", "state": "todo", "days": 0, "due": T, "owner": "u1"},
             {"id": "j", "state": "todo", "days": 1, "waits_on": ["f"], "due": T + 9, "owner": "u1"}]
    deps = {t["id"]: t.get("waits_on", []) for t in tasks}
    entries = [{"id": "t1", "minutes": 90, "rate": 15000, "approved": True, "billable": True}, {"id": "t2", "minutes": 7, "rate": 12345, "approved": True, "billable": True},
               {"id": "t3", "minutes": 60, "rate": 15000, "approved": False, "billable": True}, {"id": "t4", "minutes": 30, "rate": 15000, "approved": True, "billable": False},
               {"id": "t5", "minutes": 45, "rate": 15000, "approved": True, "billable": True, "billed": True}, {"id": "t6", "minutes": 1, "rate": 30, "approved": True, "billable": True}]
    items = [{"points": 3, "done_day": 1}, {"points": 5, "done_day": 3}, {"points": 8, "done_day": None}, {"points": 2, "done_day": 3}]
    return {"version": 1, "description": "LynkProject's rules (SIX SERVICES UPDATE 69.4). core/project.py is the reference; ts/src/project.ts must agree.",
            "today": T, "tasks": tasks, "deps": deps,
            "moves": [{"f": f, "t": t, "expect": P.move_ok(f, t)} for f in P.PJ["states"] for t in P.PJ["states"]],
            "blockers": {t["id"]: P.blockers(t, tasks) for t in tasks},
            "done": {t["id"]: P.done_ok(t, tasks) for t in tasks},
            "wait": [{"a": a, "b": b, "expect": P.wait_ok(deps, a, b)} for a, b in (("a", "e"), ("e", "a"), ("c", "c"), ("d", "g"), ("a", "b"), ("g", "j"))],
            "schedule": P.schedule([t for t in tasks if t["id"] in "abcdeh"]),
            "schedule_empty": P.schedule([]),
            "late": [{"d": d, "expect": P.late(tasks, T + d)} for d in (-10, 0, 4, 30)],
            "risk": [{"d": d, "expect": P.at_risk(tasks, T + d)} for d in (-10, 0, 4)],
            "mywork": [{"p": p, "d": d, "expect": P.my_work(tasks, p, T + d)} for p in ("u1", "u2", "u9") for d in (0, 3)],
            "workload": [{"pl": pl, "lv": lv, "wk": wk, "expect": P.workload(pl, lv, wk)} for pl in ({"u1": 2000, "u2": 3000},) for lv in (None, {"u2": 2}) for wk in (None, {"u1": 1200})],
            "entries_ok": {str(m): P.entry_ok(m) for m in (0, 1, 60, 1440, 1441, -5)},
            "approve": [{"l": l, "a": a, "expect": P.time_approve_ok(l, a)} for l, a in (("u1", "u2"), ("u1", "u1"), ("u1", None))],
            "entries": entries, "billable": P.billable(entries),
            "money": [{"b": b, "c": c, "i": i, "expect": P.money(b, c, i)} for b, c, i in ((100000, [30000, 25000], 90000), (50000, [60000], 0), (0, [], 0))],
            "variance": P.variance({"m1": T, "m2": T + 10, "m3": T + 20}, {"m1": T + 2, "m2": T + 7, "m4": T}),
            "sprint": [{"d": d, "expect": P.sprint(items, d)} for d in (1, 3, 5)], "items": items,
            "guest": [{"part": part, "inv": inv, "expect": P.guest_sees(part, inv, "p1")} for part in ("tasks", "budget", "files", "time_rates") for inv in ([], ["p1"], ["p2"])],
            "field": [{"s": s, "a": a, "expect": P.field_place_ok(s, a)} for s in (False, True) for a in (False, True)],
            "assist": {a: P.assist_may(a) for a in P.PJ["assist"]["may"] + P.PJ["assist"]["never"] + ["fly"]},
            "tiers": [{"t": t, "f": f, "expect": P.tier_has(t, f)} for t in ("free", "plus", "pro", "max", "x") for f in ("tasks", "timeline", "workload", "programmes", "nothing")]}


def ts_source():
    return ("// GENERATED by tools/project_vectors.py from catalog/project.v1.json. Do not edit by hand.\n"
            "import type { ProjectRegister } from \"./project.js\";\n"
            f"export const PROJECT = {json.dumps(P.PJ, ensure_ascii=False, separators=(',', ':'))} as unknown as ProjectRegister;\n")


def main():
    vec = json.dumps(build(), ensure_ascii=False, separators=(",", ":")) + "\n"
    ts = ts_source()
    if "--check" in sys.argv:
        stale = [p for p, want in ((OUT, vec), (TS, ts)) if not os.path.exists(p) or open(p, encoding="utf-8").read() != want]
        if stale:
            print("out of date:", ", ".join(os.path.relpath(p, ROOT) for p in stale), "- run python3 tools/project_vectors.py")
            sys.exit(1)
        return
    for p, text in ((OUT, vec), (TS, ts)):
        with open(p, "w", encoding="utf-8") as f:
            f.write(text)
    print("wrote", os.path.relpath(OUT, ROOT), "and", os.path.relpath(TS, ROOT))


if __name__ == "__main__":
    main()
