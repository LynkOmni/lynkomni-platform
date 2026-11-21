#!/usr/bin/env python3
"""Shared test answers for LynkVote's security core and counting methods (VOTE UPDATE, master blueprint 68.5 and 68.7):
core/vote_crypto.py and core/vote_count.py are the reference; ts/src/votecrypto.ts and ts/src/votecount.ts must agree.
Every whole number in the security part is written as lowercase hex text, so both languages read it exactly.
  python3 tools/vote_vectors.py          writes contract/vectors/vote.v1.json and ts/src/vote.generated.ts
  python3 tools/vote_vectors.py --check  fails when either file is out of date (tests/test_vote_core.py)"""
import json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from core import vote_count as C  # noqa: E402
from core import vote_crypto as V  # noqa: E402

OUT = os.path.join(ROOT, "contract", "vectors", "vote.v1.json")
TS = os.path.join(ROOT, "ts", "src", "vote.generated.ts")


def hx(x):
    """Numbers become hex text; booleans stay as they are."""
    if isinstance(x, bool) or x is None or isinstance(x, str):
        return x
    if isinstance(x, int):
        return format(x, "x")
    if isinstance(x, (list, tuple)):
        return [hx(v) for v in x]
    if isinstance(x, dict):
        return {k: hx(v) for k, v in x.items()}
    raise TypeError(type(x))


def crypto_case():
    """One small vote from start to finish with seeded numbers: three trustees, any two open; two contests; three voters."""
    rng, vid = V.seeded_rng("lynkvote-vector-1"), "LOVOT-0000-0000-0001"
    parts = [V.trustee_part(i, 2, rng, vid) for i in (1, 2, 3)]
    pubs = [p["public"] for p in parts]
    x = {j: sum(V.share_for(p, j) for p in parts) % V.Q for j in (1, 2, 3)}
    h = V.joint_key(pubs)
    contests = [{"id": "chair", "options": 3, "values": [0, 1], "totals": [1]},
                {"id": "motion", "options": 2, "values": [0, 1], "totals": [0, 1]}]
    choices = [[[1, 0, 0], [1, 0]], [[0, 0, 1], [0, 1]], [[1, 0, 0], [0, 0]]]
    ballots, codes, prev = [], [], "start"
    for ch in choices:
        b = V.lock_ballot(h, vid, contests, ch, rng)
        prev = V.tracking_code(prev, vid, b)
        ballots.append(b)
        codes.append(prev)
    challenged = V.lock_ballot(h, vid, contests, [[0, 1, 0], [1, 0]], rng)          # a ballot the voter challenged, never cast
    totals, opens = [], []
    for ci, con in enumerate(contests):
        for k in range(con["options"]):
            ct = V.multiply([b[ci]["cts"][k] for b in ballots])
            ctx = f"{vid}:{con['id']}:{k}"
            ps = [V.partial_open(pubs, j, x[j], ct, rng, ctx) for j in (1, 3)]
            opens.append({"ct": ct, "ctx": ctx, "parts": ps})
            totals.append(V.combine(ct, ps, len(ballots)))
    rows = [b[0]["cts"] for b in ballots]
    shuffled = V.shuffle(h, rows, rng, f"{vid}:mix", rounds=6)
    return {"vote_id": vid, "seed": "lynkvote-vector-1", "threshold": 2, "contests": contests, "choices": choices,
            "parts": hx([{"index": p["index"], "coeffs": p["coeffs"], "public": p["public"]} for p in parts]),
            "shares": hx({str(j): x[j] for j in x}), "joint_key": hx(h),
            "ballots": hx([V.public_ballot(b) for b in ballots]), "codes": codes,
            "challenged": hx(challenged), "challenged_choices": [[0, 1, 0], [1, 0]],
            "public_list": V.public_list([{"code": c} for c in codes]), "opens": hx(opens), "totals": totals,
            "shuffle_rows": hx(rows), "shuffled": hx(shuffled), "challenge_example": hx(V.challenge("key", vid, 10, 255))}


