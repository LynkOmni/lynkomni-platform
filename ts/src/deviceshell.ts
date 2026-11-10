/** The shared shell parts inside every device app (blueprint 41 B, owner rule 9 November 2026: "enforce section 1 in every app").
 *  The real shell (ts/src/shell.ts) draws them; this kit puts them on a device: "Find or do anything" (search that runs actions,
 *  voice, hand-over to LynkAssist), the help panel (?) for the screen in view, the account menu, the connection chip with its sync
 *  sheet, the first-run language and region card with one-tap English, and the screen's own address (deep link). The device
 *  supplies what only it knows (its screens, search entries, articles, account and sync state) through DsHost. */
import * as SH from "./shell.js";
import { bell, count, badge, whySheet } from "./notify.js";
import type { Line } from "./notify.js";
import { askBox, lookup } from "./assist.js";
import type { Entry as KEntry } from "./assist.js";
import { deviceCrumbs } from "./devicekit.js";

export type DsPanel = "" | "search" | "help" | "account" | "sync" | "locale" | "bell" | "why";
/** The screen in view: its register id, its title and its address on app.lynkomni.com (catalog/addresses.v1.json). */
export interface DsScreen { id: string; title: string; path: string }
export interface DsLocale { language: string; region: string; currency: string; english: boolean }
export interface DsHost {
  t: SH.T; icon: SH.Icon; clock: (ms: number) => string;
  screen(): DsScreen;
  entries(): SH.Entry[];
  articles(screenId: string): SH.Article[];
  sync(): SH.SyncInfo;
  account(): SH.Account | null;
  locale(): DsLocale;
  /** Runs an action the shell hands back: a search result ("go:sell", "new_sale"), theme, sign out, English, sync now, toggles. */
  run(act: string): void;
  redraw(): void;
  /** MASTER UPDATE section 3: the device's bell lines (the cloud's and its own offline ones), already in the reader's language. */
  lines?(): Line[];
  /** The offline knowledge pack for LynkAssist's Ask box in help (layer 1), in the device's language. */
  knowledge?(): KEntry[];
  /** A word for a breadcrumb step's address. */
  crumbLabel?(path: string): string;
}

export const APP_HOST = "app.lynkomni.com";

export class DeviceShell {
  panel: DsPanel = "";
  q = "";
  note = "";
  firstRun: boolean;
  /** Picture mode (S4, 43 G low-literacy mode on every device): bigger pictures with the word always beside them. */
  pictures = false;
  /** The bell's filter, when it was last opened, and the line "Why am I seeing this?" is about. */
  filter = "all"; lastOpened = 0; whyNid = ""; ask = "";
  constructor(private h: DsHost, opts: { firstRun?: boolean } = {}) {
    this.firstRun = opts.firstRun ?? true;
    (globalThis as unknown as { __dsh?: DeviceShell }).__dsh = this;   // lets the layout test open each panel in every language
  }
  /** Opens a panel (or the first-run card) from outside: the layout and accessibility tests walk every shell part. */
  show(p: DsPanel | "first"): void { if (p === "first") { this.firstRun = true; this.panel = ""; } else { this.firstRun = false; this.panel = p; this.q = p === "search" ? "a" : ""; } this.note = ""; this.h.redraw(); }

  /** The address of the screen in view: every screen has its own (41 B deep links). */
  address(): string { const p = this.h.screen().path; return p.includes(".lynkomni.com") ? p : `${APP_HOST}${p}`; }

