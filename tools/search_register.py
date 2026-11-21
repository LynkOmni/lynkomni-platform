#!/usr/bin/env python3
"""Builds catalog/search.v1.json, the search register (MASTER UPDATE, master blueprint section 57), from the one address map and
the product catalog. Never edit the register by hand: change the catalog and run

    python3 tools/search_register.py

tests/test_search_register.py fails when the register is stale. Only public pages of indexed hosts are listed; app, account, pay,
staff, partner, API and mail addresses never are, and neither are pages that carry a private record (a parcel tracker, a table
code). Titles and descriptions are written per language in build section 5 under the keys named here."""
import json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from core.breadcrumbs import trail  # noqa: E402
from core import names  # noqa: E402

OUT = os.path.join(ROOT, "catalog", "search.v1.json")
PRIVATE_RECORD = re.compile(r"\{LO(?!LST)[A-Z]+\}|\{table\}")
HOST_SECTION = {"lynkomni.com": 5, "shop.lynkomni.com": 7, "booking.lynkomni.com": 8, "essential.lynkomni.com": 9,
                "exchange.lynkomni.com": 10, "hub.lynkomni.com": 11, "doc.lynkomni.com": 11, "sdk.lynkomni.com": 11,
                "status.lynkomni.com": 6, "vote.lynkomni.com": 14, "job.lynkomni.com": "8B"}
FAMILIES = [
    {"id": "countries", "what": "one page per country, only where the country truly differs (what is on, local rules)", "build_section": 5},
    {"id": "business_kinds", "what": "one page per kind of business or entity", "build_section": 5},
    {"id": "comparisons", "what": "honest comparisons with kinds of tools; a rival is named only after a lawyer's review", "build_section": 5},
    {"id": "free_tools", "what": "invoice maker, receipt maker, price and margin calculator, QR maker", "build_section": 5},
    {"id": "glossary", "what": "plain explanations of business words, in every language", "build_section": 5},
    {"id": "help_articles", "what": "how-to tasks and grouped questions as real help articles", "build_section": 6},
    {"id": "shop_pages", "what": "shop, offer and review pages with local business facts", "build_section": 7},
    {"id": "api_pages", "what": "every API with examples", "build_section": 11},
    {"id": "names", "what": "Names A to Z: every Lynk name with its plain word, what it does and the names it could be confused with, in every language", "build_section": 5},
]
# Plain words in search (owner, 21 November 2026; catalog/names.v1.json "outside": search_engines). Section 5 writes every product
# page's title and sharing card from this pattern, in every language, and its keyword register from these sources.
NAMES = {"source": "catalog/names.v1.json",
         "title": "{name}: {plain}",
         "rule": "A product page's title, description, sharing card and app store text lead with its Lynk name and plain word in the page's language. Search words for each name are its name, its plain word and description in every language, its spoken form and its old names; a page about an old name never exists, the old address redirects to the new page.",
         "search_words": ["name", "plain word (web/names, every language)", "description (web/nameinfo, every language)", "spoken form", "old names (now_called)"],
         "names_page": "https://lynkomni.com/names"}


def _kind(path, product_pages):
    if path in product_pages:
        return "product"
    for prefix, kind in (("/legal", "legal"), ("/trust", "trust"), ("/developers", "developers"), ("/solutions", "solutions"),
                         ("/about", "company"), ("/careers", "company"), ("/investors", "company"), ("/newsroom", "company"),
                         ("/brand", "company"), ("/blog", "company"), ("/roadmap", "company"), ("/contact", "company"),
                         ("/partners", "company"), ("/faq", "help"), ("/support", "help"), ("/safety", "help"),
                         ("/feedback", "help"), ("/recover", "help"), ("/names", "help"), ("/pricing", "pricing")):
        if path == prefix or path.startswith(prefix + "/"):
            return kind
    return "page"


def _slug(host, path):
    base = host.replace(".lynkomni.com", "").replace("lynkomni.com", "www")
    rest = re.sub(r"[{}]", "", path).strip("/").replace("/", "-") or "home"
    return f"{base}-{rest}".lower()


def build():
    with open(os.path.join(ROOT, "catalog", "addresses.v1.json"), encoding="utf-8") as f:
        addr = json.load(f)
    with open(os.path.join(ROOT, "catalog", "products.v1.json"), encoding="utf-8") as f:
        cat = json.load(f)
    products = cat.get("products") or cat
    product_pages = {p["page"] for p in products if p.get("page", "").startswith("/")}
    page_name = {p["page"]: names.for_family(p["family"]) for p in products if p.get("page", "").startswith("/")}
    indexed = [h["host"] for h in addr["hosts"] if h["indexed"]]
    pages = []
    for host in indexed:
        paths = addr["website_paths"] if host == "lynkomni.com" else addr["shop_paths"] if host == "shop.lynkomni.com" else ["/"]
        for path in paths:
            if PRIVATE_RECORD.search(path):
                continue
            slug = _slug(host, path)
            pages.append({"url": f"https://{host}{path}", "kind": _kind(path, product_pages) if host == "lynkomni.com" else "site",
                          "title_key": f"seo_title_{slug}", "description_key": f"seo_desc_{slug}",
                          "breadcrumb": trail(host, path) if host in ("lynkomni.com", "shop.lynkomni.com") else ["/"],
                          "langs": "all", "build_section": HOST_SECTION[host], "status": "planned"})
            if host == "lynkomni.com" and page_name.get(path):
                n = page_name[path]
                pages[-1].update({"name": n, "plain_key": names.plain_key(n), "old_names": [o for o, x in names.NOW_CALLED.items() if names.BY_ID[x["id"]]["name"] == n]})
    return {"version": 1, "agreed": "2026-11-10",
            "rule": "MASTER UPDATE 57: every public page with its title, description, language versions and kind. Generated by tools/search_register.py; never edited by hand. No bought links, copied or hidden text, keyword stuffing or fake reviews; pages are published as written.",
            "never_indexed_hosts": [h["host"] for h in addr["hosts"] if not h["indexed"]],
            "change_notices": {"indexnow": ["Bing", "Yandex", "Naver", "Seznam"], "google": "Search Console and page lists"},
            "families": FAMILIES, "names": NAMES, "pages": pages}


if __name__ == "__main__":
    reg = build()
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(reg, f, indent=1, ensure_ascii=False)
        f.write("\n")
    print(f"{len(reg['pages'])} public pages -> {os.path.relpath(OUT, ROOT)}")
