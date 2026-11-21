/** LynkVote's security core (VOTE UPDATE, master blueprint 68.7; section 4 step E1): the TypeScript port of core/vote_crypto.py,
 *  checked against contract/vectors/vote.v1.json. It runs on the voter's own device, in a browser and offline, so it carries its
 *  own SHA-256 and HMAC (checked against Node's in ts/test/vote.test.ts). Exponential ElGamal in the subgroup of order q of the
 *  RFC 7919 group ffdhe2048; trustees' key parts with commitments and proofs; every locked choice proved allowed; totals opened
 *  by a threshold of trustees with proofs; a shuffle with a cut-and-choose proof; tracking codes that chain the public list. */
import { VOTE } from "./vote.generated.js";

export type Ct = [bigint, bigint];
export const P = BigInt("0x" + VOTE.group.p_hex);
export const Q = (P - 1n) / 2n;
export const G = BigInt(VOTE.group.g);

// ---- SHA-256 and HMAC (FIPS 180-4, RFC 2104) -------------------------------------------------------------------------------------
const K256 = new Uint32Array([0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5, 0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3,
  0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174, 0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da, 0x983e5152, 0xa831c66d,
  0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967, 0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
  0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070, 0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a,
  0x5b9cca4f, 0x682e6ff3, 0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2]);
export function sha256(data: Uint8Array): Uint8Array {
  const l = data.length, n = Math.ceil((l + 9) / 64) * 64, m = new Uint8Array(n);
  m.set(data); m[l] = 0x80;
  const bits = l * 8; for (let i = 0; i < 8; i++) m[n - 1 - i] = Math.floor(bits / 2 ** (8 * i)) & 0xff;
  const h = new Uint32Array([0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a, 0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19]), w = new Uint32Array(64);
  const r = (x: number, k: number): number => (x >>> k) | (x << (32 - k));
  for (let o = 0; o < n; o += 64) {
    for (let i = 0; i < 16; i++) w[i] = (m[o + 4 * i]! << 24) | (m[o + 4 * i + 1]! << 16) | (m[o + 4 * i + 2]! << 8) | m[o + 4 * i + 3]!;
    for (let i = 16; i < 64; i++) {
      const a = w[i - 15]!, b = w[i - 2]!;
      w[i] = (w[i - 16]! + (r(a, 7) ^ r(a, 18) ^ (a >>> 3)) + w[i - 7]! + (r(b, 17) ^ r(b, 19) ^ (b >>> 10))) >>> 0;
    }
    let [a, b, c, d, e, f, g, hh] = [h[0]!, h[1]!, h[2]!, h[3]!, h[4]!, h[5]!, h[6]!, h[7]!];
    for (let i = 0; i < 64; i++) {
      const t1 = (hh + (r(e, 6) ^ r(e, 11) ^ r(e, 25)) + ((e & f) ^ (~e & g)) + K256[i]! + w[i]!) >>> 0;
      const t2 = ((r(a, 2) ^ r(a, 13) ^ r(a, 22)) + ((a & b) ^ (a & c) ^ (b & c))) >>> 0;
      hh = g; g = f; f = e; e = (d + t1) >>> 0; d = c; c = b; b = a; a = (t1 + t2) >>> 0;
    }
    h[0] = (h[0]! + a) >>> 0; h[1] = (h[1]! + b) >>> 0; h[2] = (h[2]! + c) >>> 0; h[3] = (h[3]! + d) >>> 0;
    h[4] = (h[4]! + e) >>> 0; h[5] = (h[5]! + f) >>> 0; h[6] = (h[6]! + g) >>> 0; h[7] = (h[7]! + hh) >>> 0;
  }
  const out = new Uint8Array(32); for (let i = 0; i < 8; i++) { out[4 * i] = h[i]! >>> 24; out[4 * i + 1] = (h[i]! >>> 16) & 0xff; out[4 * i + 2] = (h[i]! >>> 8) & 0xff; out[4 * i + 3] = h[i]! & 0xff; }
  return out;
}
const utf8 = (s: string): Uint8Array => new TextEncoder().encode(s);
export const hex = (b: Uint8Array): string => Array.from(b, (x) => x.toString(16).padStart(2, "0")).join("");
export function hmacSha256(key: Uint8Array, msg: Uint8Array): Uint8Array {
  let k = key.length > 64 ? sha256(key) : key; const kk = new Uint8Array(64); kk.set(k); k = kk;
  const ip = new Uint8Array(64 + msg.length), op = new Uint8Array(96);
  for (let i = 0; i < 64; i++) { ip[i] = k[i]! ^ 0x36; op[i] = k[i]! ^ 0x5c; }
  ip.set(msg, 64); op.set(sha256(ip), 64);
  return sha256(op);
}
const big = (b: Uint8Array): bigint => (b.length ? BigInt("0x" + hex(b)) : 0n);

