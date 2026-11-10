import { paymentOptions } from "./payments.js";
/** LynkOmni footer: one model for every site and app. Menus use ecosystem names, copyright is fixed text, the year follows the viewer's
 *  time zone, language and payment methods follow the country pack. Translations are DRAFTS pending native-speaker review. */
export interface Pack { code: string; name: string; currency: string; tz: string; languages: string[]; providers: string[]; card_networks: string[]; wallets: string[] }
export interface Item { id: string; label: string; href: string; brand?: boolean; plain?: string }
/** `span` is how many grid tracks the column takes: a list longer than PER_COLUMN links flows into more sub-columns, so no column
 *  runs much taller than the others and no space is left empty. Every future column or item follows the same rule. */
export interface Column { id: string; title: string; items: Item[]; span: number }
/** The tallest a footer list may run before it wraps into another sub-column (owner, 9 November 2026: even display, no empty space). */
export const PER_COLUMN = 6;
export const spanFor = (items: number): number => Math.max(1, Math.min(3, Math.ceil(items / PER_COLUMN)));

const T: Record<string, Record<string, string>> = {
  en: { products: "Products", solutions: "Solutions", developers: "Developers", enterprise: "Enterprise & Partners", company: "Company", resources: "Resources", support: "Support",
    social: "Follow us", download: "Download", payments: "Payment methods", pricing: "Pricing", merchants: "Merchants & Retail", suppliers: "Suppliers & Marketplace",  currency: "Currency & Crypto", cards: "Business Cards & Spend", entItem: "Enterprise", integrations: "Custom Integrations", partners: "Partner Program", agents: "Become an Agent",
    about: "About Us", leadership: "Leadership", careers: "Careers", newsroom: "Newsroom", investors: "Investors", contact: "Contact", how: "How It Works", trust: "Security & Trust", roadmap: "Roadmap",
    blog: "Blog", brand: "Brand Kit", help: "Help Center", vuln: "Report a Vulnerability",
    appstore: "App Store", gplay: "Google Play", pwa: "Install web app", terms: "Terms", privacy: "Privacy", cookies: "Cookies", compliance: "Compliance & Licenses", accessibility: "Accessibility",
    language: "Language", region: "Region", tagline: "Works with or without internet.", nlTitle: "Stay in the loop",
    individuals: "Individuals & Freelancers", companies: "Companies", organisations: "Organisations & Non-profits", logoHome: "LynkOmni home",
    plain_suite: "All-in-one", plain_pos: "Point of sale", plain_stock: "Inventory", plain_acc: "Accounting", plain_inv: "Invoicing", plain_crm: "Customers",
    plain_ops: "Office bundle", plain_stat: "Analytics", plain_grow: "Marketing", plain_rewards: "Loyalty", plain_chat: "Business chat", plain_mpay: "Payments",
    plain_checkout: "Pay links & QR", plain_recover: "Failed-payment recovery", plain_vcard: "Virtual cards", plain_assist: "AI assistant",
    plain_booking: "Travel & ticketing", plain_essential: "Bills & connectivity", plain_dev: "Developer platform",
    move: "Move & protect", plain_motion: "Everyday tracking", plain_guard: "Vehicle & asset protection", plain_trace: "Tracking", plain_gps: "Location & maps", plain_sentry: "Protection",
    plain_hub: "Developer portal", plain_doc: "Documentation", plain_api: "Programming interface", plain_sdk: "Software kits",
    plain_ai: "AI assistant", plain_faq: "Questions & answers", plain_status: "Service status", plain_feedback: "Product feedback", plain_safety: "Safety & reporting",
    nlText: "Product updates, merchant tips and LynkOmni news.", nlEmail: "Email address", nlConsent: "I agree to receive LynkOmni emails and understand I can unsubscribe at any time.",
    pm_bank_transfer: "Bank transfer", pm_qr: "QR payment", pm_crypto: "Crypto", follow: "Follow LynkOmni", nlTopics: "Topics", footerLabel: "LynkOmni site links", nlButton: "Subscribe", nlNote: "We will send a confirmation email first. You are not subscribed until you confirm.", tProduct: "Product updates", tMerchant: "Merchant tips", tDev: "Developer updates", tCompany: "Company news" },
  fr: { products: "Produits", solutions: "Solutions", developers: "Développeurs", enterprise: "Entreprises et partenaires", company: "Entreprise", resources: "Ressources", support: "Assistance",
    social: "Suivez-nous", download: "Télécharger", payments: "Moyens de paiement", pricing: "Tarifs", merchants: "Commerçants et distribution", suppliers: "Fournisseurs et marketplace",
    currency: "Devises et crypto", cards: "Cartes et dépenses pro", entItem: "Entreprise", integrations: "Intégrations sur mesure", partners: "Programme partenaires", agents: "Devenir agent",
    about: "À propos", leadership: "Direction", careers: "Carrières", newsroom: "Presse", investors: "Investisseurs", contact: "Contact", how: "Comment ça marche", trust: "Sécurité et confiance", roadmap: "Feuille de route",
    blog: "Blog", brand: "Kit de marque", help: "Centre d'aide", vuln: "Signaler une vulnérabilité",
    appstore: "App Store", gplay: "Google Play", pwa: "Installer l'application web", terms: "Conditions", privacy: "Confidentialité", cookies: "Cookies", compliance: "Conformité et licences", accessibility: "Accessibilité",
    language: "Langue", region: "Région", tagline: "Fonctionne avec ou sans internet.", nlTitle: "Restez informé",
    nlText: "Nouveautés produits, conseils pour commerçants et actualités de LynkOmni.", nlEmail: "Adresse e-mail", nlConsent: "J'accepte de recevoir les e-mails de LynkOmni et je sais que je peux me désabonner à tout moment.",
    nlButton: "S'abonner", nlNote: "Nous enverrons d'abord un e-mail de confirmation. Vous n'êtes inscrit qu'après confirmation.", tProduct: "Nouveautés produits", tMerchant: "Conseils commerçants", tDev: "Actualités développeurs", tCompany: "Actualités de l'entreprise" },
  sw: { products: "Bidhaa", solutions: "Suluhisho", developers: "Wasanidi", enterprise: "Biashara kubwa na washirika", company: "Kampuni", resources: "Rasilimali", support: "Msaada",
    social: "Tufuate", download: "Pakua", payments: "Njia za malipo", pricing: "Bei", about: "Kuhusu sisi", leadership: "Uongozi", careers: "Kazi", newsroom: "Habari", investors: "Wawekezaji", contact: "Wasiliana nasi",
    how: "Inavyofanya kazi", trust: "Usalama na uaminifu", roadmap: "Ramani ya maendeleo", blog: "Blogu", brand: "Vifaa vya chapa", help: "Kituo cha msaada", ai: "Msaidizi wa AI",
    vuln: "Ripoti udhaifu wa kiusalama", pwa: "Sakinisha programu ya wavuti", terms: "Masharti", privacy: "Faragha", cookies: "Vidakuzi",
    compliance: "Utiifu na leseni", accessibility: "Ufikiaji", language: "Lugha", region: "Eneo", tagline: "Inafanya kazi na au bila intaneti.", nlTitle: "Endelea kupata habari",
    nlText: "Habari za bidhaa, vidokezo kwa wafanyabiashara na habari za LynkOmni.", nlEmail: "Barua pepe", nlConsent: "Nakubali kupokea barua pepe za LynkOmni na ninajua naweza kujiondoa wakati wowote.",
    nlButton: "Jiandikishe", nlNote: "Tutatuma barua pepe ya uthibitisho kwanza. Hujajiandikisha hadi uthibitishe." },
};
export const footerText = (lang: string, key: string): string => T[lang]?.[key] ?? T["en"]![key] ?? key;   // per-string fallback to English
/** The footer words of the app's language packs (web/footer, keys "ft_<key>"), when the app carries them: every interface language. */
export type Words = (key: string) => string | undefined;
const say = (lang: string, words: Words | undefined, key: string): string => words?.(`ft_${key}`) ?? footerText(lang, key);
/** Every key the footer shows, in one list: web/footer/strings.en.json holds exactly these (tests/test_footer_words). */
export const FOOTER_KEYS = Object.keys(T["en"]!);
/** Methods named by a common word (translated); every other method is a provider's own name, written as text. */
const GENERIC_METHODS: readonly string[] = ["bank_transfer", "qr", "crypto"];

