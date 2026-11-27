"""The device's own on-screen keyboard in touch-screen emulators (catalog/keyboards.v1.json; TypeScript port ts/src/keyboard.ts,
shared vectors contract/vectors/keyboards.v1.json). Pure rules:
  layout(lang)          the rows of letters a real phone in that language shows
  kind_of(type, mode)   which keyboard a typing field gets: letters, email, number or phone
  hangul(text, jamo)    Korean letters join into syllables as they are typed
  ethiopic(text, order) an Amharic consonant takes the vowel form of the key pressed after it
  romaji(text)          Japanese romaji turns into kana as it is typed (romaji_done ends a last n)"""
import json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
with open(os.path.join(ROOT, "catalog", "keyboards.v1.json"), encoding="utf-8") as _f:
    REGISTER = json.load(_f)


def layout(lang):
    return REGISTER["layouts"][REGISTER["languages"].get(lang, "latin")]


def kind_of(input_type, input_mode=""):
    t, m = (input_type or "").lower(), (input_mode or "").lower()
    if t == "email" or m == "email": return "email"
    if t == "tel" or m == "tel": return "phone"
    if t == "number" or m in ("numeric", "decimal"): return "number"
    return "letters"


# Korean: initial, medial and final letters of the standard two-set keyboard, joined into one syllable (U+AC00 + ...).
_L = "ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ"
_V = "ㅏㅐㅑㅒㅓㅔㅕㅖㅗㅘㅙㅚㅛㅜㅝㅞㅟㅠㅡㅢㅣ"
_T = " ㄱㄲㄳㄴㄵㄶㄷㄹㄺㄻㄼㄽㄾㄿㅀㅁㅂㅄㅅㅆㅇㅈㅊㅋㅌㅍㅎ"
_VV = {("ㅗ", "ㅏ"): "ㅘ", ("ㅗ", "ㅐ"): "ㅙ", ("ㅗ", "ㅣ"): "ㅚ", ("ㅜ", "ㅓ"): "ㅝ", ("ㅜ", "ㅔ"): "ㅞ", ("ㅜ", "ㅣ"): "ㅟ", ("ㅡ", "ㅣ"): "ㅢ"}
_TT = {("ㄱ", "ㅅ"): "ㄳ", ("ㄴ", "ㅈ"): "ㄵ", ("ㄴ", "ㅎ"): "ㄶ", ("ㄹ", "ㄱ"): "ㄺ", ("ㄹ", "ㅁ"): "ㄻ", ("ㄹ", "ㅂ"): "ㄼ", ("ㄹ", "ㅅ"): "ㄽ",
       ("ㄹ", "ㅌ"): "ㄾ", ("ㄹ", "ㅍ"): "ㄿ", ("ㄹ", "ㅎ"): "ㅀ", ("ㅂ", "ㅅ"): "ㅄ"}
_SPLIT = {v: k for k, v in _TT.items()}


def _syl(l, v, t=" "):
    return chr(0xAC00 + (_L.index(l) * 21 + _V.index(v)) * 28 + _T.index(t))


def _parts(ch):
    c = ord(ch) - 0xAC00
    if not 0 <= c < 11172: return None
    return _L[c // 588], _V[(c % 588) // 28], _T[c % 28]


def hangul(text, jamo):
    last = text[-1:] if text else ""
    p = _parts(last) if last else None
    if jamo in _V:
        if p and p[2] == " ":                                           # a syllable without a final takes a joined vowel
            vv = _VV.get((p[1], jamo))
            return text[:-1] + _syl(p[0], vv) if vv else text + jamo
        if p and p[2] != " ":                                           # the final moves to start the next syllable
            if p[2] in _SPLIT:
                a, b = _SPLIT[p[2]]
                return text[:-1] + _syl(p[0], p[1], a) + _syl(b, jamo)
            if p[2] in _L:
                return text[:-1] + _syl(p[0], p[1]) + _syl(p[2], jamo)
        if last in _L:
            return text[:-1] + _syl(last, jamo)
        return text + jamo
    if p and p[2] == " " and jamo in _T:
        return text[:-1] + _syl(p[0], p[1], jamo)
    if p and p[2] != " " and (p[2], jamo) in _TT:
        return text[:-1] + _syl(p[0], p[1], _TT[(p[2], jamo)])
    return text + jamo


def ethiopic(text, order):
    """order: 1 u, 2 i, 3 a, 4 e, 5 ə (no vowel), 6 o, applied to the last letter typed."""
    if not text: return text
    cp = ord(text[-1])
    if not 0x1200 <= cp <= 0x137F: return text
    base = cp - (cp - 0x1200) % 8
    return text[:-1] + chr(base + order)


_KANA = {"a": "あ", "i": "い", "u": "う", "e": "え", "o": "お"}
for c, row in {"k": "かきくけこ", "s": "さしすせそ", "t": "たちつてと", "n": "なにぬねの", "h": "はひふへほ", "m": "まみむめも", "y": "や ゆ よ",
               "r": "らりるれろ", "w": "わ   を", "g": "がぎぐげご", "z": "ざじずぜぞ", "d": "だぢづでど", "b": "ばびぶべぼ", "p": "ぱぴぷぺぽ"}.items():
    for v, k in zip("aiueo", row):
        if k != " ": _KANA[c + v] = k
_KANA.update({"shi": "し", "chi": "ち", "tsu": "つ", "fu": "ふ", "ji": "じ"})


def romaji(text):
    """Turns the romaji at the end of the text into kana, longest match first; a lone n before a consonant becomes ん."""
    for n in (3, 2, 1):
        tail = text[-n:]
        if len(tail) == n and tail.isascii() and tail in _KANA:
            head = text[:-n]
            if head.endswith("n"): head = head[:-1] + "ん"                # a doubled n before a syllable: こん + に
            return head + _KANA[tail]
    if len(text) >= 2 and text[-2] == "n" and text[-1].isascii() and text[-1] not in "aiueoyn":
        return text[:-2] + "ん" + text[-1]
    return text


def romaji_done(text):
    """When typing ends (space, Done, leaving the field), a last lone n becomes ん."""
    return text[:-1] + "ん" if text.endswith("n") else text


def validate():
    problems = []
    for lang, lay in REGISTER["languages"].items():
        if lay not in REGISTER["layouts"]: problems.append(f"{lang}: unknown layout {lay}")
    return problems
