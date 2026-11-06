# LynkOmni change log

What changed in each version, in plain words, newest first. Version numbers: `0.MINOR.PATCH` until the first pilot (a new feature raises MINOR, a fix raises PATCH). Each version has a Git tag `v<number>`.

## v0.12.1 (2026-11-06)
- Recorded the nine approved experience improvements in the decision diary (they are built during building).

## v0.12.0 (2026-11-06)
- Global availability rule: every service is shown in every country. Services that need no licensed partner (POS, books, stock, dashboard, insights, chat) work everywhere, even in countries without their own settings file. Regulated services say "Coming to your country soon." with a Notify me option until their partner is signed, then switch on by themselves.
- Notify me list: needs the person's consent, keeps only a reference to their contact details, and tells each person once when the service arrives.

## v0.11.1 (2026-11-06)
- Recorded the owner's decisions on the footer social channels, the build order and the POS additions; added "claim the LynkOmni name on every social platform" to the owner's actions list.

## v0.11.0 (2026-11-06)
- Payment methods follow the country. Rwanda shows Visa, Mastercard, MTN MoMo, Airtel Money, bank transfer and QR payment; every other country shows its own list from its country file. Visa and Mastercard appear everywhere; crypto appears only where a country allows it and a licensed partner exists (none today).
- Six new LynkOmni payment icons (card, mobile money, bank, instant bank payment, phone wallet, digital asset) in icon package 1.3.0. Each method shows our icon with the provider's name as text; drawn copies of other companies' logos were removed from the footer preview. Official provider artwork is added only when a provider is signed and supplies it.
- The terminal emulator's payment screen uses the new icons. The brand-sync workflow now rebuilds the emulators by itself.
- Fixed a rare false alarm: the personal-data check no longer mistakes a random record ID for a phone number.

## v0.10.1 (2026-11-06)
- Working standards: a rule book (docs/lynkomni-standards.md), a finish checklist used on every change, changes tested on a copy before they enter the main version, version numbers with this change log, and a decision diary (docs/lynkomni-decisions.md).

## v0.10.0 (2026-11-06)
- LynkPOS handheld terminal emulator: a clickable card machine with printer, keypad, tap lights, card slot and scan key, running the real sale rules on practice providers.
- Brand fonts Montserrat and Inter, self-hosted and offline.
- Full font system for 15 languages, including Arabic, Persian, Urdu, Hebrew and the other right-to-left languages, and Hindi.
- Swift tests run on Linux on every change; a weekly Mac run.

## v0.9.9 (2026-11-06)
- Provider ledger: every provider service has a practice version and stays off until signed; the later list; the owner's actions list.
- LynkVCard card backs, physical OMNI card and CORE near-limit state; merchant logo safety check; install manifest for the web app.

## v0.9.8 (2026-11-06)
- Automatic pictures system: product illustrations, screen states, onboarding, charts, diagrams, share and store images, app and web icons.
- LynkVCard tier faces (EDGE, HUB, CORE, OMNI) and the tier ladder.

## v0.9.7 (2026-11-06)
- 43 one-colour icons from the lynkomni-icons package (product marks, status icons, everyday icons).

## v0.9.6 (2026-11-06)
- Invoices, receipts and emails drawn with the brand module (logo rules by tier, wordmark on receipts).

## v0.9.5 (2026-11-06)
- Logo placement rules for every place; "Powered by LynkOmni" rule; prices raised and locked at version 1.

Version tags are created automatically by the version-tag workflow when a new entry reaches main (from v0.10.1 on; v0.9.5 was tagged by hand, v0.10.0 has no tag).

Earlier versions (up to v0.9.4) are described in README.md and the master blueprint, sections 1 to 29.
