"""LynkSurvey, the cloud side (LynkS; master blueprint section 63; build section 3B).

One system controls everything: it builds the survey (by hand, from the library or "Write it for me"), checks every question for
clarity, keeps versions (a question changed after answers arrived makes a new version, so answers are never mixed), sends it for
approval where the organisation wants that, opens it, takes answers from every way (link, website, WhatsApp, LynkChat, basic phone,
voice call, LynkKiosk, LynkPOS, email, field interviews and paper), checks "one person, one answer" and "Real answers only", and
turns the answers into results with their margins, the research tools, call back tasks, "You said, we did", rewards, the LynkSurvey
Panel and verified results anyone can check.

Anonymous really means anonymous: the check of one person, one answer is done here, then the link to the person is dropped; no
result is ever shown for fewer than 5 people, at any level and in any tool. A phone number is kept only in the PII vault, by
reference, and is removed after 30 days. No event carries a name, a phone number or a person's answers to a sensitive question
outside the answer itself. The devices only follow: a kiosk, phone or screen never decides anything on its own."""
import csv, hashlib, hmac, io, json, math, re, secrets, time

from contract.tools.validate_contract import uuid4
from core import surveys as R
from services import billing

DAY = 86400
CONTACT_KEPT_DAYS = 30
REMINDER_EVERY_DAYS = 3
UNHAPPY_BURST = 3                     # 3 unhappy answers in an hour at one place: an alert for the manager
UNHAPPY_WINDOW_S = 3600
CALL_BACK_HOURS = 48
KINDS = ("quick_rating", "satisfaction", "recommend", "staff_pulse", "staff_journey", "poll", "event_feedback", "research", "consultation",
         "what_matters_most", "trade_off", "form")
QTYPES = ("choice", "many", "yes_no", "stars", "rating", "score", "number", "date", "short", "long", "ranking", "spoken", "best_worst", "offer_pick")
BASIC_QTYPES = ("choice", "yes_no", "stars", "rating", "score", "short")          # LynkSurvey Free: "basic" logic and question types
WAYS = ("smartphone", "website", "whatsapp", "lynkchat", "basic_phone", "voice", "kiosk", "pos", "email", "field", "paper")
DEVICE_WAYS = ("kiosk", "pos", "field", "paper")                                    # answered on an added device, also offline
SHARED_WAYS = ("kiosk", "pos", "field", "paper")                                    # many people answer on one device: never "many from one device"
WAY_FEATURE = {"whatsapp": "whatsapp_and_chat", "lynkchat": "whatsapp_and_chat", "basic_phone": "basic_phone", "field": "field_and_paper", "paper": "field_and_paper", "voice": "voice_call"}
PARTNER_WAYS = {"whatsapp": "people_messages", "basic_phone": "people_messages", "voice": "survey_voice"}
ROLES = ("owner", "manager", "creator", "approver", "viewer", "field_worker")
BUILDERS = ("owner", "manager", "creator")
SEES_ALL = ("owner", "manager")
LEVELS = ("head_office", "country", "region", "branch", "department")
STATES = ("draft", "waiting_for_approval", "sent_back", "approved", "open", "paused", "closed", "test")
UNHAPPY = {"rating": 2, "stars": 2, "score": 6}                                     # at or below: an unhappy answer
LEADING = ("don't you agree", "dont you agree", "do you agree that our", "isn't it", "wouldn't you", "surely", "how great", "how much do you love", "don't you think")
SENSITIVE = ("health", "illness", "disease", "religion", "faith", "church", "mosque", "politic", "party", "vote", "sexual", "ethnic", "tribe", "income", "salary")
LONG_QUESTION = 140
AFTER = ("lynkpos", "lynkqueue", "lynkchat", "lynkattend", "lynkinv", "delivery", "booking", "support", "api")   # "Automatic surveys at the right moment"
RESEARCH_KINDS = {"what_matters_most": "what_matters_most", "trade_off": "trade_off"}


