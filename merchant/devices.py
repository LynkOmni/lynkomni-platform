"""Registered devices and the web rule (blueprint 44 C), and device drivers behind one interface.

The web rule: selling, the cash drawer, shifts, cash counts and agent services run only on a phone, tablet or LynkPOS handheld
registered to the business (app.lynkomni.com/business/devices). Everything else works in any browser; on a computer that is not
registered the rest of the Business app can be viewed, and settings change with an extra check.

Device drivers: LynkPOS runs on the LynkOmni handheld, on Android smart terminals that allow third-party apps, on any Android
phone or tablet and on iPhone and iPad. Each maker's printer, scanner, cash drawer, customer display and card reader plugs in
behind DeviceDrivers, the way providers plug in behind Provider. The card reader is the acquirer's certified part: our app
never touches card data. Old-style bank terminals that run only the bank's software cannot run LynkPOS; where the bank offers
an interface, a terminal link pairs the two (provider ledger: pos_terminal_drivers, bank_terminal_link; SANDBOX drivers here)."""
import time

from services import billing

TILL_ACTIONS = ("sell", "cash_drawer", "shift", "cash_count", "agent_service", "collection", "partner_finance")
BROWSER_OK = ("view", "reports", "stock_view", "customers", "chats", "invoices", "accounting", "crm", "analytics", "settings_view")
STEP_UP_IN_BROWSER = ("settings_change",)
KINDS = ("phone", "tablet", "handheld", "smart_terminal", "button_phone", "scanner", "kitchen_screen", "customer_display", "rider_phone")
PLATFORMS = ("android", "ios")
def _now(n): return time.time() if n is None else n


def web_rule(action, device_registered):
    """What an action needs: 'ok', 'registered_device' or 'step_up'."""
    if action in TILL_ACTIONS: return "ok" if device_registered else "registered_device"
    if action in STEP_UP_IN_BROWSER: return "ok" if device_registered else "step_up"
    return "ok"


class DeviceDrivers:
    """One interface for the hardware around the till. A maker's adapter implements the parts its device has; `has()` tells the
    screen which buttons to show. Nothing here ever sees a card number."""
    def has(self, part): raise NotImplementedError            # "printer", "scanner", "cash_drawer", "customer_display", "card_reader"
    def print(self, lines): raise NotImplementedError          # thermal printer, 32 or 48 characters wide
    def open_drawer(self): raise NotImplementedError
    def scan(self): raise NotImplementedError                   # returns a barcode text or None
    def show(self, lines): raise NotImplementedError            # customer-facing display
    def card_tap(self, amount_minor, currency): raise NotImplementedError   # hands the amount to the acquirer's certified kit; returns {"sent": True, "reference"} only


class SandboxDrivers(DeviceDrivers):
    """SANDBOX drivers: remember what was printed, shown and tapped, so emulators and tests can look."""
    def __init__(self, parts=("printer", "scanner", "cash_drawer", "customer_display", "card_reader")):
        self.parts, self.printed, self.shown, self.drawer_opens, self.taps, self.next_scan = set(parts), [], [], 0, [], None
    def has(self, part): return part in self.parts
    def print(self, lines):
        if not self.has("printer"): raise RuntimeError("no_printer")
        self.printed.append(list(lines))
    def open_drawer(self):
        if not self.has("cash_drawer"): raise RuntimeError("no_cash_drawer")
        self.drawer_opens += 1
    def scan(self): v, self.next_scan = self.next_scan, None; return v
    def show(self, lines): self.shown.append(list(lines))
    def card_tap(self, amount_minor, currency):
        if not self.has("card_reader"): raise RuntimeError("no_card_reader")
        self.taps.append((amount_minor, currency)); return {"sent": True, "reference": f"SBXTAP{len(self.taps):04d}"}   # the acquirer confirms later, never the device


class BankTerminalLink:
    """Interface for pairing with an existing bank terminal where the bank offers one: LynkPOS sends the amount, the bank's
    terminal takes the card, the bank reports the result. PLACEHOLDER until a bank signs (ledger: bank_terminal_link)."""
    def send_amount(self, amount_minor, currency, reference): raise NotImplementedError
    def result(self, reference): raise NotImplementedError


class Devices:
    def __init__(s, cloud, platform):
        s.cloud, s.p, s.db = cloud, platform, platform.c.store.db
        s.db.executescript("create table if not exists mdev(device_id text primary key, merchant text, name text, kind text, platform text, enrolled real, revoked real, reason text, last_seen real, app_version text, battery int, storage_free_mb int);")
    def enrol(s, merchant, device_id, name, kind, platform_, by_user, public_key, now=None):
        if kind not in KINDS: raise ValueError("unknown device kind")
        limit = billing.Billing(s.p.c).entitlement(merchant, "lynkpos").get("devices")
        have = s.db.execute("select count(*) from mdev where merchant=? and revoked is null", (merchant,)).fetchone()[0]
        if limit is not None and have >= limit: raise PermissionError("device_limit_for_tier")
        s.db.execute("insert or replace into mdev(device_id, merchant, name, kind, platform, enrolled) values(?,?,?,?,?,?)", (device_id, merchant, name, kind, platform_, _now(now)))
        s.cloud.event(merchant, "DeviceEnrolled", {"device_id": device_id, "device_name": name, "platform": platform_, "public_key": public_key, "enrolled_by_user_id": by_user}, now=now)
    def revoke(s, merchant, device_id, by_user, reason, now=None):
        s.db.execute("update mdev set revoked=?, reason=? where device_id=? and merchant=?", (_now(now), reason, device_id, merchant))
        s.cloud.event(merchant, "DeviceRevoked", {"device_id": device_id, "revoked_by_user_id": by_user, "reason": reason}, now=now)
    def registered(s, merchant, device_id):
        r = s.db.execute("select revoked from mdev where device_id=? and merchant=?", (device_id, merchant)).fetchone()
        return bool(r) and r[0] is None
    def list(s, merchant):
        return [{"device_id": r[0], "name": r[1], "kind": r[2], "platform": r[3], "active": r[4] is None} for r in s.db.execute("select device_id, name, kind, platform, revoked from mdev where merchant=? order by enrolled", (merchant,))]
    def may(s, merchant, device_id, action): return web_rule(action, s.registered(merchant, device_id))
    # ---- device health (automation: daily): old app, low battery, little storage, long silence
    def heartbeat(s, merchant, device_id, app_version, battery, storage_free_mb, now=None):
        s.db.execute("update mdev set last_seen=?, app_version=?, battery=?, storage_free_mb=? where device_id=? and merchant=?", (_now(now), app_version, battery, storage_free_mb, device_id, merchant))
    def health(s, merchant, current_version, now=None, silent_days=3):
        now, out = _now(now), []
        for r in s.db.execute("select device_id, last_seen, app_version, battery, storage_free_mb from mdev where merchant=? and revoked is null", (merchant,)):
            issues = []
            if r[1] is not None and now - r[1] > silent_days * 86400: issues.append("not_seen")
            if r[2] and r[2] != current_version: issues.append("old_app")
            if r[3] is not None and r[3] < 15: issues.append("low_battery")
            if r[4] is not None and r[4] < 200: issues.append("low_storage")
            if issues: out.append({"device_id": r[0], "issues": issues})
        return out
