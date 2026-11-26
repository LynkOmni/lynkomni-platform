"""Nothing is cut, squeezed or blocked on any emulator, at any size (owner report 2026-11-19, two phone screenshots: the Account
side menu's labels were cut on a tablet, the owner's "Is this right?" card looked cut off on the laptop, and the laptop screen
ignored mouse clicks). For every emulator in web/emulators/dist, at every size it offers and in the light and dark theme:

- menus: every menu item keeps its full height (a long menu scrolls, it never squeezes), its label is never cut sideways, and no
  item hangs outside a menu that cannot scroll;
- pop-ups: every open dialog or sheet sits fully inside its screen; on anything wider than a phone it does not touch the
  screen's edges (a phone slides its sheet up from the bottom edge); its first button can really be pressed;
- input: a screen that has a mouse, trackpad, stylus or touch takes clicks and taps (only buttons-only screens ignore them).
- space: tick choices that wrap line up in columns with no extra space between rows; menu and list rows sit no further apart
  than a comfortable tap needs; the account menu never runs the name and the LynkOmni ID together.

Needs Playwright with Chromium (installed in CI's layout job); skipped where it is missing."""
import glob, os, unittest

from tests.staff_pin import sign_in
from core import names as _names

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST = os.path.join(ROOT, "web", "emulators", "dist")
# CI runs this check in all 8 parts of the layout job at once (LAYOUT_SHARD="k/n", k from 1): each part takes every n-th
# emulator, so every emulator is still checked once in every run; the signed-in Business app runs in part 3 (section 4 part 1c).
# Without the variable, everything runs here.
_K, _N = (int(x) for x in os.environ.get("LAYOUT_SHARD", "1/1").split("/"))
SIGNED_IN_PART = min(3, _N)


def mine(files):
    """This part's share of the emulators: every n-th file of the sorted list."""
    return [f for i, f in enumerate(sorted(files)) if i % _N == _K - 1]
try:
    from playwright.sync_api import sync_playwright
except ImportError:          # pragma: no cover
    sync_playwright = None

SETTLE = "() => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)))"
SIZE_CONTROLS = ("#cSize", "#cView")                 # the emulator panel's size or view choice, where an emulator has one
PANELS = ("first", "search", "help", "account", "sync", "bell")
SHELL_OVERLAYS = ("launcher", "account", "globe", "search", "help", "bell", "sync")

VISIBLE = """const shown = (e) => { if (!e || !e.getClientRects().length) return false; const cs = getComputedStyle(e);
  return cs.display !== 'none' && cs.visibility !== 'hidden'; };
const name = (e) => ((e.innerText || e.getAttribute('aria-label') || e.className || e.tagName) + '').trim().replace(/\\s+/g, ' ').slice(0, 40);"""

MENUS = "() => {" + VISIBLE + """
  const bad = [];
  for (const el of document.querySelectorAll('.shell-nav .navitem, .rail button, nav.side button, .tabbar button')) {
    if (!shown(el)) continue;
    if (el.scrollHeight > el.clientHeight + 1) bad.push('menu item squeezed: ' + name(el));
    const lab = el.querySelector('.nlabel') || el;
    if (lab.scrollWidth > lab.clientWidth + 1) bad.push('menu label cut sideways: ' + name(el));
    const nav = el.closest('.shell-nav, .rail, nav.side, .tabbar');
    if (nav && !/(auto|scroll)/.test(getComputedStyle(nav).overflowY)) {
      const n = nav.getBoundingClientRect(), r = el.getBoundingClientRect();
      if (r.bottom > n.bottom + 1 || r.top < n.top - 1) bad.push('menu item outside a menu that cannot scroll: ' + name(el));
    }
  }
  return [...new Set(bad)];
}"""

