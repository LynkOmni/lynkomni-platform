// Placeholders done properly (PLACEHOLDER UPDATE, owner 2026-11-19, master blueprint section 83; rules in
// catalog/placeholders.v1.json, checked by tests/test_placeholders.py). Three parts, shared by every screen:
//  1. Loading skeletons shaped like the real content, so nothing jumps when it arrives. They appear only when loading takes
//     longer than a moment, stay at least a moment once shown, and turn into a "taking longer" note with Retry when slow.
//  2. Field hints: an example of what to type, never the instruction (the label stays visible). Sensitive fields get none.
//  3. Designed empty states come from shell.ts state(); this file only decides when loading becomes one of them.
// Cached content is always shown first; a skeleton is only for content the device has never had.

/** The shapes a skeleton can take: one per page template and part. */
export type SkeletonShape = "list" | "cards" | "record" | "form" | "table" | "chart" | "chat" | "tracker" | "tiles" | "media" | "text";
export const SHAPES: readonly SkeletonShape[] = ["list", "cards", "record", "form", "table", "chart", "chat", "tracker", "tiles", "media", "text"];

/** Timing (ms): nothing before SHOW_AFTER (no flash), at least MIN_SHOW once shown, a "taking longer" note after SLOW_AFTER. */
export const TIMING = { SHOW_AFTER: 300, MIN_SHOW: 300, SLOW_AFTER: 8000 } as const;

export type Phase = "nothing" | "skeleton" | "slow";
/** What a screen shows while it waits: pure, so every device and the tests agree. */
export function loadingPhase(elapsedMs: number, cached: boolean): Phase {
  if (cached) return "nothing";                         // cached content stays on screen; a quiet "Updating" chip may show
  if (elapsedMs < TIMING.SHOW_AFTER) return "nothing";
  return elapsedMs < TIMING.SLOW_AFTER ? "skeleton" : "slow";
}
/** How long a skeleton that was shown must stay before the content replaces it (never a flash). */
export function holdFor(shownAtMs: number, nowMs: number): number {
  return Math.max(0, TIMING.MIN_SHOW - (nowMs - shownAtMs));
}

const phEsc = (s: string) => s.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c] as string));
const phBar = (cls: string) => `<span class="skel ${cls}" aria-hidden="true"></span>`;

/** A skeleton in the shape of the content to come. count = how many rows or cards the screen showed last time (default 3).
 *  One polite "Loading" for the whole block; screen readers never hear each grey bar. */
export function skeletonHtml(shape: SkeletonShape, loadingWord: string, count = 3): string {
  const n = Math.max(1, Math.min(count, 12));
  const rep = (f: () => string) => Array.from({ length: n }, f).join("");
  const body: Record<SkeletonShape, () => string> = {
    list: () => rep(() => `<span class="skel-row">${phBar("dot")}<span class="skel-col">${phBar("line")}${phBar("line short")}</span></span>`),
    cards: () => `<span class="skel-grid">${rep(() => `<span class="skel-card">${phBar("media")}${phBar("line")}${phBar("line short")}</span>`)}</span>`,
    record: () => `${phBar("title")}${phBar("line short")}${rep(() => `<span class="skel-pair">${phBar("label")}${phBar("line")}</span>`)}`,
    form: () => rep(() => `<span class="skel-field">${phBar("label")}${phBar("input")}</span>`) + phBar("button"),
    table: () => `<span class="skel-table">${rep(() => `<span class="skel-tr">${phBar("cell")}${phBar("cell")}${phBar("cell")}</span>`)}</span>`,
    chart: () => `<span class="skel-chart">${phBar("axis")}${rep(() => phBar("col"))}</span>`,
    chat: () => rep(() => `<span class="skel-msg">${phBar("bubble")}</span>`),
    tracker: () => `<span class="skel-steps">${rep(() => `<span class="skel-step">${phBar("dot")}${phBar("line short")}</span>`)}</span>`,
    tiles: () => `<span class="skel-grid">${rep(() => `<span class="skel-tile">${phBar("label")}${phBar("figure")}</span>`)}</span>`,
    media: () => phBar("media"),
    text: () => rep(() => phBar("line")) + phBar("line short"),
  };
  return `<div class="skeleton skel-${shape}" role="status" aria-busy="true" aria-live="polite" aria-label="${phEsc(loadingWord)}" data-skeleton="${shape}">${body[shape]()}</div>`;
}