/** Fixed text. Never translated, reworded or shortened. */
export const copyright = (year: number): string => `© ${year} CruxOmni Group. All rights reserved. LynkOmni is a product of CruxOmni Group.`;

/** The year in the viewer's own time zone, so it flips to the new year at local midnight and is never cached into a page. */
export function currentYear(now: Date, tz: string): number {
  try { return Number(new Intl.DateTimeFormat("en-US", { timeZone: tz, year: "numeric" }).format(now)); } catch { return now.getUTCFullYear(); }
}
export const shortFooter = (now: Date, tz: string): string => copyright(currentYear(now, tz));

let WORDS: Words | undefined, LANG = "en";
/** A product's short name always travels with a plain word for it ("LynkAcc (Accounting)"), translated like every footer word. */
const brand = (id: string, label: string, href: string): Item => ({ id, label, href, brand: true, plain: say(LANG, WORDS, `plain_${id}`) });
const txt = (lang: string, id: string, key: string, href: string): Item => ({ id, label: say(lang, WORDS, key), href });

export function columns(lang: string, words?: Words): Column[] {
  WORDS = words; LANG = lang;
  const tt = (k: string): string => say(lang, words, k);
  const cols: Omit<Column, "span">[] = [
    { id: "products", title: tt("products"), items: [brand("suite", "LynkSuite", "/suite"), brand("pos", "LynkPOS", "/pos"), brand("stock", "LynkStock", "/stock"), brand("acc", "LynkAcc", "/accounting"), brand("inv", "LynkInv", "/invoicing"), brand("crm", "LynkCRM", "/crm"), brand("ops", "LynkOps", "/ops"),
      brand("stat", "LynkStat", "/analytics"), brand("grow", "LynkGrow", "/grow"), brand("rewards", "LynkRewards", "/rewards"), brand("chat", "LynkChat", "/chat"), brand("mpay", "LynkMPay", "/mpay"),
      brand("checkout", "LynkCheckout", "/checkout"), brand("recover", "LynkRecover", "/recover"), brand("vcard", "LynkVCard", "/vcard"), brand("assist", "LynkAssist", "/ai"), txt(lang, "pricing", "pricing", "/pricing")] },
    { id: "move", title: tt("move"), items: [brand("motion", "LynkMotion", "/motion"), brand("guard", "LynkGuard", "/guard"), brand("trace", "LynkTrace", "/tracking"),
      brand("gps", "LynkGPS", "/gps"), brand("sentry", "LynkSentry", "/protection")] },
    { id: "solutions", title: tt("solutions"), items: [txt(lang, "merchants", "merchants", "/solutions/merchants"), txt(lang, "suppliers", "suppliers", "/solutions/suppliers"),
      txt(lang, "individuals", "individuals", "/solutions/individuals"), txt(lang, "companies", "companies", "/solutions/companies"), txt(lang, "organisations", "organisations", "/solutions/organisations"),
      brand("booking", "LynkBooking", "https://booking.lynkomni.com"), brand("essential", "LynkEssential", "https://essential.lynkomni.com"), txt(lang, "currency", "currency", "https://exchange.lynkomni.com"),
      txt(lang, "cards", "cards", "/vcard")] },
    { id: "developers", title: tt("developers"), items: [brand("dev", "LynkDev", "/developers"), brand("hub", "LynkHub", "https://hub.lynkomni.com"), brand("doc", "LynkDoc", "https://doc.lynkomni.com"), brand("api", "LynkAPI", "https://api.lynkomni.com"),
      brand("sdk", "LynkSDK", "https://sdk.lynkomni.com")] },
    { id: "enterprise", title: tt("enterprise"), items: [txt(lang, "enterprise", "entItem", "/enterprise"), txt(lang, "integrations", "integrations", "/enterprise/integrations"),
      txt(lang, "partners", "partners", "/partners"), txt(lang, "agents", "agents", "/agents")] },
    { id: "company", title: tt("company"), items: [txt(lang, "about", "about", "/about"), txt(lang, "leadership", "leadership", "/about/leadership"), txt(lang, "careers", "careers", "/careers"),
      txt(lang, "newsroom", "newsroom", "/newsroom"), txt(lang, "investors", "investors", "/investors"), txt(lang, "contact", "contact", "/contact")] },
    { id: "resources", title: tt("resources"), items: [txt(lang, "how", "how", "/how-it-works"), txt(lang, "trust", "trust", "/trust"), txt(lang, "roadmap", "roadmap", "/roadmap"),
      txt(lang, "blog", "blog", "/blog"), txt(lang, "brand", "brand", "/brand")] },
    { id: "support", title: tt("support"), items: [txt(lang, "help", "help", "/support"), brand("faq", "LynkFAQ", "/faq"), brand("ai", "LynkAssist", "/ai"), brand("status", "LynkStatus", "https://status.lynkomni.com"),
      brand("feedback", "LynkFeedback", "/feedback"), brand("safety", "LynkSafety", "/safety"), txt(lang, "vuln", "vuln", "/trust/disclosure")] },
  ];
  return cols.map((c) => ({ ...c, span: spanFor(c.items.length) }));
}
export const SOCIAL = ["linkedin", "x", "facebook", "instagram", "youtube", "tiktok", "whatsapp"] as const;   // Snapchat, Pinterest and Threads removed: no audience fit for a merchant and fintech platform
/** Official LynkOmni accounts (claimed 2026-11-06 under the name "LynkOmni" on all ten platforms; seven are shown). */
export const SOCIAL_LINKS: Record<(typeof SOCIAL)[number], string> = {
  linkedin: "https://www.linkedin.com/showcase/lynkomni", x: "https://x.com/LynkOmni", facebook: "https://www.facebook.com/LynkOmni",
  instagram: "https://www.instagram.com/lynkomni", youtube: "https://www.youtube.com/@LynkOmni", tiktok: "https://www.tiktok.com/@lynkomni",
  whatsapp: "https://wa.me/237681296652",
};
/** Only methods this country's transactions really use, from the country pack (ts/src/payments.ts). Each is shown as a
 *  LynkOmni method icon plus the provider's name as text; never a copied logo. */
