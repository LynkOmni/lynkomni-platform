import json, os, shutil, tempfile, unittest
import visuals
from visuals import check, generate, kit
from services import billing
from finance import revenue_model
import brand


def doc():
    with open(generate.NEEDS, encoding="utf-8") as f:
        return json.load(f)


class Gate(unittest.TestCase):
    def test_repository_passes_the_gate(self):
        self.assertEqual(check.problems(), [])

    def test_every_product_family_has_art_and_new_families_need_it(self):
        have = set(visuals.ids())
        for fam in billing.FAMILIES:
            self.assertIn("product-" + fam[len("lynk"):], have, f"{fam} has no product illustration")

    def test_every_status_state_screen_and_onboarding_step_exists(self):
        have = set(visuals.ids())
        for need in ("state-offline", "state-error", "state-success", "state-sync-pending", "state-permission", "state-unavailable-region",
                     "onboarding-offline", "onboarding-chain", "onboarding-provider", "onboarding-growth", "diagram-sync-states"):
            self.assertIn(need, have)

    def test_planned_brand_files_now_exist(self):
        files = {f["file"] for v in visuals.index()["needs"].values() for f in v["files"]}
        with open(os.path.join(brand.ROOT, "brand", "surfaces.v1.json"), encoding="utf-8") as fh:
            surfaces = json.load(fh)["surfaces"]
        for s in surfaces:
            for rel in s.get("files", []):
                if rel.startswith("web/"):
                    self.assertIn(rel, files, f"surface {s['id']} lists {rel} but no visual makes it")

    def test_palette_contrast_holds_in_every_theme_and_accent(self):
        self.assertEqual(check.palette_checks(), [])

    def test_svg_output_is_deterministic(self):
        a = generate.build(png=False)[1]
        b = generate.build(png=False)[1]
        self.assertEqual(a, b)

    def test_chart_numbers_come_from_the_code(self):
        svg = visuals.svg_text("chart-pricing-ladder")
        for k, v in billing.FAMILIES.items():
            if k in ("lynkdev", "lynksuite"):
                continue
            self.assertIn(" · ".join(f"${v[3][t]:g}" for t in (1, 2, 3)), svg)
        rev = visuals.svg_text("chart-revenue-path")
        for stage in revenue_model.path().values():
            self.assertIn(f"${stage['end']:,}", rev)
        self.assertIn("not a forecast", rev)

    def test_diagram_uses_the_five_states_and_their_wording(self):
        svg = visuals.svg_text("diagram-sync-states")
        for label in ("Queued", "Sent", "Accepted", "Confirmed", "Failed"):
            self.assertIn(label, svg)

    def test_illustrations_have_no_words(self):
        for nid in visuals.ids():
            if visuals.index()["needs"][nid]["kind"] == "illustration":
                self.assertNotIn("<text", visuals.svg_text(nid, "dark"))

    def test_every_picture_has_a_text_alternative(self):
        for nid, need in visuals.index()["needs"].items():
            self.assertGreater(len(need["alt"]), 19)
            for f in need["files"]:
                if f["file"].endswith(".svg"):
                    with open(os.path.join(visuals.GENERATED, f["file"]), encoding="utf-8") as fh:
                        self.assertIn('<title id="t-', fh.read())


class GateCatchesProblems(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.gen = os.path.join(self.tmp, "generated")
        shutil.copytree(generate.OUT, self.gen)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def edit(self, rel, fn):
        p = os.path.join(self.gen, rel)
        with open(p, encoding="utf-8") as f:
            t = f.read()
        with open(p, "w", encoding="utf-8") as f:
            f.write(fn(t))

    def test_missing_file_is_reported(self):
        os.remove(os.path.join(self.gen, "illustrations", "product-pos.dark.svg"))
        self.assertTrue(any("product-pos.dark.svg" in p and "missing" in p for p in check.file_checks(doc(), self.gen)))

    def test_orphan_file_is_reported(self):
        with open(os.path.join(self.gen, "illustrations", "stray.svg"), "w") as f:
            f.write("<svg/>")
        self.assertTrue(any("orphan" in p for p in check.file_checks(doc(), self.gen)))

    def test_tampered_file_is_reported(self):
        self.edit("illustrations/product-pos.light.svg", lambda t: t.replace("<title", " <title", 1))
        self.assertTrue(any("does not match index.json" in p for p in check.file_checks(doc(), self.gen)))

    def test_off_token_colour_text_script_and_web_image_are_reported(self):
        bad = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10" role="img"><title id="t">x</title><path fill="#123456"/><text>hi</text>'
               '<script>1</script><image href="https://example.com/a.png"/></svg>')
        out = check.svg_problems("x.svg", bad, "illustration", "light", 12)
        joined = " ".join(out)
        for word in ("not a light design token", "contain no words", "has a script", "embeds a raster image", "link or external"):
            self.assertIn(word, joined)

    def test_dark_colour_is_not_allowed_in_light_picture(self):
        from design import generate as d
        light_vals = {v.upper() for v in d.resolved("light").values()}
        dark_only = next(v for v in d.resolved("dark").values() if v.startswith("#") and v.upper() not in light_vals)
        svg = f'<svg viewBox="0 0 1 1" role="img"><title id="t">a long enough title</title><rect fill="{dark_only}"/></svg>'
        self.assertTrue(any("not a light design token" in p for p in check.svg_problems("x.svg", svg, "illustration", "light", 12)))

    def test_png_size_budget_and_dimensions(self):
        p = os.path.join(self.gen, "web", "pwa-192.png")
        with open(p, "wb") as f:
            f.write(b"\x89PNG\r\n\x1a\n" + b"\x00" * 8 + b"\x00\x00\x00\x10\x00\x00\x00\x10" + b"\x00" * 10)
        self.assertTrue(any("pwa-192.png" in x for x in check.file_checks(doc(), self.gen)))

    def test_scan_flags_placeholders_and_unknown_visual_ids(self):
        root = os.path.join(self.tmp, "repo")
        os.makedirs(os.path.join(root, "app"))
        with open(os.path.join(root, "app", "a.py"), "w") as f:
            f.write('x = "placeholder.png"\n# TODO image for the empty state\nvisuals.get("product-nothing")\nvisuals.get("product-pos")\n')
        with open(os.path.join(root, "app", "b.html"), "w") as f:
            f.write('<img src="https://images.unsplash.com/x.jpg">\n')
        out = " ".join(check.scan_code(root, {"product-pos"}))
        for word in ("placeholder image file", "TODO image", "stock or placeholder", "product-nothing"):
            self.assertIn(word, out)
        self.assertNotIn("product-pos", out)

    def test_needs_rules(self):
        d = doc()
        d["needs"][0]["alt"] = "placeholder"
        d["needs"][1]["id"] = "Bad_ID"
        d["needs"].append(dict(d["needs"][2]))
        out = " ".join(check.need_checks(d))
        for word in ("real text alternative", "lowercase words", "duplicate id"):
            self.assertIn(word, out)


