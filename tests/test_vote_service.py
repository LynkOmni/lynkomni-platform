"""LynkVote in the cloud (VOTE UPDATE, master blueprint 68; section 4 step E2): services/vote.py on the security core.

A vote goes from set-up to a certified result through contract version 12; every event it writes fits the contract and carries no
choice, voter or key part. The roll comes in with its check report and the plan's limit; a code votes once (or replaces its ballot
where the rules allow); a forged ballot is refused; only a threshold of trustees with checking proofs opens the count; methods that
read each ballot see them only after a shuffle; a rule change while open needs two people; the seal is claimed only when the partner
confirms. The governance home keeps decisions, owed actions and signed minutes; federations combine only published branch results."""
import json, os, unittest

from core import vote_crypto as V
from services.vote_partners import SandboxVoteIdentity, SandboxVotePost, SandboxVoteSeal

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
V12 = json.load(open(os.path.join(ROOT, "contract", "event-payloads.v12.json"), encoding="utf-8"))["events"]
HEADER = ["ref", "name", "email", "group", "weight"]


def roll(n, start=1, weight=""):
    return [[f"M{i}", f"Member {i}", f"m{i}@example.org", "north" if i % 2 else "south", weight] for i in range(start, start + n)]


class Base(unittest.TestCase):
    def setUp(self):
        from services.platform import Platform
        self.p = Platform(); self.p.register("m1", "RW"); self.v = self.p.vote
        self.rng = V.seeded_rng("service-test")

    def run_vote(self, method, cands, choices, m="m1", **kw):
        """Sets up, rolls, opens, casts the given value lists (one per voter), closes, opens with two trustees and counts."""
        vid = self.v.create(m, "owner", kw.pop("kind", "election_one_seat"), method, cands, **kw)
        keys = self.v.key_ceremony(m, vid, self.rng)
        rep = self.v.import_roll(m, vid, "lynkcrm", HEADER, roll(len(choices)), "consent-1")
        self.v.lock_roll(m, vid); self.v.open(m, vid)
        v = self.v.votes.get(vid)
        codes = [rep["codes"][f"M{i}"] for i in range(1, len(choices) + 1)]
        for code, vals in zip(codes, choices):
            b = V.lock_ballot(self.v.key(v), vid, self.v.ballot_contests(m, vid, code), [vals], self.rng)
            self.v.cast(m, vid, code, V.public_ballot(b))
        self.v.close(m, vid)
        cts = self.v.to_open(m, vid, self.rng)
        v = self.v.votes.get(vid)
        parts = {j: self.v.trustee_open(v["publics"], j, keys[j], cts, vid, self.rng) for j in (1, 3)}
        return vid, self.v.publish_tally(m, vid, parts), keys, codes

    def events(self, m="m1"):
        return [e for e in self.p.c.store.since(m) if e["type"] in V12 and (V12[e["type"]].get("since") == "v12" or e["type"] == "VoteRollImported")]


