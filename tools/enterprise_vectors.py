#!/usr/bin/env python3
"""Shared vectors for the large-organisation set and the Move in tool (OFFICE UPDATE, master blueprint 66.5 and 66.6):
core/enterprise.py is the reference and ts/src/enterprise.ts must agree. Also writes ts/src/enterprise.generated.ts.
  python3 tools/enterprise_vectors.py          writes contract/vectors/enterprise.v1.json and ts/src/enterprise.generated.ts
  python3 tools/enterprise_vectors.py --check  fails when either file is out of date (tests/test_enterprise.py)"""
import json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from core import enterprise as E  # noqa: E402

OUT = os.path.join(ROOT, "contract", "vectors", "enterprise.v1.json")
TS = os.path.join(ROOT, "ts", "src", "enterprise.generated.ts")


def build():
    flow = [{"role": "manager", "from_minor": 0}, {"role": "finance", "from_minor": 100000, "stand_in": "owner"},
            {"role": "owner", "from_minor": 1000000}, {"role": "head_of_sales", "from_minor": 0, "department": "sales"}]
    steps = E.flow_steps(flow, 500000, "sales")
    approve_cases = []
    for approvals in ([], [{"who": "u2"}], [{"who": "u2"}, {"who": "u3"}], [{"who": "u2"}, {"who": "u3"}, {"who": "u4"}]):
        for who, role, away in (("u1", "manager", False), ("u2", "finance", False), ("u5", "finance", False), ("u5", "owner", True), ("u5", "owner", False),
                                ("u6", "head_of_sales", False), ("u7", "manager", False)):
            approve_cases.append({"approvals": approvals, "who": who, "role": role, "away": away, "expect": E.may_approve(steps, approvals, "u1", who, role, away)})
    roles = [{"inv": ["view", "prepare"]}, {"acc": ["prepare", "approve"]}, {"crm": ["post"]}, {"hr": ["view"]}, {"acc": ["view", "prepare", "approve", "export"], "stat": ["admin", "view"]}]
    amounts = ["1500", "1,234.50", "1234,5", "-12", "12.345", "1.234", "", "12abc", " 1 000.5 ", "0", "0.00", "99999999999.99", "1,23", "1.5.2", "-0.10", ",5", "5,"]
    dates = ["2026-02-28", "2026-02-29", "2024-02-29", "31/01/2026", "01/31/2026", "1/2/2026", "2026-13-01", "31.12.2025", "", "2026/01/31"]
    cust_h, cust = ["ref", "name", "email"], [["C1", "Amina", "a@x.rw"], ["C2", "", ""], ["C1", "Jean", ""], ["", "Solo", ""]]
    ob_h, ob = ["account", "debit", "credit"], [["1000", "150.00", ""], ["3000", "", "150"], ["9999", "1", ""], ["1020", "1", "1"], ["1020", "abc", ""], ["1020", "", ""]]
    inv_h, inv = ["number", "customer_ref", "issued_on", "due_on", "amount"], [["A-1", "C1", "2026-01-31", "2026-02-14", "1,250.00"], ["A-2", "C9", "2026-02-30", "", "12.5"],
                                                                             ["A-1", "C1", "2026-01-31", "", "-4"], ["A-3", "C1", "2026-01-31", "", ""]]
    chart_h, chart = ["code", "name", "type"], [["700", "Ventes", "income"], ["701", "Autre", "revenue"], ["700", "Twice", "income"]]
    known = {"customers": ["C1", "C2"], "suppliers": ["S1"]}
    checks = [{"kind": "customers", "header": cust_h, "rows": cust}, {"kind": "customers", "header": ["name"], "rows": cust},
              {"kind": "opening_balances", "header": ob_h, "rows": ob, "accounts": ["1000", "1020", "3000"]},
              {"kind": "opening_balances", "header": ob_h, "rows": ob[:2], "accounts": None},
              {"kind": "open_invoices", "header": inv_h, "rows": inv, "known": known},
              {"kind": "open_invoices", "header": inv_h, "rows": inv[:1], "known": known, "decimals": 0},
              {"kind": "chart", "header": chart_h, "rows": chart},
              {"kind": "voters", "header": ["ref", "name", "group", "weight"], "rows": [["V1", "Ana", "north", "3"], ["V2", "Bo", "", ""], ["V1", "Ana again", "", "1"],
                                                                              ["V3", "Cy", "", "0"], ["V4", "Di", "", "1.5"], ["V5", "", "", "x"]]}]
    for c in checks:
        c["expect"] = E.check(c["kind"], c["header"], c["rows"], c.get("decimals", 2), "iso", c.get("known"), c.get("accounts"))
    return {"version": 1, "description": "The large-organisation set and Move in (OFFICE UPDATE 66.5, 66.6). core/enterprise.py is the reference.",
            "flow": flow, "steps": [{"amount": a, "dept": d, "expect": E.flow_steps(flow, a, d)} for a in (0, 99999, 100000, 2000000) for d in (None, "sales", "it")],
            "approve_steps": steps, "approve": approve_cases,
            "roles": [{"perms": r, "apart": k, "expect": E.role_problems(r, k)} for r in roles for k in (True, False)],
            "split": [{"t": t, "s": s, "expect": E.split_charges(t, s)} for t in (100000, 333) for s in ({"sales": 5000, "it": 3000, "ops": 2000}, {"all": 10000})],
            "delete": [{"age": a, "policy": p, "law": l, "held": h, "expect": E.may_delete(a, p, l, h)} for a in (100, 4000) for p, l in ((365, 3650), (None, None), (7000, 365)) for h in (False, True)],
            "region": [{"choice": c, "pack": p, "expect": E.data_region(c, p)} for c in ("europe", None) for p in (None, {"office": {"crm": {"data_region": "africa"}}}, {"office": {"crm": {"data_region": None}}})],
            "amounts": [{"t": t, "d": d, "expect": E.parse_amount(t, d)} for t in amounts for d in (0, 2, 3)],
            "dates": [{"t": t, "f": f, "expect": E.parse_date(t, f)} for t in dates for f in ("iso", "day_first", "month_first")],
            "checks": checks, "suspended": E.suspended_by(600)}


def ts_source():
    return ("// GENERATED by tools/enterprise_vectors.py from catalog/enterprise.v1.json. Do not edit by hand.\n"
            "import type { EnterpriseRegister } from \"./enterprise.js\";\n"
            f"export const ENTERPRISE = {json.dumps(E.ENT, ensure_ascii=False, separators=(',', ':'))} as unknown as EnterpriseRegister;\n")


def main():
    vec = json.dumps(build(), ensure_ascii=False, separators=(",", ":")) + "\n"
    ts = ts_source()
    if "--check" in sys.argv:
        stale = [p for p, want in ((OUT, vec), (TS, ts)) if not os.path.exists(p) or open(p, encoding="utf-8").read() != want]
        if stale:
            print("out of date:", ", ".join(os.path.relpath(p, ROOT) for p in stale), "- run python3 tools/enterprise_vectors.py")
            sys.exit(1)
        return
    for p, text in ((OUT, vec), (TS, ts)):
        with open(p, "w", encoding="utf-8") as f:
            f.write(text)
    print("wrote", os.path.relpath(OUT, ROOT), "and", os.path.relpath(TS, ROOT))


if __name__ == "__main__":
    main()
