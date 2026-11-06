# Font files (release gate)

Place the self-hosted WOFF2 files here before a web release (the paths are used by `design/fonts.css`):
inter-latin, inter-latin-ext, inter-cyrillic, inter-greek, inter-vietnamese, montserrat-latin, montserrat-latin-ext, montserrat-cyrillic, montserrat-vietnamese (all `.woff2`).

- Inter and Montserrat are open-source fonts under the SIL Open Font License. Download the official releases and subset them by script; keep the licence text in `fonts/LICENSES/`.
- The build environment had no internet access, so the files are NOT included in this repository. Run `python3 design/check_fonts.py` in CI: it fails the release if a file is missing or the Latin first load is over 100 KB.
- Native apps (Android, iOS) bundle the same fonts in their resources.
