"""Step-up verification for sensitive actions (Exchange, credit). Sandbox: the caller states that the extra check passed.
A real deployment verifies a fresh second factor first. Tokens are short-lived and bound to one account."""
import hashlib, hmac, time
from services.suite import PayLinks

class StepUp:
    TTL = 300
    def issue(s, account, verified=False):
        if not verified:
            raise PermissionError("the extra verification step has not passed")
        exp = int(time.time()) + s.TTL; body = f"{account}|{exp}"
        return body + "|" + hmac.new(PayLinks.SECRET.encode(), body.encode(), hashlib.sha256).hexdigest()[:24]
    def stepup_valid(s, token, account):
        try:
            acct, exp, sig = token.split("|")
            ok = hmac.compare_digest(sig, hmac.new(PayLinks.SECRET.encode(), f"{acct}|{exp}".encode(), hashlib.sha256).hexdigest()[:24])
            return ok and acct == account and int(exp) >= time.time()
        except Exception:
            return False