export function paymentMarks(pack: Pack | null): string[] {
  return paymentOptions(pack).map((o) => o.id);
}
export function buildFooter(o: { now: Date; pack: Pack | null; lang: string; words?: Words }) {
  const tz = o.pack?.tz ?? "UTC", lang = o.words || T[o.lang] ? o.lang : "en";
  const t = (_l: string, k: string): string => say(lang, o.words, k);
  return {
    lang, region: o.pack ? { code: o.pack.code, name: o.pack.name, currency: o.pack.currency } : null, tagline: t(lang, "tagline"),
    newsletter: { title: t(lang, "nlTitle"), text: t(lang, "nlText"), email: t(lang, "nlEmail"), consent: t(lang, "nlConsent"), button: t(lang, "nlButton"), note: t(lang, "nlNote"), preticked: false, doubleOptIn: true,
      topics: [t(lang, "tProduct"), t(lang, "tMerchant"), t(lang, "tDev"), t(lang, "tCompany")] },
    columns: columns(lang, o.words), social: [...SOCIAL], socialLinks: SOCIAL.map((id) => ({ id, href: SOCIAL_LINKS[id] })), download: [{ id: "appstore", label: t(lang, "appstore") }, { id: "gplay", label: t(lang, "gplay") }, { id: "pwa", label: t(lang, "pwa") }],
    payments: { title: t(lang, "payments"), marks: paymentMarks(o.pack), options: paymentOptions(o.pack).map((x) => ({ ...x, label: GENERIC_METHODS.includes(x.id) ? t(lang, `pm_${x.id}`) : x.label })) },
    labels: { language: t(lang, "language"), region: t(lang, "region"), social: t(lang, "social"), download: t(lang, "download"), topics: t(lang, "nlTopics"), footer: t(lang, "footerLabel"), home: t(lang, "logoHome") },
    legal: { copyright: copyright(currentYear(o.now, tz)), links: [txt(lang, "terms", "terms", "/legal/terms"), txt(lang, "privacy", "privacy", "/legal/privacy"), txt(lang, "cookies", "cookies", "/legal/cookies"),
      txt(lang, "compliance", "compliance", "/legal/compliance"), txt(lang, "accessibility", "accessibility", "/legal/accessibility")] },
  };
}

