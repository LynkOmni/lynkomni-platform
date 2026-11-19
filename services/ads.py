"""Advertising (master blueprint sections 21 and 79, ADS UPDATE 2026-11-19). Every rule comes from catalog/ads.v1.json: ads show
only in the places listed there (an allow-list), matched to the screen's subject and never to the person, always labelled,
capped, never in the never list, never on a paid tier, never for a child or in a household workspace. Off per country until
legal and policy sign-off. Offline: devices cache a bundle, and their impressions sync later. Only impressions that were really
seen count; devices never bill; advertisers see totals only, and never below the report minimum."""
import json, os, time, uuid
from core.locale import t
from core.regions import country
from services.control import COMPANY

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
with open(os.path.join(_ROOT, "catalog", "ads.v1.json"), encoding="utf-8") as _f:
    REGISTER = json.load(_f)
PLACES = {p["id"]: p for p in REGISTER["places"]}
SURFACES = set(PLACES)
BLOCKED_SCREENS = set(REGISTER["never"])
NEVER_AUDIENCES = set(REGISTER["never_audiences"])
CATS = REGISTER["categories"]
BASELINE_BLOCKED = set(CATS["blocked"])                  # never accepted anywhere
AGE_SENSITIVE = set(CATS["age_sensitive"])               # only where the country pack allows it, never for children
REGULATED = set(CATS["regulated"])                       # need a licensed advertiser in every target country
SHARE_BPS = {k: p["share_bps"] for k, p in PLACES.items() if p["share_bps"]}   # merchant share of ad income: PLACEHOLDERS
CAPS = REGISTER["caps"]
DAILY_CAP = CAPS["per_campaign_per_merchant_per_day"]
VIEW = REGISTER["viewability"]
REPORT_MIN = REGISTER["report_minimum"]
HOSTED_BY_CHOICE = {k for k, p in PLACES.items() if p["owner"] == "merchant" and p["audience"] in ("customer", "public")}
BILLABLE = {"cpm": "ad.impression", "cpc": "ad.click", "cpa": "ad.conversion"}
def _id(): return uuid.uuid4().hex