def _now(n): return time.time() if n is None else n
def _day(n): return int(n // DAY)


class Survey:
    def __init__(s, cloud, platform, notifier=None, messages=None, voice=None, rewards=None):
        s.cloud, s.p, s.db, s.vault = cloud, platform, platform.c.store.db, platform.vault
        s.n, s.partner, s.voice, s.rewards = notifier, messages, voice, rewards
        s.key = secrets.token_hex(16)                                          # marks for "one per phone" are keyed, never the number itself
        s.db.executescript("""
        create table if not exists sv_roles(merchant text, person text, role text, place text, primary key(merchant, person, role));
        create table if not exists sv_settings(merchant text primary key, approval int, country text);
        create table if not exists sv_places(place_id text primary key, merchant text, parent text, level text, country text);
        create table if not exists sv_surveys(survey_id text primary key, merchant text, place text, kind text, rule text, anonymous int, languages text, version int,
          state text, by text, created real, rest_days int, repeat_days int, rounds int, targets text, group_q text, sensitive int, opened real, sent_back_note text, library int, after text);
        create table if not exists sv_versions(survey_id text, version int, questions text, logic text, at real, primary key(survey_id, version));
        create table if not exists sv_invites(code_hash text primary key, survey_id text, person text, contact_ref text, used int, reminders int, last_at real);
        create table if not exists sv_phone(survey_id text, mark text, contact_ref text, code_hash text, until real, confirmed int, primary key(survey_id, mark));
        create table if not exists sv_answers(answer_id text primary key, merchant text, survey_id text, version int, way text, place text, grp text, answers text, result text,
          reason text, test int, person text, contact_ref text, call_back_ok int, at real, deleted int, entered_by text, device text, language text);
        create table if not exists sv_marks(survey_id text, mark text, primary key(survey_id, mark));
        create table if not exists sv_device_day(device text, day int, n int, primary key(device, day));
        create table if not exists sv_devices(device_id text primary key, merchant text, place text, kind text, locked int);
        create table if not exists sv_seen(event_id text primary key);
        create table if not exists sv_tasks(task_id text primary key, merchant text, answer_id text, assignee text, state text, due real, done_at real, done_by text);
        create table if not exists sv_rewards(reward_id text primary key, merchant text, survey_id text, answer_id text, person text, kind text, amount int, currency text, state text);
        create table if not exists sv_panel(member_ref text primary key, person text, country text, age_range text, language text, topics text, owns_business int, joined real);
        create table if not exists sv_optout(person text, merchant text, primary key(person, merchant));
        create table if not exists sv_asked(person text, merchant text, at real, primary key(person, merchant));
        create table if not exists sv_history(merchant text, at real, by text, what text, survey text);
        create table if not exists sv_verified(digest text primary key, survey_id text, version int, counts text, method text, at real);
        create table if not exists sv_said(survey_id text, text text, at real, told int);
        create table if not exists sv_alerts(place text, hour int, primary key(place, hour));""")

    # ---- small helpers
    def _ent(s, merchant): return billing.Billing(s.p.c).entitlement(merchant, "lynksurvey")
    def _log(s, merchant, by, what, survey=None, now=None): s.db.execute("insert into sv_history values(?,?,?,?,?)", (merchant, _now(now), by, what, survey))
    def _roles(s, merchant, person): return {r[0] for r in s.db.execute("select role from sv_roles where merchant=? and person=?", (merchant, person))}
    def _need(s, merchant, person, roles):
        if not s._roles(merchant, person) & set(roles): raise PermissionError("not_allowed_for_this_role")
    def _tell(s, kind, person, event_id, now, record=None, business=None, role=None, facts=None, lang="en"):
        if s.n: return s.n.notify(kind, person, event_id, _now(now), facts=facts, record=record, business=business, role=role, lang=lang)
    def _sv(s, survey):
        r = s.db.execute("select merchant, place, kind, rule, anonymous, languages, version, state, by, rest_days, repeat_days, rounds, targets, group_q, sensitive, opened, library from sv_surveys where survey_id=?", (survey,)).fetchone()
        if not r: raise KeyError("no such survey")
        d = dict(zip(("merchant", "place", "kind", "rule", "anonymous", "languages", "version", "state", "by", "rest_days", "repeat_days", "rounds", "targets", "group_q", "sensitive", "opened", "library"), r))
        d["languages"], d["targets"], d["anonymous"], d["sensitive"] = json.loads(d["languages"]), json.loads(d["targets"] or "{}"), bool(d["anonymous"]), bool(d["sensitive"])
        return d
    def questions(s, survey, version=None):
        v = version or s._sv(survey)["version"]
        r = s.db.execute("select questions, logic from sv_versions where survey_id=? and version=?", (survey, v)).fetchone()
        return {"questions": json.loads(r[0]), "logic": json.loads(r[1])}
    def _country(s, merchant):
        r = s.db.execute("select country from sv_settings where merchant=?", (merchant,)).fetchone(); return (r and r[0]) or "CM"
    def _mark(s, survey, contact): return hmac.new(s.key.encode(), f"{survey}:{contact}".encode(), hashlib.sha256).hexdigest()
    def _hash(s, code): return hashlib.sha256(f"sv:{code}".encode()).hexdigest()

    # ---- setting up: roles, places (the organisation tree), settings, devices
    def add_role(s, merchant, person, role, by=None, place=None, now=None):
        """The owner, managers, creators, approvers, viewers and field workers. Only creators who built or sent a survey in a month count."""
        if role not in ROLES: raise ValueError("unknown role")
        if by is not None: s._need(merchant, by, SEES_ALL)
        s.db.execute("insert or replace into sv_roles values(?,?,?,?)", (merchant, person, role, place))
        s._log(merchant, by or person, f"role_{role}", now=now); s.db.commit()
    def settings(s, merchant, by, approval=None, country=None):
        s._need(merchant, by, SEES_ALL)
        if approval and not s._ent(merchant)["approval"]: raise PermissionError("plan_no_approval")
        old = s.db.execute("select approval, country from sv_settings where merchant=?", (merchant,)).fetchone() or (0, None)
        s.db.execute("insert or replace into sv_settings values(?,?,?)", (merchant, int(bool(approval)) if approval is not None else old[0], country or old[1])); s.db.commit()
    def add_place(s, merchant, by, level="branch", parent=None, country=None, now=None):
        """A place in the organisation tree: head office, countries, regions, branches, departments (only the levels the plan has)."""
        s._need(merchant, by, SEES_ALL); ent = s._ent(merchant)
        if level not in LEVELS: raise ValueError("unknown level")
        have = s.db.execute("select count(*) from sv_places where merchant=? and level in ('branch','department')", (merchant,)).fetchone()[0]
        if level == "branch" and ent["places"] is not None and have >= ent["places"]: raise PermissionError("plan_limit_places")
        tree = ent.get("org_tree")
        if level in ("head_office", "country", "region") and tree != "full": raise PermissionError("plan_no_organisation_tree")
        if level == "department" and tree not in ("branches_departments", "full"): raise PermissionError("plan_no_organisation_tree")
        if level == "country" and parent and s.db.execute("select count(*) from sv_places where merchant=? and level='country'", (merchant,)).fetchone()[0] >= 1 and not ent.get("several_countries"):
            raise PermissionError("plan_one_country")
        pid = uuid4(); s.db.execute("insert into sv_places values(?,?,?,?,?)", (pid, merchant, parent, level, country))
        s._log(merchant, by, f"place_{level}", now=now); s.db.commit(); return pid
    def _below(s, place):
        """A place and every place under it: results add up the tree."""
        out, todo = [], [place]
        while todo:
            p = todo.pop(); out.append(p); todo += [r[0] for r in s.db.execute("select place_id from sv_places where parent=?", (p,))]
        return out
    def _sees(s, merchant, person):
        """Which places a person may see: owners and managers everything; everyone else the place they were given and below."""
        if s._roles(merchant, person) & set(SEES_ALL): return None
        r = s.db.execute("select place from sv_roles where merchant=? and person=? and place is not null", (merchant, person)).fetchall()
        if not r and s._roles(merchant, person) & {"creator"}: return "own"
        return sorted({x for row in r for x in s._below(row[0])})
    def add_device(s, merchant, place, device_id, kind, by, now=None):
        """Only added devices collect answers at the place (LynkKiosk, LynkTab, LynkPOS, a field worker's LynkMobile)."""
        s._need(merchant, by, SEES_ALL)
        if kind not in ("kiosk", "tablet", "pos", "field", "screen", "counter_display", "button_stand", "printer", "scanner", "speaker"): raise ValueError("unknown device")
        if kind in ("button_stand", "printer", "scanner", "speaker") and not s._ent(merchant)["own_hardware"]: raise PermissionError("plan_no_hardware_without_display")
        s.db.execute("insert or replace into sv_devices values(?,?,?,?,0)", (device_id, merchant, place, kind)); s._log(merchant, by, f"device_{kind}", now=now); s.db.commit()
    def device_pack(s, device_id):
        """What an added device is given: the open surveys of its place (questions included, so answering works offline) and the
        ways it may record. A locked device gets nothing more."""
        r = s.db.execute("select merchant, place, kind, locked from sv_devices where device_id=?", (device_id,)).fetchone()
        if not r: return None
        merchant, place, kind, locked = r; ent = s._ent(merchant)
        ways = {"kiosk": ["kiosk"], "tablet": ["kiosk", "field", "paper"], "pos": ["pos"], "field": ["field"]}.get(kind, [])
        ways = [w for w in ways if not WAY_FEATURE.get(w) or ent[WAY_FEATURE[w]]]
        out = []
        for sid, v, state in s.db.execute("select survey_id, version, state from sv_surveys where merchant=? and state in ('open','test') and (place is null or place=?)", (merchant, place)).fetchall():
            out.append({"survey_id": sid, "version": v, "state": state, "questions": s.questions(sid, v)["questions"]})
        return {"device_id": device_id, "place": place, "kind": kind, "locked": bool(locked), "ways": ways, "surveys": [] if locked else out}
    def lock_device(s, merchant, device_id, by, now=None):
        s._need(merchant, by, SEES_ALL); s.db.execute("update sv_devices set locked=1 where device_id=? and merchant=?", (device_id, merchant)); s._log(merchant, by, "device_locked", now=now); s.db.commit()

    # ---- building
    @staticmethod
    def check_questions(questions):
        """The clear question check: confusing, too long, two questions in one, or pushing people towards an answer, with a fair version.
        Sensitive topics are flagged so the person's clear agreement is asked first."""
        out = []
        for q in questions:
            text, low = q.get("text", ""), q.get("text", "").lower()
            if any(w in low for w in LEADING):
                fair = re.sub(r"^(don'?t you (agree|think) (that )?|do you agree that |surely |isn'?t it )", "", low).rstrip("?").strip()
                out.append({"q": q["id"], "problem": "pushes_towards_an_answer", "suggestion": f"How would you rate {fair.replace('our ', 'our ').replace(' is great', '').strip()}?"})
            if len(text) > LONG_QUESTION: out.append({"q": q["id"], "problem": "too_long", "suggestion": None})
            if text.count("?") > 1 or (" and " in low and q.get("type") in ("rating", "stars", "score", "yes_no")): out.append({"q": q["id"], "problem": "two_questions_in_one", "suggestion": None})
            if any(w in low for w in SENSITIVE): out.append({"q": q["id"], "problem": "sensitive_topic", "suggestion": None})
        return out
    def _valid(s, merchant, kind, questions, logic):
        ent = s._ent(merchant)
        if kind not in KINDS: raise ValueError("unknown kind")
        if kind == "staff_journey" and not ent["staff_journey"]: raise PermissionError("plan_no_staff_journey")
        if kind in RESEARCH_KINDS and RESEARCH_KINDS[kind] not in ent["research"]: raise PermissionError(f"plan_no_{kind}")
        if not questions: raise ValueError("a survey needs a question")
        ids = set()
        for q in questions:
            if q.get("type") not in QTYPES: raise ValueError(f"unknown question type {q.get('type')}")
            if ent["logic"] == "basic" and q["type"] not in BASIC_QTYPES: raise PermissionError("plan_basic_question_types")
            if not re.fullmatch(r"[a-z0-9_]{1,64}", q.get("id", "")) or q["id"] in ids: raise ValueError("each question needs its own short id")
            ids.add(q["id"])
        for rule in logic or []:
            if ent["logic"] == "basic": raise PermissionError("plan_basic_logic")
            if rule.get("if") not in ids or rule.get("show") not in ids: raise ValueError("logic must point at questions of this survey")
    def create(s, merchant, by, kind, questions, rule="open", anonymous=False, languages=("en",), place=None, logic=None, targets=None, group_q=None,
               rest_days=R.DEFAULT_REST_DAYS, repeat_days=None, after=None, now=None):
        s._need(merchant, by, BUILDERS)
        if rule not in R.RULES: raise ValueError("unknown rule")
        s._valid(merchant, kind, questions, logic); ent = s._ent(merchant)
        if targets and "groups_to_fill" not in ent["research"]: raise PermissionError("plan_no_groups_to_fill")
        if repeat_days and not ent["repeating"]: raise PermissionError("plan_no_repeating")
        if after is not None and after not in AFTER: raise ValueError("unknown moment")
        if after is not None and not s._may_follow(ent, after): raise PermissionError("plan_no_automatic_survey")
        from services.translation import languages as _langs
        if any(l not in _langs() for l in languages): raise ValueError("unknown language")
        sid, n = uuid4(), _now(now)
        sensitive = any(c["problem"] == "sensitive_topic" for c in s.check_questions(questions))
        s.db.execute("insert into sv_surveys values(?,?,?,?,?,?,?,1,'draft',?,?,?,?,0,?,?,?,null,null,0,?)", (sid, merchant, place, kind, rule, int(bool(anonymous)), json.dumps(list(languages)),
                     by, n, rest_days, repeat_days, json.dumps(targets or {}), group_q, int(sensitive), after))
        s.db.execute("insert into sv_versions values(?,1,?,?,?)", (sid, json.dumps(questions), json.dumps(logic or []), n))
        s.cloud.event(merchant, "SurveySaved", {"survey_id": sid, "version": 1, "kind": kind, "rule": rule, "anonymous": bool(anonymous), "languages": list(languages)}, now=n)
        s._log(merchant, by, "built", sid, n); s.db.commit(); return sid
    def edit(s, merchant, survey, by, questions, logic=None, now=None):
        """Once answers have arrived, a change makes a new version, so answers to the old and new questions are never mixed."""
        s._need(merchant, by, BUILDERS); sv = s._sv(survey); s._valid(merchant, sv["kind"], questions, logic); n = _now(now)
        answered = s.db.execute("select 1 from sv_answers where survey_id=? and version=? and test=0", (survey, sv["version"])).fetchone()
        v = sv["version"] + 1 if answered else sv["version"]
        s.db.execute("insert or replace into sv_versions values(?,?,?,?,?)", (survey, v, json.dumps(questions), json.dumps(logic or []), n))
        s.db.execute("update sv_surveys set version=?, sensitive=? where survey_id=?", (v, int(any(c["problem"] == "sensitive_topic" for c in s.check_questions(questions))), survey))
        if v != sv["version"] or sv["state"] in ("approved", "sent_back"):
            if sv["state"] in ("approved", "sent_back"): s.db.execute("update sv_surveys set state='draft' where survey_id=?", (survey,))   # a changed survey is approved again
        s.cloud.event(merchant, "SurveySaved", {"survey_id": survey, "version": v, "kind": sv["kind"], "rule": sv["rule"], "anonymous": sv["anonymous"], "languages": sv["languages"]}, now=n)
        s._log(merchant, by, "changed", survey, n); s.db.commit(); return v
    def write_it_for_me(s, merchant, by, sentence, language="en"):
        """LynkAssist writes a draft from one sentence (labelled a suggestion); the creator changes anything before it is saved."""
        s._need(merchant, by, BUILDERS)
        if not s._ent(merchant)["write_it_for_me"]: raise PermissionError("plan_no_write_it_for_me")
        low = sentence.lower()
        if any(w in low for w in ("come back", "return", "lose", "loyal", "recommend")):
            kind, qs = "recommend", [{"id": "recommend", "type": "score", "text": "How likely are you to recommend us to a friend?"},
                                     {"id": "why", "type": "long", "text": "What is the main reason for your score?"},
                                     {"id": "come_back", "type": "yes_no", "text": "Will you come back to us?"}]
        elif any(w in low for w in ("staff", "team", "employee", "workers")):
            kind, qs = "staff_pulse", [{"id": "feel", "type": "rating", "text": "How do you feel about work this week?"},
                                       {"id": "help", "type": "yes_no", "text": "Do you have what you need to do your job well?"},
                                       {"id": "change", "type": "long", "text": "What one thing should we change?"}]
        elif any(w in low for w in ("wait", "queue", "slow", "service")):
            kind, qs = "satisfaction", [{"id": "visit", "type": "rating", "text": "How was your visit today?"},
                                        {"id": "wait", "type": "choice", "text": "How long did you wait?", "choices": ["Under 5 minutes", "5 to 15 minutes", "Over 15 minutes"]},
                                        {"id": "better", "type": "long", "text": "What should we do better?"}]
        else:
            kind, qs = "satisfaction", [{"id": "overall", "type": "rating", "text": "How satisfied are you overall?"},
                                        {"id": "best", "type": "short", "text": "What did you like most?"},
                                        {"id": "better", "type": "long", "text": "What should we do better?"}]
        logic = [{"if": qs[0]["id"], "at_most": 2 if qs[0]["type"] == "rating" else 6, "show": qs[-1]["id"]}]
        return {"kind": kind, "questions": qs, "logic": logic, "suggestion": True, "language": language, "checks": s.check_questions(qs)}
    def library_add(s, merchant, survey, by):
        """Head office's shared library and brand kit: approved surveys every branch can start from."""
        s._need(merchant, by, SEES_ALL)
        if not s._ent(merchant)["library_and_brand_kit"]: raise PermissionError("plan_no_library")
        s.db.execute("update sv_surveys set library=1 where survey_id=?", (survey,)); s.db.commit()
    def library(s, merchant): return [r[0] for r in s.db.execute("select survey_id from sv_surveys where merchant=? and library=1", (merchant,))]
    def how_many(s, margin_percent, population=None): return R.sample_size(margin_percent, population)

    # ---- approval, opening, test mode
    def _needs_approval(s, merchant):
        r = s.db.execute("select approval from sv_settings where merchant=?", (merchant,)).fetchone(); return bool(r and r[0])
    def submit(s, merchant, survey, by, now=None):
        s._need(merchant, by, BUILDERS)
        if not s._needs_approval(merchant): return "no_approval_needed"
        s.db.execute("update sv_surveys set state='waiting_for_approval' where survey_id=?", (survey,)); s._log(merchant, by, "sent_for_approval", survey, now); s.db.commit()
        return "waiting_for_approval"
    def decide(s, merchant, survey, by, decision, note=None, now=None):
        """The approver presses Approve or Send back with a note. Nothing reaches the public without approval when it is switched on."""
        s._need(merchant, by, ("approver", "owner", "manager"))
        if decision not in ("approve", "send_back"): raise ValueError("unknown decision")
        sv = s._sv(survey)
        if sv["state"] != "waiting_for_approval": raise ValueError("not_waiting_for_approval")
        if sv["by"] == by and s._roles(merchant, by) & {"approver"} and not s._roles(merchant, by) & {"owner"}: raise PermissionError("not_your_own_survey")
        s.db.execute("update sv_surveys set state=?, sent_back_note=? where survey_id=?", ("approved" if decision == "approve" else "sent_back", note, survey))
        s.cloud.event(merchant, "SurveyApproval", {"survey_id": survey, "version": sv["version"], "decision": decision, "by": by}, now=now)
        s._log(merchant, by, f"approval_{decision}", survey, now); s.db.commit()
    def _live_count(s, merchant): return s.db.execute("select count(*) from sv_surveys where merchant=? and state='open'", (merchant,)).fetchone()[0]
    def set_state(s, merchant, survey, by, state, now=None):
        """Open, pause, close, or test mode (test answers are marked and never counted)."""
        s._need(merchant, by, BUILDERS); sv = s._sv(survey); ent = s._ent(merchant)
        if state not in ("open", "paused", "closed", "test"): raise ValueError("unknown state")
        if state == "open":
            if s._needs_approval(merchant) and sv["state"] not in ("approved", "paused"): raise PermissionError("needs_approval_first")
            if ent["live_surveys"] is not None and sv["state"] != "open" and s._live_count(merchant) >= ent["live_surveys"]: raise PermissionError("plan_limit_live_surveys")
        s.db.execute("update sv_surveys set state=?, opened=coalesce(opened, ?) where survey_id=?", (state, _now(now) if state == "open" else None, survey))
        s.cloud.event(merchant, "SurveyStateChanged", {"survey_id": survey, "state": state}, now=now)
        s._log(merchant, by, f"state_{state}", survey, now); s.db.commit()

    # ---- inviting (the four rules) and reminders
    def invite(s, merchant, survey, by, people, way="email", now=None):
        """people: [(person_id or None, contact)]. Each invited person gets their own code that works once; anyone who said
        "Don't ask me again" or was asked within the rest period is skipped. Returns the codes (sandbox: shown, not sent)."""
        s._need(merchant, by, BUILDERS); sv = s._sv(survey); n = _now(now); out = []
        for person, contact in people:
            if person and not s.may_ask(person, merchant, sv["rest_days"], n): continue
            code = secrets.token_urlsafe(9)
            ref = s.vault.put(code, "contact", contact) if contact else None
            s.db.execute("insert into sv_invites values(?,?,?,?,0,0,?)", (s._hash(code), survey, person, ref, n))
            if person: s.db.execute("insert or replace into sv_asked values(?,?,?)", (person, merchant, n))
            if person: s._tell("survey_invite", person, f"{survey}:{s._hash(code)[:12]}", n, record=survey, business=merchant)
            out.append(code)
        s._log(merchant, by, f"invited_{len(out)}", survey, n); s.db.commit(); return out
    def may_ask(s, person, merchant, rest_days=R.DEFAULT_REST_DAYS, now=None):
        opted = s.db.execute("select 1 from sv_optout where person=? and merchant=?", (person, merchant)).fetchone() is not None
        last = s.db.execute("select at from sv_asked where person=? and merchant=?", (person, merchant)).fetchone()
        return R.may_ask_again(None if not last else int((_now(now) - last[0]) // DAY), rest_days, opted)
    def phone_code(s, survey, contact, now=None):
        """One per phone: a code is sent by text, WhatsApp or LynkChat before answering (sandbox: the code comes back here)."""
        n, mark = _now(now), s._mark(survey, contact)
        if s.db.execute("select 1 from sv_marks where survey_id=? and mark=?", (survey, mark)).fetchone(): return {"state": "refused", "reason": "already_answered"}
        code = f"{secrets.randbelow(10**6):06d}"; ref = s.vault.put(f"{survey}:{mark}", "contact", contact)
        s.db.execute("insert or replace into sv_phone values(?,?,?,?,?,0)", (survey, mark, ref, s._hash(code), n + CONTACT_KEPT_DAYS * DAY))
        s.db.commit(); return {"state": "sent", "sandbox_code": code}
    def confirm_phone(s, survey, contact, code):
        mark = s._mark(survey, contact)
        r = s.db.execute("select code_hash from sv_phone where survey_id=? and mark=?", (survey, mark)).fetchone()
        if not r or r[0] != s._hash(code): return None
        s.db.execute("update sv_phone set confirmed=1 where survey_id=? and mark=?", (survey, mark)); s.db.commit(); return mark
    def reminders(s, merchant, now=None):
        """People who were invited and have not answered get up to 2 reminders, every 3 days, then no more."""
        n, told = _now(now), []
        for h, survey, person, rem, last in s.db.execute("select i.code_hash, i.survey_id, i.person, i.reminders, i.last_at from sv_invites i join sv_surveys v on v.survey_id=i.survey_id where v.merchant=? and v.state='open' and i.used=0", (merchant,)).fetchall():
            if rem >= R.REMINDERS_MAX or n - last < REMINDER_EVERY_DAYS * DAY or not person: continue
            if s.db.execute("select 1 from sv_optout where person=? and merchant=?", (person, merchant)).fetchone(): continue
            s.db.execute("update sv_invites set reminders=reminders+1, last_at=? where code_hash=?", (n, h))
            s._tell("survey_invite", person, f"{survey}:{h[:12]}:r{rem + 1}", n, record=survey, business=merchant); told.append(person)
        s.db.commit(); return told

    # ---- automatic surveys at the right moment (only when the manager switched the automation on; rest period and opt-out respected)
    @staticmethod
    def _may_follow(ent, service): return "all" in ent["automatic"] or service in ent["automatic"] or (service == "api" and "api" in ent["automatic"])
    def open_after(s, merchant, service):
        """The open survey set to follow this moment, if the plan allows automatic surveys after it."""
        if not s._may_follow(s._ent(merchant), service): return None
        r = s.db.execute("select survey_id from sv_surveys where merchant=? and after=? and state='open' order by created limit 1", (merchant, service)).fetchone()
        return r and r[0]
    def ask_after(s, merchant, service, person=None, contact_ref=None, now=None):
        """One short survey after a sale, a visit, a chat or a shift: a single-use code for this person or this ticket's contact."""
        sid = s.open_after(merchant, service)
        if not sid: return None
        sv, n = s._sv(sid), _now(now)
        if person and not s.may_ask(person, merchant, sv["rest_days"], n): return None
        code = secrets.token_urlsafe(9)
        s.db.execute("insert into sv_invites values(?,?,?,?,0,0,?)", (s._hash(code), sid, person, contact_ref, n))
        if person:
            s.db.execute("insert or replace into sv_asked values(?,?,?)", (person, merchant, n))
            s._tell("survey_invite", person, f"{sid}:{s._hash(code)[:12]}", n, record=sid, business=merchant)
        s.db.commit(); return {"survey_id": sid, "code": code}

    # ---- answering
    def answer(s, survey, way, answers, language="en", seconds=None, invite_code=None, phone_mark=None, person=None, group=None, consent=False,
               call_back_contact=None, device_today=1, device_mark=None, now=None):
        """An answer from a person's own phone or computer (link, website, WhatsApp, LynkChat, basic phone, voice, email)."""
        sv = s._sv(survey); merchant, ent, n = sv["merchant"], s._ent(sv["merchant"]), _now(now)
        if way not in WAYS or way in DEVICE_WAYS: raise ValueError("unknown way")
        if sv["state"] not in ("open", "test"): return {"state": "refused", "reason": "survey_closed"}
        f = WAY_FEATURE.get(way)
        if f and not ent[f]: return {"state": "refused", "reason": f"plan_no_{f}"}
        if way in PARTNER_WAYS:
            from providers import ready
            if not ready(PARTNER_WAYS[way], s._country(merchant))[0]: return {"state": "coming_soon"}       # "Coming to your country soon."
        if sv["sensitive"] and not consent: return {"state": "refused", "reason": "agreement_needed"}
        if person and s.db.execute("select 1 from sv_optout where person=? and merchant=?", (person, merchant)).fetchone() and invite_code is None: return {"state": "refused", "reason": "asked_not_to_be_asked"}
        mark, invite_h, ok = None, None, True
        if sv["rule"] == "invited":
            invite_h = s._hash(invite_code or "")
            r = s.db.execute("select used, person from sv_invites where code_hash=? and survey_id=?", (invite_h, survey)).fetchone()
            why = R.may_answer("invited", bool(r and r[0]), has_invite=bool(r))
            if why: return {"state": "refused", "reason": why}
            person = person or r[1]; mark = invite_h
        elif sv["rule"] == "one_per_phone":
            ok = bool(phone_mark) and s.db.execute("select 1 from sv_phone where survey_id=? and mark=? and confirmed=1", (survey, phone_mark)).fetchone()
            mark = phone_mark
        elif sv["rule"] == "verified":
            mark = s._mark(survey, f"person:{person}") if person else None
        else:
            mark = s._mark(survey, f"device:{device_mark or person or secrets.token_hex(8)}")   # Open: once per device
        already = bool(mark and s.db.execute("select 1 from sv_marks where survey_id=? and mark=?", (survey, mark)).fetchone())
        why = R.may_answer(sv["rule"], already, has_invite=True, signed_in=bool(person), phone_confirmed=bool(ok))
        if why: return {"state": "refused", "reason": why}
        if sv["targets"] and group is not None and not s.group_open(survey, group): return {"state": "group_full"}
        aid = uuid4(); test = sv["state"] == "test"
        flags = R.real_answer_flags(seconds if seconds is not None else 999, len(answers), s._same(answers), device_today, False)
        if mark and not test: s.db.execute("insert into sv_marks values(?,?)", (survey, mark))
        if invite_h and not test: s.db.execute("update sv_invites set used=1 where code_hash=?", (invite_h,))
        cb_ref = s.vault.put(aid, "contact", call_back_contact) if (call_back_contact and not sv["anonymous"]) else None
        res = s._take(merchant, survey, sv, aid, way, answers, group, None if sv["anonymous"] else person, cb_ref, flags, test, None, None, language, sv["place"], n)
        if person and not sv["anonymous"]: s.db.execute("insert or replace into sv_asked values(?,?,?)", (person, merchant, n))
        s.db.commit(); return res
    @staticmethod
    def _same(answers):
        nums = [a.get("number", a.get("choice")) for a in answers if "number" in a or "choice" in a]
        return len(nums) >= 5 and len(set(nums)) == 1
    def group_open(s, survey, group):
        sv = s._sv(survey)
        counts = {g: c for g, c in s.db.execute("select grp, count(*) from sv_answers where survey_id=? and test=0 and result='accepted' and deleted=0 group by grp", (survey,))}
        return R.group_open(group, counts, sv["targets"])
    def ingest(s, merchant, evt, now=None):
        """An answer recorded on an added device (LynkKiosk, LynkPOS, a field worker, paper entry), also days later."""
        t, p, n = evt["type"], evt["payload"], _now(now)
        dev = s.db.execute("select place, locked from sv_devices where device_id=? and merchant=?", (evt.get("device_id"), merchant)).fetchone()
        if not dev or dev[1]: return {"state": "refused", "reason": "device_not_added"}
        if s.db.execute("select 1 from sv_seen where event_id=?", (evt["event_id"],)).fetchone(): return {"state": "duplicate"}
        s.db.execute("insert into sv_seen values(?)", (evt["event_id"],))
        s.cloud.device_event(merchant, evt, now=n)
        if t == "SurveyAnswered":
            sv = s._sv(p["survey_id"])
            f = WAY_FEATURE.get(p["way"])
            if f and not s._ent(merchant)[f]: s.db.commit(); return {"state": "refused", "reason": f"plan_no_{f}"}
            day = _day(n); s.db.execute("insert into sv_device_day values(?,?,1) on conflict(device, day) do update set n=n+1", (evt["device_id"], day))
            flags = R.real_answer_flags(999, len(p["answers"]), s._same(p["answers"]), 0, p["way"] in SHARED_WAYS)
            res = s._take(merchant, p["survey_id"], sv, p["answer_id"], p["way"], p["answers"], None, None, None, flags, bool(p.get("test")) or sv["state"] == "test",
                          p.get("entered_by"), evt["device_id"], p.get("language", "en"), dev[0], n, version=p["version"])
            s.db.commit(); return res
        if t == "SurveyCashRewardRecorded":
            s.db.execute("insert or ignore into sv_rewards values(?,?,null,?,null,'cash',?,?,'paid')", (p["reward_id"], merchant, p["answer_id"], p["amount"], p["currency"]))
            s._log(merchant, evt.get("actor_user_id"), "cash_reward_recorded", now=n); s.db.commit(); return {"state": "accepted"}
        s.db.commit(); return {"state": "accepted"}
    def _take(s, merchant, survey, sv, aid, way, answers, group, person, cb_ref, flags, test, entered_by, device, language, place, n, version=None):
        result = "please_check" if flags else "accepted"
        s.db.execute("insert into sv_answers values(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,0,?,?,?)", (aid, merchant, survey, version or sv["version"], way, place, group, json.dumps(answers), result,
                     flags[0] if flags else None, int(test), person, cb_ref, int(bool(cb_ref)), n, entered_by, device, language))
        payload = {"answer_id": aid, "survey_id": survey, "version": version or sv["version"], "way": way, "test": bool(test)}
        s.cloud.event(merchant, "SurveyAnswerReceived", payload, now=n)
        chk = {"answer_id": aid, "result": result}
        if flags: chk["reason"] = flags[0]
        eid = s.cloud.event(merchant, "SurveyAnswerChecked", chk, now=n)
        if flags and not test:
            for mg in s._managers(merchant): s._tell("survey_please_check", mg, eid, n, record=survey, business=merchant, role="manager")
        if not test and result == "accepted" and s._unhappy(sv, answers, survey): s._burst(merchant, survey, place, eid, n)
        return {"state": result, "answer_id": aid, "test": bool(test)}
    def _managers(s, merchant): return [r[0] for r in s.db.execute("select person from sv_roles where merchant=? and role in ('owner','manager')", (merchant,))]
    def _unhappy(s, sv, answers, survey):
        qs = {q["id"]: q["type"] for q in s.questions(survey)["questions"]}
        return any(qs.get(a["q"]) in UNHAPPY and "number" in a and a["number"] <= UNHAPPY[qs[a["q"]]] for a in answers)
    def _burst(s, merchant, survey, place, eid, n):
        since = n - UNHAPPY_WINDOW_S; hour = int(n // 3600)
        rows = s.db.execute("select answers from sv_answers where survey_id=? and place is ? and at>=? and test=0 and result='accepted'", (survey, place, since)).fetchall()
        if sum(1 for r in rows if s._unhappy(None, json.loads(r[0]), survey)) >= UNHAPPY_BURST and not s.db.execute("select 1 from sv_alerts where place is ? and hour=?", (place, hour)).fetchone():
            s.db.execute("insert into sv_alerts values(?,?)", (place, hour))
            for mg in s._managers(merchant): s._tell("survey_alert", mg, eid, n, record=survey, business=merchant, role="manager")
    def decide_flag(s, merchant, answer_id, by, accept, now=None):
        """"Please check" is only a flag: the manager keeps the answer or sets it aside (never deleted, never an accusation)."""
        s._need(merchant, by, SEES_ALL)
        s.db.execute("update sv_answers set result=? where answer_id=? and merchant=? and result='please_check'", ("accepted" if accept else "set_aside", answer_id, merchant))
        s.cloud.event(merchant, "SurveyAnswerChecked", {"answer_id": answer_id, "result": "accepted" if accept else "set_aside"}, now=now)
        s._log(merchant, by, "kept_answer" if accept else "set_answer_aside", now=now); s.db.commit()
    def correct_paper(s, merchant, answer_id, by, answers, reason, now=None):
        """A wrong paper entry is corrected with a reason; the old one is kept beside it (answers are never changed quietly)."""
        s._need(merchant, by, SEES_ALL + ("field_worker",))
        old = s.db.execute("select survey_id, version, way, place, grp, answers, language from sv_answers where answer_id=? and merchant=? and way='paper'", (answer_id, merchant)).fetchone()
        if not old or not reason: raise ValueError("only a paper entry, with a reason")
        s.db.execute("update sv_answers set result='set_aside' where answer_id=?", (answer_id,))
        nid = uuid4(); sv = s._sv(old[0])
        s._take(merchant, old[0], sv, nid, "paper", answers, old[4], None, None, [], False, by, None, old[6], old[3], _now(now), version=old[1])
        s._log(merchant, by, f"paper_corrected:{reason}", old[0], now); s.db.commit(); return nid

    # ---- results (never for fewer than 5; viewers see only their part of the tree)
    def _rows(s, merchant, survey, by, places=None, field=None, value=None, version=None):
        sees = s._sees(merchant, by)
        sv = s._sv(survey)
        if sees == "own" and sv["by"] != by: raise PermissionError("not_your_survey")
        rows = s.db.execute("select answer_id, answers, place, grp, way, language, at from sv_answers where survey_id=? and test=0 and result='accepted' and deleted=0 and version=?",
                            (survey, version or sv["version"])).fetchall()
        allowed = None if sees in (None, "own") else set(sees)
        if places is not None: allowed = set(places) if allowed is None else allowed & set(places)
        out = []
        for aid, ans, place, grp, way, lang, at in rows:
            if allowed is not None and place not in allowed: continue
            if field == "group" and grp != value: continue
            if field == "way" and way != value: continue
            if field == "language" and lang != value: continue
            out.append({"answer_id": aid, "answers": {a["q"]: a for a in json.loads(ans)}, "place": place, "group": grp, "way": way, "at": at})
        return out
    def results(s, merchant, survey, by, places=None, field=None, value=None, version=None):
        rows = s._rows(merchant, survey, by, places, field, value, version)
        if not R.can_show(len(rows)): return {"shown": False, "answers": len(rows) if len(rows) == 0 else None, "min_group": R.MIN_GROUP}
        out = {"shown": True, "answers": len(rows), "questions": {}}
        for q in s.questions(survey, version)["questions"]:
            got = [r["answers"][q["id"]] for r in rows if q["id"] in r["answers"]]
            if not R.can_show(len(got)): out["questions"][q["id"]] = {"shown": False}; continue
            if q["type"] in ("rating", "stars", "score", "number"):
                nums = [a["number"] for a in got if "number" in a]
                good = sum(1 for x in nums if x >= (9 if q["type"] == "score" else 4))
                share = math.floor(good * 100 / len(nums) + 0.5) if nums else 0
                res = {"shown": True, "n": len(nums), "average_tenths": math.floor(sum(nums) * 10 / len(nums) + 0.5) if nums else None, "good_percent": share, "margin_tenths": R.margin(share, len(nums))}
                if q["type"] == "score":
                    pro, det = sum(1 for x in nums if x >= 9), sum(1 for x in nums if x <= 6)
                    res["recommend_score"] = round((pro - det) * 100 / len(nums))
                out["questions"][q["id"]] = res
            elif q["type"] in ("choice", "yes_no", "many"):
                counts = {}
                for a in got:
                    for c in (a.get("choice", "").split("|") if q["type"] == "many" else [a.get("choice", "")]): counts[c] = counts.get(c, 0) + 1
                out["questions"][q["id"]] = {"shown": True, "n": len(got), "shares": {c: {"percent": math.floor(k * 100 / len(got) + 0.5), "margin_tenths": R.margin(math.floor(k * 100 / len(got) + 0.5), len(got))} for c, k in sorted(counts.items())}}
            else:
                out["questions"][q["id"]] = {"shown": True, "n": len(got), "written": len([a for a in got if a.get("text")])}
        return out
    def compare(s, merchant, survey, by, question, field, values):
        """Compare groups side by side; a group below 5 shows nothing."""
        if "compare_groups" not in s._ent(merchant)["research"]: raise PermissionError("plan_no_compare_groups")
        return {v: s.results(merchant, survey, by, field=field, value=v)["questions"].get(question) if s.results(merchant, survey, by, field=field, value=v)["shown"] else {"shown": False} for v in values}
    @staticmethod
    def real_difference(p1, n1, p2, n2):
        """"Real difference or chance?": a two-group test at 95%, said in plain words. Shares are whole percents."""
        if min(n1, n2) < R.MIN_GROUP: return "too_few"
        a, b = p1 / 100, p2 / 100; pool = (a * n1 + b * n2) / (n1 + n2)
        se = math.sqrt(pool * (1 - pool) * (1 / n1 + 1 / n2))
        if se == 0: return "no_difference" if a == b else "real"
        return "real" if abs(a - b) / se >= R.Z95 else "could_be_chance"
    def real_difference_for(s, merchant, survey, by, question, field, v1, v2):
        if "real_difference" not in s._ent(merchant)["research"]: raise PermissionError("plan_no_real_difference")
        r1, r2 = (s.results(merchant, survey, by, field=field, value=v)["questions"].get(question, {}) if s.results(merchant, survey, by, field=field, value=v)["shown"] else {} for v in (v1, v2))
        if not r1.get("shown") or not r2.get("shown"): return {"verdict": "too_few"}
        return {"verdict": s.real_difference(r1["good_percent"], r1["n"], r2["good_percent"], r2["n"]), "a": r1["good_percent"], "b": r2["good_percent"]}
    def balanced(s, merchant, survey, by, question, population):
        """Balancing results: answers re-weighted so the groups match the real population (shares in whole percents that add to 100).
        The raw and the balanced result are always shown side by side."""
        if "balancing" not in s._ent(merchant)["research"]: raise PermissionError("plan_no_balancing")
        if sum(population.values()) != 100: raise ValueError("population shares must add up to 100")
        rows = s._rows(merchant, survey, by)
        if not R.can_show(len(rows)): return {"shown": False}
        by_g = {}
        for r in rows:
            a = r["answers"].get(question)
            if a and "number" in a: by_g.setdefault(r["group"], []).append(a["number"])
        raw_all = [x for v in by_g.values() for x in v]
        raw = math.floor(sum(1 for x in raw_all if x >= 4) * 100 / len(raw_all) + 0.5)
        weighted = sum(population.get(g, 0) * (sum(1 for x in v if x >= 4) / len(v)) for g, v in by_g.items() if g in population and R.can_show(len(v)))
        cover = sum(population[g] for g, v in by_g.items() if g in population and R.can_show(len(v)))
        return {"shown": True, "raw_percent": raw, "balanced_percent": math.floor(weighted * 100 / cover + 0.5) if cover else None, "groups_used": sorted(g for g, v in by_g.items() if g in population and R.can_show(len(v)))}
    THEMES = {"waiting_time": ("wait", "slow", "long", "queue", "time"), "staff_kindness": ("kind", "friendly", "rude", "polite", "staff", "nice"),
              "price": ("price", "cost", "expensive", "cheap"), "cleanliness": ("clean", "dirty", "smell"), "quality": ("quality", "good product", "broken", "fresh")}
    def themes(s, merchant, survey, by, question):
        """Themes in written and spoken answers (LynkAssist, sandbox keyword groups the researcher can check and correct)."""
        level = "themes" if "themes" in s._ent(merchant)["research"] else ("themes_basic" if "themes_basic" in s._ent(merchant)["research"] else None)
        if not level: raise PermissionError("plan_no_themes")
        texts = [r["answers"][question].get("text", "").lower() for r in s._rows(merchant, survey, by) if question in r["answers"]]
        texts = [t for t in texts if t]
        if not R.can_show(len(texts)): return {"shown": False}
        found = {k: sum(1 for t in texts if any(w in t for w in words)) for k, words in s.THEMES.items()}
        found = {k: math.floor(v * 100 / len(texts) + 0.5) for k, v in found.items() if v and (level == "themes" or v * 100 // len(texts) >= 20)}
        return {"shown": True, "n": len(texts), "themes": dict(sorted(found.items(), key=lambda kv: -kv[1])), "suggestion": True}
    def best_worst(s, merchant, survey, by, question):
        """"What matters most?": each answer names the most and least important item of a small group: score = most - least."""
        if "what_matters_most" not in s._ent(merchant)["research"]: raise PermissionError("plan_no_what_matters_most")
        rows = [r["answers"][question] for r in s._rows(merchant, survey, by) if question in r["answers"]]
        if not R.can_show(len(rows)): return {"shown": False}
        score = {}
        for a in rows:
            best, worst = (a.get("choice", "|").split("|") + [""])[:2]
            score[best] = score.get(best, 0) + 1; score[worst] = score.get(worst, 0) - 1
        return {"shown": True, "order": [k for k, _ in sorted(score.items(), key=lambda kv: (-kv[1], kv[0])) if k]}
    def trade_off(s, merchant, survey, by, question):
        """Trade-off study: which whole offer people pick, as shares with their margins."""
        if "trade_off" not in s._ent(merchant)["research"]: raise PermissionError("plan_no_trade_off")
        rows = [r["answers"][question].get("choice") for r in s._rows(merchant, survey, by) if question in r["answers"]]
        if not R.can_show(len(rows)): return {"shown": False}
        out = {}
        for c in rows: out[c] = out.get(c, 0) + 1
        return {"shown": True, "picked": {c: {"percent": math.floor(k * 100 / len(rows) + 0.5), "margin_tenths": R.margin(math.floor(k * 100 / len(rows) + 0.5), len(rows))} for c, k in sorted(out.items())}}
    def before_after(s, merchant, survey, by, question, v1, v2):
        """Before and after: the same question in two versions or rounds, with "real difference or chance?" (Pro and Max) for the change."""
        if "before_after" not in s._ent(merchant)["research"]: raise PermissionError("plan_no_before_after")
        a, b = (s.results(merchant, survey, by, version=v) for v in (v1, v2))
        qa, qb = (x["questions"].get(question, {}) if x["shown"] else {} for x in (a, b))
        if not qa.get("shown") or not qb.get("shown"): return {"shown": False}
        out = {"shown": True, "before": qa["good_percent"], "after": qb["good_percent"]}
        if "real_difference" in s._ent(merchant)["research"]: out["verdict"] = s.real_difference(qa["good_percent"], qa["n"], qb["good_percent"], qb["n"])
        return out
    def summary(s, merchant, survey, by):
        """The LynkAssist summary in plain words (every tier), only from results that may be shown."""
        r = s.results(merchant, survey, by)
        if not r["shown"]: return {"shown": False, "min_group": R.MIN_GROUP}
        lines = []
        for q in s.questions(survey)["questions"]:
            x = r["questions"].get(q["id"], {})
            if not x.get("shown"): continue
            if "good_percent" in x: lines.append({"q": q["id"], "good_percent": x["good_percent"], "margin_tenths": x["margin_tenths"]})
            elif "shares" in x and x["shares"]:
                top = max(x["shares"].items(), key=lambda kv: kv[1]["percent"]); lines.append({"q": q["id"], "top": top[0], "percent": top[1]["percent"]})
        return {"shown": True, "answers": r["answers"], "lines": lines, "suggestion": True}

    # ---- closing the loop: call back, "You said, we did"
    def call_back(s, merchant, answer_id, assignee=None, now=None):
        """An unhappy person who left a contact and agreed: a Call back task with a time limit goes to the right staff member."""
        r = s.db.execute("select call_back_ok, survey_id from sv_answers where answer_id=? and merchant=?", (answer_id, merchant)).fetchone()
        if not r or not r[0]: return None
        if s.db.execute("select 1 from sv_tasks where answer_id=?", (answer_id,)).fetchone(): return None
        tid, n = uuid4(), _now(now); who = assignee or (s._managers(merchant) or [None])[0]
        s.db.execute("insert into sv_tasks values(?,?,?,?,'created',?,null,null)", (tid, merchant, answer_id, who, n + CALL_BACK_HOURS * 3600))
        eid = s.cloud.event(merchant, "SurveyCallBack", {"task_id": tid, "answer_id": answer_id, "state": "created"}, now=n)
        if who: s._tell("survey_call_back", who, eid, n, record=r[1], business=merchant, role="staff")
        s.db.commit(); return tid
    def call_back_done(s, merchant, task_id, by, now=None):
        r = s.db.execute("select answer_id, state from sv_tasks where task_id=? and merchant=?", (task_id, merchant)).fetchone()
        if not r or r[1] == "done": raise ValueError("no open task")
        s.db.execute("update sv_tasks set state='done', done_at=?, done_by=? where task_id=?", (_now(now), by, task_id))
        s.cloud.event(merchant, "SurveyCallBack", {"task_id": task_id, "answer_id": r[0], "state": "done", "by": by}, now=now)
        s._log(merchant, by, "call_back_done", now=now); s.db.commit()
    def tasks(s, merchant):
        return [dict(zip(("task_id", "answer_id", "assignee", "state", "due", "done_at", "done_by"), r)) for r in s.db.execute("select task_id, answer_id, assignee, state, due, done_at, done_by from sv_tasks where merchant=? order by due", (merchant,))]
    def you_said(s, merchant, survey, by, text, now=None):
        """One message back to everyone who answered (non-anonymous, with a contact); for an anonymous survey it is shown on the public page."""
        s._need(merchant, by, SEES_ALL)
        if not s._ent(merchant)["call_back"]: raise PermissionError("plan_no_you_said_we_did")
        sv = s._sv(survey); people = [] if sv["anonymous"] else [r[0] for r in s.db.execute("select distinct person from sv_answers where survey_id=? and person is not null and deleted=0", (survey,))]
        s.db.execute("insert into sv_said values(?,?,?,?)", (survey, text, _now(now), len(people)))
        s._log(merchant, by, "you_said_we_did", survey, now); s.db.commit()
        return {"told": len(people), "public_page": sv["anonymous"]}

    # ---- rewards and the LynkSurvey Panel (the organisation pays; LynkOmni never holds a reward)
    def reward(s, merchant, answer_id, kind, amount, currency, now=None):
        if not s._ent(merchant)["rewards"]: raise PermissionError("plan_no_rewards")
        if isinstance(amount, bool) or not isinstance(amount, int) or amount <= 0: raise ValueError("a reward is a whole number of minor units")
        r = s.db.execute("select survey_id, person, result, test from sv_answers where answer_id=? and merchant=?", (answer_id, merchant)).fetchone()
        if not r or r[2] != "accepted" or r[3]: return {"state": "refused", "reason": "only_after_the_check"}
        if r[1] and s.db.execute("select 1 from sv_rewards where survey_id=? and person=?", (r[0], r[1])).fetchone(): return {"state": "refused", "reason": "one_reward_per_person"}
        if s.db.execute("select 1 from sv_rewards where answer_id=?", (answer_id,)).fetchone(): return {"state": "refused", "reason": "one_reward_per_person"}
        rid, n = uuid4(), _now(now)
        from providers import ready
        if not ready("survey_rewards", s._country(merchant))[0]:
            s.db.execute("insert into sv_rewards values(?,?,?,?,?,?,?,?,'coming_to_country')", (rid, merchant, r[0], answer_id, r[1], kind, amount, currency)); s.db.commit()
            return {"state": "coming_soon", "reward_id": rid}
        s.db.execute("insert into sv_rewards values(?,?,?,?,?,?,?,?,'sent')", (rid, merchant, r[0], answer_id, r[1], kind, amount, currency))
        s.cloud.event(merchant, "SurveyRewardRequested", {"reward_id": rid, "answer_id": answer_id, "kind": kind}, now=n)
        s.rewards.pay(rid, kind, amount, currency, f"vault:{answer_id}") if s.rewards else None
        s.db.commit(); return {"state": "sent", "reward_id": rid}
    def reward_answer(s, merchant, reward_id, result, now=None):
        """Only the partner's answer, in the cloud, says a reward was paid."""
        if result not in ("paid", "failed"): raise ValueError("unknown result")
        r = s.db.execute("select person from sv_rewards where reward_id=? and merchant=? and state='sent'", (reward_id, merchant)).fetchone()
        if not r: raise ValueError("no reward waiting")
        s.db.execute("update sv_rewards set state=? where reward_id=?", (result, reward_id))
        eid = s.cloud.event(merchant, "SurveyRewardAnswered", {"reward_id": reward_id, "result": result}, now=now)
        if r[0]: s._tell("survey_reward", r[0], eid, _now(now), record=reward_id)
        s.db.commit()
    def panel_join(s, person, country, age_range, language, topics=(), owns_business=False, now=None):
        ref = uuid4()
        s.db.execute("insert or replace into sv_panel values(?,?,?,?,?,?,?,?)", (ref, person, country, age_range, language, json.dumps(list(topics)), int(bool(owns_business)), _now(now)))
        s.cloud.event(person, "PanelMembership", {"member_ref": ref, "state": "joined"}, now=now); s.db.commit(); return ref
    def panel_leave(s, person, now=None):
        """A member can leave at any time, and all their panel details are deleted."""
        refs = [r[0] for r in s.db.execute("select member_ref from sv_panel where person=?", (person,))]
        s.db.execute("delete from sv_panel where person=?", (person,))
        for ref in refs: s.cloud.event(person, "PanelMembership", {"member_ref": ref, "state": "left"}, now=now)
        s.db.commit(); return len(refs)
    def ask_panel(s, merchant, survey, by, wanted, country=None, age_range=None, owns_business=None, now=None):
        """Researchers ask the panel ("500 people in Ghana, 18 to 35, who own a business"). LynkOmni sends the survey;
        the researcher only ever gets the number reached, never who the people are."""
        s._need(merchant, by, BUILDERS)
        if not s._ent(merchant)["panel"]: raise PermissionError("plan_no_panel")
        q, a = "select person from sv_panel where 1=1", []
        if country: q += " and country=?"; a.append(country)
        if age_range: q += " and age_range=?"; a.append(age_range)
        if owns_business is not None: q += " and owns_business=?"; a.append(int(owns_business))
        people = [r[0] for r in s.db.execute(q, a)][:wanted]
        sv = s._sv(survey); n = _now(now)
        for person in people:
            code = secrets.token_urlsafe(9); s.db.execute("insert into sv_invites values(?,?,?,null,0,0,?)", (s._hash(code), survey, person, n))
            s._tell("survey_invite", person, f"{survey}:panel:{s._hash(code)[:12]}", n, record=survey)
        s._log(merchant, by, f"panel_asked_{len(people)}", survey, n); s.db.commit()
        return {"reached": len(people), "wanted": wanted}

    # ---- verified results, downloads, history
    def verify(s, merchant, survey, by, now=None):
        """A check link anyone can open to confirm the numbers are real and untouched, with the research record."""
        s._need(merchant, by, SEES_ALL); sv = s._sv(survey)
        rows = s.db.execute("select answer_id, answers from sv_answers where survey_id=? and version=? and test=0 and result='accepted' and deleted=0 order by answer_id", (survey, sv["version"])).fetchall()
        body = json.dumps([[a, json.loads(x)] for a, x in rows], sort_keys=True)
        method = {"rule": sv["rule"], "anonymous": sv["anonymous"], "targets": sv["targets"], "version": sv["version"], "kind": sv["kind"], "languages": sv["languages"]}
        digest = hashlib.sha256((body + json.dumps(method, sort_keys=True)).encode()).hexdigest()
        counts = {"answers": len(rows)}
        s.db.execute("insert or replace into sv_verified values(?,?,?,?,?,?)", (digest, survey, sv["version"], json.dumps(counts), json.dumps(method), _now(now)))
        s.cloud.event(merchant, "SurveyResultsVerified", {"survey_id": survey, "version": sv["version"], "digest": digest}, now=now)
        s._log(merchant, by, "results_verified", survey, now); s.db.commit(); return digest
    def check_link(s, digest):
        """The public check: "real and untouched" while the answers still give the same digest."""
        r = s.db.execute("select survey_id, version, counts, method from sv_verified where digest=?", (digest,)).fetchone()
        if not r: return {"state": "unknown"}
        rows = s.db.execute("select answer_id, answers from sv_answers where survey_id=? and version=? and test=0 and result='accepted' and deleted=0 order by answer_id", (r[0], r[1])).fetchall()
        body = json.dumps([[a, json.loads(x)] for a, x in rows], sort_keys=True)
        same = hashlib.sha256((body + json.dumps(json.loads(r[3]), sort_keys=True)).encode()).hexdigest() == digest
        return {"state": "real_and_untouched" if same else "changed_since", "counts": json.loads(r[2]), "method": json.loads(r[3])}
    def download(s, merchant, survey, by, fmt="csv"):
        """Full research downloads with the questions and labels; never who answered, and never for fewer than 5 answers."""
        s._need(merchant, by, SEES_ALL + ("creator",))
        if fmt not in s._ent(merchant)["downloads"]: raise PermissionError(f"plan_no_download_{fmt}")
        rows = s._rows(merchant, survey, by)
        if not R.can_show(len(rows)): return None
        qs = s.questions(survey)["questions"]
        buf = io.StringIO(); w = csv.writer(buf, lineterminator="\n"); w.writerow(["answer"] + [q["id"] for q in qs] + ["way"])
        for i, r in enumerate(rows, 1):
            w.writerow([i] + [(r["answers"].get(q["id"], {}).get("number", r["answers"].get(q["id"], {}).get("choice", r["answers"].get(q["id"], {}).get("text", "")))) for q in qs] + [r["way"]])
        data = buf.getvalue()
        if fmt in ("csv", "spreadsheet"): return {"format": fmt, "data": data}
        labels = {"spss": "\n".join(f"VARIABLE LABELS {q['id']} '{q.get('text', '').replace(chr(39), chr(39) * 2)}'." for q in qs),
                  "stata": "\n".join(f'label variable {q["id"]} "{q.get("text", "")}"' for q in qs),
                  "r": "\n".join(f'attr(d${q["id"]}, "label") <- "{q.get("text", "")}"' for q in qs)}[fmt]
        return {"format": fmt, "data": data, "labels": labels}
    def history(s, merchant, limit=100):
        return [dict(zip(("at", "by", "what", "survey"), r)) for r in s.db.execute("select at, by, what, survey from sv_history where merchant=? order by at desc, rowid desc limit ?", (merchant, limit))]

    # ---- the person's control: My answers, delete, Don't ask me again, contacts kept 30 days
    def my_answers(s, person):
        return [dict(zip(("answer_id", "survey_id", "merchant", "at"), r)) for r in s.db.execute("select answer_id, survey_id, merchant, at from sv_answers where person=? and deleted=0 order by at desc", (person,))]
    def delete_my_answer(s, person, answer_id, now=None):
        r = s.db.execute("select merchant from sv_answers where answer_id=? and person=? and deleted=0", (answer_id, person)).fetchone()
        if not r: raise KeyError("not your answer")
        s.db.execute("update sv_answers set deleted=1, answers='[]', contact_ref=null where answer_id=?", (answer_id,)); s.vault.delete_subject(answer_id)
        s.cloud.event(r[0], "SurveyAnswerDeleted", {"answer_id": answer_id}, now=now); s.db.commit()
    def dont_ask_again(s, person, merchant, now=None):
        s.db.execute("insert or ignore into sv_optout values(?,?)", (person, merchant))
        s.cloud.event(merchant, "SurveyOptOut", {"organisation_id": merchant}, now=now); s.db.commit()
    def forget_contacts(s, now=None):
        n, gone = _now(now), 0
        for survey, mark in s.db.execute("select survey_id, mark from sv_phone where until<=?", (n,)).fetchall():
            s.vault.delete_subject(f"{survey}:{mark}"); s.db.execute("delete from sv_phone where survey_id=? and mark=?", (survey, mark)); gone += 1
        s.db.commit(); return gone

    # ---- repeating surveys and what is billed
    def repeat_due(s, merchant, now=None):
        """A repeating survey runs again by itself every week, month or year: a new round on the same questions."""
        n, out = _now(now), []
        for sid, opened, every, rounds in s.db.execute("select survey_id, opened, repeat_days, rounds from sv_surveys where merchant=? and repeat_days is not null and opened is not null", (merchant,)).fetchall():
            if n - opened >= every * DAY * (rounds + 1):
                s.db.execute("update sv_surveys set rounds=rounds+1, state='open' where survey_id=?", (sid,)); out.append(sid)
                s.cloud.event(merchant, "SurveyStateChanged", {"survey_id": sid, "state": "open"}, now=n)
        s.db.commit(); return out
    def billable(s, merchant, month_start, month_end):
        """Creators who built or sent a survey that month, and answers over the plan's number, from billing FEATURES."""
        ent = s._ent(merchant)
        creators = {r[0] for r in s.db.execute("select distinct by from sv_history where merchant=? and at>=? and at<? and (what='built' or what like 'state_open%' or what='changed')", (merchant, month_start, month_end))}
        answers = s.db.execute("select count(*) from sv_answers where merchant=? and at>=? and at<? and test=0", (merchant, month_start, month_end)).fetchone()[0]
        extra_creators = max(0, len(creators) - ent["creators_included"])
        over = max(0, answers - ent["answers_per_month"])
        cents = (extra_creators * (ent["extra_creator_cents"] or 0)) + (math.ceil(over / 1000) * billing.SERVICE_FEES["survey_extra_1000_answers_cents"] if ent["extra_creator_cents"] is not None else 0)
        return {"creators": len(creators), "extra_creators": extra_creators, "answers": answers, "over": over, "extra_cents": cents, "free_stops_today": ent["extra_creator_cents"] is None and over > 0}
    def live(s, merchant, by):
        """The dashboard's live view: open surveys, answers today and anything waiting for the manager."""
        s._need(merchant, by, ROLES)
        rows = s.db.execute("select survey_id, state from sv_surveys where merchant=?", (merchant,)).fetchall()
        return {"open": sum(1 for r in rows if r[1] == "open"), "surveys": len(rows),
                "please_check": s.db.execute("select count(*) from sv_answers where merchant=? and result='please_check'", (merchant,)).fetchone()[0],
                "call_backs_open": s.db.execute("select count(*) from sv_tasks where merchant=? and state='created'", (merchant,)).fetchone()[0],
                "waiting_for_approval": sum(1 for r in rows if r[1] == "waiting_for_approval")}
