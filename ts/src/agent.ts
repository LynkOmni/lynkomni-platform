/** Agent point mode rules (TypeScript port of merchant/agent.py, build section 3). The device only asks; the cloud alone writes the
 *  partner's answer. A request is "sent" until the partner confirms or fails it; cash changes hands only on "confirmed". Agent,
 *  collection and partner-finance services are online only and never queued. No browser or Node APIs. */

export const AGENT_SERVICES = ["cash_withdrawal", "cash_deposit", "money_transfer", "airtime_data", "bills", "tickets", "government_payment", "remittance"] as const;
export type AgentService = (typeof AGENT_SERVICES)[number];
export const COLLECTION_KINDS = ["loan_repayment", "insurance_premium", "voucher", "pickup"] as const;
export const FINANCE_PRODUCTS = ["savings", "loan", "pay_later", "insurance"] as const;
export const AGENT_STATES = ["sent", "confirmed", "failed"] as const;      // never "queued": offline, an agent service never starts
export type AgentState = (typeof AGENT_STATES)[number];
export const FAIL_REASONS = ["partner_declined", "limit_exceeded", "identity_check_failed", "timeout", "insufficient_float", "cancelled_by_customer", "provider_error", "other"] as const;
export const LOW_FLOAT_RATIO = 0.2;
export const AGENT_TABS = ["home", "services", "float", "chats", "business"] as const;
/** The service flow on the device (blueprint 42 I). */
export const SERVICE_FLOW = ["number", "amount", "fee_and_commission", "limit_check", "partner_identity_check", "send", "answer", "cash_or_receipt"] as const;

export const mayHandOverCash = (state: AgentState | string): boolean => state === "confirmed";
export const mayStart = (online: boolean): boolean => online;

export interface Limits { per_transaction: number; per_day: number }
/** The partner's and the country pack's limits combine to the stricter one, shown before each request. */
export function combinedLimits(partner: Limits, pack?: Partial<Limits>): Limits {
  return { per_transaction: Math.min(partner.per_transaction, pack?.per_transaction ?? Infinity), per_day: Math.min(partner.per_day, pack?.per_day ?? Infinity) };
}
/** Before sending: is the amount within what the partner and the pack allow today? */
export function limitCheck(amount: number, usedToday: number, limits: Limits): "ok" | "limit_exceeded" {
  return amount > limits.per_transaction || usedToday + amount > limits.per_day ? "limit_exceeded" : "ok";
}
/** Commission the partner pays, in basis points of the amount (the partner's figure wins when it answers). */
export const commission = (amount: number, bps: number): number => Math.floor((amount * bps) / 10_000);

/** S2: the float at a partner is low when under a fifth of a usual day's need. */
export const lowFloat = (balance: number, usualDailyNeed: number): boolean => usualDailyNeed > 0 && balance < usualDailyNeed * LOW_FLOAT_RATIO;
/** Days of float left at the usual pace: an estimate, labelled so on screen. */
export const floatForecastDays = (balance: number, usualDailyNeed: number): number | null => (usualDailyNeed === 0 ? null : balance / usualDailyNeed);

/** Cash checks at day start, day end and handover never block: the difference is a fact for the owner. */
export const cashDifference = (counted: number, expected: number): number => counted - expected;

export interface StatementRow { request_id: string; commission: number }
/** S12: match what the partner reports against what the cloud recorded; every difference is its own flag. */
export function matchStatement(ours: Readonly<Record<string, number>>, rows: readonly StatementRow[]): { matched: number; total: number; mismatches: string[] } {
  let matched = 0, total = 0; const mismatches: string[] = [];
  const seen = new Set<string>();
  for (const r of rows) {
    seen.add(r.request_id);
    if (ours[r.request_id] === r.commission) { matched += 1; total += r.commission; } else mismatches.push(r.request_id);
  }
  for (const id of Object.keys(ours)) if (!seen.has(id)) mismatches.push(id);
  return { matched, total, mismatches };
}

/** How many partners an agent point may hold and how many outlets it may run (null = unlimited), from the plan. */
export const mayAddPartner = (limit: number | null | undefined, have: number): boolean => limit === null || limit === undefined || have < limit;