def counting_cases():
    tn = ["M", "N", "C", "K"]
    tb = [["M", "N", "C", "K"]] * 42 + [["N", "C", "K", "M"]] * 26 + [["C", "K", "N", "M"]] * 15 + [["K", "C", "N", "M"]] * 17
    abc = ["A", "B", "C"]
    party = {"A": 100000, "B": 80000, "C": 30000, "D": 20000}
    lr = {"A": 47000, "B": 16000, "C": 15800, "D": 12000, "E": 6100, "F": 3100}
    sc = [{"A": 5, "B": 4, "C": 0}, {"A": 0, "B": 5, "C": 1}, {"A": 5, "B": 1, "C": 0}, {"B": 3, "C": 3}]
    cases = [
        ["plurality", [[b[0] for b in tb], tn], {}], ["plurality", [["A", "B", "A", "C", "B", "X"], abc, 2], {"seed": "s"}],
        ["two_round", [[b[0] for b in tb], tn], {}], ["two_round", [["A", "A", "B"], abc], {}],
        ["approval", [[["A", "B"], ["B"], ["B", "C", "C"], ["Z"]], abc], {}],
        ["weighted", [[["A", 40], ["B", 35], ["A", 10], ["C", 60], ["B", -5]], abc], {}],
        ["cumulative", [[{"A": 3}, {"A": 1, "B": 2}, {"C": 4}, {"B": -1, "A": 1}], abc, 3], {}],
        ["quadratic", [[{"A": 3}, {"A": 1, "B": 2}, {"C": 4}], abc, 9], {}],
        ["score", [sc, abc, 5], {}], ["star", [sc, abc, 5], {}],
        ["majority_judgment", [[{"A": 4, "B": 3}, {"A": 2, "B": 3}, {"A": 1, "B": 2}, {"A": 4}], ["A", "B"], 5], {}],
        ["budget", [[{"park": 5, "road": 3}, {"road": 4, "well": 2}, {"well": 6}], {"park": 400, "road": 700, "well": 300}, 1000], {}],
        ["irv", [tb, tn], {}], ["borda", [tb, tn], {}], ["bucklin", [tb, tn], {}], ["ranked_pairs", [tb, tn], {}], ["schulze", [tb, tn], {}],
        ["irv", [[["A", "B"], ["B", "A"], ["C"], ["C", "A"]], abc], {"seed": "tie"}],
        ["stv", [[["A", "B"]] * 6 + [["B", "A"]] * 2 + [["C"]] * 4, abc, 2], {}],
        ["stv", [[["A", "B", "C"]] * 5 + [["B", "C"]] * 3 + [["C", "B"]] * 2 + [["D", "C"]] * 2, ["A", "B", "C", "D"], 2], {"seed": "x"}],
        ["dhondt", [party, 8], {}], ["sainte_lague", [party, 8], {}], ["modified_sainte_lague", [party, 8], {}],
        ["dhondt", [party, 8, 1000], {}],
    ]
    out = []
    for name, args, kw in cases:
        out.append({"method": name, "args": args, "kw": kw, "expect": C.METHODS[name](*args, **kw)})
    for q in ("hare", "droop", "imperiali"):
        out.append({"method": f"largest_remainder_{q}", "args": [lr, 10], "kw": {}, "expect": C.largest_remainder(lr, 10, q)})
    yn = []
    for ballots, maj, members, quorum, custom in ((["yes"] * 6 + ["no"] * 3 + ["abstain"] * 5, "two_thirds", None, None, None),
                                                  (["yes"] * 6 + ["no"] * 4, "two_thirds", None, None, None),
                                                  (["yes"] * 5 + ["no"] * 1, "absolute", 11, None, None),
                                                  (["yes"] * 6, "absolute", 11, None, None),
                                                  (["yes"] * 3, "simple", None, 5, None),
                                                  (["yes"] * 3 + ["no"] * 2, "custom", None, None, [3, 5])):
        yn.append({"ballots": ballots, "majority": maj, "members": members, "quorum": quorum, "custom": custom,
                   "expect": C.yes_no(ballots, maj, members, quorum, custom)})
    return {"cases": out, "yes_no": yn, "lots": {"cands": tn, "seed": "draw-1", "expect": C.lots(tn, "draw-1")}}


def build():
    return {"version": 1, "description": "LynkVote's security core and counting methods (VOTE UPDATE 68.5, 68.7). core/vote_crypto.py and core/vote_count.py are the reference.",
            "crypto": crypto_case(), "counting": counting_cases()}


def ts_source():
    return ("// GENERATED by tools/vote_vectors.py from catalog/vote.v1.json. Do not edit by hand.\n"
            f"export const VOTE = {json.dumps(V.VOTE, ensure_ascii=False, separators=(',', ':'))} as const;\n")


def main():
    vec = json.dumps(build(), ensure_ascii=False, separators=(",", ":")) + "\n"
    ts = ts_source()
    if "--check" in sys.argv:
        stale = [p for p, want in ((OUT, vec), (TS, ts)) if not os.path.exists(p) or open(p, encoding="utf-8").read() != want]
        if stale:
            print("out of date:", ", ".join(os.path.relpath(p, ROOT) for p in stale), "- run python3 tools/vote_vectors.py")
            sys.exit(1)
        return
    for p, text in ((OUT, vec), (TS, ts)):
        with open(p, "w", encoding="utf-8") as f:
            f.write(text)
    print("wrote", os.path.relpath(OUT, ROOT), "and", os.path.relpath(TS, ROOT))


if __name__ == "__main__":
    main()
