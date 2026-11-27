/**
 * The device's own on-screen keyboard in touch-screen emulators (owner, 2026-11-27: every emulator matches its real device).
 * Touching a typing field inside a device screen slides this keyboard up inside that screen, as on the real phone, tablet,
 * kiosk or terminal, so the tester's own phone keyboard never opens. It follows the field's kind (letters, email, number,
 * phone) and the language picked, has a key to switch to English letters and back, and never covers the field being typed in.
 * Rules come only from catalog/keyboards.v1.json (ts/src/keyboards.generated.ts), proved against core/keyboards.py by
 * contract/vectors/keyboards.v1.json. Devices with real keys and computers type with their own keys; real apps use the
 * device's own keyboard.
 */
import { KEYBOARDS } from "./keyboards.generated.js";

type T = (k: string) => string;
export type KbKind = "letters" | "email" | "number" | "phone";
const K = KEYBOARDS as unknown as { layouts: Record<string, string[][]>; languages: Record<string, string>; compose: Record<string, string>;
  number: string[][]; phone: string[][]; symbols: string[][]; email_keys: string[]; ethiopic_orders: string[] };

export function kbLayout(lang: string): string[][] { return K.layouts[K.languages[lang] ?? "latin"] ?? K.layouts["latin"]!; }
export function kbKindOf(type: string, mode = ""): KbKind {
  const t = (type || "").toLowerCase(), m = (mode || "").toLowerCase();
  if (t === "email" || m === "email") return "email";
  if (t === "tel" || m === "tel") return "phone";
  if (t === "number" || m === "numeric" || m === "decimal") return "number";
  return "letters";
}

// Korean: letters join into syllables (port of core/keyboards.py hangul).
const HL = "ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ", HV = "ㅏㅐㅑㅒㅓㅔㅕㅖㅗㅘㅙㅚㅛㅜㅝㅞㅟㅠㅡㅢㅣ", HT = " ㄱㄲㄳㄴㄵㄶㄷㄹㄺㄻㄼㄽㄾㄿㅀㅁㅂㅄㅅㅆㅇㅈㅊㅋㅌㅍㅎ";
const VV: Record<string, string> = { "ㅗㅏ": "ㅘ", "ㅗㅐ": "ㅙ", "ㅗㅣ": "ㅚ", "ㅜㅓ": "ㅝ", "ㅜㅔ": "ㅞ", "ㅜㅣ": "ㅟ", "ㅡㅣ": "ㅢ" };
const TT: Record<string, string> = { "ㄱㅅ": "ㄳ", "ㄴㅈ": "ㄵ", "ㄴㅎ": "ㄶ", "ㄹㄱ": "ㄺ", "ㄹㅁ": "ㄻ", "ㄹㅂ": "ㄼ", "ㄹㅅ": "ㄽ", "ㄹㅌ": "ㄾ", "ㄹㅍ": "ㄿ", "ㄹㅎ": "ㅀ", "ㅂㅅ": "ㅄ" };
const SPLIT: Record<string, string> = Object.fromEntries(Object.entries(TT).map(([k, v]) => [v, k]));
const syl = (l: string, v: string, t = " "): string => String.fromCharCode(0xac00 + (HL.indexOf(l) * 21 + HV.indexOf(v)) * 28 + HT.indexOf(t));
function parts(ch: string): [string, string, string] | null {
  const c = (ch.codePointAt(0) ?? 0) - 0xac00;
  return c >= 0 && c < 11172 ? [HL[Math.floor(c / 588)]!, HV[Math.floor((c % 588) / 28)]!, HT[c % 28]!] : null;
}
export function hangul(text: string, jamo: string): string {
  const last = text.slice(-1), p = last ? parts(last) : null;
  if (HV.includes(jamo)) {
    if (p && p[2] === " ") { const vv = VV[p[1] + jamo]; return vv ? text.slice(0, -1) + syl(p[0], vv) : text + jamo; }
    if (p && p[2] !== " ") {
      const sp = SPLIT[p[2]];
      if (sp) return text.slice(0, -1) + syl(p[0], p[1], sp[0]!) + syl(sp[1]!, jamo);
      if (HL.includes(p[2])) return text.slice(0, -1) + syl(p[0], p[1]) + syl(p[2], jamo);
    }
    if (last && HL.includes(last)) return text.slice(0, -1) + syl(last, jamo);
    return text + jamo;
  }
  if (p && p[2] === " " && HT.includes(jamo)) return text.slice(0, -1) + syl(p[0], p[1], jamo);
  if (p && p[2] !== " " && TT[p[2] + jamo]) return text.slice(0, -1) + syl(p[0], p[1], TT[p[2] + jamo]!);
  return text + jamo;
}
/** Amharic: the last consonant takes the vowel form of the key pressed after it (1 u, 2 i, 3 a, 4 e, 5 no vowel, 6 o). */
export function ethiopic(text: string, order: number): string {
  if (!text) return text;
  const cp = text.codePointAt(text.length - 1) ?? 0;
  if (cp < 0x1200 || cp > 0x137f) return text;
  return text.slice(0, -1) + String.fromCodePoint(cp - ((cp - 0x1200) % 8) + order);
}
const KANA: Record<string, string> = { a: "あ", i: "い", u: "う", e: "え", o: "お" };
for (const [c, row] of Object.entries({ k: "かきくけこ", s: "さしすせそ", t: "たちつてと", n: "なにぬねの", h: "はひふへほ", m: "まみむめも", y: "や ゆ よ", r: "らりるれろ", w: "わ   を", g: "がぎぐげご", z: "ざじずぜぞ", d: "だぢづでど", b: "ばびぶべぼ", p: "ぱぴぷぺぽ" }))
  [..."aiueo"].forEach((v, i) => { const k = [...row][i]; if (k && k !== " ") KANA[c + v] = k; });
