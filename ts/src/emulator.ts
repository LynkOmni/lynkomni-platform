import type { BrandPlaces } from "./brand.js";
/** Shared runtime of every real-device emulator (build section 3): screen words in every language, the country chooser, money
 *  and clock formatting through the country pack, the event log with the five honest states and the sandbox cloud's answers.
 *  Each emulator keeps its own state and screens; this file keeps them consistent. No Node APIs; the DOM parts take elements. */
import { formatMoney, uuid7 } from "./pos.js";
import { buildFooter, mainFooterHtml, shortFooterHtml } from "./footer.js";
import type { UserState } from "./pos.js";

export interface CountryPack { code: string; name: string; currency: string; tz: string; locale: string; ui: string; sample: boolean; card_networks: string[]; wallets: string[]; providers: string[];
  ready: Record<string, { ok: boolean; message: string }>; services: { service: string; name: string; icon: string; state: "available" | "coming_soon" }[] }
export interface LanguagePack { native: string; dir: "ltr" | "rtl"; texts: Record<string, string> }
export interface Build { icons: Record<string, string>; statePictures: Record<string, Record<string, { svg: string; alt: string }>>; brand: { body: string; receipt: string; places: BrandPlaces }; pictures: { offLight: string; offDark: string; offAlt: string };
  states: Record<string, { label: string; meaning: string }>; packs: Record<string, CountryPack>; packOrder: string[]; i18n: Record<string, LanguagePack>;
  entitlements?: Record<string, Record<string, unknown>> }

