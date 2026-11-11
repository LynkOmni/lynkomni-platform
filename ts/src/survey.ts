/** LynkSurvey rules (LynkS, NEW UPDATE 4, blueprint section 63): the TypeScript port of core/surveys.py, checked on
 *  contract/vectors/people.v1.json. One person, one answer; anonymous means anonymous (never a result for fewer than 5);
 *  "Real answers only" flags and never deletes; sample size and margins at 95% confidence. */
export const RULES = ["open", "one_per_phone", "invited", "verified"] as const;
export const MIN_GROUP = 5, Z95 = 1.96, SECONDS_PER_QUESTION_MIN = 2, PERSONAL_DEVICE_DAILY_MAX = 3, REMINDERS_MAX = 2, DEFAULT_REST_DAYS = 30;
export function sampleSize(marginPercent: number, population?: number | null): number {
  const e = marginPercent / 100;
  let n0 = (Z95 * Z95 * 0.25) / (e * e);
  if (population) n0 = n0 / (1 + (n0 - 1) / population);
  return Math.ceil(Math.floor(n0 * 1e6 + 0.5) / 1e6);
}
export function margin(sharePercent: number, answers: number): number | null {
  if (answers < 1) return null;
  const p = sharePercent / 100;
  return Math.floor(Z95 * Math.sqrt((p * (1 - p)) / answers) * 1000 + 0.5);
}
export const canShow = (groupSize: number): boolean => groupSize >= MIN_GROUP;
export function mayAnswer(rule: string, already: boolean, invite = false, signedIn = false, phone = false): string | null {
  if (!(RULES as readonly string[]).includes(rule)) throw new Error(`${rule} is not a rule`);
  if (already) return "already_answered";
  if (rule === "one_per_phone" && !phone) return "confirm_phone_first";
  if (rule === "invited" && !invite) return "invitation_needed";
  if (rule === "verified" && !signedIn) return "sign_in_needed";
  return null;
}
export function realAnswerFlags(seconds: number, questions: number, same: boolean, today: number, shared: boolean): string[] {
  const out: string[] = [];
  if (questions > 0 && seconds < questions * SECONDS_PER_QUESTION_MIN) out.push("too_fast");
  if (same && questions >= 5) out.push("same_pattern");
  if (!shared && today > PERSONAL_DEVICE_DAILY_MAX) out.push("many_from_one_device");
  return out;
}
export const groupOpen = (group: string, counts: Record<string, number>, targets: Record<string, number>): boolean =>
  targets[group] === undefined || (counts[group] ?? 0) < targets[group]!;
export const mayAskAgain = (daysSinceLast: number | null, restDays = DEFAULT_REST_DAYS, optedOut = false): boolean =>
  !optedOut && (daysSinceLast === null || daysSinceLast >= restDays);
