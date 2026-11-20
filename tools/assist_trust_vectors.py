#!/usr/bin/env python3
"""Shared vectors for LynkAssist's trust layer (ASSIST UPDATE, master blueprint 75): core/assist_trust.py is the reference and
ts/src/assisttrust.ts must agree on every case. Also writes the register into ts/src/assisttrust.generated.ts.
  python3 tools/assist_trust_vectors.py          writes contract/vectors/assist-trust.v1.json and ts/src/assisttrust.generated.ts
  python3 tools/assist_trust_vectors.py --check  fails when either file is out of date (tests/test_assist_trust.py)"""
import itertools, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from core import assist_trust as A  # noqa: E402

OUT = os.path.join(ROOT, "contract", "vectors", "assist-trust.v1.json")
TS = os.path.join(ROOT, "ts", "src", "assisttrust.generated.ts")
WORDS = ["pin", "code", "password"]


def build():
    cert = [{"o": dict(zip(("sources", "estimate", "missing", "disagree", "unconfirmed", "checked"), (s, *b))), "expect": A.certainty(s, *b)}
            for s in (0, 1, 3) for b in itertools.product((False, True), repeat=5)]
    works = [[], [{"minor": 1500, "currency": "USD"}, {"minor": 250, "currency": "USD"}], [{"minor": -300, "currency": "RWF"}, {"minor": 1200, "currency": "RWF"}],
             [{"minor": 100, "currency": "USD"}, {"minor": 100, "currency": "EUR"}], [{"minor": 10.5, "currency": "USD"}], [{"minor": True, "currency": "USD"}],
             [{"minor": 0, "currency": "KES"}], [{"minor": 900000000, "currency": "TZS"}, {"minor": 1, "currency": "TZS"}]]
    mem = []
    for kind in ("preference", "remember_that", "secret"):
        for scope, ctx in (("business", "business"), ("person", "business"), ("household", "household")):
            for text in ("Our supplier delivers on Tuesdays", "my card 4111 1111 1111 1111", "PIN 4821"):
                for on, asked, sens, count in ((True, False, [], 0), (False, False, [], 0), (True, False, ["health"], 0), (True, True, ["health"], 0), (True, False, [], 200)):
                    mem.append({"kind": kind, "scope": scope, "text": text, "ctx": ctx, "on": on, "asked": asked, "sensitive": sens, "count": count,
                                "expect": A.remember(kind, scope, text, ctx, on, asked, sens, count, WORDS)})
    mem_items = [{"id": "m1", "scope": "business", "role_min": "cashier"}, {"id": "m2", "scope": "business", "role_min": "owner"},
             {"id": "m3", "scope": "person"}, {"id": "m4", "scope": "business", "role_min": "manager"}, {"id": "m5", "scope": "household", "role_min": "person"}]
    recall = [{"scope": s, "role": r, "expect": A.recall(mem_items, s, r)} for s in ("business", "person", "household") for r in ("cashier", "manager", "owner", "person", "nobody")]
    guards = []
    regs = [("none", True, "A"), ("confirm", False, "B"), ("fresh_check", False, "C"), ("refused", False, None), ("hand_over", False, "D"), ("none", True, "B")]
    flags = ((False, False, False), (True, False, False), (False, True, False), (False, False, True))
    for (needs, run, cls), src, (paused, role_off, practice), confirmed in itertools.product(regs, ("person", "email", "satellite"), flags, (False, True)):
        for items, amt, mi, ma, appr, arole in ((0, None, None, None, None, None), (240, None, None, None, None, None), (60, None, None, None, "u2", "manager"),
                                                (60, None, None, None, "u1", "owner"), (3, 80000, None, None, "u2", "cashier"), (3, 80000, None, None, "u2", "owner"),
                                                (3, 2000, 2, None, None, None), (3, 9000, None, 5000, None, None)):
            g = dict(register_needs=needs, register_run=run, cls=cls, source=src, paused=paused, role_off=role_off, practice=practice, confirmed=confirmed,
                     items=items, amount_minor=amt, max_items=mi, max_amount_minor=ma, owner_amount=None, asker="u1", approver=appr, approver_role=arole)
            guards.append({"g": g, "expect": A.guard(**g)})
    for oa in (None, 1000, 900000):
        g = dict(register_needs="none", register_run=True, cls="A", items=1, amount_minor=5000, owner_amount=oa, asker="u1")
        guards.append({"g": g, "expect": A.guard(**g)})
    warns = [{"check": c, "o": {"screen": sc, "shown_today": n, "pace": p, "told": t, "fine": f}, "expect": A.warning(c, sc, n, p, t, f)}
             for c in list(A.TRUST["warnings"]["checks"]) + ["made_up"] for sc in ("home", "payment") for n in (0, 2, 5, 10) for p in ("less", "normal", "more")
             for t, f in ((False, False), (True, False), (False, True))]
    scores = [({"solved_alone": 7000, "wrong": 100}, {"solved_alone": 6950, "wrong": 150}), ({"solved_alone": 7000}, {"solved_alone": 6800}),
              ({"wrong": 100, "hand_overs": 900}, {"wrong": 250, "hand_overs": 900}), ({"satisfaction": 8000}, {"satisfaction": 9000}), ({}, {"wrong": 999})]
    return {"version": 1, "description": "LynkAssist's trust layer (ASSIST UPDATE 75). core/assist_trust.py is the reference; ts/src/assisttrust.ts must agree.",
            "certainty": cert, "work": [{"parts": p, "expect": A.work(p)} for p in works],
            "adviser": {t: A.needs_not_adviser(t) for t in ("tax", "law", "money", "investment", "medical", "stock", "orders")},
            "sources": {s: A.may_act(s) for s in ("person", "email", "document", "product_name", "web_page", "chat_message", "satellite")},
            "words": WORDS, "memory": mem, "items": mem_items, "recall": recall,
            "limits": [{"r": r, "o": o, "expect": A.effective_limit(r, o)} for r in (None, 50, 200) for o in (None, 10, 500)],
            "bulk": {str(n): A.bulk(n) for n in (0, 1, 9, 10, 240)},
            "guard": guards,
            "plans": [{"from": a, "to": b, "expect": A.plan_move(a, b)} for a in A.SAFE["plans"]["states"] for b in A.SAFE["plans"]["states"]],
            "later": {str(d): A.later_ok(d) for d in (0, 1, 90, 91)},
            "warnings": warns,
            "ask": [{"t": t, "rows": r, "expect": A.ask_about(t, r)} for t in ("number", "word", "chart", "row", "rows", "photo") for r in (0, 1, 50, 51)],
            "gate": [{"before": b, "after": a, "expect": A.gate(b, a)} for b, a in scores],
            "language": [{"x": x, "expect": A.language_ready(*x)} for x in ((199, 7000, 100), (200, 6000, 200), (500, 5999, 100), (500, 9000, 201))],
            "skill": [{"x": x, "expect": A.skill_level(*x)} for x in ((499, 9900, 0), (500, 9500, 100), (800, 9400, 50), (800, 9900, 101))]}