class Ads:
    billing = None   # set by the platform: ads show on a product's place only while that product is on its Free tier
    SURFACE_PRODUCT = {k: p["family"] for k, p in PLACES.items() if p["family"] not in ("platform", "storefront")}
    def __init__(s, c, control): s.c, s.control = c, control

    # advertiser side
    def create_campaign(s, advertiser, category, creative, countries, model, price_minor, budget_minor, currency,
                        surfaces=None, licensed_in=(), merchant_types=None, contexts=None):
        cid = _id()
        s.c.store.append(COMPANY, "server", "ad.campaign", {"id": cid, "advertiser": advertiser, "category": category, "creative": creative,
                         "countries": list(countries), "model": model, "price_minor": price_minor, "budget_minor": budget_minor,
                         "currency": currency, "surfaces": list(surfaces or SURFACES), "licensed_in": list(licensed_in),
                         "merchant_types": merchant_types, "contexts": contexts})
        return cid
    def review(s, cid, reviewer="policy"):
        c = s._all()[cid]; reason = None
        packs = [country(k) for k in c["countries"]]
        blocked = BASELINE_BLOCKED | {x for p in packs for x in p.get("blocked_ad_categories", ())}
        if c["category"] in blocked:
            reason = "category not allowed"
        elif c["category"] in AGE_SENSITIVE and not all(c["category"] in p.get("allowed_ad_categories", ()) for p in packs):
            reason = "age-sensitive category: allowed only where every target country allows it"
        elif c["category"] in REGULATED and not set(c["countries"]) <= set(c["licensed_in"]):
            reason = "regulated category: advertiser must be licensed in every target country"
        s.c.store.append(COMPANY, reviewer, "ad.reviewed", {"id": cid, "approved": reason is None, "reason": reason})
        return {"approved": reason is None, "reason": reason}
    def _all(s): return {e["payload"]["id"]: e["payload"] for e in s.c.store.of(COMPANY, "ad.campaign")}
    def _active(s):
        ok = {e["payload"]["id"]: e["payload"]["approved"] for e in s.c.store.of(COMPANY, "ad.reviewed")}
        return {k: v for k, v in s._all().items() if ok.get(k)}

    # merchant controls (register merchant_controls)
    def set_ad_free(s, m, on=True): s.c.store.append(m, "server", "ad.plan", {"ad_free": on})
    def ad_free(s, m):
        e = s.c.store.of(m, "ad.plan"); return bool(e and e[-1]["payload"]["ad_free"])
    def opt_out(s, m, category): s.c.store.append(m, "server", "ad.optout", {"category": category})
    def block_advertiser(s, m, advertiser): s.c.store.append(m, "server", "ad.block", {"advertiser": advertiser})
    def set_hosting(s, m, place, on=True):
        """Customer-facing places the merchant owns (receipts, the customer display, in-store screens, offers) show ads only
        after the merchant switches them on; the merchant earns the share there."""
        if place not in HOSTED_BY_CHOICE:
            raise ValueError(f"{place} is not a place the merchant chooses to host")
        s.c.store.append(m, "server", "ad.hosting", {"place": place, "on": on})
    def hosting(s, m, place):
        if place not in HOSTED_BY_CHOICE:
            return True
        on = False
        for e in s.c.store.of(m, "ad.hosting"):
            if e["payload"]["place"] == place:
                on = e["payload"]["on"]
        return on
    def earnings(s, m):
        """The merchant's ad share, for LynkAcc (income) and the earnings card."""
        out = {}
        for e in s.c.store.of(m, "ad.share.earned"):
            cur = e["payload"]["currency"]; out[cur] = out.get(cur, 0) + e["payload"]["amount_minor"]
        return out

    # person controls
    def why(s, cid, context=None):
        """Why am I seeing this? The answer names the screen's subject and country, never anything about the person."""
        c = s._all()[cid]
        return {"advertiser": c["advertiser"], "because": ["this screen's subject" if context else "this kind of screen", "your country"],
                "never": "your personal data, history or position"}
    def report_ad(s, m, cid, reason):
        s.c.store.append(m, "server", "ad.reported", {"campaign_id": cid, "reason": reason})
        by = {e["merchant"] for e in s.c.store.all_of("ad.reported") if e["payload"]["campaign_id"] == cid}
        if len(by) >= CAPS["reports_before_pause"] and cid in s._active():
            s.c.store.append(COMPANY, "server", "ad.reviewed", {"id": cid, "approved": False, "reason": "paused after reports, waiting for a person's review"})
            return {"paused": True}
        return {"paused": False}

    # serving
    def select(s, m, surface, screen=None, lang="en", context=None, merchant_type=None, today=None, audience=None, workspace=None):
        if surface not in SURFACES:
            raise ValueError(f"unknown ad surface {surface}")   # ads only in registered places
        if screen in BLOCKED_SCREENS or audience in NEVER_AUDIENCES or workspace in NEVER_AUDIENCES:
            return None  # never in payments, voids, counts, refunds, fiscal data, private chats, children's or household places...
        s.c.gate(m, "ads")
        pr, today = s.c.profile(m), today or time.strftime("%Y-%m-%d", time.gmtime())
        if s.ad_free(m) or not s.hosting(m, surface):
            return None
        fam = s.SURFACE_PRODUCT.get(surface)
        if fam and s.billing and not s.billing.ads_enabled(m, fam):
            return None
        out = {e["payload"]["category"] for e in s.c.store.of(m, "ad.optout")}
        blocked_by = {e["payload"]["advertiser"] for e in s.c.store.of(m, "ad.block")}
        best, best_score = None, -1
        for cid, c in s._active().items():
            if pr["country"] not in c["countries"] or surface not in c["surfaces"] or c["category"] in out or c["advertiser"] in blocked_by:
                continue
            if c["category"] in country(pr["country"]).get("blocked_ad_categories", ()):
                continue
            if lang not in c["creative"] and "en" not in c["creative"]:
                continue
            if (c["contexts"] and context not in c["contexts"]) or (c["merchant_types"] and merchant_type not in c["merchant_types"]):
                continue
            if s._cost(c, s._valid(cid)) >= c["budget_minor"]:
                continue
            shown = sum(1 for e in s.c.store.of(m, "ad.impression") if e["payload"]["campaign_id"] == cid and e["ts"][:10] == today)
            if shown >= DAILY_CAP:
                continue
            score = c["price_minor"] * (2 if c["contexts"] and context in c["contexts"] else 1)   # relevance doubles the bid
            if score > best_score:
                best, best_score = c, score
        if best is None:
            return None
        return {"campaign_id": best["id"], "surface": surface, "label": t(lang, "sponsored"), "text": best["creative"].get(lang) or best["creative"]["en"]}
    def bundle(s, m, surfaces, lang="en", **kw):
        """Ads a device caches so it can show them offline (no network call while a screen draws). One per place."""
        return [a for sf in surfaces if (a := s.select(m, sf, lang=lang, **kw))]
    def impression(s, m, device, cid, surface, visible_pct=None, visible_ms=None):
        s.c.store.append(m, device, "ad.impression", {"campaign_id": cid, "surface": surface, "visible_pct": visible_pct, "visible_ms": visible_ms})
    def click(s, m, device, cid, surface): s.c.store.append(m, device, "ad.click", {"campaign_id": cid, "surface": surface})
    def conversion(s, m, cid, surface): s.c.store.append(m, "server", "ad.conversion", {"campaign_id": cid, "surface": surface})
    def receipt_footer(s, m, lang="en", **kw):
        """The labelled ad for a receipt, or None. Pass it to receipt_text(ad=...); it prints last and never on a fiscal document."""
        return s.select(m, "receipt_footer", screen="receipt", lang=lang, **kw)

    # measurement and money
    @staticmethod
    def _seen(p):
        return (p.get("visible_pct") or 0) >= VIEW["min_visible_pct"] and (p.get("visible_ms") or 0) >= VIEW["min_visible_ms"]
    def _valid(s, cid):
        seen, per_hour, imp_merchants, out = {}, {}, set(), []
        for e in s.c.store.all_of("ad.impression", "ad.click", "ad.conversion"):
            if e["payload"]["campaign_id"] != cid:
                continue
            if e["type"] == "ad.impression":
                if not s._seen(e["payload"]):
                    continue  # not really seen: not billable
                k = (e["merchant"], e["ts"][:10]); seen[k] = seen.get(k, 0) + 1
                h = (e["merchant"], e.get("device"), e["ts"][:13]); per_hour[h] = per_hour.get(h, 0) + 1
                if seen[k] > DAILY_CAP or per_hour[h] > CAPS["per_device_per_hour"]:
                    continue  # beyond a cap: not billable
                imp_merchants.add(e["merchant"])
            elif e["merchant"] not in imp_merchants:
                continue      # a click or conversion with no counted impression is not billable
            out.append(e)
        return out
    @staticmethod
    def _cost(c, ev):
        n = sum(1 for e in ev if e["type"] == BILLABLE[c["model"]])
        return min(n * c["price_minor"] // (1000 if c["model"] == "cpm" else 1), c["budget_minor"])
    def report(s, cid):
        """Totals only. Below the report minimum the counts are withheld, so no single shop or person can be picked out."""
        c, ev = s._all()[cid], s._valid(cid)
        imp, clk = sum(e["type"] == "ad.impression" for e in ev), sum(e["type"] == "ad.click" for e in ev)
        if imp < REPORT_MIN:
            return {"impressions": None, "clicks": None, "ctr": None, "spend_minor": s._cost(c, ev), "note": f"fewer than {REPORT_MIN}"}
        return {"impressions": imp, "clicks": clk if clk >= REPORT_MIN else None, "ctr": round(clk / imp, 3) if clk >= REPORT_MIN else None,
                "spend_minor": s._cost(c, ev)}
    def settle(s, cid):
        c, ev = s._all()[cid], s._valid(cid)
        done = sum(e["payload"]["spend_minor"] for e in s.c.store.of(COMPANY, "ad.settled") if e["payload"]["campaign_id"] == cid)
        due = s._cost(c, ev) - done
        bill = [e for e in ev if e["type"] == BILLABLE[c["model"]]]
        if due <= 0 or not bill:
            return {"settled_minor": 0}
        per, extra = divmod(due, len(bill)); shares, company = {}, {}
        for i, e in enumerate(bill):
            amt = per + (extra if i == 0 else 0)
            cut = amt * SHARE_BPS.get(e["payload"]["surface"], 0) // 10000
            shares[e["merchant"]] = shares.get(e["merchant"], 0) + cut
            cc = s.c.profile(e["merchant"])["country"]; company[cc] = company.get(cc, 0) + amt - cut
        for m, cut in shares.items():
            if cut:
                s.c.store.append(m, "server", "ad.share.earned", {"campaign_id": cid, "amount_minor": cut, "currency": c["currency"]})
        for cc, amt in company.items():
            s.control.record_revenue(c["advertiser"], "advertising", amt, c["currency"], cc)
        s.c.store.append(COMPANY, "server", "ad.settled", {"campaign_id": cid, "spend_minor": due})
        return {"settled_minor": due, "merchant_shares_minor": sum(shares.values())}
