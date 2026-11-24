#!/usr/bin/env python3
"""Builds contract version 17 from version 16 (BETTING UPDATE, owner 2026-11-24, master blueprint section 86: LynkBet, the betting
service for shops of licensed betting operators; core/betting.py, catalog/betting.v1.json).

Version 17 adds what a betting counter asks and what the cloud alone writes from the licensed operator. The device asks to place a
bet (online, or a queued slip when the operator has switched offline slips on), records a ticket check, asks the operator to lock a
payout, records the cash handed over after the lock, refers a big win, asks to cancel a bet and opens a dispute. The operator's
answers are cloud only: a bet confirmed or failed (a queued slip that fails is refunded in full), a payout locked or refused, a
cancellation, a referral's steps, the weekly settlement and commission, a Please check flag, a dispute's outcome and a shop's
approval. It also extends the Emulator Panel's events with the new betting counter (bet.counter); version 7's list stays as published.

What is never in an event: a customer's name, contact, ID number or photo, a ticket's printed barcode image, a position.

Nothing older changes: version 16 events read as version 17 as they are (upcaster 16 to 17 only raises the version).

    python3 contract/tools/build_v17.py          writes contract/event-payloads.v17.json and contract/command-policy-register.v17.json
    python3 contract/tools/build_v17.py --check  fails when either file is out of date (tests/test_contract_v17.py runs it)
"""
import copy, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
U7, UU = {"$ref": "#/$defs/uuid7"}, {"$ref": "#/$defs/uuid"}
BOOL = {"type": "boolean"}
INT1 = {"type": "integer", "minimum": 1}
INT0 = {"type": "integer", "minimum": 0}
MONEY, SIGNED, CUR, PREF, DATE = ({"$ref": "#/$defs/money"}, {"$ref": "#/$defs/money_signed"}, {"$ref": "#/$defs/currency"},
                                  {"$ref": "#/$defs/provider_ref"}, {"$ref": "#/$defs/date"})


def enum(*v):
    return {"enum": list(v)}


def ev(origins, required, props, note, bp="86 BETTING UPDATE"):
    return {"origins": origins, "since": "v17", "blueprint": bp, "note": note,
            "payload": {"type": "object", "additionalProperties": False, "required": required, "properties": props}}


def _register():
    with open(os.path.join(os.path.dirname(ROOT), "catalog", "betting.v1.json"), encoding="utf-8") as f:
        return json.load(f)


