/** The LynkOmni shell: the parts every surface is built from (blueprint 41 B, build section 1).
 *  One header grammar, navigation that becomes tabs, rail or sidebar by screen size, the app launcher, the account menu,
 *  language and region, "find or do anything", the help panel, notifications with a digest, every screen state, the
 *  connection chip and sync sheet, deep links from the address map, protected zones, undo for anything, data saver,
 *  continue on any device, the chat "Translated from" note, the username field and charts with a table view.
 *
 *  No DOM and no browser API here, so the same file runs in the emulators, the real web app and the Node tests. Components
 *  render HTML strings; the host binds `data-act` attributes. Every word shown comes through `t(key)` from the surface's
 *  language pack (never typed here), icons through `icon(id)` from the brand module, pictures through the visuals module.
 *  Colours and sizes live only in web/shell/shell.css, built on the design tokens. */
import { NO_BADGE_SCREENS } from "./brand.js";
import { check, suggestions } from "./usernames.js";

export type T = (key: string, vars?: Record<string, string | number>) => string;
export type Icon = (id: string, cls?: string) => string;
export const esc = (s: string): string => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
const fill = (s: string, vars?: Record<string, string | number>): string => vars ? s.replace(/\{(\w+)\}/g, (_, k) => (vars[k] ?? `{${k}}`).toString()) : s;
/** A t() that fills {placeholders} from a flat key -> text map; the surfaces wrap their language packs with it. */
export const translator = (texts: Record<string, string>, fallback: Record<string, string> = {}): T => (k, vars) => fill(texts[k] ?? fallback[k] ?? k, vars);

// ---------------------------------------------------------------- sizes
export type Viewport = "phone" | "tablet" | "computer";
/** Phone under 600 px: bottom tabs. Tablet 600 to 1023 px: side rail. Computer 1024 px and up: sidebar in apps, top navigation on sites. */
export const viewport = (widthPx: number): Viewport => (widthPx < 600 ? "phone" : widthPx < 1024 ? "tablet" : "computer");
export const CONTENT_MAX_PX = 1440;
export const TOUCH_TARGET_PX = 44;

// ---------------------------------------------------------------- header
export interface NavItem { id: string; label: string; icon?: string; href?: string; badge?: number; current?: boolean }
export interface HeaderParts { logo: string; nav: NavItem[]; notifications: number; signedIn: boolean; title?: string; primary?: { label: string; act: string }; surface?: "app" | "website";
  /** BIZZ & DEVICE: which side the screen is on, always in words (the workspace word, or Storefront), never colour alone */
  side?: { label: string; storefront: boolean } }

/** One header grammar everywhere: logo place, main navigation, then search, language and region (globe), help, notifications
 *  (signed in), the app launcher and the account menu. On a phone: logo, search, menu. */
export function header(p: HeaderParts, vp: Viewport, t: T, icon: Icon): string {
  const right = [
    `<button class="hbtn" data-act="shell:search" aria-label="${esc(t("find_or_do"))}">${icon("ui-search")}</button>`,
    vp === "phone" ? "" : `<button class="hbtn" data-act="shell:globe" aria-label="${esc(t("language_region"))}">${icon("ui-globe")}</button>`,
    vp === "phone" ? "" : `<button class="hbtn" data-act="shell:help" aria-label="${esc(t("help"))}">${icon("ui-info")}</button>`,
    p.signedIn ? `<button class="hbtn" data-act="shell:bell" aria-label="${esc(t("notifications_n", { n: p.notifications }))}">${icon("ui-bell")}${p.notifications ? `<span class="badge">${p.notifications > 99 ? "99+" : p.notifications}</span>` : ""}</button>` : "",
    p.signedIn ? `<button class="hbtn" data-act="shell:launcher" aria-label="${esc(t("app_launcher"))}">${icon("ui-grid")}</button>` : "",
    p.signedIn ? `<button class="hbtn avatar" data-act="shell:account" aria-label="${esc(t("account_menu"))}">${icon("ui-user")}</button>`
               : `<a class="hlink" href="/signin" data-act="shell:signin">${esc(t("sign_in"))}</a>${p.primary ? `<button class="primary" data-act="${esc(p.primary.act)}">${esc(p.primary.label)}</button>` : ""}`,
    vp === "phone" ? `<button class="hbtn" data-act="shell:menu" aria-label="${esc(t("menu"))}">${icon("ui-menu")}</button>` : "",
  ].join("");
  // A website carries its navigation in the header on a computer; an app has it in the sidebar instead.
  const nav = vp === "computer" && (p.surface ?? "website") === "website" ? `<nav class="hnav" aria-label="${esc(t("main_navigation"))}">${p.nav.map((n) => `<a class="hnavitem${n.current ? " current" : ""}" href="${esc(n.href ?? "#")}" data-act="nav:${esc(n.id)}"${n.current ? ' aria-current="page"' : ""}>${esc(n.label)}</a>`).join("")}</nav>` : "";
  const side = p.side ? `<button class="side-chip${p.side.storefront ? " storefront" : ""}" data-act="shell:side" data-side="${p.side.storefront ? "external" : "internal"}" aria-label="${esc(t("side_now", { side: p.side.label }))}">${icon(p.side.storefront ? "ui-cart" : "ui-home")}<span>${esc(p.side.label)}</span></button>` : "";
  // on a phone the side gets its own line under the header, so the word is never squeezed or broken
  // and so does the title: a phone header has room for the logo and its buttons only, so a title there would be cut to "A.."
  const ptitle = p.title && vp === "phone" ? `<h1 class="htitle">${esc(p.title)}</h1>` : "";
  const strip = (side || ptitle) && vp === "phone" ? `<div class="side-strip">${ptitle}${side}</div>` : "";
  return `<header class="shell-header" role="banner"><a class="logo-place" href="/" aria-label="LynkOmni">${p.logo}</a>${vp === "phone" ? '<span class="hspace"></span>' : side}${p.title && vp === "tablet" ? `<h1 class="htitle">${esc(p.title)}</h1>` : ""}${nav}<div class="hright">${right}</div></header>${strip}`;
}

