"""Subscription families, bundles and billing rules (blueprint section 14).
Rules: one subscription per product per account; the highest tier wins and tiers never stack; a bundle (LynkSuite, LynkOps)
replaces its member products at the matching tier; a product held above a bundle's tier is billed only for the difference;
LynkSuite also replaces LynkOps; add-on families are never inside LynkSuite; subscriptions never discount transaction fees;
a subscriber is counted once per paid subscription.
Prices are standard USD and LOCKED (version 3, 2026-11-08; pinned by tests/test_price_lock.py). They are not market-tested, so
adjust them later on purpose, together with the blueprint and finance/revenue_model.py. Regional price index comes from the country pack."""
from core.money import to_minor
from core.regions import country
from services.control import COMPANY

MT = ("free", "plus", "pro", "max")
# id: full name, short name, tiers, standard USD price per tier, kind, inside LynkSuite?
FAMILIES = {
 "lynkpos":      ("LynkOmni Point of Sale", "LynkPOS", MT, (0, 12, 29, 79), "merchant", True),
 "lynkacc":      ("LynkOmni Accounting", "LynkAcc", MT, (0, 6, 15, 40), "merchant", True),       # took over LynkLedger (2026-11-07)
 "lynkinv":      ("LynkOmni Invoicing", "LynkInv", MT, (0, 5, 12, 32), "merchant", True),        # moved out of LynkCheckout (2026-11-07)
 "lynkcrm":      ("LynkOmni CRM", "LynkCRM", MT, (0, 6, 15, 40), "merchant", True),
 "lynkstock":    ("LynkOmni Inventory and Reordering", "LynkStock", MT, (0, 3, 9, 22), "merchant", True),
 "lynkrewards":  ("LynkOmni Loyalty", "LynkRewards", MT, (0, 3, 9, 22), "merchant", True),
 "lynkstat":     ("LynkOmni Analytics", "LynkStat", MT, (0, 12, 29, 79), "merchant", True),      # took over LynkDash (2026-11-08)
 "lynkgrow":     ("LynkOmni Growth Engine", "LynkGrow", MT, (0, 4, 12, 32), "merchant", True),
 "lynkchat":     ("LynkOmni Chat", "LynkChat", MT, (0, 4, 11, 27), "merchant", True),
 "lynkmpay":     ("LynkOmni Merchant Payments", "LynkMPay", MT, (0, 5, 15, 38), "merchant", False),
 "lynkrecover":  ("LynkOmni Payment Failure Recovery", "LynkRecover", MT, (0, 3, 7, 12), "merchant", False),
 "lynkcheckout": ("LynkOmni Pay-by-Link and QR", "LynkCheckout", MT, (0, 3, 7, 15), "merchant", False),
 "lynkassist":   ("LynkOmni Assistant", "LynkAssist", MT, (0, 6, 15, 35), "merchant", False),
 "lynkvcard":    ("LynkOmni Virtual Card", "LynkVCard", MT, (0, 4, 12, 30), "merchant", False),   # add-on family, never inside LynkSuite
 "lynkdev":      ("LynkOmni Developer Infrastructure", "LynkDev", ("free", "starter", "business", "enterprise"), (0, 500, 2500, 15000), "developer", False),
 "lynkbooking":  ("LynkOmni Bookings Membership", "LynkBooking", MT, (0, 4.99, 9.99, 19.99), "consumer", False),
 "lynkessential": ("LynkOmni Essentials Membership", "LynkEssential", MT, (0, 2.99, 5.99, 11.99), "consumer", False),
 "lynkops":      ("LynkOmni Operations", "LynkOps", MT, (0, 20, 49, 129), "bundle", True),       # a tier: LynkAcc, LynkInv, LynkCRM and LynkStat together
 "lynksuite":    ("LynkOmni Suite", "LynkSuite", MT, (0, 29, 75, 195), "suite", False),
}
BUNDLE_KINDS = ("bundle", "suite")
OPS_MEMBERS = ["lynkacc", "lynkinv", "lynkcrm", "lynkstat"]          # the four services inside LynkOps (LynkStat joined 2026-11-08)
SUITE_MEMBERS = [k for k, v in FAMILIES.items() if v[5] and v[4] not in BUNDLE_KINDS]   # the nine products inside LynkSuite
BUNDLES = {"lynkops": OPS_MEMBERS, "lynksuite": SUITE_MEMBERS + ["lynkops"]}             # LynkSuite also replaces LynkOps
# A tier of one product that includes a tier of another (never billed twice): LynkPOS Pro and Max include LynkRewards Plus and Pro.
INCLUDES = {("lynkpos", "pro"): {"lynkrewards": "plus"}, ("lynkpos", "max"): {"lynkrewards": "pro"}}