DIALOGS = "() => {" + VISIBLE + """
  const bad = [];
  const SEL = '.dsh-panel, .overlay > *, [role="dialog"]:not(.dsh-locale)';
  for (const el of document.querySelectorAll(SEL)) {
    if (!shown(el) || (el.parentElement && el.parentElement.closest(SEL))) continue;   // the outer pop-up only; what is inside it scrolls
    const root = el.closest('[data-device-class]') || el.closest('#display, #screen');
    if (!root) continue;
    const s = root.getBoundingClientRect(), r = el.getBoundingClientRect(), cls = root.dataset.deviceClass || '';
    const k = root.offsetHeight ? s.height / root.offsetHeight : 1;      // a screen drawn smaller to fit the page
    if (r.top < s.top - 1 || r.bottom > s.bottom + 1 || r.left < s.left - 1 || r.right > s.right + 1) bad.push('dialog outside its screen: ' + name(el));
    const drawer = r.height >= s.height - 2;                  // a side drawer runs the full height on purpose
    const phone = !cls || cls === 'phone' || cls === 'watch';
    if (!phone && !drawer && (s.bottom - r.bottom) / k < 6) bad.push('dialog glued to the bottom edge on a ' + cls + ': ' + name(el));
    const inView = (x) => { const q = x.getBoundingClientRect(); return q.height > 0 && q.top >= r.top && q.bottom <= r.bottom; };
    for (const b of [...el.querySelectorAll('button')].filter((x) => shown(x) && inView(x))) {
      let q = b.getBoundingClientRect();
      if (q.top < 0 || q.bottom > innerHeight) { window.scrollBy(0, q.top - innerHeight / 2); q = b.getBoundingClientRect(); }   // the page only, never the screen
      const hit = document.elementFromPoint(q.left + q.width / 2, q.top + q.height / 2);
      if (!hit || !(hit === b || b.contains(hit))) bad.push('dialog button covered or blocked: ' + name(b));
    }
  }
  return [...new Set(bad)];
}"""

# A button never touches the text right above or below it (owner report 2026-11-19: the newsletter's agreement line, Subscribe
# button and note were stuck together, and so were the sign-in buttons and their notes): at least 4 px between them.
CROWD = r"""() => {
  const bad = new Set();
  const shown = (e) => e && e.getClientRects().length && getComputedStyle(e).visibility !== 'hidden';
  for (const b of document.querySelectorAll('button, [role="button"]')) {
    if (!shown(b)) continue;
    const root = b.closest('[data-device-class]') || b.closest('#display, #screen'); if (!root) continue;
    const k = root.offsetHeight ? root.getBoundingClientRect().height / root.offsetHeight : 1;
    const r = b.getBoundingClientRect(); if (r.height < 20) continue;
    for (const sib of [b.previousElementSibling, b.nextElementSibling]) {
      if (!sib || !shown(sib) || sib.matches('button, [role="button"], input, select, textarea, script, style')) continue;
      if (!(sib.textContent || '').trim()) continue;
      const s = sib.getBoundingClientRect();
      const overlapX = Math.min(r.right, s.right) - Math.max(r.left, s.left) > 0;
      if (!overlapX) continue;
      const gap = (s.top >= r.bottom ? s.top - r.bottom : r.top >= s.bottom ? r.top - s.bottom : -1) / k;
      if (gap >= 0 && gap < 4) bad.add('button touches text: "' + (b.innerText || '').trim().slice(0, 25) + '" / "' + (sib.innerText || '').trim().slice(0, 25) + '"');
    }
  }
  return [...bad];
}"""

