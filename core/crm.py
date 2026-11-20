"""LynkCRM's rules (OFFICE UPDATE, master blueprint 66.4; section 4 step D3), read from catalog/crm.v1.json.

Record kinds for each kind of entity, relations, own fields and required fields, saved segments, pipelines with the contract's
five stages, the forecast, lead scores as labelled suggestions, who sees which records and fields, cases with promised answer
times, the one full picture, duplicate finding and merging, consent per channel, a person's data requests and sensitive
records. Contact details are vault references only. Money is integer minor units.

This module is the Python reference; ts/src/crm.ts must agree on every case of contract/vectors/crm.v1.json
(python3 tools/crm_vectors.py after a change)."""
import json, os, re, unicodedata

from core import books as B

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
with open(os.path.join(ROOT, "catalog", "crm.v1.json"), encoding="utf-8") as _f:
    CRM = json.load(_f)


# ---- who is recorded ---------------------------------------------------------------------------------------------------------
def kinds_for(entity_kind, own=()):
    """The record kinds an entity sees, plus its own kinds (Max)."""
    return list(CRM["kinds"].get(entity_kind, [])) + [k for k in own if k not in CRM["kinds"].get(entity_kind, [])]


def relation_ok(relation, entity_kind):
    if relation not in CRM["relations"]["kinds"]:
        return False
    return relation != "guardian_of" or entity_kind == "school"


def field_limit(tier):
    return CRM["fields"]["limits"].get(tier, 0)