/** Navigation by size: bottom tab bar of 4 or 5 on a phone, a rail on a tablet, a sidebar on a computer. */
export function navigation(items: NavItem[], vp: Viewport, t: T, icon: Icon): string {
  const kind = vp === "phone" ? "tabs" : vp === "tablet" ? "rail" : "sidebar";
  const shown = kind === "tabs" ? items.slice(0, 5) : items;
  const li = shown.map((n) => `<a class="navitem${n.current ? " current" : ""}" href="${esc(n.href ?? "#")}" data-act="nav:${esc(n.id)}"${n.current ? ' aria-current="page"' : ""}>${n.icon ? icon(n.icon) : ""}<span class="nlabel">${esc(n.label)}</span>${n.badge ? `<span class="badge">${n.badge}</span>` : ""}</a>`).join("");
  return `<nav class="shell-nav ${kind}" aria-label="${esc(t("main_navigation"))}">${li}</nav>`;
}

// ---------------------------------------------------------------- launcher and account menu
export interface Place { id: string; name: string; icon: string; href: string; state: "available" | "coming_soon"; plain?: string }
/** The grid that lists every LynkOmni place the person can use. A place waiting for its partner shows "Coming to your country soon." instead of disappearing. */
export function launcher(places: Place[], t: T, icon: Icon, sides?: SideChoice): string {
  const top = sides ? `<div class="lsides" role="group" aria-label="${esc(t("switch_side_group"))}">${sideButtons(sides, t, icon)}</div>` : "";
  return `<div class="launcher" role="dialog" aria-label="${esc(t("app_launcher"))}">${top}<ul class="lgrid">${places.map((p) => `<li><a class="lplace${p.state === "coming_soon" ? " soon" : ""}" href="${esc(p.href)}" data-act="place:${esc(p.id)}">${icon(p.icon, "prod")}<span class="nm">${esc(p.name)}</span>${p.plain ? `<span class="pl">${esc(p.plain)}</span>` : ""}${p.state === "coming_soon" ? `<span class="soon-tag">${esc(t("coming_soon"))}</span>` : ""}</a></li>`).join("")}</ul></div>`;
}

export interface Account { name: string; lynkId: string; businesses: { id: string; name: string; current: boolean }[]; role: string; roles: string[]; theme: "light" | "dark" | "lite" | "sunlight"; language: string; region: string;
  /** BIZZ & DEVICE: the two sides (workspace word and Storefront) and the interface this device uses */
  sides?: SideChoice; view?: { name: string };
  /** Extra places this site puts in the account menu (catalog/placements.v1.json account_menu), e.g. My Storefront, Seller support */
  links?: { act: string; label: string; icon: string }[] }
/** The two sides of every service: the workspace (shown with its own word) and the Storefront. One tap between them. */
export interface SideChoice { current: "internal" | "external"; workspaceWord: string; storefrontWord: string }
export function sideButtons(s: SideChoice, t: T, icon: Icon): string {
  const b = (side: "internal" | "external", word: string, ic: string) => `<button class="side-btn${s.current === side ? " current" : ""}" data-act="side:${side}"${s.current === side ? ' aria-current="true"' : ""}>${icon(ic)}<span>${esc(s.current === side ? word : t("switch_side", { side: word }))}</span></button>`;
  return b("internal", s.workspaceWord, "ui-home") + b("external", s.storefrontWord, "ui-cart");
}
/** The LynkID is shown masked with a copy button: never the whole identifier on screen. */
export const maskId = (id: string): string => id.length > 9 ? `${id.slice(0, 6)}…${id.slice(-4)}` : id;
export function accountMenu(a: Account, t: T, icon: Icon): string {
  const biz = a.businesses.length > 1 ? `<li><span class="mlabel">${esc(t("switch_business"))}</span><ul class="sub">${a.businesses.map((b) => `<li><button class="mitem${b.current ? " current" : ""}" data-act="business:${esc(b.id)}"${b.current ? ' aria-current="true"' : ""}>${esc(b.name)}</button></li>`).join("")}</ul></li>` : "";
  const roles = a.roles.length > 1 ? `<li><span class="mlabel">${esc(t("switch_role"))}</span><ul class="sub">${a.roles.map((r) => `<li><button class="mitem${r === a.role ? " current" : ""}" data-act="role:${esc(r)}">${esc(t(`role_${r}`))}</button></li>`).join("")}</ul></li>` : "";
  return `<div class="account-menu" role="dialog" aria-label="${esc(t("account_menu"))}"><div class="who"><span class="avatar big">${icon("ui-user")}</span><div><strong>${esc(a.name)}</strong><div class="lynkid"><code>${esc(maskId(a.lynkId))}</code><button class="copy" data-act="copy:lynkid" aria-label="${esc(t("copy_lynkid"))}">${icon("ui-copy")}</button></div></div></div><ul class="mlist">${a.sides ? `<li class="mside">${sideButtons(a.sides, t, icon)}</li>` : ""}${(a.links ?? []).map((l) => `<li><button class="mitem" data-act="${esc(l.act)}">${icon(l.icon)}<span>${esc(l.label)}</span></button></li>`).join("")}${biz}${roles}${a.view ? `<li><button class="mitem" data-act="shell:view">${icon("ui-settings")}<span>${esc(t("change_view"))}: ${esc(a.view.name)}</span></button></li><li><button class="mitem" data-act="shell:why">${icon("ui-info")}<span>${esc(t("why_this_view"))}</span></button></li>` : ""}<li><button class="mitem" data-act="shell:globe">${icon("ui-globe")}<span>${esc(t("language_region"))}: ${esc(a.language)} · ${esc(a.region)}</span></button></li><li><button class="mitem" data-act="shell:theme">${icon("ui-theme")}<span>${esc(t("theme"))}: ${esc(t(`theme_${a.theme}`))}</span></button></li><li><a class="mitem" href="/security" data-act="go:security">${icon("ui-lock")}<span>${esc(t("security_center"))}</span></a></li><li><button class="mitem" data-act="shell:help">${icon("ui-info")}<span>${esc(t("help"))}</span></button></li><li><button class="mitem danger" data-act="shell:signout">${icon("ui-signout")}<span>${esc(t("sign_out"))}</span></button></li></ul></div>`;
}

