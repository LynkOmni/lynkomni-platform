/** The shared username check (blueprint 44 B, Step 0): one rule for every username in LynkOmni, the same in every language.
 *  Port of core/usernames.py; the rule and the reserved words come from the generated data, and contract/vectors/usernames.v1.json
 *  proves this port agrees with the Python reference. */
import { RESERVED, USERNAME_RULE } from "./usernames.generated.js";

export type Reason = "empty" | "too_short" | "too_long" | "bad_character" | "leading_or_trailing_dot" | "double_dot" |
  "web_address_ending" | "reserved_word" | "held_for_review" | null;
export interface Check { ok: boolean; username: string; reason: Reason; looksLike?: string }

const LOOK = Object.entries(USERNAME_RULE.look_alike_map).sort((a, b) => b[0].length - a[0].length);

/** Not case-sensitive: the stored form is lowercase without a leading @ or spaces around it. */
export const normalize = (value: string | null | undefined): string => (value ?? "").trim().replace(/^@/, "").toLowerCase();

/** What a username looks like at a glance: look-alike letters and separators folded away. */
export function skeleton(name: string): string {
  let s = name.toLowerCase();
  for (const [a, b] of LOOK) s = s.split(a).join(b);
  return s.replace(/(.)\1+/g, "$1");
}

const RESERVED_SKELETONS = new Map<string, string>();
for (const w of RESERVED) RESERVED_SKELETONS.set(skeleton(w), w);

export function check(value: string | null | undefined): Check {
  const u = normalize(value);
  if (!u) return { ok: false, username: u, reason: "empty" };
  if (u.length < USERNAME_RULE.min) return { ok: false, username: u, reason: "too_short" };
  if (u.length > USERNAME_RULE.max) return { ok: false, username: u, reason: "too_long" };
  if (/[^a-z0-9._]/.test(u)) return { ok: false, username: u, reason: "bad_character" };
  if (u.startsWith(".") || u.endsWith(".")) return { ok: false, username: u, reason: "leading_or_trailing_dot" };
  if (u.includes("..")) return { ok: false, username: u, reason: "double_dot" };
  for (const ending of USERNAME_RULE.reserved_endings) if (u.endsWith(ending)) return { ok: false, username: u, reason: "web_address_ending" };
  const plain = u.replace(/[._]/g, "");
  if (RESERVED.has(u) || RESERVED.has(plain)) return { ok: false, username: u, reason: "reserved_word" };
  const sk = skeleton(u);
  const like = RESERVED_SKELETONS.get(sk);
  if (like !== undefined && sk.length >= 3) return { ok: false, username: u, reason: "held_for_review", looksLike: like };
  return { ok: true, username: u, reason: null };
}

/** Shown as @name; addresses carry it without the @. */
export const display = (username: string): string => `@${normalize(username)}`;

/** Strips leading and trailing full stops and underscores without a backtracking regular expression. */
const trimDots = (s: string): string => {
  let a = 0, b = s.length;
  while (a < b && (s[a] === "." || s[a] === "_")) a++;
  while (b > a && (s[b - 1] === "." || s[b - 1] === "_")) b--;
  return s.slice(a, b);
};

/** Free usernames close to a wanted one, for the "taken" and "refused" states of the username field. */
export function suggestions(value: string, taken: (u: string) => boolean = () => false, limit = 3): string[] {
  let base = trimDots(normalize(value).replace(/\s+/g, ".").replace(/[^a-z0-9._]/g, "").replace(/\.\.+/g, ".")) || "shop";
  base = base.slice(0, USERNAME_RULE.max - 4);
  const out: string[] = [];
  for (const cand of [base, `${base}.shop`, `${base}_1`, `${base}.store`, `${base}.2`, `the.${base}`]) {
    const c = check(cand);
    if (c.ok && !taken(c.username) && !out.includes(c.username)) out.push(c.username);
    if (out.length >= limit) break;
  }
  return out;
}
