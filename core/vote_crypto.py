"""LynkVote's security core (VOTE UPDATE, master blueprint 68.7; section 4 step E1), read from catalog/vote.v1.json.

Exponential ElGamal in the subgroup of order q of the RFC 7919 group ffdhe2048:
  * a choice is locked on the voter's device as (A, B) = (g^r, g^m h^r) and the server never sees m;
  * the key h is made by trustees together (Feldman shares with published commitments and a proof of each part); any threshold of
    them opens a total, and no smaller group and not LynkOmni can;
  * every locked choice carries a proof that it is one of the allowed values (a disjunctive Chaum-Pedersen proof), and each
    contest a proof that its choices add up to an allowed number, so a ballot cannot vote twice or vote negative;
  * totals are added while still locked (multiply the ciphertexts) and opened by the trustees, each with a proof that they used
    their real key part; nobody ever opens a single ballot in such a count;
  * ballots that must be read one by one (ranked, scores) are first shuffled and re-locked with a proof (cut and choose), so the
    order and the link to the voter are gone before they are opened;
  * each locked ballot gets a tracking code that chains the public list; the voter may challenge the device before casting.
Challenges are SHA-256 of the vote's id and every public value (Fiat-Shamir). Random numbers come from a function passed in:
secrets in real use, a seeded HMAC stream only for the shared test answers.

This module is the Python reference; ts/src/votecrypto.ts must agree on every case of contract/vectors/vote.v1.json."""
import copy, hashlib, hmac, json, os, secrets

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
with open(os.path.join(ROOT, "catalog", "vote.v1.json"), encoding="utf-8") as _f:
    VOTE = json.load(_f)

P = int(VOTE["group"]["p_hex"], 16)
Q = (P - 1) // 2
G = VOTE["group"]["g"]


# ---- randomness and hashing --------------------------------------------------------------------------------------------------
def real_rng():
    """Random numbers for real use: 1 <= r < q from the operating system."""
    return lambda: secrets.randbelow(Q - 1) + 1


def seeded_rng(seed):
    """Repeatable numbers for the shared test answers only: HMAC-SHA256(seed, counter), 512 bits, reduced into 1 <= r < q."""
    n = [0]

    def nxt():
        n[0] += 1
        d = hmac.new(seed.encode(), f"{n[0]}:a".encode(), hashlib.sha256).digest() + hmac.new(seed.encode(), f"{n[0]}:b".encode(), hashlib.sha256).digest()
        return int.from_bytes(d, "big") % (Q - 1) + 1
    return nxt


def _enc(x):
    return format(x, "x") if isinstance(x, int) else str(x)


def challenge(*items):
    """The Fiat-Shamir challenge: SHA-256 of the items as lowercase hex (numbers) or text, joined by '|', modulo q."""
    return int(hashlib.sha256("|".join(_enc(i) for i in items).encode()).hexdigest(), 16) % Q


def inv(x):
    return pow(x, -1, P)


# ---- the trustees' key ---------------------------------------------------------------------------------------------------------
def trustee_part(index, threshold, rng, vote_id):
    """One trustee's key part: a secret polynomial of degree threshold - 1, its public commitments g^a_k, and a proof that the
    trustee knows a_0 (a Schnorr proof)."""
    coeffs = [rng() for _ in range(threshold)]
    commits = [pow(G, a, P) for a in coeffs]
    w = rng()
    t = pow(G, w, P)
    c = challenge("key", vote_id, index, commits[0], t)
    return {"index": index, "coeffs": coeffs, "public": {"index": index, "commits": commits, "proof": {"t": t, "z": (w + c * coeffs[0]) % Q}}}


def check_part(public, vote_id):
    pr = public["proof"]
    c = challenge("key", vote_id, public["index"], public["commits"][0], pr["t"])
    return pow(G, pr["z"], P) == pr["t"] * pow(public["commits"][0], c, P) % P


def share_for(part, j):
    """What trustee `part` hands to trustee j (privately): f(j) mod q."""
    return sum(a * pow(j, k, Q) for k, a in enumerate(part["coeffs"])) % Q


def check_share(public, j, s):
    """Trustee j checks a received share against the sender's public commitments (Feldman)."""
    rhs = 1
    for k, ck in enumerate(public["commits"]):
        rhs = rhs * pow(ck, pow(j, k, Q), P) % P
    return pow(G, s, P) == rhs


def joint_key(publics):
    """The vote's public key h: the product of every trustee's g^a_0."""
    h = 1
    for pub in publics:
        h = h * pub["commits"][0] % P
    return h


def public_share(publics, j):
    """g^x_j for trustee j, worked out by anyone from the public commitments."""
    y = 1
    for pub in publics:
        for k, ck in enumerate(pub["commits"]):
            y = y * pow(ck, pow(j, k, Q), P) % P
    return y


