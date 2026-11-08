#!/usr/bin/env python3
"""
LynkOmni contract validator (stdlib only).

1. Cross-checks the four contract files against each other.
2. Validates sample events against the envelope and payload schemas.
3. Runs a reference model of LynkCCBox event intake (idempotency, gaps, hash chain,
   quarantine, revocation, stock projection) to prove the rules are consistent.

Not covered here (needs real crypto and a device): ES256 signature verification.
This tool checks signature FORMAT only. Run:  python3 tools/validate_contract.py
"""
import base64, hashlib, itertools, json, os, random, re, sys, time
from datetime import datetime, timezone, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load(name):
    with open(os.path.join(ROOT, name), encoding="utf-8") as f:
        return json.load(f)


ENVELOPE = load("event-envelope.v1.json")
REGISTRY_V1 = load("event-payloads.v1.json")          # published, never edited; still readable through the upcaster
REGISTRY = load("event-payloads.v2.json")             # the current version (Step 0: any currency, the new event names)
REGISTRIES = {1: REGISTRY_V1, 2: REGISTRY}
CURRENCIES = load("currencies.v1.json")["decimals"]
PERMS = load("permissions.v1.json")
REGISTER = load("command-policy-register.v2.json")
STATES = load("state-machines.v1.json")
SAMPLE_CURRENCY = load(os.path.join("country-packs", "XX.json"))["currency"]   # the neutral sample pack, never a real country

# ---------------------------------------------------------------- mini JSON Schema
def _type_ok(v, t):
    if t == "object": return isinstance(v, dict)
    if t == "array": return isinstance(v, list)
    if t == "string": return isinstance(v, str)
    if t == "boolean": return isinstance(v, bool)
    if t == "null": return v is None
    if t == "integer": return isinstance(v, int) and not isinstance(v, bool)
    return False


def resolve(ref, root):
    assert ref.startswith("#/"), ref
    node = root
    for part in ref[2:].split("/"):
        node = node[part]
    return node


def validate(value, schema, root, path="$"):
    """Returns a list of error strings. Supports the subset of JSON Schema used here."""
    errs = []
    if "$ref" in schema:
        return validate(value, resolve(schema["$ref"], root), root, path)
    if "const" in schema and value != schema["const"]:
        errs.append(f"{path}: must equal {schema['const']!r}")
    if "enum" in schema and value not in schema["enum"]:
        errs.append(f"{path}: {value!r} not in enum")
    if "type" in schema:
        types = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
        if not any(_type_ok(value, t) for t in types):
            errs.append(f"{path}: expected {types}, got {type(value).__name__}")
            return errs
    if isinstance(value, str):
        if "pattern" in schema and not re.search(schema["pattern"], value):
            errs.append(f"{path}: does not match pattern")
        if "minLength" in schema and len(value) < schema["minLength"]:
            errs.append(f"{path}: too short")
        if "maxLength" in schema and len(value) > schema["maxLength"]:
            errs.append(f"{path}: too long")
    if isinstance(value, int) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            errs.append(f"{path}: below minimum")
        if "maximum" in schema and value > schema["maximum"]:
            errs.append(f"{path}: above maximum")
    if isinstance(value, list):
        if "minItems" in schema and len(value) < schema["minItems"]:
            errs.append(f"{path}: too few items")
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            errs.append(f"{path}: too many items")
        if "items" in schema:
            for i, item in enumerate(value):
                errs += validate(item, schema["items"], root, f"{path}[{i}]")
    if isinstance(value, dict):
        props = schema.get("properties", {})
        for req in schema.get("required", []):
            if req not in value:
                errs.append(f"{path}: missing required '{req}'")
        if "minProperties" in schema and len(value) < schema["minProperties"]:
            errs.append(f"{path}: too few properties")
        for k, v in value.items():
            if k in props:
                errs += validate(v, props[k], root, f"{path}.{k}")
            elif schema.get("additionalProperties") is False:
                errs.append(f"{path}: unexpected field '{k}'")
    return errs


def reject_floats(value, path="$"):
    if isinstance(value, float):
        return [f"{path}: floating-point number not allowed"]
    errs = []
    if isinstance(value, dict):
        for k, v in value.items():
            errs += reject_floats(v, f"{path}.{k}")
    if isinstance(value, list):
        for i, v in enumerate(value):
            errs += reject_floats(v, f"{path}[{i}]")
    return errs


# ---------------------------------------------------------------- event validation
SERVER_STAMP_KEYS = set(ENVELOPE["$defs"]["server_stamp"]["properties"])
PAYMENT_STATES = STATES["payment"]["states"]
METHOD_STATUS = {"cash": "cash_received", "credit": "credit_open"}


def round_half_up_line(qty_milli, unit_price, discount):
    return (qty_milli * unit_price + 500) // 1000 - discount


