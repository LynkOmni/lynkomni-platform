/** Capability tokens: one narrow action, expiring, never read access. Public identifiers are not capabilities. */
import { createHmac, randomBytes } from "node:crypto";

const WINDOW = 30;
const KINDS = new Set(["ticket_entry", "pay_link", "receipt_verify", "shop_door", "newsletter_confirm", "newsletter_unsubscribe"]);
const sig = (secret: string, body: string, n = 32): string => createHmac("sha256", secret).update(body).digest("hex").slice(0, n);
const same = (a: string, b: string): boolean => { if (a.length !== b.length) return false; let d = 0; for (let i = 0; i < a.length; i++) d |= a.charCodeAt(i) ^ b.charCodeAt(i); return d === 0; };

export class Capabilities {
  private used = new Set<string>();
  constructor(private secret: string) {}
  issue(kind: string, subject: string, action: string, ttl = 3600, singleUse = true, now = Date.now() / 1000): string {
    if (!KINDS.has(kind)) throw new Error("unknown capability kind");
    const body = JSON.stringify({ k: kind, s: subject, a: action, x: Math.floor(now + ttl), j: randomBytes(8).toString("hex"), u: singleUse });
    return `${Buffer.from(body).toString("base64url")}.${sig(this.secret, body)}`;
  }
  verify(token: string, kind: string, action: string, now = Date.now() / 1000): { subject: string; action: string } {
    const i = token.lastIndexOf("."); if (i < 0) throw new Error("invalid token");
    let body: string, c: { k: string; s: string; a: string; x: number; j: string; u: boolean };
    try { body = Buffer.from(token.slice(0, i), "base64url").toString("utf8"); c = JSON.parse(body); } catch { throw new Error("invalid token"); }
    if (!same(token.slice(i + 1), sig(this.secret, body)) || c.k !== kind || c.a !== action) throw new Error("token does not allow this action");
    if (c.x < now) throw new Error("token expired");
    if (c.u) { if (this.used.has(c.j)) throw new Error("token already used"); this.used.add(c.j); }
    return { subject: c.s, action: c.a };   // only what the token names, never a record
  }
  ticketCode(ticketId: string, now = Date.now() / 1000): string { const w = Math.floor(now / WINDOW); return `${ticketId}.${w}.${sig(this.secret, `${ticketId}|${w}`, 12)}`; }
  redeemTicket(code: string, now = Date.now() / 1000): string {
    const p = code.split("."); if (p.length < 3) throw new Error("invalid ticket code");
    const s = p.pop()!, w = Number(p.pop()), id = p.join("."), cur = Math.floor(now / WINDOW);
    if (![cur, cur - 1].includes(w) || !same(s, sig(this.secret, `${id}|${w}`, 12))) throw new Error("ticket code expired or invalid");
    if (this.used.has(`ticket:${id}`)) throw new Error("ticket already used");
    this.used.add(`ticket:${id}`); return id;
  }
}