/** The main footer (section 26 A and B) for websites and web apps, drawn from buildFooter. The full LynkOmni logo (brand surface
 *  "web-footer", one artwork per theme: the page shows the one that matches its theme) stands above the tagline. Long lists flow
 *  into sub-columns (Column.span). Payment methods are LynkOmni method icons with the provider's name as text; social channels are
 *  text links (no other company's logo is drawn); the newsletter box is unticked; the copyright line is the fixed text.
 *  `icon` draws a LynkOmni icon by id; `logo` holds the logo artwork for the light and the dark theme. */
export function mainFooterHtml(f: ReturnType<typeof buildFooter>, esc: (s: string) => string, icon: (id: string) => string, logo?: { light: string; dark: string }): string {
  const link = (i: Item): string => `<li><a href="${esc(i.href)}">${i.plain ? `<span class="fname">${esc(i.label)}</span> <span class="fplain">(${esc(i.plain)})</span>` : esc(i.label)}</a></li>`;
  const cols = f.columns.map((c) => `<section class="fcol" data-span="${c.span}" style="--span:${c.span}"><h3>${esc(c.title)}</h3><ul>${c.items.map(link).join("")}</ul></section>`).join("");
  const mark = logo ? `<a class="flogo" href="/" aria-label="${esc(f.labels.home)}"><span class="on-light">${logo.light}</span><span class="on-dark">${logo.dark}</span></a>` : "";
  const SOCIAL_NAMES: Record<string, string> = { linkedin: "LinkedIn", x: "X", facebook: "Facebook", instagram: "Instagram", youtube: "YouTube", tiktok: "TikTok", whatsapp: "WhatsApp" };
  const social = f.socialLinks.map((s) => `<li><a href="${esc(s.href)}" target="_blank" rel="noopener">${esc(SOCIAL_NAMES[s.id] ?? s.id)}</a></li>`).join("");
  const pay = f.payments.options.map((o) => `<li class="fpay"><span class="ic" aria-hidden="true">${icon(o.icon)}</span>${esc(o.label)}</li>`).join("");
  const n = f.newsletter;
  const topics = n.topics.map((x, i) => `<label class="ftopic"><input type="checkbox" name="topic${i}"> ${esc(x)}</label>`).join("");
  return `<footer class="mainfoot" role="contentinfo" aria-label="${esc(f.labels.footer)}">
${mark}<p class="ftag">${esc(f.tagline)}</p><div class="fcols">${cols}</div>
<div class="frow"><section class="fcol"><h3>${esc(f.payments.title)}</h3><ul class="fpays">${pay}</ul></section>
<section class="fcol"><h3>${esc(f.labels.social)}</h3><ul>${social}</ul></section>
<section class="fcol"><h3>${esc(f.labels.download)}</h3><ul>${f.download.map((d) => `<li><a href="/download#${esc(d.id)}">${esc(d.label)}</a></li>`).join("")}</ul></section>
<div class="fnews" role="group" aria-labelledby="fnewsTitle"><h3 id="fnewsTitle">${esc(n.title)}</h3><p>${esc(n.text)}</p><label class="fl"><span>${esc(n.email)}</span><input type="email" autocomplete="email"></label>
<fieldset><legend>${esc(f.labels.topics)}</legend>${topics}</fieldset><label class="fconsent"><input type="checkbox" required> <span>${esc(n.consent)}</span></label>
<button type="button" data-act="footer:news">${esc(n.button)}</button><p class="fnote">${esc(n.note)}</p></div></div>
<div class="flegal"><p class="fcopy">${esc(f.legal.copyright)}</p><ul>${f.legal.links.map(link).join("")}</ul></div></footer>`;
}
/** The short footer inside apps (section 26 C): one line, the fixed copyright text with the year in the viewer's time zone. */
export const shortFooterHtml = (now: Date, tz: string): string => `<footer class="shortfoot" role="contentinfo"><p>${shortFooter(now, tz)}</p></footer>`;