Object.assign(KANA, { shi: "し", chi: "ち", tsu: "つ", fu: "ふ", ji: "じ" });
const ascii = (s: string): boolean => /^[\x00-\x7f]*$/.test(s);
/** Japanese: the romaji at the end of the text turns into kana (port of core/keyboards.py romaji). */
export function romaji(text: string): string {
  for (const n of [3, 2, 1]) {
    const tail = text.slice(-n);
    if (tail.length === n && ascii(tail) && KANA[tail]) { let head = text.slice(0, -n); if (head.endsWith("n")) head = head.slice(0, -1) + "ん"; return head + KANA[tail]; }
  }
  if (text.length >= 2 && text[text.length - 2] === "n" && ascii(text.slice(-1)) && !"aiueoyn".includes(text.slice(-1))) return text.slice(0, -2) + "ん" + text.slice(-1);
  return text;
}
export const romajiDone = (text: string): string => (text.endsWith("n") ? text.slice(0, -1) + "ん" : text);

const kbEsc = (s: string): string => s.replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c] ?? c);
const TYPING = 'input:not([type]),input[type="text"],input[type="search"],input[type="email"],input[type="tel"],input[type="number"],input[type="password"],input[type="url"],textarea';
type Field = HTMLInputElement | HTMLTextAreaElement;

/** The keyboard of one device screen. The emulator gives the screen element (it may be redrawn); the keyboard keeps its target by
 *  the field's id, name or position, so a redraw never loses what is typed. */
