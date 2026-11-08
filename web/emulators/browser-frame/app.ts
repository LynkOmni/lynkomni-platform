/* The shared LynkOmni shell inside a browser window (build section 1). Every part comes from ts/src/shell.ts; this file only
 * holds the sample page, the emulator controls and the event log. Words come from strings.en.json and the language packs. */
import { STATE_PICTURE, Undo, accountMenu, chart, comingSoon, commandBar, connectionChip, deliverNow, esc, globeSheet, header, helpPanel, launcher, messageNote, messageText, navigation, notificationsPanel, route, search, state, syncSheet, translationBanner, translator, undoToast, usernameField } from "../../../ts/src/shell.js";
import type { AddressMap, ChatLang, ChatMessage, Entry, Icon, Link, NavItem, Notice, Pic, StateKind, SyncInfo, T, UsernameStatus, Viewport } from "../../../ts/src/shell.js";
import type { UserState } from "../../../ts/src/pos.js";

interface CountryPack { code: string; name: string; currency: string; tz: string; locale: string; sample: boolean; ready: Record<string, { ok: boolean; message: string }>; services: { service: string; name: string; icon: string; state: "available" | "coming_soon" }[] }
interface BuildData {
  icons: Record<string, string>;
  brand: { body: string; topLight: string; topDark: string; receipt: string };
  pictures: { offLight: string; offDark: string; offAlt: string };
  statePictures: Record<string, Record<"light" | "dark", { svg: string; alt: string; contrast?: string }>>;
  states: Record<string, { label: string; meaning: string }>;
  packs: Record<string, CountryPack>; packOrder: string[];
  addresses: AddressMap;
  i18n: Record<string, { native: string; dir: "ltr" | "rtl"; texts: Record<string, string> }>;
}
declare const DATA: BuildData;
interface Ev { n: number; type: string; origin: "device" | "server"; payload: unknown; sync: UserState; at: number }

const PACKS = DATA.i18n;
const EN: Record<string, string> = PACKS.en?.texts ?? {};
const TEST_LANGS = ["xx", "xx-rtl"];
type Overlay = null | "launcher" | "account" | "globe" | "cmd" | "help" | "bell" | "sync";
type Screen = "home" | "payment" | `state:${StateKind}`;

const S = {
  size: "computer" as Viewport, lang: "en", theme: "light" as "light" | "dark", mode: "" as "" | "lite" | "sunlight", link: "good" as Link, country: "", realUser: false,
  screen: "home" as Screen, overlay: null as Overlay, query: "", chartView: "chart" as "chart" | "table", showOriginal: false, username: "", cloud: null as UsernameStatus,
  notified: new Set<string>(), dataSaver: false, forced: false, pending: 0, lastSync: null as number | null, events: [] as Ev[], undo: new Undo(), archived: 0, voided: 0, seen: new Set<string>(),
};
const $ = <T extends HTMLElement>(sel: string): T => document.querySelector(sel) as T;
const PSEUDO: Record<string, string> = { a: "à", c: "ç", e: "é", i: "î", n: "ñ", o: "ö", s: "š", u: "ü", y: "ý" };
const pseudo = (s: string): string => `[${s.replace(/[aceinosuy]/g, (c) => PSEUDO[c] ?? c)} ${"~".repeat(Math.max(1, Math.round(s.length * 0.4)))}]`;
const isTest = (): boolean => TEST_LANGS.includes(S.lang);
const t: T = (k, vars) => (isTest() ? pseudo(translator(EN)(k, vars)) : translator(PACKS[S.lang]?.texts ?? EN, EN)(k, vars));
const icon: Icon = (id, cls = "ic") => `<span class="${cls}" aria-hidden="true">${DATA.icons[id] ?? ""}</span>`;
const pack = (): CountryPack => DATA.packs[S.country] ?? (DATA.packs[DATA.packOrder[0] ?? ""] as CountryPack);
const locale = (): string => `${isTest() ? "en" : S.lang}-${pack().code}`;
const money = (minor: number): string => { try { return new Intl.NumberFormat(locale(), { style: "currency", currency: pack().currency }).format(minor / 100); } catch { return `${pack().currency} ${(minor / 100).toFixed(2)}`; } };
const clock = (ms: number): string => new Intl.DateTimeFormat(locale(), { timeZone: pack().tz, hour: "2-digit", minute: "2-digit" }).format(ms);
const langName = (code: string): string => PACKS[code]?.native ?? code;
const SHOP = (): string => t("shop_name");
// Sample sales for the chart: data the emulator itself holds (minor units), labelled sample in the page header.
const SAMPLE_WEEK = [42000, 51500, 38000, 60250, 72000, 91000, 30500];
const DAYS = ["day_mon", "day_tue", "day_wed", "day_thu", "day_fri", "day_sat", "day_sun"];

