// One-time codes sent to a phone or an email, and the reader's own digits (section 4C point 1). A small part of its own so a
// page that only asks for a code (the survey page) carries this, not the whole phone and email field part (ts/src/fields.ts).
// Its numbers come from core/phone.py CODES through ts/src/phone.generated.ts; contract/vectors/phone.v1.json keeps them the same.
import { DIGIT_ZEROS, CODES } from "./phone.generated.js";

type CfT = (k: string, v?: Record<string, string | number>) => string;
export interface CodeLook { t: CfT; lang: string }
const cfEsc = (v: string): string => String(v).replace(/&/g, "&amp;").replace(/"/g, "&quot;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

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
const CF_DIGITS: Record<string, string[] | null> = {};
/** Digits in the reader's own numbering system, like every number on screen. */
export function ownDigits(text: string, lang: string): string {
  if (!(lang in CF_DIGITS)) {
    try { const nf = new Intl.NumberFormat(lang, { useGrouping: false }); const ds = "0123456789".split("").map((d) => nf.format(Number(d))); CF_DIGITS[lang] = ds.join("") === "0123456789" ? null : ds; }
    catch { CF_DIGITS[lang] = null; }
  }
  const ds = CF_DIGITS[lang];
  return ds ? text.replace(/[0-9]/g, (d) => ds[Number(d)] as string) : text;
}
/** Seconds still to wait before another code may be sent (the same as core/phone.py resend_wait). */
export function resendWait(sent: number[], now: number): number {
  const hour = sent.filter((t) => now - t < 3600);
  if (hour.length >= CODES.per_hour) return Math.trunc(Math.min(...hour) + 3600 - now + 0.999);
  if (!hour.length) return 0;
  const steps = CODES.resend_wait_s, need = steps[Math.min(hour.length - 1, steps.length - 1)] as number;
  return Math.max(0, Math.trunc(Math.max(...hour) + need - now + 0.999));
}
const cfClock = (s: number, lang: string): string => ownDigits(`${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`, lang);

export interface CodeFieldOpts { id: string; label: string; value: string; act?: string; resendAct?: string; sent?: number[]; now?: number }
/** A one-time code field: digits only, never more than the code's length, filled by the phone from the text message where it
 *  can (autocomplete one-time-code) and from a paste. No example value is shown (a code is a sensitive field). Beside it, Send a
 *  new code waits the growing time core/phone.py sets and counts it down (wireCodes). */
export function codeFieldHtml(look: CodeLook, o: CodeFieldOpts): string {
  const v = asciiDigits(o.value || "").replace(/[^0-9]/g, "").slice(0, CODES.length);
  const wait = o.resendAct ? resendWait(o.sent ?? [], o.now ?? Date.now() / 1000) : 0;
  return `<div class="lf-field" data-code="${cfEsc(o.id)}">
    <label for="${cfEsc(o.id)}">${cfEsc(o.label)}</label>
    <input class="text lf-in lf-code" id="${cfEsc(o.id)}" type="text" inputmode="numeric" autocomplete="one-time-code" dir="ltr" maxlength="${CODES.length}" value="${cfEsc(v)}"${o.act ? ` data-in="${cfEsc(o.act)}"` : ""}>
    ${o.resendAct ? `<button type="button" class="ghost lf-resend" data-act="${cfEsc(o.resendAct)}" data-wait-s="${wait}" ${wait ? "disabled" : ""}>${cfEsc(wait ? look.t("fd_code_wait", { time: cfClock(wait, look.lang) }) : look.t("fd_code_new"))}</button>` : ""}
  </div>`;
}
/** Call after every draw: keeps code fields to digits and counts the resend wait down. */
export function wireCodes(root: ParentNode, look: CodeLook): void {
  root.querySelectorAll<HTMLElement>("[data-code]").forEach((box) => {
    if (box.dataset.lfWired) return; box.dataset.lfWired = "1";
    const input = box.querySelector<HTMLInputElement>("input"), again = box.querySelector<HTMLButtonElement>(".lf-resend");
    if (input) input.addEventListener("input", () => { const d = asciiDigits(input.value).replace(/[^0-9]/g, "").slice(0, CODES.length); if (d !== input.value) input.value = d; });
    if (!again) return;
    let left = Number(again.dataset.waitS || "0");
    const tick = (): void => {
      if (!again.isConnected) return;
      left -= 1;
      if (left <= 0) { again.disabled = false; again.textContent = look.t("fd_code_new"); return; }
      again.textContent = look.t("fd_code_wait", { time: cfClock(left, look.lang) }); setTimeout(tick, 1000);
    };
    if (left > 0) setTimeout(tick, 1000);
  });
}
