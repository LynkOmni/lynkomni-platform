import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { canMove, shownState, editAllowed, ordered, hasWord, mask, liveSign, ownConnection, soundFor, routeSupport, routeTeam, escalate, replyTime, offlineRule, cardAction, toolsOk } from "../src/chat.js";
import type { ChatState, Msg } from "../src/chat.js";
import { CHAT } from "../src/chat.generated.js";

const root = new URL("../../..", import.meta.url).pathname;
const V = JSON.parse(readFileSync(`${root}/contract/vectors/chat.v1.json`, "utf8"));

test("message states, edits and order agree with the Python reference (CHAT UPDATE)", () => {
  for (const c of V.moves) assert.equal(canMove(CHAT, c.from, c.to, c.writer), c.expect, JSON.stringify(c));
  for (const c of V.shown) assert.equal(shownState(c.state as ChatState, c.reader, c.seen), c.expect, JSON.stringify(c));
  for (const c of V.edits) assert.equal(editAllowed(CHAT, c.body, c.author, c.me, c.min), c.expect, JSON.stringify(c));
  assert.deepEqual(ordered(V.ordered.in as Msg[]).map((m) => m.id), V.ordered.expect);
});
test("masking: card numbers and codes never leave the device", () => {
  for (const c of V.words) assert.equal(hasWord(c.text, c.word), c.expect, JSON.stringify(c));
  for (const c of V.mask) assert.deepEqual(mask(CHAT, c.text, c.words), c.expect, JSON.stringify(c));
});
test("live signs, own connection and sounds agree", () => {
  for (const c of V.signs) assert.deepEqual(liveSign(CHAT, c.sign, c.author, { onlineBoth: c.o.online_both, reducedMotion: c.o.reduced_motion, teamView: c.o.team_view, senderAllows: c.o.sender_allows }), c.expect, JSON.stringify(c));
  for (const c of V.connection) assert.deepEqual(ownConnection(CHAT, c.online, c.was, c.n), c.expect, JSON.stringify(c));
  for (const c of V.sounds) assert.deepEqual(soundFor(CHAT, c.event, c.s), c.expect, JSON.stringify(c));
});
test("routing agrees: support and a business's own team", () => {
  for (const c of V.route) assert.deepEqual(routeSupport(CHAT, c.conv, V.helpers, c.open_now), c.expect, JSON.stringify(c));
  for (const c of V.team) assert.deepEqual(routeTeam(CHAT, c.conv, c.staff, c.mode, c.turn), c.expect, JSON.stringify(c));
});
test("offline rules, cards, tools, escalation and reply time agree", () => {
  for (const [w, want] of Object.entries(V.offline)) assert.equal(offlineRule(CHAT, w), want, w);
  for (const c of V.cards) assert.equal(cardAction(CHAT, c.kind, c.action, c.online), c.expect, JSON.stringify(c));
  for (const c of V.tools) assert.equal(toolsOk(CHAT, c.choices, c.fields), c.expect, JSON.stringify(c));
  for (const c of V.escalate) assert.equal(escalate(CHAT, c.min, c.setting), c.expect, JSON.stringify(c));
  for (const c of V.reply_time) assert.equal(replyTime(c.xs), c.expect, JSON.stringify(c.xs));
});
