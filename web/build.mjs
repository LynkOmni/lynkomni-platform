// Builds each interface emulator into ONE self-contained, offline HTML file in web/emulators/dist/.
// Run from the repo root:  node web/build.mjs          (writes)
//                          node web/build.mjs --check  (writes nothing; fails if a built file is out of date)
// Steps: compile the TypeScript (tsc), join the modules into one script, add the design tokens, the emulator's CSS and
// the brand, icon and picture data from web/emulators/build_data.py. No network, no outside libraries.
import { execFileSync } from "node:child_process";
import { mkdirSync, readFileSync, writeFileSync, existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const WEB = dirname(fileURLToPath(import.meta.url));
const ROOT = dirname(WEB);
const OUT = join(WEB, "emulators", "dist");
const EMULATORS = [
  { id: "pos-terminal", out: "lynkomni-pos-terminal.html", modules: ["ts/src/pos.js", "web/emulators/pos-terminal/app.js"] },
  { id: "merchant-phone", out: "lynkomni-merchant-phone.html", modules: ["ts/src/pos.js", "ts/src/merchant.js", "web/emulators/merchant-phone/app.js"] },
  { id: "browser-frame", out: "lynkomni-browser-frame.html", modules: ["ts/src/brand.js", "ts/src/usernames.generated.js", "ts/src/usernames.js", "ts/src/shell.js", "web/emulators/browser-frame/app.js"],
    extraCss: ["web/shell/shell.css"] },
  { id: "account-site", out: "lynkomni-account-site.html", modules: ["ts/src/brand.js", "ts/src/usernames.generated.js", "ts/src/usernames.js", "ts/src/shell.js", "ts/src/account.js", "web/emulators/account-site/app.js"],
    extraCss: ["web/shell/shell.css"] },
];

const read = (p) => readFileSync(p, "utf8");
const tsc = process.env.TSC || "tsc";
execFileSync(tsc, ["-p", join(WEB, "tsconfig.json")], { stdio: "inherit" });

// Join ES modules into one script: drop import lines and the export keyword. Modules are listed in dependency order.
function bundle(mods) {
  const parts = mods.map((m) => {
    const js = read(join(WEB, ".build", m));
    return `// ---- ${m}\n` + js.replace(/^import[^;]*;\s*$/gm, "").replace(/^export \{\s*\};?\s*$/gm, "").replace(/^export (?=(const|function|class|let|async))/gm, "");
  });
  return `"use strict";\n(() => {\n${parts.join("\n")}\n})();`;
}

// Country packs travel compact (build_data.py): inflate each pack's service states and payment readiness before the app starts.
const INFLATE = `for (const p of Object.values(DATA.packs)) { p.services = DATA.serviceCatalog.map((s, i) => ({ ...s, state: p.st[i] === "a" ? "available" : "coming_soon" })); p.ready = Object.fromEntries(DATA.methods.map((m, i) => [m, { ok: p.ok[i] === "1", message: DATA.offMessage }])); }`;
const tokens = read(join(ROOT, "design", "generated", "tokens.css"));
// Brand fonts travel inside the file (offline, no font site). Only the Latin files: other scripts use the device font.
const fontCss = read(join(ROOT, "design", "fonts.css")).match(/@font-face\s*\{[^}]*\}/g)
  .filter((b) => /-latin\.woff2/.test(b))
  .map((b) => b.replace(/url\('\/fonts\/([\w-]+\.woff2)'\)/, (_, f) => `url(data:font/woff2;base64,${readFileSync(join(ROOT, "design", "fonts", f)).toString("base64")})`))
  .join("\n");
let stale = [];
for (const e of EMULATORS) {
  const D = JSON.parse(execFileSync("python3", [join(WEB, "emulators", "build_data.py"), e.id], { cwd: ROOT, encoding: "utf8", maxBuffer: 1 << 26 }));
  const dir = join(WEB, "emulators", e.id);
  let html = read(join(dir, "shell.html"))
    .replace("/*@TOKENS@*/", () => fontCss + "\n" + tokens)
    .replace("/*@STYLE@*/", () => (e.extraCss ?? []).map((c) => read(join(ROOT, c))).join("\n") + "\n" + read(join(dir, "style.css")))
    .replace("/*@BODYMARK@*/", () => D.brand.body)
    .replace(/\/\*@I:([a-z0-9-]+)@\*\//g, (_, id) => `<span class="ic" aria-hidden="true">${D.icons[id] ?? (() => { throw new Error(`unknown icon ${id}`); })()}</span>`)
    .replace("/*@SCRIPT@*/", () => `const DATA = ${JSON.stringify(D).replace(/</g, "\\u003c")};\n${INFLATE}\n${bundle(e.modules)}`);
  const target = join(OUT, e.out);
  if (process.argv.includes("--check")) {
    if (!existsSync(target) || read(target) !== html) stale.push(e.out);
  } else {
    mkdirSync(OUT, { recursive: true });
    writeFileSync(target, html);
    console.log(`wrote web/emulators/dist/${e.out} (${Math.round(html.length / 1024)} KB)`);
  }
}
if (stale.length) { console.error(`out of date (run node web/build.mjs): ${stale.join(", ")}`); process.exit(1); }
if (process.argv.includes("--check")) console.log("emulators are up to date");
