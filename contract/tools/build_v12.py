#!/usr/bin/env python3
"""Builds contract version 12 from version 11 (build section 4, step E2: the voting events of VOTE UPDATE, master blueprint 68;
catalog/vote.v1.json).

Version 12 adds the facts of a vote from set-up to certified result. A polling-place device may cast a ballot and record a
challenged ballot offline (sealed batches sent later); everything else is written by the cloud alone: rules locked or changed
(two people and a reason), trustees' key parts, the locked roll, opening and closing, a vote that replaces an earlier one, the
shuffle, the published count, the certified result, flags for unusual patterns and a reissued credential.

What is never in an event (blueprint 68.7): a choice, a voter's identity beside a ballot, a key part, a credential, a
contact detail or a time of casting. A ballot appears only as its tracking code (sha256).

Nothing older changes: version 11 events read as version 12 as they are (upcaster 11 to 12 only raises the version).

    python3 contract/tools/build_v12.py          writes contract/event-payloads.v12.json and contract/command-policy-register.v12.json
    python3 contract/tools/build_v12.py --check  fails when either file is out of date (tests/test_contract_v12.py runs it)
"""
import copy, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAT = os.path.join(os.path.dirname(ROOT), "catalog")
with open(os.path.join(CAT, "vote.v1.json"), encoding="utf-8") as _f:
    VOTE = json.load(_f)
U7, SHA = {"$ref": "#/$defs/uuid7"}, {"$ref": "#/$defs/sha256"}
INT0, INT1 = {"type": "integer", "minimum": 0}, {"type": "integer", "minimum": 1}
VOTE_ID = U7                    # the vote's internal id, as in VoteRollImported (v9); its public LOVOT- id comes from core/ids.py


def enum(*v):
    return {"enum": list(v)}


def ev(origins, required, props, note):
    return {"origins": origins, "since": "v12", "blueprint": "68 LynkVote", "note": note,
            "payload": {"type": "object", "additionalProperties": False, "required": required, "properties": props}}


S, DS = ["server"], ["device", "server"]
EVENTS = {
    "VoteCreated": ev(S, ["vote_id", "kind", "method", "assurance"],
        {"vote_id": VOTE_ID, "kind": enum(*VOTE["kinds"]), "method": enum(*VOTE["methods"]), "assurance": enum(*VOTE["assurance"]), "contests": INT1, "federation_id": U7},
        "Cloud only: an organiser set up a vote with its kind, counting method and assurance level; a branch vote of a federation names the federation's vote."),
    "VoteRulesLocked": ev(S, ["vote_id", "rules_sha256"],
        {"vote_id": VOTE_ID, "rules_sha256": SHA},
        "Cloud only: the rules locked when voting opened; their fingerprint is published."),
    "VoteRulesChanged": ev(S, ["vote_id", "rules_sha256", "reason", "approvers"],
        {"vote_id": VOTE_ID, "rules_sha256": SHA, "reason": enum("error_in_ballot", "candidate_withdrew", "court_order", "time_extended_by_rule", "other_stated"), "approvers": {"type": "integer", "minimum": 2}},
        "Cloud only: a change after the rules locked, approved by two authorised people with a stated reason; it shows in the public log."),
    "TrusteeKeyPublished": ev(S, ["vote_id", "trustee", "commitments_sha256", "proof_ok"],
        {"vote_id": VOTE_ID, "trustee": INT1, "commitments_sha256": SHA, "proof_ok": {"type": "boolean"}},
        "Cloud only: a trustee published the public side of their key part in the key ceremony, with its proof checked. The key part itself is never in an event."),
    "VoteRollLocked": ev(S, ["vote_id", "voters", "roll_sha256"],
        {"vote_id": VOTE_ID, "voters": INT0, "roll_sha256": SHA},
        "Cloud only: the final roll locked with its own fingerprint after the period for voters to check their entry."),
    "VoteOpened": ev(S, ["vote_id", "key_sha256"],
        {"vote_id": VOTE_ID, "key_sha256": SHA},
        "Cloud only: voting opened under the trustees' joint key."),
    "BallotCast": ev(DS, ["vote_id", "tracking_code", "way"],
        {"vote_id": VOTE_ID, "tracking_code": SHA, "way": enum(*VOTE["ways"]), "batch_id": U7},
        "A locked ballot joined the public list under its tracking code. A polling-place device may cast offline and send sealed batches later. Never the choice, never who cast it, never when."),
    "BallotChallenged": ev(DS, ["vote_id", "tracking_code"],
        {"vote_id": VOTE_ID, "tracking_code": SHA},
        "A voter challenged the device to prove it locked the ballot honestly; a challenged ballot is opened for that voter and never cast."),
    "BallotReplaced": ev(S, ["vote_id", "tracking_code", "by"],
        {"vote_id": VOTE_ID, "tracking_code": SHA, "by": enum("vote_again", "in_person", "duress_rule")},
        "Cloud only: where the rules allow, an earlier ballot no longer counts because the voter voted again or in person."),
    "VoteReminderSent": ev(S, ["vote_id", "round"],
        {"vote_id": VOTE_ID, "round": INT1},
        "Cloud only: a round of reminders went to voters on the roll who have not voted yet; who they are is never in the event."),
    "VoteClosed": ev(S, ["vote_id", "ballots", "list_head"],
        {"vote_id": VOTE_ID, "ballots": INT0, "list_head": SHA},
        "Cloud only: voting closed; the number of ballots and the head of the public list are published. Nobody saw totals before this."),
    "BallotsShuffled": ev(S, ["vote_id", "round", "proof_sha256"],
        {"vote_id": VOTE_ID, "round": INT1, "proof_sha256": SHA},
        "Cloud only: ballots to be read one by one were shuffled and re-locked with a proof anyone can check."),
    "TallyPublished": ev(S, ["vote_id", "results_sha256", "proofs_sha256", "trustees"],
        {"vote_id": VOTE_ID, "results_sha256": SHA, "proofs_sha256": SHA, "trustees": INT1},
        "Cloud only: the trustees opened the totals together; the results and every proof are published by fingerprint."),
    "VoteResultCertified": ev(S, ["vote_id", "certificate_sha256", "sealed"],
        {"vote_id": VOTE_ID, "certificate_sha256": SHA, "sealed": {"type": "boolean"}},
        "Cloud only: the official result was signed; sealed is true only when the trust-service partner sealed and time-stamped it."),
    "VoteAnomalyFlagged": ev(S, ["vote_id", "kind"],
        {"vote_id": VOTE_ID, "kind": enum("many_from_one_device", "many_from_one_network", "roll_bulk_change", "batch_clash", "mirror_mismatch", "late_batch")},
        "Cloud only: an unusual pattern was flagged to the organiser and observers. They decide, never LynkOmni; a flag is never an accusation."),
    "VoteCredentialReissued": ev(S, ["vote_id", "reason"],
        {"vote_id": VOTE_ID, "reason": enum("lost_link", "lost_code", "wrong_contact")},
        "Cloud only: a voter got a new link or code and the old one was cancelled; who it was is never in the event."),
    "DecisionRecorded": ev(S, ["decision_id", "outcome", "actions"],
        {"decision_id": U7, "vote_id": U7, "outcome": enum("passed", "rejected", "noted"), "actions": INT0, "due": {"$ref": "#/$defs/date"}},
        "Cloud only: the governance home's register of decisions gained one, from a vote or a meeting, with how many actions are owed; who must act is kept in the register, never in the event."),
    "MinutesSigned": ev(S, ["minutes_id", "minutes_sha256", "signers"],
        {"minutes_id": U7, "minutes_sha256": SHA, "signers": INT1},
        "Cloud only: the minutes of a meeting were signed electronically by everyone who had to sign; the text stays in LynkFiles, the event keeps its fingerprint."),
}


