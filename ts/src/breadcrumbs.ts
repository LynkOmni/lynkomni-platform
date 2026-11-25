/** Breadcrumbs and the public page head (MASTER UPDATE, master blueprint section 57; build section 1).
 *  Trails come from the one address map, by the rule of core/breadcrumbs.py (checked by contract/vectors/parts.v1.json): every
 *  address's parent is the nearest shorter address on its host, Storefront trails start at /external, a shop's at its page.
 *  Labels come from the translated menu names through the caller; addresses themselves never change by language. */
import { ADDRESS_HOSTS, STOREFRONT_PREFIX } from "./parts.generated.js";
import { esc } from "./shell.js";
import type { T } from "./shell.js";

export function trailHome(host: string, path: string): string {
  if (host === "app.lynkomni.com" && (path === STOREFRONT_PREFIX || path.startsWith(STOREFRONT_PREFIX + "/"))) return STOREFRONT_PREFIX;
  if (host === "shop.lynkomni.com" && path.startsWith("/{username}")) return "/{username}";
  return "/";
}
export function parent(host: string, path: string): string | null {
  const known = new Set(ADDRESS_HOSTS[host] ?? []);
  const h = trailHome(host, path);
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

/** The "up one level" key (CONNECT UPDATE 71.5): the step before the page, the same on every device; null at home. */
export function upOne(host: string, path: string): string | null { return parent(host, path); }
/** Jump sideways: the other pages that share this page's parent, in address-map order; a record page has none. */
export function siblings(host: string, path: string): string[] {
  const last = (x: string) => x.slice(x.lastIndexOf("/") + 1);
  if (last(path).includes("{")) return [];
  const par = parent(host, path);
  if (par === null) return [];
  return (ADDRESS_HOSTS[host] ?? []).filter((p) => p !== path && !last(p).includes("{") && parent(host, p) === par);
}

/** The "up one level" key: Alt with the Up arrow on every keyboard (catalog/devices.v1.json keys "up"); a buttons-only device
 *  uses its Back key, which already goes one level up. */
export const UP_KEY = "Alt+ArrowUp";
export const isUpKey = (e: { key: string; altKey: boolean; ctrlKey?: boolean; metaKey?: boolean }): boolean => e.key === "ArrowUp" && e.altKey && !e.ctrlKey && !e.metaKey;

/** The breadcrumb part: an ordered list, the page itself last and marked as current, never a link to itself. On a phone only
 *  the parent shows, as a "back to" link, so the line never wraps into a wall of words. The parent step answers the up key
 *  (data-up). With more: a "Pages here" list of the page's siblings to jump sideways, and Copy link (CONNECT UPDATE 71.5). */
export function breadcrumbBar(steps: { path: string; label: string }[], compact: boolean, t: T, more?: { siblings?: { path: string; label: string }[]; link?: string }): string {
  if (steps.length < 2) return "";
  const parentAt = steps.length - 2;
  if (compact) { const up = steps[parentAt]!; return `<nav class="crumbs compact" aria-label="${esc(t("crumbs"))}"><a href="${esc(up.path)}" data-act="go:${esc(up.path)}" data-up aria-keyshortcuts="${UP_KEY}">‹ ${esc(up.label)}</a></nav>`; }
  const sibs = more?.siblings ?? [];
  const menu = sibs.length || more?.link ? `<details class="crumb-more"><summary>${esc(t("crumbs_more"))}</summary><div class="crumb-menu">${sibs.length ? `<p class="crumb-head">${esc(t("crumbs_siblings"))}</p><ul>${sibs.map((x) => `<li><a href="${esc(x.path)}" data-act="go:${esc(x.path)}">${esc(x.label)}</a></li>`).join("")}</ul>` : ""}${more?.link ? `<button type="button" class="crumb-copy" data-crumb-copy="${esc(more.link)}" data-copied="${esc(t("crumbs_copied"))}">${esc(t("crumbs_copy"))}</button>` : ""}</div></details>` : "";
  return `<nav class="crumbs" aria-label="${esc(t("crumbs"))}"><ol>${steps.map((s, i) => i === steps.length - 1 ? `<li><span aria-current="page">${esc(s.label)}</span>${menu}</li>` : `<li><a href="${esc(s.path)}" data-act="go:${esc(s.path)}"${i === parentAt ? ` data-up aria-keyshortcuts="${UP_KEY}"` : ""}>${esc(s.label)}</a></li>`).join("")}</ol></nav>`;
}

/** Once per page: the up key follows the trail's parent step, and Copy link copies the page's address (a note says Copied). */
export function wireCrumbs(doc: Document): void {
  doc.addEventListener("keydown", (e) => { if (!isUpKey(e)) return; const up = doc.querySelector<HTMLElement>(".crumbs [data-up]"); if (up) { e.preventDefault(); up.click(); } });
  doc.addEventListener("click", (e) => {
    const b = (e.target as HTMLElement).closest<HTMLButtonElement>("[data-crumb-copy]"); if (!b) return;
    try { void navigator.clipboard?.writeText(b.dataset["crumbCopy"] ?? ""); } catch { /* no clipboard here: the address stays visible in the browser */ }
    b.textContent = b.dataset["copied"] ?? b.textContent;
  });
}
