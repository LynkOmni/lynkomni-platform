"""The working standards stay in place: rule book, finish checklist, change log and decision diary."""
import os, re, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read(*p):
    with open(os.path.join(ROOT, *p), encoding="utf-8") as f:
        return f.read()


class Standards(unittest.TestCase):
    def test_rule_book_has_every_part(self):
        txt = read("docs", "lynkomni-standards.md")
        for part in ("How we work", "finish checklist", "Test before adding", "Version numbers", "Decision diary"):
            self.assertIn(part, txt)

    def test_pull_requests_carry_the_finish_checklist(self):
        self.assertGreaterEqual(read(".github", "pull_request_template.md").count("- [ ]"), 9)

    def test_change_log_versions_are_newest_first(self):
        versions = re.findall(r"^## v(\d+)\.(\d+)\.(\d+)", read("docs", "lynkomni-changelog.md"), re.M)
        self.assertTrue(versions)
        nums = [tuple(map(int, v)) for v in versions]
        self.assertEqual(nums, sorted(nums, reverse=True))

    def test_decision_diary_lines_are_dated(self):
        rows = [l for l in read("docs", "lynkomni-decisions.md").splitlines() if l.startswith("| ") and not l.startswith("| Date") and not l.startswith("|---")]
        self.assertTrue(rows)
        for r in rows:
            self.assertRegex(r, r"^\| (\d{4}-\d{2}-\d{2}|Before \d{4}-\d{2}-\d{2}|[A-Z][a-z]+ \d{4}) \|", r)


if __name__ == "__main__":
    unittest.main()
