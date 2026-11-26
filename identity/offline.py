"""Sign-up and sign-in without a network (MASTER UPDATE, master blueprint section 55; Step 0 rules).

An email or a text code cannot arrive without a network, so offline LynkOmni never depends on a code: it depends on a key kept
inside the device and a PIN (or fingerprint) that unlocks it. This module holds the rules every device and the cloud share:

- No account is ever made offline (section 4C point 3, v0.118.0: the temporary "start now, confirm later" account is removed).
  Sign-up is online only; offline use starts on a device already signed in online with a real account.
- Offline permissions: a signed-in owner or manager device may approve a new device face to face, after the person matches the
  number shown on both screens. The permission is signed, short (at most 3 days), limited (never the owner role) and capped
  (3 per approving device until the cloud confirms them).
- The offline clock: offline time is counted so that turning the clock back never stretches the limit. After the limit a device
  still sells for cash; everything else waits for the network.
- The PIN: never stored; slowed after wrong tries, then a hard lock that keeps every record. Only the owner's own command wipes.
- Offline records are signed by the device key and checked by the cloud; an altered or replayed record is refused.
- Two devices presenting one identity are both suspended until the owner says which is real.
- No email or text code is ever accepted offline.

In production the device key lives in the device's secure hardware and the PIN check runs there; this reference uses Ed25519
and scrypt in software with the same rules. Only standard, publicly reviewed methods are used (no home-made cryptography)."""
import hashlib, hmac, json, secrets, time
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from identity.arrive_safe import uuid7
from identity.platform import OFFLINE_DAYS

DAY = 86400
PERMISSION_MAX_S = 3 * DAY
APPROVALS_PER_DEVICE = 3
APPROVER_ROLES = ("owner", "manager")
OFFLINE_ROLES = ("cashier", "manager")                 # a face-to-face permission never gives the owner role
PIN_DELAYS = {3: 30, 5: 300, 7: 3600}                  # seconds to wait after that many wrong tries in a row
HARD_LOCK_AFTER = 10
UNLOCK_METHODS = ("recovery_code", "signed_in_device", "online_recovery")
OFFLINE_WORKS = ("cash_sale", "receipt_screen", "receipt_paper", "stock", "cash_count", "device_reports", "assist_offline")
OFFLINE_WAITS = ("electronic_payment", "cards", "partner_services", "storefront", "plans", "other_devices", "receipt_message")
CASH_ONLY = ("cash_sale", "receipt_screen", "receipt_paper")


def _now(n):
    return time.time() if n is None else n


def _canon(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


class DeviceKey:
    """The device's own signing key. In production it never leaves the secure hardware; only the public half is shared."""
    def __init__(self):
        self._k = Ed25519PrivateKey.generate()

    @property
    def public(self):
        return self._k.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw).hex()

    def sign(self, obj):
        return self._k.sign(_canon(obj)).hex()


def signature_ok(public_hex, obj, sig_hex):
    try:
        Ed25519PublicKey.from_public_bytes(bytes.fromhex(public_hex)).verify(bytes.fromhex(sig_hex), _canon(obj))
        return True
    except (InvalidSignature, ValueError):
        return False


class OfflineClock:
    """Counts offline time so that it can only grow. Each tick gives the wall clock and the device's own running counter
    (which a person cannot set); the larger forward step counts, and a clock turned back adds nothing and is noted."""
    def __init__(self, wall, mono):
        self.wall, self.mono, self.elapsed, self.turned_back = wall, mono, 0.0, False

    def tick(self, wall, mono):
        dw, dm = wall - self.wall, mono - self.mono
        if dw < 0:
            self.turned_back = True
        self.elapsed += max(dw, dm, 0)
        self.wall, self.mono = max(self.wall, wall), max(self.mono, mono)
        return self.elapsed

    def days(self):
        return self.elapsed / DAY


def offline_mode(role, clock):
    """'full' within the role's offline limit; after it, 'cash_only': the device still sells for cash and keeps records, so a
    sale is never blocked, and everything else waits until it reconnects."""
    return "full" if clock.days() <= OFFLINE_DAYS.get(role, 7) else "cash_only"


def allowed_offline(mode, action):
    return action in (CASH_ONLY if mode == "cash_only" else OFFLINE_WORKS)


PIN_MIN, PIN_MAX = 4, 8


def pin_problem(pin):
    """None for a good PIN, "length" for the wrong number of digits, "pattern" for a repeated or running number. The PIN pad
    (ts/src/signin.ts) applies the same rule, checked by the shared vectors (tools/shell_parts.py)."""
    if not (isinstance(pin, str) and pin.isdigit() and PIN_MIN <= len(pin) <= PIN_MAX):
        return "length"
    if len(set(pin)) == 1 or pin in "0123456789" or pin in "9876543210":
        return "pattern"
    return None


