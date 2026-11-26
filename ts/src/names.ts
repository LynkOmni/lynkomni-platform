/** Every Lynk name carries its plain word (owner, 21 November 2026; catalog/names.v1.json, core/names.py).
 *
 *  - nameLabel draws a name where the screen lists it (menus, launcher, search, pricing, cards, headers).
 *  - explainNames marks every name a screen shows: the first mention on a screen in running text gets its plain word in
 *    brackets; every other mention is marked and explains itself on hover, focus and long press. Receipts, printed paper,
 *    the copyright line, what people type, code and any area marked data-names="off" are left as they are.
 *  - watchNames runs explainNames whenever a screen redraws, so no screen has to remember to.
 *  Names are the same in every language; plain words (web/names, nm_<id>) and descriptions (web/nameinfo, nma_<id>) are
 *  translated. A person may choose plain words first; the owner may switch it on for the business's devices. */
import { watchChoosers } from "./chooser.js";
import { NAMES_EN, NAMES_REG } from "./names.generated.js";

export type Say = (key: string, vars?: Record<string, string | number>) => string;
export type NamesMode = "brand_first" | "plain_first";
export interface NameEntry { id: string; name: string; kind: "product" | "service" | "feature" | "card_group" | "device"; family?: string; part_of?: string; about?: boolean; icon?: string | null; spoken: string }
export interface NamesRegister { max_plain_chars: number; company: string[]; internal: string[]; retired: string[]; names: NameEntry[];
  now_called: { old: string; id: string; since: string }[]; similar: { id: string; names: string[] }[]; familiar_after: number;
  plain_word_check: { allowed_short: string[]; words_never: string[]; rule?: string }; asks: { min_shown: number; rule?: string } }
export interface NameFind { name: string; start: number; end: number }

