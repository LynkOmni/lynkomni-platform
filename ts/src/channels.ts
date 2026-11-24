/** Text, USSD and voice channels for phones with no apps (BIZZ & DEVICE 48.17, interface phone.text): the TypeScript port of
 *  core/channels.py, proved by contract/vectors/channels.v1.json. One menu engine serves a USSD session, text messages and a
 *  voice-call menu; pages are word keys with values, so every channel speaks the person's language. A sale is recorded only
 *  after the PIN; agent and partner requests are never offered here. */
export const USSD_MAX = 182;
export const CH_MENU = ["sell", "today", "stock", "help"] as const;
export type ChScreen = "menu" | "product" | "qty" | "pin" | "done" | "today" | "stock" | "help" | "bye";
export interface ChState { screen: ChScreen; prod: number | null; qty: number | null }
export type ChLine = [string, Record<string, string | number>];
export interface ChCtx { products: [string, string, string][]; today: [number, string]; receipt?: string; pinOk: (t: string) => boolean; pinDuress?: (t: string) => boolean }

export const chStart = (): ChState => ({ screen: "menu", prod: null, qty: null });

export function chPage(s: ChState, ctx: Omit<ChCtx, "pinOk">): ChLine[] {
  const P = ctx.products;
  switch (s.screen) {
    case "menu": return [["ch_title", {}], ...CH_MENU.map((k, i): ChLine => [`ch_menu_${k}`, { n: i + 1 }]), ["ch_end", { n: 0 }]];
    case "product": return [["ch_pick_product", {}], ...P.map((p, i): ChLine => ["ch_product_line", { n: i + 1, name: p[0], price: p[1] }]), ["ch_back", { n: 0 }]];
    case "qty": return [["ch_qty", { name: P[s.prod ?? 0]?.[0] ?? "" }]];
    case "pin": return [["ch_pin", { qty: s.qty ?? 0, name: P[s.prod ?? 0]?.[0] ?? "" }]];
    case "done": return [["ch_sale_saved", { receipt: ctx.receipt ?? "" }]];
    case "today": return [["ch_today", { count: ctx.today[0], total: ctx.today[1] }], ["ch_back", { n: 0 }]];
    case "stock": return [...P.map((p): ChLine => ["ch_stock_line", { name: p[0], level: p[2] }]), ["ch_back", { n: 0 }]];
    case "help": return [["ch_help", {}], ["ch_back", { n: 0 }]];
    default: return [["ch_bye", {}]];
  }
}

const digit = (t: string): boolean => /^\d+$/.test(t);
export function chStep(state: ChState, text: string, ctx: ChCtx): [ChState, boolean, { sale: number; qty_milli: number; duress?: true } | null] {
  const s: ChState = { ...state }, t = (text ?? "").trim();
  switch (s.screen) {
    case "menu":
      if (t === "0") { s.screen = "bye"; return [s, true, null]; }
      if (digit(t) && Number(t) >= 1 && Number(t) <= CH_MENU.length) s.screen = ({ sell: "product", today: "today", stock: "stock", help: "help" } as const)[CH_MENU[Number(t) - 1]!];
      return [s, false, null];
    case "product":
      if (t === "0") return [chStart(), false, null];
      if (digit(t) && Number(t) >= 1 && Number(t) <= ctx.products.length) { s.prod = Number(t) - 1; s.screen = "qty"; }
      return [s, false, null];
    case "qty":
      if (digit(t) && Number(t) >= 1 && Number(t) <= 999) { s.qty = Number(t); s.screen = "pin"; }
      return [s, false, null];
    case "pin":
      if (ctx.pinOk(t)) { s.screen = "done"; return [s, true, { sale: s.prod ?? 0, qty_milli: (s.qty ?? 0) * 1000 }]; }
      if (ctx.pinDuress?.(t)) { s.screen = "done"; return [s, true, { sale: s.prod ?? 0, qty_milli: (s.qty ?? 0) * 1000, duress: true }]; }   // the same page; the cloud raises the alert silently
      return [chStart(), false, null];
    case "today": case "stock": case "help":
      return t === "0" ? [chStart(), false, null] : [s, false, null];
    default: return [s, true, null];
  }
}