  /** The device's shell controls: search, help (?), account, and the connection chip. Each is a 44 px target with a name. */
  bar(opts: { search?: boolean; help?: boolean; account?: boolean; chip?: boolean } = {}): string {
    const { t, icon } = this.h, o = { search: true, help: true, account: true, chip: true, ...opts };
    const btn = (act: string, ic: string, label: string): string => `<button class="dsh-btn" data-act="${act}" aria-label="${SH.esc(label)}" title="${SH.esc(label)}">${icon(ic)}</button>`;
    const n = this.h.lines ? count(this.h.lines()) : 0;
    const bellBtn = this.h.lines ? `<button class="dsh-btn dsh-bell" data-act="dsh:bell" aria-label="${SH.esc(n ? t("notifications_n", { n }) : t("notifications"))}" title="${SH.esc(t("notifications"))}">${icon("ui-bell")}${n ? `<span class="dsh-badge" aria-hidden="true">${SH.esc(badge(n))}</span>` : ""}</button>` : "";
    return `<span class="dsh-bar">${o.search ? btn("dsh:search", "ui-search", t("find_or_do")) : ""}${bellBtn}${o.help ? btn("dsh:help", "ui-info", t("help")) : ""}${o.chip ? SH.connectionChip(this.h.sync(), t, icon).replace('class="netchip', 'class="netchip dsh-chip') : ""}${o.account && this.h.account() ? btn("dsh:account", "ui-user", t("account_menu")) : ""}</span>`;
  }
  /** Only the help button, for screens whose top bar has a fixed set of parts (the Business app's top bar, 41 E). */
  helpButton(): string { return `<button class="dsh-btn" data-act="dsh:help" aria-label="${SH.esc(this.h.t("help"))}" title="${SH.esc(this.h.t("help"))}">${this.h.icon("ui-info")}</button>`; }
  /** A search field that opens "Find or do anything" (for apps whose top bar has no search button). */
  searchField(): string { return `<button class="dsh-field" data-act="dsh:search" title="${SH.esc(this.h.t("find_or_do_hint"))}">${this.h.icon("ui-search")}<span>${SH.esc(this.h.t("find_or_do"))}</span></button>`; }

  overlay(): string {
    const { t, icon } = this.h;
    const p = this.firstRun ? "locale" : this.panel;
    if (!p) return "";
    let body = "";
    if (p === "locale") {
      const l = this.h.locale();
      body = `<div class="dsh-locale" role="dialog" aria-modal="true" aria-labelledby="dshLocaleT"><h2 id="dshLocaleT">${SH.esc(t("locale_title"))}</h2><dl><dt>${SH.esc(t("language"))}</dt><dd>${SH.esc(l.language)}</dd><dt>${SH.esc(t("region"))}</dt><dd>${SH.esc(l.region)}</dd><dt>${SH.esc(t("currency"))}</dt><dd>${SH.esc(l.currency)}</dd></dl>
        <button class="dsh-primary" data-act="dsh:localeok">${SH.esc(t("looks_right"))}</button>${l.english ? "" : `<button class="dsh-secondary" data-act="dsh:english" lang="en" dir="ltr">English</button>`}<button class="dsh-link" data-act="dsh:localechange">${SH.esc(t("change"))}</button><p class="dsh-note">${SH.esc(t("presentation_only"))}</p></div>`;
    } else if (p === "search") body = SH.commandBar(this.q, SH.search([...this.h.entries(), { id: "pictures", kind: "setting", title: t("low_literacy"), act: "dsh:pictures" }], this.q), t, icon);
    else if (p === "help") body = SH.helpPanel(this.h.screen().title, this.h.articles(this.h.screen().id), t, icon, this.h.knowledge ? this.askPart() : "");
    else if (p === "bell" && this.h.lines) body = bell(this.h.lines(), { filter: this.filter, lastOpened: this.lastOpened, areas: [] }, t, icon, this.h.clock);
    else if (p === "why" && this.h.lines) { const l = this.h.lines().find((x) => x.nid === this.whyNid); body = l ? whySheet(l, t, icon) : ""; }
    else if (p === "account") { const a = this.h.account(); body = a ? SH.accountMenu(a, t, icon) + this.picturesToggle() : ""; }
    else if (p === "sync") body = SH.syncSheet(this.h.sync(), t, icon, this.h.clock);
    const note = this.note ? `<p class="dsh-note" role="status">${SH.esc(this.note)}</p>` : "";
    const close = p === "locale" ? "" : `<button class="dsh-x" data-act="dsh:close" aria-label="${SH.esc(t("close"))}">${icon("ui-close")}</button>`;
    return `<div class="dsh-scrim" data-act="${p === "locale" ? "" : "dsh:close"}"><div class="dsh-panel dsh-${p}" data-stop="1">${close}${body}${note}</div></div>`;
  }

  /** LynkAssist's Ask box (layer 1 offline): answers from the saved help in the device's language, with its date. */
  askPart(): string {
    const k = this.h.knowledge ? this.h.knowledge() : [];
    return askBox({ query: this.ask, results: this.ask ? lookup(k, this.ask) : [], online: this.h.sync().link !== "offline", builtOn: "" }, this.h.t, this.h.icon);
  }
  /** The breadcrumb trail of the screen in view (from the address map), compact on small screens. */
  crumbs(compact: boolean): string {
    const label = (p: string): string => (this.h.crumbLabel ? this.h.crumbLabel(p) : p.split("/").pop() || p);
    return deviceCrumbs(this.h.screen().path, label, compact, this.h.t);
  }

