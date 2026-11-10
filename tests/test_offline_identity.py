"""Sign-up and sign-in without a network (MASTER UPDATE, master blueprint section 55). test_attack_bank holds one case per known
attack; a release cannot pass while any of them succeeds."""
import json, os, unittest
from identity import offline as o
from identity.platform import OFFLINE_DAYS

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EVENTS = json.load(open(os.path.join(ROOT, "identity", "events.v1.json"), encoding="utf-8"))["events"]
T0 = 1_800_000_000


def start(**kw):
    args = dict(device="dev-1", adult_confirmed=True, lang="fr", country="CM", wished_username="ama.shop",
                wished_contact="+237600000000", pin="4719", now=T0)
    args.update(kw)
    return o.ProvisionalAccount(**args)


class TestProvisionalAccount(unittest.TestCase):
    def test_start_now_confirm_later(self):
        a = start()
        self.assertEqual(a.state, "queued")
        for act in ("cash_sale", "receipt_paper", "stock", "cash_count", "device_reports", "assist_offline"):
            self.assertTrue(a.can(act), act)
        for act in o.PROVISIONAL_WAITS:
            self.assertFalse(a.can(act), act)
            with self.assertRaises(PermissionError):
                a.record(act, {})
        rec = a.record("cash_sale", {"total": 1500}, now=T0 + 60)
        self.assertTrue(o.signature_ok(a.key.public, {k: v for k, v in rec.items() if k != "sig"}, rec["sig"]))
        self.assertEqual(a.events[0][0], "ProvisionalAccountStarted")
        self.assertNotIn("+237600000000", json.dumps(a.events), "no contact in any event")
        self.assertNotIn(b"+237600000000", a._contact, "the wished contact is kept encrypted")
        self.assertEqual(a.contact_for_confirmation(), "+237600000000")

    def test_age_username_and_contact_are_checked_before_anything_starts(self):
        with self.assertRaises(PermissionError):
            start(adult_confirmed=False)
        with self.assertRaises(ValueError):
            start(wished_username="..bad")
        with self.assertRaises(ValueError):
            start(wished_contact="")

    def test_first_connection_in_a_fixed_order(self):
        self.assertEqual(o.confirm_provisional(start(), False, True)["result"], "contact_not_confirmed")
        self.assertEqual(o.confirm_provisional(start(), True, False)["result"], "choose_username")
        a = start()
        self.assertEqual(o.confirm_provisional(a, True, True)["result"], "confirmed")
        self.assertEqual(a.state, "confirmed")
        self.assertTrue(a.can("electronic_payment"))
        b = start()
        self.assertEqual(o.confirm_provisional(b, True, True, existing_account=True)["result"], "sign_in_to_existing")
        self.assertEqual(b.state, "queued")
        self.assertEqual(o.confirm_provisional(b, True, True, existing_account=True, verified_existing=True)["result"], "merged")

    def test_every_event_named_here_is_an_account_event(self):
        for name in ("ProvisionalAccountStarted", "ProvisionalAccountConfirmed", "OfflinePermissionGranted", "OfflinePermissionConfirmed",
                     "DeviceHardLocked", "DeviceUnlocked", "DeviceCopySuspended", "OfflineLimitReached"):
            self.assertIn(name, EVENTS)
            self.assertFalse({"phone", "email", "pin", "code", "contact"} & set(EVENTS[name]["payload"]), name)


class TestOfflineSignIn(unittest.TestCase):
    def test_offline_limit_turns_to_cash_only_and_never_blocks_a_sale(self):
        c = o.OfflineClock(T0, 0)
        c.tick(T0 + 6 * o.DAY, 6 * o.DAY)
        self.assertEqual(o.offline_mode("owner", c), "full")
        c.tick(T0 + 8 * o.DAY, 8 * o.DAY)
        self.assertEqual(o.offline_mode("owner", c), "cash_only")
        self.assertEqual(o.offline_mode("cashier", c), "full", "a cashier has 14 days")
        self.assertTrue(o.allowed_offline("cash_only", "cash_sale"))
        self.assertFalse(o.allowed_offline("cash_only", "stock"))
        self.assertEqual(OFFLINE_DAYS, {"owner": 7, "manager": 7, "cashier": 14})

    def test_wrong_pins_lock_hard_and_never_destroy(self):
        a = start()
        a.record("cash_sale", {"total": 900})
        lock = a.pin
        self.assertNotIn("4719", repr(vars(lock)), "the PIN itself is never stored")
        now = T0
        for i in range(1, o.HARD_LOCK_AFTER):
            now += 4000
            r = lock.check("0000", now=now)
            self.assertEqual(r["reason"], "wrong")
        self.assertEqual(lock.check("0001", now=now + 4000)["reason"], "hard_locked")
        self.assertEqual(lock.check("4719", now=now + 9000)["reason"], "hard_locked", "even the right PIN waits for an unlock")
        self.assertEqual(len(a.records), 1, "nothing is destroyed by wrong PINs")
        with self.assertRaises(PermissionError):
            lock.unlock("guess")
        self.assertTrue(lock.unlock("recovery_code"))
        self.assertTrue(lock.check("4719", now=now + 9000)["ok"])

    def test_pins_slow_down_after_wrong_tries(self):
        lock = o.PinLock("4719")
        for _ in range(3):
            lock.check("1111", now=T0)
        r = lock.check("4719", now=T0 + 1)
        self.assertEqual(r["reason"], "wait")
        self.assertTrue(lock.check("4719", now=T0 + 31)["ok"])

    def test_weak_pins_are_refused(self):
        for bad in ("1111", "1234", "9876", "12", "abcd", "123456789"):
            with self.assertRaises(ValueError):
                o.PinLock(bad)

    def test_only_the_owner_wipes(self):
        with self.assertRaises(PermissionError):
            o.owner_wipe("manager", True)
        with self.assertRaises(PermissionError):
            o.owner_wipe("owner", False)
        self.assertEqual(o.owner_wipe("owner", True), "wiped")

    def test_face_to_face_permission_is_small_short_and_restricted(self):
        owner = o.Approver("dev-owner", "owner")
        n = o.Approver.number()
        p = owner.grant("dev-new", "cashier", n, n, now=T0)
        v = o.permission_valid(p, owner.key.public, now=T0 + o.DAY)
        self.assertEqual(v, {"ok": True, "role": "cashier", "restricted": True})
        self.assertLessEqual(p["expires_at"] - p["issued_at"], 3 * o.DAY)
        self.assertTrue(o.new_device_offline(p))


