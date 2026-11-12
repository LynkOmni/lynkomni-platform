/* The shared LynkOmni shell inside a browser window (build section 1). Every part comes from ts/src/shell.ts; this file only
 * holds the sample page, the emulator controls and the event log. Words come from strings.en.json and the language packs. */
import { STATE_PICTURE, Undo, accountMenu, viewSheet, IFACE_NAME, chart, comingSoon, commandBar, connectionChip, deliverNow, esc, filterRegions, globeSheet, regionName, header, helpPanel, launcher, messageNote, messageText, navigation, notificationsPanel, route, search, state, syncSheet, translationBanner, translator, undoToast, usernameField } from "../../../ts/src/shell.js";
import type { AddressMap, ChatLang, ChatMessage, Entry, Icon, Link, NavItem, Notice, Pic, StateKind, SyncInfo, T, UsernameStatus, Viewport } from "../../../ts/src/shell.js";
import type { UserState } from "../../../ts/src/pos.js";
import { brandMark, markFor } from "../../../ts/src/brand.js";
import { buildFooter, mainFooterHtml } from "../../../ts/src/footer.js";
import type { BrandPlaces } from "../../../ts/src/brand.js";
import { browserFacts, chooseInterface, safeToSwitch } from "../../../ts/src/interfaces.js";
import type { Choice } from "../../../ts/src/interfaces.js";
import { DEVICES } from "../../../ts/src/interfaces.generated.js";
import { arrowNav, gestures } from "../../../ts/src/gestures.js";
import { afterWrong, numberChoices, numberMatch, numberShown, pinPad, KEY_TONE } from "../../../ts/src/signin.js";
import { banner, bell, count, feelFor, mailPart, messagesList, priorityOf, textPart, whySheet } from "../../../ts/src/notify.js";
import type { Line, Priority, Sent } from "../../../ts/src/notify.js";
import { askBox, buildPack, confirmCard, decide, fixThis, lookup, receipt } from "../../../ts/src/assist.js";
import { breadcrumbBar, trail } from "../../../ts/src/breadcrumbs.js";
import { idcnEntry, quickRating, rateUs, scoreScale, ticketCard } from "../../../ts/src/peopleparts.js";
const HEADER_ROOM = { computer: 160, tablet: 160, phone: 160 } as const;   // px the shell header gives its brand place at each size; web-header shows the logo from 96 px (brand/surfaces.v1.json), so every size has room for it

