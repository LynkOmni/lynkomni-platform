"""LynkVote in the cloud (VOTE UPDATE, master blueprint 68; section 4 step E2), on the security core of core/vote_crypto.py and the
counting methods of core/vote_count.py (catalog/vote.v1.json).

A vote goes from set-up to certified result through the events of contract version 12. The cloud:
- keeps the rules and locks them when voting opens; a later change needs two different people and a reason, and shows in the log;
- runs the key ceremony with the trustees: it keeps only their public parts and proofs, never a key part;
- builds the roll from LynkCRM, LynkAcc, LynkAttend or a Move in file (the check report first, nothing goes in with an error); names
  and contacts go to the PII vault, a voter's code is kept only as its fingerprint, and the plan's voter limit applies;
- takes ballots that were locked on the voter's device, checks every proof and puts each on the public list under its tracking code.
  It never sees a choice, and the list never shows who cast a ballot or when. Where the rules allow voting again, the newer ballot
  replaces the older one; the link that makes this possible is deleted when the vote closes;
- closes on time and opens only totals (or, for methods that read each ballot, the ballots after a shuffle with a proof), and only with
  a threshold of trustees whose every part carries a proof; then counts with the vote's method and publishes the results and proofs;
- certifies the result: sealed is true only when the trust-service partner confirms.

The governance home (68.9) keeps by-laws, committees, the register of decisions and who must act, and minutes signed electronically.
Federations (68.3) combine their branches' published results by a rule, never a branch's ballots or roll. LynkVote never claims to be
unhackable; LynkOmni is never the electoral body.
"""
import hashlib, json, secrets, time

from contract.tools.validate_contract import uuid7
from core import enterprise as E
from core import vote_count as C
from core import vote_crypto as V
from services.improvements import Table
from services.vote_partners import SandboxVoteIdentity, SandboxVotePost, SandboxVoteSeal

REG = V.VOTE