function record(type: string, origin: "device" | "server", payload: unknown): void {
  const sync: UserState = origin === "server" ? "confirmed" : S.link === "offline" || S.forced ? "queued" : "sent";
  S.events.unshift({ n: S.events.length + 1, type, origin, payload, sync, at: Date.now() });
  if (sync === "queued") S.pending++;
  drawLog();
}

// ---------------------------------------------------------------- the page
const navItems = (): NavItem[] => {
  const base: NavItem[] = [
    { id: "home", label: t("tab_home"), icon: "ui-home", href: "/", current: S.screen === "home" },
    { id: "sell", label: t("tab_sell"), icon: "ui-cart", href: "/sell", current: S.screen === "payment" },
    { id: "stock", label: t("tab_stock"), icon: "product-stock", href: "/stock" },
    { id: "chats", label: t("tab_chats"), icon: "product-chat", href: "/chats", badge: 1 },
    { id: "business", label: t("tab_business"), icon: "product-dash", href: "/business", current: S.screen.startsWith("state:") },
  ];
  return S.size === "computer" ? [...base, { id: "reports", label: t("nav_reports"), icon: "ui-chart", href: "/analytics" }, { id: "settings", label: t("nav_settings"), icon: "ui-settings", href: "/business/settings" }] : base;
};
const screenPath = (): string => S.screen === "home" ? "/" : S.screen === "payment" ? "/sell" : S.screen === "state:not_found" ? "/nowhere" : "/business";
const sync = (): SyncInfo => ({ link: S.link, pending: S.pending, lastSync: S.lastSync, dataSaver: S.dataSaver, forcedOffline: S.forced });
const statePic = (kind: StateKind): Pic | null => {
  const id = STATE_PICTURE[kind];
  if (!id || S.mode === "lite") return null;
  const p = DATA.statePictures[id]?.[S.mode === "sunlight" ? "light" : S.theme];
  return p ? { svg: S.mode === "sunlight" ? (p.contrast ?? p.svg) : p.svg, alt: p.alt } : null;
};
const NEXT: Record<StateKind, { label: string; act: string } | null> = {
  loading: null, empty: { label: "action_add", act: "go:home" }, offline: { label: "action_continue", act: "go:home" }, error: { label: "action_retry", act: "go:home" },
  not_found: { label: "action_search", act: "shell:search" }, no_results: { label: "action_search", act: "shell:search" }, permission: { label: "action_home", act: "go:home" },
  maintenance: { label: "action_status", act: "go:home" }, sync_pending: { label: "action_sync", act: "sync:now" }, coming_soon: null, success: { label: "action_continue", act: "go:home" },
};

