"""LynkCRM in the cloud (OFFICE UPDATE, master blueprint 66.4; section 4 step D3), on the rules of core/crm.py.

Records for every kind of entity (public id LOCST-), own fields with their limit and checks, tags and saved segments, relations,
deals on the contract's five stages with the forecast, lead scores as labelled suggestions, cases with promised answer times,
handing over, duplicate finding and merging with undo, consent per channel, a person's data requests, the one full picture and
field visits. Names and contact details stay in the PII vault and the record store: the record keeps only vault references and
fingerprints, and no event carries them. Customer data is never sold. Tiers follow 66.7 (services/billing.py FEATURES lynkcrm)."""
import hashlib, time, uuid

from core import crm as C
from core.regions import country
from services.improvements import Table

SENSITIVE_KINDS = {"student": "children", "guardian": "children", "citizen_case": "citizens"}


def _fp(value):
    """A fingerprint to find the same email or phone written twice, never the value itself."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:24]


class Customers:
    def __init__(s, p, now=time.time):
        s.p, s.now, db = p, now, p.c.store.db
        s.recs, s.fields, s.segs, s.deals = Table(db, "crm_recs"), Table(db, "crm_fields"), Table(db, "crm_segs"), Table(db, "crm_deals")
        s.cases, s.merges, s.requests = Table(db, "crm_cases"), Table(db, "crm_merges"), Table(db, "crm_requests")

    def ent(s, m):
        return s.p.billing.entitlement(m, "lynkcrm")

    def _tier(s, m):
        return s.p.billing.tier(m, "lynkcrm")

    def _need(s, m, feature, words):
        if not s.ent(m).get(feature):
            raise PermissionError(f"{words} need a higher LynkCRM plan")

    def _emit(s, m, type_, payload):
        s.p.c.store.append(m, "server", type_, payload)

    # ---- records -------------------------------------------------------------------------------------------------------------
    def define_field(s, m, fid, ftype, required=False, hidden_from=()):
        have = [k for k, _ in s.fields.items() if k.startswith(m + "|")]
        t = s._tier(m)
        limit = C.field_limit(t if t in C.CRM["fields"]["limits"] else "max")      # Enterprise has Max's fields and more
        if limit is not None and len(have) >= limit:
            raise PermissionError("own fields limit reached for this LynkCRM plan")
        if ftype not in C.CRM["fields"]["types"]:
            raise ValueError("unknown field type")
        if hidden_from:
            s._need(m, "hidden_fields", "fields hidden by role")
        s.fields.put(f"{m}|{fid}", {"id": fid, "type": ftype, "required": required, "hidden_from": list(hidden_from)})
        return fid

    def _defs(s, m):
        return [v for k, v in s.fields.items() if k.startswith(m + "|")]

    def create(s, m, by, kind, entity_kind="business", name=None, email=None, phone=None, org=None, fields=None, tags=(), team=None, source="hand"):
        own = (s.ent(m).get("own_record_kinds") and [kind]) or []
        if kind not in C.kinds_for(entity_kind, own):
            raise PermissionError(f"{kind} records are not part of this workspace")
        pack = country(s.p.c.profile(m)["country"])
        if kind in SENSITIVE_KINDS and not C.sensitive_allowed(SENSITIVE_KINDS[kind], entity_kind, pack):
            raise PermissionError("this kind of record is not allowed here")
        fields = dict(fields or {})
        defs = {d["id"]: d for d in s._defs(m)}
        for k, v in fields.items():
            if k not in defs or not C.field_value_ok(defs[k]["type"], v):
                raise ValueError(f"field {k} is not valid")
        missing = C.required_missing(list(defs.values()), fields)
        if missing:
            raise ValueError("required fields: " + ", ".join(missing))
        limit = s.ent(m).get("customers")
        if limit is not None and sum(1 for k, v in s.recs.items() if v["merchant"] == m and not v.get("merged_into")) >= limit:
            raise PermissionError("customer limit for this LynkCRM plan reached")
        rid = s.p.ids.assign("CST", uuid.uuid4().hex)
        rec = {"merchant": m, "kind": kind, "owner": by, "team": team, "org": org, "fields": fields, "tags": sorted(set(tags)),
               "name_ref": s.p.vault.put(rid, "customer_name", name) if name else None,
               "email_ref": s.p.vault.put(rid, "email", email) if email else None, "phone_ref": s.p.vault.put(rid, "phone", phone) if phone else None,
               "email_fp": _fp(email.strip().lower()) if email else None, "phone_fp": _fp("".join(ch for ch in phone if ch.isdigit())) if phone else None,
               "name_key": C.normalise(name) if name else None, "created": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(s.now())),
               "consents": [], "history": [], "activities": [],
               "seq": sum(1 for _, v in s.recs.items() if v["merchant"] == m)}     # the order made, so the oldest is known within one second
        s.recs.put(rid, rec)
        s._emit(m, "crm.record_created", {"record": rid, "kind": kind, "source": source})
        return rid

    def update(s, m, rid, by, fields):
        r = s.recs[rid]; defs = {d["id"]: d for d in s._defs(m)}
        for k, v in fields.items():
            if k not in defs or not C.field_value_ok(defs[k]["type"], v):
                raise ValueError(f"field {k} is not valid")
        r["history"] = r["history"] + [{"by": by, "at": s.now(), "before": {k: r["fields"].get(k) for k in fields}, "after": dict(fields)}]
        r["fields"] = {**r["fields"], **fields}
        return r["fields"]

    def view(s, m, viewer, rid):
        """What a viewer may see of a record: nothing if access says no; fields hidden from their role are left out."""
        r = s.recs[rid]
        if not C.may_see(viewer, {"owner": r["owner"], "team": r["team"]}, (s.ent(m).get("teams") and "team") or "all"):
            raise PermissionError("not your record")
        shown = set(C.visible_fields(s._defs(m), viewer["role"]))
        return {"id": rid, "kind": r["kind"], "tags": r["tags"], "fields": {k: v for k, v in r["fields"].items() if k in shown}}

    # ---- segments ------------------------------------------------------------------------------------------------------------
    def save_segment(s, m, name, conditions):
        s._need(m, "saved_segments", "saved segments")
        s.segs.put(f"{m}|{name}", {"conditions": conditions}); return name

    def segment(s, m, name):
        conds = s.segs[f"{m}|{name}"]["conditions"]
        return C.segment([{"id": k, **v} for k, v in s.recs.items() if v["merchant"] == m and not v.get("merged_into")], conds)

    # ---- selling -------------------------------------------------------------------------------------------------------------
    def create_deal(s, m, rid, amount_minor, pipeline="main"):
        did = uuid.uuid4().hex
        s.deals.put(did, {"merchant": m, "record": rid, "amount": amount_minor, "stage": "new", "pipeline": pipeline})
        s._emit(m, "deal.stage_changed", {"deal": did, "stage": "new", "value_minor": amount_minor, "customer": rid})
        return did

    def move_deal(s, m, did, stage, reason=None):
        d = s.deals[did]
        if not C.stage_move(d["stage"], stage):
            raise ValueError(f"a deal cannot go from {d['stage']} to {stage}")
        if not C.close_ok(stage, reason):
            raise ValueError("a won or lost deal names its reason")
        d["stage"] = stage
        s._emit(m, "deal.stage_changed", {"deal": did, "stage": stage, "value_minor": d["amount"], "customer": d["record"], "reason": reason})
        return stage

    def forecast(s, m, chances=None):
        return C.forecast([{"id": k, "amount": v["amount"], "stage": v["stage"]} for k, v in s.deals.items() if v["merchant"] == m], chances)

    def lead_score(s, m, signals):
        s._need(m, "lead_scores", "lead scores")
        return C.lead_score(signals)

    # ---- service -------------------------------------------------------------------------------------------------------------
    def open_case(s, m, rid, priority="normal", hour=0, own_hours=None):
        s._need(m, "cases", "cases")
        if own_hours is not None:
            s._need(m, "promised_times", "your own promised answer times")
        cid = uuid.uuid4().hex
        s.cases.put(cid, {"merchant": m, "record": rid, "priority": priority, "opened": hour, "paused": 0, "own": own_hours, "state": "open", "answered": False})
        s._emit(m, "case.opened", {"case": cid, "record": rid, "priority": priority})
        return {"case": cid, "due_hour": C.case_due(hour, priority, 0, own_hours)}

    def late_cases(s, m, hour):
        return [k for k, v in s.cases.items() if v["merchant"] == m and v["state"] not in ("solved", "closed")
                and C.case_late(hour, v["opened"], v["priority"], v["answered"], v["paused"], v["own"])]

    def case_state(s, m, cid, state, hour=0):
        c = s.cases[cid]
        if state not in C.CRM["cases"]["states"]:
            raise ValueError("unknown state")
        c["answered"] = c["answered"] or state != "open"
        c["state"] = state
        s._emit(m, "case.state", {"case": cid, "state": state, "late": C.case_late(hour, c["opened"], c["priority"], False, c["paused"], c["own"])})
        return state

    def hand_over(s, m, rid, to_user, reason="staff_change"):
        s._need(m, "handover", "handing over a customer")
        r = s.recs[rid]; r["history"] = r["history"] + [{"handed_from": r["owner"], "to": to_user, "at": s.now()}]; r["owner"] = to_user
        s._emit(m, "crm.handed_over", {"record": rid, "to": to_user, "reason": reason})
        return to_user

    # ---- clean records -------------------------------------------------------------------------------------------------------
    def duplicates(s, m):
        rows = [{"id": k, "email": v["email_fp"], "phone_fp": v["phone_fp"], "name": v["name_key"], "org": v["org"] or "", "created": v["created"]}
                for k, v in s.recs.items() if v["merchant"] == m and not v.get("merged_into")]
        age = {k: (v["created"], v.get("seq", 0)) for k, v in s.recs.items() if v["merchant"] == m}
        return [sorted(g, key=lambda i: age[i]) for g in C.duplicates([{k: x for k, x in r.items() if x} for r in rows])]   # oldest first

    def merge(s, m, ids, by):
        recs = [{"id": i, **s.recs[i]} for i in ids]
        out = C.merge([{"id": r["id"], "created": f'{r["created"]}#{r.get("seq", 0):09d}', "fields": r["fields"], "tags": r["tags"], "activities": r["activities"]} for r in recs])
        keep = s.recs[out["id"]]
        s.merges.put(out["id"] + "|" + str(s.now()), {"before": {r["id"]: {k: v for k, v in r.items() if k != "id"} for r in recs}, "at": s.now()})
        keep["fields"], keep["tags"], keep["activities"] = out["fields"], out["tags"], out["activities"]
        for i in out["merged"]:
            s.recs[i]["merged_into"] = out["id"]
        s._emit(m, "crm.merged", {"kept": out["id"], "merged": out["merged"], "by": by})
        return out

    def undo_merge(s, m, kept):
        for k, v in s.merges.items():
            if k.startswith(kept + "|") and s.now() - v["at"] <= C.CRM["duplicates"]["undo_days"] * 86400:
                for rid, rec in v["before"].items():
                    s.recs.put(rid, rec)
                s.merges.pop(k)
                s._emit(m, "crm.merged", {"kept": kept, "merged": [r for r in v["before"] if r != kept], "undone": True})
                return True
        return False

    # ---- consent, data requests, the full picture, visits ---------------------------------------------------------------------
    def consent(s, m, rid, channel, given, basis="asked"):
        if channel not in C.CRM["consent"]["channels"] or basis not in C.CRM["consent"]["bases"]:
            raise ValueError("unknown channel or basis")
        r = s.recs[rid]; r["consents"] = r["consents"] + [{"channel": channel, "basis": basis, "withdrawn": not given}]
        s._emit(m, "crm.consent", {"record": rid, "channel": channel, "given": given, "basis": basis})
        return given

    def may_message(s, m, rid, channel, marketing=False):
        return C.consent_ok(s.recs[rid]["consents"], channel, marketing)

    def data_request(s, m, rid, kind, received):
        if kind not in C.CRM["data_requests"]["kinds"]:
            raise ValueError("unknown request")
        due = C.request_due(received, country(s.p.c.profile(m)["country"]))
        qid = uuid.uuid4().hex
        s.requests.put(qid, {"merchant": m, "record": rid, "kind": kind, "due": due, "state": "open"})
        s._emit(m, "crm.data_request", {"request": qid, "record": rid, "kind": kind, "due_on": due})
        return {"request": qid, "due": due}

    def add_activity(s, m, rid, source, at, ref):
        r = s.recs[rid]; r["activities"] = r["activities"] + [ref]
        r["timeline"] = (r.get("timeline") or []) + [{"source": source, "at": at, "id": ref}]

    def timeline(s, m, rid, links_on, role_sources=None):
        return C.timeline(s.recs[rid].get("timeline") or [], links_on, role_sources)

    def visit(s, m, rid, state):
        if state not in C.CRM["field"]["visit_states"]:
            raise ValueError("unknown visit state")
        vid = uuid.uuid4().hex
        s._emit(m, "crm.visit", {"visit": vid, "record": rid, "state": state})
        return vid