# No space that is not needed (owner report 2026-11-19, a phone screenshot of the newsletter's topics: "Avoid unnecessary empty
# space around menus, topics"): a group of tick choices that wraps lines its choices up in columns with no extra space between
# the rows; menu and list rows sit no further apart than a comfortable tap needs; the account menu's name and LynkOmni ID never
# run together on one line. Every item keeps its full tap size.
SPACE = """() => {
  const bad = new Set();
  const shown = (e) => e && e.getClientRects().length && getComputedStyle(e).visibility !== 'hidden' && getComputedStyle(e).display !== 'none';
  const name = (e) => ((e.innerText || e.getAttribute('aria-label') || e.className || e.tagName) + '').trim().replace(/\\s+/g, ' ').slice(0, 30);
  const scale = (e) => { const root = e.closest('[data-device-class]') || e.closest('#display, #screen'); return root && root.offsetHeight ? root.getBoundingClientRect().height / root.offsetHeight : 1; };
  const rowsOf = (rs) => { const rows = []; for (const r of rs) { const row = rows.find((x) => Math.abs(x.top - r.top) < 3); if (row) row.items.push(r); else rows.push({ top: r.top, items: [r] }); } return rows.sort((a, b) => a.top - b.top); };
  for (const g of document.querySelectorAll('fieldset, [role="group"], [role="radiogroup"]')) {
    if (!shown(g) || g.closest('.panel')) continue;
    const items = [...g.children].filter((c) => shown(c) && c.matches('label') && c.querySelector('input[type="checkbox"], input[type="radio"]'));
    if (items.length < 3) continue;
    const k = scale(g), rows = rowsOf(items.map((c) => c.getBoundingClientRect()));
    if (rows.length > 1 && rows[0].items.length > 1) {
      const lefts = rows[0].items.map((r) => r.left);
      if (rows.slice(1).some((row) => row.items.some((r) => !lefts.some((l) => Math.abs(l - r.left) < 3)))) bad.add('choices not lined up in columns: ' + name(g));
    }
    for (let i = 1; i < rows.length; i++) {
      if ((rows[i].top - Math.max(...rows[i - 1].items.map((r) => r.bottom))) / k > 8) { bad.add('extra space between choices: ' + name(g)); break; }
    }
  }
  const filled = (el) => {          // what a row really holds: its tap areas, words and pictures (a tap area keeps its full size)
    let top = Infinity, bottom = -Infinity;
    const take = (q) => { if (q.height > 0) { top = Math.min(top, q.top); bottom = Math.max(bottom, q.bottom); } };
    if (el.matches('a, button, label, [role="button"]')) take(el.getBoundingClientRect());
    el.querySelectorAll('a, button, label, input, select, svg, img').forEach((x) => { if (shown(x)) take(x.getBoundingClientRect()); });
    const w = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
    while (w.nextNode()) { if (!(w.currentNode.textContent || '').trim()) continue; const r = document.createRange(); r.selectNodeContents(w.currentNode); [...r.getClientRects()].forEach(take); }
    return bottom > top ? bottom - top : 0;
  };
  for (const list of document.querySelectorAll('.mlist, .lgrid, .shell-nav, nav.side, .fcol ul, .fpays')) {
    if (!shown(list) || list.closest('.panel')) continue;
    const k = scale(list), items = [...list.children].filter((i) => shown(i) && i.matches('li, a, button, label'));
    const rows = rowsOf(items.map((i) => Object.assign(i.getBoundingClientRect().toJSON(), { el: i })));
    for (let i = 1; i < rows.length; i++) {
      const space = (rows[i].top - rows[i - 1].top - Math.max(...rows[i - 1].items.map((r) => filled(r.el)))) / k;
      if (space > 12) { bad.add('menu rows too far apart (' + Math.round(space) + ' px empty): ' + name(rows[i - 1].items[0].el)); break; }
    }
  }
  for (const who of document.querySelectorAll('.who')) {
    const n = who.querySelector('strong'), id = who.querySelector('.lynkid');
    if (!shown(n) || !shown(id)) continue;
    const nr = n.getBoundingClientRect(), ir = id.getBoundingClientRect();
    if (ir.top < nr.bottom - 2 && ir.left >= nr.right - 1) bad.add('name and LynkOmni ID run together on one line');
  }
  return [...bad];
}"""

