"""LynkVCard (LynkOmni Virtual Card) and LynkVCRBox, the risk box. Reference implementation of contract/vcard.v1.json.
LynkOmni never holds customer funds and never sees a card number: a licensed issuer creates, funds and displays cards.
The issuer here is a SANDBOX simulator. Real issuing needs a signed issuer agreement, legal sign-off and the activation checklist."""
import hashlib, hmac, json, os, re, secrets, time, uuid
from core.locale import local_dt
from core.regions import country
from services.control import COMPANY

REG = json.load(open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "contract", "vcard.v1.json")))
CMD = {c["name"]: c for c in REG["commands"]}
PERM = REG["permissions"]
TYPES = {"supplier", "team", "ads", "subscription", "general"}
SINGLE_USE_ONLY = {"free"}            # Free: one single-use supplier card at a time
INTERCHANGE_BPS, FX_NET_BPS = 20, 30  # PLACEHOLDERS: LynkOmni's net share, set by the issuer contract and local interchange rules
def _id(): return uuid.uuid4().hex
def _iso(t): return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t))

class SandboxIssuer:
    """Stands in for the licensed issuer. Idempotent by key. Returns tokens and last four digits only, never a card number."""
    def __init__(s, fail_funding=False): s.done, s.debits, s.fail_funding, s.wallet = {}, 0, fail_funding, {}
    def _once(s, key, fn):
        if key not in s.done: s.done[key] = fn()
        return s.done[key]
    def create(s, key, params): return s._once(key, lambda: {"token": "tok_" + secrets.token_hex(8), "last4": f"{secrets.randbelow(10000):04d}"})
    def fund(s, key, token, amount):
        def go():
            if s.fail_funding: return {"ok": False, "reason": "issuer declined"}
            s.debits += 1; return {"ok": True}
        return s._once(key, go)
    def freeze(s, key, token): return s._once(key, lambda: {"ok": True})
    def close(s, key, token, balance): return s._once(key, lambda: {"ok": True, "refund": balance})
    def rotate(s, key, token): return s._once(key, lambda: {"token": "tok_" + secrets.token_hex(8), "last4": f"{secrets.randbelow(10000):04d}"})
    def display_session(s, token): return {"url": "https://issuer.example/display/" + secrets.token_urlsafe(12), "expires_in": 60}   # hosted by the issuer
    def provision(s, key, token, wallet): return s._once(key, lambda: {"ok": True})
    def revoke_wallet(s, token, wallet): return {"ok": True}
    def physical(s, key, token): return s._once(key, lambda: {"tracking_id": "TRK" + secrets.token_hex(4)})

def verify_issuer_webhook(secret, body, signature):
    """Inbound issuer webhooks are signed. Reject anything unsigned or altered."""
    return hmac.compare_digest(hmac.new(secret.encode(), body, hashlib.sha256).hexdigest(), signature or "")
def developer_webhook_headers(secret, body): return {"X-Lynk-Signature": hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()}
def retry_delays(limit=24 * 3600):
    out, n, total = [], 1, 0
    while total + 2 ** n <= limit: out.append(2 ** n); total += 2 ** n; n += 1
    return out                                  # exponential backoff t = 2^n seconds, stopping inside 24 hours