function main(): string {
  if (S.screen.startsWith("state:")) {
    const kind = S.screen.slice(6) as StateKind;
    const next = NEXT[kind];
    const body = kind === "coming_soon" ? comingSoon("LynkMPay", t, statePic(kind), S.notified.has("LynkMPay")) : state(kind, t, statePic(kind), next ? { label: t(next.label), act: next.act } : null);
    return `<div class="pagetitle"><h1>${esc(t("states_card"))}</h1>${connectionChip(sync(), t, icon)}</div><div class="card">${body}</div><p class="note">${esc(t("states_hint"))}</p>`;
  }
  if (S.screen === "payment") {
    return `<div class="pagetitle"><h1>${esc(t("tab_sell"))}</h1>${connectionChip(sync(), t, icon)}</div><div class="card"><div class="protected-note">${icon("ui-lock")}<span>${esc(t("protected_zone"))}</span></div><p class="muted" style="margin-top:8px">${esc(t("deep_link"))}: <span class="deeplink">https://app.lynkomni.com/sell</span></p><div class="actions"><button class="primary" data-act="go:home">${esc(t("action_home"))}</button></div></div>`;
  }
  const chartHtml = chart({ title: t("chart_title"), labels: DAYS.map((d) => t(d)), series: [{ name: t("today_sales"), values: SAMPLE_WEEK }], kind: "bar", format: money }, S.chartView, t, "week");
  // The demo customer always writes in a language other than the reader's, so the two-language chat is always two languages.
  const reader = isTest() ? "en" : S.lang;
  const writer = reader === "ar" ? "sw" : "ar";
  const writerText = writer === "ar" ? "هل يمكنك أن تحتفظ لي بصينيتين من البيض حتى الساعة 5 مساءً؟" : "Unaweza kuniwekea trei mbili za mayai hadi saa 11 jioni?";
  const chatLang: ChatLang = { reader, writer, writerName: t("customer_name"), showOriginal: S.showOriginal };
  const msg: ChatMessage = { id: "m1", text: writerText, translated: t("chat_sample_translated"), language: writer, pendingTranslation: S.link === "offline" || S.forced };
  const here = route(DATA.addresses, `https://app.lynkomni.com${screenPath()}`);
  return `<div class="pagetitle"><h1>${esc(t("title_home", { shop: SHOP() }))}</h1>${connectionChip(sync(), t, icon)}</div>
    <div class="cards">
      <div class="card"><h2>${esc(t("today_sales"))}</h2><div class="big">${esc(money(SAMPLE_WEEK[new Date().getDay() === 0 ? 6 : new Date().getDay() - 1] ?? 0))}</div><div class="muted">${esc(t("sales_count", { n: 14 }))}</div>
        <div class="actions"><button class="primary" data-act="newsale">${icon("ui-plus")}<span>${esc(t("new_sale"))}</span></button><button class="secondary" data-act="archive">${esc(t("archive_product"))}</button><button class="secondary" data-act="void">${esc(t("void_sale"))}</button></div></div>
      <div class="card"><h2>${esc(t("today_profit"))}</h2><div class="big">${esc(money(Math.round((SAMPLE_WEEK[4] ?? 0) * 0.27)))}</div><div class="muted">${esc(t("deep_link"))}: <span class="deeplink">${esc(here ? `app.lynkomni.com${here.path}` : "")}</span></div></div>
      <div class="card" style="grid-column:1/-1">${chartHtml}</div>
      <div class="card"><h2>${esc(t("username_card"))}</h2>${usernameField(S.username, S.cloud, (u) => u === "mamas.kitchen", t, icon)}</div>
      <div class="card"><h2>${esc(t("chat_card"))}</h2><div class="chat-demo">${translationBanner(chatLang, langName, t)}<div class="msg" lang="${messageText(msg, chatLang) === msg.text ? writer : esc(reader)}" dir="${messageText(msg, chatLang) === msg.text ? (PACKS[writer]?.dir ?? "ltr") : (PACKS[S.lang]?.dir ?? "ltr")}">${esc(messageText(msg, chatLang))}${messageNote(msg, chatLang, langName, t)}</div><div class="msg out">${esc(t("chat_reply"))}</div></div></div>
      <div class="card" style="grid-column:1/-1"><p class="muted">${icon("ui-sync")} ${esc(t("handoff_note"))}</p></div>
    </div>`;
}

