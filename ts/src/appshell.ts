/** The app shell's navigation parts (INTERFACE UPDATE, master blueprint 73.2 to 73.5; section 4 step B2). Every part here is
 *  drawn from the navigation register (ts/src/navigation.ts, catalog/navigation.v1.json) and the layout for the screen's shape
 *  (ts/src/interfaces.ts layoutFor), never from a list a screen keeps for itself:
 *    - the phone bottom bar (five tabs with words, four on a small phone, none on a focus screen),
 *    - the side rail on a tablet or a sideways phone, and the two-level side bar on a computer
 *      (first column: Home, Inbox, Track, pins, All services; at the bottom Emulators, Automations, Settings, Help),
 *    - the focus header (only Back or Cancel and the connection chip in a payment, cash count, void, signature or ballot),
 *    - quick create (+) by role, and the launcher in the eight groups with "My services" first.
 *  No DOM here: parts return HTML strings and the host binds data-act. Words come from web/navigation (prefix nv_) through the
 *  host's t(); a host may pass its own word for a tab (a business type's own tab names). */
import type { NavRegister } from "./navigation.js";
import { bottomBar, isFocus, quickCreate, serviceMenu } from "./navigation.js";
import type { Layout } from "./interfaces.js";

export type T = (key: string, vars?: Record<string, string | number>) => string;
export type Icon = (id: string, cls?: string) => string;
const ashEsc = (s: string): string => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");

/** Icons for the shell's own places; a host passes the icon of a business tab it names itself. */
export const SHELL_ICON: Record<string, string> = {
  home: "ui-home", inbox: "ui-bell", track: "ui-sync", pins: "ui-grid", all_services: "ui-grid", emulators: "ui-grid", automations: "ui-sync",
  settings: "ui-settings", help: "ui-info", scan: "ui-qr", chats: "product-chat", me: "ui-user",
};

export interface BarLook {
  t: T; icon: Icon;
  /** the word for a tab: a business type's own tab names (tab_<id>), otherwise the shell word nv_<id> */
  label?: (tab: string) => string;
  /** the icon id for a tab the host names itself */
  tabIcon?: (tab: string) => string | undefined;
  /** a small count beside a tab (only for things that need the person) */
  badge?: (tab: string) => number;
}

/** The same rule as navigation.bottomBar for a list the workspace gives: a small phone drops the register's chosen place. */
const ashFit = (reg: NavRegister, tabs: readonly string[], room: number): string[] => {
  const bar = [...tabs];
  if (room < bar.length) bar.splice(reg.bottom_bar.small_phone_drops, 1);
  return bar.slice(0, reg.bottom_bar.max_tabs);
};
const ashWord = (look: BarLook, id: string): string => look.label?.(id) ?? look.t(`nv_${id}`);
const ashIcon = (look: BarLook, id: string): string => look.icon(look.tabIcon?.(id) ?? SHELL_ICON[id] ?? "ui-grid");
const ashBadge = (look: BarLook, id: string): string => { const n = look.badge?.(id) ?? 0; return n ? `<span class="dot">${n > 99 ? "99+" : n}</span>` : ""; };
const ashTab = (look: BarLook, id: string, current: string, act: string): string =>
  `<button data-act="${ashEsc(act)}:${ashEsc(id)}" data-tab="${ashEsc(id)}"${id === current ? ' aria-current="page"' : ""}>${ashIcon(look, id)}<span>${ashEsc(ashWord(look, id))}</span>${ashBadge(look, id)}</button>`;

/** The bottom bar or the side rail, by the layout of the screen's shape: tabs on a phone held upright (four on a small phone),
 *  the same tabs as a side rail when the phone is turned sideways or on a tablet. Nothing on a focus screen. Words always shown. */
export function tabsHtml(reg: NavRegister, look: BarLook, o: { kind: string; layout: Layout; screen: string; current: string; chosen?: Record<number, string>; act?: string;
  /** a workspace's own tabs (a person's or an organisation's office, catalog/workspaces.v1.json) in place of the business type's */
  tabs?: readonly string[] }): string {
  if (isFocus(reg, o.screen)) return "";
  const rail = o.layout.nav === "side_rail" || o.layout.nav === "rail" || o.layout.nav === "two_level";
  const room = rail ? reg.bottom_bar.max_tabs : (o.layout.tabs || reg.bottom_bar.max_tabs);
  const tabs = o.tabs ? ashFit(reg, o.tabs, room) : bottomBar(reg, o.kind, room, o.screen, o.chosen ?? {});
  const cls = rail ? "rail ash-rail" : "tabbar ash-bottom";
  return `<nav class="${cls}" data-count="${tabs.length}" aria-label="LynkOmni">${tabs.map((id) => ashTab(look, id, o.current, o.act ?? "tab")).join("")}</nav>`;
}

/** The first column of the two-level side bar on a computer: Home, Inbox, Track, the person's pins and All services; at the
 *  bottom Emulators, Automations, Settings and Help (Settings and Help can never be hidden). */