  /** The picture mode switch (in the account menu and in search): a 44 px switch with its word. */
  picturesToggle(): string { return `<button class="dsh-toggle" role="switch" data-act="dsh:pictures" aria-checked="${this.pictures}">${this.h.icon("ui-grid")}<span>${SH.esc(this.h.t("low_literacy"))}</span><span class="dsh-sw" aria-hidden="true"></span></button>`; }
  /** The class a device puts on its screen root while picture mode is on. */
  rootClass(): string { return this.pictures ? "lowlit" : ""; }

  /** Handles a tap. Returns true when the shell used it (the device then does nothing more with it). */
  act(a: string, fromStop = false): boolean {
    const [k = "", v = ""] = a.split(/:(.*)/s);
    const open = (p: DsPanel): true => { this.panel = p; this.note = ""; if (p === "search") this.q = ""; this.h.redraw();
      if (p === "search") document.getElementById("cmdIn")?.focus();   // ready to type at once (keyboard, "/" or Ctrl+K)
      return true; };
    const say = (key: string): true => { this.note = this.h.t(key); this.h.redraw(); return true; };
    switch (a) {
      case "dsh:search": return open("search");
      case "dsh:help": case "shell:help": return open("help");
      case "dsh:account": return open("account");
      case "dsh:sync": case "shell:sync": return open("sync");
      case "dsh:bell": case "shell:bell": return open("bell");
      case "dsh:close": case "closesheet": if (fromStop) return true; this.panel = ""; this.note = ""; this.h.redraw(); return true;
      case "dsh:localeok": this.firstRun = false; this.panel = ""; this.h.redraw(); return true;
      case "dsh:english": this.h.run("lang:en"); this.firstRun = false; this.panel = ""; this.h.redraw(); return true;
      case "dsh:localechange": case "shell:globe": this.firstRun = false; this.panel = ""; this.h.run("locale:change"); this.h.redraw(); return true;
      case "shell:voice": this.q = this.h.t("voice_sample_search"); this.h.redraw(); return true;
      case "assist:ask": return say("assist_opening");
      case "support:chat": return say("support_connecting");
      case "support:case": return say("case_opened");
      case "copy:lynkid": return say("copied");
      case "dsh:pictures": this.pictures = !this.pictures; if (this.panel === "search") this.panel = ""; this.h.run("pictures"); this.h.redraw(); return true;
      case "toggle:datasaver": case "toggle:forced": case "sync:now": this.h.run(a); this.h.redraw(); return true;
      case "shell:theme": case "shell:signout": this.panel = ""; this.h.run(a); this.h.redraw(); return true;
    }
    if (k === "help" && v.startsWith("article:")) return say("article_opening");
    if (k === "ntf") {                                    // the bell's own controls; acting on a line is the device's (run)
      const [what = "", nid = ""] = v.split(":");
      if (what === "filter") { this.filter = nid; this.h.redraw(); return true; }
      if (what === "why") { this.whyNid = nid; this.panel = "why"; this.h.redraw(); return true; }
      if (this.panel === "bell" && (what === "open" || what === "act")) this.panel = "";
      this.h.run(a); this.h.redraw(); return true;
    }
    if (k === "role" || k === "business") { this.panel = ""; this.h.run(a); this.h.redraw(); return true; }
    if (this.panel === "search" && a) { this.panel = ""; this.h.run(a); this.h.redraw(); return true; }   // a search result: do it
    return false;
  }
  /** Typing in the search box: results follow every letter, focus stays in the box. */
  input(el: HTMLInputElement): boolean {
    if (el.id === "asIn") { this.ask = el.value.slice(0, 120); this.h.redraw(); const n = document.getElementById("asIn") as HTMLInputElement | null; if (n) { n.focus(); n.setSelectionRange(n.value.length, n.value.length); } return true; }
    if (el.id !== "cmdIn") return false;
    const at = el.selectionStart;
    this.q = el.value.slice(0, 80); this.h.redraw();
    const n = document.getElementById("cmdIn") as HTMLInputElement | null;
    if (n) { n.focus(); if (at !== null) n.setSelectionRange(at, at); }
    return true;
  }
  /** Keyboard: "/" or Ctrl+K opens search (computers), Escape closes the open panel. */
  key(e: KeyboardEvent): boolean {
    const typing = e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement;
    if ((e.key === "k" && (e.ctrlKey || e.metaKey)) || (e.key === "/" && !typing)) { e.preventDefault(); this.act("dsh:search"); return true; }
    if (e.key === "Escape" && (this.panel || this.firstRun)) { if (!this.firstRun) this.act("dsh:close"); return true; }
    return false;
  }
  /** Ends the first-run card (a state button or a test jumping straight to a screen). */
  settle(): void { this.firstRun = false; this.panel = ""; }
}

