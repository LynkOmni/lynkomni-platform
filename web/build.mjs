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
const EMULATORS = [{ id: "pos-terminal", out: "lynkomni-pos-terminal.html", modules: ["ts/src/pos.js", "web/emulators/pos-terminal/app.js"] }];

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

const data = execFileSync("python3", [join(WEB, "emulators", "build_data.py")], { cwd: ROOT, encoding: "utf8", maxBuffer: 1 << 26 });
const D = JSON.parse(data);
const tokens = read(join(ROOT, "design", "generated", "tokens.css"));
let stale = [];
for (const e of EMULATORS) {
  const dir = join(WEB, "emulators", e.id);
  let html = read(join(dir, "shell.html"))
    .replace("/*@TOKENS@*/", () => tokens)
    .replace("/*@STYLE@*/", () => read(join(dir, "style.css")))
    .replace("/*@BODYMARK@*/", () => D.brand.body)
    .replace(/\/\*@I:([a-z0-9-]+)@\*\//g, (_, id) => `<span class="ic" aria-hidden="true">${D.icons[id] ?? (() => { throw new Error(`unknown icon ${id}`); })()}</span>`)
    .replace("/*@SCRIPT@*/", () => `const DATA = ${JSON.stringify(D).replace(/</g, "\\u003c")};\n${bundle(e.modules)}`);
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
