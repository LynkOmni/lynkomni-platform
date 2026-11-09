// Builds each interface emulator into ONE self-contained, offline HTML file in web/emulators/dist/.
// Run from the repo root:  node web/build.mjs          (writes)
//                          node web/build.mjs --check  (writes nothing; fails if a built file is out of date)
// Steps: compile the TypeScript (tsc), join the modules into one script, add the design tokens, the emulator's CSS and
// the brand, icon and picture data from web/emulators/build_data.py. No network, no outside libraries.
import { execFileSync } from "node:child_process";
import { deflateRawSync } from "node:zlib";
import { mkdirSync, readFileSync, writeFileSync, existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const WEB = dirname(fileURLToPath(import.meta.url));
const ROOT = dirname(WEB);
const OUT = join(WEB, "emulators", "dist");
const DEVICE_MODULES = ["ts/src/brand.js", "ts/src/payments.js", "ts/src/footer.js", "ts/src/pos.js", "ts/src/merchant.js", "ts/src/business.js", "ts/src/agent.js", "ts/src/restaurant.js", "ts/src/emulator.js", "SH=ts/src/usernames.generated.js+ts/src/usernames.js+ts/src/shell.js", "ts/src/deviceshell.js"];
// every tracked thing is drawn the same way everywhere (owner, 9 November 2026): the engine, its register and the shared look
const TRACK_MODULES = ["ts/src/tracking.js", "ts/src/tracking.generated.js", "ts/src/trackview.js"];
// every interface picks its view from the device register (DEVICE, 48.17) and supports touch gestures and arrow navigation
const INTERFACE_MODULES = ["ts/src/interfaces.generated.js", "ts/src/interfaces.js", "ts/src/gestures.js"];
const EMULATORS = [
  { id: "pos-terminal", out: "lynkomni-pos-terminal.html", modules: [...DEVICE_MODULES, "web/emulators/pos-terminal/app.js"] },
  { id: "merchant-phone", out: "lynkomni-merchant-phone.html", modules: ["ts/src/usernames.generated.js", "ts/src/usernames.js", ...DEVICE_MODULES, ...TRACK_MODULES, "web/emulators/merchant-phone/app.js"] },
  { id: "browser-frame", out: "lynkomni-browser-frame.html", modules: ["ts/src/brand.js", "ts/src/usernames.generated.js", "ts/src/usernames.js", "ts/src/payments.js", "ts/src/footer.js", "ts/src/shell.js", ...INTERFACE_MODULES, "web/emulators/browser-frame/app.js"],
    extraCss: ["web/shell/shell.css"] },
  { id: "account-site", out: "lynkomni-account-site.html", modules: ["ts/src/brand.js", "ts/src/usernames.generated.js", "ts/src/usernames.js", "ts/src/payments.js", "ts/src/footer.js", "ts/src/shell.js", "ts/src/account.js", ...TRACK_MODULES, "web/emulators/account-site/app.js"],
    extraCss: ["web/shell/shell.css"] },
  // build section 3: the Business app devices, all on the shared device runtime (ts/src/emulator.js) and words (web/pos)
  ...["counter-tablet", "kitchen-screen", "customer-display", "rider-phone", "stock-scanner", "button-phone", "vcard-card", "mesh-relay", "owner-web", "track-page"]
    .map((id) => ({ id, out: `lynkomni-${id}.html`, modules: [...DEVICE_MODULES, ...(["rider-phone", "track-page"].includes(id) ? TRACK_MODULES : []), `web/emulators/${id}/app.js`], extraCss: ["web/device/device.css"] })),
];

const read = (p) => readFileSync(p, "utf8");
const tsc = process.env.TSC || "tsc";
execFileSync(tsc, ["-p", join(WEB, "tsconfig.json")], { stdio: "inherit" });

// Comments are for people reading the source, not for phones downloading the file: whole-line // comments and /** ... */
// blocks that start a line are dropped (never inside code: a line that starts a comment holds no code, and TypeScript output
// keeps strings on their own lines). Trailing comments after code stay, which is always safe.
function stripComments(js) {
  return js.replace(/^[ \t]*\/\*[\s\S]*?\*\/[ \t]*\n/gm, "").replace(/^[ \t]*\/\/.*\n/gm, "");
}
// Join ES modules into one script: drop import lines and the export keyword. Modules are listed in dependency order.
// A module listed as "NS=path" is joined in its own scope and reached through that name (import * as NS from "path"), so its
// names never clash with the device modules' own (ts/src/shell.ts and ts/src/emulator.ts both have esc, Link and state).
const MISSING = new Set();   // modules imported but not joined, reported together after every emulator is bundled
function bundle(mods) {
  const flat = mods.map((x) => (x.includes("=") ? x.split("=")[1].split("+").pop() : x));   // what the joined modules can reach (a group's files stay inside the group)
  const parts = mods.map((spec) => {
    const [ns, group] = spec.includes("=") ? spec.split("=") : [null, spec];
    if (ns && group.includes("+")) {           // "NS=a.js+b.js": a module with its own helpers, joined together in one scope
      const files = group.split("+"), last = files[files.length - 1];
      const inner = bundle.part(files, [...flat, ...files]);
      const names = [...read(join(WEB, ".build", last)).matchAll(/^export (?:const|function|class|let|async function) (\w+)/gm)].map((x) => x[1]);
      return `// ---- ${group} (as ${ns})\nconst ${ns} = (() => {\n${inner}\nreturn { ${names.join(", ")} };\n})();`;
    }
    const m = group;
    const js = read(join(WEB, ".build", m));
    // joining drops import lines, so a renamed import (import { A as B }) would leave B undefined at run time: refuse it here
    const renamed = [...js.matchAll(/^import\s*\{([^}]*)\}/gm)].map((x) => x[1]).join(",").split(",").map((x) => x.trim()).filter((x) => /\sas\s/.test(x) && !x.startsWith("type "));
    if (renamed.length) throw new Error(`${m}: renamed imports are not joined (${renamed.join(", ")}); import the name as it is exported`);
    // every module a file imports (values, not types) must be joined too, or its names are undefined at run time: refuse a missing one
    const listed = new Set(flat);
    for (const [, what, from] of js.matchAll(/^import\s+(type\s+)?[^;]*?from\s+"([^"]+)";/gm).map((x) => [x[0], x[1], x[2]])) {
      if (what) continue;
      const target = join(dirname(m), from).replace(/\\/g, "/");
      if (!listed.has(target)) MISSING.add(`${m} imports ${target}`);
    }
    const body = stripComments(js).replace(/^import[^;]*;\s*$/gm, "").replace(/^export \{\s*\};?\s*$/gm, "").replace(/^export (?=(const|function|class|let|async))/gm, "");
    if (!ns) return `// ---- ${m}\n` + body;
    const names = [...js.matchAll(/^export (?:const|function|class|let|async function) (\w+)/gm)].map((x) => x[1]);
    return `// ---- ${m} (as ${ns})\nconst ${ns} = (() => {\n${body}\nreturn { ${names.join(", ")} };\n})();`;
  });
  return `"use strict";\n(() => {\n${parts.join("\n")}\n})();`;
}
// The plain bodies of a group of modules (for "NS=a.js+b.js"), checked like any other module.
bundle.part = (files, flat) => files.map((m) => {
  const js = read(join(WEB, ".build", m));
  for (const [, what, from] of js.matchAll(/^import\s+(type\s+)?[^;]*?from\s+"([^"]+)";/gm).map((x) => [x[0], x[1], x[2]])) {
    if (!what && !flat.includes(join(dirname(m), from).replace(/\\/g, "/"))) MISSING.add(`${m} imports ${join(dirname(m), from)}`);
  }
  return `// ---- ${m}\n` + stripComments(js).replace(/^import[^;]*;\s*$/gm, "").replace(/^export \{\s*\};?\s*$/gm, "").replace(/^export (?=(const|function|class|let|async))/gm, "");
}).join("\n");