def cmd(name, emits, rejections):
    return {"name": name, "class": "B", "v12": True, "emits": emits, "permission": None, "any_authenticated": True, "channels": ["kiosk", "mobile", "web"],
            "offline": {"allowed": True, "sealed": True, "note": "Only a polling-place device keeps ballots offline, in a sealed batch sent when it reconnects; a phone or browser casts online."},
            "cloud_may_reject": True, "cloud_outcomes": ["accepted", "accepted_flagged", "failed"],
            "local_rejections": rejections, "ui_states": ["queued", "sent", "accepted", "failed"], "local_only": False}


COMMANDS = [
    cmd("CastBallot", ["BallotCast"], ["vote_not_open", "ballot_proof_failed", "already_voted_here"]),
    cmd("ChallengeBallot", ["BallotChallenged"], ["vote_not_open"]),
]


def load(name):
    with open(os.path.join(ROOT, name), encoding="utf-8") as f:
        return json.load(f)


def build():
    v12 = copy.deepcopy(load("event-payloads.v11.json"))
    v12["$id"] = "lynkomni/event-payloads.v12"
    v12["description"] = ("Contract version 12 (build section 4, step E2): version 11 plus the voting events of VOTE UPDATE (68): a vote set up, its rules "
                          "locked or changed by two people, trustees' key parts, the locked roll, opening, ballots cast and challenged under their tracking codes, "
                          "a replaced ballot, reminder rounds, closing, the shuffle, the published count, the certified result, flags and reissued credentials, and the governance home's decisions and signed minutes. "
                          "A choice, a voter's identity beside a ballot or a key part is never in an event. Upcaster 11 to 12 in contract/upcasters.v1.json only raises the version.")
    for e in v12["events"].values():
        e["schema_version"] = 12
    for name, e in EVENTS.items():
        if name in v12["events"]:
            raise SystemExit(f"{name} already exists in version 11")
        e = copy.deepcopy(e)
        e["payload"]["properties"]["side"] = {"$ref": "#/$defs/side"}
        v12["events"][name] = {"schema_version": 12, **e}
    reg = copy.deepcopy(load("command-policy-register.v11.json"))
    reg["$id"] = "lynkomni/command-policy-register.v12"
    reg["description"] = ("Command register version 12 (build section 4, step E2): version 11's commands unchanged plus casting and challenging a ballot, "
                          "which a polling-place device may do offline in sealed batches; the cloud checks every proof and may refuse. Everything else about a vote is written by the cloud alone.")
    names = {c["name"] for c in reg["commands"]}
    for c in COMMANDS:
        if c["name"] in names:
            raise SystemExit(f"command {c['name']} already exists")
        reg["commands"].append(copy.deepcopy(c))
    return {"event-payloads.v12.json": v12, "command-policy-register.v12.json": reg}


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
        print("out of date: " + ", ".join(stale) + " (run python3 contract/tools/build_v12.py)")
        return 1
    print("contract v12 is current" if check else "wrote contract v12")
    return 0


if __name__ == "__main__":
    sys.exit(main("--check" in sys.argv))
