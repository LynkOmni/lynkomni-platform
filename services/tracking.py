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
import json, re, math, os, time

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
        s.engine = s.reg.get("engine", {})
        s.applied = set()    # event ids already applied: an event seen once is never counted twice
        s.extra_defs = {}    # (owner, kind) -> [{"id", "label", "customer"}]: a business's own extra steps

    # ---- records
    def _rec(s, kind, record, owner):
        r = s.recs.get((kind, record))
        if r is None:
            r = s.recs[(kind, record)] = {"owner": owner, "reached": {}, "order": [], "seen": {}, "eta": None, "parent": None, "children": [], "progress": None,
                                          "clash": [], "extra": [], "practice": False, "ended_at": None}
        elif owner and not r["owner"]:
            r["owner"] = owner
        return r

    def _ended(s, kind, r):
        steps = s.kinds[kind]["steps"]
        return any(steps[i].get("terminal") for i in r["reached"])

    def _reach(s, kind, record, i, at, changes):
        r = s.recs[(kind, record)]
        step = s.kinds[kind]["steps"][i]
        if s._ended(kind, r):
            end_i = r["order"][-1]
            if step.get("terminal") and i != end_i and i not in r["reached"] and not any(c["step"] == step["id"] for c in r["clash"]):
                r["clash"].append({"step": step["id"], "at": at})       # two endings: the earlier stands, this one waits for a person
            elif i not in r["reached"] and at is not None and r["reached"].get(end_i) is not None and at < r["reached"][end_i] and i < end_i:
                r["reached"][i] = at; r["order"].insert(len(r["order"]) - 1, i)   # a late event lands in its true place, never current
            return                                   # nothing else moves after an ending
        cur_i = r["order"][-1] if r["order"] else None
        if (i not in r["reached"] and cur_i is not None and i < cur_i and at is not None and r["reached"].get(cur_i) is not None
                and at < r["reached"][cur_i] and not step.get("terminal")):
            r["reached"][i] = at; r["order"].insert(len(r["order"]) - 1, i)      # an earlier step arriving late stays in the past
            return
        if i in r["reached"]:
            # a step counts once, unless the register says it can come again (a queue ticket waits again after Put back or Send to)
            if not step.get("again") or r["order"][-1] == i: return
            r["order"].remove(i)
        r["reached"][i] = at
        r["order"].append(i)                         # arrival order decides the current step (device clocks can disagree)
        if step.get("terminal"):
            r["progress"] = None                     # the trip is over: positions and progress are gone
            r["ended_at"] = at
        changes.append({"kind": kind, "record": record, "step": step["id"], "state": step["state"], "customer": bool(step.get("customer")), "owner": r["owner"], "at": at})
        for pk, pi in s.by_child.get((kind, step["id"]), []):      # a child's step moves its parent
            if r["parent"] and r["parent"][0] == pk:
                s._reach(pk, r["parent"][1], pi, at, changes)

    # ---- input: events from the log, and states from services that keep their own
    def apply(s, event, owner=None):
        etype, p, at = event["type"], event.get("payload", {}), epoch(event.get("at"))
        changes = []
        eid = event.get("id")
        if eid is not None:
            if eid in s.applied: return changes      # the same event twice (a re-sent offline batch) counts once
            s.applied.add(eid)
        if etype == "TrackingStepMarked":
            return s._extra(p, at, owner)
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
            if p.get("practice") is True: r["practice"] = True                  # practice trackers stay out of counts and messages
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
        extra = [x for x in r["extra"] if audience != "customer" or x["customer"]]
        if extra: v["extra"] = [{"id": x["id"], "label": x["label"], "at": iso(x["at"])} for x in sorted(extra, key=lambda x: (x["at"] or 0, x["id"]))]
        if audience != "customer":
            v["risk"] = s.risk(kind, record, now)
            if r["clash"]: v["clash"] = [c["step"] for c in r["clash"]]
            if r["practice"]: v["practice"] = True
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


    # ---- the section 4 engine upgrade (TRACKING UPDATE 72.3): promises, risk, exceptions, the control tower, scanning, partners
    def set_extra_steps(s, owner, kind, steps):
        """A business's own extra steps for a kind (at most engine.extra_steps_max): shown on its screens, never the chip or an ending."""
        if kind not in s.kinds: raise ValueError("unknown tracking kind")
        if len(steps) > s.engine.get("extra_steps_max", 5): raise ValueError("too many extra steps")
        ids = [x["id"] for x in steps]
        if len(set(ids)) != len(ids) or any(not EXTRA_ID.fullmatch(i) or i in {st["id"] for st in s.kinds[kind]["steps"]} for i in ids):
            raise ValueError("an extra step needs its own id (lowercase letters, digits, underscore) that no registered step uses")
        s.extra_defs[(owner, kind)] = [{"id": x["id"], "label": str(x["label"])[:60], "customer": bool(x.get("customer"))} for x in steps]

    def _extra(s, p, at, owner):
        kind, record, xid = p.get("kind"), p.get("record"), p.get("extra_step")
        r = s.recs.get((kind, record))
        if r is None or s._ended(kind, r): return []
        d = next((x for x in s.extra_defs.get((r["owner"] or owner, kind), []) if x["id"] == xid), None)
        if d is None or any(x["id"] == xid for x in r["extra"]): return []
        r["extra"].append({"id": xid, "label": d["label"], "customer": d["customer"], "at": at})
        return []                                     # an extra step never changes the chip and sends no message

    def risk(s, kind, record, now, hours=None):
        """on_time, at_risk or late against the current step's promised time; None when the kind promises nothing or it ended."""
        k, r = s.kinds[kind], s.recs.get((kind, record))
        if r is None or not r["order"] or s._ended(kind, r): return None
        cur = k["steps"][r["order"][-1]]["id"]
        target = k.get("promise", {}).get(cur)
        entered = r["reached"].get(r["order"][-1])
        if target is None or entered is None: return None
        spent = working_minutes(entered, now, hours) if k.get("working_time") and hours else max(0, int(now - entered) // 60)
        if spent >= target: return "late"
        return "at_risk" if spent * 10000 >= target * s.engine.get("at_risk_bp", 8000) else "on_time"

    def _stuck(s, kind, r, now, hours):
        k = s.kinds[kind]; cur = k["steps"][r["order"][-1]]["id"]
        target = k.get("promise", {}).get(cur); entered = r["reached"].get(r["order"][-1])
        if target is None or entered is None: return False
        spent = working_minutes(entered, now, hours) if k.get("working_time") and hours else max(0, int(now - entered) // 60)
        return spent >= target * s.engine.get("stuck_factor", 2)

    def exceptions(s, owner, now, hours=None):
        """What needs a person, worst first: two endings that clash, failed, stuck, late, at risk, waiting on the customer."""
        order = ["clash", "failed", "stuck", "late", "at_risk", "waiting_on_customer"]
        out = []
        for (kind, record), r in s.recs.items():
            if r["owner"] != owner or r["practice"] or not r["order"]: continue
            k = s.kinds[kind]; cur = k["steps"][r["order"][-1]]
            if r["clash"]: why = "clash"
            elif s._ended(kind, r): why = "failed" if cur["state"] == "failed" else None
            elif s._stuck(kind, r, now, hours): why = "stuck"
            else:
                rk = s.risk(kind, record, now, hours)
                why = rk if rk in ("late", "at_risk") else ("waiting_on_customer" if cur["id"] in k.get("waits_on_customer", []) else None)
            if why: out.append({"kind": kind, "record": record, "step": cur["id"], "why": why, "since": iso(r["reached"].get(r["order"][-1]))})
        return sorted(out, key=lambda x: (order.index(x["why"]), x["since"] or "", x["kind"], x["record"]))

    def tower(s, owner, now, kind=None, step=None, hours=None):
        """The control tower: everything in motion for an owner, late first, then at risk, then the rest, oldest first; practice left out."""
        rank = {"late": 0, "at_risk": 1, "on_time": 2, None: 3}
        rows = []
        for (k_id, record), r in s.recs.items():
            if r["owner"] != owner or r["practice"] or not r["order"] or s._ended(k_id, r): continue
            cur = s.kinds[k_id]["steps"][r["order"][-1]]
            if (kind and k_id != kind) or (step and cur["id"] != step): continue
            rows.append({"kind": k_id, "record": record, "step": cur["id"], "state": cur["state"], "risk": s.risk(k_id, record, now, hours),
                         "since": iso(r["reached"].get(r["order"][-1]))})
        rows.sort(key=lambda x: (rank[x["risk"]], x["since"] or "", x["kind"], x["record"]))
        counts = {key: sum(1 for x in rows if x["risk"] == key) for key in ("late", "at_risk", "on_time")}
        return {"rows": rows, "counts": counts, "total": len(rows)}

    def partner_event(s, kind, partner, code):
        """The event LynkOmni's cloud writes for a partner's status; None for a status the register does not know (listed for staff)."""
        return s.kinds[kind].get("partner_status", {}).get(partner, {}).get(code)

    def scan(s, kind, record, step, proof=None, client_events=None):
        """May a scan on a device move this item to this step? Returns the event the device writes, or the reasons it may not."""
        k = s.kinds[kind]; r = s.recs.get((kind, record)); why = []
        rule = k.get("scan", {}).get(step)
        if rule is None: return {"ok": False, "event": None, "why": ["not_scannable"]}
        if client_events is not None and rule["event"] not in client_events: why.append("cloud_only")
        if r is not None and s._ended(kind, r): why.append("ended")
        if rule.get("proof") and proof not in rule["proof"]: why.append("needs_proof")
        for c in k.get("checks", {}).get(step, []):
            if c.startswith("after:"):
                need = next((i for i, st in enumerate(k["steps"]) if st["id"] == c[6:]), None)
                if r is None or need not in r["reached"]: why.append(c)
        return {"ok": not why, "event": None if why else rule["event"], "why": why}

    def prune(s, now):
        """Ended trackers are kept engine.keep_days (or the kind's keep_days) after their ending, then removed. Returns how many."""
        gone = [key for key, r in s.recs.items() if r["ended_at"] is not None and s._ended(key[0], r)
                and now > r["ended_at"] + 86400 * s.kinds[key[0]].get("keep_days", s.engine.get("keep_days", 400))]
        for key in gone: del s.recs[key]
        return len(gone)


EXTRA_ID = re.compile(r"[a-z][a-z0-9_]{1,30}")


def promise_minutes(base, load, capacity, per_round):
    """A promise from real capacity: base minutes plus whole rounds of the waiting work (rounded up) times one round's minutes."""
    if capacity < 1 or base < 0 or load < 0 or per_round < 0: raise ValueError("capacity at least 1, nothing below zero")
    return base + (-(-load // capacity)) * per_round


def working_minutes(start, end, hours):
    """Whole minutes between two times that fall inside opening hours. hours = {"offset_min": minutes east of UTC, "days":
    {"0": [[open, close], ...], ...}} with Monday = "0" and open and close in minutes after local midnight."""
    if hours is None or end <= start: return max(0, (end - start) // 60) if hours is None else 0
    off = int(hours.get("offset_min", 0)) * 60
    total, day0 = 0, (start + off) // 86400
    for day in range(day0, (end + off) // 86400 + 1):
        base = day * 86400 - off
        for o, c in hours.get("days", {}).get(str((day + 3) % 7), []):       # 1 January 1970 was a Thursday (3)
            a, b = max(start, base + o * 60), min(end, base + c * 60)
            if b > a: total += (b - a) // 60
    return total


QUIET_HOURS = (21, 7)                       # local time: messages wait from 21:00 until 07:00 ...
ACT_NOW_STEPS = ("on_the_way", "ready", "failed")   # ... except a step the customer must act on now


class PlatformTracking:
    """Tracking for the whole platform: follows the event store as it grows, writes TrackingStepReached for every step (LynkFlow
    runs order-updates and the owner's alerts from it), and records how a customer chose to hear (TrackingSubscribed)."""
    def __init__(s, platform):
        s.p, s.t = platform, Tracking()
        s.from_service = {x["event"]: x for x in (s.t.reg.get("from_service_events") or {}).get("events", [])}
        platform.c.store.observers.append(s._observe)
    def _observe(s, subject, type_, payload, ts):
        if type_ in ("TrackingStepReached", "TrackingUpdateSent", "AutomationRan"):
            return
        changes = s.t.apply({"type": type_, "payload": payload, "at": ts}, owner=subject)
        m = s.from_service.get(type_)                     # a service that keeps its own state reports it (from_service_events)
        if m and payload.get("state") and payload.get(m["record"]):
            changes = changes + s.t.feed_state(m["kind"], payload[m["record"]], payload["state"], ts, owner=subject)
        for ch in changes:
            s.p.cloud.signal(subject, "TrackingStepReached", {k: ch[k] for k in ("kind", "record", "step", "state", "customer")}, now=ch["at"])
    def set_extra_steps(s, owner, kind, steps):
        """A business's own extra steps (TRACKING UPDATE 72.3, at most five per kind); marked later by TrackingStepMarked."""
        s.t.set_extra_steps(owner, kind, steps)

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