/** Change view (DEVICE, 48.17): the interface versions this device can use, "Automatic" first. The person's choice is remembered
 *  for this device and can always be undone; on a selling device only the owner may change it. Why this view? names the rule. */
/** The name of each interface in catalog/devices.v1.json (written out so the words travel only where they are used). */
export const IFACE_NAME: Record<string, string> = { "universal": "iface_universal", "phone.touch": "iface_phone_touch", "phone.keypad": "iface_phone_keypad", "phone.feature": "iface_phone_feature", "phone.text": "iface_phone_text", "tablet.touch": "iface_tablet_touch", "computer.pointer": "iface_computer_pointer", "computer.touch": "iface_computer_touch", "tv.remote": "iface_tv_remote", "watch.touch": "iface_watch_touch", "car.voice": "iface_car_voice", "eink.touch": "iface_eink_touch", "eink.buttons": "iface_eink_buttons", "voice.only": "iface_voice_only" };
/** The sentence for each rule of the decision function (written out so the words travel only where they are used). */
const WHY_VIEW: Record<string, string> = { override: "why_override", registered: "why_registered", reported: "why_reported", safe_default: "why_safe_default" };
export function viewSheet(o: { current: string; rule: "override" | "registered" | "reported" | "safe_default"; options: string[]; ownerOnly: boolean; canChange: boolean }, t: T, icon: Icon): string {
  const name = (id: string) => t(IFACE_NAME[id] ?? "iface_universal");
  const why = `<p class="why" id="whyView">${icon("ui-info")}<span>${esc(t(WHY_VIEW[o.rule] ?? "why_safe_default"))}</span></p>`;
  const lock = o.ownerOnly && !o.canChange ? `<p class="note">${esc(t("view_owner_only"))}</p>` : "";
  const opts = ["auto", ...o.options].map((id) => {
    const on = id === "auto" ? o.rule !== "override" : o.rule === "override" && o.current === id;
    return `<li><button class="choice${on ? " current" : ""}" data-act="view:${esc(id)}"${on ? ' aria-current="true"' : ""}${o.canChange ? "" : " disabled"}>${esc(id === "auto" ? t("view_auto") : name(id))}</button></li>`;
  }).join("");
  return `<div class="view-sheet" role="dialog" aria-label="${esc(t("change_view"))}"><h2>${esc(t("change_view"))}</h2><p class="now">${esc(t("view_now", { name: name(o.current) }))}</p>${why}${lock}<ul class="choices">${opts}</ul></div>`;
}

/** Language and region are always one tap away (the globe), never a buried setting. Presentation only, never data. */
export function globeSheet(languages: { code: string; native: string; dir: "ltr" | "rtl" }[], regions: { code: string; name: string }[], current: { language: string; region: string }, t: T): string {
  const search = regions.length > 12 ? `<input type="search" class="region-search" data-filter="regions" placeholder="${esc(t("search_country"))}" aria-label="${esc(t("search_country"))}" autocomplete="off">` : "";
  return `<div class="globe-sheet" role="dialog" aria-label="${esc(t("language_region"))}"><h2>${esc(t("language"))}</h2><ul class="choices">${languages.map((l) => `<li><button class="choice${l.code === current.language ? " current" : ""}" lang="${esc(l.code)}" dir="${l.dir}" data-act="lang:${esc(l.code)}"${l.code === current.language ? ' aria-current="true"' : ""}>${esc(l.native)}</button></li>`).join("")}</ul><h2>${esc(t("region"))}</h2>${search}<ul class="choices regions" id="regionList">${regions.map((r) => `<li data-name="${esc(r.name.toLowerCase())}"><button class="choice${r.code === current.region ? " current" : ""}" data-act="region:${esc(r.code)}">${esc(r.name)}</button></li>`).join("")}</ul><p class="note">${esc(t("presentation_only"))}</p></div>`;
}
/** A country's name in the person's language, from the browser's own CLDR data (Intl.DisplayNames); the pack's English name when the browser has none. */
export function regionName(code: string, language: string, fallback: string): string {
  try { const n = new Intl.DisplayNames([language], { type: "region" }).of(code); return n && n !== code ? n : fallback; } catch { return fallback; }
}
/** Filters the region list of the globe sheet as the person types (every country is listed, so a search box is needed). */
export function filterRegions(list: Element, query: string): number {
  const q = query.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().trim();
  let shown = 0;
  for (const li of Array.from(list.children) as HTMLElement[]) {
    const name = (li.dataset["name"] ?? "").normalize("NFD").replace(/[\u0300-\u036f]/g, "");
    const hit = !q || name.includes(q);
    li.hidden = !hit; if (hit) shown += 1;
  }
  return shown;
}

