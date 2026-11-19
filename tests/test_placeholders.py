"""PLACEHOLDER UPDATE (owner 2026-11-19, master blueprint section 83; catalog/placeholders.v1.json). Every typing field has a hint
(an example, never the instruction) or is a sensitive field that must have none; every hinted field keeps a visible label; no
screen carries filler text; the skeleton timing in the code matches the register. Fields still due when the rule was agreed are
listed with their build section: the list may only shrink, a new field without a hint fails here at once, and the section
cannot lock while anything is due."""
import glob, json, os, re, unittest
from core import build_sections as b

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R = json.load(open(os.path.join(ROOT, "catalog", "placeholders.v1.json"), encoding="utf-8"))
SKIP_TYPES = ('type="hidden"', 'type="checkbox"', 'type="radio"', 'type="range"', 'type="file"')


def fields():
    """Every typing field in the screen code: (file, key, attributes)."""
    out = []
    for f in sorted(glob.glob(os.path.join(ROOT, "ts", "src", "*.ts")) + glob.glob(os.path.join(ROOT, "web", "emulators", "*", "app.ts"))):
        rel = os.path.relpath(f, ROOT); s = open(f, encoding="utf-8").read()
        for m in re.finditer(r"<(input|textarea)\b([^>]*)>", s):
            a = m.group(2)
            if any(x in a for x in SKIP_TYPES):
                continue
            k = re.search(r'\bid="([^"$]+)"', a) or re.search(r'data-in="([^"]+)"', a) or re.search(r'data-field="([^"]+)"', a) \
                or re.search(r'class="([^"]+)"', a) or re.search(r'type="([^"]+)"', a)
            out.append((rel, k.group(1) if k else a[:30], a, s))
    return out


class Placeholders(unittest.TestCase):
    def test_every_field_has_a_hint_or_is_sensitive_or_is_due(self):
        due, sens = R["due"]["hints"], R["sensitive"]
        for f, k, a, _ in fields():
            hinted = "placeholder=" in a
            if k in sens.get(f, []) or any(m in a for m in R["sensitive_markers"]):
                self.assertFalse(hinted and ('type="password"' in a or "one-time-code" in a), f"{f} {k}: a sensitive field never shows an example value")
                continue
            if not hinted:
                self.assertIn(k, due.get(f, []), f"{f}: the field {k} needs a hint (an example of what to type) in every language")

    def test_the_due_list_only_shrinks(self):
        now = {(f, k) for f, k, a, _ in fields() if "placeholder=" not in a}
        for f, keys in R["due"]["hints"].items():
            for k in keys:
                self.assertIn((f, k), now, f"{f} {k} has its hint now: take it off the due list")

    def test_a_hint_never_replaces_the_label(self):
        due = R["due"]["labels"]
        for f, k, a, s in fields():
            if "placeholder=" not in a:
                continue
            labelled = "aria-label" in a or "aria-labelledby" in a
            m = re.search(r'\bid="([^"]+)"', a)
            labelled = labelled or bool(m and f'for="{m.group(1)}"' in s)
            if not labelled:
                self.assertIn(k, due.get(f, []), f"{f} {k}: a hinted field keeps a visible label or an accessible name")

    def test_due_items_wait_in_a_section_still_to_lock(self):
        s = R["due"]["section"]
        self.assertIn(s, [str(n) for n in b.ORDER])
        if any(R["due"]["hints"].values()) or any(R["due"]["labels"].values()):
            self.assertNotEqual(b.status(s), "locked", f"section {s} cannot lock while fields still need hints or labels")

    def test_no_filler_text_on_any_screen(self):
        pats = [re.compile(p) if re.search(r"[A-Z]", p) else re.compile(p, re.I) for p in R["banned_text"]]
        for f in glob.glob(os.path.join(ROOT, "web", "**", "strings.en.json"), recursive=True):
            for k, v in json.load(open(f, encoding="utf-8")).items():
                for p in pats:
                    self.assertIsNone(p.search(str(v)), f"{f} {k}: filler text on a screen")

    def test_the_83_7_additions_are_recorded(self):
        self.assertGreaterEqual(len(R["more"]["rules"]), 13)
        self.assertIn("Intl.NumberFormat", open(os.path.join(ROOT, "ts", "src", "placeholder.ts"), encoding="utf-8").read())

    def test_the_code_follows_the_register(self):
        src = open(os.path.join(ROOT, "ts", "src", "placeholder.ts"), encoding="utf-8").read()
        t = R["timing_ms"]
        self.assertIn(f"SHOW_AFTER: {t['show_after']}, MIN_SHOW: {t['min_show']}, SLOW_AFTER: {t['slow_after']}", src)
        for shape in R["shapes"]:
            self.assertIn(f'"{shape}"', src)
        css = open(os.path.join(ROOT, "web", "shell", "placeholder.css"), encoding="utf-8").read()
        self.assertIn("prefers-reduced-motion", css)
        self.assertIn("data-lite", css)
        self.assertNotRegex(css, r"#[0-9a-fA-F]{3,8}\b", "tokens only")


if __name__ == "__main__":
    unittest.main()
