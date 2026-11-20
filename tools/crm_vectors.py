#!/usr/bin/env python3
"""Shared vectors for LynkCRM's rules (OFFICE UPDATE, master blueprint 66.4): core/crm.py is the reference and ts/src/crm.ts must
agree on every case. Also writes the register into ts/src/crm.generated.ts.
  python3 tools/crm_vectors.py          writes contract/vectors/crm.v1.json and ts/src/crm.generated.ts
  python3 tools/crm_vectors.py --check  fails when either file is out of date (tests/test_crm.py)"""
import json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from core import crm as C  # noqa: E402

OUT = os.path.join(ROOT, "contract", "vectors", "crm.v1.json")
TS = os.path.join(ROOT, "ts", "src", "crm.generated.ts")


def build():
    recs = [{"id": "r1", "fields": {"city": "Kigali", "spend": 120000, "vip": True, "joined": "2025-04-01"}, "tags": ["wholesale"]},
            {"id": "r2", "fields": {"city": "Nairobi", "spend": 4000, "vip": False}, "tags": []},
            {"id": "r3", "fields": {"city": "kigali", "spend": 90000, "joined": "2026-02-10", "note": ""}, "tags": ["wholesale", "late"]},
            {"id": "r4", "fields": {}, "tags": ["late"]}]
    conds = [[], [{"field": "city", "op": "eq", "value": "Kigali"}], [{"field": "city", "op": "contains", "value": "KIG"}],
             [{"field": "spend", "op": "gte", "value": 90000}, {"op": "has_tag", "value": "wholesale"}], [{"field": "spend", "op": "lt", "value": 5000}],
             [{"field": "joined", "op": "gt", "value": "2025-12-31"}], [{"field": "joined", "op": "missing"}], [{"field": "city", "op": "in", "value": ["Nairobi", "Kampala"]}],
             [{"field": "vip", "op": "neq", "value": True}], [{"field": "spend", "op": "gt", "value": "100"}], [{"field": "note", "op": "missing"}]]
    people = [{"id": "p1", "email": "Amina@Shop.rw ", "name": "Amina Uwase", "org": "Shop", "created": "2025-01-01", "fields": {"city": "Kigali"}, "tags": ["a"], "activities": ["s1"]},
              {"id": "p2", "email": "amina@shop.rw", "created": "2026-01-01", "updated": "2026-03-01", "fields": {"city": "Huye", "size": ""}, "tags": ["b"], "activities": ["s2"]},
              {"id": "p3", "name": "Amína  UWASE", "org": "shop", "created": "2024-06-01", "fields": {"size": "L"}, "activities": ["s0"]},
              {"id": "p4", "phone_fp": "fp9", "name": "Jean", "created": "2025-05-05"},
              {"id": "p5", "phone_fp": "fp9", "created": "2025-05-06", "tags": ["c"]},
              {"id": "p6", "name": "Solo", "created": "2025-01-01"}]
    viewers = [{"id": "u1", "role": "owner", "team": None}, {"id": "u2", "role": "manager", "team": "t1"}, {"id": "u3", "role": "staff", "team": "t1"},
               {"id": "u4", "role": "staff", "team": "t2"}, {"id": "u5", "role": "manager", "team": None}]
    rows = [{"owner": "u3", "team": "t1"}, {"owner": "u4", "team": "t2"}, {"owner": "u9", "team": None}]
    items = [{"source": "sales", "at": "2026-03-01T10:00", "id": "a"}, {"source": "chats", "at": "2026-03-02T09:00", "id": "b"},
             {"source": "invoices", "at": "2026-03-01T10:00", "id": "c"}, {"source": "secret", "at": "2026-03-05T00:00", "id": "d"},
             {"source": "surveys", "at": "2026-02-01T00:00", "id": "e"}]
    consents = [{"channel": "sms", "basis": "contract"}, {"channel": "email", "basis": "asked"}, {"channel": "email", "basis": "asked", "withdrawn": True},
                {"channel": "chat", "basis": "asked"}]
    packs = {"none": None, "allowed": {"office": {"crm": {"request_days": 14, "sensitive_allowed": {"health": True}}}}}
    return {"version": 1, "description": "LynkCRM's rules (OFFICE UPDATE 66.4). core/crm.py is the reference; ts/src/crm.ts must agree.",
            "kinds": [{"e": e, "own": o, "expect": C.kinds_for(e, o)} for e in list(C.CRM["kinds"]) + ["spaceship"] for o in ([], ["vehicle", "member"])],
            "relations": [{"r": r, "e": e, "expect": C.relation_ok(r, e)} for r in C.CRM["relations"]["kinds"] + ["sibling"] for e in ("business", "school")],
            "limits": {t: C.field_limit(t) for t in ("free", "plus", "pro", "max", "x")},
            "values": [{"t": t, "v": v, "expect": C.field_value_ok(t, v)} for t in C.CRM["fields"]["types"] + ["blob"]
                       for v in (None, "x", "", 5, 5.5, True, "2026-01-31", "31/01/2026", "a" * 501)],
            "required": [{"f": [{"id": "a", "required": True}, {"id": "b"}, {"id": "c", "required": True}], "v": v,
                          "expect": C.required_missing([{"id": "a", "required": True}, {"id": "b"}, {"id": "c", "required": True}], v)} for v in ({}, {"a": "x", "c": ""}, {"a": "x", "c": [1]})],
            "records": recs, "segments": [{"c": c, "expect": C.segment(recs, c)} for c in conds],
            "moves": [{"from": a, "to": b, "expect": C.stage_move(a, b)} for a in C.CRM["pipelines"]["stages"] for b in C.CRM["pipelines"]["stages"]],
            "close": [{"s": s, "r": r, "expect": C.close_ok(s, r)} for s in ("won", "lost", "proposal") for r in ("price", "timing", "quality", None)],
            "forecast": [{"d": d, "c": c, "expect": C.forecast(d, c)} for d in ([{"id": "x", "amount": 100000, "stage": "proposal"}, {"id": "y", "amount": 33333, "stage": "new"},
                                                                                    {"id": "z", "amount": 50000, "stage": "won"}], []) for c in ({}, {"proposal": 7500})],
            "scores": [{"s": s, "expect": C.lead_score(s)} for s in ([], ["opened_quote", "replied"], ["booked_meeting", "bought_before", "replied", "opened_quote"], ["no_answer_30_days"], ["unknown"])],
            "viewers": viewers, "rows": rows,
            "see": [{"v": i, "r": j, "vis": vis, "expect": C.may_see(viewers[i], rows[j], vis)} for i in range(len(viewers)) for j in range(len(rows)) for vis in (None, "own", "team", "all")],
            "hidden": [{"role": r, "expect": C.visible_fields([{"id": "a"}, {"id": "salary", "hidden_from": ["staff", "manager"]}, {"id": "b", "hidden_from": ["staff"]}], r)} for r in ("owner", "manager", "staff")],
            "cases": [{"o": o, "p": p, "pause": pa, "own": ow, "now": n, "ans": a, "due": C.case_due(o, p, pa, ow), "late": C.case_late(n, o, p, a, pa, ow)}
                      for o in (0, 100) for p in C.CRM["cases"]["priorities"] for pa, ow in ((0, None), (5, None), (0, 3)) for n, a in ((101, False), (130, False), (130, True))],
            "items": items,
            "timeline": [{"links": l, "roles": r, "expect": C.timeline(items, l, r)} for l in (["sales", "chats", "invoices", "secret", "surveys"], ["sales"], []) for r in (None, ["sales", "invoices"])],
            "normalise": {s: C.normalise(s) for s in ("  Amína  UWASE ", "Ñandú", "ÉCOLE de Kigali", "", "Ömer\tÇelik")},
            "people": people, "duplicates": C.duplicates(people),
            "merge": [C.merge([p for p in people if p["id"] in g]) for g in C.duplicates(people)],
            "consents": consents,
            "consent": [{"ch": ch, "mk": mk, "expect": C.consent_ok(consents, ch, mk)} for ch in C.CRM["consent"]["channels"] for mk in (False, True)],
            "packs": packs,
            "due": [{"d": d, "p": p, "expect": C.request_due(d, packs[p])} for d in ("2026-01-20", "2026-12-15") for p in packs],
            "sensitive": [{"k": k, "e": e, "p": p, "expect": C.sensitive_allowed(k, e, packs[p])} for k in ("health", "children", "citizens", "general") for e in ("business", "school", "public_body") for p in packs]}


def ts_source():
    return ("// GENERATED by tools/crm_vectors.py from catalog/crm.v1.json. Do not edit by hand.\n"
            "import type { CrmRegister } from \"./crm.js\";\n"
            f"export const CRM = {json.dumps(C.CRM, ensure_ascii=False, separators=(',', ':'))} as unknown as CrmRegister;\n")


def main():
    vec = json.dumps(build(), ensure_ascii=False, separators=(",", ":")) + "\n"
    ts = ts_source()
    if "--check" in sys.argv:
        stale = [p for p, want in ((OUT, vec), (TS, ts)) if not os.path.exists(p) or open(p, encoding="utf-8").read() != want]
        if stale:
            print("out of date:", ", ".join(os.path.relpath(p, ROOT) for p in stale), "- run python3 tools/crm_vectors.py")
            sys.exit(1)
        return
    for p, text in ((OUT, vec), (TS, ts)):
        with open(p, "w", encoding="utf-8") as f:
            f.write(text)
    print("wrote", os.path.relpath(OUT, ROOT), "and", os.path.relpath(TS, ROOT))


if __name__ == "__main__":
    main()
