# LynkOmni font system

One registry, `scripts.v1.json`, says which languages LynkOmni shows, their script, their writing direction and their fonts. Everything else is built from it.

| Script | Direction | Languages | Headings | Body |
|---|---|---|---|---|
| Latin | left to right | English, French, Spanish, Swahili, Kinyarwanda | Montserrat | Inter |
| Arabic | right to left | Arabic, Persian, Urdu, Pashto, Kurdish (Sorani), Sindhi, Uyghur | Noto Kufi Arabic | Noto Sans Arabic |
| Hebrew | right to left | Hebrew, Yiddish | Noto Sans Hebrew | Noto Sans Hebrew |
| Devanagari | left to right | Hindi | Noto Sans Devanagari | Noto Sans Devanagari |
| Cyrillic, Greek, Vietnamese | left to right | (ready for future packs) | Montserrat (Greek: Inter) | Inter |

- **Source and licence:** official files from github.com/google/fonts, SIL Open Font License 1.1 (free to bundle in apps). Licences in `LICENSES/`; exact commit and checksums in `sources.json`.
- **Online:** `design/fonts.css` gives each file a unicode range, so a page downloads only the scripts it shows. The Latin pair is about 68 KB (budget 100 KB); each other script stays under 220 KB.
- **Offline:** every file is self-hosted; never a font website. Apps store `fontFilesFor(languages)` from `ts/src/fonts.ts` (Latin always, plus each language's script), or `ALL_FONT_FILES` for a shared shop device. Emulators carry the Latin files inside their single file.
- **Right to left:** apps set `<html lang dir>` with `rootAttributes(lang)`; `fonts.css` and `tokens.css` also switch direction by language as a fallback. Use logical CSS (`margin-inline-start`), mirror arrows, never letter-space or uppercase Arabic or Devanagari (the rules are generated).
- **Shaping:** Arabic and Devanagari files keep every OpenType feature (joining, marks, conjuncts). Latin keeps a short list to stay small.
- **Add a language:** add it to `languages` (with its distinctive letters), and its script if new; run `python3 design/fonts/build_fonts.py --source-root <google/fonts checkout> --upstream-commit <sha>`. A language in a country pack that is missing here fails the tests.
- **Checks:** `python3 design/check_fonts.py` and `tests/test_fonts.py` (every language's letters present in both fonts, budgets, licences, generated files current, no font website) run in CI.
- **Specimen:** `python3 design/fonts/specimen.py out.html` writes an offline page showing every language.
- **Later:** Android and iOS apps bundle the same fonts when those app projects exist (ledger item `native_fonts`). Native speakers check translations before launch (user action `native-speaker-review`).
