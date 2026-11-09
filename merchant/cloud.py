"""Server events for the Business app: one place that builds a contract server envelope, validates it (contract v2, origin
'server') and appends it to the platform's event store, then hands it to LynkFlow. Signals that are not contract events are
named in merchant/events.v1.json and checked against it the same way identity/account.py checks its register.
SERVER SIGNATURE IS A DEV-ONLY PLACEHOLDER (provider ledger, later: server_signing_key)."""
import json, os, time, uuid
from datetime import datetime, timezone

from contract.tools.validate_contract import fake_sig, uuid7, validate_event

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
with open(os.path.join(ROOT, "merchant", "events.v1.json"), encoding="utf-8") as f:
    SIGNALS = json.load(f)["events"]


def _ts(now):
    return datetime.fromtimestamp(now, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _now(n): return time.time() if n is None else n


class Cloud:
    def __init__(s, platform, flow=None):
        s.p, s.c, s.db, s.flow = platform, platform.c, platform.c.store.db, flow
        s.db.executescript("create table if not exists mc_cursor(k text primary key, v integer);")
    def _cursor(s):
        r = s.db.execute("select v from mc_cursor where k='cursor'").fetchone()
        v = (r[0] if r else 0) + 1
        s.db.execute("insert or replace into mc_cursor(k, v) values('cursor', ?)", (v,))
        return v
    def event(s, merchant, type_, payload, now=None, causes=None):
        """A contract server event (origin 'server'), validated like every other event; returns its id."""
        evt = {"event_id": uuid7(), "origin": "server", "merchant_id": merchant, "type": type_, "schema_version": 2,
               "created_at_server": _ts(_now(now)), "server_cursor": s._cursor(), "payload": payload, "server_signature": fake_sig()}   # PLACEHOLDER signature
        if causes: evt["cause_event_ids"] = list(causes)
        problems = validate_event(evt)
        if problems: raise ValueError(f"{type_}: {problems}")
        s.c.store.append(merchant, "server", type_, payload, id_=evt["event_id"], ts=evt["created_at_server"])
        if s.flow: s.flow.on_event(merchant, {"id": evt["event_id"], "type": type_, "payload": payload}, now=now)
        return evt["event_id"]
    def signal(s, merchant, type_, payload, now=None, by="cloud"):
        """A Business-app signal from merchant/events.v1.json (not a contract fact): references only."""
        if type_ not in SIGNALS: raise ValueError(f"{type_} is not a Business app signal (merchant/events.v1.json)")
        bad = set(payload) - set(SIGNALS[type_]["payload"])
        if bad: raise ValueError(f"{type_} must not carry {sorted(bad)}")
        eid = uuid.uuid4().hex
        s.c.store.append(merchant, "server" if by == "cloud" else by, type_, payload, id_=eid, ts=_ts(_now(now)))
        if s.flow: s.flow.on_event(merchant, {"id": eid, "type": type_, "payload": payload}, now=now)
        return eid
    def device_event(s, merchant, evt, now=None):
        """A device event that reached the cloud (already validated and chained by cc/box.py): kept for projections and fed to LynkFlow."""
        s.c.store.append(merchant, evt.get("device_id", "device"), evt["type"], evt["payload"], id_=evt["event_id"], ts=_ts(_now(now)))
        if s.flow: s.flow.on_event(merchant, {"id": evt["event_id"], "type": evt["type"], "payload": evt["payload"]}, now=now)
        return evt["event_id"]
    def of(s, merchant, *types): return s.c.store.of(merchant, *types)