function overlay(): string {
  const wrap = (cls: string, inner: string) => `<div class="overlay ${cls}" data-act="closeoverlay">${inner.replace(/^<(div|aside)/, '<$1 data-act="keep"')}</div>`;
  switch (S.overlay) {
    case "launcher": return wrap("", launcher(pack().services.map((s) => ({ id: s.service, name: s.name, icon: s.icon, href: `/${s.service}`, state: S.realUser ? s.state : "available" })), t, icon));
    case "account": return wrap("end", accountMenu({ name: "Grace", lynkId: "LOID-4821-9035-7716", businesses: [{ id: "b1", name: SHOP(), current: true }, { id: "b2", name: `${SHOP()} 2`, current: false }], role: "owner", roles: ["owner", "manager", "cashier"], theme: S.mode === "lite" ? "lite" : S.mode === "sunlight" ? "sunlight" : S.theme, language: langName(isTest() ? "en" : S.lang), region: pack().sample ? t("sample_country") : pack().name }, t, icon));
    case "globe": return wrap("", globeSheet(Object.entries(PACKS).map(([code, p]) => ({ code, native: p.native, dir: p.dir })), DATA.packOrder.map((c) => ({ code: c, name: (DATA.packs[c] as CountryPack).sample ? t("sample_country") : (DATA.packs[c] as CountryPack).name })), { language: isTest() ? "en" : S.lang, region: pack().code }, t));
    case "cmd": {
      const index: Entry[] = [
        { id: "a1", kind: "action", title: t("new_sale"), act: "newsale" }, { id: "a2", kind: "action", title: t("archive_product"), act: "archive" },
        { id: "p1", kind: "product", title: "Rice 1 kg", subtitle: money(1500), act: "go:home" }, { id: "c1", kind: "customer", title: t("customer_name"), act: "go:home" },
        { id: "r1", kind: "report", title: t("chart_title"), act: "go:home" }, { id: "s1", kind: "setting", title: t("nav_settings"), act: "go:home" },
        { id: "h1", kind: "help", title: t("help_article_1"), act: "shell:help" }, { id: "h2", kind: "help", title: t("help_article_2"), act: "shell:help" },
      ];
      return wrap("", commandBar(S.query, search(index, S.query), t, icon));
    }
    case "help": return wrap("end", helpPanel(t("tab_home"), [{ id: "1", title: t("help_article_1"), href: "/faq/pos/offline" }, { id: "2", title: t("help_article_2"), href: "/faq/mpay/waiting" }], t, icon));
    case "bell": {
      const list: Notice[] = [
        { id: "n1", at: Date.now() - 60000, urgency: "security", title: t("notice_signin"), record: "LOSEC-2201-4410-8832", href: "/security" },
        { id: "n2", at: Date.now() - 3600000, urgency: "transactional", title: t("notice_payment"), record: "LORCP-7731-0042-9910", read: true, href: "/sell" },
        { id: "n3", at: Date.now() - 7200000, urgency: "low", title: t("notice_insight"), read: true, href: "/analytics" },
      ];
      const d = deliverNow(list, new Date().getHours(), { startHour: 22, endHour: 7 }, S.seen);
      if (d.now.length || d.digest.length) record("NotificationsDelivered", "server", { now: d.now.map((n) => n.id), digest: d.digest.map((n) => n.id), held: d.held.map((n) => n.id) });
      return wrap("end", notificationsPanel(list, t, icon));
    }
    case "sync": return wrap("bottom", syncSheet(sync(), t, icon, clock));
    default: return "";
  }
}

function draw(): void {
  const d = $("#display");
  d.className = `display ${S.theme}`;
  if (S.mode) d.setAttribute("data-mode", S.mode); else d.removeAttribute("data-mode");
  d.lang = S.lang === "xx-rtl" ? "ar" : S.lang === "xx" ? "en" : S.lang;
  d.dir = S.lang === "xx-rtl" ? "rtl" : S.lang === "xx" ? "ltr" : PACKS[S.lang]?.dir ?? "ltr";
  const logo = S.theme === "dark" ? DATA.brand.topDark : DATA.brand.topLight;
  const items = navItems();
  const head = header({ logo, nav: items, notifications: 1, signedIn: true, title: S.size === "computer" ? undefined : SHOP(), surface: "app" }, S.size, t, icon);
  const nav = navigation(items, S.size, t, icon);
  const toasts = S.undo.openToasts(Date.now()).map((u) => undoToast(u, Date.now(), t, icon)).join("");
  d.innerHTML = `<div class="shell">${head}<div class="shell-body">${S.size === "phone" ? "" : nav}<main class="shell-main" id="main">${main()}<div class="footer-line">${esc(S.realUser ? "" : t("sandbox"))}</div></main></div>${S.size === "phone" ? nav : ""}${overlay()}<div class="toasts">${toasts}</div></div>`;
  $("#device").className = `device ${S.size}`;
  $("#url").textContent = `https://app.lynkomni.com${screenPath()}`;
  $("#tabTitle").textContent = `LynkOmni · ${SHOP()}`;
  document.querySelectorAll<HTMLElement>("#stateButtons button").forEach((b) => b.classList.toggle("on", b.dataset["state"] === S.screen));
}
function drawLog(): void {
  const box = $("#log");
  const chip = (s: UserState) => `<span class="chip st-${s}">${icon(`status-${s}`)}<span>${esc(t(`st_${s}`))}</span></span>`;
  box.innerHTML = S.events.slice(0, 40).map((e) => `<li><span class="n">#${e.n}</span><code>${esc(e.type)}</code><span class="org">${e.origin}</span>${chip(e.sync)}</li>`).join("") || `<li class="empty">No events yet. Try the page.</li>`;
}

