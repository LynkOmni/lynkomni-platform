// Every message that tells a person something went wrong, needs care, is worth knowing or went well (section 4C point 2, owner
// 2026-11-25). One part draws them all: where (beside or under the field it is about, which gets the error border), what and why
// in plain words with the real names, and how to fix it (a button where possible, otherwise the words of what to do). The four
// official colours come from the design tokens (red error, amber warning, blue information, green success), always with an icon
// shape and a word, never colour alone. An error can never be drawn without its fix: the types refuse it, and
// tests/test_errors.py refuses any screen that draws its own error or warning box. Words in web/fields (prefix fd_).

type T = (k: string, v?: Record<string, string | number>) => string;
export type Level = "error" | "warning" | "info" | "success";
/** A way out: a button that does the fix (`act`, handled by the screen), or one that takes the person to the field to fix (`focus`). */
export type Fix = { label: string; act: string } | { label: string; focus: string };
/** also: more ways out beside the main fix (for example Edit first and Send hidden); cls: the screen's own class for placing it. */
interface Base { text: string; field?: string; id?: string; also?: readonly Fix[]; cls?: string }
/** An error always says how to fix it: a button, or the words of what to do. */
export type ErrorNotice = Base & { level: "error" } & ({ fix: Fix; how?: string } | { how: string; fix?: Fix });
export type OtherNotice = Base & { level: "warning" | "info" | "success"; fix?: Fix; how?: string };
export type Notice = ErrorNotice | OtherNotice;
/** A problem on LynkOmni's side: never the person's fault, never a technical code; Try again, and a reference to quote. */
export interface OurSide { ref: string; retryAct: string; supportAct: string; id?: string }

