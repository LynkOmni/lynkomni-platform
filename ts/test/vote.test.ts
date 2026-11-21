import { test } from "node:test";
import assert from "node:assert/strict";
import { createHash, createHmac } from "node:crypto";
import { readFileSync } from "node:fs";
import * as V from "../src/votecrypto.js";
import * as C from "../src/votecount.js";

const root = new URL("../../..", import.meta.url).pathname;
const D = JSON.parse(readFileSync(`${root}/contract/vectors/vote.v1.json`, "utf8"));
const X = D.crypto;
// hex text back into numbers: every string of hex digits inside the security part is a number
const big = (v: unknown): any => (typeof v === "string" && /^[0-9a-f]+$/.test(v) ? BigInt("0x" + v) : Array.isArray(v) ? v.map(big) : v && typeof v === "object" ? Object.fromEntries(Object.entries(v).map(([k, x]) => [k, k === "contest" || k === "open" ? x : big(x)])) : v);
const hx = (v: unknown): any => (typeof v === "bigint" ? v.toString(16) : typeof v === "number" ? v.toString(16) : Array.isArray(v) ? v.map(hx) : v && typeof v === "object" ? Object.fromEntries(Object.entries(v).map(([k, x]) => [k, k === "contest" || k === "open" ? x : hx(x)])) : v);
const num = (v: any) => ({ ...v, index: Number(v.index) });

test("the device's own SHA-256 and HMAC agree with Node's", () => {
  for (const s of ["", "abc", "a".repeat(55), "a".repeat(56), "a".repeat(64), "LynkVote · ballot ✓".repeat(9)]) {
    const b = new TextEncoder().encode(s);
    assert.equal(V.hex(V.sha256(b)), createHash("sha256").update(s).digest("hex"));
    assert.equal(V.hex(V.hmacSha256(new TextEncoder().encode("key-" + s), b)), createHmac("sha256", "key-" + s).update(s).digest("hex"));
  }
  assert.equal(V.challenge("key", X.vote_id, 10, 255n).toString(16), X.challenge_example);
});

test("the group is the published one and the same vote gives the same numbers in both languages (VOTE UPDATE 68.7)", () => {
  assert.equal(V.modPow(V.G, V.Q, V.P), 1n);
  const rng = V.seededRng(X.seed), vid = X.vote_id;
  const parts = [1, 2, 3].map((i) => V.trusteePart(i, X.threshold, rng, vid)), pubs = parts.map((p) => p.public);
  assert.deepEqual(hx(parts.map((p) => ({ index: p.index, coeffs: p.coeffs, public: p.public }))), X.parts);
  assert.ok(pubs.every((p) => V.checkPart(p, vid)));
  const x: Record<number, bigint> = {}; for (const j of [1, 2, 3]) x[j] = parts.reduce((s, p) => s + V.shareFor(p, j), 0n) % V.Q;
  assert.deepEqual(hx(Object.fromEntries(Object.entries(x))), X.shares);
  assert.ok(parts.every((p) => [1, 2, 3].every((j) => V.checkShare(p.public, j, V.shareFor(p, j)))));
  const h = V.jointKey(pubs); assert.equal(h.toString(16), X.joint_key);
  let prev = "start"; const codes: string[] = [], ballots: V.LockedContest[][] = [];
  for (const ch of X.choices) { const b = V.lockBallot(h, vid, X.contests, ch, rng); prev = V.trackingCode(prev, vid, b); codes.push(prev); ballots.push(b); }
  assert.deepEqual(hx(ballots.map(V.publicBallot)), X.ballots);
  assert.deepEqual(codes, X.codes);
  const ch = V.lockBallot(h, vid, X.contests, X.challenged_choices, rng);
  assert.deepEqual(hx(ch), X.challenged);
  assert.ok(V.challengeDevice(h, ch, X.challenged_choices), "the device locked what the voter chose");
  assert.ok(!V.challengeDevice(h, ch, [[1, 0, 0], [1, 0]]), "a device that lied is caught");
  assert.deepEqual(V.publicList(codes.map((code) => ({ code }))), X.public_list);
});