# Crowded areas and uneven spacing (owner, 2026-11-19: "not only crowded buttons but also crowded areas and uneven spacing"):
# two visibly bounded boxes (a border, a filled background or a shadow: cards, fields, panels, chips, filled buttons) never sit
# closer than 3.5 px, and a run of three or more repeated items of the same kind in one row or column has even gaps (a jump of
# 24 px or more is a deliberate section break).
AREAS = r"""() => {
  const crowded = new Set(), uneven = new Set();
  const roots = [...document.querySelectorAll('#screen, #display, #cscreen, #till, #screenA, #screenB, .lscreen')].filter((r) => r.getClientRects().length);
  const shown = (e) => e.getClientRects().length && getComputedStyle(e).visibility !== 'hidden' && getComputedStyle(e).display !== 'contents';
  const name = (e) => ((e.className && typeof e.className === 'string' ? '.' + e.className.split(' ')[0] : e.tagName.toLowerCase()) + ' "' + (e.innerText || e.getAttribute('aria-label') || '').trim().replace(/\s+/g, ' ').slice(0, 20) + '"');
  const isBox = (e) => {
    const cs = getComputedStyle(e);
    const r0 = e.getBoundingClientRect(); if (r0.width < 12 || r0.height < 12) return false;   // dots and tiny marks are decoration
    const border = ['Top', 'Right', 'Bottom', 'Left'].filter((s) => parseFloat(cs['border' + s + 'Width']) > 0 && cs['border' + s + 'Style'] !== 'none').length;
    const bg = cs.backgroundColor && !/rgba\(0, 0, 0, 0\)|transparent/.test(cs.backgroundColor);
    return border >= 3 || (bg && parseFloat(cs.borderRadius) > 0) || (cs.boxShadow && cs.boxShadow !== 'none');
  };
  for (const root of roots) {
    const k = root.offsetHeight ? root.getBoundingClientRect().height / root.offsetHeight : 1;
    for (const par of root.querySelectorAll('*')) {
      if (par.closest('svg, .keypad, .navpad, .seg, .segmented, table')) continue;
      const kids = [...par.children].filter((c) => shown(c) && !c.matches('script, style, br, .lname'));   // a marked name is part of the text, not a box
      if (kids.length < 2) continue;
      // crowded: two boxes next to each other with less than 4 px between them
      for (let i = 0; i + 1 < kids.length; i++) {
        const a = kids[i], b = kids[i + 1];
        if (!isBox(a) || !isBox(b)) continue;
        const r = a.getBoundingClientRect(), s = b.getBoundingClientRect();
        if (!r.width || !s.width) continue;
        const ox = Math.min(r.right, s.right) - Math.max(r.left, s.left), oy = Math.min(r.bottom, s.bottom) - Math.max(r.top, s.top);
        let gap = null;
        if (ox > 2 && oy <= 0) gap = Math.max(s.top - r.bottom, r.top - s.bottom);
        else if (oy > 2 && ox <= 0) gap = Math.max(s.left - r.right, r.left - s.right);
        if (gap !== null && gap / k < 3.5 && gap / k > -1) crowded.add('crowded: ' + name(a) + ' / ' + name(b) + ' (' + Math.round(gap / k) + ' px)');
      }
      // uneven: three or more repeated items of the same kind in one row or one column with different gaps
      let run = [kids[0]];
      const key = (c) => c.tagName + '|' + (typeof c.className === 'string' ? c.className.replace(/\b(current|active|on|selected)\b/g, '').trim() : '');
      const check = (items) => {
        if (items.length < 3) return;
        const rs = items.map((c) => c.getBoundingClientRect());
        const sameRow = rs.every((x) => Math.abs(x.top - rs[0].top) < 2), sameCol = rs.every((x) => Math.abs(x.left - rs[0].left) < 2);
        if (!sameRow && !sameCol) return;
        const gaps = [];
        for (let i = 0; i + 1 < rs.length; i++) gaps.push((sameCol ? rs[i + 1].top - rs[i].bottom : rs[i + 1].left - rs[i].right) / k);
        if (gaps.some((g) => g < -1)) return;
        const sorted = [...gaps].sort((a, b) => a - b), m = sorted[Math.floor(sorted.length / 2)];
        const odd = gaps.filter((g) => Math.abs(g - m) > 4 && g < m + 24);   // a jump of 24 px or more is a deliberate section break
        if (odd.length) uneven.add('uneven: ' + items.length + ' x ' + name(items[0]) + ' gaps ' + gaps.map(Math.round).join('/'));
      };
      for (let i = 1; i <= kids.length; i++) {
        if (i < kids.length && key(kids[i]) === key(run[0])) run.push(kids[i]);
        else { check(run); run = i < kids.length ? [kids[i]] : []; }
      }
    }
  }
  return [...crowded, ...uneven];
}"""

