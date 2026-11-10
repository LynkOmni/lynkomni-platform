"""Arrive Safe and Collect Pass on the LynkOmni Account (NEW UPDATE 1, owner approved 2026-11-10; master blueprint section 49,
build section 2). Free on every plan, for every person, in every country: the core of LynkMotion needs no partner.

Arrive Safe:
- Location sharing is always the person's own choice, with people they pick, for a set time, under a consent record
  (scope "location-share", at most 30 days). It ends by itself, can be stopped in one tap, and is always shown to the person
  sharing. Nobody else ever sees a position; this module never stores one (positions live only in the encrypted, time-limited
  position store of section 7B, and only while a share is on).
- A trip plan has a check-in deadline and at least one trusted contact. The cloud watches the deadline, so it works even if the
  phone dies or loses the network: if nobody checks in on time, TripPlanOverdue is written (cloud only) and the contacts are told.

Collect Pass: one code on the person's account collects every parcel waiting at any pickup point, from any carrier, with no paper
slip. The code changes every minute, works only for the person, and each parcel can be collected once. (The QR picture of the
same code comes with the pay pages in section 7.)

Every change is an event on the person's own stream (identity/events.v1.json), with references only."""
import hashlib, hmac, math, secrets, time, uuid

DAY, HOUR = 86400, 3600
SHARE_SCOPES = ("live", "trips", "zones")
SHARE_MAX_HOURS = 30 * 24
PASS_WINDOW_S = 60
PASS_DIGITS = 6


def _now(n): return time.time() if n is None else n


def uuid7(now=None):
    """A time-ordered id (UUID version 7), as the contract asks for new records."""
    ms = int(_now(now) * 1000)
    r = int.from_bytes(secrets.token_bytes(10), "big")
    v = (ms << 80) | (0x7 << 76) | ((r >> 66) & 0xFFF) << 64 | (0b10 << 62) | (r & ((1 << 62) - 1))
    return str(uuid.UUID(int=v))


