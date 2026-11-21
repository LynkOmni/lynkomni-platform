"""Every Lynk name carries its plain word (owner, 21 November 2026; catalog/names.v1.json, core/names.py, ts/src/names.ts).

The register knows every name a person can see; every product family has its entry; each plain word belongs to one name
only and fits the limit in every language; every page carries the plain words and marks every name it shows (the screens
themselves are checked by the fit guard's walk, tests/test_fit_guard.py NAMES)."""
import glob, json, os, re, subprocess, sys, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "web", "emulators"))
from core import names as N  # noqa: E402
from services import billing  # noqa: E402
import build_data  # noqa: E402

LANGS = sorted(f[:-5] for f in os.listdir(os.path.join(ROOT, "web", "names", "i18n")) if f.endswith(".json"))


def pack(folder, lang):
    with open(os.path.join(ROOT, "web", folder, "i18n", f"{lang}.json"), encoding="utf-8") as f:
        return json.load(f)["texts"]


def screen_words():
    """Every English word a screen can show: the emulators' and the shared parts' words."""
    out = {}
    for path in glob.glob(os.path.join(ROOT, "web", "**", "strings.en.json"), recursive=True):
        with open(path, encoding="utf-8") as f:
            for k, v in json.load(f).items():
                out[f"{os.path.relpath(path, ROOT)}:{k}"] = v
    return out


class TestRegister(unittest.TestCase):
    def test_every_product_family_has_its_name(self):
        families = {n.get("family") for n in N.NAMES if n["kind"] == "product"}
        self.assertEqual(set(billing.FAMILIES) - families, set(), "a billing family without an entry in catalog/names.v1.json")
        with open(os.path.join(ROOT, "catalog", "products.v1.json"), encoding="utf-8") as f:
            self.assertLessEqual({p["family"] for p in json.load(f)["products"]}, families)

    def test_parts_belong_to_registered_names(self):
        for n in N.NAMES:
            if n.get("part_of"):
                self.assertIn(n["part_of"], N.BY_ID, n["name"])
            self.assertTrue(n["name"].startswith("Lynk"), n["name"])

    def test_device_plain_words_are_the_device_register_words(self):
        with open(os.path.join(ROOT, "catalog", "devices.v1.json"), encoding="utf-8") as f:
            devices = json.load(f)["lynk_names"]["names"]
        for name, d in devices.items():
            self.assertIn(name, N.BY_NAME)
            self.assertEqual(N.plain(name), d["what"], name)

    def test_retired_and_internal_names_are_never_on_a_screen(self):
        for where, text in screen_words().items():
            for w in re.findall(r"(?<![A-Za-z])Lynk[A-Z][A-Za-z]*", text):
                self.assertFalse(any(w.startswith(r) for r in N.REGISTER["retired"] + N.REGISTER["internal"]), f"{where}: {w}")

    def test_every_lynk_word_on_a_screen_is_registered(self):
        unknown = {where: N.unknown(text) for where, text in screen_words().items() if N.unknown(text)}
        self.assertEqual(unknown, {}, "add the name to catalog/names.v1.json with its plain word first")