class PinLock:
    """The PIN is never stored, only a slow salted hash. Wrong tries slow down, then the device locks hard: nothing is
    destroyed, and the owner unlocks it by the recovery code, another signed-in device or online recovery."""
    def __init__(self, pin):
        problem = pin_problem(pin)
        if problem == "length":
            raise ValueError("a PIN is 4 to 8 digits")
        if problem == "pattern":
            raise ValueError("choose a PIN that is not a repeated or running number")
        self._salt = secrets.token_bytes(16)
        self._hash = self._h(pin)
        self.length = len(pin)      # the pad shows this many dots and checks once they are full (owner, 2026-11-26)
        self.wrong, self.wait_until, self.state = 0, 0.0, "open"

    def _h(self, pin):
        return hashlib.scrypt(pin.encode(), salt=self._salt, n=2 ** 14, r=8, p=1)

    def check(self, pin, now=None):
        n = _now(now)
        if self.state == "hard_locked":
            return {"ok": False, "reason": "hard_locked"}
        if n < self.wait_until:
            return {"ok": False, "reason": "wait", "seconds": int(self.wait_until - n)}
        if hmac.compare_digest(self._h(pin), self._hash):
            self.wrong, self.wait_until = 0, 0.0
            return {"ok": True}
        self.wrong += 1
        if self.wrong >= HARD_LOCK_AFTER:
            self.state = "hard_locked"
            return {"ok": False, "reason": "hard_locked"}
        self.wait_until = n + PIN_DELAYS.get(self.wrong, 0)
        return {"ok": False, "reason": "wrong", "left": HARD_LOCK_AFTER - self.wrong}

    def unlock(self, method):
        if method not in UNLOCK_METHODS:
            raise PermissionError("unlock by the recovery code, another signed-in device or online recovery")
        self.state, self.wrong, self.wait_until = "open", 0, 0.0
        return True


def owner_wipe(role, verified):
    """The only way local data is destroyed: the owner's own command after a fresh check. Never wrong PINs, never staff."""
    if role != "owner" or verified is not True:
        raise PermissionError("only the owner, after a fresh check, can wipe a device")
    return "wiped"


def accept_code(online):
    """Email and text codes are never accepted offline, so a stolen or guessed code is useless there."""
    if not online:
        raise PermissionError("codes are only accepted with a network")
    return True


def may_open_account(proofs):
    """A phone number or an email code alone never opens an account (numbers are reused by mobile networks). A passkey, the
    device PIN with its key, or a second proof is always needed as well."""
    strong = {"passkey", "device_pin", "recovery_code", "signed_in_device"}
    return bool(set(proofs) & strong) or len(set(proofs)) >= 2


def accept_records(public_hex, records, seen):
    """Cloud check of records made offline: each must carry a valid device signature and a sequence not seen before."""
    ok, refused = [], []
    for r in records:
        body = {k: v for k, v in r.items() if k != "sig"}
        key = (r.get("device_id", r.get("provisional_id")), r.get("seq"))
        if key in seen:
            refused.append((r.get("seq"), "replayed"))
        elif not signature_ok(public_hex, body, r.get("sig", "")):
            refused.append((r.get("seq"), "altered"))
        else:
            seen.add(key)
            ok.append(r)
    return ok, refused


class Approver:
    """The owner's or a manager's signed-in device, approving a new device face to face with no network."""
    def __init__(self, device, role, key=None):
        if role not in APPROVER_ROLES:
            raise PermissionError("only an owner or manager device approves another device")
        self.device, self.role, self.key, self.pending = device, role, key or DeviceKey(), 0

    @staticmethod
    def number():
        return f"{secrets.randbelow(90) + 10}"

    def grant(self, new_device, role, number_shown, number_picked, now=None):
        if number_picked != number_shown:
            raise PermissionError("the numbers did not match")
        if role not in OFFLINE_ROLES or (role == "manager" and self.role != "owner"):
            raise PermissionError("an offline permission gives at most the role of the device approving it, and never owner")
        if self.pending >= APPROVALS_PER_DEVICE:
            raise PermissionError("this device has approved enough devices until the cloud confirms them")
        n = _now(now)
        perm = {"permission_id": uuid7(n), "approver": self.device, "device": new_device, "role": role,
                "issued_at": n, "expires_at": n + PERMISSION_MAX_S, "restricted": True}
        self.pending += 1
        return {**perm, "sig": self.key.sign(perm)}


def permission_valid(perm, approver_public, now=None):
    body = {k: v for k, v in perm.items() if k != "sig"}
    if not signature_ok(approver_public, body, perm.get("sig", "")):
        return {"ok": False, "reason": "forged"}
    if _now(now) > perm["expires_at"]:
        return {"ok": False, "reason": "expired"}
    return {"ok": True, "role": perm["role"], "restricted": True}


def new_device_offline(permission=None):
    """With nobody to approve it there is no safe way to prove who is asking, so a new device cannot sign in offline."""
    if permission is None:
        raise PermissionError("a new device needs the network, or an owner's or manager's device beside it")
    return True


class CopyWatch:
    """Cloud: one identity presented by two different devices means a copy. Both are suspended until the owner chooses."""
    def __init__(self):
        self.seen, self.suspended = {}, set()

    def present(self, identity, fingerprint):
        first = self.seen.setdefault(identity, fingerprint)
        if first != fingerprint:
            self.suspended |= {first, fingerprint}
            return {"ok": False, "suspended": sorted({first, fingerprint})}
        return {"ok": fingerprint not in self.suspended}

    def owner_keeps(self, identity, fingerprint):
        self.seen[identity] = fingerprint
        self.suspended.discard(fingerprint)
        return True
