/** The two sides of every service (BIZZ & DEVICE, owner approved 2026-11-09). Port of core/sides.py; the shared vectors in
 *  contract/vectors/sides.v1.json prove both agree. internal = the workspace (a person, company or organisation using a service
 *  for its own affairs); external = the Storefront (offering to others and earning). The side is read from the address alone,
 *  so billing, records, support channels, automations and reports switch by themselves. */
export type Side = "internal" | "external";
export type PathKind = "mirrored" | "storefront_only" | "shared" | "workspace_only";
export interface SideRule { prefix: string; mirrors: readonly string[]; storefront_only: readonly string[]; shared: readonly string[]; workspace_only: readonly string[]; lists: readonly string[] }

const clean = (p: string): string => p.split("?", 1)[0]!.split("#", 1)[0]! || "/";

/** The side of an address (a path in the app, or host + path). */
export function sideOf(rule: SideRule, address: string): Side {
  let host = "", path = address;
  if (!address.startsWith("/")) { const i = address.indexOf("/"); host = i < 0 ? address : address.slice(0, i); path = i < 0 ? "/" : address.slice(i); }
  path = clean(path);
  if (host === "" || host === "app.lynkomni.com") return path === rule.prefix || path.startsWith(rule.prefix + "/") ? "external" : "internal";
  if (host === "pay.lynkomni.com") { const s = path.replace(/^\/+|\/+$/g, "").split("/"); return s.length === 2 && s[0] === "listings" ? "external" : "internal"; }
  if (host === "shop.lynkomni.com") {
    const t = path.replace(/^\/+|\/+$/g, ""), s = t ? t.split("/") : [];
    if (s.length === 2 && s[0] === "explore") return rule.lists.includes(s[1]!) ? "external" : "internal";
    if (s.length === 1 && s[0] !== "explore" && s[0] !== "track") return "external";      // a seller's Storefront page
    if (s.length === 3 && rule.lists.includes(s[1]!)) return "external";                    // one offer
    return "internal";                                                                       // tables, reviews, following a purchase
  }
  return "internal";
}

/** The Storefront twin of a mirrored workspace path (/external + the path). */
export function storefrontPath(rule: SideRule, workspacePath: string): string {
  if (!rule.mirrors.includes(workspacePath)) throw new Error(`${workspacePath} has no Storefront side`);
  return rule.prefix + workspacePath;
}

export function pathKind(rule: SideRule, appPath: string): PathKind {
  if (rule.storefront_only.includes(appPath)) return "storefront_only";
  if (appPath.startsWith(rule.prefix + "/") && rule.mirrors.includes(appPath.slice(rule.prefix.length))) return "mirrored";
  if (rule.mirrors.includes(appPath)) return "mirrored";
  if (rule.shared.includes(appPath)) return "shared";
  if (rule.workspace_only.includes(appPath)) return "workspace_only";
  throw new Error(`${appPath} is not classified`);
}