interface CountryPack { code: string; name: string; currency: string; tz: string; locale: string; sample: boolean; card_networks: string[]; wallets: string[]; providers: string[]; ready: Record<string, { ok: boolean; message: string }>; services: { service: string; id?: string; name: string; icon: string; plain: string; href?: string; state: "available" | "coming_soon" }[] }
interface BuildData {
  icons: Record<string, string>;
  brand: { body: string; receipt: string; places: BrandPlaces };
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
type Overlay = null | "launcher" | "account" | "globe" | "cmd" | "help" | "bell" | "sync" | "view" | "why";
type Screen = "home" | "payment" | `state:${StateKind}`;

const S = {
  size: "computer" as Viewport, lang: "en", theme: "light" as "light" | "dark", mode: "" as "" | "lite" | "sunlight", link: "good" as Link, country: "", realUser: false,
  screen: "home" as Screen, overlay: null as Overlay, query: "", chartView: "chart" as "chart" | "table", showOriginal: false, username: "", cloud: null as UsernameStatus,
  notified: new Set<string>(), dataSaver: false, forced: false, pending: 0, lastSync: null as number | null, events: [] as Ev[], undo: new Undo(), archived: 0, voided: 0, seen: new Set<string>(),
  // BIZZ & DEVICE: the side of the screen and the interface this device uses (chosen automatically; Change view overrides it)
  side: "internal" as "internal" | "external", override: null as string | null, pendingView: undefined as string | null | undefined,
  testView: "auto", testWidth: "auto", choice: null as Choice | null,
  // MASTER UPDATE, section 1: the bell, the sign-in parts and LynkAssist in the help panel
  lines: [] as Line[], bellFilter: "all", lastOpened: 0, whyNid: "", banners: [] as string[],
  pin: "", wrong: 0, waitUntil: 0, pictures: true, keySound: true, matchShown: "47", matchChoices: [] as string[], matchResult: "" as "" | "ok" | "wrong",
  ask: "", assistStep: "idle" as "idle" | "card" | "done", assistDoneAt: 0, resends: 0, lastDone: null as null | { nid: string; by: string },
  // NEW UPDATE 4, section 1: the shared parts of LynkAttend, LynkQueue and LynkSurvey
  rate: null as number | null, score: null as number | null, checker: null as string | null, called: false,
};
/** The interfaces a browser window can show; the others belong to their own devices (catalog/devices.v1.json). */
const VIEWS = ["universal", "phone.touch", "tablet.touch", "computer.touch", "computer.pointer"] as const;
const DEFAULT_WIDTH: Record<string, number> = { phone: 390, tablet: 800, computer: 1280, watch: 240, tv: 1920, eink: 600, voice: 390 };
const $ = <T extends HTMLElement>(sel: string): T => document.querySelector(sel) as T;
const PSEUDO: Record<string, string> = { a: "à", c: "ç", e: "é", i: "î", n: "ñ", o: "ö", s: "š", u: "ü", y: "ý" };
const pseudo = (s: string): string => `[${s.replace(/[aceinosuy]/g, (c) => PSEUDO[c] ?? c)} ${"~".repeat(Math.max(1, Math.round(s.length * 0.4)))}]`;
const isTest = (): boolean => TEST_LANGS.includes(S.lang);
const t: T = (k, vars) => (isTest() ? pseudo(translator(EN)(k, vars)) : translator(PACKS[S.lang]?.texts ?? EN, EN)(k, vars));
const icon: Icon = (id, cls = "ic") => `<span class="${cls}" aria-hidden="true">${DATA.icons[id] ?? ""}</span>`;
const pack = (): CountryPack => DATA.packs[S.country] ?? (DATA.packs[DATA.packOrder[0] ?? ""] as CountryPack);
/** The main footer (blueprint 26 A and B): every word from the language packs, payment methods from the chosen country's pack,
 *  the copyright line fixed and never translated. */
const appFooter = (): string => {
  const p = pack();
  return mainFooterHtml(buildFooter({ now: new Date(), lang: S.lang, words: (k) => (k in EN ? t(k) : undefined),
    pack: { code: p.code, name: p.name, currency: p.currency, tz: p.tz, languages: [], providers: p.providers, card_networks: p.card_networks, wallets: p.wallets } }), esc, (id) => DATA.icons[id] ?? "",
    { light: markFor(DATA.brand.places, "web-footer", false, FOOTER_LOGO_ROOM[S.size]).svg, dark: markFor(DATA.brand.places, "web-footer", true, FOOTER_LOGO_ROOM[S.size]).svg });
};
/** Room for the footer logo (brand surface web-footer): the full logo whenever 120 px or more is free, which is every size here. */
const FOOTER_LOGO_ROOM: Record<string, number> = { computer: 180, tablet: 180, phone: 160 };
const locale = (): string => `${isTest() ? "en" : S.lang}-${pack().code}`;
const money = (minor: number): string => { try { return new Intl.NumberFormat(locale(), { style: "currency", currency: pack().currency }).format(minor / 100); } catch { return `${pack().currency} ${(minor / 100).toFixed(2)}`; } };
const clock = (ms: number): string => new Intl.DateTimeFormat(locale(), { timeZone: pack().tz, hour: "2-digit", minute: "2-digit" }).format(ms);
const langName = (code: string): string => PACKS[code]?.native ?? code;
const SHOP = (): string => t("shop_name");
/** The decision function on this device's own reported facts (never its browser's name); the testing panel may force a view. */
const choose = (): Choice => {
  const forced = S.testView !== "auto" ? S.testView : null;
  return chooseInterface(DEVICES, { ...browserFacts(window), override: forced ?? S.override });
};
const width = (): number => S.testWidth !== "auto" ? Number(S.testWidth) : (DEFAULT_WIDTH[S.choice?.class ?? "computer"] ?? 1280);
const sizeOf = (w: number): Viewport => w < 600 ? "phone" : w < 1024 ? "tablet" : "computer";
const sideWord = (side: "internal" | "external"): string => side === "external" ? t("side_storefront") : t("side_business");
// Sample sales for the chart: data the emulator itself holds (minor units), labelled sample in the page header.
const SAMPLE_WEEK = [42000, 51500, 38000, 60250, 72000, 91000, 30500];
const DAYS = ["day_mon", "day_tue", "day_wed", "day_thu", "day_fri", "day_sat", "day_sun"];

function record(type: string, origin: "device" | "server", payload: unknown): void {
  const sync: UserState = origin === "server" ? "confirmed" : S.link === "offline" || S.forced ? "queued" : "sent";
  S.events.unshift({ n: S.events.length + 1, type, origin, payload, sync, at: Date.now() });
  if (sync === "queued") S.pending++;
  drawLog();
}

// ---------------------------------------------------------------- MASTER UPDATE, section 1: the bell, sign-in parts, LynkAssist
// Lines hold word keys; they are put into the reader's language when drawn, so a language change changes every line at once.
const T0 = Date.now();
S.lines = [
  { nid: "n1", kind: "new_sign_in", title: "notice_signin", at: T0 - 60_000, record: "LONTF-2201-4410-8838" },
  { nid: "n5", kind: "staff_request", title: "demo_ntf_staff", at: T0 - 300_000 },
  { nid: "n4", kind: "stock_low", title: "demo_ntf_stock", at: T0 - 1_200_000, count: 12 },
  { nid: "n2", kind: "receipt", title: "notice_payment", at: T0 - 3_600_000, record: "LORCP-7731-0042-9911", read: true, seen: true },
  { nid: "n3", kind: "owner_summary", title: "notice_insight", at: T0 - 7_200_000, read: true, seen: true },
];
S.lastOpened = T0 - 1_800_000;
const ACT_WORD: Record<string, string> = { approve: "ntf_act_approve", deny: "ntf_act_deny", cancel_recovery: "ntf_act_cancel_recovery", this_was_not_me: "ntf_act_this_was_not_me", draft_reorder: "ntf_act_draft_reorder", confirm: "as_confirm", undo: "undo" };
const AREAS = ["security", "account", "safety", "selling", "stock", "devices"];
const shown = (): Line[] => S.lines.map((l) => ({ ...l, title: t(l.title), actions: (KIND_ACTIONS[l.kind] ?? []).filter((a) => ACT_WORD[a]).map((a) => ({ id: a, label: t(ACT_WORD[a]!) })) }));
const KIND_ACTIONS: Record<string, string[]> = { new_sign_in: ["this_was_not_me"], staff_request: ["approve", "deny"], stock_low: ["draft_reorder"], recovery_started: ["cancel_recovery"] };
const when = (ms: number): string => clock(ms);
const lineOf = (nid: string): Line | undefined => S.lines.find((l) => l.nid === nid);
/** Each priority is felt as well as seen: the tones and vibration of notify.ts FEEL (never instead of the words). */
let audio: AudioContext | null = null;
function feel(p: Priority): void {
  const f = feelFor(p, { quiet: false, silent: false, lowData: S.dataSaver });
  try { (navigator as Navigator & { vibrate?: (p: number[]) => boolean }).vibrate?.(f.vibrate); } catch { /* not every device vibrates */ }
  if (!f.tones.length) return;
  try {
    audio ??= new AudioContext();
    let at = audio.currentTime;
    for (const [hz, ms] of f.tones) {
      if (hz) { const o = audio.createOscillator(), g = audio.createGain(); o.frequency.value = hz; g.gain.setValueAtTime(0.08, at); g.gain.exponentialRampToValueAtTime(0.0001, at + ms / 1000); o.connect(g).connect(audio.destination); o.start(at); o.stop(at + ms / 1000); }
      at += ms / 1000;
    }
  } catch { /* sound is never the only signal */ }
}
/** A key press on the PIN pad is heard as its own pair of tones, so a person who cannot see the screen knows which key went in. */
function keyTone(k: string): void {
  if (!S.keySound) return;
  const pair = KEY_TONE[k]; if (!pair) return;
  try { audio ??= new AudioContext(); const at = audio.currentTime; for (const hz of pair) { const o = audio.createOscillator(), g = audio.createGain(); o.frequency.value = hz; g.gain.setValueAtTime(0.05, at); g.gain.exponentialRampToValueAtTime(0.0001, at + 0.12); o.connect(g).connect(audio.destination); o.start(at); o.stop(at + 0.12); } } catch { /* silent device */ }
}
function urgent(): void {
  const nid = `u${S.lines.length + 1}`;
  S.lines.unshift({ nid, kind: "recovery_started", title: "demo_ntf_recovery", at: Date.now() });
  S.banners.unshift(nid);
  record("NotificationShown", "server", { kind: "recovery_started", priority: "critical", channels: ["bell", "push", "email", "text"] });
  feel("critical"); draw();
}
let kpack: { lang: string; entries: ReturnType<typeof buildPack> } | null = null;
const knowledge = () => { const lang = isTest() ? "en" : S.lang; if (!kpack || kpack.lang !== lang) kpack = { lang, entries: buildPack({ ...EN, ...(PACKS[lang]?.texts ?? {}) }) }; return kpack.entries; };
function assistPart(): string {
  const online = S.link !== "offline" && !S.forced;
  const ask = askBox({ query: S.ask, results: S.ask ? lookup(knowledge(), S.ask) : [], online, builtOn: new Intl.DateTimeFormat(locale(), { dateStyle: "medium" }).format(T0) }, t, icon);
  const mute = decide("mute_notification_kind", { role: "owner", confirmed: S.assistStep === "done" });
  const step = S.assistStep === "card" ? confirmCard({ what: t("demo_assist_mute"), d: mute }, t, icon)
    : S.assistStep === "done" ? receipt({ what: t("demo_assist_mute"), undoable: !!mute.undo, secondsLeft: Math.max(0, 30 - Math.round((Date.now() - S.assistDoneAt) / 1000)) }, t, icon)
    : `<div class="actions"><button type="button" class="secondary" data-act="assist:resend">${icon("product-assist")}<span>${esc(t("demo_assist_what"))}</span></button><button type="button" class="secondary" data-act="assist:mute">${icon("product-assist")}<span>${esc(t("demo_assist_mute"))}</span></button></div>`;
  return `${ask}${step}`;
}
function pinCard(): string {
  const waitLeft = Math.max(0, Math.ceil((S.waitUntil - Date.now()) / 1000));
  if (!S.matchChoices.length) { let x = 7; S.matchChoices = numberChoices(S.matchShown, () => (x = (x * 9301 + 49297) % 233280) / 233280); }
  return `<div class="card"><h2>${esc(t("demo_signin_card"))}</h2>${pinPad({ entered: S.pin.length, length: Math.max(4, S.pin.length), wrong: S.wrong, waitLeft, pictures: S.pictures, sound: S.keySound, title: t("demo_pin_title") }, t, icon)}<div class="pstack">${numberShown(S.matchShown, t)}${numberMatch(S.matchChoices, t, S.matchResult)}</div></div>`;
}
function peopleCard(): string {
  const tk = ticketCard({ section: "LAB", sectionName: t("demo_section_lab"), code: "A2K9P2", place: S.called ? null : 4, waitMinutes: S.called ? null : 12, counter: S.called ? t("demo_counter") : null }, t, icon);
  const call = `<div class="actions"><button type="button" class="secondary" data-act="ppl:call">${esc(t(S.called ? "demo_back_waiting" : "demo_call_next"))}</button></div>`;
  return `<div class="card" style="grid-column:1/-1"><h2>${esc(t("demo_people_card"))}</h2><div class="pstack"><div>${tk}${call}</div>${idcnEntry({ typed: 6, checkers: ["Ama", "Ben", "Grace"], me: "Grace", chosen: S.checker, triesLeft: null }, t)}${quickRating(t("demo_rate_title"), S.rate, t)}${scoreScale(t("demo_score_title"), S.score, t)}${rateUs(icon, t)}</div></div>`;
}
function messagesCard(): string {
  const p = pack();
  const sent: Sent[] = [{ id: "m1", channel: "email", sender: "receipts@mail.lynkomni.com", title: t("demo_mail_title"), at: T0 - 600_000, state: "confirmed" }, { id: "m2", channel: "text", sender: "LynkOmni", title: t("demo_text"), at: T0 - 590_000, state: S.link === "offline" ? "queued" : "sent" }];
  const logo = markFor(DATA.brand.places, "email-header", S.theme === "dark", 160).svg;
  return `<div class="card" style="grid-column:1/-1"><h2>${esc(t("demo_messages_card"))}</h2><div class="pstack">${mailPart({ title: t("demo_mail_title"), lines: [t("demo_mail_line"), money(1500)], record: "LORCP-7731-0042-9911", button: { label: t("demo_mail_title"), href: "https://pay.lynkomni.com/r/LORCP-7731-0042-9911" }, reason: t("demo_mail_reason"), optIn: false, lang: d0().lang, dir: d0().dir === "rtl" ? "rtl" : "ltr" }, logo, t)}${textPart(t("demo_text"), t)}${messagesList(sent, t, icon, when)}</div><p class="note">${esc(p.sample ? t("sample_country") : p.name)}</p></div>`;
}
const d0 = (): HTMLElement => $("#display");
/** The breadcrumb trail of the current address, from the address map (core/breadcrumbs.py rules); labels from the menu words. */
function crumbs(): string {
  const path = screenPath() === "/" ? "/business" : screenPath();
  const label: Record<string, string> = { "/": t("tab_home"), "/business": t("tab_business"), "/sell": t("tab_sell"), "/external": t("side_storefront"), "/external/business": t("tab_business"), "/external/sell": t("tab_sell"), "/business/settings": t("nav_settings"), "/analytics": t("nav_reports") };
  let steps: string[];
  try { steps = trail("app.lynkomni.com", path); } catch { return ""; }
  return breadcrumbBar(steps.map((p) => ({ path: p, label: label[p] ?? p.split("/").pop() ?? p })), S.size === "phone", t);
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
const screenPath = (): string => {
  const p = S.screen === "home" ? "/business" : S.screen === "payment" ? "/sell" : S.screen === "state:not_found" ? "/nowhere" : "/business";
  return S.side === "external" && p !== "/nowhere" ? `/external${p}` : S.screen === "home" ? "/" : p;    // the Storefront is /external + the workspace path
};
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
    const fix = kind === "error" || kind === "sync_pending" || kind === "offline" ? fixThis(kind, t, icon) : "";
    return `${crumbs()}<div class="pagetitle"><h1>${esc(t("states_card"))}</h1>${connectionChip(sync(), t, icon)}</div><div class="card">${body}${fix}</div><p class="note">${esc(t("states_hint"))}</p>`;
  }
  if (S.screen === "payment") {
    return `${crumbs()}<div class="pagetitle"><h1>${esc(t("tab_sell"))}</h1>${connectionChip(sync(), t, icon)}</div><div class="card"><div class="protected-note">${icon("ui-lock")}<span>${esc(t("protected_zone"))}</span></div><p class="muted" style="margin-top:8px">${esc(t("deep_link"))}: <span class="deeplink">https://app.lynkomni.com/sell</span></p><div class="actions"><button class="primary" data-act="go:home">${esc(t("action_home"))}</button></div></div>`;
  }
  const chartHtml = chart({ title: t("chart_title"), labels: DAYS.map((d) => t(d)), series: [{ name: t("today_sales"), values: SAMPLE_WEEK }], kind: "bar", format: money }, S.chartView, t, "week");
  // The demo customer always writes in a language other than the reader's, so the two-language chat is always two languages.
  const reader = isTest() ? "en" : S.lang;
  const writer = reader === "ar" ? "sw" : "ar";
  const writerText = writer === "ar" ? "هل يمكنك أن تحتفظ لي بصينيتين من البيض حتى الساعة 5 مساءً؟" : "Unaweza kuniwekea trei mbili za mayai hadi saa 11 jioni?";
  const chatLang: ChatLang = { reader, writer, writerName: t("customer_name"), showOriginal: S.showOriginal };
  const msg: ChatMessage = { id: "m1", text: writerText, translated: t("chat_sample_translated"), language: writer, pendingTranslation: S.link === "offline" || S.forced };
  const here = route(DATA.addresses, `https://app.lynkomni.com${screenPath()}`);
  return `${crumbs()}<div class="pagetitle"><h1>${esc(t("title_home", { shop: SHOP() }))}</h1>${connectionChip(sync(), t, icon)}</div>
    <div class="cards">
      <div class="card"><h2>${esc(t("today_sales"))}</h2><div class="big">${esc(money(SAMPLE_WEEK[new Date().getDay() === 0 ? 6 : new Date().getDay() - 1] ?? 0))}</div><div class="muted">${esc(t("sales_count", { n: 14 }))}</div>
        <div class="actions"><button class="primary" data-act="newsale">${icon("ui-plus")}<span>${esc(t("new_sale"))}</span></button><button class="secondary" data-act="archive">${esc(t("archive_product"))}</button><button class="secondary" data-act="void">${esc(t("void_sale"))}</button></div></div>
      <div class="card"><h2>${esc(t("today_profit"))}</h2><div class="big">${esc(money(Math.round((SAMPLE_WEEK[4] ?? 0) * 0.27)))}</div><div class="muted">${esc(t("deep_link"))}: <span class="deeplink">${esc(here ? `app.lynkomni.com${here.path}` : "")}</span></div></div>
      <div class="card" style="grid-column:1/-1">${chartHtml}</div>
      <div class="card"><h2>${esc(t("username_card"))}</h2>${usernameField(S.username, S.cloud, (u) => u === "mamas.kitchen", t, icon)}</div>
      <div class="card"><h2>${esc(t("chat_card"))}</h2><div class="chat-demo">${translationBanner(chatLang, langName, t)}<div class="msg" lang="${messageText(msg, chatLang) === msg.text ? writer : esc(reader)}" dir="${messageText(msg, chatLang) === msg.text ? (PACKS[writer]?.dir ?? "ltr") : (PACKS[S.lang]?.dir ?? "ltr")}">${esc(messageText(msg, chatLang))}${messageNote(msg, chatLang, langName, t)}</div><div class="msg out">${esc(t("chat_reply"))}</div></div></div>
      ${pinCard()}
      ${messagesCard()}
      ${peopleCard()}
      <div class="card" style="grid-column:1/-1"><p class="muted">${icon("ui-sync")} ${esc(t("handoff_note"))}</p></div>
    </div>`;
}

