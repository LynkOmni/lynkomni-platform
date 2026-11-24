/** The page-template parts (INTERFACE UPDATE 73.6, section 4 step B2c): the record header with its sticky record bar and the same
 *  tabs on every record (Details, Activity, Files, Related; at most seven tabs, the rest under More), the list toolbar (search and
 *  filter chips) and the form's save bar that stays in view. Every screen's template comes from catalog/templates.v1.json; these
 *  parts are the one shared kit, never rebuilt for one screen. No DOM here: parts return HTML strings, the host binds data-act. */
import type { NavRegister } from "./navigation.js";
import { pageTabs } from "./navigation.js";

export type T = (key: string, vars?: Record<string, string | number>) => string;
const pkEsc = (s: string): string => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
/** The tabs every record has, in this order (catalog/templates.v1.json templates.record.tabs). */
export const RECORD_TABS = ["details", "activity", "files", "related"] as const;

/** The record header: name, its state (a chip the host draws with the five states), the one main button, then the record's tabs. */
export function recordHeaderHtml(reg: NavRegister, t: T, o: { title: string; state?: string; main?: { label: string; act: string }; tabs?: readonly string[]; current?: string; tabLabel?: (id: string) => string; act?: string }): string {
  const tabs = pageTabs(reg, o.tabs ?? RECORD_TABS);
  const act = o.act ?? "rtab";
  const label = (id: string): string => (id === "more" ? t("nv_more") : o.tabLabel?.(id) ?? t(`nv_${id}`));
  return `<div class="pk-record"><div class="pk-bar"><h2>${pkEsc(o.title)}</h2>${o.state ?? ""}${o.main ? `<button class="primary pk-main" data-act="${pkEsc(o.main.act)}">${pkEsc(o.main.label)}</button>` : ""}</div>
    <div class="pk-tabs" role="tablist">${tabs.map((id) => `<button role="tab" data-act="${pkEsc(act)}:${pkEsc(id)}" aria-selected="${id === (o.current ?? tabs[0])}">${pkEsc(label(id))}</button>`).join("")}</div></div>`;
}

/** The list toolbar: a search box with its visible label, an example as its hint (in the reader's language, given by the screen;
 *  never the instruction) and filter chips (one may be on). */
export function listToolbarHtml(t: T, o: { query?: string; hint: string; chips: readonly { id: string; label: string; on?: boolean }[]; act?: string; inputId?: string }): string {
  const act = o.act ?? "filter";
  return `<div class="pk-toolbar"><label class="pk-search"><span>${pkEsc(t("nv_search"))}</span><input id="${pkEsc(o.inputId ?? "pkSearch")}" type="search" data-recents="${pkEsc(o.inputId ?? "pkSearch")}" value="${pkEsc(o.query ?? "")}" placeholder="${pkEsc(o.hint)}" aria-label="${pkEsc(t("nv_search"))}"></label>
    <div class="pk-chips" role="group">${o.chips.map((c) => `<button class="pk-chip" data-act="${pkEsc(act)}:${pkEsc(c.id)}" aria-pressed="${!!c.on}">${pkEsc(c.label)}</button>`).join("")}</div></div>`;
}

/** The form's save bar: stays in view at the bottom; the main button and, when there is no undo, a review step first. */
export function saveBarHtml(o: { label: string; act: string; secondary?: { label: string; act: string }; disabled?: boolean }): string {
  return `<div class="pk-save">${o.secondary ? `<button class="secondary" data-act="${pkEsc(o.secondary.act)}">${pkEsc(o.secondary.label)}</button>` : ""}<button class="primary" data-act="${pkEsc(o.act)}"${o.disabled ? " disabled" : ""}>${pkEsc(o.label)}</button></div>`;
}
