"""Sign-up, sign-in, the ways to prove it's you, the account protections, the Can't sign in? hub and every reset (section 4C
points 3 and 5, master blueprint section 87): the rules only, read from catalog/ways-in.v1.json. The account service that
uses them is identity/account.py; ts/src/waysin.ts is the TypeScript port and contract/vectors/ways-in.v1.json keeps the two
the same (python3 tools/waysin_vectors.py after a change). LynkOmni has no passwords and uses no outside company here."""
import json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
with open(os.path.join(ROOT, "catalog", "ways-in.v1.json"), encoding="utf-8") as f:
    W = json.load(f)
SIGN_UP, BASIC, SIGN_IN, OFFLINE = W["sign_up"], W["basic_phone_sign_up"], W["sign_in"], W["offline_sign_in"]
WAYS = {w["id"]: w for w in W["ways"]}
PROTECT, RECOVERY = W["protections"], W["recovery"]
RESETS = {r["what"]: r for r in W["resets"]}
HOUR, DAY = 3600, 86400


# ---- sign-up ------------------------------------------------------------------------------------------------------------
def sign_up_next(done):
    """The next sign-up step after the steps already done (in the fixed order), or None when every step is done."""
    for s in SIGN_UP["steps"]:
        if s not in done:
            return s
    return None


def may_start_sign_up(online, device_hour, network_hour):
    """Sign-up is online only and limited per device and per network each hour; no picture puzzles. Returns (ok, why)."""
    if not online:
        return False, SIGN_UP["offline_says"]
    if device_hour >= SIGN_UP["abuse"]["per_device_hour"]:
        return False, "device_limit"
    if network_hour >= SIGN_UP["abuse"]["per_network_hour"]:
        return False, "network_limit"
    return True, None


def _leap(y):
    return y % 4 == 0 and (y % 100 != 0 or y % 400 == 0)


def _days_in(y, m):
    return 29 if m == 2 and _leap(y) else (31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)[m - 1]


def age_check(year, month, day, today, min_age):
    """The neutral age gate (owner approved 2026-11-26): the person types a birth date without being told the age needed and
    the device works out "adult" or "under" against min_age (18 or the country's higher age); the date is then forgotten and
    only adult yes and the day it was checked are kept. "no_such_date" for a date that does not exist, lies in the future or
    is more than oldest_years ago. today is (year, month, day). A 29 February birthday counts from 1 March in other years."""
    A = SIGN_UP["age"]
    ty, tm, td = today
    if not all(isinstance(x, int) and not isinstance(x, bool) for x in (year, month, day)):
        return "no_such_date"
    if not (1 <= month <= 12) or not (1 <= day <= _days_in(year, month)) or year < 1:
        return "no_such_date"
    if (year, month, day) > (ty, tm, td) or ty - year > A["oldest_years"]:
        return "no_such_date"
    bm, bd = (3, 1) if (month, day) == (2, 29) and not _leap(ty) else (month, day)
    age = ty - year - (1 if (tm, td) < (bm, bd) else 0)
    return "adult" if age >= min_age else "under"


def age_blocked(refused_at, cleared_at=None):
    """True while someone who came out under age is blocked on that device, network or number. There is no retry by
    retyping and no wait that ends by itself: only the licensed partner's ID check clears it (cleared after the refusal)."""
    return refused_at is not None and (cleared_at is None or cleared_at < refused_at)


def legal_name_problem(name):
    """None when the legal name (as on the ID document) is acceptable, else why. Kept apart from the display name."""
    n = " ".join((name or "").split())
    if len(n) < SIGN_UP["legal_name"]["min"]:
        return "too_short"
    if len(n) > SIGN_UP["legal_name"]["max"]:
        return "too_long"
    if any(ch.isdecimal() for ch in n):
        return "no_digits"
    return None


def basic_phone_allows(act, has_email):
    """An account opened on a basic phone (phone number and PIN only) is limited until an email is added."""
    return has_email or act not in BASIC["limited"]


