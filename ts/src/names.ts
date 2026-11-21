/** Every Lynk name carries its plain word (owner, 21 November 2026; catalog/names.v1.json, core/names.py).
 *
 *  - nameLabel draws a name where the screen lists it (menus, launcher, search, pricing, cards, headers).
 *  - explainNames marks every name a screen shows: the first mention on a screen in running text gets its plain word in
 *    brackets; every other mention is marked and explains itself on hover, focus and long press. Receipts, printed paper,
 *    the copyright line, what people type, code and any area marked data-names="off" are left as they are.
 *  - watchNames runs explainNames whenever a screen redraws, so no screen has to remember to.
 *  Names are the same in every language; plain words (web/names, nm_<id>) and descriptions (web/nameinfo, nma_<id>) are
 *  translated. A person may choose plain words first; the owner may switch it on for the business's devices. */
import { NAMES_EN, NAMES_REG } from "./names.generated.js";

export type Say = (key: string, vars?: Record<string, string | number>) => string;
export type NamesMode = "brand_first" | "plain_first";
export interface NameEntry { id: string; name: string; kind: "product" | "service" | "feature" | "card_group" | "device"; family?: string; part_of?: string; about?: boolean }
export interface NamesRegister { max_plain_chars: number; company: string[]; internal: string[]; retired: string[]; names: NameEntry[] }
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
export function nameLabel(name: string, say?: Say, place: NamePlace = "label", mode: NamesMode = namesMode()): string {
  const e = NM_BY_NAME.get(name); if (!e) return nmEsc(name);
  const p = plainOf(name, say);
  const attrs = `class="lname lname-${place}${mode === "plain_first" ? " lname-pf" : ""}" data-lname="${nmEsc(name)}"`;
  if (place === "compact") return `<span ${attrs} title="${nmEsc(p)}">${nmEsc(name)}</span>`;
  const nm = `<span class="lnm">${nmEsc(name)}</span>`, pl = `<span class="lpl">${nmEsc(p)}</span>`;
  return `<span ${attrs}>${mode === "plain_first" ? `${pl} ${nm}` : `${nm} ${pl}`}</span>`;
}
/** Search entries for every name: found by its name, its plain word or its description, in the screen's language and in
 *  English (the shell's search() ranks them). */
export function nameEntries(say?: Say, mode: NamesMode = namesMode(), act?: string): { id: string; kind: "help"; title: string; subtitle: string; keywords: string[]; act: string }[] {
  return NM_REG.names.filter((n) => n.kind !== "device").map((n) => {
    const p = plainOf(n.name, say), a = aboutOf(n.name, say);
    return { id: `name:${n.id}`, kind: "help" as const, title: mode === "plain_first" ? `${p} (${n.name})` : `${n.name} (${p})`, subtitle: a,
      keywords: [p, a, NAMES_EN.plain[`nm_${n.id}`] ?? "", NAMES_EN.about[`nma_${n.id}`] ?? ""].filter(Boolean), act: act ?? `open:name-${n.id}` };
  });
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
  for (let n = walker.nextNode(); n; n = walker.nextNode()) {
    const t = n as Text, el = t.parentElement;
    if (!el || !t.data.includes("Lynk") || el.closest(NM_SKIP)) continue;
    const found = findNames(t.data);
    if (!found.length) continue;
    const cs = view?.getComputedStyle(el);
    const row = !!cs && cs.whiteSpace.startsWith("nowrap") && cs.overflowX !== "visible";   // a one-line row that cuts its text: mark the row itself
    const hits = row ? found.map((f) => ({ ...f, block: null, control: null, screen: doc.body, nearby: "", oneLine: true, shownBefore: false })) : found.map((f) => {
      const block = el.closest(NM_RUNNING), control = el.closest(NM_CONTROL), screen = el.closest(NM_SCREEN) ?? doc.body;
      const bcs = block ? view?.getComputedStyle(block) : null;
      const oneLine = !!bcs && (bcs.whiteSpace.startsWith("nowrap") || bcs.whiteSpace === "pre" || bcs.textOverflow === "ellipsis");   // no room to add words
      return { ...f, block, control, screen, nearby: ((control ?? block ?? el).textContent ?? "").toLowerCase(), oneLine,
               shownBefore: !!screen.querySelector(`.lname-shown[data-lname="${f.name}"]`) };
    });
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
      const show = !!h.block && !h.control && !said && !h.oneLine && !h.shownBefore && !seen.has(h.name);
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
  if (!Obs) return () => undefined;
  let busy = false;
  const obs = new Obs((records) => {
    if (busy) return;
    busy = true;
    try {
      for (const r of records) for (const n of Array.from(r.addedNodes)) {
        if (n.nodeType === 1) explainNames(n as Element, say(), mode());
        else if (n.nodeType === 3 && n.parentElement) explainNames(n.parentElement, say(), mode());
      }
      for (const r of records) if (r.type === "characterData" && r.target.parentElement) explainNames(r.target.parentElement, say(), mode());
    } finally { obs.takeRecords(); busy = false; }
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
    tip.innerHTML = `<b>${nmEsc(labelText(name, s, namesMode()))}</b>${aboutOf(name, s) ? `<span>${nmEsc(aboutOf(name, s))}</span>` : ""}${part ? `<small>${nmEsc((s?.("nm_part_of") ?? "Part of {name}").replace("{name}", part))}</small>` : ""}`;
    const r = span.getBoundingClientRect(), view = doc.defaultView;
    const w = view?.innerWidth ?? 360, h = view?.innerHeight ?? 640;
    tip.style.insetInlineStart = `${Math.max(8, Math.min(r.left, w - 288))}px`;
    tip.style.top = `${r.bottom + 6 > h - 96 ? Math.max(8, r.top - 96) : r.bottom + 6}px`;
    doc.body.append(tip);
    closeTimer = setTimeout(close, 6000);
  };
  root.addEventListener("pointerdown", (e) => {
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
  return `<section class="names-choice" data-names="off"><h3>${nmEsc(say("nm_pref_title"))}</h3><ul class="choices">${one("brand_first", "nm_pref_brand")}${one("plain_first", "nm_pref_plain")}</ul><p class="sub">${nmEsc(say("nm_pref_note"))}</p>${o.scope === "device" && !o.canChange ? `<p class="sub">${nmEsc(say("nm_pref_device"))}</p>` : ""}</section>`;
}
/** Apply a namesChoice act ("<act>:<mode>"); returns true when it was one. */
export function namesAct(a: string, prefix: string, scope: "person" | "device"): boolean {
  if (!a.startsWith(`${prefix}:`)) return false;
  const m = a.slice(prefix.length + 1);
  if (m !== "brand_first" && m !== "plain_first") return false;
  if (scope === "device") setDeviceMode(m); else setPersonMode(m);
  return true;
}
/** The two lines a tile or row shows for a name, in the chosen order: { main, sub }. */
export function namePair(name: string, say?: Say, mode: NamesMode = namesMode()): { main: string; sub: string } {
  const p = plainOf(name, say);
  return mode === "plain_first" ? { main: p, sub: name } : { main: name, sub: p };
}