export function firstColumnHtml(reg: NavRegister, look: BarLook, o: { current: string; pins?: { id: string; label: string; icon: string }[]; hidden?: readonly string[]; act?: string }): string {
  const hidden = new Set((o.hidden ?? []).filter((h) => !reg.rail.never_hidden.includes(h)));
  const act = o.act ?? "nav";
  const one = (id: string): string => id === "pins"
    ? (o.pins ?? []).map((p) => `<button data-act="${ashEsc(act)}:${ashEsc(p.id)}"${p.id === o.current ? ' aria-current="page"' : ""}>${look.icon(p.icon)}<span>${ashEsc(p.label)}</span></button>`).join("")
    : hidden.has(id) ? "" : ashTab(look, id, o.current, act);
  return `<nav class="ash-first" aria-label="LynkOmni"><div class="ash-top">${reg.rail.top.map(one).join("")}</div><div class="ash-bottomgroup">${reg.rail.bottom.map(one).join("")}</div></nav>`;
}

/** The second column: the open service's menu in the fixed order (Overview, its lists, Reports, Automations, Emulators,
 *  Settings) and, on the Storefront side, its Storefront items. title(screen) gives each entry's own word. */
export function serviceMenuHtml(reg: NavRegister, look: BarLook, o: { service: string; current: string; title: (screen: string) => string; side?: "internal" | "external"; act?: string }): string {
  const items = serviceMenu(reg, o.service, o.side ?? "internal");
  if (!items.length) return "";
  const act = o.act ?? "hub";
  return `<nav class="ash-menu" aria-label="${ashEsc(look.t("nv_overview"))}">${items.map(([slot, s]) => `<button data-act="${ashEsc(act)}:${ashEsc(s)}" data-slot="${ashEsc(slot)}"${s === o.current ? ' aria-current="page"' : ""}><span>${ashEsc(o.title(s))}</span></button>`).join("")}</nav>`;
}

/** Quick create (+): what the role starts most, from the register; an item for a section not yet built is left out. */
export function quickCreateHtml(reg: NavRegister, look: BarLook, o: { role: string; built?: readonly string[] | null; act?: string; close: string }): string {
  const items = quickCreate(reg, o.role, o.built ?? null);
  if (!items.length) return "";
  const act = o.act ?? "qc";
  return `<div class="scrim" data-act="${ashEsc(o.close)}"><div class="sheet ash-qc" role="dialog" aria-modal="true" aria-label="${ashEsc(look.t("nv_quick_create"))}" data-stop="1"><h2>${ashEsc(look.t("nv_quick_create"))}</h2>
    <ul class="list card">${items.map((id) => `<li><button class="rowbtn" data-act="${ashEsc(act)}:${ashEsc(id)}" data-item="${ashEsc(id)}">${look.icon("ui-plus", "prod")}<span class="main"><span class="nm">${ashEsc(look.t(`nv_${id}`))}</span></span></button></li>`).join("")}</ul>
    <button class="ghost" data-act="${ashEsc(o.close)}">${ashEsc(look.t("nv_back"))}</button></div></div>`;
}

/** The + button in the app header (hidden on a focus screen and when the role has nothing to create). */
export function quickCreateButton(reg: NavRegister, look: BarLook, o: { role: string; screen: string; built?: readonly string[] | null; act: string }): string {
  if (isFocus(reg, o.screen) || !quickCreate(reg, o.role, o.built ?? null).length) return "";
  return `<button class="iconbtn ash-plus" data-act="${ashEsc(o.act)}" aria-label="${ashEsc(look.t("nv_quick_create"))}">${look.icon("ui-plus")}</button>`;
}

/** The launcher: "My services" first, then the eight groups, each family once, with its own name and plain word. */
export function launcherGroupsHtml(reg: NavRegister, look: BarLook, o: { mine: readonly string[]; name: (family: string) => string; plain?: (family: string) => string; productIcon: (family: string) => string; act?: string; families?: readonly string[] }): string {
  const act = o.act ?? "place";
  const all = new Set(o.families ?? reg.groups.flatMap((g) => g.families));
  const tile = (f: string): string => `<li><button class="lplace" data-act="${ashEsc(act)}:${ashEsc(f)}">${look.icon(o.productIcon(f), "prod")}<span class="nm">${ashEsc(o.name(f))}</span>${o.plain ? `<span class="pl">${ashEsc(o.plain(f))}</span>` : ""}</button></li>`;
  const mine = o.mine.filter((f) => all.has(f));
  const head = mine.length ? `<section class="ash-group" data-group="mine"><h3>${ashEsc(look.t("nv_my_services"))}</h3><ul class="lgrid">${mine.map(tile).join("")}</ul></section>` : "";
  return `<div class="ash-launcher">${head}${reg.groups.map((g) => {
    const fams = g.families.filter((f) => all.has(f) && !mine.includes(f));
    return fams.length ? `<section class="ash-group" data-group="${ashEsc(g.id)}"><h3>${ashEsc(look.t(g.label_key))}</h3><ul class="lgrid">${fams.map(tile).join("")}</ul></section>` : "";
  }).join("")}</div>`;
}