class Flow(Base):
    def test_a_vote_from_set_up_to_certified_result(self):
        vid, res, _, _ = self.run_vote("plurality", ["A", "B", "C"], [[1, 0, 0], [0, 1, 0], [1, 0, 0], [0, 0, 1], [1, 0, 0]])
        self.assertEqual(res["winners"], ["A"])
        self.assertEqual(res["totals"], {"A": 3, "B": 1, "C": 1})
        cert = self.v.certify("m1", vid)
        self.assertFalse(cert["sealed"], "sealed only when the trust-service partner confirms")
        steps = [e["type"] for e in self.events()]
        for t in ("VoteCreated", "TrusteeKeyPublished", "VoteRollImported", "VoteRollLocked", "VoteRulesLocked", "VoteOpened",
                  "BallotCast", "VoteClosed", "TallyPublished", "VoteResultCertified"):
            self.assertIn(t, steps)
        self.assertEqual(self.p.tracking.view("vote", vid, "merchant")["step"], "results_published")
        public = self.p.tracking.view("vote", vid, "customer")
        self.assertEqual([s["id"] for s in public["steps"]], ["voting_open", "voting_closed", "counted", "results_published"])
        self.assertTrue(public["public_id"].startswith("LOVOT-"))

    def test_every_event_fits_the_contract_and_carries_no_choice_or_voter(self):
        self.run_vote("approval", ["A", "B"], [[1, 1], [1, 0], [0, 1]])
        for e in self.events():
            spec = V12[e["type"]]["payload"]
            self.assertTrue(set(spec["required"]) <= set(e["payload"]), e["type"])
            self.assertTrue(set(e["payload"]) <= set(spec["properties"]), e["type"])
            text = json.dumps(e["payload"])
            for word in ("M1", "Member", "example.org", "north"):
                self.assertNotIn(word, text, e["type"])

    def test_counting_methods_from_totals_and_from_shuffled_ballots(self):
        _, res, _, _ = self.run_vote("yes_no", ["yes", "no", "abstain"], [[1, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]], kind="motion")
        self.assertTrue(res["passed"])
        _, res, _, _ = self.run_vote("dhondt", ["P", "Q"], [[1, 0]] * 3 + [[0, 1]], kind="party_list", seats=2)
        self.assertEqual(res["seats"], {"P": 2, "Q": 0})
        _, res, _, _ = self.run_vote("irv", ["X", "Y", "Z"], [[1, 2, 3], [1, 3, 2], [2, 1, 3], [3, 1, 2], [2, 3, 1], [1, 2, 0]])
        self.assertEqual(res["winners"], ["X"])
        _, res, _, _ = self.run_vote("irv", ["X", "Y"], [[1, 1], [1, 2], [2, 1]])
        self.assertEqual(res["spoilt"], 1, "a rank list that repeats a rank is published as spoilt")
        _, res, _, _ = self.run_vote("star", ["X", "Y", "Z"], [[5, 4, 0], [0, 5, 4], [5, 0, 4]], top=5)
        self.assertEqual(res["winners"], ["X"])
        _, res, _, _ = self.run_vote("budget", ["park", "road"], [[3, 0], [2, 1]], kind="resolution", points=3,
                                     costs={"park": 500, "road": 900}, budget_total=1000)
        self.assertEqual(res["funded"], ["park"])

    def test_weighted_votes_lock_one_choice_worth_the_voters_weight(self):
        vid = self.v.create("m1", "owner", "resolution", "weighted", ["for", "against"])
        keys = self.v.key_ceremony("m1", vid, self.rng)
        rep = self.v.import_roll("m1", vid, "lynkacc", HEADER, roll(1, weight="30") + roll(1, start=2, weight="10"), "consent-2")
        self.v.lock_roll("m1", vid); self.v.open("m1", vid)
        v = self.v.votes.get(vid)
        big, small = rep["codes"]["M1"], rep["codes"]["M2"]
        with self.assertRaises(ValueError):
            V.lock_ballot(self.v.key(v), vid, self.v.ballot_contests("m1", vid, small), [[30, 0]], self.rng)   # 10 shares cannot cast 30
        for code, vals in ((big, [0, 30]), (small, [10, 0])):
            self.v.cast("m1", vid, code, V.public_ballot(V.lock_ballot(self.v.key(v), vid, self.v.ballot_contests("m1", vid, code), [vals], self.rng)))
        self.v.close("m1", vid)
        cts = self.v.to_open("m1", vid, self.rng)
        res = self.v.publish_tally("m1", vid, {j: self.v.trustee_open(v["publics"], j, keys[j], cts, vid, self.rng) for j in (2, 3)})
        self.assertEqual(res["totals"], {"for": 10, "against": 30})


