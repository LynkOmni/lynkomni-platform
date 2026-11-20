"""Every sound and vibration can be switched off, the choice is remembered and followed everywhere, and only security and
safety alerts always sound (owner rule 2026-11-20; catalog/sounds.v1.json)."""
import json, os, re, unittest
from core import build_sections
from services import notify_settings as ns
from services.messages import KINDS

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REG = json.load(open(os.path.join(ROOT, "catalog", "sounds.v1.json"), encoding="utf-8"))
EMU = os.path.join(ROOT, "web", "emulators")
PLAYS = re.compile(r"\b(playSound|AudioContext|speechSynthesis|feelFor|new EmKit)\b")
REMEMBERS = re.compile(r"soundprefs\.js|from \"\.\./\.\./\.\./ts/src/emkit\.js\"")


def emulators():
    return sorted(d for d in os.listdir(EMU) if os.path.isfile(os.path.join(EMU, d, "app.ts")))


class Register(unittest.TestCase):
    def test_every_source_has_a_switch_and_a_place_in_the_build(self):
        order = [str(s) for s in build_sections.ORDER]
        for s in REG["sources"]:
            self.assertTrue(s["switch"] and s["controls"] and s["what"], s["id"])
            self.assertIn(str(s["build_section"]), order, s["id"])
            self.assertIn(s["status"], ("built", "planned"), s["id"])
            if not s["can_turn_off"]:
                self.assertIn(s.get("area"), REG["person"]["never_silenced"], f"{s['id']}: only security and safety may always sound")
            for e in s["emulators"]:
                self.assertIn(e, emulators(), f"{s['id']}: no emulator {e}")

    def test_every_page_that_makes_a_sound_is_registered_and_remembers_the_choice(self):
        listed = {e for s in REG["sources"] if s["status"] == "built" for e in s["emulators"]}
        for e in emulators():
            src = open(os.path.join(EMU, e, "app.ts"), encoding="utf-8").read()
            if PLAYS.search(src):
                self.assertIn(e, listed, f"{e} makes a sound: add it to catalog/sounds.v1.json with its switch")
                self.assertRegex(src, REMEMBERS, f"{e} must follow and remember the person's choice (ts/src/soundprefs.ts)")

    def test_the_shared_device_kit_remembers_the_choice(self):
        src = open(os.path.join(ROOT, "ts", "src", "emkit.ts"), encoding="utf-8").read()
        self.assertIn("loadPrefs()", src)
        self.assertIn("savePrefs(", src)

    def test_it_is_a_rule_for_all_services(self):
        u = json.load(open(os.path.join(ROOT, "catalog", "universal.v1.json"), encoding="utf-8"))
        self.assertIn("sound_switches", {e["id"] for e in u["everywhere"]})


class PersonSetting(unittest.TestCase):
    def setUp(self):
        self.s = ns.Settings(notifier=None)

    def test_defaults_and_changes(self):
        self.assertEqual(self.s.sounds("p1"), REG["person"]["settings"])
        self.s.set_sounds("p1", tones=False, volume="low")
        self.assertEqual(self.s.sounds("p1")["tones"], False)
        self.assertEqual(self.s.sounds("p1")["volume"], "low")
        with self.assertRaises(ValueError):
            self.s.set_sounds("p1", volume="loud")
        with self.assertRaises(ValueError):
            self.s.set_sounds("p1", ringtone=True)

    def test_security_and_safety_always_sound(self):
        self.s.set_sounds("p1", notification_sounds=False)
        locked = [k for k, v in KINDS.items() if v["area"] in ns.NEVER_SILENCED]
        other = [k for k, v in KINDS.items() if v["area"] not in ns.NEVER_SILENCED]
        self.assertTrue(locked and other)
        for k in locked:
            self.assertTrue(self.s.alert_sounds("p1", k), k)
        for k in other:
            self.assertFalse(self.s.alert_sounds("p1", k), k)

    def test_shared_devices_follow_the_manager_and_the_person_where_allowed(self):
        self.s.set_sounds("p1", tones=False, vibration=False, volume="high")
        allowed = {"tones": True, "vibration": True, "volume": "medium", "user_may_change": True}
        t = self.s.device_tones("p1", allowed)
        self.assertEqual((t["tones"], t["vibration"], t["volume"]), (False, False, "high"))
        locked = dict(allowed, user_may_change=False)
        self.assertTrue(self.s.device_tones("p1", locked)["tones"])
        self.assertTrue(self.s.device_tones("p1", allowed, customer_facing=True)["tones"])
        self.s.set_sounds("p1", tones=True)
        self.assertFalse(self.s.device_tones("p1", allowed, quiet_hours=True)["tones"])


if __name__ == "__main__":
    unittest.main()