BET = _register()
S, D = ["server"], ["device"]
KIND = enum("sports", "live", "virtual", "racing", "lottery", "esports", "other")
FAIL = enum("partner_declined", "odds_changed", "game_started", "limit_exceeded", "self_excluded", "age", "timeout", "provider_error", "other")
EVENTS = {
    "BetRequested": ev(D, ["request_id", "operator_id", "kind", "selections", "stake", "currency", "method", "queued_offline"],
        {"request_id": U7, "operator_id": UU, "kind": KIND, "selections": INT1, "stake": MONEY, "currency": CUR, "method": enum(*BET["stake_methods"]),
         "queued_offline": BOOL},
        "The counter asked the operator to take a bet. Online it is sent at once; offline it is a queued slip (never a ticket) and only where the operator switched offline slips on, never for live betting. Never on credit."),
    "BetConfirmed": ev(S, ["request_id", "ticket_ref", "possible_win", "currency"],
        {"request_id": UU, "ticket_ref": PREF, "possible_win": MONEY, "currency": CUR},
        "Cloud only: the operator took the bet and gave its ticket reference; the ticket prints. Stake cash is held for the operator."),
    "BetFailed": ev(S, ["request_id", "reason", "refund_due"],
        {"request_id": UU, "reason": FAIL, "refund_due": BOOL},
        "Cloud only: the operator refused the bet. A queued slip that is refused is refunded in full (refund_due)."),
    "BetTicketChecked": ev(D, ["ticket_ref", "answer"],
        {"ticket_ref": PREF, "answer": enum(*BET["check_order"])},
        "A ticket was scanned and the operator's answer shown. Only the operator's amount is ever paid."),
    "BetPayoutLockAsked": ev(D, ["ticket_ref", "operator_id"], {"ticket_ref": PREF, "operator_id": UU},
        "The counter asked the operator to lock a payout before any cash leaves the drawer. Online only."),
    "BetPayoutLocked": ev(S, ["ticket_ref", "payable", "currency"], {"ticket_ref": PREF, "payable": MONEY, "currency": CUR},
        "Cloud only: the operator locked the payout; the ticket can never be paid again, a copy included."),
    "BetPayoutLockFailed": ev(S, ["ticket_ref", "reason"], {"ticket_ref": PREF, "reason": enum("already_paid", "not_payable", "timeout", "other")},
        "Cloud only: the operator refused the lock; nothing is paid."),
    "BetPaidOut": ev(D, ["ticket_ref", "paid", "currency", "from"], {"ticket_ref": PREF, "paid": MONEY, "currency": CUR, "from": enum("shop_cash", "mobile_money", "bank")},
        "The winnings were handed over after the operator's lock (state confirmed)."),
    "BetReferred": ev(D, ["referral_id", "ticket_ref", "operator_id", "way", "evidence_ref"],
        {"referral_id": U7, "ticket_ref": PREF, "operator_id": UU, "way": enum(*BET["payout_ways"]), "evidence_ref": PREF},
        "A big win was referred to the operator's head office. The photos of the ticket and ID go only to the operator; the event keeps a reference."),
    "BetReferralAnswered": ev(S, ["referral_id", "step"], {"referral_id": UU, "step": enum("checking", "approved", "paid", "refused")},
        "Cloud only: the operator moved a referral a step; only its answers move the tracker."),
    "BetCancelAsked": ev(D, ["ticket_ref", "manager_approved"], {"ticket_ref": PREF, "manager_approved": BOOL},
        "A manager asked to cancel a bet within the operator's allowed time, before any game started. Online only."),
    "BetCancelled": ev(S, ["ticket_ref", "refund", "currency"], {"ticket_ref": PREF, "refund": MONEY, "currency": CUR},
        "Cloud only: the operator cancelled the bet; the stake is returned."),
    "BetDisputeOpened": ev(D, ["dispute_id", "ticket_ref"], {"dispute_id": U7, "ticket_ref": PREF},
        "A customer disputes a result; the ticket and its history go to the operator."),
    "BetDisputeAnswered": ev(S, ["dispute_id", "outcome"], {"dispute_id": UU, "outcome": enum("upheld", "refused")},
        "Cloud only: the operator answered a dispute."),
    "BetSettlementRecorded": ev(S, ["statement_id", "operator_id", "period_end", "stakes", "payouts", "commission", "net", "currency"],
        {"statement_id": U7, "operator_id": UU, "period_end": DATE, "stakes": MONEY, "payouts": MONEY, "commission": MONEY, "net": SIGNED, "currency": CUR},
        "Cloud only: the operator's statement for a period: stakes held for it, payouts, the shop's commission and what is owed either way. Posted once to LynkAcc; differences are flagged."),
    "BetFlagRaised": ev(S, ["flag", "count"], {"flag": enum("repeat_scans", "many_big_payouts", "stake_splitting", "cash_churn"), "count": INT0},
        "Cloud only: a Please check flag for the owner and the operator. Never an accusation and never a block."),
    "BetShopStatusChanged": ev(S, ["operator_id", "status"], {"operator_id": UU, "status": enum("approved", "paused", "ended")},
        "Cloud only: the operator approved, paused or ended this shop through the Partner Hub."),
}


def cmd(name, emits, cls, rejections, offline):
    base = {"name": name, "class": cls, "v17": True, "emits": emits, "permission": None, "channels": ["mobile", "web"], "local_only": True,
            "local_rejections": rejections}
    if cls == "B":
        base.update({"offline": {"allowed": True, "note": offline}, "cloud_may_reject": True, "cloud_outcomes": ["accepted_pending_provider", "rejected_provider_error"],
                     "ui_states": ["queued", "sent", "accepted", "confirmed", "failed"]})
    elif cls == "C":
        base.update({"offline": {"allowed": False, "behavior": offline}, "cloud_may_reject": True, "cloud_outcomes": ["accepted_pending_provider", "rejected_provider_error"],
                     "ui_states": ["sent", "confirmed", "failed"]})
    else:
        base.update({"offline": {"allowed": True}, "cloud_may_reject": False, "cloud_outcomes": ["accepted", "accepted_flagged"],
                     "ui_states": ["recorded", "pending_sync", "accepted"]})
    return base