// ---- numbers ---------------------------------------------------------------------------------------------------------------
export function modPow(b: bigint, e: bigint, m: bigint): bigint {
  let r = 1n; b %= m; if (b < 0n) b += m;
  while (e > 0n) { if (e & 1n) r = (r * b) % m; e >>= 1n; if (e) b = (b * b) % m; }
  return r;
}
export function inv(x: bigint): bigint {
  let [a, b, x0, x1] = [((x % P) + P) % P, P, 1n, 0n];
  while (b) { const q = a / b; [a, b] = [b, a - q * b]; [x0, x1] = [x1, x0 - q * x1]; }
  return ((x0 % P) + P) % P;
}
const md = (x: bigint, m: bigint): bigint => ((x % m) + m) % m;

export type Rng = () => bigint;
export function seededRng(seed: string): Rng {
  let n = 0;
  return () => { n++; const d = new Uint8Array(64); d.set(hmacSha256(utf8(seed), utf8(`${n}:a`))); d.set(hmacSha256(utf8(seed), utf8(`${n}:b`)), 32); return big(d) % (Q - 1n) + 1n; };
}
export function realRng(): Rng {
  return () => { const d = new Uint8Array(64); globalThis.crypto.getRandomValues(d); return big(d) % (Q - 1n) + 1n; };
}
type Item = bigint | number | string;
const enc = (x: Item): string => (typeof x === "string" ? x : x.toString(16));
export const challenge = (...items: Item[]): bigint => big(sha256(utf8(items.map(enc).join("|")))) % Q;

// ---- the trustees' key ------------------------------------------------------------------------------------------------------
export interface PublicPart { index: number; commits: bigint[]; proof: { t: bigint; z: bigint } }
export interface Part { index: number; coeffs: bigint[]; public: PublicPart }
export function trusteePart(index: number, threshold: number, rng: Rng, voteId: string): Part {
  const coeffs = Array.from({ length: threshold }, () => rng()), commits = coeffs.map((a) => modPow(G, a, P));
  const w = rng(), t = modPow(G, w, P), c = challenge("key", voteId, index, commits[0]!, t);
  return { index, coeffs, public: { index, commits, proof: { t, z: md(w + c * coeffs[0]!, Q) } } };
}
export function checkPart(pub: PublicPart, voteId: string): boolean {
  const c = challenge("key", voteId, pub.index, pub.commits[0]!, pub.proof.t);
  return modPow(G, pub.proof.z, P) === (pub.proof.t * modPow(pub.commits[0]!, c, P)) % P;
}
export const shareFor = (part: Part, j: number): bigint => md(part.coeffs.reduce((s, a, k) => s + a * modPow(BigInt(j), BigInt(k), Q), 0n), Q);
export function checkShare(pub: PublicPart, j: number, s: bigint): boolean {
  let rhs = 1n; pub.commits.forEach((ck, k) => { rhs = (rhs * modPow(ck, modPow(BigInt(j), BigInt(k), Q), P)) % P; });
  return modPow(G, s, P) === rhs;
}
export const jointKey = (pubs: readonly PublicPart[]): bigint => pubs.reduce((h, p) => (h * p.commits[0]!) % P, 1n);
export function publicShare(pubs: readonly PublicPart[], j: number): bigint {
  let y = 1n; for (const p of pubs) p.commits.forEach((ck, k) => { y = (y * modPow(ck, modPow(BigInt(j), BigInt(k), Q), P)) % P; });
  return y;
}