// Country packs travel compact (build_data.py): inflate each pack's service states and payment readiness before the app starts.
// The data travels compressed (owner speed budget): only the English words stay plain, so the checks in tests/test_emulators.py
// can read them and the file stays small. Everything else (other languages, country packs, pictures, brand) is
// deflate-compressed, about a quarter of its size, and unpacked by the browser's own DecompressionStream before the app
// starts. A real app downloads one language and one country at a time; this demo file carries them all.
function packData(D) {
  const { i18n = {}, ...rest } = D;
  const { en, ...langs } = i18n;
  const Z = deflateRawSync(Buffer.from(JSON.stringify({ ...rest, i18n: langs })), { level: 9 }).toString("base64");
  return { i18n: en ? { en } : {}, Z };
}
const UNPACK = `try { const z = Uint8Array.from(atob(DATA.Z), (c) => c.charCodeAt(0)); const x = JSON.parse(await new Response(new Blob([z]).stream().pipeThrough(new DecompressionStream("deflate-raw"))).text()); const en = DATA.i18n; Object.assign(DATA, x); DATA.i18n = { ...en, ...x.i18n }; delete DATA.Z; } catch { document.body.textContent = "This browser is too old for this demo. Please open it in a current browser."; return; }`;
const INFLATE = `for (const p of Object.values(DATA.packs)) { p.services = DATA.serviceCatalog.map((s, i) => ({ ...s, state: p.st[i] === "a" ? "available" : "coming_soon" })); p.ready = Object.fromEntries(DATA.methods.map((m, i) => [m, { ok: p.ok[i] === "1", message: DATA.offMessage }])); }`;
const tokens = read(join(ROOT, "design", "generated", "tokens.css"));
// Brand fonts travel inside the file (offline, no font site). Only the Latin files: other scripts use the device font.
const fontCss = read(join(ROOT, "design", "fonts.css")).match(/@font-face\s*\{[^}]*\}/g)
  .filter((b) => /-latin\.woff2/.test(b))
  .map((b) => b.replace(/url\('\/fonts\/([\w-]+\.woff2)'\)/, (_, f) => `url(data:font/woff2;base64,${readFileSync(join(ROOT, "design", "fonts", f)).toString("base64")})`))
  .join("\n");