export class DeviceKeyboard {
  private el: HTMLElement | null = null;
  private target: Field | null = null;
  private key = "";
  private shift = false;
  private symbols = false;
  private english = false;
  constructor(private screen: () => HTMLElement | null, private t: T, private enabled: () => boolean = () => true) {
    if (typeof document === "undefined") return;
    document.addEventListener("focusin", (e) => this.focus(e.target as HTMLElement), true);
    let busy = false;                                                   // every redraw: fields ask for no system keyboard, an open keyboard comes back
    new MutationObserver(() => { if (busy) return; busy = true; queueMicrotask(() => { try { this.after(); } finally { busy = false; } }); })
      .observe(document.documentElement, { childList: true, subtree: true });
    // like a real phone: tapping a button in the app (Send, Next) keeps the keyboard and the caret; tapping anywhere else closes it
    const inApp = (n: HTMLElement): boolean => !!(this.screen()?.contains(n) && (n.matches?.(TYPING) || n.closest?.("button,a,[data-act],label,select,[role=button]")));
    document.addEventListener("pointerdown", (e) => {
      const n = e.target as HTMLElement;
      if (this.el && !this.el.contains(n) && !inApp(n)) this.hide();
    }, true);
    document.addEventListener("mousedown", (e) => {
      const n = e.target as HTMLElement;
      if (this.el && !this.el.contains(n) && inApp(n) && !n.matches?.(TYPING) && !n.closest?.("label,select")) e.preventDefault();
    }, true);
  }
  /** Called at the end of every draw: typing fields in the device screen ask for no system keyboard, and an open keyboard comes back. */
  after(): void {
    const s = this.screen(); if (!s || !this.enabled()) { this.hide(); return; }
    s.querySelectorAll<HTMLInputElement>(TYPING).forEach((f) => { if (!f.dataset["kbMode"]) f.dataset["kbMode"] = f.getAttribute("inputmode") ?? ""; f.setAttribute("inputmode", "none"); });
    if (!this.key) return;
    const f = this.find(s);                                                // the page redrew: follow the same field, keep the caret at its end
    if (!f) { this.hide(); return; }
    if (!(this.el && s.parentElement?.contains(this.el)) || !s.classList.contains("kb-open")) { this.open(f); return; }
    if (f !== this.target) {
      this.target = f;
      if (document.activeElement !== f) { f.focus({ preventScroll: true }); try { f.setSelectionRange(f.value.length, f.value.length); } catch { /* no caret */ } }
      this.place();
    }
  }
  private find(s: HTMLElement): Field | null {
    const [how, v] = this.key.split(":", 2) as [string, string];
    if (how === "id") return s.querySelector<Field>(`#${CSS.escape(v)}`);
    if (how === "name") return s.querySelector<Field>(`[name="${CSS.escape(v)}"]`);
    return s.querySelectorAll<Field>(TYPING)[Number(v)] ?? null;
  }
  private focus(n: HTMLElement): void {
    const s = this.screen();
    if (!s || !this.enabled() || !n?.matches?.(TYPING) || !s.contains(n)) return;
    const f = n as HTMLInputElement;
    if (!f.dataset["kbMode"]) { f.dataset["kbMode"] = f.getAttribute("inputmode") ?? ""; f.setAttribute("inputmode", "none"); }
    this.key = f.id ? `id:${f.id}` : f.name ? `name:${f.name}` : `at:${[...s.querySelectorAll(TYPING)].indexOf(f)}`;
    this.open(f);
  }
  private lang(): string { return (this.target?.closest("[lang]") as HTMLElement | null)?.lang || document.documentElement.lang || "en"; }
  private kind(): KbKind { const f = this.target; return f ? kbKindOf(f.getAttribute("type") ?? "text", f.dataset["kbMode"] ?? "") : "letters"; }
  private open(f: Field): void {
    const s = this.screen(); if (!s) return;
    this.target = f;
    const host = s.parentElement ?? s;
    if (!this.el || !host.contains(this.el)) {
      this.el?.remove(); this.el = document.createElement("div"); this.el.className = "lkb"; this.el.setAttribute("data-names", "off");
      if (getComputedStyle(host).position === "static") host.style.position = "relative";
      host.appendChild(this.el); this.wire();
    }
    if (s.dataset["kbH"] === undefined) {                                // like a real phone, the screen's visible part shrinks above the keys
      s.dataset["kbStyle"] = s.getAttribute("style") ?? "";              // (kept on the element, so a redraw that resets its class never measures the shrunk size)
      s.dataset["kbH"] = String(s.offsetHeight);
      s.dataset["kbFixed"] = "1";
    }
    s.style.overflowY = "auto"; s.classList.add("kb-open");
    this.draw();
    this.place();
    requestAnimationFrame(() => this.place());
  }
  /** The keyboard covers the bottom of the device screen exactly, like a real one; the screen above it shrinks, so a composer or save bar sits just above the keys. */
  private place(): void {
    const s = this.screen(), el = this.el; if (!s || !el) return;
    const host = (el.offsetParent as HTMLElement | null) ?? s.parentElement; if (!host) return;
    // emulators are often drawn smaller to fit the page, so measure on screen and turn it back into the device's own pixels
    const sr = s.getBoundingClientRect(), hr = host.getBoundingClientRect(), k = sr.width / (s.offsetWidth || sr.width || 1) || 1;
    const full = Number(s.dataset["kbH"] ?? s.offsetHeight) || s.offsetHeight;
    const h = Math.min(el.offsetHeight || 220, Math.round(full * 0.6));
    if (s.dataset["kbFixed"] === "1") { s.style.blockSize = `${full - h}px`; s.style.minBlockSize = "0"; s.style.maxBlockSize = `${full - h}px`; }
    else s.style.paddingBlockEnd = `${h}px`;
    const room = s.dataset["kbFixed"] === "1" ? full - h : s.clientHeight - h;
    el.style.insetInlineStart = "auto"; el.style.insetInlineEnd = "auto";
    el.style.left = `${(sr.left - hr.left) / k - host.clientLeft + s.clientLeft}px`; el.style.width = `${s.clientWidth}px`;
    el.style.top = `${(sr.top - hr.top) / k - host.clientTop + full - h}px`; el.style.maxHeight = `${h}px`;
    const f = this.target; if (!f) return;                               // the field being typed in always shows just above the keys
    let box: HTMLElement | null = f.parentElement;                       // scroll whichever part of the screen holds it
    while (box && box !== s && !(box.scrollHeight > box.clientHeight && /auto|scroll/.test(getComputedStyle(box).overflowY))) box = box.parentElement;
    const sc = box ?? s, cr = sc.getBoundingClientRect(), fr = f.getBoundingClientRect();
    const bottom = Math.min(cr.bottom, sr.top + room * k) - 8 * k, top = Math.max(cr.top, sr.top) + 8 * k;
    if (fr.bottom > bottom) sc.scrollTop += (fr.bottom - bottom) / k;
    else if (fr.top < top) sc.scrollTop -= (top - fr.top) / k;
  }
  hide(): void {
    this.el?.remove(); this.el = null; this.key = ""; this.target = null;
    const s = this.screen();
    if (s && s.dataset["kbH"] !== undefined) { s.classList.remove("kb-open"); const st = s.dataset["kbStyle"] ?? ""; if (st) s.setAttribute("style", st); else s.removeAttribute("style"); delete s.dataset["kbStyle"]; delete s.dataset["kbH"]; delete s.dataset["kbFixed"]; }
  }
  private rows(): string[][] {
    const k = this.kind();
    if (k === "number") return K.number;
    if (k === "phone") return K.phone;
    if (this.symbols) return K.symbols;
    const rows = this.english ? K.layouts["latin"]! : kbLayout(this.lang());
    return rows.map((r) => r.map((c) => (this.shift ? c.toLocaleUpperCase(this.lang()) : c)));
  }
  private draw(): void {
    if (!this.el) return;
    const k = this.kind(), t = this.t, lang = this.lang(), own = (K.languages[lang] ?? "latin") !== "latin" || ["ja", "zh-Hans", "zh-Hant"].includes(lang);
    const keyBtn = (c: string): string => `<button type="button" class="lkb-k" data-kb="${kbEsc(c)}" tabindex="-1">${kbEsc(c)}</button>`;
    // buttons only: the keys are reached with the arrows and OK, like a real kiosk or TV keyboard
    const s = this.screen(), keysOnly = !!(s && (s.dataset["touch"] === "no" || s.closest('[data-touch="no"]')));
    const pad = k === "number" || k === "phone";
    const rows = this.rows().map((r) => `<div class="lkb-row">${r.map((c) => (c === "⌫" ? `<button type="button" class="lkb-k lkb-wide" data-kbx="del" aria-label="${kbEsc(t("kb_delete"))}" tabindex="-1">⌫</button>` : keyBtn(c))).join("")}</div>`).join("");
    const orders = !pad && !this.symbols && !this.english && lang === "am" ? `<div class="lkb-row">${K.ethiopic_orders.map((o, i) => `<button type="button" class="lkb-k" data-kbo="${i + 1}" tabindex="-1">${kbEsc(o)}</button>`).join("")}</div>` : "";
    const note = !pad && !this.english && (lang === "ja" || lang.startsWith("zh")) ? `<p class="lkb-note">${kbEsc(t("kb_word_list"))}</p>` : "";
    const bottom = pad
      ? `<div class="lkb-row"><button type="button" class="lkb-k lkb-done" data-kbx="done" tabindex="-1">${kbEsc(t("kb_done"))}</button></div>`
      : `<div class="lkb-row">
        ${this.symbols ? "" : `<button type="button" class="lkb-k lkb-wide" data-kbx="shift" aria-pressed="${this.shift}" aria-label="${kbEsc(t("kb_shift"))}" tabindex="-1">⇧</button>`}
        <button type="button" class="lkb-k lkb-wide" data-kbx="sym" aria-label="${kbEsc(t(this.symbols ? "kb_letters" : "kb_symbols"))}" tabindex="-1">${this.symbols ? "ABC" : "123"}</button>
        ${own ? `<button type="button" class="lkb-k" data-kbx="globe" aria-label="${kbEsc(t("kb_switch"))}" tabindex="-1">🌐</button>` : ""}
        ${k === "email" ? K.email_keys.map(keyBtn).join("") : ""}
        <button type="button" class="lkb-k lkb-space" data-kbx="space" tabindex="-1">${kbEsc(t("kb_space"))}</button>
        <button type="button" class="lkb-k lkb-wide" data-kbx="del" aria-label="${kbEsc(t("kb_delete"))}" tabindex="-1">⌫</button>
        <button type="button" class="lkb-k lkb-done" data-kbx="done" tabindex="-1">${kbEsc(t("kb_done"))}</button></div>`;
    this.el.setAttribute("role", "group");
    this.el.setAttribute("aria-label", t("kb_keyboard"));
    this.el.innerHTML = `${note}${rows}${orders}${bottom}`;
    if (keysOnly) this.el.querySelectorAll("button").forEach((b) => b.removeAttribute("tabindex"));
  }
  private wire(): void {
    const el = this.el; if (!el) return;
    el.addEventListener("pointerdown", (e) => e.preventDefault());          // the field keeps its focus and caret
    el.addEventListener("click", (e) => {
      const b = (e.target as HTMLElement).closest<HTMLElement>("button"); if (!b) return;
      e.stopPropagation();
      const f = this.target; if (!f) return;
      const ch = b.dataset["kb"], x = b.dataset["kbx"], o = b.dataset["kbo"], lang = this.lang();
      if (ch !== undefined) this.type(ch, lang);
      else if (o) this.set(ethiopic(f.value.slice(0, f.selectionStart ?? f.value.length), Number(o)), f.value.slice(f.selectionEnd ?? f.value.length));
      else if (x === "del") this.del();
      else if (x === "space") { if (lang === "ja" && !this.english) this.finishKana(); this.type(" ", lang); }
      else if (x === "shift") { this.shift = !this.shift; this.draw(); }
      else if (x === "sym") { this.symbols = !this.symbols; this.draw(); }
      else if (x === "globe") { this.english = !this.english; this.draw(); }
      else if (x === "done") { if (lang === "ja") this.finishKana(); f.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true })); f.dispatchEvent(new Event("change", { bubbles: true })); this.hide(); f.blur(); }
    });
  }
  private set(before: string, after: string): void {
    const f = this.target; if (!f) return;
    const max = f.maxLength > 0 ? f.maxLength : Infinity;
    const v = (before + after).slice(0, max);
    f.value = v;
    const pos = Math.min(before.length, v.length);
    try { f.setSelectionRange(pos, pos); } catch { /* number fields have no caret */ }
    f.dispatchEvent(new Event("input", { bubbles: true }));
  }
  private type(ch: string, lang: string): void {
    const f = this.target; if (!f) return;
    const a = f.selectionStart ?? f.value.length, b = f.selectionEnd ?? f.value.length;
    let before = f.value.slice(0, a);
    const after = f.value.slice(b);
    const english = this.english || this.kind() !== "letters" || this.symbols;
    if (!english && lang === "ko") before = hangul(before, ch);
    else if (!english && lang === "ja") before = romaji(before + ch);
    else before += ch;
    this.set(before, after);
    if (this.shift) { this.shift = false; this.draw(); }
  }
  private finishKana(): void { const f = this.target; if (f) this.set(romajiDone(f.value.slice(0, f.selectionStart ?? f.value.length)), f.value.slice(f.selectionEnd ?? f.value.length)); }
  private del(): void {
    const f = this.target; if (!f) return;
    const a = f.selectionStart ?? f.value.length, b = f.selectionEnd ?? f.value.length;
    if (a !== b) this.set(f.value.slice(0, a), f.value.slice(b));
    else if (a > 0) { const chars = [...f.value.slice(0, a)]; chars.pop(); this.set(chars.join(""), f.value.slice(b)); }
  }
}