export type SmsCommand = { command: "sell"; product: number; qty_milli: number; pin: string } | { command: "today" | "stock" | "help" };
export function parseSms(text: string): SmsCommand | null {
  const parts = (text ?? "").trim().split(/\s+/);
  const first = parts[0] ?? "";
  if (!digit(first) || Number(first) < 1 || Number(first) > CH_MENU.length) return null;
  const what = CH_MENU[Number(first) - 1]!;
  if (what === "sell") {
    if (parts.length !== 4 || !parts.slice(1).every(digit) || Number(parts[1]) < 1 || Number(parts[2]) < 1 || Number(parts[2]) > 999) return { command: "help" };
    return { command: "sell", product: Number(parts[1]) - 1, qty_milli: Number(parts[2]) * 1000, pin: parts[3]! };
  }
  return { command: what };
}

// ---- LynkQueue for a person with a basic phone (build section 3B): the port of queue_start, queue_page, queue_step and parse_queue_sms
export const Q_LATE = 8, Q_LEAVE = 9;
export interface ChQState { screen: "sections" | "ticket" | "left" | "bye" }
export interface ChQTicket { number: string; place: number; minutes: number; state: string; late_used: boolean; counter?: string }
export interface ChQCtx { place: string; sections: [string, number, number, boolean][]; ticket: ChQTicket | null }
export type ChQAction = { join: number } | { running_late: true } | { leave: true };
export const chQStart = (hasTicket = false): ChQState => ({ screen: hasTicket ? "ticket" : "sections" });
export function chQPage(s: ChQState, ctx: ChQCtx): ChLine[] {
  if (s.screen === "sections") return [["ch_q_title", { place: ctx.place }], ...ctx.sections.map((sec, i): ChLine => [sec[3] ? "ch_q_section" : "ch_q_section_closed", { n: i + 1, name: sec[0], waiting: sec[1], minutes: sec[2] }]), ["ch_end", { n: 0 }]];
  if (s.screen === "ticket" && ctx.ticket) {
    const tk = ctx.ticket;
    if (tk.state !== "waiting") return [[tk.state === "called" ? "ch_q_called" : "ch_q_over", { number: tk.number, counter: tk.counter ?? "" }]];
    return [["ch_q_ticket", { number: tk.number, place: tk.place, minutes: tk.minutes }], ...(tk.late_used ? [] : [["ch_q_late", { n: 1 }] as ChLine]), ["ch_q_leave", { n: 2 }], ["ch_end", { n: 0 }]];
  }
  if (s.screen === "left") return [["ch_q_left", {}]];
  return [["ch_bye", {}]];
}
export function chQStep(state: ChQState, text: string, ctx: ChQCtx): [ChQState, boolean, ChQAction | null] {
  const s: ChQState = { ...state }, t = (text ?? "").trim();
  if (s.screen === "sections") {
    if (t === "0") { s.screen = "bye"; return [s, true, null]; }
    if (digit(t) && Number(t) >= 1 && Number(t) <= ctx.sections.length && ctx.sections[Number(t) - 1]![3]) { s.screen = "ticket"; return [s, false, { join: Number(t) - 1 }]; }
    return [s, false, null];
  }
  if (s.screen === "ticket" && ctx.ticket) {
    const tk = ctx.ticket;
    if (t === "0" || tk.state !== "waiting") { s.screen = "bye"; return [s, true, null]; }
    if (t === "1" && !tk.late_used) return [s, false, { running_late: true }];
    if (t === "2") { s.screen = "left"; return [s, true, { leave: true }]; }
    return [s, false, null];
  }
  return [s, true, null];
}
export function parseQueueSms(text: string, sections: number): { command: "running_late" | "leave" } | { command: "join"; section: number } | null {
  const t = (text ?? "").trim(); if (!digit(t)) return null;
  const n = Number(t);
  if (n === Q_LATE) return { command: "running_late" };
  if (n === Q_LEAVE) return { command: "leave" };
  if (n >= 1 && n <= Math.min(sections, Q_LATE - 1)) return { command: "join", section: n - 1 };
  return null;
}

