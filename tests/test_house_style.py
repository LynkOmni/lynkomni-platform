"""House style checks the owner asked for (2026-11-24): device names are written in capitals everywhere they are titles, and the
project rules file never states the same rule twice (a merge once left the LynkBet rule in two copies)."""
import glob
import json
import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SMALL = {"a", "an", "and", "as", "at", "between", "by", "for", "in", "of", "on", "or", "the", "to", "with"}


def title_case_problems(title):
    """Words that should start with a capital letter: every word except the small joining words (never the first word)."""
    words = re.findall(r"[A-Za-z][A-Za-z'\-]*", title)
    return [w for i, w in enumerate(words) if w[0].islower() and (i == 0 or w.lower() not in SMALL)]


def emulator_titles():
    s = json.load(open(os.path.join(ROOT, "web", "showcase", "showcase.v1.json"), encoding="utf-8"))
    out = []

    def walk(x):
        if isinstance(x, dict):
            if isinstance(x.get("title"), str) and any(isinstance(x.get(k), str) and "claude.ai/artifact" in x[k] for k in ("url", "link", "artifact")):
                out.append(x["title"])
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
    walk(s)
    return out


class HouseStyle(unittest.TestCase):
    def test_device_titles_are_in_capitals(self):
        titles = emulator_titles()
        self.assertGreater(len(titles), 10)
        for f in sorted(glob.glob(os.path.join(ROOT, "web", "emulators", "*", "shell.html"))):
            html = open(f, encoding="utf-8").read()
            titles += re.findall(r"<title>([^<]+)</title>", html)
            titles += [re.sub(r"<span.*", "", h).strip() for h in re.findall(r"<h1>(.*?)</h1>", html)]
        bad = {t: title_case_problems(t) for t in titles if title_case_problems(t)}
        self.assertEqual(bad, {}, "device names in titles use capitals, for example LynkBet Betting Counter")

    def test_the_rules_file_states_each_rule_once(self):
        lines = [l for l in open(os.path.join(ROOT, "CLAUDE.md"), encoding="utf-8").read().splitlines() if l.startswith("- ")]
        starts = [l[:80] for l in lines]
        dups = sorted({s for s in starts if starts.count(s) > 1})
        self.assertEqual(dups, [], "a rule appears twice in CLAUDE.md")


if __name__ == "__main__":
    unittest.main()