// ---------------------------------------------------------------- find or do anything
export interface Entry { id: string; kind: "product" | "customer" | "order" | "report" | "setting" | "help" | "action"; title: string; subtitle?: string; keywords?: string[]; act?: string; href?: string }
/** Ranks entries for a query: a title that starts with the words first, then any word match, then keywords. Actions ("new sale")
 *  rank above records on a short query so the bar does things, not only finds them. Diacritics and case are ignored. */
export function search(index: Entry[], query: string, limit = 8): Entry[] {
  const norm = (s: string) => s.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
  const q = norm(query).trim();
  if (!q) return index.filter((e) => e.kind === "action").slice(0, limit);
  const words = q.split(/\s+/);
  const score = (e: Entry): number => {
    const title = norm(e.title), sub = norm(e.subtitle ?? ""), kw = (e.keywords ?? []).map(norm);
    let s = 0;
    if (title.startsWith(q)) s += 100;
    for (const w of words) {
      if (title.split(/\s+/).some((tw) => tw.startsWith(w))) s += 40;
      else if (title.includes(w)) s += 20;
      else if (sub.includes(w)) s += 10;
      else if (kw.some((k) => k.includes(w))) s += 8;
      else return 0;
    }
    if (e.kind === "action" && words.length <= 2) s += 5;
    return s;
  };
  return index.map((e) => [score(e), e] as const).filter(([s]) => s > 0).sort((a, b) => b[0] - a[0]).slice(0, limit).map(([, e]) => e);
}
export function commandBar(query: string, results: Entry[], t: T, icon: Icon, assist = true): string {
  const kindIcon: Record<Entry["kind"], string> = { product: "ui-cart", customer: "ui-user", order: "ui-receipt", report: "ui-chart", setting: "ui-settings", help: "ui-info", action: "ui-bolt" };
  const li = results.map((r, i) => `<li role="option" id="cmd-${i}"><button class="result" data-act="${esc(r.act ?? (r.href ? `go:${r.href}` : `open:${r.id}`))}">${icon(kindIcon[r.kind])}<span class="rt">${esc(r.title)}</span>${r.subtitle ? `<span class="rs">${esc(r.subtitle)}</span>` : ""}<span class="rk">${esc(t(`kind_${r.kind}`))}</span></button></li>`).join("");
  return `<div class="command-bar" role="dialog" aria-label="${esc(t("find_or_do"))}"><div class="cmd-input">${icon("ui-search")}<input id="cmdIn" type="search" value="${esc(query)}" placeholder="${esc(t("find_or_do_hint"))}" aria-label="${esc(t("find_or_do"))}" role="combobox" aria-expanded="true" aria-controls="cmdList" autocomplete="off"><button class="hbtn" data-act="shell:voice" aria-label="${esc(t("voice_input"))}">${icon("ui-mic")}</button></div><ul id="cmdList" class="results" role="listbox">${li || `<li class="none">${esc(t("no_results"))}</li>`}</ul>${assist ? `<button class="assist-hand" data-act="assist:ask">${icon("product-assist")}<span>${esc(t("ask_assist", { q: query }))}</span><span class="suggested">${esc(t("suggested_by_assist"))}</span></button>` : ""}<p class="kbd">${esc(t("shortcut_hint"))}</p></div>`;
}

// ---------------------------------------------------------------- help panel
export interface Article { id: string; title: string; href: string }
/** A ? on every screen: matching articles, LynkAssist, live support chat, then a case. Self-service never blocks reaching a person. */
export function helpPanel(screen: string, articles: Article[], t: T, icon: Icon): string {
  return `<aside class="help-panel" role="dialog" aria-label="${esc(t("help"))}"><h2>${esc(t("help_for_screen", { screen }))}</h2><ul class="articles">${articles.map((a) => `<li><a href="${esc(a.href)}" data-act="help:article:${esc(a.id)}">${icon("ui-doc")}<span>${esc(a.title)}</span></a></li>`).join("") || `<li class="none">${esc(t("no_articles"))}</li>`}</ul><div class="help-steps"><button class="secondary" data-act="assist:ask">${icon("product-assist")}<span>${esc(t("ask_assist_short"))}</span></button><button class="secondary" data-act="support:chat">${icon("product-chat")}<span>${esc(t("chat_with_person"))}</span></button><button class="secondary" data-act="support:case">${icon("ui-receipt")}<span>${esc(t("open_case"))}</span></button></div><p class="note">${esc(t("never_blocks_person"))}</p></aside>`;
}

// ---------------------------------------------------------------- notifications and the digest
export type Urgency = "security" | "transactional" | "low";
export interface Notice { id: string; at: number; urgency: Urgency; title: string; body?: string; record?: string; read?: boolean; href?: string }
export interface QuietHours { startHour: number; endHour: number }   // in the person's own time zone, as hours of the day
export const inQuietHours = (hour: number, q: QuietHours | null): boolean => !!q && (q.startHour <= q.endHour ? hour >= q.startHour && hour < q.endHour : hour >= q.startHour || hour < q.endHour);
/** Sign-in codes and security alerts always pass. Transactional notices pass outside quiet hours. Low-urgency notices are
 *  grouped into one digest, delivered at the next digest time. Nothing is sent twice (ids are kept). */
