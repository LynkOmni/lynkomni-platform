import { test } from "node:test";
import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { chatDigest, threadHtml, inboxRowHtml, prepareSend, signHtml, detailsHtml, muteHtml, chatAboutHtml } from "../src/chatview.js";
import type { ChatLook, ThreadView } from "../src/chatview.js";
import { CHAT } from "../src/chat.generated.js";

const words: Record<string, string> = { ch_code_words: "PIN, password, code", ch_sign_typing: "typing…", ch_assist_label: "LynkAssist (assistant)" };
const t = (k: string, v?: Record<string, string | number>): string => (words[k] ?? k) + (v && Object.keys(v).length ? JSON.stringify(v) : "");
const look = (reducedMotion = false): ChatLook => ({ t, icon: (id) => `<i data-ic="${id}"></i>`, chip: (s) => `<span class="chip st-${s}">${s}</span>`, clock: () => "10:00", reducedMotion,
  card: (k, l) => `<span data-card="${k}">${l}</span>` });
const has = (html: string, re: RegExp, m?: string): void => assert.ok(re.test(html), m ?? String(re));
const hasNot = (html: string, re: RegExp, m?: string): void => assert.ok(!re.test(html), m ?? `not ${String(re)}`);
const view = (o: Partial<ThreadView> = {}): ThreadView => ({ id: "c1", kind: "support", title: "Support", side: "internal", online: true, draft: "", draftHint: "Is it still available?", msgs: [], ...o });

test("the fingerprint is sha256 of the text, the same as the cloud's", () => {
  for (const s of ["", "abc", "Muraho! Ndashaka amavuta 2.", "密码是••••", "x".repeat(1000)]) assert.equal(chatDigest(s), createHash("sha256").update(s).digest("hex"), s.slice(0, 20));
});
test("a draft is masked before it is queued, with the warning", () => {
  const r = prepareSend(CHAT, t, "  card 4111 1111 1111 1111 and PIN 4821 ");
  assert.equal(r.text, "card •••• 1111 and PIN ••••"); assert.deepEqual(r.found, ["card", "code"]);
  const html = threadHtml(CHAT, look(), view({ warning: r.found }));
  has(html, /role="alert"/); has(html, /ch_warn_never_ask/); has(html, /ch:sendmasked/);
});
test("LynkAssist is always named, its answer has a stage and Stop, and a person is one tap away", () => {
  const html = threadHtml(CHAT, look(), view({ assistFirst: true, msgs: [{ id: "m1", author: "assistant", out: false, text: "Let me check", at: 0, state: "accepted", stream: { stage: "assist_checking" } }] }));
  has(html, /LynkAssist \(assistant\)/); has(html, /ch_sign_assist_checking/); has(html, /ch:stop:m1/); has(html, /ch:person/);
  const done = threadHtml(CHAT, look(), view({ msgs: [{ id: "m1", author: "assistant", out: false, text: "Done", at: 0, state: "accepted", stream: { stage: "assist_writing", stopped: true } }] }));
  has(done, /ch_stopped/); hasNot(done, /ch:stop:m1/);
});
test("live signs carry words, are still when motion is off and need both sides online", () => {
  const v = { sign: { sign: "typing", author: "customer" }, online: true };
  has(signHtml(CHAT, look(), v), /data-motion="dots".*typing…/s);
  has(signHtml(CHAT, look(true), v), /data-motion="none"/);
  assert.equal(signHtml(CHAT, look(), { ...v, online: false }), "");
  assert.equal(signHtml(CHAT, look(), { sign: { sign: "staff_replying", author: "business" }, online: true }), "", "team only");
  has(signHtml(CHAT, look(), { sign: { sign: "staff_replying", author: "business", vars: { first_name: "Ama" } }, online: true, teamView: true }), /Ama/);
});
test("a person who turned 'seen' off stops at accepted; the five states only", () => {
  const m = { id: "m1", author: "business", out: true, text: "Hi", at: 0, state: "confirmed" as const };
  has(threadHtml(CHAT, look(), view({ msgs: [m], reader: "customer", readerShowsSeen: false })), /st-accepted/);
  has(threadHtml(CHAT, look(), view({ msgs: [m], reader: "customer" })), /st-confirmed/);
  const failed = threadHtml(CHAT, look(), view({ msgs: [{ ...m, state: "failed" }] }));
  has(failed, /ch:retry:m1/);
});
test("choices, small forms, upload progress, details, mute and Chat about this", () => {
  const html = threadHtml(CHAT, look(), view({ msgs: [
    { id: "m1", author: "assistant", out: false, text: "Pick", at: 0, state: "accepted", choices: [1, 2, 3, 4, 5, 6, 7].map((i) => ({ id: `c${i}`, label: `C${i}` })) },
    { id: "m2", author: "assistant", out: false, text: "Order?", at: 0, state: "accepted", form: [{ id: "f1", kind: "short_text", label: "Order number" }] },
    { id: "m3", author: "business", out: true, text: "", at: 0, state: "queued", upload: { kind: "photo", pct: 40 } }], details: "m3" }));
  assert.equal((html.match(/ch:choice:m1:/g) ?? []).length, CHAT.tools.choices.max, "at most six choices");
  has(html, /<label for="chf-m2-f1"><span>Order number<\/span>/); has(html, /role="progressbar"[^>]*aria-valuenow="40"/); has(html, /ch:pause:m3/);
  has(html, /role="dialog"/);
  has(detailsHtml(CHAT, look(), { id: "x", author: "business", out: true, text: "", at: 0, state: "sent", times: { written: 1, sent: 2 } }), /ch_d_written.*ch_d_sent/s);
  has(muteHtml(CHAT, look(), "day"), /ch:mute:day" aria-pressed="true"/);
  has(chatAboutHtml(look(), "invoice", "LOINV-1"), /chatabout:invoice:LOINV-1/);
  has(threadHtml(CHAT, look(), view()), /<label class="ch-label" for="chIn">ch_write<\/label>.*placeholder="Is it still available\?"/s, "a visible label and an example as the hint");
});
test("the inbox row shows the live sign instead of the last message, and the Storefront side in words", () => {
  const row = inboxRowHtml(CHAT, look(), { id: "c1", name: "Aline", last: "Hello", at: 0, unread: 2, side: "external", sign: { sign: "typing", author: "customer" } }, { online: true });
  has(row, /typing…/); hasNot(row, /Hello/); has(row, /ch_side_word/); has(row, /pill ok">2/);
  has(inboxRowHtml(CHAT, look(), { id: "c1", name: "Aline", last: "Hello", at: 0, unread: 0, sign: { sign: "typing", author: "customer" } }, { online: false }), /Hello/);
});
