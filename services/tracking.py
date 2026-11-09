"""LynkOmni tracking (owner request 9 November 2026): one engine for everything that moves through steps and that someone
waits on. It follows the event log (and, for services that keep their own state such as invoices, that state) using the
register in catalog/tracking.v1.json, so every screen, message and automation reads the same steps.

    t = Tracking()
    t.apply({"type": "DeliveryRequested", "payload": {...}, "at": 1700000000}, owner="merchant-1")
    t.view("delivery", delivery_id, audience="customer", now=...)

A step is reached only by the event that proves it. The chip state is one of queued, sent, accepted, confirmed, failed.
Customers see customer steps only, never an address, a phone number, a person's name or coordinates. Live progress
(deliveries) is a share and an arrival time from positions held only in memory during the trip, deleted when it ends.
The TypeScript port (ts/src/tracking.ts) must agree with this file: tools/tracking_vectors.py writes the shared vectors."""
import json, math, os, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGISTER = os.path.join(ROOT, "catalog", "tracking.v1.json")
STATES = ("queued", "sent", "accepted", "confirmed", "failed")
AUDIENCES = ("merchant", "customer", "person", "staff")
PROGRESS_STEP = 0.05          # progress is shown in steps of 5%, never a precise position


def register(path=REGISTER):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def iso(ts):
    return None if ts is None else time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ts))


def epoch(value):
    """A timestamp from the log: seconds, or an ISO-8601 UTC text ('2026-11-09T10:00:00Z')."""
    if value is None or isinstance(value, (int, float)):
        return value
    import calendar
    return calendar.timegm(time.strptime(value[:19], "%Y-%m-%dT%H:%M:%S"))


