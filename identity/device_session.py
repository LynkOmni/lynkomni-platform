"""Device-tied sessions (MASTER UPDATE, master blueprint section 59; build section 1).

A session belongs to the device that signed in, not to whoever holds its token. When a session starts, the device's public key
(identity/offline.py DeviceKey; the private half never leaves the device) is bound to the session. Every request then carries a
proof signed by that key over the method, the address, the time and a fresh number used once. So a token copied from a log, a
browser extension or a stolen backup is useless on another device:
- no proof, a proof from another key, or a proof for another request is refused;
- a proof older or newer than PROOF_WINDOW_S is refused (a clock turned back cannot replay it);
- a number used once is never accepted twice (replay);
- a session ends by itself after IDLE_S without use and after MAX_S in all; a revoked session never comes back.
Every refusal says why, for the Security Center, and three refusals in a row end the session; the person then signs in again on
their own device (section 2 shows these refusals in the Security Center)."""
import secrets, time
from identity.offline import signature_ok

PROOF_WINDOW_S = 120
IDLE_S = 30 * 60
MAX_S = 30 * 86_400
REFUSALS_BEFORE_END = 3


def _now(n):
    return time.time() if n is None else n


class Sessions:
    def __init__(self):
        self.s = {}

    def start(self, person, device_public_hex, now=None):
        if not device_public_hex or len(device_public_hex) != 64:
            raise ValueError("a session needs the device's public key")
        tok = secrets.token_urlsafe(32)
        n = _now(now)
        self.s[tok] = {"person": person, "device": device_public_hex, "started": n, "last": n, "nonces": set(), "refused": 0, "ended": None}
        return tok

    @staticmethod
    def proof_body(token, method, address, ts, nonce):
        return {"token_tail": token[-8:], "method": method.upper(), "address": address, "ts": int(ts), "nonce": nonce}

    def check(self, token, method, address, ts, nonce, sig, now=None):
        """Returns {"ok": True, "person": ...} or {"ok": False, "why": ...}."""
        n = _now(now)
        x = self.s.get(token)
        if x is None:
            return {"ok": False, "why": "unknown_session"}
        if x["ended"]:
            return {"ok": False, "why": "session_ended"}
        if n - x["last"] > IDLE_S or n - x["started"] > MAX_S:
            x["ended"] = "expired"
            return {"ok": False, "why": "session_ended"}
        why = None
        if abs(n - ts) > PROOF_WINDOW_S:
            why = "proof_too_old"
        elif nonce in x["nonces"]:
            why = "proof_replayed"
        elif not sig or not signature_ok(x["device"], self.proof_body(token, method, address, ts, nonce), sig):
            why = "not_this_device"
        if why:
            x["refused"] += 1
            if x["refused"] >= REFUSALS_BEFORE_END:
                x["ended"] = "refused"
            return {"ok": False, "why": why}
        x["nonces"].add(nonce)
        x["last"], x["refused"] = n, 0
        return {"ok": True, "person": x["person"]}

    def revoke(self, token):
        if token in self.s:
            self.s[token]["ended"] = "revoked"


def sign_request(key, token, method, address, now=None):
    """What the device sends with each request: the time, a fresh number and its signature."""
    ts, nonce = int(_now(now)), secrets.token_hex(12)
    return ts, nonce, key.sign(Sessions.proof_body(token, method, address, ts, nonce))
