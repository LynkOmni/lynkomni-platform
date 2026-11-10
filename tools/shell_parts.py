#!/usr/bin/env python3
"""The shared rules behind the MASTER UPDATE shell parts (build section 1), written for the screens and checked by vectors.

The Python modules are the reference; the screens (ts/src/signin.ts, notify.ts, assist.ts, breadcrumbs.ts) must agree on every
case in contract/vectors/parts.v1.json. ts/src/parts.generated.ts carries the registers the screens need offline: the PIN rule,
the message and notification kinds, LynkAssist's actions and answer topics, the address map for breadcrumbs, the plan prices and
product pages for the offline knowledge pack, and the languages.
  python3 tools/shell_parts.py          writes both files
  python3 tools/shell_parts.py --check  fails when either is out of date (tests/test_shell_parts.py)"""
import json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from core import breadcrumbs as B  # noqa: E402
from identity import offline as O  # noqa: E402
from services import assist_register as A, billing  # noqa: E402
from tools.assist import knowledge_pack as KP  # noqa: E402

VEC = os.path.join(ROOT, "contract", "vectors", "parts.v1.json")
TS = os.path.join(ROOT, "ts", "src", "parts.generated.ts")
MSG = json.load(open(os.path.join(ROOT, "catalog", "messages.v1.json"), encoding="utf-8"))
SEARCH = json.load(open(os.path.join(ROOT, "catalog", "search.v1.json"), encoding="utf-8"))
PRODUCTS = json.load(open(os.path.join(ROOT, "catalog", "products.v1.json"), encoding="utf-8"))
PINS = ["", "1", "123", "1357", "0000", "1234", "4321", "9876", "12345678", "2580", "13579", "123456789", "12a4", "73914", "00001", "8642", "0123", "98765432", "55555555", "246813579"]
LOOKUPS = [("en", "How much is LynkStat?"), ("en", "what does sent mean"), ("en", "where is LynkPOS"), ("fr", "Combien coûte LynkStat ?"),
           ("ja", "LynkStatの料金"), ("ar", "كم سعر LynkStat"), ("sw", "LynkPOS iko wapi"), ("zh-Hans", "LynkStat 多少钱"), ("hi", "LynkStat की कीमत"), ("en", "zzz")]


def decide_cases():
    out = []
    for a in A.REG["actions"]:
        r0 = a["roles"][0]
        lim = a["limits"]
        variants = [dict(role=r0), dict(role=r0, confirmed=True), dict(role=r0, fresh_check=True), dict(role=r0, fresh_check=True, confirmed=True),
                    dict(role="nobody"), dict(role=r0, done_today=lim["per_day"]), dict(role=r0, switched_off=[a["id"]]), dict(role=r0, switched_off=[a["area"]]),
                    dict(role=r0, country="CM", switched_off=["country:CM"]), dict(role=r0, country="KE", switched_off=["country:CM"]),
                    dict(role="manager" if "manager" in a["roles"] else r0, ask_owner_first=[a["id"]]), dict(role=r0, standing=[a["id"]])]
        if lim.get("max_minor") is not None:
            variants.append(dict(role=r0, amount_minor=lim["max_minor"] + 1, confirmed=True))
        for v in variants:
            d = A.decide(a["id"], **v)
            out.append({"action": a["id"], "ask": v, "run": d["run"], "needs": d["needs"], "class": d.get("class")})
    out.append({"action": "send_all_money_to_me", "ask": {"role": "owner"}, "run": False, "needs": "refused", "class": None})
    return out


def answer_cases():
    out = []
    askers = [{}, {"signed_in": True}, {"signed_in": True, "fresh_check": True}, {"signed_in": True, "fresh_check": True, "role": "owner"},
              {"signed_in": True, "role": "cashier"}, {"signed_in": True, "fresh_check": True, "role": "manager"}]
    for topic in list(A.REG["topics"]) + ["no_such_topic"]:
        for asker in askers:
            r = A.answer(topic, **asker)
            out.append({"topic": topic, "asker": asker, "answer": r["answer"], "class": r["class"]})
    return out


