"""Advertising structure. Contextual (never personal) targeting, always labeled, capped, and never inside critical flows.
Off per country until legal and policy sign-off. Offline: devices cache a bundle and their impressions sync later."""
import textwrap, time, uuid
from core.locale import t
from core.regions import country
from services.control import COMPANY

SURFACES = {"receipt_footer", "pos_idle", "pos_after_sale", "dashboard_card", "reorder_promoted",
            "services_promoted", "loyalty_offer", "discover_listing"}
BLOCKED_SCREENS = {"payment", "checkout", "cash_count", "void", "refund", "fiscal_receipt_body", "chat_thread"}
BASELINE_BLOCKED = {"gambling", "adult", "tobacco", "weapons", "political"}      # never accepted anywhere
REGULATED = {"lending", "insurance", "crypto", "investment"}                       # need a licensed advertiser per country
SHARE_BPS = {"receipt_footer": 4000, "pos_idle": 3000, "pos_after_sale": 3000}     # merchant share of ad income: PLACEHOLDERS
DAILY_CAP = 5                                                                      # per merchant, per campaign, per day
BILLABLE = {"cpm": "ad.impression", "cpc": "ad.click", "cpa": "ad.conversion"}
def _id(): return uuid.uuid4().hex

class Ads:
    billing = None   # set by the platform: ads show on a product surface only while that product is on its Free tier
    SURFACE_PRODUCT = {"receipt_footer": "pos", "pos_idle": "pos", "pos_after_sale": "pos", "dashboard_card": "dash", "reorder_promoted": "stock"}
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
        blocked = BASELINE_BLOCKED | {x for k in c["countries"] for x in country(k).get("blocked_ad_categories", ())}
        if c["category"] in blocked:
            reason = "category not allowed"
        elif c["category"] in REGULATED and not set(c["countries"]) <= set(c["licensed_in"]):
            reason = "regulated category: advertiser must be licensed in every target country"
        s.c.store.append(COMPANY, reviewer, "ad.reviewed", {"id": cid, "approved": reason is None, "reason": reason})
        return {"approved": reason is None, "reason": reason}
    def _all(s): return {e["payload"]["id"]: e["payload"] for e in s.c.store.of(COMPANY, "ad.campaign")}
    def _active(s):
        ok = {e["payload"]["id"]: e["payload"]["approved"] for e in s.c.store.of(COMPANY, "ad.reviewed")}
        return {k: v for k, v in s._all().items() if ok.get(k)}
    # merchant controls
    def set_ad_free(s, m, on=True): s.c.store.append(m, "server", "ad.plan", {"ad_free": on})
    def ad_free(s, m):
        e = s.c.store.of(m, "ad.plan"); return bool(e and e[-1]["payload"]["ad_free"])
    def opt_out(s, m, category): s.c.store.append(m, "server", "ad.optout", {"category": category})
    # serving
    def select(s, m, surface, screen=None, lang="en", context=None, merchant_type=None, today=None):
        if surface not in SURFACES:
            raise ValueError(f"unknown ad surface {surface}")
        if screen in BLOCKED_SCREENS:
            return None  # never inside payments, voids, cash counts, refunds, fiscal data or private chats
        s.c.gate(m, "ads")
        pr, today = s.c.profile(m), today or time.strftime("%Y-%m-%d")
        if s.ad_free(m):
            return None
        prod = s.SURFACE_PRODUCT.get(surface)
        if prod and s.billing and not s.billing.ads_enabled(m, prod):
            return None
        out, best = {e["payload"]["category"] for e in s.c.store.of(m, "ad.optout")}, None
        for cid, c in s._active().items():
            if pr["country"] not in c["countries"] or surface not in c["surfaces"] or c["category"] in out:
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
            if best is None or c["price_minor"] > best["price_minor"]:
                best = c
        if best is None:
            return None
        return {"campaign_id": best["id"], "surface": surface, "label": t(lang, "sponsored"), "text": best["creative"].get(lang) or best["creative"]["en"]}
    def bundle(s, m, surfaces, lang="en", **kw):
        """Ads a device caches so it can show them offline. Each may be shown at most DAILY_CAP times a day."""
        return [a for sf in surfaces if (a := s.select(m, sf, lang=lang, **kw))]
    def impression(s, m, device, cid, surface): s.c.store.append(m, device, "ad.impression", {"campaign_id": cid, "surface": surface})
    def click(s, m, device, cid, surface): s.c.store.append(m, device, "ad.click", {"campaign_id": cid, "surface": surface})
    def conversion(s, m, cid, surface): s.c.store.append(m, "server", "ad.conversion", {"campaign_id": cid, "surface": surface})
    def receipt_footer(s, m, lang="en", **kw):
        """The labeled ad for a receipt, or None. Pass it to receipt_text(ad=...); it prints last and never on a fiscal document."""
        return s.select(m, "receipt_footer", screen="receipt", lang=lang, **kw)
    # measurement and money
    def _valid(s, cid):
        seen, imp_merchants, out = {}, set(), []
        for e in s.c.store.all_of("ad.impression", "ad.click", "ad.conversion"):
            if e["payload"]["campaign_id"] != cid:
                continue
            if e["type"] == "ad.impression":
                k = (e["merchant"], e["ts"][:10]); seen[k] = seen.get(k, 0) + 1
                if seen[k] > DAILY_CAP:
                    continue  # beyond the cap: not billable
                imp_merchants.add(e["merchant"])
            elif e["merchant"] not in imp_merchants:
                continue      # a click or conversion with no valid impression is not billable
            out.append(e)
        return out
    @staticmethod
    def _cost(c, ev):
        n = sum(1 for e in ev if e["type"] == BILLABLE[c["model"]])
        return min(n * c["price_minor"] // (1000 if c["model"] == "cpm" else 1), c["budget_minor"])
    def report(s, cid):
        c, ev = s._all()[cid], s._valid(cid)
        imp, clk = sum(e["type"] == "ad.impression" for e in ev), sum(e["type"] == "ad.click" for e in ev)
        return {"impressions": imp, "clicks": clk, "ctr": round(clk / imp, 3) if imp else None, "spend_minor": s._cost(c, ev)}  # aggregates only
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
