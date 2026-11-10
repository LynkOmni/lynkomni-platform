"""LynkVCard card groups: prepaid, debit and credit on the four faces (MASTER UPDATE, master blueprint section 61; Step 0).

One LynkVCard plan covers three card groups. The tier (EDGE, HUB, CORE, OMNI = Free, Plus, Pro, Max) is the plan and the look;
the group is the kind of money behind the card:

- prepaid (LynkPrima): money loaded in advance, held by the licensed issuer;
- debit (LynkDyna): spends straight from the person's or business's own account at a licensed bank or e-money partner;
- credit (LynkCrest): a credit line from a licensed lender, as a secured card, a charge card or a credit card.

LynkOmni never holds funds, never stores a card number and never decides credit: the issuer, the account partner and the
lender answer every request, and only the cloud records their answer. A request is made online only. The form's details
(load amount, account, income, consent) go to the partner directly and never into an event. Sample faces show placeholder
details that can never work as a real card. Tier limits per group live only in services/billing.py FEATURES.

SANDBOX: SandboxAccountPartner and SandboxLender stand in for the debit account partner and the lender (provider ledger
"card_account_partner" and "card_lender"); the prepaid issuer is services.vcard.SandboxIssuer."""
import re
from services import billing

GROUPS = ("prepaid", "debit", "credit")
NAMES = {"prepaid": "LynkPrima", "debit": "LynkDyna", "credit": "LynkCrest"}
TIER_WORD = {"edge": "Free", "hub": "Plus", "core": "Pro", "omni": "Max"}
TIERS = tuple(TIER_WORD)
CARD_WORD = {"prepaid": "PREPAID", "debit": "DEBIT", "credit": "CREDIT"}
PARTNER = {"prepaid": "issuer", "debit": "account_partner", "credit": "lender"}
CREDIT_KINDS = ("secured", "charge", "credit")
LENDER_NOTE_KEY = "card_lender_terms"           # \"the lender's interest and fees apply\", shown beside every LynkCrest name

SAMPLE = {"number": "1234 5678 9012 3456", "expiry": "MM/YY", "holder": "CARD HOLDER", "code": "000", "sample_word": "SAMPLE"}

FORM = {
    "prepaid": ("holder", "form", "first_load", "limits"),
    "debit": ("holder", "form", "account", "limits"),
    "credit": ("holder", "form", "credit_kind", "limit_asked", "income", "credit_check_consent", "records_consent"),
}


def luhn_ok(number):
    d = re.sub(r"\D", "", number)
    if not 12 <= len(d) <= 19:
        return False
    s, alt = 0, False
    for c in reversed(d):
        n = int(c)
        if alt:
            n = n * 2 - 9 if n * 2 > 9 else n * 2
        s, alt = s + n, not alt
    return s % 10 == 0


def looks_like_a_network_number(number):
    """Starts the way Visa (4) or Mastercard (51-55, 2221-2720) numbers start."""
    d = re.sub(r"\D", "", number)
    return d.startswith("4") or 51 <= int(d[:2]) <= 55 or 2221 <= int(d[:4]) <= 2720


def plan_name(group, tier):
    """For example 'LynkDyna Pro'. Names stay the same in every language."""
    return f"{NAMES[group]} {TIER_WORD[tier]}"


def tier_rules(tier):
    return billing.FEATURES["lynkvcard"][TIERS.index(tier)]


def allowed(group, tier, credit_kind=None, physical=False):
    """What the tier allows for the group. The lender may still say no: this only says what may be asked for."""
    f = tier_rules(tier)
    if group not in f["card_groups"]:
        return {"ok": False, "reason": "group_not_on_tier"}
    if group == "credit":
        if credit_kind not in CREDIT_KINDS:
            return {"ok": False, "reason": "choose_credit_kind"}
        if credit_kind not in f["credit_kinds"]:
            return {"ok": False, "reason": "credit_kind_not_on_tier"}
    if physical and group not in f["physical_groups"]:
        return {"ok": False, "reason": "physical_not_on_tier"}
    return {"ok": True, "physical_fee": "issuer" if physical and not f.get("physical_included") else None}


def request(group, tier, form, holder, online, partner_ready, request_id, credit_kind=None, identity_check_id=None):
    """The device side of 'Get a card': checks what can be checked here and returns the CardRequested payload. Never offline,
    never before the partner is signed in the country; the card exists only when the partner answers."""
    if not online:
        raise PermissionError("a card request needs the network and the licensed partner")
    if not partner_ready:
        return {"state": "coming_soon"}
    a = allowed(group, tier, credit_kind, physical=(form == "physical"))
    if not a["ok"]:
        return {"state": "refused", "reason": a["reason"]}
    payload = {"request_id": request_id, "card_group": group, "tier": tier, "form": form, "holder": holder}
    if credit_kind:
        payload["credit_kind"] = credit_kind
    if identity_check_id:
        payload["identity_check_id"] = identity_check_id
    return {"state": "sent", "event": ("CardRequested", payload)}


def partner_answer(request_id, group, answer, card_id=None, credit_limit=None, currency=None):
    """Cloud only: turns the partner's answer into CardRequestConfirmed or CardRequestFailed."""
    if answer.get("ok"):
        p = {"request_id": request_id, "card_id": card_id, "partner_kind": PARTNER[group]}
        if group == "credit" and credit_limit is not None:
            if not isinstance(credit_limit, int) or currency is None:
                raise ValueError("a credit limit is an integer amount with its currency")
            p.update(credit_limit=credit_limit, currency=currency)
        return ("CardRequestConfirmed", p)
    return ("CardRequestFailed", {"request_id": request_id, "reason": answer.get("reason", "partner_declined")})


class SandboxAccountPartner:
    """SANDBOX: the bank or e-money partner that holds a debit card's account. Declines when the identity is not confirmed."""
    def open_card(self, identity_confirmed):
        return {"ok": True} if identity_confirmed else {"ok": False, "reason": "identity_not_confirmed"}


class SandboxLender:
    """SANDBOX: the licensed lender. It alone decides; a secured card needs the deposit received by the lender, never LynkOmni."""
    def decide(self, credit_kind, identity_confirmed, credit_check_consent, deposit_received=False, asked_limit=0):
        if not identity_confirmed:
            return {"ok": False, "reason": "identity_not_confirmed"}
        if not credit_check_consent:
            return {"ok": False, "reason": "partner_declined"}
        if credit_kind == "secured" and not deposit_received:
            return {"ok": False, "reason": "deposit_not_received"}
        return {"ok": True, "limit": min(int(asked_limit), 50_000) if credit_kind != "charge" else None}
