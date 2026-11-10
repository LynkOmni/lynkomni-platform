"""The twelve sample cards in the fixed layout (MASTER UPDATE, master blueprint section 61; build section 1)."""
import re, unittest
import visuals
from design import generate as design
from services import card_groups as cg
from visuals import cards, kit

FACES = [(t, g) for t in cards.TIERS for g in cards.GROUPS]


def texts(svg):
    """(words, x, y, size, anchor) for every <text> in a picture."""
    out = []
    for attrs, words in re.findall(r"<text([^>]*)>(.*?)</text>", svg, re.S):
        a = dict(re.findall(r'([a-z-]+)="([^"]*)"', attrs))
        out.append((words, float(a["x"]), float(a["y"]), float(a["font-size"]), a.get("text-anchor", "start")))
    return out


def box(words, x, y, size, anchor):
    w = len(words) * size * 0.72                                 # generous: wider than any of the card fonts
    x0 = x if anchor == "start" else x - w if anchor == "end" else x - w / 2
    return (x0, y - size, x0 + w, y + size * 0.25)


def overlaps(a, z):
    zx, zy, zw, zh = z
    return a[0] < zx + zw and a[2] > zx and a[1] < zy + zh and a[3] > zy


class TestSampleCards(unittest.TestCase):
    def test_twelve_fronts_and_twelve_backs_exist(self):
        ids = set(visuals.ids())
        for t, g in FACES:
            self.assertIn(f"vcard-{t}-{g}", ids); self.assertIn(f"vcard-{t}-{g}-back", ids)

    def test_each_front_carries_exactly_the_fixed_layout_words(self):
        for t, g in FACES:
            words = sorted(w for w, *_ in texts(visuals.svg_text(f"vcard-{t}-{g}")))
            want = sorted([cards.SAMPLE_TEXT[k] for k in ("sample", "number", "valid", "expiry", "holder")] + [cards.TIER_TEXT[t], cg.CARD_WORD[g]])
            self.assertEqual(words, want, (t, g))
            back = sorted(w for w, *_ in texts(visuals.svg_text(f"vcard-{t}-{g}-back")))
            self.assertEqual(back, sorted([cg.SAMPLE["code"], cg.SAMPLE["sample_word"], cards.BACK_TEXT[t]]), (t, g))

    def test_the_issuers_spaces_stay_empty_and_the_network_space_is_an_empty_outline(self):
        nx, ny, nw, nh = cards.ZONES["network"]
        for t, g in FACES:
            svg = visuals.svg_text(f"vcard-{t}-{g}")
            for item in texts(svg):
                for name, zone in cards.ZONES.items():
                    self.assertFalse(overlaps(box(*item), zone), f"{t}-{g}: {item[0]!r} is inside the {name} space")
            self.assertIn(f'x="{nx}" y="{ny}" width="{nw}" height="{nh}"', svg)
            self.assertIn("stroke-dasharray", svg)
            for banned in ("visa", "mastercard", "amex", "bank", "contactless"):
                self.assertNotIn(banned, re.sub(r"<title[^>]*>.*?</title>", "", svg.lower()), (t, g, banned))
            group_word = next(i for i in texts(svg) if i[0] == cg.CARD_WORD[g])
            self.assertLess(group_word[2], ny, "the group word sits just above the network space")

    def test_the_logo_is_top_left_and_the_number_in_the_middle(self):
        for t, g in FACES:
            svg = visuals.svg_text(f"vcard-{t}-{g}")
            self.assertIn('data-brand="logo"', svg)
            num = next(i for i in texts(svg) if i[0] == cg.SAMPLE["number"])
            self.assertTrue(cards.H * .45 < num[2] < cards.H * .65, "the number sits across the middle")

    def test_the_sample_number_can_never_work_and_only_it_has_digits(self):
        self.assertFalse(cg.luhn_ok(cards.SAMPLE_TEXT["number"]))
        for t, g in FACES:
            body = re.sub(r"<title[^>]*>.*?</title>|<desc[^>]*>.*?</desc>", "", visuals.svg_text(f"vcard-{t}-{g}"), flags=re.S)
            words = re.sub(r"<[^>]+>", " ", body).replace(cg.SAMPLE["number"], "")
            self.assertIsNone(re.search(r"\d{4}", words), (t, g))

    def test_every_word_has_enough_contrast(self):
        tok = design.resolved("dark")
        for t in cards.TIERS:
            self.assertGreaterEqual(kit.contrast(tok[f"on-vcard-{t}"], tok[f"vcard-{t}-bg"]), 4.5, t)
        self.assertGreaterEqual(kit.contrast(tok["vcard-stripe"], tok["vcard-panel"]), 4.5, "the code on the issuer's panel")

    def test_every_sample_says_so_in_its_text_alternative(self):
        for t, g in FACES:
            for vid in (f"vcard-{t}-{g}", f"vcard-{t}-{g}-back"):
                self.assertIn("Not a real card", visuals.alt(vid) if hasattr(visuals, "alt") else visuals.svg_text(vid))


if __name__ == "__main__":
    unittest.main()
