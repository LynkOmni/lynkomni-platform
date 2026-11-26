/** Field hints (PLACEHOLDER UPDATE 83, catalog/placeholders.v1.json): a small part of its own so every page whose fields use it
 *  carries only this, not the whole placeholder part. */
const hEsc = (v: string): string => v.replace(/&/g, "&amp;").replace(/"/g, "&quot;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
/** Field hints. Format hints are the same in every language (no words); word hints come from the page's words as hint_<kind>.
 *  Sensitive fields (PINs, passwords, card details, one-time codes, recovery codes) never get a hint that looks like a value. */
export type HintKind = "amount" | "count" | "email" | "username" | "phone" | "code_short" | "country" | "search" | "name" | "note" | "ask" | "answer" | "section" | "question" | "yousaid" | "shop";
/** Format hints. Every handle field (username, shop, business, developer app, partner, agent point) shows "@username":
 *  the @ shows how a handle is written, and a typed @ is ignored (usernames.ts normalize; owner 2026-11-26). The shared
 *  shell writes the same plain string, so it needs no import (tests/test_placeholders.py HandleHint keeps them equal). */
export const FORMAT_HINTS: Partial<Record<HintKind, string>> = { amount: "0", count: "0", email: "name@example.com", username: "@username", phone: "123 456 789", code_short: "A1" };
export const SENSITIVE = ["pin", "password", "card", "otp", "one-time-code", "recovery", "cvv"] as const;
/** Digits in the reader's own numbering system (Arabic-Indic, Bengali, Devanagari and the rest), like every number on screen. */
export function readerDigits(text: string, lang?: string): string {
  if (!lang) return text;
  let nf: Intl.NumberFormat;
  try { nf = new Intl.NumberFormat(lang, { useGrouping: false }); } catch { return text; }
  return text.replace(/[0-9]/g, (d) => nf.format(Number(d)));
}
/** Number hints use the reader's own digits. A country hint is the page's own country code, passed by the caller (no country is
 *  written in code: core/regions.py and the packs hold them). */
export function hintFor(kind: HintKind, t: (k: string) => string, lang?: string, example?: string): string {
  if (kind === "country") return example ?? "";
  const f = FORMAT_HINTS[kind];
  if (f !== undefined) return kind === "email" || kind === "username" ? f : readerDigits(f, lang);
  return t(`hint_${kind}`);   // screens write word hints as literal keys (t("hint_name")) so a page carries only the words it uses
}
/** A hint attribute pair for a field; empty for sensitive fields. The visible label (or aria-label) is never replaced. */
export function hintAttr(kind: HintKind | null, t: (k: string) => string, lang?: string, example?: string): string {
  return kind ? ` placeholder="${hEsc(hintFor(kind, t, lang, example))}"` : "";
}
