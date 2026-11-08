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
    REGISTER = {a["id"]: a for a in json.load(f)["automations"]}
MAX_DEPTH = 3
def _now(n): return time.time() if n is None else n


class Flow:
    def __init__(s, c):
        s.c, s.db, s.handlers = c, c.store.db, {}
        s.db.executescript("""
        create table if not exists flow_runs(key text primary key, automation text, subject text, trigger_event text, at real, level text, did text, why text);
        create table if not exists flow_off(subject text, automation text, primary key(subject, automation));
        create table if not exists flow_last(automation text, subject text, at real, primary key(automation, subject));""")
    # registration and switches
    def handle(s, automation_id, fn):
        if automation_id not in REGISTER: raise ValueError(f"{automation_id} is not in catalog/automations.v1.json: register it first")
        s.handlers[automation_id] = fn
    def set_off(s, subject, automation_id, off=True):
        if off: s.db.execute("insert or ignore into flow_off values(?,?)", (subject, automation_id))
        else: s.db.execute("delete from flow_off where subject=? and automation=?", (subject, automation_id))
        s.db.commit()
    def is_on(s, subject, automation_id):
        a = REGISTER[automation_id]
        row = s.db.execute("select 1 from flow_off where subject=? and automation=?", (subject, automation_id)).fetchone()
        return a.get("default", "on") == "on" and row is None
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
        """Scheduled runs: kind is 'daily' or 'weekly'. Each (automation, subject) runs at most once per period."""
        period = 86400 if kind == "daily" else 7 * 86400
        ran = []
        for a in s.by_trigger(f"schedule:{kind}"):
            for subject in subjects:
                last = s.db.execute("select at from flow_last where automation=? and subject=?", (a["id"], subject)).fetchone()
                if last and _now(now) - last[0] < period: continue
                s.db.execute("insert or replace into flow_last values(?,?,?)", (a["id"], subject, _now(now))); s.db.commit()
                ran += s._run(a, subject, {"period": kind}, trigger_event=f"{kind}:{int(_now(now) // period)}", now=now)
        return ran
    def _run(s, a, subject, payload, trigger_event, now=None, depth=0):
        key = f"{a['id']}|{subject}|{trigger_event}"
        if not s.is_on(subject, a["id"]) or s.db.execute("select 1 from flow_runs where key=?", (key,)).fetchone(): return []
        did = s.handlers[a["id"]](s, subject, payload, _now(now))
        if did is None: return []
        why = did.pop("why", a["action"])
        s.db.execute("insert into flow_runs values(?,?,?,?,?,?,?,?)", (key, a["id"], subject, trigger_event, _now(now), a["level"], json.dumps(did), why)); s.db.commit()
        s.c.store.append(subject, "server", "AutomationRan", {"automation": a["id"], "level": a["level"], "trigger": trigger_event, "did": did, "why": why, "depth": depth})
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