export const TEST_LANGS = ["xx", "xx-rtl"] as const;      // long-text test and right-to-left test: never shown to real users
const PSEUDO: Record<string, string> = { a: "à", c: "ç", e: "é", i: "î", n: "ñ", o: "ö", s: "š", u: "ü", y: "ý" };
/** The same pseudo-translation as services/translation.py: accented letters and about 40% more length, to prove screens never break. */
export const pseudo = (s: string): string => `[${s.split(/(\{\w+\})/).map((part) => (part.startsWith("{") ? part : part.replace(/[aceinosuy]/g, (c) => PSEUDO[c] ?? c))).join("")} ${"~".repeat(Math.max(1, Math.round(s.length * 0.4)))}]`;
export const esc = (s: string): string => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
/** Text from the page can only be one of the known choices (CodeQL: never trust a DOM value as a state). */
export const pick = <T extends string>(allowed: readonly T[], value: string, fallback: T): T => (allowed as readonly string[]).includes(value) ? (value as T) : fallback;
export const plain = (s: string): string => s.replace(/[<>"'&]/g, "").slice(0, 200);
export const randomBytes = (n: number): Uint8Array => crypto.getRandomValues(new Uint8Array(n));
export const newId = (): string => uuid7(Date.now(), randomBytes);
/** A public identifier in the one LynkOmni format (core/ids.py, ts/src/ids.ts): LO + type code + 12 digits with a Luhn check digit.
 *  The browser copy of the allocator's format step, for sample records in emulators; the code must be in the identifier registry. */
export function publicId(code: string): string {
  const p11 = [...randomBytes(11)].map((b) => String(b % 10)).join("");
  let s = 0;
  [...p11].reverse().forEach((ch, i) => { let d = Number(ch) * (i % 2 === 0 ? 2 : 1); if (d > 9) d -= 9; s += d; });
  const p12 = p11 + String((10 - (s % 10)) % 10);
  return `LO${code}-${p12.slice(0, 4)}-${p12.slice(4, 8)}-${p12.slice(8)}`;
}
export const reducedMotion = (): boolean => typeof matchMedia === "function" && matchMedia("(prefers-reduced-motion: reduce)").matches;

/** Words: English from strings.en.json, every other language from its pack; {placeholders} filled from vars. */
export class Words {
  private en: Record<string, string>;
  constructor(private packs: Record<string, LanguagePack>, private lang: () => string) { this.en = packs["en"]?.texts ?? {}; }
  isTest(): boolean { return (TEST_LANGS as readonly string[]).includes(this.lang()); }
  dir(): "ltr" | "rtl" { return this.lang() === "xx-rtl" ? "rtl" : this.packs[this.lang()]?.dir ?? "ltr"; }
  htmlLang(): string { return this.isTest() ? "en" : this.lang(); }
  /** Whether the app carries this word (the footer's words travel only in apps that show a footer). */
  has = (k: string): boolean => k in this.en;
  t = (k: string, vars: Record<string, string | number> = {}): string => {
    const en = this.en[k] ?? k, raw = this.isTest() ? pseudo(en) : this.packs[this.lang()]?.texts[k] ?? en;
    return raw.replace(/\{(\w+)\}/g, (m, v: string) => (v in vars ? String(vars[v]) : m));
  };
  /** <option>s for the language select: every pack in its own name, then the two test languages. */
  options(testLong: string, testRtl: string): string {
    return Object.entries(this.packs).map(([code, p]) => `<option value="${esc(code)}" lang="${esc(code)}" dir="${p.dir}">${esc(p.native)}</option>`).join("") + `<option value="xx">${esc(testLong)}</option><option value="xx-rtl">${esc(testRtl)}</option>`;
  }
}

/** The country shown: read from the pack and the provider ledger; nothing about a country lives in emulator code. */
export class Country {
  constructor(private data: Build, private code: () => string, private lang: () => string) {}
  pack(): CountryPack { return this.data.packs[this.code()] ?? (this.data.packs[this.data.packOrder[0] ?? ""] as CountryPack); }
  locale(): string { return `${(TEST_LANGS as readonly string[]).includes(this.lang()) ? "en" : this.lang()}-${this.pack().code}`; }
  money(minor: number, currency = this.pack().currency): string { return formatMoney(minor, currency, this.locale()); }
  clock(ms: number): string { return new Intl.DateTimeFormat(this.locale(), { timeZone: this.pack().tz, hour: "2-digit", minute: "2-digit" }).format(ms); }
  date(ms: number): string { return new Intl.DateTimeFormat(this.locale(), { timeZone: this.pack().tz, dateStyle: "medium" }).format(ms); }
  /** The chooser's <option>s: the neutral sample first, then every country in the person's language (browser CLDR data). */
  options(sampleWord: string): string {
    const lang = (TEST_LANGS as readonly string[]).includes(this.lang()) ? "en" : this.lang();
    let names: Intl.DisplayNames | null = null;
    try { names = new Intl.DisplayNames([lang], { type: "region" }); } catch { names = null; }
    return this.data.packOrder.map((c) => { const p = this.data.packs[c] as CountryPack; const n = p.sample ? sampleWord : (names?.of(c) ?? p.name); return `<option value="${esc(c)}">${esc(n === c ? p.name : n)}</option>`; }).join("");
  }
  /** A partner-backed method works only where the ledger says its items are signed (shown when "real user" is on). */
  methodOk(method: string, realUser: boolean): boolean { return method === "cash" || !realUser || (this.pack().ready[method]?.ok ?? false); }
}

/** The event log every emulator shows: what the device sends and the cloud answers, each with its honest state. */
export interface Ev { n: number; type: string; origin: "device" | "server"; payload: unknown; sync: UserState; at: number }
export class EventLog {
  events: Ev[] = [];
  constructor(private onChange: () => void) {}
  emit(type: string, payload: unknown, origin: "device" | "server" = "device", sync?: UserState): Ev {
    const e: Ev = { n: this.events.length + 1, type, origin, payload, sync: sync ?? (origin === "server" ? "accepted" : "queued"), at: Date.now() };
    this.events.unshift(e); this.onChange(); return e;
  }
  /** Queued items go out when a link exists (a weak link now and then); sent items are accepted by the cloud after a moment. */
  tick(maySend: boolean, weak: boolean, tickNo: number, onAccepted: (e: Ev) => void): boolean {
    if (!maySend || (weak && tickNo % 4)) return false;
    const now = Date.now(); let changed = false;
    for (const e of [...this.events].reverse()) {
      if (e.sync === "queued") { e.sync = "sent"; e.at = now; changed = true; }
      else if (e.sync === "sent" && now - e.at > 700) { e.sync = "accepted"; changed = true; onAccepted(e); }
    }
    if (changed) this.onChange();
    return changed;
  }
  pending(): { count: number; state: UserState } {
    const waiting = this.events.filter((e) => e.sync === "queued" || e.sync === "sent");
    return { count: waiting.length, state: waiting.some((e) => e.sync === "queued") ? "queued" : waiting.length ? "sent" : "accepted" };
  }
  html(esc_: (s: string) => string, chip: (s: UserState) => string, empty: string): string {
    return this.events.slice(0, 40).map((e) => `<li><span class="n">#${e.n}</span><code>${esc_(e.type)}</code><span class="org">${e.origin}</span>${chip(e.sync)}</li>`).join("") || `<li class="empty">${esc_(empty)}</li>`;
  }
}

/** Root attributes for right-to-left and the language (ts/src/fonts.ts rootAttributes does the same for real screens). */
export function applyRoot(el: HTMLElement, words: Words): void { el.setAttribute("lang", words.htmlLang()); el.setAttribute("dir", words.dir()); }

/** Scales a device drawing down to the width it has (never up), so a counter till or a wall screen fits a phone too. */
export function fitToWidth(rig: HTMLElement, deviceWidth: number): () => void {
  const fit = (): void => { document.documentElement.style.setProperty("--fit", String(Math.min(1, (rig.clientWidth - 8) / deviceWidth))); };
  fit(); addEventListener("resize", fit); return fit;
}

/** The control panel beside every device: the same conditions in the same words everywhere. `controls` picks which appear. */
export type Control = "online" | "fail" | "type" | "plan" | "country" | "real" | "practice" | "dark" | "lang";
export interface PanelState { online: boolean; fail: boolean; type: string; tier: string; country: string; realUser: boolean; practice: boolean; dark: boolean; lang: string }
export function panelHtml(controls: readonly Control[], st: PanelState, words: Words, country: Country, extra: { types?: readonly string[]; tiers?: readonly string[]; help?: string } = {}): string {
  const t = words.t, row = (inner: string, center = false): string => `<label${center ? ' class="center"' : ""}>${inner}</label>`;
  const box = (id: string, on: boolean, label: string, help?: string): string => row(`<input type="checkbox" data-ctl="${id}" ${on ? "checked" : ""}> <span>${esc(label)}${help ? `<br><span class="help">${esc(help)}</span>` : ""}</span>`);
  const sel = (id: string, label: string, options: string): string => row(`<span>${esc(label)}</span> <select data-ctl="${id}">${options}</select>`, true);
  const parts: string[] = [`<h2>${esc(t("try_it"))}</h2><p class="help">${esc(extra.help ?? t("sandbox_note"))}</p><h3>${esc(t("conditions"))}</h3>`];
  for (const c of controls) {
    if (c === "online") parts.push(box("online", st.online, t("internet"), t("internet_help")));
    if (c === "fail") parts.push(box("fail", st.fail, t("provider_declines"), t("provider_declines_help")));
    if (c === "type") parts.push(sel("type", t("business_type"), (extra.types ?? []).map((x) => `<option value="${esc(x)}" ${x === st.type ? "selected" : ""}>${esc(t(`type_${x}`))}</option>`).join("")));
    if (c === "plan") parts.push(sel("plan", t("plan"), (extra.tiers ?? []).map((x) => `<option value="${esc(x)}" ${x === st.tier ? "selected" : ""}>${esc(t(`card_${x}`))}</option>`).join("")));
    if (c === "country") parts.push(sel("country", t("country"), country.options(t("sample_country")).replace(`value="${esc(st.country)}"`, `value="${esc(st.country)}" selected`)));
    if (c === "real") parts.push(box("real", st.realUser, t("real_user"), t("real_user_help")));
    if (c === "practice") parts.push(box("practice", st.practice, t("practice_mode"), t("practice_mode_help")));
    if (c === "dark") parts.push(box("dark", st.dark, t("dark_screen")));
    if (c === "lang") parts.push(sel("lang", t("language"), words.options(t("long_text_test"), t("rtl_test")).replace(`value="${esc(st.lang)}"`, `value="${esc(st.lang)}" selected`)));
  }
  parts.push(`<div id="stateButtons" class="states"></div><h3>${esc(t("event_log"))}</h3><ul class="log" id="log" aria-live="polite"></ul>`);
  return parts.join("");
}
/** Reads a panel change into the state; returns true when the screen words must be redrawn (language). */
export function panelChange(el: HTMLInputElement | HTMLSelectElement, st: PanelState, data: Build, extra: { types?: readonly string[]; tiers?: readonly string[] } = {}): boolean {
  const ctl = el.dataset["ctl"] ?? "", on = (el as HTMLInputElement).checked, v = el.value;
  if (ctl === "online") st.online = on; else if (ctl === "fail") st.fail = on; else if (ctl === "real") st.realUser = on; else if (ctl === "practice") st.practice = on; else if (ctl === "dark") st.dark = on;
  else if (ctl === "type") st.type = pick(extra.types ?? [], v, st.type);
  else if (ctl === "plan") st.tier = pick(extra.tiers ?? [], v, st.tier);
  else if (ctl === "country") st.country = pick(data.packOrder, v, st.country);
  else if (ctl === "lang") { st.lang = v in data.i18n || v === "xx" || v === "xx-rtl" ? v : "en"; return true; }
  return false;
}
/** The state buttons under the panel (the layout test walks them): each names a screen the emulator can show at once. */
export function stateButtons(el: HTMLElement, states: readonly string[], go: (s: string) => void): void {
  el.innerHTML = states.map((k) => `<button type="button" data-state="${esc(k)}">${esc(k)}</button>`).join("");
  el.addEventListener("click", (e) => {
    const b = (e.target as HTMLElement).closest<HTMLElement>("[data-state]"); if (!b) return;
    (window as unknown as { __settle?: () => void }).__settle?.();   // jumping to a screen ends the first-run card (ts/src/deviceshell.ts)
    go(pick(states, b.dataset["state"] ?? "", states[0] ?? ""));
  });
}

/** The footer (blueprint section 26). Web apps (the owner's web view) show the main footer; apps on a device show the one-line
 *  short footer. Words come from the language packs, payment methods from the chosen country's pack, and the copyright line is
 *  fixed text with the year in the country's time zone. */
export function appMainFooter(words: Words, country: Country, data: Build): string {
  const p = country.pack();
  return mainFooterHtml(buildFooter({ now: new Date(), lang: words.htmlLang(), words: (k) => (words.has(k) ? words.t(k) : undefined),
    pack: { code: p.code, name: p.name, currency: p.currency, tz: p.tz, languages: [], providers: p.providers, card_networks: p.card_networks, wallets: p.wallets } }), esc, (id) => data.icons[id] ?? "");
}
export const appShortFooter = (country: Country): string => shortFooterHtml(new Date(), country.pack().tz);