def bundle_price(bundle, tier):
    """What a bundle's members cost at this tier when bought separately (LynkOps counted at its own price inside LynkSuite)."""
    i = MT.index(tier)
    members = [m for m in BUNDLES[bundle] if not (bundle == "lynksuite" and m in OPS_MEMBERS)]
    return sum(FAMILIES[m][3][i] for m in members)
# What each tier adds. Higher tiers include everything below. None means unlimited.
FEATURES = {
 "lynkpos": [dict(devices=1, users=1, products=100, history_months=3, ads=True, sales_per_month=None, agent_services=True, agent_partners=1, outlets=1,
                  receipts=("print", "qr"), customer_credit="view", daily_close="screen", stock_at_till="counts", staff="owner", rewards_included=None, pickup_orders=False),
             dict(devices=2, users=3, products=None, history_months=24, ads=False, agent_partners=3, receipts=("print", "qr", "message"), customer_credit="full",
                  daily_close="nightly_summary", staff="shifts_cash_counts"),
             dict(devices=5, users=10, branches=3, history_months=None, discount_rules=True, staff_cash_controls=True, agent_partners=None, outlets=3,
                  stock_at_till="barcodes_variants_alerts", staff="tracking", rewards_included="plus", pickup_orders=True, staff_commissions=True),
             dict(devices=None, users=None, branches=None, outlets=None, custom_roles=True, api=True, custom_domain=True, several_businesses=True,
                  rewards_included="pro", payroll_lite=True, custom_receipts=True, dedicated_manager=True)],   # seat price and hardware are PLACEHOLDERS
 "lynkacc": [dict(users=1, daily_profit=True, monthly_profit=True, cash_and_mobile_money=True, accountant_access="view", audit_fee_cents=250),
             dict(users=3, full_books=True, tax_estimate=True, bank_accounts=True, statement_import=True, weekly_report=True, accountant_access="full"),
             dict(users=10, multi_branch_totals=True, credit_ledger=True, collections=True, full_statements=True, journal=True, tax_presets=True, several_currencies=True, audit_fee_cents=150),
             dict(users=None, exports=True, integrations=True, consolidation=True, payroll_lite=True, api=True, audit_fee_cents=0)],   # LynkAudit exports; included at Max
 "lynkinv": [dict(powered_by="required", users=1, invoices_per_month=5, invoice_branding="lynkomni", invoice_series=1, quotes=True, credit_notes=True, pay_link=True,
                  sending=("link", "qr", "email"), auto_reminders=False, partial_payments=False, recurring_invoices=False),
             dict(powered_by="removable", users=3, invoices_per_month=None, invoice_branding="logo", sending=("link", "qr", "email", "chat", "message"), auto_reminders=True),
             dict(users=10, invoice_branding="full", invoice_series=3, recurring=True, recurring_invoices=True, partial_payments=True, deposits=True),
             dict(users=None, invoice_series=None, customer_portal=True, custom_domain=True, invoice_api=True)],   # limits are PLACEHOLDERS; credit notes and a pay link at every tier
 "lynkcrm": [dict(users=1, customers=50, timeline=True, notes=True),
             dict(users=3, customers=500, follow_ups=True, reminders=True, groups=True, consented_messages=True),
             dict(users=10, customers=None, leads=True, pipeline=True, tasks=True, roles=("owner", "accountant", "sales", "viewer")),
             dict(users=None, pipelines=None, staff_sales=True, api=True)],
 "lynkstock": [dict(products=100), dict(products=None, low_stock_alerts=True, supplier_comparison=True), dict(reorder_drafts=True, batch_expiry=True, multi_location=True), dict(auto_reorder=True, forecasting=True)],
 "lynkrewards": [dict(members=50, points=True), dict(members=500), dict(members=5000, coupons=True, referrals=True), dict(members=None, brand_offers=True, segments=True)],
 "lynkstat": [dict(businesses=1, viewers=1, imported_records_per_month=1000, outside_sources=1, history_months=3, today_view=True, daily_close=True, score=True, exports=True,
                   analytics=("business_basics",), reports=("daily_summary",), forecasts=False),
              dict(viewers=3, imported_records_per_month=25000, outside_sources=3, history_months=24, analytics=("business", "customers"), score_details=True,
                   reports=("daily_summary", "daily_alert", "weekly"), simple_alerts=True, full_reports=True, setup_fee_cents=9900),
              dict(businesses=3, viewers=10, imported_records_per_month=250000, outside_sources=10, history_months=60, multi_branch=True, team_comparison=True,
                   analytics=("business", "customers", "products", "marketing", "money"), custom_dashboards=True, benchmark=True, sell_through=True,
                   reports=("daily_summary", "daily_alert", "weekly", "monthly", "assist_weekly_insight"), forecasts=True),
              dict(businesses=None, viewers=None, imported_records_per_month=1000000, outside_sources=None, history_months=None, predictions=True,
                   custom_ai_reports=True, consolidation=True, white_label=True, api=True, webhooks=True, custom_reports=True, scheduled_reports=True)],   # LynkStat (took over LynkDash); LynkOmni's own data is never counted
 "lynkgrow": [dict(daily_insight=True), dict(weekly_insights=True), dict(full_intelligence=True, marketplace_tools=True, financing_access=True), dict(business_protection=True, priority_financing=True)],
 "lynkchat": [dict(seats=1, customer_messaging=True), dict(seats=1, shared_inbox=True, saved_replies=True), dict(seats=5, team_inbox=True, automation=True), dict(seats=None, api=True, priority_messaging=True)],
 "lynkmpay": [dict(providers=1, proof_packs_per_month=3, proof_fee_cents=500, split_max_legs=0, split_discount_pct=0),
              dict(providers=2, higher_limits=True, proof_packs_per_month=20, split_max_legs=2),
              dict(providers=None, auto_routing=True, fast_reconciliation=True, proof_packs_per_month=100, proof_fee_cents=400, split_max_legs=5),
              dict(custom_limits=True, dedicated_support=True, proof_packs_per_month=None, proof_fee_cents=300, split_max_legs=None, split_discount_pct=20)],   # LynkProof and LynkSplit live here; numbers are PLACEHOLDERS
 "lynkrecover": [dict(retry_prompt=True), dict(auto_retries=True), dict(rerouting=True), dict(recovery_analytics=True, priority_handling=True)],
 "lynkcheckout": [dict(powered_by="required", static_qr=True),
                  dict(powered_by="removable", payment_links=True),
                  dict(powered_by="removable", branded_links=True, recurring=True),
                  dict(powered_by="removable", api=True, custom_domain=True)],   # invoicing moved to LynkInv (2026-11-07); powered_by: the small "Powered by LynkOmni" wordmark is required on Free and removable on paid tiers (DECIDED 2026-11-06: Plus is the first tier that removes it; pinned by tests/test_brand.py)
 "lynkops": [dict(contains="free"), dict(contains="plus"), dict(contains="pro"), dict(contains="max")],   # a tier: its members carry the features
 "lynkassist": [dict(ai_questions=10), dict(ai_questions=100), dict(ai_questions=500), dict(ai_questions=None)],
 "lynkvcard": [dict(active_cards=1, new_cards_per_month=6, monthly_cap_usd=500, users=1, single_use_only=True, manual_freeze=True, card_expiry_hours=24, fx_fee_pct=1.5),
               dict(active_cards=3, new_cards_per_month=20, monthly_cap_usd=3000, users=3, single_use_only=False, team_cards=True, supplier_auto_cards=True, category_locks=True, card_expiry_hours=90 * 24, fx_fee_pct=1.0),
               dict(active_cards=15, new_cards_per_month=60, monthly_cap_usd=20000, users=10, pan_masking_roles=True, approvals=True, time_locked=True, supplier_locked=True, shift_locked=True, recurring=True, card_expiry_hours=1095 * 24, fx_fee_pct=0.5, cashback_bps=5),
               dict(active_cards=None, new_cards_per_month=500, monthly_cap_usd=100000, users=None, branch_cards=True, two_step_roles=True, physical_companion=True, founders_edition=True, custom_limits=True, fx_fee_pct=0.25, cashback_bps=10)],  # prices and limits are PLACEHOLDERS set against competitor plans
 "lynkdev": [dict(sandbox=True, api_calls_per_day=1000, bandwidth_gb=10, bandwidth_cents_per_gb=8), dict(production=True, api_calls_per_day=50000, bandwidth_gb=50, bandwidth_cents_per_gb=7),
             dict(api_calls_per_day=500000, sla=True, bandwidth_gb=250, bandwidth_cents_per_gb=6), dict(api_calls_per_day=None, custom_terms=True, bandwidth_gb=None)],   # LynkEdge bandwidth and metering live here  # call limits are PLACEHOLDERS
 "lynkbooking": [dict(standard_fees=True, ads=True), dict(ads=False, priority_support=True, price_alerts=True), dict(higher_priority_support=True, group_trips=True),
                  dict(dedicated_concierge=True, dedicated_support=True, traveler_profiles=5)],
 "lynkessential": [dict(standard_fees=True, ads=True), dict(ads=False, priority_support=True, reminders=True), dict(higher_priority_support=True, scheduled_payments=True, household_members=3),
                    dict(dedicated_support=True, household_members=8, bulk_topups=True)],
}
# Second review (owner approved 2026-11-08): limits of the 14 new services, added inside existing families. PLACEHOLDERS until
# partner contracts and the pilot set them; partner-backed parts stay off per country until the partner is live (providers.ready).
_NEW = {
 "lynkpos": [dict(tables=5, kitchen_screens=0, split_bills=True, tips=False, table_qr_ordering=False, time_clock=True, partner_deliveries_per_month=20, own_riders=0, delivery_routing=False),
             dict(tables=20, kitchen_screens=1, tips=True, partner_deliveries_per_month=None, own_riders=1),
             dict(tables=None, kitchen_screens=3, table_qr_ordering=True, own_riders=5, delivery_routing=True),
             dict(central_menu=True, kitchen_screens=None, own_riders=None)],
 "lynkcheckout": [dict(partner_deliveries_per_month=20, own_riders=0, delivery_routing=False), dict(partner_deliveries_per_month=None, own_riders=1),
                  dict(own_riders=5, delivery_routing=True), dict(own_riders=None)],
 "lynkacc": [dict(payroll="time_clock", payroll_staff_included=0, tax_summary=True, tax_return_prepared=False, tax_filing=False),
             dict(payroll="lite", payroll_staff_included=3, payroll_payouts=True, tax_return_prepared=True),
             dict(payroll="full", payroll_staff_included=10, payroll_extra_staff_cents=100, tax_filing=True, tax_filing_fee_cents=500),
             dict(payroll_staff_included=50, tax_filing_fee_cents=0)],
 "lynkinv": [dict(standing_payments=0, quote_accept_tap=True, esignatures_per_month=0, get_paid_early=False),
             dict(esignatures_per_month=10, esignature_extra_cents=20, get_paid_early=True),
             dict(standing_payments=100, esignatures_per_month=50),
             dict(standing_payments=None, esignatures_per_month=250)],
 "lynkcrm": [dict(warranties=True, returns="till", repair_tickets=0, extended_warranty_offer=False),
             dict(returns="full", repair_tickets=20), dict(repair_tickets=None, extended_warranty_offer=True), dict(service_centre=True)],
 "lynkgrow": [dict(verified_reviews=True, review_replies=False, review_requests=False, promoted_listings=False),
              dict(review_replies=True, review_requests=True, promoted_listings=True, promoted_listing_from_cents=1000), dict(), dict(promoted_all_outlets=True)],
 "lynkstock": [dict(buy_together_join=True, buy_together_start=False), dict(), dict(buy_together_start=True), dict(buy_together_branches=True)],
}
for _f, _tiers in _NEW.items():
    for _i, _d in enumerate(_tiers):
        for _k, _v in _d.items():
            FEATURES[_f][_i].setdefault(_k, _v)
