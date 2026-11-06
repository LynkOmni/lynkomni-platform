"""Adaptive Locale System: language, number/date formats, local time, mode manager. PRESENTATION ONLY.
Functions, data, identifiers and event types never change with locale."""
import datetime as dt
import textwrap
from decimal import Decimal
from core.money import CURRENCIES
from core.regions import country

# DRAFT translations: every pack needs native-speaker review. Kinyarwanda is pending and falls back to English.
PACKS = {
 "en": {"welcome": "Welcome to LynkOmni", "new_sale": "New sale", "online": "Online", "offline_ok": "Offline: working normally",
        "queued": "Saved on this phone", "pending": "Waiting to send", "sent": "Sent", "delivered": "Delivered", "read": "Read",
        "paid_confirmed": "Paid (confirmed by provider)", "total": "Total", "thanks": "Thank you",
        "not_fiscal": "Not a tax invoice", "debt_reminder": "Reminder: a payment is overdue", "sponsored": "Sponsored", "recovery_started": "A recovery of your LynkOmni account was started. If this was not you, cancel it now.", "recovery_done": "Your LynkOmni account was recovered on a new device. The old device was removed."},
 "fr": {"welcome": "Bienvenue sur LynkOmni", "new_sale": "Nouvelle vente", "online": "En ligne",
        "offline_ok": "Hors ligne : fonctionne normalement", "queued": "Enregistr\u00e9 sur ce t\u00e9l\u00e9phone",
        "pending": "En attente d'envoi", "sent": "Envoy\u00e9", "delivered": "Remis", "read": "Lu",
        "paid_confirmed": "Pay\u00e9 (confirm\u00e9 par le prestataire)", "total": "Total", "thanks": "Merci",
        "not_fiscal": "Ceci n'est pas une facture fiscale", "debt_reminder": "Rappel : un paiement est en retard", "sponsored": "Sponsoris\u00e9", "recovery_started": "Une r\u00e9cup\u00e9ration de votre compte LynkOmni a commenc\u00e9. Si ce n'est pas vous, annulez-la maintenant.", "recovery_done": "Votre compte LynkOmni a \u00e9t\u00e9 r\u00e9cup\u00e9r\u00e9 sur un nouvel appareil. L'ancien appareil a \u00e9t\u00e9 retir\u00e9."},
 "sw": {"welcome": "Karibu LynkOmni", "new_sale": "Mauzo mapya", "online": "Mtandaoni",
        "offline_ok": "Nje ya mtandao: inafanya kazi kawaida", "queued": "Imehifadhiwa kwenye simu hii",
        "pending": "Inasubiri kutumwa", "sent": "Imetumwa", "delivered": "Imefikishwa", "read": "Imesomwa",
        "paid_confirmed": "Imelipwa (imethibitishwa na mtoa huduma)", "total": "Jumla", "thanks": "Asante",
        "not_fiscal": "Hii si ankara ya kodi", "debt_reminder": "Kumbusho: malipo yamechelewa", "sponsored": "Imedhaminiwa", "recovery_started": "Urejeshaji wa akaunti yako ya LynkOmni umeanza. Kama si wewe, ughairi sasa.", "recovery_done": "Akaunti yako ya LynkOmni imerejeshwa kwenye kifaa kipya. Kifaa cha zamani kimeondolewa."},
}
SUPPORTED_UI = {"en", "fr", "sw", "rw"}  # rw: pack pending, so every string falls back to English

def t(lang, key):
    """Per-string fallback to English, then to the key. Never a blank screen or a crash."""
    return PACKS.get(lang, {}).get(key) or PACKS["en"].get(key) or key

def choose_language(explicit=None, saved=None, device=None, country_code=None, supported=SUPPORTED_UI):
    """Priority: explicit choice, saved preference, device language, location suggestion, English."""
    for cand in (explicit, saved, device):
        base = (cand or "").split("-")[0].lower()
        if base in supported:
            return base
    for lang in country(country_code)["languages"]:
        if lang in supported:
            return lang
    return "en"

