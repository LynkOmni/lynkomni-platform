"""LynkVote's counting methods (VOTE UPDATE, master blueprint 68.5; section 4 step E1), read from catalog/vote.v1.json.

Every method counts opened ballots with whole numbers and exact fractions (never floats). A tie is broken by the published
draw: candidates ordered by SHA-256 of the vote's seed and their id, so anyone can repeat it. "What if" counts the same ballots
with another method and is always labelled, never the official result. Each method returns its rounds, so the plain example
shown to the organiser is the real count.

This module is the Python reference; ts/src/votecount.ts must agree on every case of contract/vectors/vote.v1.json."""
import hashlib
from fractions import Fraction

from core.vote_crypto import VOTE


def lots(cands, seed):
    """The published draw: the order used to break any tie (first in the list wins a tie; last is removed first)."""
    return sorted(cands, key=lambda c: (hashlib.sha256(f"{seed}|{c}".encode()).hexdigest(), c))


def _best(scores, cands, seed, n=1):
    """The n highest by score, ties broken by the draw."""
    order = lots(cands, seed)
    return sorted(cands, key=lambda c: (-scores[c], order.index(c)))[:n]


def _worst(scores, cands, seed):
    order = lots(cands, seed)
    return sorted(cands, key=lambda c: (scores[c], -order.index(c)))[0]


def _fr(x):
    """A fraction as [numerator, denominator] for the shared test answers."""
    x = Fraction(x)
    return [x.numerator, x.denominator]


# ---- one mark ----------------------------------------------------------------------------------------------------------------
def plurality(ballots, cands, seats=1, seed=""):
    counts = {c: 0 for c in cands}
    for b in ballots:
        if b in counts:
            counts[b] += 1
    return {"counts": counts, "winners": _best(counts, cands, seed, seats)}


def two_round(ballots, cands, seed=""):
    """More than half of the valid votes wins in the first round; otherwise the top two go to a second round."""
    r = plurality(ballots, cands, 1, seed)
    valid = sum(r["counts"].values())
    top = _best(r["counts"], cands, seed, 2)
    if r["counts"][top[0]] * 2 > valid:
        return {"counts": r["counts"], "winners": [top[0]], "second_round": None}
    return {"counts": r["counts"], "winners": [], "second_round": top}


def approval(ballots, cands, seats=1, seed=""):
    counts = {c: 0 for c in cands}
    for b in ballots:
        for c in set(b):
            if c in counts:
                counts[c] += 1
    return {"counts": counts, "winners": _best(counts, cands, seed, seats)}


def weighted(ballots, cands, seats=1, seed=""):
    """ballots: [[choice, weight]] (shares, units, delegates, patronage)."""
    counts = {c: 0 for c in cands}
    for c, w in ballots:
        if c in counts and w > 0:
            counts[c] += w
    return {"counts": counts, "winners": _best(counts, cands, seed, seats)}


def cumulative(ballots, cands, points, seats=1, seed=""):
    """Each voter shares at most `points` among the candidates; a ballot over the limit or with negative points is not counted."""
    counts, refused = {c: 0 for c in cands}, 0
    for b in ballots:
        if any(v < 0 or c not in counts for c, v in b.items()) or sum(b.values()) > points:
            refused += 1
            continue
        for c, v in b.items():
            counts[c] += v
    return {"counts": counts, "winners": _best(counts, cands, seed, seats), "refused": refused}


def quadratic(ballots, cands, credits, seed=""):
    """A voter's votes for a candidate cost their square in credits; a ballot over the credits is not counted."""
    counts, refused = {c: 0 for c in cands}, 0
    for b in ballots:
        if any(v < 0 or c not in counts for c, v in b.items()) or sum(v * v for v in b.values()) > credits:
            refused += 1
            continue
        for c, v in b.items():
            counts[c] += v
    return {"counts": counts, "winners": _best(counts, cands, seed, 1), "refused": refused}


def score(ballots, cands, top, seats=1, seed=""):
    """Scores 0..top for each candidate; the highest total wins (a missing score is 0)."""
    counts = {c: 0 for c in cands}
    for b in ballots:
        for c in cands:
            v = b.get(c, 0)
            if not 0 <= v <= top:
                raise ValueError("a score outside the scale")
            counts[c] += v
    return {"counts": counts, "winners": _best(counts, cands, seed, seats)}


