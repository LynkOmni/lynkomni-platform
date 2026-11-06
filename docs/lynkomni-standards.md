# LynkOmni standards (the rule book)

Plain-language rules for building LynkOmni, grouped by topic. The master blueprint ("LynkOmni Master Blueprint", sections 1 to 37) is the authority for what LynkOmni is; this rule book says how it is built. The detailed engineering rules are in CLAUDE.md, and the checks named here enforce them automatically.

## 1. How we work
- Build the whole platform now; switch services on country by country.
- Build everything that can be built now. Work that needs a provider gets a practice version and is connected when the provider is signed. Only what truly cannot be done now waits, and it is written in the "later" list (providers/registry.v1.json).
- Every step that needs the owner (a repository, an account, a setting, a signature, a file) is written in the owner's actions list and said out loud at once.
- Nothing enters the blueprint until it is agreed. When asked to propose, only propose.
- Stay on the current topic. New ideas go on a later list, not into the work in progress.
- Explain every change in plain words, one small step at a time.

## 2. The finish checklist (definition of "done")
A piece of work is "done" only when every line is true:
1. It does what the blueprint says, and nothing the blueprint forbids.
2. It works without internet where the blueprint says it must, and never blocks an offline sale.
3. If it has a screen, the screen is in its real-device emulator, in light and dark, with brand fonts, and works at phone width.
4. If it needs a provider, it runs on a practice version, stays off for real users, and is in the provider ledger.
5. It has tests, and all tests pass.
6. All automatic GitHub checks are green with no warnings.
7. The owner's actions list and the later list are up to date.
8. It has a version number and a change-log line.
9. The owner got a plain-words summary, and the master blueprint is updated once the owner confirms.

## 3. Test before adding (safe changes)
- Every change is made on a separate copy (a branch named `lynkomni-<topic>`), never directly on the main version.
- A pull request shows exactly what changed. The automatic checks run on it.
- It is merged into the main version only when every check is green with no warnings. A failed check is fixed on the copy first.
- The main version therefore always works.

## 4. Version numbers and change log
- Each finished piece gets a version number: `0.MINOR.PATCH` until the first pilot, then `1.0.0`. A new feature raises MINOR (0.10 to 0.11); a fix raises PATCH (0.10.0 to 0.10.1).
- Each version gets a short entry in docs/lynkomni-changelog.md, written in plain words. When it reaches the main version, the version-tag workflow creates its Git tag (for example `v0.11.0`) automatically.

## 5. Decision diary
- Every decision the owner makes (prices, names, what is in or out, yes or no to an idea) is written in docs/lynkomni-decisions.md with its date, what was decided and where it is applied.
- Decisions are never deleted. A changed decision gets a new dated line that says what it replaces.

## 6. Product rules (summary; the blueprint has the detail)
- Money is whole numbers of the smallest unit plus a currency code, never decimals. LynkOmni never holds customer money.
- The event log is the source of truth. Devices send only the events they are allowed to send.
- No receipt or invoice is called a tax receipt or tax invoice until the tax authority confirms in writing.
- A payment is confirmed only when the provider confirms it. Paid but not delivered means a refund is owed.
- Language, currency and time zone change how things look, never the data or logic.
- Public identifiers come only from the identifier registry.
- Chat is customer-business and support only, and never claims end-to-end encryption.

## 7. Design, brand and pictures
- Colours and fonts come only from the design tokens; fonts and languages from design/fonts/scripts.v1.json. Never load fonts or logos from another website.
- Logos and icons come only from the brand module, by place, never by file.
- Every picture is made through the visuals module; never a missing or unfinished image; no stock art, no photos of real people.
- No fake provider names or logos, no made-up payment marks, no copies of other makers' devices.
- Accessibility: WCAG 2.2 AA, 44 px touch targets, never colour alone. Never claim AAA.
- Everything visual is a draft until a human designer reviews it.

## 8. Security and privacy
- Anything that moves money needs a human security review before release.
- Device databases are encrypted in production; device signatures must be hardware-backed before production sync.
- Card numbers never touch LynkOmni; card details show only inside the issuer's secure display after a fingerprint, face or PIN check.
- Support sees customer data only through a time-limited consent record. Credentials are never changed in chat.

## 9. Naming
- Every LynkOmni repository, folder and file is lowercase with hyphens and starts with `lynkomni` where it is a LynkOmni-specific name. Repositories live under the LynkOmni organisation on GitHub.

## 10. Checks that enforce these rules
| Check | What it guards |
|---|---|
| Python reference tests | Product rules, billing, contract, events |
| TypeScript tests and emulator build | Shared rules, fonts, brand, emulators are current |
| Rust, Kotlin, Swift | The same rules on the offline core and phones |
| PostgreSQL schema | The database schema runs |
| Names and secrets | No banned names, no secrets in the code |
| Brand and fonts | Logos, icons, placement rules, font files and languages |
| Visuals | Every picture present, current, on-brand |
| Providers | Placeholders registered; nothing on without a signed provider |
| Workflow warnings | Read after every run; any warning is fixed in the same task |
