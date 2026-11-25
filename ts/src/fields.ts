// The phone and email fields and the field message (section 4C points 1 and 2, owner 2026-11-25). Every phone and email field in
// the ecosystem is drawn here (words in web/fields, prefix fd_; styles web/shell/fields.css); a screen never draws its own.
// Rules come from ts/src/phone.ts and the country pack's phone block, so nothing here names a country.
import { phoneRules, phoneCheck, phoneAccept, phoneGroups, phoneSample, phoneInternational, phoneLengths, phoneReadPasted, phoneCodes, type PhoneRules, type PhoneCheck, emailCheck } from "./phone.js";
import { EMAIL_DOMAINS } from "./phone.generated.js";

type T = (k: string, v?: Record<string, string | number>) => string;
export interface FieldPack { name: string; sample?: boolean; ph?: PhoneRules | null }
export interface FieldCtx {
  t: T; lang: string; packs: Record<string, FieldPack>; packOrder: string[]; countryName: (code: string) => string;
  onPhone?: (id: string, v: PhoneValue) => void; onEmail?: (id: string, v: EmailValue) => void;
}
export interface PhoneValue { country: string; digits: string; international: string; valid: boolean }
export interface EmailValue { text: string; valid: boolean }
export type Level = "error" | "warning" | "info" | "success";