def field_value_ok(ftype, value):
    if value is None:
        return True
    if ftype == "text":
        return isinstance(value, str) and len(value) <= 500
    if ftype in ("number", "money"):
        return isinstance(value, int) and not isinstance(value, bool)
    if ftype == "date":
        return isinstance(value, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", value) is not None
    if ftype == "yes_no":
        return isinstance(value, bool)
    if ftype == "choice":
        return isinstance(value, str) and value != ""
    return False


def required_missing(fields, values):
    """The required fields still empty, in the layout's order."""
    return [f["id"] for f in fields if f.get("required") and values.get(f["id"]) in (None, "", [])]


# ---- segments ----------------------------------------------------------------------------------------------------------------
def _cond(rec, c):
    v = rec.get("fields", {}).get(c.get("field")) if c["op"] != "has_tag" else None
    op, want = c["op"], c.get("value")
    if op == "has_tag":
        return want in rec.get("tags", [])
    if op == "missing":
        return v in (None, "", [])
    if v is None:
        return False
    if op == "eq":
        return v == want
    if op == "neq":
        return v != want
    if op == "in":
        return v in want
    if op == "contains":
        return isinstance(v, str) and isinstance(want, str) and want.lower() in v.lower()
    if isinstance(v, bool) or not isinstance(v, (int, str)) or type(v) is not type(want):
        return False
    return {"gt": v > want, "gte": v >= want, "lt": v < want, "lte": v <= want}[op]


def segment(records, conditions):
    """The ids of the records that meet every condition, worked out again each time."""
    return [r["id"] for r in records if all(_cond(r, c) for c in conditions)]


# ---- selling -----------------------------------------------------------------------------------------------------------------
def stage_move(old, new):
    return new in CRM["pipelines"]["moves"].get(old, [])


def close_ok(stage, reason):
    """A won or lost deal names its reason from the list."""
    if stage not in ("won", "lost"):
        return True
    return reason in CRM["pipelines"]["reasons"][stage]


def forecast(deals, chances=None):
    """Each open deal's amount times its stage's chance (basis points), and the total."""
    ch = {**CRM["pipelines"]["default_chance_bp"], **(chances or {})}
    rows = [{"id": d["id"], "weighted": B.round_div(d["amount"] * ch[d["stage"]], 10000)} for d in deals if d["stage"] not in ("won", "lost")]
    return {"deals": rows, "total": sum(r["weighted"] for r in rows)}


def lead_score(signals):
    """LynkAssist's suggestion, 0 to 100, labelled as a suggestion; never decides anything."""
    w = CRM["lead_score"]["signals"]
    score = sum(w.get(s, 0) for s in signals)
    return {"score": max(0, min(100, score)), "suggestion": True}


# ---- access ------------------------------------------------------------------------------------------------------------------
def may_see(viewer, record, visibility=None):
    """viewer: {"id", "role", "team"}; record: {"owner", "team"}. The owner role sees all; a manager their team."""
    vis = visibility or CRM["access"]["default"]
    if viewer["role"] == "owner" or vis == "all":
        return True
    if record.get("owner") == viewer["id"]:
        return True
    if vis == "own":
        return viewer["role"] == "manager" and record.get("team") is not None and record.get("team") == viewer.get("team")
    return record.get("team") is not None and record.get("team") == viewer.get("team")


def visible_fields(fields, role):
    """The fields a role may see; a hidden field is never sent to that role's screens."""
    return [f["id"] for f in fields if role not in f.get("hidden_from", [])]


# ---- service -----------------------------------------------------------------------------------------------------------------
def case_due(opened_hour, priority, paused_hours=0, own_hours=None):
    """The hour by which the first answer is promised (hours as whole numbers since any fixed start)."""
    hours = own_hours if own_hours is not None else CRM["cases"]["priorities"][priority]
    return opened_hour + hours + paused_hours


def case_late(now_hour, opened_hour, priority, answered=False, paused_hours=0, own_hours=None):
    return not answered and now_hour > case_due(opened_hour, priority, paused_hours, own_hours)


# ---- the one full picture ----------------------------------------------------------------------------------------------------
def timeline(items, links_on, role_sources=None):
    """Items [{"source", "at", "id"}] shown only when their link is on (and the role may see the source), newest first."""
    ok = [i for i in items if i["source"] in CRM["timeline"]["sources"] and i["source"] in links_on and (role_sources is None or i["source"] in role_sources)]
    return [i["id"] for i in sorted(ok, key=lambda i: (i["at"], i["id"]), reverse=True)]


# ---- clean records -----------------------------------------------------------------------------------------------------------
def normalise(s):
    """Spaces, case and accents set aside (for finding the same name written two ways)."""
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    return " ".join(s.lower().split())


def match_keys(rec):
    keys = []
    if rec.get("email"):
        keys.append("e:" + rec["email"].strip().lower())
    if rec.get("phone_fp"):
        keys.append("p:" + rec["phone_fp"])
    if rec.get("name"):
        keys.append("n:" + normalise(rec["name"]) + "|" + normalise(rec.get("org", "")))
    return keys


def duplicates(records):
    """Groups of record ids that are likely the same, in the order first seen; a group has at least two."""
    parent = {r["id"]: r["id"] for r in records}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    first = {}
    for r in records:
        for k in match_keys(r):
            if k in first:
                a, b = find(first[k]), find(r["id"])
                if a != b:
                    parent[b] = a
            else:
                first[k] = r["id"]
    groups = {}
    for r in records:
        groups.setdefault(find(r["id"]), []).append(r["id"])
    return [g for g in groups.values() if len(g) > 1]


def merge(records):
    """Keep the oldest record; join the tags; keep the newest non-empty value of each field; keep every activity."""
    recs = sorted(records, key=lambda r: (r["created"], r["id"]))
    keep = recs[0]
    fields = {}
    for r in sorted(records, key=lambda r: (r.get("updated", r["created"]), r["id"])):
        for k, v in (r.get("fields") or {}).items():
            if v not in (None, "", []):
                fields[k] = v
    return {"id": keep["id"], "merged": [r["id"] for r in recs[1:]], "tags": sorted({t for r in records for t in r.get("tags", [])}),
            "fields": dict(sorted(fields.items())), "activities": sorted(a for r in records for a in r.get("activities", []))}


# ---- consent, data requests, sensitive records -------------------------------------------------------------------------------
def _crm_pack(pack):
    """A country pack's LynkCRM settings (office.crm, tools/country_office.py)."""
    return (((pack or {}).get("office") or {}).get("crm")) or {}


def consent_ok(consents, channel, marketing=False):
    """consents: [{"channel", "basis", "withdrawn"}]; the latest for the channel decides; marketing needs 'asked'."""
    mine = [c for c in consents if c["channel"] == channel]
    if not mine or mine[-1].get("withdrawn"):
        return False
    return not marketing or mine[-1]["basis"] == "asked"


def request_due(received, pack=None):
    days = _crm_pack(pack).get("request_days") or CRM["data_requests"]["default_days"]
    return B._dt.date.fromordinal(B._date(received).toordinal() + days).isoformat()


def sensitive_allowed(kind, entity_kind, pack=None):
    """Health, children and citizens records only where the pack allows them; a school's students and a public body's cases
    are what those workspaces exist for, under the strictest rules."""
    if kind not in CRM["sensitive"]["kinds"]:
        return True
    if (kind == "children" and entity_kind == "school") or (kind == "citizens" and entity_kind == "public_body"):
        return True
    allowed = (_crm_pack(pack).get("sensitive_allowed") or {}).get(kind)
    return allowed is True