test("ballots, openings and the shuffle made by Python check out here, and tampering fails", () => {
  const pubs = X.parts.map((p: any) => num(big(p.public))) as V.PublicPart[], h = big(X.joint_key) as bigint, vid = X.vote_id;
  const ballots = X.ballots.map(big) as V.LockedContest[][];
  assert.ok(ballots.every((b) => V.checkBallot(h, vid, X.contests, b)));
  const forged = structuredClone(ballots[0]!); forged[0]!.cts[1] = forged[0]!.cts[0]!;                 // two marks for the chair
  assert.ok(!V.checkBallot(h, vid, X.contests, forged));
  assert.throws(() => V.lockBallot(h, vid, X.contests, [[1, 1, 0], [0, 0]], V.seededRng("x")), "a double vote is refused on the device");
  const totals = X.opens.map((o: any) => {
    const ct = big(o.ct) as V.Ct, parts = o.parts.map((p: any) => num(big(p))) as V.Partial[];
    assert.ok(parts.every((p) => V.checkPartial(pubs, p, ct, o.ctx)));
    const lied = { ...parts[0]!, d: (parts[0]!.d * V.G) % V.P };
    assert.ok(!V.checkPartial(pubs, lied, ct, o.ctx), "a trustee's false opening is caught");
    return V.combine(ct, parts, ballots.length);
  });
  assert.deepEqual(totals, X.totals);
  const rows = big(X.shuffle_rows) as V.Ct[][], sh = big(X.shuffled);
  sh.proof = sh.proof.map((p: any) => ({ ...p, perm: p.perm.map(Number) }));
  assert.ok(V.checkShuffle(h, rows, sh, `${vid}:mix`));
  assert.ok(!V.checkShuffle(h, rows, { rows: [rows[0]!, ...sh.rows.slice(1)], proof: sh.proof }, `${vid}:mix`), "a swapped ballot is caught");
});

const run = (method: string, args: any[], kw: Record<string, unknown>): unknown => {
  const seed = (kw["seed"] as string | undefined) ?? "";
  switch (method) {
    case "plurality": return C.plurality(args[0], args[1], args[2] ?? 1, seed);
    case "two_round": return C.twoRound(args[0], args[1], seed);
    case "approval": return C.approval(args[0], args[1], args[2] ?? 1, seed);
    case "weighted": return C.weighted(args[0], args[1], args[2] ?? 1, seed);
    case "cumulative": return C.cumulative(args[0], args[1], args[2], args[3] ?? 1, seed);
    case "quadratic": return C.quadratic(args[0], args[1], args[2], seed);
    case "score": return C.score(args[0], args[1], args[2], args[3] ?? 1, seed);
    case "star": return C.star(args[0], args[1], args[2], seed);
    case "majority_judgment": return C.majorityJudgment(args[0], args[1], args[2], seed);
    case "budget": return C.budget(args[0], args[1], args[2], seed);
    case "irv": return C.irv(args[0], args[1], seed);
    case "stv": return C.stv(args[0], args[1], args[2], seed);
    case "borda": return C.borda(args[0], args[1], seed);
    case "bucklin": return C.bucklin(args[0], args[1], seed);
    case "ranked_pairs": return C.rankedPairs(args[0], args[1], seed);
    case "schulze": return C.schulze(args[0], args[1], seed);
    case "dhondt": return C.dhondt(args[0], args[1], args[2] ?? 0, seed);
    case "sainte_lague": return C.sainteLague(args[0], args[1], args[2] ?? 0, seed);
    case "modified_sainte_lague": return C.modifiedSainteLague(args[0], args[1], args[2] ?? 0, seed);
    default: return C.largestRemainder(args[0], args[1], method.split("_").pop(), 0, seed);
  }
};
test("every counting method agrees with the Python reference on the published examples (VOTE UPDATE 68.5)", () => {
  for (const c of D.counting.cases) assert.deepEqual(JSON.parse(JSON.stringify(run(c.method, c.args, c.kw))), c.expect, c.method);
  for (const c of D.counting.yes_no) assert.deepEqual(C.yesNo(c.ballots, c.majority, c.members, c.quorum, c.custom), c.expect);
  assert.deepEqual(C.lots(D.counting.lots.cands, D.counting.lots.seed), D.counting.lots.expect);
});
