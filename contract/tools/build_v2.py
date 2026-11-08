#!/usr/bin/env python3
"""Builds contract version 2 (Step 0, blueprint 42 A and 44 L row 0) from version 1 plus the new event names.

Version 1 is never edited. Version 2:
  * money is an integer in the currency's minor unit, and every payload that carries money carries its `currency`
    (ISO 4217, read from contract/currencies.v1.json); `rwf` becomes `money`;
  * registers the event names agreed in blueprint sections 42 I (LynkPOS services), 44 E (chat translation),
    44 G (Partner Hub), 44 I (the fourteen services N1 to N14), 44 J (LynkStat) and 45 A (automation runs);
  * adds the device commands that issue the new device events to the command policy register (class A offline
    facts; class C for anything that goes to a partner and is never queued offline).

Writes contract/event-payloads.v2.json and contract/command-policy-register.v2.json. tests/test_contract_v2.py
fails when the committed files differ from this script's output, so the files are never hand-edited.
Run:  python3 contract/tools/build_v2.py
"""
import copy, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load(name):
    with open(os.path.join(ROOT, name), encoding="utf-8") as f:
        return json.load(f)


# ------------------------------------------------------------------ field shorthands
T = {
    "uuid7": {"$ref": "#/$defs/uuid7"}, "uuid": {"$ref": "#/$defs/uuid"}, "money": {"$ref": "#/$defs/money"},
    "money_signed": {"$ref": "#/$defs/money_signed"}, "currency": {"$ref": "#/$defs/currency"},
    "name": {"$ref": "#/$defs/name"}, "note": {"$ref": "#/$defs/note"}, "ref": {"$ref": "#/$defs/provider_ref"},
    "int": {"type": "integer", "minimum": 0, "maximum": 1000000000}, "bool": {"type": "boolean"},
    "lang": {"$ref": "#/$defs/language"}, "country": {"$ref": "#/$defs/country"}, "ts": {"$ref": "#/$defs/timestamp_utc"},
    "date": {"$ref": "#/$defs/date"}, "period": {"$ref": "#/$defs/period"}, "username": {"$ref": "#/$defs/username"},
    "kebab": {"$ref": "#/$defs/kebab"}, "sha256": {"$ref": "#/$defs/sha256"}, "score": {"type": "integer", "minimum": 0, "maximum": 100},
    "rating": {"type": "integer", "minimum": 1, "maximum": 5},
}


def enum(*vals): return {"enum": list(vals)}


def payload(fields, optional=()):
    """fields: {name: shorthand or schema}. Every field is required unless listed in optional."""
    props = {k: (T[v] if isinstance(v, str) else v) for k, v in fields.items()}
    return {"type": "object", "additionalProperties": False,
            "required": [k for k in fields if k not in optional], "properties": props}


D, S, DS = ["device"], ["server"], ["device", "server"]
REASON = enum("partner_declined", "limit_exceeded", "identity_check_failed", "timeout", "insufficient_float",
              "cancelled_by_customer", "provider_error", "other")
AGENT_SERVICES = enum("cash_withdrawal", "cash_deposit", "money_transfer", "airtime_data", "bills", "tickets",
                      "government_payment", "remittance", "loan_repayment", "insurance_premium")

