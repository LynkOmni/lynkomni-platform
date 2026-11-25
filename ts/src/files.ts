/** LynkFiles' rules (SIX SERVICES UPDATE, master blueprint 69.7; section 4 step E3): the TypeScript port of core/files.py,
 *  checked against contract/vectors/files.v1.json. The register travels in ts/src/files.generated.ts (python3 tools/files_vectors.py).
 *  A file's type comes from its bytes; signers follow their order; a share link opens only while it may; a verification code
 *  shows nothing about who signed. */

export interface FilesRegister {
  content: { allowed: Record<string, string | null>; blocked_starts: string[]; max_mb: number };
  signing: { levels: Record<string, { partner: string | null }>; orders: string[]; states: string[]; code_groups: number; code_group_length: number; max_signers: number; link_days: number };
  sharing: { rights: string[]; max_days: number; default_days: number; password_min: number };
  [k: string]: unknown;
}

const FL_ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ";       // the Lynk Alphabet (core/queue_tickets.py)
const GB = 1024 ** 3;
const hex = (b: Uint8Array): string => Array.from(b.subarray(0, 16), (x) => x.toString(16).padStart(2, "0")).join("");

export function sniff(F: FilesRegister, data: Uint8Array): string | null {
  const head = hex(data);
  if (F.content.blocked_starts.some((b) => head.startsWith(b))) return "blocked";
  for (const [name, magic] of Object.entries(F.content.allowed)) if (magic && head.startsWith(magic)) return name;
  let text: string;
  try { text = new TextDecoder("utf-8", { fatal: true }).decode(data); } catch { return null; }
  for (const ch of text) { const c = ch.codePointAt(0)!; if (!("\t\n\r".includes(ch) || (c >= 32 && c !== 127))) return null; }
  return "text";
}

export function nextSigners(F: FilesRegister, order: string, signers: readonly string[], signed: readonly string[], declined: readonly string[] = []): string[] {
  if (!F.signing.orders.includes(order)) throw new Error("unknown order");
  if (declined.some((d) => signers.includes(d))) return [];
  const left = signers.filter((s) => !signed.includes(s));
  return order === "in_order" ? left.slice(0, 1) : left;
}

export function signRequestState(signers: readonly string[], signed: readonly string[], declined: readonly string[] = [], expired = false, cancelled = false): string {
  if (cancelled) return "cancelled";
  if (declined.some((d) => signers.includes(d))) return "declined";
  const done = signers.filter((s) => signed.includes(s));
  if (done.length === signers.length) return "completed";
  if (expired) return "expired";
  return done.length ? "partly_signed" : "sent";
}

export function shareOpen(link: { until: number; password_set?: boolean; stopped?: boolean }, now: number, password: boolean | null = null): [boolean, string | null] {
  if (link.stopped) return [false, "stopped"];
  if (now >= link.until) return [false, "expired"];
  if (link.password_set && password !== true) return [false, "password"];
  return [true, null];
}

export const shareDaysOk = (F: FilesRegister, days: unknown): boolean => typeof days === "number" && Number.isInteger(days) && days >= 1 && days <= F.sharing.max_days;

export function formatCode(F: FilesRegister, n: bigint): string {
  const g = F.signing.code_groups, len = F.signing.code_group_length, base = BigInt(FL_ALPHABET.length);
  const chars: string[] = [];
  for (let i = 0; i < g * len; i++) { chars.push(FL_ALPHABET[Number(n % base)]!); n /= base; }
  const s = chars.reverse().join("");
  const out: string[] = [];
  for (let i = 0; i < s.length; i += len) out.push(s.slice(i, i + len));
  return out.join("-");
}

export function codeOk(F: FilesRegister, code: unknown): boolean {
  if (typeof code !== "string") return false;
  const parts = code.toUpperCase().split("-");
  return parts.length === F.signing.code_groups && parts.every((p) => p.length === F.signing.code_group_length && [...p].every((ch) => FL_ALPHABET.includes(ch)));
}

export function fits(used: number, add: number, storageGb: number | null, extra100Gb = 0): boolean {
  if (storageGb === null) return true;
  return used + add <= (storageGb + 100 * extra100Gb) * GB;
}

export function levelPartner(F: FilesRegister, level: string): string | null {
  const l = F.signing.levels[level];
  if (!l) throw new Error("unknown signing level");
  return l.partner;
}