// Field hints live in ts/src/hints.ts (a small part of their own).

/** Cached content stays on screen while it refreshes; a quiet chip says so (83.4 and 83.7), never a skeleton over content already there. */
export function updatingChip(updatingWord: string): string {
  return `<span class="ph-updating" role="status" aria-live="polite">${phEsc(updatingWord)}</span>`;
}

/** The calm end of a list that loads more (83.7): skeleton rows while the next part comes, then "That's everything". */
export function listEnd(more: "loading" | "done", t: (k: string) => string): string {
  return more === "loading" ? skeletonHtml("list", t("loading")) : `<p class="ph-end" role="status">${phEsc(t("ph_all_loaded"))}</p>`;
}

/** A button that started something waiting on the cloud keeps its width and says it is working (83.4): nothing beside it moves. */
export function markBusy(btn: HTMLElement, workingWord: string): void {
  if (btn.getAttribute("aria-busy") === "true") return;
  btn.style.minInlineSize = `${btn.getBoundingClientRect().width}px`;
  btn.setAttribute("aria-busy", "true");
  const own = btn.getAttribute("aria-label");
  if (own !== null) btn.dataset["label0"] = own;
  btn.setAttribute("aria-label", `${own ?? btn.textContent?.trim() ?? ""} · ${workingWord}`);
  if (btn instanceof HTMLButtonElement) btn.disabled = true;
}


/** Gives a busy button back as it was. */
export function clearBusy(btn: HTMLElement): void {
  btn.removeAttribute("aria-busy"); btn.style.minInlineSize = "";
  const own = btn.dataset["label0"];
  if (own !== undefined) { btn.setAttribute("aria-label", own); delete btn.dataset["label0"]; } else btn.removeAttribute("aria-label");
  if (btn instanceof HTMLButtonElement) btn.disabled = false;
}

const BUSY_MAX_MS = 8000;
/** A button marked data-wait (it asks the cloud) keeps its width and says it is working until the screen draws again (83.4). */
export function wireBusy(root: Document | HTMLElement, t: (k: string) => string): void {
  // the action always runs first; the button turns busy only afterwards
  root.addEventListener("click", (e) => {
    const b = (e.target as HTMLElement | null)?.closest?.<HTMLElement>("[data-wait]");
    if (!b || b.hasAttribute("disabled")) return;
    // after every other handler of this click has run (they skip a disabled button): a screen that drew again leaves b detached
    window.setTimeout(() => { if (b.isConnected && !b.hasAttribute("disabled")) markBusy(b, t("ph_working")); }, 0);
    // a screen that answered without drawing again (offline, a refusal) gets its button back; nothing stays stuck
    if (typeof window !== "undefined") window.setTimeout(() => { if (b.isConnected) clearBusy(b); }, BUSY_MAX_MS);
  });
}

/** The content area of a screen (the part that waits; the header, menus and buttons stay). Its shape is data-shape, else a list. */
export const WAIT_AREA = ".body, .rbody, .qp-body, .sp-body, .home, .tiles12, .display-main, [data-wait-area]";
/** How long content takes to arrive in the demo when the link is up (the tester condition "First open"). */
export const ARRIVES_MS = 900;
/** The Retry act of a page without the kit (the kit uses its own, emk:retry). */
export const PAGE_RETRY = "ph:retry";
const UPDATING_MS = 1200;
export type WaitLook = { t: (k: string) => string; online: () => boolean; redraw: () => void; retryAct: string; retryClass: string; area?: string };

/** Waiting well on any page (PLACEHOLDER UPDATE 83). The first open on a device, nothing saved yet: each screen's content area
 *  waits (about 0.9 s online, never offline): nothing new before 300 ms, then a skeleton shaped like the content for at least
 *  300 ms, and after 8 s a calm "taking longer" note with Retry. A screen seen once opens from the device's copy at once. When the
 *  link comes back the screen keeps what it shows and a quiet Updating chip stands for about a second. Call apply() at the end of
 *  every draw; Retry is the act named in retryAct and calls retry(). */
