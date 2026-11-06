"""Append-only, idempotent event log. The single source of truth; everything else is a projection."""
import json, sqlite3, time, uuid

class EventStore:
    def __init__(self, path=":memory:"):
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.execute("create table if not exists events(seq integer primary key autoincrement, "
                        "id text unique, merchant text, device text, type text, ts text, payload text)")
    def append(self, merchant, device, type_, payload, id_=None, ts=None):
        """Returns False for a duplicate id, so retries never double-count."""
        try:
            self.db.execute("insert into events(id,merchant,device,type,ts,payload) values(?,?,?,?,?,?)",
                            (id_ or uuid.uuid4().hex, merchant, device, type_,
                             ts or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), json.dumps(payload)))
            self.db.commit()
            return True
        except sqlite3.IntegrityError:
            return False
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