class TestWords(unittest.TestCase):
    def test_every_name_has_words_in_every_language(self):
        for lang in LANGS:
            p, i = pack("names", lang), pack("nameinfo", lang) if lang != "en" else None
            for n in N.NAMES:
                self.assertTrue(p.get(f"nm_{n['id']}"), f"{lang}: nm_{n['id']}")
                if i is not None and n.get("about", True):
                    self.assertTrue(i.get(f"nma_{n['id']}"), f"{lang}: nma_{n['id']}")

    def test_each_plain_word_names_one_thing_and_fits(self):
        for lang in LANGS:
            p = pack("names", lang)
            seen = {}
            for n in N.NAMES:
                word = p[f"nm_{n['id']}"]
                self.assertLessEqual(len(word), N.MAX_PLAIN, f"{lang}: {n['name']} plain word is too long ({word})")
                self.assertNotIn(word.casefold(), seen, f"{lang}: {n['name']} and {seen.get(word.casefold())} share the plain word {word!r}")
                seen[word.casefold()] = n["name"]

    def test_names_stay_the_same_in_every_language(self):
        for lang in LANGS:
            i = pack("nameinfo", lang)
            self.assertIn("{name}", i["nmi_what_q"], lang)
            for k in ("{name}", "{plain}", "{about}"):
                self.assertIn(k, i["nmi_what_a"], lang)

    def test_the_footer_reads_plain_words_from_the_register(self):
        with open(os.path.join(ROOT, "web", "footer", "strings.en.json"), encoding="utf-8") as f:
            self.assertFalse([k for k in json.load(f) if k.startswith("ft_plain_")], "plain words live only in web/names")


class TestPages(unittest.TestCase):
    def test_every_page_carries_the_plain_words_and_marks_its_names(self):
        for app in glob.glob(os.path.join(ROOT, "web", "emulators", "*", "app.ts")):
            emu = os.path.basename(os.path.dirname(app))
            with open(app, encoding="utf-8") as f:
                self.assertIn("watchNames(document.body", f.read(), emu)
            self.assertIn(os.path.join("web", "names"), build_data.shared_folders(emu), emu)

    def test_shared_vectors_and_generated_register_are_current(self):
        r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "names_register.py"), "--check"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_find_and_label(self):
        self.assertEqual([f["name"] for f in N.find("Ask LynkAssist about LynkStat, not LynkStats or MyLynkPOS.")], ["LynkAssist", "LynkStat"])
        self.assertEqual(N.label("LynkStat"), "LynkStat (Analytics)")
        self.assertEqual(N.label("LynkStat", mode="plain_first"), "Analytics (LynkStat)")
        self.assertEqual(N.part_of("LynkProof"), "LynkMPay")
        self.assertEqual(N.unknown("LynkWidget and LynkOmni and LynkDVBox"), ["LynkWidget"])