# ---- sign-in ------------------------------------------------------------------------------------------------------------
def identifier_kind(text):
    """username, email or phone, read from what the person typed (the same box takes all three)."""
    t = (text or "").strip()
    if "@" in t:
        return "email"
    digits = sum(ch.isdecimal() for ch in t)
    if t.startswith("+") or (digits >= 6 and digits >= len(t.replace(" ", "")) - 1):
        return "phone"
    return "username"


def sign_in_ways(has, strongest=False):
    """The ways this person can sign in with, strongest first; strongest protection mode keeps only passkeys and keys.
    Codes by email or text come last and never alone open a new device (an extra check follows)."""
    order = [w for w in W["ways"] if w["kind"] in ("sign_in", "code") and w["id"] in has]
    if any(w["id"] in W["free_first"]["free_ways"] for w in order):
        order = [w for w in order if w["id"] != "text_code"]    # a text code only when no free way exists (owner, 2026-11-26)
    if strongest:
        order = [w for w in order if w["id"] in PROTECT["strongest_mode"]["only"]]
    return [w["id"] for w in sorted(order, key=lambda w: -w["strength"])]


def extra_checks(has):
    """The extra checks a person has turned on, strongest first."""
    return [w["id"] for w in sorted((w for w in W["ways"] if w["kind"] == "extra" and w["id"] in has), key=lambda w: -w["strength"])]


def code_valid(sent_at, now, asking_device, device):
    """A code by email or text lasts 5 minutes and only works on the device that asked for it."""
    c = SIGN_IN["codes"]
    return now - sent_at <= c["lifetime_s"] and (not c["only_asking_device"] or asking_device == device)


def offline_sign_in(known_device, role, days_offline):
    """Offline sign-in only on a device already signed in online with that account, within its role's days. (ok, why)"""
    if not known_device:
        return False, "sign_in_online_first"
    if days_offline > OFFLINE["back_online_days"].get(role, 7):
        return False, "go_online"
    return True, None


# ---- protections --------------------------------------------------------------------------------------------------------
def unusual(history, attempt, tries=0):
    """Why a sign-in looks unusual: a new country, a journey too fast between two countries, or many tries. history is a
    list of {country, at} of earlier sign-ins, attempt the new one. Places are countries only, never positions."""
    u = PROTECT["unusual"]
    out = []
    seen = {h["country"] for h in history}
    if history and attempt["country"] not in seen:
        out.append("new_country")
    last = max(history, key=lambda h: h["at"]) if history else None
    if last and last["country"] != attempt["country"] and attempt["at"] - last["at"] < u["journey_hours"] * HOUR:
        out.append("impossible_journey")
    if tries >= u["many_tries"]:
        out.append("many_tries")
    return out


def country_allowed(lock, country):
    """The optional country lock: an empty lock allows every country."""
    return not lock or country in lock


def old_device(last_used, now):
    """A device unused for 90 days is signed out."""
    return now - last_used >= PROTECT["old_devices_days"] * DAY


def session_hours(remember):
    """Remember this device keeps the session for 30 days; otherwise 12 hours (shared computers)."""
    r = PROTECT["remember_device"]
    return r["remembered_days"] * 24 if remember else r["not_remembered_hours"]


def anti_phishing_problem(word):
    w = (word or "").strip()
    a = PROTECT["anti_phishing_word"]
    if len(w) < a["min"]:
        return "too_short"
    if len(w) > a["max"]:
        return "too_long"
    return None


def backup_codes_left_note(left):
    """'make_new' once only remind_at or fewer codes are left, 'none_left' at zero, else None."""
    if left <= 0:
        return "none_left"
    return "make_new" if left <= W["backup_codes"]["remind_at"] else None


def checkup(have):
    """The security checkup: every item still missing, in the register's order, each with its fix."""
    return [i for i in PROTECT["checkup"]["items"] if not have.get(i)]