class VCRBox:
    """LynkOmni Virtual Card Risk Box: velocity, bounds, chargeback tiers. Thresholds are configurable placeholders."""
    def __init__(s, v): s.v = v
    def cfg(s): return REG["risk_defaults"]
    def issuance_ok(s, account, now):
        n = s.v.db.execute("select count(*) from vcards where account=? and created>?", (account, now - 600)).fetchone()[0]
        return n < s.cfg()["issuance_per_10_min"]
    def chargeback_ratio(s):
        d = s.v.db.execute("select count(*) from vtxns where state='disputed'").fetchone()[0]; t = s.v.db.execute("select count(*) from vtxns where state in ('settled','disputed')").fetchone()[0]
        return 0.0 if t == 0 else 100.0 * d / t
    def halted(s):
        return s.chargeback_ratio() >= s.cfg()["chargeback_halt_pct"] and bool(s.v.db.execute("select 1 from vflags where cleared=0 and rule='chargeback_halt'").fetchone())
    def flag(s, account, card, rule):
        case = s.v.p.support.open_case(account, "card_risk"); s.v.db.execute("insert into vflags values(?,?,?,?,0)", (case, card, rule, time.time())); s.v.db.commit()
        s.v.ev(account, "LynkVCRBoxFlagged", {"card": card, "case": case, "rule": rule}); return case
    def clear(s, account, case):
        s.v.db.execute("update vflags set cleared=1 where case_id=?", (case,)); s.v.db.commit(); s.v.ev(account, "LynkVCRBoxCleared", {"case": case})
    def check_chargebacks(s, account):
        r = s.chargeback_ratio()
        if r >= s.cfg()["chargeback_halt_pct"]: s.flag(account, None, "chargeback_halt")
        elif r >= s.cfg()["chargeback_warning_pct"]: s.flag(account, None, "chargeback_warning")
        return r