// The page's own tab icon (brand surface "favicon"): the light-theme emblem when the browser is light, the dark-theme emblem when it is dark.
// a small data address: double quotes become single quotes and only the characters an address cannot carry are escaped
// (far smaller than escaping everything, so the two favicons cost little in every file)
const svgUri = (svg) => `data:image/svg+xml,${svg.replace(/\s+(role|aria-label|focusable)="[^"]*"/g, "").replace(/"/g, "'").replace(/\s+/g, " ").replace(/[%#<>{}|\\^`[\]]/g, (c) => encodeURIComponent(c))}`;
const faviconLinks = (f) => `<link rel="icon" type="image/svg+xml" media="(prefers-color-scheme: light)" href="${svgUri(f.light)}">\n<link rel="icon" type="image/svg+xml" media="(prefers-color-scheme: dark)" href="${svgUri(f.dark)}">`;
let stale = [];
for (const e of EMULATORS) {
  const D = JSON.parse(execFileSync("python3", [join(WEB, "emulators", "build_data.py"), e.id], { cwd: ROOT, encoding: "utf8", maxBuffer: 1 << 26 }));
  const dir = join(WEB, "emulators", e.id);
  let html = read(join(dir, "shell.html"))
    .replace("/*@TOKENS@*/", () => fontCss + "\n" + tokens)
    .replace("/*@STYLE@*/", () => [...(e.extraCss ?? []), ...(e.modules.includes("ts/src/footer.js") ? ["web/footer/footer.css"] : []), ...(e.modules.includes("ts/src/deviceshell.js") ? ["web/device/deviceshell.css"] : []), ...(e.modules.includes("ts/src/trackview.js") ? ["web/tracking/tracking.css"] : [])].map((c) => read(join(ROOT, c))).join("\n") + "\n" + read(join(dir, "style.css")))   // the footer's styles travel with the footer module
    .replace("/*@BODYMARK@*/", () => D.brand.body)
    .replace("/*@FAVICON@*/", () => `<span class="fav-l">${D.brand.favicon.light}</span><span class="fav-d">${D.brand.favicon.dark}</span>`)
    .replace("</head>", () => `${faviconLinks(D.brand.favicon)}\n</head>`)
    .replace(/\/\*@I:([a-z0-9-]+)@\*\//g, (_, id) => `<span class="ic" aria-hidden="true">${D.icons[id] ?? (() => { throw new Error(`unknown icon ${id}`); })()}</span>`)
    .replace("/*@SCRIPT@*/", () => `const DATA = ${JSON.stringify(packData(D)).replace(/</g, "\\u003c")};\n(async () => {\n${UNPACK}\n${INFLATE}\n${bundle(e.modules)}\ndocument.documentElement.dataset.ready = "1"; window.__readyAt = performance.now();\n})();`);
  const target = join(OUT, e.out);
  if (process.argv.includes("--check")) {
    if (!existsSync(target) || read(target) !== html) stale.push(e.out);
  } else {
    mkdirSync(OUT, { recursive: true });
    writeFileSync(target, html);
    console.log(`wrote web/emulators/dist/${e.out} (${Math.round(html.length / 1024)} KB)`);
  }
}
if (MISSING.size) { console.error(`imported but not joined (add them to the emulator's modules):\n  ${[...MISSING].join("\n  ")}`); process.exit(1); }
if (stale.length) { console.error(`out of date (run node web/build.mjs): ${stale.join(", ")}`); process.exit(1); }
if (process.argv.includes("--check")) console.log("emulators are up to date");
