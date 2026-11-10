"""The shared rules behind the section 1 shell parts stay current (MASTER UPDATE, build section 1)."""
import os, subprocess, sys, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestShellParts(unittest.TestCase):
    def test_vectors_and_generated_rules_are_current(self):
        r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "shell_parts.py"), "--check"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_the_parts_exist_on_every_side(self):
        for f in ("signin", "notify", "assist", "breadcrumbs", "pagehead"):
            self.assertTrue(os.path.isfile(os.path.join(ROOT, "ts", "src", f"{f}.ts")), f)


if __name__ == "__main__":
    unittest.main()