/** Help articles for a screen: the screen's own guide first, then the general ones (LynkFAQ, served by section 6). */
export function screenArticles(t: SH.T, screenId: string, title: string): SH.Article[] {
  return [
    { id: `screen-${screenId}`, title: t("article_screen", { screen: title }), href: `/help/articles/${screenId}` },
    { id: "offline", title: t("article_offline"), href: "/help/articles/offline" },
    { id: "fake-payment", title: t("article_fake_payment"), href: "/help/articles/fake-payment" },
  ];
}

/** The picture for a designed state (visuals state-* sets, carried in every emulator's DATA.statePictures), by theme. */
export type StatePictures = Record<string, Record<string, { svg: string; alt: string }>>;
export function statePic(pics: StatePictures, kind: SH.StateKind, dark: boolean): SH.Pic | null {
  const id = SH.STATE_PICTURE[kind];
  const p = id ? pics[id]?.[dark ? "dark" : "light"] : undefined;
  return p ? { svg: p.svg, alt: p.alt } : null;
}
/** A designed state (41 B: picture, title, line and a next step; never a dead end), drawn by the shell. */
export function designedState(kind: SH.StateKind, t: SH.T, pics: StatePictures, dark: boolean, next: { label: string; act: string } | null): string {
  return `<div class="dsh-state">${SH.state(kind, t, statePic(pics, kind, dark), next)}</div>`;
}

/** The shell for an emulator built on the shared panel (ts/src/emulator.ts PanelState): language, theme and connection come
 *  from the panel's state; the device adds its screens, search entries, account and actions. */
export interface PanelLike { lang: string; dark: boolean; online: boolean }
export function panelShell(o: {
  st: PanelLike; t: SH.T; icon: SH.Icon; clock: (ms: number) => string;
  native(): string; region(): string; currency(): string; pending(): number; lastSync(): number | null;
  screen(): DsScreen; entries(): SH.Entry[]; account?: () => SH.Account | null; run(a: string): void; redraw(): void; firstRun?: boolean;
  lines?: () => Line[]; knowledge?: () => KEntry[]; crumbLabel?: (path: string) => string;
}): DeviceShell {
  const ctl = (name: string): HTMLInputElement | null => document.querySelector<HTMLInputElement>(`[data-ctl="${name}"]`);
  return new DeviceShell({
    t: o.t, icon: o.icon, clock: o.clock, screen: o.screen, entries: o.entries,
    articles: (id) => screenArticles(o.t, id, o.screen().title),
    sync: () => ({ link: o.st.online ? "good" : "offline", pending: o.pending(), lastSync: o.lastSync(), dataSaver: false, forcedOffline: !o.st.online }),
    account: () => (o.account ? o.account() : null),
    locale: () => ({ language: o.native(), region: o.region(), currency: o.currency(), english: o.st.lang === "en" }),
    run: (a) => {
      if (a === "lang:en") { o.st.lang = "en"; const s = ctl("lang"); if (s) s.value = "en"; return; }
      if (a === "locale:change") { ctl("lang")?.focus(); return; }
      if (a === "shell:theme") { o.st.dark = !o.st.dark; const c = ctl("dark"); if (c) c.checked = o.st.dark; return; }
      if (a === "toggle:forced") { o.st.online = !o.st.online; const c = ctl("online"); if (c) c.checked = o.st.online; return; }
      if (a === "toggle:datasaver" || a === "sync:now") return;
      o.run(a);
    },
    redraw: o.redraw,
    ...(o.lines ? { lines: o.lines } : {}), ...(o.knowledge ? { knowledge: o.knowledge } : {}), ...(o.crumbLabel ? { crumbLabel: o.crumbLabel } : {}),
  }, { firstRun: o.firstRun ?? true });
}
/** A sample signed-in person for a device (staff on a shop device): never a real person, a masked public id from core/ids.py. */
export function sampleAccount(t: SH.T, role: string, roles: string[], business: string, theme: "light" | "dark", language: string, region: string): SH.Account {
  return { name: t(`role_${role}`), lynkId: "LOID-4821-9035-7715", businesses: [{ id: "b1", name: business, current: true }], role, roles, theme, language, region };
}
