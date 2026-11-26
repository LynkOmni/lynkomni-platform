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
                        if key.startswith("pin:"):
                            pg.click('[data-act="pin:ok"]')
                        self.assertEqual(pg.locator(PAD).count(), 0, "the chosen screen opens after the PIN")
                        self.assertGreater(pg.locator('[data-act="gate:lock"]').count(), 0, "the screen shows who is serving with Lock")
                pg.close()
            b.close()


if __name__ == "__main__":
    unittest.main()