# ---- recovery -----------------------------------------------------------------------------------------------------------
def recovery_ways(has):
    """The ways back in this person actually has, strongest first, each with its wait in hours."""
    return [dict(w) for w in RECOVERY["ways"] if w["id"] in has]


def never_allowed(way):
    return way in RECOVERY["never"]


def restricted(act, recovered_at, now):
    """For 24 hours after a recovery: no payouts, payout changes, downloads, card changes or contact changes."""
    return recovered_at is not None and act in RECOVERY["restricted"] and now - recovered_at < RECOVERY["restricted_h"] * HOUR


def contacts_confirmed(confirmations, contacts):
    """Recovery contacts: enough different people on the person's own list have confirmed."""
    ok = {c for c in confirmations if c in contacts}
    return len(ok) >= W["recovery_contacts"]["confirm_min"]


def contacts_problem(contacts):
    n = len(set(contacts))
    rc = W["recovery_contacts"]
    if n < rc["min"]:
        return "too_few"
    if n > rc["max"]:
        return "too_many"
    return None


def to_strongest(failed):
    """Repeated failed recovery attempts move the account into the strongest protection mode for a time."""
    return failed >= RECOVERY["failed_attempts_to_strongest"]


# ---- resets -------------------------------------------------------------------------------------------------------------
def may_reset(what, by, own=False, online=True):
    """Who may reset what, online or offline. by is self, owner, manager, shop, agent_point, card_issuer, key_owner,
    another_admin, lynkomni_staff_with_agreement, successor or election_rules. Returns (ok, why)."""
    r = RESETS.get(what)
    if r is None:
        return False, "unknown"
    if r.get("never"):
        return False, "never"
    if by not in r["who"]:
        return False, "not_allowed"
    if r.get("never_own") and own:
        return False, "not_own"
    if not online and r["where"] == "online":
        return False, "go_online"
    return True, None


# ---- point 4: the phone owner check (only where deep identity is needed) -----------------------------------------------
OWNER = W["phone_owner"]


def owner_check_needed(activity):
    """Only the activities in the register need the real owner of the number; everyday use never does."""
    return activity in OWNER["activities"]


def owner_payer(activity):
    """Who pays for the check: "partner" (the licensed partner's own identity check, at its own cost) or "requester" (the one who
    asks for it). Never LynkOmni and never the person being checked (owner, 2026-11-26)."""
    return OWNER["payers"][activity]


def owner_check_method(network_ready, business=False, registered_name_supported=False, payer="requester"):
    """Which check applies: for a partner's service, the partner's own identity check; otherwise the mobile network where it offers
    the check (a business by its registered name where supported), else the identity partner's ID document check (for a business,
    the owner's own), paid by the one who asks."""
    if payer == "partner":
        return "partner"
    if network_ready and (not business or registered_name_supported):
        return "registered_name" if business else "network"
    return "owner_id_document" if business else "id_document"


def owner_check_outcome(answer, sim_changed_at, now):
    """What the network's answer means. A recent SIM change makes the activity wait, whatever the answer.
    Returns {"result": go | fix | stop | wait, "fixes": [...], "until": time or None}."""
    wait = OWNER["sim_swap_wait_hours"] * HOUR
    if sim_changed_at is not None and now - sim_changed_at < wait:
        return {"result": "wait", "fixes": [], "until": sim_changed_at + wait}
    result = OWNER["answers"].get(answer)
    if result is None:
        raise ValueError("unknown answer")
    fixes = OWNER["partial_fixes"] if result == "fix" else OWNER["no_match_fixes"] if result == "stop" else []
    return {"result": result, "fixes": list(fixes), "until": None}


def owner_match_valid(matched_at, now, number_changed=False, sim_changed_at=None):
    """A match is kept for a time for the same number; a new number or a SIM change since the match asks again."""
    if matched_at is None or number_changed:
        return False
    if sim_changed_at is not None and sim_changed_at > matched_at:
        return False
    return now - matched_at < OWNER["match_valid_days"] * DAY