def ts_text():
    keep = {k: A.TRUST[k] for k in ("certainty", "not_adviser", "unconfirmed", "content", "memory", "safety", "warnings", "ask_about", "quality")}
    return ("// GENERATED by tools/assist_trust_vectors.py from catalog/assist-trust.v1.json. Do not edit by hand.\n"
            "import type { TrustRegister } from \"./assisttrust.js\";\n"
            f"export const TRUST = {json.dumps(keep, ensure_ascii=False, separators=(',', ':'))} as TrustRegister;\n")


def main(check=False):
    vec = json.dumps(build(), ensure_ascii=False, separators=(",", ":")) + "\n"
    ts = ts_text()
    if check:
        bad = [p for p, want in ((OUT, vec), (TS, ts)) if not os.path.isfile(p) or open(p, encoding="utf-8").read() != want]
        if bad:
            print("out of date: " + ", ".join(bad) + " (run python3 tools/assist_trust_vectors.py)"); return 1
        print("assist trust vectors are current"); return 0
    for p, txt in ((OUT, vec), (TS, ts)):
        with open(p, "w", encoding="utf-8") as f: f.write(txt)
    print(f"wrote {OUT} ({len(vec) // 1024} KB) and {TS}"); return 0


if __name__ == "__main__":
    sys.exit(main("--check" in sys.argv))
