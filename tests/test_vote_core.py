"""LynkVote's security core and counting methods (VOTE UPDATE, master blueprint 68.5 and 68.7; section 4 step E1): catalog/vote.v1.json
read through core/vote_crypto.py and core/vote_count.py with the TypeScript ports and shared vectors. A choice is locked on the
device; a ballot can only hold allowed values; no single trustee and not LynkOmni can open a total; every opening and shuffle
carries a proof that catches a lie; the counting methods give the published answers; LynkVote never claims to be unhackable."""
import glob, json, os, secrets, subprocess, sys, unittest

from core import vote_count as C
from core import vote_crypto as V

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _probably_prime(n, rounds=40):
    if n % 2 == 0:
        return False
    d, s = n - 1, 0
    while d % 2 == 0:
        d, s = d // 2, s + 1
    for _ in range(rounds):
        x = pow(secrets.randbelow(n - 3) + 2, d, n)
        if x in (1, n - 1):
            continue
        for _ in range(s - 1):
            x = pow(x, 2, n)
            if x == n - 1:
                break
        else:
            return False
    return True


class Core(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.vid, rng = "LOVOT-TEST", V.seeded_rng("test")
        cls.parts = [V.trustee_part(i, 2, rng, cls.vid) for i in (1, 2, 3)]
        cls.pubs = [p["public"] for p in cls.parts]
        cls.x = {j: sum(V.share_for(p, j) for p in cls.parts) % V.Q for j in (1, 2, 3)}
        cls.h = V.joint_key(cls.pubs)
        cls.con = [{"id": "chair", "options": 2, "values": [0, 1], "totals": [1]}]
        cls.rng = staticmethod(rng)

    def test_vectors_and_the_typescript_register_are_current(self):
        r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "vote_vectors.py"), "--check"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_the_group_is_a_safe_prime_group(self):
        self.assertEqual(V.P.bit_length(), 2048)
        self.assertTrue(_probably_prime(V.P) and _probably_prime(V.Q), "p and q = (p - 1) / 2 are both prime")
        self.assertEqual(pow(V.G, V.Q, V.P), 1, "g has order q")
        self.assertEqual(VOTE_REG["group"]["name"], "ffdhe2048")

    def test_a_ballot_holds_only_allowed_values(self):
        b = V.lock_ballot(self.h, self.vid, self.con, [[1, 0]], self.rng)
        self.assertTrue(V.check_ballot(self.h, self.vid, self.con, V.public_ballot(b)))
        with self.assertRaises(ValueError):
            V.lock_ballot(self.h, self.vid, self.con, [[1, 1]], self.rng)
        # a cheating device locks 2 for one option and tries to prove it is 0 or 1
        r = self.rng()
        ct = V.encrypt(self.h, 2, r)
        forged = V.public_ballot(b)
        forged[0]["cts"][0] = ct
        forged[0]["proofs"][0] = V.prove_in(self.h, ct, 1, r, [0, 1], self.rng, f"{self.vid}:chair:0")
        self.assertFalse(V.check_ballot(self.h, self.vid, self.con, forged))
        self.assertTrue(V.challenge_device(self.h, b, [[1, 0]]))
        self.assertFalse(V.challenge_device(self.h, b, [[0, 1]]))

    def test_no_single_trustee_opens_a_total_and_false_openings_are_caught(self):
        ballots = [V.lock_ballot(self.h, self.vid, self.con, [c], self.rng) for c in ([1, 0], [1, 0], [0, 1])]
        ct = V.multiply([b[0]["cts"][0] for b in ballots])
        parts = [V.partial_open(self.pubs, j, self.x[j], ct, self.rng, "t") for j in (1, 2, 3)]
        self.assertTrue(all(V.check_partial(self.pubs, p, ct, "t") for p in parts))
        for pair in ((0, 1), (0, 2), (1, 2)):
            self.assertEqual(V.combine(ct, [parts[i] for i in pair], 3), 2, "any two trustees open the same total")
        with self.assertRaises(ValueError):
            V.combine(ct, [parts[0]], 3)                                                      # one trustee alone opens nothing
        lied = dict(parts[0], d=parts[0]["d"] * V.G % V.P)
        self.assertFalse(V.check_partial(self.pubs, lied, ct, "t"))
        bad = dict(self.pubs[0], proof={"t": self.pubs[0]["proof"]["t"], "z": (self.pubs[0]["proof"]["z"] + 1) % V.Q})
        self.assertFalse(V.check_part(bad, self.vid))
        self.assertFalse(V.check_share(self.pubs[0], 2, (V.share_for(self.parts[0], 2) + 1) % V.Q))

    def test_receipts_chain_the_public_list_and_hide_the_order(self):
        codes, prev = [], "start"
        for c in ([1, 0], [0, 1], [1, 0]):
            prev = V.tracking_code(prev, self.vid, V.lock_ballot(self.h, self.vid, self.con, [c], self.rng))
            codes.append(prev)
        lst = V.public_list([{"code": c} for c in codes])
        self.assertEqual(lst["codes"], sorted(codes))
        self.assertEqual(lst["head"], codes[-1])

    def test_a_shuffle_with_a_changed_ballot_is_caught(self):
        rows = [V.lock_ballot(self.h, self.vid, self.con, [c], self.rng)[0]["cts"] for c in ([1, 0], [0, 1], [1, 0])]
        sh = V.shuffle(self.h, rows, self.rng, "m", rounds=6)
        self.assertTrue(V.check_shuffle(self.h, rows, sh, "m"))
        self.assertFalse(V.check_shuffle(self.h, rows, {"rows": [rows[1]] + sh["rows"][1:], "proof": sh["proof"]}, "m"))
        self.assertFalse(V.check_shuffle(self.h, rows, {"rows": sh["rows"], "proof": sh["proof"][1:] + sh["proof"][:1]}, "m"))