# ------------------------------------------------------------------ the new events of sections 42 I, 44 and 45
# name: (origins, fields, optional fields, blueprint part)
NEW = {
    # 42 I: LynkPOS services. Device facts work offline; anything sent to a partner is online only (class C).
    "AgentRequestCreated": (D, {"request_id": "uuid7", "partner_id": "uuid", "service": AGENT_SERVICES, "amount": "money", "fee": "money", "currency": "currency", "customer_reference": "ref"}, ("customer_reference",), "42 I"),
    "ShiftOpened": (D, {"shift_id": "uuid7", "float_amount": "money", "currency": "currency"}, (), "42 I"),
    "ShiftClosed": (D, {"shift_id": "uuid7", "counted_cash": "money", "expected_cash": "money", "currency": "currency"}, (), "42 I"),
    "CashCounted": (D, {"count_id": "uuid7", "shift_id": "uuid7", "kind": enum("day_start", "day_end", "handover", "spot"), "counted_cash": "money", "expected_cash": "money", "currency": "currency"}, (), "42 I"),
    "VoucherRedeemed": (D, {"redemption_id": "uuid7", "voucher_id": "uuid", "amount": "money", "currency": "currency"}, (), "42 I"),
    "PickupHandedOver": (D, {"pickup_id": "uuid7", "order_id": "uuid", "code_hash": "sha256"}, (), "42 I"),
    "CustomerCreditRecorded": (D, {"credit_id": "uuid7", "customer_id": "uuid", "sale_id": "uuid7", "amount": "money", "currency": "currency", "due_on": "date"}, ("due_on",), "42 I"),
    "CustomerCreditPaid": (D, {"payment_id": "uuid7", "credit_id": "uuid7", "amount": "money", "currency": "currency", "method": {"$ref": "#/$defs/payment_method"}}, (), "42 I"),
    "AgentRequestConfirmed": (S, {"request_id": "uuid7", "partner_reference": "ref", "amount": "money", "fee": "money", "commission": "money", "currency": "currency"}, (), "42 I"),
    "AgentRequestFailed": (S, {"request_id": "uuid7", "reason_code": REASON, "partner_reference": "ref"}, ("partner_reference",), "42 I"),
    "CommissionRecorded": (S, {"commission_id": "uuid7", "request_id": "uuid7", "partner_id": "uuid", "amount": "money", "currency": "currency", "period": "period"}, (), "42 I"),
    "PartnerStatementMatched": (S, {"statement_id": "uuid7", "partner_id": "uuid", "period": "period", "matched_count": "int", "total": "money", "currency": "currency"}, (), "42 I"),
    "CommissionMismatchFlagged": (S, {"mismatch_id": "uuid7", "statement_id": "uuid7", "request_id": "uuid7", "expected": "money", "reported": "money", "currency": "currency"}, ("request_id",), "42 I"),
    "FloatBalanceRead": (S, {"partner_id": "uuid", "balance": "money", "currency": "currency", "read_at": "ts"}, (), "42 I"),
    "CashDifferenceFlagged": (S, {"count_id": "uuid7", "difference": "money_signed", "currency": "currency"}, (), "42 I"),
    "CollectionRecorded": (S, {"collection_id": "uuid7", "request_id": "uuid7", "partner_id": "uuid", "kind": enum("loan_repayment", "insurance_premium", "voucher", "pickup"), "amount": "money", "currency": "currency"}, (), "42 I"),
    "PartnerReferralRecorded": (S, {"referral_id": "uuid7", "partner_id": "uuid", "product": enum("savings", "loan", "pay_later", "insurance", "financing", "bank_account", "extended_warranty", "registration"), "fee": "money", "currency": "currency"}, (), "42 I"),
    # 44 E: LynkChat in two languages. The cloud alone writes the translation.
    "MessageTranslated": (S, {"message_id": "uuid7", "from_language": "lang", "to_language": "lang", "engine": enum("madlad")}, (), "44 E"),
    # 44 G: Partner Hub. Cloud only.
    "PartnerRegistered": (S, {"partner_id": "uuid", "username": "username", "kind": enum("bank", "mobile_money", "card_issuer", "tax_authority", "biller", "booking_supplier", "lender", "insurer", "remittance", "government_gateway", "delivery", "messaging", "cloud", "ai_model", "hardware", "auditor", "other")}, (), "44 G"),
    "ConnectionStaged": (S, {"connection_id": "uuid7", "partner_id": "uuid", "service": "kebab", "country": "country"}, (), "44 G"),
    "ConnectionActivated": (S, {"connection_id": "uuid7", "stage": enum("shadow", "pilot", "share", "live")}, (), "44 G"),
    "ConnectionPaused": (S, {"connection_id": "uuid7", "emergency": "bool", "reason": "note"}, ("reason",), "44 G"),
    "ConnectionResumed": (S, {"connection_id": "uuid7"}, (), "44 G"),
    "ConnectionUnplugged": (S, {"connection_id": "uuid7", "replacement_connection_id": "uuid7"}, ("replacement_connection_id",), "44 G"),
    "PartnerAssetPublished": (S, {"partner_id": "uuid", "asset": enum("logo", "method_icon", "display_name", "legal_line", "receipt_text"), "licensed": "bool"}, (), "44 G"),
    "PartnerAssetWithdrawn": (S, {"partner_id": "uuid", "asset": enum("logo", "method_icon", "display_name", "legal_line", "receipt_text")}, (), "44 G"),
    "ScorecardComputed": (S, {"connection_id": "uuid7", "score": "score", "period": "period"}, (), "44 G"),
    # 44 I N1: restaurant and food mode (device facts, offline).
    "TableOpened": (D, {"table_id": "uuid7", "table_label": "name", "covers": "int"}, ("covers",), "44 I N1"),
    "OrderSentToKitchen": (D, {"order_id": "uuid7", "table_id": "uuid7", "lines": {"type": "array", "minItems": 1, "maxItems": 200, "items": payload({"line_no": "int", "product_id": "uuid7", "quantity_milli": {"$ref": "#/$defs/qty"}, "modifiers": "note"}, ("modifiers",))}}, (), "44 I N1"),
    "KitchenItemReady": (D, {"order_id": "uuid7", "line_no": "int"}, (), "44 I N1"),
    "TableBillSplit": (D, {"table_id": "uuid7", "sale_ids": {"type": "array", "minItems": 2, "maxItems": 50, "items": T["uuid7"]}}, (), "44 I N1"),
    "TipRecorded": (D, {"tip_id": "uuid7", "sale_id": "uuid7", "amount": "money", "currency": "currency"}, (), "44 I N1"),
    "TableClosed": (D, {"table_id": "uuid7"}, (), "44 I N1"),
    # 44 I N2: payroll. Clock in and out on the device; the run and pay-outs in the cloud.
    "ClockedIn": (D, {"clock_id": "uuid7", "employee_id": "uuid"}, (), "44 I N2"),
    "ClockedOut": (D, {"clock_id": "uuid7", "employee_id": "uuid"}, (), "44 I N2"),
    "PayrollRunApproved": (S, {"run_id": "uuid7", "period": "period", "employees": "int", "total": "money", "currency": "currency"}, (), "44 I N2"),
    "PayoutRequested": (S, {"payout_id": "uuid7", "run_id": "uuid7", "amount": "money", "currency": "currency"}, (), "44 I N2"),
    "PayoutConfirmed": (S, {"payout_id": "uuid7", "provider_reference": "ref"}, (), "44 I N2"),
    "PayoutFailed": (S, {"payout_id": "uuid7", "reason_code": REASON}, (), "44 I N2"),
    # 44 I N3: tax filing helper. Never "filed" until the authority answers.
    "TaxReturnPrepared": (S, {"return_id": "uuid7", "period": "period", "document_id": "uuid7"}, (), "44 I N3"),
    "TaxReturnSubmitted": (S, {"return_id": "uuid7", "authority_reference": "ref"}, ("authority_reference",), "44 I N3"),
    "TaxReturnAccepted": (S, {"return_id": "uuid7", "authority_reference": "ref"}, (), "44 I N3"),
    "TaxReturnRejected": (S, {"return_id": "uuid7", "reason": "note"}, (), "44 I N3"),
    # 44 I N4: recurring collections under the customer's own capped standing instruction at the provider.
    "MandateCreated": (S, {"mandate_id": "uuid7", "customer_id": "uuid", "amount_cap": "money", "currency": "currency", "interval": enum("weekly", "monthly", "quarterly", "yearly")}, (), "44 I N4"),
    "MandateConfirmed": (S, {"mandate_id": "uuid7", "provider_reference": "ref"}, (), "44 I N4"),
    "MandateFailed": (S, {"mandate_id": "uuid7", "reason_code": REASON}, (), "44 I N4"),
    "CollectionRequested": (S, {"collection_id": "uuid7", "mandate_id": "uuid7", "invoice_id": "uuid7", "amount": "money", "currency": "currency"}, (), "44 I N4"),
    "CollectionConfirmed": (S, {"collection_id": "uuid7", "provider_reference": "ref"}, (), "44 I N4"),
    "CollectionFailed": (S, {"collection_id": "uuid7", "reason_code": REASON}, (), "44 I N4"),
    "MandateCancelled": (S, {"mandate_id": "uuid7", "by": enum("customer", "merchant", "provider")}, (), "44 I N4"),
    # 44 I N5: quote acceptance and e-signature.
    "QuoteAccepted": (S, {"quote_id": "uuid7", "customer_id": "uuid"}, ("customer_id",), "44 I N5"),
    "QuoteSigned": (S, {"quote_id": "uuid7", "consent_id": "uuid7", "qualified": "bool"}, (), "44 I N5"),
    "InvoiceIssuedFromQuote": (S, {"quote_id": "uuid7", "invoice_id": "uuid7"}, (), "44 I N5"),
    # 44 I N6: get paid early. The request is online only; the lender decides.
    "FinancingRequested": (D, {"request_id": "uuid7", "invoice_id": "uuid7", "consent_id": "uuid7"}, (), "44 I N6"),
    "FinancingOffered": (S, {"offer_id": "uuid7", "request_id": "uuid7", "lender_id": "uuid", "amount": "money", "total_cost": "money", "currency": "currency"}, (), "44 I N6"),
    "FinancingAccepted": (S, {"offer_id": "uuid7"}, (), "44 I N6"),
    "FinancingPaidOut": (S, {"offer_id": "uuid7", "provider_reference": "ref"}, (), "44 I N6"),
    "FinancingRepaid": (S, {"offer_id": "uuid7"}, (), "44 I N6"),
    # 44 I N7: lease a device (DeviceEnrolled already exists in version 1).
    "LeaseOffered": (S, {"lease_id": "uuid7", "device_model": "name", "monthly": "money", "currency": "currency", "months": "int"}, (), "44 I N7"),
    "LeaseConfirmed": (S, {"lease_id": "uuid7", "provider_reference": "ref"}, (), "44 I N7"),
    "DeviceShipped": (S, {"lease_id": "uuid7", "tracking_reference": "ref"}, (), "44 I N7"),
    "LeaseEnded": (S, {"lease_id": "uuid7", "reason": enum("completed", "returned", "lost", "cancelled")}, (), "44 I N7"),
    # 44 I N8: delivery and pickup. The request is online only; own riders record pickup and delivery on their device.
    "DeliveryRequested": (D, {"delivery_id": "uuid7", "order_id": "uuid", "partner_id": "uuid", "own_rider": "bool", "price": "money", "currency": "currency"}, ("partner_id",), "44 I N8"),
    "DeliveryAccepted": (S, {"delivery_id": "uuid7", "partner_reference": "ref", "eta": "ts"}, ("eta",), "44 I N8"),
    "DeliveryPickedUp": (DS, {"delivery_id": "uuid7"}, (), "44 I N8"),
    "DeliveryDelivered": (DS, {"delivery_id": "uuid7", "proof": enum("code", "photo")}, (), "44 I N8"),
    "DeliveryFailed": (S, {"delivery_id": "uuid7", "reason_code": REASON}, (), "44 I N8"),
    # 44 I N9: warranty, returns and repairs (ReturnRecorded exists in version 1).
    "WarrantyIssued": (D, {"warranty_id": "uuid7", "sale_id": "uuid7", "product_id": "uuid7", "ends_on": "date"}, (), "44 I N9"),
    "RepairTicketOpened": (D, {"ticket_id": "uuid7", "customer_id": "uuid", "product_id": "uuid7", "note": "note"}, ("product_id", "note"), "44 I N9"),
    "RepairStatusChanged": (D, {"ticket_id": "uuid7", "to_status": enum("open", "diagnosing", "waiting_parts", "repairing", "ready", "closed")}, (), "44 I N9"),
    # 44 I N10: verified reviews and promoted listings.
    "ReviewSubmitted": (S, {"review_id": "uuid7", "receipt_id": "uuid7", "rating": "rating"}, (), "44 I N10"),
    "ReviewReplied": (S, {"review_id": "uuid7"}, (), "44 I N10"),
    "ReviewReported": (S, {"review_id": "uuid7", "reason": enum("abuse", "fake", "personal_data", "other")}, (), "44 I N10"),
    "PromotionStarted": (S, {"promotion_id": "uuid7", "budget": "money", "currency": "currency"}, (), "44 I N10"),
    "PromotionImpressionValidated": (S, {"promotion_id": "uuid7", "impression_id": "uuid7"}, (), "44 I N10"),
    "PromotionEnded": (S, {"promotion_id": "uuid7", "reason": enum("budget_spent", "ended_by_merchant", "period_over", "policy")}, (), "44 I N10"),
    # 44 I N11: buy together. Each shop pays the supplier for its own part; nothing is pooled.
    "GroupOrderOpened": (S, {"group_id": "uuid7", "supplier_id": "uuid", "closes_at": "ts"}, (), "44 I N11"),
    "GroupOrderJoined": (S, {"group_id": "uuid7", "order_id": "uuid7", "amount": "money", "currency": "currency"}, (), "44 I N11"),
    "GroupOrderReached": (S, {"group_id": "uuid7"}, (), "44 I N11"),
    "GroupOrderFailed": (S, {"group_id": "uuid7"}, (), "44 I N11"),
    # 44 I N12: supplier sell-through, only by the merchant's recorded consent.
    "SupplierShareGranted": (S, {"share_id": "uuid7", "supplier_id": "uuid", "consent_id": "uuid7"}, (), "44 I N12"),
    "SupplierShareRevoked": (S, {"share_id": "uuid7"}, (), "44 I N12"),
    "DataSharingConsentGiven": (S, {"consent_id": "uuid7", "scope": "kebab"}, (), "44 I N12"),
    "DataSharingConsentWithdrawn": (S, {"consent_id": "uuid7"}, (), "44 I N12"),
    # 44 I N13: Academy.
    "CourseCompleted": (S, {"completion_id": "uuid7", "course": "kebab", "user_id": "uuid"}, (), "44 I N13"),
    "CertificateIssued": (S, {"certificate_id": "uuid7", "completion_id": "uuid7", "document_id": "uuid7"}, (), "44 I N13"),
    # 44 I N14: start a business.
    "RegistrationStarted": (S, {"application_id": "uuid7", "country": "country"}, (), "44 I N14"),
    "RegistrationSubmitted": (S, {"application_id": "uuid7", "gateway_reference": "ref"}, ("gateway_reference",), "44 I N14"),
    "RegistrationApproved": (S, {"application_id": "uuid7", "gateway_reference": "ref"}, (), "44 I N14"),
    "RegistrationRejected": (S, {"application_id": "uuid7", "reason": "note"}, (), "44 I N14"),
    "BankAccountReferred": (S, {"referral_id": "uuid7", "application_id": "uuid7", "partner_id": "uuid"}, (), "44 I N14"),
    # 44 J: LynkStat. Cloud only.
    "DataSourceConnected": (S, {"source_id": "uuid7", "kind": "kebab", "consent_id": "uuid7"}, (), "44 J"),
    "RecordsImported": (S, {"import_id": "uuid7", "source_id": "uuid7", "count": "int"}, (), "44 J"),
    "DataSourceDisconnected": (S, {"source_id": "uuid7"}, (), "44 J"),
    "ReportBuilt": (S, {"report_id": "uuid7", "kind": enum("daily", "weekly", "monthly", "custom", "health_pack"), "period": "period"}, (), "44 J"),
    "AlertRaised": (S, {"alert_id": "uuid7", "kind": "kebab", "severity": enum("info", "warning", "urgent")}, (), "44 J"),
    "ForecastMade": (S, {"forecast_id": "uuid7", "kind": "kebab", "period": "period"}, (), "44 J"),
    "ScoreComputed": (S, {"score_id": "uuid7", "score": "score", "period": "period"}, (), "44 J"),
    "InsightActionDrafted": (S, {"draft_id": "uuid7", "insight_id": "uuid7", "action": enum("restock", "send_offer", "follow_up", "chase_payment", "fix_budget", "get_paid_early", "add_staff", "top_up_float")}, (), "44 J"),
    # 45 A: automation runs. On the device when the automation must work offline, otherwise in the cloud.
    "AutomationTriggered": (DS, {"run_id": "uuid7", "automation_id": "kebab", "trigger": enum("event", "schedule", "request"), "cause_event_id": "uuid7"}, ("cause_event_id",), "45 A"),
    "AutomationDrafted": (DS, {"run_id": "uuid7"}, (), "45 A"),
    "AutomationApplied": (DS, {"run_id": "uuid7", "undo_until": "ts"}, ("undo_until",), "45 A"),
    "AutomationUndone": (DS, {"run_id": "uuid7", "by_user_id": "uuid"}, (), "45 A"),
    "AutomationSkipped": (DS, {"run_id": "uuid7", "reason": enum("switched_off", "tier", "consent", "quiet_hours", "country", "duplicate", "loop_guard", "limit")}, (), "45 A"),
}

