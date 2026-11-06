import { paymentOptions } from "./payments.js";
/** LynkOmni footer: one model for every site and app. Menus use ecosystem names, copyright is fixed text, the year follows the viewer's
 *  time zone, language and payment methods follow the country pack. Translations are DRAFTS pending native-speaker review. */
export interface Pack { code: string; name: string; currency: string; tz: string; languages: string[]; providers: string[]; card_networks: string[]; wallets: string[] }
export interface Item { id: string; label: string; href: string; brand?: boolean }
export interface Column { id: string; title: string; items: Item[] }

const T: Record<string, Record<string, string>> = {
  en: { products: "Products", solutions: "Solutions", developers: "Developers", enterprise: "Enterprise & Partners", company: "Company", resources: "Resources", support: "Support",
    social: "Follow us", download: "Download", payments: "Payment methods", pricing: "Pricing", merchants: "Merchants & Retail", suppliers: "Suppliers & Marketplace", travel: "Travel & Ticketing",
    bills: "Bills & Connectivity", currency: "Currency & Crypto", cards: "Business Cards & Spend", entItem: "Enterprise", integrations: "Custom Integrations", partners: "Partner Program", agents: "Become an Agent",
    about: "About Us", leadership: "Leadership", careers: "Careers", newsroom: "Newsroom", investors: "Investors", contact: "Contact", how: "How It Works", trust: "Security & Trust", roadmap: "Roadmap",
    blog: "Blog", brand: "Brand Kit", help: "Help Center", faq: "FAQ", ai: "AI Assistant", status: "Service Status", feedback: "Feedback", safety: "Safety", vuln: "Report a Vulnerability",
    appstore: "App Store", gplay: "Google Play", pwa: "Install web app", terms: "Terms", privacy: "Privacy", cookies: "Cookies", compliance: "Compliance & Licenses", accessibility: "Accessibility",
    language: "Language", region: "Region", tagline: "Works with or without internet. Built from Africa, for the world.", nlTitle: "Stay in the loop",
    nlText: "Product updates, merchant tips and LynkOmni news.", nlEmail: "Email address", nlConsent: "I agree to receive LynkOmni emails and understand I can unsubscribe at any time.",
    nlButton: "Subscribe", nlNote: "We will send a confirmation email first. You are not subscribed until you confirm.", tProduct: "Product updates", tMerchant: "Merchant tips", tDev: "Developer updates", tCompany: "Company news" },
  fr: { products: "Produits", solutions: "Solutions", developers: "Développeurs", enterprise: "Entreprises et partenaires", company: "Entreprise", resources: "Ressources", support: "Assistance",
    social: "Suivez-nous", download: "Télécharger", payments: "Moyens de paiement", pricing: "Tarifs", merchants: "Commerçants et distribution", suppliers: "Fournisseurs et marketplace", travel: "Voyages et billetterie",
    bills: "Factures et connectivité", currency: "Devises et crypto", cards: "Cartes et dépenses pro", entItem: "Entreprise", integrations: "Intégrations sur mesure", partners: "Programme partenaires", agents: "Devenir agent",
    about: "À propos", leadership: "Direction", careers: "Carrières", newsroom: "Presse", investors: "Investisseurs", contact: "Contact", how: "Comment ça marche", trust: "Sécurité et confiance", roadmap: "Feuille de route",
    blog: "Blog", brand: "Kit de marque", help: "Centre d'aide", faq: "FAQ", ai: "Assistant IA", status: "État du service", feedback: "Retours", safety: "Sécurité des utilisateurs", vuln: "Signaler une vulnérabilité",
    appstore: "App Store", gplay: "Google Play", pwa: "Installer l'application web", terms: "Conditions", privacy: "Confidentialité", cookies: "Cookies", compliance: "Conformité et licences", accessibility: "Accessibilité",
    language: "Langue", region: "Région", tagline: "Fonctionne avec ou sans internet. Conçu en Afrique, pour le monde.", nlTitle: "Restez informé",
    nlText: "Nouveautés produits, conseils pour commerçants et actualités de LynkOmni.", nlEmail: "Adresse e-mail", nlConsent: "J'accepte de recevoir les e-mails de LynkOmni et je sais que je peux me désabonner à tout moment.",
    nlButton: "S'abonner", nlNote: "Nous enverrons d'abord un e-mail de confirmation. Vous n'êtes inscrit qu'après confirmation.", tProduct: "Nouveautés produits", tMerchant: "Conseils commerçants", tDev: "Actualités développeurs", tCompany: "Actualités de l'entreprise" },
  sw: { products: "Bidhaa", solutions: "Suluhisho", developers: "Wasanidi", enterprise: "Biashara kubwa na washirika", company: "Kampuni", resources: "Rasilimali", support: "Msaada",
    social: "Tufuate", download: "Pakua", payments: "Njia za malipo", pricing: "Bei", about: "Kuhusu sisi", leadership: "Uongozi", careers: "Kazi", newsroom: "Habari", investors: "Wawekezaji", contact: "Wasiliana nasi",
    how: "Inavyofanya kazi", trust: "Usalama na uaminifu", roadmap: "Ramani ya maendeleo", blog: "Blogu", brand: "Vifaa vya chapa", help: "Kituo cha msaada", faq: "Maswali ya mara kwa mara", ai: "Msaidizi wa AI",
    status: "Hali ya huduma", feedback: "Maoni", safety: "Usalama wa watumiaji", vuln: "Ripoti udhaifu wa kiusalama", pwa: "Sakinisha programu ya wavuti", terms: "Masharti", privacy: "Faragha", cookies: "Vidakuzi",
    compliance: "Utiifu na leseni", accessibility: "Ufikiaji", language: "Lugha", region: "Eneo", tagline: "Inafanya kazi na au bila intaneti. Imejengwa Afrika, kwa dunia.", nlTitle: "Endelea kupata habari",
    nlText: "Habari za bidhaa, vidokezo kwa wafanyabiashara na habari za LynkOmni.", nlEmail: "Barua pepe", nlConsent: "Nakubali kupokea barua pepe za LynkOmni na ninajua naweza kujiondoa wakati wowote.",
    nlButton: "Jiandikishe", nlNote: "Tutatuma barua pepe ya uthibitisho kwanza. Hujajiandikisha hadi uthibitishe." },
};
export const t = (lang: string, key: string): string => T[lang]?.[key] ?? T["en"]![key] ?? key;   // per-string fallback to English