class VCard:
    def __init__(s, p, issuer=None):
        s.p, s.db, s.issuer = p, p.c.store.db, issuer or SandboxIssuer(); s.risk = VCRBox(s)
        s.db.executescript("""
        create table if not exists vcards(card text primary key, account text, internal text, token text, last4 text, type text, state text, lock text, expiry real, auto_renew int, rotation text,
                                          balance integer default 0, created real, physical text);
        create table if not exists vtxns(txn text primary key, card text, account text, state text, amount integer, buffer integer default 0, currency text, merchant text, supplier text, created real);
        create table if not exists vcommands(account text, key text, command text, payload_hash text, result text, primary key(account, key));
        create table if not exists vintents(nonce text primary key, account text, card text, reason text, expires real, state text);
        create table if not exists vdisputes(case_id text primary key, card text, txn text, state text);
        create table if not exists vflags(case_id text primary key, card text, rule text, created real, cleared integer);
        create table if not exists vwallet(card text, wallet text, active integer, primary key(card, wallet));
        create table if not exists vphysical(physical text primary key, card text, state text, tracking text);
        create table if not exists vrequests(request text primary key, account text, params text, state text, requester text);
        create table if not exists vkyb(account text primary key, issuer text, expires real);""")
    # plumbing
    def ev(s, account, name, payload): s.p.c.store.append(account, "server", name, payload)
    def _gate(s, account):
        s.p.c.gate(account, "vcard")
        code = s.p.c.profile(account)["country"]
        if os.environ.get("LYNK_MODE") != "sandbox" and not (country(code).get("vcard") or {}).get("enabled"): raise PermissionError("cards are not enabled in this country: no issuer agreement yet")
    def _perm(s, command, role, own_team_card=False):
        perm = CMD[command]["permission"]
        if role not in PERM[perm]["roles"] and not (own_team_card and perm == "vcard.freeze"): raise PermissionError(f"{role} cannot do {command}")
    def _once(s, account, key, command, payload, fn):
        """Idempotency: the same key and request returns the stored result. The same key with a different request is refused."""
        if not key: raise ValueError("idempotency_key is required")
        h = hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()
        r = s.db.execute("select payload_hash,result from vcommands where account=? and key=?", (account, key)).fetchone()
        if r:
            if r[0] != h: raise ValueError("idempotency key reused with a different request")
            return {**json.loads(r[1]), "replayed": True}
        res = fn(); s.db.execute("insert into vcommands values(?,?,?,?,?)", (account, key, command, h, json.dumps(res, default=str))); s.db.commit(); return res
    def _ent(s, account): return s.p.billing.entitlement(account, "lynkvcard")
    def _tier(s, account): return s.p.billing.tier(account, "lynkvcard")
    def _row(s, card):
        r = s.db.execute("select card,account,token,last4,type,state,lock,expiry,auto_renew,rotation,balance,physical from vcards where card=?", (card,)).fetchone()
        if not r: raise KeyError("unknown card")
        return dict(zip(("card", "account", "token", "last4", "type", "state", "lock", "expiry", "auto_renew", "rotation", "balance", "physical"), r)) | {"lock": json.loads(r[6] or "{}")}
    def _set(s, card, **kw):
        for k, v in kw.items(): s.db.execute(f"update vcards set {k}=? where card=?", (json.dumps(v) if k == "lock" else v, card))
        s.db.commit()
    def _usd(s, account, minor): return s.p.c.fx.convert(minor, s.p.c.profile(account)["currency"], "USD")
    def _month_spend_usd(s, account, now):
        rows = s.db.execute("select amount,currency from vtxns where account=? and state in ('authorized','settled') and created>?", (account, now - 30 * 86400)).fetchall()
        return sum(s.p.c.fx.convert(a, c, "USD") for a, c in rows)
    # identity: the issuer verifies the business. LynkOmni stores only the outcome.
    def attest_kyb(s, account, issuer, days=365, now=None):
        s.db.execute("insert or replace into vkyb values(?,?,?)", (account, issuer, (now or time.time()) + days * 86400)); s.db.commit()
        s.ev(account, "vcard.kyb_attested", {"issuer": issuer, "days": days})
    def _kyb(s, account, now):
        r = s.db.execute("select expires from vkyb where account=?", (account,)).fetchone()
        if not r or r[0] < now: raise PermissionError("the issuer has not verified this business yet")
    # commands
    def request_card(s, account, key, role, type="supplier", lock=None, amount_base=0, expiry_days=None, auto_renew=False, rotation_days=None, now=None, requester="owner"):
        s._gate(account); s._perm("RequestVirtualCard", role); now = now or time.time(); tier, ent = s._tier(account), s._ent(account)
        def go():
            if type not in TYPES: raise ValueError("unknown card type")
            s._kyb(account, now)
            if tier in SINGLE_USE_ONLY and type != "supplier": raise PermissionError("Free cards are single-use supplier cards. Upgrade for team, ads and subscription cards.")
            if type == "team" and not ent.get("team_cards"): raise PermissionError("team cards need LynkVCard Plus or higher")
            if s.risk.halted(): raise PermissionError("issuance is paused while a chargeback case is open")
            if not s.risk.issuance_ok(account, now): s.risk.flag(account, None, "issuance_velocity"); raise PermissionError("too many cards requested at once: flagged for review")
            active = s.db.execute("select count(*) from vcards where account=? and state in ('issued','active','frozen')", (account,)).fetchone()[0]
            if ent["active_cards"] is not None and active >= ent["active_cards"]: raise PermissionError("active card limit reached for this plan")
            made = s.db.execute("select count(*) from vcards where account=? and created>?", (account, now - 30 * 86400)).fetchone()[0]
            fee = 0
            if ent["new_cards_per_month"] is not None and made >= ent["new_cards_per_month"]:
                fee = s.p.c.fx.convert(25, "USD", s.p.c.profile(account)["currency"]); pr = s.p.c.profile(account)
                s.p.control.record_revenue(account, "vcard_issuance", fee, pr["currency"], pr["country"])     # $0.25 per card beyond the plan allowance
            cap = ent["monthly_cap_usd"]
            if amount_base and cap is not None and s._month_spend_usd(account, now) + s._usd(account, amount_base) > cap * 100: raise PermissionError("monthly spend cap for this plan would be exceeded")
            res = s.issuer.create(key, {"type": type}); internal = _id(); card = s.p.ids.assign("VC", internal)
            if tier in SINGLE_USE_ONLY: expiry = now + ent["card_expiry_hours"] * 3600
            else: expiry = now + (expiry_days or 90) * 86400
            s.db.execute("insert into vcards values(?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (card, account, internal, res["token"], res["last4"], type, "active", json.dumps(lock or {}), expiry, int(auto_renew), f"{rotation_days}d" if rotation_days else None, 0, now, None)); s.db.commit()
            s.ev(account, "VirtualCardCreated", {"card": card, "last4": res["last4"], "token": res["token"], "country_pack": s.p.c.profile(account)["country"], "expiry_utc": _iso(expiry), "rotation_policy": f"{rotation_days}d" if rotation_days else None})
            return {"card": card, "last4": res["last4"], "state": "active", "extra_card_fee_minor": fee}
        out = s._once(account, key, "RequestVirtualCard", {"type": type, "lock": lock, "amount": amount_base, "role": role}, go)
        if amount_base and not out.get("replayed"): out["funding"] = s.request_funding(account, key + ":fund", out["card"], amount_base, role=role, now=now)
        return out
    def request_funding(s, account, key, card, amount_base, funding_source=None, role="owner", now=None):
        s._gate(account); s._perm("RequestFunding", role); now = now or time.time(); c = s._row(card)
        def go():
            methods = country(s.p.c.profile(account)["country"])["providers"]; src = funding_source or next((m for m in methods if m not in ("qr",)), None)
            if src not in methods: raise ValueError("funding source is not a payment method of this country pack")
            method = {"momo_mtn": "mobile_money", "airtel_money": "mobile_money", "mpesa": "mobile_money", "upi": "upi", "bank_transfer": "bank", "card": "card"}.get(src, src)
            pay = s.p.payments.charge(account, amount_base, method, key)                              # the debit runs on the local rail, idempotent by the same key
            if not pay["ok"]: s.ev(account, "VirtualCardFundingFailed", {"card": card, "reason": "payment failed"}); return {"ok": False, "reason": "payment failed"}
            r = s.issuer.fund(key, c["token"], amount_base)
            if not r["ok"]: s.ev(account, "VirtualCardFundingFailed", {"card": card, "reason": r["reason"]}); return {"ok": False, "reason": r["reason"]}
            txn = s.p.ids.assign("TXN", _id()); s._set(card, balance=c["balance"] + amount_base)
            s.db.execute("insert into vtxns values(?,?,?,?,?,?,?,?,?,?)", (txn, card, account, "settled", amount_base, 0, s.p.c.profile(account)["currency"], "funding", None, now)); s.db.commit()
            s.ev(account, "VirtualCardFunded", {"card": card, "txn": txn, "amount_base": amount_base, "amount_card": amount_base, "rate": 1}); return {"ok": True, "txn": txn}
        return s._once(account, key, "RequestFunding", {"card": card, "amount": amount_base, "src": funding_source}, go)
    def _freeze_now(s, account, card, reason):
        c = s._row(card)
        if c["state"] != "active": return {"state": c["state"]}
        s.issuer.freeze(f"freeze:{card}:{reason}:{_id()}", c["token"]); s._set(card, state="frozen"); s._revoke_wallets(account, card, "freeze"); s.ev(account, "VirtualCardFrozen", {"card": card, "reason": reason}); return {"state": "frozen"}
    def request_freeze(s, account, key, card, reason, role="owner", own_card=False):
        s._gate(account); s._perm("RequestFreeze", role, own_card)
        return s._once(account, key, "RequestFreeze", {"card": card, "reason": reason}, lambda: s._freeze_now(account, card, reason))
    def queue_freeze(s, account, card, reason, nonce, now=None):
        """Offline: record an intent. It is NOT a freeze. The card stays active until VirtualCardFrozen is issued."""
        now = now or time.time(); s._row(card)
        try: s.db.execute("insert into vintents values(?,?,?,?,?,'queued')", (nonce, account, card, reason, now + 24 * 3600)); s.db.commit()
        except Exception: raise PermissionError("this intent was already submitted (replay)")
        s.ev(account, "VirtualCardFreezeIntentQueued", {"card": card, "nonce": nonce, "expires_utc": _iso(now + 24 * 3600)})
        return {"state": "freeze_requested_waiting_for_connection", "card_state": s._row(card)["state"]}
    def process_intents(s, now=None):
        now, out = now or time.time(), {"done": 0, "expired": 0}
        for nonce, account, card, reason, exp in s.db.execute("select nonce,account,card,reason,expires from vintents where state='queued'").fetchall():
            if exp < now: s.db.execute("update vintents set state='expired' where nonce=?", (nonce,)); s.ev(account, "VirtualCardFreezeIntentExpired", {"card": card, "nonce": nonce}); out["expired"] += 1
            else: s._freeze_now(account, card, reason); s.db.execute("update vintents set state='done' where nonce=?", (nonce,)); out["done"] += 1
        s.db.commit(); return out
    def request_unfreeze(s, account, key, card, role="owner"):
        s._gate(account); s._perm("RequestUnfreeze", role)
        def go():
            if s.db.execute("select 1 from vflags where card=? and cleared=0", (card,)).fetchone(): raise PermissionError("an open risk case blocks unfreezing")
            c = s._row(card)
            if c["state"] != "frozen": raise ValueError("card is not frozen")
            s._set(card, state="active"); s.ev(account, "VirtualCardUnfrozen", {"card": card}); return {"state": "active"}
        return s._once(account, key, "RequestUnfreeze", {"card": card}, go)
    def request_close(s, account, key, card, role="owner"):
        s._gate(account); s._perm("RequestClose", role)
        def go():
            c = s._row(card); r = s.issuer.close(key, c["token"], c["balance"]); s._set(card, state="closed", balance=0); s._revoke_wallets(account, card, "close")
            s.ev(account, "VirtualCardClosed", {"card": card, "refund_base": r["refund"]}); return {"state": "closed", "refund_base": r["refund"]}   # the balance returns through the issuer, never held by LynkOmni
        return s._once(account, key, "RequestClose", {"card": card}, go)
    def request_rotate(s, account, key, card, reason, role="owner"):
        s._gate(account); s._perm("RequestRotateCard", role)
        def go():
            c = s._row(card); r = s.issuer.rotate(key, c["token"]); s.db.execute("update vcards set token=?, last4=? where card=?", (r["token"], r["last4"], card)); s.db.commit(); s._revoke_wallets(account, card, "rotate")
            s.ev(account, "VirtualCardRotated", {"card": card, "new_token": r["token"], "new_last4": r["last4"], "old_revoked": True}); return {"card": card, "last4": r["last4"]}   # same LOVC- identifier, new token
        return s._once(account, key, "RequestRotateCard", {"card": card, "reason": reason}, go)
    def set_lock(s, account, key, card, role, **lock):
        """Time-locked, supplier-locked, shift-locked and category-locked cards. Pro and above."""
        s._gate(account); s._perm("RequestTimeLockedCard", role); e = s._ent(account)
        if ("until" in lock and not e.get("time_locked")) or ("supplier" in lock and not (e.get("supplier_locked") or e.get("supplier_auto_cards"))) or ("shift" in lock and not e.get("shift_locked")):
            raise PermissionError("this lock is not in your LynkVCard plan")
        def go():
            c = s._row(card); s._set(card, lock={**c["lock"], **lock}); s.ev(account, "VirtualCardLimitsChanged", {"card": card, "limits": lock}); return {"lock": s._row(card)["lock"]}
        return s._once(account, key, "RequestTimeLockedCard", {"card": card, "lock": lock}, go)
    # wallets and display (never a card number)
    def provision_wallet(s, account, key, card, wallet, role="owner"):
        s._gate(account); s._perm("RequestWalletProvisioning", role); c = s._row(card)
        def go():
            s.issuer.provision(key, c["token"], wallet); s.db.execute("insert or replace into vwallet values(?,?,1)", (card, wallet)); s.db.commit(); s.ev(account, "WalletTokenProvisioned", {"card": card, "wallet": wallet}); return {"ok": True}
        return s._once(account, key, "RequestWalletProvisioning", {"card": card, "wallet": wallet}, go)
    def _revoke_wallets(s, account, card, why):
        for (w,) in s.db.execute("select wallet from vwallet where card=? and active=1", (card,)).fetchall():
            s.issuer.revoke_wallet(card, w); s.db.execute("update vwallet set active=0 where card=? and wallet=?", (card, w)); s.ev(account, "WalletTokenRevoked", {"card": card, "wallet": w, "reason": why})
        s.db.commit()
    def display_session(s, account, card, role, stepup):
        s._gate(account); s._perm("RequestCardDisplaySession", role)
        if not stepup or not s.p.identity.stepup_valid(stepup, account): raise PermissionError("extra verification is required to view card details")
        return s.issuer.display_session(s._row(card)["token"])        # an ephemeral issuer-hosted view. LynkOmni never receives the number.
    # card use
    def authorize(s, card, merchant, mcc, amount, currency, supplier=None, now=None):
        now = now or time.time(); c = s._row(card); a = c["account"]; pr = s.p.c.profile(a); pack = country(pr["country"]); deny = None
        if c["state"] != "active": deny = f"card is {c['state']}"
        elif c["expiry"] < now: deny = "card expired"
        elif mcc in (pack.get("vcard") or {}).get("blocked_mcc", []): deny = "category blocked in this country"
        elif c["lock"].get("supplier") and c["lock"]["supplier"] != supplier: deny = "locked to another supplier"
        elif c["lock"].get("until") and c["lock"]["until"] < now: deny = "time lock expired"
        elif c["lock"].get("categories") and mcc not in c["lock"]["categories"]: deny = "category lock"
        elif c["lock"].get("shift"):
            h = local_dt(_iso(now), pr["country"]).strftime("%H:%M"); lo, hi = c["lock"]["shift"]
            if not (lo <= h <= hi): deny = "outside the shift window"
        hold = amount * 2 // 100 if currency != pr["currency"] else 0   # 2% temporary buffer on foreign-currency spend, released at settlement
        if not deny and c["balance"] < amount + hold: deny = "insufficient balance"
        if not deny and s._ent(a)["monthly_cap_usd"] is not None and s._month_spend_usd(a, now) + s._usd(a, amount) > s._ent(a)["monthly_cap_usd"] * 100: deny = "monthly cap reached"
        if deny: s.ev(a, "VirtualCardAuthDeclined", {"card": card, "reason": deny}); return {"approved": False, "reason": deny}
        txn = s.p.ids.assign("TXN", _id()); s._set(card, balance=c["balance"] - amount - hold)
        s.db.execute("insert into vtxns values(?,?,?,?,?,?,?,?,?,?)", (txn, card, a, "authorized", amount, hold, currency, merchant, supplier, now)); s.db.commit()
        s.ev(a, "VirtualCardAuthorized", {"card": card, "txn": txn, "merchant": merchant, "mcc": mcc, "amount": amount, "category": mcc, "auth_rate": 1, "buffer_hold": hold})
        if amount >= 50 * 10 ** 4 or currency != pr["currency"]: s.ev(a, "VirtualCardChallengeIssued", {"card": card, "txn": txn, "channel": "app_approval"})   # never a chat thread
        return {"approved": True, "txn": txn, "buffer_hold": hold, "challenge_channel": "app_approval"}
    def respond_to_challenge(s, account, card, txn, decision, stepup):
        if not stepup or not s.p.identity.stepup_valid(stepup, account): raise PermissionError("the approval must come from the signed-in device with extra verification")
        s.ev(account, "VirtualCardChallengeResolved", {"card": card, "txn": txn, "decision": decision}); return {"decision": decision}
    def settle(s, txn, final_amount_base, final_rate=1.0, supplier_fiscal_ref=None):
        t = s.db.execute("select card,account,amount,buffer,currency,state from vtxns where txn=?", (txn,)).fetchone()
        if not t or t[5] != "authorized": raise ValueError("transaction is not awaiting settlement")
        card, a, auth, hold, cur, _ = t; c = s._row(card); pr = s.p.c.profile(a)
        s._set(card, balance=c["balance"] + hold + auth - final_amount_base); s.db.execute("update vtxns set state='settled', buffer=0, amount=? where txn=?", (final_amount_base, txn)); s.db.commit()
        rcp = s.p.ids.assign("RCP", _id())
        s.ev(a, "VirtualCardSettled", {"card": card, "txn": txn, "final_amount_base": final_amount_base, "final_rate": final_rate, "buffer_released": hold})
        s.ev(a, "VirtualCardReceiptCreated", {"receipt": rcp, "card": card, "txn": txn, "final_amount_base": final_amount_base, "fiscal": False, "supplier_fiscal_ref": supplier_fiscal_ref})   # a payment record, never a fiscal invoice
        s.p.c.store.append(a, "server", "expense.recorded", {"amount_minor": final_amount_base, "category": "card_spend", "currency": pr["currency"]})            # feeds the accountant automatically
        interchange = final_amount_base * INTERCHANGE_BPS // 10000; fx = final_amount_base * FX_NET_BPS // 10000 if cur != pr["currency"] else 0
        if interchange: s.p.control.record_revenue(a, "vcard_interchange", interchange, pr["currency"], pr["country"])
        if fx: s.p.control.record_revenue(a, "vcard_fx", fx, pr["currency"], pr["country"])
        cb = final_amount_base * (s._ent(a).get("cashback_bps") or 0) // 10000
        if cb: s.p.c.store.append(a, "server", "loyalty.earned", {"customer": a, "points": cb})          # cashback as LynkPoints, funded from interchange
        return {"receipt": rcp, "interchange_minor": interchange, "fx_minor": fx, "cashback_points": cb}
    # disputes, physical companion, supplier score
    def request_dispute(s, account, key, card, txn, reason, role="owner"):
        s._gate(account); s._perm("RequestDispute", role)
        def go():
            case = s.p.support.open_case(account, "card_dispute"); s.db.execute("update vtxns set state='disputed' where txn=?", (txn,)); s.db.execute("insert into vdisputes values(?,?,?,'opened')", (case, card, txn)); s.db.commit()
            s.ev(account, "DisputeCreated", {"case": case, "card": card, "txn": txn}); s.risk.check_chargebacks(account); return {"case": case}
        return s._once(account, key, "RequestDispute", {"card": card, "txn": txn, "reason": reason}, go)
    def resolve_dispute(s, account, case, outcome):
        s.db.execute("update vdisputes set state='resolved' where case_id=?", (case,)); s.db.commit()
        refund = s.p.ids.assign("TXN", _id()) if outcome == "refund" else None; s.ev(account, "DisputeResolved", {"case": case, "outcome": outcome, "refund_txn": refund}); return {"refund_txn": refund}
    def request_physical(s, account, key, card, address_ref, role="owner", now=None):
        s._gate(account); s._perm("RequestPhysicalCompanionCard", role); now = now or time.time()
        if not s._ent(account).get("physical_companion"): raise PermissionError("the physical companion is part of LynkVCard Max")
        def go():
            s._kyb(account, now); c = s._row(card); phys = s.p.ids.assign("PC", _id()); r = s.issuer.physical(key, c["token"])
            s.db.execute("insert into vphysical values(?,?,?,?)", (phys, card, "shipped", r["tracking_id"])); s._set(card, physical=phys); s.db.commit()
            s.ev(account, "PhysicalCardOrdered", {"physical": phys, "card": card}); s.ev(account, "PhysicalCardShipped", {"physical": phys, "tracking_id": r["tracking_id"]}); return {"physical": phys, "tracking_id": r["tracking_id"]}   # linked to its card by the database, not by composing IDs
        return s._once(account, key, "RequestPhysicalCompanionCard", {"card": card, "addr": address_ref}, go)
    def activate_physical(s, account, key, physical, stepup, role="owner"):
        s._gate(account); s._perm("ActivatePhysicalCard", role)
        if not stepup or not s.p.identity.stepup_valid(stepup, account): raise PermissionError("activation needs extra verification")
        def go():
            s.db.execute("update vphysical set state='activated' where physical=?", (physical,)); s.db.commit(); s.ev(account, "PhysicalCardActivated", {"physical": physical}); return {"state": "activated"}
        return s._once(account, key, "ActivatePhysicalCard", {"physical": physical}, go)
    def update_supplier_scores(s, min_group=3):
        """Aggregated only: a supplier needs at least three distinct merchants before any score exists."""
        out = {}
        for sup, n, bad in s.db.execute("select supplier, count(distinct account), sum(case when state='disputed' then 1 else 0 end) from vtxns where supplier is not null group by supplier").fetchall():
            if n >= min_group:
                total = s.db.execute("select count(*) from vtxns where supplier=?", (sup,)).fetchone()[0]; score = s.p.ids.assign("SC", sup)
                s.p.c.store.append(COMPANY, "server", "VirtualCardSupplierScoreUpdated", {"score": score, "supplier": sup, "reliability_pct": round(100 * (1 - bad / total), 1)}); out[sup] = score
        return out
