#!/usr/bin/env python3
"""Shared vectors for sign-up, sign-in, protections, recovery and resets (section 4C points 3 and 5): core/ways_in.py is the
reference and ts/src/waysin.ts must agree. Also writes ts/src/waysin.generated.ts with the register.
  python3 tools/waysin_vectors.py          writes contract/vectors/ways-in.v1.json and ts/src/waysin.generated.ts
  python3 tools/waysin_vectors.py --check  fails when either file is out of date (tests/test_ways_in.py)"""
import json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from core import ways_in as WI  # noqa: E402

OUT = os.path.join(ROOT, "contract", "vectors", "ways-in.v1.json")
TS = os.path.join(ROOT, "ts", "src", "waysin.generated.ts")
H = 3600
ALL = [w["id"] for w in WI.W["ways"]] + ["email_and_phone", "id_check"]
HAS = [[], ["passkey"], ["email_code", "text_code"], ["passkey", "security_key", "email_code", "text_code", "qr_code", "other_device"],
       ["authenticator", "backup_code"], ALL, ["recovery_code", "email_and_phone"], ["id_check", "recovery_contacts", "backup_code"]]
BY = ["self", "owner", "manager", "shop", "card_issuer", "key_owner", "another_admin", "successor", "election_rules", "cashier"]


def build():
    steps = WI.SIGN_UP["steps"]
    return {"version": 1, "description": "Sign-up, sign-in, protections, recovery and resets (section 4C points 3 and 5). core/ways_in.py is the reference.",
            "sign_up_next": [{"done": steps[:i], "expect": WI.sign_up_next(steps[:i])} for i in range(len(steps) + 1)] + [{"done": ["phone", "country"], "expect": WI.sign_up_next(["phone", "country"])}],
            "may_start": [{"a": [o, d, n], "expect": list(WI.may_start_sign_up(o, d, n))} for o in (True, False) for d in (0, 2, 3) for n in (0, 9, 10)],
            "legal_name": [{"a": x, "expect": WI.legal_name_problem(x)} for x in ("", "A", "Grace Uwase", "  Jean   Claude  Habimana ", "R2D2", "x" * 101, "Nguyễn Thị Lan", "محمد علي")],
            "basic": [{"a": [a, e], "expect": WI.basic_phone_allows(a, e)} for a in ("payouts", "cards", "exchange", "storefront_selling", "cash_sale", "messages") for e in (False, True)],
            "identifier": [{"a": x, "expect": WI.identifier_kind(x)} for x in ("grace.shop", "grace@example.com", "+237 671 23 45 67", "0788123456", "678889666", "shop2024", "", "  12 ")],
            "sign_in_ways": [{"a": [h, s], "expect": WI.sign_in_ways(set(h), s)} for h in HAS for s in (False, True)],
            "extra": [{"a": h, "expect": WI.extra_checks(set(h))} for h in HAS],
            "code_valid": [{"a": [s, n, a, d], "expect": WI.code_valid(s, n, a, d)} for s, n in ((0, 0), (0, 300), (0, 301)) for a, d in (("d1", "d1"), ("d1", "d2"))],
            "offline": [{"a": [k, r, d], "expect": list(WI.offline_sign_in(k, r, d))} for k in (True, False) for r in ("owner", "cashier", "rider") for d in (0, 7, 8, 14, 15)],
            "unusual": [{"a": [h, a, t], "expect": WI.unusual(h, a, t)} for h, a, t in (
                ([], {"country": "CM", "at": 0}, 0),
                ([{"country": "CM", "at": 0}], {"country": "CM", "at": 10 * H}, 0),
                ([{"country": "CM", "at": 0}], {"country": "FR", "at": 1 * H}, 0),
                ([{"country": "CM", "at": 0}], {"country": "FR", "at": 3 * H}, 0),
                ([{"country": "CM", "at": 0}, {"country": "FR", "at": 5 * H}], {"country": "CM", "at": 6 * H}, 5),
                ([{"country": "CM", "at": 0}], {"country": "CM", "at": H}, 4))],
            "country": [{"a": [l, c], "expect": WI.country_allowed(l, c)} for l in ([], ["CM"], ["CM", "NG"]) for c in ("CM", "NG", "FR")],
            "old_device": [{"a": [l, n], "expect": WI.old_device(l, n)} for l, n in ((0, 89 * 86400), (0, 90 * 86400), (100, 100))],
            "session_hours": [{"a": r, "expect": WI.session_hours(r)} for r in (True, False)],
            "word": [{"a": x, "expect": WI.anti_phishing_problem(x)} for x in ("", "ab", "sunflower", "x" * 31, " blue ")],
            "codes_left": [{"a": n, "expect": WI.backup_codes_left_note(n)} for n in (0, 1, 2, 3, 10)],
            "checkup": [{"a": h, "expect": WI.checkup(h)} for h in ({}, {"second_way": True, "backup_codes": True}, {i: True for i in WI.PROTECT["checkup"]["items"]})],
            "recovery_ways": [{"a": h, "expect": WI.recovery_ways(set(h))} for h in HAS],
            "never": [{"a": x, "expect": WI.never_allowed(x)} for x in ("password", "security_questions", "text_alone", "backup_code", "support_in_chat")],
            "restricted": [{"a": [a, r, n], "expect": WI.restricted(a, r, n)} for a in ("payouts", "contact_changes", "sell") for r, n in ((None, 0), (0, 23 * H), (0, 24 * H))],
            "contacts_confirmed": [{"a": [c, l], "expect": WI.contacts_confirmed(c, l)} for c, l in ((["a"], ["a", "b", "c"]), (["a", "b"], ["a", "b", "c"]), (["a", "x"], ["a", "b", "c"]), (["a", "a"], ["a", "b", "c"]))],
            "contacts_problem": [{"a": l, "expect": WI.contacts_problem(l)} for l in (["a", "b"], ["a", "b", "c"], ["a", "b", "c", "d", "e"], ["a", "b", "c", "d", "e", "f"], ["a", "a", "b"])],
            "to_strongest": [{"a": n, "expect": WI.to_strongest(n)} for n in (0, 4, 5)],
            "may_reset": [{"a": [w, b, o, on], "expect": list(WI.may_reset(w, b, o, on))} for w in list(WI.RESETS) + ["nope"] for b in BY for o, on in ((False, True), (True, True), (False, False))],
            "owner_needed": [{"a": a, "expect": WI.owner_check_needed(a)} for a in WI.OWNER["activities"] + ["sign_in", "cash_sale", "messages"]],
            "owner_method": [{"a": [n, b, r], "expect": WI.owner_check_method(n, b, r)} for n in (True, False) for b in (False, True) for r in (False, True)],
            "owner_outcome": [{"a": [a, s, n], "expect": WI.owner_check_outcome(a, s, n)} for a in ("match", "partial", "no_match") for s, n in ((None, 0), (0, 71 * H), (0, 72 * H))],
            "owner_valid": [{"a": [m, n, c, s], "expect": WI.owner_match_valid(m, n, c, s)} for m, n, c, s in (
                (None, 0, False, None), (0, 179 * 86400, False, None), (0, 180 * 86400, False, None), (0, 10, True, None), (0, 10, False, 5), (10, 20, False, 5))]}


