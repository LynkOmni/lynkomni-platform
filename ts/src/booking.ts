/** LynkBooking's money and figures for the office services (BOOKING UPDATE, master blueprint 64; section 4 step E4a): the TypeScript
 *  port of core/booking.py, checked against contract/vectors/booking.v1.json. The locked commission rule travels in
 *  ts/src/booking.generated.ts (python3 tools/booking_vectors.py). Nothing on a business's own customers; a forecast is an estimate. */
import { roundDiv } from "./books.js";

export type CommissionRules = Record<string, number>;
export const KINDS = ["appointment", "stay", "tour", "event", "cinema", "transport", "transfer", "rental", "space", "thing", "table", "class"] as const;
export const SOURCES = ["lynkbooking", "own_link", "qr", "front_desk", "returning", "partner"] as const;
const OWN = ["own_link", "qr", "front_desk", "returning"];
const RATE: Record<string, string> = { stay: "stay_bps", tour: "tour_bps", transport: "transport_bps", transfer: "transport_bps", rental: "rental_and_space_bps",
  space: "rental_and_space_bps", thing: "rental_and_space_bps", class: "class_bps" };

export function commission(rules: CommissionRules, kind: string, source: string, amount: number, firstVisit = false, guests = 0, paidTickets = 0,
                           fixed: Partial<Record<"cap" | "ticket" | "guest", number>> = {}): number | null {
  if (!(KINDS as readonly string[]).includes(kind) || !(SOURCES as readonly string[]).includes(source)) throw new Error("unknown booking kind or source");
  if (!Number.isInteger(amount) || amount < 0) throw new Error("an amount is whole minor units");
  if (OWN.includes(source)) return roundDiv(amount * rules.own_customers_bps!, 10000);
  if (source === "partner") return null;
  const f = { cap: rules.appointment_first_visit_cap_cents!, ticket: rules.event_ticket_cents!, guest: rules.table_guest_cents!, ...fixed };
  if (kind === "appointment") return firstVisit ? Math.min(roundDiv(amount * rules.appointment_first_visit_bps!, 10000), f.cap) : 0;
  if (kind === "event" || kind === "cinema") return amount === 0 ? 0 : roundDiv(amount * rules.event_bps!, 10000) + paidTickets * f.ticket;
  if (kind === "table") return guests * f.guest;
  return roundDiv(amount * rules[RATE[kind]!]!, 10000);
}

export function busyForecast(bookings: readonly { weekday: number; hour: number }[], weeks: number): { estimate: true; slots: [number, number, number][] } {
  if (!Number.isInteger(weeks) || weeks < 1) throw new Error("at least one week");
  const count = new Map<string, number>();
  for (const b of bookings) {
    if (!(b.weekday >= 0 && b.weekday <= 6 && b.hour >= 0 && b.hour <= 23)) throw new Error("a weekday is 0 to 6 and an hour 0 to 23");
    const k = `${b.weekday},${b.hour}`;
    count.set(k, (count.get(k) ?? 0) + 1);
  }
  const slots = [...count.entries()].map(([k, n]) => { const [w, h] = k.split(",").map(Number); return [w!, h!, roundDiv(n, weeks)] as [number, number, number]; });
  slots.sort((a, b) => a[0] - b[0] || a[1] - b[1]);
  return { estimate: true, slots };
}

export function emptyHours(capacity: Record<string, number>, booked: Record<string, number>): [string, number][] {
  const out: [string, number][] = [];
  for (const [slot, cap] of Object.entries(capacity)) { const left = cap - (booked[slot] ?? 0); if (left > 0) out.push([slot, left]); }
  return out.sort((a, b) => b[1] - a[1] || (a[0] < b[0] ? -1 : a[0] > b[0] ? 1 : 0));
}

export function noShowRate(confirmed: number, noShows: number): number | null {
  if (confirmed <= 0) return null;
  if (!(noShows >= 0 && noShows <= confirmed)) throw new Error("no-shows are between zero and the confirmed bookings");
  return roundDiv(noShows * 10000, confirmed);
}
