"""INTERFACE UPDATE (master blueprint 73, section 4 step B): one navigation register and one page-template register for every
screen. Eight groups with every family in exactly one; every Business app screen has a template and a way in; anything used often
is at most three taps from Home; focus screens hide everything but Back or Cancel and the connection chip; the TypeScript port
agrees through the shared vectors."""
import json, os, subprocess, sys, unittest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from core import navigation as N

WORDS = json.load(open(os.path.join(ROOT, "web", "navigation", "strings.en.json"), encoding="utf-8"))


class Register(unittest.TestCase):
    def test_register_is_consistent(self):
        self.assertEqual(N.validate(), [])

    def test_the_eight_groups_in_their_order(self):
        self.assertEqual([g["id"] for g in N.NAV["groups"]],
                         ["sell", "get_paid", "run_the_office", "people", "move_and_protect", "learn_and_work", "ask_and_decide", "build"])
        self.assertEqual(N.group_of("lynkmotion_land"), "move_and_protect")
        self.assertIsNone(N.group_of("lynkdocs"))

    def test_every_label_has_its_words(self):
        keys = [g["label_key"] for g in N.NAV["groups"]]
        nav = N.NAV
        for item in (nav["rail"]["top"] + nav["rail"]["bottom"] + nav["rail"]["extras"] + nav["bottom_bar"]["person"]["tabs"]
                     + nav["bottom_bar"]["soft_keys"] + nav["header"]["app"] + nav["header"]["app_banners"] + nav["search_groups"]
                     + nav["account_menu"] + nav["launcher"] + nav["rail"]["service_menu_order"] + [q["id"] for q in nav["quick_create"]]
                     + N.TEMPLATES["templates"]["record"]["tabs"] + ["back_or_cancel", "storefront", "more", "needs_internet", "reset_to_default", "turned_sideways", "turned_upright"]):
            keys.append(f"nv_{item}")
        keys = [k for k in keys if k != "nv_assist"]   # LynkAssist is a product name, shown from the code, never translated
        missing = sorted({k for k in keys if k not in WORDS})
        self.assertEqual(missing, [], "every navigation label has its words in web/navigation/strings.en.json")

    def test_safety_and_settings_can_never_be_hidden(self):
        self.assertIn("settings", N.NAV["rail"]["never_hidden"])


class Menus(unittest.TestCase):
    def test_focus_screens_keep_only_back_and_the_connection_chip(self):
        self.assertEqual(N.header("pay"), ["back_or_cancel", "connection_chip"])
        self.assertEqual(N.bottom_bar("shop", screen="pay"), [])
        self.assertEqual(N.protected("shift"), "cash_count")
        self.assertIn("quick_create", N.header("stock"))

    def test_bottom_bars(self):
        self.assertEqual(N.bottom_bar("person"), ["home", "track", "scan", "chats", "me"])
        self.assertEqual(N.centre("person"), "scan")
        self.assertEqual(N.bottom_bar("shop"), ["home", "sell", "stock", "chats", "business"])
        self.assertEqual(len(N.bottom_bar("person", 4)), 4, "a small phone has four tabs")
        self.assertEqual(N.bottom_bar("person", chosen={2: "jobs"}), N.bottom_bar("person"), "the centre is not chosen")

    def test_quick_create_follows_the_role_and_the_build_order(self):
        self.assertEqual(N.quick_create("cashier"), ["new_sale", "new_customer"])
        self.assertNotIn("new_task", N.quick_create("owner", built=["4"]), "LynkProject is built in section 4B")

    def test_every_service_menu_in_the_same_order(self):
        order = N.NAV["rail"]["service_menu_order"]
        for m in N.MENUS:
            slots = [s for s, _ in N.service_menu(m)]
            slots = [("lists" if s == "list" else s) for s in slots]
            self.assertEqual(slots, sorted(slots, key=order.index), m)
            self.assertEqual(slots[0], "overview", m)

    def test_three_taps_and_no_orphans(self):
        taps = N.taps_from_home("shop")
        self.assertEqual(set(N.SCREENS) - set(taps), set(), "every screen has a way in")
        for s in N.NAV["often"]:
            self.assertLessEqual(taps[s], 3, s)
        self.assertEqual(N.page_tabs(list("abcdefgh")), list("abcdef") + ["more"])

    def test_vectors_current(self):
        r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "navigation_vectors.py"), "--check"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


class Turning(unittest.TestCase):
    """TURN UPDATE (master blueprint 76): nothing in LynkOmni locks a person's screen to one direction."""
    def test_nothing_locks_the_direction(self):
        found = []
        for base in ("ts/src", "web"):
            for dirpath, dirs, files in os.walk(os.path.join(ROOT, base)):
                dirs[:] = [d for d in dirs if d not in ("dist", "node_modules", "i18n")]
                for name in files:
                    if name.endswith((".ts", ".mjs", ".html", ".css", ".json", ".webmanifest")):
                        text = open(os.path.join(dirpath, name), encoding="utf-8").read()
                        if "orientation.lock(" in text or '"orientation": "portrait"' in text or '"orientation": "landscape"' in text:
                            found.append(os.path.relpath(os.path.join(dirpath, name), ROOT))
        self.assertEqual(found, [])

    def test_the_turn_keeps_everything(self):
        from core import interfaces as I
        t = I.SHAPES["turn"]
        for must in ("typed_text", "cursor", "basket", "cash_count", "focus", "form_step", "scroll"):
            self.assertIn(must, t["keep"])
        self.assertEqual(set(t["keep_step"]), set(N.NAV["protected"]))
        self.assertNotIn("smartphone", I.SHAPES["lockable"], "a person's own phone is never locked")


if __name__ == "__main__":
    unittest.main()
