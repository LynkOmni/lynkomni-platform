"""LynkAttend, the cloud side (LynkA; master blueprint section 63; build section 3B).

What happens here, in the order a manager and a person meet it:
- a place (a branch or an event) is its own PIN group; the manager registers each person with an ID document, a set (only the means
  the country allows) and the person's agreement; LynkOmni creates the PIN (never easy, never given twice, never reused) and sends
  the PIN and the IDCN together to the person's own contact;
- only door devices the manager added count; each holds locked check values, never a PIN or an IDCN;
- check-ins and check-outs arrive from the door (also after days offline) and become records; backups, flags, hand check-ins and
  wrong device clocks are marked, never hidden; a record is never changed quietly (a correction keeps the old line);
- "Was this you?" after each check, warning signs for the manager (only flags, never an accusation), missed check-outs;
- visitors, with the manager's yes when there is no ID document, and the fire list;
- the person's own page (set, PIN, IDCN, attendance), deletion requests and disputes with reminders at 7, 14 and 25 days and
  automatic deletion after 30; hours the law requires are kept locked, without any personal detail.

Personal details (the full ID number, the IDCN, the PIN, contacts, names) live only in the PII vault, by reference; no event
carries one. In production the vault is encrypted (provider ledger: later)."""
import hashlib, hmac, json, secrets, time

from contract.tools.validate_contract import uuid4
from core import attendance as R, regions
from services import billing

DAY = 86400
REQUEST_REMINDER_DAYS = (7, 14, 25)
REQUEST_DELETE_AFTER_DAYS = 30
VISITOR_ID_KEPT_DAYS = 30
WARN_WINDOW_DAYS = 30
WARN_TIMES = 3                     # the same thing 3 times in 30 days raises "Please check"
PAIR_SECONDS = 60                  # two people checking in one after the other on one device
UNUSUAL_HOURS = 4
CLOCK_TOLERANCE_S = 120
SEND_CHANNELS = ("email", "lynkchat", "text")
PARTNER_CHANNELS = ("text",)                     # needs the people_messages partner in that country; email and LynkChat never do
SIGNS = ("same_pair", "on_leave", "unusual_hours", "checker_often_absent", "often_on_backup", "often_by_hand")


def _now(n): return time.time() if n is None else n
def pin_check(key, pin): return hmac.new(key.encode(), f"pin:{pin}".encode(), hashlib.sha256).hexdigest()
def idcn_check(key, member, idcn): return hmac.new(key.encode(), f"idcn:{member}:{idcn}".encode(), hashlib.sha256).hexdigest()


