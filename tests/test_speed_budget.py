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
    def test_first_screen_and_first_tap_within_budget_on_a_slow_cpu(self):
        with sync_playwright() as p:
            b = p.chromium.launch()
            for emulator, cfg in BUDGETS["emulators"].items():
                pg = b.new_page(viewport={"width": 390, "height": 844}, reduced_motion="reduce")
                cdp = pg.context.new_cdp_session(pg)
                cdp.send("Emulation.setCPUThrottlingRate", {"rate": BUDGETS["cpu_slowdown"]})
                pg.goto("file://" + os.path.join(DIST, f"lynkomni-{emulator}.html"))
                pg.wait_for_selector("html[data-ready]", state="attached")   # the app has unpacked its data and drawn its first screen (web/build.mjs)
                first = pg.evaluate("window.__readyAt")
                self.assertLessEqual(first, budget(emulator, "first_screen_ms"), f"{emulator}: first screen took {first:.0f} ms")
                nodes = pg.evaluate("(r) => document.querySelector(r).querySelectorAll('*').length", budget(emulator, "root"))
                self.assertLessEqual(nodes, budget(emulator, "dom_nodes"), f"{emulator}: {nodes} nodes on the first screen")
                tap = pg.evaluate("""(sel) => new Promise((done) => { const t0 = performance.now(); document.querySelector(sel).click(); requestAnimationFrame(() => requestAnimationFrame(() => done(performance.now() - t0))); })""", cfg["first_tap"])
                self.assertLessEqual(tap, budget(emulator, "tap_ms"), f"{emulator}: the first tap took {tap:.0f} ms")
                pg.close()
            b.close()


if __name__ == "__main__":
    unittest.main()