# Text never touches the edge of its screen (owner report 2026-11-21: the LynkPOS limit lines ran to the screen's edge): every
# line of text keeps at least 6 px from the screen's left and right edges, unless it sits in a row that scrolls or ends in an
# ellipsis on purpose.
EDGE = r"""() => {
  const out = new Set();
  const roots = [...document.querySelectorAll('#screen, #display, #cscreen, #till, #screenA, #screenB, .lscreen')].filter((r) => r.getClientRects().length);
  for (const root of roots) {
    const R = root.getBoundingClientRect(); const k = root.offsetWidth ? R.width / root.offsetWidth : 1;
    const w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    for (let n = w.nextNode(); n; n = w.nextNode()) {
      if (!n.data.trim()) continue;
      const el = n.parentElement; if (!el || el.closest('svg, script, style, [aria-hidden="true"], .sr')) continue;
      const cs = getComputedStyle(el); if (cs.visibility === 'hidden' || cs.display === 'none') continue;
      if ([el, ...(function* () { for (let a = el.parentElement; a && a !== root; a = a.parentElement) yield a; })()].some((a) => { const c = getComputedStyle(a); return c.textOverflow === 'ellipsis' || (c.overflowX !== 'visible' && a.scrollWidth > a.clientWidth + 1); })) continue;   // a row that scrolls or ends in an ellipsis on purpose
      const rg = document.createRange(); rg.selectNodeContents(n);
      for (const r of rg.getClientRects()) {
        if (!r.width || r.bottom < R.top || r.top > R.bottom) continue;
        const l = (r.left - R.left) / k, rt = (R.right - r.right) / k;
        if (l < 6 || rt < 6) out.add('edge: ' + (el.className && typeof el.className === 'string' ? '.' + el.className.split(' ')[0] : el.tagName.toLowerCase()) + ' "' + n.data.trim().slice(0, 30) + '" (' + Math.round(Math.min(l, rt)) + ' px)');
      }
    }
  }
  return [...out];
}"""

# Every button can be reached (owner report 2026-11-24: the LynkPOS "Send to the partner" button sat below the screen): a
# button, link or field whose label or icon lies outside its screen must sit in a part that scrolls to it.
CLIP = r"""() => {
  const out = new Set();
  const roots = [...document.querySelectorAll('#screen, #display, #cscreen, #till, #screenA, #screenB, .lscreen')].filter((r) => r.getClientRects().length);
  for (const root of roots) {
    const R = root.getBoundingClientRect();
    for (const el of root.querySelectorAll('button, a[href], input, select, textarea, [role="button"]')) {
      if (!el.getClientRects().length || el.closest('[aria-hidden="true"], [hidden], .dsh-scrim:empty')) continue;
      const cs = getComputedStyle(el); if (cs.visibility === 'hidden' || cs.display === 'none' || cs.position === 'fixed') continue;
      const rg = document.createRange(); rg.selectNodeContents(el); const c = rg.getBoundingClientRect();   // what the person sees: its label or icon, not the empty tap area around it
      const r = c.width && c.height ? c : el.getBoundingClientRect(); if (!r.width || !r.height) continue;
      if (r.top >= R.top - 1 && r.bottom <= R.bottom + 1 && r.left >= R.left - 1 && r.right <= R.right + 1) continue;
      let reach = false;
      for (let a = el.parentElement; a && a !== root.parentElement; a = a.parentElement) {
        const c = getComputedStyle(a);
        if ((/(auto|scroll)/.test(c.overflowY) && a.scrollHeight > a.clientHeight + 1) || (/(auto|scroll)/.test(c.overflowX) && a.scrollWidth > a.clientWidth + 1)) { reach = true; break; }
      }
      if (!reach) out.add('cut off: ' + (el.textContent.trim() || el.getAttribute('aria-label') || el.dataset.act || el.tagName).slice(0, 30));
    }
  }
  return [...out];
}"""

INPUT = """() => {
  const bad = [];
  for (const el of document.querySelectorAll('[data-interface]')) {
    const i = el.dataset.interface || '';
    if ((i.startsWith('computer.') || i.endsWith('.touch') || i === 'universal') && el.dataset.touch === 'no') bad.push('screen ignores clicks: ' + i);
  }
  return bad;
}"""

