"""DEVICE (master blueprint 48.17): one register and one decision function choose the interface for every device; every
combination of facts gets exactly one interface; overrides and registered devices win; unknown means the safe default."""
import json, os, subprocess, sys, unittest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from core import interfaces as I


class Register(unittest.TestCase):
    def test_register_is_consistent(self):
        self.assertEqual(I.validate(), [])
        for need in I.REGISTER["every_interface_accepts"]: self.assertIn(need, I.REGISTER["inputs"])

    def test_every_emulator_named_exists_or_is_built_later(self):
        for d in I.REGISTER["devices"]:
            for v in ("touch", "non_touch"):
                e = d["emulator"][v]
                if e: self.assertTrue(os.path.isdir(os.path.join(ROOT, "web", "emulators", e)), (d["id"], v, e))
                elif d[v] and d["section"] <= 3: self.fail(f"{d['id']}.{v} belongs to a built section and needs an emulator")


class Choosing(unittest.TestCase):
    def test_order_and_examples(self):
        self.assertEqual(I.choose({})["interface"], "universal")
        self.assertEqual(I.choose({"os_class": "phone", "touch": True, "width": 390}), {"interface": "phone.touch", "class": "phone", "rule": "reported"})
        self.assertEqual(I.choose({"registered": {"device": "kitchen-screen", "version": "non_touch"}, "touch": True})["interface"], "tv.remote")
        self.assertEqual(I.choose({"override": "computer.pointer", "registered": {"device": "pos-terminal", "version": "touch"}})["rule"], "override")
        self.assertEqual(I.choose({"os_class": "car", "touch": True})["interface"], "car.voice")
        self.assertEqual(I.choose({"os_class": "desktop", "touch": True, "fine": True, "width": 1280, "last_input": "mouse"})["interface"], "computer.pointer")
        self.assertEqual(I.choose({"os_class": "desktop", "touch": True, "fine": True, "width": 1280, "last_input": "touch"})["interface"], "computer.touch")
        self.assertEqual(I.choose({"no_apps": True})["interface"], "phone.text")
        self.assertFalse(I.safe_to_switch("signature")); self.assertTrue(I.safe_to_switch(None))

    def test_never_the_browser_name(self):
        src = open(os.path.join(ROOT, "core", "interfaces.py")).read() + open(os.path.join(ROOT, "ts", "src", "interfaces.ts")).read()
        self.assertNotIn("userAgent", src); self.assertNotIn("user_agent", src)

    def test_vectors_current(self):
        r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "interfaces_vectors.py"), "--check"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


if __name__ == "__main__": unittest.main()


class Tokens(unittest.TestCase):
    def test_every_device_class_has_its_type_scale_in_the_tokens(self):
        t = json.load(open(os.path.join(ROOT, "design", "tokens.v1.json"), encoding="utf-8"))["fonts"]["device_classes"]
        self.assertEqual(set(t), set(I.REGISTER["classes"]))
        self.assertGreater(t["tv"]["min_text_px"], t["phone"]["min_text_px"])           # read from across the room
        css = open(os.path.join(ROOT, "design", "generated", "tokens.css"), encoding="utf-8").read()
        for c in t: self.assertIn(f'[data-device-class="{c}"]', css)


class KeyMeanings(unittest.TestCase):
    """Each key means the same on every device (DEVICE 48.17): its word exists in the shared device words and every
    language, and its colour is a real token."""
    def test_keys_have_words_and_colours(self):
        en = json.load(open(os.path.join(ROOT, "web", "pos", "strings.en.json"), encoding="utf-8"))
        tokens = json.dumps(json.load(open(os.path.join(ROOT, "design", "tokens.v1.json"), encoding="utf-8")))
        for key, k in I.REGISTER["keys"].items():
            self.assertIn(k["label_key"], en, key)
            if "colour_token" in k:
                self.assertIn(f'"{k["colour_token"]}"', tokens, key)
        self.assertEqual(set(I.REGISTER["keys"]) & {"confirm", "cancel", "clear"}, {"confirm", "cancel", "clear"})