// ---- locking a choice --------------------------------------------------------------------------------------------------------
export const encrypt = (h: bigint, m: number, r: bigint): Ct => [modPow(G, r, P), (modPow(G, BigInt(m), P) * modPow(h, r, P)) % P];
export function proveIn(h: bigint, ct: Ct, m: number, r: bigint, allowed: readonly number[], rng: Rng, ctx: string): [bigint, bigint][] {
  const [A, B] = ct, parts = new Map<number, [bigint, bigint]>(), sim = new Map<number, [bigint, bigint]>();
  for (const v of allowed) {
    if (v === m) continue;
    const cv = rng(), zv = rng(), Bv = (B * inv(modPow(G, BigInt(v), P))) % P;
    parts.set(v, [(modPow(G, zv, P) * inv(modPow(A, cv, P))) % P, (modPow(h, zv, P) * inv(modPow(Bv, cv, P))) % P]);
    sim.set(v, [cv, zv]);
  }
  const w = rng(); parts.set(m, [modPow(G, w, P), modPow(h, w, P)]);
  const c = challenge("in", ctx, A, B, ...allowed.flatMap((v) => parts.get(v)!));
  let simSum = 0n; for (const [cv] of sim.values()) simSum += cv;
  const cm = md(c - simSum, Q);
  return allowed.map((v): [bigint, bigint] => (v === m ? [cm, md(w + cm * r, Q)] : sim.get(v)!));
}
export function checkIn(h: bigint, ct: Ct, allowed: readonly number[], proof: readonly [bigint, bigint][], ctx: string): boolean {
  const [A, B] = ct;
  if (proof.length !== allowed.length) return false;
  const xs: bigint[] = [];
  allowed.forEach((v, i) => { const [cv, zv] = proof[i]!, Bv = (B * inv(modPow(G, BigInt(v), P))) % P;
    xs.push((modPow(G, zv, P) * inv(modPow(A, cv, P))) % P, (modPow(h, zv, P) * inv(modPow(Bv, cv, P))) % P); });
  return challenge("in", ctx, A, B, ...xs) === md(proof.reduce((s, [cv]) => s + cv, 0n), Q);
}
export const multiply = (cts: readonly Ct[]): Ct => cts.reduce<Ct>((acc, [a, b]) => [(acc[0] * a) % P, (acc[1] * b) % P], [1n, 1n]);

export interface Contest { id: string; options: number; values: number[]; totals: number[] }
export interface LockedContest { contest: string; cts: Ct[]; proofs: [bigint, bigint][][]; total_proof: [bigint, bigint][]; _r?: bigint[] }
export function lockBallot(h: bigint, voteId: string, contests: readonly Contest[], choices: readonly number[][], rng: Rng): LockedContest[] {
  return contests.map((con, ci) => {
    const vals = choices[ci]!;
    if (vals.length !== con.options || vals.some((v) => !con.values.includes(v)) || !con.totals.includes(vals.reduce((a, b) => a + b, 0))) throw new Error("a choice outside the contest's rules");
    const rs = vals.map(() => rng()), cts = vals.map((v, i) => encrypt(h, v, rs[i]!)), ctx = `${voteId}:${con.id}`;
    const proofs = cts.map((ct, i) => proveIn(h, ct, vals[i]!, rs[i]!, con.values, rng, `${ctx}:${i}`));
    const total_proof = proveIn(h, multiply(cts), vals.reduce((a, b) => a + b, 0), md(rs.reduce((a, b) => a + b, 0n), Q), con.totals, rng, `${ctx}:total`);
    return { contest: con.id, cts, proofs, total_proof, _r: rs };
  });
}
/** What leaves the device: a copy without the random numbers (nothing done to it changes the device's own ballot). */
export const publicBallot = (b: readonly LockedContest[]): LockedContest[] =>
  b.map(({ _r, contest, cts, proofs, total_proof }) => ({ contest, cts: cts.map(([a, x]): Ct => [a, x]), proofs: proofs.map((p) => p.map(([c, z]): [bigint, bigint] => [c, z])), total_proof: total_proof.map(([c, z]): [bigint, bigint] => [c, z]) }));