/** Text that came from the page (an attribute or an input) never carries HTML characters into state; every value is escaped again when drawn. */
const plain = (s: string): string => s.replace(/[<>"'&]/g, "");
function act(a: string): void {
  const [k, v = ""] = plain(a).split(/:(.*)/s);
  switch (k) {
    case "keep": return;
    case "closeoverlay": case "closesheet": S.overlay = null; draw(); return;
    case "shell": {
      const map: Record<string, Overlay> = { launcher: "launcher", account: "account", globe: "globe", search: "cmd", help: "help", bell: "bell", sync: "sync", menu: "launcher" };
      if (v === "theme") { S.theme = S.theme === "dark" ? "light" : "dark"; $<HTMLInputElement>("#cDark").checked = S.theme === "dark"; S.overlay = null; draw(); return; }
      if (v === "signout" || v === "signin" || v === "voice") { S.overlay = null; draw(); return; }
      S.overlay = S.overlay === map[v] ? null : (map[v] ?? null); S.query = ""; draw();
      if (S.overlay === "cmd") $<HTMLInputElement>("#cmdIn")?.focus();
      return;
    }
    case "nav": S.screen = v === "home" ? "home" : v === "sell" ? "payment" : v === "business" ? "state:empty" : S.screen; S.overlay = null; draw(); return;
    case "go": S.screen = v === "home" ? "home" : S.screen; S.overlay = null; draw(); return;
    case "place": case "business": case "role": case "region": case "open": case "notice": case "help": case "support": case "assist": case "copy": S.overlay = null; record("ShellAction", "device", { action: a }); draw(); return;
    case "lang": S.lang = v; $<HTMLSelectElement>("#cLang").value = v; S.overlay = null; draw(); return;
    case "newsale": record("SaleRecorded", "device", { total: 1500, currency: pack().currency }); S.overlay = null; draw(); return;
    case "archive": { const id = `arch${++S.archived}`; S.undo.push(id, t("product_archived"), Date.now(), () => record("ProductArchiveUndone", "device", { id })); record("ProductArchived", "device", { id }); S.overlay = null; draw(); return; }
    case "void": { const id = `void${++S.voided}`; S.undo.push(id, t("sale_voided"), Date.now(), () => record("SaleVoidReversedWithReason", "device", { id, reason: "entered_in_error" }), true); record("SaleVoided", "device", { id }); S.overlay = null; draw(); return; }
    case "undo": { const r = S.undo.undo(v, Date.now()); record("AutomationUndone", "device", { id: v, result: r }); draw(); return; }
    case "chart": S.chartView = v.endsWith(":table") ? "table" : "chart"; draw(); return;
    case "chat": S.showOriginal = v === "lang:original" || v.startsWith("original:"); draw(); return;
    case "username": S.username = v; S.cloud = S.link === "offline" ? "checking" : v === "mamas.kitchen" ? "taken" : "available"; draw(); return;
    case "notify": S.notified.add(v); record("NotifyMeSubscribed", "device", { service: v }); draw(); return;
    case "toggle": if (v === "datasaver") S.dataSaver = !S.dataSaver; if (v === "forced") S.forced = !S.forced; draw(); return;
    case "sync": if (S.link !== "offline" && !S.forced) { S.lastSync = Date.now(); S.events.forEach((e) => { if (e.sync === "queued") e.sync = "sent"; }); S.pending = 0; record("SyncCompleted", "server", {}); } S.overlay = null; draw(); return;
  }
}

function init(): void {
  const bind = (sel: string, fn: (el: HTMLInputElement) => void) => $<HTMLInputElement>(sel).addEventListener("change", (e) => fn(e.target as HTMLInputElement));
  bind("#cSize", (el) => { S.size = el.value as Viewport; S.overlay = null; draw(); });
  bind("#cLink", (el) => { S.link = el.value as Link; draw(); });
  bind("#cDark", (el) => { S.theme = el.checked ? "dark" : "light"; draw(); });
  bind("#cMode", (el) => { S.mode = el.value as "" | "lite" | "sunlight"; draw(); });
  bind("#cReal", (el) => { S.realUser = el.checked; draw(); });
  const country = $<HTMLSelectElement>("#cCountry");
  country.innerHTML = DATA.packOrder.map((c) => { const p = DATA.packs[c] as CountryPack; return `<option value="${esc(c)}">${esc(p.sample ? t("sample_country") : p.name)}</option>`; }).join("");
  country.addEventListener("change", (e) => { S.country = (e.target as HTMLSelectElement).value; draw(); });
  const sel = $<HTMLSelectElement>("#cLang");
  sel.insertAdjacentHTML("afterbegin", Object.entries(PACKS).map(([code, p]) => `<option value="${esc(code)}" lang="${esc(code)}" dir="${p.dir}">${esc(p.native)}</option>`).join(""));
  sel.value = "en";
  sel.addEventListener("change", (e) => { S.lang = (e.target as HTMLSelectElement).value; draw(); });
  const kinds: Screen[] = ["home", "payment", "state:loading", "state:empty", "state:offline", "state:error", "state:not_found", "state:no_results", "state:permission", "state:maintenance", "state:sync_pending", "state:coming_soon", "state:success"];
  $("#stateButtons").innerHTML = kinds.map((k) => `<button type="button" data-state="${k}">${esc(k === "home" ? "Home" : k === "payment" ? "Payment (protected)" : k.slice(6).replace("_", " "))}</button>`).join("");
  $("#stateButtons").addEventListener("click", (e) => { const b = (e.target as HTMLElement).closest<HTMLElement>("button[data-state]"); if (b) { const picked = kinds.find((k) => k === b.dataset["state"]); if (picked) { S.screen = picked; S.overlay = null; draw(); } } });
  $("#display").addEventListener("click", (e) => {
    const el = (e.target as HTMLElement).closest<HTMLElement>("[data-act]");
    if (!el) return;
    if (el.tagName === "A") e.preventDefault();
    if (el.dataset["act"] === "closeoverlay" && e.target !== el) return;
    act(el.dataset["act"]!);
  });
  $("#display").addEventListener("input", (e) => {
    const el = e.target as HTMLInputElement;
    if (el.id === "cmdIn") { S.query = plain(el.value); const list = $("#cmdList"); const index = overlay(); const m = /<ul id="cmdList"[^>]*>([\s\S]*?)<\/ul>/.exec(index); if (list && m) list.innerHTML = m[1]!; }
    if (el.id === "usernameIn") { act(`username:${el.value}`); const inp = $<HTMLInputElement>("#usernameIn"); inp.focus(); inp.setSelectionRange(inp.value.length, inp.value.length); }
  });
  $("#display").addEventListener("change", (e) => { const el = e.target as HTMLInputElement; if (el.dataset["act"]?.startsWith("toggle:")) act(el.dataset["act"]); });
  document.addEventListener("keydown", (e) => { if (e.key === "/" && !(e.target as HTMLElement).matches("input,select,textarea")) { e.preventDefault(); act("shell:search"); } if (e.key === "Escape" && S.overlay) { S.overlay = null; draw(); } });
  const fit = () => { const w = $("#rig").clientWidth - 8, dev = { computer: 1280, tablet: 800, phone: 390 }[S.size]; document.documentElement.style.setProperty("--fit", String(Math.min(1, w / dev))); };
  new ResizeObserver(fit).observe($("#rig")); fit();
  bind("#cSize", () => fit());
  window.setInterval(() => { if (S.undo.openToasts(Date.now()).length || $(".toasts").children.length) draw(); }, 1000);
  draw(); drawLog();
}
init();