def domain_errors(etype, p):
    errs = []
    if etype == "SaleRecorded":
        lines = p["lines"]
        nos = [l["line_no"] for l in lines]
        if nos != list(range(1, len(lines) + 1)):
            errs.append("line_no must run 1..n in order")
        for l in lines:
            if l["line_total"] != round_half_up_line(l["quantity_milli"], l["unit_price"], l["discount"]):
                errs.append(f"line {l['line_no']}: line_total mismatch")
        if p["subtotal"] != sum(l["line_total"] for l in lines):
            errs.append("subtotal != sum(line_total)")
        if p["discount_total"] != sum(l["discount"] for l in lines):
            errs.append("discount_total != sum(line discount)")
        expected = p["subtotal"] + (p["tax_total"] if p["tax_mode"] == "exclusive" else 0)
        if p["total"] != expected:
            errs.append("total mismatch")
    elif etype == "ReturnRecorded":
        if p["refund_total"] != sum(l["refund_amount"] for l in p["lines"]):
            errs.append("refund_total != sum(refund_amount)")
    elif etype == "PaymentRecorded":
        want = METHOD_STATUS.get(p["method"], "pending_confirmation")
        if p["status"] != want:
            errs.append(f"method {p['method']} requires status {want}")
    elif etype == "StockReceived":
        if any("unit_cost" in l for l in p["lines"]) and "currency" not in p:
            errs.append("unit_cost needs a currency")
    elif etype == "ProductUpdated":
        if "price" in p["changes"] and "currency" not in p:
            errs.append("price change needs a currency")
    elif etype == "StockAdjusted":
        if p["delta_milli"] == 0:
            errs.append("delta_milli must be non-zero")
    elif etype == "PaymentStatusChanged":
        ok = [t for t in STATES["payment"]["transitions"]
              if t["from"] == p["from_status"] and t["to"] == p["to_status"] and p["source"] in t["allowed_sources"]]
        if not ok:
            errs.append("illegal payment transition or source")
    return errs


def validate_event(evt, stored=False):
    """Validate one event. stored=True allows server_stamp fields on device events."""
    errs = reject_floats(evt)
    origin = evt.get("origin")
    if origin not in ("device", "server"):
        return errs + ["origin must be 'device' or 'server'"]
    body = dict(evt)
    if origin == "device":
        if stored:
            body = {k: v for k, v in evt.items() if k not in SERVER_STAMP_KEYS}
            errs += validate({k: evt[k] for k in evt if k in SERVER_STAMP_KEYS},
                             ENVELOPE["$defs"]["server_stamp"], ENVELOPE)
        errs += validate(body, ENVELOPE["$defs"]["device_event"], ENVELOPE)
    else:
        errs += validate(body, ENVELOPE["$defs"]["server_event"], ENVELOPE)
    if errs:
        return errs
    if evt["type"] not in REGISTRY["events"]:
        return [f"unknown event type {evt['type']}"]
    registry = REGISTRIES.get(evt["schema_version"])
    entry = registry["events"].get(evt["type"]) if registry else None
    if not entry or evt["schema_version"] != entry["schema_version"]:
        return [f"unsupported schema_version {evt['schema_version']} for {evt['type']}"]
    if origin not in entry["origins"]:
        return [f"{evt['type']} may not originate from '{origin}'"]
    perr = validate(evt["payload"], entry["payload"], registry)
    if perr:
        return perr
    for key, want in entry.get("origin_constraints", {}).get(origin, {}).items():
        if key.endswith("_in"):
            field = key[:-3]
            if evt["payload"][field] not in want:
                return [f"{evt['type']} from {origin}: {field} must be one of {want}"]
        elif evt["payload"][key] != want:
            return [f"{evt['type']} from {origin}: {key} must be {want!r}"]
    return domain_errors(evt["type"], evt["payload"])


# ---------------------------------------------------------------- hash chain
def signing_bytes(evt):
    skip = SERVER_STAMP_KEYS | {"signature"}
    body = {k: v for k, v in evt.items() if k not in skip}
    return json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def event_hash(evt):
    return hashlib.sha256(signing_bytes(evt)).hexdigest()


# ---------------------------------------------------------------- sample builders
def uuid7():
    ms = int(time.time() * 1000) & ((1 << 48) - 1)
    rand_a = random.getrandbits(12)
    rand_b = random.getrandbits(62)
    n = (ms << 80) | (0x7 << 76) | (rand_a << 64) | (0b10 << 62) | rand_b
    h = f"{n:032x}"
    return f"{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:]}"


def uuid4():
    h = f"{random.getrandbits(128):032x}"
    return f"{h[:8]}-{h[8:12]}-4{h[13:16]}-a{h[17:20]}-{h[20:]}"


def fake_sig():
    return base64.urlsafe_b64encode(os.urandom(64)).decode().rstrip("=")