function overlay(): string {
  const wrap = (cls: string, inner: string) => `<div class="overlay ${cls}" data-act="closeoverlay">${inner.replace(/^<(div|aside)/, '<$1 data-act="keep"')}</div>`;
  switch (S.overlay) {
    case "launcher": return wrap("", launcher(pack().services.map((s) => ({ id: s.id ?? s.service, name: s.name, plain: t(`ft_plain_${s.plain}`), icon: s.icon, href: s.href ?? `/${s.service}`, state: S.realUser ? s.state : "available" })), t, icon, sides()));
    case "account": return wrap("end", accountMenu({ name: "Grace", lynkId: "LOID-4821-9035-7715", businesses: [{ id: "b1", name: SHOP(), current: true }, { id: "b2", name: `${SHOP()} 2`, current: false }], role: "owner", roles: ["owner", "manager", "cashier"], theme: S.mode === "lite" ? "lite" : S.mode === "sunlight" ? "sunlight" : S.theme, language: langName(isTest() ? "en" : S.lang), region: pack().sample ? t("sample_country") : pack().name, sides: sides(), view: { name: t(IFACE_NAME[S.choice?.interface ?? "universal"] ?? "iface_universal") } }, t, icon));
    case "view": return wrap("", viewSheet({ current: S.choice?.interface ?? "universal", rule: S.choice?.rule ?? "safe_default", options: [...VIEWS], ownerOnly: false, canChange: true }, t, icon) + (S.pendingView !== undefined ? `<p class="toast-note" role="status">${esc(t("view_waits"))}</p>` : ""));
    case "globe": return wrap("", globeSheet(Object.entries(PACKS).map(([code, p]) => ({ code, native: p.native, dir: p.dir })), DATA.packOrder.map((c) => ({ code: c, name: (DATA.packs[c] as CountryPack).sample ? t("sample_country") : regionName(c, isTest() ? "en" : S.lang, (DATA.packs[c] as CountryPack).name) })), { language: isTest() ? "en" : S.lang, region: pack().code }, t));
    case "cmd": {
      const index: Entry[] = [
        { id: "a1", kind: "action", title: t("new_sale"), act: "newsale" }, { id: "a2", kind: "action", title: t("archive_product"), act: "archive" },
        { id: "p1", kind: "product", title: "Rice 1 kg", subtitle: money(1500), act: "go:home" }, { id: "c1", kind: "customer", title: t("customer_name"), act: "go:home" },
        { id: "r1", kind: "report", title: t("chart_title"), act: "go:home" }, { id: "s1", kind: "setting", title: t("nav_settings"), act: "go:home" },
        { id: "v1", kind: "action", title: t("switch_side", { side: sideWord(S.side === "external" ? "internal" : "external") }), act: "shell:side" },
        { id: "v2", kind: "setting", title: t("change_view"), act: "shell:view" }, { id: "v3", kind: "help", title: t("why_this_view"), act: "shell:why" },
        { id: "h1", kind: "help", title: t("help_article_1"), act: "shell:help" }, { id: "h2", kind: "help", title: t("help_article_2"), act: "shell:help" },
      ];
      return wrap("", commandBar(S.query, search(index, S.query), t, icon));
    }
    case "help": return wrap("end", helpPanel(t("tab_home"), [{ id: "1", title: t("help_article_1"), href: "/faq/pos/offline" }, { id: "2", title: t("help_article_2"), href: "/faq/mpay/waiting" }, { id: "3", title: t("switch_side_group"), href: "/faq/storefront/sides" }, { id: "4", title: t("why_this_view"), href: "/faq/devices/view" }], t, icon, assistPart()));
    case "bell": {
      const present = AREAS.filter((a) => S.lines.some((l) => (KIND_AREA[l.kind] ?? "") === a)).map((a) => ({ id: a, label: t(`ntf_area_${a}`) }));
      return wrap("end", bell(shown(), { filter: S.bellFilter, lastOpened: S.lastOpened, areas: present }, t, icon, when));
    }
    case "why": { const l = shown().find((x) => x.nid === S.whyNid); return l ? wrap("", whySheet(l, t, icon)) : ""; }
    case "sync": return wrap("bottom", syncSheet(sync(), t, icon, clock));
    default: return "";
  }
}

