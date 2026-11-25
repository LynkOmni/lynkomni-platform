// Phone number and email checks: the TypeScript port of core/phone.py (section 4C point 1, owner 2026-11-25). The rules come only
// from the country pack's phone block (pack.ph, from tools/country_phone.py); nothing here names a country. The shared cases in
// contract/vectors/phone.v1.json (python3 tools/phone_vectors.py) keep the two the same.

import { DIGIT_ZEROS } from "./phone.generated.js";

export interface PhoneKind { lengths: number[]; groups: Record<string, number[]>; sample: string }
export interface PhoneRules { code: string; prefix: string; main?: boolean; mobile: PhoneKind; any: PhoneKind }
/** No rule about how a number starts (owner, 2026-11-25: new networks can start numbers with any digit). */
export type PhoneState = "empty" | "long" | "typing" | "short" | "ok";
export interface PhoneCheck { state: PhoneState; lengths: number[]; max: number }

const PH_RANGE = Array.from({ length: 12 }, (_, i) => i + 4);
/** A territory with no numbering plan of its own: 4 to 15 digits, any first digit. */
export const GENERIC_PHONE: PhoneRules = { code: "", prefix: "", main: false, mobile: { lengths: PH_RANGE, groups: {}, sample: "" }, any: { lengths: PH_RANGE, groups: {}, sample: "" } };

export const phoneRules = (r: PhoneRules | null | undefined): PhoneRules => r ?? GENERIC_PHONE;
const phKind = (r: PhoneRules, mobile: boolean): PhoneKind => (mobile ? r.mobile : r.any);
/** Every decimal digit of any script as 0 to 9 (the same as unicodedata.decimal in core/phone.py). */
export function asciiDigits(text: string): string {
  let out = "";
  for (const ch of text || "") {
    const c = ch.codePointAt(0) as number;
    if (c < 0x80) { out += ch; continue; }
    const z = DIGIT_ZEROS.find((zero) => c >= zero && c <= zero + 9);
    out += z === undefined ? ch : String(c - z);
  }
  return out;
}
const phDigits = (t: string): string => asciiDigits(t).replace(/[^0-9]/g, "");

/** Digits only, the trunk prefix taken off: a leading 0 once more digits follow it; any other prefix (1, 8, 06) only when the
 *  number is too long with it and the right length without it (the same as core/phone.py clean). */
export function phoneClean(r: PhoneRules, text: string): string {
  let d = phDigits(text);
  const p = r.prefix || "", m = r.mobile.lengths;
  if (p && d.startsWith(p) && d.length > p.length && (p === "0" || d.length > Math.max(...r.any.lengths) || (!m.includes(d.length) && m.includes(d.length - p.length)))) d = d.slice(p.length);
  return d;
}

/** Every pack's dialling code, for reading a number pasted with + and a code (the sample pack is left out). */
export function phoneCodes(packs: Record<string, { ph?: PhoneRules | null; sample?: boolean }>): Record<string, string[]> {
  const out: Record<string, string[]> = {};
  for (const c of Object.keys(packs).sort()) { const p = packs[c]; if (!p || p.sample || !p.ph?.code) continue; (out[p.ph.code] ??= []).push(c); }
  return out;
}

/** A number pasted or typed with + (or 00) and a dialling code: [country, national digits]. */
export function phoneReadPasted(text: string, current: string, rulesFor: (c: string) => PhoneRules, codes: Record<string, string[]>): [string, string] {
  const t = asciiDigits(text || "").trim();
  if (!t.startsWith("+") && !t.startsWith("00")) return [current, phoneClean(rulesFor(current), t)];
  let d = phDigits(t); if (t.startsWith("00")) d = d.slice(2);
  for (const n of [3, 2, 1]) {
    const cc = d.slice(0, n), rest = d.slice(n), list = codes[cc];
    if (!list) continue;
    if (rulesFor(current).code === cc) return [current, phoneClean(rulesFor(current), rest)];
    const best = list.find((c) => rulesFor(c).main) ?? (list[0] as string);
    return [best, phoneClean(rulesFor(best), rest)];
  }
  return [current, phoneClean(rulesFor(current), d)];
}

