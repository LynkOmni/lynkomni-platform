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
 "lynkmotion":   ("LynkOmni Motion", "LynkMotion", MT, (0, 9, 29, 79), "movement", False),    # NEW UPDATE 1 (2026-11-10): everyday tracking (LynkTrace, LynkGPS, LynkSentry)
 "lynkguard":    ("LynkOmni Guard", "LynkGuard", MT, (0, 15, 49, 149), "movement", False),    # NEW UPDATE 1 (2026-11-10): vehicle and asset protection on the same core
 "lynkattend":   ("LynkOmni Attendance", "LynkAttend", MT, (0, 49.5, 95, 179), "people", False),   # NEW UPDATE 4 (LynkA, 2026-11-11)
 "lynkqueue":    ("LynkOmni Queue", "LynkQueue", MT, (0, 55, 115, 249), "people", False),           # NEW UPDATE 4 (LynkQ, 2026-11-11)
 "lynksurvey":   ("LynkOmni Survey", "LynkSurvey", MT, (0, 59, 155, 249), "people", False),         # NEW UPDATE 4 (LynkS, 2026-11-11)
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
 "lynkassist": [dict(ai_questions=10, custom_automations=0, drafts=True, explain=True, weekly_insight=False, automation_builder=False),
                dict(ai_questions=100, custom_automations=3, weekly_insight=True),
                dict(ai_questions=500, custom_automations=20, automation_builder=True, chat_suggested_replies=True),
                dict(ai_questions=None, custom_automations=None, custom_ai_reports=True)],   # LynkAssist everywhere (blueprint 45); built-in automations come with each family
 # LynkVCard (MASTER UPDATE section 61): one plan covers the prepaid, debit and credit groups; card counts and the monthly cap are
 # shared across the groups; credit_kinds are what a lender may offer on that tier (the lender alone decides); physical debit and
 # credit cards are on demand at the issuer's fee on HUB and CORE and included on OMNI; EDGE stays virtual. Placeholders until a contract.
 "lynkvcard": [dict(card_groups=("prepaid", "debit", "credit"), credit_kinds=("secured",), physical_groups=(), single_use_group="prepaid", active_cards=1, new_cards_per_month=6, monthly_cap_usd=500, users=1, single_use_only=True, manual_freeze=True, card_expiry_hours=24, fx_fee_pct=1.5),
               dict(card_groups=("prepaid", "debit", "credit"), credit_kinds=("secured", "charge"), physical_groups=("debit", "credit"), physical_included=False, active_cards=3, new_cards_per_month=20, monthly_cap_usd=3000, users=3, single_use_only=False, team_cards=True, supplier_auto_cards=True, category_locks=True, card_expiry_hours=90 * 24, fx_fee_pct=1.0),
               dict(card_groups=("prepaid", "debit", "credit"), credit_kinds=("secured", "charge", "credit"), physical_groups=("debit", "credit"), physical_included=False, active_cards=15, new_cards_per_month=60, monthly_cap_usd=20000, users=10, pan_masking_roles=True, approvals=True, time_locked=True, supplier_locked=True, shift_locked=True, recurring=True, card_expiry_hours=1095 * 24, fx_fee_pct=0.5, cashback_bps=5),
               dict(card_groups=("prepaid", "debit", "credit"), credit_kinds=("secured", "charge", "credit"), physical_groups=("prepaid", "debit", "credit"), physical_included=True, active_cards=None, new_cards_per_month=500, monthly_cap_usd=100000, users=None, branch_cards=True, two_step_roles=True, physical_companion=True, founders_edition=True, custom_limits=True, fx_fee_pct=0.25, cashback_bps=10)],  # prices and limits are PLACEHOLDERS set against competitor plans
 "lynkdev": [dict(sandbox=True, api_calls_per_day=1000, bandwidth_gb=10, bandwidth_cents_per_gb=8), dict(production=True, api_calls_per_day=50000, bandwidth_gb=50, bandwidth_cents_per_gb=7),
             dict(api_calls_per_day=500000, sla=True, bandwidth_gb=250, bandwidth_cents_per_gb=6), dict(api_calls_per_day=None, custom_terms=True, bandwidth_gb=None)],   # LynkEdge bandwidth and metering live here  # call limits are PLACEHOLDERS
 # NEW UPDATE 1 (owner approved 2026-11-10, blueprint section 49): two plans on one core, each covering LynkTrace, LynkGPS and
 # LynkSentry. Phones are the tracker; hardware, SIM data, monitoring and satellite airtime are charged only when chosen.
 "lynkmotion": [dict(tracked_per_month=50, live=2, history_days=7, places=2, drivers=2, offline_regions=0, branded_page=False, proof=("code",),
                     receiver_choices=False, route_stops_per_day=0, partner_carriers=False, multi_leg=False, multimodal=False, api=False,
                     sos=True, safe_arrival=True, trip_plan=True, unknown_tracker_alerts=True, store_and_forward=True, mesh_relay=True, text_tracking=True),
                dict(tracked_per_month=1000, live=10, history_days=30, places=25, drivers=5, offline_regions=1, branded_page=True,
                     proof=("code", "photo", "signature"), receiver_choices=True, route_stops_per_day=25, rider_checkins=True, hidden_numbers=True),
                dict(tracked_per_month=10000, live=50, history_days=365, places=250, drivers=50, offline_regions=5, proof_chain=True,
                     route_stops_per_day=300, dispatch_board=True, partner_carriers=True, multi_leg=True, api=True, webhooks=True, fraud_checks=True),
                dict(tracked_per_month=100000, live=250, history_days=1095, places=None, drivers=None, offline_regions=None, route_stops_per_day=None,
                     multimodal=True, customs_documents=True, predicted_arrival=True, control_tower=True, seals_on_demand=True, insurer_pack=True,
                     ship_and_flight_data=True)],
 "lynkguard": [dict(assets=1, extra_asset_cents=None, tracker="phone", history_days=7, zones=1, crash_detection=True, sos=True, moved_without_you=True,
                    trusted_contacts=True, trip_plan=True, store_and_forward=True, mesh_relay=True, text_tracking=True, gone_silent=False, api=False),
               dict(assets=3, connected_car=True, history_days=90, zones=10, theft_and_tow_alerts=True, after_hours_alerts=True, police_report_pack=True,
                    gone_silent=True, driver_sharing=True),
               dict(assets=25, extra_asset_cents=150, trackers_on_demand=True, history_days=365, zones=100, tamper_and_jamming_alerts=True, curfews=True,
                    rental_mode=True, fleet_tools=True, driver_identity=True, driver_hours=True, safety_scores=True, incident_room=True,
                    power_cut_alerts=True, satellite_on_demand=True, api=True, webhooks=True),
               dict(assets=100, extra_asset_cents=100, seals_and_sensors=True, history_days=1095, zones=None, control_room_wall=True, cargo_custody=True,
                    safe_stop=True, monitoring_partner=True, insurer_sharing=True, ship_and_flight_data=True)],
 # NEW UPDATE 4 (owner locked 2026-11-11, blueprint section 63): LynkA, LynkQ and LynkS. Safety is never a paid extra: every tier has
 # the full check-in protections, the fair queue and one person one answer. Only active units are counted (people who checked in,
 # places that gave a ticket, creators who built or sent a survey). Pro and Max carry the ecosystem links (blueprint 63.4).
 "lynkattend": [dict(people_included=15, extra_person_cents=None, branches=1, managers=1, door_devices=2, history_months=3, shifts="basic",
                     own_hardware=False, events_at_once=1, certificates=False, links=(), api=False, several_countries=False, reports="monthly_summary",
                     sets=("face_finger_idcn", "face_idcn", "finger_idcn", "idcn"), visitors=True, fire_list=True, was_this_you=True, offline=True),
                dict(people_included=50, extra_person_cents=150, branches=3, managers=3, door_devices=None, history_months=24, shifts="full",
                     own_hardware=True, events_at_once=5, links=("lynkacc",), reports="full"),
                dict(extra_person_cents=250, branches=None, managers=10, deputy_managers=True, history_months=60, events_at_once=None, certificates=True,
                     links=("lynkacc", "lynkstat", "ecosystem"), api="read", reports="by_email"),
                dict(extra_person_cents=400, managers=None, history_months=None, links=("all",), api="full", several_countries=True, reports="custom")],
 "lynkqueue": [dict(places_included=1, extra_place_cents=None, max_places=1, tickets_per_place_month=500, sections_per_place=3, counters_per_place=3,
                    staff_accounts=3, basic_phone=False, whatsapp_and_chat=False, appointments=False, send_to=False, own_hardware=False, busy_forecast=False,
                    own_logo=False, powered_by="required", api=False, reports="daily_summary", history_months=3, several_countries=False, links=(),
                    queue_keeper=True, check_ticket=True, public_queue_page=True, running_late=True, offline=True),
               dict(places_included=5, extra_place_cents=1000, max_places=10, tickets_per_place_month=3000, sections_per_place=None, counters_per_place=15,
                    staff_accounts=15, basic_phone=True, whatsapp_and_chat=True, send_to=True, own_hardware=True, busy_forecast=True, own_logo=True,
                    powered_by="removable", reports="full", history_months=24, links=("lynkattend", "lynksurvey")),
               dict(extra_place_cents=2000, max_places=None, tickets_per_place_month=10000, counters_per_place=None, staff_accounts=None, appointments=True,
                    api="read", reports="by_email", history_months=60, links=("lynkattend", "lynksurvey", "lynkcrm", "lynkstat", "ecosystem")),
               dict(extra_place_cents=4000, tickets_per_place_month=50000, api="full", reports="custom", history_months=None, several_countries=True, links=("all",))],
 "lynksurvey": [dict(creators_included=1, extra_creator_cents=None, answers_per_month=300, live_surveys=3, places=1, org_tree=None, whatsapp_and_chat=False,
                     basic_phone=False, field_and_paper=False, voice_call=False, write_it_for_me=False, logic="basic", repeating=False, automatic=(),
                     staff_journey=False, experience_dashboards=False, library_and_brand_kit=False, approval=False, call_back=False, rewards=False,
                     panel=False, own_hardware=False, company_login=False, own_logo=False, powered_by="required", api=False,
                     research=("margins", "sample_size", "research_record"), downloads=(), reports="summary", history_months=3, several_countries=False,
                     answer_rules=("open", "one_per_phone", "invited", "verified"), anonymity_min_group=5, real_answers_check=True, verified_results=True, offline=True),
                dict(creators_included=5, extra_creator_cents=1000, answers_per_month=10000, live_surveys=None, places=10, whatsapp_and_chat=True, basic_phone=True,
                     field_and_paper=True, write_it_for_me=True, logic="full", repeating=True, automatic=("lynkpos", "lynkqueue", "lynkchat"), call_back=True,
                     rewards=True, own_hardware=True, own_logo=True, powered_by="removable",
                     research=("margins", "sample_size", "research_record", "compare_groups", "before_after", "themes_basic"), downloads=("spreadsheet", "csv"),
                     reports="full", history_months=24),
                dict(extra_creator_cents=2500, answers_per_month=50000, places=None, org_tree="branches_departments", voice_call=True, automatic=("all", "api"),
                     staff_journey=True, experience_dashboards=True, library_and_brand_kit=True, approval=True, panel=True, api="read",
                     research=("margins", "sample_size", "research_record", "compare_groups", "before_after", "themes", "real_difference", "groups_to_fill",
                               "balancing", "what_matters_most", "trade_off"), downloads=("spreadsheet", "csv", "spss", "stata", "r"), reports="by_email",
                     history_months=60),
                dict(extra_creator_cents=4000, answers_per_month=250000, org_tree="full", company_login=True, api="full", reports="custom", history_months=None,
                     several_countries=True)],
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
    # NEW UPDATE 1 (2026-11-10): LynkMotion extras. LynkGuard's extra vehicles are its tiers' extra_asset_cents.
    "motion_extra_1000_tracked_cents": 500, "motion_extra_live_cents": 100,
    # NEW UPDATE 4 (2026-11-11): extra queue tickets and survey answers above a paid tier (nobody is turned away; no survey stops).
    "queue_extra_1000_tickets_cents": 200, "survey_extra_1000_answers_cents": 100,
}
# LynkA, LynkQ and LynkS: any two or all three paid plans held together take 20% off each of them (a bundle discount, not a link;
# owner locked 2026-11-11). LOCKED with the prices.
PEOPLE_FAMILIES = ("lynkattend", "lynkqueue", "lynksurvey")
PEOPLE_BUNDLE_DISCOUNT_BPS = 2000