def star(ballots, cands, top, seed=""):
    """Score then automatic run-off: the two highest totals meet, and the one more voters scored higher wins."""
    s = score(ballots, cands, top, 2, seed)
    a, b = s["winners"]
    pa = sum(1 for x in ballots if x.get(a, 0) > x.get(b, 0))
    pb = sum(1 for x in ballots if x.get(b, 0) > x.get(a, 0))
    if pa != pb:
        win = a if pa > pb else b
    elif s["counts"][a] != s["counts"][b]:
        win = a if s["counts"][a] > s["counts"][b] else b
    else:
        win = lots([a, b], seed)[0]
    return {"counts": s["counts"], "finalists": [a, b], "preferred": {a: pa, b: pb}, "winners": [win]}


def majority_judgment(ballots, cands, grades, seed=""):
    """Each candidate's lower median grade; ties broken by taking away median grades one at a time."""
    def profile(c):
        return sorted(b[c] for b in ballots if c in b)

    def key(c):
        g, out = profile(c), []
        while g:
            i = (len(g) - 1) // 2
            out.append(g.pop(i))
        return out
    keys = {c: key(c) for c in cands}
    order = lots(cands, seed)
    ranking = sorted(cands, key=lambda c: ([-x for x in keys[c]], order.index(c)))
    return {"medians": {c: (keys[c][0] if keys[c] else None) for c in cands}, "winners": [ranking[0]], "ranking": ranking}


def budget(ballots, projects, total, seed=""):
    """Voters share points between projects; projects are funded from the most points down while the money lasts.
    projects: {id: cost}."""
    pts = {p: 0 for p in projects}
    for b in ballots:
        for p, v in b.items():
            if p in pts and v > 0:
                pts[p] += v
    left, funded = total, []
    for p in _best(pts, list(projects), seed, len(projects)):
        if pts[p] > 0 and projects[p] <= left:
            funded.append(p)
            left -= projects[p]
    return {"points": pts, "funded": funded, "left": left}


def yes_no(ballots, majority="simple", members=None, quorum=None, custom=None):
    """yes, no or abstain. Abstentions never count as yes. simple: yes > no; absolute: yes > half of the members;
    two_thirds: yes >= two thirds of yes + no; custom [n, d]: yes * d >= n * (yes + no). A quorum (number who took part)
    is checked first."""
    y = sum(1 for b in ballots if b == "yes")
    n = sum(1 for b in ballots if b == "no")
    a = sum(1 for b in ballots if b == "abstain")
    took_part = y + n + a
    if quorum is not None and took_part < quorum:
        return {"yes": y, "no": n, "abstain": a, "quorum_met": False, "passed": False}
    if majority == "simple":
        ok = y > n
    elif majority == "absolute":
        ok = members is not None and y * 2 > members
    elif majority == "two_thirds":
        ok = y + n > 0 and y * 3 >= 2 * (y + n)
    elif majority == "custom":
        num, den = custom
        ok = y + n > 0 and y * den >= num * (y + n)
    else:
        raise ValueError("unknown majority")
    return {"yes": y, "no": n, "abstain": a, "quorum_met": True, "passed": ok}


# ---- ranked ballots ----------------------------------------------------------------------------------------------------------
def _clean(ballots, cands):
    """Each ranking with unknown names and repeats removed."""
    out = []
    for b in ballots:
        seen, r = set(), []
        for c in b:
            if c in cands and c not in seen:
                seen.add(c)
                r.append(c)
        out.append(r)
    return out


def irv(ballots, cands, seed=""):
    ballots, left, rounds = _clean(ballots, cands), list(cands), []
    while True:
        counts = {c: 0 for c in left}
        for b in ballots:
            top = next((c for c in b if c in counts), None)
            if top is not None:
                counts[top] += 1
        active = sum(counts.values())
        rounds.append(dict(counts))
        best = _best(counts, left, seed)[0]
        if counts[best] * 2 > active or len(left) == 1:
            return {"rounds": rounds, "winners": [best]}
        left.remove(_worst(counts, left, seed))


