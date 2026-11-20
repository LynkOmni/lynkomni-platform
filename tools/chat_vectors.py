#!/usr/bin/env python3
"""Shared vectors for the conversation engine (CHAT UPDATE, master blueprint 74): core/chat.py is the reference and
ts/src/chat.ts must agree on every case. Also writes the register into ts/src/chat.generated.ts so every app carries it offline.
  python3 tools/chat_vectors.py          writes contract/vectors/chat.v1.json and ts/src/chat.generated.ts
  python3 tools/chat_vectors.py --check  fails when either file is out of date (tests/test_chat.py)"""
import itertools, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from core import chat as C  # noqa: E402

OUT = os.path.join(ROOT, "contract", "vectors", "chat.v1.json")
TS = os.path.join(ROOT, "ts", "src", "chat.generated.ts")

TEXTS = [
    ("my card is 4111 1111 1111 1111 thanks", []), ("4111-1111-1111-1111", []), ("4111111111111112 is not a card", []),
    ("5500 0000 0000 0004 and pin 4821", ["pin"]), ("PIN: 1234", ["pin"]), ("spinach costs 1234", ["pin"]),
    ("Your CODE is 902211", ["code"]), ("mon code est 4433", ["code"]), ("密码是123456", ["密码"]), ("call +250 788 123 456 about order 12345", ["pin"]),
    ("I paid 5000 RWF", []), ("password 12 and 123456789", ["password"]), ("378282246310005 has fifteen digits", []), ("", ["pin"]),
    ("пин-код 5521", ["пин-код"]), ("code1234", ["code"]), ("الرمز 7788", ["الرمز"]),
]
HELPERS = [
    {"id": "h1", "available": True, "on_shift": True, "open": 2, "topics": ["orders", "payments"], "languages": ["en", "fr"]},
    {"id": "h2", "available": True, "on_shift": True, "open": 1, "topics": ["orders"], "languages": ["rw", "en"], "sides": ["internal"]},
    {"id": "h3", "available": True, "on_shift": True, "open": 5, "topics": ["orders", "payments"], "languages": ["sw"]},
    {"id": "h4", "available": False, "on_shift": True, "open": 0, "topics": ["orders", "payments"], "languages": ["fr"]},
    {"id": "h5", "available": True, "on_shift": True, "open": 1, "topics": ["payments"], "languages": ["ar"], "countries": ["EG"]},
]
CONVS = [
    {"topic": "fraud"}, {"topic": "safety", "wants_person": True}, {"topic": "orders"},
    {"topic": "orders", "wants_person": True, "language": "fr"}, {"topic": "orders", "wants_person": True, "language": "rw"},
    {"topic": "orders", "wants_person": True, "language": "sw"}, {"topic": "orders", "wants_person": True, "language": "en", "side": "external"},
    {"topic": "orders", "wants_person": True, "language": "fr", "last_helper": "h2"}, {"topic": "payments", "wants_person": True, "language": "ar", "country": "EG"},
    {"topic": "payments", "wants_person": True, "language": "ar", "country": "RW"}, {"topic": "tax", "wants_person": True, "was_with": "h1"},
    {"topic": "tax", "wants_person": True},
]
STAFF = [
    {"id": "s1", "on_shift": True, "open": 3, "branch": "kigali", "languages": ["en"], "products": ["phones"]},
    {"id": "s2", "on_shift": True, "open": 1, "branch": "huye", "languages": ["fr", "rw"]},
    {"id": "s3", "on_shift": False, "open": 0, "branch": "kigali", "languages": ["fr"]},
    {"id": "s4", "on_shift": True, "open": 1, "branch": "kigali", "languages": ["rw"], "products": ["phones", "tvs"]},
]
TEAM = [{}, {"served_by": "s2"}, {"served_by": "s3"}, {"branch": "kigali"}, {"branch": "kigali", "product": "phones"},
        {"branch": "kigali", "language": "rw"}, {"language": "fr"}, {"product": "tvs"}, {"branch": "musanze"}]


