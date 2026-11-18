"""The LynkAttend door, on the device (LynkA; build section 3B). It runs on any door device the manager added (LynkKiosk, LynkTab,
LynkPC, LynkPOS, LynkMobile, or hardware through LynkDriver) and works fully without internet.

The device holds only locked check values for its own PIN group (people/attendance.py door_pack): never a PIN, an IDCN or an ID
number. The PIN comes first and says who the person is and which set is theirs; then core/attendance.py door() runs the means in the
order Face, Finger, IDCN. Every record is a contract event on the device's own chain (dv/box.py), sent when the internet returns.
Nothing here decides who may work; it only records, marks and flags."""
from contract.tools.validate_contract import uuid7
from core import attendance as R
from dv.box import LocalRejection
from people.attendance import idcn_check, pin_check


class Door:
    def __init__(s, box, pack=None, readers=("face", "finger")):
        s.box, s.readers, s.pack = box, set(readers), None
        s.wrong_pins, s.paused_until, s.clock_wrong = 0, None, False
        s.inside, s.visitors, s.blocked = {}, {}, set()
        if pack: s.load(pack)
    def load(s, pack):
        """Fresh check values from the cloud (when online). People already inside stay inside."""
        s.pack, s.by_pin, s.people = pack, {p["pin_check"]: p for p in pack["people"]}, {p["member_id"]: p for p in pack["people"]}
        s.blocked |= {p["member_id"] for p in pack["people"] if p["blocked"]}
        for p in pack["people"]:
            if p.get("open") and p["member_id"] not in s.inside: s.inside[p["member_id"]] = (p["open"]["record_id"], p["open"]["in_at"])
    def _ready(s):
        if not s.pack: raise LocalRejection("device_not_registered")          # only a door device the manager added counts
    def _now(s): return s.box.clock.timestamp()

    # ---- step 1: the PIN (it only says who the person is; 5 unknown PINs in a row pause the device for a minute)
    def who(s, pin):
        s._ready()
        if s.paused_until and s._now() < s.paused_until: raise LocalRejection("device_paused")
        p = s.by_pin.get(pin_check(s.pack["key"], pin))
        if not p or R.is_easy_pin(pin):
            s.wrong_pins += 1
            if s.wrong_pins >= R.PIN_TRIES_BEFORE_PAUSE: s.paused_until, s.wrong_pins = s._now() + R.PIN_PAUSE_SECONDS, 0
            raise LocalRejection("pin_not_recognised")
        s.wrong_pins = 0
        if p["member_id"] in s.blocked: raise LocalRejection("pin_blocked")   # "Your PIN is blocked. Please see your manager."
        return p

    # ---- steps 2 and 3: the person's set, then the record
    def check(s, pin, direction, outcomes=(), broken=(), checker=None):
        """One person at the door. outcomes lists what happens in order: "ok" or "fail" for a Face or Finger read, and the digits
        typed for an IDCN. broken lists means that do not work on this device (a means with no reader counts as broken).
        Returns the door result; "waiting" names the means the screen asks for next."""
        if direction not in ("in", "out"): raise ValueError("in or out")
        p = s.who(pin); member = p["member_id"]
        if direction == "in" and member in s.inside: raise LocalRejection("already_checked_in")
        if direction == "out" and member not in s.inside: raise LocalRejection("not_checked_in")
        broken = set(broken) | {m for m in ("face", "finger") if m not in s.readers}
        attempts, out = [], R.door(p["set"], [], broken)
        for o in outcomes:
            if out["result"] != "waiting": break
            if out["means"] == "idcn":
                if not checker: raise ValueError("select_a_checker")
                if checker == member or checker not in s.pack["checkers"]: raise ValueError("not_a_checker_for_this_person")   # nobody names themself
                attempts.append("ok" if idcn_check(s.pack["key"], member, str(o)) == p["idcn_check"] else "fail")
            else:
                if o not in ("ok", "fail"): raise ValueError("a read is ok or fail")
                attempts.append(o)
            out = R.door(p["set"], attempts, broken)
        res = {"result": out["result"], "member_id": member, "lang": p["lang"], "means": out["means"], "backup_from": out["backup_from"], "steps": out["steps"]}
        if out["result"] == "pin_blocked":
            s.blocked.add(member); s.box._emit("AttendancePinBlocked", {"member_id": member, "reason": "idcn_wrong_5_times"})
        elif out["result"] == "in":
            flags = (R.checker_flags(checker in s.inside) if out["means"] == "idcn" else []) + (["device_clock_wrong"] if s.clock_wrong else [])
            res.update(s._record(member, direction, out["means"], out["backup_from"], checker if out["means"] == "idcn" else None, flags))
        return res
    def _record(s, member, direction, means, backup, checker, flags, extra=None):
        s.box._guard("CheckIn" if direction == "in" else "CheckOut")
        base = {"member_id": member, "device_id": s.box.d, "means": means, **({"backup_from": backup} if backup else {}), **({"checker_id": checker} if checker else {}), **({"flags": flags} if flags else {})}
        if direction == "in":
            rec = uuid7(); s.box._emit("CheckedIn", {"record_id": rec, **base, **(extra or {})}); s.inside[member] = (rec, s._now())
            return {"record_id": rec, "flags": flags}
        rec, in_at = s.inside.pop(member); minutes = max(0, int((s._now() - in_at) // 60))
        s.box._emit("CheckedOut", {"record_id": rec, **base, "minutes": minutes})
        return {"record_id": rec, "flags": flags, "minutes": minutes}

    # ---- every means failed: the manager checks the person in by hand, with a reason, never themself
    def by_hand(s, member, manager, reason):
        s._ready()
        if s.box.role not in ("owner", "manager"): raise LocalRejection("permission_denied")
        if reason not in ("all_means_failed", "device_broken", "other"): raise LocalRejection("reason_missing")
        if manager == member: raise LocalRejection("own_record")               # another manager must do it
        if member not in s.people: raise LocalRejection("pin_not_recognised")
        if member in s.inside: raise LocalRejection("already_checked_in")
        return s._record(member, "in", "hand", None, None, ["by_hand"] + (["device_clock_wrong"] if s.clock_wrong else []), {"hand_by": manager, "hand_reason": reason})

    # ---- enrolment for Face or Finger (at registration, after the person agreed)
    def enrol(s, member, means, agreed):
        if not agreed: raise LocalRejection("no_consent")
        if means not in s.readers: raise LocalRejection("no_reader")           # "A fingerprint reader is needed for this person."
        s.box._guard("EnrolBiometric")
        s.box._emit("BiometricEnrolled", {"member_id": member, "means": means, "device_id": s.box.d})

    # ---- visitors and the fire list (both work offline)
    def visitor_in(s, host, id_document, allowed_by=None, with_guardian=False):
        """Door staff check the ID document. Without one the visitor waits for the manager's yes."""
        s._ready(); s.box._guard("SignInVisitor")
        if id_document not in ("official", "work", "none"): raise ValueError("official, work or none")
        v = uuid7(); waiting = id_document == "none" and not allowed_by
        s.box._emit("VisitorSignedIn", {"visitor_id": v, "place_id": s.pack["place_id"], "host_id": host, "id_document": id_document, **({"allowed_by": allowed_by} if allowed_by else {}), **({"with_guardian": True} if with_guardian else {})})
        s.visitors[v] = "waiting_for_manager" if waiting else "inside"
        return {"visitor_id": v, "state": s.visitors[v]}
    def visitor_decision(s, visitor, decision, by):
        if s.box.role not in ("owner", "manager"): raise LocalRejection("permission_denied")
        if s.visitors.get(visitor) != "waiting_for_manager": raise LocalRejection("manager_not_allowed_yet")
        s.box._emit("VisitorDecision", {"visitor_id": visitor, "decision": decision, "by": by})
        s.visitors[visitor] = "inside" if decision == "allow" else "refused"
    def visitor_out(s, visitor):
        if s.visitors.get(visitor) != "inside": raise LocalRejection("manager_not_allowed_yet")
        s.box._emit("VisitorSignedOut", {"visitor_id": visitor}); s.visitors[visitor] = "left"
    def fire_list(s, by):
        """One button lists everyone inside, staff and visitors, to tick off at the meeting point."""
        s._ready(); s.box._guard("OpenFireList")
        s.box._emit("FireListOpened", {"place_id": s.pack["place_id"], "by": by})
        return {"staff": sorted(s.inside), "visitors": sorted(v for v, st in s.visitors.items() if st == "inside")}
