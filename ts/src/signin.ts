/** Shared sign-in parts (MASTER UPDATE, master blueprint section 55; build section 1): the PIN pad and number matching.
 *  The rules are identity/offline.py's (PIN 4 to 8 digits, never a repeated or running number; waits after wrong tries; a hard
 *  lock after ten that never destroys anything), carried in parts.generated.ts and checked by contract/vectors/parts.v1.json.
 *
 *  The PIN pad works for everyone: each digit key also shows a picture of that many dots (zero is an empty ring), so a person who
 *  reads numbers with difficulty can still use it; each key has its own tone (the telephone keypad tones), so a person who cannot
 *  see the screen hears each press; the digits typed are never shown, only filled dots; the keys never move. */
import { PIN_RULE } from "./parts.generated.js";
import { esc } from "./shell.js";
import type { Icon, T } from "./shell.js";

export type PinProblem = null | "length" | "pattern";
/** Same rule as identity/offline.py pin_problem. */
export function pinProblem(pin: string): PinProblem {
  if (!/^\d+$/.test(pin) || pin.length < PIN_RULE.min || pin.length > PIN_RULE.max) return "length";
  if (new Set(pin).size === 1 || "0123456789".includes(pin) || "9876543210".includes(pin)) return "pattern";
  return null;
}
/** Seconds to wait after this many wrong tries in a row (0 when none); "locked" from the hard-lock count on. */
export function afterWrong(wrong: number): number | "locked" {
  if (wrong >= PIN_RULE.hardLockAfter) return "locked";
  return PIN_RULE.delays[String(wrong)] ?? 0;
}

/** The telephone keypad tones: each key a pair of frequencies (Hz), so every press is heard and no two keys sound alike. */
export const KEY_TONE: Record<string, [number, number]> = {
  "1": [697, 1209], "2": [697, 1336], "3": [697, 1477], "4": [770, 1209], "5": [770, 1336], "6": [770, 1477],
  "7": [852, 1209], "8": [852, 1336], "9": [852, 1477], "0": [941, 1336], clear: [941, 1209], ok: [941, 1477],
};
/** A picture of n dots on a 3 x 3 grid (the dice layout; 0 is an empty ring), drawn with currentColor. */
export function dots(n: number): string {
  const P: Record<number, [number, number][]> = { 1: [[1, 1]], 2: [[0, 0], [2, 2]], 3: [[0, 0], [1, 1], [2, 2]], 4: [[0, 0], [2, 0], [0, 2], [2, 2]],
    5: [[0, 0], [2, 0], [1, 1], [0, 2], [2, 2]], 6: [[0, 0], [2, 0], [0, 1], [2, 1], [0, 2], [2, 2]], 7: [[0, 0], [2, 0], [0, 1], [1, 1], [2, 1], [0, 2], [2, 2]],
    8: [[0, 0], [1, 0], [2, 0], [0, 1], [2, 1], [0, 2], [1, 2], [2, 2]], 9: [[0, 0], [1, 0], [2, 0], [0, 1], [1, 1], [2, 1], [0, 2], [1, 2], [2, 2]] };
  const body = n === 0 ? '<circle cx="12" cy="12" r="7" fill="none" stroke="currentColor" stroke-width="2"/>'
    : (P[n] ?? []).map(([x, y]) => `<circle cx="${5 + x * 7}" cy="${5 + y * 7}" r="2.4" fill="currentColor"/>`).join("");
  return `<svg class="pdots" viewBox="0 0 24 24" aria-hidden="true" focusable="false">${body}</svg>`;
}

