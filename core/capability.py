"""Capability tokens: tickets, payment links, receipt checks. A capability grants ONE narrow action, expires, and never grants read
access to a record. A public identifier is not a capability. Tickets rotate every 30 seconds so a screenshot stops working."""
import base64, hashlib, hmac, json, os, secrets, time

SECRET = os.environ.get("LYNK_CAP_SECRET", "dev-only-change-me")
WINDOW = 30
KINDS = {"ticket_entry", "pay_link", "receipt_verify", "shop_door", "newsletter_confirm", "newsletter_unsubscribe"}

def _sig(body): return hmac.new(SECRET.encode(), body.encode(), hashlib.sha256).hexdigest()[:32]

class Capabilities:
    def __init__(s, db):
        s.db = db; db.execute("create table if not exists cap_used(jti text primary key, used_at real)"); db.commit()
    def issue(s, kind, subject, action, ttl=3600, single_use=True, now=None):
        if kind not in KINDS: raise ValueError("unknown capability kind")
        now = time.time() if now is None else now
        body = json.dumps({"k": kind, "s": subject, "a": action, "x": int(now + ttl), "j": secrets.token_hex(8), "u": single_use}, separators=(",", ":"))
        return base64.urlsafe_b64encode(body.encode()).decode() + "." + _sig(body)
    def verify(s, token, kind, action, subject=None, now=None, consume=True):
        now = time.time() if now is None else now
        try:
            b, sig = token.rsplit(".", 1); body = base64.urlsafe_b64decode(b.encode()).decode(); c = json.loads(body)
        except Exception:
            raise PermissionError("invalid token")
        if not hmac.compare_digest(sig, _sig(body)) or c["k"] != kind or c["a"] != action or (subject and c["s"] != subject):
            raise PermissionError("token does not allow this action")
        if c["x"] < now: raise PermissionError("token expired")
        if c["u"] and consume:
            try: s.db.execute("insert into cap_used values(?,?)", (c["j"], now)); s.db.commit()
            except Exception: raise PermissionError("token already used")
        return {"subject": c["s"], "action": c["a"]}          # the caller receives only what the token names, never a record
    # ticket entry: a rotating code derived from the ticket secret, valid for the current 30-second window (and one before)
    def ticket_code(s, ticket_id, now=None):
        w = int((time.time() if now is None else now) // WINDOW); return f"{ticket_id}.{w}.{_sig(f'{ticket_id}|{w}')[:12]}"
    def redeem_ticket(s, code, now=None):
        now = time.time() if now is None else now
        try: tid, w, sig = code.rsplit(".", 2); w = int(w)
        except Exception: raise PermissionError("invalid ticket code")
        cur = int(now // WINDOW)
        if w not in (cur, cur - 1) or not hmac.compare_digest(sig, _sig(f"{tid}|{w}")[:12]): raise PermissionError("ticket code expired or invalid: refresh it")
        try: s.db.execute("insert into cap_used values(?,?)", (f"ticket:{tid}", now)); s.db.commit()
        except Exception: raise PermissionError("ticket already used")
        return tid
