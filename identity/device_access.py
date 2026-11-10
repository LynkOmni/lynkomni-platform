"""Signing in on every LynkOmni device, also offline (MASTER UPDATE, master blueprint sections 55 and 59; build section 3).

Who may use a device, and how it stays safe when it is lost, forced or altered:
- every staff member has their own PIN on the device, so every act is tied to a person; the PIN is never stored, only a slow
  salted hash (identity/offline.py PinLock); wrong PINs slow down and then lock hard, never wipe;
- offline, a role keeps its own limits: a cashier cannot void, refund or discount above the shop's limit without a manager's
  PIN on the same device (OFFLINE_LIMITS, the owner can lower them);
- a duress PIN opens a harmless limited view and quietly raises an alert for the owner's trusted contacts; it works offline
  (sent by the first path that appears: a text, a nearby device or the internet) and never calls the police by itself, and the
  screen never shows that it was used;
- the owner or a manager resets a staff member's forgotten PIN, or removes a staff member, on the device itself, also offline;
  the owner's own forgotten PIN needs the online recovery paths;
- the owner can lock or wipe a device from anywhere; the device carries the command out the next time it hears from the
  cloud; a wipe is the owner's own command after a fresh check, and the owner is told first how many records were never sent;
- the app checks that it has not been altered and that the device is not unlocked at root level; a device that fails is not
  trusted with the account: its uploads are held for the owner to review, never thrown away;
- a long-offline or provisional device can make an encrypted backup to a second device or a memory card, readable only by the
  owner (services/sealing.py).
Events are Business app signals (merchant/events.v1.json) with references only: never a PIN, a hash or a contact."""
import hashlib, hmac, json, os, secrets, time

from identity.offline import HARD_LOCK_AFTER, PIN_DELAYS, PinLock, offline_mode, owner_wipe, pin_problem

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SIGNALS = {}
for _reg in (("merchant", "events.v1.json"), ("identity", "events.v1.json")):      # Business app signals and the device lock events
    with open(os.path.join(ROOT, *_reg), encoding="utf-8") as f:
        SIGNALS.update(json.load(f)["events"])

ROLES = ("owner", "manager", "cashier", "stock_staff")
CAN_MANAGE = {"owner": ("manager", "cashier", "stock_staff"), "manager": ("cashier", "stock_staff")}
OFFLINE_LIMITS = {                                    # the most a role may do alone offline; above it a manager's PIN on the same device
    "cashier": {"void_minor": 0, "refund_minor": 0, "discount_bps": 1000},
    "stock_staff": {"void_minor": 0, "refund_minor": 0, "discount_bps": 0},
    "manager": {"void_minor": None, "refund_minor": None, "discount_bps": None},   # None: no limit of its own
    "owner": {"void_minor": None, "refund_minor": None, "discount_bps": None},
}
DURESS_VIEW = ("sell_cash", "receipt_screen", "receipt_paper")       # the harmless limited view: no reports, totals, cash count or settings
DURESS_PATHS = ("text", "nearby_device", "internet")                  # the alert leaves by the first path that appears
BACKUP_PLACES = ("second_device", "memory_card")
INTEGRITY = ("app_signature", "not_rooted", "verified_boot", "not_emulator")


def _now(n):
    return time.time() if n is None else n


def emit_checked(fn, type_, payload):
    """Every signal is in a register and carries exactly its registered payload (references only)."""
    if type_ not in SIGNALS:
        raise ValueError(f"{type_} is not a registered signal (merchant/events.v1.json, identity/events.v1.json)")
    if set(payload) != set(SIGNALS[type_]["payload"]):
        raise ValueError(f"{type_} carries {sorted(payload)}, its register says {SIGNALS[type_]['payload']}")
    fn(type_, payload)