export function deliverNow(notices: Notice[], hour: number, quiet: QuietHours | null, seen: Set<string>): { now: Notice[]; digest: Notice[]; held: Notice[] } {
  const now: Notice[] = [], digest: Notice[] = [], held: Notice[] = [];
  for (const n of notices) {
    if (seen.has(n.id)) continue;
    seen.add(n.id);
    if (n.urgency === "security") now.push(n);
    else if (n.urgency === "transactional") (inQuietHours(hour, quiet) ? held : now).push(n);
    else digest.push(n);
  }
  return { now, digest, held };
}
export function notificationsPanel(list: Notice[], t: T, icon: Icon): string {
  const li = list.map((n) => `<li class="notice${n.read ? "" : " unread"}"><a href="${esc(n.href ?? "#")}" data-act="notice:${esc(n.id)}">${icon(n.urgency === "security" ? "ui-lock" : n.urgency === "transactional" ? "ui-receipt" : "ui-bell")}<span class="nt">${esc(n.title)}</span>${n.body ? `<span class="nb">${esc(n.body)}</span>` : ""}${n.record ? `<code class="rec">${esc(n.record)}</code>` : ""}</a></li>`).join("");
  return `<div class="notifications" role="dialog" aria-label="${esc(t("notifications"))}"><h2>${esc(t("notifications"))}</h2><ul class="nlist">${li || `<li class="none">${esc(t("no_notifications"))}</li>`}</ul><a class="mitem" href="/notifications" data-act="go:notifications">${icon("ui-settings")}<span>${esc(t("notification_settings"))}</span></a></div>`;
}

// ---------------------------------------------------------------- every state is designed
export type StateKind = "loading" | "empty" | "offline" | "error" | "not_found" | "no_results" | "permission" | "maintenance" | "sync_pending" | "coming_soon" | "success";
/** The picture each state uses (visuals module ids). Loading has no picture: a skeleton. Empty reuses "no results" in the muted set. */
export const STATE_PICTURE: Record<StateKind, string | null> = { loading: null, empty: "state-no-results", offline: "state-offline", error: "state-error", not_found: "state-not-found", no_results: "state-no-results", permission: "state-permission", maintenance: "state-maintenance", sync_pending: "state-sync-pending", coming_soon: "state-coming-soon", success: "state-success" };
export interface Pic { svg: string; alt: string }
/** Every state has a picture, a title, a line and a next step: no dead ends. */
export function state(kind: StateKind, t: T, pic: Pic | null, next: { label: string; act: string } | null, vars?: Record<string, string | number>): string {
  if (kind === "loading") return `<div class="state loading" role="status" aria-live="polite" aria-label="${esc(t("loading"))}"><div class="skel title"></div><div class="skel line"></div><div class="skel line short"></div><div class="skel card"></div></div>`;
  const picture = pic ? `<span class="pic" role="img" aria-label="${esc(pic.alt)}">${pic.svg}</span>` : "";
  const live = kind === "error" || kind === "offline" ? ' role="alert"' : ' role="status"';
  return `<div class="state ${kind.replace("_", "-")}"${live}>${picture}<h2>${esc(t(`state_${kind}_title`, vars))}</h2><p>${esc(t(`state_${kind}_body`, vars))}</p>${next ? `<button class="primary" data-act="${esc(next.act)}">${esc(next.label)}</button>` : ""}</div>`;
}
/** "Coming to your country soon." with Notify me: a service waiting for its partner keeps its place and never says "not available". */
export function comingSoon(service: string, t: T, pic: Pic | null, notified: boolean): string {
  return `<div class="state coming-soon" role="status">${pic ? `<span class="pic" role="img" aria-label="${esc(pic.alt)}">${pic.svg}</span>` : ""}<h2>${esc(service)}</h2><p>${esc(t("coming_soon"))}</p>${notified ? `<p class="note">${esc(t("notify_done"))}</p>` : `<button class="primary" data-act="notify:${esc(service)}">${esc(t("notify_me"))}</button>`}</div>`;
}

// ---------------------------------------------------------------- connection chip and sync sheet
export type Link = "good" | "weak" | "offline";
export interface SyncInfo { link: Link; pending: number; lastSync: number | null; dataSaver: boolean; forcedOffline: boolean }
export function connectionChip(s: SyncInfo, t: T, icon: Icon): string {
  const word = s.link === "offline" || s.forcedOffline ? t("offline") : s.link === "weak" ? t("weak_link") : t("online");
  return `<button class="netchip ${s.link}${s.forcedOffline ? " forced" : ""}" data-act="shell:sync" aria-label="${esc(word)}${s.pending ? `, ${esc(t("waiting_send", { n: s.pending }))}` : ""}">${icon(s.link === "offline" || s.forcedOffline ? "ui-offline" : "ui-sync")}<span>${esc(word)}</span>${s.pending ? `<span class="badge">${s.pending}</span>` : ""}</button>`;
}
export function syncSheet(s: SyncInfo, t: T, icon: Icon, clock: (ms: number) => string): string {
  return `<div class="sheet sync" role="dialog" aria-label="${esc(t("sync"))}"><h2>${esc(t("sync"))}</h2><dl><dt>${esc(t("waiting_send_label"))}</dt><dd>${s.pending ? esc(t("waiting_send", { n: s.pending })) : esc(t("all_sent"))}</dd><dt>${esc(t("last_sync"))}</dt><dd>${s.lastSync ? esc(clock(s.lastSync)) : esc(t("not_yet"))}</dd></dl><p class="note">${esc(s.link === "weak" ? t("weak_note") : t("needs_net"))}</p><label class="switch"><input type="checkbox" data-act="toggle:datasaver"${s.dataSaver ? " checked" : ""}><span>${esc(t("data_saver"))}</span></label><label class="switch"><input type="checkbox" data-act="toggle:forced"${s.forcedOffline ? " checked" : ""}><span>${esc(t("stay_offline"))}</span></label><button class="primary" data-act="sync:now"${s.link === "offline" || s.forcedOffline ? " disabled" : ""}>${icon("ui-sync")}<span>${esc(t("sync_now"))}</span></button><button class="secondary" data-act="closesheet">${esc(t("close"))}</button></div>`;
}
/** Data saver on a weak link (automation, auto with undo): defer pictures and non-urgent sync; sales always go first. */
export function dataSaverPlan(link: Link, saver: boolean): { pictures: boolean; syncPriorityOnly: boolean; chatMedia: boolean } {
  const on = saver || link === "weak";
  return { pictures: !on, syncPriorityOnly: on, chatMedia: !on };
}