def build():
    sounds = []
    flags = ("sounds", "vibration", "silent", "muted", "quiet_hours", "chat_open")
    for ev in list(C.SOUND_EVENTS) + ["received", "nothing"]:
        for bits in itertools.product((False, True), repeat=len(flags)):
            s = dict(zip(flags, bits))
            sounds.append({"event": ev, "s": s, "expect": C.sound_for(ev, s)})
        for extra in ({"screen": "payment"}, {"screen": "home"}, {"since_last_ms": 500}, {"since_last_ms": 5000}, {"dnd": True}, {"focus": True}):
            s = {"sounds": True, "vibration": True, **extra}
            sounds.append({"event": ev, "s": s, "expect": C.sound_for(ev, s)})
    signs = [{"sign": sg, "author": a, "o": dict(zip(("online_both", "reduced_motion", "team_view", "sender_allows"), b)),
              "expect": C.live_sign(sg, a, *b)}
             for sg in list(C.SIGNS) + ["shouting"] for a in C.CHAT["authors"] for b in itertools.product((True, False), repeat=4)]
    moves = [{"from": a, "to": b, "writer": w, "expect": C.can_move(a, b, w)} for a in C.STATES for b in C.STATES for w in ("device", "cloud")]
    shown = [{"state": s, "reader": r, "seen": v, "expect": C.shown_state(s, r, v)} for s in C.STATES for r in C.CHAT["authors"] for v in (True, False)]
    edits = [{"body": b, "author": a, "me": me, "min": m, "expect": C.edit_allowed(b, a, me, m)}
             for b in ("text", "voice", "card") for a in ("customer", "system") for me in ("customer", "business") for m in (-1, 0, 15, 16)]
    msgs = [{"id": "c", "written_at": 5, "device_seq": 2}, {"id": "a", "written_at": 5, "device_seq": 1}, {"id": "b", "written_at": 3, "device_seq": 9},
            {"id": "a", "written_at": 1, "device_seq": 0}, {"id": "d", "written_at": 5, "device_seq": 1}]
    route = [{"conv": c, "open_now": o, "expect": C.route_support(c, HELPERS, o)} for c in CONVS for o in (True, False)]
    team = [{"conv": c, "mode": m, "turn": t, "staff": st, "expect": C.route_team(c, st, m, t)}
            for c in TEAM for m in ("least_busy", "take_turns") for t in (0, 1, 2) for st in (STAFF, STAFF[:1], [STAFF[2]])]
    return {"version": 1, "description": "The conversation engine (CHAT UPDATE 74): states, masking, live signs, sounds, routing, offline, cards and tools. core/chat.py is the reference; ts/src/chat.ts must agree.",
            "moves": moves, "shown": shown, "edits": edits,
            "ordered": {"in": msgs, "expect": [m["id"] for m in C.ordered(msgs)]},
            "words": [{"text": t, "word": w, "expect": C.has_word(t, w)} for t, ws in TEXTS for w in ws],
            "mask": [{"text": t, "words": w, "expect": C.mask(t, w)} for t, w in TEXTS],
            "signs": signs,
            "connection": [{"online": o, "was": w, "n": n, "expect": C.own_connection(o, w, n)} for o in (True, False) for w in (True, False) for n in (0, 3)],
            "sounds": sounds, "helpers": HELPERS, "route": route, "team": team,
            "escalate": [{"min": m, "setting": s, "expect": C.escalate(m, s)} for m in (0, 5, 14, 15, 60, 121) for s in (None, 2, 30, 500)],
            "reply_time": [{"xs": xs, "expect": C.reply_time(xs)} for xs in ([3] * 19, [3] * 20, list(range(1, 41)), [200] * 25, [2000] * 21, [4, 6] * 10)],
            "offline": {w: C.offline(w) for w in list(C.CHAT["offline"]["what"]) + ["teleport"]},
            "cards": [{"kind": k, "action": a, "online": o, "expect": C.card_action(k, a, o)}
                      for k in list(C.CARDS) + ["ballot"] for a in ("pay", "accept", "sign", "chat_about", "answer", "open_secure_step", "leave") for o in (True, False)],
            "tools": [{"choices": c, "fields": f, "expect": C.tools_ok(c, f)} for c in (0, 6, 7) for f in ([], ["date", "option"], ["date"] * 5, ["password"])]}


def ts_text():
    keep = {k: C.CHAT[k] for k in ("kinds", "states", "edit", "live_signs", "sounds", "masking", "routing", "offline", "cards", "tools")}
    return ("// GENERATED by tools/chat_vectors.py from catalog/chat.v1.json. Do not edit by hand.\n"
            "import type { ChatRegister } from \"./chat.js\";\n"
            f"export const CHAT = {json.dumps(keep, ensure_ascii=False, separators=(',', ':'))} as ChatRegister;\n")


def main(check=False):
    vec = json.dumps(build(), ensure_ascii=False, separators=(",", ":")) + "\n"
    ts = ts_text()
    if check:
        bad = [p for p, want in ((OUT, vec), (TS, ts)) if not os.path.isfile(p) or open(p, encoding="utf-8").read() != want]
        if bad:
            print("out of date: " + ", ".join(bad) + " (run python3 tools/chat_vectors.py)"); return 1
        print("chat vectors are current"); return 0
    for p, txt in ((OUT, vec), (TS, ts)):
        with open(p, "w", encoding="utf-8") as f: f.write(txt)
    print(f"wrote {OUT} ({len(vec) // 1024} KB) and {TS}"); return 0


if __name__ == "__main__":
    sys.exit(main("--check" in sys.argv))
