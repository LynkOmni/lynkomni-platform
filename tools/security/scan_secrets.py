#!/usr/bin/env python3
"""Secrets scan (MASTER UPDATE, security register control "secrets-scan"): fails when a private key, a cloud key or a
live-looking token is committed to the code. Runs in CI on every push and pull request.

    python3 tools/security/scan_secrets.py            -> exit 0 when clean, 1 with the findings listed

Only text files are read. Test fixtures may hold a planted secret only on a line marked "scan: planted-test-secret"."""
import os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SKIP_DIRS = {".git", "node_modules", "dist", "__pycache__", "target", ".gradle", "build", ".build", "vendor", "i18n", "generated"}
SKIP_EXT = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".woff2", ".woff", ".ttf", ".otf", ".ico", ".pdf", ".zip", ".gz", ".lock", ".svg"}
ALLOW_MARK = "scan: planted-test-secret"

PATTERNS = [
    ("private key", re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP |ENCRYPTED )?PRIVATE KEY-----")),
    ("cloud access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("Google API key", re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b")),
    ("GitHub token", re.compile(r"\bgh[pousr]_[0-9A-Za-z]{36,}\b")),
    ("Slack token", re.compile(r"\bxox[abprs]-[0-9A-Za-z\-]{10,}\b")),
    ("live payment key", re.compile(r"\b(?:sk|rk)_live_[0-9A-Za-z]{16,}\b")),
    ("JSON web token", re.compile(r"\beyJ[0-9A-Za-z_\-]{10,}\.eyJ[0-9A-Za-z_\-]{10,}\.[0-9A-Za-z_\-]{10,}\b")),
]


def scan_text(text, name="text"):
    found = []
    for n, line in enumerate(text.splitlines(), 1):
        if ALLOW_MARK in line:
            continue
        for kind, rx in PATTERNS:
            if rx.search(line):
                found.append({"file": name, "line": n, "kind": kind})
    return found


def scan(root=ROOT):
    found = []
    for d, dirs, files in os.walk(root):
        dirs[:] = [x for x in dirs if x not in SKIP_DIRS]
        for f in files:
            if os.path.splitext(f)[1].lower() in SKIP_EXT:
                continue
            p = os.path.join(d, f)
            try:
                if os.path.getsize(p) > 2_000_000:
                    continue
                with open(p, encoding="utf-8") as h:
                    text = h.read()
            except (UnicodeDecodeError, OSError):
                continue
            found += scan_text(text, os.path.relpath(p, root))
    return found


if __name__ == "__main__":
    hits = scan()
    for h in hits:
        print(f"{h['file']}:{h['line']}: {h['kind']}")
    print("secrets scan:", "clean" if not hits else f"{len(hits)} finding(s)")
    sys.exit(1 if hits else 0)