class Safety(Base):
    def setUp(self):
        super().setUp()
        self.vid = self.v.create("m1", "owner", "election_one_seat", "plurality", ["A", "B"], vote_again=True)
        self.keys = self.v.key_ceremony("m1", self.vid, self.rng)
        self.codes = self.v.import_roll("m1", self.vid, "upload", HEADER, roll(3), "consent-3")["codes"]
        self.v.lock_roll("m1", self.vid); self.v.open("m1", self.vid)
        self.h = self.v.key(self.v.votes.get(self.vid))
        self.con = self.v.votes.get(self.vid)["rules"]["contests"]

    def ballot(self, vals):
        return V.public_ballot(V.lock_ballot(self.h, self.vid, self.con, [vals], self.rng))

    def test_a_forged_ballot_and_an_unknown_code_are_refused(self):
        forged = self.ballot([1, 0])
        r = self.rng(); ct = V.encrypt(self.h, 5, r)
        forged[0]["cts"][0] = ct
        forged[0]["proofs"][0] = V.prove_in(self.h, ct, 1, r, [0, 1], self.rng, f"{self.vid}:main:0")
        with self.assertRaises(ValueError):
            self.v.cast("m1", self.vid, self.codes["M1"], forged)
        with self.assertRaises(PermissionError):
            self.v.cast("m1", self.vid, "not-a-code", self.ballot([1, 0]))

    def test_voting_again_replaces_and_the_link_is_gone_after_closing(self):
        first = self.v.cast("m1", self.vid, self.codes["M1"], self.ballot([1, 0]))
        self.v.cast("m1", self.vid, self.codes["M1"], self.ballot([0, 1]))
        lst = self.v.public_list(self.vid)
        self.assertEqual(lst["replaced"], [first])
        self.assertEqual(self.v.close("m1", self.vid), 1, "only the newer ballot counts")
        self.assertEqual([k for k, _ in self.v.links.items() if k.startswith(self.vid)], [])

    def test_one_trustee_or_a_false_opening_never_opens_the_count(self):
        self.v.cast("m1", self.vid, self.codes["M1"], self.ballot([1, 0]))
        self.v.close("m1", self.vid)
        cts = self.v.to_open("m1", self.vid, self.rng)
        pubs = self.v.votes.get(self.vid)["publics"]
        one = {1: self.v.trustee_open(pubs, 1, self.keys[1], cts, self.vid, self.rng)}
        with self.assertRaises(PermissionError):
            self.v.publish_tally("m1", self.vid, one)
        lie = self.v.trustee_open(pubs, 2, self.keys[2], cts, self.vid, self.rng)
        lie[0] = dict(lie[0], d=lie[0]["d"] * V.G % V.P)
        with self.assertRaises(ValueError):
            self.v.publish_tally("m1", self.vid, {**one, 2: lie})

    def test_rule_changes_while_open_need_two_people_and_never_touch_the_ballot(self):
        with self.assertRaises(PermissionError):
            self.v.change_rules("m1", self.vid, {"closes_at": "2026-12-01T18:00:00Z"}, "time_extended_by_rule", ["chair"])
        with self.assertRaises(PermissionError):
            self.v.change_rules("m1", self.vid, {"candidates": ["A", "B", "C"]}, "other_stated", ["chair", "clerk"])
        self.v.change_rules("m1", self.vid, {"closes_at": "2026-12-01T18:00:00Z"}, "time_extended_by_rule", ["chair", "clerk"])
        self.assertIn("VoteRulesChanged", [e["type"] for e in self.events()])

    def test_a_reissued_code_cancels_the_old_one(self):
        new = self.v.reissue("m1", self.vid, "M2", "lost_code")
        with self.assertRaises(PermissionError):
            self.v.cast("m1", self.vid, self.codes["M2"], self.ballot([1, 0]))
        self.v.cast("m1", self.vid, new, self.ballot([1, 0]))

    def test_public_elections_wait_for_certification(self):
        with self.assertRaises(PermissionError):
            self.v.create("m1", "owner", "election_one_seat", "plurality", ["A", "B"], assurance="public_election")


class Roll(Base):
    def test_the_check_report_comes_first_and_the_plan_limit_applies(self):
        vid = self.v.create("m1", "owner", "motion", "yes_no", ["yes", "no", "abstain"])
        rep = self.v.import_roll("m1", vid, "upload", HEADER, roll(2) + [["M1", "Twice", "", "", ""]], "consent")
        self.assertFalse(rep["ok"])
        self.assertEqual([e["issue"] for e in rep["errors"]], ["duplicate_ref"])
        self.assertEqual(len(self.v.votes.get(vid)["roll"]), 0, "nothing goes in while the report has an error")
        with self.assertRaises(PermissionError):
            self.v.import_roll("m1", vid, "upload", HEADER, roll(101), "consent")      # Free covers 100 voters in a vote
        self.p.billing.set_plan("m1", "lynkvote", "plus")
        rep = self.v.import_roll("m1", vid, "upload", HEADER, roll(1001), "consent")
        self.assertTrue(rep["ok"])
        self.assertEqual(self.v.votes.get(vid)["extra_voters"], 1, "one extra block of 1,000 on Plus")
        stored = json.dumps(self.v.votes.get(vid)["roll"]) + json.dumps([x for _, x in self.v.voters.items()])
        self.assertNotIn("example.org", stored, "contacts live only in the PII vault")
        self.assertNotIn(rep["codes"]["M1"], stored, "a voter's code is kept only as its fingerprint")


