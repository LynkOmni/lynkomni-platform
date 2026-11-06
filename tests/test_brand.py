import json, os, shutil, tempfile, unittest
import brand
from brand import sync, check
from design import generate

SVG = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="-8 -8 10 10" role="img" aria-label="LynkOmni"><path fill="#18181B" d="M0 0L1 1Z"/></svg>\n'


def make_package(root, version="1.2.3", themes_override=None, drop_dir=None, corrupt=None):
    dist = os.path.join(root, "dist")
    files, rasters = {}, {}
    def put(rel, data, into):
        p = os.path.join(dist, *rel.split("/")); os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "wb") as f: f.write(data)
        into[rel] = {"sha256": brand.sha256_file(p), "bytes": len(data)}
    assets = {}
    for aid, mw in (("logo", 96), ("emblem", 24)):
        variants = {}
        for v in brand.VARIANTS:
            rel = f"svg/lynkomni-{aid}-{v}.svg"
            put(rel, SVG.encode(), files)
            variants[v] = {"svg": rel, "react": "X", "android": "x", "ios": "x"}
        assets[aid] = {"kind": aid, "component": "X", "accessibleName": "LynkOmni", "minWidthPx": mw, "viewBox": [-8, -8, 10, 10], "variants": variants, "auto": {"react": "XAuto"}}
    put("web/favicon.svg", b"<svg/>", files)
    for rel in ("email/logo-light.png", "email/logo-dark.png", "web/pwa-192.png"):
        if drop_dir and rel.startswith(drop_dir):
            continue
        put(rel, b"\x89PNG-fake-" + rel.encode(), rasters)
    themes = {}
    for t in brand.THEMES:
        m = generate.resolved(t)
        themes[t] = {"ink": m["logo-ink"], "accent": m["brand-primary"], "backgrounds": {k: m[k] for k in ("bg-base", "bg-surface")}}
    themes.update(themes_override or {})
    bj = {"schema": 1, "package": "@lynkomni/icons", "themes": themes, "assets": assets, "files": files, "rasters": rasters}
    os.makedirs(dist, exist_ok=True)
    with open(os.path.join(dist, "brand.json"), "w") as f: json.dump(bj, f)
    with open(os.path.join(root, "package.json"), "w") as f: json.dump({"name": "@lynkomni/icons", "version": version}, f)
    if corrupt:
        with open(os.path.join(dist, *corrupt.split("/")), "ab") as f: f.write(b"x")
    return root


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.pkg = os.path.join(self.tmp, "pkg"); os.makedirs(self.pkg)
        self.vendor = os.path.join(self.tmp, "vendor"); os.makedirs(self.vendor)
        self.lock = os.path.join(self.tmp, "brand.lock.json")
        self.state = os.path.join(self.tmp, "state.json")
        with open(self.state, "w") as f: json.dump({"synced": False}, f)
        self.kw = dict(vendor=self.vendor, lock_path=self.lock, state_path=self.state)
    def do_sync(self, **make):
        make_package(self.pkg, **make)
        return sync.sync(self.pkg, **self.kw)


