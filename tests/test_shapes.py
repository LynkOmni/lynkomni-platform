"""One rounding for every part (owner, 2026-11-26): fields, choosers, buttons and notes take --radius-control, panels and pop-ups
--radius-card, rows inside lists --radius-small and round-ended bars and chips --radius-pill, all from design/tokens.v1.json
"shape". Only hardware details (key edges, speaker slots, device bodies and glass) keep their own shapes. A hand-typed rounding
in the ranges the tokens cover fails here."""
import glob
import json
import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TYPED = re.compile(r"border-radius:[^;}]*\b(?:[89]|1[0-9]|2[2-6]|999)px")


class Shapes(unittest.TestCase):
    def test_the_tokens_hold_the_roundings(self):
        with open(os.path.join(ROOT, "design", "tokens.v1.json"), encoding="utf-8") as f:
            shape = json.load(f)["shape"]
        self.assertEqual((shape["radius_small_px"], shape["radius_control_px"], shape["radius_card_px"]), (8, 12, 16))
        with open(os.path.join(ROOT, "design", "generated", "tokens.css"), encoding="utf-8") as f:
            css = f.read()
        for name in ("small", "control", "card", "pill"):
            self.assertIn(f"--radius-{name}:", css)
        self.assertIn('select, textarea { border-radius: var(--radius-control); }', css)

    def test_no_page_types_its_own_rounding(self):
        bad = []
        files = glob.glob(os.path.join(ROOT, "web", "**", "*.css"), recursive=True)
        for p in files:
            rel = os.path.relpath(p, ROOT).replace(os.sep, "/")
            if "/dist/" in rel:
                continue
            with open(p, encoding="utf-8") as f:
                for i, line in enumerate(f, 1):
                    if TYPED.search(line) and "/* hardware shape */" not in line:   # device bodies keep their own shape
                        bad.append(f"{rel}:{i}")
        self.assertEqual(bad, [], "use var(--radius-small|control|card|pill): " + ", ".join(bad))

    def test_the_shared_fields_look_the_same(self):
        with open(os.path.join(ROOT, "web", "shell", "fields.css"), encoding="utf-8") as f:
            css = f.read()
        self.assertRegex(css, r"\.lf-in, \.lf-ccfind \{[^}]*min-block-size: 48px;[^}]*border-radius: var\(--radius-control\)")
        self.assertRegex(css, r"\.lf-cc \{[^}]*min-block-size: 48px;[^}]*border-radius: var\(--radius-control\)")

    def test_one_kind_one_shape(self):
        """The same kind of thing has the same corners on every page (owner 2026-11-26)."""
        kinds = {
            "button": (r"\.(primary|ghost|secondary)\b", "var(--radius-control)"),
            "toast": (r"\.toast\b", "var(--radius-card)"),
            "notice": (r"\.(notice|why|qs-soon)\b", "var(--radius-card)"),
            "typing box": (r"(input(\.text)?|\.dsh-field|\.lf-in)\b", "var(--radius-control)"),
        }
        bad = []
        for p in glob.glob(os.path.join(ROOT, "web", "**", "*.css"), recursive=True):
            rel = os.path.relpath(p, ROOT).replace(os.sep, "/")
            if "/dist/" in rel:
                continue
            with open(p, encoding="utf-8") as f:
                css = f.read()
            for m in re.finditer(r"([^{}]+)\{([^}]*)\}", css):
                sel = m.group(1).strip().split("\n")[-1].split("*/")[-1]
                r = re.search(r"border-radius:\s*([^;]+)", m.group(2))
                if not r or re.search(r"::|:hover|:focus|checkbox|radio|range", sel) or "/* hardware shape */" in m.group(2):
                    continue
                for kind, (rx, want) in kinds.items():
                    if re.search(rx, sel) and r.group(1).strip() != want and "a" != sel.strip()[-1:]:
                        bad.append(f"{rel}: {sel.strip()[:60]} ({kind}) has {r.group(1).strip()}")
        self.assertEqual(bad, [], "; ".join(bad))


if __name__ == "__main__":
    unittest.main()