class Attendance:
    def __init__(s, cloud, platform, notifier=None, messages=None):
        s.cloud, s.p, s.db, s.vault = cloud, platform, platform.c.store.db, platform.vault
        s.n, s.partner = notifier, messages
        s.db.executescript("""
        create table if not exists at_places(place_id text primary key, merchant text, group_id text, shift_end_min int, country text);
        create table if not exists at_members(member_id text primary key, merchant text, place text, set_name text, id_document text, role text, group_id text,
          id_ref text, idcn_ref text, contact_ref text, pin_ref text, pin_state text, covers text, confirmed int, enrolled text, lang text, was_this_you int, created real, deleted real);
        create table if not exists at_pins(group_id text, pin_hash text, member text, primary key(group_id, pin_hash));
        create table if not exists at_checkers(place text, member text, primary key(place, member));
        create table if not exists at_managers(merchant text, manager text, email_ref text, primary key(merchant, manager));
        create table if not exists at_devices(device_id text primary key, merchant text, place text, key text, locked int, clock_ok_at real);
        create table if not exists at_records(record_id text primary key, merchant text, member text, place text, device text, in_at real, out_at real, means text, backup text,
          checker text, flags text, minutes int, history text);
        create table if not exists at_requests(request_id text primary key, merchant text, member text, kind text, at real, reminded int, closed real, outcome text);
        create table if not exists at_visitors(visitor_id text primary key, merchant text, place text, host text, id_document text, id_ref text, name_ref text, allowed_by text,
          guardian int, state text, in_at real, out_at real);
        create table if not exists at_leave(member text, from_day int, to_day int);
        create table if not exists at_signs(member text, sign text, record text, primary key(member, sign, record));
        create table if not exists at_history(merchant text, at real, by text, what text, member text);
        create table if not exists at_hours(merchant text, place text, day int, minutes int, kept_until real);
        create table if not exists at_names(member text primary key, name_ref text);
        create table if not exists at_seen(event_id text primary key);""")

    # ---- small helpers
    def _m(s, member):
        r = s.db.execute("select merchant, place, set_name, id_document, role, group_id, id_ref, idcn_ref, contact_ref, pin_ref, pin_state, covers, confirmed, enrolled, lang, was_this_you, deleted from at_members where member_id=?", (member,)).fetchone()
        if not r or r[16]: raise KeyError("no such person")
        return dict(zip(("merchant", "place", "set", "id_document", "role", "group", "id_ref", "idcn_ref", "contact_ref", "pin_ref", "pin_state", "covers", "confirmed", "enrolled", "lang", "was_this_you", "deleted"), r))
    def _ent(s, merchant): return billing.Billing(s.p.c).entitlement(merchant, "lynkattend")
    def _log(s, merchant, by, what, member=None, now=None): s.db.execute("insert into at_history values(?,?,?,?,?)", (merchant, _now(now), by, what, member))
    def _is_manager(s, merchant, who): return s.db.execute("select 1 from at_managers where merchant=? and manager=?", (merchant, who)).fetchone() is not None
    def _need_manager(s, merchant, who):
        if not s._is_manager(merchant, who): raise PermissionError("only_the_manager")
    def _tell(s, kind, person, event_id, now, record=None, business=None, role=None, facts=None):
        if s.n: return s.n.notify(kind, person, event_id, _now(now), facts=facts, record=record, business=business, role=role)
    def _managers(s, merchant): return [r[0] for r in s.db.execute("select manager from at_managers where merchant=?", (merchant,))]

    # ---- setting up: managers, places (each its own PIN group), checkers, door devices
    def add_manager(s, merchant, manager, email, by=None, now=None):
        """A manager must give at least one email address: it is where LynkOmni reaches them about their people."""
        if not email or "@" not in email: raise ValueError("a manager gives at least one email address")
        limit = s._ent(merchant)["managers"]
        if limit is not None and len(s._managers(merchant)) >= limit and not s._is_manager(merchant, manager): raise PermissionError("manager_limit_for_tier")
        s.db.execute("insert or replace into at_managers values(?,?,?)", (merchant, manager, s.vault.put(manager, "email", email)))
        s._log(merchant, by or manager, "manager_added", now=now); s.db.commit()
    def add_place(s, merchant, by, country=None, shift_end_min=None, join_group_of=None, now=None):
        """A branch or an event. It starts its own PIN group; join_group_of puts it in another place's group (people who check in at both)."""
        s._need_manager(merchant, by)
        limit = s._ent(merchant)["branches"]
        if limit is not None and s.db.execute("select count(*) from at_places where merchant=?", (merchant,)).fetchone()[0] >= limit: raise PermissionError("branch_limit_for_tier")
        group = s.db.execute("select group_id from at_places where place_id=? and merchant=?", (join_group_of, merchant)).fetchone()[0] if join_group_of else uuid4()
        place = uuid4()
        s.db.execute("insert into at_places values(?,?,?,?,?)", (place, merchant, group, shift_end_min, country)); s._log(merchant, by, "place_added", now=now); s.db.commit()
        return place
    def _place(s, place):
        r = s.db.execute("select merchant, group_id, shift_end_min, country from at_places where place_id=?", (place,)).fetchone()
        if not r: raise KeyError("no such place")
        return dict(zip(("merchant", "group", "shift_end_min", "country"), r))
    def set_checkers(s, merchant, place, members, by, now=None):
        s._need_manager(merchant, by)
        s.db.execute("delete from at_checkers where place=?", (place,))
        for m in members:
            if s._m(m)["merchant"] != merchant: raise ValueError("a checker is one of your own people")
            s.db.execute("insert or ignore into at_checkers values(?,?)", (place, m))
        s._log(merchant, by, "checker_list_set", now=now); s.db.commit()
    def checkers(s, place): return [r[0] for r in s.db.execute("select member from at_checkers where place=? order by rowid", (place,))]
    def add_door_device(s, merchant, place, device_id, by, now=None):
        """Only a door device the manager added counts; a person's own phone or home computer can never check them in."""
        s._need_manager(merchant, by)
        limit = s._ent(merchant)["door_devices"]
        if limit is not None and s.db.execute("select count(*) from at_devices where merchant=? and locked=0", (merchant,)).fetchone()[0] >= limit: raise PermissionError("door_device_limit_for_tier")
        s.db.execute("insert or replace into at_devices values(?,?,?,?,0,?)", (device_id, merchant, place, secrets.token_hex(32), _now(now))); s._log(merchant, by, "door_device_added", now=now); s.db.commit()
    def lock_device(s, merchant, device_id, by, now=None):
        """A lost or stolen door device: locked from the dashboard; what it sends afterwards is refused."""
        s._need_manager(merchant, by)
        s.db.execute("update at_devices set locked=1 where device_id=? and merchant=?", (device_id, merchant)); s._log(merchant, by, "door_device_locked", now=now); s.db.commit()

    # ---- registration (once per person, by the manager)
    def sets_for(s, place):
        return R.sets_for_country(regions.country(s._place(place)["country"]))
    def register(s, merchant, place, by, full_id_number, id_document, set_name, contact, name, role="staff", lang="en", now=None):
        s._need_manager(merchant, by)
        pl = s._place(place)
        if pl["merchant"] != merchant: raise ValueError("no such place")
        if id_document not in ("official", "work"): raise ValueError("an official ID or the work ID")
        if set_name not in s.sets_for(place): raise ValueError("means_not_allowed_in_country")
        code = R.idcn(full_id_number)
        if code is None: raise ValueError("id_document_too_few_digits")           # "Please register another ID document for this person."
        ent = s._ent(merchant)
        if ent["extra_person_cents"] is None and s.db.execute("select count(*) from at_members where merchant=? and deleted is null", (merchant,)).fetchone()[0] >= ent["people_included"]:
            raise PermissionError("people_limit_for_tier")
        member = uuid4()
        refs = [s.vault.put(member, f, v) for f, v in (("id_number", str(full_id_number)), ("idcn", code), ("contact", contact or ""), ("full_name", name))]
        s.db.execute("insert into at_members values(?,?,?,?,?,?,?,?,?,?,null,'none','[]',0,'[]',?,1,?,null)", (member, merchant, place, set_name, id_document, role, pl["group"], refs[0], refs[1], refs[2], lang, _now(now)))
        s.db.execute("insert into at_names values(?,?)", (member, refs[3]))
        s.cloud.event(merchant, "AttendancePersonRegistered", {"member_id": member, "place_id": place, "set": set_name, "id_document": id_document, "pin_group_id": pl["group"], "role": role}, now)
        s._log(merchant, by, "registered", member, now); s.db.commit()
        return member
    def name(s, member):
        r = s.db.execute("select name_ref from at_names where member=?", (member,)).fetchone()
        return s.vault.get(r[0]) if r else None
    def change_set(s, merchant, member, set_name, by, now=None):
        """Changing the set needs the person's agreement again for a new means, so the PIN waits until it is given."""
        s._need_manager(merchant, by); m = s._m(member)
        if set_name not in s.sets_for(m["place"]): raise ValueError("means_not_allowed_in_country")
        s.db.execute("update at_members set set_name=?, confirmed=0 where member_id=?", (set_name, member))
        s.cloud.event(merchant, "AttendanceSetChanged", {"member_id": member, "set": set_name}, now); s._log(merchant, by, "set_changed", member, now); s.db.commit()
    def agree(s, member, method, full_id_number=None, now=None):
        """The person agrees in one step. It always covers "sharing my PIN or IDCN is cheating" and the face or finger in their set.
        On a device without a touch screen the person types their full ID number (not the IDCN), and it must match."""
        m = s._m(member)
        if method == "full_id_number" and str(full_id_number) != s.vault.get(m["id_ref"]): raise ValueError("id_number_does_not_match")
        covers = [x for x in ("face", "finger") if x in m["set"].split("_")] + ["no_sharing"]
        s.db.execute("update at_members set covers=? where member_id=?", (json.dumps(covers), member))
        s.cloud.event(m["merchant"], "AttendanceConsentRecorded", {"member_id": member, "consent_id": uuid4(), "method": method, "covers": covers}, now); s.db.commit()
        return covers
    def needs_enrolment(s, member):
        m = s._m(member)
        return [x for x in ("face", "finger") if x in m["set"].split("_") and x not in json.loads(m["enrolled"])]
    def confirm(s, merchant, member, by, now=None):
        s._need_manager(merchant, by); m = s._m(member)
        if "no_sharing" not in json.loads(m["covers"]) or any(x in m["set"].split("_") and x not in json.loads(m["covers"]) for x in ("face", "finger")): raise ValueError("the_person_has_not_agreed")
        s.db.execute("update at_members set confirmed=1 where member_id=?", (member,)); s._log(merchant, by, "confirmed", member, now); s.db.commit()

    # ---- PINs: created by LynkOmni only, 6 digits, never easy, never twice in a group, never reused
    def _taken(s, group): return {r[0] for r in s.db.execute("select pin_hash from at_pins where group_id=?", (group,))}
    def _new_pin(s, group, member):
        taken = s._taken(group)
        h = lambda pin: hashlib.sha256(f"{group}:{pin}".encode()).hexdigest()
        class _T:                                                 # the group's used PINs, known only by their hash
            def __len__(_): return len(taken)
            def __contains__(_, pin): return h(pin) in taken
        pin = R.new_pin(lambda: secrets.randbelow(10 ** R.PIN_LENGTH), _T())
        s.db.execute("insert into at_pins values(?,?,?)", (group, h(pin), member))
        return pin
    def create_pin(s, merchant, member, by, now=None):
        s._need_manager(merchant, by); m = s._m(member)
        if not m["confirmed"]: raise ValueError("confirm_first")
        if m["pin_state"] != "none": raise ValueError("this_person_has_a_pin")
        pin = s._new_pin(m["group"], member)
        s.db.execute("update at_members set pin_ref=?, pin_state='live' where member_id=?", (s.vault.put(member, "pin", pin), member))
        s.cloud.event(merchant, "AttendancePinCreated", {"member_id": member, "pin_group_id": m["group"]}, now); s._log(merchant, by, "pin_created", member, now); s.db.commit()
    def recreate_pin(s, merchant, member, by, now=None):
        """A blocked PIN is dead for ever; the new one is created and sent the same way."""
        s._need_manager(merchant, by); m = s._m(member)
        if m["pin_state"] != "blocked": raise ValueError("only_a_blocked_pin_is_re_created")
        pin = s._new_pin(m["group"], member)
        s.db.execute("update at_members set pin_ref=?, pin_state='live' where member_id=?", (s.vault.put(member, "pin", pin), member))
        s.cloud.event(merchant, "AttendancePinRecreated", {"member_id": member}, now); s._log(merchant, by, "pin_re_created", member, now); s.db.commit()
    def block_pin(s, merchant, member, by, now=None):
        s._need_manager(merchant, by); s._m(member)
        s.db.execute("update at_members set pin_state='blocked' where member_id=?", (member,))
        s.cloud.event(merchant, "AttendancePinBlocked", {"member_id": member, "reason": "manager"}, now); s._log(merchant, by, "pin_blocked", member, now); s.db.commit()
    def send_pin(s, merchant, member, channel, by, now=None):
        """The PIN and the IDCN go together, only to the person's own contact. A text message waits for the messaging partner in
        that country ("Coming to your country soon."); email and LynkChat work everywhere."""
        s._need_manager(merchant, by); m = s._m(member)
        if channel not in SEND_CHANNELS: raise ValueError("email, LynkChat or text message")
        if m["pin_state"] != "live": raise ValueError("no_live_pin")
        if channel in PARTNER_CHANNELS:
            from providers import ready
            if not ready("people_messages", s._place(m["place"])["country"])[0] or not s.partner: return {"state": "coming_soon"}       # "Coming to your country soon."
            if not s.partner.send(channel, "vault:" + m["contact_ref"], "attend_pin_and_idcn", m["lang"]).get("ok"): return {"state": "failed"}
        eid = s.cloud.event(merchant, "AttendancePinSent", {"member_id": member, "channel": channel}, now)
        s._tell("attend_pin_sent", member, eid, now); s._log(merchant, by, f"pin_sent_{channel}", member, now); s.db.commit()
        return {"state": "sent", "channel": channel}
    def show_pin(s, merchant, member, by, now=None):
        """Hidden as dots on the dashboard; every Show is recorded."""
        s._need_manager(merchant, by); m = s._m(member)
        if not m["pin_ref"]: raise ValueError("no_pin")
        s.cloud.event(merchant, "AttendancePinShown", {"member_id": member, "by": by}, now); s._log(merchant, by, "pin_shown", member, now); s.db.commit()
        return s.vault.get(m["pin_ref"])
    def pin_group(s, place):
        g = s._place(place)["group"]; used = len(s._taken(g))
        return {"group": g, "used": used, "size": R.PIN_GROUP_SIZE, "warn": R.pin_group_warning(used)}

    # ---- what a door device holds: locked check values only, for its own PIN group
    def door_pack(s, device_id):
        r = s.db.execute("select merchant, place, key, locked from at_devices where device_id=?", (device_id,)).fetchone()
        if not r or r[3]: raise PermissionError("device_not_registered")
        merchant, place, key, _ = r; pl = s._place(place); people = []
        for (member, set_name, pin_ref, idcn_ref, state, lang) in s.db.execute("select member_id, set_name, pin_ref, idcn_ref, pin_state, lang from at_members where group_id=? and deleted is null and pin_ref is not null", (pl["group"],)):
            people.append({"member_id": member, "set": set_name, "pin_check": pin_check(key, s.vault.get(pin_ref)), "idcn_check": idcn_check(key, member, s.vault.get(idcn_ref)), "blocked": state != "live", "lang": lang,
                           "open": (lambda o: {"record_id": o[0], "in_at": o[1]} if o else None)(s._open(member))})
        return {"place_id": place, "key": key, "people": people, "checkers": s.checkers(place), "shift_end_min": pl["shift_end_min"]}

    # ---- records from the door
    def in_now(s, merchant):
        """Everyone checked in now at the merchant's places, for messages to whoever holds a role on shift (link attend-messages)."""
        return {r[0] for r in s.db.execute("select member from at_records where merchant=? and out_at is null", (merchant,))}
    def _open(s, member):
        r = s.db.execute("select record_id, in_at from at_records where member=? and out_at is null order by in_at desc limit 1", (member,)).fetchone()
        return r
    def _was_in(s, member, at):
        return s.db.execute("select 1 from at_records where member=? and in_at<=? and (out_at is null or out_at>?)", (member, at, at)).fetchone() is not None
    def ingest(s, merchant, evt, now=None):
        """A door event that reached the cloud (maybe days later). A device that was never added, or was locked, is refused."""
        t, p, n = evt["type"], evt["payload"], _now(now)
        dev = s.db.execute("select place, locked from at_devices where device_id=? and merchant=?", (evt.get("device_id"), merchant)).fetchone()
        if not dev or dev[1]: return {"state": "refused", "reason": "device_not_registered"}
        at = _epoch(evt["occurred_at_device"])
        if s.db.execute("select 1 from at_seen where event_id=?", (evt["event_id"],)).fetchone(): return {"state": "duplicate"}
        s.db.execute("insert into at_seen values(?)", (evt["event_id"],))
        eid = s.cloud.device_event(merchant, evt, now=n)
        if t == "CheckedIn":
            flags = list(p.get("flags", []))
            if p.get("checker_id") and "checker_not_checked_in" in flags and s._was_in(p["checker_id"], at): flags.remove("checker_not_checked_in")   # checked again with every device's records
            elif p.get("checker_id") and "checker_not_checked_in" not in flags and not s._was_in(p["checker_id"], at): flags.append("checker_not_checked_in")
            s.db.execute("insert or ignore into at_records values(?,?,?,?,?,?,null,?,?,?,?,null,'[]')", (p["record_id"], merchant, p["member_id"], dev[0], evt["device_id"], at, p["means"], p.get("backup_from"), p.get("checker_id"), json.dumps(flags)))
            if s._on_leave(p["member_id"], at): s._sign(merchant, p["member_id"], "on_leave", p["record_id"], n)
            if flags or p.get("backup_from") or p["means"] == "hand":
                for mg in s._managers(merchant): s._tell("attend_flag_for_manager", mg, eid, n, record=p["record_id"], business=merchant, role="manager")
        elif t == "CheckedOut":
            s.db.execute("update at_records set out_at=?, minutes=? where record_id=? and out_at is null", (at, p["minutes"], p["record_id"]))
            s._was_this_you(merchant, p["member_id"], f"{p['record_id']}:out", p["record_id"], n)
        elif t == "AttendancePinBlocked":
            s.db.execute("update at_members set pin_state='blocked' where member_id=?", (p["member_id"],))
            for mg in s._managers(merchant): s._tell("attend_pin_blocked", mg, eid, n, record=p["member_id"], business=merchant, role="manager")
        elif t == "BiometricEnrolled":
            m = s._m(p["member_id"]); done = sorted(set(json.loads(m["enrolled"])) | {p["means"]})
            s.db.execute("update at_members set enrolled=? where member_id=?", (json.dumps(done), p["member_id"]))
        elif t == "AttendanceCorrected":
            s._log(merchant, p["by"], f"corrected_{p['reason']}", now=n)
        elif t == "VisitorSignedIn":
            st = "waiting_for_manager" if p["id_document"] == "none" and not p.get("allowed_by") else "inside"
            s.db.execute("insert or ignore into at_visitors values(?,?,?,?,?,null,null,?,?,?,?,null)", (p["visitor_id"], merchant, dev[0], p["host_id"], p["id_document"], p.get("allowed_by"), int(bool(p.get("with_guardian"))), st, at))
            if st == "inside": s._tell("attend_visitor_arrived", p["host_id"], eid, n, record=p["visitor_id"], business=merchant)
            else:
                for mg in s._managers(merchant): s._tell("attend_visitor_decision", mg, eid, n, record=p["visitor_id"], business=merchant, role="manager")
        elif t == "VisitorDecision":
            s._visitor_decided(merchant, p["visitor_id"], p["decision"], p["by"], eid, n)
        elif t == "VisitorSignedOut":
            s.db.execute("update at_visitors set state='left', out_at=? where visitor_id=?", (at, p["visitor_id"]))
        s.db.commit()
        return {"state": "accepted"}
    def _was_this_you(s, merchant, member, key, record, now):
        """Free, by LynkChat or email, after each check-in (LynkFlow, attend-was-this-you) and check-out; the person can turn it off
        on "My details", and the business can switch the automation off."""
        if s.p.flow.is_on(merchant, "attend-was-this-you") and s.db.execute("select was_this_you from at_members where member_id=? and deleted is null", (member,)).fetchone() in ((1,),):
            return s._tell("attend_was_this_you", member, key, now, record=record, business=merchant) or True
        return None
    def role_of(s, member):
        r = s.db.execute("select role from at_members where member_id=? and deleted is null", (member,)).fetchone()
        return r[0] if r else None
    def not_me(s, member, record_id, now=None):
        """The person says the check was not theirs: the record is flagged and the manager is told at once."""
        m = s._m(member)
        r = s.db.execute("select flags from at_records where record_id=? and member=?", (record_id, member)).fetchone()
        if not r: raise KeyError("no such record")
        return s._flag(m["merchant"], record_id, "not_me", now)
    def _flag(s, merchant, record_id, flag, now):
        r = s.db.execute("select flags from at_records where record_id=?", (record_id,)).fetchone(); flags = json.loads(r[0])
        if flag in flags: return None
        s.db.execute("update at_records set flags=? where record_id=?", (json.dumps(flags + [flag]), record_id))
        eid = s.cloud.event(merchant, "CheckInFlagged", {"record_id": record_id, "flag": flag}, now)
        for mg in s._managers(merchant): s._tell("attend_flag_for_manager", mg, eid, now, record=record_id, business=merchant, role="manager")
        s.db.commit(); return eid
    def correct(s, merchant, record_id, by, reason, out_at=None, in_at=None, now=None):
        """Only the manager, always with a reason, never their own record; the old line is kept beside the new one."""
        s._need_manager(merchant, by)
        if reason not in ("missed_check_out", "device_clock_wrong", "other"): raise ValueError("reason_missing")
        r = s.db.execute("select member, in_at, out_at, minutes, history from at_records where record_id=? and merchant=?", (record_id, merchant)).fetchone()
        if not r: raise KeyError("no such record")
        if r[0] == by: raise PermissionError("own_record")
        new_in, new_out = in_at if in_at is not None else r[1], out_at if out_at is not None else r[2]
        if new_out is not None and new_out < new_in: raise ValueError("a check-out comes after its check-in")
        history = json.loads(r[4]) + [{"in_at": r[1], "out_at": r[2], "minutes": r[3], "changed_by": by, "reason": reason, "at": _now(now)}]
        s.db.execute("update at_records set in_at=?, out_at=?, minutes=?, history=? where record_id=?", (new_in, new_out, None if new_out is None else int((new_out - new_in) // 60), json.dumps(history), record_id))
        s.cloud.event(merchant, "AttendanceCorrected", {"record_id": record_id, "by": by, "reason": reason}, now); s._log(merchant, by, f"corrected_{reason}", r[0], now); s.db.commit()

    # ---- the device clock guard
    def clock_check(s, merchant, device_id, device_now, now=None):
        """When a door device is online its clock is checked against LynkOmni's. If it is wrong, the records it made since its last
        good check are marked "Device clock was wrong" for the manager to correct."""
        n = _now(now); r = s.db.execute("select clock_ok_at from at_devices where device_id=? and merchant=?", (device_id, merchant)).fetchone()
        if not r: raise PermissionError("device_not_registered")
        if abs(device_now - n) <= CLOCK_TOLERANCE_S:
            s.db.execute("update at_devices set clock_ok_at=? where device_id=?", (n, device_id)); s.db.commit(); return []
        marked = [rec for (rec,) in s.db.execute("select record_id from at_records where device=? and in_at>=?", (device_id, min(r[0], device_now))).fetchall() if s._flag(merchant, rec, "device_clock_wrong", n)]
        return marked

    # ---- missed check-out, leave, warning signs
    def set_leave(s, merchant, member, from_day, to_day, by, now=None):
        s._need_manager(merchant, by); s._m(member)
        s.db.execute("insert into at_leave values(?,?,?)", (member, from_day, to_day)); s._log(merchant, by, "leave_approved", member, now); s.db.commit()
    def _on_leave(s, member, at): return s.db.execute("select 1 from at_leave where member=? and from_day<=? and to_day>=?", (member, int(at // DAY), int(at // DAY))).fetchone() is not None
    def mark_no_check_out(s, merchant, now=None):
        """2 hours after the shift ends (at midnight without shifts) an open record is marked "No check-out"; the manager fixes the time."""
        n, out = _now(now), []
        for (rec, place, in_at) in s.db.execute("select record_id, place, in_at from at_records where merchant=? and out_at is null", (merchant,)).fetchall():
            due = R.no_check_out_due(int(in_at % DAY // 60), s._place(place)["shift_end_min"])
            if n >= (in_at // DAY) * DAY + due * 60 and s._flag(merchant, rec, "no_check_out", n): out.append(rec)
        return out
    def _sign(s, merchant, member, sign, record, now):
        if s.db.execute("select 1 from at_signs where member=? and sign=? and record=?", (member, sign, record)).fetchone(): return None
        s.db.execute("insert into at_signs values(?,?,?)", (member, sign, record))
        return s._flag(merchant, record, "warning_sign", now) or True
    def warning_signs(s, merchant, now=None):
        """Patterns that often mean someone checked in for another person, or that a camera or reader needs fixing. Only "Please check"."""
        n = _now(now); since = n - WARN_WINDOW_DAYS * DAY; found = []
        rows = s.db.execute("select record_id, member, device, in_at, means, backup, flags from at_records where merchant=? and in_at>=? order by in_at", (merchant, since)).fetchall()
        by_member, pairs = {}, {}
        for i, (rec, member, device, in_at, means, backup, flags) in enumerate(rows):
            by_member.setdefault(member, []).append((rec, in_at, means, backup, json.loads(flags)))
            if i and rows[i - 1][2] == device and rows[i - 1][1] != member and in_at - rows[i - 1][3] <= PAIR_SECONDS:
                pairs.setdefault(tuple(sorted((member, rows[i - 1][1]))), {})[int(in_at // DAY)] = (member, rec)
        for pair, days in pairs.items():
            if len(days) >= WARN_TIMES:
                member, rec = days[max(days)]
                if s._sign(merchant, member, "same_pair", rec, n): found.append((member, "same_pair"))
        for member, recs in by_member.items():
            last = recs[-1][0]
            for sign, hit in (("checker_often_absent", lambda r: "checker_not_checked_in" in r[4]), ("often_on_backup", lambda r: r[3] is not None), ("often_by_hand", lambda r: r[2] == "hand")):
                if sum(1 for r in recs if hit(r)) >= WARN_TIMES and s._sign(merchant, member, sign, last, n): found.append((member, sign))
            hours = sorted(int(r[1] % DAY // 3600) for r in recs[:-1])
            if len(hours) >= 10 and abs(int(recs[-1][1] % DAY // 3600) - hours[len(hours) // 2]) >= UNUSUAL_HOURS and s._sign(merchant, member, "unusual_hours", last, n): found.append((member, "unusual_hours"))
        return found

    # ---- visitors and the fire list
    def visitor_details(s, merchant, visitor_id, name, full_id_number=None):
        """The visitor's name and ID number go to the vault only (kept for identification, deleted after 30 days unless there is an incident)."""
        refs = (s.vault.put(visitor_id, "full_name", name), s.vault.put(visitor_id, "id_number", str(full_id_number)) if full_id_number else None)
        s.db.execute("update at_visitors set name_ref=?, id_ref=? where visitor_id=? and merchant=?", (refs[0], refs[1], visitor_id, merchant)); s.db.commit()
    def decide_visitor(s, merchant, visitor_id, decision, by, now=None):
        """A visitor without an ID document gets in only with the manager's yes; the record shows who allowed it."""
        s._need_manager(merchant, by)
        if decision not in ("allow", "refuse"): raise ValueError("allow or refuse")
        eid = s.cloud.event(merchant, "VisitorDecision", {"visitor_id": visitor_id, "decision": decision, "by": by}, now)
        s._visitor_decided(merchant, visitor_id, decision, by, eid, _now(now)); s.db.commit()
    def _visitor_decided(s, merchant, visitor_id, decision, by, eid, now):
        r = s.db.execute("select host, state from at_visitors where visitor_id=? and merchant=?", (visitor_id, merchant)).fetchone()
        if not r or r[1] != "waiting_for_manager": return
        s.db.execute("update at_visitors set state=?, allowed_by=? where visitor_id=?", ("inside" if decision == "allow" else "refused", by if decision == "allow" else None, visitor_id))
        if decision == "allow": s._tell("attend_visitor_arrived", r[0], eid, now, record=visitor_id, business=merchant)
    def purge_visitors(s, now=None, incidents=()):
        n = _now(now); gone = 0
        for (v,) in s.db.execute("select visitor_id from at_visitors where in_at<? and id_ref is not null", (n - VISITOR_ID_KEPT_DAYS * DAY,)).fetchall():
            if v in incidents: continue
            s.vault.delete_subject(v); s.db.execute("update at_visitors set id_ref=null, name_ref=null where visitor_id=?", (v,)); gone += 1
        s.db.commit(); return gone
    def inside(s, merchant, place=None):
        """Who is inside now, staff and visitors: the live view and the fire list (it works offline on the door device too)."""
        q = "select member, place, in_at, means, backup, checker, flags from at_records where merchant=? and out_at is null" + (" and place=?" if place else "")
        staff = [dict(zip(("member_id", "place_id", "in_at", "means", "backup_from", "checker_id", "flags"), r[:6] + (json.loads(r[6]),))) for r in s.db.execute(q, (merchant, place) if place else (merchant,))]
        qv = "select visitor_id, place, host, in_at from at_visitors where merchant=? and state='inside'" + (" and place=?" if place else "")
        visitors = [dict(zip(("visitor_id", "place_id", "host_id", "in_at"), r)) for r in s.db.execute(qv, (merchant, place) if place else (merchant,))]
        return {"staff": staff, "visitors": visitors}

    # ---- the person's own page, deletion requests and disputes
    def my_details(s, member):
        """Opened only after a code to the person's own contact (identity/account.py): their set, PIN, IDCN and attendance."""
        m = s._m(member)
        recs = [dict(zip(("record_id", "in_at", "out_at", "minutes", "means", "flags"), r[:5] + (json.loads(r[5]),))) for r in s.db.execute("select record_id, in_at, out_at, minutes, means, flags from at_records where member=? order by in_at desc", (member,))]
        return {"set": m["set"], "means": R.means_of(m["set"]), "pin": s.vault.get(m["pin_ref"]) if m["pin_ref"] else None, "idcn": s.vault.get(m["idcn_ref"]), "pin_state": m["pin_state"], "was_this_you": bool(m["was_this_you"]), "records": recs}
    def set_was_this_you(s, member, on):
        s._m(member); s.db.execute("update at_members set was_this_you=? where member_id=?", (int(bool(on)), member)); s.db.commit()
    def request(s, member, kind, now=None):
        """Delete my details, or a dispute. The manager is told at once; nothing is deleted yet."""
        m = s._m(member)
        if kind not in ("delete_my_details", "dispute"): raise ValueError("delete my details, or a dispute")
        rid = uuid4()
        s.db.execute("insert into at_requests values(?,?,?,?,?,0,null,null)", (rid, m["merchant"], member, kind, _now(now)))
        eid = s.cloud.event(m["merchant"], "AttendanceRequestRaised", {"member_id": member, "request_id": rid, "kind": kind}, now)
        for mg in s._managers(m["merchant"]): s._tell("attend_request_raised", mg, eid, now, record=rid, business=m["merchant"], role="manager")
        s.db.commit(); return rid
    def close_request(s, merchant, request_id, by, delete, now=None):
        s._need_manager(merchant, by)
        r = s.db.execute("select member, closed from at_requests where request_id=? and merchant=?", (request_id, merchant)).fetchone()
        if not r or r[1]: raise KeyError("no open request")
        if delete: s._delete(merchant, r[0], "manager", now)
        s.db.execute("update at_requests set closed=?, outcome=? where request_id=?", (_now(now), "deleted" if delete else "answered", request_id)); s._log(merchant, by, "request_closed", r[0], now); s.db.commit()
    def requests_tick(s, now=None, merchant=None):
        """Reminders to the manager at 7, 14 and 25 days; after 30 days with no action the details are deleted by themselves."""
        n, out = _now(now), {"reminded": [], "deleted": []}
        for (rid, m_, member, at, reminded) in s.db.execute("select request_id, merchant, member, at, reminded from at_requests where closed is null").fetchall():
            if merchant and m_ != merchant: continue
            days = (n - at) / DAY
            if days >= REQUEST_DELETE_AFTER_DAYS:
                s._delete(m_, member, "thirty_days_passed", n)
                s.db.execute("update at_requests set closed=?, outcome='deleted_after_30_days' where request_id=?", (n, rid)); out["deleted"].append(rid); continue
            due = sum(1 for d in REQUEST_REMINDER_DAYS if days >= d)
            if due > reminded:
                for mg in s._managers(m_): s._tell("attend_request_raised", mg, f"{rid}:reminder:{due}", n, record=rid, business=m_, role="manager")
                s.db.execute("update at_requests set reminded=? where request_id=?", (due, rid)); out["reminded"].append((rid, REQUEST_REMINDER_DAYS[due - 1]))
        s.db.commit(); return out
    def _delete(s, merchant, member, by, now):
        """Removes every personal detail (name, contacts, ID number, IDCN, PIN, face or finger pattern on the devices). The PIN's
        hash stays in the group so it is never given again. Hours the law requires stay, locked, with nothing personal on them."""
        m = s._m(member); n = _now(now)
        years = ((regions.country(s._place(m["place"])["country"]).get("people") or {}).get("attendance") or {}).get("hours_records_years")
        for (in_at, minutes) in s.db.execute("select in_at, minutes from at_records where member=? and minutes is not null", (member,)).fetchall():
            if years: s.db.execute("insert into at_hours values(?,?,?,?,?)", (merchant, m["place"], int(in_at // DAY), minutes, n + years * 365 * DAY))
        s.db.execute("delete from at_records where member=?", (member,)); s.db.execute("delete from at_checkers where member=?", (member,)); s.db.execute("delete from at_leave where member=?", (member,))
        s.db.execute("delete from at_names where member=?", (member,))
        s.vault.delete_subject(member)
        s.db.execute("update at_members set deleted=?, id_ref=null, idcn_ref=null, contact_ref=null, pin_ref=null, pin_state='none' where member_id=?", (n, member))
        eid = s.cloud.event(merchant, "AttendanceDetailsDeleted", {"member_id": member, "by": by}, n)
        s._tell("attend_details_deleted", member, eid, n, business=merchant)
    def kept_hours_expire(s, now=None):
        c = s.db.execute("delete from at_hours where kept_until<?", (_now(now),)); s.db.commit(); return c.rowcount

    # ---- the manager's views: live, history, hours, what is billed
    def live(s, merchant, place=None, now=None):
        n = _now(now); day = int(n // DAY)
        q = "select member_id, place from at_members where merchant=? and deleted is null" + (" and place=?" if place else "")
        people = []
        for (member, pl) in s.db.execute(q, (merchant, place) if place else (merchant,)).fetchall():
            r = s.db.execute("select record_id, in_at, out_at, means, backup, checker, flags from at_records where member=? and in_at>=? order by in_at desc limit 1", (member, day * DAY)).fetchone()
            state = "absent" if not r else "left" if r[2] else "inside"
            if not r and s._on_leave(member, n): state = "on_leave"
            people.append({"member_id": member, "place_id": pl, "state": state, "record_id": r[0] if r else None, "in_at": r[1] if r else None, "means": r[3] if r else None,
                           "backup_from": r[4] if r else None, "checker_id": r[5] if r else None, "flags": json.loads(r[6]) if r else [],
                           "pin_state": s._m(member)["pin_state"]})
        return {"people": people, "inside": sum(1 for x in people if x["state"] == "inside"), "visitors": len(s.inside(merchant, place)["visitors"]),
                "open_requests": s.db.execute("select count(*) from at_requests where merchant=? and closed is null", (merchant,)).fetchone()[0]}
    def history(s, merchant, limit=100):
        """Every manager action (Show PIN, edit, hand check-in, correction, deletion), for the owner of the account."""
        return [dict(zip(("at", "by", "what", "member_id"), r)) for r in s.db.execute("select at, by, what, member from at_history where merchant=? order by rowid desc limit ?", (merchant, limit))]
    def hours(s, merchant, member, from_day, to_day):
        return s.db.execute("select coalesce(sum(minutes),0) from at_records where merchant=? and member=? and in_at>=? and in_at<?", (merchant, member, from_day * DAY, (to_day + 1) * DAY)).fetchone()[0]
    def billable(s, merchant, month_start, month_end):
        """Only people who checked in at least once that month are counted; visitors, and managers or checkers who do not check in, are free."""
        ent = s._ent(merchant)
        people = s.db.execute("select count(distinct member) from at_records where merchant=? and in_at>=? and in_at<?", (merchant, month_start, month_end)).fetchone()[0]
        extra = max(0, people - ent["people_included"])
        return {"people": people, "included": ent["people_included"], "extra_people": extra, "extra_cents": extra * (ent["extra_person_cents"] or 0)}


def _epoch(ts):
    """Seconds from a contract timestamp (with or without milliseconds)."""
    from datetime import datetime
    return datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp()
