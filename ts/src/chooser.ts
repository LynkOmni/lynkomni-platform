/**
 * LynkOmni's own drop-down for every choice on every page (owner, 2026-11-26: "Why is checker list empty and dropdown not
 * working?"). A phone's built-in picker opens full screen, ignores the theme and, inside some apps, does not open at all or
 * draws its items dark on dark, so a choice that is there looks empty. Every <select> stays in the page as the source of the
 * value, so every screen's own code keeps reading it and listening to it unchanged; it is only hidden behind LynkOmni's button
 * and list: the list opens in place (above the button when there is no room below), scrolls, follows the theme and the
 * reader's language and direction, finds by typing when the list is long, and works with arrows, Enter, Escape and a first
 * letter. Choosing sets the select's value and sends the same input and change events the built-in picker would.
 * A select marked data-native keeps the built-in picker (none does today). The phone field's country keeps its own
 * drop-down in ts/src/fields.ts.
 */

type Say = (k: string, v?: Record<string, string | number>) => string;

const LO_LONG = 10;   // a list longer than this gets a Find box
let loSeq = 0;

/** The same escaping as the shared parts (ts/src/emulator.ts esc): every attribute here is written in double quotes. */
function loEsc(s: string): string {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

/** The words a person reads for a select: its label, or the first option when it has none. */
function loLabel(sel: HTMLSelectElement): string {
  const byFor = sel.id ? sel.ownerDocument.querySelector(`label[for="${CSS.escape(sel.id)}"]`) : null;
  const wrap = sel.closest("label");
  const own = sel.getAttribute("aria-label");
  const text = (own ?? (byFor ?? wrap)?.textContent ?? "").replace(sel.textContent ?? "", "").replace(/\s+/g, " ").trim();
  return text;
}

function loShown(sel: HTMLSelectElement): string {
  const o = sel.selectedOptions[0];
  return (o?.textContent ?? "").trim();
}

/** Turns every select under root into LynkOmni's drop-down, once each; refreshes the words of those already turned. */
export function enhanceChoosers(root: ParentNode, say: () => Say | undefined): void {
  for (const sel of Array.from(root.querySelectorAll<HTMLSelectElement>("select:not([data-native])"))) {
    if (sel.multiple) continue;
    if (sel.classList.contains("lo-src")) continue;   // already LynkOmni's drop-down; its change listener keeps it in step
    const wrap = sel.ownerDocument.createElement("span");
    wrap.className = "lo-sel";
    const id = `lo-${++loSeq}`;
    sel.parentElement!.insertBefore(wrap, sel);
    wrap.appendChild(sel);
    sel.classList.add("lo-src");
    sel.tabIndex = -1;
    sel.setAttribute("aria-hidden", "true");
    const btn = sel.ownerDocument.createElement("button");
    btn.type = "button";
    btn.className = "lo-selbtn";
    btn.id = id;
    btn.setAttribute("aria-haspopup", "listbox");
    btn.setAttribute("aria-expanded", "false");
    btn.innerHTML = `<span class="lo-now"></span><span class="lo-caret" aria-hidden="true"></span>`;
    wrap.appendChild(btn);
    for (const k of ["why", "wait"]) if (sel.dataset[k] !== undefined) btn.dataset[k] = sel.dataset[k]!;
    loSync(sel);
    sel.addEventListener("change", () => loSync(sel));
    btn.addEventListener("click", () => loToggle(sel, say));
    btn.addEventListener("keydown", (e) => {
      if (e.key === "ArrowDown" || e.key === "ArrowUp") { e.preventDefault(); if (!wrap.querySelector(".lo-pop")) loToggle(sel, say); }
    });
  }
}

/** Keeps the button's words and state in step with the select (a redraw or code may change it). */
function loSync(sel: HTMLSelectElement): void {
  const btn = sel.parentElement?.querySelector<HTMLButtonElement>(".lo-selbtn");
  if (!btn) return;
  const now = loShown(sel);
  const label = loLabel(sel);
  // Only what changed is written: the watcher below reacts to changes, so writing the same words again would wake it for ever.
  const box = btn.querySelector(".lo-now")!;
  if (box.textContent !== now) box.textContent = now;
  const name = label && label !== now ? `${label}: ${now}` : now;
  if (btn.getAttribute("aria-label") !== name) btn.setAttribute("aria-label", name);
  if (btn.disabled !== sel.disabled) btn.disabled = sel.disabled;
  if (btn.classList.contains("lo-empty") !== (sel.value === "")) btn.classList.toggle("lo-empty", sel.value === "");
}

function loClose(wrap: Element): void {
  wrap.querySelector(".lo-pop")?.remove();
  wrap.querySelector(".lo-selbtn")?.setAttribute("aria-expanded", "false");
}

function loChoose(sel: HTMLSelectElement, value: string): void {
  const wrap = sel.parentElement!;
  loClose(wrap);
  const btn = wrap.querySelector<HTMLButtonElement>(".lo-selbtn");
  if (sel.value !== value) {
    sel.value = value;
    sel.dispatchEvent(new Event("input", { bubbles: true }));
    sel.dispatchEvent(new Event("change", { bubbles: true }));
  }
  loSync(sel);
  if (btn?.isConnected) btn.focus();
}

function loToggle(sel: HTMLSelectElement, say: () => Say | undefined): void {
  const wrap = sel.parentElement!;
  const btn = wrap.querySelector<HTMLButtonElement>(".lo-selbtn")!;
  if (wrap.querySelector(".lo-pop")) { loClose(wrap); return; }
  for (const other of Array.from(sel.ownerDocument.querySelectorAll(".lo-sel"))) if (other !== wrap) loClose(other);
  const t = say();
  const doc = sel.ownerDocument;
  const pop = doc.createElement("div");
  pop.className = "lo-pop";
  const listId = `${btn.id}-list`;
  const opts = Array.from(sel.options);
  const long = opts.length > LO_LONG;
  const rows: string[] = [];
  let group: HTMLOptGroupElement | null = null;
  opts.forEach((o, i) => {
    const g = o.parentElement instanceof HTMLOptGroupElement ? o.parentElement : null;
    if (g && g !== group) rows.push(`<li class="lo-group" role="presentation">${loEsc(g.label)}</li>`);
    group = g;
    const text = (o.textContent ?? "").trim();
    rows.push(`<li class="lo-opt" role="option" id="${listId}-${i}" data-v="${loEsc(o.value)}" data-find="${loEsc(text.toLowerCase())}"`
      + ` aria-selected="${o.selected}"${o.disabled ? ' aria-disabled="true"' : ""}>${loEsc(text)}</li>`);
  });
  pop.innerHTML = (long && t ? `<input class="lo-find" type="search" data-recents="choice" autocomplete="off" aria-label="${loEsc(t("fd_find"))}"`
      + ` placeholder="${loEsc((opts.find((o) => o.value !== "")?.textContent ?? "").trim())}" aria-controls="${listId}">` : "")
    + `<ul class="lo-list" role="listbox" id="${listId}" aria-labelledby="${btn.id}">${rows.join("")}</ul>`
    + (long && t ? `<p class="lo-none" hidden>${loEsc(t("fd_find_none"))}</p>` : "");
  wrap.appendChild(pop);
  btn.setAttribute("aria-expanded", "true");
  const room = (doc.defaultView?.innerHeight ?? 800) - btn.getBoundingClientRect().bottom;
  if (room < 260 && btn.getBoundingClientRect().top > room) pop.classList.add("lo-up");
  const list = pop.querySelector<HTMLElement>(".lo-list")!;
  const all = (): HTMLElement[] => Array.from(list.querySelectorAll<HTMLElement>(".lo-opt:not([hidden]):not([aria-disabled])"));
  let active: HTMLElement | null = list.querySelector<HTMLElement>('[aria-selected="true"]') ?? all()[0] ?? null;
  const mark = (el: HTMLElement | null): void => {
    list.querySelector(".lo-active")?.classList.remove("lo-active");
    active = el;
    if (!el) return;
    el.classList.add("lo-active");
    (pop.querySelector(".lo-find") ?? btn).setAttribute("aria-activedescendant", el.id);
    el.scrollIntoView({ block: "nearest" });
  };
  mark(active);
  list.addEventListener("click", (e) => {
    const li = (e.target as HTMLElement).closest<HTMLElement>(".lo-opt");
    if (li && !li.hasAttribute("aria-disabled")) loChoose(sel, li.dataset["v"] ?? "");
  });
  const keys = (e: KeyboardEvent): void => {
    const items = all();
    const i = active ? items.indexOf(active) : -1;
    if (e.key === "ArrowDown") { e.preventDefault(); mark(items[Math.min(items.length - 1, i + 1)] ?? null); }
    else if (e.key === "ArrowUp") { e.preventDefault(); mark(items[Math.max(0, i - 1)] ?? null); }
    else if (e.key === "Home") { e.preventDefault(); mark(items[0] ?? null); }
    else if (e.key === "End") { e.preventDefault(); mark(items[items.length - 1] ?? null); }
    else if (e.key === "Enter" || (e.key === " " && !(e.target instanceof HTMLInputElement))) { e.preventDefault(); if (active) loChoose(sel, active.dataset["v"] ?? ""); }
    else if (e.key === "Escape" || e.key === "Tab") { loClose(wrap); if (e.key === "Escape") btn.focus(); }
    else if (e.key.length === 1 && !(e.target instanceof HTMLInputElement)) {
      const k = e.key.toLowerCase();
      const from = i + 1;
      const hit = [...items.slice(from), ...items.slice(0, from)].find((li) => (li.dataset["find"] ?? "").startsWith(k));
      if (hit) mark(hit);
    }
  };
  btn.addEventListener("keydown", keys);
  const find = pop.querySelector<HTMLInputElement>(".lo-find");
  if (find) {
    find.addEventListener("keydown", keys);
    find.addEventListener("input", () => {
      const q = find.value.trim().toLowerCase();
      let first: HTMLElement | null = null;
      for (const li of Array.from(list.querySelectorAll<HTMLElement>(".lo-opt"))) {
        const hit = !q || (li.dataset["find"] ?? "").split(/\s+/).some((w) => w.startsWith(q)) || (li.dataset["find"] ?? "").includes(q);
        li.hidden = !hit;
        if (hit && !first) first = li;
      }
      pop.querySelector<HTMLElement>(".lo-none")!.hidden = first !== null;
      mark(first);
    });
    find.focus();
  }
  const outside = (e: Event): void => {
    if (!wrap.contains(e.target as Node)) { loClose(wrap); doc.removeEventListener("pointerdown", outside, true); }
  };
  doc.addEventListener("pointerdown", outside, true);
}

/** Every page: turns its selects now and after every redraw (called by ts/src/names.ts watchNames, which every page runs).
 *  Only what was just added is looked at, never the whole page again, so a tap stays fast. */
export function watchChoosers(root: Element, say: () => Say | undefined): void {
  const view = root.ownerDocument?.defaultView as (Window & typeof globalThis) | null;
  enhanceChoosers(root, say);
  const Obs = view?.MutationObserver;
  if (!Obs) return;
  new Obs((records) => {
    for (const r of records) {
      for (const n of Array.from(r.addedNodes)) {
        if (n.nodeType !== 1) continue;
        const el = n as Element;
        if (el.tagName === "SELECT") { if (el.parentElement) enhanceChoosers(el.parentElement, say); }
        else if (!el.classList.contains("lo-pop") && !el.classList.contains("lo-sel") && el.getElementsByTagName("select").length) enhanceChoosers(el, say);
      }
    }
  }).observe(root, { childList: true, subtree: true });
}
