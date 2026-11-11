/** LynkAttend rules (LynkA, NEW UPDATE 4, blueprint section 63): the TypeScript port of core/attendance.py, checked on
 *  contract/vectors/people.v1.json. PIN first; then the set's means in the order Face, Finger, IDCN; 3 tries for Face or Finger,
 *  5 for IDCN; every backup is marked. A PIN, an IDCN or an ID number never goes into an event. */
export const ATTEND_SETS = ["face_finger_idcn", "face_idcn", "finger_idcn", "idcn"] as const;
export type AttendSet = (typeof ATTEND_SETS)[number];
export type Means = "face" | "finger" | "idcn";
const ORDER: readonly Means[] = ["face", "finger", "idcn"];
export const PIN_LENGTH = 6, IDCN_LENGTH = 6, IDCN_MIN_DIGITS = 4, BIOMETRIC_TRIES = 3, IDCN_TRIES = 5;
export const PIN_TRIES_BEFORE_PAUSE = 5, PIN_PAUSE_SECONDS = 60, PIN_GROUP_WARN_PERCENT = 90, NO_CHECK_OUT_AFTER_MINUTES = 120;

/** The IDCN from a full ID number, or null when it has too few digits (register another ID document). */
export function idcn(fullIdNumber: string): string | null {
  const digits = [...fullIdNumber].filter((c) => c >= "0" && c <= "9").join("");
  if (digits.length < IDCN_MIN_DIGITS) return null;
  return digits.slice(-IDCN_LENGTH).padEnd(IDCN_LENGTH, "0");
}
export function meansOf(set: string): Means[] {
  if (!(ATTEND_SETS as readonly string[]).includes(set)) throw new Error(`${set} is not a set`);
  const parts = set.split("_");
  return ORDER.filter((m) => parts.includes(m));
}
export const setsAllowed = (face: boolean, finger: boolean): AttendSet[] =>
  ATTEND_SETS.filter((s) => (!s.includes("face") || face) && (!s.includes("finger") || finger));

export function isEasyPin(pin: string): boolean {
  if (pin.length !== PIN_LENGTH || !/^\d+$/.test(pin)) return true;
  const d = [...pin].map(Number);
  if (new Set(d).size === 1) return true;
  const steps = new Set(d.slice(1).map((x, i) => x - d[i]!));
  if (steps.size === 1 && (steps.has(1) || steps.has(-1))) return true;
  return pin === pin.slice(0, 2).repeat(3) || pin === pin.slice(0, 3).repeat(2);
}
let easy = 0;
for (let n = 0; n < 10 ** PIN_LENGTH; n++) if (isEasyPin(String(n).padStart(6, "0"))) easy++;
export const EASY_PIN_COUNT = easy;
export const PIN_GROUP_SIZE = 10 ** PIN_LENGTH - easy;
export const pinGroupWarning = (used: number): boolean => used * 100 >= PIN_GROUP_SIZE * PIN_GROUP_WARN_PERCENT;

export interface DoorStep { means: Means; try?: number; result: "ok" | "fail" | "not_working" }
export interface DoorOut { steps: DoorStep[]; result: "in" | "pin_blocked" | "see_manager" | "waiting"; means: Means | null; backup_from: string | null }
/** Runs the door for one person after their PIN (see core/attendance.py door). */
export function door(set: string, attempts: readonly ("ok" | "fail")[], broken: readonly string[] = []): DoorOut {
  const steps: DoorStep[] = [];
  let i = 0, backup: string | null = null;
  for (const means of meansOf(set)) {
    if (broken.includes(means)) { steps.push({ means, result: "not_working" }); backup ??= `${means}_not_working`; continue; }
    const tries = means === "idcn" ? IDCN_TRIES : BIOMETRIC_TRIES;
    for (let t = 1; t <= tries; t++) {
      if (i >= attempts.length) return { steps, result: "waiting", means, backup_from: backup };
      const outcome = attempts[i++]!;
      steps.push({ means, try: t, result: outcome });
      if (outcome === "ok") return { steps, result: "in", means, backup_from: backup };
    }
    if (means === "idcn") return { steps, result: "pin_blocked", means: null, backup_from: backup };
    backup ??= `${means}_failed`;
  }
  return { steps, result: "see_manager", means: null, backup_from: backup };
}
export const checkerChoices = (checkers: readonly string[], me: string): string[] => checkers.filter((c) => c !== me);
export const checkerFlags = (checkerCheckedIn: boolean): string[] => (checkerCheckedIn ? [] : ["checker_not_checked_in"]);
export function noCheckOutDue(checkInMinute: number, shiftEndMinute: number | null): number {
  if (shiftEndMinute === null) return 1440;
  return shiftEndMinute >= checkInMinute ? Math.min(shiftEndMinute + NO_CHECK_OUT_AFTER_MINUTES, 1440) : 1440;
}
