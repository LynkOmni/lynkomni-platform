"""Safe page settings (MASTER UPDATE, master blueprint section 59; build section 1): every built page carries the one policy."""
import glob, json, os, unittest
from core import pagesafety as ps

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGES = sorted(glob.glob(os.path.join(ROOT, "web", "emulators", "dist", "*.html"))) + [os.path.join(ROOT, "web", "showcase", "dist", "lynkomni-showcase.html")]


class TestPageSafety(unittest.TestCase):
    def test_every_built_page_carries_the_policy_and_only_its_own_scripts_run(self):
        self.assertGreaterEqual(len(PAGES), 15)
        for p in PAGES:
            with self.subTest(page=os.path.basename(p)):
                self.assertEqual(ps.check_html(open(p, encoding="utf-8").read()), [])

    def test_an_injected_or_changed_script_is_refused(self):
        page = open(PAGES[0], encoding="utf-8").read()
        self.assertIn("does not match", " ".join(ps.check_html(page.replace("</body>", "<script>alert(1)</script></body>"))))
        self.assertIn("does not match", " ".join(ps.check_html(page.replace("document.documentElement.dataset.ready", "fetch('//x');document.documentElement.dataset.ready", 1))))
        self.assertIn("loads from an address", " ".join(ps.check_html(page.replace("</body>", '<script src="https://x.example/a.js"></script></body>'))))
        self.assertIn("event handler", " ".join(ps.check_html(page.replace("<body>", '<body><img alt="" onerror="x()">'))))
        self.assertEqual(ps.check_html("<html><head></head><body></body></html>"), ["no page safety policy"])

    def test_the_policy_allows_nothing_from_outside(self):
        d = ps.DIRECTIVES
        self.assertEqual((d["default-src"], d["connect-src"], d["object-src"], d["base-uri"], d["form-action"]), ("'none'",) * 5)
        self.assertEqual(d["script-src"], "HASHES", "scripts are pinned by hash, never 'unsafe-inline'")
        self.assertNotIn("http", json.dumps(d))
        h = ps.HEADERS
        self.assertIn("frame-ancestors 'none'", h["Content-Security-Policy"])
        self.assertIn("includeSubDomains", h["Strict-Transport-Security"])
        self.assertEqual(h["X-Content-Type-Options"], "nosniff")


if __name__ == "__main__":
    unittest.main()
