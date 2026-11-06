// Renders the footer model (dist/src/footer.js) into one self-contained preview page. Marks are PLACEHOLDERS: use official brand artwork before launch.
import { readFileSync, writeFileSync } from "node:fs";
import { execFileSync } from "node:child_process";
import { buildFooter, shortFooter } from "../dist/src/footer.js";
// The real logo comes only from the vendored, hash-checked brand module (python brand/). Unsynced or tampered: show the text placeholder.
function vendoredLogo() {
  try {
    const out = execFileSync("python3", ["-c", "import json,brand;print(json.dumps({v:brand.svg_text('logo',v) for v in ('light','dark')}))"], { cwd: "..", encoding: "utf8", stdio: ["ignore", "pipe", "ignore"] });
    return JSON.parse(out);
  } catch { return null; }
}
const LOGO = vendoredLogo();
const pack = (c) => JSON.parse(readFileSync(`../contract/country-packs/${c}.json`, "utf8"));
const esc = (s) => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/"/g, "&quot;");
const svg = (label, body) => `<svg class="mk" viewBox="0 0 60 38" role="img" aria-label="${esc(label)}"><title>${esc(label)}</title>${body}</svg>`;
const MARKS = {
  visa: ["Visa", `<rect width="60" height="38" rx="5" fill="#fff" stroke="#c9cdd6"/><text x="30" y="25" text-anchor="middle" font-family="Arial" font-weight="800" font-style="italic" font-size="16" fill="#1a1f71">VISA</text>`],
  mastercard: ["Mastercard", `<rect width="60" height="38" rx="5" fill="#fff" stroke="#c9cdd6"/><circle cx="24" cy="19" r="9" fill="#eb001b"/><circle cx="36" cy="19" r="9" fill="#f79e1b" fill-opacity=".9"/>`],
  mtn_momo: ["MTN MoMo", `<rect width="60" height="38" rx="5" fill="#ffcc00"/><text x="30" y="24" text-anchor="middle" font-family="Arial" font-weight="800" font-size="13" fill="#111">MoMo</text>`],
  airtel_money: ["Airtel Money", `<rect width="60" height="38" rx="5" fill="#e40000"/><text x="30" y="24" text-anchor="middle" font-family="Arial" font-weight="700" font-size="12" fill="#fff">airtel</text>`],
  mpesa: ["M-Pesa", `<rect width="60" height="38" rx="5" fill="#2ea44f"/><text x="30" y="24" text-anchor="middle" font-family="Arial" font-weight="800" font-size="11" fill="#fff">M-PESA</text>`],
  upi: ["UPI", `<rect width="60" height="38" rx="5" fill="#fff" stroke="#c9cdd6"/><text x="30" y="25" text-anchor="middle" font-family="Arial" font-weight="800" font-size="15" fill="#e8742c">UPI</text>`],
  bank_transfer: ["Bank transfer", `<rect width="60" height="38" rx="5" fill="#eef1f6" stroke="#c9cdd6"/><path d="M14 16 30 8l16 8v2H14zM17 20h4v9h-4zm8 0h4v9h-4zm8 0h4v9h-4zm8 0h4v9h-4zM13 30h34v3H13z" fill="#3b4a66"/>`],
  qr: ["QR payment", `<rect width="60" height="38" rx="5" fill="#fff" stroke="#c9cdd6"/><path d="M18 9h10v10H18zm14 0h10v10H32zM18 23h10v10H18zm14 2h4v4h-4zm6 4h4v4h-4zm-6 4h4v0z" fill="#111"/>`],
  mobile_money: ["Mobile money", `<rect width="60" height="38" rx="5" fill="#eef1f6" stroke="#c9cdd6"/><rect x="22" y="7" width="16" height="24" rx="3" fill="#3b4a66"/><circle cx="30" cy="22" r="5" fill="#ffcc00"/>`],
};
const SOCIAL = { linkedin: "in", x: "X", facebook: "f", instagram: "ig", youtube: "yt", tiktok: "tt", whatsapp: "wa" };
const LANG = { en: "English (EN)", fr: "Français (FR)", sw: "Kiswahili (SW)" };
const NOW = new Date();
function main(code, lang) {
  const p = pack(code), f = buildFooter({ now: NOW, pack: p, lang });
  const cols = f.columns.map((c) => `<nav aria-labelledby="h-${code}-${c.id}"><h3 id="h-${code}-${c.id}">${esc(c.title)}</h3><ul>${c.items.map((i) => `<li><a href="${esc(i.href)}">${esc(i.label)}</a></li>`).join("")}</ul></nav>`).join("");
  const marks = f.payments.marks.map((m) => svg(...MARKS[m])).join('<span class="bar" aria-hidden="true">|</span>');
  return `<footer class="ft" aria-label="LynkOmni"><div class="top"><div class="brand">${LOGO ? `<div class="logo logo-real"><span class="lt">${LOGO.light}</span><span class="dk">${LOGO.dark}</span></div>` : `<div class="logo" aria-label="LynkOmni">Lynk<b>Omni</b></div>`}<p>${esc(f.tagline)}</p>
  <form class="nl" onsubmit="return false"><h3>${esc(f.newsletter.title)}</h3><p>${esc(f.newsletter.text)}</p><label>${esc(f.newsletter.email)}<input type="email" autocomplete="email" required></label>
  <fieldset><legend class="sr">Topics</legend>${f.newsletter.topics.map((t) => `<label class="chk"><input type="checkbox"> ${esc(t)}</label>`).join("")}</fieldset>
  <label class="chk"><input type="checkbox" required> <span>${esc(f.newsletter.consent)} <a href="/legal/privacy">${esc(f.legal.links[1].label)}</a></span></label>
  <button>${esc(f.newsletter.button)}</button><small>${esc(f.newsletter.note)}</small></form></div><div class="cols">${cols}</div></div>
  <div class="mid"><div><h3>${esc(f.newsletter.title === "" ? "" : "")}</h3></div><div class="social" aria-label="Social">${f.social.map((s) => `<a href="/social/${s}" aria-label="${s}" class="so">${SOCIAL[s]}</a>`).join("")}</div>
  <div class="dl">${f.download.map((d) => `<a href="/download/${d.id}" class="btn">${esc(d.label)}</a>`).join("")}</div></div>
  <div class="pay"><span class="pt">${esc(f.payments.title)}</span><div class="marks">${marks}</div></div>
  <div class="bot"><p class="copy">${esc(f.legal.copyright)}</p><div class="legal">${f.legal.links.map((l) => `<a href="${esc(l.href)}">${esc(l.label)}</a>`).join('<span class="bar" aria-hidden="true">|</span>')}</div>
  <div class="sel"><span>${esc(f.region ? "Region: " + f.region.name + " · " + f.region.currency : "")}</span><span>Language: ${LANG[lang]}</span></div></div></footer>`;
}
const tabs = [["RW", "en", "Rwanda · English"], ["KE", "sw", "Kenya · Kiswahili"], ["IN", "en", "India · English"]];
const html = `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover"><title>LynkOmni footer</title><style>
:root{box-sizing:border-box;padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px);--bg:#fff;--fg:#0f172a;--mut:#5b6577;--line:#e3e7ef;--card:#f6f8fb;--acc:#0b7a75;--acc2:#ffffff}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#0b1220;--fg:#e8edf6;--mut:#9aa6bb;--line:#222c40;--card:#111a2c;--acc:#35c6bd;--acc2:#05201e;color-scheme:dark}}
:root[data-theme="dark"]{--bg:#0b1220;--fg:#e8edf6;--mut:#9aa6bb;--line:#222c40;--card:#111a2c;--acc:#35c6bd;--acc2:#05201e;color-scheme:dark}
*{box-sizing:border-box}html{scroll-padding-top:env(safe-area-inset-top,0px)}body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.5 system-ui,-apple-system,Segoe UI,Roboto,sans-serif}
.wrap{max-width:1200px;margin:0 auto;padding:16px}h1{font-size:18px;margin:8px 0}.note{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:10px 12px;color:var(--mut);font-size:13px}
.tabs{display:flex;gap:8px;flex-wrap:wrap;margin:14px 0}.tabs button{border:1px solid var(--line);background:var(--card);color:var(--fg);padding:8px 12px;border-radius:999px;cursor:pointer;font:inherit}.tabs button[aria-selected="true"]{background:var(--acc);color:var(--acc2);border-color:var(--acc)}
.ft{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:28px 22px}.top{display:grid;grid-template-columns:minmax(260px,1fr) 3fr;gap:32px}.cols{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:22px}
h3{font-size:12px;letter-spacing:.08em;text-transform:uppercase;color:var(--mut);margin:0 0 10px}ul{list-style:none;margin:0;padding:0}li{margin:6px 0}a{color:var(--fg);text-decoration:none}a:hover,a:focus-visible{text-decoration:underline;outline:2px solid transparent}
.logo-real svg{display:block;width:160px;height:auto}.logo-real .dk{display:none}@media(prefers-color-scheme:dark){.logo-real .lt{display:none}.logo-real .dk{display:block}}.logo{font-size:24px;font-weight:700;letter-spacing:-.02em}.logo b{color:var(--acc)}.brand>p{color:var(--mut);margin:6px 0 18px}
.nl{border-top:1px solid var(--line);padding-top:14px}.nl p{color:var(--mut);margin:0 0 8px}.nl label{display:block;font-size:13px;margin:8px 0}.nl input[type=email]{display:block;width:100%;margin-top:4px;padding:10px;border:1px solid var(--line);border-radius:8px;background:var(--bg);color:var(--fg);font:inherit}
fieldset{border:0;padding:0;margin:6px 0}.chk{display:flex!important;gap:8px;align-items:flex-start;color:var(--mut)}.chk input{margin-top:3px}.nl button{margin-top:8px;padding:10px 16px;border:0;border-radius:8px;background:var(--acc);color:var(--acc2);font:inherit;font-weight:600;cursor:pointer}.nl small{display:block;margin-top:8px;color:var(--mut)}
.mid{display:flex;justify-content:space-between;align-items:center;gap:16px;flex-wrap:wrap;margin-top:26px;padding-top:18px;border-top:1px solid var(--line)}.social{display:flex;gap:8px}.so{width:34px;height:34px;border-radius:50%;border:1px solid var(--line);display:grid;place-items:center;font-size:12px;font-weight:700;color:var(--fg)}
.dl{display:flex;gap:8px;flex-wrap:wrap}.btn{border:1px solid var(--line);padding:8px 12px;border-radius:8px;font-size:13px}
.pay{margin-top:18px;padding-top:16px;border-top:1px solid var(--line);display:flex;align-items:center;gap:16px;flex-wrap:wrap}.pt{font-size:12px;letter-spacing:.08em;text-transform:uppercase;color:var(--mut)}.marks{display:flex;align-items:center;gap:10px;flex-wrap:wrap}.mk{width:60px;height:38px}.bar{color:var(--line);font-size:22px;line-height:1}
.bot{margin-top:18px;padding-top:16px;border-top:1px solid var(--line);display:grid;gap:10px}.copy{margin:0;color:var(--mut);font-size:13px}.legal{display:flex;gap:10px;flex-wrap:wrap;font-size:13px;align-items:center}.sel{display:flex;gap:16px;flex-wrap:wrap;font-size:13px;color:var(--mut)}
.short{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px 14px;color:var(--mut);font-size:12.5px}.sr{position:absolute;left:-9999px}
@media (max-width:820px){.top{grid-template-columns:1fr}.mk{width:48px;height:30px}.ft{padding:22px 16px}}[hidden]{display:none!important}
</style></head><body><div class="wrap"><h1>LynkOmni footer preview</h1><div class="note">Built from one model: menus use ecosystem names, the copyright line is fixed text, the year follows the viewer's time zone, and language, region and payment marks follow the country pack. Brand marks and social icons are placeholders: replace with official artwork before launch.</div>
<div class="tabs" role="tablist">${tabs.map((t, i) => `<button role="tab" aria-selected="${i === 0}" data-t="${i}">${t[2]}</button>`).join("")}<button role="tab" aria-selected="false" data-t="s">Short footer</button></div>
${tabs.map((t, i) => `<section data-p="${i}" ${i ? "hidden" : ""}>${main(t[0], t[1])}</section>`).join("")}
<section data-p="s" hidden><div class="short">${esc(shortFooter(NOW, "Africa/Kigali"))}</div><p class="note">The short footer is used in live chat and other in-app places. It is fixed text; only the year changes.</p></section></div>
<script>document.querySelectorAll('[data-t]').forEach(b=>b.addEventListener('click',()=>{document.querySelectorAll('[data-t]').forEach(x=>x.setAttribute('aria-selected',x===b));document.querySelectorAll('[data-p]').forEach(p=>p.hidden=p.dataset.p!==b.dataset.t)}))</script></body></html>`;
writeFileSync("/mnt/user-data/outputs/lynkomni-footer-preview.html", html);
console.log(html.length);