const lfEsc = (v: string): string => String(v).replace(/&/g, "&amp;").replace(/"/g, "&quot;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
/** Digits in the reader's own numbering system, like every number on screen. */
export function ownDigits(text: string, lang: string): string {
  let nf: Intl.NumberFormat;
  try { nf = new Intl.NumberFormat(lang, { useGrouping: false }); } catch { return text; }
  return text.replace(/[0-9]/g, (d) => nf.format(Number(d)));
}
/** "6 or 2", "8, 9 or 10": a list joined the reader's way. */
function lfOrList(items: string[], lang: string): string {
  try { return new (Intl as unknown as { ListFormat: new (l: string, o: object) => { format: (x: string[]) => string } }).ListFormat(lang, { type: "disjunction" }).format(items); }
  catch { return items.join(" / "); }
}

/** Country names in the reader's language (the browser's own names; the pack's English name when it has none; the sample pack's own word). */
const LF_NAMES: Record<string, Record<string, string>> = {};
export function countryNamer(lang: string, packs: Record<string, FieldPack>, sampleWord: string): (code: string) => string {
  const memo = (LF_NAMES[lang] ??= {});
  let dn: { of: (c: string) => string | undefined } | null | undefined;
  return (code: string): string => {
    const p = packs[code]; if (p?.sample) return sampleWord;
    const hit = memo[code]; if (hit !== undefined) return hit;
    if (dn === undefined) { try { dn = new Intl.DisplayNames([lang], { type: "region" }); } catch { dn = null; } }
    let name: string; try { name = dn?.of(code) ?? p?.name ?? code; } catch { name = p?.name ?? code; }
    return (memo[code] = name);
  };
}

let FLAGS: boolean | null = null;
/** True when this device draws flags (checked once by drawing one and looking for colour). */
export function flagsShown(): boolean {
  if (FLAGS !== null) return FLAGS;
  try {
    const cv = document.createElement("canvas"); cv.width = 24; cv.height = 24;
    const x = cv.getContext("2d", { willReadFrequently: true }); if (!x) return (FLAGS = false);
    x.textBaseline = "top"; x.font = "20px sans-serif"; x.fillText(flagOf("FR"), 0, 0);
    const d = x.getImageData(0, 0, 24, 24).data; FLAGS = false;
    for (let i = 0; i < d.length; i += 4) if ((d[i + 3] as number) > 0 && (Math.abs((d[i] as number) - (d[i + 2] as number)) > 60)) { FLAGS = true; break; }
  } catch { FLAGS = false; }
  return FLAGS;
}
/** The flag of a two-letter country code (empty for anything else, such as the sample pack). */
export const flagOf = (code: string): string => (/^[A-Z]{2}$/.test(code) && code !== "XX" ? String.fromCodePoint(...[...code].map((ch) => 0x1f1e6 + ch.charCodeAt(0) - 65)) : "");
/** How a country shows beside its number: its flag, or its two-letter code where flags cannot be drawn. */
export const countryMark = (code: string): string => (flagsShown() && flagOf(code) ? flagOf(code) : code);

// ---- the field message (where, why and how to fix; the official colours with a word, never colour alone) -------------------
export function fieldMsgHtml(t: T, id: string, level: Level | null, text: string, fix?: { label: string; act: string }): string {
  if (!level) return `<p class="lf-msg" id="${lfEsc(id)}-msg" aria-live="polite"></p>`;
  const word = t(`fd_${level}`);
  return `<p class="lf-msg lf-${level}" id="${lfEsc(id)}-msg" role="${level === "error" ? "alert" : "status"}"><strong class="lf-word">${lfEsc(word)}</strong> <span>${lfEsc(text)}</span>${fix ? ` <button type="button" class="lf-fix" data-lf-fix="${lfEsc(fix.act)}">${lfEsc(fix.label)}</button>` : ""}</p>`;
}

// ---- phone ----------------------------------------------------------------------------------------------------------------------
const lfRules = (ctx: FieldCtx, c: string): PhoneRules => phoneRules(ctx.packs[c]?.ph ?? null);
function lfLengthWords(ctx: FieldCtx, lengths: number[]): string {
  const L = phoneLengths(lengths);
  if (L.one !== undefined) return ownDigits(String(L.one), ctx.lang);
  if (L.from !== undefined) return ctx.t("fd_range", { from: ownDigits(String(L.from), ctx.lang), to: ownDigits(String(L.to), ctx.lang) });
  return lfOrList((L.list ?? []).map((n) => ownDigits(String(n), ctx.lang)), ctx.lang);
}
/** The words for where a number stands: null when there is nothing to say. There is no rule about how a number starts
 *  (owner, 2026-11-25); only its length is checked. */
export function phoneMessage(ctx: FieldCtx, country: string, _digits: string, c: PhoneCheck): { level: Level; text: string } | null {
  const name = ctx.countryName(country), t = ctx.t;
  if (c.state === "long") return { level: "error", text: t("fd_long", { country: name, n: lfLengthWords(ctx, c.lengths) }) };
  if (c.state === "short") return { level: "error", text: t("fd_short", { country: name, n: lfLengthWords(ctx, c.lengths) }) };
  return null;
}
function lfOption(ctx: FieldCtx, code: string, selected = false): string {
  const cc = ctx.packs[code]?.ph?.code;
  return `<option value="${lfEsc(code)}"${selected ? " selected" : ""} title="${lfEsc(ctx.countryName(code))}">${lfEsc(countryMark(code))}${cc ? ` +${lfEsc(ownDigits(cc, ctx.lang))}` : ""}</option>`;
}
const LF_OPTS: Record<string, string> = {};
/** The whole country list, made once per language (the list never changes while the page is open). */
function lfOptions(ctx: FieldCtx): string {
  return (LF_OPTS[ctx.lang] ??= ctx.packOrder.map((code) => lfOption(ctx, code)).join(""));
}
export interface PhoneFieldOpts { id: string; label: string; country: string; digits: string; mobile?: boolean; submitted?: boolean }
/** One phone field: the country chooser, the number in the country's groups, the country's sample as its placeholder, and the
 *  message under it. Buttons marked data-needs-phone="<id>" stay off until the number is complete. */
export function phoneFieldHtml(ctx: FieldCtx, o: PhoneFieldOpts): string {
  const mobile = o.mobile !== false, r = lfRules(ctx, o.country), d = phoneAccept(r, o.digits || "", mobile);
  const c = phoneCheck(r, d, mobile, !!o.submitted), msg = phoneMessage(ctx, o.country, d, c);
  const sample = phoneSample(r, mobile);
  // The country is its flag (or its two-letter code where the device cannot draw flags) and its dialling code, never its full
  // name (owner, 2026-11-25); the full name is the option's tooltip.
  // Only the chosen country is drawn at first; the whole list joins when the chooser is first opened (wireFields), so a screen
  // with phone fields opens as fast as one without.
  const opts = lfOption(ctx, o.country, true);
  return `<div class="lf-field" data-phone="${lfEsc(o.id)}" data-country="${lfEsc(o.country)}" data-mobile="${mobile ? "1" : "0"}" data-valid="${c.state === "ok" ? "1" : "0"}">
    <label for="${lfEsc(o.id)}">${lfEsc(o.label)}</label>
    <div class="lf-row"><select class="lf-cc" id="${lfEsc(o.id)}-cc" aria-label="${lfEsc(ctx.t("fd_country"))}">${opts}</select><input class="text lf-in" id="${lfEsc(o.id)}" type="text" inputmode="tel" autocomplete="tel-national" dir="ltr" value="${lfEsc(phoneGroups(r, d, mobile))}"${sample ? ` placeholder="${lfEsc(ownDigits(sample, ctx.lang))}"` : ""} aria-describedby="${lfEsc(o.id)}-msg"${msg ? ` aria-invalid="true"` : ""}></div>
    ${fieldMsgHtml(ctx.t, o.id, msg?.level ?? null, msg?.text ?? "")}
  </div>`;
}
/** A number to show back to the person: + dialling code and the country's groups, in the reader's own digits. */
export function phoneDisplay(ctx: FieldCtx, country: string, digits: string): string {
  const r = lfRules(ctx, country);
  return ownDigits((r.code ? `+${r.code} ` : "") + phoneGroups(r, digits, true), ctx.lang);
}
/** The value of a phone field as it stands. */
export function phoneValue(ctx: FieldCtx, country: string, digits: string, mobile = true): PhoneValue {
  const r = lfRules(ctx, country), d = phoneAccept(r, digits, mobile);
  return { country, digits: d, international: phoneInternational(r, d), valid: phoneCheck(r, d, mobile).state === "ok" };
}

// ---- email ----------------------------------------------------------------------------------------------------------------------
export interface EmailFieldOpts { id: string; label: string; text: string; deep?: boolean; submitted?: boolean }
export function emailMessage(ctx: FieldCtx, id: string, text: string, deep: boolean, submitted: boolean): string {
  const c = emailCheck(EMAIL_DOMAINS, text, deep);
  if (c.state === "format" && submitted) return fieldMsgHtml(ctx.t, id, "error", ctx.t("fd_email_format"));
  if (c.state === "throwaway") return fieldMsgHtml(ctx.t, id, "error", ctx.t("fd_email_throwaway"));
  if (c.suggest) return fieldMsgHtml(ctx.t, id, "warning", ctx.t("fd_email_suggest", { email: c.suggest }), { label: ctx.t("fd_email_use", { email: c.suggest }), act: `email:${c.suggest}` });
  return fieldMsgHtml(ctx.t, id, null, "");
}
export function emailFieldHtml(ctx: FieldCtx, o: EmailFieldOpts): string {
  const c = emailCheck(EMAIL_DOMAINS, o.text, !!o.deep);
  return `<div class="lf-field" data-email="${lfEsc(o.id)}" data-deep="${o.deep ? "1" : "0"}" data-valid="${c.state === "ok" ? "1" : "0"}">
    <label for="${lfEsc(o.id)}">${lfEsc(o.label)}</label>
    <input class="text lf-in" id="${lfEsc(o.id)}" type="email" inputmode="email" autocomplete="email" dir="ltr" value="${lfEsc(o.text)}" placeholder="name@example.com" aria-describedby="${lfEsc(o.id)}-msg">
    ${emailMessage(ctx, o.id, o.text, !!o.deep, !!o.submitted)}
  </div>`;
}

// ---- wiring: typing updates the field in place (no redraw, the cursor stays) -----------------------------------------------------
function lfSetMsg(box: HTMLElement, html: string): void {
  const old = box.querySelector(".lf-msg"); if (!old) return;
  const tmp = document.createElement("div"); tmp.innerHTML = html;
  const fresh = tmp.firstElementChild; if (fresh) old.replaceWith(fresh);
  const input = box.querySelector("input");
  if (input) { if (fresh?.classList.contains("lf-error")) input.setAttribute("aria-invalid", "true"); else input.removeAttribute("aria-invalid"); }
}
function lfNeeds(root: ParentNode, id: string, ok: boolean): void {
  root.querySelectorAll<HTMLButtonElement>(`[data-needs-phone="${CSS.escape(id)}"], [data-needs-email="${CSS.escape(id)}"]`).forEach((b) => { b.disabled = !ok; });
}
/** Call once after every draw: wires every phone and email field under root. */
export function wireFields(root: ParentNode, ctx: FieldCtx): void {
  const codes = phoneCodes(ctx.packs);
  root.querySelectorAll<HTMLElement>("[data-phone]").forEach((box) => {
    if (box.dataset.lfWired) return; box.dataset.lfWired = "1";
    const id = box.dataset.phone as string, input = box.querySelector<HTMLInputElement>("input"), cc = box.querySelector<HTMLSelectElement>("select");
    if (!input || !cc) return;
    const mobile = box.dataset.mobile !== "0";
    const fill = (): void => { if (cc.options.length > 1) return; const keep = cc.value; cc.innerHTML = lfOptions(ctx); cc.value = keep; };
    for (const ev of ["focus", "pointerdown", "keydown", "touchstart"]) cc.addEventListener(ev, fill, { passive: true });
    const run = (raw: string, submitted: boolean): void => {
      let country = box.dataset.country as string;
      // A dialling code being typed after + (or 00) stays as typed until it is a whole code; then the country follows it.
      const lead = raw.trim(), plus = lead.startsWith("+") || lead.startsWith("00");
      if (plus) { const dd = lead.replace(/\D/g, "").slice(lead.startsWith("00") ? 2 : 0); if (![1, 2, 3].some((n) => codes[dd.slice(0, n)] && dd.length >= n)) { lfSetMsg(box, fieldMsgHtml(ctx.t, id, null, "")); return; } }
      const [c, cleaned] = phoneReadPasted(raw, country, (x) => lfRules(ctx, x), codes);
      if (c !== country) { country = c; box.dataset.country = c; cc.value = c; const s = phoneSample(lfRules(ctx, c), mobile); input.placeholder = s ? ownDigits(s, ctx.lang) : ""; }
      const r = lfRules(ctx, country), over = phoneCheck(r, cleaned, mobile).state === "long";
      const d = phoneAccept(r, cleaned, mobile), check = over ? { ...phoneCheck(r, d, mobile), state: "long" as const } : phoneCheck(r, d, mobile, submitted);
      input.value = phoneGroups(r, d, mobile);
      const msg = phoneMessage(ctx, country, d, check);
      lfSetMsg(box, fieldMsgHtml(ctx.t, id, msg?.level ?? null, msg?.text ?? ""));
      const v = phoneValue(ctx, country, d, mobile);
      box.dataset.valid = v.valid ? "1" : "0"; lfNeeds(root, id, v.valid); ctx.onPhone?.(id, v);
    };
    input.addEventListener("input", () => run(input.value, false));
    input.addEventListener("blur", () => { if (input.value) run(input.value, true); });
    cc.addEventListener("change", () => { box.dataset.country = cc.value; const s = phoneSample(lfRules(ctx, cc.value), mobile); input.placeholder = s ? ownDigits(s, ctx.lang) : ""; run(input.value, false); });
    lfNeeds(root, id, box.dataset.valid === "1");
  });
  root.querySelectorAll<HTMLElement>("[data-email]").forEach((box) => {
    if (box.dataset.lfWired) return; box.dataset.lfWired = "1";
    const id = box.dataset.email as string, input = box.querySelector<HTMLInputElement>("input"); if (!input) return;
    const deep = box.dataset.deep === "1";
    const run = (submitted: boolean): void => {
      lfSetMsg(box, emailMessage(ctx, id, input.value, deep, submitted));
      const ok = emailCheck(EMAIL_DOMAINS, input.value, deep).state === "ok";
      box.dataset.valid = ok ? "1" : "0"; lfNeeds(root, id, ok); ctx.onEmail?.(id, { text: input.value.trim(), valid: ok });
    };
    input.addEventListener("input", () => run(false));
    input.addEventListener("blur", () => { if (input.value) run(true); });
    box.addEventListener("click", (e) => {
      const b = (e.target as HTMLElement).closest<HTMLElement>("[data-lf-fix]"); const act = b?.dataset.lfFix ?? "";
      if (act.startsWith("email:")) { input.value = act.slice(6); run(true); input.focus(); }
    });
    lfNeeds(root, id, box.dataset.valid === "1");
  });
}