# ---- locking a choice ----------------------------------------------------------------------------------------------------------
def encrypt(h, m, r):
    return [pow(G, r, P), pow(G, m, P) * pow(h, r, P) % P]


def prove_in(h, ct, m, r, allowed, rng, ctx):
    """A proof that ct locks one of `allowed` (the real one is m), without saying which."""
    A, B = ct
    parts, sim = {}, {}
    for v in allowed:
        if v == m:
            continue
        cv, zv = rng(), rng()
        Bv = B * inv(pow(G, v, P)) % P
        parts[v] = (pow(G, zv, P) * inv(pow(A, cv, P)) % P, pow(h, zv, P) * inv(pow(Bv, cv, P)) % P)
        sim[v] = (cv, zv)
    w = rng()
    parts[m] = (pow(G, w, P), pow(h, w, P))
    c = challenge("in", ctx, A, B, *[x for v in allowed for x in parts[v]])
    cm = (c - sum(cv for cv, _ in sim.values())) % Q
    out = []
    for v in allowed:
        cv, zv = (cm, (w + cm * r) % Q) if v == m else sim[v]
        out.append([cv, zv])
    return out


def check_in(h, ct, allowed, proof, ctx):
    A, B = ct
    if len(proof) != len(allowed):
        return False
    xs = []
    for v, (cv, zv) in zip(allowed, proof):
        Bv = B * inv(pow(G, v, P)) % P
        xs += [pow(G, zv, P) * inv(pow(A, cv, P)) % P, pow(h, zv, P) * inv(pow(Bv, cv, P)) % P]
    return challenge("in", ctx, A, B, *xs) == sum(cv for cv, _ in proof) % Q


def multiply(cts):
    A, B = 1, 1
    for a, b in cts:
        A, B = A * a % P, B * b % P
    return [A, B]


def lock_ballot(h, vote_id, contests, choices, rng):
    """A ballot: for each contest, each option's value locked with its proof, and the contest's total proved allowed.
    contests: [{"id", "options": n, "values": [allowed per option], "totals": [allowed sums]}]; choices: [[value per option]]."""
    out = []
    for con, vals in zip(contests, choices):
        if len(vals) != con["options"] or any(v not in con["values"] for v in vals) or sum(vals) not in con["totals"]:
            raise ValueError("a choice outside the contest's rules")
        rs = [rng() for _ in vals]
        cts = [encrypt(h, v, r) for v, r in zip(vals, rs)]
        ctx = f"{vote_id}:{con['id']}"
        proofs = [prove_in(h, ct, v, r, con["values"], rng, f"{ctx}:{i}") for i, (ct, v, r) in enumerate(zip(cts, vals, rs))]
        tot = multiply(cts)
        total_proof = prove_in(h, tot, sum(vals), sum(rs) % Q, con["totals"], rng, f"{ctx}:total")
        out.append({"contest": con["id"], "cts": cts, "proofs": proofs, "total_proof": total_proof, "_r": rs})
    return out


def public_ballot(ballot):
    """What leaves the device: everything except the random numbers."""
    return [copy.deepcopy({k: v for k, v in c.items() if k != "_r"}) for c in ballot]   # a copy: nothing done to it changes the device's own ballot


def check_ballot(h, vote_id, contests, ballot):
    if len(ballot) != len(contests):
        return False
    for con, c in zip(contests, ballot):
        ctx = f"{vote_id}:{con['id']}"
        if c["contest"] != con["id"] or len(c["cts"]) != con["options"]:
            return False
        if not all(0 < x < P and pow(x, Q, P) == 1 for ct in c["cts"] for x in ct):
            return False
        if not all(check_in(h, ct, con["values"], pr, f"{ctx}:{i}") for i, (ct, pr) in enumerate(zip(c["cts"], c["proofs"]))):
            return False
        if not check_in(h, multiply(c["cts"]), con["totals"], c["total_proof"], f"{ctx}:total"):
            return False
    return True


# ---- the voter checks the device, and the receipt -------------------------------------------------------------------------------
def challenge_device(h, ballot, choices):
    """Test the device (Benaloh): the device reveals its random numbers; anyone re-locks the stated choices and compares.
    A challenged ballot is never cast."""
    return all(encrypt(h, v, r) == ct for c, vals in zip(ballot, choices) for v, r, ct in zip(vals, c["_r"], c["cts"]))


def tracking_code(previous, vote_id, ballot):
    """The receipt: SHA-256 of the previous code and the locked ballot, so the public list is a chain."""
    body = "|".join(_enc(x) for c in public_ballot(ballot) for ct in c["cts"] for x in ct)
    return hashlib.sha256(f"{previous}|{vote_id}|{body}".encode()).hexdigest()


def public_list(entries):
    """The published list of locked ballots: sorted by tracking code (no times, no order of arrival) with the head of the chain."""
    return {"codes": sorted(e["code"] for e in entries), "head": entries[-1]["code"] if entries else hashlib.sha256(b"empty").hexdigest()}