/** The tester condition's word: the panel control "First open on this device (nothing saved yet)". */
export const FIRST_OPEN_WORD = "emk_first_open";

export class PageWait {
  firstOpen = false;
  private wired = false;
  loaded = new Set<string>();
  loading = new Map<string, { start: number; shown: number | null }>();
  wasOffline = false;
  updatingUntil = 0;
  setFirstOpen(on: boolean): void { this.firstOpen = on; this.loaded.clear(); this.loading.clear(); }
  retry(): void { this.loading.clear(); }                            // online it arrives, offline it waits again

  apply(screen: HTMLElement, o: WaitLook): void { this.wire(o); this.waitFor(screen, o); this.refreshing(screen, o); enhanceFields(screen, o.t); }

  /** Once per page: Retry starts the wait again and buttons that ask the cloud keep their width while working. */
  private wire(o: WaitLook): void {
    if (this.wired || typeof document === "undefined") return;
    this.wired = true;
    document.addEventListener("click", (e) => {
      const b = (e.target as HTMLElement | null)?.closest?.<HTMLElement>("[data-act]");
      if (b && b.dataset["act"] === o.retryAct && o.retryAct === PAGE_RETRY) { e.stopImmediatePropagation(); this.retry(); o.redraw(); }
    }, true);
    if (o.retryAct === PAGE_RETRY) wireBusy(document, o.t);         // the kit wires its own busy buttons
  }

  private waitFor(screen: HTMLElement, o: WaitLook): void {
    if (!this.firstOpen) return;
    const area = screen.querySelector<HTMLElement>(o.area ?? WAIT_AREA);
    if (!area) return;
    const key = (screen.querySelector("h1, h2")?.textContent ?? "") + "|" + (area.className || "main");
    if (this.loaded.has(key)) return;
    const now = Date.now(), w = this.loading.get(key) ?? { start: now, shown: null };
    this.loading.set(key, w);
    const elapsed = now - w.start, online = o.online();
    if (online && elapsed >= ARRIVES_MS && holdFor(w.shown ?? now, now) === 0) { this.loaded.add(key); this.loading.delete(key); return; }
    const phase = loadingPhase(elapsed, false);
    const shape = (area.dataset["shape"] as SkeletonShape | undefined) ?? "list";
    if (phase === "nothing") area.style.visibility = "hidden";        // nothing new before 300 ms, and nothing jumps
    else {
      if (w.shown === null) w.shown = now;
      area.innerHTML = skeletonHtml(shape, o.t("loading")) + (phase === "slow"
        ? `<p class="ph-slow" role="status">${phEsc(o.t("ph_slow"))} <button type="button" class="${phEsc(o.retryClass)}" data-act="${phEsc(o.retryAct)}">${phEsc(o.t("action_retry"))}</button></p>` : "");
    }
    const next = phase === "nothing" ? TIMING.SHOW_AFTER - elapsed : online ? Math.max(ARRIVES_MS - elapsed, holdFor(w.shown ?? now, now), 50) : TIMING.SLOW_AFTER - elapsed;
    if (next > 0 && typeof window !== "undefined") window.setTimeout(() => o.redraw(), next + 5);
  }

  private refreshing(screen: HTMLElement, o: WaitLook): void {
    const online = o.online(), now = Date.now();
    if (!online) { this.wasOffline = true; return; }
    if (this.wasOffline) { this.wasOffline = false; this.updatingUntil = now + UPDATING_MS; if (typeof window !== "undefined") window.setTimeout(() => o.redraw(), UPDATING_MS + 10); }
    if (now >= this.updatingUntil) return;
    const area = screen.querySelector<HTMLElement>(o.area ?? WAIT_AREA) ?? screen;
    area.insertAdjacentHTML("afterbegin", updatingChip(o.t("ph_updating")));
  }
}