def _sha(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()


def _fp(code):
    return hashlib.sha256(("lynkvote-code|" + code).encode()).hexdigest()


class Voting:
    def __init__(s, p, now=time.time, identity=None, seal=None, post=None):
        s.p, s.now, db = p, now, p.c.store.db
        s.identity, s.seal, s.post = identity or SandboxVoteIdentity(), seal or SandboxVoteSeal(), post or SandboxVotePost()
        s.votes, s.voters, s.ballots, s.links = Table(db, "vote_votes"), Table(db, "vote_voters"), Table(db, "vote_ballots"), Table(db, "vote_links")
        s.gov, s.decisions, s.minutes, s.history = Table(db, "vote_gov"), Table(db, "vote_decisions"), Table(db, "vote_minutes"), Table(db, "vote_history")

    # ---- helpers ---------------------------------------------------------------------------------------------------------------
    def _emit(s, m, type_, payload):
        s.p.c.store.append(m, "server", type_, payload)

    def _vote(s, m, vid):
        v = s.votes.get(vid)
        if not v or v["merchant"] != m:
            raise KeyError("no such vote")
        return v

    def _need(s, v, *states):
        if v["state"] not in states:
            raise ValueError(f"the vote is {v['state']}")

    def limit(s, m):
        return s.p.billing.entitlement(m, "lynkvote")

    @staticmethod
    def contests_for(method, candidates, seats=1, top=None, points=None, weight=1):
        """The contest a ballot must fit, from the method's ballot type; the proofs check it, so a ballot can only hold allowed values.
        A weighted vote gives a voter of weight w one choice worth w (the weight is on the roll; the choice stays locked)."""
        n = len(candidates)
        ballot = REG["methods"][method]["ballot"]
        if ballot == "choose":
            return [{"id": "main", "options": n, "values": [0, weight], "totals": [weight]}]
        if ballot == "approve":
            return [{"id": "main", "options": n, "values": [0, 1], "totals": list(range(n + 1))}]
        if ballot == "scores":
            top = top or 5
            return [{"id": "main", "options": n, "values": list(range(top + 1)), "totals": list(range(top * n + 1))}]
        if ballot == "points":
            points = points or n
            return [{"id": "main", "options": n, "values": list(range(points + 1)), "totals": [points]}]
        if ballot in ("grades", "credits"):
            top = top or (5 if ballot == "grades" else 3)                       # grades 0..top; credits: at most top votes on one choice
            return [{"id": "main", "options": n, "values": list(range(top + 1)), "totals": list(range(top * n + 1))}]
        if ballot == "rank":
            return [{"id": "main", "options": n, "values": list(range(n + 1)), "totals": list(range(n * (n + 1) // 2 + 1))}]
        raise ValueError(f"ballot type {ballot} is built with its method's screens")

    # ---- set-up ----------------------------------------------------------------------------------------------------------------
    def create(s, m, by, kind, method, candidates, assurance="basic", ways=("online_link",), seats=1, trustees=3, threshold=2,
               vote_again=False, majority="simple", quorum=None, closes_at=None, federation_id=None, top=None, points=None,
               costs=None, budget_total=None):
        if kind not in REG["kinds"] or method not in REG["methods"] or assurance not in REG["assurance"]:
            raise ValueError("unknown kind, method or assurance level")
        if any(w not in REG["ways"] for w in ways):
            raise ValueError("unknown way to vote")
        if assurance == "public_election":
            raise PermissionError("Coming to your country soon.")     # only where the law allows and after certification (ledger later vote_certification)
        if not (REG["trustees"]["min"] <= trustees <= REG["trustees"]["max"]) or not (trustees // 2 < threshold <= trustees):
            raise ValueError("trustees: " + REG["trustees"]["threshold_rule"])
        if len(set(candidates)) != len(candidates) or len(candidates) < 2:
            raise ValueError("at least two different choices")
        if federation_id:
            fed = s.votes.get(federation_id)
            if not fed or not fed.get("federation") or m not in fed["branches"]:
                raise PermissionError("a branch vote needs the federation's link")
        if method == "budget" and (not isinstance(costs, dict) or set(costs) != set(candidates) or not isinstance(budget_total, int)
                                   or any(isinstance(c, bool) or not isinstance(c, int) or c <= 0 for c in costs.values())):
            raise ValueError("a budget vote needs each project's cost and the total, in whole minor units")
        vid = uuid7()
        public = s.p.ids.assign("VOT", vid)
        contests = s.contests_for(method, candidates, seats, top, points)
        rules = {"kind": kind, "method": method, "candidates": list(candidates), "seats": seats, "assurance": assurance, "ways": list(ways),
                 "trustees": trustees, "threshold": threshold, "vote_again": vote_again, "majority": majority, "quorum": quorum,
                 "closes_at": closes_at, "contests": contests, "top": top, "points": points, "costs": costs, "budget_total": budget_total,
                 "seed": secrets.token_hex(16)}
        s.votes.put(vid, {"id": vid, "public_id": public, "merchant": m, "by": by, "state": "set_up", "rules": rules, "publics": [],
                          "roll": [], "roll_locked": False, "extra_voters": 0, "federation_id": federation_id, "federation": None, "branches": []})
        ev = {"vote_id": vid, "kind": kind, "method": method, "assurance": assurance, "contests": len(contests)}
        if federation_id:
            ev["federation_id"] = federation_id
        s._emit(m, "VoteCreated", ev)
        return vid

    def change_rules(s, m, vid, changes, reason, approvers):
        """Before opening, the organiser changes rules freely. After the rules lock, two different authorised people and a reason."""
        v = s._vote(m, vid)
        s._need(v, "set_up", "roll_ready", "open")
        if any(k in changes for k in ("method", "candidates", "contests", "seed", "trustees", "threshold")) and v["state"] == "open":
            raise PermissionError("what a ballot holds and who opens it never change while voting is open")
        rules = dict(v["rules"], **changes)
        if v["state"] == "open":
            if len(set(approvers)) < 2:
                raise PermissionError("a change after the rules locked needs two different people")
            s._emit(m, "VoteRulesChanged", {"vote_id": vid, "rules_sha256": _sha(rules), "reason": reason, "approvers": len(set(approvers))})
        v["rules"] = rules
        return _sha(rules)

    # ---- the key ceremony ------------------------------------------------------------------------------------------------------
    def key_ceremony(s, m, vid, rng=None):
        """Each trustee makes their key part on their own device; the cloud receives only the public part with its proof. This sandbox
        ceremony returns the key parts to the trustees (the caller) and keeps none of them."""
        v = s._vote(m, vid)
        s._need(v, "set_up")
        rng = rng or V.real_rng()
        n, t = v["rules"]["trustees"], v["rules"]["threshold"]
        parts = [V.trustee_part(i, t, rng, vid) for i in range(1, n + 1)]
        for part in parts:
            s.publish_trustee(m, vid, part["public"])
        keys = {j: sum(V.share_for(p, j) for p in parts) % V.Q for j in range(1, n + 1)}   # handed privately to each trustee
        return keys

    def publish_trustee(s, m, vid, public):
        v = s._vote(m, vid)
        s._need(v, "set_up")
        ok = V.check_part(public, vid)
        if not ok:
            raise ValueError("the trustee's proof does not check")
        if any(p["index"] == public["index"] for p in v["publics"]):
            raise ValueError("this trustee already published")
        v["publics"] = v["publics"] + [public]
        s._emit(m, "TrusteeKeyPublished", {"vote_id": vid, "trustee": public["index"], "commitments_sha256": _sha(public["commits"]), "proof_ok": True})

    def key(s, v):
        return V.joint_key(v["publics"])

    # ---- the roll --------------------------------------------------------------------------------------------------------------
    def import_roll(s, m, vid, source, header, rows, consent_id):
        """Members from LynkCRM, LynkAcc, LynkAttend or a Move in file become voters, with the organisation's consent record.
        Returns the check report; nothing goes in while it has an error."""
        v = s._vote(m, vid)
        s._need(v, "set_up")
        if v["roll_locked"]:
            raise ValueError("the roll is locked")
        if source not in ("lynkcrm", "lynkacc", "lynkattend", "upload"):
            raise ValueError("unknown roll source")
        report = E.check("voters", header, rows)
        have = {x["ref"] for x in v["roll"]}
        dup = [n for n, r in enumerate(rows, 1) if r[header.index("ref")].strip() in have]
        for n in dup:
            report["errors"].append({"row": n, "column": "ref", "issue": "already_on_roll"})
        report["ok"] = not report["errors"]
        if not report["ok"]:
            return report
        ent, total = s.limit(m), len(v["roll"]) + len(rows)
        cap = ent.get("voters_per_vote")
        extra = 0
        if cap is not None and total > cap:
            if not ent.get("extra_1000_voters_cents"):
                raise PermissionError("this plan covers {} voters in a vote; choose a bigger plan to add more".format(cap))
            extra = -(-(total - cap) // 1000)            # whole blocks of 1,000, billed by the plan's extra price
        idx = {c: i for i, c in enumerate(header)}
        get = lambda r, c: (r[idx[c]].strip() if c in idx and idx[c] < len(r) else "")
        codes = {}
        roll = list(v["roll"])
        for r in rows:
            ref = get(r, "ref")
            vault = {f: s.p.vault.put(f"{vid}|{ref}", f, get(r, f)) for f in ("name", "email", "phone") if get(r, f)}
            code = secrets.token_urlsafe(12)
            codes[ref] = code                                                                  # sent to the voter only, never stored
            roll.append({"ref": ref, "group": get(r, "group") or None, "weight": int(get(r, "weight") or 1), "vault": vault})
            s.voters.put(f"{vid}|{_fp(code)}", {"ref": ref, "used": False})
        v["roll"], v["extra_voters"] = roll, extra
        s._emit(m, "VoteRollImported", {"vote_id": vid, "source": source, "voters": len(rows), "consent_id": consent_id})
        report["codes"] = codes
        return report

    def lock_roll(s, m, vid):
        v = s._vote(m, vid)
        s._need(v, "set_up")
        if not v["roll"]:
            raise ValueError("the roll is empty")
        v["roll_locked"], v["state"] = True, "roll_ready"
        s._emit(m, "VoteRollLocked", {"vote_id": vid, "voters": len(v["roll"]), "roll_sha256": _sha(sorted(x["ref"] for x in v["roll"]))})

    def reissue(s, m, vid, ref, reason):
        """A voter lost their link or code: the old one stops working and a new one is sent. Who it was is never in the event."""
        v = s._vote(m, vid)
        s._need(v, "roll_ready", "open")
        old = [k for k, x in s.voters.items() if k.startswith(vid + "|") and x["ref"] == ref]
        if not old:
            raise KeyError("not on the roll")
        if any(s.voters.get(k)["used"] for k in old):
            raise PermissionError("this voter has already voted")
        for k in old:
            s.voters.pop(k)
        code = secrets.token_urlsafe(12)
        s.voters.put(f"{vid}|{_fp(code)}", {"ref": ref, "used": False})
        s._emit(m, "VoteCredentialReissued", {"vote_id": vid, "reason": reason})
        return code

    # ---- voting ----------------------------------------------------------------------------------------------------------------
    def open(s, m, vid):
        v = s._vote(m, vid)
        s._need(v, "roll_ready")
        if len(v["publics"]) != v["rules"]["trustees"]:
            raise ValueError("every trustee must publish their key part first")
        s._emit(m, "VoteRulesLocked", {"vote_id": vid, "rules_sha256": _sha(v["rules"])})
        v["state"], v["head"] = "open", "start"
        s._emit(m, "VoteOpened", {"vote_id": vid, "key_sha256": _sha(str(s.key(v)))})

    def cast(s, m, vid, code, ballot, way="online_link"):
        """A ballot locked on the voter's device arrives with the voter's code. The cloud checks the code and every proof, puts the
        ballot on the public list and returns the tracking code (the receipt). It never learns the choice."""
        v = s._vote(m, vid)
        s._need(v, "open")
        if way not in v["rules"]["ways"]:
            raise PermissionError("this way to vote is not open for this vote")
        voter = s.voters.get(f"{vid}|{_fp(code)}")
        if not voter:
            raise PermissionError("this code is not on the roll")
        if voter["used"] and not v["rules"]["vote_again"]:
            raise PermissionError("already voted")
        if not V.check_ballot(s.key(v), vid, s.ballot_contests(m, vid, code), ballot):
            raise ValueError("ballot_proof_failed")
        tcode = V.tracking_code(v["head"], vid, ballot)
        s.ballots.put(f"{vid}|{tcode}", {"code": tcode, "ballot": ballot, "counts": True})
        link = f"{vid}|{_fp(code)}"
        prev = s.links.get(link)
        if prev:
            old = s.ballots.get(f"{vid}|{prev['code']}")
            old["counts"] = False
            s._emit(m, "BallotReplaced", {"vote_id": vid, "tracking_code": prev["code"], "by": "vote_again"})
        if v["rules"]["vote_again"]:
            s.links.put(link, {"code": tcode})                       # deleted at closing, so no ballot can be tied to a voter afterwards
        voter["used"] = True
        v["head"] = tcode
        s._emit(m, "BallotCast", {"vote_id": vid, "tracking_code": tcode, "way": way})
        return tcode

    def ballot_contests(s, m, vid, code):
        """What the voter's device locks against: the vote's contest, or for a weighted vote the one sized by the voter's weight."""
        v = s._vote(m, vid)
        r = v["rules"]
        if r["method"] != "weighted":
            return r["contests"]
        voter = s.voters.get(f"{vid}|{_fp(code)}")
        w = next(x["weight"] for x in v["roll"] if x["ref"] == voter["ref"])
        return s.contests_for("weighted", r["candidates"], weight=w)

    def challenged(s, m, vid, tracking_code):
        """The voter tested the device instead of casting: recorded, never counted."""
        s._need(s._vote(m, vid), "open")
        s._emit(m, "BallotChallenged", {"vote_id": vid, "tracking_code": tracking_code})

    def public_list(s, vid):
        v = s.votes.get(vid)
        entries = [x for k, x in s.ballots.items() if k.startswith(vid + "|")]
        return {"codes": sorted(x["code"] for x in entries), "head": v.get("head"), "replaced": sorted(x["code"] for x in entries if not x["counts"])}

    def remind(s, m, vid, round_):
        v = s._vote(m, vid)
        s._need(v, "open")
        waiting = [x["ref"] for k, x in s.voters.items() if k.startswith(vid + "|") and not x["used"]]
        s._emit(m, "VoteReminderSent", {"vote_id": vid, "round": round_})
        return len(waiting)

    def close(s, m, vid):
        v = s._vote(m, vid)
        s._need(v, "open")
        for k, _ in s.links.items():
            if k.startswith(vid + "|"):
                s.links.pop(k)
        n = sum(1 for k, x in s.ballots.items() if k.startswith(vid + "|") and x["counts"])
        v["state"] = "closed"
        s._emit(m, "VoteClosed", {"vote_id": vid, "ballots": n, "list_head": v["head"] if v["head"] != "start" else _sha("empty")})
        return n

    # ---- counting --------------------------------------------------------------------------------------------------------------
    def _counted(s, vid):
        return [x["ballot"] for k, x in s.ballots.items() if k.startswith(vid + "|") and x["counts"]]

    def to_open(s, m, vid, rng=None):
        """What the trustees must open. Totals for homomorphic methods; for methods that read each ballot, every ballot row after a
        shuffle with its proof (BallotsShuffled), so no row can be tied to its tracking code."""
        v = s._vote(m, vid)
        s._need(v, "closed")
        ballots = s._counted(vid)
        n = len(v["rules"]["candidates"])
        if REG["methods"][v["rules"]["method"]]["secret_count"] == "homomorphic":
            cts = [V.multiply([b[0]["cts"][i] for b in ballots]) if ballots else V.encrypt(s.key(v), 0, 0) for i in range(n)]
            v["opening"] = {"mode": "totals", "cts": cts}
        else:
            rows = [b[0]["cts"] for b in ballots]
            sh = V.shuffle(s.key(v), rows, rng or V.real_rng(), vid, rounds=REG["shuffle"]["rounds"]) if rows else {"rows": [], "proof": []}
            if rows and not V.check_shuffle(s.key(v), rows, sh, vid):
                raise ValueError("the shuffle proof does not check")
            v["opening"] = {"mode": "rows", "cts": [ct for row in sh["rows"] for ct in row], "width": n}
            s._emit(m, "BallotsShuffled", {"vote_id": vid, "round": 1, "proof_sha256": _sha(sh["proof"])})
        return v["opening"]["cts"]

    def publish_tally(s, m, vid, parts_by_trustee):
        """parts_by_trustee: {trustee index: [one partial opening per value to open, each with its proof]}. Every part must check
        and a threshold of trustees must take part; then the totals are read and counted with the vote's method."""
        v = s._vote(m, vid)
        s._need(v, "closed")
        op, rules = v["opening"], v["rules"]
        if len(parts_by_trustee) < rules["threshold"]:
            raise PermissionError("a threshold of trustees must open the count together")
        for j, parts in parts_by_trustee.items():
            if len(parts) != len(op["cts"]) or not all(V.check_partial(v["publics"], p, ct, f"{vid}:{i}") for i, (p, ct) in enumerate(zip(parts, op["cts"]))):
                raise ValueError(f"trustee {j}'s opening does not check")
        chosen = sorted(parts_by_trustee)[:rules["threshold"]]
        heaviest = max([x["weight"] for x in v["roll"]] or [1])
        limit = max(1, len(s._counted(vid))) * max(rules.get("top") or 5, rules.get("points") or 1, len(rules["candidates"]), heaviest)
        values = [V.combine(ct, [parts_by_trustee[j][i] for j in chosen], limit) for i, ct in enumerate(op["cts"])]
        results = s._count(rules, op, values)
        proofs = {"parts": {str(j): parts_by_trustee[j] for j in chosen}, "opened": values}
        v["results"], v["state"] = results, "counted"
        s._emit(m, "TallyPublished", {"vote_id": vid, "results_sha256": _sha(results), "proofs_sha256": _sha(proofs), "trustees": len(chosen)})
        return results

    @staticmethod
    def trustee_open(publics, j, x_j, cts, vid, rng=None):
        """Runs on trustee j's own device: its part of opening each value, each with its proof. The key part never leaves it."""
        rng = rng or V.real_rng()
        return [V.partial_open(publics, j, x_j, ct, rng, f"{vid}:{i}") for i, ct in enumerate(cts)]

    @staticmethod
    def _count(rules, op, values):
        cands, method, seed, seats = rules["candidates"], rules["method"], rules["seed"], rules["seats"]
        if op["mode"] == "totals":
            totals = dict(zip(cands, values))
            marks = [c for c in cands for _ in range(totals[c])]                  # the totals read as one mark per vote counted
            one = [totals]                                                         # or as one combined ballot
            if method == "yes_no":
                out = C.yes_no(marks, rules["majority"], quorum=rules.get("quorum"))
            elif method in ("plurality", "weighted"):
                out = C.plurality(marks, cands, seats, seed=seed)
            elif method == "two_round":
                out = C.two_round(marks, cands, seed=seed)
            elif method == "approval":
                out = C.score(one, cands, max(values + [1]), seats, seed=seed)
            elif method == "score":
                out = C.score(one, cands, max(values + [1]), seats, seed=seed)
            elif method == "cumulative":
                out = C.cumulative(one, cands, sum(values), seats, seed=seed)
            elif method == "budget":
                out = C.budget(one, rules["costs"], rules["budget_total"], seed=seed)
            elif method in ("dhondt", "sainte_lague", "modified_sainte_lague"):
                out = getattr(C, method)(totals, seats, seed=seed)
            elif method.startswith("largest_remainder_"):
                out = C.largest_remainder(totals, seats, method.rsplit("_", 1)[1], seed=seed)
            else:
                raise ValueError(f"{method} is not counted from totals")
            return dict(out, totals=totals, method=method, official=True)
        w = op["width"]
        rows = [values[i:i + w] for i in range(0, len(values), w)]
        ballot = REG["methods"][method]["ballot"]
        if ballot != "rank":
            marked = [dict(zip(cands, row)) for row in rows]
            if method == "star":
                out = C.star(marked, cands, rules.get("top") or 5, seed=seed)
            elif method == "majority_judgment":
                out = C.majority_judgment(marked, cands, rules.get("top") or 5, seed=seed)
            else:
                out = C.quadratic(marked, cands, (rules.get("top") or 3) ** 2, seed=seed)
            return dict(out, method=method, official=True)
        ballots, spoilt = [], 0
        for row in rows:
            ranks = [r for r in row if r]
            if len(set(ranks)) != len(ranks) or sorted(ranks) != list(range(1, len(ranks) + 1)):
                spoilt += 1                                                       # a rank list that skips or repeats is published as spoilt
                continue
            ballots.append([cands[i] for i in sorted((i for i in range(w) if row[i]), key=lambda i: row[i])])
        fn = getattr(C, method)
        out = fn(ballots, cands, seats, seed=seed) if method == "stv" else fn(ballots, cands, seed=seed)
        return dict(out, spoilt=spoilt, method=method, official=True)

    def certify(s, m, vid):
        """The official result: signed and published; sealed only when the trust-service partner confirms."""
        v = s._vote(m, vid)
        s._need(v, "counted")
        cert = _sha({"vote": v["public_id"], "results": v["results"], "rules": _sha(v["rules"])})
        answer = s.seal.seal(vid, cert)
        v["state"] = "certified"
        s._emit(m, "VoteResultCertified", {"vote_id": vid, "certificate_sha256": cert, "sealed": bool(answer.get("sealed"))})
        return {"certificate_sha256": cert, "sealed": bool(answer.get("sealed")), "seal_state": answer.get("state")}

    def flag(s, m, vid, kind):
        """An unusual pattern for the organiser and observers to look at; it never removes a ballot and never names anyone."""
        s._vote(m, vid)
        s._emit(m, "VoteAnomalyFlagged", {"vote_id": vid, "kind": kind})

    # ---- federations -----------------------------------------------------------------------------------------------------------
    def create_federation(s, m, by, kind, method, candidates, rule="pooled", seats=1):
        if rule not in REG["federation"]["rules"]:
            raise ValueError("unknown federation rule")
        fid = s.create(m, by, kind, method, candidates, seats=seats)
        f = s.votes.get(fid)
        f["federation"] = rule
        return fid

    def link_branch(s, m, fid, branch, consent_id):
        f = s._vote(m, fid)
        if not f.get("federation") or not consent_id:
            raise PermissionError("a branch joins with its own consent")
        f["branches"] = f["branches"] + [branch]

    def federation_result(s, m, fid):
        """Combines only the branches' published results. A branch below the small-group rule is in the total, never shown alone."""
        f = s._vote(m, fid)
        rule, cands = f["federation"], f["rules"]["candidates"]
        branch_votes = [x for _, x in s.votes.items() if x.get("federation_id") == fid and x["state"] in ("counted", "certified")]
        small = REG["small_group_min"]
        pooled, shown, branch_wins, delegates = {c: 0 for c in cands}, [], {c: 0 for c in cands}, {c: 0 for c in cands}
        for b in branch_votes:
            totals = b["results"].get("totals") or {}
            n = sum(totals.values())
            for c in cands:
                pooled[c] += totals.get(c, 0)
            if b["results"].get("winners"):
                branch_wins[b["results"]["winners"][0]] += 1
            if rule == "delegates":
                for c, seats in C.dhondt(totals, b["rules"]["seats"], seed=b["rules"]["seed"])["seats"].items():
                    delegates[c] += seats
            if n >= small:
                shown.append({"vote": b["public_id"], "totals": totals})
        score = {"pooled": pooled, "branch_vote": branch_wins, "delegates": delegates}[rule]
        ranked = sorted(cands, key=lambda c: (-score[c], C.lots(cands, f["rules"]["seed"]).index(c)))
        return {"rule": rule, "score": score, "winners": ranked[:f["rules"]["seats"]], "branches": len(branch_votes), "shown": shown,
                "hidden": len(branch_votes) - len(shown)}

    # ---- the governance home ---------------------------------------------------------------------------------------------------
    def set_up_governance(s, m, by, org_kind, bylaws_sha256=None):
        tpl = REG["governance"]["templates"].get(org_kind)
        if tpl is None:
            raise ValueError("no template for this kind of organisation; start from a blank set of rules")
        s.gov.put(m, {"kind": org_kind, "rules": dict(tpl), "bylaws_sha256": bylaws_sha256, "committees": {}, "by": by})
        return dict(tpl)

    def add_committee(s, m, cid, members):
        """members: {member ref: role}; roles from the register; names stay in LynkCRM or the vault."""
        g = s.gov.get(m)
        if any(r not in REG["governance"]["roles"] + ["chair", "secretary", "clerk", "member"] for r in members.values()):
            raise ValueError("unknown role")
        g["committees"] = dict(g["committees"], **{cid: dict(members)})

    def record_decision(s, m, outcome, actions=(), vote_id=None, due=None):
        """actions: [{"who": member ref, "what": text}] kept in the register; the event carries only how many are owed."""
        if outcome not in REG["governance"]["outcomes"]:
            raise ValueError("unknown outcome")
        if vote_id:
            v = s._vote(m, vote_id)
            if v["state"] not in ("counted", "certified"):
                raise ValueError("a decision from a vote waits for its count")
        did = uuid7()
        s.decisions.put(did, {"id": did, "merchant": m, "outcome": outcome, "vote_id": vote_id, "due": due,
                              "actions": [dict(a, done=False) for a in actions]})
        ev = {"decision_id": did, "outcome": outcome, "actions": len(actions)}
        if vote_id:
            ev["vote_id"] = vote_id
        if due:
            ev["due"] = due
        s._emit(m, "DecisionRecorded", ev)
        return did

    def owed(s, m, who=None):
        """The register's open actions, for the person who must act or for everyone."""
        return [dict(a, decision=d["id"]) for _, d in s.decisions.items() if d["merchant"] == m
                for a in d["actions"] if not a["done"] and (who is None or a["who"] == who)]

    def action_done(s, m, did, index):
        d = s.decisions.get(did)
        if not d or d["merchant"] != m:
            raise KeyError("no such decision")
        acts = [dict(a) for a in d["actions"]]
        acts[index]["done"] = True
        d["actions"] = acts

    def draft_minutes(s, m, text):
        g = s.gov.get(m)
        if not g:
            raise ValueError("set up the governance home first")
        mid = uuid7()
        s.minutes.put(mid, {"merchant": m, "sha256": hashlib.sha256(text.encode()).hexdigest(), "need": list(g["rules"]["minutes_signers"]), "signed": {}})
        return mid

    def sign_minutes(s, m, mid, role, who):
        """Each required role signs once; when all have signed, the minutes are final and MinutesSigned is written."""
        x = s.minutes.get(mid)
        if not x or x["merchant"] != m:
            raise KeyError("no such minutes")
        if role not in x["need"] or role in x["signed"]:
            raise PermissionError("not a signer, or already signed")
        if who in x["signed"].values():
            raise PermissionError("one person signs once, in one role")
        x["signed"] = dict(x["signed"], **{role: who})
        if set(x["signed"]) == set(x["need"]):
            s._emit(m, "MinutesSigned", {"minutes_id": mid, "minutes_sha256": x["sha256"], "signers": len(x["signed"])})
            return True
        return False

    # ---- move in -----------------------------------------------------------------------------------------------------------------
    def move_in_history(s, m, rows):
        """Past votes from another voting service, kept as read-only history labelled as moved in; LynkOmni never re-certifies them."""
        out = []
        for r in rows:
            if not r.get("title") or not isinstance(r.get("totals"), dict) or any(isinstance(n, bool) or not isinstance(n, int) or n < 0 for n in r["totals"].values()):
                raise ValueError("each past vote needs a title and whole-number totals")
            hid = uuid7()
            s.history.put(hid, {"merchant": m, "title": r["title"], "totals": r["totals"], "held_on": r.get("held_on"), "label": "moved_in"})
            out.append(hid)
        return out
