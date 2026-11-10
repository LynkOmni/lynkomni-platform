"""Append-only, idempotent event log. The single source of truth; everything else is a projection.

Tamper evidence (MASTER UPDATE, master blueprint section 59): every event carries a chain value, the SHA-256 of the previous
event's chain value and this event's own fields. Changing, removing or reordering any stored event breaks the chain from that
point on, and verify() names the first broken event. The chain proves the log was not quietly changed; it does not hide anything,
and it adds no personal data to the log."""
import hashlib, json, sqlite3, time, uuid

GENESIS = "0" * 64


def link(prev, id_, merchant, device, type_, ts, payload_json):
    """The chain value of one event: SHA-256 over the previous value and the event's own fields, in a fixed order."""
    body = json.dumps([prev, id_, merchant, device, type_, ts, payload_json], separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(body.encode()).hexdigest()


class EventStore:
    def __init__(self, path=":memory:"):
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.execute("create table if not exists events(seq integer primary key autoincrement, "
                        "id text unique, merchant text, device text, type text, ts text, payload text, chain text)")
        cols = [r[1] for r in self.db.execute("pragma table_info(events)")]
        if "chain" not in cols:                                   # a log made before the chain existed: add it and seal what is there
            self.db.execute("alter table events add column chain text")
            self._seal_existing()
        self.observers = []          # projections that follow the log as it grows (services/tracking.py); called once per new event

    def _last(self):
        r = self.db.execute("select chain from events order by seq desc limit 1").fetchone()
        return r[0] if r and r[0] else GENESIS

    def _seal_existing(self):
        prev = GENESIS
        for seq, id_, m, d, t, ts, p in self.db.execute("select seq,id,merchant,device,type,ts,payload from events order by seq").fetchall():
            prev = link(prev, id_, m, d, t, ts, p)
            self.db.execute("update events set chain=? where seq=?", (prev, seq))
        self.db.commit()

    def append(self, merchant, device, type_, payload, id_=None, ts=None):
        """Returns False for a duplicate id, so retries never double-count."""
        ts = ts or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        id_ = id_ or uuid.uuid4().hex
        body = json.dumps(payload)
        if self.db.execute("select 1 from events where id=?", (id_,)).fetchone():
            return False
        chain = link(self._last(), id_, merchant, device, type_, ts, body)
        try:
            self.db.execute("insert into events(id,merchant,device,type,ts,payload,chain) values(?,?,?,?,?,?,?)",
                            (id_, merchant, device, type_, ts, body, chain))
            self.db.commit()
        except sqlite3.IntegrityError:
            return False
        for observe in list(self.observers):
            observe(merchant, type_, payload, ts)
        return True

    def verify(self):
        """Walks the whole log. Returns {"ok": True, "events": n} or {"ok": False, "broken_at": seq} for the first event whose
        stored chain value does not match what its fields and the event before it produce."""
        prev, n = GENESIS, 0
        for seq, id_, m, d, t, ts, p, chain in self.db.execute("select seq,id,merchant,device,type,ts,payload,chain from events order by seq"):
            prev = link(prev, id_, m, d, t, ts, p)
            if prev != chain:
                return {"ok": False, "broken_at": seq}
            n += 1
        return {"ok": True, "events": n}

    def head(self):
        """The chain value of the newest event: a short fingerprint of the whole log, to be copied somewhere the log cannot reach."""
        return self._last()

    def _rows(self, q, args):
        return [dict(seq=r[0], id=r[1], device=r[2], type=r[3], ts=r[4], payload=json.loads(r[5]), merchant=r[6])
                for r in self.db.execute(q, args)]
    def since(self, merchant, seq=0):
        return self._rows("select seq,id,device,type,ts,payload,merchant from events where merchant=? and seq>? order by seq", (merchant, seq))
    def all_of(self, *types):
        """Company-level query across merchants (Control Center only)."""
        marks = ",".join("?" * len(types))
        return self._rows(f"select seq,id,device,type,ts,payload,merchant from events where type in ({marks}) order by seq", types)
    def of(self, merchant, *types):
        marks = ",".join("?" * len(types))
        return self._rows(f"select seq,id,device,type,ts,payload,merchant from events where merchant=? and type in ({marks}) order by seq", (merchant, *types))
