"""One identity per person, two security levels. Sessions are bound to one site (no cookie shared across lynkomni.com).
Sensitive actions need a short-lived step-up. Owner recovery follows the agreed layered design. In production the codes
below are sent by SMS or email and are never returned to the caller; they are returned here so tests can run offline."""
import hashlib, json, secrets, time
from core.locale import t

SITES = {"account", "bookings", "essentials", "exchange", "merchant"}
RESTRICTED = {"change_role", "change_payout", "revoke_device", "export_data"}   # blocked for 24h on a newly recovered device
def _h(x): return hashlib.sha256(x.encode()).hexdigest()
def _now(now): return time.time() if now is None else now

class Identity:
    SESSION_S, STEPUP_S, WAIT_S, ASSISTED_S, MAX_ATTEMPTS = 12 * 3600, 600, 24 * 3600, 72 * 3600, 5
    def __init__(s, c, ccbox=None):
        s.c, s.cc, s.db = c, ccbox, c.store.db
        s.db.executescript("""
        create table if not exists identities(person text primary key, phone text, email text, lang text, merchant_id text, recovery_hash text, backup_contact text);
        create table if not exists idevices(device_id text primary key, merchant_id text, person text, role text, enrolled_at real, revoked_at real, restricted_until real);
        create table if not exists isessions(token text primary key, person text, site text, expires real);
        create table if not exists istepups(token text primary key, person text, scope text, expires real);
        create table if not exists ichallenges(person text primary key, code text, expires real);
        create table if not exists irecoveries(id text primary key, person text, path text, new_device text, lost_device text, status text, ready_at real, approvals text);
        create table if not exists iattempts(person text, ts real);""")
    # identity and devices
    def register(s, person, phone, email, lang="en"):
        s.db.execute("insert into identities values(?,?,?,?,null,null,null)", (person, phone, email, lang)); s.db.commit()
    def add_merchant_role(s, person, merchant_id, backup_contact=None):
        """Returns the recovery code ONCE. It goes on paper, never on the phone. Only its hash is kept."""
        code = secrets.token_hex(8)
        s.db.execute("update identities set merchant_id=?, recovery_hash=?, backup_contact=? where person=?", (merchant_id, _h(code), backup_contact, person)); s.db.commit()
        return code
    def enroll_device(s, person, merchant_id, device_id, role="owner", now=None, restricted_until=0):
        s.db.execute("insert into idevices values(?,?,?,?,?,null,?)", (device_id, merchant_id, person, role, _now(now), restricted_until)); s.db.commit()
        if s.cc: s.cc.enroll(device_id, merchant_id)
    def revoke_device(s, device_id, now=None):
        s.db.execute("update idevices set revoked_at=? where device_id=?", (_now(now), device_id)); s.db.commit()
        if s.cc: s.cc.revoke(device_id, time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(_now(now))))
    def _devices(s, merchant_id, role=None):
        q = "select device_id,person,role from idevices where merchant_id=? and revoked_at is null" + (" and role=?" if role else "")
        return s.db.execute(q, (merchant_id, role) if role else (merchant_id,)).fetchall()
    def assurance(s, person):
        r = s.db.execute("select merchant_id from identities where person=?", (person,)).fetchone()
        return "high" if r and r[0] and s._devices(r[0], "owner") else "standard"
    def _lang(s, person): return s.db.execute("select lang from identities where person=?", (person,)).fetchone()[0]
    def _alert(s, person, key, extra=None):
        s.c.store.append("_identity", "server", "alert.sent", {"person": person, "key": key, "text": t(s._lang(person), key),
                         "channels": ["sms", "email", "push"], **(extra or {})})
    # sessions bound to one site, and step-up
    def sign_in(s, person, site, now=None):
        if site not in SITES: raise ValueError("unknown site")
        tok = secrets.token_hex(16)
        s.db.execute("insert into isessions values(?,?,?,?)", (tok, person, site, _now(now) + s.SESSION_S)); s.db.commit(); return tok
    def validate_session(s, token, site, now=None):
        r = s.db.execute("select person,site,expires from isessions where token=?", (token,)).fetchone()
        return r[0] if r and r[1] == site and r[2] > _now(now) else None   # a token from another site is refused
    def begin_stepup(s, person, now=None):
        code = f"{secrets.randbelow(10**6):06d}"
        s.db.execute("insert or replace into ichallenges values(?,?,?)", (person, _h(code), _now(now) + s.STEPUP_S)); s.db.commit(); return code
    def complete_stepup(s, person, session_token, code, now=None):
        if not any(s.validate_session(session_token, site, now) == person for site in SITES): raise PermissionError("sign in first")
        s._attempt(person, now)
        r = s.db.execute("select code,expires from ichallenges where person=?", (person,)).fetchone()
        if not r or r[1] < _now(now) or r[0] != _h(code): raise PermissionError("wrong or expired code")
        tok = secrets.token_hex(16)
        s.db.execute("insert into istepups values(?,?,?,?)", (tok, person, "sensitive", _now(now) + s.STEPUP_S)); s.db.commit(); return tok
    def stepup_valid(s, token, scope="sensitive", now=None):
        r = s.db.execute("select scope,expires from istepups where token=?", (token or "",)).fetchone()
        return bool(r and r[0] == scope and r[1] > _now(now))
    def _attempt(s, person, now=None):
        n = _now(now)
        if s.db.execute("select count(*) from iattempts where person=? and ts>?", (person, n - 3600)).fetchone()[0] >= s.MAX_ATTEMPTS:
            raise PermissionError("too many attempts: try again later")
        s.db.execute("insert into iattempts values(?,?)", (person, n)); s.db.commit()
    # owner recovery: layered, SMS never enough on its own
    def _new_recovery(s, person, path, new_device, lost_device, wait, now):
        rid = secrets.token_hex(8)
        s.db.execute("insert into irecoveries values(?,?,?,?,?,?,?,?)", (rid, person, path, new_device, lost_device, "waiting", _now(now) + wait, "[]")); s.db.commit()
        s._alert(person, "recovery_started", {"recovery_id": rid, "path": path}); return rid
    def _merchant(s, person): return s.db.execute("select merchant_id from identities where person=?", (person,)).fetchone()[0]
    def _finish(s, rid, now):
        _, person, path, new_dev, lost, *_ = s.db.execute("select * from irecoveries where id=?", (rid,)).fetchone(); m = s._merchant(person)
        s.enroll_device(person, m, new_dev, "owner", now, restricted_until=_now(now) + 24 * 3600)   # restricted for 24 hours
        if lost: s.revoke_device(lost, now)
        s.db.execute("update irecoveries set status='done' where id=?", (rid,)); s.db.commit(); s._alert(person, "recovery_done", {"recovery_id": rid})
    def approve_by_device(s, person, new_device, approver_device, pin_ok, lost_device=None, now=None):
        """Path 1, fastest and strongest: another enrolled owner device approves with its PIN."""
        m = s._merchant(person)
        if not pin_ok or approver_device not in [d[0] for d in s._devices(m, "owner")]: raise PermissionError("approval must come from an enrolled owner device with its PIN")
        rid = s._new_recovery(person, "device", new_device, lost_device, 0, now); s._finish(rid, now); return rid
    def start_code_recovery(s, person, recovery_code, sms_ok, new_device, lost_device=None, now=None):
        """Path 2: recovery code AND SMS code, then a 24-hour wait during which any enrolled device or the backup contact can cancel."""
        s._attempt(person, now); r = s.db.execute("select recovery_hash from identities where person=?", (person,)).fetchone()
        if not sms_ok or not r or r[0] != _h(recovery_code or ""): raise PermissionError("recovery needs the recovery code and the SMS code")
        return s._new_recovery(person, "code", new_device, lost_device, s.WAIT_S, now)
    def start_assisted(s, person, new_device, identity_check_done, business_proof_done, lost_device=None, now=None):
        """Path 3, last resort: 72-hour wait and two different staff approvals. Never a phone-call reset."""
        if not (identity_check_done and business_proof_done): raise PermissionError("support needs an ID check and business proof")
        return s._new_recovery(person, "assisted", new_device, lost_device, s.ASSISTED_S, now)
    def staff_approve(s, rid, staff_id):
        r = s.db.execute("select approvals from irecoveries where id=? and path='assisted'", (rid,)).fetchone(); a = set(json.loads(r[0])) | {staff_id}
        s.db.execute("update irecoveries set approvals=? where id=?", (json.dumps(sorted(a)), rid)); s.db.commit()
        s.c.store.append("_identity", staff_id, "audit.logged", {"action": "recovery_approved", "recovery_id": rid})
    def cancel_recovery(s, rid, by):
        person = s.db.execute("select person from irecoveries where id=?", (rid,)).fetchone()[0]; m = s._merchant(person)
        allowed = [d[0] for d in s._devices(m)] + [s.db.execute("select backup_contact from identities where person=?", (person,)).fetchone()[0]]
        if by not in allowed: raise PermissionError("only an enrolled device or the backup contact can cancel")
        s.db.execute("update irecoveries set status='cancelled' where id=?", (rid,)); s.db.commit()
    def complete_recovery(s, rid, now=None):
        r = s.db.execute("select status,ready_at,path,approvals from irecoveries where id=?", (rid,)).fetchone()
        if r[0] != "waiting": raise PermissionError(f"recovery is {r[0]}")
        if _now(now) < r[1]: raise PermissionError("the waiting period is not over")
        if r[2] == "assisted" and len(json.loads(r[3])) < 2: raise PermissionError("two staff approvals are required")
        s._finish(rid, now)
    def device_can(s, device_id, action, now=None):
        r = s.db.execute("select restricted_until,revoked_at from idevices where device_id=?", (device_id,)).fetchone()
        return bool(r and r[1] is None and not (action in RESTRICTED and r[0] > _now(now)))
    def rotate_recovery_code(s, person, approver_device):
        if approver_device not in [d[0] for d in s._devices(s._merchant(person), "owner")]: raise PermissionError("an enrolled owner device must approve a new code")
        return s.add_merchant_role(person, s._merchant(person), s.db.execute("select backup_contact from identities where person=?", (person,)).fetchone()[0])
    def staff_recover(s, *a, **k): raise PermissionError("staff accounts cannot self-recover: the owner resets them")
    def owner_reset_staff(s, owner_device, staff_person):
        if not s.db.execute("select 1 from idevices where device_id=? and role='owner' and revoked_at is null", (owner_device,)).fetchone(): raise PermissionError("owner device required")
        s.c.store.append("_identity", owner_device, "audit.logged", {"action": "staff_reset", "staff": staff_person})
    # consumer-only accounts: a lighter recovery with alerts and a waiting period for sensitive changes
    def start_consumer_recovery(s, person, phone_ok, email_ok, now=None):
        if not (phone_ok and email_ok): raise PermissionError("consumer recovery needs both a verified phone and a verified email")
        s._attempt(person, now)
        s.db.execute("insert or replace into irecoveries values(?,?,?,?,?,?,?,?)", (f"c-{person}", person, "consumer", None, None, "waiting", _now(now) + s.WAIT_S, "[]")); s.db.commit()
        s._alert(person, "recovery_started", {"path": "consumer"})
    def sensitive_change_allowed(s, person, now=None):
        r = s.db.execute("select status,ready_at from irecoveries where id=?", (f"c-{person}",)).fetchone()
        return not (r and r[0] == "waiting" and _now(now) < r[1])
