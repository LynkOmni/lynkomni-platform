# LynkOmni change log

What changed in each version, in plain words, newest first. Version numbers: `0.MINOR.PATCH` until the first pilot (a new feature raises MINOR, a fix raises PATCH). Each version has a Git tag `v<number>`.

## v0.22.1 (2026-11-08)
- Showcase: `python3 tools/showcase.py` builds one offline page of everything completed (emulator pages, the 15 build steps, numbers from tools/blueprint_numbers.py, products with prices and pictures, LynkVCard faces, charts and diagrams, other pictures, store and web images) from web/showcase/showcase.v1.json and the code. Published for the owner after every section (owner rule 2026-11-08).

## v0.22.0 (2026-11-08)
Build section 2, LynkOmni Account and sign-in (blueprint 41 S row 2, 42 J row 2 and 44 L row 2), built and locked.
- The account rules in Python (identity/account.py, on the identity platform and the layered recovery of section 10): sign-up as four steps (username in the Instagram format, a verified phone or email, a passkey, the recovery code shown once); passkeys (never the last one removed, a fresh step-up to remove); sessions bound to one site, with an alert on every channel and no link in it when a sign-in comes from a new device or place; the Security Center (passkeys and devices, sessions, recent events, recovery settings, connected apps and sharing, memberships); data-sharing consents with a scope, a purpose and an end (health pack, accountant, lender, developer app, support, supplier sell-through; capped days per scope); the takeover safeguards of 43 H (a 24-hour wait before payout details change unless a second enrolled device approves; exports need a step-up and never run from a device still restricted after recovery); download-my-records with a 30-day due date; closing with a 30-day grace period and a LynkID and username that are never reused; businesses, leaving (never the last owner) and the accountant's client switcher, which shows a client only with the owner's consent; subscriptions read from billing; N14 Start a business (four steps, "Coming to your country soon." where no gateway is signed, nothing approved before the authority answers) behind a new `registration` service and its sandbox gateway in the provider ledger; N4 standing payments (the customer's own capped instruction, held by the licensed provider, told every time, revocable). 17 Python tests.
- The account event register identity/events.v1.json: every account event the cloud writes, with references only; a test keeps every automation trigger up to the built sections on a registered event.
- LynkFlow runs (services/flow.py): only registered automations run, once per trigger, loop-guarded, with "Why did this happen?", history and an off switch per subject. The seven section-2 automations run on it (identity/automations.py): sign-in alert, recovery guide, consent expiry, data-request timer, start-business tracker, quiet-business watch (draft) and renewal reminders.
- The same rules in TypeScript (ts/src/account.ts), proved against the shared vectors contract/vectors/account.v1.json (tools/account_vectors.py). 4 new TypeScript tests (71 in all).
- The account-site emulator (web/emulators/account-site): account.lynkomni.com in a browser window at computer, tablet and phone size, built on the shared shell: sign-in with a passkey, the four sign-up steps, the three recovery paths with their waits and the restricted day, the Security Center, businesses with the client switcher, orders, transactions, wallet, plans, memberships, privacy and data, notifications, support, payslips, standing payments and Start a business; in all 26 languages (25 packs written and checked), walked by the layout and accessibility test at every size.
- The shared shell's words moved to web/shell/strings.en.json with their 26 packs, merged into every emulator built on the shell, so the shell is translated once.
- Catalog: the account site's addresses (/, /sign-in, /sign-up, /recover, /profile, /security, /businesses, /wallet, /billing, /memberships, /privacy, /support, /start/{LODOC}); the `accountant` role (reads only, with consent).
- Leftovers adjusted in this section (owner rule of 8 November): the data-request timer is a daily schedule; two shell events of section 1 (CountryPackSelected, ConnectionWeak) are now registered; an invented identifier (LOSEC-) in the browser-frame notice is LONTF- and a test keeps emulator ids to the registry; the recovery and payout waits are hours, as the blueprint says, not days; placeholder-only strings pass the script check. The account-site file budget is 900 KB with its reason (26 languages of the shell and the site in one offline file).

## v0.21.1 (2026-11-08)
- Dependency updates taken in (owner rule of 8 November: merge them without asking once the checks are green and nothing else is pending): the GitHub Actions moved to their current major versions (checkout 7, setup-node 6, setup-python 6, setup-java 6, cache 6, upload-artifact 5) and the pinned Python and Node packages to their latest releases (Dependabot pull requests #29 to #36; #30 was superseded by the same change on #39).
- The Kotlin job caches its Gradle downloads and retries up to five times when GitHub's release store times out, so a 504 no longer fails a run.
- Traditional Chinese: the engine's language tag is `zh_Hant` (MADLAD-400 writes the script with an underscore); the test that had pushed it to a hyphen now accepts the underscore, and the translation workflow passes again.

## v0.21.0 (2026-11-08)
Build section 1, the shared shell (blueprint 41 S row 1 and 44 L row 1), built and locked.
- The shell component library (ts/src/shell.ts, web/shell/shell.css): translator, viewport, header, navigation (tabs on a phone, rail on a tablet, sidebar on a computer), app launcher, account menu, language and region sheet, "find or do anything" search and command bar, help panel, notifications with quiet hours, every screen state with its picture and next step, connection chip and sync sheet, data-saver plan, deep links from the address map, protected zones, undo toasts, continue-on-any-device handoff, two-language chat banner and notes, the username field and accessible charts. 19 TypeScript tests.
- The browser-frame emulator (web/emulators/browser-frame): the shell in a browser window at computer, tablet and phone size, every state, every overlay, dark, lite and sunlight modes, the country chooser and all languages.
- Speed and accessibility in the build: size budgets per emulator (web/budgets.v1.json, tests/test_speed_budget.py) and LynkOmni's own accessibility checker (tools/a11y/check.js) run on every screen in English and the right-to-left test, light and dark; a new `on-brand-hover` token and contrast fixes that came out of it.
- Icons: @lynkomni/icons 1.4.0 vendored (eleven shell icons and the twelve low-literacy tiles); emulators embed only the icons they use.
- Language wave 1: German, Italian, Turkish, Indonesian, Vietnamese, Russian, Chinese (simplified and traditional), Japanese and Korean, making 26 languages. Chinese, Japanese and Korean fonts are split into blocks within a per-slice budget; every emulator is translated into all 26 and the layout test walks every screen in each of them at every size.
- Leftovers adjusted in this section (owner rule of 8 November): the Chinese traditional machine-translation code, visuals regenerated after the token change, the chat demo always showing two different languages, and the layout test measuring after the browser's next frame.

## v0.20.0 (2026-11-08)
Step 0, one global structure (blueprint 42 A and 44 L row 0), built and locked.
- Contract version 2: every amount is an integer in its currency's minor unit and carries its ISO 4217 currency; one currency list (contract/currencies.v1.json, 37 currencies) that the contract and the code both read; version 1 is never edited and stays readable through the upcaster (contract/upcasters.v1.json, contract/upcast.py); the 104 event names of blueprint sections 42 I, 44 E, 44 G, 44 I (N1 to N14), 44 J and 45 A are registered with their payloads, and 22 new device commands issue the new device events (agent, financing and delivery requests are class C: never queued offline). Generated by contract/tools/build_v2.py; the validator runs 893 checks.
- Emulators open on a neutral sample country and carry a country chooser listing every country pack; what works in a country is read from the provider ledger; a test fails if a country name or currency code is ever written into an emulator's source.
- Rule texts, revenue stages and test titles speak of the country pack: one pending-fiscal adapter for any tax authority not yet confirmed in writing; stage names proving ground, regional scale, global scale; tools/blueprint_numbers.py also prints the contract version, event types, currencies and country packs.
- One global chart of accounts (contract/chart-of-accounts.v1.json, 20 accounts) and the double-entry journal as a projection of the event log at every tier (core/accounts.py, LynkAcc journal and trial balance); a country pack may map the global codes to its own labels.
- The shared username check (contract/usernames.v1.json, core/usernames.py, ts/src/usernames.ts, 42 shared vectors): Instagram format 3 to 30, reserved words from the rule, the product catalog, the address hosts and the provider ledger, web-address endings refused, look-alikes held for review, one owner forever, never reissued, old names redirect, transfer only by a recorded staff decision with a 90-day redirect.
- Portuguese is the 16th language (fonts, both emulators, layout test). The dependency-updates automation runs through .github/dependabot.yml as drafts.

## v0.19.2 (2026-11-08)
- The owner's 14 to-dos locked as the REMINDER in the provider ledger (none mandatory before building).
- General rule (owner, 8 November 2026): anything left out is adjusted automatically during the build, in the section it belongs to, and recorded; written into CLAUDE.md, the decisions diary and blueprint section 40.
- Final deep scan, part two. The address map now holds every product's place in the Business app (/business/money, /pay-links, /recovery, /cards, /plans, /loyalty, /growth), the shared LynkStat dashboards (/analytics/shared) and the account site's /invoices, /orders and /transactions, with a new test: a product's place must be a registered address, so the catalog and the address map can never drift apart.
- Blueprint brought in line with the later decisions in sections 9, 13, 16, 17, 20, 21, 23, 24, 25, 28, 29, 30, 38, 41, 42 and 45: the global rule replaces the one-type pilot and one-country segments, legal pages at /legal, support levels from billing, 40 identifier types, price lock version 3, LynkInv in place of the old invoicing table, six new risk rows, the stack table as it runs in CI today, and the automation table read from the register.

## v0.19.1 (2026-11-08)
- Nine more automations for speed and trust: undo for anything within 30 seconds, a speed budget per screen, continue on any device, a quiet-business watch for support, renewal reminders, one-tap reorder, an automatic accessibility check in the build, automatic data saver, and a visible reply-time promise in support. 105 automations in all.

## v0.19.0 (2026-11-08)
- Automation across LynkOmni: one list of 96 automations, from the daily close and stock reorders to invoice reminders, support triage and partner failover, each with a clear level (tell, prepare for a person, do with undo, or do) and checked by safety tests.
- LynkAssist is placed in every section to answer, guide, prepare drafts, explain, summarise, watch and support, and it never moves money or acts without the right confirmation. Custom automations come with LynkAssist plans (0, 3, 20, unlimited).
- The expense model includes LynkAssist's running cost across the ecosystem.

## v0.18.0 (2026-11-08)
- LynkStat, the new analytics service, takes over LynkDash: $0, $12, $29 and $79. LynkOps now bundles four services (accounting, invoicing, CRM and analytics) at $0, $20, $49 and $129. LynkSuite keeps its price, so it is now about 37% cheaper than buying its services.
- Two new record numbers: LODOC- for business documents and LOREV- for verified reviews.
- The limits and fees of 14 new services are set (restaurant mode, payroll, tax filing, standing payments, e-signature, get paid early, device lease, delivery, warranty, reviews, buy together, supplier sell-through, Academy, start a business). Each is built in its own build section.
- New expense model: LynkOmni's expenses and net profit per day, month and year, beside the revenue. Every figure is an assumption.
- The address map knows every new path and the partners.lynkomni.com door; usernames follow the Instagram format.
- Fixed: two daily limits (developer API calls and ads) now count days in UTC, like the event times, so they no longer break around midnight.

## v0.17.0 (2026-11-07)
- The whole LynkOmni system was reviewed end to end and every conflict fixed, so all parts work as one. There is now one product list, one address map and one email map, and automatic checks stop them from ever disagreeing with the footer, billing or the code.
- Support follows the plan: every product's Plus gives priority help, Pro higher priority and Max a dedicated manager, including LynkPOS and LynkSuite.
- The footer lists LynkOps, LynkCheckout and LynkRecover. The "not available" picture is now "coming soon", matching the rule that users never read "not available".
- The revenue model counts every income stream across the ecosystem (agent services, setup fees, hardware, partner referrals) minus discounts and partner costs, per day, month and year. The new rates are assumptions.

## v0.16.3 (2026-11-07)
- Fourteen safeguards added to the email plan, among them a second emergency admin account, phishing-proof sign-in for both admins, and no sign-in links in security emails. The owner's steps after paying for Google Workspace are on the action list.

## v0.16.2 (2026-11-07)
- The full list of LynkOmni and CruxOmni email addresses is agreed and written down, with the steps to set them up. Sign-in codes and security alerts come from a no-reply address; every other email can be answered.

## v0.16.1 (2026-11-07)
- The LynkPOS services are agreed and written down: 31 services in 6 groups, agent point mode, how each one reaches the books, customers, stock and reports, and how LynkOmni stays out of holding money. They are built in build section 3.
- New working rule: the real-device emulators are updated whenever the product changes, and every agreed emulator has its place in the build order.

## v0.16.0 (2026-11-07)
- New prices, locked as version 2. LynkPOS is now $0, $12, $29 and $79 a month, with every agent, collection and partner service at every level, unlimited sales, and an Agent point mode planned for vendors who run LynkPOS full-time.
- Three standalone services: LynkAcc for accounting (it takes over LynkLedger), LynkInv for invoicing (moved out of LynkCheckout, which keeps pay links and QR) and LynkCRM for customers. Each can be bought alone; LynkOps puts all three together for less ($0, $12, $29, $79).
- Invoicing is friendlier on Free: five invoices a month, credit notes and a pay link on every invoice at every level.
- LynkSuite now holds nine services for $0, $29, $75 and $195, and also replaces LynkOps. A business is never billed twice: bundles replace their services, LynkPOS Pro and Max include LynkRewards, and a service above its bundle's level costs only the difference.
- The revenue model was re-run with the new prices (the adoption mix, including the new services, is an assumption, not a forecast).
- New pictures for LynkAcc, LynkInv, LynkCRM and LynkOps, and the LynkSuite picture now shows nine services. The website footer lists LynkAcc, LynkInv and LynkCRM.
- LynkInv and LynkCRM work in every country from day one, like LynkPOS and LynkAcc, because they need no partner.

## v0.15.0 (2026-11-07)
- The LynkOmni merchant app, as a phone you can click: sign in with a phone number and a code, the phone registers itself with its own security key, then the five tabs Home, Sell, Stock, Chats and Business.
- Home changes with the person: the owner sees today's sales and profit, a big New sale button, stock that needs attention, unread customer chats, one insight for the day and what is waiting to send; staff see selling and stock first, and profit only if the owner allows it.
- Selling works with or without internet. Stock may go below zero (a sale is never blocked) and the owner is told to count it. Stock received, counted or removed with a reason. Customer chats show their real state (queued or sent). Business shows the day's closing summary, every LynkOmni service with "Coming to your country soon." and Notify me where its partner is not signed, and who may see profit.
- The connection chip and sync sheet: a weak connection counts as offline and sends when it can; "stay offline to save data"; nothing is ever shown as paid before the provider confirms.
- All screens in all 15 languages (translated by Claude, checked automatically), and the layout test now opens every phone screen in every language at desktop and phone size.
- The owner's actions list now includes the company email (domains bought), company registration, the GitHub Team plan (last) and the Google Cloud account.

## v0.14.0 (2026-11-07)
- The LynkPOS terminal emulator now works in all 15 languages (English, French, Spanish, Swahili, Kinyarwanda, Arabic, Persian, Urdu, Pashto, Kurdish, Sindhi, Uyghur, Hebrew, Yiddish, Hindi), with right-to-left layout where needed, all inside the offline file. Every screen text is translated by Claude and passes automatic checks: names, amounts and placeholders unchanged, no repeated or added words, the right script for each language, nothing left in English.
- The translation engine for text people type is installed: Google's MADLAD-400 model (Apache 2.0 licence, so commercial use is allowed), replacing Meta's NLLB-200, whose licence forbids commercial use. It is installed on GitHub's machines (workflow "translation"), which check the licence and pin the exact model version. It refuses any translation that drifts in meaning, repeats itself or adds words, and then shows the original text instead.
- The automatic layout check now opens every screen in every language at desktop and phone size, with the brand's Noto fonts for Arabic, Hebrew and Hindi.
- Still to come: running the engine on LynkOmni's own server for text people type; until that server exists such text shows in the original, marked queued.

## v0.13.1 (2026-11-06)
- Translation works offline: screen text is translated ahead of time into language packs that ship inside the apps, so every language works with no internet and no engine on the phone. Text people type is translated on LynkOmni's server when online, saved on the device, and shown in the original (marked queued) when offline.
- The Meta NLLB-200 engine is connected behind the translation slot (compact int8 version, loaded only from LynkOmni's own server, never downloaded while the app runs). Every language has its NLLB code. The model itself is installed once package installs are allowed.

## v0.13.0 (2026-11-06)
- Machine translation for every language, the way large platforms do it: one engine slot (Meta's open NLLB-200 model, the engine behind Facebook's translations, to be installed when package installs are allowed). Brand, product and provider names, amounts and numbers are protected; a damaged translation is refused and English is kept.
- Translations can never break a screen: the terminal emulator has a long-text test and a right-to-left test, and a new automatic check opens every screen in four languages at desktop and phone size and fails if any text spills over or the device changes size.
- Native-speaker review dropped from the owner's actions list.

## v0.12.4 (2026-11-06)
- LinkedIn link corrected: LynkOmni is a showcase page under the CruxOmni Group company page.

## v0.12.3 (2026-11-06)
- The footer now links to the official LynkOmni accounts on LinkedIn, X, Facebook, Instagram, YouTube, TikTok and WhatsApp Business. The LynkOmni name is claimed on all ten platforms.

## v0.12.2 (2026-11-06)
- Recorded that the remaining owner decisions follow the global rule: every business type, standard devices, every supported language, competitors stay competitors, merchants own their data.

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
