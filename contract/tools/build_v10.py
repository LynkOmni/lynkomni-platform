#!/usr/bin/env python3
"""Builds contract version 10 from version 9 (build section 4, step C1: the conversation events of CHAT UPDATE, master
blueprint 74.24; catalog/chat.v1.json).

Version 10 adds eight conversation events. A device may open a conversation, post a message, fix its own text message within
the edit window, close a conversation and report one: those work offline and send in order, never doubled. The cloud alone
writes what only it can know: that a message reached the other side, was seen or failed (MessageStateChanged), who a chat was
routed to and why (ConversationRouted) and a hand-over (ConversationHandedOver).

What is never in an event: the text of a message (it lives in the message store, encrypted, kept and deleted by each country's
rules; the event carries only its sha256 for disputes), live signs, card numbers, PINs, codes, a position, a vote or a person's
name. ConversationCardSent's list of cards grows to the cards of catalog/chat.v1.json (an older event keeps its card).

Nothing older changes: version 9 events read as version 10 as they are (upcaster 9 to 10 only raises the version).

    python3 contract/tools/build_v10.py          writes contract/event-payloads.v10.json and contract/command-policy-register.v10.json
    python3 contract/tools/build_v10.py --check  fails when either file is out of date (tests/test_contract_v10.py runs it)
"""
import copy, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
with open(os.path.join(os.path.dirname(ROOT), "catalog", "chat.v1.json"), encoding="utf-8") as _f:
    CHAT = json.load(_f)
U7, SHA, INT0 = {"$ref": "#/$defs/uuid7"}, {"$ref": "#/$defs/sha256"}, {"type": "integer", "minimum": 0}
BOOL = {"type": "boolean"}


def enum(*v):
    return {"enum": list(v)}


def ev(origins, required, props, note):
    return {"origins": origins, "since": "v10", "blueprint": "74 CHAT UPDATE", "note": note,
            "payload": {"type": "object", "additionalProperties": False, "required": required, "properties": props}}


S, DS = ["server"], ["device", "server"]
KINDS = enum(*CHAT["kinds"])
AUTHORS = enum(*CHAT["authors"])
DESKS = enum("general", "orders", "payments", "account", "storefront", "security", "safety", "fraud", "tax", "devices", "team")
EVENTS = {
    "ConversationOpened": ev(DS, ["conversation_id", "kind", "opened_by"],
        {"conversation_id": U7, "kind": KINDS, "opened_by": AUTHORS, "about_kind": enum(*CHAT["chat_about"]["records"]), "about_id": U7},
        "A conversation (LOCNV-) was opened: customer and business, Storefront or support; never personal, group or staff-to-staff chat. 'Chat about this' names the record it is about."),
    "MessagePosted": ev(DS, ["message_id", "conversation_id", "author", "body", "content_sha256"],
        {"message_id": U7, "conversation_id": U7, "author": AUTHORS, "body": enum(*CHAT["bodies"]), "device_seq": INT0,
         "reply_to": U7, "masked": BOOL, "content_sha256": SHA},
        "A message was written (queued on the device, sent when it leaves). The text is never in the event: it is kept in the message store, already masked on the device (card numbers, PINs and codes), and the event carries its sha256 only. message_id is the device's own id, so a repeat is dropped."),
    "MessageEdited": ev(DS, ["message_id", "content_sha256"],
        {"message_id": U7, "content_sha256": SHA},
        "The author fixed their own text message within the edit window (15 minutes); it is marked edited and the first version is kept for disputes."),
    "MessageStateChanged": ev(S, ["message_id", "state"],
        {"message_id": U7, "state": enum("accepted", "confirmed", "failed"), "reason": enum("not_delivered", "blocked", "too_large", "too_fast", "conversation_closed")},
        "Cloud only: the message reached the other side (accepted), was seen or played (confirmed; never written for a reader who turned 'seen' off) or failed. A device never writes these."),
    "ConversationRouted": ev(S, ["conversation_id", "to", "reason"],
        {"conversation_id": U7, "to": enum("assistant", "desk", "helper", "staff", "line", "case"), "desk": DESKS, "helper_id": U7,
         "reason": enum(*CHAT["routing"]["reasons"]), "translate": BOOL},
        "Cloud only: who gets the chat and why, from the routing register (LynkAssist first, the fast lane, the same helper, language, least busy, the owner's team rules). Answers 'Why did I get this chat?' and 'Who is helping me?'."),
    "ConversationHandedOver": ev(S, ["conversation_id", "from", "to"],
        {"conversation_id": U7, "from": enum("assistant", "helper", "staff"), "to": enum("helper", "staff", "desk", "line"), "desk": DESKS},
        "Cloud only: a warm hand-over; the person who joins gets a short summary and the full history, so the customer never repeats themselves."),
    "ConversationClosed": ev(DS, ["conversation_id", "reason"],
        {"conversation_id": U7, "reason": enum("solved", "quiet", "customer_left", "blocked")},
        "A conversation was closed; one new message reopens it. Never deletes anything."),
    "ConversationReported": ev(DS, ["conversation_id", "reason"],
        {"conversation_id": U7, "message_id": U7, "reason": enum("abuse", "spam", "scam", "safety", "impersonation")},
        "Block and report in one tap; the report goes to the safety desk from either side."),
}