const KIND_AREA: Record<string, string> = { new_sign_in: "security", recovery_started: "security", staff_request: "selling", stock_low: "stock", receipt: "proof", owner_summary: "selling" };
const sides = () => ({ current: S.side, workspaceWord: sideWord("internal"), storefrontWord: sideWord("external") });

let lastOverlay: Overlay = null;
function draw(): void {
  if (lastOverlay === "bell" && S.overlay !== "bell" && S.overlay !== "why") S.lastOpened = Date.now();   // New becomes Earlier once the bell was seen
  if (S.overlay === "bell") S.lines.forEach((l) => { l.seen = true; });
  lastOverlay = S.overlay;
  S.choice = choose();
  const W = width(); S.size = sizeOf(W);
  const d = $("#display");
  d.dataset["deviceClass"] = S.choice.class; d.dataset["interface"] = S.choice.interface;      // type scale and focus rules per device (design tokens)
  const auto = $("#autoName"); if (auto) auto.textContent = `${EN[IFACE_NAME[chooseInterface(DEVICES, browserFacts(window)).interface] ?? "iface_universal"] ?? ""}`;
  d.className = `display ${S.theme}`;
  if (S.mode) d.setAttribute("data-mode", S.mode); else d.removeAttribute("data-mode");
  d.lang = S.lang === "xx-rtl" ? "ar" : S.lang === "xx" ? "en" : S.lang;
  d.dir = S.lang === "xx-rtl" ? "rtl" : S.lang === "xx" ? "ltr" : PACKS[S.lang]?.dir ?? "ltr";
  const logo = brandMark(DATA.brand.places, "web-header", S.theme === "dark", "brandfill", HEADER_ROOM[S.size]);
  const items = navItems();
  const head = header({ logo, nav: items, notifications: count(S.lines), signedIn: true, title: S.size === "computer" ? undefined : SHOP(), surface: "app", side: { label: sideWord(S.side), storefront: S.side === "external" } }, S.size, t, icon);
  const nav = navigation(items, S.size, t, icon);
  const toasts = S.undo.openToasts(Date.now()).map((u) => undoToast(u, Date.now(), t, icon)).join("");
  d.innerHTML = `<div class="shell">${head}<div class="shell-body">${S.size === "phone" ? "" : nav}<main class="shell-main" id="main">${main()}<div class="footer-line">${esc(S.realUser ? "" : t("sandbox"))}</div>${appFooter()}</main></div>${S.size === "phone" ? nav : ""}${overlay()}<div class="banners">${S.banners.map((nid) => { const l = shown().find((x) => x.nid === nid); return l ? banner(l, t, icon) : ""; }).join("")}</div><div class="toasts">${toasts}</div></div>`;
  $("#device").className = `device ${S.size}`;
  $("#device").style.width = `${W}px`;
  $("#tab").className = `tab ${S.theme}`;                       // the tab and its icon follow the page theme (brand surface "favicon")
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
/** A choice from a control is only ever one of the known values, never the control's own text. */
const pick = <V extends string>(allowed: readonly V[], value: string, fallback: V): V => allowed.find((x) => x === value) ?? fallback;
function act(a: string): void {
  const [k, v = ""] = plain(a).split(/:(.*)/s);
  switch (k) {
    case "keep": return;
    case "ppl": {
      const [what = "", n = ""] = v.split(":");
      if (what === "rate") S.rate = Number(n); else if (what === "score") S.score = Number(n); else if (what === "call") S.called = !S.called;
      else if (what === "checker") S.checker = ($<HTMLSelectElement>("#checker").value || null);
      draw(); return;
    }
    case "ntf": {
      const [what = "", nid = "", extra = ""] = v.split(":");
      const l = lineOf(nid);
      if (what === "filter") { S.bellFilter = nid; draw(); return; }
      if (what === "allread") { S.lines.forEach((x) => { x.read = true; }); record("NotificationsRead", "device", { all: true }); draw(); return; }
      if (!l) return;
      if (what === "read") { l.read = !l.read; record(l.read ? "NotificationRead" : "NotificationUnread", "device", { nid }); }
      if (what === "open") { l.read = true; S.overlay = null; record("NotificationOpened", "device", { nid, kind: l.kind }); }
      if (what === "why") { S.whyNid = nid; S.overlay = "why"; }
      if (what === "dismiss") S.banners = S.banners.filter((b) => b !== nid);
      if (what === "ack") { l.acknowledged = true; l.read = true; l.seen = true; S.banners = S.banners.filter((b) => b !== nid); record("NotificationAcknowledged", "device", { nid, kind: l.kind }); }
      if (what === "act") {
        l.doneBy = "Grace"; l.read = true;
        record("NotificationActed", "device", { nid, kind: l.kind, action: extra });
        S.undo.push(`ntf-${nid}`, t("ntf_done_by", { name: "Grace" }), Date.now(), () => { l.doneBy = undefined; record("NotificationActionUndone", "device", { nid }); });
      }
      draw(); return;
    }
    case "pin": {
      if (afterWrong(S.wrong) === "locked" || Date.now() < S.waitUntil) return;
      if (v === "pictures") { S.pictures = !S.pictures; draw(); return; }
      if (v === "sound") { S.keySound = !S.keySound; draw(); return; }
      keyTone(v);
      if (v === "clear") S.pin = "";
      else if (/^\d$/.test(v) && S.pin.length < 8) S.pin += v;
      else if (v === "ok") {
        if (S.pin === "2580") { S.wrong = 0; record("DeviceUnlocked", "device", { by: "pin" }); }
        else { S.wrong += 1; const w = afterWrong(S.wrong); if (typeof w === "number" && w) S.waitUntil = Date.now() + w * 1000; record(w === "locked" ? "DeviceHardLocked" : "PinRefused", "device", { wrong: S.wrong }); }
        S.pin = "";
      }
      draw(); return;
    }
    case "match": { S.matchResult = v === S.matchShown ? "ok" : "wrong"; record(S.matchResult === "ok" ? "OfflinePermissionGranted" : "OfflinePermissionRefused", "device", { matched: S.matchResult === "ok" }); draw(); return; }
    case "assist": {
      if (v === "resend") { const d = decide("resend_receipt", { role: "cashier", done_today: S.resends }); if (d.run) { S.resends += 1; record("AssistActionRun", "device", { action: "resend_receipt", class: d.class }); } return; }
      if (v === "mute") { S.assistStep = "card"; draw(); return; }
      if (v === "deny") { S.assistStep = "idle"; record("AssistActionDenied", "device", { action: "mute_notification_kind" }); draw(); return; }
      if (v === "confirm") { const d = decide("mute_notification_kind", { role: "owner", confirmed: true }); if (d.run) { S.assistStep = "done"; S.assistDoneAt = Date.now(); record("AssistActionRun", "device", { action: "mute_notification_kind", class: d.class }); } draw(); return; }
      if (v === "undo") { S.assistStep = "idle"; record("AssistActionUndone", "device", { action: "mute_notification_kind", undo: "unmute" }); draw(); return; }
      if (v === "why") { S.overlay = "help"; draw(); return; }
      if (v.startsWith("fix")) { S.overlay = "help"; S.ask = ""; record("AssistFixAsked", "device", { problem: v.slice(4) }); draw(); return; }
      S.overlay = null; record("ShellAction", "device", { action: a }); draw(); return;
    }
    case "closeoverlay": case "closesheet": S.overlay = null; draw(); return;
    case "shell": {
      const map: Record<string, Overlay> = { launcher: "launcher", account: "account", globe: "globe", search: "cmd", help: "help", bell: "bell", sync: "sync", menu: "launcher" };
      if (v === "theme") { S.theme = S.theme === "dark" ? "light" : "dark"; $<HTMLInputElement>("#cDark").checked = S.theme === "dark"; S.overlay = null; draw(); return; }
      if (v === "signout" || v === "signin" || v === "voice") { S.overlay = null; draw(); return; }
      if (v === "side") { act(`side:${S.side === "external" ? "internal" : "external"}`); return; }
      if (v === "view" || v === "why") { S.overlay = "view"; draw(); if (v === "why") $("#whyView")?.focus(); return; }
      S.overlay = S.overlay === map[v] ? null : (map[v] ?? null); S.query = ""; draw();
      if (S.overlay === "cmd") $<HTMLInputElement>("#cmdIn")?.focus();
      return;
    }
    case "side": {
      const next = v === "external" ? "external" : "internal";
      if (next !== S.side) { S.side = next; record("SideSwitched", "device", { side: next, path: screenPath() }); }
      S.overlay = null; draw(); return;
    }
    case "view": {
      const want = v === "auto" ? null : (VIEWS as readonly string[]).includes(v) ? v : null;
      if (!safeToSwitch(S.screen === "payment" ? "payment" : null)) { S.pendingView = want; draw(); return; }   // never in the middle of a payment
      S.override = want; S.pendingView = undefined; S.overlay = null;
      draw(); record("InterfaceChosen", "device", { interface: S.choice?.interface, rule: S.choice?.rule }); return;
    }
    case "nav": S.screen = v === "home" ? "home" : v === "sell" ? "payment" : v === "business" ? "state:empty" : S.screen; S.overlay = null;
      if (S.screen !== "payment" && S.pendingView !== undefined) { S.override = S.pendingView; S.pendingView = undefined; }   // the waiting view starts after the payment step
      draw(); return;
    case "go": S.screen = v === "home" ? "home" : S.screen; S.overlay = null; draw(); return;
    case "place": case "business": case "role": case "region": case "open": case "notice": case "help": case "support": case "assist": case "copy": S.overlay = null; record("ShellAction", "device", { action: a }); draw(); return;
    case "lang": S.lang = pick(Object.keys(PACKS), v, S.lang); $<HTMLSelectElement>("#cLang").value = S.lang; S.overlay = null; draw(); return;
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
  bind("#cSize", (el) => { S.testWidth = pick(["auto", "240", "320", "360", "390", "412", "600", "768", "1024", "1280", "1920", "3840"], el.value, S.testWidth); S.overlay = null; draw(); });
  bind("#cView", (el) => { S.testView = pick(["auto", ...VIEWS], el.value, S.testView); S.overlay = null; draw(); });
  bind("#cLink", (el) => { S.link = pick(["good", "weak", "offline"] as Link[], el.value, S.link); draw(); });
  bind("#cDark", (el) => { S.theme = el.checked ? "dark" : "light"; draw(); });
  bind("#cMode", (el) => { S.mode = pick(["", "lite", "sunlight"] as ("" | "lite" | "sunlight")[], el.value, S.mode); draw(); });
  bind("#cReal", (el) => { S.realUser = el.checked; draw(); });
  const country = $<HTMLSelectElement>("#cCountry");
  country.innerHTML = DATA.packOrder.map((c) => { const p = DATA.packs[c] as CountryPack; return `<option value="${esc(c)}">${esc(p.sample ? t("sample_country") : p.name)}</option>`; }).join("");
  country.addEventListener("change", (e) => { S.country = pick(DATA.packOrder, (e.target as HTMLSelectElement).value, S.country); draw(); });
  const sel = $<HTMLSelectElement>("#cLang");
  sel.insertAdjacentHTML("afterbegin", Object.entries(PACKS).map(([code, p]) => `<option value="${esc(code)}" lang="${esc(code)}" dir="${p.dir}">${esc(p.native)}</option>`).join(""));
  sel.value = "en";
  sel.addEventListener("change", (e) => { S.lang = pick(Object.keys(PACKS).concat(["xx", "xx-rtl"]), (e.target as HTMLSelectElement).value, S.lang); draw(); });
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
    if (el.dataset["filter"] === "regions") { const list = $("#regionList"); if (list) filterRegions(list, el.value); return; }
    if (el.id === "cmdIn") { S.query = plain(el.value); const list = $("#cmdList"); const index = overlay(); const m = /<ul id="cmdList"[^>]*>([\s\S]*?)<\/ul>/.exec(index); if (list && m) list.innerHTML = m[1]!; }
    if (el.id === "asIn") { S.ask = plain(el.value); draw(); const inp = $<HTMLInputElement>("#asIn"); inp.focus(); inp.setSelectionRange(inp.value.length, inp.value.length); return; }
    if (el.id === "usernameIn") { act(`username:${el.value}`); const inp = $<HTMLInputElement>("#usernameIn"); inp.focus(); inp.setSelectionRange(inp.value.length, inp.value.length); }
  });
  $("#display").addEventListener("change", (e) => { const el = e.target as HTMLInputElement; if (el.dataset["act"]?.startsWith("toggle:") || el.dataset["act"] === "ppl:checker") act(el.dataset["act"]); });
  document.addEventListener("keydown", (e) => {
    if (e.key === "/" && !(e.target as HTMLElement).matches("input,select,textarea")) { e.preventDefault(); act("shell:search"); }
    if (e.key === "Escape" && S.overlay) { S.overlay = null; draw(); return; }
    const group = (document.activeElement as HTMLElement | null)?.closest<HTMLElement>(".shell-nav, .lgrid, .choices, .lsides, .mside");
    if (group) arrowNav(e, group, $("#display").dir === "rtl");                   // keyboard, remote and switch access move inside a group
  });
  // Touch and pen (every touch view): swipe from the start edge opens the menu, swipe a sheet down to close it, press and hold a tab for its help
  gestures($("#display"), {
    edgeSwipe: () => { if (!S.overlay) act("shell:launcher"); },
    swipeDown: (el) => { if (S.overlay && el.closest(".overlay")) { S.overlay = null; draw(); } },
    longPress: (el) => { if (el.closest(".navitem")) { S.overlay = "help"; draw(); } },
  }, () => $("#display").dir === "rtl");
  const fit = () => { const w = $("#rig").clientWidth - 8, dev = width(); document.documentElement.style.setProperty("--fit", String(Math.min(1, w / dev))); };
  new ResizeObserver(fit).observe($("#rig")); fit();
  bind("#cSize", () => fit()); bind("#cView", () => fit());
  window.setInterval(() => {
    const now = Date.now();
    const before = S.banners.length;
    S.banners = S.banners.filter((nid) => { const l = lineOf(nid); return !!l && (priorityOf(l.kind) === "critical" || now - l.at < 8000); });
    if (S.banners.some((nid) => { const l = lineOf(nid); return l && !l.acknowledged && priorityOf(l.kind) === "critical" && Math.round((now - l.at) / 1000) % 30 === 0 && now - l.at > 1000; })) feel("critical");   // repeats until "I have seen this" (every 30 s here, 5 minutes in the product)
    if (S.undo.openToasts(now).length || $(".toasts").children.length || before !== S.banners.length || S.waitUntil > now - 1000 || S.assistStep === "done") draw();
  }, 1000);
  $("#urgent").addEventListener("click", () => urgent());
  draw(); drawLog();
}
init();
