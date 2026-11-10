/** Breadcrumbs and the public page head (MASTER UPDATE, master blueprint section 57; build section 1).
 *  Trails come from the one address map, by the rule of core/breadcrumbs.py (checked by contract/vectors/parts.v1.json): every
 *  address's parent is the nearest shorter address on its host, Storefront trails start at /external, a shop's at its page.
 *  Labels come from the translated menu names through the caller; addresses themselves never change by language. */
import { ADDRESS_HOSTS, STOREFRONT_PREFIX } from "./parts.generated.js";
import { esc } from "./shell.js";
import type { T } from "./shell.js";

export function home(host: string, path: string): string {
  if (host === "app.lynkomni.com" && (path === STOREFRONT_PREFIX || path.startsWith(STOREFRONT_PREFIX + "/"))) return STOREFRONT_PREFIX;
  if (host === "shop.lynkomni.com" && path.startsWith("/{username}")) return "/{username}";
  return "/";
}
export function parent(host: string, path: string): string | null {
  const known = new Set(ADDRESS_HOSTS[host] ?? []);
  const h = home(host, path);
  if (path === h) return null;
  let parts = path.replace(/\/+$/, "").split("/");
  while (parts.length > 1) {
    parts = parts.slice(0, -1);
    const cand = parts.join("/") || "/";
    if (known.has(cand) && (cand.startsWith(h) || h === "/")) return cand;
    if (cand === h) return h;
  }
  return h;
}
export function trail(host: string, path: string): string[] {
  const steps = [path];
  for (;;) {
    const p = parent(host, steps[0]!);
    if (p === null) return steps;
    if (steps.includes(p)) throw new Error(`loop in the trail of ${host}${path}`);
    steps.unshift(p);
  }
}

/** The breadcrumb part: an ordered list, the page itself last and marked as current, never a link to itself. On a phone only
 *  the parent shows, as a "back to" link, so the line never wraps into a wall of words. */
export function breadcrumbBar(steps: { path: string; label: string }[], compact: boolean, t: T): string {
  if (steps.length < 2) return "";
  if (compact) { const up = steps[steps.length - 2]!; return `<nav class="crumbs compact" aria-label="${esc(t("crumbs"))}"><a href="${esc(up.path)}" data-act="go:${esc(up.path)}">‹ ${esc(up.label)}</a></nav>`; }
  return `<nav class="crumbs" aria-label="${esc(t("crumbs"))}"><ol>${steps.map((s, i) => i === steps.length - 1 ? `<li><span aria-current="page">${esc(s.label)}</span></li>` : `<li><a href="${esc(s.path)}" data-act="go:${esc(s.path)}">${esc(s.label)}</a></li>`).join("")}</ol></nav>`;
}
