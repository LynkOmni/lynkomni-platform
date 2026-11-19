/** Key tones and press vibration for every device emulator (EMULATOR UPDATE 70.6; owner, 19 November 2026): like a real device,
 *  keys of different kinds sound different. Each number key has its own telephone keypad pair; confirm, cancel, clear, moving
 *  around, tabs, switches, scanning and printing each have their own tone. A PIN, door code or ID number follows the manager's
 *  choice (each key its own pair, or one same tone so nobody nearby can tell the keys apart). The tones are the design tokens. */
import type { Tones } from "./emulators.js";

export type Sound = "key" | "confirm" | "cancel" | "error" | "scan" | "paid" | "printer" | "pin_same" | "clear" | "nav" | "tab" | "toggle_on" | "toggle_off"
  /** a number key: its own telephone keypad pair from the tokens ("digit:5", "digit:*") */
  | `digit:${string}`;
/** The shared tone set (design/tokens.v1.json sounds, generated as ts/src/sounds.generated.ts). */
export interface SoundSet { volume_gain: Readonly<Record<string, number>>; tones: Readonly<Record<string, ReadonlyArray<readonly [number, number]>>>; vibrate: Readonly<Record<string, ReadonlyArray<number>>>;
  keypad?: Readonly<Record<string, readonly [number, number]>>; keypad_ms?: number }

/** One audio context for every press: browsers allow only a few, and opening one per key would slow the first tap. */
let shared: AudioContext | undefined;
/** The tone and vibration for one press, from the design tokens; silent where the browser has no sound or vibration. */
export function playSound(snd: SoundSet, kind: Sound, s: Pick<Tones, "tones" | "vibration" | "volume">): void {
  if (typeof window === "undefined") return;
  try {
    const digit = kind.startsWith("digit:") ? kind.slice(6) : "";
    if (s.vibration && typeof navigator !== "undefined" && "vibrate" in navigator) navigator.vibrate(snd.vibrate[digit ? "digit" : kind] ?? snd.vibrate["key"] ?? []);
    if (!s.tones) return;
    const AC = (window as unknown as { AudioContext?: typeof AudioContext }).AudioContext; if (!AC) return;
    const ac = (shared ??= new AC()), gain = snd.volume_gain[s.volume] ?? snd.volume_gain["medium"] ?? 0.06;
    if (ac.state === "suspended") void ac.resume();
    let at = ac.currentTime;
    const pair = digit ? snd.keypad?.[digit] : undefined;
    if (pair) {            // a number key: its two keypad frequencies together, like a real phone or terminal keypad
      const len = (snd.keypad_ms ?? 70) / 1000;
      for (const hz of pair) {
        const o = ac.createOscillator(), g = ac.createGain();
        o.frequency.value = hz; g.gain.setValueAtTime(0.0001, at); g.gain.exponentialRampToValueAtTime(gain / 2, at + 0.008); g.gain.exponentialRampToValueAtTime(0.0001, at + len);
        o.connect(g).connect(ac.destination); o.start(at); o.stop(at + len + 0.02);
      }
      return;
    }
    for (const [hz, ms] of snd.tones[kind] ?? snd.tones["key"] ?? []) {
      if (hz > 0) {
        const o = ac.createOscillator(), g = ac.createGain();
        o.frequency.value = hz; g.gain.setValueAtTime(0.0001, at); g.gain.exponentialRampToValueAtTime(gain, at + 0.008); g.gain.exponentialRampToValueAtTime(0.0001, at + ms / 1000);
        o.connect(g).connect(ac.destination); o.start(at); o.stop(at + ms / 1000 + 0.02);
      }
      at += ms / 1000;
    }
  } catch { /* no sound on this device: every press also shows on the screen */ }
}

/** Where a typed number must stay private: a PIN, a door code or an ID number. Those keys follow the manager's choice (70.6):
 *  the keypad pairs, or one same tone on every key so nobody nearby can tell them apart. */
export const PRIVATE_ENTRY = ".lock, .pinpad, .ph-door, [data-private-entry]";
/** What a control's action says about the key, without a screen of its own: a number key ("d5", "pin:5", "at:digit:5", "d00"),
 *  star and hash, clear, cancel or back, moving around, a tab, confirm. Shared by every emulator (owner, 19 November 2026):
 *  like a real device, keys of different kinds sound different. */
export function soundForAct(act: string, o: { primary?: boolean; pressed?: boolean | null; privateEntry?: boolean; pinTones?: "same" | "per_key"; text?: string } = {}): Sound {
  const a = act;
  const num = /^(?:d|digit:|pin:|at:digit:|key:)(\d{1,2}|\*|#)$/.exec(a)?.[1] ?? (a === "star" ? "*" : a === "hash" ? "#" : (/^\d$/.test(o.text ?? "") && !a.includes(":") ? o.text : undefined));
  if (num !== undefined) return o.privateEntry && o.pinTones === "same" ? "pin_same" : (`digit:${num.slice(-1)}` as Sound);
  if (o.primary || /(^|:)(ok|enter|confirm|accept|save|send|charge|done|call)$/.test(a)) return "confirm";
  if (/(^|:)(clear|backspace|del|delete)$/.test(a) || a === "pin:clear") return "clear";
  if (/(^|:)(cancel|back|deny|end|close)$/.test(a)) return "cancel";
  if (o.pressed === true) return "toggle_off";
  if (o.pressed === false) return "toggle_on";
  if (/^(tab:|dsh:tab|qu:sec:)/.test(a)) return "tab";
  if (/^(pad:(up|down|left|right)|nav:|menu$|go:|soft:|cat:|sheet:)/.test(a)) return "nav";
  if (/(^|:)(scan|scanner)$/.test(a)) return "scan";
  if (/(^|:)(print|reprint)$/.test(a)) return "printer";
  return "key";
}