# Every Lynk name a screen shows carries its plain word (owner 2026-11-21, catalog/names.v1.json): each one sits inside the
# names part's mark (ts/src/names.ts), except on receipts, printed paper, the copyright line, typed text and code.
NAMES = r"""() => {
  const bad = new Set(), re = new RegExp('(?<![A-Za-z])(""" + "|".join(sorted(_names.BY_NAME, key=len, reverse=True)) + r""")(?![A-Za-z])', 'g');
  const roots = document.querySelectorAll('#screen, #display, #cscreen, #till, #screenA, #screenB, .display, .lscreen');
  const skip = 'script, style, code, pre, input, textarea, svg, title, .sr, #paper, .receipt, .rtext, .fcopy, .shortfoot, .lname, [data-lname], [data-names="off"]';
  const walk = (n) => {
    for (const c of n.childNodes) {
      if (c.nodeType === 3) {
        const p = c.parentElement; if (!p || !p.getClientRects().length || p.closest(skip)) continue;
        for (const m of (c.textContent || '').match(re) || []) bad.add(m + ' without its plain word');
      } else if (c.nodeType === 1) walk(c);
    }
  };
  roots.forEach(walk);
  return [...bad];
}"""


RAW = r"""() => {
  const bad = new Set(), re = /\b[a-z][a-z0-9]*(?:_[a-z0-9]+)+\b/g;
  const roots = document.querySelectorAll('#screen, #display, #cscreen, #till, #screenA, #screenB, .display, .lscreen');
  const walk = (n) => {
    for (const c of n.childNodes) {
      if (c.nodeType === 3) {
        const p = c.parentElement; if (!p || !p.getClientRects().length || p.closest('script, style, code, input, textarea, .sr')) continue;
        for (const m of (c.textContent || '').match(re) || []) bad.add(m);
      } else if (c.nodeType === 1) {
        walk(c);
        for (const a of ['aria-label', 'title', 'placeholder', 'alt']) { const v = c.getAttribute(a); if (v) for (const m of v.match(re) || []) bad.add(m + ' (' + a + ')'); }
      }
    }
  };
  roots.forEach(walk);
  return [...bad];
}"""


def _ci():
    with open(os.path.join(ROOT, ".github", "workflows", "ci.yml"), encoding="utf-8") as fh:
        return fh.read()


class BrowserTestsRun(unittest.TestCase):
    """A browser test skips itself where Chromium is missing, so it only protects anything if the layout job (which installs
    Chromium) runs it. Every test file that uses Playwright must be named in that job (the owner-web click bug of 2026-11-19
    sat in tests/test_device_shell.py, which no job with a browser ran)."""
    def test_every_browser_test_runs_in_the_layout_job(self):
        ci = _ci()
        for f in sorted(glob.glob(os.path.join(ROOT, "tests", "test_*.py"))):
            mod = os.path.basename(f)[:-3]
            with open(f, encoding="utf-8") as fh:
                uses_browser = "playwright" in fh.read()
            if uses_browser:
                self.assertIn(f"tests.{mod}", ci, f"{mod} uses a browser but no job with a browser runs it")

    def test_every_layout_part_has_a_time_limit(self):
        """A stuck part fails within minutes instead of blocking the merge for an hour (on 19 November one part hung for over an
        hour while setting up the test machine): the job and its set-up step each have a time limit (section 4 part 1c)."""
        ci = _ci()
        job = ci[ci.index("  layout-part:"):ci.index("  layout:")]
        self.assertRegex(job, r"timeout-minutes: \d+", "the layout parts need a time limit")
        self.assertRegex(job, r"layout_setup\.sh, timeout-minutes: \d+", "the set-up step needs its own time limit")
        self.assertIn("tests.test_fit_guard", job.split("matrix.part ==")[0], "the fit guard is shared across every part")


