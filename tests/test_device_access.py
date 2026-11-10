"""Signing in on every device, also offline (MASTER UPDATE sections 55 and 59; build section 3): staff PINs, the duress PIN,
resets on the spot, offline limits by role, remote lock and wipe, integrity checks and the owner-only backup."""
import unittest
from identity import device_access as da
from identity.offline import OfflineClock
from services.sealing import generate_keypair

T0 = 1_800_000_000


class Device(unittest.TestCase):
    def setUp(self):
        self.events = []
        self.d = da.DeviceAccess("dev-1", "owner-1", "4719", emit=lambda t, p: self.events.append((t, p)))
        self.d.add_staff("owner-1", "4719", "mgr-1", "manager", "2580")
        self.d.add_staff("owner-1", "4719", "cash-1", "cashier", "1357")

    def types(self):
        return [t for t, _ in self.events]

    def test_each_person_signs_in_with_their_own_pin_offline(self):
        clock = OfflineClock(T0, 0)
        r = self.d.sign_in("cash-1", "1357", clock=clock, now=T0)
        self.assertEqual((r["ok"], r["view"], r["role"]), (True, "full", "cashier"))
        self.assertFalse(self.d.sign_in("cash-1", "2580", now=T0)["ok"], "another person's PIN never opens it")

    def test_wrong_pins_slow_down_then_lock_hard_never_wipe(self):
        for i in range(10):
            self.d.sign_in("cash-1", "9999", now=T0 + i * 10_000)
        self.assertEqual(self.d.sign_in("cash-1", "1357", now=T0 + 200_000)["reason"], "hard_locked")
        self.assertIn("DeviceHardLocked", self.types())
        self.assertEqual(self.d.state, "open", "the device and its records are untouched")
        self.assertTrue(self.d.sign_in("owner-1", "4719", now=T0)["ok"], "other staff still sign in")

    def test_duress_pin_opens_a_limited_view_and_alerts_quietly(self):
        self.d.set_duress_pin("cash-1", "1357", "8642")
        r = self.d.sign_in("cash-1", "8642", now=T0)
        self.assertEqual((r["ok"], r["view"]), (True, "limited"))
        self.assertNotIn("duress", repr(r), "the screen is never told")
        self.assertEqual(self.d.paths_out([], now=T0), [], "no path yet: the alert waits on the device")
        sent = self.d.paths_out(["nearby_device", "internet"], now=T0)
        self.assertEqual(sent[0]["sent_by"], "nearby_device")
        self.assertEqual(self.types().count("DuressSignalled"), 1)
        self.assertEqual(self.d.paths_out(["text"]), [], "sent once")
        with self.assertRaises(ValueError):
            self.d.set_duress_pin("cash-1", "1357", "1357")

    def test_staff_pins_are_managed_on_the_spot_but_never_the_owners(self):
        self.d.reset_pin("mgr-1", "2580", "cash-1", "4826")
        self.assertTrue(self.d.sign_in("cash-1", "4826", now=T0)["ok"])
        with self.assertRaises(PermissionError):
            self.d.reset_pin("mgr-1", "2580", "owner-1", "1111")
        with self.assertRaises(PermissionError):
            self.d.reset_pin("cash-1", "4826", "mgr-1", "4826"), "a cashier resets nobody"
        with self.assertRaises(PermissionError):
            self.d.reset_pin("mgr-1", "0000", "cash-1", "4826")
        self.assertTrue(self.d.remove_staff("owner-1", "4719", "cash-1"))
        self.assertEqual(self.d.sign_in("cash-1", "4826")["reason"], "unknown")
        self.assertIn("StaffPinReset", self.types()); self.assertIn("StaffRemovedOnDevice", self.types())

    def test_offline_limits_by_role_need_a_managers_pin_on_the_same_device(self):
        self.assertTrue(self.d.needs_manager("cash-1", "void", 500))
        self.assertTrue(self.d.needs_manager("cash-1", "refund", 1))
        self.assertFalse(self.d.needs_manager("cash-1", "discount", 1000))
        self.assertTrue(self.d.needs_manager("cash-1", "discount", 1001))
        self.assertFalse(self.d.needs_manager("mgr-1", "void", 10 ** 9))
        with self.assertRaises(PermissionError):
            self.d.manager_approves("cash-1", "void", 500, "cash-1", "1357")
        self.assertTrue(self.d.manager_approves("cash-1", "void", 500, "mgr-1", "2580"))
        self.d.set_limit("owner-1", "4719", "cashier", "discount_bps", 500)
        self.assertTrue(self.d.needs_manager("cash-1", "discount", 600))
        with self.assertRaises(ValueError):
            self.d.set_limit("owner-1", "4719", "cashier", "discount_bps", 5000)

    def test_remote_lock_and_wipe(self):
        cloud = da.RemoteCommands(emit=lambda t, p: self.events.append((t, p)))
        with self.assertRaises(PermissionError):
            cloud.lock("dev-1", "cashier", True)
        cloud.lock("dev-1", "owner", True)
        self.assertEqual(self.d.state, "open", "nothing happens until the device hears from the cloud")
        cloud.deliver(self.d)
        self.assertEqual(self.d.sign_in("owner-1", "4719")["reason"], "locked_by_owner")
        with self.assertRaises(PermissionError):
            cloud.wipe("dev-1", "manager", True, unsent=0, accept_loss=False)
        self.assertEqual(cloud.wipe("dev-1", "owner", True, unsent=12, accept_loss=False)["state"], "confirm_loss")
        cloud.wipe("dev-1", "owner", True, unsent=12, accept_loss=True)
        cloud.deliver(self.d)
        self.assertEqual(self.d.state, "wiped")
        self.assertEqual(self.d.sign_in("owner-1", "4719")["reason"], "wiped")
        self.assertEqual([t for t in self.types() if t.startswith("Device")], ["DeviceLockRequested", "DeviceLocked", "DeviceWipeRequested", "DeviceWiped"])

    def test_every_signal_is_registered_with_its_payload(self):
        with self.assertRaises(ValueError):
            self.d.emit("MadeUpSignal", {})
        with self.assertRaises(ValueError):
            self.d.emit("StaffPinReset", {"device_id": "d", "person": "p", "by": "o", "pin": "1234"})


