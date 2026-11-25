"""No WhatsApp anywhere (owner, 2026-11-19 and 2026-11-25, section 4C point 2): WhatsApp is not a channel, a partner, a link or a
logo anywhere in LynkOmni, the footer included. The only places the word may stay are the published contract versions (they are
never edited), the history (decisions and change log), the rules that forbid it, the refusals that keep it out, and the tests."""
import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIP_DIRS = {".git", "node_modules", "dist", "__pycache__", ".venv", "vendor", "generated"}
TEXT = (".py", ".ts", ".mjs", ".js", ".json", ".css", ".html", ".md", ".svg", ".yml", ".yaml", ".kt", ".swift", ".rs", ".sql", ".txt")
# Where the word may stay, and why.
ALLOWED = {
    "CLAUDE.md": "the rule that forbids it",
    "docs/lynkomni-decisions.md": "history: owner decisions are never deleted",
    "docs/lynkomni-changelog.md": "history: what changed in each version",
    "services/services_partners.py": "the messaging sandbox refuses WhatsApp (NEVER)",
    "web/emulators/build_data.py": "a comment about the raw word name bug of 2026-11-19",
    "contract/upcast.py": "the upcaster from 7 to 8 that took WhatsApp out of old events",
    "contract/upcasters.v1.json": "the note of the upcaster from 7 to 8",
    "contract/tools/build_v8.py": "frozen builder of contract version 8, the version that removed WhatsApp",
    "contract/tools/validate_contract.py": "the check that no newer version brings WhatsApp back",
}
FROZEN = re.compile(r"^contract/(event-payloads|command-policy-register)\.v[1-8]\.json$|^contract/tools/build_v[1-7]\.py$")
# A line in a register may name WhatsApp only to say it is never used.
NEVER = re.compile(r"whatsapp is never|never whatsapp|no whatsapp|whatsapp business account stays outside|errors and whatsapp|whatsapp removed", re.I)


def files():
    for d, dirs, names in os.walk(ROOT):
        dirs[:] = [x for x in dirs if x not in SKIP_DIRS and not (x == "i18n" and False)]
        for n in names:
            if n.endswith(TEXT):
                yield os.path.relpath(os.path.join(d, n), ROOT).replace(os.sep, "/")


class NoWhatsApp(unittest.TestCase):
    def test_whatsapp_appears_nowhere_outside_the_history_and_the_rules(self):
        bad = []
        for rel in files():
            if rel.startswith("tests/") or rel.startswith("ts/test/") or rel in ALLOWED or FROZEN.match(rel):
                continue
            with open(os.path.join(ROOT, rel), encoding="utf-8", errors="ignore") as f:
                for i, line in enumerate(f, 1):
                    if re.search(r"whats\s?app|wa\.me/", line, re.I) and not NEVER.search(line):
                        bad.append(f"{rel}:{i}: {line.strip()[:120]}")
        self.assertEqual(bad, [], "WhatsApp must not appear (section 4C point 2):\n" + "\n".join(bad))

    def test_the_footer_has_no_whatsapp_link(self):
        with open(os.path.join(ROOT, "ts", "src", "footer.ts"), encoding="utf-8") as f:
            src = f.read()
        self.assertNotIn("wa.me", src)
        self.assertNotRegex(src, r'SOCIAL = \[[^\]]*whatsapp')

    def test_no_built_page_carries_a_whatsapp_link_or_logo(self):
        dist = os.path.join(ROOT, "web", "emulators", "dist")
        for n in sorted(os.listdir(dist)) if os.path.isdir(dist) else []:
            if n.endswith(".html"):
                with open(os.path.join(dist, n), encoding="utf-8", errors="ignore") as f:
                    src = f.read()
                self.assertNotIn("wa.me/", src, n)
                self.assertNotRegex(src, r'https?://[^"\s]*whatsapp', n)

    def test_the_allowed_list_is_still_needed(self):
        for rel in ALLOWED:
            p = os.path.join(ROOT, rel)
            self.assertTrue(os.path.isfile(p), rel)
            with open(p, encoding="utf-8", errors="ignore") as f:
                self.assertRegex(f.read(), re.compile(r"whatsapp", re.I), f"{rel} no longer names WhatsApp: take it off the list")


if __name__ == "__main__":
    unittest.main()