// ---- LynkSurvey for a person with a basic phone (build section 3B): the port of survey_start, survey_page and survey_step
export const S_TYPES = ["rating", "stars", "score", "yes_no", "choice"] as const;
export interface ChSQuestion { id: string; type: string; text: string; choices?: string[] }
export interface ChSCtx { org: string; minutes: number; anonymous: boolean; questions: ChSQuestion[] }
export type ChSAnswer = { q: string; number: number } | { q: string; choice: string };
export interface ChSState { screen: "intro" | "question" | "done" | "bye"; i: number; answers: ChSAnswer[] }
export const chSStart = (): ChSState => ({ screen: "intro", i: 0, answers: [] });
const asked = (ctx: ChSCtx): ChSQuestion[] => ctx.questions.filter((q) => (S_TYPES as readonly string[]).includes(q.type));
export function chSPage(s: ChSState, ctx: ChSCtx): ChLine[] {
  const qs = asked(ctx);
  if (s.screen === "intro") return [["ch_s_intro", { org: ctx.org, count: qs.length, minutes: ctx.minutes }], ...(ctx.anonymous ? [["ch_s_anon", {}] as ChLine] : []), ["ch_s_start", { n: 1 }], ["ch_end", { n: 0 }]];
  if (s.screen === "question") {
    const q = qs[s.i]!, head: ChLine[] = [["ch_s_q", { i: s.i + 1, of: qs.length, text: q.text }]];
    if (q.type === "rating" || q.type === "stars") return [...head, ["ch_s_rate", {}]];
    if (q.type === "score") return [...head, ["ch_s_score", {}]];
    if (q.type === "yes_no") return [...head, ["ch_s_yes", { n: 1 }], ["ch_s_no", { n: 2 }]];
    return [...head, ...(q.choices ?? []).map((c, i): ChLine => ["ch_s_choice", { n: i + 1, name: c }])];
  }
  if (s.screen === "done") return [["ch_s_done", {}]];
  return [["ch_bye", {}]];
}
function reply(q: ChSQuestion, t: string): ChSAnswer | null {
  if (!digit(t)) return null;
  const n = Number(t);
  if ((q.type === "rating" || q.type === "stars") && n >= 1 && n <= 5) return { q: q.id, number: n };
  if (q.type === "score" && n >= 0 && n <= 10) return { q: q.id, number: n };
  if (q.type === "yes_no" && (n === 1 || n === 2)) return { q: q.id, choice: n === 1 ? "yes" : "no" };
  if (q.type === "choice" && n >= 1 && n <= (q.choices ?? []).length) return { q: q.id, choice: q.choices![n - 1]! };
  return null;
}
export function chSStep(state: ChSState, text: string, ctx: ChSCtx): [ChSState, boolean, { answers: ChSAnswer[] } | null] {
  const s: ChSState = { ...state, answers: [...state.answers] }, t = (text ?? "").trim(), qs = asked(ctx);
  if (s.screen === "intro") {
    if (t === "0" || !qs.length) { s.screen = "bye"; return [s, true, null]; }
    if (t === "1") { s.screen = "question"; return [s, false, null]; }
    return [s, false, null];
  }
  if (s.screen === "question") {
    const a = reply(qs[s.i]!, t); if (!a) return [s, false, null];
    s.answers.push(a);
    if (s.i + 1 < qs.length) { s.i += 1; return [s, false, null]; }
    s.screen = "done"; return [s, true, { answers: s.answers }];
  }
  return [s, true, null];
}

export function chRender(lines: ChLine[], words: (key: string) => string): string {
  return lines.map(([k, v]) => words(k).replace(/\{(\w+)\}/g, (m, n: string) => (n in v ? String(v[n]) : m))).join("\n");
}