class TestImprovements(unittest.TestCase):
    """The 15 improvements (owner, 21 November 2026, v0.81.0) and the rule that every new name follows them."""

    def test_marks_are_released_icons(self):
        import brand
        icons = brand.manifest()["icons"]
        for n in N.NAMES:
            if n.get("icon"):
                self.assertIn(n["icon"], icons, n["name"])
                self.assertEqual(icons[n["icon"]]["group"], "products", n["name"])
            if n["kind"] == "device":
                self.assertIsNone(n.get("icon"), n["name"])

    def test_every_name_can_be_said(self):
        for n in N.NAMES:
            self.assertTrue(n["spoken"].startswith("Link "), n["name"])
        self.assertEqual(N.speakable("Open LynkPOS"), "Open Link P O S")

    def test_old_names_lead_to_a_registered_name_and_nowhere_else(self):
        for old, x in N.NOW_CALLED.items():
            self.assertIn(old, N.REGISTER["retired"], old)
            self.assertNotIn(old, N.BY_NAME)
            self.assertIn(x["id"], N.BY_ID, old)
            self.assertRegex(x["since"], r"^\d{4}-\d{2}-\d{2}$")

    def test_similar_groups_name_registered_names(self):
        for g in N.SIMILAR:
            self.assertGreaterEqual(len(g["names"]), 2, g["id"])
            for i in g["names"]:
                self.assertIn(i, N.BY_ID, g["id"])
        self.assertEqual(N.similar("LynkMotion"), ["LynkGuard"])

    def test_every_plain_word_is_plain_in_every_language(self):
        for lang in LANGS:
            p = pack("names", lang)
            for n in N.NAMES:
                self.assertEqual(N.check_plain(p[f"nm_{n['id']}"]), [], f"{lang}: {n['name']} plain word {p[f'nm_{n['id']}']!r}")

    def test_new_words_exist_in_every_language(self):
        keys = ["nm_now_called", "nm_renamed", "nm_compare_title", "nm_welcome_title", "nm_welcome_start", "nm_got_it", "nm_az_title",
                "nm_az_note", "nm_familiar", "nm_familiar_note", "nm_say"]
        for lang in LANGS:
            p = pack("names", lang)
            for k in keys:
                self.assertTrue(p.get(k), f"{lang}: {k}")
            for k, ph in (("nm_now_called", ("{old}", "{name}")), ("nm_renamed", ("{old}", "{name}")), ("nm_welcome_title", ("{name}",)), ("nm_say", ("{spoken}",))):
                for x in ph:
                    self.assertIn(x, p[k], f"{lang}: {k}")

    def test_messages_and_paper_explain_each_name_once(self):
        self.assertEqual(N.explain_text("Paid with LynkCheckout. LynkCheckout again."), "Paid with LynkCheckout (Pay links & QR). LynkCheckout again.")
        lines = N.paper_lines(["Paid by LynkCheckout", "LynkCheckout"], width=24)
        self.assertEqual(lines, ["LynkCheckout: Pay links", "  & QR"])
        self.assertTrue(all(len(l) <= 24 for l in lines))
        self.assertEqual(N.paper_lines(["Thank you"]), [])

    def test_bills_name_each_line(self):
        self.assertEqual(N.bill_label("lynkstat", "Plus"), "LynkStat Plus (Analytics)")
        self.assertEqual(N.bill_label("storefront", "Storefront Plus"), "Storefront Plus")
        with open(os.path.join(ROOT, "services", "billing.py"), encoding="utf-8") as f:
            self.assertIn('l["name"], l["plain_key"] = n', f.read())

    def test_every_api_belongs_to_a_name(self):
        with open(os.path.join(ROOT, "catalog", "apis.v1.json"), encoding="utf-8") as f:
            for a in json.load(f)["apis"]:
                if a.get("family") != "platform":   # platform APIs are named in plain words already ("Translation API")
                    self.assertIsNotNone(N.for_family(a["family"]), a["id"])
                    self.assertEqual(N.unknown(a["name"]), [], a["id"])

    def test_search_engines_get_plain_words(self):
        with open(os.path.join(ROOT, "catalog", "search.v1.json"), encoding="utf-8") as f:
            reg = json.load(f)
        self.assertEqual(reg["names"]["title"], "{name}: {plain}")
        self.assertIn("https://lynkomni.com/names", [p["url"] for p in reg["pages"]])
        for p in reg["pages"]:
            if p["kind"] == "product" and p.get("name"):
                self.assertEqual(p["plain_key"], N.plain_key(p["name"]), p["url"])
        stat = [p for p in reg["pages"] if p.get("name") == "LynkStat"]
        self.assertEqual(stat[0]["old_names"], ["LynkDash"])

    def test_confusing_names_are_shown_as_totals_of_five_or_more(self):
        from services.name_asks import NameAsks
        a = NameAsks()
        a.receive("2026-11-21", {"stat": 4, "pos": 6, "nope": 50, "acc": -3})
        self.assertEqual(a.report(), [{"name": "LynkPOS", "asks": 6}])
        a.receive("2026-11-22", {"stat": 1})
        self.assertEqual([r["name"] for r in a.report()], ["LynkPOS", "LynkStat"])
        with self.assertRaises(ValueError):
            a.receive("2026-11-22T10:00", {"stat": 1})

    def test_outside_places_have_their_build_section(self):
        places = {o["place"]: o for o in N.REGISTER["outside"]}
        self.assertEqual(set(places), {"messages", "bills", "customers", "developers", "staff", "search_engines", "names_page"})
        for o in places.values():
            self.assertIn(str(o["build_section"]), ("4", "5", "6", "11", "12"))


if __name__ == "__main__":
    unittest.main()