class DeviceAccess:
    """One device's staff, their PINs and what the device may do. `emit(type, payload)` records Business app signals."""

    def __init__(self, device_id, owner, owner_pin, emit=None):
        self.device = device_id
        self.emit_fn = emit or (lambda t, p: None)
        self.staff = {}                 # person -> {"role", "lock", "duress"}
        self.state = "open"             # open | remote_locked | wiped
        self.outbox = []                # sealed alerts and requests waiting for a path out
        self.limits = {r: dict(v) for r, v in OFFLINE_LIMITS.items()}
        self.staff[owner] = {"role": "owner", "lock": PinLock(owner_pin), "duress": None}

    def emit(self, type_, payload):
        emit_checked(self.emit_fn, type_, payload)

    def role(self, person):
        s = self.staff.get(person)
        return s["role"] if s else None

    # ------------------------------------------------------------------ staff on the device, also offline
    def _authorised(self, by, by_pin, target_role):
        s = self.staff.get(by)
        if not s or target_role not in CAN_MANAGE.get(s["role"], ()):
            raise PermissionError("only the owner, or a manager for cashiers and stock staff, can do this")
        if not s["lock"].check(by_pin)["ok"]:
            raise PermissionError("the PIN of the person doing this was not right")
        return s["role"]

    def add_staff(self, by, by_pin, person, role, pin, now=None):
        if role not in ROLES or role == "owner":
            raise ValueError("a device has one owner; add a manager, cashier or stock staff")
        self._authorised(by, by_pin, role)
        self.staff[person] = {"role": role, "lock": PinLock(pin), "duress": None}
        self.emit("StaffAddedOnDevice", {"device_id": self.device, "person": person, "role": role, "by": by})

    def remove_staff(self, by, by_pin, person, now=None):
        target = self.staff.get(person)
        if not target:
            return False
        self._authorised(by, by_pin, target["role"])
        del self.staff[person]
        self.emit("StaffRemovedOnDevice", {"device_id": self.device, "person": person, "by": by})
        return True

    def reset_pin(self, by, by_pin, person, new_pin, now=None):
        """A forgotten staff PIN is reset on the spot by the owner or a manager, also offline. The owner's own PIN is never
        reset this way: it needs the online recovery paths."""
        target = self.staff.get(person)
        if not target:
            raise KeyError(person)
        if target["role"] == "owner":
            raise PermissionError("the owner's own PIN is reset only through online recovery")
        self._authorised(by, by_pin, target["role"])
        target["lock"] = PinLock(new_pin)
        target["duress"] = None                  # a reset clears the duress PIN too; the person sets a new one
        self.emit("StaffPinReset", {"device_id": self.device, "person": person, "by": by})

    def set_duress_pin(self, person, pin, duress_pin):
        s = self.staff[person]
        if not s["lock"].check(pin)["ok"]:
            raise PermissionError("the PIN was not right")
        if pin_problem(duress_pin):
            raise ValueError("choose a duress PIN of 4 to 8 digits that is not a repeated or running number")
        if duress_pin == pin:
            raise ValueError("the duress PIN must differ from the normal PIN")
        salt = secrets.token_bytes(16)
        s["duress"] = (salt, hashlib.scrypt(duress_pin.encode(), salt=salt, n=2 ** 14, r=8, p=1))

    def _is_duress(self, s, pin):
        if not s["duress"]:
            return False
        salt, h = s["duress"]
        return hmac.compare_digest(hashlib.scrypt(pin.encode(), salt=salt, n=2 ** 14, r=8, p=1), h)

    # ------------------------------------------------------------------ signing in
    def sign_in(self, person, pin, clock=None, now=None):
        """Unlock with a personal PIN, with no network. Returns what the screen may show:
        {"ok": True, "view": "full" | "cash_only" | "limited"} or {"ok": False, "reason": ...}.
        A duress PIN returns the limited view, which looks like an ordinary quiet till, and the alert leaves silently."""
        if self.state == "wiped":
            return {"ok": False, "reason": "wiped"}
        if self.state == "remote_locked":
            return {"ok": False, "reason": "locked_by_owner"}
        s = self.staff.get(person)
        if not s:
            return {"ok": False, "reason": "unknown"}
        if s["lock"].state != "hard_locked" and self._is_duress(s, pin):
            self.outbox.append({"kind": "duress", "device_id": self.device, "person": person, "at": _now(now), "sent_by": None})
            return {"ok": True, "view": "limited", "role": s["role"]}
        r = s["lock"].check(pin, now)
        if not r["ok"]:
            if r["reason"] == "hard_locked":
                self.emit("DeviceHardLocked", {"device": self.device})
            return r
        mode = offline_mode(s["role"], clock) if clock is not None else "full"
        return {"ok": True, "view": mode, "role": s["role"]}

    def paths_out(self, available, now=None):
        """Send waiting alerts by the first path that appears (text, a nearby device or the internet). Nothing calls the
        police by itself; the owner's trusted contacts decide."""
        path = next((p for p in DURESS_PATHS if p in available), None)
        if not path:
            return []
        sent = []
        for item in self.outbox:
            if item["sent_by"] is None:
                item["sent_by"] = path
                if item["kind"] == "duress":
                    self.emit("DuressSignalled", {"device_id": self.device, "person": item["person"], "path": path, "at": item["at"]})
                sent.append(item)
        return sent

    # ------------------------------------------------------------------ offline limits by role
    def set_limit(self, by, by_pin, role, key, value):
        """The owner may lower a role's offline limit (never raise a cashier above the platform's limit)."""
        if self.role(by) != "owner" or not self.staff[by]["lock"].check(by_pin)["ok"]:
            raise PermissionError("only the owner sets offline limits")
        base = OFFLINE_LIMITS[role][key]
        if base is not None and (value is None or value > base):
            raise ValueError("an offline limit can be lowered, never raised above the platform's limit")
        self.limits[role][key] = value
        self.emit("OfflineLimitChanged", {"device_id": self.device, "role": role, "limit": key, "value": value})

    def needs_manager(self, person, act, amount):
        """True when this act, this big, needs a manager's PIN on the same device. act: void | refund | discount."""
        key = {"void": "void_minor", "refund": "refund_minor", "discount": "discount_bps"}[act]
        lim = self.limits[self.role(person)][key]
        return lim is not None and amount > lim

    def manager_approves(self, person, act, amount, manager, manager_pin, now=None):
        """A manager (or the owner) approves an act above the staff member's limit by their own PIN on this device."""
        m = self.staff.get(manager)
        if not m or m["role"] not in ("manager", "owner") or manager == person:
            raise PermissionError("a manager or the owner, not the same person, approves this")
        if not m["lock"].check(manager_pin, now)["ok"]:
            raise PermissionError("the manager's PIN was not right")
        self.emit("OverLimitApproved", {"device_id": self.device, "person": person, "act": act, "amount": amount, "by": manager})
        return True

    # ------------------------------------------------------------------ remote lock and wipe by the owner
    def receive(self, command, now=None):
        """The device carries out the owner's command the next time it hears from the cloud."""
        if command["kind"] == "lock":
            self.state = "remote_locked"
            self.emit("DeviceLocked", {"device_id": self.device, "after_s": 0, "by_automation": False})
            return "locked"
        if command["kind"] == "unlock":
            self.state = "open"
            return "open"
        if command["kind"] == "wipe":
            self.state = "wiped"                   # the keys are destroyed, so the encrypted records can never be read again
            self.staff.clear()
            self.outbox.clear()
            self.emit("DeviceWiped", {"device_id": self.device, "unsent_lost": command.get("unsent", 0)})
            return "wiped"
        raise ValueError(command["kind"])


