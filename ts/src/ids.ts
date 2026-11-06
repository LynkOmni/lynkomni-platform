/** LynkOmni Universal Identifier Standard: LO + TYPE + '-XXXX-XXXX-XXXX'. Random, Luhn check digit, strings only, never reused. */
import { randomInt } from "node:crypto";

export interface IdType { code: string; prefix: string; name: string }
export class Registry {
  readonly types = new Map<string, IdType>();
  constructor(json: string) { for (const t of JSON.parse(json).types as IdType[]) this.types.set(t.code, t); }
}

export function luhnDigit(p11: string): string {
  let s = 0;
  [...p11].reverse().forEach((ch, i) => { let d = Number(ch) * (i % 2 === 0 ? 2 : 1); if (d > 9) d -= 9; s += d; });
  return String((10 - (s % 10)) % 10);
}
export function luhnOk(p12: string): boolean {
  let s = 0;
  [...p12].reverse().forEach((ch, i) => { let d = Number(ch) * (i % 2 === 1 ? 2 : 1); if (d > 9) d -= 9; s += d; });
  return s % 10 === 0;
}
export const format = (code: string, p12: string): string => `LO${code}-${p12.slice(0, 4)}-${p12.slice(4, 8)}-${p12.slice(8)}`;

/** Format check only. A well-formed ID proves nothing about existence or access. */
export function parse(reg: Registry, id: string): { code: string; payload: string } {
  const m = /^LO([A-Z]{2,4})-(\d{4})-(\d{4})-(\d{4})$/.exec(id ?? "");
  if (!m || !reg.types.has(m[1]!)) throw new Error("not a registered LynkOmni identifier");
  const payload = `${m[2]}${m[3]}${m[4]}`;
  if (!luhnOk(payload)) throw new Error("check digit does not match");
  return { code: m[1]!, payload };
}

export type Status = "assigned" | "leased" | "retired";
interface Row { type: string; internalId: string | null; status: Status; leasedTo: string | null }

/** In-memory allocator with the same rules as the SQL schema. Production uses the database constraints. */
export class IdAllocator {
  private rows = new Map<string, Row>();
  private byInternal = new Map<string, string>();
  constructor(private reg: Registry) {}
  private fresh(code: string, row: Omit<Row, "type">): string {
    if (!this.reg.types.has(code)) throw new Error(`type ${code} is not registered`);
    for (let i = 0; i < 50; i++) {
      const p11 = String(randomInt(0, 100_000_000_000)).padStart(11, "0");
      const id = format(code, p11 + luhnDigit(p11));
      if (!this.rows.has(id)) { this.rows.set(id, { type: code, ...row }); return id; }   // a collision is retried, never reused
    }
    throw new Error("could not allocate an identifier");
  }
  assign(code: string, internalId: string): string {
    const key = `${code}|${internalId}`, have = this.byInternal.get(key);
    if (have) return have;
    const id = this.fresh(code, { internalId, status: "assigned", leasedTo: null }); this.byInternal.set(key, id); return id;
  }
  lease(code: string, device: string, n = 50): string[] {
    return Array.from({ length: n }, () => this.fresh(code, { internalId: null, status: "leased", leasedTo: device }));
  }
  claim(id: string, internalId: string, device: string): void {
    const r = this.rows.get(id);
    if (!r || r.status !== "leased" || r.leasedTo !== device) throw new Error("not leased to this device");
    r.internalId = internalId; r.status = "assigned"; this.byInternal.set(`${r.type}|${internalId}`, id);
  }
  release(device: string): number {   // unused leased IDs are retired for good
    let n = 0; for (const r of this.rows.values()) if (r.leasedTo === device && r.status === "leased") { r.status = "retired"; n++; } return n;
  }
  retire(id: string): void { const r = this.rows.get(id); if (r) r.status = "retired"; }
  lookup(id: string): Row | undefined { return this.rows.get(id); }
}
