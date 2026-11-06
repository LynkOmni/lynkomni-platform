/** Contract v1 canonical serialization and hash chain. Must match the Python reference byte for byte. */
import { createHash } from "node:crypto";

type J = null | boolean | number | string | J[] | { [k: string]: J };
export function canonical(v: J): string {
  if (typeof v === "number" && !Number.isInteger(v)) throw new Error("floating point numbers are not allowed in events");
  if (v === null || typeof v !== "object") return JSON.stringify(v);
  if (Array.isArray(v)) return `[${v.map(canonical).join(",")}]`;
  return `{${Object.keys(v).sort().map((k) => `${JSON.stringify(k)}:${canonical((v as { [k: string]: J })[k]!)}`).join(",")}}`;
}
export function signingBytes(evt: { [k: string]: J }, stampKeys: string[]): string {
  const skip = new Set([...stampKeys, "signature"]), body: { [k: string]: J } = {};
  for (const [k, v] of Object.entries(evt)) if (!skip.has(k)) body[k] = v;
  return canonical(body);
}
export const eventHash = (evt: { [k: string]: J }, stampKeys: string[]): string => createHash("sha256").update(signingBytes(evt, stampKeys)).digest("hex");

/** Returns the index of the first event that breaks the chain, or -1 if the whole stream is intact. */
export function verifyChain(events: { [k: string]: J }[], stampKeys: string[]): number {
  let prev = "GENESIS";
  for (let i = 0; i < events.length; i++) {
    const e = events[i]!;
    if (e["device_seq"] !== i + 1 || e["prev_hash"] !== prev) return i;
    prev = eventHash(e, stampKeys);
  }
  return -1;
}