def cmd(name, emits, rejections):
    return {"name": name, "class": "A", "v10": True, "emits": emits, "permission": None, "channels": ["mobile", "web"],
            "offline": {"allowed": True}, "cloud_may_reject": False, "cloud_outcomes": ["accepted", "accepted_flagged"],
            "local_rejections": rejections, "ui_states": ["recorded", "pending_sync", "accepted"], "local_only": True}


COMMANDS = [
    cmd("OpenConversation", ["ConversationOpened"], ["kind_not_allowed", "blocked"]),
    cmd("PostMessage", ["MessagePosted"], ["conversation_closed", "blocked", "too_long", "too_fast"]),
    cmd("EditMessage", ["MessageEdited"], ["edit_window_passed", "not_your_message", "not_text"]),
    cmd("CloseConversation", ["ConversationClosed"], ["already_closed"]),
    cmd("ReportConversation", ["ConversationReported"], ["already_reported"]),
]


def load(name):
    with open(os.path.join(ROOT, name), encoding="utf-8") as f:
        return json.load(f)


def build():
    v10 = copy.deepcopy(load("event-payloads.v9.json"))
    v10["$id"] = "lynkomni/event-payloads.v10"
    v10["description"] = ("Contract version 10 (build section 4, step C1): version 9 plus the conversation events of CHAT UPDATE (74.24): opened, "
                          "posted, edited, state, routed, handed over, closed and reported; the cards of a conversation follow catalog/chat.v1.json. "
                          "Upcaster 9 to 10 in contract/upcasters.v1.json only raises the version.")
    for e in v10["events"].values():
        e["schema_version"] = 10
    cards = v10["events"]["ConversationCardSent"]["payload"]["properties"]["card"]
    old = list(cards["enum"])
    cards["enum"] = old + [k for k in CHAT["cards"]["kinds"] if k not in old]
    for name, e in EVENTS.items():
        if name in v10["events"]:
            raise SystemExit(f"{name} already exists in version 9")
        e = copy.deepcopy(e)
        e["payload"]["properties"]["side"] = {"$ref": "#/$defs/side"}
        v10["events"][name] = {"schema_version": 10, **e}
    reg = copy.deepcopy(load("command-policy-register.v9.json"))
    reg["$id"] = "lynkomni/command-policy-register.v10"
    reg["description"] = ("Command register version 10 (build section 4, step C1): version 9's commands unchanged plus opening a conversation, "
                          "posting and fixing a message, closing and reporting, which work offline. Message states, routing and hand-overs are "
                          "written by the cloud alone.")
    names = {c["name"] for c in reg["commands"]}
    for c in COMMANDS:
        if c["name"] in names:
            raise SystemExit(f"command {c['name']} already exists")
        reg["commands"].append(copy.deepcopy(c))
    return {"event-payloads.v10.json": v10, "command-policy-register.v10.json": reg}


def main(check=False):
    stale = []
    for name, data in build().items():
        text = json.dumps(data, indent=1, ensure_ascii=False) + "\n"
        path = os.path.join(ROOT, name)
        if check:
            if not os.path.isfile(path) or open(path, encoding="utf-8").read() != text:
                stale.append(name)
        else:
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)
    if stale:
        print("out of date: " + ", ".join(stale) + " (run python3 contract/tools/build_v10.py)")
        return 1
    print("contract v10 is current" if check else "wrote contract v10")
    return 0


if __name__ == "__main__":
    sys.exit(main("--check" in sys.argv))