// ---- 83.7: fields that help while people type (applied by every page's wait step, so no screen can forget them) ----------
const PH_SENSITIVE = 'input[type="password"], [data-sensitive], [autocomplete="one-time-code"]';
const phStore = (): Storage | null => { try { return typeof localStorage === "undefined" ? null : localStorage; } catch { return null; } };
const phReadList = (k: string): string[] => { try { const v = JSON.parse(phStore()?.getItem(k) ?? "[]"); return Array.isArray(v) ? v.filter((x): x is string => typeof x === "string").slice(0, RECENT_MAX) : []; } catch { return []; } };
const phWrite = (k: string, v: string | null): void => { try { const s = phStore(); if (!s) return; if (v === null) s.removeItem(k); else s.setItem(k, v); } catch { /* storage full or blocked: typing goes on */ } };
/** How many recent searches a box keeps. */
export const RECENT_MAX = 5;
const phFormats = new Map<string, Intl.NumberFormat>();
const phNum = (n: number, el: Element): string => {
  const lang = el.closest("[lang]")?.getAttribute("lang") ?? "";
  try { let f = phFormats.get(lang); if (!f) { f = new Intl.NumberFormat(lang || undefined); phFormats.set(lang, f); } return f.format(n); } catch { return String(n); }
};
const phRestored = new Set<string>();
let phFieldsWired = false;

/** The counter beside a field with a limit: how many of how many, in the reader's own digits. A box whose length is its
 *  format (the day, month and year of a date) carries data-count="off" and shows none. */
export function counterText(len: number, max: number, el: Element): string { return `${phNum(len, el)} / ${phNum(max, el)}`; }

/** Drafts are kept only for a person's own typing on their own device or a staff screen, never on an answer a customer types on a
 *  shared device (the next person must never see it), and never for a sensitive field. */
/** Run after every draw: counters, reasons on disabled fields, drafts offered back and recent searches. */
export function enhanceFields(root: HTMLElement, t: (k: string) => string): void {
  if (typeof document === "undefined") return;
  phWireFields(t);
  for (const box of root.getElementsByClassName("ph-pic")) phPicture(box as HTMLElement);
  // one pass over the form fields only (most screens have few or none), so a draw stays inside its tap budget
  const fields = root.getElementsByTagName("input").length + root.getElementsByTagName("textarea").length + root.getElementsByTagName("select").length;
  if (!fields) return;
  for (const el of root.querySelectorAll<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>("input, textarea, select")) {
    if (el.hasAttribute("maxlength") && el.getAttribute("data-count") !== "off" && !(el instanceof HTMLSelectElement) && !el.matches(PH_SENSITIVE) && !el.nextElementSibling?.classList.contains("ph-count")) {
      const max = Number(el.getAttribute("maxlength"));
      if (max > 0) el.insertAdjacentHTML("afterend", `<span class="ph-count" aria-hidden="true">${phEsc(counterText(el.value.length, max, el))}</span>`);
    }
    if (el.disabled && el.dataset["why"]) phWhy(root, el, t);
    if (el.dataset["draft"] && !(el instanceof HTMLSelectElement)) phDraft(el, t);
    if (el instanceof HTMLInputElement && el.type === "search" && el.dataset["recents"] !== undefined) phShowRecents(el, t);
  }
}

function phWhy(root: HTMLElement, el: HTMLElement, t: (k: string) => string): void {
  const why = el.dataset["why"] ?? ""; if (why === "shown" || !why) return;          // "shown": the reason already stands beside it
  const group = el.closest(".card, section, fieldset, ul, form") ?? root;   // one reason per card, shared by its switches
  const same = [...group.querySelectorAll<HTMLElement>(".ph-why")].find((w) => w.dataset["why"] === why);
  if (same) { el.setAttribute("aria-describedby", same.id); return; }
  const id = `why-${Math.random().toString(36).slice(2, 9)}`;
  const at = el.closest("li") ?? el.closest("label") ?? el;
  at.insertAdjacentHTML("afterend", at.tagName === "LI" ? `<li class="ph-whyrow"><span class="ph-why" id="${id}" data-why="${phEsc(why)}">${phEsc(t(why))}</span></li>` : `<span class="ph-why" id="${id}" data-why="${phEsc(why)}">${phEsc(t(why))}</span>`);
  el.setAttribute("aria-describedby", id);
}

