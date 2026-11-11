"""LynkSurvey rules (LynkS, NEW UPDATE 4, owner locked 2026-11-11, master blueprint section 63). The Python reference;
ts/src/survey.ts must agree on contract/vectors/people.v1.json (run python3 tools/people_vectors.py after a change).

One person, one answer under one of four rules; anonymous means anonymous (results are never shown for a group of fewer than 5);
"Real answers only" flags answers for the manager without ever deleting them; "How many people do I need?" and "How sure are we?"
use the world-standard formulas at 95% confidence, shown in plain words."""
import math

RULES = ("open", "one_per_phone", "invited", "verified")
MIN_GROUP = 5                    # never show a result for fewer than 5 people
Z95 = 1.96
SECONDS_PER_QUESTION_MIN = 2     # faster than this is "too fast to be read"
PERSONAL_DEVICE_DAILY_MAX = 3    # more answers than this from one personal device in a day is "Please check" (kiosks and field devices are exempt)
REMINDERS_MAX = 2
DEFAULT_REST_DAYS = 30


def sample_size(margin_percent, population=None):
    """How many answers are needed for results within +/- margin_percent at 95% confidence (the most careful 50/50 case),
    with the finite-population correction when the population is known: 5% gives 385."""
    e = margin_percent / 100
    n0 = Z95 * Z95 * 0.25 / (e * e)
    if population:
        n0 = n0 / (1 + (n0 - 1) / population)
    return math.ceil(math.floor(n0 * 1e6 + 0.5) / 1e6)   # rounded first so 384.16000000001 and 384.16 agree everywhere


def margin(share_percent, answers):
    """The margin, in tenths of a percent, of a result: 54% from 600 answers is +/- 4.0% (shown as "54% (±4%)")."""
    if answers < 1:
        return None
    p = share_percent / 100
    return math.floor(Z95 * math.sqrt(p * (1 - p) / answers) * 1000 + 0.5)      # half up, the same in every language


def can_show(group_size):
    """Results for a group are shown only from 5 people up, at every level and in every research tool."""
    return group_size >= MIN_GROUP


def may_answer(rule, already_answered, has_invite=False, signed_in=False, phone_confirmed=False):
    """One person, one answer. Returns None when the answer may be given, or the reason it may not."""
    if rule not in RULES:
        raise ValueError(f"{rule} is not a rule")
    if already_answered:
        return "already_answered"
    if rule == "one_per_phone" and not phone_confirmed:
        return "confirm_phone_first"
    if rule == "invited" and not has_invite:
        return "invitation_needed"
    if rule == "verified" and not signed_in:
        return "sign_in_needed"
    return None


def real_answer_flags(seconds, questions, same_choice_every_time, answers_today_from_device, shared_device):
    """The "Real answers only" check: reasons to keep an answer apart until the manager decides (never deleted, never an accusation)."""
    out = []
    if questions > 0 and seconds < questions * SECONDS_PER_QUESTION_MIN:
        out.append("too_fast")
    if same_choice_every_time and questions >= 5:
        out.append("same_pattern")
    if not shared_device and answers_today_from_device > PERSONAL_DEVICE_DAILY_MAX:
        out.append("many_from_one_device")
    return out


def group_open(group, counts, targets):
    """Groups to fill: a person from a group that is already full is thanked and the survey closes for them."""
    t = targets.get(group)
    return t is None or counts.get(group, 0) < t


def may_ask_again(days_since_last, rest_days=DEFAULT_REST_DAYS, opted_out=False):
    """The rest period, and Don't ask me again (respected straight away)."""
    return not opted_out and (days_since_last is None or days_since_last >= rest_days)