@unittest.skipUnless(sync_playwright and glob.glob(os.path.join(DIST, "*.html")), "Playwright with Chromium is needed")
class FitGuard(unittest.TestCase):
    def check(self, pg, where, found):
        pg.mouse.move(0, 0)            # a hovered item is not part of the layout
        pg.evaluate(SETTLE)
        bad = list(pg.evaluate(MENUS)) + list(pg.evaluate(DIALOGS)) + list(pg.evaluate(INPUT)) + list(pg.evaluate(CROWD)) + list(pg.evaluate(SPACE)) + list(pg.evaluate(AREAS))
        if bad:                               # look again after a moment: only what stays on screen counts
            pg.wait_for_timeout(400); pg.evaluate(SETTLE)
            bad = list(pg.evaluate(MENUS)) + list(pg.evaluate(DIALOGS)) + list(pg.evaluate(INPUT)) + list(pg.evaluate(CROWD)) + list(pg.evaluate(SPACE)) + list(pg.evaluate(AREAS))
        if bad:
            found[where] = bad

    def open_dialogs(self, pg, where, found):
        """Opens each shell pop-up the emulator has, checks it and closes it again."""
        if pg.evaluate("!!window.__dsh"):
            for p in PANELS:
                try:
                    pg.evaluate("(p) => window.__dsh.show(p)", p)
                except Exception:
                    continue
                self.check(pg, f"{where}, {p}", found)
            pg.evaluate("window.__dsh.settle(); window.__settle && window.__settle()")
            return
        for ov in SHELL_OVERLAYS:
            btn = pg.locator(f'[data-act="shell:{ov}"]')
            if btn.count() == 0 or not btn.first.is_visible():
                continue
            btn.first.click()
            self.check(pg, f"{where}, {ov}", found)
            pg.keyboard.press("Escape")

    def test_nothing_cut_squeezed_or_blocked_anywhere(self):
        self.assertGreater(len(glob.glob(os.path.join(DIST, "*.html"))), 10)
        files = mine(glob.glob(os.path.join(DIST, "*.html")))
        found = {}
        with sync_playwright() as p:
            b = p.chromium.launch()
            for f in files:
                emu = os.path.basename(f)[len("lynkomni-"):-len(".html")]
                for dark in (False, True):
                    pg = b.new_page(viewport={"width": 1500, "height": 1100}, reduced_motion="reduce")
                    errors = []
                    pg.on("pageerror", lambda e: errors.append(str(e)))
                    pg.goto("file://" + f)
                    pg.wait_for_timeout(300)
                    if dark:
                        box = pg.locator('#cDark, #cDarkTheme, input[type="checkbox"][id*="Dark"]')
                        if box.count() == 0:
                            pg.close(); continue
                        box.first.check()
                    control = next((c for c in SIZE_CONTROLS if pg.locator(c).count()), None)
                    sizes = pg.eval_on_selector_all(f"{control} option", "o => o.map(x => x.value)") if control else [None]
                    for size in sizes:
                        if size is not None:
                            pg.select_option(control, size)
                        where = f"{emu}{' dark' if dark else ''}{f' at {size}' if size else ''}"
                        self.check(pg, where, found)
                        self.open_dialogs(pg, where, found)
                    self.assertEqual(errors, [], emu)
                    pg.close()
            b.close()
        self.assertEqual(found, {}, "\n".join(f"{k}: {v}" for k, v in found.items()))

    def test_links_handled_by_the_screen_never_leave_the_page(self):
        """A link a screen handles itself (it carries data-act) never makes the browser leave the demo page; it keeps its real
        address for hosted pages and screen readers (ts/src/inpage.ts, added to every page; found on CI in section 4 step D2b)."""
        left = {}
        with sync_playwright() as p:
            b = p.chromium.launch()
            for f in mine(glob.glob(os.path.join(DIST, "*.html"))):
                pg = b.new_page(viewport={"width": 1500, "height": 1100})
                url = "file://" + f
                pg.goto(url); pg.wait_for_selector("html[data-ready]")
                hrefs = pg.eval_on_selector_all("a[data-act][href]", "e => [...new Set(e.map(a => a.getAttribute('href')).filter(h => h && !h.startsWith('#')))]")
                for h in hrefs:
                    pg.evaluate("h => { const a = [...document.querySelectorAll('a[data-act][href]')].find(x => x.getAttribute('href') === h); if (a) a.click(); }", h)
                    pg.wait_for_timeout(150)
                    if pg.url != url:
                        left.setdefault(os.path.basename(f), []).append(h)
                        pg.goto(url); pg.wait_for_selector("html[data-ready]")
                pg.close()
            b.close()
        self.assertEqual(left, {})

    def test_no_raw_word_names_on_any_screen(self):
        """Every screen of every emulator (each state button and each tab, view or choice it offers), in English: no raw word name
        such as "ppl_at_way_whatsapp" is ever shown, in text or in a label read aloud, and no button touches the text beside it
        (owner reports 2026-11-19)."""
        found = {}
        with sync_playwright() as p:
            b = p.chromium.launch()
            for f in mine(glob.glob(os.path.join(DIST, "*.html"))):
                emu = os.path.basename(f)[len("lynkomni-"):-len(".html")]
                pg = b.new_page(viewport={"width": 1500, "height": 1100}, reduced_motion="reduce")
                pg.goto("file://" + f); pg.wait_for_timeout(300)
                def look(where):
                    pg.mouse.move(0, 0)
                    pg.evaluate(SETTLE)
                    bad = pg.evaluate(RAW) + pg.evaluate(NAMES) + pg.evaluate(CROWD) + pg.evaluate(AREAS) + pg.evaluate(EDGE) + pg.evaluate(CLIP)
                    if bad:                   # look again after a moment: only what stays on screen counts
                        pg.wait_for_timeout(400); pg.evaluate(SETTLE)
                        bad = pg.evaluate(RAW) + pg.evaluate(NAMES) + pg.evaluate(CROWD) + pg.evaluate(AREAS) + pg.evaluate(EDGE) + pg.evaluate(CLIP)
                    if bad:
                        found.setdefault(emu, {})[where] = bad
                look("start")
                states = pg.eval_on_selector_all("[data-state]", "e => e.map(x => x.dataset.state)")
                for st in states or [None]:
                    if st is not None:
                        try:
                            pg.click(f'[data-state="{st}"]', timeout=2000)
                            sign_in(pg, emu, st)   # the panel never skips the staff PIN: type it like a person, then check the real screen
                        except Exception:
                            continue
                        look(st)
                    acts = pg.eval_on_selector_all('#screen [data-act], #display [data-act], .lscreen [data-act]',
                        "e => [...new Set(e.filter(x => x.getClientRects().length && /^(tab|view|way|go|nav|page|show|open|mode|join|qu|sv|at|tile):/.test(x.dataset.act)).map(x => x.dataset.act))].slice(0, 40)")
                    for a in acts:
                        try:
                            pg.click(f'[data-act="{a}"] >> visible=true', timeout=1500)
                        except Exception:
                            continue
                        look(f"{st or 'start'} > {a}")
                        if st is not None:
                            try:
                                pg.click(f'[data-state="{st}"]', timeout=1500)
                                sign_in(pg, emu, st)
                            except Exception:
                                pass
                pg.close()
            b.close()
        self.assertEqual(found, {}, "\n".join(f"{k}: {v}" for k, v in found.items()))

    @unittest.skipUnless(_K == SIGNED_IN_PART, "runs in part 3 of the layout check")
    def test_business_app_signed_in_at_every_size(self):
        """The Business app's menus (phone tabs, tablet side rail, computer view) appear only after signing in."""
        found = {}
        with sync_playwright() as p:
            b = p.chromium.launch()
            pg = b.new_page(viewport={"width": 1500, "height": 1100}, reduced_motion="reduce")
            pg.goto("file://" + os.path.join(DIST, "lynkomni-merchant-phone.html"))
            pg.fill("#phoneIn", "0788123456"); pg.click('[data-act="sendcode"]')
            pg.fill("#codeIn", "123456"); pg.click('[data-act="verify"]')
            pg.click('[data-act="business:0"]'); pg.wait_for_selector('[data-act="start"]'); pg.click('[data-act="start"]')
            self.check(pg, "language and region card", found)
            pg.click('[data-act="localeok"]'); pg.evaluate("__go('home')")
            sizes = pg.eval_on_selector_all("#cSize option", "o => o.map(x => x.value)")
            for kind in ("shop", "no_till", "agent_point", "restaurant"):
                pg.select_option("#cType", kind)
                for size in sizes:
                    pg.select_option("#cSize", size)
                    pg.evaluate("__go('home')")
                    if size == "tablet":
                        self.assertGreater(pg.locator(".rail button").count(), 0, "the tablet side rail is checked")
                    self.check(pg, f"business app {kind} at {size}", found)
                    self.open_dialogs(pg, f"business app {kind} at {size}", found)
            b.close()
        self.assertEqual(found, {}, "\n".join(f"{k}: {v}" for k, v in found.items()))


if __name__ == "__main__":
    unittest.main()
