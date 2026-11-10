/** The head of every public page (MASTER UPDATE, master blueprint section 57; build section 1): title, description, canonical
 *  address, one alternate per language and x-default, robots, the sharing tags and the breadcrumb list for search engines.
 *  Values come from catalog/search.v1.json. Used where pages are served (the website and shop pages, section 5); the offline
 *  emulators never carry it. */
import { LANGS, NEVER_INDEXED } from "./parts.generated.js";
import { esc } from "./shell.js";
import type { T } from "./shell.js";

export interface SearchPage { url: string; kind: string; title_key: string; description_key: string; breadcrumb: string[]; langs: "all" | string[] }
/** The address of a page in one language: the main website carries the language as its first step (/fr/pricing); English has none. */
export function langUrl(url: string, lang: string): string {
  const u = new URL(url);
  if (u.hostname !== "lynkomni.com" || lang === "en") return u.href;
  return `${u.origin}/${lang}${u.pathname === "/" ? "" : u.pathname}`;
}
/** The head of a public page, as tags. JSON-LD goes in its own script, which the page's safety policy pins by hash like any other. */
export function pageHead(p: SearchPage, lang: string, t: T, crumbLabel: (path: string) => string): string {
  const u = new URL(p.url);
  const langs = p.langs === "all" ? LANGS : p.langs;
  const title = t(p.title_key), desc = t(p.description_key), canonical = langUrl(p.url, lang);
  const index = !NEVER_INDEXED.includes(u.hostname);
  const alt = langs.map((l) => `<link rel="alternate" hreflang="${esc(l)}" href="${esc(langUrl(p.url, l))}">`).join("") + `<link rel="alternate" hreflang="x-default" href="${esc(langUrl(p.url, "en"))}">`;
  const list = { "@context": "https://schema.org", "@type": "BreadcrumbList", itemListElement: p.breadcrumb.map((path, i) => ({ "@type": "ListItem", position: i + 1, name: crumbLabel(path), item: langUrl(`${u.origin}${path}`, lang) })) };
  return `<title>${esc(title)}</title><meta name="description" content="${esc(desc)}"><link rel="canonical" href="${esc(canonical)}">${alt}<meta name="robots" content="${index ? "index, follow" : "noindex, nofollow"}"><meta property="og:type" content="website"><meta property="og:title" content="${esc(title)}"><meta property="og:description" content="${esc(desc)}"><meta property="og:url" content="${esc(canonical)}"><meta property="og:locale" content="${esc(lang.replace("-", "_"))}"><meta name="twitter:card" content="summary"><script type="application/ld+json">${JSON.stringify(list).replace(/</g, "\\u003c")}<\/script>`; // written as <\/script> so a page that carries this code never ends its own script early
}