# The device commands that issue the new device events (class A = offline fact; class C = goes to a partner, never offline).
NEW_COMMANDS = [
    ("RequestAgentService", "C", ["AgentRequestCreated"], "sale.record", ["mobile"], ["partner_declined", "limit_exceeded", "offline_not_possible", "permission_denied", "session_expired", "device_locked"]),
    ("OpenShift", "A", ["ShiftOpened"], "sale.record", ["mobile"], ["shift_already_open", "permission_denied", "session_expired", "device_locked"]),
    ("CloseShift", "A", ["ShiftClosed", "CashCounted"], "sale.record", ["mobile"], ["no_open_shift", "permission_denied", "session_expired", "device_locked"]),
    ("CountCash", "A", ["CashCounted"], "sale.record", ["mobile"], ["no_open_shift", "permission_denied", "session_expired", "device_locked"]),
    ("RedeemVoucher", "A", ["VoucherRedeemed"], "sale.record", ["mobile"], ["voucher_unknown_local", "voucher_already_used", "permission_denied", "session_expired", "device_locked"]),
    ("HandOverPickup", "A", ["PickupHandedOver"], "sale.record", ["mobile"], ["code_mismatch", "permission_denied", "session_expired", "device_locked"]),
    ("RecordCustomerCredit", "A", ["CustomerCreditRecorded"], "sale.record", ["mobile"], ["credit_over_limit", "customer_not_found_local", "permission_denied", "session_expired", "device_locked"]),
    ("RecordCreditPayment", "A", ["CustomerCreditPaid"], "payment.record", ["mobile"], ["invalid_amount", "credit_not_found_local", "permission_denied", "session_expired", "device_locked"]),
    ("OpenTable", "A", ["TableOpened"], "sale.record", ["mobile"], ["table_already_open", "permission_denied", "session_expired", "device_locked"]),
    ("SendToKitchen", "A", ["OrderSentToKitchen"], "sale.record", ["mobile"], ["empty_order", "table_not_open", "permission_denied", "session_expired", "device_locked"]),
    ("MarkKitchenItemReady", "A", ["KitchenItemReady"], "sale.record", ["mobile"], ["order_not_found_local", "permission_denied", "session_expired", "device_locked"]),
    ("SplitTableBill", "A", ["TableBillSplit"], "sale.record", ["mobile"], ["table_not_open", "permission_denied", "session_expired", "device_locked"]),
    ("RecordTip", "A", ["TipRecorded"], "payment.record", ["mobile"], ["invalid_amount", "permission_denied", "session_expired", "device_locked"]),
    ("CloseTable", "A", ["TableClosed"], "sale.record", ["mobile"], ["table_not_open", "unpaid_balance", "permission_denied", "session_expired", "device_locked"]),
    ("ClockIn", "A", ["ClockedIn"], "sale.record", ["mobile"], ["already_clocked_in", "session_expired", "device_locked"]),
    ("ClockOut", "A", ["ClockedOut"], "sale.record", ["mobile"], ["not_clocked_in", "session_expired", "device_locked"]),
    ("RequestFinancing", "C", ["FinancingRequested"], "sale.record", ["mobile"], ["no_consent", "offline_not_possible", "permission_denied", "session_expired", "device_locked"]),
    ("RequestDelivery", "C", ["DeliveryRequested"], "sale.record", ["mobile"], ["offline_not_possible", "order_not_found_local", "permission_denied", "session_expired", "device_locked"]),
    ("RecordDeliveryStep", "A", ["DeliveryPickedUp", "DeliveryDelivered"], "sale.record", ["mobile"], ["code_mismatch", "delivery_not_found_local", "permission_denied", "session_expired", "device_locked"]),
    ("IssueWarranty", "A", ["WarrantyIssued"], "sale.record", ["mobile"], ["sale_not_found_local", "permission_denied", "session_expired", "device_locked"]),
    ("OpenRepairTicket", "A", ["RepairTicketOpened", "RepairStatusChanged"], "sale.record", ["mobile"], ["customer_not_found_local", "permission_denied", "session_expired", "device_locked"]),
    ("RunDeviceAutomation", "A", ["AutomationTriggered", "AutomationDrafted", "AutomationApplied", "AutomationUndone", "AutomationSkipped"], None, ["mobile"], ["automation_off", "loop_guard", "device_locked"]),
]


