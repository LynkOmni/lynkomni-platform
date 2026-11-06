"""LynkOmni Universal Identifier Standard (reference implementation).
LO + TYPE + '-XXXX-XXXX-XXXX': 12 digits, random (never sequential), last digit is a Luhn check digit, stored as strings.
Uniqueness is enforced by the database, retired identifiers are never reissued, and a public ID never grants access by itself."""
import json, os, re, secrets, sqlite3, threading, time

_REG = json.load(open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "contract", "identifier-registry.v1.json")))
TYPES = {t["code"]: t for t in _REG["types"]}
_PAT = re.compile(r"^LO([A-Z]{2,4})-(\d{4})-(\d{4})-(\d{4})$")

def luhn_digit(p11):
    s = 0
    for i, ch in enumerate(reversed(p11)):
        d = int(ch) * (2 if i % 2 == 0 else 1)
        s += d - 9 if d > 9 else d
    return str((10 - s % 10) % 10)

def luhn_ok(p12):
    s = 0
    for i, ch in enumerate(reversed(p12)):
        d = int(ch) * (2 if i % 2 == 1 else 1)
        s += d - 9 if d > 9 else d
    return s % 10 == 0

def fmt(code, p12): return f"LO{code}-{p12[:4]}-{p12[4:8]}-{p12[8:]}"

def parse(public_id):
    """Format check only. A well-formed ID does not prove the record exists or that anyone may access it."""
    m = _PAT.match(public_id or "")
    if not m or m.group(1) not in TYPES:
        raise ValueError("not a registered LynkOmni identifier")
    payload = "".join(m.group(2, 3, 4))
    if not luhn_ok(payload):
        raise ValueError("check digit does not match: a typing error?")
    return m.group(1), payload

def _locked(f):
    def w(s, *a, **k):
        with s._lock: return f(s, *a, **k)
    w.__name__ = f.__name__; w.__doc__ = f.__doc__
    return w

class IdAllocator:
    def __init__(s, db):
        s.db = db; s._lock = threading.RLock()      # one shared connection: serialise access across threads
        db.executescript("""
        create table if not exists public_ids(public_id text primary key, type text not null, internal_id text, status text not null,
                                              leased_to text, created_at real, check(length(public_id) between 18 and 22));
        create unique index if not exists pid_internal on public_ids(type, internal_id) where internal_id is not null;""")
    @_locked
    def _new(s, code, internal_id=None, status="assigned", leased_to=None):
        if code not in TYPES:
            raise ValueError(f"type {code} is not registered")
        for _ in range(50):                                   # collisions are retried, never silently reused
            p11 = f"{secrets.randbelow(10 ** 11):011d}"; pid = fmt(code, p11 + luhn_digit(p11))
            try:
                s.db.execute("insert into public_ids values(?,?,?,?,?,?)", (pid, code, internal_id, status, leased_to, time.time())); s.db.commit()
                return pid
            except sqlite3.IntegrityError:
                s.db.rollback()
                if internal_id is not None:
                    r = s.db.execute("select public_id from public_ids where type=? and internal_id=?", (code, internal_id)).fetchone()
                    if r: return r[0]                          # a concurrent request got there first: same record, same ID
        raise RuntimeError("could not allocate an identifier")
    @_locked
    def assign(s, code, internal_id):
        """Idempotent: the same internal record always gets the same public ID."""
        r = s.db.execute("select public_id from public_ids where type=? and internal_id=?", (code, internal_id)).fetchone()
        return r[0] if r else s._new(code, internal_id)
    @_locked
    def lookup(s, public_id):
        r = s.db.execute("select type,internal_id,status,leased_to from public_ids where public_id=?", (public_id,)).fetchone()
        return dict(type=r[0], internal_id=r[1], status=r[2], leased_to=r[3]) if r else None
    @_locked
    def public_for(s, code, internal_id):
        r = s.db.execute("select public_id from public_ids where type=? and internal_id=?", (code, internal_id)).fetchone()
        return r[0] if r else None
    # offline use: a device is leased a block of IDs it may print before it ever syncs
    def lease(s, code, device_id, n=50): return [s._new(code, None, "leased", device_id) for _ in range(n)]
    @_locked
    def claim(s, public_id, internal_id, device_id):
        r = s.lookup(public_id)
        if not r or r["status"] != "leased" or r["leased_to"] != device_id:
            raise PermissionError("this identifier was not leased to this device")
        s.db.execute("update public_ids set internal_id=?, status='assigned' where public_id=?", (internal_id, public_id)); s.db.commit()
    @_locked
    def release(s, device_id):
        """Unused leased IDs are retired for good (gaps are fine; reuse is not)."""
        c = s.db.execute("update public_ids set status='retired' where leased_to=? and status='leased'", (device_id,)); s.db.commit(); return c.rowcount
    @_locked
    def retire(s, public_id): s.db.execute("update public_ids set status='retired' where public_id=?", (public_id,)); s.db.commit()
