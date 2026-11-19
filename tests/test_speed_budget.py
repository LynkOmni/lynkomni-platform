"""Speed budget per screen (blueprint 45 E, build section 1): every emulator's offline file stays within its size budget, shows
its first screen and answers a tap within the time budget on a four-times-slower CPU, and keeps its screens light.
Playwright with Chromium is needed for the timing part; the size part always runs."""
import json, os, unittest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUDGETS = json.load(open(os.path.join(ROOT, "web", "budgets.v1.json"), encoding="utf-8"))
DIST = os.path.join(ROOT, "web", "emulators", "dist")
try:
    from playwright.sync_api import sync_playwright
except ImportError:          # pragma: no cover
    sync_playwright = None


def budget(emulator, key):
    return BUDGETS["emulators"].get(emulator, {}).get(key, BUDGETS["defaults"][key])


class SizeBudget(unittest.TestCase):
    def test_every_built_emulator_is_within_its_size_budget(self):
        for emulator in BUDGETS["emulators"]:
            path = os.path.join(DIST, f"lynkomni-{emulator}.html")
            self.assertTrue(os.path.isfile(path), f"run node web/build.mjs for {emulator}")
            kb = os.path.getsize(path) / 1024
            self.assertLessEqual(kb, budget(emulator, "file_kb"), f"{emulator}: {kb:.0f} KB is over its {budget(emulator, 'file_kb')} KB budget")

    def test_every_emulator_has_a_budget(self):
        built = {f[len("lynkomni-"):-len(".html")] for f in os.listdir(DIST) if f.endswith(".html")}
        self.assertEqual(built, set(BUDGETS["emulators"]), "every emulator needs a speed budget in web/budgets.v1.json")


@unittest.skipUnless(sync_playwright, "Playwright with Chromium is needed")
class TimeBudget(unittest.TestCase):
    TRIES = 3     # a shared test machine is sometimes busy for a moment: the fastest of three fresh loads counts (owner, 2026-11-19)

    def measure(self, b, emulator, cfg):
        """One fresh load on the four-times-slower CPU: first screen, nodes on it and the first tap."""
        pg = b.new_page(viewport={"width": 390, "height": 844}, reduced_motion="reduce")
        cdp = pg.context.new_cdp_session(pg)
        cdp.send("Emulation.setCPUThrottlingRate", {"rate": BUDGETS["cpu_slowdown"]})
        pg.goto("file://" + os.path.join(DIST, f"lynkomni-{emulator}.html"))
        pg.wait_for_selector("html[data-ready]", state="attached")   # the app has unpacked its data and drawn its first screen (web/build.mjs)
        first = pg.evaluate("window.__readyAt")
        nodes = pg.evaluate("(r) => document.querySelector(r).querySelectorAll('*').length", budget(emulator, "root"))
        tap = pg.evaluate("""(sel) => new Promise((done) => { const t0 = performance.now(); document.querySelector(sel).click(); requestAnimationFrame(() => requestAnimationFrame(() => done(performance.now() - t0))); })""", cfg["first_tap"])
        pg.close()
        return first, nodes, tap

    def test_first_screen_and_first_tap_within_budget_on_a_slow_cpu(self):
        """The budgets never change to make a run pass. A real slowdown fails all three loads; a busy moment on the test machine
        fails only one (twice on 19 November LynkPOS took about 1.6 s once and well under 1.5 s when run again)."""
        with sync_playwright() as p:
            b = p.chromium.launch()
            for emulator, cfg in BUDGETS["emulators"].items():
                runs = []
                for _ in range(self.TRIES):
                    runs.append(self.measure(b, emulator, cfg))
                    first, nodes, tap = runs[-1]
                    if first <= budget(emulator, "first_screen_ms") and tap <= budget(emulator, "tap_ms"):
                        break
                self.assertLessEqual(runs[-1][1], budget(emulator, "dom_nodes"), f"{emulator}: {runs[-1][1]} nodes on the first screen")
                firsts, taps = [r[0] for r in runs], [r[2] for r in runs]
                self.assertLessEqual(min(firsts), budget(emulator, "first_screen_ms"), f"{emulator}: first screen took {', '.join(f'{x:.0f}' for x in firsts)} ms in {len(runs)} loads")
                self.assertLessEqual(min(taps), budget(emulator, "tap_ms"), f"{emulator}: the first tap took {', '.join(f'{x:.0f}' for x in taps)} ms in {len(runs)} loads")
            b.close()

if __name__ == "__main__":
    unittest.main()