def format_money(minor, cur, lang="en"):
    d = CURRENCIES[cur]
    s = f"{Decimal(minor) / Decimal(10) ** d:,.{d}f}"
    if lang == "fr":  # French: narrow space groups, comma decimal, code after the number
        return s.replace(",", "\x00").replace(".", ",").replace("\x00", "\u202f") + " " + cur
    return f"{cur} {s}"

_FIXED = {"Africa/Kigali": 2, "Africa/Nairobi": 3, "Africa/Kampala": 3, "Africa/Dar_es_Salaam": 3, "Africa/Lagos": 1,
          "Africa/Accra": 0, "Asia/Kolkata": 5.5, "Asia/Dubai": 4, "UTC": 0}  # fallback if the OS lacks tz data
def _tz(name):
    try:
        from zoneinfo import ZoneInfo
        return ZoneInfo(name)
    except Exception:
        return dt.timezone(dt.timedelta(hours=_FIXED.get(name, 0)))

FMT = "%Y-%m-%dT%H:%M:%SZ"
def local_dt(ts, code=None):
    """Timestamps are stored in UTC and shown in the shop's local time."""
    return dt.datetime.strptime(ts, FMT).replace(tzinfo=dt.timezone.utc).astimezone(_tz(country(code).get("tz", "UTC")))

def in_quiet_hours(ts, code, start=21, end=7):
    h = local_dt(ts, code).hour
    return h >= start or h < end

def receipt_text(p, ts, code, lang="en", width=32, shop="LynkOmni shop", fiscal=False, ad=None):
    """Plain text for 32-column Bluetooth thermal printers."""
    cur, lines = p["currency"], [shop.center(width), local_dt(ts, code).strftime("%d/%m/%Y %H:%M").center(width), "-" * width]
    for i in p["items"]:
        right = format_money(i["qty"] * i["price_minor"], cur, lang)
        lines.append(f"{i['qty']} x {i['sku']}"[:width - len(right) - 1].ljust(width - len(right)) + right)
    tot = format_money(p["total_minor"], cur, lang)
    lines += ["-" * width, t(lang, "total").ljust(width - len(tot)) + tot, t(lang, "thanks").center(width)]
    if not fiscal:
        lines += [x.center(width) for x in textwrap.wrap(t(lang, "not_fiscal"), width)]  # long translations wrap
    if ad and not fiscal:  # never on a fiscal document
        lines += ["-" * width] + [x.center(width) for x in textwrap.wrap(f"{ad['label']}: {ad['text']}", width)]
    return "\n".join(lines)

class ModeManager:
    """Two channels. A weak connection counts as Offline with opportunistic syncing."""
    SLOW_MS = 2000
    def __init__(s): s.forced_offline = False
    def mode(s, reachable, latency_ms=None):
        slow = latency_ms is not None and latency_ms > s.SLOW_MS
        return "offline" if (s.forced_offline or not reachable or slow) else "online"
    def chip(s, mode, pending, lang="en"):
        return t(lang, "online") if mode == "online" and not pending else (
            f"{t(lang, 'online')} \u00b7 {pending} {t(lang, 'pending').lower()}" if mode == "online"
            else f"{t(lang, 'offline_ok')} \u00b7 {pending} {t(lang, 'pending').lower()}")

PACKS["en"]["ad_label"], PACKS["fr"]["ad_label"], PACKS["sw"]["ad_label"] = "Ad", "Pub", "Tangazo"  # DRAFT

PACKS["en"].update(transfer_requested="I've asked the right team to take over. I'm staying with you until they accept.",
                   transfer_accepted="Your conversation is now with {team}. Your history is available, so you won't need to explain it again.",
                   transfer_declined="That team couldn't take it right now. You're still with {agent}.",
                   consent_needed="To look at your account, please allow time-limited support access.")   # other languages fall back per string
