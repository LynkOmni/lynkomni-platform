"""LynkFlow: the automation runner (blueprint section 45, built from build section 2 on).
Every automation lives in catalog/automations.v1.json; this runner only runs what is registered there, at the level the register
gives it. A run is an event of its own ("AutomationRan", with the trigger event id, the level, what it did and a plain "why"),
idempotent (the same trigger never runs the same automation twice), loop-guarded (an automation's own events never re-trigger it,
and a chain stops at depth 3), and every subject (a person or a business) can switch any automation off.
Handlers are plain functions registered by automation id; they receive the runner, the subject and the trigger payload and return a
short record of what they did (or None to do nothing). Levels: inform writes a notice; draft writes a draft a person confirms;
auto_undo and auto act within the limits the register states. Nothing here moves money, changes credentials or completes recovery."""
import json, os, time, uuid

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
with open(os.path.join(ROOT, "catalog", "automations.v1.json"), encoding="utf-8") as f:
    _REG = json.load(f)
REGISTER = {a["id"]: a for a in _REG["automations"]}
SYSTEM = _REG["system"]            # how every automation is run, limited and explained (CONNECT UPDATE 71.2)
DAY = 86400
MAX_DEPTH = 3
def _now(n): return time.time() if n is None else n


class Flow:
    def __init__(s, c):
        s.c, s.db, s.handlers = c, c.store.db, {}
        s.db.executescript("""
        create table if not exists flow_runs(key text primary key, automation text, subject text, trigger_event text, at real, level text, did text, why text);
        create table if not exists flow_off(subject text, automation text, primary key(subject, automation)); create table if not exists flow_on(subject text, automation text, primary key(subject, automation));
        create table if not exists flow_last(automation text, subject text, at real, primary key(automation, subject));
        create table if not exists flow_settings(subject text, automation text, version integer, settings text, by text, at real, primary key(subject, automation, version));
        create table if not exists flow_paused(subject text, automation text, why text, at real, primary key(subject, automation));
        create table if not exists flow_told(key text primary key);
        create table if not exists flow_spent(subject text, month text, minor integer, primary key(subject, month));
        create table if not exists flow_caps(subject text primary key, minor integer);
        create table if not exists flow_drafts(id text primary key, subject text, automation text, did text, chain text, step integer, approvers text, state text, at real, raised real);""")
    # registration and switches
    def handle(s, automation_id, fn):
        if automation_id not in REGISTER: raise ValueError(f"{automation_id} is not in catalog/automations.v1.json: register it first")
        s.handlers[automation_id] = fn
    def set_off(s, subject, automation_id, off=True):
        if off: s.db.execute("insert or ignore into flow_off values(?,?)", (subject, automation_id))
        else: s.db.execute("delete from flow_off where subject=? and automation=?", (subject, automation_id))
        s.db.commit()
    def set_on(s, subject, automation_id, on=True):
        """An automation that is off by default (a link between two services, a message to customers) runs only after the owner switches it on."""
        if on: s.db.execute("insert or ignore into flow_on values(?,?)", (subject, automation_id)); s.db.execute("delete from flow_off where subject=? and automation=?", (subject, automation_id))
        else: s.db.execute("delete from flow_on where subject=? and automation=?", (subject, automation_id))
        s.db.commit()
    def is_on(s, subject, automation_id):
        a = REGISTER[automation_id]
        if s.db.execute("select 1 from flow_off where subject=? and automation=?", (subject, automation_id)).fetchone(): return False
        if s.db.execute("select 1 from flow_paused where subject=? and automation=?", (subject, automation_id)).fetchone(): return False
        return a.get("default", "on") == "on" or s.db.execute("select 1 from flow_on where subject=? and automation=?", (subject, automation_id)).fetchone() is not None
    # triggers
    def by_trigger(s, trigger): return [a for a in REGISTER.values() if a["trigger"] == trigger and a["id"] in s.handlers]
    def on_event(s, subject, event, now=None, depth=0):
        """Run every registered automation whose trigger is this event. `event` is a stored event row (id, type, payload)."""
        if depth >= MAX_DEPTH: return []
        ran = []
        for a in s.by_trigger(f"event:{event['type']}"):
            if event["payload"].get("by_automation") == a["id"]: continue                      # an automation never re-triggers itself
            ran += s._run(a, subject, event["payload"], trigger_event=event["id"], now=now, depth=depth)
        return ran
    def tick(s, kind, subjects, now=None):
        """Scheduled runs: kind is 'minutely', 'hourly', 'daily', 'weekly' or a daily moment such as 'closing_time' or 'shift_start'. Each (automation, subject) runs at most once per period."""
        period = {"minutely": 60, "hourly": 3600, "weekly": 7 * 86400}.get(kind, 86400)
        ran = []
        for a in s.by_trigger(f"schedule:{kind}"):
            for subject in subjects:
                last = s.db.execute("select at from flow_last where automation=? and subject=?", (a["id"], subject)).fetchone()
                if last and _now(now) - last[0] < period: continue
                s.db.execute("insert or replace into flow_last values(?,?,?)", (a["id"], subject, _now(now))); s.db.commit()
                ran += s._run(a, subject, {"period": kind}, trigger_event=f"{kind}:{int(_now(now) // period)}", now=now)
        return ran
    def metric(s, name, subject, payload, key, now=None):
        """A watched number crossed its line (trigger 'metric:<name>'): the service that owns the number says so, with a key that makes
        each crossing its own run (for example the section and the hour), so the same crossing is never acted on twice."""
        ran = []
        for a in s.by_trigger(f"metric:{name}"):
            ran += s._run(a, subject, payload, trigger_event=f"metric:{name}:{key}", now=now)
        return ran
    def user_action(s, subject, action, payload, now=None):
        """A person asked for something an automation drafts or summarises (trigger 'user:<action>'); each ask is its own run."""
        ran = []
        for a in s.by_trigger(f"user:{action}"):
            ran += s._run(a, subject, payload, trigger_event=f"user:{action}:{uuid.uuid4().hex[:8]}", now=now)
        return ran
    def _run(s, a, subject, payload, trigger_event, now=None, depth=0):
        key = f"{a['id']}|{subject}|{trigger_event}"
        if not s.is_on(subject, a["id"]) or s.db.execute("select 1 from flow_runs where key=?", (key,)).fetchone(): return []
        t = _now(now)
        if s.runs_on_day(subject, a["id"], t) >= s.daily_limit(subject, a["id"]):
            s._tell_once(subject, f"limit|{a['id']}|{int(t // DAY)}", "automation_limited", a["id"], {"limit": s.daily_limit(subject, a["id"])})
            return []
        cap = s.cap(subject)
        if cap is not None and a.get("customer_message") and s.spent(subject, t) >= cap:
            s._tell_once(subject, f"cap|{a['id']}|{_month(t)}", "automation_over_cap", a["id"], {"cap_minor": cap})
            return []
        did = s.handlers[a["id"]](s, subject, payload, t)
        if did is None: return []
        if did.get("cost_minor"):
            s.db.execute("insert into flow_spent values(?,?,?) on conflict(subject, month) do update set minor = minor + excluded.minor", (subject, _month(t), int(did["cost_minor"])))
        why = did.pop("why", a["action"])
        s.db.execute("insert into flow_runs values(?,?,?,?,?,?,?,?)", (key, a["id"], subject, trigger_event, _now(now), a["level"], json.dumps(did), why)); s.db.commit()
        s.c.store.append(subject, "server", "AutomationRan", {"automation": a["id"], "level": a["level"], "trigger": trigger_event, "did": did, "why": why, "depth": depth})
        if a["level"] == "draft": s._draft(subject, a["id"], did, t)
        s._watch_unusual(subject, a["id"], t)
        return [{"automation": a["id"], "level": a["level"], **did}]
    def emit(s, subject, type_, payload, automation_id, now=None, depth=0):
        """An event written by an automation: marked, so the same automation never loops on it, then offered to the others."""
        eid = uuid.uuid4().hex
        s.c.store.append(subject, "server", type_, {**payload, "by_automation": automation_id}, id_=eid)
        s.on_event(subject, {"id": eid, "type": type_, "payload": {**payload, "by_automation": automation_id}}, now=now, depth=depth + 1)
        return eid
    def history(s, subject, limit=50):
        """What ran for this subject and why (app.lynkomni.com/business/automations/history and the account's own view)."""
        return [{"automation": r[0], "trigger": r[1], "at": r[2], "level": r[3], "did": json.loads(r[4]), "why": r[5]}
                for r in s.db.execute("select automation,trigger_event,at,level,did,why from flow_runs where subject=? order by at desc limit ?", (subject, limit))]

    # ---- the automation system (CONNECT UPDATE 71.2, section 4 row 71.9; rules in catalog/automations.v1.json "system") -------------
    def _tell_once(s, subject, key, kind, automation_id, detail):
        """The owner is told once per key (a limit reached today, a cap reached this month, a pause)."""
        if s.db.execute("select 1 from flow_told where key=?", (f"{subject}|{key}",)).fetchone(): return False
        s.db.execute("insert into flow_told values(?)", (f"{subject}|{key}",)); s.db.commit()
        s.c.store.append(subject, "server", "AlertSent", {"kind": kind, "ref": automation_id, "detail": {**detail, "owner": s.owner(subject, automation_id)}, "by_automation": "flow"})
        return True

    def runs_on_day(s, subject, automation_id, t):
        d0 = (t // DAY) * DAY
        return s.db.execute("select count(*) from flow_runs where subject=? and automation=? and at>=? and at<?", (subject, automation_id, d0, d0 + DAY)).fetchone()[0]

    def try_on_past(s, subject, automation_id, now=None):
        """How often an automation would have been started on this business's own last days of events. Nothing is written and no
        handler runs, so the answer never acts; a schedule counts its periods, a metric or a person's ask cannot be replayed."""
        a, t = REGISTER[automation_id], _now(now)
        days = SYSTEM["try_on_past"]["days"]
        kind, _, what = a["trigger"].partition(":")
        if kind == "event":
            since = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(t - days * DAY))
            hits = [e for e in s.c.store.of(subject, what) if (e["ts"] or "") >= since and e["payload"].get("by_automation") != automation_id]
            return {"automation": automation_id, "days": days, "would_start": len(hits), "examples": [e["id"] for e in hits[:3]], "replayable": True}
        if kind == "schedule":
            per = {"minutely": 1440, "hourly": 24, "weekly": 1 / 7}.get(what, 1)
            return {"automation": automation_id, "days": days, "would_start": int(days * per), "examples": [], "replayable": True}
        return {"automation": automation_id, "days": days, "would_start": None, "examples": [], "replayable": False}

    # owners and versioned settings
    def settings(s, subject, automation_id):
        r = s.db.execute("select settings from flow_settings where subject=? and automation=? order by version desc limit 1", (subject, automation_id)).fetchone()
        return json.loads(r[0]) if r else {}
    def versions(s, subject, automation_id):
        return [{"version": v, "settings": json.loads(st), "by": by, "at": at} for v, st, by, at in
                s.db.execute("select version, settings, by, at from flow_settings where subject=? and automation=? order by version", (subject, automation_id))]
    def configure(s, subject, automation_id, by, now=None, **changes):
        """A new version of this automation's settings for this business (owner, daily_limit, chain, digest)."""
        if automation_id not in REGISTER: raise ValueError(automation_id)
        if "daily_limit" in changes:
            n = changes["daily_limit"]
            if not isinstance(n, int) or n < 0 or n > SYSTEM["limits"]["max_per_day"]: raise ValueError("a daily limit is a whole number the owner may only lower")
        if "digest" in changes and changes["digest"] and REGISTER[automation_id]["level"] != "inform": raise ValueError("only inform-level notices go into a digest")
        if "chain" in changes and (not changes["chain"] or REGISTER[automation_id]["level"] != "draft"): raise ValueError("an approval chain belongs to a draft")
        new = {**s.settings(subject, automation_id), **changes}
        v = len(s.versions(subject, automation_id)) + 1
        s.db.execute("insert into flow_settings values(?,?,?,?,?,?)", (subject, automation_id, v, json.dumps(new, sort_keys=True), by, _now(now))); s.db.commit()
        s.c.store.append(subject, "server", "automation.settings", {"automation": automation_id, "version": v, "by": by})
        return v
    def restore(s, subject, automation_id, version, by, now=None):
        """Bring back an earlier version: a new version with the old settings, so the history never loses a step."""
        old = next((x for x in s.versions(subject, automation_id) if x["version"] == version), None)
        if old is None: raise KeyError(version)
        v = len(s.versions(subject, automation_id)) + 1
        s.db.execute("insert into flow_settings values(?,?,?,?,?,?)", (subject, automation_id, v, json.dumps(old["settings"], sort_keys=True), by, _now(now))); s.db.commit()
        return v
    def owner(s, subject, automation_id): return s.settings(subject, automation_id).get("owner", "owner")
    def daily_limit(s, subject, automation_id): return s.settings(subject, automation_id).get("daily_limit", SYSTEM["limits"]["max_per_day"])

    # the monthly spending cap for runs that cost money to send
    def set_cap(s, subject, minor):
        if not isinstance(minor, int) or minor < 0: raise ValueError("a cap is whole minor units")
        s.db.execute("insert or replace into flow_caps values(?,?)", (subject, minor)); s.db.commit()
    def cap(s, subject):
        r = s.db.execute("select minor from flow_caps where subject=?", (subject,)).fetchone(); return r[0] if r else None
    def spent(s, subject, now=None):
        r = s.db.execute("select minor from flow_spent where subject=? and month=?", (subject, _month(_now(now)))).fetchone(); return r[0] if r else 0

    # unusual change: pause and tell
    def _watch_unusual(s, subject, automation_id, t):
        u = SYSTEM["unusual"]; today = s.runs_on_day(subject, automation_id, t)
        if today < u["floor"]: return
        past = sum(s.runs_on_day(subject, automation_id, t - k * DAY) for k in range(1, u["history_days"] + 1))
        usual = past / u["history_days"]
        if today > u["factor"] * max(usual, 1):
            s.db.execute("insert or ignore into flow_paused values(?,?,?,?)", (subject, automation_id, "unusual", t)); s.db.commit()
            s._tell_once(subject, f"unusual|{automation_id}|{int(t // DAY)}", "automation_unusual", automation_id, {"today": today, "usual_per_day": int(usual)})
    def paused(s, subject):
        return [{"automation": a, "why": w, "at": at} for a, w, at in s.db.execute("select automation, why, at from flow_paused where subject=?", (subject,))]
    def resume(s, subject, automation_id, by):
        """Only a person switches a paused automation back on."""
        if not by: raise PermissionError("a person resumes a paused automation")
        s.db.execute("delete from flow_paused where subject=? and automation=?", (subject, automation_id)); s.db.commit()

    # drafts: approval chains, escalation and approving several at once
    def _draft(s, subject, automation_id, did, t):
        chain = s.settings(subject, automation_id).get("chain") or ["owner"]
        s.db.execute("insert into flow_drafts values(?,?,?,?,?,?,?,?,?,?)", (uuid.uuid4().hex, subject, automation_id, json.dumps(did), json.dumps(chain), 0, "[]", "waiting", t, t)); s.db.commit()
    def drafts(s, subject, state="waiting"):
        return [{"id": i, "automation": a, "did": json.loads(d), "chain": json.loads(c), "step": st, "approvers": json.loads(ap), "state": sta}
                for i, a, d, c, st, ap, sta in s.db.execute("select id, automation, did, chain, step, approvers, state from flow_drafts where subject=? and state=? order by at", (subject, state))]
    def approve_draft(s, subject, draft_id, person, role, asked_by=None):
        r = s.db.execute("select automation, chain, step, approvers, state from flow_drafts where id=? and subject=?", (draft_id, subject)).fetchone()
        if not r or r[4] != "waiting": raise KeyError("no waiting draft")
        chain, step, approvers = json.loads(r[1]), r[2], json.loads(r[3])
        if role != chain[step]: raise PermissionError(f"this step is for the {chain[step]}")
        if person in approvers or person == asked_by: raise PermissionError("each step is a different person, never the one who asked")
        approvers.append(person); step += 1
        state = "approved" if step == len(chain) else "waiting"
        s.db.execute("update flow_drafts set step=?, approvers=?, state=? where id=?", (step, json.dumps(approvers), state, draft_id)); s.db.commit()
        s.c.store.append(subject, "server", "automation.draft_step", {"draft": draft_id, "automation": r[0], "role": role, "state": state})
        return state
    def approve_many(s, subject, draft_ids, person, role):
        """Several at once: each is checked on its own and a refusal never stops the others."""
        out = {}
        for d in draft_ids:
            try: out[d] = s.approve_draft(subject, d, person, role)
            except (KeyError, PermissionError) as e: out[d] = f"refused: {e}"
        return out
    def escalate(s, subject, now=None):
        """A draft nobody acted on goes up to the next role (or the owner); waiting never approves anything."""
        t, after = _now(now), SYSTEM["escalation"]["after_hours"] * 3600
        up = []
        for i, a, c, st, raised in s.db.execute("select id, automation, chain, step, raised from flow_drafts where subject=? and state='waiting'", (subject,)).fetchall():
            if t - raised < after: continue
            chain = json.loads(c)
            if chain[st] != "owner":                       # this step's role is skipped: the next role in the chain, or the owner
                chain = chain[:st] + chain[st + 1:] if st + 1 < len(chain) else chain[:st] + ["owner"]
            s.db.execute("update flow_drafts set chain=?, raised=? where id=?", (json.dumps(chain), t, i)); s.db.commit()
            s.c.store.append(subject, "server", "AlertSent", {"kind": "automation_escalated", "ref": a, "detail": {"draft": i, "to": chain[st]}, "by_automation": "flow"})
            up.append({"draft": i, "to": chain[st]})
        return up

    # clash warnings and the digest
    def clashes(s, subject):
        """Automations that are on and would trip over each other: both message the customer about the same trigger, or the register
        names them as a pair (clashes_with). Shown before either runs; the owner chooses which stays on."""
        on = [a for a in REGISTER.values() if a["id"] in s.handlers and s.is_on(subject, a["id"])]
        out = []
        for i, a in enumerate(on):
            for b in on[i + 1:]:
                named = b["id"] in a.get("clashes_with", []) or a["id"] in b.get("clashes_with", [])
                double = a["trigger"] == b["trigger"] and a["customer_message"] and b["customer_message"]
                if named or double:
                    out.append({"a": a["id"], "b": b["id"], "trigger": a["trigger"], "why": "named" if named else "two_customer_messages"})
        return out
    def digest(s, subject, since, now=None):
        """The day's inform-level notices of the automations the owner gathered, one line each with how many and the latest reason."""
        t = _now(now); out = []
        for a in REGISTER.values():
            if a["level"] != "inform" or not s.settings(subject, a["id"]).get("digest"): continue
            rows = s.db.execute("select why from flow_runs where subject=? and automation=? and at>=? and at<=? order by at", (subject, a["id"], since, t)).fetchall()
            if rows: out.append({"automation": a["id"], "runs": len(rows), "latest_why": rows[-1][0]})
        return out


def _month(t): return time.strftime("%Y-%m", time.gmtime(t))