class Tracking:
    def __init__(s, reg=None):
        s.reg = reg or register()
        s.kinds = {k["id"]: k for k in s.reg["kinds"]}
        s.by_event, s.by_state, s.by_child = {}, {}, {}
        for k in s.reg["kinds"]:
            for i, st in enumerate(k["steps"]):
                for rule in st["on"]:
                    if "event" in rule: s.by_event.setdefault(rule["event"], []).append((k["id"], i, rule))
                    elif "state" in rule: s.by_state.setdefault((k["id"], rule["state"]), []).append(i)
                    elif "child" in rule: s.by_child.setdefault((rule["child"], rule["step"]), []).append((k["id"], i))
            for a in k.get("aliases", []): s.by_event.setdefault(a["event"], [])
        s.recs = {}          # (kind, record) -> {"owner", "reached": {step index: time}, "seen": {}, "eta", "parent", "children", "progress"}
        s.alias = {}         # (kind, alias value) -> record
        s.lines = {}         # (kind, record, rule key) -> set of unique values (all_of rules)
        s.subs = {}          # (kind, record) -> {"channel", "lang"}: how the customer chose to hear about it (TrackingSubscribed)

    # ---- records
    def _rec(s, kind, record, owner):
        r = s.recs.get((kind, record))
        if r is None:
            r = s.recs[(kind, record)] = {"owner": owner, "reached": {}, "order": [], "seen": {}, "eta": None, "parent": None, "children": [], "progress": None}
        elif owner and not r["owner"]:
            r["owner"] = owner
        return r

    def _ended(s, kind, r):
        steps = s.kinds[kind]["steps"]
        return any(steps[i].get("terminal") for i in r["reached"])

    def _reach(s, kind, record, i, at, changes):
        r = s.recs[(kind, record)]
        if i in r["reached"] or s._ended(kind, r):
            return                                   # a step counts once; nothing moves after an ending
        r["reached"][i] = at
        r["order"].append(i)                         # arrival order decides the current step (device clocks can disagree)
        step = s.kinds[kind]["steps"][i]
        if step.get("terminal"):
            r["progress"] = None                     # the trip is over: positions and progress are gone
        changes.append({"kind": kind, "record": record, "step": step["id"], "state": step["state"], "customer": bool(step.get("customer")), "owner": r["owner"], "at": at})
        for pk, pi in s.by_child.get((kind, step["id"]), []):      # a child's step moves its parent
            if r["parent"] and r["parent"][0] == pk:
                s._reach(pk, r["parent"][1], pi, at, changes)

    # ---- input: events from the log, and states from services that keep their own
    def apply(s, event, owner=None):
        etype, p, at = event["type"], event.get("payload", {}), epoch(event.get("at"))
        changes = []
        if etype == "TrackingSubscribed" and p.get("kind") in s.kinds:
            s.subs[(p["kind"], p["record"])] = {"channel": p["channel"], "lang": p.get("lang", "en")}
            return changes
        for k in s.reg["kinds"]:
            for a in k.get("aliases", []):
                if a["event"] == etype and a["from"] in p and a["to"] in p:
                    s.alias[(k["id"], p[a["from"]])] = p[a["to"]]
            par = k.get("parent")
            if par and par["event"] == etype and k["key"] in p and p.get(par["field"]):
                child = s._rec(k["id"], p[k["key"]], owner)
                parent = s._rec(par["kind"], p[par["field"]], owner)
                child["parent"] = (par["kind"], p[par["field"]])
                if (k["id"], p[k["key"]]) not in parent["children"]: parent["children"].append((k["id"], p[k["key"]]))
        for kind, i, rule in s.by_event.get(etype, []):
            k = s.kinds[kind]
            record = p.get(k["key"])
            if record is None:
                record = next((s.alias.get((kind, p[a["from"]])) for a in k.get("aliases", []) if a["from"] in p), None)
            if record is None:
                continue
            r = s._rec(kind, record, owner)
            if any(etype == e["event"] and e.get("field") in p for e in k.get("eta", [])):
                r["eta"] = epoch(next(p[e["field"]] for e in k["eta"] if e["event"] == etype and e.get("field") in p))
            when = rule.get("when")
            if when and not all(p.get(f) in vals for f, vals in when.items()):
                continue
            r["seen"].setdefault(etype, p)
            allof = rule.get("all_of")
            if allof:
                seen = s.lines.setdefault((kind, record, etype), set())
                seen.add(p.get(allof["unique"]))
                source = r["seen"].get(allof["from"])
                if not source or len(seen) < len(source.get(allof["list"], [])):
                    continue
            s._reach(kind, record, i, at, changes)
        return changes

    def feed_state(s, kind, record, state, at, owner=None):
        """For services that keep their own state (invoices): the state the service reports moves the tracker."""
        if kind not in s.kinds:
            raise ValueError(f"unknown tracking kind {kind}")
        s._rec(kind, record, owner)
        changes = []
        for i in s.by_state.get((kind, state), []):
            s._reach(kind, record, i, epoch(at), changes)
        return changes

    def set_eta(s, kind, record, eta):
        s.recs[(kind, record)]["eta"] = epoch(eta)

    def set_progress(s, kind, record, share, eta=None):
        """Live progress of a trip, from positions the partner reports or the shop's rider shares with consent. Only while the
        trip is on its way; rounded to 5%; deleted when it ends. Returns False when progress may not be shown."""
        k = s.kinds[kind]; r = s.recs.get((kind, record))
        if not k.get("live_progress") or r is None or s._ended(kind, r) or s._current(kind, r) != "on_the_way":
            return False
        share = max(0.0, min(1.0, float(share)))
        r["progress"] = math.floor(share * 20 + 0.5) * 5 / 100      # whole steps of 5%, rounded half up (same in TypeScript)
        if eta is not None: r["eta"] = epoch(eta)
        return True

    # ---- output
    def _current(s, kind, r):
        return s.kinds[kind]["steps"][r["order"][-1]]["id"] if r["order"] else None

    def state(s, kind, record):
        r = s.recs.get((kind, record))
        if r is None or not r["order"]: return "queued"
        return s.kinds[kind]["steps"][r["order"][-1]]["state"]

    def view(s, kind, record, audience="merchant", now=None, public_id=None):
        if audience not in AUDIENCES: raise ValueError("unknown audience")
        k, r = s.kinds[kind], s.recs.get((kind, record))
        if r is None: return None
        now = time.time() if now is None else now
        steps, ended = k["steps"], s._ended(kind, r)
        kids = {c[0] for c in r["children"]}
        def eligible(st):
            return all(rule.get("child") is None or rule["child"] in kids for rule in st["on"])
        out, chose_end = [], False
        terminal_order = sorted(range(len(steps)), key=lambda i: (0 if any(rule.get("child") in kids for rule in steps[i]["on"]) else 1, i))
        expected_end = None
        if not ended:
            expected_end = next((i for i in terminal_order if steps[i].get("terminal") and not steps[i].get("optional") and steps[i]["state"] != "failed" and eligible(steps[i])), None)
        cur = s._current(kind, r)
        for i, st in enumerate(steps):
            if audience == "customer" and not st.get("customer"): continue
            done = i in r["reached"]
            if st.get("terminal"):
                if not (done or i == expected_end): continue
            elif not done and (ended or st.get("optional") or st["state"] == "failed" or not eligible(st)):
                continue
            out.append({"id": st["id"], "label": f"trk_{st['id']}", "state": st["state"], "done": done, "current": st["id"] == cur,
                        "at": iso(r["reached"].get(i))})
        eta = r["eta"] if not ended else None
        v = {"kind": kind, "label": f"trk_k_{kind}", "state": s.state(kind, record), "step": cur, "ended": ended, "steps": out,
             "eta": iso(eta), "late": bool(eta is not None and now > eta and not ended),
             "progress": r["progress"] if k.get("live_progress") and not ended else None}
        if audience != "customer":
            v["record"] = record
            v["children"] = [{"kind": c[0], "record": c[1], "state": s.state(*c), "step": s._current(c[0], s.recs[c])} for c in r["children"]]
            if r["parent"]: v["parent"] = {"kind": r["parent"][0], "record": r["parent"][1]}
        else:
            v["children"] = [s.view(c[0], c[1], "customer", now) for c in r["children"]]
        if public_id: v["public_id"] = public_id
        return v

    def active(s, owner=None, kinds=None, now=None):
        """Trackers still moving (not ended), newest first: what an owner's Home shows as "On the way"."""
        out = []
        for (kind, record), r in s.recs.items():
            if (owner is None or r["owner"] == owner) and (kinds is None or kind in kinds) and r["reached"] and not s._ended(kind, r):
                out.append((max(v or 0 for v in r["reached"].values()), kind, record))
        return [s.view(k, rec, "merchant", now) for _, k, rec in sorted(out, key=lambda x: (-x[0], x[1], x[2]))]

    def late(s, now, owner=None):
        return [v for v in s.active(owner, now=now) if v["late"]]