class Governance(Base):
    def test_decisions_owed_actions_and_signed_minutes(self):
        self.assertEqual(self.v.set_up_governance("m1", "owner", "cooperative")["minutes_signers"], ["chair", "secretary"])
        vid, _, _, _ = self.run_vote("yes_no", ["yes", "no", "abstain"], [[1, 0, 0]] * 3, kind="motion")
        did = self.v.record_decision("m1", "passed", [{"who": "M1", "what": "Order the new roof"}], vote_id=vid, due="2027-01-31")
        self.assertEqual(len(self.v.owed("m1", "M1")), 1)
        self.v.action_done("m1", did, 0)
        self.assertEqual(self.v.owed("m1"), [])
        mid = self.v.draft_minutes("m1", "Meeting of 20 November: the roof was approved.")
        self.assertFalse(self.v.sign_minutes("m1", mid, "chair", "M1"))
        with self.assertRaises(PermissionError):
            self.v.sign_minutes("m1", mid, "secretary", "M1")                        # one person, one role
        self.assertTrue(self.v.sign_minutes("m1", mid, "secretary", "M2"))
        dec = [e for e in self.events() if e["type"] == "DecisionRecorded"][0]["payload"]
        self.assertNotIn("roof", json.dumps(dec), "who must act and what stays in the register")


class Federation(Base):
    def test_a_federation_combines_only_published_branch_results(self):
        for b in ("b1", "b2"):
            self.p.register(b, "RW")
        fid = self.v.create_federation("m1", "owner", "election_one_seat", "plurality", ["A", "B"], rule="branch_vote")
        with self.assertRaises(PermissionError):
            self.v.create("b1", "owner", "election_one_seat", "plurality", ["A", "B"], federation_id=fid)
        for b in ("b1", "b2"):
            self.v.link_branch("m1", fid, b, "consent-" + b)
        self.run_vote("plurality", ["A", "B"], [[1, 0]] * 5 + [[0, 1]] * 2, m="b1", federation_id=fid)
        self.run_vote("plurality", ["A", "B"], [[0, 1]] * 3, m="b2", federation_id=fid)
        r = self.v.federation_result("m1", fid)
        self.assertEqual((r["score"], r["branches"], r["hidden"]), ({"A": 1, "B": 1}, 2, 1), "the branch of 3 is never shown alone")
        self.assertEqual(len(r["shown"]), 1)


class Partners(Base):
    def test_witness_mirrors_follow_the_public_list_and_a_change_is_flagged_once(self):
        vid, _, _, _ = self.run_vote("plurality", ["A", "B"], [[1, 0], [0, 1], [1, 0]])
        self.assertEqual(set(self.v.check_mirrors("m1", vid).values()), {"same"}, "every cast reached each witness")
        w = self.v.mirrors[0]
        w.copies[vid] = {**w.copies[vid], "codes": w.copies[vid]["codes"][1:]}       # a witness's copy differs
        self.assertEqual(self.v.check_mirrors("m1", vid)["sandbox-witness-a"], "different")
        self.v.check_mirrors("m1", vid)
        flags = [e for e in self.p.c.store.of("m1", "VoteAnomalyFlagged") if e["payload"]["kind"] == "mirror_mismatch"]
        self.assertEqual(len(flags), 1, "flagged once; nothing removed")
        self.assertEqual(len(self.v.public_list(vid)["codes"]), 3)
        self.assertFalse(self.v.witnessed("m1"), "never claimed as witnessed before the witnesses are signed")
        with self.assertRaises(ValueError):
            w.publish(vid, "not-a-code", [])

    def test_sandboxes_take_only_vault_references_and_never_claim_success(self):
        self.assertEqual(SandboxVoteIdentity().check("c1", "vault:x", "document", "RW")["state"], "pending")
        self.assertFalse(SandboxVoteIdentity().check("c1", "Ana, 0788", "document", "RW")["ok"])
        self.assertFalse(SandboxVoteSeal().seal("v", "a" * 64)["sealed"])
        with self.assertRaises(ValueError):
            SandboxVoteSeal().seal("v", "the results")
        self.assertEqual(SandboxVotePost().send("i", "postal_ballot", "vault:a", "fr")["state"], "pending")


if __name__ == "__main__":
    unittest.main()
