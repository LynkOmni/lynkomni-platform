/** Text, USSD and voice channels for phones with no apps (BIZZ & DEVICE 48.17, interface phone.text): the TypeScript port of
 *  core/channels.py, proved by contract/vectors/channels.v1.json. One menu engine serves a USSD session, text messages and a
 *  voice-call menu; pages are word keys with values, so every channel speaks the person's language. A sale is recorded only
 *  after the PIN; agent and partner requests are never offered here. */
export const USSD_MAX = 182;
export const CH_MENU = ["sell", "today", "stock", "help"] as const;
export type ChScreen = "menu" | "product" | "qty" | "pin" | "done" | "today" | "stock" | "help" | "bye";
export interface ChState { screen: ChScreen; prod: number | null; qty: number | null }
export type ChLine = [string, Record<string, string | number>];
export interface ChCtx { products: [string, string, string][]; today: [number, string]; receipt?: string; pinOk: (t: string) => boolean }

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
export function chStep(state: ChState, text: string, ctx: ChCtx): [ChState, boolean, { sale: number; qty_milli: number } | null] {
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

export function chRender(lines: ChLine[], words: (key: string) => string): string {
  return lines.map(([k, v]) => words(k).replace(/\{(\w+)\}/g, (m, n: string) => (n in v ? String(v[n]) : m))).join("\n");
}
