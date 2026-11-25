import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { sniff, nextSigners, signRequestState, shareOpen, shareDaysOk, formatCode, codeOk, fits, levelPartner } from "../src/files.js";
import { FILES as F } from "../src/files.generated.js";

const root = new URL("../../..", import.meta.url).pathname;
const V = JSON.parse(readFileSync(`${root}/contract/vectors/files.v1.json`, "utf8"));
const attempt = (f: () => unknown) => { try { return { value: f() }; } catch { return { error: true }; } };
const bytes = (h: string) => new Uint8Array((h.match(/../g) ?? []).map((x) => parseInt(x, 16)));
const GB = 1024 ** 3;

test("a file's type comes from its bytes and programs are refused, as in the Python reference (69.7)", () => {
  for (const c of V.sniff) assert.equal(sniff(F, bytes(c.hex)), c.expect, c.hex);
});
test("signing order, request states and share links agree with the Python reference", () => {
  for (const c of V.next) assert.deepEqual(attempt(() => nextSigners(F, c.o, ["a", "b", "c"], c.signed, c.declined)), c.expect, JSON.stringify(c));
  for (const c of V.states) assert.equal(signRequestState(["a", "b", "c"], c.signed, c.declined, c.exp, c.can), c.expect, JSON.stringify(c));
  for (const c of V.share) assert.deepEqual(shareOpen(c.link, c.now, c.pw), c.expect, JSON.stringify(c));
  for (const c of V.days) assert.equal(shareDaysOk(F, c.d), c.expect, JSON.stringify(c));
});
test("verification codes, storage and signing levels agree with the Python reference", () => {
  for (const c of V.format) assert.equal(formatCode(F, BigInt(c.n)), c.expect, c.n);
  for (const c of V.codes) assert.equal(codeOk(F, c.c), c.expect, String(c.c));
  for (const c of V.fits) assert.equal(fits(c.u, c.a, c.g, c.x), c.expect, JSON.stringify(c));
  for (const c of V.levels) assert.deepEqual(attempt(() => levelPartner(F, c.l)), c.expect, c.l);
  assert.equal(fits(5 * GB, 1, 5), false);
});
