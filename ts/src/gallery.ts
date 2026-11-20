/** The part gallery of the showcase (INTERFACE UPDATE 73.8, section 4 step B2c): every app-shell and page-template part, drawn
 *  by the real parts from the real registers, in English. web/build.mjs writes it to web/showcase/gallery.generated.html (icons
 *  filled from the brand module) and its --check fails when the gallery is out of date; tools/showcase.py shows it. */
import type { NavRegister } from "./navigation.js";
import { firstColumnHtml, launcherGroupsHtml, quickCreateHtml, serviceMenuHtml, tabsHtml } from "./appshell.js";
import { listToolbarHtml, recordHeaderHtml, saveBarHtml } from "./pagekit.js";
import type { DeviceRegister } from "./interfaces.js";
import { layoutFor } from "./interfaces.js";
import { CHAT } from "./chat.generated.js";
import { inboxRowHtml, threadHtml, warningHtml } from "./chatview.js";
import type { ChatLook } from "./chatview.js";

/** Icons are written as build markers, filled by the page build from the brand module. */
const mark = (id: string): string => `<span class="ic" aria-hidden="true">/*@I:${id}@*/</span>`;

export function galleryHtml(nav: NavRegister, devices: DeviceRegister, words: Record<string, string>, names: Record<string, string>): string {
  const t = (k: string): string => words[k] ?? k;
  const look = { t, icon: (id: string) => mark(id) };
  const shape = (w: number, h: number, i = "phone.touch") => layoutFor(devices, { interface: i, width: w, height: h });
  const tile = (title: string, note: string, html: string): string => `<figure class="gal-part"><div class="gal-stage">${html}</div><figcaption><strong>${title}</strong><span>${note}</span></figcaption></figure>`;
  const shopWord = (k: string): string => ({ home: "Home", sell: "Sell", stock: "Stock", chats: "Chats", business: "Business" } as Record<string, string>)[k] ?? t(`nv_${k}`);
  const shop = { ...look, label: shopWord, tabIcon: (k: string) => ({ sell: "ui-cart", stock: "product-stock", chats: "product-chat", business: "product-dash" } as Record<string, string>)[k] };
  return [
    tile("Bottom bar, a person", "Home, Track, Scan, Chats, Me; words always shown", tabsHtml(nav, look, { kind: "person", layout: shape(390, 844), screen: "home", current: "home" })),
    tile("Bottom bar, a shop", "The business type's five tabs", tabsHtml(nav, shop, { kind: "shop", layout: shape(390, 844), screen: "home", current: "sell" })),
    tile("Bottom bar, a small phone", "Four tabs under 340 px", tabsHtml(nav, shop, { kind: "shop", layout: shape(320, 568), screen: "home", current: "home" })),
    tile("Side rail", "A phone turned sideways or a tablet", tabsHtml(nav, shop, { kind: "shop", layout: shape(844, 390), screen: "home", current: "stock" })),
    tile("Focus screen", "During a payment, count, void, signature or ballot there is no bar at all", `<p class="gal-empty">${tabsHtml(nav, shop, { kind: "shop", layout: shape(390, 844), screen: "pay", current: "sell" }) || "No bar: only Back and the connection chip."}</p>`),
    tile("Side bar, first column", "On a computer; Settings and Help can never be hidden", firstColumnHtml(nav, look, { current: "home" })),
    tile("Side bar, service menu", "The same order in every service", serviceMenuHtml(nav, look, { service: "queue", current: "queue_tickets", title: (s) => { const w = s.replace(/^queue_?/, "").replace(/_/g, " ") || "overview"; return w.charAt(0).toUpperCase() + w.slice(1); } })),
    tile("Quick create (+)", "What an owner starts most", quickCreateHtml(nav, look, { role: "owner", close: "gal" })),
    tile("Launcher", "My services first, then the eight groups", launcherGroupsHtml(nav, look, { mine: ["lynkpos", "lynkstock"], name: (f) => names[f] ?? f, productIcon: () => "ui-grid" })),
    tile("Record header", "Name, state, one main button and the same four tabs", recordHeaderHtml(nav, t, { title: "Sample record", main: { label: "Main action", act: "gal" } })),
    tile("List toolbar", "Search with its label and filter chips", listToolbarHtml(t, { hint: "Sample: LOINV-0042", chips: [{ id: "all", label: "All", on: true }, { id: "open", label: "Open" }, { id: "late", label: "Late" }] })),
    tile("Save bar", "Stays in view at the bottom of a form", saveBarHtml({ label: "Save", act: "gal", secondary: { label: t("nv_back"), act: "gal" } })),
    ...chatTiles(t, tile),
  ].join("\n");
}

/** The shared chat part (CHAT UPDATE 74, section 4 step C2), drawn by the real part from the chat register, still (motion off). */
function chatTiles(t: (k: string) => string, tile: (title: string, note: string, html: string) => string): string[] {
  const words = (k: string, v?: Record<string, string | number>): string => Object.entries(v ?? {}).reduce((s, [a, b]) => s.replace(`{${a}}`, String(b)), t(k));
  const look: ChatLook = { t: words, icon: (id) => mark(id), clock: () => "10:42", reducedMotion: true,
    chip: (s) => `<span class="chip st-${s}">${mark(`status-${s}`)}<span>${s}</span></span>` };
  const base = { id: "g", kind: "support", title: "Support", side: "internal" as const, online: true, draft: "", draftHint: t("ch_hint_message"), act: "gal" };
  return [
    tile("Chat: a support conversation", "LynkAssist always named, its stage with Stop, a person one tap away, the five states",
      threadHtml(CHAT, look, { ...base, assistFirst: true, msgs: [
        { id: "a", author: "business", out: true, text: "A question about a payment", at: 0, state: "confirmed" },
        { id: "b", author: "assistant", out: false, text: "Payments show as paid only", at: 0, state: "accepted", stream: { stage: "assist_writing" } }] })),
    tile("Chat: live sign and states", "Typing shows as words; your message moves from sent to seen",
      threadHtml(CHAT, look, { ...base, kind: "customer_business", sign: { sign: "typing", author: "customer" }, msgs: [
        { id: "c", author: "customer", out: false, text: "Do you have cooking oil today?", at: 0, state: "accepted" },
        { id: "d", author: "business", out: true, text: "Yes, 1 L and 5 L", at: 0, state: "accepted" }] })),
    tile("Chat: a card number is never sent", "Masked before it is queued, with the warning", warningHtml(look, ["card"], "gal")),
    tile("Chat: inbox row", "The live sign replaces the last message for a moment",
      `<ul class="list card">${inboxRowHtml(CHAT, look, { id: "x", name: "Sample customer", last: "Thank you!", at: 0, unread: 2, sign: { sign: "typing", author: "customer" } }, { online: true, act: "gal" })}</ul>`),
  ];
}
