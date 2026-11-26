"""PLACEHOLDER UPDATE (owner 2026-11-19, master blueprint section 83; catalog/placeholders.v1.json). Every typing field has a hint
(an example, never the instruction) or is a sensitive field that must have none; every hinted field keeps a visible label; no
screen carries filler text; the skeleton timing in the code matches the register. Fields still due when the rule was agreed are
listed with their build section: the list may only shrink, a new field without a hint fails here at once, and the section
cannot lock while anything is due."""
import glob, json, os, re, unittest
from core import build_sections as b

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R = json.load(open(os.path.join(ROOT, "catalog", "placeholders.v1.json"), encoding="utf-8"))
SKIP_TYPES = ('type="hidden"', 'type="checkbox"', 'type="radio"', 'type="range"', 'type="file"')


def fields():
    """Every typing field in the screen code: (file, key, attributes)."""
    out = []
    for f in sorted(glob.glob(os.path.join(ROOT, "ts", "src", "*.ts")) + glob.glob(os.path.join(ROOT, "web", "emulators", "*", "app.ts"))):
        rel = os.path.relpath(f, ROOT); s = open(f, encoding="utf-8").read()
        for m in re.finditer(r"<(input|textarea)\b([^>]*)>", s):
            a = m.group(2)
            if any(x in a for x in SKIP_TYPES):
                continue
            k = re.search(r'\bid="([^"$]+)"', a) or re.search(r'data-in="([^"]+)"', a) or re.search(r'data-field="([^"]+)"', a) \
                or re.search(r'class="([^"]+)"', a) or re.search(r'type="([^"]+)"', a)
            out.append((rel, k.group(1) if k else a[:30], a, s))
    return out


class Placeholders(unittest.TestCase):
    def test_every_field_has_a_hint_or_is_sensitive_or_is_due(self):
        due, sens = R["due"]["hints"], R["sensitive"]
        for f, k, a, _ in fields():
            hinted = "placeholder=" in a
            if k in sens.get(f, []) or any(m in a for m in R["sensitive_markers"]):
                self.assertFalse(hinted and ('type="password"' in a or "one-time-code" in a), f"{f} {k}: a sensitive field never shows an example value")
                continue
            if not hinted:
                self.assertIn(k, due.get(f, []), f"{f}: the field {k} needs a hint (an example of what to type) in every language")

    def test_the_due_list_only_shrinks(self):
        now = {(f, k) for f, k, a, _ in fields() if "placeholder=" not in a}
        for f, keys in R["due"]["hints"].items():
            for k in keys:
                self.assertIn((f, k), now, f"{f} {k} has its hint now: take it off the due list")

    def test_a_hint_never_replaces_the_label(self):
        due = R["due"]["labels"]
        for f, k, a, s in fields():
            if "placeholder=" not in a:
                continue
            labelled = "aria-label" in a or "aria-labelledby" in a
            m = re.search(r'\bid="([^"]+)"', a)
            labelled = labelled or bool(m and f'for="{m.group(1)}"' in s)
            if not labelled:
                self.assertIn(k, due.get(f, []), f"{f} {k}: a hinted field keeps a visible label or an accessible name")

    def test_due_items_wait_in_a_section_still_to_lock(self):
        s = R["due"]["section"]
        self.assertIn(s, [str(n) for n in b.ORDER])
        if any(R["due"]["hints"].values()) or any(R["due"]["labels"].values()):
            self.assertNotEqual(b.status(s), "locked", f"section {s} cannot lock while fields still need hints or labels")

    def test_no_filler_text_on_any_screen(self):
        pats = [re.compile(p) if re.search(r"[A-Z]", p) else re.compile(p, re.I) for p in R["banned_text"]]
        for f in glob.glob(os.path.join(ROOT, "web", "**", "strings.en.json"), recursive=True):
            for k, v in json.load(open(f, encoding="utf-8")).items():
                for p in pats:
                    self.assertIsNone(p.search(str(v)), f"{f} {k}: filler text on a screen")

    def test_the_83_7_additions_are_recorded(self):
        self.assertGreaterEqual(len(R["more"]["rules"]), 13)
        self.assertIn("Intl.NumberFormat", open(os.path.join(ROOT, "ts", "src", "hints.ts"), encoding="utf-8").read(), "number hints use the reader's digits (ts/src/hints.ts)")

    def test_the_code_follows_the_register(self):
        src = open(os.path.join(ROOT, "ts", "src", "placeholder.ts"), encoding="utf-8").read()
        t = R["timing_ms"]
        self.assertIn(f"SHOW_AFTER: {t['show_after']}, MIN_SHOW: {t['min_show']}, SLOW_AFTER: {t['slow_after']}", src)
        for shape in R["shapes"]:
            self.assertIn(f'"{shape}"', src)
        css = open(os.path.join(ROOT, "web", "shell", "placeholder.css"), encoding="utf-8").read()
        self.assertIn("prefers-reduced-motion", css)
        self.assertIn("data-lite", css)
        self.assertNotRegex(css, r"#[0-9a-fA-F]{3,8}\b", "tokens only")