def build():
    v1 = load("event-payloads.v1.json")
    currencies = load("currencies.v1.json")["decimals"]
    v2 = copy.deepcopy(v1)
    v2["$id"] = "lynkomni/event-payloads.v2"
    v2["description"] = ("Registry of every event type allowed in version 2 (Step 0, blueprint 42 A). A type not listed here is quarantined by LynkCCBox. "
                         "Money is an integer in the currency's minor unit and every payload that carries money carries its ISO 4217 currency, "
                         "listed in contract/currencies.v1.json (decimals for display only). Quantities are integer thousandths. "
                         "Version 1 events (integer RWF) stay readable through the upcaster in contract/upcasters.v1.json. "
                         "Generated by contract/tools/build_v2.py; never hand-edited.")
    defs = v2["$defs"]
    defs.pop("rwf")
    defs["money"] = {"type": "integer", "minimum": 0, "maximum": 1000000000000000, "description": "Integer minor units of the payload's currency."}
    defs["money_signed"] = {"type": "integer", "minimum": -1000000000000000, "maximum": 1000000000000000}
    defs["currency"] = {"enum": sorted(currencies), "description": "ISO 4217 code from contract/currencies.v1.json."}
    defs["language"] = {"type": "string", "pattern": "^[a-z]{2,3}(-[A-Za-z]{2,4})?$"}
    defs["country"] = {"type": "string", "pattern": "^[A-Z]{2}$"}
    defs["date"] = {"type": "string", "pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}$"}
    defs["period"] = {"type": "string", "pattern": "^[0-9]{4}(-[0-9]{2}(-[0-9]{2})?)?$", "description": "A year, a month or a day."}
    defs["username"] = {"type": "string", "pattern": "^(?!\\.)(?!.*\\.\\.)(?!.*\\.$)[a-z0-9._]{3,30}$", "description": "The shared username rule (blueprint 44 B, core/usernames.py)."}
    defs["kebab"] = {"type": "string", "pattern": "^[a-z0-9]+(-[a-z0-9]+)*$", "maxLength": 60}
    defs["sha256"] = {"type": "string", "pattern": "^[0-9a-f]{64}$"}
    defs["timestamp_utc"] = {"type": "string", "pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(\\.[0-9]{1,3})?Z$"}
    # version 1 events become version 2: rwf -> money, and a currency beside every amount
    events = v2["events"]
    text = json.dumps(events).replace('"#/$defs/rwf"', '"#/$defs/money"')
    events = json.loads(text)
    for name in ("PaymentRecorded", "ReturnRecorded", "ProductCreated"):
        p = events[name]["payload"]
        p["properties"]["currency"] = T["currency"]
        p["required"].append("currency")
    events["SaleRecorded"]["payload"]["properties"]["currency"] = T["currency"]   # was fixed to one currency in version 1
    for name in ("StockReceived", "ProductUpdated"):                              # money is optional here, so the currency is required only with it
        events[name]["payload"]["properties"]["currency"] = T["currency"]
    # upcasters: the upcaster in contract/upcasters.v1.json adds the default currency to these three
    assert set(load("upcasters.v1.json")["upcasters"][0]["adds_currency_to"]) == {"PaymentRecorded", "ReturnRecorded", "ProductCreated"}
    for name, e in events.items():
        e["schema_version"] = 2
        e["since"] = "v1"
    for name, (origins, fields, optional, part) in NEW.items():
        assert name not in events, name
        events[name] = {"schema_version": 2, "origins": origins, "since": "v2", "blueprint": part, "payload": payload(fields, optional)}
    v2["events"] = events

    r1 = load("command-policy-register.v1.json")
    r2 = copy.deepcopy(r1)
    r2["$id"] = "lynkomni/command-policy-register.v2"
    r2["description"] = r1["description"] + " Version 2 adds the commands of blueprint sections 42 I, 44 I and 45 (generated by contract/tools/build_v2.py; never hand-edited)."
    template_a = next(c for c in r1["commands"] if c["name"] == "RecordSale")
    template_c = next(c for c in r1["commands"] if c["name"] == "RequestMobileMoneyPayment")
    for name, cls, emits, perm, channels, rejections in NEW_COMMANDS:
        base = copy.deepcopy(template_a if cls == "A" else template_c)
        base.update({"name": name, "class": cls, "v1": False, "v2": True, "emits": emits, "permission": perm, "channels": channels,
                     "local_rejections": rejections})
        if perm is None:
            base["local_only"] = True
        if cls == "A":
            base["ui_states"] = ["recorded", "pending_sync", "accepted"]
        else:
            base["offline"] = {"allowed": False, "behavior": "refused with offline_not_possible; the request is never queued (blueprint 42 I)"}
            base["ui_states"] = ["sent", "confirmed", "failed"]
        r2["commands"].append(base)
    return v2, r2


def main(check=False):
    v2, r2 = build()
    out = {"event-payloads.v2.json": v2, "command-policy-register.v2.json": r2}
    stale = []
    for name, data in out.items():
        path = os.path.join(ROOT, name)
        text = json.dumps(data, indent=1, ensure_ascii=False) + "\n"
        if check:
            with open(path, encoding="utf-8") as f:
                if f.read() != text:
                    stale.append(name)
        else:
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)
    if check:
        if stale:
            print("stale:", ", ".join(stale)); sys.exit(1)
        print("contract version 2 files are up to date")
    else:
        print(f"wrote {', '.join(out)}: {len(v2['events'])} event types, {len(r2['commands'])} commands")


if __name__ == "__main__":
    main(check="--check" in sys.argv)
