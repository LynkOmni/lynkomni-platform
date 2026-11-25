// The email field and the field message (section 4C points 1 and 2, owner 2026-11-25). Every email field in the ecosystem is drawn
// here, the footer's too (words in web/fields, prefix fd_; styles web/shell/fields.css); a screen never draws its own. Kept apart
// from the phone field so a page with only an email box (the footer) carries no phone rules.
import { EMAIL_DOMAINS } from "./phone.generated.js";

type T = (k: string, v?: Record<string, string | number>) => string;
export type Level = "error" | "warning" | "info" | "success";
export interface EmailValue { text: string; valid: boolean }
/** What the email field needs: the words, and who hears about a change. */
export interface EmailCtx { t: T; onEmail?: (id: string, v: EmailValue) => void }
const efEsc = (v: string): string => String(v).replace(/&/g, "&amp;").replace(/"/g, "&quot;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

// ---- the email check -------------------------------------------------------------------------------------------------------------------
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

// ---- the field message (where, why and how to fix; the official colours with a word, never colour alone) -------------------
export function fieldMsgHtml(t: T, id: string, level: Level | null, text: string, fix?: { label: string; act: string }): string {
  if (!level) return `<p class="lf-msg" id="${efEsc(id)}-msg" aria-live="polite"></p>`;
  const word = t(`fd_${level}`);
  return `<p class="lf-msg lf-${level}" id="${efEsc(id)}-msg" role="${level === "error" ? "alert" : "status"}"><strong class="lf-word">${efEsc(word)}</strong> <span>${efEsc(text)}</span>${fix ? ` <button type="button" class="lf-fix" data-lf-fix="${efEsc(fix.act)}">${efEsc(fix.label)}</button>` : ""}</p>`;
}

// ---- the email field ----------------------------------------------------------------------------------------------------------------------
export interface EmailFieldOpts { id: string; label: string; text: string; deep?: boolean; submitted?: boolean }
export function emailMessage(ctx: EmailCtx, id: string, text: string, deep: boolean, submitted: boolean): string {
  const c = emailCheck(EMAIL_DOMAINS, text, deep);
  if (c.state === "format" && submitted) return fieldMsgHtml(ctx.t, id, "error", ctx.t("fd_email_format"));
  if (c.state === "throwaway") return fieldMsgHtml(ctx.t, id, "error", ctx.t("fd_email_throwaway"));
  if (c.suggest) return fieldMsgHtml(ctx.t, id, "warning", ctx.t("fd_email_suggest", { email: c.suggest }), { label: ctx.t("fd_email_use", { email: c.suggest }), act: `email:${c.suggest}` });
  return fieldMsgHtml(ctx.t, id, null, "");
}
export function emailFieldHtml(ctx: EmailCtx, o: EmailFieldOpts): string {
  const c = emailCheck(EMAIL_DOMAINS, o.text, !!o.deep);
  return `<div class="lf-field" data-email="${efEsc(o.id)}" data-deep="${o.deep ? "1" : "0"}" data-valid="${c.state === "ok" ? "1" : "0"}">
    <label for="${efEsc(o.id)}">${efEsc(o.label)}</label>
    <input class="text lf-in" id="${efEsc(o.id)}" type="email" inputmode="email" autocomplete="email" dir="ltr" value="${efEsc(o.text)}" placeholder="name@example.com" aria-describedby="${efEsc(o.id)}-msg">
    ${emailMessage(ctx, o.id, o.text, !!o.deep, !!o.submitted)}
  </div>`;
}

// ---- wiring: typing updates the field in place (no redraw, the cursor stays) ----
export function efSetMsg(box: HTMLElement, html: string): void {
  const old = box.querySelector(".lf-msg"); if (!old) return;
  const tmp = document.createElement("div"); tmp.innerHTML = html;
  const fresh = tmp.firstElementChild;
  // an unchanged message stays as it is, so a tap on its button (which first takes the focus from the field) still lands
  if (fresh && fresh.outerHTML !== old.outerHTML) old.replaceWith(fresh);
  const input = box.querySelector("input");
  if (input) { if (fresh?.classList.contains("lf-error")) input.setAttribute("aria-invalid", "true"); else input.removeAttribute("aria-invalid"); }
}
export function efNeeds(root: ParentNode, id: string, ok: boolean): void {
  root.querySelectorAll<HTMLButtonElement>(`[data-needs-phone="${CSS.escape(id)}"], [data-needs-email="${CSS.escape(id)}"]`).forEach((b) => { b.disabled = !ok; });
}
/** Call once after every draw: wires every email field under root. */
export function wireEmails(root: ParentNode, ctx: EmailCtx): void {
  root.querySelectorAll<HTMLElement>("[data-email]").forEach((box) => {
    if (box.dataset.efWired) return; box.dataset.efWired = "1";
    const id = box.dataset.email as string, input = box.querySelector<HTMLInputElement>("input"); if (!input) return;
    const deep = box.dataset.deep === "1";
    const run = (submitted: boolean): void => {
      efSetMsg(box, emailMessage(ctx, id, input.value, deep, submitted));
      const ok = emailCheck(EMAIL_DOMAINS, input.value, deep).state === "ok";
      box.dataset.valid = ok ? "1" : "0"; efNeeds(root, id, ok); ctx.onEmail?.(id, { text: input.value.trim(), valid: ok });
    };
    input.addEventListener("input", () => run(false));
    input.addEventListener("blur", () => { if (input.value) run(true); });
    box.addEventListener("mousedown", (e) => { if ((e.target as HTMLElement).closest("[data-lf-fix]")) e.preventDefault(); });   // keep the focus in the field
    box.addEventListener("click", (e) => {
      const b = (e.target as HTMLElement).closest<HTMLElement>("[data-lf-fix]"); const act = b?.dataset.lfFix ?? "";
      if (act.startsWith("email:")) { input.value = act.slice(6); run(true); input.focus(); }
    });
    efNeeds(root, id, box.dataset.valid === "1");
  });
}
