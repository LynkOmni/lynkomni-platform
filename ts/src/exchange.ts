/** LynkExchange's price and book-value rules (EXCHANGE UPDATE, master blueprint 65; section 4 step E4b): the TypeScript port of
 *  core/exchange.py, checked against contract/vectors/exchange.v1.json. The locked levels and tier parts travel in
 *  ts/src/exchange.generated.ts (python3 tools/exchange_vectors.py). Whole numbers only: a rate is a fraction, never a decimal. */
import { roundDiv } from "./books.js";

export type Levels = readonly (readonly [number, number])[];
const big = (n: number): bigint => BigInt(n);
const whole = (...v: unknown[]): boolean => v.every((x) => typeof x === "number" && Number.isInteger(x));

export function levelBps(levels: Levels, volume: number): number {
  if (volume < 0) throw new Error("a volume is never negative");
  let bps = levels[0]![1];
  for (const [start, part] of levels) if (volume >= start) bps = part;
  return bps;
}
export const partBps = (tierBps: number, levels: Levels, volume: number): number => Math.min(tierBps, levelBps(levels, volume));

export function quote(amount: number, rateNum: number, rateDen: number, part: number): { part: number; to_amount: number } {
  if (!whole(amount, rateNum, rateDen, part)) throw new Error("whole numbers only");
  if (amount <= 0 || rateNum <= 0 || rateDen <= 0 || !(part >= 0 && part < 10000)) throw new Error("an amount and a rate are more than nothing, and a part is below 100%");
  const fee = roundDiv(amount * part, 10000);
  return { part: fee, to_amount: Number((big(amount - fee) * big(rateNum)) / big(rateDen)) };
}

export function aboveMidBps(amount: number, toAmount: number, midNum: number, midDen: number): number {
  const atMid = Number((big(amount) * big(midNum)) / big(midDen));
  if (atMid <= 0) throw new Error("the mid-market rate gives nothing for this amount");
  return Math.max(0, roundDiv((atMid - toAmount) * 10000, atMid));
}

export function costOut(held: number, heldCost: number, spent: number): number {
  if (!(spent > 0 && spent <= held)) throw new Error("spend more than nothing and at most what is held");
  return spent === held ? heldCost : roundDiv(heldCost * spent, held);
}