export interface PinPadState { entered: number; length: number; wrong: number; waitLeft: number; pictures: boolean; sound: boolean; title: string }
/** The pad: filled dots for what is typed, the twelve keys (1 to 9, clear, 0, OK) in fixed places, and the wait or lock message. */
export function pinPad(s: PinPadState, t: T, icon: Icon): string {
  const state = afterWrong(s.wrong);
  const locked = state === "locked", waiting = !locked && s.waitLeft > 0;
  const shown = Array.from({ length: Math.max(s.length, PIN_RULE.min) }, (_, i) => `<span class="pdot${i < s.entered ? " on" : ""}"></span>`).join("");
  const key = (k: string, label: string, aria: string) => `<button type="button" class="pkey${/^\d$/.test(k) ? "" : " fn"}" data-act="pin:${k}" aria-label="${esc(aria)}"${locked || waiting ? " disabled" : ""}><span class="pnum">${label}</span>${s.pictures && /^\d$/.test(k) ? dots(Number(k)) : ""}</button>`;
  const keys = ["1", "2", "3", "4", "5", "6", "7", "8", "9"].map((d) => key(d, d, d)).join("")
    + key("clear", icon("ui-undo"), t("pin_clear")) + key("0", "0", "0") + key("ok", icon("ui-check"), t("pin_ok"));
  const msg = locked ? `<p class="pmsg danger" role="alert">${icon("ui-lock")}<span>${esc(t("pin_locked"))}</span></p>`
    : waiting ? `<p class="pmsg warning" role="status">${esc(t("pin_wait", { s: s.waitLeft }))}</p>`
    : s.wrong ? `<p class="pmsg" role="status">${esc(t("pin_wrong", { n: PIN_RULE.hardLockAfter - s.wrong }))}</p>` : "";
  return `<div class="pinpad" role="group" aria-label="${esc(s.title)}"><p class="ptitle">${esc(s.title)}</p><div class="pdots-row" role="img" aria-label="${esc(t("pin_entered", { n: s.entered }))}">${shown}</div>${msg}<div class="pkeys">${keys}</div><div class="popts"><button type="button" class="chipbtn${s.pictures ? " on" : ""}" data-act="pin:pictures" aria-pressed="${s.pictures}">${esc(t("pin_pictures"))}</button><button type="button" class="chipbtn${s.sound ? " on" : ""}" data-act="pin:sound" aria-pressed="${s.sound}">${esc(t("pin_sound"))}</button></div>${locked ? `<p class="note">${esc(t("pin_locked_how"))}</p>` : ""}</div>`;
}

/** Number matching (face-to-face permission, identity/offline.py Approver): the approving device shows one two-digit number; the
 *  new device offers three and the person taps the same one. A wrong tap refuses the permission and nothing is granted. */
export function numberChoices(correct: string, rnd: () => number): string[] {
  const out = new Set<string>([correct]);
  while (out.size < 3) {                       // a weak or repeating random source can never stall it: step to the next free number
    let n = 10 + Math.floor(Math.abs(rnd()) * 90) % 90;
    while (out.has(String(n))) n = n === 99 ? 10 : n + 1;
    out.add(String(n));
  }
  const list = [...out];
  for (let i = list.length - 1; i > 0; i--) { const j = Math.floor(rnd() * (i + 1)); [list[i], list[j]] = [list[j]!, list[i]!]; }
  return list;
}
export function numberShown(n: string, t: T): string {
  return `<div class="nmatch shown" role="group" aria-label="${esc(t("match_show_title"))}"><p class="ptitle">${esc(t("match_show_title"))}</p><p class="nbig" aria-live="polite">${esc(n)}</p><p class="note">${esc(t("match_show_note"))}</p></div>`;
}
export function numberMatch(choices: string[], t: T, result: "" | "ok" | "wrong" = ""): string {
  const res = result === "ok" ? `<p class="pmsg success" role="status">${esc(t("match_ok"))}</p>` : result === "wrong" ? `<p class="pmsg danger" role="alert">${esc(t("match_wrong"))}</p>` : "";
  return `<div class="nmatch" role="group" aria-label="${esc(t("match_pick_title"))}"><p class="ptitle">${esc(t("match_pick_title"))}</p><div class="nchoices">${choices.map((c) => `<button type="button" class="nchoice" data-act="match:${esc(c)}"${result ? " disabled" : ""}>${esc(c)}</button>`).join("")}</div>${res}<p class="note">${esc(t("match_pick_note"))}</p></div>`;
}