# ---- opening the total ---------------------------------------------------------------------------------------------------------
def partial_open(publics, j, x_j, ct, rng, ctx):
    """Trustee j's part of opening ct, with a proof (Chaum-Pedersen) that it used the same key part as its public share."""
    A = ct[0]
    d = pow(A, x_j, P)
    w = rng()
    a, b = pow(G, w, P), pow(A, w, P)
    c = challenge("open", ctx, j, A, d, a, b)
    return {"index": j, "d": d, "proof": {"a": a, "b": b, "z": (w + c * x_j) % Q}}


def check_partial(publics, part, ct, ctx):
    A, j, d, pr = ct[0], part["index"], part["d"], part["proof"]
    y = public_share(publics, j)
    c = challenge("open", ctx, j, A, d, pr["a"], pr["b"])
    return pow(G, pr["z"], P) == pr["a"] * pow(y, c, P) % P and pow(A, pr["z"], P) == pr["b"] * pow(d, c, P) % P


def lagrange_at_zero(j, indices):
    num, den = 1, 1
    for k in indices:
        if k != j:
            num = num * (-k) % Q
            den = den * (j - k) % Q
    return num * pow(den, Q - 2, Q) % Q


def combine(ct, parts, limit):
    """Open ct from a threshold of checked parts and read the small number m (0 <= m <= limit) from g^m."""
    idx = [p["index"] for p in parts]
    D = 1
    for p in parts:
        D = D * pow(p["d"], lagrange_at_zero(p["index"], idx), P) % P
    gm = ct[1] * inv(D) % P
    acc = 1
    for m in range(limit + 1):
        if acc == gm:
            return m
        acc = acc * G % P
    raise ValueError("the opened value is out of range")


# ---- shuffling before ballots are read one by one ------------------------------------------------------------------------------
def _reencrypt(h, ct, s):
    return [ct[0] * pow(G, s, P) % P, ct[1] * pow(h, s, P) % P]


def _perm(n, rng):
    idx = list(range(n))
    for i in range(n - 1, 0, -1):
        j = rng() % (i + 1)
        idx[i], idx[j] = idx[j], idx[i]
    return idx


def _apply(h, rows, perm, rand):
    """rows[i] (a list of ciphertexts) goes to place perm[i], each re-locked with rand[i][k]."""
    out = [None] * len(rows)
    for i, row in enumerate(rows):
        out[perm[i]] = [_reencrypt(h, ct, s) for ct, s in zip(row, rand[i])]
    return out


def shuffle(h, rows, rng, ctx, rounds=None):
    """Shuffle and re-lock rows of ciphertexts with a cut-and-choose proof: for each round a shadow shuffle is made and, by the
    challenge bit, either the input-to-shadow or the shadow-to-output link is revealed. A cheat survives one round in two."""
    k = VOTE["shuffle"]["rounds"] if rounds is None else rounds
    n, width = len(rows), len(rows[0]) if rows else 0
    perm, rand = _perm(n, rng), [[rng() for _ in range(width)] for _ in range(n)]
    out = _apply(h, rows, perm, rand)
    shadows = []
    for _ in range(k):
        sp, sr = _perm(n, rng), [[rng() for _ in range(width)] for _ in range(n)]
        shadows.append((sp, sr, _apply(h, rows, sp, sr)))
    bits = challenge("shuffle", ctx, *[x for row in out for ct in row for x in ct], *[x for _, _, sh in shadows for row in sh for ct in row for x in ct])
    proof = []
    for t, (sp, sr, sh) in enumerate(shadows):
        if (bits >> t) & 1 == 0:
            proof.append({"shadow": sh, "open": "in", "perm": sp, "rand": sr})
        else:
            # shadow -> output: shadow place sp[i] goes to out place perm[i], with the difference of the random numbers
            p2, r2 = [0] * n, [[0] * width for _ in range(n)]
            for i in range(n):
                p2[sp[i]] = perm[i]
                r2[sp[i]] = [(a - b) % Q for a, b in zip(rand[i], sr[i])]
            proof.append({"shadow": sh, "open": "out", "perm": p2, "rand": r2})
    return {"rows": out, "proof": proof}


def check_shuffle(h, rows, shuffled, ctx):
    out, proof = shuffled["rows"], shuffled["proof"]
    if len(out) != len(rows) or len(proof) > 256:
        return False
    bits = challenge("shuffle", ctx, *[x for row in out for ct in row for x in ct], *[x for p in proof for row in p["shadow"] for ct in row for x in ct])
    for t, p in enumerate(proof):
        want = "in" if (bits >> t) & 1 == 0 else "out"
        if p["open"] != want or sorted(p["perm"]) != list(range(len(rows))):
            return False
        src, dst = (rows, p["shadow"]) if want == "in" else (p["shadow"], out)
        if _apply(h, src, p["perm"], p["rand"]) != dst:
            return False
    return True
