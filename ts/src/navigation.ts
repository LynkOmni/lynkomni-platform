/** Every menu in LynkOmni (INTERFACE UPDATE, master blueprint 73). Port of core/navigation.py; contract/vectors/navigation.v1.json
 *  proves both give the same groups, headers, bottom bars, quick-create lists, service menus and taps from Home. The register is
 *  carried offline in ts/src/navigation.generated.ts (python3 tools/navigation_vectors.py). No screen builds its own menu. */
export interface QuickItem { id: string; family: string; opens?: string; planned_section?: string; roles: readonly string[] }
export interface ServiceMenu { service: string; family: string | null; overview: string; lists: readonly string[]; reports: string | null; automations: string | null; emulators: string | null; settings: string | null; storefront?: readonly string[] }
export interface NavRegister {
  groups: readonly { id: string; label_key: string; families: readonly string[] }[];
  header: { app: readonly string[]; focus: readonly string[]; [more: string]: unknown };
  rail: { top: readonly string[]; bottom: readonly string[]; never_hidden: readonly string[]; service_menu_order: readonly string[]; max_page_tabs: number; [more: string]: unknown };
  bottom_bar: { max_tabs: number; small_phone_drops: number; person: { tabs: readonly string[]; centre: string; choosable: readonly number[]; [more: string]: unknown };
    business: { centre: Record<string, string>; choosable: readonly number[]; [more: string]: unknown }; soft_keys: readonly string[]; [more: string]: unknown };
  quick_create: readonly QuickItem[]; service_menus: readonly ServiceMenu[]; header_ways_in: Record<string, string>;
  children: Record<string, readonly { screen: string; via: "tap" | "flow" }[]>; three_taps: number; often: readonly string[];
  /** from catalog/business-app.v1.json and catalog/templates.v1.json */
  app_tabs: Record<string, readonly string[]>; screens: Record<string, { template: string; protected?: string; device?: boolean }>;
}

export const groupOf = (reg: NavRegister, family: string): string | null => reg.groups.find((g) => g.families.includes(family))?.id ?? null;
export const templateOf = (reg: NavRegister, screen: string): string | null => reg.screens[screen]?.template ?? null;
export const isFocus = (reg: NavRegister, screen: string | null | undefined): boolean => !!screen && templateOf(reg, screen) === "focus";

/** A focus screen (payment, cash count, void, signature, ballot, one-task device screens) shows only Back or Cancel and the connection chip. */
export const headerFor = (reg: NavRegister, screen: string): string[] => [...(isFocus(reg, screen) ? reg.header.focus : reg.header.app)];

/** The phone bottom bar: kind "person" or a business type; tabs 5, or 4 on a small phone; hidden on focus screens. */
export function bottomBar(reg: NavRegister, kind: string, tabs = 5, screen: string | null = null, chosen: Record<number, string> = {}): string[] {
  if (isFocus(reg, screen)) return [];
  const bb = reg.bottom_bar;
  const person = kind === "person";
  const bar = [...(person ? bb.person.tabs : reg.app_tabs[kind] ?? [])];
  const choosable = person ? bb.person.choosable : bb.business.choosable;
  for (const [pos, tab] of Object.entries(chosen)) if (choosable.includes(Number(pos)) && !bar.includes(tab)) bar[Number(pos)] = tab;
  if (tabs < bar.length) bar.splice(bb.small_phone_drops, 1);
  return bar.slice(0, bb.max_tabs);
}
export const centreOf = (reg: NavRegister, kind: string): string | null => (kind === "person" ? reg.bottom_bar.person.centre : reg.bottom_bar.business.centre[kind] ?? null);

/** What + offers a role; an item planned for a section not yet built is left out. */
export const quickCreate = (reg: NavRegister, role: string, built: readonly string[] | null = null): string[] =>
  reg.quick_create.filter((q) => q.roles.includes(role) && (q.planned_section === undefined || (built !== null && built.includes(q.planned_section)))).map((q) => q.id);

/** A service's menu in the fixed order (Overview, its lists, Reports, Automations, Emulators, Settings); the Storefront side its own items. */
export function serviceMenu(reg: NavRegister, service: string, side: "internal" | "external" = "internal"): [string, string][] {
  const m = reg.service_menus.find((x) => x.service === service);
  if (!m) return [];
  if (side === "external") return (m.storefront ?? []).map((s) => ["storefront", s]);
  const out: [string, string][] = [];
  for (const slot of reg.rail.service_menu_order) {
    if (slot === "lists") { for (const s of m.lists) out.push(["list", s]); continue; }
    const v = (m as unknown as Record<string, string | null>)[slot];
    if (v) out.push([slot, v]);
  }
  return out;
}

/** At most seven tabs in a page; the rest under More. */
export const pageTabs = (reg: NavRegister, tabs: readonly string[]): string[] =>
  tabs.length <= reg.rail.max_page_tabs ? [...tabs] : [...tabs.slice(0, reg.rail.max_page_tabs - 1), "more"];

/** The fewest taps from Home to every Business app screen on a phone of this business type. */
export function tapsFromHome(reg: NavRegister, kind = "shop"): Record<string, number> {
  const e = new Map<string, Set<string>>();
  const add = (a: string, b: string): void => { if (!e.has(a)) e.set(a, new Set()); e.get(a)!.add(b); };
  e.set("home", new Set());
  for (const t of reg.app_tabs[kind] ?? []) if (t in reg.screens) add("home", t);
  for (const target of Object.values(reg.header_ways_in)) add("home", target);
  add("home", "@launcher"); add("home", "@quick_create");
  for (const m of reg.service_menus) {
    add("@launcher", m.overview);
    for (const [, s] of [...serviceMenu(reg, m.service), ...serviceMenu(reg, m.service, "external")]) if (s !== m.overview) add(m.overview, s);
  }
  for (const q of reg.quick_create) if (q.opens) add("@quick_create", q.opens);
  for (const [p, kids] of Object.entries(reg.children)) for (const k of kids) add(p, k.screen);
  const dist: Record<string, number> = { home: 0 };
  let todo = ["home"];
  while (todo.length) {
    const next: string[] = [];
    for (const a of todo) for (const b of [...(e.get(a) ?? [])].sort()) if (!(b in dist)) { dist[b] = dist[a]! + 1; next.push(b); }
    todo = next;
  }
  const out: Record<string, number> = {};
  for (const k of Object.keys(dist).sort()) if (!k.startsWith("@")) out[k] = dist[k]!;
  return out;
}
