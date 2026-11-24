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
    shifts: dict = {}
    TRIES = 3     # a shared test machine is sometimes busy for a moment: the fastest of three fresh loads counts (owner, 2026-11-19)

    def measure(self, b, emulator, cfg):
        """One fresh load on the four-times-slower CPU: first screen, nodes on it and the first tap."""
        pg = b.new_page(viewport={"width": 390, "height": 844}, reduced_motion="reduce")
        cdp = pg.context.new_cdp_session(pg)
        cdp.send("Emulation.setCPUThrottlingRate", {"rate": BUDGETS["cpu_slowdown"]})
        # nothing jumps while the screen loads (INTERFACE UPDATE 73.8): every layout shift not caused by a tap is added up
        pg.add_init_script("window.__shift = 0; new PerformanceObserver((l) => { for (const e of l.getEntries()) if (!e.hadRecentInput) window.__shift += e.value; }).observe({ type: 'layout-shift', buffered: true });")
        pg.goto("file://" + os.path.join(DIST, f"lynkomni-{emulator}.html"))
        pg.wait_for_selector("html[data-ready]", state="attached")   # the app has unpacked its data and drawn its first screen (web/build.mjs)
        first = pg.evaluate("window.__readyAt")
        nodes = pg.evaluate("(r) => document.querySelector(r).querySelectorAll('*').length", budget(emulator, "root"))
        pg.wait_for_timeout(2000)
        shift = pg.evaluate("window.__shift")
        self.shifts[emulator] = min(self.shifts.get(emulator, shift), shift)   # like the times: the best of the fresh loads counts; a real jump fails every load
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
        for emulator, shift in self.shifts.items():
            self.assertLessEqual(shift, budget(emulator, "layout_shift_max"), f"{emulator}: the screen moved while loading (layout shift {shift:.3f})")


class TimeToSkeleton(unittest.TestCase):
    """PLACEHOLDER UPDATE 83 (row 83.6): on a first open, nothing new shows before 300 ms and the shape-matched skeleton is up soon
    after; a page with its own First open box (pageWaiting) and a device with the kit (emkit) are both measured."""
    KIT, OWN, SHELL = '[data-kit="firstopen"]', '[data-ctl="firstopen"]', "#cFirst"
    PAGES = {"counter-tablet": KIT, "kitchen-screen": KIT, "rider-phone": KIT, "stock-scanner": KIT, "lynk-kiosk": KIT, "lynk-dscreen": KIT,
             "lynk-cdisplay": KIT, "customer-display": KIT, "track-page": OWN, "queue-page": OWN, "survey-page": OWN, "vcard-card": OWN,
             "owner-web": OWN, "browser-frame": SHELL, "account-site": SHELL}
    # first screen is sign-in, with nothing to load: the POS terminal, the betting counter (v0.97.1) and the Business app wait on every screen after it (checked
    # by the fit guard with First open); the button phone and the mesh relay never wait (catalog/placeholders.v1.json waits)
    NOT_HERE = {"pos-terminal", "bet-counter", "merchant-phone", "button-phone", "mesh-relay"}

    def test_every_page_is_measured_or_says_why_not(self):
        built = {f[len("lynkomni-"):-len(".html")] for f in os.listdir(DIST) if f.startswith("lynkomni-") and f.endswith(".html")}
        self.assertEqual(built - set(self.PAGES) - self.NOT_HERE, set())
    SLACK_MS = 400

    @unittest.skipIf(sync_playwright is None, "playwright is not installed")
    def test_the_skeleton_waits_300_ms_and_then_comes_quickly(self):
        timing = json.load(open(os.path.join(ROOT, "catalog", "placeholders.v1.json"), encoding="utf-8"))["timing_ms"]
        with sync_playwright() as p:
            b = p.chromium.launch()
            for emulator, box in self.PAGES.items():
                pg = b.new_page(viewport={"width": 1280, "height": 900})
                pg.goto("file://" + os.path.join(DIST, f"lynkomni-{emulator}.html"))
                pg.wait_for_selector("html[data-ready]", state="attached")
                got = pg.evaluate("""(sel) => new Promise((done) => {
                    const t0 = performance.now(); let early = false;
                    document.querySelector(sel).click();
                    const check = () => {
                        const dt = performance.now() - t0, sk = document.querySelector('.skeleton');
                        if (sk && dt < 250) early = true;
                        if (sk || dt > 3000) done({ at: sk ? dt : -1, early }); else requestAnimationFrame(check);
                    };
                    requestAnimationFrame(check);
                })""", box)
                self.assertFalse(got["early"], f"{emulator}: the skeleton showed before {timing['show_after']} ms")
                self.assertGreaterEqual(got["at"], timing["show_after"] - 50, f"{emulator}: no skeleton, or too early ({got['at']:.0f} ms)")
                self.assertLessEqual(got["at"], timing["show_after"] + self.SLACK_MS, f"{emulator}: the skeleton took {got['at']:.0f} ms")
                pg.close()
            b.close()


if __name__ == "__main__":
    unittest.main()
