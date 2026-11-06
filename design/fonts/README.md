# LynkOmni brand fonts

| Font | Used for | Weights kept | Files |
|---|---|---|---|
| Montserrat | Headings, display, badges, card tier lines | 500 to 700 (one variable file per script) | montserrat-latin, -latin-ext, -cyrillic, -vietnamese |
| Inter | Body text, forms, numbers, ledgers | 400 to 700, optical size fixed at text size | inter-latin, -latin-ext, -cyrillic, -greek, -vietnamese |

- **Source:** the official files in github.com/google/fonts (`ofl/montserrat`, `ofl/inter`). The exact commit and SHA-256 of every input and output are in `sources.json`.
- **Licence:** SIL Open Font License 1.1, kept in `LICENSES/`. The fonts are free to use, bundle and ship in apps. They may not be sold on their own.
- **Self-hosted only.** No page loads a font from another site (tests/test_fonts.py fails if one does). `design/fonts.css` lists the files with their unicode ranges, so a page downloads only the scripts it shows. Scripts neither font covers fall back to the device's own font.
- **Size:** the two Latin files every page needs first are about 68 KB together, inside the 100 KB budget in `tokens.v1.json`.
- **Rebuild:** `python3 design/fonts/build_fonts.py --inter <Inter[opsz,wght].ttf> --montserrat <Montserrat[wght].ttf> --upstream-commit <sha>`. Never edit the .woff2 files by hand.
- **Checks:** `python3 design/check_fonts.py` (every file present, budget kept) and `tests/test_fonts.py` run in CI (brand job).
- **Where they are used:** web pages via `fonts.css`; interface emulators embed the Latin files inside their single offline file; generated PNG images are drawn with them. The Android and iOS apps will bundle TTF instances from the same sources when their app projects exist (ledger item `native_fonts`).