class TestSync(Base):
    def test_sync_copies_only_the_vendored_folders_and_writes_a_lock(self):
        lk = self.do_sync()
        self.assertEqual(lk["version"], "1.2.3")
        self.assertIn("brand.json", lk["files"])
        self.assertTrue(all(r == "brand.json" or r.split("/")[0] in ("svg", "web", "email") for r in lk["files"]))
        self.assertTrue(brand.is_synced(self.state))
        self.assertEqual(brand.verify(**self.kw), [])

    def test_sync_is_repeatable_and_replaces_old_files(self):
        self.do_sync()
        with open(os.path.join(self.vendor, "stray.txt"), "w") as f: f.write("old")
        lk = self.do_sync(version="1.2.4")
        self.assertEqual(lk["version"], "1.2.4")
        self.assertFalse(os.path.exists(os.path.join(self.vendor, "stray.txt")))

    def test_refuses_a_package_whose_file_was_changed(self):
        make_package(self.pkg, corrupt="svg/lynkomni-logo-light.svg")
        with self.assertRaises(ValueError): sync.plan(self.pkg)

    def test_refuses_the_wrong_package(self):
        make_package(self.pkg)
        with open(os.path.join(self.pkg, "package.json"), "w") as f: json.dump({"name": "@evil/icons", "version": "1"}, f)
        with self.assertRaises(ValueError): sync.plan(self.pkg)

    def test_refuses_a_package_without_raster_files(self):
        make_package(self.pkg, drop_dir="email/")
        with self.assertRaises(ValueError): sync.plan(self.pkg)

    def test_refuses_unsafe_file_names(self):
        make_package(self.pkg)
        path = os.path.join(self.pkg, "dist", "brand.json")
        with open(path) as f: bj = json.load(f)
        bj["files"]["svg/../../etc/x.svg"] = {"sha256": "0", "bytes": 1}
        with open(path, "w") as f: json.dump(bj, f)
        with self.assertRaises(ValueError): sync.plan(self.pkg)


class TestApi(Base):
    def test_not_synced_raises_a_clear_error(self):
        with self.assertRaises(brand.BrandNotSynced): brand.asset("logo", "light", **self.kw)

    def test_asset_lookup_and_metadata(self):
        self.do_sync()
        a = brand.asset("logo", "mono", **self.kw)
        self.assertEqual((a.min_width_px, a.accessible_name, a.view_box), (96, "LynkOmni", (-8, -8, 10, 10)))
        self.assertTrue(os.path.isfile(a.path))
        self.assertEqual(brand.for_theme("emblem", "contrast-dark", **self.kw).variant, "contrast-dark")

    def test_unknown_asset_variant_and_theme_are_errors(self):
        self.do_sync()
        with self.assertRaises(KeyError): brand.asset("nope", "light", **self.kw)
        with self.assertRaises(KeyError): brand.asset("logo", "purple", **self.kw)
        with self.assertRaises(KeyError): brand.theme_variant("mono")

    def test_data_uri_and_svg_text(self):
        self.do_sync()
        self.assertTrue(brand.data_uri("logo", "light", **self.kw).startswith("data:image/svg+xml;base64,"))
        self.assertIn("<svg", brand.svg_text("logo", "light", **self.kw))

    def test_every_read_rechecks_the_file_against_the_lock(self):
        self.do_sync()
        with open(os.path.join(self.vendor, "svg", "lynkomni-logo-light.svg"), "a") as f: f.write("<script/>")
        with self.assertRaises(brand.BrandTampered): brand.svg_text("logo", "light", **self.kw)
        self.assertTrue(any("checksum mismatch" in p for p in brand.verify(**self.kw)))

    def test_extra_and_missing_vendored_files_are_reported(self):
        self.do_sync()
        with open(os.path.join(self.vendor, "svg", "extra.svg"), "w") as f: f.write("<svg/>")
        os.remove(os.path.join(self.vendor, "web", "pwa-192.png"))
        probs = brand.verify(**self.kw)
        self.assertTrue(any("not in brand.lock.json" in p for p in probs))
        self.assertTrue(any("missing vendored file web/pwa-192.png" in p for p in probs))

    def test_raster_only_serves_email_and_web_files(self):
        self.do_sync()
        self.assertTrue(os.path.isfile(brand.raster("email/logo-light.png", **self.kw)))
        with self.assertRaises(KeyError): brand.raster("svg/lynkomni-logo-light.svg", **self.kw)

    def test_invoice_branding_follows_the_checkout_tiers(self):
        from services import billing
        tiers = {f["invoice_branding"] for f in billing.FEATURES["lynkcheckout"] if "invoice_branding" in f}
        self.assertEqual(tiers, set(brand.INVOICE_BRANDING))
        self.assertTrue(brand.invoice_brand("lynkomni")["show_lynkomni"])
        self.assertFalse(brand.invoice_brand("logo")["show_lynkomni"])
        self.assertTrue(brand.invoice_brand("full")["merchant_logo"])
        with self.assertRaises(ValueError): brand.invoice_brand("platinum")


