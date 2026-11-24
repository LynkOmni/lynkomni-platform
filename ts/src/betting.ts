/** LynkBet (BETTING UPDATE, master blueprint section 86): the TypeScript port of core/betting.py. The rules come from
 *  catalog/betting.v1.json (ts/src/betting.generated.ts) and contract/vectors/betting.v1.json proves both agree. The operator's
 *  system decides every result and amount; LynkOmni is only the shop's tool. Money is whole minor units and odds are whole
 *  thousandths. Every export starts with "bet" so the bundled pages never meet another part's name. No browser or Node APIs. */
import { BETTING } from "./betting.generated.js";

export const BET_STATES = BETTING.request_states;
export const BET_RESULTS = BETTING.results;
export const BET_CHECK_ORDER = BETTING.check_order;
export const BET_STAKE_METHODS = BETTING.stake_methods;
export const BET_SCALE = BETTING.odds_scale;
export const BET_ADULT_AGE = 18;
export type BetState = "sent" | "confirmed" | "failed";
export type BetCheckAnswer = "pay" | "refer" | "short_of_cash" | "already_paid" | "not_valid" | "pending" | "lost" | "expired";
export type BetStartAnswer = "ok" | "offline" | "coming_soon" | "age" | "self_excluded";
export type BetStakeAnswer = "ok" | "below_min" | "above_max" | "personal_limit";
export type BetOddsFormat = "decimal" | "fractional" | "american" | "hong_kong";
export interface BetTicket { known: boolean; result?: string; paid?: boolean; payable?: number; expires?: number }

function whole(n: number, what: string): number {
  if (!Number.isSafeInteger(n)) throw new TypeError(`${what} must be a whole number`);
  return n;
}
const big = (n: number): bigint => BigInt(n);
/** Whether a bet may start, or the first reason it may not. Offline a bet is only ever a queued slip (betOfflineSlip). */
export function betMayStart(online: boolean, operatorSigned: boolean, ageConfirmed: boolean, selfExcluded = false): BetStartAnswer {
  if (!online) return "offline";
  if (!operatorSigned) return "coming_soon";
  if (!ageConfirmed) return "age";
  if (selfExcluded) return "self_excluded";
  return "ok";
}
export const betAdultAge = (packAge?: number | null): number => Math.max(BET_ADULT_AGE, packAge ?? 0);
export const betStakeMethodOk = (method: string): boolean => (BET_STAKE_METHODS as readonly string[]).includes(method);
/** Combined odds in thousandths, rounded down at each step (with BigInt, so nothing ever loses a digit). */
export function betTotalOdds(odds: readonly number[]): number {
  let total = big(BET_SCALE);
  for (const o of odds) { whole(o, "odds"); if (o < BET_SCALE) throw new RangeError("odds below 1.000"); total = (total * big(o)) / big(BET_SCALE); }
  return Number(total);
}
export function betPossibleWin(stake: number, odds: readonly number[], maxWin?: number | null): number {
  whole(stake, "stake");
  const win = Number((big(stake) * big(betTotalOdds(odds))) / big(BET_SCALE));
  return maxWin === undefined || maxWin === null ? win : Math.min(win, maxWin);
}
export function betStakeCheck(stake: number, minStake: number, maxStake: number, personalLeft?: number | null): BetStakeAnswer {
  whole(stake, "stake");
  if (stake < minStake) return "below_min";
  if (stake > maxStake) return "above_max";
  if (personalLeft !== undefined && personalLeft !== null && stake > personalLeft) return "personal_limit";
  return "ok";
}
/** What the counter says after a scan, from the operator's answer, in the register's fixed order. */
export function betCheckAnswer(ticket: BetTicket | null, today: number, shopMax: number, cashInDrawer: number): BetCheckAnswer {
  if (!ticket || !ticket.known) return "not_valid";
  if (ticket.paid) return "already_paid";
  const r = ticket.result ?? "";
  if (!(BET_RESULTS as readonly string[]).includes(r)) return "not_valid";
  if (r === "pending") return "pending";
  if (r === "lost") return "lost";
  if (today > (ticket.expires ?? today)) return "expired";
  const payable = whole(ticket.payable ?? 0, "payable");
  if (payable > shopMax) return "refer";
  if (payable > cashInDrawer) return "short_of_cash";
  return "pay";
}
export const betMayHandOverCash = (lockState: string): boolean => lockState === "confirmed";
export const betCommission = (amount: number, bps: number): number => Number((big(whole(amount, "amount")) * big(whole(bps, "bps"))) / 10_000n);
export const betExpectedCash = (opening: number, stakesCash: readonly number[], payoutsCash: readonly number[]): number =>
  opening + stakesCash.reduce((a, b) => a + b, 0) - payoutsCash.reduce((a, b) => a + b, 0);