def build():
    packs = {lang: KP.build("2026-11-10", lang)["entries"] for lang in ("en", "ar", "ja", "fr", "sw", "zh-Hans", "hi")}
    return {
        "version": 1,
        "description": "Shared cases for the section 1 shell parts. Python is the reference (identity/offline.py, core/breadcrumbs.py, services/assist_register.py, tools/assist/knowledge_pack.py); the TypeScript parts must agree.",
        "pins": [{"pin": p, "problem": O.pin_problem(p)} for p in PINS],
        "trails": [{"host": h, "path": p, "trail": B.trail(h, p)} for h, p in B.every_address()],
        "decide": decide_cases(),
        "answers": answer_cases(),
        "packs": packs,
        "lookups": [{"lang": l, "query": q, "ids": [e["id"] for e in KP.lookup(KP.build("2026-11-10", l), q)]} for l, q in LOOKUPS],
        "badges": [{"n": n, "text": "" if n <= 0 else ("99+" if n > 99 else str(n))} for n in (0, 1, 9, 99, 100, 250)],
    }


def ts_text():
    kinds = {k["id"]: {f: k[f] for f in ("area", "priority", "group", "can_turn_off", "actions", "basis")} for k in MSG["kinds"]}
    msg = {"priorities": MSG["priorities"], "daily_cap": MSG["daily_cap"], "history_days": MSG["history_days"], "quiet_hours": MSG["quiet_hours"], "kinds": kinds}
    assist = {"only_hand_over": A.REG["only_hand_over"], "never_auto": A.REG["never_auto"],
              "actions": {a["id"]: {f: a[f] for f in ("area", "class", "roles", "limits", "touches", "undo")} for a in A.REG["actions"]},
              "topics": {t: {"class": v["class"], **({"roles": v["roles"]} if v.get("roles") else {})} for t, v in A.REG["topics"].items()}}
    pin = {"min": O.PIN_MIN, "max": O.PIN_MAX, "delays": {str(k): v for k, v in O.PIN_DELAYS.items()}, "hardLockAfter": O.HARD_LOCK_AFTER}
    prods = PRODUCTS.get("products") or PRODUCTS
    pages = {p["family"]: p["page"] for p in prods if p.get("page")}
    fams = [[f, v[1], list(v[2]), list(v[3])] for f, v in billing.FAMILIES.items()]
    j = lambda o: json.dumps(o, ensure_ascii=False, separators=(",", ":"))
    return ("// GENERATED by tools/shell_parts.py from the registers. Do not edit by hand.\n"
            f"export const PIN_RULE: {{ min: number; max: number; delays: Record<string, number>; hardLockAfter: number }} = {j(pin)};\n"
            "export interface MessageKind { area: string; priority: \"critical\" | \"high\" | \"normal\" | \"low\"; group: string; can_turn_off: boolean; actions: string[]; basis: string }\n"
            "export interface AssistAction { area: string; class: \"A\" | \"B\" | \"C\" | \"D\"; roles: string[]; limits: { per_day: number; max_minor?: number | null }; touches: string[]; undo: string | null }\n"
            f"export const MESSAGES: {{ priorities: Record<string, {{ breaks_quiet_hours: boolean; repeat_until_acknowledged: boolean; capped: boolean; raises_count: boolean }}>; daily_cap: number; history_days: number; quiet_hours: {{ start: number; end: number }}; kinds: Record<string, MessageKind> }} = {j(msg)};\n"
            f"export const ASSIST: {{ only_hand_over: string[]; never_auto: string[]; actions: Record<string, AssistAction>; topics: Record<string, {{ class: number; roles?: string[] }}> }} = {j(assist)};\n"
            f"export const ADDRESS_HOSTS: Record<string, string[]> = {j(B.HOSTS)};\n"
            f"export const STOREFRONT_PREFIX = {j(B.STOREFRONT)};\n"
            f"export const FAMILIES: [string, string, string[], number[]][] = {j(fams)};\n"
            f"export const PRODUCT_PAGES: Record<string, string> = {j(pages)};\n"
            f"export const KP_STATES = {j(list(KP.STATES))};\n"
            f"export const LANGS: string[] = {j(KP.LANGS)};\n"
            f"export const NEVER_INDEXED: string[] = {j(SEARCH['never_indexed_hosts'])};\n")


def main(check=False):
    vec = json.dumps(build(), indent=1, ensure_ascii=False) + "\n"
    ts = ts_text()
    if check:
        bad = [p for p, want in ((VEC, vec), (TS, ts)) if not os.path.isfile(p) or open(p, encoding="utf-8").read() != want]
        if bad:
            print("out of date: " + ", ".join(bad) + " (run python3 tools/shell_parts.py)"); return 1
        print("shell parts are current"); return 0
    for p, txt in ((VEC, vec), (TS, ts)):
        with open(p, "w", encoding="utf-8") as f:
            f.write(txt)
    print(f"wrote {VEC} and {TS}"); return 0


if __name__ == "__main__":
    sys.exit(main("--check" in sys.argv))
