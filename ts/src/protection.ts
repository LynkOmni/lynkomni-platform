/** Account protections on screen (MASTER UPDATE, master blueprint sections 55 and 59; build section 2).
 *  The rules are identity/protection.py's (the cloud enforces them); the screens only show them: how long a cool-off or a
 *  contact change waits (normal or advanced protection), which acts are held, and the card group names. Values come from
 *  parts.generated.ts and are checked by contract/vectors/parts.v1.json. */
import { CARD_GROUP_NAMES, CARD_TIER_WORD, PROTECTION } from "./parts.generated.js";

export const coolOffSeconds = (advanced: boolean): number => (advanced ? PROTECTION.advanced_cool_off_s : PROTECTION.cool_off_s);
export const contactWaitSeconds = (advanced: boolean): number => (advanced ? PROTECTION.advanced_contact_wait_s : PROTECTION.contact_wait_s);
/** Whether a held act may run now, as the cloud decides it: a locked account does nothing sensitive, and a held act waits out the cool-off. */
export function mayNow(act: string, o: { locked: boolean; heldUntil: number; now: number }): { ok: boolean; why?: "locked" | "cool_off" } {
  if (!(PROTECTION.held_acts as string[]).includes(act)) throw new Error(`${act} is not a held act`);
  if (o.locked) return { ok: false, why: "locked" };
  if (o.heldUntil > o.now) return { ok: false, why: "cool_off" };
  return { ok: true };
}
/** "LynkDyna Pro": the group name and the tier word; names stay the same in every language. */
export const cardPlanName = (group: string, tier: string): string => `${CARD_GROUP_NAMES[group] ?? group} ${CARD_TIER_WORD[tier] ?? tier}`;
export const TERMS_IN_FORCE = PROTECTION.terms;