def ts(dt=None):
    dt = dt or datetime.now(timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%S.") + f"{dt.microsecond // 1000:03d}Z"


MERCHANT, BRANCH, USER = uuid4(), uuid4(), uuid4()


class Device:
    """Produces a correctly chained, sequenced stream of device events."""
    def __init__(self):
        self.id = uuid4()
        self.seq = 0
        self.prev = "GENESIS"
        self.clock = datetime.now(timezone.utc)

    def emit(self, etype, payload, at=None):
        self.seq += 1
        evt = {
            "event_id": uuid7(), "origin": "device", "merchant_id": MERCHANT, "branch_id": BRANCH,
            "device_id": self.id, "actor_user_id": USER, "device_seq": self.seq, "type": etype,
            "schema_version": 2, "occurred_at_device": ts(at or self.clock), "prev_hash": self.prev,
            "payload": payload, "signature": fake_sig(),
        }
        self.prev = event_hash(evt)
        return evt


def sale_payload(product_id, qty_milli=1000, unit_price=1500, discount=0, currency=SAMPLE_CURRENCY):
    lt = round_half_up_line(qty_milli, unit_price, discount)
    return {
        "sale_id": uuid7(), "receipt_number_local": "A1-1",
        "lines": [{"line_no": 1, "product_id": product_id, "product_name": "Juice 1L",
                   "quantity_milli": qty_milli, "unit_price": unit_price, "discount": discount, "line_total": lt}],
        "subtotal": lt, "discount_total": discount, "tax_total": 0, "tax_mode": "none", "total": lt, "currency": currency,
    }


# ---------------------------------------------------------------- reference model of LynkCCBox intake
class ReferenceIngest:
    ENTITY_KEY = {"SaleRecorded": "sale_id", "PaymentRecorded": "payment_id", "ReturnRecorded": "return_id",
                  "StockReceived": "stock_receipt_id", "StockAdjusted": "adjustment_id",
                  "StockCounted": "count_id", "ProductCreated": "product_id", "ReceiptIssued": "receipt_id"}
    SKEW_MS = 600_000

    def __init__(self):
        self.cursor = 0
        self.devices = {}     # device_id -> dict(last_seq, last_hash, revoked_at)
        self.by_id = {}       # event_id -> stored record
        self.entities = {}    # (type, entity_id) -> event_id
        self.store = []       # accepted/flagged events in server order
        self.quarantine = []  # (event, reason)

    def enroll(self, device_id):
        self.devices[device_id] = {"last_seq": 0, "last_hash": "GENESIS", "revoked_at": None}

    def revoke(self, device_id, at):
        self.devices[device_id]["revoked_at"] = at

    def _quarantine(self, dev, evt, reason):
        self.quarantine.append((evt, reason))
        self.by_id[evt["event_id"]] = {"status": "quarantined", "reason": reason}
        dev["last_seq"] = evt["device_seq"]               # slot consumed so the stream never stalls
        dev["last_hash"] = event_hash(evt)
        return {"event_id": evt["event_id"], "result": "quarantined", "reason": reason}

    def push(self, batch, device_now=None):
        results, ack = [], None
        for evt in batch:
            dev = self.devices.get(evt.get("device_id"))
            if dev is None:
                results.append({"event_id": evt.get("event_id"), "result": "rejected_unknown_device"})
                break
            known = self.by_id.get(evt["event_id"])
            if known:
                results.append({"event_id": evt["event_id"], "result": "duplicate", "stored_status": known["status"]})
                continue
            expected = dev["last_seq"] + 1
            if evt["device_seq"] > expected:
                results.append({"event_id": evt["event_id"], "result": "gap", "expected_seq": expected})
                break                                     # later events in this batch are not processed
            if evt["device_seq"] < expected:
                results.append(self._quarantine(dev, evt, "broken_hash_chain"))
                dev["last_seq"] = expected - 1            # do not move the pointer backwards
                continue
            problems = validate_event(evt)
            if problems:
                reason = "unknown_schema_version" if "unsupported schema_version" in problems[0] or "unknown event type" in problems[0] else "invalid_payload"
                results.append(self._quarantine(dev, evt, reason))
                continue
            if evt["prev_hash"] != dev["last_hash"]:
                results.append(self._quarantine(dev, evt, "broken_hash_chain"))
                continue
            flags = []
            if dev["revoked_at"] is not None:
                if evt["occurred_at_device"] <= dev["revoked_at"]:
                    flags.append("after_revocation")
                else:
                    results.append(self._quarantine(dev, evt, "after_revocation"))
                    continue
            key = self.ENTITY_KEY.get(evt["type"])
            if key and evt["type"] != "ReceiptIssued":
                ent = (evt["type"], evt["payload"][key])
                if ent in self.entities and self.entities[ent] != evt["event_id"]:
                    results.append(self._quarantine(dev, evt, "duplicate_entity_id"))
                    continue
                self.entities[ent] = evt["event_id"]
            offset_ms = None
            if device_now is not None:
                offset_ms = int((datetime.now(timezone.utc) - datetime.fromisoformat(device_now.replace("Z", "+00:00"))).total_seconds() * 1000)
                if abs(offset_ms) > self.SKEW_MS:
                    flags.append("clock_skew")
            if evt["type"] == "PaymentStatusChanged":
                flags.append("manual_confirmation")
            self.cursor += 1
            stored = dict(evt, server_cursor=self.cursor, received_at_server=ts(), flags=flags)
            if offset_ms is not None:
                stored["clock_offset_ms"] = offset_ms
            self.store.append(stored)
            self.by_id[evt["event_id"]] = {"status": "accepted", "cursor": self.cursor}
            dev["last_seq"], dev["last_hash"] = evt["device_seq"], event_hash(evt)
            results.append({"event_id": evt["event_id"], "result": "accepted", "flags": flags})
        ack = max((self.devices[d]["last_seq"] for d in {e.get("device_id") for e in batch} if d in self.devices), default=0)
        return {"results": results, "ack_seq": ack}

    def snapshot(self):
        """State that must be identical after any number of replays."""
        return (len(self.store), [e["event_id"] for e in self.store], len(self.quarantine),
                {d: v["last_seq"] for d, v in self.devices.items()})


def stock_projection(events):
    """Order-independent stock projection from deltas. Returns {product_id: milli}."""
    stock, sale_lines = {}, {}
    def add(pid, d): stock[pid] = stock.get(pid, 0) + d
    for e in events:
        t, p = e["type"], e["payload"]
        if t == "SaleRecorded":
            sale_lines[p["sale_id"]] = p["lines"]
    for e in events:
        t, p = e["type"], e["payload"]
        if t == "SaleRecorded":
            for l in p["lines"]: add(l["product_id"], -l["quantity_milli"])
        elif t == "SaleVoided":
            for l in sale_lines.get(p["sale_id"], []): add(l["product_id"], l["quantity_milli"])
        elif t == "ReturnRecorded":
            for l in p["lines"]:
                if l["restock"]: add(l["product_id"], l["quantity_milli"])
        elif t == "StockReceived":
            for l in p["lines"]: add(l["product_id"], l["quantity_milli"])
        elif t == "StockAdjusted":
            add(p["product_id"], p["delta_milli"])
        elif t == "StockCounted":
            add(p["product_id"], p["counted_milli"] - p["device_view_milli"])
    return stock


# ---------------------------------------------------------------- test harness
PASS, FAIL = [], []

def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name if cond else f"{name} {detail}")

def expect_invalid(name, evt, needle=None, stored=False):
    errs = validate_event(evt, stored=stored)
    ok = bool(errs) and (needle is None or any(needle in e for e in errs))
    check(name, ok, f"-> errors: {errs}")


def contract_checks():
    ev = REGISTRY["events"]
    # registry
    for name, e in ev.items():
        check(f"registry:{name}:origins", set(e["origins"]) <= {"device", "server"} and e["origins"])
        check(f"registry:{name}:version", isinstance(e["schema_version"], int))
    def walk_refs(node):
        if isinstance(node, dict):
            if "$ref" in node:
                try: resolve(node["$ref"], REGISTRY); return []
                except KeyError: return [node["$ref"]]
            return [r for v in node.values() for r in walk_refs(v)]
        if isinstance(node, list):
            return [r for v in node for r in walk_refs(v)]
        return []
    check("registry:all $refs resolve", not walk_refs(REGISTRY["events"]), str(walk_refs(REGISTRY["events"])))
    # permissions
    roles = PERMS["roles"]; ids = [p["id"] for p in PERMS["permissions"]]
    check("permissions:unique ids", len(ids) == len(set(ids)))
    by_role = {r: {p["id"] for p in PERMS["permissions"] if r in p["roles"]} for r in roles}
    check("permissions:cashier ⊆ manager", by_role["cashier"] <= by_role["manager"])
    check("permissions:manager ⊆ owner", by_role["manager"] <= by_role["owner"])
    check("permissions:owner has all", by_role["owner"] == set(ids))
    check("permissions:web roles valid", set(PERMS["web_access_v1_roles"]) <= set(roles))
    perm = {p["id"]: p for p in PERMS["permissions"]}
    for p in PERMS["permissions"]:
        check(f"permissions:{p['id']}:roles valid", set(p["roles"]) <= set(roles))
        check(f"permissions:{p['id']}:channels valid", set(p["channels"]) <= {"mobile", "web"})
    # register
    names = [c["name"] for c in REGISTER["commands"]]
    check("register:unique names", len(names) == len(set(names)))
    emitted_device = set()
    sync_states = {"recorded", "pending_sync", "accepted", "reconciled"} | set(STATES["sale"]["states"]) | set(PAYMENT_STATES) | set(STATES["receipt"]["states"])
    for c in REGISTER["commands"]:
        n, cls = c["name"], c["class"]
        check(f"register:{n}:class valid", cls in ("A", "B", "C"))
        for et in c["emits"]:
            check(f"register:{n}:emits {et} exists", et in ev)
            if et in ev:
                if cls == "A": check(f"register:{n}:{et} origin allows device", "device" in ev[et]["origins"])
                else: check(f"register:{n}:{et} has an origin", bool(ev[et]["origins"]))
                if (c.get("v1") or c.get("v2")) and "device" in ev[et]["origins"]: emitted_device.add(et)
        pid = c["permission"]
        if pid is None:
            check(f"register:{n}:null permission is declared", c.get("local_only") or c.get("pre_auth") or c.get("any_authenticated"))
        else:
            check(f"register:{n}:permission exists", pid in perm)
            if pid in perm:
                check(f"register:{n}:channels ⊆ permission channels", set(c["channels"]) <= set(perm[pid]["channels"]),
                      f"{c['channels']} vs {perm[pid]['channels']}")
        for x in c.get("extra_permissions", []):
            check(f"register:{n}:extra permission exists", x["permission"] in perm)
        if cls == "A":
            check(f"register:{n}:A never rejected by cloud", c["cloud_may_reject"] is False)
            check(f"register:{n}:A works offline", c["offline"]["allowed"] is True)
            check(f"register:{n}:A ui_states known", set(c["ui_states"]) <= sync_states, str(c["ui_states"]))
        if cls == "B":
            check(f"register:{n}:B offline + may reject", c["offline"]["allowed"] is True and c["cloud_may_reject"] is True)
        if cls == "C":
            check(f"register:{n}:C refuses or pends offline", c["offline"]["allowed"] is False and "behavior" in c["offline"])
        check(f"register:{n}:has local rejections", len(c["local_rejections"]) >= 1)
    # orphan device events
    sys_gen = {"PaymentStatusChanged"}  # also emitted by provider callbacks (server side)
    for name, e in ev.items():
        if "device" in e["origins"] and name not in sys_gen:
            check(f"coverage:{name} has an issuing command", name in emitted_device)
    # version 2 money rule: every payload that carries an amount carries its currency, and v1 stays readable
    def carries_money(node):
        if isinstance(node, dict):
            if node.get("$ref") in ("#/$defs/money", "#/$defs/money_signed"): return True
            return any(carries_money(v) for v in node.values())
        return isinstance(node, list) and any(carries_money(v) for v in node)
    for name, e in ev.items():
        props = e["payload"]["properties"]
        if carries_money(props):
            optional_money = name in ("StockReceived", "ProductUpdated")   # money optional there; domain_errors demands the currency with it
            check(f"money:{name} carries its currency", "currency" in props and (optional_money or "currency" in e["payload"]["required"]))
    check("money:no rwf definition left in version 2", "rwf" not in REGISTRY["$defs"])
    check("money:currency enum == currency list", set(REGISTRY["$defs"]["currency"]["enum"]) == set(CURRENCIES))
    for name in REGISTRY_V1["events"]:
        check(f"upcast:{name} still registered in version 2", name in ev)
    for part in ("42 I", "44 E", "44 G", "44 I N1", "44 I N8", "44 J", "45 A"):
        check(f"registry:blueprint part {part} registered", any(e.get("blueprint", "").startswith(part) for e in ev.values()))
    # state machines vs registry
    pay_enum = set(REGISTRY["$defs"]["payment_status"]["enum"])
    check("states:payment enum == state machine", pay_enum == set(PAYMENT_STATES))
    rec_status = set(ev["PaymentRecorded"]["payload"]["properties"]["status"]["enum"])
    check("states:PaymentRecorded statuses ⊆ initial", rec_status <= set(STATES["payment"]["initial"]))
    for t in STATES["payment"]["transitions"]:
        check(f"states:transition {t['from']}->{t['to']} not from terminal", not PAYMENT_STATES[t["from"]]["terminal"])
    only_provider = [t["to"] for t in STATES["payment"]["transitions"] if "provider_callback" in t["allowed_sources"] and t["to"] == "confirmed"]
    check("states:'confirmed' reachable only via provider_callback",
          all(t["allowed_sources"] == ["provider_callback"] for t in STATES["payment"]["transitions"] if t["to"] == "confirmed"))
    val_enum = set(ev["ReceiptIssued"]["payload"]["properties"]["validity"]["enum"])
    check("states:receipt enum == state machine", val_enum == set(STATES["receipt"]["states"]))


def event_checks():
    pid = uuid7()
    d = Device()
    ok_sale = d.emit("SaleRecorded", sale_payload(pid))
    check("event:valid sale", validate_event(ok_sale) == [], str(validate_event(ok_sale)))
    # unicode name (Kinyarwanda / French accents) round-trips through canonical bytes
    p = sale_payload(pid); p["lines"][0]["product_name"] = "Café – ikawa – قهوة – कॉफ़ी"
    e = Device().emit("SaleRecorded", p)
    check("event:unicode name ok", validate_event(e) == [])
    check("hash:canonical bytes are utf-8 stable", signing_bytes(e) == signing_bytes(json.loads(json.dumps(e, ensure_ascii=False))))

    bad = json.loads(json.dumps(ok_sale)); bad["payload"]["lines"][0]["unit_price"] = 1500.5
    expect_invalid("event:float money rejected", bad, "floating-point")
    bad = json.loads(json.dumps(ok_sale)); bad["extra"] = 1
    expect_invalid("event:extra envelope field rejected", bad, "unexpected field")
    bad = json.loads(json.dumps(ok_sale)); bad["event_id"] = uuid4()
    expect_invalid("event:non-uuid7 event_id rejected", bad, "pattern")
    bad = json.loads(json.dumps(ok_sale)); bad["type"] = "TeleportInventory"
    expect_invalid("event:unknown type rejected", bad, "unknown event type")
    bad = json.loads(json.dumps(ok_sale)); bad["server_cursor"] = 5
    expect_invalid("event:device may not send server stamp", bad, "unexpected field")
    bad = json.loads(json.dumps(ok_sale)); bad["schema_version"] = 3
    expect_invalid("event:future schema_version rejected", bad, "unsupported schema_version")
    # version 1 (integer RWF, no currency on payments) is still readable: as it is, and upcast to version 2
    sys.path.insert(0, os.path.dirname(ROOT)); from contract.upcast import upcast
    v1_sale = json.loads(json.dumps(ok_sale)); v1_sale["schema_version"] = 1; v1_sale["payload"]["currency"] = "RWF"
    check("v1:sale still valid as version 1", validate_event(v1_sale) == [], str(validate_event(v1_sale)))
    v1_pay = Device().emit("PaymentRecorded", {"payment_id": uuid7(), "sale_id": ok_sale["payload"]["sale_id"], "method": "cash", "amount": 1500, "status": "cash_received"})
    v1_pay["schema_version"] = 1
    check("v1:payment without currency valid as version 1", validate_event(v1_pay) == [], str(validate_event(v1_pay)))
    up = upcast(v1_pay)
    check("upcast:v1 payment reads as version 2 with RWF", up["schema_version"] == 2 and up["payload"]["currency"] == "RWF" and validate_event(up) == [], str(validate_event(up)))
    check("upcast:amount never rescaled", up["payload"]["amount"] == v1_pay["payload"]["amount"] and v1_pay["schema_version"] == 1)
    no_cur = Device().emit("PaymentRecorded", {"payment_id": uuid7(), "sale_id": ok_sale["payload"]["sale_id"], "method": "cash", "amount": 1500, "status": "cash_received"})
    expect_invalid("v2:payment without currency rejected", no_cur, "missing required 'currency'")
    bad_cur = json.loads(json.dumps(ok_sale)); bad_cur["payload"]["currency"] = "XXX"
    expect_invalid("v2:unknown currency rejected", bad_cur, "not in enum")
    # the new event names: an agent request is a device fact, its answer is cloud only
    agent = Device().emit("AgentRequestCreated", {"request_id": uuid7(), "partner_id": uuid4(), "service": "cash_withdrawal", "amount": 20000, "fee": 200, "currency": SAMPLE_CURRENCY})
    check("v2:agent request from a device ok", validate_event(agent) == [], str(validate_event(agent)))
    confirm_dev = Device().emit("AgentRequestConfirmed", {"request_id": uuid7(), "partner_reference": "PRT-1", "amount": 20000, "fee": 200, "commission": 50, "currency": SAMPLE_CURRENCY})
    expect_invalid("v2:device cannot confirm an agent request", confirm_dev, "may not originate")
    bad = json.loads(json.dumps(ok_sale)); bad["payload"]["total"] += 1
    expect_invalid("event:sale arithmetic enforced", bad, "total mismatch")
    bad = json.loads(json.dumps(ok_sale)); bad["payload"]["lines"][0]["line_total"] += 1
    expect_invalid("event:line rounding enforced", bad, "line_total mismatch")
    stored = dict(ok_sale, server_cursor=1, received_at_server=ts(), flags=["negative_stock"])
    check("event:stored form accepted", validate_event(stored, stored=True) == [])
    # payments
    sale_id = ok_sale["payload"]["sale_id"]
    good_pay = Device().emit("PaymentRecorded", {"payment_id": uuid7(), "sale_id": sale_id, "method": "mobile_money", "amount": 1500, "status": "pending_confirmation", "currency": SAMPLE_CURRENCY})
    check("payment:mobile money pending ok", validate_event(good_pay) == [])
    cash_bad = Device().emit("PaymentRecorded", {"payment_id": uuid7(), "sale_id": sale_id, "method": "cash", "amount": 1500, "status": "pending_confirmation", "currency": SAMPLE_CURRENCY})
    expect_invalid("payment:cash must be cash_received", cash_bad, "requires status")
    mm_bad = Device().emit("PaymentRecorded", {"payment_id": uuid7(), "sale_id": sale_id, "method": "mobile_money", "amount": 1500, "status": "confirmed", "currency": SAMPLE_CURRENCY})
    expect_invalid("payment:device cannot record confirmed", mm_bad)
    conf_dev = Device().emit("PaymentStatusChanged", {"payment_id": uuid7(), "from_status": "pending_confirmation", "to_status": "confirmed", "source": "owner_manual"})
    expect_invalid("payment:device cannot emit 'confirmed'", conf_dev)
    man_ok = Device().emit("PaymentStatusChanged", {"payment_id": uuid7(), "from_status": "pending_confirmation", "to_status": "manually_confirmed", "source": "owner_manual"})
    check("payment:device manual confirmation ok", validate_event(man_ok) == [], str(validate_event(man_ok)))
    srv_ok = {"event_id": uuid7(), "origin": "server", "merchant_id": MERCHANT, "type": "PaymentStatusChanged", "schema_version": 2,
              "created_at_server": ts(), "server_cursor": 9, "payload": {"payment_id": uuid7(), "from_status": "pending_confirmation", "to_status": "confirmed", "source": "provider_callback"},
              "server_signature": fake_sig()}
    check("payment:provider callback confirms", validate_event(srv_ok) == [], str(validate_event(srv_ok)))
    srv_bad = json.loads(json.dumps(srv_ok)); srv_bad["payload"]["source"] = "system"
    expect_invalid("payment:'system' cannot confirm", srv_bad, "illegal payment transition")
    rcpt = Device().emit("ReceiptIssued", {"receipt_id": uuid7(), "sale_id": sale_id, "receipt_number_local": "A1-1", "copy_number": 1, "validity": "valid"})
    expect_invalid("receipt:device may only issue provisional", rcpt)
    prov = Device().emit("ReceiptIssued", {"receipt_id": uuid7(), "sale_id": sale_id, "receipt_number_local": "A1-1", "copy_number": 1, "validity": "provisional"})
    check("receipt:provisional ok", validate_event(prov) == [])
    cost_no_cur = Device().emit("StockReceived", {"stock_receipt_id": uuid7(), "lines": [{"product_id": pid, "quantity_milli": 1000, "unit_cost": 900}]})
    expect_invalid("v2:unit cost without currency rejected", cost_no_cur, "needs a currency")
    adj0 = Device().emit("StockAdjusted", {"adjustment_id": uuid7(), "product_id": pid, "delta_milli": 0, "reason_code": "loss"})
    expect_invalid("stock:zero adjustment rejected", adj0, "non-zero")


def chain_and_ingest_checks():
    pid = uuid7()
    # --- hash chain and gaps
    d = Device()
    evs = [d.emit("StockReceived", {"stock_receipt_id": uuid7(), "lines": [{"product_id": pid, "quantity_milli": 5000}]}) for _ in range(3)]
    check("chain:valid chain verifies", all(evs[i]["prev_hash"] == event_hash(evs[i - 1]) for i in range(1, 3)) and evs[0]["prev_hash"] == "GENESIS")
    tampered = json.loads(json.dumps(evs[1])); tampered["payload"]["lines"][0]["quantity_milli"] = 9000
    check("chain:tamper detected by next event", evs[2]["prev_hash"] != event_hash(tampered))

    # --- T6: replay the same batch five times
    srv = ReferenceIngest(); srv.enroll(d.id)
    r1 = srv.push(evs); snap = srv.snapshot()
    check("ingest:first push accepts all", [r["result"] for r in r1["results"]] == ["accepted"] * 3 and r1["ack_seq"] == 3)
    for _ in range(4): r = srv.push(evs)
    check("ingest:T6 five replays leave state identical", srv.snapshot() == snap)
    check("ingest:replay reports duplicates", all(x["result"] == "duplicate" for x in r["results"]))

    # --- T5: interrupted batch resumes with no gaps or duplicates
    d2 = Device(); s2 = ReferenceIngest(); s2.enroll(d2.id)
    many = [d2.emit("StockReceived", {"stock_receipt_id": uuid7(), "lines": [{"product_id": pid, "quantity_milli": 1000}]}) for _ in range(10)]
    s2.push(many[:4])                       # connection drops after 4
    res = s2.push(many)                     # client resends everything from its last unacked point
    check("ingest:T5 resume after drop", s2.snapshot()[0] == 10 and s2.devices[d2.id]["last_seq"] == 10, str(res["results"][:5]))
    # gap: events 1,2 then jump to 5
    d3 = Device(); s3 = ReferenceIngest(); s3.enroll(d3.id)
    seq = [d3.emit("StockReceived", {"stock_receipt_id": uuid7(), "lines": [{"product_id": pid, "quantity_milli": 1000}]}) for _ in range(5)]
    g = s3.push([seq[0], seq[1], seq[4]])
    check("ingest:gap stops batch and asks for resend", g["results"][-1]["result"] == "gap" and g["ack_seq"] == 2, str(g))

    # --- invalid payload is quarantined, never dropped, never blocks the stream
    d4 = Device(); s4 = ReferenceIngest(); s4.enroll(d4.id)
    good1 = d4.emit("StockReceived", {"stock_receipt_id": uuid7(), "lines": [{"product_id": pid, "quantity_milli": 1000}]})
    poison = d4.emit("StockAdjusted", {"adjustment_id": uuid7(), "product_id": pid, "delta_milli": 0, "reason_code": "loss"})
    good2 = d4.emit("StockReceived", {"stock_receipt_id": uuid7(), "lines": [{"product_id": pid, "quantity_milli": 2000}]})
    out = s4.push([good1, poison, good2])
    check("ingest:poison event quarantined, stream continues",
          [r["result"] for r in out["results"]] == ["accepted", "quarantined", "accepted"] and out["ack_seq"] == 3, str(out))
    check("ingest:quarantine keeps the event", len(s4.quarantine) == 1 and s4.quarantine[0][1] == "invalid_payload")

    # --- unknown schema version quarantined
    d5 = Device(); s5 = ReferenceIngest(); s5.enroll(d5.id)
    fut = d5.emit("StockReceived", {"stock_receipt_id": uuid7(), "lines": [{"product_id": pid, "quantity_milli": 1000}]}); 
    # re-sign chain after changing version: rebuild event manually
    fut["schema_version"] = 3
    o = s5.push([fut])
    check("ingest:future schema quarantined", o["results"][0].get("reason") == "unknown_schema_version", str(o))

    # --- duplicate entity id with a different event_id (a buggy client) is quarantined
    d6 = Device(); s6 = ReferenceIngest(); s6.enroll(d6.id)
    p = sale_payload(pid); a = d6.emit("SaleRecorded", p); b = d6.emit("SaleRecorded", p)
    o = s6.push([a, b])
    check("ingest:duplicate sale_id quarantined", [r["result"] for r in o["results"]] == ["accepted", "quarantined"] and o["results"][1]["reason"] == "duplicate_entity_id", str(o))

    # --- unknown device rejected at the gate
    stranger = Device(); s7 = ReferenceIngest()
    o = s7.push([stranger.emit("StockReceived", {"stock_receipt_id": uuid7(), "lines": [{"product_id": pid, "quantity_milli": 1000}]})])
    check("ingest:unknown device rejected", o["results"][0]["result"] == "rejected_unknown_device")

    # --- revocation: pre-revocation events flagged, post-revocation events quarantined
    d8 = Device(); s8 = ReferenceIngest(); s8.enroll(d8.id)
    t0 = datetime.now(timezone.utc)
    e_before = d8.emit("StockReceived", {"stock_receipt_id": uuid7(), "lines": [{"product_id": pid, "quantity_milli": 1000}]}, at=t0 - timedelta(hours=2))
    e_after = d8.emit("StockReceived", {"stock_receipt_id": uuid7(), "lines": [{"product_id": pid, "quantity_milli": 1000}]}, at=t0 + timedelta(hours=1))
    s8.revoke(d8.id, ts(t0 - timedelta(hours=1)))
    o = s8.push([e_before, e_after])
    check("ingest:revoked device pre-revocation event flagged", o["results"][0]["result"] == "accepted" and "after_revocation" in o["results"][0]["flags"], str(o))
    check("ingest:revoked device later event quarantined", o["results"][1].get("reason") == "after_revocation", str(o))

    # --- T8: wrong device clock does not affect order; skew is flagged
    d9 = Device(); s9 = ReferenceIngest(); s9.enroll(d9.id)
    wrong = datetime.now(timezone.utc) - timedelta(days=3)
    c1 = d9.emit("StockReceived", {"stock_receipt_id": uuid7(), "lines": [{"product_id": pid, "quantity_milli": 1000}]}, at=wrong)
    c2 = d9.emit("StockReceived", {"stock_receipt_id": uuid7(), "lines": [{"product_id": pid, "quantity_milli": 1000}]}, at=wrong - timedelta(days=1))  # clock went backwards
    o = s9.push([c1, c2], device_now=ts(wrong))
    cursors = [e["server_cursor"] for e in s9.store]
    check("clock:T8 order by device_seq/cursor despite backwards clock", cursors == [1, 2] and [e["device_seq"] for e in s9.store] == [1, 2])
    check("clock:T8 skew flagged", all("clock_skew" in e["flags"] for e in s9.store))

    # --- T7: two devices sell the last item; both sales kept, stock negative, order-independent
    dA, dB = Device(), Device()
    sv = ReferenceIngest(); sv.enroll(dA.id); sv.enroll(dB.id)
    prod = uuid7()
    seed = Device(); sv.enroll(seed.id)
    sv.push([seed.emit("StockReceived", {"stock_receipt_id": uuid7(), "lines": [{"product_id": prod, "quantity_milli": 1000}]})])
    sa = dA.emit("SaleRecorded", sale_payload(prod, 1000)); sb = dB.emit("SaleRecorded", sale_payload(prod, 1000))
    sv.push([sa]); sv.push([sb])
    proj = stock_projection(sv.store)
    check("stock:T7 both sales kept", sum(1 for e in sv.store if e["type"] == "SaleRecorded") == 2)
    check("stock:T7 projection negative (flaggable)", proj[prod] == -1000, str(proj))
    perms_ok = all(stock_projection(list(p))[prod] == -1000 for p in itertools.permutations(sv.store))
    check("stock:projection independent of event order", perms_ok)
    # count is a delta against the device's own view, so it cannot erase another device's sale
    cnt = dA.emit("StockCounted", {"count_id": uuid7(), "product_id": prod, "counted_milli": 0, "device_view_milli": 0})
    sv.push([cnt])
    check("stock:count relative to device view keeps concurrent sale", stock_projection(sv.store)[prod] == -1000)

    # --- server enforces the hash chain: a device stream edited in transit is caught at the next event
    d11 = Device(); s11 = ReferenceIngest(); s11.enroll(d11.id)
    h1 = d11.emit("StockReceived", {"stock_receipt_id": uuid7(), "lines": [{"product_id": pid, "quantity_milli": 1000}]})
    h2 = d11.emit("StockReceived", {"stock_receipt_id": uuid7(), "lines": [{"product_id": pid, "quantity_milli": 1000}]})
    h3 = d11.emit("StockReceived", {"stock_receipt_id": uuid7(), "lines": [{"product_id": pid, "quantity_milli": 1000}]})
    forged = json.loads(json.dumps(h2)); forged["payload"]["lines"][0]["quantity_milli"] = 999000   # edited after signing
    o = s11.push([h1, forged, h3])
    check("ingest:edited event breaks chain at the next event",
          [r["result"] for r in o["results"]] == ["accepted", "accepted", "quarantined"] and o["results"][2]["reason"] == "broken_hash_chain", str(o))
    check("ingest:chain break is surfaced, never silent", len(s11.quarantine) == 1)

    # --- T12-lite: unknown future field in an old payload fails closed (quarantine), not silently dropped
    d10 = Device(); s10 = ReferenceIngest(); s10.enroll(d10.id)
    extra = d10.emit("StockReceived", {"stock_receipt_id": uuid7(), "lines": [{"product_id": pid, "quantity_milli": 1000}], "surprise": 1})
    o = s10.push([extra])
    check("ingest:unexpected payload field fails closed", o["results"][0]["result"] == "quarantined")


def main():
    contract_checks(); event_checks(); chain_and_ingest_checks()
    print(f"passed: {len(PASS)}   failed: {len(FAIL)}")
    for f in FAIL:
        print("  FAIL", f)
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
