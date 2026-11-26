"""The review panel never skips the staff PIN (owner, 2026-11-26), and every screen opened with a PIN shows who is serving with
Lock (owner, 2026-11-25). For every staff device emulator with screen buttons, in a real browser: from the lock screen each screen
button keeps the PIN pad on screen (with the sample duress PIN), the sample PIN then opens the chosen screen, and that screen has
Lock. Runs in the browser (CI layout job, part 3)."""
import os
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST = os.path.join(ROOT, "web", "emulators", "dist")
try:
    from playwright.sync_api import sync_playwright
except ImportError:  # pragma: no cover
    sync_playwright = None

# device: (the sample PIN of the first person, how its pad's keys are named)
DEVICES = {
    "counter-tablet": ("1234", "d{}"),
    "stock-scanner": ("2468", "pin:{}"),
    "rider-phone": ("1357", "pin:{}"),
    "kitchen-screen": ("3691", "pin:{}"),
    "bet-counter": ("1234", "pin:{}"),
}
# Buttons that only lock, pick a person or ask for the duress PIN; a manager's approval pad is its own screen.
NOT_A_SCREEN = {"locked", "lock_screen", "pick_staff", "duress", "approve_second"}
# On the kitchen screen's Free plan the orders print on paper and nobody uses the screen, so there is nothing to sign in to.
NO_SCREEN_IN_USE = {("kitchen-screen", "printed")}
PAD = '[data-act^="pin:"], [data-act="d1"]'


@unittest.skipIf(sync_playwright is None, "needs the browser (CI layout job)")
class PanelNeverSkipsThePin(unittest.TestCase):
    def test_every_screen_button_waits_for_the_pin_and_shows_lock(self):
        with sync_playwright() as p:
            b = p.chromium.launch()
            for name, (pin, key) in DEVICES.items():
                pg = b.new_page(viewport={"width": 1280, "height": 900}, reduced_motion="reduce")
                pg.goto("file://" + os.path.join(DIST, f"lynkomni-{name}.html"))
                if pg.locator('[data-act="localeok"]').count():
                    pg.click('[data-act="localeok"]')
                states = [s for s in pg.eval_on_selector_all("#stateButtons [data-state]", "els => els.map(e => e.dataset.state)") if s not in NOT_A_SCREEN and (name, s) not in NO_SCREEN_IN_USE]
                self.assertTrue(states, name)
                for state in states:
                    with self.subTest(device=name, screen=state):
                        lock = pg.locator('#stateButtons [data-state="lock_screen"], #stateButtons [data-state="locked"]')
                        lock.first.click()
                        pg.click(f'#stateButtons [data-state="{state}"]')
                        self.assertGreater(pg.locator(PAD).count(), 0, "the PIN is asked first")
                        self.assertGreater(pg.locator("text=8642").count(), 0, "the sample duress PIN is shown on the lock")
                        for d in pin:
                            pg.click(f'[data-act="{key.format(d)}"]')
                        self.assertEqual(pg.locator('[data-act="pin:ok"]').count(), 0, "a full PIN is checked at once, without OK")
                        self.assertEqual(pg.locator(PAD).count(), 0, "the chosen screen opens after the PIN")
                        self.assertGreater(pg.locator('[data-act="gate:lock"]').count(), 0, "the screen shows who is serving with Lock")
                pg.close()
            b.close()


LOCKS = {"stock-scanner": "lock_screen", "rider-phone": "lock_screen", "kitchen-screen": "lock_screen", "bet-counter": "lock_screen", "counter-tablet": "locked"}
DOTS = ".pinpad .pdot, .lock .dots i"
LANG = '#cLang, select[data-ctl="lang"]'
KEYS_FIT = """() => { const k = document.querySelector('.pinpad .pkeys') || document.querySelector('.lock .soft');
  let b = k.parentElement; while (b && !/(auto|scroll|hidden)/.test(getComputedStyle(b).overflowY)) b = b.parentElement;
  return !b || k.getBoundingClientRect().bottom <= b.getBoundingClientRect().bottom + 0.5; }"""


@unittest.skipIf(sync_playwright is None, "needs the browser (CI layout job)")
class PinPadsFitAndStopAtTheLength(unittest.TestCase):
    """Owner, 2026-11-26: a 4-digit PIN showed more dots with every press and the scanner cut off its last row of keys. Every lock
    shows exactly as many dots as the person's PIN has digits, takes no digit more (it checks once full) and keeps all its keys
    on screen, at phone and computer size, in long text, upright and turned."""
    def test_every_lock_stops_at_the_pin_length_and_fits(self):
        with sync_playwright() as p:
            b = p.chromium.launch()
            for width in (390, 1280):
                for name, state in LOCKS.items():
                    pin, key = DEVICES[name]
                    pg = b.new_page(viewport={"width": width, "height": 844}, reduced_motion="reduce")
                    pg.set_default_timeout(8000)
                    pg.goto("file://" + os.path.join(DIST, f"lynkomni-{name}.html"))
                    if pg.locator('[data-act="dsh:localeok"]').count():
                        pg.click('[data-act="dsh:localeok"]')
                    for lang in ("en", "xx"):
                        pg.select_option(LANG, lang)
                        shapes = [None] + (["sideways"] if pg.locator('#cSize option[value="sideways"]').count() else [])
                        for shape in shapes:
                            with self.subTest(device=name, width=width, lang=lang, shape=shape or "upright"):
                                if shape:
                                    pg.select_option("#cSize", shape)
                                pg.click(f'#stateButtons [data-state="{state}"]')
                                pg.wait_for_timeout(120)
                                self.assertEqual(pg.locator(DOTS).count(), len(pin), "one dot for each digit of the PIN")
                                self.assertTrue(pg.evaluate(KEYS_FIT), "every key of the PIN pad is on screen")
                            if shape:
                                pg.select_option("#cSize", "upright" if pg.locator('#cSize option[value="upright"]').count() else pg.eval_on_selector("#cSize option", "o => o.value"))
                    with self.subTest(device=name, width=width, typed="one digit too many"):
                        pg.select_option(LANG, "en")
                        pg.click(f'#stateButtons [data-state="{state}"]')
                        wrong = "9" * (len(pin) - 1)
                        for d in wrong:
                            pg.click(f'[data-act="{key.format(d)}"]')
                        self.assertEqual(pg.locator(".pdot.on, .lock .dots i.on").count(), len(pin) - 1)
                        pg.click(f'[data-act="{key.format("8")}"]')   # the last digit: checked at once (a wrong PIN here)
                        self.assertEqual(pg.locator(".pdot.on, .lock .dots i.on").count(), 0, "a full PIN is checked at once and never takes a digit more")
                    pg.close()
            b.close()


if __name__ == "__main__":
    unittest.main()