export function checkBallot(h: bigint, voteId: string, contests: readonly Contest[], ballot: readonly LockedContest[]): boolean {
  if (ballot.length !== contests.length) return false;
  return contests.every((con, i) => {
    const c = ballot[i]!, ctx = `${voteId}:${con.id}`;
    if (c.contest !== con.id || c.cts.length !== con.options) return false;
    if (!c.cts.every((ct) => ct.every((x) => x > 0n && x < P && modPow(x, Q, P) === 1n))) return false;
    if (!c.cts.every((ct, k) => checkIn(h, ct, con.values, c.proofs[k]!, `${ctx}:${k}`))) return false;
    return checkIn(h, multiply(c.cts), con.totals, c.total_proof, `${ctx}:total`);
  });
}

// ---- the voter checks the device, and the receipt -------------------------------------------------------------------------------
export const challengeDevice = (h: bigint, ballot: readonly LockedContest[], choices: readonly number[][]): boolean =>
  ballot.every((c, i) => choices[i]!.every((v, k) => { const e = encrypt(h, v, c._r![k]!), ct = c.cts[k]!; return e[0] === ct[0] && e[1] === ct[1]; }));
export function trackingCode(previous: string, voteId: string, ballot: readonly LockedContest[]): string {
  const body = publicBallot(ballot).flatMap((c) => c.cts.flatMap((ct) => ct.map((x) => x.toString(16)))).join("|");
  return hex(sha256(utf8(`${previous}|${voteId}|${body}`)));
}
export const publicList = (entries: readonly { code: string }[]): { codes: string[]; head: string } =>
  ({ codes: entries.map((e) => e.code).sort(), head: entries.length ? entries[entries.length - 1]!.code : hex(sha256(utf8("empty"))) });

// ---- opening the total ---------------------------------------------------------------------------------------------------------
export interface Partial { index: number; d: bigint; proof: { a: bigint; b: bigint; z: bigint } }
export function partialOpen(j: number, xj: bigint, ct: Ct, rng: Rng, ctx: string): Partial {
  const A = ct[0], d = modPow(A, xj, P), w = rng(), a = modPow(G, w, P), b = modPow(A, w, P), c = challenge("open", ctx, j, A, d, a, b);
  return { index: j, d, proof: { a, b, z: md(w + c * xj, Q) } };
}
export function checkPartial(pubs: readonly PublicPart[], part: Partial, ct: Ct, ctx: string): boolean {
  const A = ct[0], y = publicShare(pubs, part.index), c = challenge("open", ctx, part.index, A, part.d, part.proof.a, part.proof.b);
  return modPow(G, part.proof.z, P) === (part.proof.a * modPow(y, c, P)) % P && modPow(A, part.proof.z, P) === (part.proof.b * modPow(part.d, c, P)) % P;
}
export function lagrangeAtZero(j: number, indices: readonly number[]): bigint {
  let num = 1n, den = 1n;
  for (const k of indices) if (k !== j) { num = md(num * BigInt(-k), Q); den = md(den * BigInt(j - k), Q); }
  return md(num * modPow(den, Q - 2n, Q), Q);
}
export function combine(ct: Ct, parts: readonly Partial[], limit: number): number {
  const idx = parts.map((p) => p.index);
  let D = 1n; for (const p of parts) D = (D * modPow(p.d, lagrangeAtZero(p.index, idx), P)) % P;
  const gm = (ct[1] * inv(D)) % P;
  let acc = 1n;
  for (let m = 0; m <= limit; m++) { if (acc === gm) return m; acc = (acc * G) % P; }
  throw new Error("the opened value is out of range");
}