class Integrity(unittest.TestCase):
    def test_an_altered_app_or_rooted_device_is_held_for_the_owner(self):
        good = {"app_hash": "h1", "rooted": False, "verified_boot": True, "emulator": False}
        self.assertTrue(da.integrity_check(good, {"h1"})["ok"])
        bad = da.integrity_check({**good, "app_hash": "x", "rooted": True}, {"h1"})
        self.assertEqual(bad["failed"], ["app_signature", "not_rooted"])
        ev = []
        gate = da.UploadGate(emit=lambda t, p: ev.append(t))
        gate.checked("d1", bad)
        self.assertEqual(gate.upload("d1", {"n": 1}), "held_for_owner")
        self.assertEqual(gate.owner_review("d1", keep=True), {"accepted": 1, "set_aside": 0}, "nothing is thrown away")
        gate.checked("d2", da.integrity_check(good, {"h1"}))
        self.assertEqual(gate.upload("d2", {}), "accepted")
        self.assertEqual(ev, ["DeviceIntegrityFailed"])


class Backup(unittest.TestCase):
    def test_backup_is_readable_only_by_the_owner(self):
        priv, pub = generate_keypair()
        other, _ = generate_keypair()
        ev = []
        b = da.make_backup([{"sale": 1}, {"sale": 2}], pub, "memory_card", device_id="dev-1", emit=lambda t, p: ev.append((t, p)))
        self.assertEqual(da.restore_backup(b, priv), [{"sale": 1}, {"sale": 2}])
        with self.assertRaises(Exception):
            da.restore_backup(b, other)
        self.assertEqual(ev[0][1]["count"], 2)
        with self.assertRaises(ValueError):
            da.make_backup([], pub, "cloud_drive")


if __name__ == "__main__":
    unittest.main()