def people_bundle_discount_cents(tiers):
    """The monthly discount, in US cents, for an account holding two or three of LynkAttend, LynkQueue and LynkSurvey on paid tiers:
    20% of each paid plan's price. tiers maps a family to its tier; families not held are left out."""
    paid = [int(round(FAMILIES[f][3][MT.index(t)] * 100)) for f, t in tiers.items() if f in PEOPLE_FAMILIES]
    paid = [c for c in paid if c > 0]
    if len(paid) < 2:
        return 0
    return sum((c * PEOPLE_BUNDLE_DISCOUNT_BPS + 5000) // 10000 for c in paid)
# An account may hold one LynkMotion plan and one LynkGuard plan (they cover different things; each is counted once). Holding both
# takes this much off the lower paid plan (NEW UPDATE 1, owner approved 2026-11-10). LOCKED with the prices.
MOVEMENT_FAMILIES = ("lynkmotion", "lynkguard")
MOVEMENT_PAIR_DISCOUNT_BPS = 2000


def movement_pair_discount_cents(motion_tier, guard_tier):
    """The monthly discount, in US cents, for an account holding both LynkMotion and LynkGuard: 20% of the lower paid plan."""
    a = int(round(FAMILIES["lynkmotion"][3][MT.index(motion_tier)] * 100))
    b = int(round(FAMILIES["lynkguard"][3][MT.index(guard_tier)] * 100))
    if a == 0 or b == 0:
        return 0
    return (min(a, b) * MOVEMENT_PAIR_DISCOUNT_BPS + 5000) // 10000


# Open APIs for every service (NEW UPDATE 1, blueprint section 50; catalog/apis.v1.json lists each API). Usage prices in US cents,
# charged only where a service has a real running cost; LOCKED with the prices. Money services add no fee beyond their tiers.
API_PRICES = {
    "tracking_shipment_cents": 1,                 # each tracked shipment
    "geocoding_per_1000_cents": 100, "routing_per_1000_cents": 100, "routing_25_stops_per_1000_cents": 200,
    "map_tiles_per_1000_cents": 50, "offline_region_month_cents": 1000, "zone_events_per_1000_cents": 100,
    "lynkstat_queries_per_1000_cents": 100,       # above the plan
    "lynkassist_requests_per_1000_cents": 200,    # above the plan
    "translation_per_million_chars_cents": 500,
}
API_FREE_MONTHLY = {"tracked_shipments": 100, "geocoding": 10000, "routing": 10000, "map_tiles": 50000}   # on a LynkDev production plan
API_BUSINESS_DISCOUNT_BPS = 2000                  # LynkDev Business; Enterprise is by contract
API_OWN_ACCOUNT = {"pro": ("read", "webhooks"), "max": ("read", "write", "webhooks")}   # a business's own apps on its own data

# Support level per tier (review P3, 2026-11-07): every family's Free is help center and chat, Plus priority, Pro higher
# priority and Max a dedicated manager. A business with several plans gets its highest level; LynkSuite and LynkOps
# give their members' levels through the bundle.
SUPPORT_LEVELS = ("help", "priority", "higher", "dedicated")
for _tiers in FEATURES.values():
    for _i, _d in enumerate(_tiers):
        _d.setdefault("support", SUPPORT_LEVELS[min(_i, len(SUPPORT_LEVELS) - 1)])
ADS_PRODUCT = {"pos": "lynkpos", "dash": "lynkstat", "stock": "lynkstock"}

# Storefront plans (BIZZ & DEVICE, owner approved 2026-11-09): the external side of every service, where anyone offers to others
# and earns. A plan type, not a product family: one Storefront plan per account covers every service's Storefront, the
# highest plan wins and nothing is billed twice; outside LynkSuite. Workspace prices above never change. LOCKED with the
# other prices (tests/test_price_lock.py). Enterprise is by contract.
STOREFRONT_TIERS = ("free", "plus", "pro", "max", "enterprise")
STOREFRONT_PRICES = (0, 12, 29, 79)                # standard USD per month for free, plus, pro, max (the same ladder as the plans)
STOREFRONT_SHARE_BPS = (800, 500, 300, 150)        # LynkOmni's share of each Storefront sale, in basis points: 8%, 5%, 3%, 1.5%
STOREFRONT_SHARE_CAP_USD_CENTS = {"max": 5000}     # Max: the share of one sale never exceeds $50 (converted by the provider)
STOREFRONT_TRIAL_DAYS = {"plus": 14, "pro": 14}
STOREFRONT_FEATURES = [
    dict(items=3, storage_gb=1, team=1, reports="basic", powered_by="required", own_logo=False, discount_codes=False, live_seats=0, certificates=False, support="help"),
    dict(items=25, storage_gb=20, team=2, reports="full", powered_by="removable", own_logo=True, discount_codes=True, live_seats=50, certificates=True, support="priority"),
    dict(items=250, storage_gb=200, team=5, reports="buyer_insights", powered_by="removable", own_logo=True, discount_codes=True, live_seats=500, certificates=True, support="higher"),
    dict(items=None, storage_gb=1000, team=20, reports="exports", powered_by="removable", own_logo=True, discount_codes=True, live_seats=5000, certificates=True, support="dedicated"),
    dict(items=None, storage_gb="agreed", team=None, reports="custom", powered_by="removable", own_logo=True, discount_codes=True, live_seats="agreed", certificates=True, support="dedicated"),
]
STOREFRONT_RULES = (
    "The share applies only to sales made through a Storefront, never to a business's own till sales, invoices or pay links.",
    "The licensed provider takes the share at the moment of sale and pays the seller the rest; LynkOmni never holds money.",
    "Free material is never charged; there is no minimum fee; the share is refunded with a refund and held during a dispute.",
    "Before publishing and on every sale the seller sees the price, the provider's charges, the share and what they receive.",
    "Items over the limit after a downgrade are hidden, never deleted.",
)


def storefront_share(tier, sale_minor, free_item=False, cap_minor=None):
    """LynkOmni's share of one Storefront sale, in the sale's minor units (integers only, half up). cap_minor is the $50 Max
    cap already converted to the sale's currency by the provider; Enterprise shares come from its contract (None here)."""
    if tier not in STOREFRONT_TIERS:
        raise ValueError(f"{tier} is not a Storefront plan")
    if isinstance(sale_minor, bool) or not isinstance(sale_minor, int) or sale_minor < 0:
        raise ValueError("a sale is a whole number of minor units")
    if free_item or sale_minor == 0:
        return 0
    if tier == "enterprise":
        return None
    share = (sale_minor * STOREFRONT_SHARE_BPS[STOREFRONT_TIERS.index(tier)] + 5000) // 10000
    if tier in STOREFRONT_SHARE_CAP_USD_CENTS and cap_minor is not None:
        share = min(share, cap_minor)
    return share

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
        """The highest support level across every plan the account has (help, priority, higher, dedicated), the Storefront
        plan included: the channel follows the side, the priority follows the highest plan (BIZZ & DEVICE)."""
        levels = [s.entitlement(account, f)["support"] for f, v in FAMILIES.items() if v[4] not in BUNDLE_KINDS]
        levels.append(s.storefront_entitlement(account)["support"])
        return max(levels, key=SUPPORT_LEVELS.index)
    def set_storefront_plan(s, account, tier):
        """One Storefront plan per account, covering every service's Storefront (never billed per service)."""
        if tier not in STOREFRONT_TIERS:
            raise ValueError(f"{tier} is not a Storefront plan")
        s.c.store.append(account, "server", "storefront.plan_set", {"tier": tier, "side": "external"})
    def storefront_tier(s, account):
        t = "free"
        for e in s.c.store.of(account, "storefront.plan_set"):
            t = e["payload"]["tier"]
        return t
    def storefront_entitlement(s, account):
        return dict(STOREFRONT_FEATURES[STOREFRONT_TIERS.index(s.storefront_tier(account))])
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
        for l in lines:
            l["side"] = "internal"                                           # workspace plans: today's locked prices
        sf = s.storefront_tier(account)
        if sf not in ("free", "enterprise"):                                 # one Storefront line, never per service; Enterprise is by contract
            pr = s.c.profile(account)
            usd = STOREFRONT_PRICES[STOREFRONT_TIERS.index(sf)] * country(pr["country"]).get("price_index", 1.0)
            lines.append({"family": "storefront", "tier": sf, "side": "external", "amount_minor": s.c.fx.convert(to_minor(usd, "USD"), "USD", pr["currency"])})
        return {"currency": s.c.profile(account)["currency"], "lines": lines, "credited": credits, "total_minor": sum(l["amount_minor"] for l in lines)}
    def invoice(s, account, period):
        """One invoice per account per period. Revenue is recorded once per paid line, by family."""
        if any(e["payload"]["period"] == period for e in s.c.store.of(account, "billing.invoiced")):
            return {"status": "already_invoiced", "period": period}
        b, pr = s.bill(account), s.c.profile(account)
        s.c.store.append(account, "server", "billing.invoiced", {"period": period, "total_minor": b["total_minor"], "currency": b["currency"]})
        if s.control:
            for l in b["lines"]:
                s.control.record_revenue(account, f"storefront:plan" if l["side"] == "external" else f"subscription:{l['family']}", l["amount_minor"], b["currency"], pr["country"])
        return {"status": "invoiced", "period": period, **b}
    def counts(s):
        """Paid subscribers per family and tier. Each is counted once; LynkSuite Free and Free tiers are not paid."""
        out = {}
        for acct in {e["merchant"] for e in s.c.store.all_of("subscription.set")}:
            for l in s.bill(acct)["lines"]:
                out.setdefault(l["family"], {}).setdefault(l["tier"], 0)
                out[l["family"]][l["tier"]] += 1
        return out
