"""Approved improvements (design proposal, all 8 decisions accepted). State is saved in the platform database.

Honest limits:
 * Providers, CDN and relay transport are SANDBOX interfaces. Nothing here moves real money.
 * Sealing uses the `cryptography` library (services/sealing.py); it still needs a security review.
 * Prices are the agreed placeholders; check them before publishing.
Not built on purpose: LynkShield (replaced by OfflineRisk), and no LOSHLD-, LOSNAP-, LOONE-, LOSTRM-, LOEDGE-, LOUSAGE-, LOPORT- ids.
"""
import hashlib, json, sqlite3, time, uuid
from decimal import Decimal as D
from core.money import to_minor
from core.regions import country

def _h(x): return hashlib.sha256(x if isinstance(x, bytes) else json.dumps(x, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
def _cur(p, m): return p.c.profile(m)["currency"]
def _usd(p, m, usd):
    cur = _cur(p, m); return cur, p.c.fx.convert(to_minor(D(str(usd)), "USD"), "USD", cur)


class Rec(dict):
    """A dict that saves itself on every change."""
    def __init__(s, table, key, data): super().__init__(data); s._t, s._k = table, key
    def __setitem__(s, k, v): super().__setitem__(k, v); s._t.put(s._k, dict(s))
    def update(s, *a, **k): super().update(*a, **k); s._t.put(s._k, dict(s))
    def setdefault(s, k, v=None):
        if k not in s: s[k] = v
        return s[k]
class Table:
    def __init__(s, db, name):
        s.db, s.name = db, "imp_" + name
        s.db.execute(f"create table if not exists {s.name}(k text primary key, v text not null)"); s.db.commit()
    def put(s, k, v): s.db.execute(f"insert or replace into {s.name} values(?,?)", (k, json.dumps(v, sort_keys=True))); s.db.commit()
    def get(s, k, default=None):
        r = s.db.execute(f"select v from {s.name} where k=?", (k,)).fetchone(); return Rec(s, k, json.loads(r[0])) if r else default
    def __getitem__(s, k):
        r = s.get(k)
        if r is None: raise KeyError(k)
        return r
    def __contains__(s, k): return s.db.execute(f"select 1 from {s.name} where k=?", (k,)).fetchone() is not None
    def items(s): return [(k, Rec(s, k, json.loads(v))) for k, v in s.db.execute(f"select k,v from {s.name} order by rowid")]
    def pop(s, k, default=None):
        v = s.get(k, default); s.db.execute(f"delete from {s.name} where k=?", (k,)); s.db.commit(); return v


class MeshRelay:
    """LynkMesh: a nearby device carries sealed batches to the cloud. It carries data, never money. No fee, no payment to relays.
    The relay cannot read a batch. Anything that parses as plain JSON is refused unless a test allows plaintext."""
    def __init__(s, ccbox, limit=60, window=60, now=time.time, allow_plaintext=False, db=None):
        s.cc, s.limit, s.window, s.now, s.allow_plaintext = ccbox, limit, window, now, allow_plaintext
        s.items, s.hits = Table(db or sqlite3.connect(":memory:"), "mesh"), {}
    @staticmethod
    def _looks_plain(body):
        try: json.loads(body); return True
        except Exception: return False
    def submit(s, relay_id, device_id, batch_hash, body, sealed=True):
        if (not sealed or s._looks_plain(body)) and not s.allow_plaintext:
            return {"state": "refused", "reason": "batch must be sealed end to end"}
        t = s.now(); h = [x for x in s.hits.get(relay_id, []) if t - x < s.window]
        if len(h) >= s.limit: return {"state": "refused", "reason": "rate_limited"}
        s.hits[relay_id] = h + [t]
        if batch_hash in s.items: return {"state": s.items[batch_hash]["state"], "duplicate": True}
        s.items.put(batch_hash, {"device": device_id, "body": body.hex(), "state": "queued", "relay": relay_id})
        return {"state": "queued"}
    def forward(s, opener):
        out = []
        for bh, it in s.items.items():
            if it["state"] != "queued": continue
            body = bytes.fromhex(it["body"])
            if _h(body) != bh: it["state"] = "tampered"; out.append((bh, "tampered")); continue
            try: batch = opener(body)
            except Exception: it["state"] = "unreadable"; out.append((bh, "unreadable")); continue
            res = s.cc.push(batch)["results"]
            it["state"] = "cloud_accepted" if res and all(r["result"] in ("accepted", "duplicate") for r in res) else "cloud_refused"; out.append((bh, it["state"]))
        return out
    def ui_state(s, batch_hash):
        """Uses the shared state vocabulary (queued, sent, accepted, confirmed, failed). A relay can never produce 'confirmed'."""
        st = s.items.get(batch_hash, {}).get("state") if batch_hash in s.items else None
        return {"queued": "sent", "cloud_accepted": "accepted", "tampered": "failed", "unreadable": "failed", "cloud_refused": "failed"}.get(st)


class OfflineRisk:
    """Replaces LynkShield. A merchant-set cap on unconfirmed non-cash value. Nothing is guaranteed; sales stay pending until confirmed.
    It stops accepting more non-cash payments on a device at the cap; the sale itself is never blocked, and cash always works."""
    CEILING_USD, DEFAULT_USD = 500, 50
    def __init__(s, p): s.p, s.caps, s.open = p, Table(p.c.store.db, "risk_caps"), Table(p.c.store.db, "risk_open")
    def set_cap(s, m, usd):
        if usd < 0 or usd > s.CEILING_USD: raise ValueError(f"cap must be between 0 and {s.CEILING_USD} USD equivalent")
        s.caps.put(m, {"usd": usd})
    def cap_minor(s, m):
        c = s.caps.get(m); usd = c["usd"] if c else s.DEFAULT_USD
        return s.p.c.fx.convert(to_minor(D(usd), "USD"), "USD", _cur(s.p, m))
    def exposure(s, m, device): return sum((s.open.get(f"{m}|{device}") or {}).values())
    def authorise(s, m, device, sale_id, minor, method):
        base = {"status": "pending_confirmation", "guaranteed": False}
        if method == "cash": return {**base, "allowed": True, "counted": False}
        cur, key = s.exposure(m, device), f"{m}|{device}"
        if cur + minor > s.cap_minor(m): return {**base, "allowed": False, "reason": "offline_limit_reached", "exposure_minor": cur}
        d = dict(s.open.get(key) or {}); d[sale_id] = minor; s.open.put(key, d)
        return {**base, "allowed": True, "counted": True, "exposure_minor": cur + minor}
    def confirm(s, m, device, sale_id):
        key = f"{m}|{device}"; d = dict(s.open.get(key) or {}); d.pop(sale_id, None); s.open.put(key, d)


class GuardedDevice:
    """Puts the offline risk limit in front of a LynkDVBox payment. At the cap a non-cash payment is declined; the sale stays open for cash or another method."""
    def __init__(s, dv, risk, merchant): s.dv, s.risk, s.m = dv, risk, merchant
    def record_payment(s, sale_id, method, amount_minor):
        a = s.risk.authorise(s.m, str(s.dv.d), sale_id, amount_minor, method)
        if not a["allowed"]: return "offline_limit_reached"
        return s.dv.record_payment(sale_id, method, amount_minor)
    def __getattr__(s, n): return getattr(s.dv, n)


class ProofPack:
    """LynkProof: an evidence pack handed to the merchant's provider. LynkOmni never decides a dispute."""
    SENSITIVE = ("biometric", "signature")
    def __init__(s, p): s.p, s.packs = p, Table(p.c.store.db, "proof")
    def used(s, m, month): return sum(1 for _, v in s.packs.items() if v["merchant"] == m and v.get("month") == month)
    def create(s, m, payment_ref, evidence, consent_id=None, month=None):
        """Packs per month and the success fee depend on the merchant's LynkMPay tier (billing.FEATURES)."""
        if any(k in evidence for k in s.SENSITIVE) and not consent_id: raise PermissionError("biometric or signature evidence needs a recorded consent")
        ent, month = s.p.billing.entitlement(m, "lynkmpay"), month or time.strftime("%Y-%m")
        lim = ent.get("proof_packs_per_month")
        if lim is not None and s.used(m, month) >= lim: raise PermissionError("evidence pack limit for this plan reached this month")
        pid = s.p.ids.assign("PRF", uuid.uuid4().hex); h = _h({"p": payment_ref, "e": evidence})
        s.packs.put(pid, {"merchant": m, "payment": payment_ref, "hash": h, "state": "created", "fee_charged": False, "consent": consent_id, "month": month, "fee_cents": ent["proof_fee_cents"]})
        return {"id": pid, "hash": h}
    def hand_over(s, pid, provider): s.packs[pid].update(state="handed_to_provider", provider=provider); return "handed_to_provider"
    def provider_outcome(s, pid, outcome):
        pk = s.packs[pid]
        if pk["state"] == outcome: return outcome
        if pk["state"] != "handed_to_provider": raise ValueError("the pack was not handed to a provider")
        pk["state"] = outcome
        if outcome == "won" and not pk["fee_charged"]:
            cur, amt = _usd(s.p, pk["merchant"], D(pk["fee_cents"]) / 100)
            s.p.control.record_revenue(pk["merchant"], "proof:success_fee", amt, cur, s.p.c.profile(pk["merchant"])["country"]); pk["fee_charged"] = True
        return outcome


def merkle_root(leaves):
    lv = [bytes.fromhex(_h(x)) for x in leaves] or [b"\0" * 32]
    while len(lv) > 1:
        if len(lv) % 2: lv.append(lv[-1])
        lv = [hashlib.sha256(lv[i] + lv[i + 1]).digest() for i in range(0, len(lv), 2)]
    return lv[0].hex()
def merkle_proof(leaves, index):
    lv, idx, proof = [bytes.fromhex(_h(x)) for x in leaves], index, []
    while len(lv) > 1:
        if len(lv) % 2: lv.append(lv[-1])
        proof.append((lv[idx ^ 1].hex(), idx % 2)); lv = [hashlib.sha256(lv[i] + lv[i + 1]).digest() for i in range(0, len(lv), 2)]; idx //= 2
    return proof
def merkle_verify(leaf, proof, root):
    cur = bytes.fromhex(_h(leaf))
    for sib, right in proof: cur = hashlib.sha256((bytes.fromhex(sib) + cur) if right else (cur + bytes.fromhex(sib))).digest()
    return cur.hex() == root


class AuditExport:
    """LynkAudit: tamper-evident export. It is not a tax authority device and is not validated by any tax authority."""
    def __init__(s, p): s.p, s.exports = p, Table(p.c.store.db, "audit")
    def export(s, m):
        leaves = [{"seq": e["seq"], "id": e["id"], "type": e["type"], "ts": e["ts"], "payload": e["payload"]} for e in s.p.c.store.since(m)]
        aid = s.p.ids.assign("AUD", uuid.uuid4().hex); fee_cents = s.p.billing.entitlement(m, "lynkledger")["audit_fee_cents"]; free = fee_cents == 0
        if not free:
            cur, amt = _usd(s.p, m, D(fee_cents) / 100); s.p.control.record_revenue(m, "audit:export", amt, cur, s.p.c.profile(m)["country"])
        root = merkle_root(leaves); s.exports.put(aid, {"merchant": m, "root": root, "count": len(leaves), "leaves": leaves})
        return {"id": aid, "root": root, "count": len(leaves), "fee_charged": not free, "tax_authority_validated": False}
    def proof_for(s, aid, index):
        x = s.exports[aid]; return {"leaf": x["leaves"][index], "proof": merkle_proof(x["leaves"], index), "root": x["root"]}


class Split:
    """LynkSplit: instructions executed by a licensed provider. LynkOmni holds no funds. Fee $0.10 + 0.10% per split."""
    def __init__(s, p): s.p, s.splits = p, Table(p.c.store.db, "split")
    @staticmethod
    def divide(total, legs):
        out, rest = {}, total
        for name, bp in legs.items():
            if name == "merchant": continue
            out[name] = total * bp // 10000; rest -= out[name]
        out["merchant"] = rest; return out
    def create(s, m, payment_ref, total_minor, legs_bp, provider_confirmed, tax_leg=False):
        if not provider_confirmed: raise ValueError("a split needs a payment the provider has confirmed")
        if "tax_authority" in legs_bp and not (tax_leg and country(s.p.c.profile(m)["country"]).get("flags", {}).get("tax_split", False)):
            raise PermissionError("a tax-authority leg is only allowed where the law and a partner allow it")
        if sum(v for k, v in legs_bp.items() if k != "merchant") > 10000: raise ValueError("legs exceed 100%")
        ent = s.p.billing.entitlement(m, "lynkmpay"); legs = len([k for k in legs_bp if k != "merchant"]); mx = ent.get("split_max_legs")
        if mx is not None and legs > mx: raise PermissionError(f"this plan allows {mx} split legs; upgrade LynkMPay")
        parts = s.divide(total_minor, legs_bp); assert sum(parts.values()) == total_minor
        sid = s.p.ids.assign("SPLT", uuid.uuid4().hex); cur = _cur(s.p, m); fee = (s.p.c.fx.convert(10, "USD", cur) + total_minor // 1000) * (100 - ent.get("split_discount_pct", 0)) // 100
        s.p.control.record_revenue(m, "split:fee", fee, cur, s.p.c.profile(m)["country"])
        s.splits.put(sid, {"merchant": m, "payment": payment_ref, "parts": parts, "held_by_lynkomni": 0, "executed_by": "provider"})
        return {"id": sid, "parts": parts, "held_by_lynkomni": 0, "fee_minor": fee}


class Seats:
    """Extra seat add-on: $2 per month beyond the users or seats the tier includes. Charged once per account, family and month."""
    PRICE_USD = 2
    KEYS = {"lynkpos": "users", "lynkchat": "seats"}
    def __init__(s, p): s.p, s.done = p, Table(p.c.store.db, "seat_charges")
    def included(s, m, family): return s.p.billing.entitlement(m, family).get(s.KEYS[family])
    def extra_cost(s, m, family, used):
        inc = s.included(m, family)
        return 0 if inc is None or used <= inc else _usd(s.p, m, s.PRICE_USD * (used - inc))[1]
    def charge(s, m, family, used, month):
        key = f"{m}|{family}|{month}"; amt = s.extra_cost(m, family, used)
        if not amt or key in s.done: return 0
        s.p.control.record_revenue(m, "seats:extra", amt, _cur(s.p, m), s.p.c.profile(m)["country"]); s.done.put(key, {"amount_minor": amt}); return amt


class Meter:
    """Internal metering for LynkDev. No public id. Idempotent. Overage $0.0005 a call beyond the daily allowance on paid tiers."""
    OVER_USD = D("0.0005")
    def __init__(s, p): s.p, s.seen, s.day, s.billed = p, Table(p.c.store.db, "meter_seen"), Table(p.c.store.db, "meter_day"), Table(p.c.store.db, "meter_billed")
    def record(s, m, key, day, n=1):
        if key in s.seen: return False
        s.seen.put(key, {}); k = f"{m}|{day}"; s.day.put(k, {"n": (s.day.get(k) or {"n": 0})["n"] + n}); return True
    def calls(s, m, day): return (s.day.get(f"{m}|{day}") or {"n": 0})["n"]
    def overage_calls(s, m, day):
        al = s.p.billing.entitlement(m, "lynkdev").get("api_calls_per_day"); return 0 if al is None else max(0, s.calls(m, day) - al)
    def bill_day(s, m, day):
        n, k = s.overage_calls(m, day), f"{m}|{day}"
        if not n or s.p.billing.tier(m, "lynkdev") == "free" or k in s.billed: return 0
        cur = _cur(s.p, m); amt = s.p.c.fx.convert(max(1, int(n * s.OVER_USD * 100)), "USD", cur)
        s.p.control.record_revenue(m, "meter:api_overage", amt, cur, s.p.c.profile(m)["country"]); s.billed.put(k, {"amount_minor": amt}); return amt


class Edge:
    """CDN behind an interface. Included bandwidth and the per-GB rate depend on the LynkDev tier. A target, not a promise."""
    def __init__(s, p): s.p, s.done = p, Table(p.c.store.db, "edge_charges")
    def overage_minor(s, m, gb):
        ent = s.p.billing.entitlement(m, "lynkdev"); inc = ent.get("bandwidth_gb")
        if inc is None: return 0
        extra = max(0, gb - inc); return _usd(s.p, m, D(extra) * D(ent["bandwidth_cents_per_gb"]) / 100)[1] if extra else 0
    def charge(s, m, gb, month):
        key, amt = f"{m}|{month}", s.overage_minor(m, gb)
        if not amt or key in s.done: return 0
        s.p.control.record_revenue(m, "edge:bandwidth", amt, _cur(s.p, m), s.p.c.profile(m)["country"]); s.done.put(key, {"amount_minor": amt}); return amt


class GuestCheckout:
    """LynkCheckout guest and passkey flow (LynkOne merged). Methods come from the country pack, never from IP or GPS filtering."""
    def __init__(s, p): s.p = p
    def methods(s, country_code, buyer_choice=None, ip_hint=None, location=None, location_consent=False):
        pk = country(country_code); opts = list(pk.get("providers", [])) + list(pk.get("wallets", [])) + list(pk.get("card_networks", []))
        if pk.get("vcard", {}).get("enabled"): opts.append("vcard")
        if buyer_choice: opts = [o for o in opts if o == buyer_choice] or opts
        used = bool(location and location_consent)   # location is read only with consent, and only ever a suggestion
        return {"methods": opts, "surcharge_bp": 0, "ip_used_as_filter": False, "suggested_country": ip_hint, "location_used_as_suggestion": used}
    def passkey_pay(s, passkey_ok, lynkid=None):
        if not passkey_ok: raise PermissionError("passkey check failed")
        if lynkid: return {"lynkid": lynkid, "created": False}
        return {"lynkid": s.p.idp.register_person()["lynkid"], "created": True}


class BusinessSettings:
    """LynkPortal merged. High-risk changes need step-up, a waiting period and a second approver, and are applied only after all three."""
    HIGH = ("tax_id", "payout_target", "role_permissions")
    WAIT = 24 * 3600
    def __init__(s, p, now=time.time): s.p, s.now, s.req, s.values = p, now, Table(p.c.store.db, "settings_req"), Table(p.c.store.db, "settings")
    def get(s, org, field): return (s.values.get(f"{org}|{field}") or {}).get("value")
    def request(s, org, person, field, value, stepup_token):
        high = field in s.HIGH
        if high:
            if not s.p.identity.stepup_valid(stepup_token, person): raise PermissionError("step-up verification needed")
            if s.p.idp.role_of(person, org) != "owner": raise PermissionError("only an owner can request this change")
        elif s.p.idp.role_of(person, org) not in ("owner", "manager"): raise PermissionError("not allowed")
        rid = uuid.uuid4().hex
        s.req.put(rid, {"org": org, "by": person, "field": field, "value": value, "at": s.now(), "approved_by": None, "state": "waiting" if high else "applied"})
        if not high: s.values.put(f"{org}|{field}", {"value": value})
        return rid
    def approve(s, rid, approver, stepup_token):
        r = s.req[rid]
        if approver == r["by"]: raise PermissionError("a second person must approve")
        if s.p.idp.role_of(approver, r["org"]) != "owner": raise PermissionError("only an owner can approve")
        if not s.p.identity.stepup_valid(stepup_token, approver): raise PermissionError("step-up verification needed")
        r["approved_by"] = approver
    def apply(s, rid):
        r = s.req[rid]
        if r["state"] == "applied": return True
        if not r["approved_by"]: raise PermissionError("not approved")
        if s.now() - r["at"] < s.WAIT: raise PermissionError("waiting period not over")
        r["state"] = "applied"; s.values.put(f"{r['org']}|{r['field']}", {"value": r["value"]}); s.p.idp.audit(r["by"], "setting_changed", r["field"]); return True