QUIET_HOURS = (21, 7)                       # local time: messages wait from 21:00 until 07:00 ...
ACT_NOW_STEPS = ("on_the_way", "ready", "failed")   # ... except a step the customer must act on now


class PlatformTracking:
    """Tracking for the whole platform: follows the event store as it grows, writes TrackingStepReached for every step (LynkFlow
    runs order-updates and the owner's alerts from it), and records how a customer chose to hear (TrackingSubscribed)."""
    def __init__(s, platform):
        s.p, s.t = platform, Tracking()
        platform.c.store.observers.append(s._observe)
    def _observe(s, subject, type_, payload, ts):
        if type_ in ("TrackingStepReached", "TrackingUpdateSent", "AutomationRan"):
            return
        for ch in s.t.apply({"type": type_, "payload": payload, "at": ts}, owner=subject):
            s.p.cloud.signal(subject, "TrackingStepReached", {k: ch[k] for k in ("kind", "record", "step", "state", "customer")}, now=ch["at"])
    def subscribe(s, owner, kind, record, channel, lang="en", now=None):
        """The customer chose a way to hear about this record (the tracking page's "Tell me each step"); the contact itself stays in the PII vault."""
        if kind not in s.t.kinds: raise ValueError("unknown tracking kind")
        if channel not in ("sms", "chat", "push", "email"): raise ValueError("unknown channel")
        s.p.cloud.signal(owner, "TrackingSubscribed", {"kind": kind, "record": record, "channel": channel, "lang": lang}, now=now)
    def view(s, kind, record, audience="merchant", now=None):
        pid = None
        k = s.t.kinds.get(kind)
        if k and k.get("record") and audience in ("customer", "person"):
            pid = s.p.ids.assign(k["record"], record)          # the public id the customer's address uses
        return s.t.view(kind, record, audience, now, public_id=pid)
    def by_public_id(s, public_id, now=None):
        """The customer's tracking page (no account): the public id leads to the record; only customer steps come back."""
        found = s.p.ids.lookup(public_id)
        if not found: return None
        for k in s.t.reg["kinds"]:
            if k.get("record") == found["type"] and (k["id"], found["internal_id"]) in s.t.recs:
                return s.view(k["id"], found["internal_id"], "customer", now)
        return None
    @staticmethod
    def quiet_until(now, tz="UTC"):
        """When quiet hours end, if `now` falls in them in time zone `tz` (the business's country pack); otherwise None."""
        from datetime import datetime, timedelta, timezone
        try:
            from zoneinfo import ZoneInfo
            zone = ZoneInfo(tz)
        except Exception:
            zone = timezone.utc
        local = datetime.fromtimestamp(now, tz=zone)
        start, end = QUIET_HOURS
        if end <= local.hour < start: return None
        wake = local.replace(hour=end, minute=0, second=0, microsecond=0)
        if local.hour >= start: wake += timedelta(days=1)
        return int(wake.timestamp())
