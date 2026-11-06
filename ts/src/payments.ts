/** Payment options shown to people, per country. Global standard used by large payment platforms: a neutral LynkOmni
 *  method icon plus the provider's name as text. Another company's logo is never drawn or copied; its official artwork
 *  is added only when that provider is signed and supplies it (see providers/registry.v1.json, later item
 *  official_payment_marks). Which options a country has comes only from its country pack. */

export type PaymentKind = "card" | "mobile_money" | "bank" | "instant" | "wallet" | "qr" | "crypto";
export interface PaymentMethod { label: string; kind: PaymentKind; icon: string }
export interface PaymentOption extends PaymentMethod { id: string; official: false }

/** Icons per kind: LynkOmni originals from @lynkomni/icons. */
export const KIND_ICON: Record<PaymentKind, string> = {
  card: "ui-pay-card", mobile_money: "ui-pay-mobile-money", bank: "ui-pay-bank", instant: "ui-pay-instant", wallet: "ui-pay-wallet", qr: "ui-qr", crypto: "ui-pay-crypto",
};

/** Every payment method LynkOmni knows. Labels are the providers' own names, written as plain text. */
export const PAYMENT_METHODS: Record<string, PaymentMethod> = Object.fromEntries(([
  ["visa", "Visa", "card"], ["mastercard", "Mastercard", "card"],
  ["momo_mtn", "MTN MoMo", "mobile_money"], ["airtel_money", "Airtel Money", "mobile_money"], ["mpesa", "M-Pesa", "mobile_money"],
  ["upi", "UPI", "instant"], ["bank_transfer", "Bank transfer", "bank"], ["qr", "QR payment", "qr"],
  ["apple_pay", "Apple Pay", "wallet"], ["google_pay", "Google Pay", "wallet"],
  ["crypto", "Crypto", "crypto"],
] as const).map(([id, label, kind]) => [id, { label, kind, icon: KIND_ICON[kind] }]));

/** Accepted everywhere a card acquirer is signed. Crypto is global in principle but appears only in a country whose pack
 *  lists it (the country allows it and a licensed partner exists); no country lists it today. */
export const GLOBAL_CARD_NETWORKS = ["visa", "mastercard"] as const;

interface PackLike { card_networks?: readonly string[]; wallets?: readonly string[]; providers?: readonly string[] }

/** The options to show for one country, in a stable order: card networks, phone wallets, local methods, crypto last.
 *  "card" (the generic acquirer) is represented by the networks, so it is not shown twice. Unknown ids are skipped. */
export function paymentOptions(pack: PackLike | null): PaymentOption[] {
  const ids: string[] = [];
  const add = (id: string): void => { if (PAYMENT_METHODS[id] && !ids.includes(id)) ids.push(id); };
  (pack?.card_networks ?? GLOBAL_CARD_NETWORKS).forEach(add);
  (pack?.wallets ?? []).forEach(add);
  for (const p of pack?.providers ?? ["bank_transfer"]) if (p !== "card" && p !== "crypto") add(p);
  if (pack?.providers?.includes("crypto")) add("crypto");
  return ids.map((id) => ({ id, ...PAYMENT_METHODS[id]!, official: false as const }));
}