class EveryPageWaits(unittest.TestCase):
    def test_every_page_waits_well_or_says_why_not(self):
        """83.4: every emulator page has the kit's wait or calls the shared PageWait at the end of its draw."""
        reg = json.load(open(os.path.join(ROOT, "catalog", "placeholders.v1.json"), encoding="utf-8"))["waits"]
        for app in sorted(glob.glob(os.path.join(ROOT, "web", "emulators", "*", "app.ts"))):
            emu = os.path.basename(os.path.dirname(app)); src = open(app, encoding="utf-8").read()
            waits = "wireKit(" in src or "pageWaiting(" in src or "WAIT.apply(" in src
            if emu in reg["not_needed"]:
                self.assertFalse(waits, f"{emu} waits now: take it off the not_needed list")
            else:
                self.assertTrue(waits, f"{emu}: call pageWaiting (ts/src/emulator.ts) at the end of draw, or give a reason in placeholders.v1.json waits")
                if "wireKit(" not in src:
                    self.assertIn("firstopen", src.replace("cFirst", "firstopen"), f"{emu}: the panel needs the First open condition")

    def test_the_wait_words_match_the_shell(self):
        for f in sorted(os.listdir(os.path.join(ROOT, "web", "wait", "i18n"))):
            wait = json.load(open(os.path.join(ROOT, "web", "wait", "i18n", f), encoding="utf-8"))["texts"]
            shell = json.load(open(os.path.join(ROOT, "web", "shell", "i18n", f), encoding="utf-8"))["texts"]
            for k, v in wait.items():
                self.assertEqual(v, shell[k], f"{f} {k}: the wait words are the shell's own")

    def test_buttons_that_ask_the_cloud_keep_their_width(self):
        css = open(os.path.join(ROOT, "web", "shell", "placeholder.css"), encoding="utf-8").read()
        ts = open(os.path.join(ROOT, "ts", "src", "placeholder.ts"), encoding="utf-8").read()
        self.assertIn("minInlineSize", ts); self.assertIn('[aria-busy="true"]', css)
        self.assertIn("BUSY_MAX_MS", ts)                                    # nothing stays stuck


class FieldsHelp(unittest.TestCase):
    """83.7: fields that help while people type. The help itself is added by ts/src/placeholder.ts enhanceFields after every draw."""
    SOURCES = sorted(glob.glob(os.path.join(ROOT, "ts", "src", "*.ts")) + glob.glob(os.path.join(ROOT, "web", "emulators", "*", "app.ts")))

    def tags(self, pattern):
        for p in self.SOURCES:
            if p.endswith(".generated.ts"):
                continue
            s = open(p, encoding="utf-8").read()
            for m in re.finditer(pattern, s):
                yield os.path.relpath(p, ROOT), s.count("\n", 0, m.start()) + 1, m.group(0)

    def test_a_disabled_field_says_why(self):
        for f, line, tag in self.tags(r'<(?:input|select|textarea)\b[^>]*?(?:\$\{[^}]*disabled[^}]*\}|\bdisabled\b)[^>]*>'):
            self.assertIn("data-why", tag, f"{f}:{line}: a disabled field needs data-why (a word key, or \"shown\" when the reason stands beside it)")

    def test_a_search_box_offers_recent_searches(self):
        for f, line, tag in self.tags(r'<input\b[^>]*type="search"[^>]*>'):
            self.assertIn("data-recents", tag, f"{f}:{line}: a search box needs data-recents (and data-suggest when nothing else shows under it)")

    def test_long_typing_keeps_a_draft_unless_the_device_is_shared(self):
        shared = json.load(open(os.path.join(ROOT, "catalog", "placeholders.v1.json"), encoding="utf-8"))["fields"]["no_draft"]
        for f, line, tag in self.tags(r'<textarea\b[^>]*>'):
            if "data-draft" not in tag:
                self.assertTrue(any(k in tag for k in shared), f"{f}:{line}: a long text box keeps a draft (data-draft) or is listed in fields.no_draft with its reason")

    def test_the_parts_exist_and_never_keep_a_card_number(self):
        ts = open(os.path.join(ROOT, "ts", "src", "placeholder.ts"), encoding="utf-8").read()
        for part in ("export function enhanceFields", "export function counterText", "export function rememberSearch", "export function draftSafe", "SENSITIVE"):
            self.assertIn(part, ts)
        css = open(os.path.join(ROOT, "web", "shell", "placeholder.css"), encoding="utf-8").read()
        for mode in ('[data-mode="sunlight"] .skeleton', "forced-colors: active", "prefers-reduced-motion"):
            self.assertIn(mode, css)