def ts_text():
    w = WI.W
    reg = {"sign_up": w["sign_up"], "basic": w["basic_phone_sign_up"], "sign_in": w["sign_in"], "offline": w["offline_sign_in"], "ways": w["ways"],
           "backup_codes": w["backup_codes"], "recovery_contacts": w["recovery_contacts"], "extra_checks": w["extra_checks"],
           "protections": w["protections"], "recovery": w["recovery"], "resets": w["resets"], "phone_owner": w["phone_owner"]}
    return ("// Generated by tools/waysin_vectors.py from catalog/ways-in.v1.json. Do not edit by hand.\n"
            f"export const WAYS_IN = {json.dumps(reg, ensure_ascii=False, sort_keys=True)} as const;\n")


def main():
    v = json.dumps(build(), indent=1, ensure_ascii=False, sort_keys=True) + "\n"
    t = ts_text()
    if "--check" in sys.argv:
        bad = [p for p, s in ((OUT, v), (TS, t)) if not os.path.exists(p) or open(p, encoding="utf-8").read() != s]
        if bad:
            sys.exit("out of date: " + ", ".join(os.path.relpath(p, ROOT) for p in bad) + " (run python3 tools/waysin_vectors.py)")
        return
    for p, s in ((OUT, v), (TS, t)):
        with open(p, "w", encoding="utf-8") as f:
            f.write(s)
    print("wrote", os.path.relpath(OUT, ROOT), "and", os.path.relpath(TS, ROOT))


if __name__ == "__main__":
    main()
