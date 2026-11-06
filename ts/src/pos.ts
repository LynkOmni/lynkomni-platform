/** LynkPOS sale rules (TypeScript port of the reference in dv/box.py). No browser or Node APIs, so the same file runs in the
 *  terminal emulator, the real web app and the tests.
 *  Money is an integer number of minor units plus a currency code. Quantities are integer thousandths (1000 = one piece).
 *  Tax: the fiscal workflow is not confirmed in any country yet, so sales use tax_mode "none" and receipts are provisional. */

export const USER_STATES = ["queued", "sent", "accepted", "confirmed", "failed"] as const;
export type UserState = (typeof USER_STATES)[number];
export type PaymentMethod = "cash" | "mobile_money" | "bank_transfer" | "card" | "credit" | "other";
export type PaymentStatus = "cash_received" | "pending_confirmation" | "confirmed" | "failed" | "credit_open";

export interface Product { id: string; name: string; price: number; category: string; barcode?: string }
export interface CartLine { product: Product; qtyMilli: number; discount: number }
export interface SaleLine { line_no: number; product_id: string; product_name: string; quantity_milli: number; unit_price: number; discount: number; line_total: number }
export interface SalePayload { sale_id: string; receipt_number_local: string; lines: SaleLine[]; subtotal: number; discount_total: number; tax_total: number; tax_mode: "none"; total: number; currency: string }
export interface PaymentPayload { payment_id: string; sale_id: string; method: PaymentMethod; amount: number; status: PaymentStatus; provider_reference?: string }

export class PosError extends Error { constructor(public reason: string) { super(reason); } }

const isMoney = (n: number): boolean => Number.isSafeInteger(n) && n >= 0;

/** Same rule as the reference: round half up to a whole minor unit, then take off the discount. BigInt so large values stay exact. */
export function lineTotal(qtyMilli: number, unitPrice: number, discount: number): number {
  if (!Number.isSafeInteger(qtyMilli) || qtyMilli < 1 || !isMoney(unitPrice) || !isMoney(discount)) throw new PosError("invalid_amount");
  const t = Number((BigInt(qtyMilli) * BigInt(unitPrice) + 500n) / 1000n) - discount;
  if (t < 0) throw new PosError("invalid_amount");
  return t;
}

export class Cart {
  private items: CartLine[] = [];
  add(product: Product, qtyMilli = 1000): void {
    const hit = this.items.find((l) => l.product.id === product.id);
    if (hit) hit.qtyMilli += qtyMilli; else this.items.push({ product, qtyMilli, discount: 0 });
  }
  setQty(productId: string, qtyMilli: number): void {
    if (qtyMilli <= 0) { this.remove(productId); return; }
    const hit = this.items.find((l) => l.product.id === productId);
    if (hit) hit.qtyMilli = qtyMilli;
  }
  remove(productId: string): void { this.items = this.items.filter((l) => l.product.id !== productId); }
  clear(): void { this.items = []; }
  lines(): readonly CartLine[] { return this.items; }
  count(): number { return this.items.reduce((n, l) => n + Math.ceil(l.qtyMilli / 1000), 0); }
  total(): number { return this.items.reduce((s, l) => s + lineTotal(l.qtyMilli, l.product.price, l.discount), 0); }
}

/** The SaleRecorded payload, exactly as the contract wants it. */
export function salePayload(cart: Cart, saleId: string, receiptNo: string, currency: string): SalePayload {
  if (cart.lines().length === 0) throw new PosError("empty_cart");
  if (!/^[A-Z0-9]{2,8}-[0-9]{1,10}$/.test(receiptNo)) throw new PosError("bad_receipt_number");
  const lines = cart.lines().map((l, i) => ({ line_no: i + 1, product_id: l.product.id, product_name: l.product.name, quantity_milli: l.qtyMilli,
    unit_price: l.product.price, discount: l.discount, line_total: lineTotal(l.qtyMilli, l.product.price, l.discount) }));
  const sub = lines.reduce((s, l) => s + l.line_total, 0);
  return { sale_id: saleId, receipt_number_local: receiptNo, lines, subtotal: sub, discount_total: lines.reduce((s, l) => s + l.discount, 0),
    tax_total: 0, tax_mode: "none", total: sub, currency };
}

/** A device never marks non-cash money as settled: only the provider can confirm it. */
export function deviceStatus(method: PaymentMethod): PaymentStatus {
  return method === "cash" ? "cash_received" : method === "credit" ? "credit_open" : "pending_confirmation";
}

