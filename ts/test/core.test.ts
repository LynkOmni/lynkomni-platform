import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { Registry, IdAllocator, luhnDigit, parse } from "../src/ids.js";
import { Capabilities } from "../src/capability.js";
import { eventHash, signingBytes, verifyChain } from "../src/chain.js";

const root = `${process.cwd()}/..`;
const reg = new Registry(readFileSync(`${root}/contract/identifier-registry.v1.json`, "utf8"));
const idv = JSON.parse(readFileSync(`${root}/contract/vectors/identifiers.v1.json`, "utf8"));
const chain = JSON.parse(readFileSync(`${root}/contract/vectors/chain.v1.json`, "utf8"));

test("registry has the 38 approved types", () => { assert.equal(reg.types.size, 38); assert.ok(reg.types.has("DEV") && reg.types.has("CST")); });
test("identifier vectors from the Python reference", () => {
  for (const v of idv.valid) { assert.equal(parse(reg, v.id).payload, v.payload); assert.equal(luhnDigit(v.payload.slice(0, 11)), v.payload[11]); }
  for (const v of idv.invalid) assert.throws(() => parse(reg, v.id));
});
test("allocation is idempotent, unique, random, and leases are never reused", () => {
  const a = new IdAllocator(reg);
  assert.equal(a.assign("RCP", "r1"), a.assign("RCP", "r1"));
  const set = new Set(Array.from({ length: 300 }, (_, i) => a.assign("TXN", `t${i}`))); assert.equal(set.size, 300);
  const block = a.lease("RCP", "dev-1", 4); a.claim(block[0]!, "receipt-9", "dev-1");
  assert.throws(() => a.claim(block[1]!, "x", "dev-2"));
  assert.equal(a.release("dev-1"), 3); assert.equal(a.lookup(block[1]!)?.status, "retired");
  assert.throws(() => a.claim(block[1]!, "x", "dev-1"));
});
test("capability tokens are narrow, expiring and single use", () => {
  const c = new Capabilities("test-secret"), t = c.issue("pay_link", "LOINV-0000-0000-0000", "pay", 60, true, 1000);
  assert.throws(() => c.verify(t, "pay_link", "read", 1001));
  assert.equal(c.verify(t, "pay_link", "pay", 1001).action, "pay");
  assert.throws(() => c.verify(t, "pay_link", "pay", 1002));
  assert.throws(() => c.verify(c.issue("pay_link", "x", "pay", 10, true, 1000), "pay_link", "pay", 2000));
  const code = c.ticketCode("LOTKT-1111-1111-1118", 100);
  assert.notEqual(code, c.ticketCode("LOTKT-1111-1111-1118", 160)); assert.throws(() => c.redeemTicket(code, 220));
  assert.equal(c.redeemTicket(code, 105), "LOTKT-1111-1111-1118"); assert.throws(() => c.redeemTicket(code, 106));
});
test("canonical bytes and hashes match the Python reference exactly", () => {
  chain.events.forEach((e: never, i: number) => { assert.equal(signingBytes(e, chain.server_stamp_keys), chain.signing_bytes[i]); assert.equal(eventHash(e, chain.server_stamp_keys), chain.hashes[i]); });
  assert.equal(eventHash(chain.stamped_event, chain.server_stamp_keys), chain.stamped_hash);      // server stamps never change the hash
  assert.notEqual(eventHash(chain.tampered_event, chain.server_stamp_keys), chain.hashes[2]);
  assert.equal(verifyChain(chain.events, chain.server_stamp_keys), -1);
  assert.equal(verifyChain([chain.events[0], chain.tampered_event], chain.server_stamp_keys), 1);
  assert.throws(() => signingBytes({ x: 1.5 } as never, []));
});
