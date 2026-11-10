import json, os, re, unittest
import pathlib
from design import generate
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = generate.SRC

def lum(h):
    c = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]; f = lambda x: x / 12.92 if x <= .03928 else ((x + .055) / 1.055) ** 2.4
    r, g, b = map(f, c); return .2126 * r + .7152 * g + .0722 * b
def ratio(a, b):
    la, lb = sorted((lum(a), lum(b)), reverse=True); return (la + .05) / (lb + .05)

# Values from the supplied specification. They must never change; additions are allowed, edits are not.
SPEC = {"light": {"bg-base": "#FAFAFA", "bg-surface": "#FFFFFF", "bg-subtle": "#F4F4F5", "border-subtle": "#E4E4E7", "border-strong": "#A1A1AA", "text-primary": "#18181B",
        "text-secondary": "#71717A", "text-muted": "#A1A1AA", "brand-primary": "#7C4DFF", "brand-hover": "#651FFF", "brand-subtle": "#F3E8FF", "accent-vcard": "#9E75FF",
        "accent-booking": "#0EA5E9", "accent-essential": "#10B981", "accent-exchange": "#F59E0B", "accent-hub": "#18181B", "vcard-edge-bg": "#0A4E54", "vcard-hub-bg": "#0C2470",
        "vcard-core-bg": "#320B73", "vcard-omni-bg": "#0B0906", "status-success-text": "#047857", "status-danger-bg": "#FEF2F2", "status-info-text": "#6B21A8"},
        "dark": {"bg-base": "#09090B", "bg-surface": "#18181B", "bg-subtle": "#27272A", "border-subtle": "#3F3F46", "border-strong": "#52525B", "text-primary": "#FAFAFA",
        "text-secondary": "#A1A1AA", "text-muted": "#71717A", "brand-primary": "#7C4DFF", "brand-hover": "#9E75FF", "brand-subtle": "#1F1047", "accent-vcard": "#B388FF",
        "accent-booking": "#38BDF8", "accent-essential": "#34D399", "accent-exchange": "#FBBF24", "accent-hub": "#FAFAFA", "status-success-text": "#34D399", "status-danger-bg": "#450A0A", "status-info-text": "#D8B4FE"}}

class TestDesignSystem(unittest.TestCase):
    def test_spec_values_unchanged(self):
        for theme, vals in SPEC.items():
            m = generate.resolved(theme)
            for k, v in vals.items(): self.assertEqual(m[k], v, f"{theme}:{k}")
    def test_every_spec_token_is_tagged_and_additions_are_tagged(self):
        for t, toks in SRC["themes"].items():
            for k, (v, origin) in toks.items(): self.assertIn(origin, ("spec", "added"), k)
        self.assertTrue(all(o == "added" for t in ("contrast-light", "contrast-dark") for _, o in SRC["themes"][t].values()))
    def test_contrast_pairs_meet_their_minimum(self):
        for p in SRC["pairs"]:
            for theme in p["themes"]:
                m = generate.resolved(theme)
                for bg in p["bg"]: self.assertGreaterEqual(ratio(m[p["fg"]], m[bg]), p["min"], f"{theme}: {p['fg']} on {bg}")
    def test_known_limits_are_real_so_the_docs_stay_honest(self):
        L = generate.resolved("light"); D = generate.resolved("dark")
        self.assertLess(ratio(L["text-muted"], L["bg-base"]), 4.5); self.assertLess(ratio(D["text-muted"], D["bg-surface"]), 4.5)
        self.assertLess(ratio("#FFFFFF", L["accent-booking"]), 4.5)                      # why booking buttons use dark text
        self.assertLess(ratio(D["brand-primary"], D["bg-surface"]), 4.5)                  # why violet text uses brand-ink in dark mode
        self.assertLess(ratio(L["text-secondary"], L["bg-base"]), 7)                      # so we never claim AAA for secondary text
    def test_fonts_are_the_two_brand_fonts_and_self_hosted(self):
        F = SRC["fonts"]; self.assertTrue(F["heading"].startswith("'Montserrat'")); self.assertTrue(F["body"].startswith("'Inter'"))
        self.assertIn("tnum", F["feature_tabular"])
        for rel in ("design/fonts.css", "design/generated/tokens.css", "design/generated/tailwind.preset.cjs"):
            text = pathlib.Path(os.path.join(ROOT, rel)).read_text(); self.assertNotIn("googleapis", text); self.assertNotIn("gstatic", text); self.assertNotIn("@import", text)
        css = pathlib.Path(os.path.join(ROOT, "design/fonts.css")).read_text(); self.assertEqual(css.count("font-display: swap"), css.count("@font-face"))
    def test_generated_files_are_up_to_date(self):
        for rel, text in generate.build().items(): self.assertEqual(pathlib.Path(os.path.join(ROOT, rel)).read_text(), text, f"{rel} is stale: run python3 design/generate.py")
    def test_no_third_party_font_links_anywhere_in_the_repo(self):
        bad = []
        for d, _, files in os.walk(ROOT):
            if any(x in d for x in ("node_modules", "/dist", "__pycache__", "/tests")): continue
            for f in files:
                if f.endswith((".css", ".ts", ".mjs", ".html", ".js", ".cjs")) and "googleapis.com/css" in pathlib.Path(os.path.join(d, f)).read_text(errors="ignore"): bad.append(os.path.join(d, f))
        self.assertEqual(bad, [])
    def test_high_contrast_themes_inherit_and_improve(self):
        for base, hc in (("light", "contrast-light"), ("dark", "contrast-dark")):
            b, h = generate.resolved(base), generate.resolved(hc)
            self.assertGreater(ratio(h["text-primary"], h["bg-base"]), 20); self.assertGreater(ratio(h["text-secondary"], h["bg-base"]), 7)
            self.assertEqual(h["status-success-text"], b["status-success-text"])


class TestModesAndStates(unittest.TestCase):
    def test_accessibility_gate_passes(self):
        from design import check_a11y
        self.assertEqual(check_a11y.problems(), [])
    def test_state_tones_are_readable_and_never_colour_alone(self):
        for theme in ("light", "dark", "contrast-light", "contrast-dark"):
            m = generate.resolved(theme)
            for k, v in SRC["states"].items():
                self.assertGreaterEqual(ratio(m[f"status-{v['tone']}-text"], m[f"status-{v['tone']}-bg"]), 4.5, f"{theme}:{k}")
        self.assertEqual(len({(v["icon"], v["label"]) for v in SRC["states"].values()}), 5)
    def test_sunlight_mode_uses_the_high_contrast_values(self):
        css = pathlib.Path(os.path.join(ROOT, "design/generated/tokens.css")).read_text()
        self.assertIn('[data-mode="sunlight"]', css); self.assertIn("--text-secondary: #3F3F46", css)

if __name__ == "__main__": unittest.main()