def stv(ballots, cands, seats, seed=""):
    """Single transferable vote: Droop quota (floor of valid / (seats + 1)) + 1; a winner's surplus moves on at the exact
    fraction surplus / their votes (Gregory); when nobody reaches the quota, the lowest is removed."""
    ballots = [[b, Fraction(1)] for b in _clean(ballots, cands) if b]
    quota = len(ballots) // (seats + 1) + 1
    hopeful, elected, rounds = list(cands), [], []
    while len(elected) < seats:
        if len(hopeful) + len(elected) <= seats:
            elected += _best({c: 0 for c in hopeful}, hopeful, seed, len(hopeful))
            break
        piles = {c: [] for c in hopeful}
        for b in ballots:
            top = next((c for c in b[0] if c in piles), None)
            if top is not None:
                piles[top].append(b)
        totals = {c: sum((b[1] for b in piles[c]), Fraction(0)) for c in hopeful}
        rounds.append({c: _fr(v) for c, v in totals.items()})
        top = _best(totals, hopeful, seed)[0]
        if totals[top] >= quota:
            elected.append(top)
            hopeful.remove(top)
            keep = (totals[top] - quota) / totals[top]
            for b in piles[top]:
                b[1] = b[1] * keep
        else:
            hopeful.remove(_worst(totals, hopeful, seed))
    return {"quota": quota, "rounds": rounds, "winners": elected}


def borda(ballots, cands, seed=""):
    """n - 1 points for a first place, down to 0; unranked candidates get 0."""
    n, pts = len(cands), {c: 0 for c in cands}
    for b in _clean(ballots, cands):
        for i, c in enumerate(b):
            pts[c] += n - 1 - i
    return {"counts": pts, "winners": _best(pts, cands, seed)}


def bucklin(ballots, cands, seed=""):
    """Count first choices, then add second choices, and so on, until someone has more than half of the voters."""
    ballots, n, rounds = _clean(ballots, cands), len(ballots), []
    counts = {c: 0 for c in cands}
    for k in range(len(cands)):
        for b in ballots:
            if k < len(b):
                counts[b[k]] += 1
        rounds.append(dict(counts))
        best = _best(counts, cands, seed)[0]
        if counts[best] * 2 > n:
            return {"rounds": rounds, "winners": [best]}
    return {"rounds": rounds, "winners": [_best(counts, cands, seed)[0]]}


def _pairwise(ballots, cands):
    d = {a: {b: 0 for b in cands if b != a} for a in cands}
    for r in _clean(ballots, cands):
        pos = {c: i for i, c in enumerate(r)}
        for a in cands:
            for b in cands:
                if a != b and a in pos and (b not in pos or pos[a] < pos[b]):
                    d[a][b] += 1
    return d


def ranked_pairs(ballots, cands, seed=""):
    """Tideman: lock the pairwise wins from the biggest margin down, skipping any that would make a circle; the candidate no
    locked win points at wins."""
    d, order = _pairwise(ballots, cands), lots(cands, seed)
    pairs = [(a, b, d[a][b] - d[b][a]) for a in cands for b in cands if a != b and d[a][b] > d[b][a]]
    pairs.sort(key=lambda p: (-p[2], -d[p[0]][p[1]], order.index(p[0]), order.index(p[1])))
    locked = {c: set() for c in cands}

    def reaches(x, y):
        stack, seen = [x], set()
        while stack:
            n = stack.pop()
            if n == y:
                return True
            if n not in seen:
                seen.add(n)
                stack.extend(locked[n])
        return False
    for a, b, _ in pairs:
        if not reaches(b, a):
            locked[a].add(b)
    beaten = {b for a in cands for b in locked[a]}
    sources = [c for c in cands if c not in beaten]
    return {"pairwise": d, "locked": [[a, b] for a in cands for b in sorted(locked[a], key=order.index)], "winners": [lots(sources, seed)[0]]}