class Counting(unittest.TestCase):
    TN = ["M", "N", "C", "K"]
    TB = [["M", "N", "C", "K"]] * 42 + [["N", "C", "K", "M"]] * 26 + [["C", "K", "N", "M"]] * 15 + [["K", "C", "N", "M"]] * 17

    def test_the_published_examples(self):
        self.assertEqual(C.plurality([b[0] for b in self.TB], self.TN)["winners"], ["M"])
        self.assertEqual(C.irv(self.TB, self.TN)["winners"], ["K"])
        for m in (C.borda, C.ranked_pairs, C.schulze, C.bucklin):
            self.assertEqual(m(self.TB, self.TN)["winners"], ["N"], m.__name__)
        v = {"A": 100000, "B": 80000, "C": 30000, "D": 20000}
        self.assertEqual(C.dhondt(v, 8)["seats"], {"A": 4, "B": 3, "C": 1, "D": 0})
        self.assertEqual(C.sainte_lague(v, 8)["seats"], {"A": 3, "B": 3, "C": 1, "D": 1})
        lr = {"A": 47000, "B": 16000, "C": 15800, "D": 12000, "E": 6100, "F": 3100}
        self.assertEqual(C.largest_remainder(lr, 10, "hare")["seats"], {"A": 5, "B": 2, "C": 1, "D": 1, "E": 1, "F": 0})
        self.assertEqual(C.largest_remainder(lr, 10, "droop")["seats"], {"A": 5, "B": 2, "C": 2, "D": 1, "E": 0, "F": 0})

    def test_majorities_never_count_abstentions_as_yes(self):
        self.assertTrue(C.yes_no(["yes"] * 6 + ["no"] * 3 + ["abstain"] * 9, "two_thirds")["passed"])
        self.assertFalse(C.yes_no(["yes"] * 5 + ["abstain"] * 9, "absolute", members=11)["passed"])
        self.assertFalse(C.yes_no(["yes"] * 3, "simple", quorum=5)["quorum_met"])

    def test_ties_follow_the_published_draw_and_what_if_is_labelled(self):
        a = C.plurality(["A", "B"], ["A", "B"], seed="draw")["winners"]
        self.assertEqual(a, C.lots(["A", "B"], "draw")[:1])
        w = C.what_if("borda", self.TB, self.TN)
        self.assertEqual((w["label"], w["official"]), ("what_if", False))

    def test_every_method_in_the_register_counts(self):
        for m in VOTE_REG["methods"]:
            self.assertTrue(m in C.METHODS or m.startswith("largest_remainder_"), m)


class Honest(unittest.TestCase):
    def test_no_screen_or_message_claims_lynkvote_is_unhackable(self):
        banned = [w.lower() for w in VOTE_REG["honest_words"]["never"]]
        found = []
        for f in glob.glob(os.path.join(ROOT, "web", "**", "strings.en.json"), recursive=True) + [os.path.join(ROOT, "catalog", "messages.v1.json")]:
            text = open(f, encoding="utf-8").read().lower()
            found += [(os.path.relpath(f, ROOT), w) for w in banned if w in text]
        self.assertEqual(found, [])

    def test_the_future_proof_layer_is_not_claimed_before_review(self):
        self.assertEqual(VOTE_REG["future_proof"]["status"], "planned")
        ledger = json.load(open(os.path.join(ROOT, "providers", "registry.v1.json"), encoding="utf-8"))
        self.assertIn("vote_everlasting_privacy", [i["id"] for i in ledger["later"]])


VOTE_REG = V.VOTE

if __name__ == "__main__":
    unittest.main()