// ---------------------------------------------------------------- deep links
export interface AddressMap { hosts: { host: string }[]; website_paths: string[]; app_paths: string[]; account_paths: string[]; pay_paths: string[]; shop_paths: string[]; staff_paths: string[]; redirects: Record<string, string> }
export interface Route { host: string; surface: "website" | "app" | "account" | "pay" | "shop" | "staff" | "other"; path: string; params: Record<string, string>; redirectedFrom?: string }
const HOST_SURFACE: Record<string, Route["surface"]> = { "lynkomni.com": "website", "app.lynkomni.com": "app", "account.lynkomni.com": "account", "pay.lynkomni.com": "pay", "shop.lynkomni.com": "shop", "staff.lynkomni.com": "staff" };
/** Every screen has its own address: a link in chat, email, SMS or a QR opens the exact screen. Old addresses redirect forever.
 *  Returns null for an address outside the map (the not-found state, with search and help). */
export function route(map: AddressMap, url: string): Route | null {
  let u: URL;
  try { u = new URL(url); } catch { return null; }
  const host = u.hostname.toLowerCase();
  if (!map.hosts.some((h) => h.host === host)) return null;
  const surface = HOST_SURFACE[host] ?? "other";
  let path = u.pathname.replace(/\/+$/, "") || "/";
  let redirectedFrom: string | undefined;
  if (surface === "website") {
    path = path.replace(/^\/[a-z]{2,3}(-[A-Za-z]{2,4})?(?=\/|$)/, "") || "/";      // /fr/... carries the language only
    if (map.redirects[path]) { redirectedFrom = path; path = map.redirects[path]!; }
  }
  const table = surface === "website" ? map.website_paths : surface === "app" ? map.app_paths : surface === "account" ? map.account_paths : surface === "pay" ? map.pay_paths : surface === "shop" ? map.shop_paths : surface === "staff" ? map.staff_paths : [];
  const params: Record<string, string> = {};
  const match = (pattern: string): boolean => {
    const re = new RegExp("^" + pattern.replace(/\{(\w+)\}/g, "(?<$1>[A-Za-z0-9._-]+)") + "$");
    const m = re.exec(path);
    if (!m) return false;
    Object.assign(params, m.groups ?? {});
    return true;
  };
  if (surface === "other" || table.some(match) || path === "/") return { host, surface, path, params, ...(redirectedFrom ? { redirectedFrom } : {}) };
  // a record under a registered app path: /invoicing/invoices/LOINV-1234-5678-9015 or ?view=overdue
  // a record (or /new) under a registered path, through its plural list: /invoicing/invoices/LOINV-... (address rules, section 42 E)
  const parent = table.filter((p) => !p.includes("{") && path.startsWith(p + "/")).sort((a, b) => b.length - a.length)[0];
  if (!parent) return null;
  const rest = path.slice(parent.length + 1);
  const id = /^(?:[a-z-]+\/)?(LO[A-Z]{2,4}-\d{4}-\d{4}-\d{4}|new)$/.exec(rest);
  if (id) return { host, surface, path, params: { under: parent, record: id[1]! } };
  if (/^[a-z0-9/-]+$/.test(rest)) return { host, surface, path, params: { under: parent } };
  return null;
}

/** Protected zones: payment, refund, void, cash count, fiscal and private chat screens never show ads, promotions or "Powered by LynkOmni". */
export const protectedZone = (screen: string): boolean => NO_BADGE_SCREENS.includes(screen);

// ---------------------------------------------------------------- undo for anything
export interface UndoItem { id: string; label: string; at: number; until: number; undo: () => void; money: boolean }
/** Anything done can be undone within 30 seconds from the toast, and later from the history. A money action is never
 *  silently reversed: it is voided with a reason, so it is shown as an audited void instead of a plain undo. */