export function paymentPayload(paymentId: string, saleId: string, method: PaymentMethod, amount: number, providerReference?: string): PaymentPayload {
  if (!isMoney(amount) || amount === 0) throw new PosError("invalid_amount");
  const p: PaymentPayload = { payment_id: paymentId, sale_id: saleId, method, amount, status: deviceStatus(method) };
  if (providerReference) p.provider_reference = providerReference;
  return p;
}

/** Cash change. Refuses less than the total instead of showing a negative number. */
export function change(total: number, tendered: number): number {
  if (!isMoney(total) || !isMoney(tendered)) throw new PosError("invalid_amount");
  if (tendered < total) throw new PosError("not_enough_cash");
  return tendered - total;
}

/** Quick cash buttons: the exact amount, then the next round notes above it. */
export function quickCash(total: number, notes: readonly number[]): number[] {
  const out = [total];
  for (const n of notes) { const up = Math.ceil(total / n) * n; if (up > total && !out.includes(up)) out.push(up); }
  return out.slice(0, 4);
}

/** What the person sees for a payment. Words come from the five-state vocabulary; cash is not a provider state. */
export function paymentState(status: PaymentStatus, online: boolean): UserState | "cash" | "credit" {
  if (status === "cash_received") return "cash";
  if (status === "credit_open") return "credit";
  if (status === "confirmed") return "confirmed";
  if (status === "failed") return "failed";
  return online ? "sent" : "queued";
}

/** Integer minor units to a display string. Locale changes presentation only. */
export function formatMoney(minor: number, currency: string, locale: string): string {
  const nf = new Intl.NumberFormat(locale, { style: "currency", currency });
  const d = nf.resolvedOptions().maximumFractionDigits ?? 0;
  if (d === 0) return nf.format(BigInt(minor));
  const s = String(minor).padStart(d + 1, "0");
  return nf.format(`${s.slice(0, -d)}.${s.slice(-d)}` as unknown as number);   // a decimal string keeps it exact
}

export const qtyText = (qtyMilli: number): string => (qtyMilli % 1000 === 0 ? String(qtyMilli / 1000) : (qtyMilli / 1000).toFixed(3));

/** Text for the built-in thermal printer (58 mm paper is 32 characters wide). */
export function receiptLines(o: { shop: string; sale: SalePayload; payments: PaymentPayload[]; tendered?: number; when: string; money: (n: number) => string; words: Record<string, string>; width?: number }): string[] {
  const w = o.width ?? 32, rule = "-".repeat(w);
  const two = (a: string, b: string): string => { const room = w - b.length - 1; return (a.length > room ? a.slice(0, Math.max(room - 1, 1)) + "." : a).padEnd(room) + " " + b; };
  const centre = (t: string): string => " ".repeat(Math.max(Math.floor((w - t.length) / 2), 0)) + t;
  const out = [centre(o.shop), centre(o.words["provisional"] ?? "Provisional receipt"), rule, two(o.words["receipt"] ?? "Receipt", o.sale.receipt_number_local), o.when, rule];
  for (const l of o.sale.lines) {
    out.push(l.product_name.slice(0, w));
    out.push(two(`  ${qtyText(l.quantity_milli)} x ${o.money(l.unit_price)}`, o.money(l.line_total)));
  }
  out.push(rule, two(o.words["total"] ?? "Total", o.money(o.sale.total)));
  for (const p of o.payments) {
    const label = o.words[`method_${p.method}`] ?? p.method;
    out.push(two(label, o.money(p.amount)));
    if (p.status !== "cash_received") out.push(`  ${o.words[`state_${p.status}`] ?? p.status}`.slice(0, w));
  }
  if (o.tendered !== undefined) { out.push(two(o.words["tendered"] ?? "Cash given", o.money(o.tendered)), two(o.words["change"] ?? "Change", o.money(change(o.sale.total, o.tendered)))); }
  out.push(rule, centre(o.words["thanks"] ?? "Thank you"), centre(o.words["not_tax"] ?? "Not a tax receipt"));
  return out;
}

/** A UUIDv7 (the contract's id format) from a clock and a random source, so it works in any runtime. */
export function uuid7(nowMs: number, randomBytes: (n: number) => Uint8Array): string {
  const r = randomBytes(10);
  const hex = (b: number): string => b.toString(16).padStart(2, "0");
  const ms = BigInt(nowMs) & ((1n << 48n) - 1n);
  const t = ms.toString(16).padStart(12, "0");
  const a = ((r[0] ?? 0) & 0x0f).toString(16) + hex(r[1] ?? 0);
  const b = hex(((r[2] ?? 0) & 0x3f) | 0x80) + hex(r[3] ?? 0);
  const c = Array.from(r.slice(4, 10), hex).join("");
  return `${t.slice(0, 8)}-${t.slice(8, 12)}-7${a}-${b}-${c}`;
}