# Fees that are not tier limits (second review; assumptions until contracts): shares are paid by partners, never by merchants.
SERVICE_FEES = {
    "standing_payment_share_bps": 30, "get_paid_early_referral_bps": 50, "delivery_share_cents": 10, "extended_warranty_referral_cents": 100,
    "lease_margin_cents_per_month": 100, "registration_referral_cents": 500, "academy_certificate_cents": 1000,
    "lynkstat_setup_cents": 9900,      # LynkOps Setup includes it, so it is never charged twice
}

# Support level per tier (review P3, 2026-11-07): every family's Free is help center and chat, Plus priority, Pro higher
# priority and Max a dedicated manager. A business with several plans gets its highest level; LynkSuite and LynkOps
# give their members' levels through the bundle.
SUPPORT_LEVELS = ("help", "priority", "higher", "dedicated")
for _tiers in FEATURES.values():
    for _i, _d in enumerate(_tiers):
        _d.setdefault("support", SUPPORT_LEVELS[min(_i, len(SUPPORT_LEVELS) - 1)])
ADS_PRODUCT = {"pos": "lynkpos", "dash": "lynkstat", "stock": "lynkstock"}

class Billing:
    def __init__(s, c, control=None): s.c, s.control = c, control
    def set_plan(s, account, family, tier):
        if family not in FAMILIES or tier not in FAMILIES[family][2]:
            raise ValueError(f"{tier} is not a plan of {family}")
        s.c.store.append(account, "server", "subscription.set", {"family": family, "tier": tier})
    def cancel(s, account, family): s.set_plan(account, family, "free")
    def _held(s, account):
        h = {}
        for e in s.c.store.of(account, "subscription.set"):
            h[e["payload"]["family"]] = e["payload"]["tier"]
        return h
    def _idx(s, family, tier): return FAMILIES[family][2].index(tier)
    def _usd(s, family, tier): return FAMILIES[family][3][s._idx(family, tier)]
    def _covered(s, held, fam):
        """The tier of `fam` that bundles and inclusions already provide, from what the account holds."""
        best = "free"
        for b, members in BUNDLES.items():
            t = held.get(b, "free")
            if fam in members and s._idx(fam, t) > s._idx(fam, best):
                best = t
        if fam in OPS_MEMBERS:                                               # LynkSuite replaces LynkOps, so it covers LynkOps' members
            t = held.get("lynksuite", "free")
            if s._idx(fam, t) > s._idx(fam, best):
                best = t
        for (src, src_tier), gives in INCLUDES.items():
            if fam in gives:
                have = max(held.get(src, "free"), held.get("lynksuite", "free") if src in SUITE_MEMBERS else "free", key=lambda t: s._idx(src, t))
                if s._idx(src, have) >= s._idx(src, src_tier) and s._idx(fam, gives[fam]) > s._idx(fam, best):
                    best = gives[fam]
        return best
    def effective(s, account):
        """The highest of the product's own tier and the tier a bundle or inclusion provides. Tiers never stack."""
        held, out = s._held(account), {}
        for fam, v in FAMILIES.items():
            if v[4] in BUNDLE_KINDS:
                continue
            own, via = held.get(fam, "free"), s._covered(held, fam)
            top = own if s._idx(fam, own) > s._idx(fam, via) else via
            out[fam] = {"tier": top, "source": "bundle" if (via != "free" and s._idx(fam, via) >= s._idx(fam, own)) else "standalone"}
        return out
    def tier(s, account, family): return s.effective(account)[family]["tier"]
    def entitlement(s, account, family):
        ent = {}
        for d in FEATURES[family][: s._idx(family, s.tier(account, family)) + 1]:
            ent.update(d)
        return ent
    def support_level(s, account):
        """The highest support level across every plan the account has (help, priority, higher, dedicated)."""
        return max((s.entitlement(account, f)["support"] for f, v in FAMILIES.items() if v[4] not in BUNDLE_KINDS), key=SUPPORT_LEVELS.index)
    def ads_enabled(s, account, product):  # ads show only while the surface's product is on its Free tier
        return s.tier(account, ADS_PRODUCT[product]) == "free"
    def _money(s, account, family, usd):
        pr = s.c.profile(account); idx = 1 if FAMILIES[family][4] == "developer" else country(pr["country"]).get("price_index", 1.0)
        return s.c.fx.convert(to_minor(usd * idx, "USD"), "USD", pr["currency"])
    def bill(s, account):
        held, lines, credits = s._held(account), [], []
        st = held.get("lynksuite", "free")
        if st != "free":
            lines.append({"family": "lynksuite", "tier": st, "amount_minor": s._money(account, "lynksuite", s._usd("lynksuite", st))})
        for fam in FAMILIES:
            own = held.get(fam, "free")
            if fam == "lynksuite" or own == "free":
                continue
            covered = st if fam == "lynkops" else s._covered(held, fam)
            if s._idx(fam, own) > s._idx(fam, covered):  # only the difference above what a bundle or inclusion already provides
                lines.append({"family": fam, "tier": own, "amount_minor": s._money(account, fam, s._usd(fam, own) - s._usd(fam, covered))})
            else:
                credits.append(fam)
        return {"currency": s.c.profile(account)["currency"], "lines": lines, "credited": credits, "total_minor": sum(l["amount_minor"] for l in lines)}
    def invoice(s, account, period):
        """One invoice per account per period. Revenue is recorded once per paid line, by family."""
        if any(e["payload"]["period"] == period for e in s.c.store.of(account, "billing.invoiced")):
            return {"status": "already_invoiced", "period": period}
        b, pr = s.bill(account), s.c.profile(account)
        s.c.store.append(account, "server", "billing.invoiced", {"period": period, "total_minor": b["total_minor"], "currency": b["currency"]})
        if s.control:
            for l in b["lines"]:
                s.control.record_revenue(account, f"subscription:{l['family']}", l["amount_minor"], b["currency"], pr["country"])
        return {"status": "invoiced", "period": period, **b}
    def counts(s):
        """Paid subscribers per family and tier. Each is counted once; LynkSuite Free and Free tiers are not paid."""
        out = {}
        for acct in {e["merchant"] for e in s.c.store.all_of("subscription.set")}:
            for l in s.bill(acct)["lines"]:
                out.setdefault(l["family"], {}).setdefault(l["tier"], 0)
                out[l["family"]][l["tier"]] += 1
        return out
