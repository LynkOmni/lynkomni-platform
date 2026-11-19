"""Every menu in LynkOmni (INTERFACE UPDATE, master blueprint 73; catalog/navigation.v1.json), with the page templates of
catalog/templates.v1.json. The TypeScript port is ts/src/navigation.ts; contract/vectors/navigation.v1.json proves both give the
same menus, bottom bars, quick-create lists and taps from Home (run python3 tools/navigation_vectors.py after a change).

No screen builds its own menu: the header, side bar, bottom bar, launcher, quick create and each service's menu are read from here."""
import json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load(name):
    with open(os.path.join(ROOT, "catalog", name), encoding="utf-8") as f:
        return json.load(f)


NAV = _load("navigation.v1.json")
TEMPLATES = _load("templates.v1.json")
APP = _load("business-app.v1.json")
SCREENS = {s["id"]: s for s in APP["screens"]}
GROUP_OF = {fam: g["id"] for g in NAV["groups"] for fam in g["families"]}
MENUS = {m["service"]: m for m in NAV["service_menus"]}


def group_of(family):
    """The one group a billing family sits in (header menu, launcher, side bar, footer and search)."""
    return GROUP_OF.get(family)


def protected(screen):
    """The protected task a screen holds (payment, cash_count, void, signature, ballot) or None."""
    return TEMPLATES["screens"].get(screen, {}).get("protected")


def template(screen):
    return TEMPLATES["screens"][screen]["template"]


def header(screen):
    """The header parts: a focus screen (protected or a one-task device screen) shows only Back or Cancel and the connection chip."""
    return list(NAV["header"]["focus"] if template(screen) == "focus" else NAV["header"]["app"])


def bottom_bar(kind, tabs=5, screen=None, chosen=None):
    """The bottom bar of a phone. kind: "person" or a business type of catalog/business-app.v1.json; tabs: 5, or 4 on a small phone
    (layout() decides); chosen: {position: tab} for the two middle tabs a person may choose. Hidden (empty) on focus screens."""
    if screen and template(screen) == "focus":
        return []
    bb = NAV["bottom_bar"]
    if kind == "person":
        bar, choosable = list(bb["person"]["tabs"]), bb["person"]["choosable"]
    else:
        bar, choosable = list(APP["tabs"][kind]), bb["business"]["choosable"]
    for pos, tab in (chosen or {}).items():
        if int(pos) in choosable and tab not in bar:
            bar[int(pos)] = tab
    if tabs < len(bar):
        bar.pop(bb["small_phone_drops"])
    return bar[:bb["max_tabs"]]


def centre(kind):
    bb = NAV["bottom_bar"]
    return bb["person"]["centre"] if kind == "person" else bb["business"]["centre"][kind]


def quick_create(role, built=None):
    """What + offers a role. built: the build sections already built; an item planned for a later section is left out."""
    out = []
    for q in NAV["quick_create"]:
        if role not in q["roles"]:
            continue
        if "planned_section" in q and (built is None or q["planned_section"] not in built):
            continue
        out.append(q["id"])
    return out


def service_menu(service, side="internal"):
    """A service's second side-bar column, always in the same order: Overview, its lists, Reports, Automations, Emulators, Settings;
    on the Storefront side its Storefront items. Returns [(slot, screen)], leaving out slots the service does not have."""
    m = MENUS[service]
    if side == "external":
        return [("storefront", s) for s in m.get("storefront", [])]
    out = []
    for slot in NAV["rail"]["service_menu_order"]:
        v = m.get(slot)
        if slot == "lists":
            out += [("list", s) for s in v]
        elif v:
            out.append((slot, v))
    return out


def page_tabs(tabs):
    """At most seven tabs in a page; the rest go under More."""
    n = NAV["rail"]["max_page_tabs"]
    return list(tabs) if len(tabs) <= n else list(tabs[:n - 1]) + ["more"]


def _edges(kind):
    """Every way in, with one tap each: Home -> tabs and header buttons; Home -> launcher -> a service; quick create; a service's
    overview -> its menu; a screen -> its children."""
    e = {"home": set()}
    def add(a, b): e.setdefault(a, set()).add(b)
    for t in APP["tabs"][kind]:
        if t in SCREENS: add("home", t)
    for target in NAV["header_ways_in"].values():
        add("home", target)
    add("home", "@launcher"); add("home", "@quick_create")
    for m in NAV["service_menus"]:
        add("@launcher", m["overview"])
        for slot, s in service_menu(m["service"]) + service_menu(m["service"], "external"):
            if s != m["overview"]: add(m["overview"], s)
    for q in NAV["quick_create"]:
        if "opens" in q: add("@quick_create", q["opens"])
    for parent, kids in NAV["children"].items():
        for k in kids: add(parent, k["screen"])
    return e


def taps_from_home(kind="shop"):
    """The fewest taps from Home to every screen of the Business app on a phone of this business type."""
    e, dist, todo = _edges(kind), {"home": 0}, ["home"]
    while todo:
        nxt = []
        for a in todo:
            for b in sorted(e.get(a, ())):
                if b not in dist:
                    dist[b] = dist[a] + 1; nxt.append(b)
        todo = nxt
    return {k: v for k, v in sorted(dist.items()) if not k.startswith("@")}


def validate():
    """Register self-check: every family in exactly one group, every screen with a template and a way in, every menu entry real,
    nothing used often more than three taps from Home."""
    problems = []
    products = {p["family"] for p in _load("products.v1.json")["products"]}
    seen = [f for g in NAV["groups"] for f in g["families"]]
    for f in set(seen):
        if seen.count(f) > 1: problems.append(f"{f} sits in more than one group")
    if set(seen) != products: problems.append(f"groups differ from the products: {sorted(set(seen) ^ products)}")
    if len(NAV["groups"]) != 8: problems.append("there are eight groups")
    tpl = TEMPLATES["screens"]
    if set(tpl) != set(SCREENS): problems.append(f"templates differ from the screens: {sorted(set(tpl) ^ set(SCREENS))}")
    for s, v in tpl.items():
        if v["template"] not in TEMPLATES["templates"]: problems.append(f"{s}: unknown template {v['template']}")
        if v.get("protected") and v.get("protected") not in NAV["protected"]: problems.append(f"{s}: unknown protected task")
    named = set()
    for m in NAV["service_menus"]:
        for _, s in service_menu(m["service"]) + service_menu(m["service"], "external"):
            named.add(s)
            if s not in SCREENS: problems.append(f"{m['service']}: menu names unknown screen {s}")
        if m["family"] and m["family"] not in products: problems.append(f"{m['service']}: unknown family")
    for p, kids in NAV["children"].items():
        if p not in SCREENS: problems.append(f"children: unknown parent {p}")
        for k in kids:
            if k["screen"] not in SCREENS: problems.append(f"children: unknown screen {k['screen']}")
            if k["via"] not in ("tap", "flow"): problems.append(f"children: {k['screen']} via")
    for q in NAV["quick_create"]:
        if q.get("opens") and q["opens"] not in SCREENS: problems.append(f"quick create {q['id']}: unknown screen")
        if q["family"] not in products: problems.append(f"quick create {q['id']}: unknown family")
    taps = taps_from_home("shop")
    for s in SCREENS:
        if s not in taps: problems.append(f"{s} has no way in")
    for s in NAV["often"]:
        if taps.get(s, 99) > NAV["three_taps"]: problems.append(f"{s} is used often but {taps.get(s)} taps from Home")
    for place in TEMPLATES["places"]:
        if not os.path.isdir(os.path.join(ROOT, "web", "emulators", place)): problems.append(f"place {place} is not an emulator")
    return problems