class NoGapsLeft(unittest.TestCase):
    """83.7: what a screen shows instead of a gap, each through its shared part (ts/src/placeholder.ts)."""
    SOURCES = FieldsHelp.SOURCES

    def code(self):
        for p in self.SOURCES:
            if not p.endswith((".generated.ts", "placeholder.ts")):
                yield os.path.relpath(p, ROOT), open(p, encoding="utf-8").read()

    def test_every_83_7_rule_says_where_it_is_built(self):
        more = json.load(open(os.path.join(ROOT, "catalog", "placeholders.v1.json"), encoding="utf-8"))["more"]
        self.assertEqual(len(more["built"]), len(more["rules"]))

    def test_a_feature_on_a_higher_plan_shows_what_it_does_on_staff_screens(self):
        s = open(os.path.join(ROOT, "ts", "src", "queuedesk.ts"), encoding="utf-8").read()
        for k in ("ppl_qu_plan_forecast", "ppl_qu_plan_hardware", "ppl_qu_plan_send_to"):
            self.assertIn(f'planPreviewHtml(t, "{k}"', s, k)
            self.assertNotIn(f'esc(t("{k}"))', s, k)
        sv = open(os.path.join(ROOT, "ts", "src", "surveydesk.ts"), encoding="utf-8").read()
        self.assertIn("plan_limit_live_surveys: ", sv); self.assertIn("plan_no_hardware_without_display: ", sv)   # staff refusals for the plan
        self.assertEqual(sv.count("svRefusedStaff(d.refused, t)"), 2)

    def test_pictures_uploads_and_longer_lists_use_their_parts(self):
        for f, s in self.code():
            self.assertNotRegex(s, r"<img\b|createElement\(\"img\"\)", f"{f}: draw a picture with pictureHtml (it keeps its shape and its alt text)")
            if 'type="file"' in s:
                self.assertIn("uploadHtml(", s, f"{f}: a file field shows its upload with uploadHtml")
            if re.search(r"load[_-]?more|loadMore", s):
                self.assertIn("listEnd(", s, f"{f}: a list that loads more ends with listEnd")

    def test_logos_waiting_their_check_show_initials_and_voice_never_goes_silent(self):
        mp = open(os.path.join(ROOT, "web", "emulators", "merchant-phone", "app.ts"), encoding="utf-8").read()
        self.assertIn("logoInitialsHtml(shop(), t)", mp)
        bp = open(os.path.join(ROOT, "web", "emulators", "button-phone", "app.ts"), encoding="utf-8").read()
        self.assertIn('t("ch_working")', bp)


if __name__ == "__main__":
    unittest.main()


class HandleHint(unittest.TestCase):
    """Every handle field (username, shop, business, developer app, partner, agent point) shows "@username" as its example,
    never "your.name", which made people think a full stop was needed (owner, 2026-11-26). A typed @ is ignored."""
    SOURCES = glob.glob(os.path.join(ROOT, "ts", "src", "*.ts")) + glob.glob(os.path.join(ROOT, "web", "emulators", "*", "app.ts"))

    def test_the_hint_is_at_username(self):
        with open(os.path.join(ROOT, "ts", "src", "hints.ts"), encoding="utf-8") as f:
            self.assertIn('username: "@username"', f.read())

    def test_no_old_example_and_every_handle_field_uses_the_hint(self):
        for path in self.SOURCES:
            with open(path, encoding="utf-8") as f:
                src = f.read()
            self.assertNotIn("your.name", src, path)
            for m in re.finditer(r'<input[^>]*(?:id="(?:usernameIn|userIn|wyUser|handleIn)"|data-in="[^"]*user)[^>]*>', src):
                tag = m.group(0)
                self.assertTrue('hintFor("username"' in tag or 'placeholder="@username"' in tag, f"{path}: a handle field without the @username hint: {tag[:80]}")

    def test_a_typed_at_is_ignored(self):
        from core import usernames
        self.assertEqual(usernames.normalize("@Mamas.Kitchen"), "mamas.kitchen")