def schulze(ballots, cands, seed=""):
    d = _pairwise(ballots, cands)
    p = {a: {b: (d[a][b] if d[a][b] > d[b][a] else 0) for b in cands if b != a} for a in cands}
    for i in cands:
        for j in cands:
            if i == j:
                continue
            for k in cands:
                if k in (i, j):
                    continue
                p[j][k] = max(p[j][k], min(p[j][i], p[i][k]))
    wins = {a: sum(1 for b in cands if b != a and p[a][b] > p[b][a]) for a in cands}
    return {"pairwise": d, "paths": p, "winners": [_best(wins, cands, seed)[0]], "ranking": _best(wins, cands, seed, len(cands))}


# ---- seats for party lists ---------------------------------------------------------------------------------------------------
def _passing(votes, threshold_bp):
    total = sum(votes.values())
    return {p: v for p, v in votes.items() if v * 10000 >= threshold_bp * total}


def highest_averages(votes, seats, divisor, threshold_bp=0, seed=""):
    """votes: {party: n}; divisor(k) for the party's (k+1)th seat as a Fraction. D'Hondt k+1; Sainte-Lague 2k+1; modified
    Sainte-Lague 7/5 for the first seat."""
    ok = _passing(votes, threshold_bp)
    got = {p: 0 for p in votes}
    order = lots(list(ok), seed)
    for _ in range(seats):
        if not ok:
            break
        best = max(ok, key=lambda p: (Fraction(ok[p]) / divisor(got[p]), -order.index(p)))
        got[best] += 1
    return got


def dhondt(votes, seats, threshold_bp=0, seed=""):
    return {"seats": highest_averages(votes, seats, lambda k: Fraction(k + 1), threshold_bp, seed)}


def sainte_lague(votes, seats, threshold_bp=0, seed=""):
    return {"seats": highest_averages(votes, seats, lambda k: Fraction(2 * k + 1), threshold_bp, seed)}


def modified_sainte_lague(votes, seats, threshold_bp=0, seed=""):
    n, d = VOTE["methods"]["modified_sainte_lague"]["first_divisor"]
    return {"seats": highest_averages(votes, seats, lambda k: Fraction(n, d) if k == 0 else Fraction(2 * k + 1), threshold_bp, seed)}


def largest_remainder(votes, seats, quota="hare", threshold_bp=0, seed=""):
    """Whole quotas first, then the largest remainders. Hare votes / seats; Droop floor(votes / (seats + 1)) + 1; Imperiali
    votes / (seats + 2). If whole quotas give more seats than there are (possible with Imperiali), the lowest remainders give
    seats back."""
    ok = _passing(votes, threshold_bp)
    total = sum(ok.values())
    got = {p: 0 for p in votes}
    if not ok or total == 0:
        return {"seats": got, "quota": None}
    q = {"hare": Fraction(total, seats), "droop": Fraction(total // (seats + 1) + 1), "imperiali": Fraction(total, seats + 2)}[quota]
    rem, order = {}, lots(list(ok), seed)
    for p, v in ok.items():
        whole = int(Fraction(v) // q)
        got[p] = whole
        rem[p] = Fraction(v) - whole * q
    left = seats - sum(got.values())
    by_rem = sorted(ok, key=lambda p: (-rem[p], order.index(p)))
    for p in by_rem[:max(left, 0)]:
        got[p] += 1
    for p in reversed(by_rem):
        if sum(got.values()) <= seats:
            break
        if got[p] > 0:
            got[p] -= 1
    return {"seats": got, "quota": _fr(q)}


# ---- one door for every method -----------------------------------------------------------------------------------------------
METHODS = {"plurality": plurality, "two_round": two_round, "approval": approval, "weighted": weighted, "cumulative": cumulative,
           "quadratic": quadratic, "score": score, "star": star, "majority_judgment": majority_judgment, "budget": budget,
           "irv": irv, "stv": stv, "borda": borda, "bucklin": bucklin, "ranked_pairs": ranked_pairs, "schulze": schulze,
           "dhondt": dhondt, "sainte_lague": sainte_lague, "modified_sainte_lague": modified_sainte_lague, "yes_no": yes_no}


def what_if(method, *args, **kw):
    """The same ballots counted another way: for learning only, always labelled, never the official result."""
    if method.startswith("largest_remainder_"):
        out = largest_remainder(*args, quota=method.split("_")[-1], **kw)
    else:
        out = METHODS[method](*args, **kw)
    return {**out, "label": "what_if", "official": False}