COMMANDS = [
    cmd("PlaceBet", ["BetRequested"], "B", ["age_not_confirmed", "self_excluded", "stake_out_of_limits", "method_not_allowed", "offline_slips_off", "live_offline"],
        "Online it is sent at once. Offline only as a queued slip where the operator switched offline slips on, never for live betting, within the operator's offline limits; a refused slip is refunded in full."),
    cmd("RecordTicketCheck", ["BetTicketChecked"], "A", ["ticket_missing"], None),
    cmd("AskPayoutLock", ["BetPayoutLockAsked"], "C", ["offline_not_possible", "not_payable"], "refused with offline_not_possible: a payout needs the operator's lock"),
    cmd("RecordPayout", ["BetPaidOut"], "A", ["not_locked"], None),
    cmd("ReferBigWin", ["BetReferred"], "C", ["offline_not_possible", "photos_missing"], "refused with offline_not_possible: a referral goes to the operator at once"),
    cmd("AskCancelBet", ["BetCancelAsked"], "C", ["offline_not_possible", "manager_needed", "game_started"], "refused with offline_not_possible"),
    cmd("OpenBetDispute", ["BetDisputeOpened"], "A", ["ticket_missing"], None),
]


def load(name):
    with open(os.path.join(ROOT, name), encoding="utf-8") as f:
        return json.load(f)


def emulator_ids():
    with open(os.path.join(os.path.dirname(ROOT), "catalog", "emulators.v1.json"), encoding="utf-8") as f:
        return [e["id"] for e in json.load(f)["emulators"]]


def build():
    v17 = copy.deepcopy(load("event-payloads.v16.json"))
    v17["$id"] = "lynkomni/event-payloads.v17"
    v17["description"] = ("Contract version 17 (BETTING UPDATE, master blueprint section 86): version 16 plus LynkBet's events. The counter only asks; "
                          "the licensed operator's answers are written by the cloud alone. A customer's name, contact, ID number or photo is never in an "
                          "event. The Emulator Panel's events also name the new betting counter. Upcaster 16 to 17 in contract/upcasters.v1.json only "
                          "raises the version.")
    ids = emulator_ids()
    for e in v17["events"].values():
        e["schema_version"] = 17
        p = e["payload"]["properties"].get("emulator")
        if isinstance(p, dict) and "enum" in p:
            p["enum"] = list(ids)
    for name, e in EVENTS.items():
        if name in v17["events"]:
            raise SystemExit(f"{name} already exists in version 16")
        e = copy.deepcopy(e)
        e["payload"]["properties"]["side"] = {"$ref": "#/$defs/side"}
        v17["events"][name] = {"schema_version": 17, **e}
    reg = copy.deepcopy(load("command-policy-register.v16.json"))
    reg["$id"] = "lynkomni/command-policy-register.v17"
    reg["description"] = ("Command register version 17 (BETTING UPDATE, master blueprint section 86): version 16's commands plus LynkBet's: placing a bet "
                          "(class B: a queued slip offline only where the operator allows it), asking for a payout lock, referring a big win and asking to "
                          "cancel (class C: online only), and recording a ticket check, a payout after the lock and a dispute (class A).")
    names = {c["name"] for c in reg["commands"]}
    for c in COMMANDS:
        if c["name"] in names:
            raise SystemExit(f"command {c['name']} already exists")
        reg["commands"].append(copy.deepcopy(c))
    return {"event-payloads.v17.json": v17, "command-policy-register.v17.json": reg}


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
        print("out of date: " + ", ".join(stale) + " (run python3 contract/tools/build_v17.py)")
        return 1
    print("contract v17 is current" if check else "wrote contract v17")
    return 0


if __name__ == "__main__":
    sys.exit(main("--check" in sys.argv))