/** Fixed text. Never translated, reworded or shortened. */
export const copyright = (year: number): string => `© ${year} CruxOmni Group. All rights reserved. LynkOmni is a product of CruxOmni Group.`;

/** The year in the viewer's own time zone, so it flips to the new year at local midnight and is never cached into a page. */
export function currentYear(now: Date, tz: string): number {
  try { return Number(new Intl.DateTimeFormat("en-US", { timeZone: tz, year: "numeric" }).format(now)); } catch { return now.getUTCFullYear(); }
}
export const shortFooter = (now: Date, tz: string): string => copyright(currentYear(now, tz));

const brand = (id: string, label: string, href: string): Item => ({ id, label, href, brand: true });
const txt = (lang: string, id: string, key: string, href: string): Item => ({ id, label: t(lang, key), href });

export function columns(lang: string): Column[] {
  return [
    { id: "products", title: t(lang, "products"), items: [brand("suite", "LynkSuite", "/suite"), brand("pos", "LynkPOS", "/pos"), brand("stock", "LynkStock", "/stock"), brand("ledger", "LynkLedger", "/ledger"),
      brand("dash", "LynkDash", "/dash"), brand("grow", "LynkGrow", "/grow"), brand("rewards", "LynkRewards", "/rewards"), brand("chat", "LynkChat", "/chat"), brand("mpay", "LynkMPay", "/mpay"),
      brand("vcard", "LynkVCard", "/vcard"), brand("assist", "LynkAssist", "/ai"), txt(lang, "pricing", "pricing", "/pricing")] },
    { id: "solutions", title: t(lang, "solutions"), items: [txt(lang, "merchants", "merchants", "/solutions/merchants"), txt(lang, "suppliers", "suppliers", "/solutions/suppliers"),
      txt(lang, "travel", "travel", "https://booking.lynkomni.com"), txt(lang, "bills", "bills", "https://essential.lynkomni.com"), txt(lang, "currency", "currency", "https://exchange.lynkomni.com"),
      txt(lang, "cards", "cards", "/vcard")] },
    { id: "developers", title: t(lang, "developers"), items: [brand("hub", "LynkHub", "https://hub.lynkomni.com"), brand("doc", "LynkDoc", "https://doc.lynkomni.com"), brand("api", "LynkAPI", "https://api.lynkomni.com"),
      brand("sdk", "LynkSDK", "https://sdk.lynkomni.com")] },
    { id: "enterprise", title: t(lang, "enterprise"), items: [txt(lang, "enterprise", "entItem", "/enterprise"), txt(lang, "integrations", "integrations", "/enterprise/integrations"),
      txt(lang, "partners", "partners", "/partners"), txt(lang, "agents", "agents", "/agents")] },
    { id: "company", title: t(lang, "company"), items: [txt(lang, "about", "about", "/about"), txt(lang, "leadership", "leadership", "/about/leadership"), txt(lang, "careers", "careers", "/careers"),
      txt(lang, "newsroom", "newsroom", "/newsroom"), txt(lang, "investors", "investors", "/investors"), txt(lang, "contact", "contact", "/contact")] },
    { id: "resources", title: t(lang, "resources"), items: [txt(lang, "how", "how", "/how-it-works"), txt(lang, "trust", "trust", "/trust"), txt(lang, "roadmap", "roadmap", "/roadmap"),
      txt(lang, "blog", "blog", "/blog"), txt(lang, "brand", "brand", "/brand")] },
    { id: "support", title: t(lang, "support"), items: [txt(lang, "help", "help", "/support"), brand("faq", "LynkFAQ", "/faq"), brand("ai", "LynkAssist", "/ai"), brand("status", "LynkStatus", "https://status.lynkomni.com"),
      brand("feedback", "LynkFeedback", "/feedback"), brand("safety", "LynkSafety", "/safety"), txt(lang, "vuln", "vuln", "/trust/disclosure")] },
  ];
}
export const SOCIAL = ["linkedin", "x", "facebook", "instagram", "youtube", "tiktok", "whatsapp"] as const;   // Snapchat, Pinterest and Threads removed: no audience fit for a merchant and fintech platform
/** Only methods this country's transactions really use, from the country pack (ts/src/payments.ts). Each is shown as a
 *  LynkOmni method icon plus the provider's name as text; never a copied logo. */
