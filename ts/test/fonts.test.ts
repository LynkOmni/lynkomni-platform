import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { ALL_FONT_FILES, LANGUAGES, baseLanguage, direction, fontFilesFor, rootAttributes } from "../src/fonts.js";

const CSS = readFileSync("../design/fonts.css", "utf8");

test("right-to-left languages get dir=rtl, others ltr", () => {
  for (const l of ["ar", "ar-AE", "fa", "ur", "ps", "ckb", "sd", "ug", "he", "yi"]) assert.equal(direction(l), "rtl", l);
  for (const l of ["en", "fr-RW", "sw", "rw", "hi", "es-US", "xx"]) assert.equal(direction(l), "ltr", l);
  assert.deepEqual(rootAttributes("ar-AE"), { lang: "ar-AE", dir: "rtl" });
  assert.equal(baseLanguage("EN_us"), "en");
  assert.equal(baseLanguage("zz"), null);
});

test("offline font files: Latin always, plus each language's script", () => {
  const en = fontFilesFor(["en"]);
  assert.deepEqual([...en].sort(), ["inter-latin.woff2", "montserrat-latin.woff2"].concat(en.filter((f) => f.includes("latin-ext"))).sort());
  const ar = fontFilesFor(["ar-AE", "en"]);
  assert.ok(ar.includes("noto-sans-arabic-arabic.woff2") && ar.includes("noto-kufi-arabic-arabic.woff2") && ar.includes("inter-latin.woff2"));
  assert.ok(fontFilesFor(["hi"]).includes("noto-sans-devanagari-devanagari.woff2"));
  assert.ok(fontFilesFor(["he"]).includes("noto-sans-hebrew-hebrew.woff2"));
  assert.ok(fontFilesFor(["bn"]).includes("noto-sans-bengali-bengali.woff2"));
  assert.ok(fontFilesFor(["am"]).includes("noto-sans-ethiopic-ethiopic.woff2"));
  assert.ok(fontFilesFor(["yo"]).includes("inter-vietnamese.woff2"), "Yoruba dot-below vowels live in the Vietnamese files");
});

test("every file the apps may ask for is declared in fonts.css", () => {
  for (const f of ALL_FONT_FILES) assert.ok(CSS.includes(`/fonts/${f}`), f);
  assert.ok(Object.keys(LANGUAGES).length >= 15);
});