export class Undo {
  readonly items: UndoItem[] = [];
  constructor(private readonly windowMs = 30_000) {}
  push(id: string, label: string, now: number, undo: () => void, money = false): UndoItem {
    const it = { id, label, at: now, until: now + this.windowMs, undo, money };
    this.items.unshift(it);
    return it;
  }
  openToasts(now: number): UndoItem[] { return this.items.filter((i) => i.until > now); }
  undo(id: string, now: number, fromHistory = false): "undone" | "voided" | "expired" | "unknown" {
    const it = this.items.find((i) => i.id === id);
    if (!it) return "unknown";
    if (!fromHistory && it.until <= now) return "expired";
    it.undo();
    this.items.splice(this.items.indexOf(it), 1);
    return it.money ? "voided" : "undone";
  }
}
export function undoToast(it: UndoItem, now: number, t: T, icon: Icon): string {
  const left = Math.max(0, Math.ceil((it.until - now) / 1000));
  return `<div class="toast undo" role="status" aria-live="polite"><span>${esc(it.label)}</span><button class="link" data-act="undo:${esc(it.id)}">${icon("ui-undo")}<span>${esc(it.money ? t("void_with_reason") : t("undo"))}</span></button><span class="left" aria-hidden="true">${left}s</span></div>`;
}

// ---------------------------------------------------------------- continue on any device
export interface Handoff { surface: string; screen: string; record?: string; draft?: Record<string, string>; at: number; business: string }
/** What follows a person from one device to the next: where they were and an unsent draft. Never a credential, a session, a
 *  card detail or anything under a protected zone. Drafts die after a day. */
export function handoff(h: Handoff, now: number): Handoff | null {
  if (now - h.at > 86_400_000) return null;
  if (protectedZone(h.screen)) return { ...h, screen: "home", record: undefined, draft: undefined } as Handoff;
  const draft = h.draft ? Object.fromEntries(Object.entries(h.draft).filter(([k]) => !/pin|password|code|card|cvv|otp|token|secret/i.test(k))) : undefined;
  return { ...h, draft };
}

// ---------------------------------------------------------------- chat in two languages
export interface ChatLang { reader: string; writer: string; writerName: string; showOriginal: boolean }
export const needsTranslation = (c: ChatLang): boolean => c.reader !== c.writer;
/** The banner at the top of a chat whose two people write in different languages, with the switch to read in the writer's language and back. */
export function translationBanner(c: ChatLang, langName: (code: string) => string, t: T): string {
  if (!needsTranslation(c)) return "";
  return c.showOriginal
    ? `<div class="chat-lang" role="status"><span>${esc(t("reading_in", { lang: langName(c.writer) }))}</span><button class="link" data-act="chat:lang:translated">${esc(t("back_to", { lang: langName(c.reader) }))}</button></div>`
    : `<div class="chat-lang" role="status"><span>${esc(t("writes_in", { name: c.writerName, from: langName(c.writer), to: langName(c.reader) }))}</span><button class="link" data-act="chat:lang:original">${esc(t("read_in", { lang: langName(c.writer) }))}</button></div>`;
}
export interface ChatMessage { id: string; text: string; translated?: string; language: string; failed?: boolean; pendingTranslation?: boolean }
/** Under each message: "Translated from Arabic · Show original". Same language: nothing. Refused: the original with a note. Offline: the original, "will translate when back online". */
export function messageNote(m: ChatMessage, c: ChatLang, langName: (code: string) => string, t: T): string {
  if (!needsTranslation(c) || m.language === c.reader) return "";
  if (m.failed) return `<span class="mnote">${esc(t("could_not_translate"))}</span>`;
  if (m.pendingTranslation || !m.translated) return `<span class="mnote">${esc(t("will_translate_online"))}</span>`;
  if (c.showOriginal) return "";
  return `<span class="mnote">${esc(t("translated_from", { lang: langName(m.language) }))} · <button class="link" data-act="chat:original:${esc(m.id)}">${esc(t("show_original"))}</button></span>`;
}
export const messageText = (m: ChatMessage, c: ChatLang): string => (!needsTranslation(c) || c.showOriginal || !m.translated || m.failed ? m.text : m.translated);

// ---------------------------------------------------------------- username field
export type UsernameStatus = "available" | "taken" | "reserved" | "checking" | null;
/** The field shows "available" or "taken" as you type and suggests free ones; the rule is the shared one (ts/src/usernames.ts). */
export function usernameField(value: string, cloud: UsernameStatus, taken: (u: string) => boolean, t: T, icon: Icon): string {
  const c = check(value);
  let msg = "", tone = "neutral", ok = false;
  if (!value) { msg = t("username_hint"); }
  else if (!c.ok) { msg = t(`username_${c.reason}`); tone = c.reason === "held_for_review" ? "warning" : "danger"; }
  else if (cloud === "checking") { msg = t("username_checking"); }
  else if (cloud === "taken" || cloud === "reserved") { msg = t("username_taken"); tone = "danger"; }
  else { msg = t("username_available"); tone = "success"; ok = true; }
  const sugg = value && !ok && cloud !== "checking" ? suggestions(value, taken) : [];
  return `<div class="field username"><label for="usernameIn">${esc(t("username"))}</label><div class="uinput"><span class="at" aria-hidden="true">@</span><input id="usernameIn" type="text" value="${esc(value)}" autocapitalize="none" autocomplete="off" spellcheck="false" maxlength="30" inputmode="latin" aria-describedby="usernameMsg" aria-invalid="${tone === "danger"}">${ok ? icon("ui-check", "ic ok") : ""}</div><p id="usernameMsg" class="fmsg ${tone}" aria-live="polite">${esc(msg)}</p>${sugg.length ? `<p class="sugg">${esc(t("username_try"))} ${sugg.map((s) => `<button class="chipbtn" data-act="username:${esc(s)}">@${esc(s)}</button>`).join(" ")}</p>` : ""}<p class="note">${esc(t("username_rule"))}</p></div>`;
}

