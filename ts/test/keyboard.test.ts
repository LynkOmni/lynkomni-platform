import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { ethiopic, hangul, kbKindOf, kbLayout, romaji, romajiDone } from "../src/keyboard.js";
import { KEYBOARDS } from "../src/keyboards.generated.js";

const root = new URL("../../..", import.meta.url).pathname;
const V = JSON.parse(readFileSync(`${root}/contract/vectors/keyboards.v1.json`, "utf8"));

test("Korean letters join into syllables as core/keyboards.py does", () => {
  for (const c of V.hangul) { let out = ""; for (const j of [...c.keys]) out = hangul(out, j); assert.equal(out, c.text, c.keys); }
});
test("Japanese romaji turns into kana as core/keyboards.py does", () => {
  for (const c of V.romaji) { let out = ""; for (const ch of c.keys) out = romaji(out + ch); assert.equal(romajiDone(out), c.text, c.keys); }
});
test("an Amharic consonant takes the vowel form of the key after it", () => {
  for (const c of V.ethiopic) assert.equal(ethiopic(c.text, c.order), c.out);
});
test("each typing field gets its own keyboard: letters, email, number or phone", () => {
  for (const c of V.kind) assert.equal(kbKindOf(c.type, c.mode), c.kind, `${c.type} ${c.mode}`);
});
test("every one of the 38 languages has its keyboard", () => {
  for (const lang of Object.keys(KEYBOARDS.languages)) assert.ok(kbLayout(lang).length >= 3, lang);
  assert.equal(Object.keys(KEYBOARDS.languages).length, 38);
});
