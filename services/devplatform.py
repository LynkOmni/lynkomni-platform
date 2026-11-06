"""LynkHub (apps, keys, consent scopes, metering) and LynkAPI (authorization, quotas, audit) for LynkDev customers.
Placeholders: scope names and daily call limits. Real deployments need hardened key storage and rate limiting at the gateway."""
import hashlib, secrets, time
from services.control import COMPANY
from services.billing import FEATURES

SCOPES = {"sales.read", "stock.read", "customers.read", "payments.read"}

class RateLimited(Exception):
    pass

class DevPlatform:
    def __init__(s, c, billing, rights): s.c, s.billing, s.rights = c, billing, rights
    @staticmethod
    def _h(key): return hashlib.sha256(key.encode()).hexdigest()
    def create_app(s, developer, name, scopes):
        bad = set(scopes) - SCOPES
        if bad:
            raise ValueError(f"unknown scopes {sorted(bad)}")
        app_id, key = secrets.token_hex(6), "lk_" + secrets.token_urlsafe(24)
        s.c.store.append(COMPANY, "server", "dev.app.created", {"app_id": app_id, "developer": developer, "name": name, "scopes": sorted(scopes), "key_hash": s._h(key)})
        return {"app_id": app_id, "api_key": key}   # the key is shown once and only its hash is stored
    def _app(s, key):
        h = s._h(key)
        return next((e["payload"] for e in s.c.store.of(COMPANY, "dev.app.created") if e["payload"]["key_hash"] == h), None)
    def grant(s, merchant, app_id, scope): s.rights.grant(merchant, f"app:{app_id}:{scope}")      # the merchant approves what each app may read
    def revoke(s, merchant, app_id, scope): s.rights.revoke(merchant, f"app:{app_id}:{scope}")
    def authorize(s, api_key, merchant, scope, day=None):
        app = s._app(api_key)
        if app is None:
            raise PermissionError("unknown API key")
        if scope not in app["scopes"] or not s.rights.has_consent(merchant, f"app:{app['app_id']}:{scope}"):
            raise PermissionError("the merchant has not approved this scope for this app")
        limit = s.billing.entitlement(app["developer"], "lynkdev").get("api_calls_per_day")
        day = day or time.strftime("%Y-%m-%d")
        used = sum(1 for e in s.c.store.of(COMPANY, "api.call") if e["payload"]["app_id"] == app["app_id"] and e["ts"][:10] == day)
        if limit is not None and used >= limit:
            raise RateLimited("daily quota reached for this LynkDev plan")
        s.c.store.append(COMPANY, "server", "api.call", {"app_id": app["app_id"], "merchant": merchant, "scope": scope})   # audit and metering in one record
        s.c.store.append(merchant, "server", "api.access", {"app_id": app["app_id"], "scope": scope})                      # the merchant can see who read what
        return {"ok": True, "calls_today": used + 1}
    def usage(s, app_id): return sum(1 for e in s.c.store.of(COMPANY, "api.call") if e["payload"]["app_id"] == app_id)