// ---------------------------------------------------------------- charts with a table view and a one-line summary
export interface Series { name: string; values: number[] }
export interface ChartSpec { title: string; labels: string[]; series: Series[]; kind: "bar" | "line"; unit?: string; format?: (n: number) => string; assumption?: boolean }
/** One plain sentence about the data, computed, never invented: the top point and the change from first to last. */
export function chartSummary(spec: ChartSpec, t: T): string {
  const s = spec.series[0];
  if (!s || !s.values.length) return t("chart_no_data");
  const fmt = spec.format ?? ((n: number) => String(n));
  const max = Math.max(...s.values), i = s.values.indexOf(max);
  const first = s.values[0] ?? 0, last = s.values[s.values.length - 1] ?? 0;
  const change = first === 0 ? null : Math.round(((last - first) / Math.abs(first)) * 100);
  const trend = change === null ? "" : change > 0 ? t("chart_up", { pct: change }) : change < 0 ? t("chart_down", { pct: -change }) : t("chart_flat");
  return `${t("chart_peak", { label: spec.labels[i] ?? "", value: fmt(max) })}${trend ? ` ${trend}` : ""}`;
}
export function chart(spec: ChartSpec, view: "chart" | "table", t: T, id = "chart"): string {
  const fmt = spec.format ?? ((n: number) => String(n));
  const summary = chartSummary(spec, t);
  const toggle = `<div class="chart-head"><h3 id="${id}-title">${esc(spec.title)}${spec.assumption ? ` <span class="assumption">${esc(t("assumption"))}</span>` : ""}</h3><div class="seg" role="group" aria-label="${esc(t("chart_view"))}"><button class="segbtn${view === "chart" ? " on" : ""}" data-act="chart:${id}:chart" aria-pressed="${view === "chart"}">${esc(t("view_chart"))}</button><button class="segbtn${view === "table" ? " on" : ""}" data-act="chart:${id}:table" aria-pressed="${view === "table"}">${esc(t("view_table"))}</button></div></div>`;
  const table = `<table class="chart-table"><caption class="sr">${esc(spec.title)}</caption><thead><tr><th scope="col">${esc(t("period"))}</th>${spec.series.map((s) => `<th scope="col">${esc(s.name)}${spec.unit ? ` (${esc(spec.unit)})` : ""}</th>`).join("")}</tr></thead><tbody>${spec.labels.map((l, i) => `<tr><th scope="row">${esc(l)}</th>${spec.series.map((s) => `<td>${esc(fmt(s.values[i] ?? 0))}</td>`).join("")}</tr>`).join("")}</tbody></table>`;
  if (view === "table") return `<figure class="chart" aria-labelledby="${id}-title">${toggle}${table}<figcaption class="summary">${esc(summary)}</figcaption></figure>`;
  const W = 320, H = 140, pad = 8, all = spec.series.flatMap((s) => s.values), max = Math.max(1, ...all), n = spec.labels.length;
  const x = (i: number) => pad + (i + 0.5) * ((W - 2 * pad) / Math.max(1, n)), y = (v: number) => H - pad - (v / max) * (H - 2 * pad);
  const marks = spec.series.map((s, si) => spec.kind === "bar"
    ? s.values.map((v, i) => `<rect class="s${si}" x="${(x(i) - (W - 2 * pad) / n / 2 + 2 + si * ((W - 2 * pad) / n - 4) / spec.series.length).toFixed(1)}" y="${y(v).toFixed(1)}" width="${(((W - 2 * pad) / n - 4) / spec.series.length).toFixed(1)}" height="${(H - pad - y(v)).toFixed(1)}" rx="2"><title>${esc(spec.labels[i] ?? "")}: ${esc(fmt(v))}</title></rect>`).join("")
    : `<polyline class="s${si}" fill="none" stroke-width="2" points="${s.values.map((v, i) => `${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(" ")}"/>` + s.values.map((v, i) => `<circle class="s${si}" cx="${x(i).toFixed(1)}" cy="${y(v).toFixed(1)}" r="3"><title>${esc(spec.labels[i] ?? "")}: ${esc(fmt(v))}</title></circle>`).join("")).join("");
  const svg = `<svg class="chart-svg" viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(summary)}"><line class="axis" x1="${pad}" y1="${H - pad}" x2="${W - pad}" y2="${H - pad}"/>${marks}</svg><ul class="xlabels" aria-hidden="true">${spec.labels.map((l) => `<li>${esc(l)}</li>`).join("")}</ul>${spec.series.length > 1 ? `<ul class="legend">${spec.series.map((s, i) => `<li><i class="sw s${i}"></i>${esc(s.name)}</li>`).join("")}</ul>` : ""}`;
  return `<figure class="chart" aria-labelledby="${id}-title">${toggle}${svg}<figcaption class="summary">${esc(summary)}</figcaption><details class="sr-table"><summary>${esc(t("view_table"))}</summary>${table}</details></figure>`;
}

// ---------------------------------------------------------------- smart defaults (automation, auto with undo)
export interface Defaults { language: string; region: string; currency: string; timeZone: string; businessType: string }
/** First-run defaults from the country pack and the device, each shown on the confirmation card and changeable with one tap. */
export function smartDefaults(pack: { code: string; currency: string; tz: string; locale: string; languages: string[] }, deviceLanguage: string | null, businessType = "shop"): Defaults {
  const lang = deviceLanguage && pack.languages.includes(deviceLanguage.split("-")[0] ?? "") ? deviceLanguage.split("-")[0]! : pack.locale;
  return { language: lang, region: pack.code, currency: pack.currency, timeZone: pack.tz, businessType };
}
