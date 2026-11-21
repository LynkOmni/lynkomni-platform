"""LynkFiles' rules (SIX SERVICES UPDATE, master blueprint 69.7; section 4 step E3): catalog/files.v1.json.

This module is the Python reference; ts/src/files.ts must agree on every case of contract/vectors/files.v1.json
(python3 tools/files_vectors.py after a change). It holds only pure rules: what a file's bytes are, who signs next, the state of a
signature request, whether a share link may open, the verification code's shape and whether a file fits the plan's storage."""
import json, os

from core.queue_tickets import ALPHABET

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
with open(os.path.join(_ROOT, "catalog", "files.v1.json"), encoding="utf-8") as _f:
    FILES = json.load(_f)

GB = 1024 ** 3


def sniff(data):
    """The type from the first bytes: a name from content.allowed, "blocked" for a program, or None when it is not a kept type."""
    head = bytes(data[:16]).hex()
    if any(head.startswith(b) for b in FILES["content"]["blocked_starts"]):
        return "blocked"
    for name, magic in FILES["content"]["allowed"].items():
        if magic and head.startswith(magic):
            return name
    try:
        text = bytes(data).decode("utf-8")
    except UnicodeDecodeError:
        return None
    return "text" if all(ch in "\t\n\r" or ord(ch) >= 32 and ord(ch) != 127 for ch in text) else None


def next_signers(order, signers, signed, declined=()):
    """Who may sign now. in_order: the first who has not signed; together: everyone who has not. Nobody once someone declined."""
    if order not in FILES["signing"]["orders"]:
        raise ValueError("unknown order")
    if set(declined) & set(signers):
        return []
    left = [s for s in signers if s not in signed]
    return left[:1] if order == "in_order" else left


def request_state(signers, signed, declined=(), expired=False, cancelled=False):
    """One of the signing states, from the facts."""
    if cancelled:
        return "cancelled"
    if set(declined) & set(signers):
        return "declined"
    done = [s for s in signers if s in signed]
    if len(done) == len(signers):
        return "completed"
    if expired:
        return "expired"
    return "partly_signed" if done else "sent"


def share_open(link, now, password=None):
    """(True, None) when a share link may open now, else (False, reason). link: {"until", "password_set", "stopped"}; times are
    whole seconds; the password check itself is done by the caller (password is True, False or None for none given)."""
    if link.get("stopped"):
        return False, "stopped"
    if now >= link["until"]:
        return False, "expired"
    if link.get("password_set") and password is not True:
        return False, "password"
    return True, None


def share_days_ok(days):
    return isinstance(days, int) and not isinstance(days, bool) and 1 <= days <= FILES["sharing"]["max_days"]


def format_code(n):
    """A verification code from a whole number: groups of the Lynk Alphabet joined by dashes (XXXX-XXXX-XXXX)."""
    g, length = FILES["signing"]["code_groups"], FILES["signing"]["code_group_length"]
    chars = []
    for _ in range(g * length):
        n, r = divmod(n, len(ALPHABET))
        chars.append(ALPHABET[r])
    s = "".join(reversed(chars))
    return "-".join(s[i:i + length] for i in range(0, len(s), length))


def code_ok(code):
    g, length = FILES["signing"]["code_groups"], FILES["signing"]["code_group_length"]
    if not isinstance(code, str):
        return False
    parts = code.upper().split("-")
    return len(parts) == g and all(len(p) == length and all(ch in ALPHABET for ch in p) for p in parts)


def fits(used_bytes, add_bytes, storage_gb, extra_100_gb=0):
    """Whether a new file fits the plan's storage (and any extra blocks of 100 GB bought). None storage means no limit."""
    if storage_gb is None:
        return True
    return used_bytes + add_bytes <= (storage_gb + 100 * extra_100_gb) * GB


def level_partner(level):
    """The partner part a signing level needs, or None for a simple signature."""
    if level not in FILES["signing"]["levels"]:
        raise ValueError("unknown signing level")
    return FILES["signing"]["levels"][level]["partner"]
