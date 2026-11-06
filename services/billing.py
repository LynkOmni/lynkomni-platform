"""Subscription families, LynkSuite and billing rules (blueprint section 14).
Rules: one subscription per product per account; the highest tier wins and tiers never stack; LynkSuite replaces its seven
products at the matching tier; a product held above the Suite tier is billed only for the difference; add-on families are never
inside LynkSuite; subscriptions never discount transaction fees; a subscriber is counted once per paid subscription.
Prices are standard USD and LOCKED (version 1, 2026-11-06; pinned by tests/test_price_lock.py). They are not market-tested, so adjust them later on purpose, together with the blueprint and finance/revenue_model.py. Regional price index comes from the country pack."""
from core.money import to_minor
from core.regions import country
from services.control import COMPANY

MT = ("free", "plus", "pro", "max")
# id: full name, short name, tiers, standard USD price per tier, kind, inside LynkSuite?
FAMILIES = {
 "lynkpos":      ("LynkOmni Point of Sale", "LynkPOS", MT, (0, 4, 14, 35), "merchant", True),
 "lynkledger":   ("LynkOmni Accountant", "LynkLedger", MT, (0, 3, 9, 22), "merchant", True),
 "lynkstock":    ("LynkOmni Inventory and Reordering", "LynkStock", MT, (0, 3, 9, 22), "merchant", True),
 "lynkrewards":  ("LynkOmni Loyalty", "LynkRewards", MT, (0, 3, 9, 22), "merchant", True),
 "lynkdash":     ("LynkOmni Dashboard", "LynkDash", MT, (0, 3, 7, 17), "merchant", True),
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
 "lynksuite":    ("LynkOmni Suite", "LynkSuite", MT, (0, 17, 49, 125), "suite", False),
}
SUITE_MEMBERS = [k for k, v in FAMILIES.items() if v[5]]            # the seven products inside LynkSuite
# What each tier adds. Higher tiers include everything below. None means unlimited.
FEATURES = {
 "lynkpos": [dict(devices=1, users=1, products=100, history_months=3, ads=True), dict(devices=2, users=3, products=None, history_months=24, ads=False),
             dict(devices=5, users=10, branches=3, discount_rules=True, staff_cash_controls=True), dict(devices=None, users=None, branches=10, custom_roles=True, api=True)],
 "lynkledger": [dict(daily_profit=True, audit_fee_cents=250), dict(full_books=True, tax_estimate=True), dict(multi_branch_totals=True, credit_ledger=True, collections=True, audit_fee_cents=150), dict(exports=True, integrations=True, accountant_access=True, audit_fee_cents=0)],   # LynkAudit exports; included at Max
 "lynkstock": [dict(products=100), dict(products=None, low_stock_alerts=True, supplier_comparison=True), dict(reorder_drafts=True, batch_expiry=True, multi_location=True), dict(auto_reorder=True, forecasting=True)],
 "lynkrewards": [dict(members=50, points=True), dict(members=500), dict(members=5000, coupons=True, referrals=True), dict(members=None, brand_offers=True, segments=True)],
 "lynkdash": [dict(today_view=True), dict(full_reports=True), dict(multi_branch=True), dict(custom_reports=True, exports=True)],
 "lynkgrow": [dict(daily_insight=True), dict(weekly_insights=True), dict(full_intelligence=True, marketplace_tools=True, financing_access=True), dict(business_protection=True, priority_financing=True)],
 "lynkchat": [dict(seats=1, customer_messaging=True), dict(seats=1, shared_inbox=True, saved_replies=True), dict(seats=5, team_inbox=True, automation=True), dict(seats=None, api=True, priority_messaging=True)],
 "lynkmpay": [dict(providers=1, proof_packs_per_month=3, proof_fee_cents=500, split_max_legs=0, split_discount_pct=0),
              dict(providers=2, higher_limits=True, proof_packs_per_month=20, split_max_legs=2),
              dict(providers=None, auto_routing=True, fast_reconciliation=True, proof_packs_per_month=100, proof_fee_cents=400, split_max_legs=5),
              dict(custom_limits=True, dedicated_support=True, proof_packs_per_month=None, proof_fee_cents=300, split_max_legs=None, split_discount_pct=20)],   # LynkProof and LynkSplit live here; numbers are PLACEHOLDERS
 "lynkrecover": [dict(retry_prompt=True), dict(auto_retries=True), dict(rerouting=True), dict(recovery_analytics=True, priority_handling=True)],
 "lynkcheckout": [dict(powered_by="required", static_qr=True, invoices_per_month=3, invoice_branding="lynkomni", invoice_series=1, auto_reminders=False, credit_notes=False, partial_payments=False, recurring_invoices=False),
                  dict(powered_by="removable", payment_links=True, invoices_per_month=20, invoice_branding="logo", credit_notes=True),
                  dict(powered_by="removable", branded_links=True, invoices=True, recurring=True, invoices_per_month=200, invoice_branding="full", invoice_series=3, auto_reminders=True, partial_payments=True, recurring_invoices=True),
                  dict(powered_by="removable", api=True, custom_domain=True, invoices_per_month=None, invoice_series=None, invoice_api=True)],   # invoice limits are PLACEHOLDERS; powered_by: the small "Powered by LynkOmni" wordmark is required on Free and removable on paid tiers (DECIDED 2026-11-06: Plus is the first tier that removes it; pinned by tests/test_brand.py)
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
ADS_PRODUCT = {"pos": "lynkpos", "dash": "lynkdash", "stock": "lynkstock"}

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
    def effective(s, account):
        """The highest of the product's own tier and the tier LynkSuite provides. Tiers never stack."""
        held, suite, out = s._held(account), s._held(account).get("lynksuite", "free"), {}
        for fam, v in FAMILIES.items():
            if fam == "lynksuite":
                continue
            own, via = held.get(fam, "free"), (suite if v[5] else "free")
            top = own if s._idx(fam, own) > s._idx(fam, via) else via
            out[fam] = {"tier": top, "source": "suite" if (v[5] and via != "free" and s._idx(fam, via) >= s._idx(fam, own)) else "standalone"}
        return out
    def tier(s, account, family): return s.effective(account)[family]["tier"]
    def entitlement(s, account, family):
        ent = {}
        for d in FEATURES[family][: s._idx(family, s.tier(account, family)) + 1]:
            ent.update(d)
        return ent
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
        for fam, (_, _, tiers, _, _, inside) in FAMILIES.items():
            own = held.get(fam, "free")
            if fam == "lynksuite" or own == "free":
                continue
            covered = st if inside else "free"
            if s._idx(fam, own) > s._idx(fam, covered):  # only the difference above what LynkSuite already provides
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
