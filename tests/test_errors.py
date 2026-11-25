"""Errors say where, why and how to fix (section 4C point 2, owner 2026-11-25).

Every error, warning, information and success message is drawn by the one shared part ts/src/errorbox.ts (noticeHtml,
summaryHtml, ourSideHtml, fieldMsgHtml): the official colours with an icon shape and a word, the field it is about, what and
why, and a fix. Its types refuse an error without a fix. This check refuses any screen that draws its own error or warning box.
DUE lists the files still being moved onto the part in section 4C step 2b; it may only shrink, and 4C cannot lock while it has
anything in it."""
import glob
import json
import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PARTS = {"ts/src/errorbox.ts", "ts/src/fields.ts", "ts/src/emailfield.ts", "ts/src/codefield.ts"}
# Still drawing their own boxes, moved in section 4C step 2b (v0.116.0).
DUE = {
    "ts/src/attenddesk.ts", "ts/src/chatview.ts", "ts/src/officeview.ts", "ts/src/sharedview.ts", "ts/src/signin.ts",
    "ts/src/devicekit.ts", "ts/src/peopleparts.ts", "ts/src/shell.ts", "ts/src/queuedesk.ts", "ts/src/surveydesk.ts",
    "ts/src/workview.ts", "web/emulators/account-site/app.ts", "web/emulators/counter-tablet/app.ts",
    "web/emulators/pos-terminal/app.ts", "web/emulators/bet-counter/app.ts", "web/emulators/owner-web/app.ts",
    "web/emulators/rider-phone/app.ts", "web/emulators/merchant-phone/app.ts",
}
OWN_BOX = re.compile(r'role=\\?"alert\\?"|class=\\?"(?:warn|bwarn|sv-warn|ch-warn|error|err|alert [a-z]+|pmsg danger|pmsg success)[ "\\]')


def screen_files():
    for p in glob.glob(os.path.join(ROOT, "ts", "src", "*.ts")) + glob.glob(os.path.join(ROOT, "web", "emulators", "*", "app.ts")):
        rel = os.path.relpath(p, ROOT).replace(os.sep, "/")
        if not rel.endswith(".generated.ts"):
            yield rel


class Errors(unittest.TestCase):
    def test_no_screen_draws_its_own_error_box(self):
        bad = []
        for rel in screen_files():
            if rel in PARTS or rel in DUE:
                continue
            with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
                for i, line in enumerate(f, 1):
                    if OWN_BOX.search(line):
                        bad.append(f"{rel}:{i}")
        self.assertEqual(bad, [], "draw errors and warnings with ts/src/errorbox.ts (noticeHtml): " + ", ".join(bad))

    def test_the_due_list_only_names_files_that_still_need_moving(self):
        for rel in sorted(DUE):
            with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
                self.assertRegex(f.read(), OWN_BOX, f"{rel} no longer draws its own box: take it off DUE")

    def test_an_error_cannot_be_drawn_without_a_fix(self):
        with open(os.path.join(ROOT, "ts", "src", "errorbox.ts"), encoding="utf-8") as f:
            src = f.read()
        self.assertIn('export type ErrorNotice = Base & { level: "error" } & ({ fix: Fix; how?: string } | { how: string; fix?: Fix });', src)
        self.assertIn('role="${n.level === "error" ? "alert" : "status"}"', src)

    def test_every_level_has_its_word_in_every_language(self):
        words = ["fd_error", "fd_warning", "fd_info", "fd_success", "fd_our_side", "fd_ref", "fd_try_again", "fd_contact_support", "fd_one_to_fix", "fd_things_to_fix"]
        for p in glob.glob(os.path.join(ROOT, "web", "fields", "i18n", "*.json")):
            with open(p, encoding="utf-8") as f:
                pack = json.load(f)["texts"]
            for w in words:
                self.assertTrue(pack.get(w), f"{os.path.basename(p)} {w}")

    def test_the_colours_are_the_official_tokens(self):
        with open(os.path.join(ROOT, "web", "shell", "fields.css"), encoding="utf-8") as f:
            css = f.read()
        for level, token in (("error", "danger"), ("warning", "warning"), ("info", "info"), ("success", "success")):
            self.assertRegex(css, rf"\.lf-{level} {{ background: var\(--status-{token}-bg\); color: var\(--status-{token}-text\); border-color: var\(--status-{token}-border\); }}")
        self.assertNotRegex(css, r"#[0-9a-fA-F]{3,8}\b")

    def test_the_tracking_refusal_names_the_item_the_step_and_the_earlier_step(self):
        with open(os.path.join(ROOT, "web", "tracking", "strings.en.json"), encoding="utf-8") as f:
            en = json.load(f)
        self.assertEqual(en["trk_scan_why_after"], "{item} can't be marked {step} yet, because {earlier} hasn't been confirmed.")
        self.assertEqual(en["trk_scan_fix_after"], "Mark {step} first")


if __name__ == "__main__":
    unittest.main()