/** Where the typed number stands (see core/phone.py check). */
export function phoneCheck(r: PhoneRules, digits: string, mobile = true, submit = false): PhoneCheck {
  const k = phKind(r, mobile);
  const out = { lengths: k.lengths, max: Math.max(...k.lengths) };
  if (!digits) return { ...out, state: "empty" };
  if (digits.length > out.max) return { ...out, state: "long" };
  if (k.lengths.includes(digits.length)) return { ...out, state: "ok" };
  return { ...out, state: submit ? "short" : "typing" };
}

/** What a field keeps of what was typed: never more digits than the country's longest number. */
export const phoneAccept = (r: PhoneRules, digits: string, mobile = true): string => digits.slice(0, Math.max(...phKind(r, mobile).lengths));

/** The number in the country's groups; a partial number follows the groups of the shortest length it can still be. */
export function phoneGroups(r: PhoneRules, digits: string, mobile = true): string {
  const k = phKind(r, mobile);
  let g = k.groups[String(digits.length)];
  if (!g) { const fits = Object.keys(k.groups).map(Number).filter((L) => L >= digits.length); g = fits.length ? k.groups[String(Math.min(...fits))] : undefined; }
  if (!g) return digits;
  const out: string[] = []; let i = 0;
  for (const n of g) { if (i >= digits.length) break; out.push(digits.slice(i, i + n)); i += n; }
  if (i < digits.length) out.push(digits.slice(i));
  return out.join(" ");
}

export const phoneSample = (r: PhoneRules, mobile = true): string => { const k = phKind(r, mobile); return k.sample ? phoneGroups(r, k.sample, mobile) : ""; };
/** The one saved form: + dialling code + national digits. */
export const phoneInternational = (r: PhoneRules, digits: string): string => "+" + (r.code || "") + digits;
/** The lengths as an error says them: {one}, {from, to} or {list}. */
export function phoneLengths(lengths: number[]): { one?: number; from?: number; to?: number; list?: number[] } {
  const ls = [...lengths].sort((a, b) => a - b);
  if (ls.length === 1) return { one: ls[0] as number };
  const run = ls.every((v, i) => i === 0 || v === (ls[i - 1] as number) + 1);
  if (run && ls.length > 2) return { from: ls[0] as number, to: ls[ls.length - 1] as number };
  return { list: ls };
}

// ---- email -------------------------------------------------------------------------------------------------------------------
export interface EmailDomains { common: string[]; throwaway: string[] }
export interface EmailCheck { state: "empty" | "format" | "throwaway" | "ok"; suggest: string }
const PH_EMAIL = /^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)*\.[A-Za-z]{2,}$/;
function phDistance(a: string, b: string): number {
  let prev = Array.from({ length: b.length + 1 }, (_, i) => i);
  for (let i = 1; i <= a.length; i++) {
    const cur = [i];
    for (let j = 1; j <= b.length; j++) cur.push(Math.min((prev[j] as number) + 1, (cur[j - 1] as number) + 1, (prev[j - 1] as number) + (a[i - 1] === b[j - 1] ? 0 : 1)));
    prev = cur;
  }
  return prev[b.length] as number;
}
/** Format, "Did you mean" for a domain one or two letters from a common one, throwaway domains refused only when deep. */
export function emailCheck(D: EmailDomains, text: string, deep = false): EmailCheck {
  const t = (text || "").trim();
  if (!t) return { state: "empty", suggest: "" };
  if (t.length > 254 || !PH_EMAIL.test(t) || t.includes("..")) return { state: "format", suggest: "" };
  const at = t.lastIndexOf("@"), local = t.slice(0, at), d = t.slice(at + 1).toLowerCase();
  let suggest = "";
  if (!D.common.includes(d)) {
    const near = D.common.map((c) => [phDistance(d, c), c] as [number, string]).sort((x, y) => x[0] - y[0] || (x[1] < y[1] ? -1 : x[1] > y[1] ? 1 : 0))[0];
    if (near && near[0] > 0 && near[0] <= (d.length >= 8 ? 2 : 1)) suggest = `${local}@${near[1]}`;
  }
  if (deep && D.throwaway.includes(d)) return { state: "throwaway", suggest: "" };
  return { state: "ok", suggest };
}