class ArriveSafe:
    def __init__(s, account):
        s.a, s.db = account, account.db
        s.db.executescript("""
        create table if not exists safe_shares(share_id text primary key, person text, grantee text, locns text, scope text, started real, ends real, ended real, reason text);
        create table if not exists safe_plans(plan_id text primary key, person text, due real, contacts text, set_at real, checked_in real, overdue real);
        create table if not exists safe_pass(person text primary key, secret text);
        create table if not exists safe_pass_used(person text, shipment text, used real, primary key(person, shipment));""")

    # ---- location sharing, always by consent and for a set time
    def share(s, person, grantee, scope, hours, now=None):
        if scope not in SHARE_SCOPES: raise ValueError("a share is live, trips or zones")
        if isinstance(hours, bool) or not isinstance(hours, int) or not 1 <= hours <= SHARE_MAX_HOURS:
            raise ValueError("a share lasts from 1 hour to 30 days")
        if not grantee or grantee == s.a._lynkid(person): raise ValueError("share with someone you choose")
        n = _now(now)
        locns = s.a.grant_consent(person, "location-share", grantee, f"see my {scope} until the share ends", math.ceil(hours / 24), n)
        share_id, ends = uuid7(n), n + hours * HOUR
        s.db.execute("insert into safe_shares values(?,?,?,?,?,?,?,null,null)", (share_id, person, grantee, locns, scope, n, ends)); s.db.commit()
        s.a.emit(person, "LocationShareStarted", {"share_id": share_id, "consent_id": locns, "scope": scope, "ends_at": ends}, n)
        return {"share_id": share_id, "locns": locns, "ends_at": ends}

    def _end(s, share_id, reason, now):
        r = s.db.execute("select person, locns from safe_shares where share_id=? and ended is null", (share_id,)).fetchone()
        if not r: return False
        s.db.execute("update safe_shares set ended=?, reason=? where share_id=?", (now, reason, share_id)); s.db.commit()
        if reason == "stopped": s.a.withdraw_consent(r[0], r[1], "self", now)
        s.a.emit(r[0], "LocationShareEnded", {"share_id": share_id, "reason": reason}, now)
        return True

    def stop(s, person, share_id, now=None):
        if not s.db.execute("select 1 from safe_shares where share_id=? and person=?", (share_id, person)).fetchone():
            raise PermissionError("only the person sharing stops a share")
        return s._end(share_id, "stopped", _now(now))

    def expire(s, now=None):
        """Cloud tick: shares past their end time end by themselves."""
        n = _now(now)
        due = [r[0] for r in s.db.execute("select share_id from safe_shares where ended is null and ends<=?", (n,)).fetchall()]
        return [x for x in due if s._end(x, "expired", n)]

    def shares(s, person, now=None):
        """What the person sharing always sees: every share that is on, with whom and until when."""
        n = _now(now)
        rows = s.db.execute("select share_id, grantee, scope, ends from safe_shares where person=? and ended is null and ends>? order by started", (person, n)).fetchall()
        return [{"share_id": r[0], "with": r[1], "scope": r[2], "ends_at": r[3]} for r in rows]

    def can_see(s, grantee, person, now=None):
        n = _now(now)
        return s.db.execute("select 1 from safe_shares where person=? and grantee=? and ended is null and ends>?", (person, grantee, n)).fetchone() is not None

    # ---- trip plans with a check-in deadline, watched by the cloud
    def plan(s, person, due_at, contacts, now=None):
        n = _now(now)
        contacts = [c for c in dict.fromkeys(contacts or []) if c and c != s.a._lynkid(person)]
        if not contacts: raise ValueError("a trip plan needs at least one trusted contact")
        if due_at <= n: raise ValueError("the check-in time is in the future")
        plan_id = uuid7(n)
        s.db.execute("insert into safe_plans values(?,?,?,?,?,null,null)", (plan_id, person, due_at, ",".join(contacts), n)); s.db.commit()
        s.a.emit(person, "TripPlanSet", {"plan_id": plan_id, "due_at": due_at, "contacts": len(contacts)}, n)
        return plan_id

    def check_in(s, person, plan_id, now=None):
        n = _now(now)
        r = s.db.execute("select person, checked_in, overdue from safe_plans where plan_id=?", (plan_id,)).fetchone()
        if not r or r[0] != person: raise PermissionError("only the traveller checks in")
        if r[1]: return False
        s.db.execute("update safe_plans set checked_in=? where plan_id=?", (n, plan_id)); s.db.commit()
        s.a.emit(person, "TripPlanCheckedIn", {"plan_id": plan_id}, n)
        return True

    def tick(s, now=None):
        """Cloud only: plans past their deadline with no check-in become overdue, and their trusted contacts are told. Nothing about
        where the person is goes with the message unless the person has a share on with that contact."""
        n, out = _now(now), []
        for plan_id, person, contacts in s.db.execute("select plan_id, person, contacts from safe_plans where checked_in is null and overdue is null and due<=?", (n,)).fetchall():
            s.db.execute("update safe_plans set overdue=? where plan_id=?", (n, plan_id)); s.db.commit()
            s.a.emit(person, "TripPlanOverdue", {"plan_id": plan_id}, n)
            out.append({"plan_id": plan_id, "person": person, "tell": [{"contact": c, "with_location": s.can_see(c, person, n)} for c in contacts.split(",")]})
        return out

    # ---- Collect Pass: one changing code for every parcel waiting at any pickup point
    def _secret(s, person):
        r = s.db.execute("select secret from safe_pass where person=?", (person,)).fetchone()
        if r: return bytes.fromhex(r[0])
        k = secrets.token_bytes(32)
        s.db.execute("insert into safe_pass values(?,?)", (person, k.hex())); s.db.commit()
        return k

    def _code(s, person, window):
        d = hmac.new(s._secret(person), f"{person}|{window}".encode(), hashlib.sha256).digest()
        return str(int.from_bytes(d[:8], "big") % 10 ** PASS_DIGITS).zfill(PASS_DIGITS)

    def collect_pass(s, person, now=None):
        n = _now(now); w = int(n // PASS_WINDOW_S)
        return {"code": s._code(person, w), "changes_at": (w + 1) * PASS_WINDOW_S}

    def collect(s, person, code, shipment_id, now=None):
        """A pickup point checks the pass for one parcel: the current or the previous minute's code, once per parcel. The pickup
        device then writes ShipmentHandedOver with method collect_pass (and waits for the provider when payment is due)."""
        n = _now(now); w = int(n // PASS_WINDOW_S)
        if not any(hmac.compare_digest(code or "", s._code(person, x)) for x in (w, w - 1)):
            return {"ok": False, "reason": "code_not_valid"}
        if s.db.execute("select 1 from safe_pass_used where person=? and shipment=?", (person, shipment_id)).fetchone():
            return {"ok": False, "reason": "already_collected"}
        s.db.execute("insert into safe_pass_used values(?,?,?)", (person, shipment_id, n)); s.db.commit()
        return {"ok": True, "method": "collect_pass"}
