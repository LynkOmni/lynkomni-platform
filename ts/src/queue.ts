/** LynkQueue ticket rules (LynkQ, NEW UPDATE 4, blueprint section 63): the TypeScript port of core/queue_tickets.py, checked on
 *  contract/vectors/people.v1.json. A ticket number is the section code and a 6-character Lynk Code (LAB-A2K9P2): 1,073,741,824 codes
 *  for each section at each place, never used twice, rude words skipped; a fair order where staff never choose. */
export const ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ";
export const CODE_LENGTH = 6, SECTION_LENGTH = 3, CAPACITY = ALPHABET.length ** CODE_LENGTH;
export const CALLS_BEFORE_MISSED = 3, PUT_BACK_MINUTES = 15, PUT_BACK_AFTER = 3, RUNNING_LATE_PLACES = 3, PRIORITY_BALANCE = 3;
export const APPOINTMENT_GRACE_MINUTES = 10, PLEASE_COME_AT = 5, BLOCK_SIZE = 1000;
export const BLOCKED = ["FUCK", "FUK", "FCK", "SHT", "CUNT", "DCK", "PUSY", "PUSSY", "SLUT", "WHRE", "RAPE", "NAZ", "KKK", "XXX", "SEX", "ANAL", "ANUS",
  "CUM", "TWAT", "WANK", "FAG", "NGGA", "NGR", "PUTA", "PUTE", "MERDE", "SUCK", "KYS", "STFU", "WTF", "KILL"] as const;

export function code(n: number): string {
  if (!(Number.isInteger(n) && n >= 0 && n < CAPACITY)) throw new Error("no such code");
  let out = "";
  for (let k = 0; k < CODE_LENGTH; k++) { out = ALPHABET[n % ALPHABET.length]! + out; n = Math.floor(n / ALPHABET.length); }
  return out;
}
export const validCode = (c: unknown): c is string => typeof c === "string" && c.length === CODE_LENGTH && [...c].every((ch) => ALPHABET.includes(ch));
export function index(c: string): number {
  if (!validCode(c)) throw new Error(`${c} is not a Lynk Code`);
  return [...c].reduce((n, ch) => n * ALPHABET.length + ALPHABET.indexOf(ch), 0);
}
export const rude = (text: string): boolean => BLOCKED.some((w) => text.includes(w));
export const validSection = (s: unknown): boolean => typeof s === "string" && s.length === SECTION_LENGTH && [...s].every((ch) => ALPHABET.includes(ch)) && !rude(s);
export function nextCode(after: string | null): string | null {
  for (let n = after === null ? 0 : index(after) + 1; n < CAPACITY; n++) { const c = code(n); if (!rude(c)) return c; }
  return null;
}
export const ticketNumber = (section: string, c: string): string => `${section}-${c}`;
export function reserveBlock(after: string | null, size = BLOCK_SIZE): { first: string; last: string } | null {
  const first = nextCode(after);
  return first === null ? null : { first, last: code(Math.min(index(first) + size - 1, CAPACITY - 1)) };
}
export interface Waiting { id: string; seq: number; priority?: boolean; appointment?: number | null; held?: boolean }
export function pickNext(waiting: readonly Waiting[], servedSincePriority: number, nowMinute: number, balance = PRIORITY_BALANCE): string | null {
  const live = waiting.filter((t) => !t.held);
  if (!live.length) return null;
  const appt = (t: Waiting): number | null => t.appointment ?? null;
  const due = live.filter((t) => appt(t) !== null && appt(t)! <= nowMinute + APPOINTMENT_GRACE_MINUTES).sort((a, b) => appt(a)! - appt(b)! || a.seq - b.seq);
  if (due.length) return due[0]!.id;
  const normal = live.filter((t) => !t.priority && appt(t) === null).sort((a, b) => a.seq - b.seq);
  const prio = live.filter((t) => t.priority && appt(t) === null).sort((a, b) => a.seq - b.seq);
  if (prio.length && (servedSincePriority >= balance || !normal.length)) return prio[0]!.id;
  if (normal.length) return normal[0]!.id;
  return [...live].sort((a, b) => (appt(a) ?? 0) - (appt(b) ?? 0) || a.seq - b.seq)[0]!.id;
}
export const placeOf = (id: string, order: readonly string[]): number => order.indexOf(id) + 1;
export const waitMinutes = (place: number, avg: number, open: number): number | null => (open < 1 ? null : Math.ceil((place * avg) / open));
export function putBack(order: readonly string[], id: string, missedMinute: number, nowMinute: number): string[] | null {
  if (nowMinute - missedMinute > PUT_BACK_MINUTES) return null;
  const rest = order.filter((t) => t !== id), at = Math.min(PUT_BACK_AFTER, rest.length);
  return [...rest.slice(0, at), id, ...rest.slice(at)];
}
export function runningLate(order: readonly string[], id: string): string[] {
  const rest = order.filter((t) => t !== id), at = Math.min(order.indexOf(id) + RUNNING_LATE_PLACES, rest.length);
  return [...rest.slice(0, at), id, ...rest.slice(at)];
}
