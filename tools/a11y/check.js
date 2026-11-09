// Automatic accessibility check run inside every emulator screen by tests/test_layout_i18n.py (build section 1 automation
// "accessibility check in the build", level auto). It checks what a script can check against WCAG 2.2 AA: names on
// controls and images, labels on fields, contrast of text (4.5:1, 3:1 for large text), 44 px targets (blueprint 41 B), one language and
// direction on the screen root, dialogs with names, no duplicate ids, nothing focusable hidden from assistive tech.
// A human accessibility audit is still required before launch (provider ledger, later list). Returns a list of problems.
(() => {
  const root = document.querySelector(window.__a11yRoot || '#display') || document.body;   // a device emulator names its screen (tests/test_layout_i18n.py DeviceLayout)
  const bad = [];
  const vis = (el) => { const cs = getComputedStyle(el); const r = el.getBoundingClientRect(); return cs.display !== 'none' && cs.visibility !== 'hidden' && r.width > 1 && r.height > 1; };   // 1 px boxes are screen-reader-only text
  const hiddenFromAT = (el) => !!el.closest('[aria-hidden="true"]');
  const name = (el) => (el.getAttribute('aria-label') || (el.getAttribute('aria-labelledby') && (document.getElementById(el.getAttribute('aria-labelledby')) || {}).textContent) || el.getAttribute('title') || el.textContent || '').trim();
  const desc = (el) => `${el.tagName.toLowerCase()}${el.className && typeof el.className === 'string' ? '.' + el.className.split(/\s+/).join('.') : ''}`;
  const parse = (c) => { const m = /rgba?\(([\d.]+),\s*([\d.]+),\s*([\d.]+)(?:,\s*([\d.]+))?\)/.exec(c); return m ? [+m[1], +m[2], +m[3], m[4] === undefined ? 1 : +m[4]] : null; };
  const lum = ([r, g, b]) => { const f = (v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4; }; return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b); };
  const blend = (fg, bg) => fg[3] >= 1 ? fg : [0, 1, 2].map((i) => fg[i] * fg[3] + bg[i] * (1 - fg[3])).concat([1]);
  const bgOf = (el) => { let e = el; while (e && e !== document.documentElement) { const c = parse(getComputedStyle(e).backgroundColor); if (c && c[3] > 0) return c[3] >= 1 ? c : blend(c, bgOf(e.parentElement) || [255, 255, 255, 1]); e = e.parentElement; } return [255, 255, 255, 1]; };
  const contrast = (a, b) => { const l1 = lum(a), l2 = lum(b); return (Math.max(l1, l2) + 0.05) / (Math.min(l1, l2) + 0.05); };
  // root language and direction
  if (!root.getAttribute('lang') && !document.documentElement.lang) bad.push('root: no lang');
  if (!root.getAttribute('dir') && !document.documentElement.dir) bad.push('root: no dir');
  // duplicate ids
  const ids = new Map();
  for (const el of root.querySelectorAll('[id]')) { if (ids.has(el.id)) bad.push(`duplicate id #${el.id}`); ids.set(el.id, 1); }
  for (const el of root.querySelectorAll('*')) {
    if (!vis(el)) continue;
    if (el.closest(':disabled, [aria-disabled="true"]')) continue;   // inactive controls are exempt from contrast (WCAG 1.4.3)
    const tag = el.tagName.toLowerCase();
    const role = el.getAttribute('role');
    if (hiddenFromAT(el)) {
      if ((tag === 'button' || tag === 'a' || tag === 'input' || tag === 'select' || el.tabIndex >= 0) && !el.disabled && el.tabIndex !== -1) bad.push(`focusable but aria-hidden: ${desc(el)}`);
      continue;
    }
    if (tag === 'svg' && !el.closest('button, a, [role="button"], [role="img"], [aria-label], [aria-labelledby]')) bad.push(`svg without a name or aria-hidden: ${desc(el.parentElement || el)}`);
    if (role === 'img' && !name(el)) bad.push(`image without a name: ${desc(el)}`);
    if (role === 'dialog' && !el.getAttribute('aria-label') && !el.getAttribute('aria-labelledby')) bad.push(`dialog without a name: ${desc(el)}`);
    if (tag === 'button' || role === 'button' || (tag === 'a' && el.hasAttribute('href'))) {
      if (!name(el)) bad.push(`control without a name: ${desc(el)}`);
      const r0 = el.getBoundingClientRect();
      // A device shown smaller to fit the window (.fit zoom, emulator.ts fitToWidth) is a scaled picture of the real device:
      // tap sizes are judged in the device's own pixels, which is what a finger meets on the real hardware.
      const fit = parseFloat(getComputedStyle(el.closest('.fit') || document.documentElement).getPropertyValue('--fit')) || 1;
      const r = { width: Math.round(r0.width / fit * 10) / 10, height: Math.round(r0.height / fit * 10) / 10 };   // to 0.1 px, so dividing by the zoom never turns 24 into 23.99
      const inline = tag === 'a' && el.closest('p, li, td, figcaption, .note, .sugg, .mnote, .chat-lang');
      if (!inline && Math.min(r.width, r.height) < 44) bad.push(`target under 44 px: ${desc(el)} ${Math.round(r.width)}x${Math.round(r.height)}`);   // blueprint 41 B: 44 px touch targets (stricter than the WCAG 2.2 AA minimum of 24)
    }
    if (tag === 'input' || tag === 'select' || tag === 'textarea') {
      const type = el.getAttribute('type');
      if (type !== 'hidden' && !(el.id && document.querySelector(`label[for="${el.id}"]`)) && !el.closest('label') && !el.getAttribute('aria-label') && !el.getAttribute('aria-labelledby')) bad.push(`field without a label: ${desc(el)}`);
    }
    // text contrast: elements that directly hold text
    const own = [...el.childNodes].filter((n) => n.nodeType === 3 && n.textContent.trim()).map((n) => n.textContent.trim()).join(' ');
    if (own) {
      const cs = getComputedStyle(el);
      const fg = parse(cs.color);
      if (fg) {
        const bg = bgOf(el);
        const c = contrast(blend(fg, bg), bg);
        const size = parseFloat(cs.fontSize), bold = parseInt(cs.fontWeight, 10) >= 700;
        const large = size >= 24 || (bold && size >= 18.66);
        if (c < (large ? 3 : 4.5) && !el.closest('.skel, .left')) bad.push(`contrast ${c.toFixed(2)}:1 on "${own.slice(0, 30)}" (${desc(el)})`);
      }
    }
  }
  return [...new Set(bad)];
})()