class Api(unittest.TestCase):
    def test_get_and_alt(self):
        v = visuals.get("product-pos", "dark")
        self.assertEqual((v.theme, v.kind, v.decorative), ("dark", "illustration", True))
        self.assertTrue(os.path.isfile(v.path))
        self.assertEqual(visuals.alt("product-pos"), v.alt)

    def test_unknown_id_says_how_to_add_it(self):
        with self.assertRaises(KeyError) as c:
            visuals.get("product-unknown")
        self.assertIn("needs.v1.json", str(c.exception))

    def test_lite_mode_hides_decorative_images_but_keeps_figures(self):
        self.assertIsNone(visuals.decorative("state-offline", "light", mode="lite"))
        self.assertIsNotNone(visuals.decorative("diagram-sync-states", "light", mode="lite"))
        self.assertIsNotNone(visuals.decorative("state-offline", "light"))

    def test_sunlight_mode_uses_the_contrast_set(self):
        self.assertEqual(visuals.get("product-pos", "light", mode="sunlight").theme, "contrast-light")
        self.assertEqual(visuals.get("product-pos", "dark", mode="sunlight").theme, "contrast-dark")

    def test_fixed_appearance_images_fall_back_to_light(self):
        self.assertEqual(visuals.get("share-card", "dark").theme, "light")
        with self.assertRaises(KeyError):
            visuals.get("product-pos", "sepia")

    def test_png_and_data_uri(self):
        self.assertTrue(visuals.get("app-icon", "dark", file_ext="png").file.endswith("app-icon-1024-dark.png"))
        self.assertTrue(visuals.data_uri("product-pos", "light").startswith("data:image/svg+xml;base64,"))
        self.assertTrue(visuals.data_uri("share-card", "light", file_ext="png").startswith("data:image/png;base64,"))

    def test_tampering_is_detected(self):
        tmp = tempfile.mkdtemp()
        old_gen, old_cache = visuals.GENERATED, dict(visuals._CACHE)
        try:
            shutil.copytree(generate.OUT, os.path.join(tmp, "g"))
            visuals.GENERATED = os.path.join(tmp, "g")
            visuals._CACHE.clear()
            p = os.path.join(tmp, "g", "illustrations", "product-pos.light.svg")
            with open(p, "a") as f:
                f.write(" ")
            with self.assertRaises(visuals.VisualsTampered):
                visuals.get("product-pos", "light")
        finally:
            visuals.GENERATED = old_gen
            visuals._CACHE.clear(); visuals._CACHE.update(old_cache)
            shutil.rmtree(tmp, ignore_errors=True)


class Style(unittest.TestCase):
    def test_product_accents_follow_the_design_system(self):
        self.assertEqual(kit.Palette("light", "booking").accent, "#0EA5E9")
        self.assertNotEqual(kit.Palette("light", "essential").accent, kit.Palette("light").accent)

    def test_icons_still_come_from_the_icon_package(self):
        # the diagram draws state icons from brand.status_icon sources, never its own copies
        svg = visuals.svg_text("diagram-sync-states")
        for state in ("queued", "sent", "accepted", "confirmed", "failed"):
            inner = brand.icon_svg(f"status-{state}").split(">", 1)[1].rsplit("</svg>", 1)[0]
            self.assertIn(inner, svg)


if __name__ == "__main__":
    unittest.main()
