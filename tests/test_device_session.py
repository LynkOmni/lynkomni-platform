"""Device-tied sessions (MASTER UPDATE, master blueprint section 59; build section 1)."""
import unittest
from identity.offline import DeviceKey
from identity import device_session as ds

T0 = 1_800_000_000


class TestDeviceSessions(unittest.TestCase):
    def setUp(self):
        self.s, self.key = ds.Sessions(), DeviceKey()
        self.tok = self.s.start("p1", self.key.public, now=T0)

    def call(self, key=None, method="GET", address="/security", now=T0 + 5, **over):
        ts, nonce, sig = ds.sign_request(key or self.key, self.tok, method, address, now=now)
        args = {"ts": ts, "nonce": nonce, "sig": sig, **over}
        return self.s.check(self.tok, method, address, args["ts"], args["nonce"], args["sig"], now=now), (ts, nonce, sig)

    def test_the_session_works_only_from_its_own_device(self):
        self.assertTrue(self.call()[0]["ok"])
        self.assertEqual(self.call(key=DeviceKey())[0]["why"], "not_this_device", "a copied token on another device is refused")
        self.assertEqual(self.call(sig="")[0]["why"], "not_this_device", "no proof, no access")
        with self.assertRaises(ValueError):
            self.s.start("p1", "")

    def test_a_proof_is_for_one_request_once_and_only_fresh(self):
        ok, (ts, nonce, sig) = self.call(method="POST", address="/security/passkeys")
        self.assertTrue(ok["ok"])
        self.assertEqual(self.s.check(self.tok, "POST", "/security/passkeys", ts, nonce, sig, now=T0 + 6)["why"], "proof_replayed")
        ts2, n2, sig2 = ds.sign_request(self.key, self.tok, "GET", "/security", now=T0 + 7)
        self.assertEqual(self.s.check(self.tok, "POST", "/security/passkeys", ts2, n2, sig2, now=T0 + 7)["why"], "not_this_device", "a proof cannot be moved to another request")
        old = ds.sign_request(self.key, self.tok, "GET", "/a", now=T0)
        self.assertEqual(self.s.check(self.tok, "GET", "/a", *old, now=T0 + ds.PROOF_WINDOW_S + 1)["why"], "proof_too_old")

    def test_three_refusals_end_the_session_and_it_never_comes_back(self):
        other = DeviceKey()
        for _ in range(ds.REFUSALS_BEFORE_END):
            self.call(key=other)
        self.assertEqual(self.call()[0]["why"], "session_ended")

    def test_idle_and_maximum_age_and_revoke(self):
        self.assertEqual(self.call(now=T0 + ds.IDLE_S + 10)[0]["why"], "session_ended")
        tok = self.s.start("p1", self.key.public, now=T0)
        self.s.revoke(tok)
        ts, n, sig = ds.sign_request(self.key, tok, "GET", "/", now=T0 + 1)
        self.assertEqual(self.s.check(tok, "GET", "/", ts, n, sig, now=T0 + 1)["why"], "session_ended")


if __name__ == "__main__":
    unittest.main()