class TestGates(Base):
    def test_unsynced_state_skips_lock_checks_but_scan_still_runs(self):
        self.assertEqual(check.vendored_checks(**self.kw), [])

    def test_synced_but_lock_deleted_is_caught(self):
        self.do_sync(); os.remove(self.lock)
        self.assertTrue(check.vendored_checks(**self.kw))

    def test_token_mirror_passes_when_colours_match(self):
        self.do_sync()
        self.assertEqual(check.vendored_checks(**self.kw), [])

    def test_token_mirror_catches_a_changed_logo_colour(self):
        m = generate.resolved("dark")
        bad = {"dark": {"ink": "#FAFAFA", "accent": m["brand-primary"], "backgrounds": {"bg-base": m["bg-base"], "bg-surface": m["bg-surface"]}}}
        self.do_sync(themes_override=bad)
        probs = check.vendored_checks(**self.kw)
        self.assertTrue(any("dark: logo ink #FAFAFA" in p for p in probs), probs)

    def test_token_mirror_catches_a_changed_background(self):
        m = generate.resolved("light")
        bad = {"light": {"ink": m["logo-ink"], "accent": m["brand-primary"], "backgrounds": {"bg-base": "#FFFFFF", "bg-surface": m["bg-surface"]}}}
        self.do_sync(themes_override=bad)
        self.assertTrue(any("bg-base" in p for p in check.vendored_checks(**self.kw)))

    def test_the_real_surfaces_file_is_valid_unsynced_and_synced(self):
        self.assertEqual(check.surface_checks(**self.kw), [])
        self.do_sync()
        # the fixture package has no pwa files etc. for every listed surface file, so only structure is asserted here
        probs = check.surface_checks(**self.kw)
        self.assertTrue(all("is not in the brand lock" in p or "is not vendored" in p for p in probs), probs)

    def test_surface_rules_reject_bad_entries(self):
        bad = {"surfaces": [{"id": "Bad_Id", "status": "maybe", "uses": []}, {"id": "ok-one", "status": "live", "offline": True, "uses": [{"asset": "logo", "variants": ["neon"]}]}]}
        p = os.path.join(self.tmp, "s.json")
        with open(p, "w") as f: json.dump(bad, f)
        probs = check.surface_checks(surfaces_path=p, **self.kw)
        for needle in ("lowercase with hyphens", "live or planned", "offline", "list the assets", "unknown variant neon"):
            self.assertTrue(any(needle in x for x in probs), (needle, probs))

    def test_scan_catches_hard_coded_brand_violet_logo_names_and_image_urls(self):
        root = os.path.join(self.tmp, "repo"); os.makedirs(os.path.join(root, "services")); os.makedirs(os.path.join(root, "design"))
        with open(os.path.join(root, "services", "x.py"), "w") as f: f.write('C = "#7c4dff"\nP = "svg/lynkomni-logo-light.svg"\nU = "https://cdn.example.com/logo.png"\n')
        with open(os.path.join(root, "design", "ok.py"), "w") as f: f.write('C = "#7C4DFF"\n')
        probs = check.scan_code(root)
        self.assertEqual(len(probs), 3, probs)
        self.assertTrue(all(p.startswith("services/x.py") for p in probs))

    def test_the_real_repository_passes_the_scan(self):
        self.assertEqual(check.scan_code(), [])


class TestTokens(unittest.TestCase):
    def test_logo_ink_matches_the_logo_in_every_theme(self):
        exp = {"light": "#18181B", "dark": "#FFFFFF", "contrast-light": "#000000", "contrast-dark": "#FFFFFF"}
        for t, v in exp.items(): self.assertEqual(generate.resolved(t)["logo-ink"], v)

    def test_logo_ink_is_not_the_text_colour_in_dark(self):
        self.assertNotEqual(generate.resolved("dark")["logo-ink"], generate.resolved("dark")["text-primary"])


if __name__ == "__main__":
    unittest.main()
