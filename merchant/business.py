"""The Business app (blueprint sections 5, 7 and 42 H; 44 C; 44 I): the business profile and the rules every merchant screen
shares. Tabs follow the business type; setup takes under two minutes and the first sale under one; the daily close is one
simple message; a second currency shows beside the sale currency as a labelled estimate while the sale stays in local money;
receipts go by print, QR or message by tier; practice mode never touches real records; "Confirmed" appears only when the
provider confirms (fake payment protection); the shop's username follows the one username rule; data sharing with suppliers
is one recorded consent each, withdrawable; the Academy opens beside the screen it teaches."""
import re, time

from core import workspaces
from core.usernames import UsernameRegistry, check as username_check
from services import billing

TYPES = ("shop", "no_till", "agent_point", "restaurant")
TABS = {"shop": ("home", "sell", "stock", "chats", "business"), "no_till": ("home", "invoices", "customers", "chats", "business"),
        "agent_point": ("home", "services", "float", "chats", "business"), "restaurant": ("home", "tables", "kitchen", "chats", "business")}
SETUP_STEPS = ("locale_card", "who_for", "business_name", "business_type", "first_product")       # under two minutes; the first sale within a minute
HANDHELD_TILES = ("sell", "agent", "collect", "bills", "airtime_data", "tickets", "government", "remittances", "partner_finance", "customers_credit", "reports", "settings")
FAST_CHECKOUT = ("scan", "tap", "voice")
RECEIPT_CHANNELS = ("print", "qr", "message")
BUSINESS_SECTIONS = ("money", "reports", "staff", "devices", "loyalty", "marketplace", "growth", "automations", "settings", "academy")
PROOF_WARNING_KEY = "payment_proof_warning"      # the cashier is told that a text message or screenshot is not proof of payment
NUMBER_WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10, "a": 1, "an": 1}
def _now(n): return time.time() if n is None else n