class RemoteCommands:
    """The cloud side of remote lock and wipe. Lock: the owner (or a manager for cashier devices) after a fresh check.
    Wipe: the owner only, after a fresh check, told first how many records the device never sent."""

    def __init__(self, emit=None):
        self.emit_fn = emit or (lambda t, p: None)
        self.waiting = {}

    def lock(self, device_id, role, verified, now=None):
        if role not in ("owner", "manager") or verified is not True:
            raise PermissionError("the owner or a manager, after a fresh check, can lock a device")
        self.waiting.setdefault(device_id, []).append({"kind": "lock"})
        emit_checked(self.emit_fn, "DeviceLockRequested", {"device_id": device_id, "by_role": role})
        return "sent"

    def unlock(self, device_id, role, verified):
        if role != "owner" or verified is not True:
            raise PermissionError("only the owner, after a fresh check, unlocks a device locked from afar")
        self.waiting.setdefault(device_id, []).append({"kind": "unlock"})
        return "sent"

    def wipe(self, device_id, role, verified, unsent, accept_loss):
        owner_wipe(role, verified)
        if unsent and accept_loss is not True:
            return {"state": "confirm_loss", "unsent": unsent}
        self.waiting.setdefault(device_id, []).append({"kind": "wipe", "unsent": unsent})
        emit_checked(self.emit_fn, "DeviceWipeRequested", {"device_id": device_id, "unsent": unsent})
        return {"state": "sent", "unsent": unsent}

    def deliver(self, device):
        """When the device next connects. Shown to the owner as sent until the device reports back."""
        done = [device.receive(c) for c in self.waiting.pop(device.device, [])]
        return done