const NM_REG = NAMES_REG;
const NM_BY_NAME = new Map(NM_REG.names.map((n) => [n.name, n] as const));
const NM_BY_ID = new Map(NM_REG.names.map((n) => [n.id, n] as const));
const NM_NOT_SHOWN = [...NM_REG.company, ...NM_REG.internal, ...NM_REG.retired];
const nmEsc = (s: string): string => s.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c] as string);
// Longest names first, so no name is cut out of a longer one; a name never sits inside a longer word.
const NM_ALT = [...NM_BY_NAME.keys()].sort((a, b) => b.length - a.length).map((n) => n.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|");
const NM_RE = new RegExp(`(?<![A-Za-z])(${NM_ALT})(?![A-Za-z])`, "g");   // built once: matchAll works on its own copy, so sharing it is safe
const nmPattern = (): RegExp => NM_RE;
const NM_ANY_LYNK = /(?<![A-Za-z])Lynk[A-Z][A-Za-z]*/g;

export const entryOf = (name: string): NameEntry | undefined => NM_BY_NAME.get(name);
export const nameById = (id: string): string | undefined => NM_BY_ID.get(id)?.name;
export const allNames = (): readonly NameEntry[] => NM_REG.names;

/** The registered names in a text, in order, with where each starts and ends (the same answer as core/names.py find). */
export function findNames(text: string): NameFind[] {
  return [...text.matchAll(nmPattern())].map((m) => ({ name: m[1] as string, start: m.index ?? 0, end: (m.index ?? 0) + (m[1] as string).length }));
}
/** Lynk words a person could see that the register does not know (the company name and internal or retired names aside). */
export function unknownNames(text: string): string[] {
  return (text.match(NM_ANY_LYNK) ?? []).filter((w) => !NM_BY_NAME.has(w) && !NM_NOT_SHOWN.some((n) => w.startsWith(n)));
}
const nmSaid = (say: Say | undefined, key: string): string | undefined => { const v = say?.(key); return v && v !== key ? v : undefined; };
const nmFill = (t: string, v: Record<string, string>): string => t.replace(/\{(\w+)\}/g, (m, k: string) => v[k] ?? m);
/** The plain word in the screen's language; English when a word is missing. */
export function plainOf(name: string, say?: Say): string {
  const e = NM_BY_NAME.get(name); if (!e) return "";
  return nmSaid(say, `nm_${e.id}`) ?? NAMES_EN.plain[`nm_${e.id}`] ?? "";
}
/** The one-line description, in the screen's language, when the page carries the descriptions (it imports
 *  ts/src/nameinfo.ts, words in web/nameinfo); otherwise nothing, never English on a screen in another language.
 *  With no words at all (tests and tools) the English description. */
export function aboutOf(name: string, say?: Say): string {
  const e = NM_BY_NAME.get(name); if (!e || e.about === false) return "";
  return say ? (nmSaid(say, `nma_${e.id}`) ?? "") : (NAMES_EN.about[`nma_${e.id}`] ?? "");
}
/** The product a service, feature or card group belongs to (its name). */
export function partOf(name: string): string | null { const p = NM_BY_NAME.get(name)?.part_of; return p ? (NM_BY_ID.get(p)?.name ?? null) : null; }
/** The words of a label: "LynkStat (Analytics)", or "Analytics (LynkStat)" with plain words first (core/names.py label). */
export function labelText(name: string, say?: Say, mode: NamesMode = "brand_first"): string {
  const p = plainOf(name, say);
  return mode === "plain_first" ? `${p} (${name})` : `${name} (${p})`;
}

// ---------------------------------------------------------------- the person's and the device's choice
const NM_KEY = "lynkomni.names.v1", NM_DEVICE_KEY = "lynkomni.names.device.v1";
let nmMemory: NamesMode | null = null, nmDeviceMemory: NamesMode | null = null;
const nmRead = (k: string): NamesMode | null => { try { const v = typeof localStorage !== "undefined" ? localStorage.getItem(k) : null; return v === "plain_first" || v === "brand_first" ? v : null; } catch { return null; } };
const nmWrite = (k: string, v: NamesMode | null): void => { try { if (typeof localStorage !== "undefined") { if (v) localStorage.setItem(k, v); else localStorage.removeItem(k); } } catch { /* kept for this visit */ } };
/** The person's own choice (their account, Language and region), remembered on every device they sign in on. */
export function personMode(): NamesMode { return nmRead(NM_KEY) ?? nmMemory ?? "brand_first"; }
export function setPersonMode(m: NamesMode): void { nmMemory = m; nmWrite(NM_KEY, m); }
/** The owner's choice for this business device; when set it applies to everyone using the device. */
export function deviceMode(): NamesMode | null { return nmRead(NM_DEVICE_KEY) ?? nmDeviceMemory; }
export function setDeviceMode(m: NamesMode | null): void { nmDeviceMemory = m; nmWrite(NM_DEVICE_KEY, m); }
/** What the screen shows: the owner's device choice first, otherwise the person's own. */
export function namesMode(): NamesMode { return deviceMode() ?? personMode(); }

// ---------------------------------------------------------------- drawing a name where a screen lists it
export type NamePlace = "label" | "header" | "compact";
/** A name with its plain word. label: beside it; header: a small line under it; compact: the name alone, explained on
 *  hover, focus and long press and to screen readers. */
export function nameLabel(name: string, say?: Say, place: NamePlace = "label", mode: NamesMode = namesMode(), icon?: (id: string) => string): string {
  const e = NM_BY_NAME.get(name); if (!e) return nmEsc(name);
  const p = plainOf(name, say);
  const mark = icon && e.icon ? `<span class="lic" aria-hidden="true">${icon(e.icon)}</span>` : "";
  const attrs = `class="lname lname-${place}${mode === "plain_first" ? " lname-pf" : ""}" data-lname="${nmEsc(name)}"`;
  if (place === "compact") return `<span ${attrs} title="${nmEsc(p)}">${mark}${nmEsc(name)}</span>`;
  const nm = `<span class="lnm">${nmEsc(name)}</span>`, pl = `<span class="lpl">${nmEsc(p)}</span>`;
  return `<span ${attrs}>${mark}${mode === "plain_first" ? `${pl} ${nm}` : `${nm} ${pl}`}</span>`;
}
/** Search entries for every name: found by its name, its plain word or its description, in the screen's language and in
 *  English (the shell's search() ranks them). */
export function nameEntries(say?: Say, mode: NamesMode = namesMode(), act?: string): { id: string; kind: "help"; title: string; subtitle: string; keywords: string[]; act: string; icon?: string }[] {
  const old = (id: string): string[] => NM_REG.now_called.filter((x) => x.id === id).map((x) => x.old);
  const out = NM_REG.names.filter((n) => n.kind !== "device").map((n) => {
    const p = plainOf(n.name, say), a = aboutOf(n.name, say);
    return { id: `name:${n.id}`, kind: "help" as const, title: mode === "plain_first" ? `${p} (${n.name})` : `${n.name} (${p})`, subtitle: a,
      keywords: [p, a, n.spoken, ...old(n.id), NAMES_EN.plain[`nm_${n.id}`] ?? "", NAMES_EN.about[`nma_${n.id}`] ?? ""].filter(Boolean), act: act ?? `open:name-${n.id}`, ...(n.icon ? { icon: n.icon } : {}) };
  });
  // An old name still finds the new one, with a short "now called" note (catalog/names.v1.json now_called).
  for (const x of NM_REG.now_called) {
    const n = NM_BY_ID.get(x.id); if (!n) continue;
    out.push({ id: `name-old:${x.old}`, kind: "help" as const, title: nmFill(nmSaid(say, "nm_now_called") ?? "{old} is now {name}.", { old: x.old, name: n.name }), subtitle: labelText(n.name, say, mode), keywords: [x.old], act: act ?? `open:name-${n.id}` });
  }
  const title = nmSaid(say, "nm_compare_title") ?? "Which one do I need?";
  for (const g of NM_REG.similar) {
    const names = g.names.map((i) => NM_BY_ID.get(i)?.name ?? "");
    out.push({ id: `name-compare:${g.id}`, kind: "help" as const, title, subtitle: names.join(", "), keywords: names.flatMap((n) => [n, plainOf(n, say)]), act: act ?? `open:compare-${g.id}` });
  }
  return out;
}
/** The answer to "What is LynkStat?", from the register (LynkAssist and the offline knowledge pack use the same words). */
export function whatIs(name: string, say?: Say): string {
  const p = plainOf(name, say), a = aboutOf(name, say);
  const t = nmSaid(say, "nmi_what_a");
  if (!a) return `${name} (${p})`;
  return t ? t.replace("{name}", name).replace("{plain}", p).replace("{about}", a) : `${name} (${p}): ${a}`;
}

// ---------------------------------------------------------------- marking every name on a screen
const NM_SKIP = "script,style,textarea,input,select,option,code,pre,svg,title,[contenteditable],#paper,.receipt,.rtext,.fcopy,.shortfoot,.lname,[data-lname],.ltip,[data-names=\"off\"]";
const NM_RUNNING = "p,li,dd,dt,td,th,label,figcaption,blockquote,h1,h2,h3,h4,h5,h6,.muted,.note,.desc";
const NM_CONTROL = "button,a,[role=button],[role=tab],[role=option],[role=menuitem],summary,.chip";
const NM_SCREEN = "[data-screen],.screen,#display,#screen,main,body";

/** Mark every registered name inside root. Safe to run again: a marked name is never marked twice. */
export function explainNames(root: Element, say?: Say, mode: NamesMode = namesMode()): number {
  const doc = root.ownerDocument; if (!doc) return 0;
  const view = doc.defaultView;
  // Read everything first, then change the page: a computed style read between two changes makes the browser work out every
  // style again, once for each name (a launcher full of names took over 120 ms on a slow phone). The result is the same.
  type Hit = { name: string; start: number; end: number; block: Element | null; control: Element | null; screen: Element; nearby: string; oneLine: boolean; shownBefore: boolean };
  type Job = { t: Text; el: Element; row: boolean; hits: Hit[] };
  const walker = doc.createTreeWalker(root, 4 /* text */);
  const jobs: Job[] = [];
  // Each lookup is made once per element and remembered for this pass (a launcher repeats the same screen, blocks and styles
  // for every name; looking them up again for each name cost a slow phone about 60 ms on the first tap). The result is the same.
  const styleOf = new Map<Element, CSSStyleDeclaration | null>(), textOf = new Map<Element, string>(), shownIn = new Map<Element, Set<string>>();
  const style = (e: Element): CSSStyleDeclaration | null => { if (!styleOf.has(e)) styleOf.set(e, view?.getComputedStyle(e) ?? null); return styleOf.get(e) ?? null; };
  const text = (e: Element): string => { let v = textOf.get(e); if (v === undefined) { v = (e.textContent ?? "").toLowerCase(); textOf.set(e, v); } return v; };
  const shown = (scr: Element): Set<string> => {
    let v = shownIn.get(scr);
    if (!v) { v = new Set(Array.from(scr.querySelectorAll(".lname-shown[data-lname]"), (x) => x.getAttribute("data-lname") ?? "")); shownIn.set(scr, v); }
    return v;
  };
  for (let n = walker.nextNode(); n; n = walker.nextNode()) {
    const t = n as Text, el = t.parentElement;
    if (!el || !t.data.includes("Lynk") || el.closest(NM_SKIP)) continue;
    const found = findNames(t.data);
    if (!found.length) continue;
    const cs = style(el);
    const row = !!cs && cs.whiteSpace.startsWith("nowrap") && cs.overflowX !== "visible";   // a one-line row that cuts its text: mark the row itself
    const block = row ? null : el.closest(NM_RUNNING), control = row ? null : el.closest(NM_CONTROL), screen = row ? doc.body : el.closest(NM_SCREEN) ?? doc.body;
    const bcs = block ? style(block) : null;
    const oneLine = !!bcs && (bcs.whiteSpace.startsWith("nowrap") || bcs.whiteSpace === "pre" || bcs.textOverflow === "ellipsis");   // no room to add words
    const hits = row ? found.map((f) => ({ ...f, block: null, control: null, screen: doc.body, nearby: "", oneLine: true, shownBefore: false }))
      : found.map((f) => ({ ...f, block, control, screen, nearby: text(control ?? block ?? el), oneLine, shownBefore: shown(screen).has(f.name) }));
    jobs.push({ t, el, row, hits });
  }
  const shownNow = new Map<Element, Set<string>>();       // first mentions shown in this pass, per screen
  const addedNow = new Map<Element, string[]>();          // plain words this pass added to a block or control
  let marked = 0;
  for (const { t, el, row, hits } of jobs) {
    if (row) {
      const words = hits.map((f) => `${f.name}: ${plainOf(f.name, say)}`).join("; ");
      el.setAttribute("data-lname", hits.map((f) => f.name).join(" "));
      if (!el.getAttribute("title")) el.setAttribute("title", words);
      if (!el.getAttribute("aria-description")) el.setAttribute("aria-description", words);
      marked += hits.length; continue;
    }
    const frag = doc.createDocumentFragment();
    let at = 0;
    for (const h of hits) {
      if (h.start > at) frag.append(t.data.slice(at, h.start));
      const where = h.control ?? h.block ?? el, p = plainOf(h.name, say).toLowerCase();
      const said = h.nearby.includes(p) || (addedNow.get(where) ?? []).some((w) => w.includes(p));
      const seen = shownNow.get(h.screen) ?? new Set<string>();
      const show = !!h.block && !h.control && !said && !h.oneLine && !h.shownBefore && !seen.has(h.name) && !familiar(h.name);
      frag.append(nmMark(doc, h.name, say, mode, show, said, h.control));
      if (show) { seen.add(h.name); shownNow.set(h.screen, seen); addedNow.set(where, [...(addedNow.get(where) ?? []), p]); }
      at = h.end; marked += 1;
    }
    if (at < t.data.length) frag.append(t.data.slice(at));
    t.replaceWith(frag);
  }
  return marked;
}
function nmMark(doc: Document, name: string, say: Say | undefined, mode: NamesMode, show: boolean, said: boolean, control: Element | null): HTMLElement {
  const p = plainOf(name, say), a = aboutOf(name, say);
  const span = doc.createElement("span");
  span.className = "lname lname-x"; span.dataset["lname"] = name; span.title = a ? `${p}: ${a}` : p;
  // The first mention on a screen, in running text, shows its plain word; never when the words around already say it.
  if (show) {
    span.classList.add("lname-shown");
    const nm = doc.createElement("span"); nm.className = "lnm"; nm.textContent = name;
    const pl = doc.createElement("span"); pl.className = "lpl"; pl.textContent = mode === "plain_first" ? p : `(${p})`;
    if (mode === "plain_first") { nm.textContent = `(${name})`; span.append(pl, " ", nm); } else span.append(nm, " ", pl);
  } else {
    span.textContent = name;
    if (said) span.classList.add("lname-said");
    if (control && !control.getAttribute("aria-description")) control.setAttribute("aria-description", `${name}: ${p}`);
  }
  return span;
}

/** Run explainNames on root now and whenever anything inside it is drawn again. Returns a function that stops watching. */
export function watchNames(root: Element, say: () => Say | undefined, mode: () => NamesMode = namesMode): () => void {
  const view = root.ownerDocument?.defaultView as (Window & typeof globalThis) | null;
  const Obs = view?.MutationObserver;
  explainNames(root, say(), mode());
  nmWireTips(root, say);
  watchChoosers(root, say, (text) => explainText(text, say(), mode()));   // every page runs this watcher, so every choice on every page becomes LynkOmni's own drop-down
  if (!Obs) return () => undefined;
  // New text is marked just after the screen is shown, not while it is being drawn: checking whether a line has room for the
  // plain word needs the page's styles, and reading them in the middle of a redraw made the browser work the whole screen out
  // twice (about 45 ms of a launcher tap on a slow phone). Marking waits for the next frame, when the styles are already known,
  // and a timer catches a page that is not drawing frames. The marks are the same; they appear one frame later.
  let busy = false, due = false;
  const pending = new Set<Element>();
  const flush = (): void => {
    if (!due) return;
    due = false;
    const roots = [...pending].filter((e) => e.isConnected); pending.clear();
    busy = true;
    try {
      for (const e of roots) if (!roots.some((o) => o !== e && o.contains(e))) explainNames(e, say(), mode());
    } finally { obs.takeRecords(); busy = false; }
  };
  const obs = new Obs((records) => {
    if (busy) return;
    for (const r of records) {
      for (const n of Array.from(r.addedNodes)) {
        if (n.nodeType === 1) pending.add(n as Element);
        else if (n.nodeType === 3 && n.parentElement) pending.add(n.parentElement);
      }
      if (r.type === "characterData" && r.target.parentElement) pending.add(r.target.parentElement);
    }
    if (!pending.size || due) return;
    due = true;
    if (view?.requestAnimationFrame) view.requestAnimationFrame(() => view.requestAnimationFrame(flush));
    view?.setTimeout(flush, 250);
  });
  obs.observe(root, { childList: true, subtree: true, characterData: true });
  return () => obs.disconnect();
}

/** A long press (or a tap outside a button or link) on a marked name shows its plain word and what it does, in a small
 *  note inside the screen; it closes on the next tap, Escape or after six seconds. Hover uses the name's own title. */
function nmWireTips(root: Element, say: () => Say | undefined): void {
  const doc = root.ownerDocument; if (!doc || (root as HTMLElement).dataset["namesTips"]) return;
  (root as HTMLElement).dataset["namesTips"] = "1";
  let timer: ReturnType<typeof setTimeout> | null = null, closeTimer: ReturnType<typeof setTimeout> | null = null;
  const close = (): void => { doc.querySelectorAll(".ltip").forEach((x) => x.remove()); if (closeTimer) clearTimeout(closeTimer); };
  const open = (span: HTMLElement): void => {
    close();
    const name = span.dataset["lname"] ?? ""; const s = say();
    const tip = doc.createElement("div"); tip.className = "ltip"; tip.setAttribute("role", "status");
    const part = partOf(name);
    const like = similarOf(name), sayIt = nmSaid(s, "nm_say");
    tip.innerHTML = `<b>${nmEsc(labelText(name, s, namesMode()))}</b>${aboutOf(name, s) ? `<span>${nmEsc(aboutOf(name, s))}</span>` : ""}${part ? `<small>${nmEsc((s?.("nm_part_of") ?? "Part of {name}").replace("{name}", part))}</small>` : ""}${sayIt ? `<small>${nmEsc(nmFill(sayIt, { spoken: spokenOf(name) }))}</small>` : ""}${like.length ? `<button class="lcmp" data-nmcompare="${nmEsc(name)}">${nmEsc(nmSaid(s, "nm_compare_title") ?? "Which one do I need?")}</button>` : ""}`;
    nameAsked(name, "note");
    const r = span.getBoundingClientRect(), view = doc.defaultView;
    const w = view?.innerWidth ?? 360, h = view?.innerHeight ?? 640;
    tip.style.insetInlineStart = `${Math.max(8, Math.min(r.left, w - 288))}px`;
    tip.style.top = `${r.bottom + 6 > h - 96 ? Math.max(8, r.top - 96) : r.bottom + 6}px`;
    doc.body.append(tip);
    closeTimer = setTimeout(close, 6000);
  };
  doc.addEventListener("click", (e) => {
    const b = (e.target as Element | null)?.closest?.("[data-nmcompare]") as HTMLElement | null;
    const tip = b?.closest(".ltip") as HTMLElement | null; if (!b || !tip) return;
    e.stopPropagation();
    const name = b.dataset["nmcompare"] ?? "";
    tip.innerHTML = compareHtml(name, say());
    nameAsked(name, "compare");
    const h = doc.defaultView?.innerHeight ?? 640, r = tip.getBoundingClientRect();
    if (r.bottom > h - 8) tip.style.top = `${Math.max(8, h - r.height - 8)}px`;
    if (closeTimer) clearTimeout(closeTimer); closeTimer = setTimeout(close, 20000);
  }, true);
  root.addEventListener("pointerdown", (e) => {
    if ((e.target as Element | null)?.closest?.(".ltip")) return;
    const span = (e.target as Element | null)?.closest?.(".lname-x") as HTMLElement | null;
    if (timer) clearTimeout(timer);
    if (!span) { close(); return; }
    timer = setTimeout(() => open(span), 450);
  });
  root.addEventListener("pointerup", () => { if (timer) clearTimeout(timer); });
  root.addEventListener("click", (e) => {
    const span = (e.target as Element | null)?.closest?.(".lname-x") as HTMLElement | null;
    if (span && !span.closest(NM_CONTROL)) open(span);
  });
  doc.addEventListener("keydown", (e) => { if ((e as KeyboardEvent).key === "Escape") close(); });
}

/** The choice of how names show, for a settings page: "Lynk names with plain words" or "Plain words first".
 *  scope person: the person's own choice (their account); scope device: the owner's choice for this business device,
 *  which others see but cannot change. The act on each button is `${act}:<mode>`. */
export function namesChoice(say: Say, o: { scope: "person" | "device"; act: string; canChange: boolean }): string {
  const current = o.scope === "device" ? (deviceMode() ?? "brand_first") : personMode();
  const one = (m: NamesMode, key: string): string => `<li><button class="choice${m === current ? " current" : ""}" data-act="${nmEsc(o.act)}:${m}" aria-pressed="${m === current}"${o.canChange ? "" : " disabled"}>${nmEsc(say(key))}<span class="names-eg" aria-hidden="true">${nmEsc(labelText("LynkStat", say, m))}</span></button></li>`;
  const keep = o.scope === "person" ? `<label class="switch"><span>${nmEsc(say("nm_familiar"))}</span><input type="checkbox" data-act="${nmEsc(o.act)}:${keepBrackets() ? "fade" : "keep"}" ${keepBrackets() ? "checked" : ""}></label><p class="sub">${nmEsc(say("nm_familiar_note"))}</p>` : "";
  return `<section class="names-choice" data-names="off"><h3>${nmEsc(say("nm_pref_title"))}</h3><ul class="choices">${one("brand_first", "nm_pref_brand")}${one("plain_first", "nm_pref_plain")}</ul><p class="sub">${nmEsc(say("nm_pref_note"))}</p>${o.scope === "device" && !o.canChange ? `<p class="sub">${nmEsc(say("nm_pref_device"))}</p>` : ""}${keep}</section>`;
}
/** Apply a namesChoice act ("<act>:<mode>"); returns true when it was one. */
export function namesAct(a: string, prefix: string, scope: "person" | "device"): boolean {
  if (!a.startsWith(`${prefix}:`)) return false;
  const m = a.slice(prefix.length + 1);
  if (m === "keep" || m === "fade") { setKeepBrackets(m === "keep"); return true; }
  if (m !== "brand_first" && m !== "plain_first") return false;
  if (scope === "device") setDeviceMode(m); else setPersonMode(m);
  return true;
}
/** The two lines a tile or row shows for a name, in the chosen order: { main, sub }. */
export function namePair(name: string, say?: Say, mode: NamesMode = namesMode()): { main: string; sub: string } {
  const p = plainOf(name, say);
  return mode === "plain_first" ? { main: p, sub: name } : { main: name, sub: p };
}


// ---------------------------------------------------------------- the 15 improvements (owner, 21 November 2026, v0.81.0)
/** The product mark a name shows beside it (brand icon id), or null (core/names.py icon_of). */
export const iconOf = (name: string): string | null => NM_BY_NAME.get(name)?.icon ?? null;
/** How to say a name aloud: "Link Stat" (voice menus, LynkAssist's voice, screen readers' note). */
export const spokenOf = (name: string): string => NM_BY_NAME.get(name)?.spoken ?? name;
/** A text ready to be read aloud: every name replaced by its spoken form (core/names.py speakable). */
export const speakable = (text: string): string => text.replace(nmPattern(), (_m, n: string) => spokenOf(n));
/** The name a retired name is now called, or null. */
export function nowCalled(old: string): string | null { const x = NM_REG.now_called.find((y) => y.old === old); return x ? (NM_BY_ID.get(x.id)?.name ?? null) : null; }
/** The registered name of a billing family, or null. */
export function forFamily(family: string): string | null { return NM_REG.names.find((n) => n.family === family)?.name ?? null; }
/** The other names a name could be confused with (core/names.py similar). */
export function similarOf(name: string): string[] {
  const id = NM_BY_NAME.get(name)?.id; const out: string[] = [];
  for (const g of NM_REG.similar) if (id && g.names.includes(id)) for (const x of g.names) { const n = NM_BY_ID.get(x)?.name; if (x !== id && n && !out.includes(n)) out.push(n); }
  return out;
}
/** Why a plain word is not plain enough ([] when it is). */
export function checkPlain(word: string): string[] {
  const c = NM_REG.plain_word_check;
  const bad = (word.match(/(?<![A-Za-z])[A-Z]{2,}(?![A-Za-z])/g) ?? []).filter((x) => !c.allowed_short.includes(x));
  for (const w of c.words_never) if (new RegExp(`(?<![A-Za-z])${w}(?![A-Za-z])`, "i").test(word)) bad.push(w);
  if (word.includes("Lynk")) bad.push("Lynk");
  return [...new Set(bad)].sort();
}
/** A message or document text with the first mention of each name followed by its plain word (core/names.py explain_text).
 *  Pass the same seen set for a title and its lines so each name is explained once in the whole message. */
export function explainText(text: string, say?: Say, mode: NamesMode = "brand_first", seen: Set<string> = new Set()): string {
  return text.replace(nmPattern(), (_m, n: string) => { if (seen.has(n)) return n; seen.add(n); return labelText(n, say, mode); });
}
/** The lines printed paper ends with: one "LynkCheckout: Pay links & QR" line for each name it shows, wrapped to the width. */
export function paperLines(lines: readonly string[], say?: Say, width = 32): string[] {
  const out: string[] = [];
  const names = [...new Set(lines.flatMap((l) => findNames(l).map((f) => f.name)))];
  for (const n of names) {
    let row = "";
    for (const w of `${n}: ${plainOf(n, say)}`.split(" ")) {
      if (row && row.length + 1 + w.length > width) { out.push(row); row = `  ${w}`; } else row = row ? `${row} ${w}` : w;
    }
    out.push(row);
  }
  return out;
}

// ---- how often a person has opened each service (on this device only, never sent), and the brackets stepping back
const NM_SEEN = "lynkomni.names.seen.v1", NM_KEEP = "lynkomni.names.keep.v1", NM_WELCOMED = "lynkomni.names.welcomed.v1", NM_RENAMED = "lynkomni.names.renamed.v1";
const nmMem: Record<string, string> = {};
const nmGet = (k: string): string | null => { try { const v = typeof localStorage !== "undefined" ? localStorage.getItem(k) : null; return v ?? nmMem[k] ?? null; } catch { return nmMem[k] ?? null; } };
const nmSet = (k: string, v: string): void => { nmMem[k] = v; try { if (typeof localStorage !== "undefined") localStorage.setItem(k, v); } catch { /* kept for this visit */ } };
const nmJson = <T>(k: string, d: T): T => { try { return JSON.parse(nmGet(k) ?? "") as T; } catch { return d; } };
// Read once and kept in memory: marking a screen asks for every name it shows, so storage is never read per name.
let nmKeep: boolean | null = null, nmSeen: Record<string, number> | null = null;
export function keepBrackets(): boolean { if (nmKeep === null) nmKeep = nmGet(NM_KEEP) === "1"; return nmKeep; }
export function setKeepBrackets(on: boolean): void { nmKeep = on; nmSet(NM_KEEP, on ? "1" : "0"); }
const nmSeenNow = (): Record<string, number> => (nmSeen ??= nmJson<Record<string, number>>(NM_SEEN, {}));
export function timesOpened(name: string): number { const id = NM_BY_NAME.get(name)?.id; return id ? (nmSeenNow()[id] ?? 0) : 0; }
/** Count one opening of a service (its overview), for the brackets that step back. */
export function nameOpened(name: string): void {
  const id = NM_BY_NAME.get(name)?.id; if (!id) return;
  const seen = nmSeenNow(); seen[id] = (seen[id] ?? 0) + 1; nmSet(NM_SEEN, JSON.stringify(seen));
}
/** A name the person knows well: its brackets step back, its underline and note stay. */
export function familiar(name: string): boolean { return !keepBrackets() && timesOpened(name) >= NM_REG.familiar_after; }

// ---- which names confuse people: counted as totals by name, sent without a person, device, account or time
const nmAsks: Record<string, number> = {};
export function nameAsked(name: string, _place: "note" | "compare" | "what_is" | "search"): void { const id = NM_BY_NAME.get(name)?.id; if (id) nmAsks[id] = (nmAsks[id] ?? 0) + 1; }
/** The totals since the last call, for the cloud (services/name_asks.py); clears them. */
export function takeNameAsks(): Record<string, number> { const out = { ...nmAsks }; for (const k of Object.keys(nmAsks)) delete nmAsks[k]; return out; }

// ---- Which one do I need?
/** The names a name could be confused with, side by side with their plain words and what each does. */
export function compareHtml(name: string, say?: Say, icon?: (id: string) => string): string {
  const all = [name, ...similarOf(name)];
  return `<section class="lcompare" data-names="off"><b>${nmEsc(nmSaid(say, "nm_compare_title") ?? "Which one do I need?")}</b><ul>${all.map((n) => `<li>${nameLabel(n, say, "label", namesMode(), icon)}<span>${nmEsc(aboutOf(n, say))}</span></li>`).join("")}</ul></section>`;
}
/** The comparison of one similar group by its id (search's "open:compare-<id>"). */
export function compareGroupHtml(groupId: string, say?: Say, icon?: (id: string) => string): string {
  const g = NM_REG.similar.find((x) => x.id === groupId); const first = g ? NM_BY_ID.get(g.names[0] ?? "")?.name : undefined;
  return first ? compareHtml(first, say, icon) : "";
}

// ---- the first-time welcome card
export function welcomed(name: string): boolean { return nmJson<string[]>(NM_WELCOMED, []).includes(NM_BY_NAME.get(name)?.id ?? ""); }
export function setWelcomed(name: string): void { const id = NM_BY_NAME.get(name)?.id; if (!id) return; const w = nmJson<string[]>(NM_WELCOMED, []); if (!w.includes(id)) nmSet(NM_WELCOMED, JSON.stringify([...w, id])); }
/** The card shown the first time a person opens a service: its name and plain word, what it does, its first three places to
 *  start and Got it (act "<act>:<id>"). Nothing once it has been closed on this device. */
export function welcomeCard(name: string, say: Say, steps: { label: string; act: string }[], o: { act: string; icon?: (id: string) => string }): string {
  const e = NM_BY_NAME.get(name); if (!e || welcomed(name)) return "";
  const title = nmFill(nmSaid(say, "nm_welcome_title") ?? "Welcome to {name}", { name: "\u0000" });
  const [before, after] = title.split("\u0000");
  return `<section class="card lwelcome" data-item="name_welcome" data-names="off"><h2>${nmEsc(before ?? "")}${nameLabel(name, say, "label", namesMode(), o.icon)}${nmEsc(after ?? "")}</h2><p>${nmEsc(aboutOf(name, say))}</p>${steps.length ? `<p class="sub">${nmEsc(nmSaid(say, "nm_welcome_start") ?? "Start here")}</p><ol class="lsteps">${steps.slice(0, 3).map((s) => `<li>${s.act ? `<button class="secondary" data-act="${nmEsc(s.act)}">${nmEsc(s.label)}</button>` : nmEsc(s.label)}</li>`).join("")}</ol>` : ""}<div class="actions"><button class="primary" data-act="${nmEsc(o.act)}:${e.id}">${nmEsc(nmSaid(say, "nm_got_it") ?? "Got it")}</button></div></section>`;
}
/** Apply a welcome act ("<prefix>:<id>"); returns true when it was one. */
export function welcomeAct(a: string, prefix: string): boolean {
  if (!a.startsWith(`${prefix}:`)) return false;
  const n = NM_BY_ID.get(a.slice(prefix.length + 1))?.name; if (n) setWelcomed(n);
  return !!n;
}

// ---- Names A to Z
/** Every name with its plain word, what it does and the names it could be confused with, A to Z. */
export function namesIndexHtml(say?: Say, icon?: (id: string) => string): string {
  const all = [...NM_REG.names].sort((a, b) => a.name.localeCompare(b.name, "en"));
  return `<section class="lindex" data-names="off"><h2>${nmEsc(nmSaid(say, "nm_az_title") ?? "Names A to Z")}</h2><p class="sub">${nmEsc(nmSaid(say, "nm_az_note") ?? "")}</p><ul class="list card">${all.map((n) => `<li id="name-${n.id}"><div class="rowbtn static"><span class="main"><span class="nm">${nameLabel(n.name, say, "label", namesMode(), icon)}</span>${aboutOf(n.name, say) ? `<span class="sub">${nmEsc(aboutOf(n.name, say))}</span>` : ""}</span></div></li>`).join("")}</ul></section>`;
}

// ---- "now called": a one-time notice for people whose account is older than a name change
/** The notices of name changes made after the account's first day (YYYY-MM-DD) and not yet closed; act "<act>:<old>". */
export function renameNotices(say: Say, accountSince: string, o: { act: string }): string {
  const closed = nmJson<string[]>(NM_RENAMED, []);
  return NM_REG.now_called.filter((x) => x.since > accountSince && !closed.includes(x.old)).map((x) => {
    const n = NM_BY_ID.get(x.id)?.name ?? "";
    return `<section class="card lrenamed" data-item="name_renamed" data-names="off" data-names-old="${nmEsc(x.old)}"><p>${nmEsc(nmFill(nmSaid(say, "nm_renamed") ?? "{old} has a new name: {name}. Nothing else changes.", { old: x.old, name: labelText(n, say, namesMode()) }))}</p><div class="actions"><button class="secondary" data-act="${nmEsc(o.act)}:${nmEsc(x.old)}">${nmEsc(nmSaid(say, "nm_got_it") ?? "Got it")}</button></div></section>`;
  }).join("");
}
export function renameAct(a: string, prefix: string): boolean {
  if (!a.startsWith(`${prefix}:`)) return false;
  const old = a.slice(prefix.length + 1); if (!NM_REG.now_called.some((x) => x.old === old)) return false;
  const c = nmJson<string[]>(NM_RENAMED, []); if (!c.includes(old)) nmSet(NM_RENAMED, JSON.stringify([...c, old]));
  return true;
}

/** The Names A to Z sheet (search, help and LynkAssist open it): a comparison first when focus is "compare-<group>", then every
 *  name A to Z; focus "name-<id>" is scrolled to by the page after drawing (focusName). */
export function namesSheet(say: Say, focus: string, o: { close: string; icon?: (id: string) => string }): string {
  const compare = focus.startsWith("compare-") ? compareGroupHtml(focus.slice(8), say, o.icon) : "";
  return `<div class="sheet names-sheet" role="dialog" aria-label="${nmEsc(nmSaid(say, "nm_az_title") ?? "Names A to Z")}">${compare}${namesIndexHtml(say, o.icon)}<button class="secondary" data-act="${nmEsc(o.close)}">${nmEsc(nmSaid(say, "nm_got_it") ?? "Got it")}</button></div>`;
}
/** What a search, help or LynkAssist act asks the Names sheet to show ("" for the list, "name-<id>", "compare-<group>"), or null. */
export function namesFocusOf(a: string): string | null {
  if (a === "open:names-az" || a === "help:article:names") return "";
  const m = /^open:((?:name|compare)-[a-z_]+)$/.exec(a); if (!m) return null;
  const f = m[1] as string;
  const id = f.startsWith("name-") ? f.slice(5) : null;
  if (id && NM_BY_ID.get(id)) nameAsked(NM_BY_ID.get(id)?.name ?? "", "search");
  return f;
}
/** Scroll the Names sheet to the name in focus, once it is drawn. */
export function focusName(doc: Document, focus: string): void { if (focus.startsWith("name-")) doc.getElementById(focus)?.scrollIntoView({ block: "center" }); }
/** The groups of names that sound alike, and the old names now called something else (for LynkAssist's pack). */
export const similarGroups = (): readonly { id: string; names: string[] }[] => NM_REG.similar;
export const renamedNames = (): readonly { old: string; id: string; since: string }[] => NM_REG.now_called;
