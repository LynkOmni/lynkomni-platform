"""LynkCCBox: cloud intake of device events under contract v1. Persistent (SQLite), idempotent, replay-safe.
Signatures are checked for FORMAT only. Real ES256 verification needs a crypto library and device public keys."""
import json, sqlite3
from datetime import datetime, timezone
from contract.tools.validate_contract import ReferenceIngest, event_hash, stock_projection, ts, validate_event

class LynkCCBox:
    SKEW_MS = ReferenceIngest.SKEW_MS
    ENTITY_KEY = ReferenceIngest.ENTITY_KEY
    def __init__(s, path=":memory:", ids=None):
        s.db = sqlite3.connect(path); s.ids = ids   # an IdAllocator on the same database gives accepted records their public LO identifiers
        s.db.executescript("""
        create table if not exists devices(device_id text primary key, merchant_id text, public_key text, last_seq int, last_hash text, revoked_at text);
        create table if not exists events(event_id text primary key, status text, reason text, cursor int, device_id text, device_seq int,
                                          merchant_id text, body text, flags text, received_at text, clock_offset_ms int);
        create table if not exists entities(type text, entity_id text, event_id text, primary key(type, entity_id));
        create index if not exists ev_cursor on events(merchant_id, cursor);""")
    # devices
    def enroll(s, device_id, merchant_id, public_key=None):
        s.db.execute("insert or ignore into devices values(?,?,?,0,'GENESIS',null)", (device_id, merchant_id, public_key)); s.db.commit()
    def revoke_user(s, user_id, at):
        s.db.execute("create table if not exists revoked_users(user_id text primary key, revoked_at text)")
        s.db.execute("insert or replace into revoked_users values(?,?)", (user_id, at)); s.db.commit()
    def owner_alerts(s, merchant_id):
        """Accepted-but-flagged events the owner should look at (revoked user or device, manual confirmations)."""
        return [(e["event_id"], e["flags"]) for e in s.events(merchant_id) if set(e["flags"]) & {"after_user_revocation", "after_revocation", "manual_confirmation"}]
    def revoke(s, device_id, at):
        s.db.execute("update devices set revoked_at=? where device_id=?", (at, device_id)); s.db.commit()
    def _dev(s, device_id):
        r = s.db.execute("select last_seq,last_hash,revoked_at from devices where device_id=?", (device_id,)).fetchone()
        return {"last_seq": r[0], "last_hash": r[1], "revoked_at": r[2]} if r else None
    def _save(s, device_id, seq, h): s.db.execute("update devices set last_seq=?, last_hash=? where device_id=?", (seq, h, device_id))
    def _cursor(s): return (s.db.execute("select coalesce(max(cursor),0) from events").fetchone()[0]) + 1
    def _quarantine(s, dev, evt, reason):
        s.db.execute("insert into events(event_id,status,reason,device_id,device_seq,merchant_id,body) values(?,?,?,?,?,?,?)",
                     (evt["event_id"], "quarantined", reason, evt["device_id"], evt["device_seq"], evt.get("merchant_id"), json.dumps(evt)))
        s._save(evt["device_id"], evt["device_seq"], event_hash(evt)); dev["last_seq"] = evt["device_seq"]  # slot consumed: the stream never stalls
        return {"event_id": evt["event_id"], "result": "quarantined", "reason": reason}
    # intake
    def push(s, batch, device_now=None):
        results = []
        for evt in batch:
            did = evt.get("device_id"); dev = s._dev(did)
            if dev is None:
                results.append({"event_id": evt.get("event_id"), "result": "rejected_unknown_device"}); break
            known = s.db.execute("select status from events where event_id=?", (evt["event_id"],)).fetchone()
            if known:
                results.append({"event_id": evt["event_id"], "result": "duplicate", "stored_status": known[0]}); continue
            expected = dev["last_seq"] + 1
            if evt["device_seq"] > expected:
                results.append({"event_id": evt["event_id"], "result": "gap", "expected_seq": expected}); break
            if evt["device_seq"] < expected:
                s.db.execute("insert into events(event_id,status,reason,device_id,device_seq,merchant_id,body) values(?,?,?,?,?,?,?)",
                             (evt["event_id"], "quarantined", "broken_hash_chain", did, evt["device_seq"], evt.get("merchant_id"), json.dumps(evt)))
                results.append({"event_id": evt["event_id"], "result": "quarantined", "reason": "broken_hash_chain"}); continue
            problems = validate_event(evt)
            if problems:
                bad = "unsupported schema_version" in problems[0] or "unknown event type" in problems[0]
                results.append(s._quarantine(dev, evt, "unknown_schema_version" if bad else "invalid_payload")); continue
            if evt["prev_hash"] != dev["last_hash"]:
                results.append(s._quarantine(dev, evt, "broken_hash_chain")); continue
            flags = []
            if dev["revoked_at"] is not None:
                if evt["occurred_at_device"] <= dev["revoked_at"]:
                    flags.append("after_revocation")
                else:
                    results.append(s._quarantine(dev, evt, "after_revocation")); continue
            if s.db.execute("select 1 from sqlite_master where name='revoked_users'").fetchone():
                ru = s.db.execute("select revoked_at from revoked_users where user_id=?", (evt.get("actor_user_id"),)).fetchone()
                if ru and evt["occurred_at_device"] >= ru[0]: flags.append("after_user_revocation")   # flagged for the owner, never silent, never dropped
            key = s.ENTITY_KEY.get(evt["type"])
            if key and evt["type"] != "ReceiptIssued":
                owner = s.db.execute("select event_id from entities where type=? and entity_id=?", (evt["type"], evt["payload"][key])).fetchone()
                if owner and owner[0] != evt["event_id"]:
                    results.append(s._quarantine(dev, evt, "duplicate_entity_id")); continue
                s.db.execute("insert or ignore into entities values(?,?,?)", (evt["type"], evt["payload"][key], evt["event_id"]))
            offset = None
            if device_now is not None:
                offset = int((datetime.now(timezone.utc) - datetime.fromisoformat(device_now.replace("Z", "+00:00"))).total_seconds() * 1000)
                if abs(offset) > s.SKEW_MS:
                    flags.append("clock_skew")
            if evt["type"] == "PaymentStatusChanged":
                flags.append("manual_confirmation")
            cur = s._cursor()
            s.db.execute("insert into events values(?,?,?,?,?,?,?,?,?,?,?)", (evt["event_id"], "accepted", None, cur, did, evt["device_seq"],
                         evt["merchant_id"], json.dumps(evt), json.dumps(flags), ts(), offset))
            s._save(did, evt["device_seq"], event_hash(evt)); dev["last_seq"] = evt["device_seq"]
            if s._leaves_negative_stock(evt) and "negative_stock" not in flags:
                flags.append("negative_stock"); s.db.execute("update events set flags=? where event_id=?", (json.dumps(flags), evt["event_id"]))
            s._public_ids(evt)
            results.append({"event_id": evt["event_id"], "result": "accepted", "flags": flags})
        s.db.commit()
        ack = max((s._dev(d)["last_seq"] for d in {e.get("device_id") for e in batch} if s._dev(d)), default=0)
        return {"results": results, "ack_seq": ack}
    # reads
    PUBLIC = {"SaleRecorded": ("ORD", "sale_id"), "ReceiptIssued": ("RCP", "receipt_id"), "PaymentRecorded": ("TXN", "payment_id")}
    def _public_ids(s, evt):
        """Public IDs are assigned by the cloud when a record is accepted. Internal UUIDs stay the keys; a POS sale is an order."""
        if s.ids and evt["type"] in s.PUBLIC:
            code, key = s.PUBLIC[evt["type"]]; s.ids.assign(code, evt["payload"][key])
    def claim_leased(s, device_id, mapping):
        """A device that printed identifiers from its leased block reports {internal_id: public_id}. Only IDs leased to it can be claimed."""
        from core.ids import parse
        for internal, public in mapping.items():
            s.ids.claim(public, internal, device_id); parse(public)
    def events(s, merchant_id, after_cursor=0):
        out = []
        for body, cur, flags, off in s.db.execute("select body,cursor,flags,clock_offset_ms from events where merchant_id=? and status='accepted' and cursor>? order by cursor", (merchant_id, after_cursor)):
            e = json.loads(body); e.update(server_cursor=cur, flags=json.loads(flags))
            if off is not None: e["clock_offset_ms"] = off
            out.append(e)
        return out
    def quarantined(s, merchant_id):
        return [(json.loads(b)["event_id"], r) for b, r in s.db.execute("select body,reason from events where merchant_id=? and status='quarantined'", (merchant_id,))]
    def stock(s, merchant_id): return stock_projection(s.events(merchant_id))   # order-independent: a sum of deltas
    def negative_stock(s, merchant_id): return {k: v for k, v in s.stock(merchant_id).items() if v < 0}
    def _leaves_negative_stock(s, evt):
        if evt["type"] not in ("SaleRecorded", "StockAdjusted", "StockCounted", "SaleVoided", "ReturnRecorded", "StockReceived"):
            return False
        return bool(s.negative_stock(evt["merchant_id"]))
