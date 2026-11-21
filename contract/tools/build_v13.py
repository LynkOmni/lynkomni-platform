"""Builds contract version 13 from version 12 (build section 4, step E3: LynkFiles' document engine, SIX SERVICES UPDATE 69.7;
catalog/files.v1.json).

Version 13 adds the facts of signing and sharing a document and keeping its versions: a signature request, each signature, a
refusal, the completed document, a share link made or stopped, a new version, a legal hold and a deletion. A new version made
offline on a device (an edited form or a scan) may come from the device; everything else is written by the cloud alone, and an
identity-checked or qualified signature is written only when its partner confirms.

What is never in an event: a file's content or name, a signer's name or contact, a link's address or password, or a verification
code (only its fingerprint). A file appears only as its id and sha256.

Nothing older changes: version 12 events read as version 13 as they are (upcaster 12 to 13 only raises the version).

    python3 contract/tools/build_v13.py          writes contract/event-payloads.v13.json and contract/command-policy-register.v13.json
    python3 contract/tools/build_v13.py --check  fails when either file is out of date (tests/test_contract_v13.py runs it)
"""
import copy, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAT = os.path.join(os.path.dirname(ROOT), "catalog")
with open(os.path.join(CAT, "files.v1.json"), encoding="utf-8") as _f:
    FILES = json.load(_f)
U7, SHA = {"$ref": "#/$defs/uuid7"}, {"$ref": "#/$defs/sha256"}
INT0, INT1 = {"type": "integer", "minimum": 0}, {"type": "integer", "minimum": 1}
BOOL, DATE = {"type": "boolean"}, {"$ref": "#/$defs/date"}


def enum(*v):
    return {"enum": list(v)}


def ev(origins, required, props, note):
    return {"origins": origins, "since": "v13", "blueprint": "69.7 LynkFiles", "note": note,
            "payload": {"type": "object", "additionalProperties": False, "required": required, "properties": props}}


S, DS = ["server"], ["device", "server"]
LEVEL = enum(*FILES["signing"]["levels"])
EVENTS = {
    "SignatureRequested": ev(S, ["request_id", "document_id", "level", "order", "signers"],
        {"request_id": U7, "document_id": U7, "level": LEVEL, "order": enum(*FILES["signing"]["orders"]), "signers": {"type": "integer", "minimum": 1, "maximum": FILES["signing"]["max_signers"]}, "expires_on": DATE},
        "Cloud only: a document was sent for signing to a number of signers, in order or together; who they are is never in the event."),
    "DocumentSigned": ev(S, ["request_id", "turn", "level"],
        {"request_id": U7, "turn": INT1, "level": LEVEL},
        "Cloud only: the signer whose turn it was signed. An identity-checked or qualified signature is written only when its partner confirms."),
    "SignatureDeclined": ev(S, ["request_id", "turn", "reason"],
        {"request_id": U7, "turn": INT1, "reason": enum("declined", "wrong_document", "not_me")},
        "Cloud only: a signer refused; the request stops and the sender is told."),
    "SignatureCompleted": ev(S, ["request_id", "document_id", "signed_sha256", "code_sha256"],
        {"request_id": U7, "document_id": U7, "signed_sha256": SHA, "code_sha256": SHA},
        "Cloud only: every signer signed; the signed document's fingerprint and the fingerprint of its verification code are kept."),
    "ShareLinkCreated": ev(S, ["link_id", "document_id", "rights", "days", "password", "download_blocked"],
        {"link_id": U7, "document_id": U7, "rights": enum(*FILES["sharing"]["rights"]), "days": {"type": "integer", "minimum": 1, "maximum": FILES["sharing"]["max_days"]}, "password": BOOL, "download_blocked": BOOL},
        "Cloud only: a share link was made with its rights and end date; the address and any password are never in the event."),
    "ShareLinkStopped": ev(S, ["link_id", "reason"],
        {"link_id": U7, "reason": enum("owner", "expired", "legal_hold", "deleted")},
        "Cloud only: a share link stopped working."),
    "FileVersionAdded": ev(DS, ["document_id", "version", "sha256"],
        {"document_id": U7, "version": {"type": "integer", "minimum": 2}, "sha256": SHA},
        "A new version of a kept file (an edited form or a new scan); earlier versions stay and can be restored. May be made offline on a device."),
    "LegalHoldChanged": ev(S, ["document_id", "on"],
        {"document_id": U7, "on": BOOL},
        "Cloud only: a legal hold was set or lifted; nothing under hold is changed or deleted."),
    "FileDeleted": ev(S, ["document_id", "reason"],
        {"document_id": U7, "reason": enum("owner", "retention")},
        "Cloud only: a file was deleted by its owner or at the end of its keeping time, never while under legal hold."),
}


def cmd(name, emits, rejections):
    return {"name": name, "class": "A", "v13": True, "emits": emits, "permission": None, "channels": ["mobile", "web"],
            "offline": {"allowed": True}, "cloud_may_reject": False, "cloud_outcomes": ["accepted", "accepted_flagged"],
            "local_rejections": rejections, "ui_states": ["recorded", "pending_sync", "accepted"], "local_only": True}


COMMANDS = [
    cmd("AddFileVersion", ["FileVersionAdded"], ["file_not_kept_offline", "under_legal_hold"]),
]


def load(name):
    with open(os.path.join(ROOT, name), encoding="utf-8") as f:
        return json.load(f)


def build():
    v13 = copy.deepcopy(load("event-payloads.v12.json"))
    v13["$id"] = "lynkomni/event-payloads.v13"
    v13["description"] = ("Contract version 13 (build section 4, step E3): version 12 plus LynkFiles' document engine (69.7): signature requests, each "
                          "signature, refusals, completed documents, share links made and stopped, new versions, legal holds and deletions. A file's content or "
                          "name, a signer's name or contact, a link's address or password and a verification code are never in an event. Upcaster 12 to 13 in "
                          "contract/upcasters.v1.json only raises the version.")
    for e in v13["events"].values():
        e["schema_version"] = 13
    for name, e in EVENTS.items():
        if name in v13["events"]:
            raise SystemExit(f"{name} already exists in version 12")
        e = copy.deepcopy(e)
        e["payload"]["properties"]["side"] = {"$ref": "#/$defs/side"}
        v13["events"][name] = {"schema_version": 13, **e}
    reg = copy.deepcopy(load("command-policy-register.v12.json"))
    reg["$id"] = "lynkomni/command-policy-register.v13"
    reg["description"] = ("Command register version 13 (build section 4, step E3): version 12's commands unchanged plus adding a new version of a kept file, "
                          "which a device may do offline. Signing, sharing, holds and deletions are written by the cloud alone.")
    names = {c["name"] for c in reg["commands"]}
    for c in COMMANDS:
        if c["name"] in names:
            raise SystemExit(f"command {c['name']} already exists")
        reg["commands"].append(copy.deepcopy(c))
    return {"event-payloads.v13.json": v13, "command-policy-register.v13.json": reg}


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
        print("out of date: " + ", ".join(stale) + " (run python3 contract/tools/build_v13.py)")
        return 1
    print("contract v13 is current" if check else "wrote contract v13")
    return 0


if __name__ == "__main__":
    sys.exit(main("--check" in sys.argv))