const ebxEsc = (v: string): string => String(v).replace(/&/g, "&amp;").replace(/"/g, "&quot;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
/** The icon shape per level, so the level is clear in black and white too: a cross, a triangle, an i and a tick. */
const EBX_MARK: Record<Level, string> = {
  error: '<svg class="ebx-mark" viewBox="0 0 16 16" aria-hidden="true"><circle cx="8" cy="8" r="7" fill="none" stroke="currentColor" stroke-width="1.6"/><path d="M5.4 5.4l5.2 5.2M10.6 5.4l-5.2 5.2" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg>',
  warning: '<svg class="ebx-mark" viewBox="0 0 16 16" aria-hidden="true"><path d="M8 1.6l6.6 12H1.4z" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/><path d="M8 6v3.6" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/><circle cx="8" cy="11.6" r="0.9" fill="currentColor"/></svg>',
  info: '<svg class="ebx-mark" viewBox="0 0 16 16" aria-hidden="true"><circle cx="8" cy="8" r="7" fill="none" stroke="currentColor" stroke-width="1.6"/><path d="M8 7.2v4.4" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/><circle cx="8" cy="4.8" r="0.9" fill="currentColor"/></svg>',
  success: '<svg class="ebx-mark" viewBox="0 0 16 16" aria-hidden="true"><circle cx="8" cy="8" r="7" fill="none" stroke="currentColor" stroke-width="1.6"/><path d="M4.8 8.2l2.2 2.2 4.2-4.6" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>',
};

function ebxFix(fix: Fix | undefined): string {
  if (!fix) return "";
  const how = "act" in fix ? `data-act="${ebxEsc(fix.act)}"` : `data-ebx-focus="${ebxEsc(fix.focus)}"`;
  return `<button type="button" class="lf-fix" ${how}>${ebxEsc(fix.label)}</button>`;
}
/** The message under a field (phone, email, code): empty until there is something to say; its fix button is handled by the field. */
export function fieldMsgHtml(t: T, id: string, level: Level | null, text: string, fix?: { label: string; act: string }): string {
  if (!level) return `<p class="lf-msg" id="${ebxEsc(id)}-msg" aria-live="polite"></p>`;
  return `<p class="lf-msg lf-${level}" id="${ebxEsc(id)}-msg" role="${level === "error" ? "alert" : "status"}">${EBX_MARK[level]}<strong class="lf-word">${ebxEsc(t(`fd_${level}`))}</strong> <span>${ebxEsc(text)}</span>${fix ? ` <button type="button" class="lf-fix" data-lf-fix="${ebxEsc(fix.act)}">${ebxEsc(fix.label)}</button>` : ""}</p>`;
}
/** One message. Errors are read out at once (alert); the others politely (status). */
export function noticeHtml(t: T, n: Notice): string {
  const id = n.id ?? (n.field ? `${n.field}-msg` : "");
  const fixes = n.also?.length ? `<div class="ebx-acts">${[n.fix, ...n.also].map(ebxFix).join("")}</div>` : ebxFix(n.fix);
  return `<div class="lf-msg lf-${n.level} ebx${n.cls ? ` ${ebxEsc(n.cls)}` : ""}" data-level="${n.level}"${id ? ` id="${ebxEsc(id)}"` : ""}${n.field ? ` data-field="${ebxEsc(n.field)}"` : ""} role="${n.level === "error" ? "alert" : "status"}">`
    + `<p class="ebx-line">${EBX_MARK[n.level]}<strong class="lf-word">${ebxEsc(t(`fd_${n.level}`))}</strong> <span>${ebxEsc(n.text)}</span></p>`
    + `${n.how ? `<p class="ebx-how">${ebxEsc(n.how)}</p>` : ""}${fixes}</div>`;
}
/** A problem on LynkOmni's side, with Try again and the reference to quote to support. */
export function ourSideHtml(t: T, o: OurSide): string {
  return `<div class="lf-msg lf-error ebx" data-level="error" role="alert"${o.id ? ` id="${ebxEsc(o.id)}"` : ""}>`
    + `<p class="ebx-line">${EBX_MARK.error}<strong class="lf-word">${ebxEsc(t("fd_error"))}</strong> <span>${ebxEsc(t("fd_our_side"))}</span></p>`
    + `<p class="ebx-how">${ebxEsc(t("fd_ref", { ref: o.ref }))}</p>`
    + `<div class="ebx-acts"><button type="button" class="lf-fix" data-act="${ebxEsc(o.retryAct)}">${ebxEsc(t("fd_try_again"))}</button><button type="button" class="lf-fix" data-act="${ebxEsc(o.supportAct)}">${ebxEsc(t("fd_contact_support"))}</button></div></div>`;
}
/** Several things to fix: a list at the top, each one taking the person to its field; the cursor goes to the first. */
export function summaryHtml(t: T, items: readonly { field: string; text: string }[]): string {
  if (!items.length) return "";
  const head = items.length === 1 ? t("fd_one_to_fix") : t("fd_things_to_fix", { n: items.length });
  return `<div class="lf-msg lf-error ebx ebx-summary" data-level="error" role="alert" tabindex="-1"><p class="ebx-line">${EBX_MARK.error}<strong class="lf-word">${ebxEsc(head)}</strong></p>`
    + `<ul class="ebx-list">${items.map((x) => `<li><button type="button" class="ebx-go" data-ebx-focus="${ebxEsc(x.field)}">${ebxEsc(x.text)}</button></li>`).join("")}</ul></div>`;
}

/** Call once after every draw: the field each error is about gets the error border and is linked to its message; the focus
 *  buttons take the person to their field; a summary puts the cursor on the first field to fix. Fixed means gone: the next
 *  draw without the message takes the border away. */
export function wireNotices(root: ParentNode): void {
  const scope = root as ParentNode & { querySelectorAll: Document["querySelectorAll"] };
  scope.querySelectorAll<HTMLElement>("[data-ebx-marked]").forEach((f) => { if (!scope.querySelector(`.ebx[data-field="${CSS.escape(f.id)}"][data-level="error"]`)) { f.removeAttribute("aria-invalid"); f.removeAttribute("data-ebx-marked"); } });
  scope.querySelectorAll<HTMLElement>(".ebx[data-field]").forEach((m) => {
    const f = document.getElementById(m.dataset.field ?? ""); if (!f) return;
    const ids = (f.getAttribute("aria-describedby") ?? "").split(/\s+/).filter(Boolean);
    if (m.id && !ids.includes(m.id)) f.setAttribute("aria-describedby", [...ids, m.id].join(" "));
    if (m.dataset.level === "error") { f.setAttribute("aria-invalid", "true"); f.setAttribute("data-ebx-marked", "1"); }
  });
  const el = root as HTMLElement;
  if (el.dataset && !el.dataset.ebxWired) {
    el.dataset.ebxWired = "1";
    el.addEventListener("click", (e) => {
      const b = (e.target as HTMLElement).closest<HTMLElement>("[data-ebx-focus]"); if (!b) return;
      const f = document.getElementById(b.dataset.ebxFocus ?? "") as HTMLElement | null;
      if (f) { f.focus(); f.scrollIntoView?.({ block: "center" }); }
    });
  }
  const sum = scope.querySelector<HTMLElement>(".ebx-summary:not([data-ebx-seen])");
  if (sum) { sum.setAttribute("data-ebx-seen", "1"); const first = sum.querySelector<HTMLElement>("[data-ebx-focus]"); const f = first ? document.getElementById(first.dataset.ebxFocus ?? "") : null; (f ?? sum).focus?.(); }
}