// ---- shuffling before ballots are read one by one ------------------------------------------------------------------------------
const reenc = (h: bigint, ct: Ct, s: bigint): Ct => [(ct[0] * modPow(G, s, P)) % P, (ct[1] * modPow(h, s, P)) % P];
function perm(n: number, rng: Rng): number[] {
  const idx = Array.from({ length: n }, (_, i) => i);
  for (let i = n - 1; i > 0; i--) { const j = Number(rng() % BigInt(i + 1)); [idx[i], idx[j]] = [idx[j]!, idx[i]!]; }
  return idx;
}
function apply(h: bigint, rows: readonly Ct[][], p: readonly number[], rand: readonly bigint[][]): Ct[][] {
  const out: Ct[][] = new Array(rows.length);
  rows.forEach((row, i) => { out[p[i]!] = row.map((ct, k) => reenc(h, ct, rand[i]![k]!)); });
  return out;
}
export interface ShuffleProofRound { shadow: Ct[][]; open: "in" | "out"; perm: number[]; rand: bigint[][] }
export interface Shuffled { rows: Ct[][]; proof: ShuffleProofRound[] }
const flat = (rows: readonly Ct[][]): bigint[] => rows.flatMap((row) => row.flatMap((ct) => ct));
export function shuffle(h: bigint, rows: readonly Ct[][], rng: Rng, ctx: string, rounds: number = VOTE.shuffle.rounds): Shuffled {
  const n = rows.length, width = n ? rows[0]!.length : 0;
  const p = perm(n, rng), rand = Array.from({ length: n }, () => Array.from({ length: width }, () => rng())), out = apply(h, rows, p, rand);
  const shadows: [number[], bigint[][], Ct[][]][] = [];
  for (let t = 0; t < rounds; t++) {
    const sp = perm(n, rng), sr = Array.from({ length: n }, () => Array.from({ length: width }, () => rng()));
    shadows.push([sp, sr, apply(h, rows, sp, sr)]);
  }
  const bits = challenge("shuffle", ctx, ...flat(out), ...shadows.flatMap(([, , sh]) => flat(sh)));
  const proof = shadows.map(([sp, sr, sh], t): ShuffleProofRound => {
    if (((bits >> BigInt(t)) & 1n) === 0n) return { shadow: sh, open: "in", perm: sp, rand: sr };
    const p2 = new Array<number>(n).fill(0), r2: bigint[][] = Array.from({ length: n }, () => new Array<bigint>(width).fill(0n));
    for (let i = 0; i < n; i++) { p2[sp[i]!] = p[i]!; r2[sp[i]!] = rand[i]!.map((a, k) => md(a - sr[i]![k]!, Q)); }
    return { shadow: sh, open: "out", perm: p2, rand: r2 };
  });
  return { rows: out, proof };
}
const sameRows = (a: readonly Ct[][], b: readonly Ct[][]): boolean => a.length === b.length && a.every((row, i) => row.length === b[i]!.length && row.every((ct, k) => ct[0] === b[i]![k]![0] && ct[1] === b[i]![k]![1]));
export function checkShuffle(h: bigint, rows: readonly Ct[][], s: Shuffled, ctx: string): boolean {
  if (s.rows.length !== rows.length || s.proof.length > 256) return false;
  const bits = challenge("shuffle", ctx, ...flat(s.rows), ...s.proof.flatMap((p) => flat(p.shadow)));
  return s.proof.every((p, t) => {
    const want = ((bits >> BigInt(t)) & 1n) === 0n ? "in" : "out";
    if (p.open !== want || [...p.perm].sort((a, b) => a - b).some((v, i) => v !== i)) return false;
    const [src, dst] = want === "in" ? [rows, p.shadow] : [p.shadow, s.rows];
    return sameRows(apply(h, src, p.perm, p.rand), dst);
  });
}
