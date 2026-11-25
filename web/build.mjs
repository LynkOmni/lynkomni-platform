// Builds each interface emulator into ONE self-contained, offline HTML file in web/emulators/dist/.
// Run from the repo root:  node web/build.mjs          (writes)
//                          node web/build.mjs --check  (writes nothing; fails if a built file is out of date)
// Steps: compile the TypeScript (tsc), join the modules into one script, add the design tokens, the emulator's CSS and
// the brand, icon and picture data from web/emulators/build_data.py. No network, no outside libraries.
import { execFileSync } from "node:child_process";
import { deflateRawSync } from "node:zlib";
import { createHash } from "node:crypto";
import { mkdirSync, readFileSync, writeFileSync, existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const WEB = dirname(fileURLToPath(import.meta.url));
const ROOT = dirname(WEB);
const OUT = join(WEB, "emulators", "dist");
const DEVICE_MODULES = ["ts/src/brand.js", "ts/src/payments.js", "ts/src/footer.js", "ts/src/pos.js", "ts/src/merchant.js", "ts/src/business.js", "ts/src/agent.js", "ts/src/restaurant.js", "ts/src/emulator.js", "SH=ts/src/usernames.generated.js+ts/src/usernames.js+ts/src/shell.js", "ts/src/parts.generated.js", "ts/src/signin.js", "ts/src/notify.js", "ts/src/assist.js", "ts/src/breadcrumbs.js", "ts/src/devicekit.js", "ts/src/deviceshell.js", "ts/src/interfaces.generated.js", "ts/src/interfaces.js", "ts/src/devicemode.js"];
// every tracked thing is drawn the same way everywhere (owner, 9 November 2026): the engine, its register and the shared look
const TRACK_MODULES = ["ts/src/tracking.js", "ts/src/tracking.generated.js", "ts/src/trackview.js"];
const SHARED_PAGE_MODULES = ["ts/src/shared.generated.js", "ts/src/shared.js", "ts/src/sharedview.js"];   // the shared parts' pages (CONNECT UPDATE 71.3)
// every interface picks its view from the device register (DEVICE, 48.17) and supports touch gestures and arrow navigation
const INTERFACE_MODULES = ["ts/src/interfaces.generated.js", "ts/src/interfaces.js", "ts/src/gestures.js"];
// MASTER UPDATE, section 1: the shared sign-in parts (section 3 puts them on every device too, with ts/src/devicekit.js), the bell and message parts, LynkAssist and breadcrumbs, on their registers
const PARTS_MODULES = ["ts/src/parts.generated.js", "ts/src/signin.js", "ts/src/notify.js", "ts/src/assist.js", "ts/src/breadcrumbs.js"];
// NEW UPDATE 4 (section 1): the shared parts of LynkAttend, LynkQueue and LynkSurvey with the rules they draw from
const PEOPLE_MODULES = ["ts/src/attendance.js", "ts/src/queue.js", "ts/src/peopleparts.js"];
// NEW UPDATE 4 (section 3): the Business app devices also run the people engine (setup, Add a device, door, reception, counter, rating)
const PEOPLE_DEVICE = ["ts/src/attendance.js", "ts/src/queue.js", "ts/src/survey.js", "ts/src/peopleparts.js", "ts/src/afterpay.js", "ts/src/attenddesk.js", "ts/src/queuedesk.js", "ts/src/surveydesk.js", "ts/src/peoplehub.js"];
// the customer display carries only the rating after payment (ts/src/afterpay.js), not the whole people engine
// LynkDScreen, LynkCDisplay and the page on a person's phone carry only the queue engine and its words
const QUEUE_ONLY = ["ts/src/attendance.js", "ts/src/queue.js", "ts/src/peopleparts.js", "ts/src/queuedesk.js"];
/** The screens that show LynkQueue and LynkSurvey on a wall or above a counter (LynkDScreen, LynkCDisplay). */
const SCREENS = [...QUEUE_ONLY, "ts/src/survey.js", "ts/src/surveydesk.js"];
/** The person's phone answering a survey (no app, no account). */
const SURVEY_ONLY = ["ts/src/attendance.js", "ts/src/queue.js", "ts/src/survey.js", "ts/src/peopleparts.js", "ts/src/surveydesk.js"];
const AFTER_PAY = ["ts/src/attendance.js", "ts/src/queue.js", "ts/src/survey.js", "ts/src/peopleparts.js", "ts/src/afterpay.js"];
// build section 3A: the Emulator Panel's rules and register (ts/src/emulators.js), the device side every panel emulator carries (emkit),
// and the panel itself in the Business app (emulatorpanel)
const KIT = ["ts/src/placeholder.js", "ts/src/emulators.generated.js", "ts/src/emulators.js", "ts/src/keytones.js", "ts/src/soundprefs.js", "ts/src/emkit.js"];          // after ts/src/queue.js (the Lynk Code)
const PANEL_DEVICES = ["counter-tablet", "kitchen-screen", "customer-display", "rider-phone", "stock-scanner"];
// BETTING UPDATE (blueprint 86): the LynkBet betting counter on LynkPOS, with the betting rules and register
const BET_MODULES = ["ts/src/betting.generated.js", "ts/src/betting.js"];
const EMULATORS = [
  { id: "pos-terminal", out: "lynkomni-pos-terminal.html", modules: [...DEVICE_MODULES, ...PEOPLE_DEVICE, ...KIT, "ts/src/ads.generated.js", "ts/src/ads.js", "web/emulators/pos-terminal/app.js"] },
  { id: "merchant-phone", out: "lynkomni-merchant-phone.html", modules: [...SHARED_PAGE_MODULES, "ts/src/usernames.generated.js", "ts/src/usernames.js", ...DEVICE_MODULES, ...TRACK_MODULES, "ts/src/reservations.js", "ts/src/drivers.js", "ts/src/drivers.generated.js", ...PEOPLE_DEVICE, ...KIT, "ts/src/emulatorpanel.js", "ts/src/navigation.js", "ts/src/navigation.generated.js", "ts/src/turn.js", "ts/src/appshell.js", "ts/src/chat.js", "ts/src/chat.generated.js", "ts/src/chatview.js", "ts/src/assisttrust.js", "ts/src/assisttrust.generated.js", "ts/src/assistview.js", "ts/src/ads.generated.js", "ts/src/pagekit.js", "ts/src/books.generated.js", "ts/src/books.js", "ts/src/invoices.generated.js", "ts/src/invoices.js", "ts/src/crm.generated.js", "ts/src/crm.js", "ts/src/stats.generated.js", "ts/src/stats.js", "ts/src/enterprise.generated.js", "ts/src/enterprise.js", "ts/src/officeview.js", "ts/src/hr.generated.js", "ts/src/hr.js", "ts/src/project.generated.js", "ts/src/project.js", "ts/src/files.generated.js", "ts/src/files.js", "ts/src/workview.js", "web/emulators/merchant-phone/app.js"] },
  { id: "browser-frame", out: "lynkomni-browser-frame.html", modules: ["ts/src/soundprefs.js", "ts/src/brand.js", "ts/src/usernames.generated.js", "ts/src/usernames.js", "ts/src/payments.js", "ts/src/footer.js", "ts/src/shell.js", ...INTERFACE_MODULES, ...PARTS_MODULES, ...PEOPLE_MODULES, "web/emulators/browser-frame/app.js"],
    extraCss: ["web/shell/shell.css"] },
  { id: "account-site", out: "lynkomni-account-site.html", modules: ["ts/src/soundprefs.js", "ts/src/brand.js", "ts/src/usernames.generated.js", "ts/src/usernames.js", "ts/src/payments.js", "ts/src/footer.js", "ts/src/shell.js", "ts/src/account.js", ...INTERFACE_MODULES, ...TRACK_MODULES, ...PARTS_MODULES, "ts/src/protection.js", ...PEOPLE_MODULES, "ts/src/turn.js", "web/emulators/account-site/app.js"],
    extraCss: ["web/shell/shell.css"] },
  // build section 3: the Business app devices, all on the shared device runtime (ts/src/emulator.js) and words (web/pos)
  // build section 3B: LynkKiosk (LynkAttend's door, LynkQueue's tickets and LynkSurvey's answers on one self-service device)
  { id: "lynk-kiosk", out: "lynkomni-lynk-kiosk.html", modules: [...DEVICE_MODULES, ...PEOPLE_DEVICE, ...KIT, "web/emulators/lynk-kiosk/app.js"], extraCss: ["web/device/device.css"] },
  // build section 3B: LynkQueue's own screens: the main calling screen, the small screen above each counter, and the page on a person's phone
  ...["lynk-dscreen", "lynk-cdisplay"].map((id) => ({ id, out: `lynkomni-${id}.html`, modules: [...DEVICE_MODULES, ...SCREENS, ...KIT, `web/emulators/${id}/app.js`], extraCss: ["web/device/device.css"] })),
  { id: "bet-counter", out: "lynkomni-bet-counter.html", modules: [...DEVICE_MODULES, "ts/src/queue.js", ...KIT, ...BET_MODULES, "web/emulators/bet-counter/app.js"], extraCss: ["web/device/device.css"] },
  { id: "queue-page", out: "lynkomni-queue-page.html", modules: [...DEVICE_MODULES, ...QUEUE_ONLY, "ts/src/turn.js", "web/emulators/queue-page/app.js"], extraCss: ["web/device/device.css"] },
  { id: "files-signing", out: "lynkomni-files-signing.html", modules: [...DEVICE_MODULES, "ts/src/files.generated.js", "ts/src/files.js", "ts/src/queue.js", ...KIT, "web/emulators/files-signing/app.js"], extraCss: ["web/device/device.css"] },   // build section 4B: the LynkFiles signing tablet
  { id: "survey-page", out: "lynkomni-survey-page.html", modules: [...DEVICE_MODULES, ...SURVEY_ONLY, "ts/src/turn.js", "web/emulators/survey-page/app.js"], extraCss: ["web/device/device.css"] },
  ...["counter-tablet", "kitchen-screen", "customer-display", "rider-phone", "stock-scanner", "button-phone", "vcard-card", "mesh-relay", "owner-web", "track-page"]
    .map((id) => ({ id, out: `lynkomni-${id}.html`, modules: [...(id === "button-phone" ? ["ts/src/usernames.generated.js", "ts/src/usernames.js"] : []), ...DEVICE_MODULES, ...(["rider-phone", "track-page", "owner-web"].includes(id) ? TRACK_MODULES : []), ...(id === "owner-web" ? SHARED_PAGE_MODULES : []), ...(id === "button-phone" ? ["ts/src/channels.js", "ts/src/basicphone.js", "ts/src/queue.js", "ts/src/sounds.generated.js", "ts/src/keytones.js", "ts/src/soundprefs.js"] : []), ...(id === "customer-display" ? AFTER_PAY : []), ...(PANEL_DEVICES.includes(id) ? [...(id === "customer-display" ? [] : ["ts/src/queue.js"]), ...KIT] : []), ...(id === "owner-web" ? ["ts/src/navigation.js", "ts/src/navigation.generated.js", "ts/src/appshell.js", "ts/src/pagekit.js", "ts/src/books.generated.js", "ts/src/books.js", "ts/src/invoices.generated.js", "ts/src/invoices.js", "ts/src/crm.generated.js", "ts/src/crm.js", "ts/src/stats.generated.js", "ts/src/stats.js", "ts/src/enterprise.generated.js", "ts/src/enterprise.js", "ts/src/ads.generated.js", "ts/src/ads.js", "ts/src/officeview.js", "ts/src/hr.generated.js", "ts/src/hr.js", "ts/src/project.generated.js", "ts/src/project.js", "ts/src/files.generated.js", "ts/src/files.js", "ts/src/workview.js"] : id === "counter-tablet" ? ["ts/src/navigation.js", "ts/src/navigation.generated.js", "ts/src/turn.js", "ts/src/appshell.js", "ts/src/ads.generated.js", "ts/src/ads.js"] : ["rider-phone", "track-page", "stock-scanner"].includes(id) ? ["ts/src/turn.js"] : []), `web/emulators/${id}/app.js`], extraCss: ["web/device/device.css"] })),
];

// Every Lynk name on every page carries its plain word (catalog/names.v1.json): the names part joins every page before the
// footer and the shells that use it; the pages with the launcher and search also carry the one-line descriptions.
const NAME_INFO = ["browser-frame", "account-site", "owner-web", "merchant-phone"];
// PLACEHOLDER UPDATE 83: pages whose fields take hints carry the small hint part (ts/src/hints.ts) (format hints with the reader's own digits),
// so the part joins every page first (it imports nothing).
const HINTED = ["merchant-phone", "pos-terminal", "counter-tablet", "account-site", "files-signing"];
for (const e of EMULATORS) if (!e.modules.includes("ts/src/hints.js") && (HINTED.includes(e.id) || e.modules.some((m) => m === "ts/src/queuedesk.js" || m === "ts/src/surveydesk.js"))) e.modules.unshift("ts/src/hints.js");
// PLACEHOLDER UPDATE 83: every page waits well (ts/src/placeholder.ts PageWait: first open, skeletons, Updating, busy buttons).
// The shared emulator helpers use it, so the part joins every page first (it imports nothing).
for (const e of EMULATORS) { e.modules = e.modules.filter((m) => m !== "ts/src/placeholder.js"); e.modules.unshift("ts/src/placeholder.js"); }
for (const e of EMULATORS) {
  const at = e.modules.findIndex((m) => m === "ts/src/footer.js" || m.startsWith("SH="));
  // Section 4C point 1: every phone and email field is drawn by ts/src/fields.ts; a page whose screens have such a field carries
  // the part, its checks and the countries' phone rules (before the footer and the shells).
  const appSrc = readFileSync(join(ROOT, "web", "emulators", e.id, "app.ts"), "utf8");
  const fields = appSrc.includes("ts/src/fields.js") ? ["ts/src/phone.generated.js", "ts/src/codefield.js", "ts/src/emailfield.js", "ts/src/phone.js", "ts/src/fields.js"]
    : appSrc.includes("ts/src/emailfield.js") ? ["ts/src/phone.generated.js", "ts/src/emailfield.js"]
    : e.modules.includes("ts/src/surveydesk.js") ? ["ts/src/phone.generated.js", "ts/src/codefield.js"] : [];   // the survey page asks only for a code
  const add = [...fields, "ts/src/names.generated.js", "ts/src/names.js", ...(NAME_INFO.includes(e.id) ? ["ts/src/nameinfo.js"] : [])];
  e.modules.splice(at < 0 ? e.modules.length - 1 : at, 0, ...add);
}

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
const DUPLICATES = new Set();
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
  // joined modules share one scope: two top-level declarations with one name would silently replace each other (a function)
  // or fail at load (a const), so refuse any name declared twice
  const seen = new Map();
  for (const [i, part] of parts.entries()) {
    if (/^const \w+ = \(\(\) => \{/m.test(part.split("\n")[1] ?? "")) continue;          // a namespaced group keeps its names inside
    for (const name of topNames(part)) {
      if (seen.has(name)) DUPLICATES.add(`${name} (${seen.get(name)} and ${mods[i]})`); else seen.set(name, mods[i]);
    }
  }
  return `"use strict";\n(() => {\n${parts.join("\n")}\n})();`;
}
/** Every name a module declares at its top level, including the later names of one statement ("const A = 1, B = 2"):
 *  a scan that skips strings, comments and anything inside brackets, so only the statement's own names are read. */
function topNames(src) {
  const out = [];
  for (const m of src.matchAll(/^(?:async )?(?:function\*? |class )(\w+)/gm)) out.push(m[1]);
  for (const m of src.matchAll(/^(?:const|let) /gm)) {
    let i = m.index + m[0].length, depth = 0, expectName = true;
    while (i < src.length) {
      const ch = src[i];
      if (ch === '"' || ch === "'" || ch === "`") { const q = ch; i++; while (i < src.length && src[i] !== q) { if (src[i] === "\\") i++; i++; } i++; continue; }
      if (ch === "/" && src[i + 1] === "/") { while (i < src.length && src[i] !== "\n") i++; continue; }
      if (ch === "/" && src[i + 1] === "*") { i = src.indexOf("*/", i + 2); if (i < 0) break; i += 2; continue; }
      if ("([{".includes(ch)) depth++;
      else if (")]}".includes(ch)) depth--;
      else if (depth === 0 && ch === ";") break;
      else if (depth === 0 && ch === "\n" && /^\S/.test(src[i + 1] ?? "") && !/^[.?:+\-*/|&=,]/.test(src[i + 1] ?? "")) break;
      else if (depth === 0 && ch === ",") expectName = true;
      else if (expectName && /[A-Za-z_$]/.test(ch)) { const name = /^[A-Za-z_$][\w$]*/.exec(src.slice(i))[0]; out.push(name); i += name.length; expectName = false; continue; }
      else if (expectName && !/\s/.test(ch)) expectName = false;
      i++;
    }
  }
  return out;
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
// a plain loop turns the packed text into bytes about ten times faster than Uint8Array.from with a callback (LynkPOS start-up, 19 November 2026)
const UNPACK = `try { const s = atob(DATA.Z), z = new Uint8Array(s.length); for (let i = 0; i < s.length; i++) z[i] = s.charCodeAt(i); const x = JSON.parse(await new Response(new Blob([z]).stream().pipeThrough(new DecompressionStream("deflate-raw"))).text()); const en = DATA.i18n; Object.assign(DATA, x); DATA.i18n = { ...en, ...x.i18n }; delete DATA.Z; } catch { document.body.textContent = "This browser is too old for this demo. Please open it in a current browser."; return; }`;
const INFLATE = `for (const p of Object.values(DATA.packs)) { p.services = DATA.serviceCatalog.map((s, i) => ({ ...s, state: p.st[i] === "a" ? "available" : "coming_soon" })); p.ready = Object.fromEntries(DATA.methods.map((m, i) => [m, { ok: p.ok[i] === "1", message: DATA.offMessage }])); }`;
const tokens = read(join(ROOT, "design", "generated", "tokens.css"));
// Brand fonts travel inside the file (offline, no font site). Only the Latin files: other scripts use the device font.
const fontCss = read(join(ROOT, "design", "fonts.css")).match(/@font-face\s*\{[^}]*\}/g)
  .filter((b) => /-latin\.woff2/.test(b))
  .map((b) => b.replace(/url\('\/fonts\/([\w-]+\.woff2)'\)/, (_, f) => `url(data:font/woff2;base64,${readFileSync(join(ROOT, "design", "fonts", f)).toString("base64")})`))
  .join("\n")
  // and every script rule of the font register (taller lines for Arabic and Indian scripts, never spacing or capitalising letters
  // that join or ideographs, right to left): they apply whatever font the device uses (owner check, 19 November 2026)
  + "\n" + read(join(ROOT, "design", "fonts.css")).replace(/\/\*[\s\S]*?\*\//g, "").replace(/@font-face\s*\{[^}]*\}/g, "").split("\n").filter((l) => l.trim()).join("\n");
// The page's own tab icon (brand surface "favicon"): the light-theme emblem when the browser is light, the dark-theme emblem when it is dark.
// a small data address: double quotes become single quotes and only the characters an address cannot carry are escaped
// (far smaller than escaping everything, so the two favicons cost little in every file)
const svgUri = (svg) => `data:image/svg+xml,${svg.replace(/\s+(role|aria-label|focusable)="[^"]*"/g, "").replace(/"/g, "'").replace(/\s+/g, " ").replace(/[%#<>{}|\\^`[\]]/g, (c) => encodeURIComponent(c))}`;
const faviconLinks = (f) => `<link rel="icon" type="image/svg+xml" media="(prefers-color-scheme: light)" href="${svgUri(f.light)}">\n<link rel="icon" type="image/svg+xml" media="(prefers-color-scheme: dark)" href="${svgUri(f.dark)}">`;
// Safe page settings (MASTER UPDATE 59, web/pagesafety.v1.json, the same file core/pagesafety.py reads): nothing loads from
// elsewhere and only this page's own script runs, pinned by its SHA-256 hash. The policy goes right after the charset line.
const SAFETY = JSON.parse(read(join(WEB, "pagesafety.v1.json")));
function withPolicy(html) {
  const hashes = [...html.matchAll(/<script\b([^>]*)>([\s\S]*?)<\/script\b[^>]*>/gi)].map((m) => `'sha256-${createHash("sha256").update(m[2], "utf8").digest("base64")}'`).join(" ") || "'none'";
  const csp = Object.entries(SAFETY.directives).map(([k, v]) => `${k} ${v === "HASHES" ? hashes : v}`).join("; ");
  if (!html.includes('<meta charset="utf-8">')) throw new Error("every page starts with <meta charset=\"utf-8\">");
  return html.replace('<meta charset="utf-8">', () => `<meta charset="utf-8">\n<meta http-equiv="Content-Security-Policy" content="${csp}">`);
}
// The font register's script rules sit on the element that carries lang and are inherited. A page's own rules that space out or
// capitalise letters (badges, small headings) would beat inheritance, so each page gets the script rule again for exactly those
// selectors: letters that join and ideographs are never spaced or capitalised anywhere, and the rule stays as fast as the page's
// own rules (owner font check, 19 November 2026; tests/test_emulators.py ScriptRules).
const SCRIPT_RULES = [...read(join(ROOT, "design", "fonts.css")).matchAll(/^((?:\[lang\|="[\w-]+"\](?:, )?)+) (\{[^}]*!important[^}]*\})$/gm)]
  .map((m) => ({ langs: m[1].split(", "), body: m[2] }));
function withScriptCover(html) {
  const css = [...html.matchAll(/<style[^>]*>([\s\S]*?)<\/style>/gi)].map((m) => m[1]).join("\n").replace(/\/\*[\s\S]*?\*\//g, "");
  const sels = new Set();
  for (const m of css.matchAll(/([^{}]+)\{([^{}]*)\}/g)) {
    const decl = m[2], sel = m[1].trim();
    if (sel.startsWith("@") || /^(from|to|[\d.]+%)/.test(sel) || sel.includes("[lang|=")) continue;
    const spaced = /letter-spacing\s*:\s*(?!0\b|0\s*!|normal)[^;]+/.test(decl), caps = /text-transform\s*:\s*(uppercase|capitalize)/.test(decl);
    if (spaced || caps) for (const s of sel.split(",")) if (s.trim()) sels.add(s.trim());
  }
  if (!sels.size) return html;
  const cover = SCRIPT_RULES.map((r) => `:is(${r.langs.join(", ")}) :is(${[...sels].join(", ")}) ${r.body}`).join("\n");
  return html.replace("</style>", () => `/* script cover */\n${cover}\n</style>`);
}
const EARLY_FIT = `(() => { const r = document.getElementById("rig"); const w = r ? Number(r.dataset.width) : 0; if (w) document.documentElement.style.setProperty("--fit", String(Math.min(1, (r.clientWidth - 8) / w))); })();`;
let stale = [];
let GALLERY_DATA = null;   // the Business app's build data: its icons and product names fill the part gallery
for (const e of EMULATORS) {
  const D = JSON.parse(execFileSync("python3", [join(WEB, "emulators", "build_data.py"), e.id], { cwd: ROOT, encoding: "utf8", maxBuffer: 1 << 26 }));
  if (e.id === "merchant-phone") GALLERY_DATA = D;
  const dir = join(WEB, "emulators", e.id);
  // The device drawing is scaled to the window before the first paint, so nothing jumps while the page loads (speed target, INTERFACE UPDATE 73.8)
  let html = read(join(dir, "shell.html")).replace("<script>/*@SCRIPT@*/</script>", () => `<script>${EARLY_FIT}</script>\n<script>/*@SCRIPT@*/</script>`).replace("</head>", () => "<style>html:not([data-ready]) body { visibility: hidden; }</style>\n</head>")
    .replace("/*@TOKENS@*/", () => fontCss + "\n" + tokens)
    .replace("/*@STYLE@*/", () => [...(e.extraCss ?? []), ...(e.modules.includes("ts/src/footer.js") ? ["web/footer/footer.css"] : []), ...(e.modules.includes("ts/src/names.js") ? ["web/shell/names.css"] : []), ...(e.modules.includes("ts/src/codefield.js") || e.modules.includes("ts/src/emailfield.js") ? ["web/shell/fields.css"] : []), ...(e.modules.includes("ts/src/deviceshell.js") ? ["web/device/deviceshell.css"] : []), ...(e.modules.includes("ts/src/devicemode.js") ? ["web/device/devicemode.css"] : []), ...(e.modules.includes("ts/src/trackview.js") ? ["web/tracking/tracking.css"] : []), ...(e.modules.includes("ts/src/notify.js") || e.modules.includes("ts/src/queuedesk.js") || e.modules.includes("ts/src/surveydesk.js") ? ["web/shell/parts.css"] : []), ...(e.modules.includes("ts/src/devicekit.js") ? ["web/device/deviceparts.css"] : []), ...(e.modules.includes("ts/src/placeholder.js") ? ["web/shell/placeholder.css"] : []), ...(e.modules.includes("ts/src/ads.js") ? ["web/shell/ads.css"] : []), ...(e.modules.includes("ts/src/emkit.js") ? ["web/device/emkit.css"] : []), ...(e.modules.includes("ts/src/appshell.js") ? ["web/shell/appshell.css"] : []), ...(e.modules.includes("ts/src/chatview.js") ? ["web/shell/chat.css"] : []), ...(e.modules.includes("ts/src/assistview.js") ? ["web/shell/assist.css"] : []), ...(e.modules.includes("ts/src/pagekit.js") ? ["web/shell/pagekit.css"] : []), ...(e.modules.includes("ts/src/officeview.js") ? ["web/shell/office.css"] : []), ...(e.modules.includes("ts/src/sharedview.js") ? ["web/shell/sharedview.css"] : [])].map((c) => read(join(ROOT, c))).join("\n") + "\n" + read(join(dir, "style.css")))   // the footer's styles travel with the footer module
    .replace("/*@BODYMARK@*/", () => D.brand.body)
    .replace("/*@FAVICON@*/", () => `<span class="fav-l">${D.brand.favicon.light}</span><span class="fav-d">${D.brand.favicon.dark}</span>`)
    .replace("</head>", () => `${faviconLinks(D.brand.favicon)}\n</head>`)
    .replace(/\/\*@I:([a-z0-9-]+)@\*\//g, (_, id) => `<span class="ic" aria-hidden="true">${D.icons[id] ?? (() => { throw new Error(`unknown icon ${id}`); })()}</span>`)
    .replace("/*@SCRIPT@*/", () => `const DATA = ${JSON.stringify(packData(D)).replace(/</g, "\\u003c")};\n(async () => {\n${UNPACK}\n${INFLATE}\n${bundle(["ts/src/inpage.js", ...e.modules])}\ndocument.documentElement.dataset.ready = "1"; window.__readyAt = performance.now();\n})();`);
  html = withScriptCover(html);
  html = withPolicy(html);
  const target = join(OUT, e.out);
  if (process.argv.includes("--check")) {
    if (!existsSync(target) || read(target) !== html) stale.push(e.out);
  } else {
    mkdirSync(OUT, { recursive: true });
    writeFileSync(target, html);
    console.log(`wrote web/emulators/dist/${e.out} (${Math.round(html.length / 1024)} KB)`);
  }
}
// The part gallery of the showcase (INTERFACE UPDATE 73.8): every app-shell and page-template part, drawn by the real parts.
{
  const { galleryHtml } = await import(join(WEB, ".build", "ts", "src", "gallery.js"));
  const { NAV } = await import(join(WEB, ".build", "ts", "src", "navigation.generated.js"));
  const { DEVICES } = await import(join(WEB, ".build", "ts", "src", "interfaces.generated.js"));
  const words = { ...JSON.parse(read(join(WEB, "navigation", "strings.en.json"))), ...JSON.parse(read(join(WEB, "chat", "strings.en.json"))), ...JSON.parse(read(join(WEB, "assist", "strings.en.json"))) };
  const names = Object.fromEntries(GALLERY_DATA.launcher.map((x) => [x.family, x.name]));
  const icons = JSON.parse(execFileSync("python3", ["-c", "import json,sys; sys.path.insert(0,'.'); import brand; print(json.dumps({i: brand.icon_svg(i) for i in sys.argv[1:]}))", ...new Set([...galleryHtml(NAV, DEVICES, words, names).matchAll(/\/\*@I:([a-z0-9-]+)@\*\//g)].map((m) => m[1]))], { cwd: ROOT, encoding: "utf8" }));
  const html = "<!-- GENERATED by web/build.mjs from ts/src/gallery.ts. Do not edit by hand. -->\n" + galleryHtml(NAV, DEVICES, words, names).replace(/\/\*@I:([a-z0-9-]+)@\*\//g, (_, id) => icons[id]) + "\n";
  const target = join(WEB, "showcase", "gallery.generated.html");
  if (process.argv.includes("--check")) { if (!existsSync(target) || read(target) !== html) stale.push("web/showcase/gallery.generated.html"); }
  else { writeFileSync(target, html); console.log("wrote web/showcase/gallery.generated.html"); }
}
if (MISSING.size) { console.error(`imported but not joined (add them to the emulator's modules):\n  ${[...MISSING].join("\n  ")}`); process.exit(1); }
if (DUPLICATES.size) { console.error(`declared twice in one joined scope (rename one):\n  ${[...DUPLICATES].join("\n  ")}`); process.exit(1); }
if (stale.length) { console.error(`out of date (run node web/build.mjs): ${stale.join(", ")}`); process.exit(1); }
if (process.argv.includes("--check")) console.log("emulators are up to date");