function phDraft(el: HTMLInputElement | HTMLTextAreaElement, t: (k: string) => string): void {
  const k = `lynk.draft.${el.dataset["draft"]}`;
  if (el.value) return;
  if (phRestored.has(k)) { phWrite(k, null); return; }                // emptied by the screen after the first open: sent or thrown away
  phRestored.add(k);
  let kept = ""; try { kept = phStore()?.getItem(k) ?? ""; } catch { kept = ""; }
  if (!kept) return;
  el.value = kept;
  el.dispatchEvent(new Event("input", { bubbles: true }));                // the screen's own state takes the kept words
  el.insertAdjacentHTML("afterend", `<span class="ph-draft" role="status">${phEsc(t("ph_draft_kept"))}</span>`);
}

/** The chips go below the search bar's own row (never inside it, so nothing beside the box is squeezed). */
const phAnchor = (el: HTMLElement): HTMLElement => el.closest<HTMLElement>(".cmd-input, .pk-search, .askbox .cmd-input") ?? el;
function phShowRecents(el: HTMLInputElement, t: (k: string) => string): void {
  const at = phAnchor(el), next = at.nextElementSibling;
  if (next?.classList.contains("ph-recents")) next.remove();
  if (el.value || document.activeElement !== el) return;
  const recent = phReadList(`lynk.recent.${el.dataset["recents"]}`);
  let given: unknown = []; try { given = JSON.parse(el.dataset["suggest"] ?? "[]"); } catch { given = []; }
  const suggest = (Array.isArray(given) ? given : []).filter((s): s is string => typeof s === "string" && !!s && !recent.includes(s));
  if (!recent.length && !suggest.length) return;
  const chip = (s: string): string => `<button type="button" class="ph-chip" data-fill="${phEsc(s)}">${phEsc(s)}</button>`;
  at.insertAdjacentHTML("afterend", `<div class="ph-recents">${recent.length ? `<span class="ph-rlabel">${phEsc(t("ph_recent"))}</span>${recent.map(chip).join("")}` : ""}${suggest.length ? `<span class="ph-rlabel">${phEsc(t("ph_suggested"))}</span>${suggest.slice(0, 4).map(chip).join("")}` : ""}</div>`);
}

/** Remembers a search in its box's recent list (newest first, at most RECENT_MAX, never twice). */
export function rememberSearch(scope: string, query: string): void {
  const q = query.trim(); if (!q) return;
  const k = `lynk.recent.${scope}`;
  phWrite(k, JSON.stringify([q, ...phReadList(k).filter((x) => x !== q)].slice(0, RECENT_MAX)));
}

function phWireFields(t: (k: string) => string): void {
  if (phFieldsWired) return;
  phFieldsWired = true;
  document.addEventListener("input", (e) => {
    const el = e.target as HTMLInputElement | HTMLTextAreaElement | null;
    if (!el?.matches?.("input, textarea")) return;
    const c = el.nextElementSibling;
    if (c?.classList.contains("ph-count")) c.textContent = counterText(el.value.length, Number(el.getAttribute("maxlength")), el);
    if (el.dataset["draft"] && !el.matches(PH_SENSITIVE)) phWrite(`lynk.draft.${el.dataset["draft"]}`, draftSafe(el.value) || null);
    if (el.matches('input[type="search"][data-recents]')) phShowRecents(el as HTMLInputElement, t);
  });
  document.addEventListener("focusin", (e) => { const el = e.target as HTMLInputElement | null; if (el?.matches?.('input[type="search"][data-recents]')) phShowRecents(el, t); });
  document.addEventListener("keydown", (e) => { const el = e.target as HTMLInputElement | null; if (e.key === "Enter" && el?.matches?.('input[type="search"][data-recents]')) rememberSearch(el.dataset["recents"] ?? "", el.value); });
  document.addEventListener("click", (e) => {
    const up = (e.target as HTMLElement | null)?.closest?.<HTMLElement>('[data-act="ph:plans"]');
    if (up) {                                                              // Upgrade: where the owner changes the plan, said beside the button
      e.stopImmediatePropagation();
      const box = up.closest(".ph-plan");
      if (box && !box.querySelector(".ph-where")) up.insertAdjacentHTML("afterend", `<p class="ph-where" role="status">${phEsc(t("ph_plans_where"))}</p>`);
      return;
    }
    const b = (e.target as HTMLElement | null)?.closest?.<HTMLElement>(".ph-recents [data-fill]"); if (!b) return;
    const prev = b.closest(".ph-recents")?.previousElementSibling as HTMLElement | null;
    const box = prev?.matches('input[type="search"]') ? (prev as HTMLInputElement) : prev?.querySelector<HTMLInputElement>('input[type="search"]') ?? null; if (!box) return;
    box.value = b.dataset["fill"] ?? ""; rememberSearch(box.dataset["recents"] ?? "", box.value);
    box.dispatchEvent(new Event("input", { bubbles: true })); box.focus();
  });
}