class TestAttackBank(unittest.TestCase):
    def test_attack_bank(self):
        # 1. A stolen or guessed email or text code is useless offline.
        with self.assertRaises(PermissionError):
            o.accept_code(online=False)
        # 2. A reused phone number alone never opens an account.
        self.assertFalse(o.may_open_account({"sms_code"}))
        self.assertTrue(o.may_open_account({"sms_code", "passkey"}))
        # 3. A new device with nobody to approve it cannot sign in offline.
        with self.assertRaises(PermissionError):
            o.new_device_offline(None)
        # 4. An approval tapped by habit: the numbers must match.
        owner = o.Approver("dev-owner", "owner")
        with self.assertRaises(PermissionError):
            owner.grant("dev-x", "cashier", "42", "24", now=T0)
        # 5. A permission can never give the owner role, and a manager cannot make another manager.
        with self.assertRaises(PermissionError):
            owner.grant("dev-x", "owner", "42", "42", now=T0)
        with self.assertRaises(PermissionError):
            o.Approver("dev-m", "manager").grant("dev-x", "manager", "42", "42", now=T0)
        with self.assertRaises(PermissionError):
            o.Approver("dev-c", "cashier")
        # 6. One stolen device cannot approve many others.
        for i in range(o.APPROVALS_PER_DEVICE):
            owner.grant(f"dev-{i}", "cashier", "42", "42", now=T0)
        with self.assertRaises(PermissionError):
            owner.grant("dev-many", "cashier", "42", "42", now=T0)
        # 7. A forged or expired permission is refused.
        other = o.Approver("dev-evil", "owner")
        forged = other.grant("dev-y", "cashier", "11", "11", now=T0)
        self.assertEqual(o.permission_valid(forged, owner.key.public, now=T0)["reason"], "forged")
        good = o.Approver("dev-o2", "owner")
        p = good.grant("dev-z", "cashier", "11", "11", now=T0)
        self.assertEqual(o.permission_valid(p, good.key.public, now=T0 + 4 * o.DAY)["reason"], "expired")
        tampered = dict(p, role="manager")
        self.assertEqual(o.permission_valid(tampered, good.key.public, now=T0)["reason"], "forged")
        # 8. The clock turned back never stretches the offline limit.
        c = o.OfflineClock(T0, 0)
        c.tick(T0 + 8 * o.DAY, 8 * o.DAY)
        c.tick(T0, 8 * o.DAY + 60)
        self.assertTrue(c.turned_back)
        self.assertEqual(o.offline_mode("owner", c), "cash_only")
        frozen = o.OfflineClock(T0, 0)
        frozen.tick(T0, 9 * o.DAY)
        self.assertEqual(o.offline_mode("owner", frozen), "cash_only", "a stopped wall clock does not stop the count")
        # 9. An altered or replayed offline record is refused.
        a = start()
        r1 = a.record("cash_sale", {"total": 1000})
        r2 = a.record("cash_sale", {"total": 2000})
        seen = set()
        ok, refused = o.accept_records(a.key.public, [r1, dict(r2, body={"total": 2})], seen)
        self.assertEqual([r["seq"] for r in ok], [1])
        self.assertEqual(refused, [(2, "altered")])
        ok, refused = o.accept_records(a.key.public, [r1], seen)
        self.assertEqual(refused, [(1, "replayed")])
        # 10. A copied device is caught: both copies wait for the owner.
        w = o.CopyWatch()
        self.assertTrue(w.present("lynkid-1", "fp-a")["ok"])
        self.assertEqual(w.present("lynkid-1", "fp-b"), {"ok": False, "suspended": ["fp-a", "fp-b"]})
        self.assertFalse(w.present("lynkid-1", "fp-a")["ok"])
        w.owner_keeps("lynkid-1", "fp-a")
        self.assertTrue(w.present("lynkid-1", "fp-a")["ok"])
        # 11. A wished username taken meanwhile is never a promise.
        self.assertEqual(o.confirm_provisional(start(), True, False)["result"], "choose_username")
        # 12. Guessing PINs ends in a hard lock, never in lost records.
        lock = o.PinLock("4719")
        for k in range(o.HARD_LOCK_AFTER):
            lock.check("0000", now=T0 + k * 4000)
        self.assertEqual(lock.state, "hard_locked")


if __name__ == "__main__":
    unittest.main()