export function paymentMarks(pack: Pack | null): string[] {
  return paymentOptions(pack).map((o) => o.id);
}
export function buildFooter(o: { now: Date; pack: Pack | null; lang: string }) {
  const tz = o.pack?.tz ?? "UTC", lang = T[o.lang] ? o.lang : "en";
  return {
    lang, region: o.pack ? { code: o.pack.code, name: o.pack.name, currency: o.pack.currency } : null, tagline: t(lang, "tagline"),
    newsletter: { title: t(lang, "nlTitle"), text: t(lang, "nlText"), email: t(lang, "nlEmail"), consent: t(lang, "nlConsent"), button: t(lang, "nlButton"), note: t(lang, "nlNote"), preticked: false, doubleOptIn: true,
      topics: [t(lang, "tProduct"), t(lang, "tMerchant"), t(lang, "tDev"), t(lang, "tCompany")] },
    columns: columns(lang), social: [...SOCIAL], download: [{ id: "appstore", label: t(lang, "appstore") }, { id: "gplay", label: t(lang, "gplay") }, { id: "pwa", label: t(lang, "pwa") }],
    payments: { title: t(lang, "payments"), marks: paymentMarks(o.pack), options: paymentOptions(o.pack) },
    legal: { copyright: copyright(currentYear(o.now, tz)), links: [txt(lang, "terms", "terms", "/legal/terms"), txt(lang, "privacy", "privacy", "/legal/privacy"), txt(lang, "cookies", "cookies", "/legal/cookies"),
      txt(lang, "compliance", "compliance", "/legal/compliance"), txt(lang, "accessibility", "accessibility", "/legal/accessibility")] },
  };
}