/** Please check flags, never an accusation and never a block. */
export function betFlags(scans: Readonly<Record<string, number>>, payouts: readonly number[], shopMax: number): string[] {
  const out = Object.keys(scans).sort().filter((c) => (scans[c] ?? 0) >= BETTING.flags.repeat_scans).map((c) => `repeat_scans:${c}`);
  const many = payouts.filter((p) => p * 10_000 >= shopMax * BETTING.flags.big_payout_share_bps);
  if (many.length >= BETTING.flags.big_payouts) out.push("many_big_payouts");
  return out;
}
export function betReferNext(step: string): string | null {
  const s = BETTING.refer_steps as readonly string[], i = s.indexOf(step);
  if (i < 0) throw new RangeError(`unknown step ${step}`);
  return s[i + 1] ?? null;
}
/** How the operator's odds look (display only): decimal 2.15, fractional 23/20, American +115 or -118, Hong Kong 1.15. */
export function betOddsText(milli: number, fmt: BetOddsFormat = "decimal"): string {
  whole(milli, "odds");
  if (milli < BET_SCALE) throw new RangeError("odds below 1.000");
  const win = milli - BET_SCALE, two = (n: number): string => `${Math.floor(n / BET_SCALE)}.${String(n % BET_SCALE).padStart(3, "0")}`.slice(0, -1);
  if (fmt === "decimal") return two(milli);
  if (fmt === "hong_kong") return two(win);
  if (fmt === "fractional") { const g = gcd(win, BET_SCALE) || 1; return `${win / g}/${BET_SCALE / g}`; }
  if (win === 0) return "0";
  return milli >= 2 * BET_SCALE ? `+${Math.floor(win / 10)}` : `-${Math.ceil((100 * BET_SCALE) / win)}`;
}
function gcd(a: number, b: number): number { while (b) [a, b] = [b, a % b]; return a; }
export type BetSlipAnswer = "ok" | "operator_off" | "live" | "starts_soon" | "slip_cap" | "shop_cap";
/** Whether a queued slip may be taken offline, or the first reason it may not. A slip is never a ticket until the operator accepts. */
export function betOfflineSlip(operatorAllows: boolean, kind: string, startsInMinutes: number, minLeadMinutes: number, stake: number, slipCap: number, queuedTotal: number, shopCap: number): BetSlipAnswer {
  if (!operatorAllows) return "operator_off";
  if (kind === "live") return "live";
  if (kind !== "lottery" && startsInMinutes < minLeadMinutes) return "starts_soon";
  if (stake > slipCap) return "slip_cap";
  if (queuedTotal + stake > shopCap) return "shop_cap";
  return "ok";
}
export const betSlipResult = (accepted: boolean, stake: number): { ticket: boolean; refund: number } => (accepted ? { ticket: true, refund: 0 } : { ticket: false, refund: whole(stake, "stake") });
/** Paying a winning ticket, referring a big win and cancelling never happen offline. */
export function betOnlineOnly(action: string, online: boolean): boolean {
  if (!["payout", "refer", "cancel"].includes(action)) throw new RangeError(`unknown action ${action}`);
  return online;
}
export type BetCancelAnswer = "ok" | "offline" | "operator_off" | "game_started" | "too_late" | "manager_needed";
export function betCancelCheck(online: boolean, operatorAllows: boolean, gameStarted: boolean, managerApproved: boolean, minutesSince: number, windowMinutes: number): BetCancelAnswer {
  if (!online) return "offline";
  if (!operatorAllows) return "operator_off";
  if (gameStarted) return "game_started";
  if (minutesSince > windowMinutes) return "too_late";
  if (!managerApproved) return "manager_needed";
  return "ok";
}
export const betTwoPersonNeeded = (amount: number, ownerAmount: number | null): boolean => ownerAmount !== null && amount >= ownerAmount;
/** Stakes kept just under a reporting amount: a money-washing warning for the operator when there are enough of them. */
export function betSplitting(stakes: readonly number[], reportThreshold: number): boolean {
  const band = Math.floor((reportThreshold * BETTING.flags.split_band_bps) / 10_000);
  return stakes.filter((s) => s >= band && s < reportThreshold).length >= BETTING.flags.stake_splitting;
}
/** One period with an operator: positive, the shop owes the operator; negative, the operator owes the shop. */
export const betSettlement = (stakes: number, payouts: number, commission: number): number => whole(stakes, "stakes") - whole(payouts, "payouts") - whole(commission, "commission");