def integrity_check(report, signed_app_hashes):
    """report: {"app_hash", "rooted", "verified_boot", "emulator"} from the device's own attestation (a sandbox now; the
    platform attestation service per operating system later, provider ledger 'device_attestation').
    Returns {"ok": True} or {"ok": False, "failed": [...]} : the cloud then holds the device's uploads for the owner."""
    failed = []
    if report.get("app_hash") not in signed_app_hashes:
        failed.append("app_signature")
    if report.get("rooted"):
        failed.append("not_rooted")
    if not report.get("verified_boot"):
        failed.append("verified_boot")
    if report.get("emulator"):
        failed.append("not_emulator")
    return {"ok": not failed, "failed": failed}


class UploadGate:
    """The cloud's door for a device's sealed batches: a device that failed its integrity check is not trusted with the
    account, so its uploads wait for the owner to review them. Nothing is thrown away."""

    def __init__(self, emit=None):
        self.emit_fn = emit or (lambda t, p: None)
        self.trusted, self.held = {}, {}

    def checked(self, device_id, result):
        self.trusted[device_id] = result["ok"]
        if not result["ok"]:
            emit_checked(self.emit_fn, "DeviceIntegrityFailed", {"device_id": device_id, "failed": result["failed"]})

    def upload(self, device_id, batch):
        if self.trusted.get(device_id) is True:
            return "accepted"
        self.held.setdefault(device_id, []).append(batch)
        return "held_for_owner"

    def owner_review(self, device_id, keep):
        batches = self.held.pop(device_id, [])
        return {"accepted": len(batches) if keep else 0, "set_aside": 0 if keep else len(batches)}


def make_backup(records, owner_public, place, device_id=None, emit=None):
    """An encrypted backup of the device's records, readable only by the owner (their key), to a second device or a memory
    card. The device keeps its own copy; nothing is uploaded."""
    from services.sealing import seal
    if place not in BACKUP_PLACES:
        raise ValueError(f"a backup goes to {' or '.join(BACKUP_PLACES)}")
    blob = seal(json.dumps(records, sort_keys=True).encode(), owner_public)
    if emit:
        emit_checked(emit, "OfflineBackupMade", {"device_id": device_id, "place": place, "count": len(records)})
    return {"place": place, "blob": blob, "count": len(records)}


def restore_backup(backup, owner_private):
    from services.sealing import unseal
    return json.loads(unseal(backup["blob"], owner_private))