class Business:
    def __init__(s, cloud, platform, usernames=None):
        s.cloud, s.p, s.db, s.usernames = cloud, platform, platform.c.store.db, usernames or UsernameRegistry()
        s.db.executescript("""
        create table if not exists biz(lynkoid text primary key, name text, type text, country text, username text, currency text, low_literacy int, practice int, setup text, created real, entity text default 'company', kind text default 'business');
        create table if not exists biz_share(lynkoid text, supplier text, locns text, granted real, withdrawn real, primary key(lynkoid, supplier));""")
    # ---- profile, type and tabs
    def create(s, lynkoid, name, business_type, country, currency, now=None, entity="company", kind=None):
        """A workspace for a person, a company or an organisation (core/workspaces.py): the entity changes words, tabs and
        categories only; every record and rule is the same."""
        if business_type not in TYPES: raise ValueError("unknown business type")
        entity, kind = workspaces.check(entity, kind)
        s.db.execute("insert or replace into biz(lynkoid, name, type, country, currency, low_literacy, practice, setup, created, entity, kind) values(?,?,?,?,?,0,0,'',?,?,?)", (lynkoid, name, business_type, country, currency, _now(now), entity, kind))
        s.cloud.signal(lynkoid, "BusinessCreated", {"lynkoid": lynkoid, "business_type": business_type, "country": country, "entity": entity, "kind": kind}, now=now)
    def entity(s, lynkoid):
        r = s.db.execute("select entity, kind from biz where lynkoid=?", (lynkoid,)).fetchone(); return (r[0], r[1]) if r else ("company", "business")
    def word(s, lynkoid, key): return workspaces.word(s.entity(lynkoid)[0], key)
    def set_type(s, lynkoid, business_type):
        if business_type not in TYPES: raise ValueError("unknown business type")
        s.db.execute("update biz set type=? where lynkoid=?", (business_type, lynkoid))
    def type(s, lynkoid):
        r = s.db.execute("select type from biz where lynkoid=?", (lynkoid,)).fetchone(); return r[0] if r else "shop"
    def tabs(s, lynkoid): return workspaces.tabs(s.entity(lynkoid)[0], s.type(lynkoid), TABS[s.type(lynkoid)])
    @staticmethod
    def tabs_for(business_type): return TABS[business_type]
    # ---- setup under two minutes
    def complete_setup_step(s, lynkoid, step):
        if step not in SETUP_STEPS: raise ValueError("unknown setup step")
        done = s.setup_done(lynkoid) | {step}
        s.db.execute("update biz set setup=? where lynkoid=?", (",".join(x for x in SETUP_STEPS if x in done), lynkoid))
        return [x for x in SETUP_STEPS if x not in done]
    def setup_done(s, lynkoid):
        r = s.db.execute("select setup from biz where lynkoid=?", (lynkoid,)).fetchone(); return set(x for x in (r[0] if r else "").split(",") if x)
    def ready_to_sell(s, lynkoid): return set(SETUP_STEPS) <= s.setup_done(lynkoid)
    # ---- shop username: the one rule for every username (core/usernames.py), one owner for ever
    def take_username(s, lynkoid, value, now=None):
        c = username_check(value)
        if not c["ok"]: raise ValueError(c["reason"])
        s.usernames.take(value, lynkoid, "shop", now=now)
        s.db.execute("update biz set username=? where lynkoid=?", (value.lower(), lynkoid))
        return value.lower()
    def shop_page(s, lynkoid):
        r = s.db.execute("select username from biz where lynkoid=?", (lynkoid,)).fetchone()
        return f"shop.lynkomni.com/{r[0]}" if r and r[0] else None
    # ---- receipts by tier (print, QR, message; own design on Max within the brand rules)
    def receipt_channels(s, lynkoid):
        e = billing.Billing(s.p.c).entitlement(lynkoid, "lynkpos")
        return tuple(e.get("receipts", ["print", "qr"]))
    def custom_receipt_allowed(s, lynkoid): return bool(billing.Billing(s.p.c).entitlement(lynkoid, "lynkpos").get("custom_receipts"))
    # ---- second currency beside the sale currency (S7, visitor prices): an estimate at the day's rate, the sale stays local
    def second_currency(s, amount_minor, sale_currency, shown_currency):
        if shown_currency == sale_currency: return None
        return {"amount": s.p.c.fx.convert(amount_minor, sale_currency, shown_currency), "currency": shown_currency, "estimate": True, "sale_currency": sale_currency}
    # ---- low-literacy mode and practice mode
    def set_low_literacy(s, lynkoid, on): s.db.execute("update biz set low_literacy=? where lynkoid=?", (int(bool(on)), lynkoid))
    def low_literacy(s, lynkoid):
        r = s.db.execute("select low_literacy from biz where lynkoid=?", (lynkoid,)).fetchone(); return bool(r and r[0])
    @staticmethod
    def practice_label(practice): return "PRACTICE" if practice else None     # always visible on a training copy; a practice device never syncs
    # ---- fake payment protection: only the provider confirms
    @staticmethod
    def may_show_confirmed(payment_status): return payment_status == "confirmed"
    # ---- sell by voice: a short English parser for the reference; the cashier confirms before the sale is saved
    @staticmethod
    def parse_voice(text, products):
        """"two bags of rice, one soap" -> [(product_id, qty_milli)] for products whose name appears in the phrase. Unknown words are left for the cashier."""
        out, lower = [], text.lower()
        for part in re.split(r",| and ", lower):
            part = part.strip()
            if not part: continue
            m = re.match(r"^(\d+|[a-z]+)\s+(.*)$", part)
            qty, rest = (int(m.group(1)) if m and m.group(1).isdigit() else NUMBER_WORDS.get(m.group(1)) if m else None, m.group(2) if m else part)
            if qty is None: qty, rest = 1, part
            hit = next((p for p in products if p["name"].lower() in rest or rest.endswith(p["name"].lower().rstrip("s"))), None)
            if hit: out.append((hit["id"], qty * 1000))
        return out
    # ---- daily close: one simple message (section 7), from the day's events that reached the cloud
    def day_close(s, lynkoid, day, low_stock=()):
        sales, voided, cash, confirmed, waiting, failed = 0, set(), 0, 0, 0, 0
        for e in s.cloud.of(lynkoid, "SaleVoided"):
            if e["ts"].startswith(day): voided.add(e["payload"]["sale_id"])
        total = 0
        for e in s.cloud.of(lynkoid, "SaleRecorded"):
            if e["ts"].startswith(day) and e["payload"]["sale_id"] not in voided: sales += 1; total += e["payload"]["total"]
        latest = {}
        for e in s.cloud.of(lynkoid, "PaymentRecorded", "PaymentStatusChanged"):
            if not e["ts"].startswith(day): continue
            p = e["payload"]
            if e["type"] == "PaymentRecorded": latest[p["payment_id"]] = (p["sale_id"], p["amount"], p["status"])
            elif p["payment_id"] in latest: sid, amt, _ = latest[p["payment_id"]]; latest[p["payment_id"]] = (sid, amt, p["to_status"])
        for sid, amt, st in latest.values():
            if sid in voided: continue
            if st == "cash_received": cash += amt
            elif st == "confirmed": confirmed += amt
            elif st == "failed": failed += amt
            elif st in ("pending_confirmation",): waiting += amt
        unusual = [f for f in (["failed_payments"] if failed else []) + (["many_voids"] if len(voided) > max(2, sales // 5) else [])]
        return {"day": day, "sales": sales, "total": total, "cash_expected": cash, "confirmed": confirmed, "waiting": waiting, "failed": failed, "low_stock": list(low_stock), "unusual": unusual}
    # ---- data sharing with suppliers (N12 merchant side): one recorded consent per supplier, withdrawable at any time
    def share_with_supplier(s, lynkoid, supplier_id, locns, now=None):
        s.db.execute("insert or replace into biz_share(lynkoid, supplier, locns, granted, withdrawn) values(?,?,?,?,null)", (lynkoid, supplier_id, locns, _now(now)))
    def stop_sharing(s, lynkoid, supplier_id, now=None): s.db.execute("update biz_share set withdrawn=? where lynkoid=? and supplier=?", (_now(now), lynkoid, supplier_id))
    def sharing(s, lynkoid): return [r[0] for r in s.db.execute("select supplier from biz_share where lynkoid=? and withdrawn is null", (lynkoid,))]
    # ---- academy: a course opens beside the screen it teaches
    @staticmethod
    def academy_path(course=None): return "app.lynkomni.com/business/academy" + (f"/{course}" if course else "")
    # ---- LynkStat home cards (the merchant home, section 5)
    @staticmethod
    def home_cards(role, staff_see_profit, pending_sync, low_stock, negative_stock, unread_chats):
        cards = ["today_sales"] + (["today_profit"] if role == "owner" or staff_see_profit else []) + ["new_sale"]
        if low_stock or negative_stock: cards.append("stock_alerts")
        if unread_chats: cards.append("chats")
        cards += ["insight", "pending_sync"] if pending_sync else ["insight"]
        return cards