/** What a draft may keep on the device: a long run of digits (a card or account number, a code) is masked first, as chat does. */
export function draftSafe(v: string): string { return v.replace(/\d(?:[ -]?\d){7,}/g, (m) => "•".repeat(Math.min(m.replace(/\D/g, "").length, 19))); }

/** A draft is sent or thrown away: forget it on the device. */
export function clearDraft(key: string): void { phWrite(`lynk.draft.${key}`, null); }

// ---- 83.7: what a screen shows instead of a gap (upgrade previews, logos waiting their check, pictures, uploads) ---------
/** A feature on a higher plan, on a staff screen: what it does and Upgrade, never a hidden or broken screen (never inside a
 *  payment, count or signature, and never on a customer's screen, where only the reason shows). The Upgrade answer says where
 *  the owner changes the plan (Business settings, Plans). */
export function planPreviewHtml(t: (k: string) => string, reasonKey: string, whatKey: string): string {
  return `<div class="ph-plan" role="note"><p>${phEsc(t(reasonKey))}</p><p class="ph-what"><strong>${phEsc(t("ph_what"))}</strong> ${phEsc(t(whatKey))}</p><button type="button" class="ph-upgrade" data-act="ph:plans">${phEsc(t("ph_upgrade"))}</button></div>`;
}

/** A business's initials, shown wherever its logo goes while the logo waits for its check (services/merchant_logo.py). */
export function initialsOf(name: string): string {
  const words = name.trim().split(/[\s._-]+/u).filter(Boolean);
  const first = (w: string | undefined): string => (w ? Array.from(w)[0] ?? "" : "");
  return (first(words[0]) + (words.length > 1 ? first(words[words.length - 1]) : "")).toLocaleUpperCase();
}
export function logoInitialsHtml(name: string, t: (k: string) => string): string {
  return `<span class="ph-initials" role="img" aria-label="${phEsc(name)}">${phEsc(initialsOf(name))}</span><span class="ph-why">${phEsc(t("ph_logo_checking"))}</span>`;
}

/** Every picture keeps its shape while it loads and, if it fails, shows a token-coloured stand-in with its alt text, never a
 *  broken-image icon. Only a picture carried inside the page (a data: address) is ever shown: nothing loads from the web. The box
 *  is drawn here; enhanceFields puts the picture into it after the draw. */
export function pictureHtml(src: string, alt: string, ratio = "16 / 9"): string {
  return `<span class="ph-pic" role="img" aria-label="${phEsc(alt)}" style="aspect-ratio: ${phEsc(ratio)}" data-alt="${phEsc(alt)}" data-src="${phEsc(src)}"></span>`;
}

function phPicture(box: HTMLElement): void {
  if (box.firstElementChild) return;
  const src = box.dataset["src"] ?? "";
  if (!src.startsWith("data:image/")) { box.classList.add("ph-failed"); return; }        // never a web address
  const pic = document.createElement("img");
  pic.alt = ""; pic.decoding = "async";                                                 // the box carries the description
  pic.addEventListener("error", () => box.classList.add("ph-failed"), { once: true });
  pic.src = src;
  box.appendChild(pic);
}

/** An upload shows the file's own name and real progress, and waits queued when offline (the five states only). */
export function uploadHtml(name: string, percent: number, state: "queued" | "sent" | "accepted" | "confirmed" | "failed", t: (k: string) => string): string {
  const p = Math.max(0, Math.min(100, Math.round(percent)));
  return `<div class="ph-upload" data-state="${state}"><span class="ph-uname">${phEsc(name)}</span><progress max="100" value="${p}" aria-label="${phEsc(name)}">${p}%</progress><span class="ph-ustate">${phEsc(t(`st_${state}`))}</span></div>`;
}
